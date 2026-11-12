"""Last BGA pass (user 2026-10-26): songs still without a movie.
- Infinity shortcuts whose arcade version has an Infinity movie: that movie (as the other shortcuts).
- Every other one: PRIME generic HD movie 010 / 011 (alternating), like full songs and remixes."""
from pathlib import Path
import json,shutil
R=Path(__file__).resolve().parent
BASE={'Girlz Buttz':'Girlz Buttz/GirlzButtz.bik','Moonshard':'Moonshard/Moonshard.bik','Party 4U':'Party 4u (Holy Nite Mix)/Party 4u (Holy Nite Mix).bik'}
GEN=[r'E:\Pump It Up Data\PIU\rise_channel\into_remix_bga_v30\sources\010.m2v',r'E:\Pump It Up Data\PIU\rise_channel\into_remix_bga_v30\sources\011.m2v']
S=json.loads((R/'selection.json').read_text(encoding='utf8'));done=[];g=0
for s in S['records']:
    if s['video_segments']:continue
    base=next((v for k,v in BASE.items() if s['kind']=='SHORT' and s['title'].startswith(k)),None)
    if base:
        f=R/'src/10 Pump It Up Infinity'/base;assert f.exists(),f
        s['video_segments']=[dict(beat='0',seconds=0.,file=str(f),rate=1.)];s['video_policy']='Infinity BGA of the arcade version '+base.split('/')[0]
    else:
        s['video_segments']=[dict(beat='0',seconds=0.,file=GEN[g%2],rate=1.)];s['video_policy']='PRIME generic BGA '+Path(GEN[g%2]).stem+' (user: no movie in any source)';g+=1
    shutil.rmtree(R/'media/D'/s['game_song_id'],ignore_errors=True);(R/'media_results'/(s['game_song_id']+'.json')).unlink(missing_ok=True)
    for q in ('HD','SD'):(R/'media/USER_INTERFACE/SELECT/EYE_SMALL'/q/(s['game_song_id']+'.G')).unlink(missing_ok=True)
    done.append(s['game_song_id']);print(s['game_song_id'],s['title'],'<-',s['video_policy'])
(R/'selection.json').write_text(json.dumps(S,ensure_ascii=False,indent=1),encoding='utf8')
(R/'redo_ids.txt').write_text(' '.join(done));print('APPLIED',len(done))
