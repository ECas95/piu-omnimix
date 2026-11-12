"""New synchronized PRIME media; full timeline crop audit, no pack previews."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse, hashlib, math, os, re, shutil, struct, subprocess, threading
import numpy as np
from PIL import Image, ImageOps
from common import *
from plan_media import FPS, DECODER_DELAY, VIDEO_ADVANCE
from source_store import SourceStore

_ctx=None;_crop_locks={};_crop_guard=threading.Lock();_store=None;_disk_commit=threading.Lock()

def context():
    global _ctx
    if _ctx is None:
        d=read_json(INVENTORY/'discovery.json');selection=read_json(ROOT/'integration_selection.json')
        _ctx=({f['id']:f for f in d['files']},selection['images'])
    return _ctx

def input_path(fid):
    return _store.path(fid)

def run(args,log):
    log.parent.mkdir(parents=True,exist_ok=True)
    with log.open('wb') as out:
        result=subprocess.run(args,stdout=out,stderr=subprocess.STDOUT,cwd=r'C:\Windows',creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:raise RuntimeError(str(log)+': '+log.read_text(errors='replace')[-1500:])

def crop(fid):
    with _crop_guard:guard=_crop_locks.setdefault(fid,threading.Lock())
    with guard:
        receipt=ROOT/'crop_audits'/(fid+'.json')
        if receipt.exists():return read_json(receipt)
        src=input_path(fid)
        p=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_streams','-of','json',str(src)]))['streams'][0]
        w,h=int(p['width']),int(p['height']);scaled_h=round(h*640/w/2)*2
        log=ROOT/'logs/crop'/(fid+'.log')
        run(['ffmpeg','-nostdin','-v','info','-threads','2','-i',str(src),'-an','-vf','fps=2,scale=640:-2,setsar=1,cropdetect=limit=24:round=2:reset=1','-f','null','-'],log)
        values=[]
        for cw,ch,x,y in re.findall(r'crop=(\d+):(\d+):(\d+):(\d+)',log.read_text(errors='replace')):
            cw,ch,x,y=map(int,(cw,ch,x,y))
            if cw>=320 and ch>=scaled_h*.5 and cw+x<=640 and ch+y<=scaled_h:
                values.append((x,640-x-cw,y,scaled_h-y-ch))
        margins=np.quantile(np.array(values),.10,axis=0) if values else np.zeros(4)
        left,right=[max(0,int(v*w/640)//2*2) for v in margins[:2]]
        top,bottom=[max(0,int(v*h/scaled_h)//2*2) for v in margins[2:]]
        cw=(w-left-right)//2*2;ch=(h-top-bottom)//2*2
        assert cw>=w*.5 and ch>=h*.5
        result={'file_id':fid,'source_sha256':digest(src),'source_size':[w,h],'crop':[cw,ch,left,top],
                'full_timeline_decoded':True,'stable_border_observations':len(values),
                'policy':'10th percentile per black margin over full timeline; then scale active image to fill 16:9',
                'black_bars_removed':any(v>0 for v in (left,right,top,bottom))}
        write_json(receipt,result);return result

def static_crop(fid):
    """Trim only contiguous almost entirely black outer rows/columns of a still."""
    src=input_path(fid);receipt=CACHE/'static_crop_audits'/(fid+'.json')
    overrides=CACHE/'research/static_crop_visual_review/overrides.json'
    if overrides.exists():
        override=read_json(overrides).get(fid)
        if override:
            assert digest(src)==override['source_sha256'],'Visual still decision source changed'
            w,h=override['source_size']
            result={'revision':'static-border-2','file_id':fid,'source_sha256':override['source_sha256'],
                'source_size':[w,h],'crop':[w,h,0,0],'black_bars_removed':False,
                'all_source_pixels_inspected':True,'manual_visual_review':override['reason']}
            write_json(receipt,result);return result
    if receipt.exists():
        old=read_json(receipt);assert old['source_sha256']==digest(src)
        if old.get('revision')=='static-border-2':return old
    with Image.open(src) as im:
        assert getattr(im,'n_frames',1)==1,'Animated image requires timeline crop audit'
        pixels=np.asarray(im.convert('RGB'));w,h=im.size
    dark=pixels.max(axis=2)<=8
    def edge_count(flags):
        count=0
        for value in flags:
            if not value:break
            count+=1
        return count
    row_black=dark.mean(axis=1)>=.995;col_black=dark.mean(axis=0)>=.995
    top,bottom=edge_count(row_black),edge_count(row_black[::-1])
    left,right=edge_count(col_black),edge_count(col_black[::-1])
    # A single still cannot distinguish dark artwork from a black border as a
    # temporal crop audit can. Trim only the shared symmetric outer margin.
    top=bottom=min(top,bottom);left=right=min(left,right)
    if top+bottom>h*.5 or left+right>w*.5:top=bottom=left=right=0
    left,right,top,bottom=[n//2*2 for n in (left,right,top,bottom)]
    result={'revision':'static-border-2','file_id':fid,'source_sha256':digest(src),'source_size':[w,h],
        'crop':[w-left-right,h-top-bottom,left,top],'black_bars_removed':any((left,right,top,bottom)),
        'policy':'Shared symmetric contiguous outer margins with >=99.5% pixels <=8; preserve at least half width/height; then fill16:9',
        'all_source_pixels_inspected':True}
    write_json(receipt,result);return result

def encode(dest,args,policy,video_frames=None,size=None):
    dest.parent.mkdir(parents=True,exist_ok=True)
    marker=ROOT/'media_receipts'/(hashlib.sha256(str(dest).encode()).hexdigest()+'.json')
    if marker.exists():
        receipt=read_json(marker)
        assert receipt['policy']==policy,('Media policy changed; inspect before replacing',str(dest))
        assert dest.stat().st_size==receipt['bytes'] and digest(dest)==receipt['sha256'],dest
        return receipt
    scratch=CACHE/'media_encode_cache'/str(os.getpid());scratch.mkdir(parents=True,exist_ok=True)
    # Keep the SSD reserve throughout an encode, including its expected output.
    # Long movies can exceed the remaining SSD budget after a disconnected batch.
    # Spill only transient encode output to E:, retaining all originals/receipts.
    estimated_bytes=int((video_frames/FPS*1_250_000 if video_frames is not None
                         else (10 if policy.get('preview') else policy['seconds'])*40_000)+(32<<20))
    if shutil.disk_usage(scratch).free < (2<<30)+estimated_bytes:
        scratch=ROOT/'encode_overflow_cache'/str(os.getpid());scratch.mkdir(parents=True,exist_ok=True)
        assert shutil.disk_usage(scratch).free > estimated_bytes+(2<<30),'Destination encode cache lacks space'
    partial=scratch/(hashlib.sha256(str(dest).encode()).hexdigest()+'.partial')
    log=ROOT/'logs/media'/(hashlib.sha256(str(dest).encode()).hexdigest()[:16]+'.log')
    run(['ffmpeg','-nostdin','-v','warning','-y',*args,str(partial)],log)
    if video_frames is not None:
        streams=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_streams','-of','json',str(partial)]))['streams']
        v=streams[0];assert v['codec_name']=='mpeg2video' and [v['width'],v['height']]==list(size),v
        assert int(v['nb_read_frames'])==video_frames,(str(dest),v.get('nb_read_frames'),video_frames)
    else:
        run(['ffmpeg','-nostdin','-v','error','-i',str(partial),'-f','null','-'],log.with_suffix('.decode.log'))
    sha=digest(partial);byte_count=partial.stat().st_size
    with _disk_commit:
        incoming=dest.with_name(dest.name+'.partial')
        with partial.open('rb') as src,incoming.open('wb') as out:shutil.copyfileobj(src,out,16<<20)
        assert incoming.stat().st_size==byte_count and digest(incoming)==sha,'Encoded media readback differs'
        os.replace(incoming,dest)
    partial.unlink()
    receipt={'file':str(dest),'bytes':byte_count,'sha256':sha,'policy':policy,
             'full_decode_passed':True,'frames':video_frames,'size':size}
    write_json(marker,receipt);return receipt

MPEG=['-an','-c:v','mpeg2video','-pix_fmt','yuv420p','-r','30','-g','15','-bf','2','-flags','+cgop',
      '-sc_threshold','1000000000','-threads','2','-aspect','16:9','-f','mpeg2video']

def run_song(plan_path):
    with _store.song():return render_song(plan_path)

def render_song(plan_path):
    plan=read_json(plan_path);sid=plan['game_song_id']
    source_path=ROOT/'chart_sources'/(plan['song_id']+'.json')
    if source_path.exists():
        seconds=read_json(source_path)['output_seconds']
    else:
        # A native conversion blocker must not prevent independent media work.
        # Re-audit original clocks and compare the separate signed-source census;
        # never fabricate a chart_sources record or native acceptance receipt.
        from audit_media_duration_dng import audit
        timing_path=ROOT/'media_timing'/(plan['song_id']+'.json')
        previous=read_json(timing_path)
        current=audit(plan['song_id'])
        assert current==previous,'Media duration source census changed'
        assert current['selected_audio_id']==plan['audio_id']
        assert current['chart_acceptance'] is False
        assert digest(input_path(plan['audio_id']))==current['audio_source_sha256']
        seconds=current['output_seconds']
    dest=ROOT/'staging/D'/sid;frames=math.ceil((seconds+DECODER_DELAY+VIDEO_ADVANCE)*FPS)
    full_seconds=frames/FPS;audio=input_path(plan['audio_id']);input_args=(['-f',plan['mp3_input_format']] if plan['mp3_input_format'] else [])+['-i',str(audio)]
    records=[];policy={'revision':'anime-media-2','source_audio_sha256':digest(audio),'seconds':seconds,
                       'original_audio_clock_preserved':True,'preview_from_pack':False}
    for preview in (False,True):
        apath=dest/('P/A/.A' if preview else 'A/.A')
        args=[*input_args]
        if preview:args=['-ss',str(plan['preview_seconds']),*input_args,'-t','10','-af','asetpts=PTS-STARTPTS,afade=t=in:d=0.15,afade=t=out:st=9.5:d=0.5']
        else:args+=['-af',f'apad,atrim=duration={seconds:.9f}']
        args+=['-vn','-c:a','libmp3lame','-ar','48000','-ac','2','-b:a','192k','-f','mp3']
        rec=encode(apath,args,{**policy,'preview':preview,'preview_seconds':plan['preview_seconds'] if preview else None})
        records.append(rec)
    events=plan['events'];segments=[]
    for i,e in enumerate(events):
        begin=max(0,e['native_frame_start']);end=min(frames,events[i+1]['native_frame_start'] if i+1<len(events) else frames)
        if end<=begin:continue
        if not segments and begin>0:segments.append({'start':0,'end':begin,'video_id':None,'color':'black'})
        if e['video_id']:
            input_path(e['video_id']);crop(e['video_id'])
        if e.get('image_id'):
            still_crop=static_crop(e['image_id'])
            if still_crop['black_bars_removed']:e={**e,'static_crop_audit':still_crop}
        song_at=begin/FPS-DECODER_DELAY-VIDEO_ADVANCE
        segments.append({**e,'start':begin,'end':end,'source_start':max(0,e['source_start_seconds']+(song_at-e['seconds'])*e['rate'])})
    assert segments and segments[-1]['end']==frames and any(s.get('video_id') for s in segments),('No complete video BGA timeline',plan['title'])
    for n,s in enumerate(segments):
        s['fade_frames']=min(round(s.get('transition_seconds',0)*FPS),s['end']-s['start']) if n else 0
    args=[];filters=[];labels=[];index=0
    for n,s in enumerate(segments):
        extra=segments[n+1]['fade_frames'] if n+1<len(segments) else 0
        count=s['end']-s['start']+extra;duration=count/FPS;label=f'part{n}';labels.append('['+label+']')
        if not s.get('video_id') and not s.get('image_id'):
            filters.append(f'color=c={s.get("color") or "black"}:s=1280x720:r=30:d={duration:.9f},setsar=1,format=yuv420p[{label}]');continue
        if s.get('image_id'):
            image_path=input_path(s['image_id'])
            args+=(['-ignore_loop','1','-stream_loop','-1','-i',str(image_path)] if image_path.suffix.casefold()=='.gif'
                   else ['-loop','1','-framerate','30','-i',str(image_path)])
            c=(s.get('static_crop_audit') or static_crop(s['image_id']))['crop']
            # A declared1x1WHITE.jpg is a valid authored color scene. Crop it
            # in RGB before subsampled YUV would round its dimensions to zero.
            tiny_format='format=rgba,' if min(c[:2])<2 else ''
            vf=f'[{index}:v]setpts=PTS-STARTPTS,fps=30,{tiny_format}crop={c[0]}:{c[1]}:{c[2]}:{c[3]},scale=1280:720,setsar=1,format=yuv420p,trim=end_frame={count},setpts=PTS-STARTPTS[{label}]'
            filters.append(vf);index+=1;continue
        if s['loop']:
            from finite_media import required_video_loops
            source_seconds=read_json(INVENTORY/'media_index.json')['records'][s['video_id']]['duration']
            repeats=required_video_loops(source_seconds,s['source_start'],duration,s['rate'])
            args+=['-stream_loop',str(repeats)]
        args+=['-threads','2','-i',str(input_path(s['video_id']))]
        c=crop(s['video_id'])['crop'];vf=f'[{index}:v]trim=start={s["source_start"]:.9f},setpts=PTS-STARTPTS'
        if s['rate']==0:vf+=',trim=end_frame=1,loop=loop=-1:size=1:start=0'
        elif s['rate']!=1:vf+=f',setpts=PTS/{s["rate"]:.9f}'
        vf+=f',fps=30,crop={c[0]}:{c[1]}:{c[2]}:{c[3]},scale=1280:720,setsar=1,format=yuv420p,tpad=stop_mode=clone:stop_duration={duration:.9f},trim=end_frame={count},setpts=PTS-STARTPTS[{label}]'
        filters.append(vf);index+=1
    current=labels[0]
    for n in range(1,len(labels)):
        target=f'join{n}';raw_target=target+'_raw';fade=segments[n]['fade_frames']
        if fade:
            filters.append(current+labels[n]+f'xfade=transition=fade:duration={fade/FPS:.9f}:offset={segments[n]["start"]/FPS:.9f}[{raw_target}]')
        else:filters.append(current+labels[n]+f'concat=n=2:v=1:a=0[{raw_target}]')
        # concat emits a microsecond timebase; later xfade requires both links
        # to share the exact frame timebase. Preserve every output frame/time.
        filters.append(f'[{raw_target}]settb=expr=1/{FPS},setpts=N[{target}]')
        current='['+target+']'
    filters.append(current+f'trim=end_frame={frames},format=yuv420p[out]')
    hd=dest/'V/HD/.V'
    vp={**policy,'timeline':segments,'frames':frames,'native_decoder_delay':DECODER_DELAY,'native_video_advance':VIDEO_ADVANCE,'fit':'verified black crop then fill 16:9'}
    records.append(encode(hd,[*args,'-filter_complex_threads','2','-filter_complex',';'.join(filters),'-map','[out]','-frames:v',str(frames),'-b:v','6M','-maxrate','6M','-bufsize','4M',*MPEG],vp,frames,(1280,720)))
    for preview,quality,w,h,rate in [(False,'SD',640,480,'3M'),(True,'HD',464,264,'3M'),(True,'SD',312,176,'3M')]:
        target=dest/(('P/' if preview else '')+'V/'+quality+'/.V');count=300 if preview else frames
        vf=(f'trim=start={plan["preview_seconds"]:.9f}:duration=10,setpts=PTS-STARTPTS,' if preview else '')+f'scale={w}:{h},setsar=1'
        records.append(encode(target,['-threads','2','-i',str(hd),'-vf',vf,'-frames:v',str(count),'-b:v',rate,'-maxrate',rate,'-bufsize','4M',*MPEG],
                              {**vp,'preview':preview,'preview_seconds':plan['preview_seconds'] if preview else None,'quality':quality},count,(w,h)))
    candidates=[]
    for rec in context()[1].get(plan['song_id'],[]):
        try:
            p=input_path(rec['file_id'])
            with Image.open(p) as im:
                candidates.append((rec['tag'] in ('BACKGROUND','JACKET'),im.width*im.height,p))
        except Exception:continue
    image_source=None
    if candidates:
        image_source=max(candidates,key=lambda x:x[:2])[2]
        with Image.open(image_source) as im:img=ImageOps.exif_transpose(im).convert('RGB').resize((1280,720),Image.Resampling.LANCZOS)
    else:
        frame=dest/'banner_frame.png'
        run(['ffmpeg','-nostdin','-v','error','-y','-i',str(hd),'-ss',str(plan['preview_seconds']+1),'-frames:v','1',str(frame)],ROOT/'logs/media'/(sid+'_banner.log'))
        with Image.open(frame) as im:img=im.convert('RGB').resize((1280,720),Image.Resampling.LANCZOS)
        image_source=frame
    banner=dest/'P/.G';banner.write_bytes(struct.pack('<IHH',0x18,1280,720)+img.tobytes())
    img.thumbnail((640,360));img.save(dest/'banner_preview.jpg')
    records.append({'file':str(banner),'bytes':banner.stat().st_size,'sha256':digest(banner),'source':str(image_source),'size':[1280,720],'aspect_ratio':'16:9'})
    result={'complete':True,'song_id':plan['song_id'],'game_song_id':sid,'title':plan['title'],'records':records,
            'preview_seconds':plan['preview_seconds'],'seconds':seconds,'preview_regenerated':True,'source_audio_id':plan['audio_id'],
            'source_file_sha256':policy['source_audio_sha256'],'media_plan_sha256':digest(plan_path)}
    write_json(ROOT/'media_results'/(plan['song_id']+'.json'),result);print('MEDIA_READY',plan['title'],flush=True)
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--songs',nargs='*');p.add_argument('--workers',type=int,default=2);a=p.parse_args()
    global _store
    handle=lock('media_worker.lock');context();_store=SourceStore();plan=read_json(ROOT/'media_plan.json')
    paths=[r['path'] for r in plan['records'] if not a.songs or r['song_id'] in a.songs]
    if not a.songs:assert read_json(ROOT/'source_assembly.json')['complete']
    records=[];errors=[]
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        jobs={pool.submit(run_song,path):path for path in paths}
        for job in as_completed(jobs):
            try:records.append(job.result())
            except Exception as ex:errors.append({'path':jobs[job],'error':repr(ex)});print('MEDIA_REVIEW',jobs[job],repr(ex),flush=True)
            state('media_worker_state.json','encoding',songs=len(records),expected_songs=len(paths),errors=errors,complete=False)
    report={'complete':not errors and len(records)==len(paths) and (bool(a.songs) or len(records)==EXPECTED_SONGS),
            'songs':len(records),'records':records,'errors':errors,'pilot':bool(a.songs),'source_modified':False}
    write_json(ROOT/('pilot_media_manifest.json' if a.songs else 'media_manifest.json'),report)
    state('media_worker_state.json','complete' if report['complete'] else 'review_required',songs=len(records),errors=errors,complete=report['complete'])

if __name__=='__main__':main()
