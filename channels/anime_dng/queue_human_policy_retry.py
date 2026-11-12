from pathlib import Path
import json,subprocess,sys,time,psutil
R=Path(__file__).resolve().parent
while psutil.pid_exists(38876):
 try:
  if 'run_preflight_special_omissions.py' not in ' '.join(psutil.Process(38876).cmdline()):break
 except psutil.NoSuchProcess:break
 time.sleep(2)
omissions=json.loads((R.parent/'anime_final_v8/release_omissions.json').read_text())['excluded_songs'];ids=[x['song_id'] for x in omissions]
subprocess.run([sys.executable,'-u',str(R/'run_human_policy_charts.py'),'--workers','1','--songs',*ids],cwd=R,check=True)
import run_human_policy_charts as W
import generate_charts as G
failures=[]
for row in omissions:
 p=R/'chart_sources'/(row['song_id']+'.json')
 if not p.exists():
  failures.append(dict(song_id=row['song_id'],title=row['title'],error='Source preflight still blocked; see source_preflight errors'));continue
 song=json.loads(p.read_text())
 for c in song['native_pump_charts']:
  try:W.native_with_effects(c,song['output_seconds'])
  except Exception as e:failures.append(dict(song_id=row['song_id'],title=row['title'],mode=c['mode'],level=c['meter'],description=c.get('description'),signature=c['signature'],source_file_id=c['source_file_id'],error=repr(e)))
(R/'human_policy_remaining_charts.json').write_text(json.dumps(dict(native_chart_failures=failures,song_generation_report=str(R/'pilot_chart_manifest.json'),originals_preserved=True),indent=2,ensure_ascii=False))
