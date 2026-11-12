"""INFINITY upscaled BGAs (user 2026-10-29): '06. INFINITY BGAs' now holds <ID>.realesrgan.mkv in place of <ID>.mpg.
Every INFINITY segment playing one of those IDs switches to the new file; timeline (start/rate) unchanged."""
from pathlib import Path
import json,shutil
R=Path(__file__).resolve().parent;D=Path(r'C:\DATA\PJD\DATA INF PRO PRO2\06. INFINITY BGAs')
NEW={p.name[:-len('.realesrgan.mkv')].lower():p for p in D.glob('*.realesrgan.mkv')}
S=json.loads((R/'selection.json').read_text(encoding='utf8'));done=[];used=set()
for s in S['records']:
    if s['channel']!='INF':continue
    hit=False
    for g in s['video_segments']:
        k=Path(g['file']).stem.lower()
        if k in NEW and g['file']!=str(NEW[k]):g['file']=str(NEW[k]);hit=True;used.add(k)
    if not hit:continue
    s['video_policy']+=' (upscaled INFINITY BGAs)'
    shutil.rmtree(R/'media/D'/s['game_song_id'],ignore_errors=True);(R/'media_results'/(s['game_song_id']+'.json')).unlink(missing_ok=True)
    for q in ('HD','SD'):(R/'media/USER_INTERFACE/SELECT/EYE_SMALL'/q/(s['game_song_id']+'.G')).unlink(missing_ok=True)
    done.append(s['game_song_id']);print(s['game_song_id'],s['title'],[Path(g['file']).name for g in s['video_segments']])
(R/'selection.json').write_text(json.dumps(S,ensure_ascii=False,indent=1),encoding='utf8')
(R/'redo_ids.txt').write_text(' '.join(done));print('APPLIED',len(done),'unused new files',sorted(set(NEW)-used))
