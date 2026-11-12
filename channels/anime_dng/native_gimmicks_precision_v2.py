import copy
from fractions import Fraction as F
import native_gimmicks_dense as D
import simfile as SM
from nx_adapter import Q,nx20

def convert(chart,seconds):
 c=copy.deepcopy(chart);repairs=[];source_clock=SM.Clock(chart['timing'])
 for field,value in list(c['timing'].items()):
  if field=='OFFSET' or not value.strip():continue
  rows=[]
  for entry in value.split(','):
   if not entry.strip():continue
   fields=entry.strip().split('=');beat=F(fields[0]);snap=F(round(beat*48),48)
   if beat!=snap and abs(beat-snap)<=F(1,10000) and abs(source_clock.seconds(beat)-source_clock.seconds(snap))<0.00001:
    repairs.append(dict(field=field,source_beat=str(beat),native_beat=str(snap),maximum_difference_beats=float(abs(beat-snap)),source_clock_difference_ms=abs(source_clock.seconds(beat)-source_clock.seconds(snap))*1000,reason='Near-grid decimal writer precision; source-clock displacement<0.01ms, original onset/tail guard unchanged'));fields[0]=str(snap)
   if field=='SPEEDS' and len(fields)>=4 and fields[3].strip()=='0':
    duration=F(fields[2]);snapped=F(round(duration*48),48)
    if duration!=snapped and abs(duration-snapped)<=F(1,10000) and abs(source_clock.seconds(beat+duration)-source_clock.seconds(beat+snapped))<0.00001:
     repairs.append(dict(field='SPEEDS.duration_beats',source=str(duration),native=str(snapped),source_clock_difference_ms=abs(source_clock.seconds(beat+duration)-source_clock.seconds(beat+snapped))*1000,reason='Beat-duration decimal writer precision; original source head/tail bound unchanged'));fields[2]=str(snapped)
   rows.append('='.join(fields))
  c['timing'][field]=','.join(rows)
 raw,proof=D.convert(c,seconds)
 actual=sorted((x[1],x[2],x[4]) for x in Q.notes_of(nx20.parse(raw)));expected=sorted((x['ms'],x['lane'],x.get('tail_ms')) for x in chart['attack_events']);assert len(actual)==len(expected)
 errors=[]
 for a,z in zip(actual,expected):
  assert a[1]==z[1] and (a[2] is None)==(z[2] is None)
  errors.append(abs(a[0]-z[0]))
  if a[2] is not None:errors.append(abs(a[2]-z[2]))
 assert max(errors or [0])<.1,('Original source timing differs',max(errors))
 proof.update(decimal_timing_precision_repairs=repairs,maximum_original_source_timing_error_ms=max(errors or [0]),original_source_attack_count=len(expected));return raw,proof
