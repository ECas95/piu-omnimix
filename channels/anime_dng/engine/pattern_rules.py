"""User-reviewed Pump vocabulary and independent serialized pattern audits.
Panel order: down-left, up-left, center, up-right, down-right.
Templates preserve panel vocabulary only: chart rhythm always comes from source.
"""
import math
from functools import lru_cache
REFERENCE_RUNS={
 'img4_corrected':[2,1,2,1,3,2,3,2,3,1,2,0,4,2,3,1,3,2,4,0,4,0,2,1],
 'img5_stream':[2,1,3,1,2,0,4,2,3,2,4,0,2,1,3,2,4,0,2,1,2,0,4,2,3,1,2,0,2,1,3,2,4],
 'img6_stairs':[0,1,2,3,1,2,3,4,2,3,1,3,2,4,0,2,1],
 'img8_sweeps':[2,1,0,2,4,0,2,4,3,2,4,3,4,2,3,1,2],
 'img9_stream':[2,1,2,1,3,1,3,1,2,1,2,0,1,0,2,1,3,1,2,0,4,2,3,1,3,2,4,2,3,1,3,2,4],
}

def _front_walkable(lanes):
 coords=((-1,-1),(-1,1),(0,0),(1,1),(1,-1))
 states={(a,b,-1) for a in range(5) for b in range(5) if a!=b and coords[a][0]<coords[b][0]}
 for lane in lanes:
  nxt=set()
  for left,right,last in states:
   for foot in (0,1):
    if foot==last:continue
    a,b=(lane,right) if foot==0 else (left,lane)
    dx=coords[b][0]-coords[a][0];dy=coords[b][1]-coords[a][1]
    if a!=b and dx>=0 and abs(math.degrees(math.atan2(-dy,dx)))<=60 and math.hypot(dx,dy)<=2.9:nxt.add((a,b,foot))
  states=nxt
  if not states:return False
 return bool(states)

@lru_cache(maxsize=8)
def curated_pool(cols,size):
 out=[];seen=set()
 for label,run in REFERENCE_RUNS.items():
  for start in range(len(run)-size+1):
   lanes=run[start:start+size]
   if not _front_walkable(lanes):continue
   for mirror in (False,True):
    single=[4-l if mirror else l for l in lanes]
    for pad in ((0,) if cols==5 else (0,5)):
     phrase=tuple(l+pad for l in single)
     if phrase in seen:continue
     seen.add(phrase);out.append({'lanes':list(phrase),'gaps':[.25]*(size-1),'count':1,'reference':label})
 return out

def stream_violation(history,lane,beat,ms):
 if history and not (0<beat-history[-1][1]<=.50001 and ms-history[-1][2]<=400):history=()
 if history and history[-1][0]==lane:return 'adjacent_stream_jack'
 result=(history+((lane,beat,ms),))[-12:];seq=[v[0] for v in result]
 if len(seq)>=8 and seq[-8:]==seq[-2:]*4:return 'eight_note_two_panel_loop'
 if len(seq)>=12 and len(set(seq))<4:return 'twelve_note_stationary_stream'
 return None

def next_stream(history,lane,beat,ms):
 if history and not (0<beat-history[-1][1]<=.50001 and ms-history[-1][2]<=400):history=()
 return (history+((lane,beat,ms),))[-12:]

def hold_violation(previous,lane,foot,ms,free_both,direct=False):
 if not previous:return None
 old_lane,old_foot,end_ms=previous[:3]
 if ms-end_ms>650:return None
 if lane==old_lane:return 'same_panel_hold_chain'
 if direct and free_both and foot==old_foot:return 'same_foot_hold_chain'
 return None

def release_violation(releases,lane,beat,ms):
 for release in releases:
  old_lane,end_ms,end_beat=release[:3]
  # Half a beat, capped at350ms: this is the immediate release/repress gesture,
  # not an intentional repeated panel after a musical rest.
  if lane==old_lane and 0<=ms-end_ms<=350.+1e-5 and 0<=beat-end_beat<=.50001:
   return 'same_panel_immediately_after_hold'
 return None


def audit(timeline,events,footsteps):
 active={};last_hold=None;stream=();errors=[];chains=0;changed=0;fast_rows=0
 plan={r['index']:r for r in footsteps};heads=0;previous_row_ms=None;releases=[];held_panels={};release_checks=0
 for event in events:
  i=event['index'];ms=event['ms']
  for foot,end in active.items():
   if end<i:releases.append((held_panels[foot],timeline[end][1],timeline[end][0],foot))
  releases=[v for v in releases if ms-v[1]<=350.+1e-5 and event['beat']-v[2]<=.50001]
  active={f:end for f,end in active.items() if end>=i}
  actions=plan[i]['actions'];free_both=not active
  for lane,foot,end in actions:
   if releases:
    release_checks+=1
    error=release_violation(releases,lane,event['beat'],ms)
    if error:errors.append({'kind':error,'index':i,'ms':ms,'lane':lane})
   if end>=0:
    heads+=1
    if last_hold and ms-last_hold[2]<=650:
     chains+=1;changed+=lane!=last_hold[0]
    error=hold_violation(last_hold,lane,foot,ms,free_both, bool(last_hold and previous_row_ms==last_hold[3]))
    if error:errors.append({'kind':error,'index':i,'ms':ms,'lane':lane})
    last_hold=(lane,foot,timeline[end][1],ms);active[foot]=end;held_panels[foot]=lane
  if len(actions)==1 and not active:
   lane=actions[0][0];error=stream_violation(stream,lane,event['beat'],ms)
   if error:errors.append({'kind':error,'index':i,'ms':ms,'lane':lane})
   stream=next_stream(stream,lane,event['beat'],ms);fast_rows+=len(stream)>1
  else:stream=()
  previous_row_ms=ms
 return {'pass':not errors,'errors':errors,'post_hold_attacks_checked':release_checks,'hold_heads':heads,'hold_chain_transitions':chains,'hold_chain_direction_changes':changed,'fast_stream_rows_checked':fast_rows,'policy':'no same-panel attack within half-beat/350ms after hold release; change panel in released hold chains; alternate feet in direct chains; no adjacent stream jack; no eight-note two-panel loop; at least four panels per twelve fast singles'}
