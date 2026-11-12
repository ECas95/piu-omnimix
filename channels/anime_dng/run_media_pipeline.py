from pathlib import Path
import subprocess,sys,json,time
R=Path(__file__).resolve().parent
for name,args in [('assemble_sources.py',[]),('preflight.py',[]),('plan_media.py',[]),('prepare_media.py',['--workers','1'])]:
 (R/'pipeline_state.json').write_text(json.dumps(dict(stage=name,complete=False,pid=__import__('os').getpid(),started=time.time())))
 with (R/'logs'/(name+'.stdout.log')).open('ab') as a,(R/'logs'/(name+'.stderr.log')).open('ab') as z:
  p=subprocess.run([sys.executable,'-u',str(R/name)]+args,cwd=str(R),stdout=a,stderr=z)
 if p.returncode:
  (R/'pipeline_state.json').write_text(json.dumps(dict(stage=name,complete=False,returncode=p.returncode,needs_review=True)));raise SystemExit(p.returncode)
(R/'pipeline_state.json').write_text(json.dumps(dict(stage='available_media_complete_semantic_blocks_pending',complete=True,installed=False)))
