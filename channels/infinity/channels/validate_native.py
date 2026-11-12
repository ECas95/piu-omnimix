"""Load every converted NX in PRIME's original engine (loader + hold-mask probe of the NSDE/RISE imports).
Runs in WSL; the engine and probe are only executed, never modified. Output: native_results.json."""
from pathlib import Path
import json,hashlib,subprocess,re
R=Path(__file__).resolve().parent
ENGINE='/mnt/c/Users/USER/.codex/workspaces/anime_channel_cache/native_build/full_validation_engine'
PROBE='/mnt/e/Pump It Up Data/PIU/nsde_channel/native_hold_probe'
unix=lambda p:'/mnt/'+p[0].lower()+p[2:].replace('\\','/')
sel=json.loads((R/'selection.json').read_text(encoding='utf8'))['records']
report={(r['song'],r['name']):r for r in json.loads((R/'charts_report_pack.json').read_text(encoding='utf8')) if r.get('ok')}
out=[];bad=0
for s in sel:
    for c in s['charts']:
        p=subprocess.run([PROBE,ENGINE,unix(c['nx'])],capture_output=True,timeout=90);text=(p.stdout+p.stderr).decode(errors='replace')
        m=re.search(r'HOLD_ROWS_PASS cols=(\d+) judged=(\d+) visual_only=(\d+)',text)
        want=(report.get((s['source_group']+'/'+s['source_folder'],c['name'])) or {}).get('proof',{}).get('hold_ticks')
        ok=p.returncode==0 and bool(m) and (want is None or int(m[2])==want)
        bad+=not ok;out.append(dict(gid=s['game_song_id'],chart=c['name'],ok=ok,returncode=p.returncode,judged=int(m[2]) if m else None,expected=want,tail=None if ok else text[-400:]))
(R/'native_results.json').write_text(json.dumps(dict(engine=ENGINE,probe=PROBE,charts=len(out),failed=bad,results=out),indent=1))
print('NATIVE_LOADER',len(out),'failed',bad,flush=True)
