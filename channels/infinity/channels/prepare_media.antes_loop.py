"""PRIME media for the PRO 1 / PRO 2 / INFINITY songs (same formats and sync policy as the RISE channel).

Per song /D/<GID>/: A/.A full audio (mp3 48k), P/A/.A 10 s preview, V/HD|SD/.V movie (mpeg2, 30 fps,
native decoder delay + selector advance), P/V/HD|SD/.V 10 s preview movie, P/.G preview still,
USER_INTERFACE/SELECT/EYE_SMALL/HD|SD/<GID>.G. The movie follows the original BGCHANGES timeline
(each clip from its own beat, looped until the next change); songs whose clips are absent from the
game data show their background still, exactly as Infinity does. Resumable: media_results/<GID>.json.
"""
from pathlib import Path
import sys,json,math,struct,subprocess,hashlib,os,re,time,traceback,threading
from concurrent.futures import ThreadPoolExecutor,as_completed
from PIL import Image
R=Path(__file__).resolve().parent;E=Path(r'E:\Pump It Up Data\PIU')
sys.dont_write_bytecode=True
sys.path[:0]=[str(E),str(E/'rise_channel')]
from g_texture import banner_from_preview
import rise_nx as NX
FPS=30;DECODER_DELAY=2257/48000;VIDEO_ADVANCE=1/FPS
MPEG=['-an','-c:v','mpeg2video','-pix_fmt','yuv420p','-r','30','-g','15','-bf','2','-flags','+cgop','-sc_threshold','1000000000','-threads','2','-aspect','16:9','-f','mpeg2video']
RATES={'EZ2ON':('3500k','1000k'),'IIDX':('2600k','600k'),'IMAS':('2600k','600k'),'MAINSEL':('2600k','600k'),'LL':('2600k','600k')}   # IIDX: PRIME's own HD rate (1356 songs)
HD_ONLY={'IIDX','IMAS','MAINSEL','LL'}
OUT=R/'media';LOGS=R/'logs/media';lock=threading.Lock()
EMBLEM={'PRO1':'08 Pump It Up Pro 1.png','PRO2':'09 Pump It Up Pro 2.png','INF':'10 Pump It Up Infinity.png'}
def still_of(s):
    """Song art; else the channel emblem; else (old versions without title art, v375) a plain title card."""
    if s['still'] or s['banner']:return s['still'] or s['banner']
    if s['channel'] in EMBLEM:return str(R/'ui_src/Graphics/GroupFolders'/EMBLEM[s['channel']])
    from PIL import ImageDraw,ImageFont
    p=R/'media_src_cards'/(s['game_song_id']+'.png');p.parent.mkdir(exist_ok=True)
    im=Image.new('RGB',(1280,720),(16,18,28));d=ImageDraw.Draw(im);f=ImageFont.truetype('arialbd.ttf',72);g=ImageFont.truetype('arial.ttf',40)
    d.text((640,330),s['title'],font=f,fill=(240,240,240),anchor='mm');d.text((640,420),s.get('artist') or '',font=g,fill=(170,170,190),anchor='mm');im.save(p);return str(p)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def ff(args,log):
    log.parent.mkdir(parents=True,exist_ok=True)
    with log.open('wb') as f:p=subprocess.run(['ffmpeg','-nostdin','-v','warning','-y',*args],stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    if p.returncode:raise RuntimeError(log.read_text(errors='replace')[-1200:])

def duration(p):
    return float(json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','json',str(p)],creationflags=subprocess.CREATE_NO_WINDOW))['format']['duration'])

def frames_of(p):
    s=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_streams','-of','json',str(p)],creationflags=subprocess.CREATE_NO_WINDOW))['streams'][0]
    return s['codec_name'],int(s['width']),int(s['height']),int(s['nb_read_frames'])

def movie_inputs(s,seconds):
    """ffmpeg inputs + filter graph producing [v]: 1280x720/30fps, audio-clock aligned from t=0, `seconds` long."""
    segs=s['video_segments']
    if not segs:
        still=still_of(s)
        return ['-loop','1','-framerate','30','-t',f'{seconds:.6f}','-i',still],f'[0:v]scale=1280:720,setsar=1,fps=30,format=yuv420p,trim=duration={seconds:.6f}[v]','still'
    args=['-f','lavfi','-t',f'{seconds:.6f}','-i','color=c=black:s=1280x720:r=30'];graph=[];last='[0:v]'
    crop='crop=iw:iw*9/16,' if s.get('crop_16_9') else ''   # user 2026-11: 4:3 movies cut top and bottom to 16:9
    for i,g in enumerate(segs,1):
        start=max(0.,g['seconds']);end=segs[i]['seconds'] if i<len(segs) else seconds
        if end<=start:continue
        skip=max(0.,-g['seconds'])   # clip that started before the audio: keep its running position
        # PRO 2 _BGA.mp4 renders change colour metadata mid-stream: a filter-graph reinit there loops forever
        args+=['-reinit_filter','0','-stream_loop','-1','-t',f"{(end-start+skip)*(g['rate'] or 1)+2:.3f}",'-i',g['file']]
        graph.append(f"[{i}:v]setpts=(PTS-STARTPTS)/{g['rate'] or 1},fps=30,{crop}scale=1280:720,setsar=1,format=yuv420p,trim=start={skip:.6f}:duration={end-start+skip:.6f},setpts=PTS-STARTPTS+{start:.6f}/TB[c{i}]")
        graph.append(f"{last}[c{i}]overlay=eof_action=pass:enable='between(t,{start:.6f},{end:.6f})'[o{i}]");last=f'[o{i}]'
    graph.append(f'{last}format=yuv420p[v]')
    return args,';'.join(graph),'timeline'

def run_song(s):
    gid=s['game_song_id'];dest=OUT/'D'/gid;result=R/'media_results'/(gid+'.json')
    if result.exists():return json.loads(result.read_text(encoding='utf8'))
    log=LOGS/gid;records=[]
    audio_seconds=duration(s['audio'])
    last=max((NX.last_note_seconds(NX.parse(Path(c["nx"]).read_bytes())) for c in s["charts"]),default=0.)   # media-only records (v378) have no charts
    seconds=max(audio_seconds,last+1);frames=math.ceil((seconds+DECODER_DELAY+VIDEO_ADVANCE)*FPS);start_frames=round((DECODER_DELAY+VIDEO_ADVANCE)*FPS)
    def done(path,**meta):
        records.append(dict(file=str(path),bytes=path.stat().st_size,sha256=sha(path),**meta))
    # audio
    a=dest/'A/.A';a.parent.mkdir(parents=True,exist_ok=True)
    ff(['-i',s['audio'],'-af',f'apad,atrim=duration={seconds:.9f}','-vn','-c:a','libmp3lame','-ar','48000','-ac','2','-b:a','192k','-f','mp3',str(a)],log/'audio.log');done(a)
    pa=dest/'P/A/.A';pa.parent.mkdir(parents=True,exist_ok=True)
    start=min(max(0.,s['sample_start']),max(0.,audio_seconds-10))
    src=['-i',s['preview_audio']] if s.get('preview_audio') else ['-ss',f'{start:.3f}','-i',s['audio']]   # v375: Fiesta 2 songs keep their own preview
    ff([*src,'-t','10','-af','asetpts=PTS-STARTPTS,afade=t=in:d=0.15,afade=t=out:st=9.5:d=0.5','-vn','-c:a','libmp3lame','-ar','48000','-ac','2','-b:a','192k','-f','mp3',str(pa)],log/'preview_audio.log');done(pa,preview=True)
    # movie (HD from the original timeline, SD from HD)
    hdr,sdr=RATES.get(s['channel'],('6M','3M'))   # v379: EZ2ON nearer PRIME's own rates (2.6 / 0.6 Mbps) so it fits the game partition
    ins,graph,kind=movie_inputs(s,seconds)
    hd=dest/'V/HD/.V';hd.parent.mkdir(parents=True,exist_ok=True)
    graph+=f';[v]tpad=start={start_frames}:start_mode=add:color=black:stop_mode=add:color=black:stop_duration={frames/30:.6f},trim=end_frame={frames},setpts=PTS-STARTPTS[out]'
    ff(['-threads','2',*ins,'-filter_complex',graph,'-map','[out]','-frames:v',str(frames),'-b:v',hdr,'-maxrate',hdr,'-bufsize','4M',*MPEG,str(hd)],log/'hd.log')
    assert frames_of(hd)==('mpeg2video',1280,720,frames),frames_of(hd);done(hd,source=kind,frames=frames)
    if s['channel'] not in HD_ONLY:   # IIDX ships HD only: its SD movies would never be packed
     sd=dest/'V/SD/.V';sd.parent.mkdir(parents=True,exist_ok=True)
     ff(['-threads','2','-i',str(hd),'-vf','fps=30,scale=640:480,setsar=1,format=yuv420p','-frames:v',str(frames),'-b:v',sdr,'-maxrate',sdr,'-bufsize','4M',*MPEG,str(sd)],log/'sd.log')
     assert frames_of(sd)[1:]==(640,480,frames);done(sd,frames=frames)
    # preview movies: Infinity's own preview clip, else the movie at the sample start
    for q,w,h in (('HD',464,264),('SD',312,176))[:1 if s['channel'] in HD_ONLY else 2]:
        pv=dest/'P/V'/q/'.V';pv.parent.mkdir(parents=True,exist_ok=True)
        src=['-i',s['preview_video']] if s['preview_video'] else ['-ss',f'{start+start_frames/FPS:.3f}','-i',str(hd)]
        ff(['-threads','2',*src,'-vf',f'fps=30,scale={w}:{h},setsar=1,format=yuv420p,tpad=stop_mode=clone:stop_duration=10,trim=end_frame=300,setpts=PTS-STARTPTS','-frames:v','300','-b:v','3M','-maxrate','3M','-bufsize','4M',*MPEG,str(pv)],log/f'preview_{q}.log')
        assert frames_of(pv)[1:]==(w,h,300);done(pv,preview=True)
    # preview still + selector thumbnail
    with Image.open(still_of(s)) as im:im=im.convert('RGB').resize((1280,720),Image.Resampling.LANCZOS)
    raw=struct.pack('<IHH',0x18,1280,720)+im.tobytes()
    for path,data in [(dest/'P/.G',raw)]+[(OUT/'USER_INTERFACE/SELECT/EYE_SMALL'/q/(gid+'.G'),banner_from_preview(raw,q)) for q in ('HD','SD')]:
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);done(path)
    im.thumbnail((640,360));im.save(dest/'banner_preview.jpg')
    r=dict(complete=True,game_song_id=gid,title=s['title'],seconds=seconds,audio_seconds=audio_seconds,movie=kind,frames=frames,native_video_start_frame=start_frames,records=records)
    result.parent.mkdir(exist_ok=True);tmp=result.with_suffix('.tmp');tmp.write_text(json.dumps(r,ensure_ascii=False,indent=1),encoding='utf8');os.replace(tmp,result);return r

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--limit',type=int);p.add_argument('--workers',type=int,default=4);p.add_argument('--songs',nargs='*');a=p.parse_args()
    sel=json.loads((R/'selection.json').read_text(encoding='utf8'))['records']
    if a.songs:sel=[s for s in sel if s['game_song_id'] in a.songs]
    if a.limit:sel=sel[:a.limit]
    errors=[];done=0;t=time.time()
    with ThreadPoolExecutor(a.workers) as ex:
        fut={ex.submit(run_song,s):s for s in sel}
        for f in as_completed(fut):
            s=fut[f]
            try:f.result();done+=1;print('MEDIA',done,len(sel),s['game_song_id'],s['title'],'%.0fs'%(time.time()-t),flush=True)
            except Exception as e:errors.append(dict(gid=s['game_song_id'],title=s['title'],error=repr(e)[:600]));print('MEDIA_ERROR',s['game_song_id'],s['title'],repr(e)[:300],flush=True)
    (R/'media_state.json').write_text(json.dumps(dict(finished=True,done=done,total=len(sel),errors=errors),ensure_ascii=False,indent=1),encoding='utf8')
    print('MEDIA_FINISHED',done,'errors',len(errors),flush=True)

if __name__=='__main__':main()
