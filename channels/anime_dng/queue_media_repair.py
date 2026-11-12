from pathlib import Path
import json,time,subprocess,sys,psutil
R=Path(__file__).resolve().parent
while psutil.pid_exists(20720):
 try:
  p=psutil.Process(20720)
  if 'run_media_pipeline.py' not in ' '.join(p.cmdline()):break
 except psutil.NoSuchProcess:break
 time.sleep(15)
with (R/'logs/media_retry_plan.log').open('wb') as f:subprocess.run([sys.executable,'-u',str(R/'plan_media.py')],cwd=str(R),stdout=f,stderr=subprocess.STDOUT,check=True)
plan=json.loads((R/'media_plan.json').read_text());todo=[]
for row in plan['records']:
 sid=row['song_id'];p=R/'media_results'/f'{sid}.json'
 if not p.exists() or not json.loads(p.read_text()).get('complete',False):todo.append(sid)
# The normal receipts retain successful outputs; retry only missing/failed songs once.
if todo:
 with (R/'logs/media_retry_encode.log').open('wb') as f:subprocess.run([sys.executable,'-u',str(R/'prepare_media.py'),'--workers','1','--songs',*todo],cwd=str(R),stdout=f,stderr=subprocess.STDOUT,check=True)
(R/'media_retry_state.json').write_text(json.dumps(dict(done=True,retried=todo,planning_errors=plan['errors'],installed=False)))
