"""bga_delay is in 1/60 s (sync_grupo.py), not ms: every IIDX song with a delay gets its movie start corrected. Keeps a SHA snapshot of the old media so the patch ships only what changed,
then removes the song's media result so prepare_media redoes it. Writes reparar_sync.json. Run once."""
import json,hashlib,shutil
from pathlib import Path
H=Path(__file__).resolve().parent;SEL=Path('D:/PIU_INFINITY/channels/selection.json');CH=SEL.parent
if (H/'reparar_sync.json').exists():raise SystemExit('already done')
S=json.loads(SEL.read_text(encoding='utf8'));shutil.copy2(SEL,SEL.with_name('selection.antes_sync.json'));done=[];snap={}
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()
for r in S['records']:
    if r['channel']!='IIDX':continue
    res=json.loads((H/'canal/songs'/r['source_folder']/'result.json').read_text(encoding='utf8'));d=res['delay'];seg=r['video_segments'][0];old=seg['seconds'];new=d/60
    assert abs(old-d/1000)<1e-6,(r['title'],old,d)
    seg['seconds']=new;r['video_policy']=f"IIDX own BGA {Path(seg['file']).name} from {new:.3f}s (bga_delay {d}/60), cut to 16:9"
    if abs(d)<2:continue
    gid=r['game_song_id'];dest=CH/'media/D'/gid;snap[gid]={p.relative_to(dest).as_posix():sha(p) for p in dest.rglob('*') if p.is_file()}
    (CH/'media_results'/(gid+'.json')).unlink();done.append(dict(id=gid,folder=r['source_folder'],title=r['title'],delay=d,old=old,new=new))
SEL.write_text(json.dumps(S,ensure_ascii=False,indent=1),encoding='utf8')
(H/'reparar_sync.json').write_text(json.dumps(dict(songs=done,old_media=snap),ensure_ascii=False,indent=0),encoding='utf8');print('SYNC_REPARADO',len(done))
