"""Resolve the original song BGCHANGES, including still images and transitions."""
import argparse, io, posixpath, re
from pathlib import PurePosixPath
from common import *
from simfile import Clock, Reader, unescape
from PIL import Image

FPS=30
DECODER_DELAY=2257/48000
VIDEO_ADVANCE=1/FPS
TRANSITIONS={'':0.,'CrossFade':1.,'CrossFade_Fastest':.5}

def norm(s):return posixpath.normpath(unescape(s).replace('\\','/')).casefold()

def image_reference(reference, anchor, files, extensions=None):
    base=files[anchor]
    wanted=norm(posixpath.join(base['folder'],reference))
    logical=norm(posixpath.join(posixpath.dirname(base['logical']),reference))
    hits=[f for f in files.values() if f['pack']==base['pack']
          and f['extension'] in (extensions or {'.png','.jpg','.jpeg','.bmp','.webp','.gif'})
          and (norm(f['logical'])==logical or
               (f['kind']==base['kind'] and f['container']==base['container'] and norm(f['member'])==wanted) or
               (f['kind']=='file' and norm(f['container'])==wanted))]
    local=[f for f in hits if f['container']==base['container']]
    if local:hits=local
    if len(hits)!=1:raise ValueError('Image event reference must resolve exactly: '+reference)
    return hits[0]['id']

def main():
    handle=lock('media_plan.lock')
    parser=argparse.ArgumentParser();parser.add_argument('--songs',nargs='*');args=parser.parse_args()
    selection=read_json(INVENTORY/'selected_manifest.json')['selected']
    probes=read_json(INVENTORY/'media_index.json')['records']
    files={f['id']:f for f in read_json(INVENTORY/'discovery.json')['files']}
    mapping=read_json(ROOT/'channel_plan.json')['song_mapping'];records=[];errors=[]
    repair_path=ROOT/'media_scene_repairs.json'
    scene_repairs={(r['song_id'],norm(r['reference'])):r for r in read_json(repair_path)['repairs']} if repair_path.exists() else {}
    if args.songs and (ROOT/'media_plan.json').exists():
        before=read_json(ROOT/'media_plan.json')
        records=[r for r in before['records'] if r['song_id'] not in args.songs]
        errors=[e for e in before['errors'] if e['song_id'] not in args.songs]
    reader=Reader()
    for s in selection:
        if args.songs and s['id'] not in args.songs:continue
        try:
            video=next(v for v in s['video_candidates'] if v['id']==s['selected_video_id'])
            anchor=video.get('chart_file') or s['variants'][0]['file_id']
            metadata=next((v['metadata'] for v in s['variants'] if v['file_id']==anchor),s['metadata'])
            clock=Clock(metadata);events=[]
            # Commas are legal in movie filenames; only a new numeric beat
            # starts another BGCHANGES event. The discovery list is descriptive.
            bga=[];syntax_repairs=[];text=metadata.get('BGCHANGES','')
            cleaned=re.sub(r'(?m)^\[\d\d:\d\d:\d\d\]\s*<[^>]+>\s*','',text)
            if cleaned!=text:syntax_repairs.append('Removed chat-log line prefix from malformed BGCHANGES; source file unchanged')
            if '#KEYSOUNDS:' in cleaned:
                cleaned=cleaned.split('#KEYSOUNDS:',1)[0].rstrip()
                syntax_repairs.append('Separated dangling KEYSOUNDS tag from malformed BGCHANGES; source file unchanged')
            for raw in re.split(r',\s*(?=[+-]?(?:\d+(?:\.\d*)?|\.\d+)\s*=)',cleaned):
                fields=re.split(r'(?<!\\)=',raw.strip().rstrip(','))
                if len(fields)>=2:bga.append({'raw':raw.strip().rstrip(','),'beat':fields[0],'file':fields[1]})
            for e in bga:
                fields=re.split(r'(?<!\\)=',e['raw']);reference=unescape(e['file']).replace('\\','/')
                candidates=[v for v in s['video_candidates'] if norm(v.get('reference',''))==norm(reference)]
                vid=next((v['id'] for v in candidates if v['id']==s['selected_video_id']),candidates[0]['id'] if candidates else None)
                image=None;color=None;freeze_previous=False;movie_repair=None
                if not vid and PurePosixPath(reference).suffix.casefold() in {'.avi','.mpg','.mpeg','.mp4','.wmv','.mkv','.m2v','.webm'}:
                    try:vid=image_reference(reference,anchor,files,{PurePosixPath(reference).suffix.casefold()})
                    except ValueError:pass
                if not vid and (s['id'],norm(reference)) in scene_repairs:
                    movie_repair=scene_repairs[s['id'],norm(reference)]
                    assert digest(movie_repair['evidence'])==movie_repair['evidence_sha256'],'BGA reconstruction evidence changed'
                    vid=movie_repair['source_video_id']
                    assert vid==s['selected_video_id'] and files[vid]['pack']==s['pack'],'BGA reconstruction must use selected same-pack movie'
                    assert probes[vid]['sha256']==movie_repair['source_video_sha256'],'BGA reconstruction source changed'
                    evidence=read_json(movie_repair['evidence'])
                    assert evidence['all_eight_authored_stills_match_supplied_full_movie'] and len(evidence['stills'])==8
                    assert evidence['source_end_seconds']<=probes[vid]['duration'],'BGA reconstruction exceeds supplied movie'
                    e['missing_movie_reconstruction']={**movie_repair,'inference':evidence['inference'],'method':evidence['method']}
                if not vid:
                    if reference.casefold()=='-nosongbg-':
                        reference=unescape(metadata.get('BACKGROUND',''))
                    if reference.casefold() in ('_black.jpg','_white.jpg'):
                        # These explicit color-scene references are absent from
                        # the supplied pack; render the named solid color and
                        # retain that repair instead of fabricating a source JPG.
                        color='white' if 'white' in reference.casefold() else 'black'
                        e['missing_still_repair']={'missing':reference,'replacement':'solid '+color,
                            'reason':'explicit missing solid-color scene; no source asset invented'}
                    elif PurePosixPath(reference).suffix.casefold() in {'.png','.jpg','.jpeg','.bmp','.webp','.gif'}:
                        try:image=image_reference(reference,anchor,files)
                        except ValueError:
                            # Stale ending-still names occur in renamed packs.
                            # Use only this song's declared own background and
                            # retain the explicit repair in the render receipt.
                            original_reference=reference
                            reference=unescape(metadata.get('BACKGROUND',''))
                            try:image=image_reference(reference,anchor,files)
                            except ValueError:
                                previous=next((q for q in reversed(events) if q['video_id']),None)
                                if not previous:raise
                                vid=previous['video_id'];freeze_previous=True
                                reference='freeze previous song BGA at missing still cue'
                            e['missing_still_repair']={'missing':original_reference,'replacement':reference,
                                'reason':'missing referenced still; use same song declared BACKGROUND'}
                        if image and files[image]['extension']=='.gif':
                            with Image.open(io.BytesIO(reader.read(files[image]))) as gif:
                                frames=gif.n_frames
                            e['gif_frame_count']=frames
                            if frames>1:vid=image;image=None
                    elif re.search(r'(?:^|/)(?:black|blank|white)\.(?:avi|mpg|mp4)$',reference,re.I):
                        color='white' if PurePosixPath(reference).stem.casefold()=='white' else 'black'
                    elif not reference:color='black'
                    else:raise ValueError('BGA event needs explicit compositing: '+e['raw'])
                rate=float(fields[2]) if len(fields)>2 and fields[2] else 1.
                if freeze_previous:rate=0.
                if rate<0:raise ValueError('Reverse BGA playback requires explicit render')
                effect=fields[6] if len(fields)>6 else ''
                if effect=='NoLoop' and len(fields)>5 and fields[5].strip()=='0':
                    e['effect_alias_repair']={'source':'NoLoop','target':'StretchNoLoop','reason':'Authored loop flag is explicitly zero; preserve non-repeating playback'}
                    effect='StretchNoLoop'
                if effect not in ('','StretchNormal','StretchNoLoop','StretchRewind','Centered'):
                    raise ValueError('Unsupported BGA effect: '+effect)
                if len(fields)>7 and fields[7]:raise ValueError('Two-layer BGA requires explicit compositing')
                transition=fields[8] if len(fields)>8 else ('CrossFade' if len(fields)>3 and fields[3]=='1' else '')
                if transition not in TRANSITIONS:raise ValueError('Unsupported transition: '+transition)
                if len(fields)>=11 and all(v.strip().casefold() in ('#000000','#000000ff') for v in fields[9:11]) and not any(fields[11:]):
                    e['explicit_black_tint']={'source_colors':fields[9:11],'original_video_id':vid,'original_image_id':image,'reason':'Both authored color endpoints are opaque black; render opaque black scene'}
                    vid=None;image=None;color='black';fields[9:11]=['1^1^1^1','1^1^1^1']
                if any(v and v not in ('1^1^1^1','1.000000^1.000000^1.000000^1.000000') for v in fields[9:]):
                    raise ValueError('BGA tint needs explicit color conversion: '+e['raw'])
                events.append({'beat':e['beat'],'seconds':clock.seconds(e['beat']),
                    'video_id':vid,'image_id':image,'color':color,'rate':rate,
                    'loop':(len(fields)<6 or fields[5].strip()!='0') and effect!='StretchNoLoop',
                    'rewind':False if freeze_previous else (len(fields)>4 and fields[4].strip()=='1') or effect=='StretchRewind',
                    'transition':transition,'transition_seconds':TRANSITIONS[transition],
                    'effect':effect,'raw':e['raw'],
                    **({'effect_alias_repair':e['effect_alias_repair']} if 'effect_alias_repair' in e else {}),
                    **({'explicit_black_tint':e['explicit_black_tint']} if 'explicit_black_tint' in e else {}),'missing_still_repair':e.get('missing_still_repair'),
                    'missing_movie_reconstruction':e.get('missing_movie_reconstruction'),
                    'gif_frame_count':e.get('gif_frame_count')})
            if not events:
                automatic=video.get('beat') in (None,'automatic') or video.get('evidence') in ('unreferenced_song_movie','BACKGROUND','MOVIE')
                events=[{'beat':video.get('beat'),'seconds':0. if automatic else clock.seconds(video['beat']),
                    'video_id':s['selected_video_id'],'image_id':None,'color':None,'rate':1.,'loop':False,'rewind':True,
                    'transition':'','transition_seconds':0.,'raw':video.get('evidence')}]
            events.sort(key=lambda e:e['seconds'])
            playback={}
            for i,e in enumerate(events):
                key=e['video_id'];offset=0. if e['rewind'] else playback.get(key,0.)
                if e.get('missing_movie_reconstruction'):
                    offset=e['missing_movie_reconstruction']['source_start_seconds']
                e['source_start_seconds']=offset
                if key and i+1<len(events):playback[key]=offset+(events[i+1]['seconds']-e['seconds'])*e['rate']
                e['movie_origin_seconds']=e['seconds']-offset/e['rate'] if e['rate'] else e['seconds']
                e['native_frame_start']=round((e['seconds']+DECODER_DELAY+VIDEO_ADVANCE)*FPS)
            assert any(e['video_id'] for e in events),'No video retained in BGA timeline'
            duration=probes[s['selected_audio_id']]['duration']
            start=max(0,min(float(metadata.get('SAMPLESTART') or min(30,duration*.3)),max(0,duration-10)))
            result={'song_id':s['id'],'title':s['title'],**mapping[s['id']],
                'audio_id':s['selected_audio_id'],'audio_source_seconds':duration,'events':events,
                'preview_seconds':start,'preview_duration':10,'preview_source':'fresh synchronized full song, no pack previews',
                'native_mp3_decoder_latency_seconds':DECODER_DELAY,'native_video_selector_advance_seconds':VIDEO_ADVANCE,
                'cue_source_chart_file_id':anchor,'source_offset':metadata.get('OFFSET','0'),
                'clock_reference':'StepMania song timing, movie pauses while out of focus',
                'mp3_input_format':probes[s['selected_audio_id']].get('forced_input_format'),
                'source_bga_syntax_repairs':syntax_repairs}
            out=ROOT/'media_plans'/(s['id']+'.json');write_json(out,result)
            records.append({'song_id':s['id'],'path':str(out),'events':len(events)})
        except Exception as ex:
            errors.append({'song_id':s['id'],'title':s['title'],'error':repr(ex)})
            print('MEDIA_REVIEW',s['title'],repr(ex),flush=True)
    reader.close()
    write_json(ROOT/'media_plan.json',{'complete':not errors and len(records)==EXPECTED_SONGS,'records':records,'errors':errors,
        'native_decoder_latency_reference':str(ROOT.parent/'djmax_v3/test_libmad.c'),
        'timing_references':['https://raw.githubusercontent.com/stepmania/stepmania/5_1-new/src/TimingData.cpp',
            'https://raw.githubusercontent.com/stepmania/stepmania/5_1-new/src/NotesLoaderSM.cpp'],
        'transition_references':['https://raw.githubusercontent.com/stepmania/stepmania/5_1-new/BackgroundTransitions/CrossFade.xml',
            'https://raw.githubusercontent.com/stepmania/stepmania/5_1-new/BackgroundTransitions/CrossFade_Fastest.xml']})
    print('MEDIA_PLAN',len(records),'READY',len(errors),'REVIEW',flush=True)

if __name__=='__main__':main()
