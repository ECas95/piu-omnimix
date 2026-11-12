"""PRO 2 real BGAs (user 2026-10-26): the pack now ships one rendered <song>_BGA.mp4 per PRO 2 song (same length as
the song audio, #BGCHANGES at 0.000). Every PRO 2 song with one uses it from second 0.
Songs without one keep a song-specific official movie (Infinity / PRIME); anything else -> PRIME generic 010 / 011."""
from pathlib import Path
import json,shutil,re
R=Path(__file__).resolve().parent;PRO2=Path(r'C:\DATA\PJD\DATA INF PRO PRO2\02.PRO2')
GEN=[r'E:\Pump It Up Data\PIU\rise_channel\into_remix_bga_v30\sources\010.m2v',r'E:\Pump It Up Data\PIU\rise_channel\into_remix_bga_v30\sources\011.m2v']
KEEP=('Infinity image movie','Infinity BGA of the base version','PRIME movie of','PRIME generic')
def charts(p):   # everything except the background tags must be unchanged (charts, timing)
    t=p.read_text(encoding='utf-8-sig',errors='replace').replace('\r','')
    return re.sub(r'\s+','',re.sub(r'#(BGCHANGES2?|FGCHANGES):.*?;','',t,flags=re.S))
S=json.loads((R/'selection.json').read_text(encoding='utf8'));done=[];g=0;keep=[]
for s in S['records']:
    if s['channel']!='PRO2':continue
    folder=PRO2/s['source_folder'];mp4=sorted(folder.glob('*_BGA.mp4')) if folder.is_dir() else []
    if mp4:
        for ssc in folder.glob('*.ssc'):
            bak=ssc.with_name(ssc.name+'.bak')
            if bak.exists():assert charts(ssc)==charts(bak),ssc
        seg=[dict(beat='0',seconds=0.,file=str(mp4[0]),rate=1.)];policy='PRO 2 real BGA '+mp4[0].name
    elif s['video_policy'].startswith(KEEP):keep.append((s['game_song_id'],s['title'],s['video_policy']));continue
    else:seg=[dict(beat='0',seconds=0.,file=GEN[g%2],rate=1.)];policy='PRIME generic BGA '+Path(GEN[g%2]).stem+' (no PRO 2 BGA in the pack)';g+=1
    if s['video_segments']==seg:continue
    s['video_segments']=seg;s['video_policy']=policy
    shutil.rmtree(R/'media/D'/s['game_song_id'],ignore_errors=True);(R/'media_results'/(s['game_song_id']+'.json')).unlink(missing_ok=True)
    for q in ('HD','SD'):(R/'media/USER_INTERFACE/SELECT/EYE_SMALL'/q/(s['game_song_id']+'.G')).unlink(missing_ok=True)
    done.append(s['game_song_id']);print(s['game_song_id'],s['title'],'<-',policy)
for k in keep:print('KEPT',*k)
(R/'selection.json').write_text(json.dumps(S,ensure_ascii=False,indent=1),encoding='utf8')
(R/'redo_ids.txt').write_text(' '.join(done));print('APPLIED',len(done),'kept',len(keep))
