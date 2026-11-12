from pathlib import Path
import json,subprocess,re
from fractions import Fraction as F
import native_gimmicks_tick_compensation as D
import simfile as SM
R=Path(__file__).resolve().parent;O=R/'research/native_pause_critical';C=Path(r'C:\Users\USER/.codex/workspaces/anime_channel_cache/native_build/native_pause_revision');rows=json.loads((O/'result.json').read_text())['results'];results=[]
for row in rows:
 if not row['pass_source']:continue
 name=Path(row['path']).name;proof=json.loads(Path(row['proof']).read_text());args=['wsl','-d','Ubuntu','-u','root','--','chroot','/mnt/piu-anime-native-validation']
 p=subprocess.run(args+['/mnt/native_build/test_native_full_nx_short_rows_chroot','/mnt/native_build/full_validation_engine','/mnt/native_build/native_pause_revision/'+name],capture_output=True,text=True,cwd=R);(O/(name+'.selector.log')).write_text(p.stdout+'\n'+p.stderr);m=re.search(r'notes=(\d+)',p.stdout);selector=p.returncode==0 and m is not None and int(m[1])==proof['source_heads']
 song=json.loads((R/'chart_sources'/(row['song_id']+'.json')).read_text());c=next(x for x in song['native_pump_charts'] if x['signature']==row['signature']);clock=SM.Clock(c['timing']);old=D.canonical_beat;D.canonical_beat=F
 try:speeds=D.Speeds(c['timing'].get('SPEEDS',''))
 finally:D.canonical_beat=old
 beats=set()
 for a,z,begin,target in speeds.segments:
  if z>a:
   for part in [F(1,10),F(1,2),F(9,10)]:beats.add(a+(z-a)*part)
 if not beats:beats={F(1),F(4),F(8)}
 samples=sorted((clock.seconds(b)*1000,speeds.value(b)) for b in beats);samplepath=C/(name+'.samples');samplepath.write_text('\n'.join(str(ms) for ms,value in samples))
 p=subprocess.run(args+['/mnt/native_build/probe_native_speed_samples','/mnt/native_build/full_validation_engine','/mnt/native_build/native_pause_revision/'+name,'/mnt/native_build/native_pause_revision/'+samplepath.name],capture_output=True,text=True,cwd=R);(O/(name+'.speed.log')).write_text(p.stdout+'\n'+p.stderr);actual=[tuple(map(float,m)) for m in re.findall(r'^SV ([-\d.e+]+) ([-\d.e+]+)',p.stdout,re.M)];error=max([abs(a[1]-e[1]) for a,e in zip(actual,samples)] or [999]);speed=p.returncode==0 and len(actual)==len(samples) and error<.002
 results.append(dict(song_id=row['song_id'],signature=row['signature'],title=row['title'],mode=row['mode'],level=row['level'],pass_native_selector=selector,pass_native_global_speed=speed,maximum_speed_error=error,samples=len(samples),promoted=False));print(results[-1],flush=True)
(O/'native_selector_speed_result.json').write_text(json.dumps(dict(results=results,complete=True,promoted=False),indent=2))
