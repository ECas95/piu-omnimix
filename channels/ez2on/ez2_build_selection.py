"""EZ2ON REBOOT : R channel (id 0x48, version 0x30) records -> D:\PIU_INFINITY\channels\selection.json (same schema as SSS).
A song enters only with: chart offset CONFIRMADO (sync_final.json), BGA start verified (same length as Song.mp3, or
located in the gameplay video: bga_video_sync.json), Cover.png, and its generated charts (runs/<folder>/song.json).
Audio: Song.mp3 (start padded with silence when the first note would fall before the audio; the chart offset and
the BGA start include that padding). Banner / preview still: Cover.png (1920x1080). IDs AA000001+ frozen in gid_map.json."""
from pathlib import Path
import json,hashlib,subprocess,sys
H=Path(__file__).resolve().parent;SEL=Path(r'D:\PIU_INFINITY\channels\selection.json');O=Path(r'D:\eeez2abackup\EZ2ON_ORGANIZADO')
sys.path.insert(0,str(H));import measure_sync as M,leadin as L
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
TITLE_FIX={'個人的なメモ (KENPO SAITO)':'Kojinteki na Memo (KENPO SAITO)','sweet★star':'sweet star',   # selector font is Latin only:
           '고백 (Go Back)':'Go Back','Hidden (秘伝)':'Hidden','Kamui (神威)':'Kamui','별바라기 (Starseeker)':'Starseeker',   # the song's own Latin title
           '별처럼 (Stella)':'Stella','星になる (We Become Stars)':'We Become Stars','E 2 O':'E2O'}
ARTIST_FIX={'SATO (SANODG ▶◀ KATO [noisycroak])':'SATO (SANODG x KATO [noisycroak])'}

def main():
    sync=json.loads((H/'sync_final.json').read_text(encoding='utf8'))
    bga={k:v for k,v in json.loads((H/'bga_sync.json').read_text(encoding='utf8')).items() if v['rule']=='same length'}
    if (H/'bga_video_sync.json').exists():bga.update({k:v for k,v in json.loads((H/'bga_video_sync.json').read_text(encoding='utf8')).items() if v['status']=='OK'})
    gmap=json.loads((H/'gid_map.json').read_text()) if (H/'gid_map.json').exists() else {}
    nxt=max([int(g,16) for g in gmap.values()]+[0xAA000000])+1;recs=[];skipped={}
    for k in sorted(sync,key=str.lower):
        v=sync[k]
        if v['status'] not in ('CONFIRMADO','CONFIRMADO_VIDEO'):continue
        if k not in bga:skipped[k]='BGA start not verified';continue
        run=H/'runs'/k/'song.json'
        res=json.loads(run.read_text()) if run.exists() else {'charts':[]}
        if len(res['charts'])<2:skipped[k]='charts missing';continue
        d=O/k;cover=d/'Cover.png';bfile=next(d/x for x in ('BGA.mp4','BGA.webm') if (d/x).exists())
        # lead-in (user 2026-10-30): first note at >= 2.5 s; audio, charts and BGA move together (leadin.py)
        first=min(L.first_ms(Path(c['nx']).read_bytes()) for c in res['charts']);extra=max(0,round(L.LEAD_MS-first))
        pad=v['pad_ms']+extra;audio=d/'Song.mp3'
        if pad:
            audio=H/'audio'/f'{k}_{pad}.flac';audio.parent.mkdir(exist_ok=True)
            if not audio.exists():subprocess.run([M.FF,'-v','error','-y','-i',str(d/'Song.mp3'),'-af',f'adelay={pad}:all=1','-c:a','flac',str(audio)],check=True)
        j=json.loads((Path(r'D:\eeez2abackup\ez2on_charts')/v['chart']/'song.json').read_text(encoding='utf8'))
        if k not in gmap:gmap[k]=f'{nxt:08X}';nxt+=1
        fmt=lambda x:f'{x:.2f}'.rstrip('0').rstrip('.')
        bpm=fmt(j['bpm_min']) if j['bpm_min']==j['bpm_max'] else fmt(j['bpm_min'])+'-'+fmt(j['bpm_max'])
        dur=float(subprocess.run([M.FF.replace('ffmpeg.exe','ffprobe.exe'),'-v','error','-show_entries','format=duration','-of','csv=p=0',str(audio)],capture_output=True,text=True).stdout)
        charts=[];names=set()
        for c in sorted(res['charts'],key=lambda c:(c['mode'],c['level'],c['tier'])):
            name=('S' if c['mode']=='Single' else 'D')+f"{c['level']:02d}";n=0
            while name+('' if not n else chr(96+n)) in names:n+=1
            name+='' if not n else chr(96+n);names.add(name)
            assert sha(c['nx'])==c['sha256'];nx=c['nx']
            if extra:
                raw=L.shift(Path(c['nx']).read_bytes(),extra);nx=H/'runs'/k/'lead'/f"{extra}_{Path(c['nx']).name}";nx.parent.mkdir(exist_ok=True);nx.write_bytes(raw);nx=str(nx)
            charts.append(dict(name=name,mode='pump-single' if c['mode']=='Single' else 'pump-double',level=c['level'],nx=nx,sha256=sha(nx),generated=True,
                               special=dict(source_chart=c['source_chart'],reduction=c['reduction'],omitted_conflicts=c['omitted_conflicts'])))
        start=round(bga[k]['start_s']+pad/1000,3)   # pad includes the lead-in
        recs.append(dict(game_song_id=gmap[k],channel='EZ2ON',channel_id=0x48,channel_name='EZ2ON REBOOT : R',kind='ARCADE',source_group='EZ2ON',source_folder=k,
            source='ez2on',title=TITLE_FIX.get(j['title'],j['title']),artist=ARTIST_FIX.get(j['artist'],j['artist']),bpm=bpm,audio=str(audio),sample_start=round(dur*.35,3),sample_length=12.,
            video_segments=[dict(beat='0',seconds=start,file=str(bfile),rate=1.)],video_policy=f"EZ2ON own BGA from {start:.3f}s ({bga[k]['rule']}); chart offset {v['lag_ms']}+{v['pad_ms']} ms, lead-in {extra} ms",
            preview_video=None,still=str(cover),banner=None,charts=charts,skipped_charts=[]))
    (H/'gid_map.json').write_text(json.dumps(gmap,indent=1));(H/'skipped.json').write_text(json.dumps(skipped,indent=1))
    S=json.loads(SEL.read_text(encoding='utf8'));S['records']=[r for r in S['records'] if r['channel']!='EZ2ON']+recs;S['songs']=len(S['records'])
    SEL.write_text(json.dumps(S,ensure_ascii=False,indent=1),encoding='utf8')
    print('EZ2ON_SELECTION',len(recs),'songs',sum(len(r['charts']) for r in recs),'charts; skipped',len(skipped))
if __name__=='__main__':main()
