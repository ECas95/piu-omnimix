"""Use the PRIME catalog's own movie (native Fiesta EX / Fiesta 2 / PRIME 2 ... entry of the same song, same
artist) for PRO / PRO 2 / INFINITY songs that only had a still or a generic movie (user 2026-10-26).
The movie is read from the installed game (read-only) and aligned like any PRIME movie (decoder delay +
selector advance already inside it, so it starts that many frames before the song)."""
from pathlib import Path
import sys,json,shutil
R=Path(__file__).resolve().parent;OUT=R/'prime_bga'
sys.dont_write_bytecode=True
sys.path[:0]=[r'E:\Pump It Up Data\PIU',r'E:\Pump It Up Data\PIU\nsde_channel']
from current_parent import load
FPS=30;START=round((2257/48000+1/FPS)*FPS)
P,game=load();OUT.mkdir(exist_ok=True)
m=json.loads((R/'prime_bga_matches.json').read_text(encoding='utf8'))['found']
S=json.loads((R/'selection.json').read_text(encoding='utf8'));sel={s['game_song_id']:s for s in S['records']}
done=[]
for f in m:
    s=sel[f['gid']]
    if s['video_segments'] and not (s.get('video_policy') or '').startswith('PRIME generic'):continue   # keep Infinity's own movies
    h=next((x for x in f['prime'] if not x.get('from_other_kind')),f['prime'][0])
    dst=OUT/(h['id']+'.m2v')
    if not dst.exists():dst.write_bytes(game.get(h['movie']))
    s['video_segments']=[dict(beat='0',seconds=-START/FPS,file=str(dst),rate=1.)]
    s['video_policy']=f"PRIME movie of {h['title']} ({h['artist']}), channel {h['channel']}, id {h['id']}"
    shutil.rmtree(R/'media/D'/s['game_song_id'],ignore_errors=True);(R/'media_results'/(s['game_song_id']+'.json')).unlink(missing_ok=True)
    for q in ('HD','SD'):(R/'media/USER_INTERFACE/SELECT/EYE_SMALL'/q/(s['game_song_id']+'.G')).unlink(missing_ok=True)
    done.append(s['game_song_id']);print(s['game_song_id'],s['title'],'<-',s['video_policy'])
(R/'selection.json').write_text(json.dumps(S,ensure_ascii=False,indent=1),encoding='utf8')
(R/'redo_ids.txt').write_text(' '.join(done));print('PRIME_BGA_APPLIED',len(done))
