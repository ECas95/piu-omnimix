from pathlib import Path
import sys,json,hashlib,math,traceback
from fractions import Fraction as F
R=Path(__file__).resolve().parent;OUT=R/'research/native_tick_compensation';OUT.mkdir(parents=True,exist_ok=True)
import native_gimmicks_tick_compensation as N
import simfile as SM
from nx_adapter import nx20
rows=json.loads((R/'human_policy_remaining_charts.json').read_text())['native_chart_failures'];results=[];seen=set()
for row in rows:
 if 'tick density' not in row['error']:continue
 key=(row['song_id'],row['signature'])
 if key in seen:continue
 seen.add(key)
 try:
  song=json.loads((R/'chart_sources'/(key[0]+'.json')).read_text());c=next(c for c in song['native_pump_charts'] if c['signature']==key[1]);raw,proof=N.convert(c,song['output_seconds']);nx=nx20.parse(raw)
  assert all(0<(s['head'][8]&255)<=24 for s in nx['splits'])
  notes,_=SM.events(c,native=True);clock=SM.Clock(c['timing']);ticks=SM.pairs(c['timing'].get('TICKCOUNTS','')) or [(F(0),4)];expected=[]
  for note in notes:
   if note['tail_beat'] is None:continue
   a,z=F(note['beat']),F(note['tail_beat'])
   for i,(begin,tick) in enumerate(ticks):
    tick=int(tick)
    if tick<=0:continue
    end=ticks[i+1][0] if i+1<len(ticks) else z
    left=max(a,begin);right=min(z,end)
    for k in range(math.ceil(left*tick),math.ceil(right*tick)):
     beat=F(k,tick)
     if a<beat<z and clock.judgable(beat):expected.append((note['lane'],clock.seconds(beat)*1000))
  actual=[]
  for split in nx['splits']:
   h=split['head'];step=60000/h[4]/(h[8]&255)
   for j,cells in enumerate(split['rows']):
    for lane,cell in enumerate(cells or []):
     if cell&255==0x5b:actual.append((lane,h[3]+j*step))
  expected.sort();actual.sort();assert len(expected)==len(actual),('Hold tick count differs',len(expected),len(actual));error=0
  for x,y in zip(expected,actual):assert x[0]==y[0];error=max(error,abs(x[1]-y[1]))
  assert error<.1,('Hold tick timing differs',error)
  path=OUT/(key[0]+'_'+key[1][:12]+'.NX');path.write_bytes(raw);proof.update(independent_expected_hold_ticks=len(expected),independent_actual_hold_ticks=len(actual),maximum_hold_tick_timing_error_ms=error,native_runtime_judgment_pending=True,promoted=False);path.with_suffix('.proof.json').write_text(json.dumps(proof,indent=2));result=dict(song_id=key[0],signature=key[1],title=song['title'],mode=c['mode'],level=c['meter'],pass_source_ticks=True,hold_ticks=len(actual),nx_sha256=hashlib.sha256(raw).hexdigest(),native_runtime_judgment_pending=True)
 except Exception as e:result=dict(song_id=key[0],signature=key[1],title=row['title'],pass_source_ticks=False,error=repr(e),traceback=traceback.format_exc())
 results.append(result);(OUT/'result.json').write_text(json.dumps(dict(results=results,complete=False,promoted=False),indent=2));print(result,flush=True)
(OUT/'result.json').write_text(json.dumps(dict(results=results,complete=True,promoted=False),indent=2))
