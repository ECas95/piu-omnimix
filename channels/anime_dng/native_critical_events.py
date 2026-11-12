"""Native critical-event NX placement; no fixed global denominator required.
Pauses, warps, negative effects and second-based ramps explicitly remain unsupported.
"""
from fractions import Fraction as F
import math,struct,hashlib
import simfile as SM
import native_gimmicks_tick_compensation as D
from nx_adapter import nx20,Q

def convert(c,seconds):
 clock=SM.Clock(c['timing'])
 assert not clock.stops and not clock.delays and not clock.warps,'Critical-event converter does not map pauses/warps'
 assert c['mode'] in ('pump-single','pump-double')
 notes,_=SM.events(c,native=True);cols=SM.COLS[c['mode']]
 scrolls=SM.pairs(c['timing'].get('SCROLLS','')) or [(F(0),1.)];ticks=SM.pairs(c['timing'].get('TICKCOUNTS','')) or [(F(0),4.)]
 assert all(v>=0 for b,v in scrolls),'Negative SCROLLS remains blocked'
 old=D.canonical_beat;D.canonical_beat=F
 try:speeds=D.Speeds(c['timing'].get('SPEEDS',''))
 finally:D.canonical_beat=old
 cells={};expected_ticks=[];points={F(0)}|{b for b,v in clock.bpms+scrolls+ticks}|{b for a,z,x,y in speeds.segments for b in (a,z)}
 for n in notes:
  a=F(n['beat']);points.add(a);key=(a,n['lane']);assert key not in cells;cells[key]=nx20.HOLD_START if n['tail_beat'] is not None else nx20.TAP
  if n['tail_beat'] is not None:
   z=F(n['tail_beat']);points.add(z);key=(z,n['lane']);assert key not in cells;cells[key]=nx20.HOLD_END
   for i,(start,tick) in enumerate(ticks):
    tick=int(tick)
    if tick<=0:continue
    end=ticks[i+1][0] if i+1<len(ticks) else z
    for k in range(math.ceil(max(a,start)*tick),math.ceil(min(z,end)*tick)):
     beat=F(k,tick)
     if a<beat<z and clock.judgable(beat):points.add(beat);expected_ticks.append((n['lane'],clock.seconds(beat)*1000))
 last=max(points);points.add(last+max(F(4),F(str(max(0,seconds-clock.seconds(last))*clock.bpm(last)/60))))
 # Float32 timestamps are the format precision. Coalesce identical stored times;
 # preserve every source cell or reject an unrepresentable same-panel collision.
 groups={}
 for b in sorted(points):groups.setdefault(D.float32(clock.seconds(b)*1000),[]).append(b)
 grouped=sorted(groups.items());splits=[];max_error=0;body_tick_times=[];previous_end=0.
 for i,(ms,beats) in enumerate(grouped[:-1]):
  a=beats[0];next_ms,next_beats=grouped[i+1];z=next_beats[0];duration=next_ms-ms;assert duration>0
  row=[0]*cols
  for beat in beats:
   for lane in range(cols):
    value=cells.get((beat,lane),0)
    if value:assert not row[lane] or row[lane]==value,('Critical source cells collide',beat,lane);row[lane]=value
  for n in notes:
   if n['tail_beat'] is None:continue
   lane=n['lane'];start,end=F(n['beat']),F(n['tail_beat'])
   if start<a<end and not row[lane]:
    judged=any((start<b<end and int(D.at(ticks,b))>0 and (b*int(D.at(ticks,b))).denominator==1) for b in beats)
    row[lane]=nx20.HOLD_BODY if judged else 0x33b
    if judged:body_tick_times.append((lane,ms))
  bpm=D.ceil_float32(60000/duration)
  while ms+60000/bpm>next_ms:bpm=D.next_float32(bpm)
  begin=speeds.value(a);target=speeds.value(z,left=True);smooth=abs(target-begin)>1e-10
  head=(0,0,1,ms,bpm,float(z-a)*D.at(scrolls,a),ms-previous_end,target,0x401|(0x10000 if smooth else 0),0,1)
  splits.append(dict(head=head,rows=[tuple(row) if any(row) else None]));previous_end=ms+60000/bpm
 raw=nx20.build(dict(cols=cols,unk=0,tags=[(1000,1),(1001,int(float(c['meter'])))],splits=splits,pool=b''));parsed=nx20.parse(raw)
 actual=sorted((x[1],x[2],x[4]) for x in Q.notes_of(parsed));expected=sorted((n['ms'],n['lane'],n['tail_ms']) for n in notes);assert len(actual)==len(expected),'Critical native attack count changed'
 for x,y in zip(actual,expected):
  assert x[1]==y[1] and (x[2] is None)==(y[2] is None),'Critical native panel/hold changed';max_error=max(max_error,abs(x[0]-y[0]))
  if x[2] is not None:max_error=max(max_error,abs(x[2]-y[2]))
 assert max_error<.1,('Original attack/tail timing changed',max_error)
 actual_ticks=sorted(body_tick_times);expected_ticks.sort();assert len(actual_ticks)==len(expected_ticks),('Critical tick count changed',len(actual_ticks),len(expected_ticks))
 tick_error=0
 for x,y in zip(actual_ticks,expected_ticks):assert x[0]==y[0];tick_error=max(tick_error,abs(x[1]-y[1]))
 assert tick_error<.1
 return raw,dict(sha256=hashlib.sha256(raw).hexdigest(),source_signature=c['signature'],source_file_sha256=c['source_file_sha256'],source_heads=len(notes),hold_ticks=len(expected_ticks),maximum_source_attack_tail_error_ms=max_error,maximum_source_tick_error_ms=tick_error,final_rpb=1,source_patterns_preserved=True,native_loader_render_pending=True,promoted=False)
