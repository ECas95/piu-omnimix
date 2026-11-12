import run_human_policy_charts as W
import json
from pathlib import Path
R=Path(__file__).resolve().parent
s=json.loads((R/'chart_sources/4727e126b88a0c0bb598db06.json').read_text())
f=[]
for c in s['native_pump_charts']:
 try:W.native_with_effects(c,s['output_seconds'])
 except Exception as e:f.append(dict(song_id=s['song_id'],title=s['title'],mode=c['mode'],level=c['meter'],description=c.get('description'),signature=c['signature'],source_file_id=c['source_file_id'],error=repr(e)))
p=R/'human_policy_remaining_charts.json';d=json.loads(p.read_text());d['native_chart_failures']=[x for x in d['native_chart_failures'] if x['song_id']!=s['song_id']]+f;p.write_text(json.dumps(d,indent=2,ensure_ascii=False))
print('Death failures',len(f))
