"""Experimental lossless native Pump import; promote only after native probes.

NX mystery/row distance models SCROLLS; global speed models SPEEDS.
The native loader uses the sign of global speed for delay freezing, not reverse.
"""
import bisect,hashlib,math,struct
from fractions import Fraction as F
import simfile as SM
from nx_adapter import E,Q,nx20,native_source_cells

def canonical_beat(token):
    value=F(token)
    return F(round(value*48),48)

def step_pairs(text,default):
    out={canonical_beat(b):float(v) for b,v in SM.pairs(text)}
    if not out:out[F(0)]=default
    elif min(out)>0:out[F(0)]=out[min(out)]
    return sorted(out.items())

def at(points,beat):
    eligible=[v for b,v in points if b<=beat]
    return eligible[-1] if eligible else points[0][1]

def float32(value):return struct.unpack('<f',struct.pack('<f',value))[0]
def next_float32(value):
    bits=struct.unpack('<I',struct.pack('<f',value))[0]
    return struct.unpack('<f',struct.pack('<I',bits+1))[0]
def ceil_float32(value):
    rounded=float32(value)
    return next_float32(rounded) if rounded<value else rounded

class Speeds:
    def __init__(self,text):
        self.segments=[];self.quantization=[]
        rows=[]
        for item in text.split(','):
            if not item.strip():continue
            p=item.strip().split('=');assert len(p)>=2
            b=canonical_beat(p[0]);target=float(p[1]);duration=F(p[2]) if len(p)>2 else F(0);unit=int(p[3]) if len(p)>3 else 0
            if target<0:raise ValueError('Native reverse SPEEDS needs dedicated support; negative NX speed is a freeze flag')
            if unit and duration:raise ValueError('Native second-based SPEEDS needs independent mapping')
            assert duration>=0
            rows.append((b,target,duration));self.quantization.append({'source_beat':p[0],'native_sm_beat':str(b)})
        for b,target,duration in sorted(rows):
            start=self.value(b)
            self.segments.append((b,b+duration,start,target))
    def segment(self,beat,left=False):
        matches=[s for s in self.segments if s[0]<beat or (s[0]==beat and not left)]
        return matches[-1] if matches else None
    def value(self,beat,left=False):
        s=self.segment(beat,left)
        if s is None:return 1.
        b,e,start,target=s
        return target if e==b or beat>=e else start+(target-start)*float((beat-b)/(e-b))

def convert(chart,seconds):
    assert chart['mode'] in ('pump-single','pump-double')
    notes,_=SM.events(chart,native=True);clock=SM.Clock(chart['timing'])
    scrolls=step_pairs(chart['timing'].get('SCROLLS',''),1.)
    ticks=step_pairs(chart['timing'].get('TICKCOUNTS',''),4.)
    assert all(v>=0 for b,v in scrolls),'Negative native SCROLLS needs independent mapping'
    assert all(v>=0 and int(v)==v for b,v in ticks),'Invalid native tickcount'
    if any(v>24 for b,v in ticks):raise ValueError('Native tick density is not exactly representable within24 checkpoints per beat')
    speeds=Speeds(chart['timing'].get('SPEEDS',''))
    bounds={b for b,v in scrolls+ticks}|{b for b,e,a,z in speeds.segments}|{e for b,e,a,z in speeds.segments}
    bpms=dict(clock.bpms)
    for b in bounds:bpms[b]=clock.bpm(b)
    regions=[];original=E.pick_rpb
    def choose(start,end,beats):
        tick=max(1,int(at(ticks,start)))
        candidates=[r for r in E.RPB_CHOICES if r%tick==0 and (start*r).denominator==1
                    and all(((b-start)*r).denominator==1 for b in beats+[end])]
        # Some authored SPEED durations use fifths in addition to 48-row
        # positions. A240-row internal placement grid is exactly representable
        # in the one-byte intermediate field and is compensated to<=24 below.
        exact=math.lcm(tick,start.denominator,*((b-start).denominator for b in beats+[end]))
        if exact<=65535 and (end-start)*exact<=250000:candidates.append(exact)
        if not candidates:raise ValueError('Native timing/tick grid is not exactly representable: '+str((start,end,tick,beats[:6])))
        r=min(candidates);regions.append((start,end,r));return r
    E.pick_rpb=choose
    try:
        source,warp_tails=native_source_cells(chart,notes,clock)
        raw=E.build_nx(source,sorted(bpms.items()),dict(clock.stops),dict(clock.delays),-clock.offset*1000,
            int(float(chart['meter'])),SM.COLS[chart['mode']],seconds*1000,warps={a:b-a for a,b in clock.warps})
    finally:E.pick_rpb=original
    descriptors=[]
    for a,z,r in regions:
        n=int((z-a)*r)
        if a in dict(clock.stops) and n:
            descriptors.append((a,r,1));a+=F(1,r);n-=1
        if n:descriptors.append((a,r,n))
    nx=nx20.parse(raw);assert len(descriptors)==len(nx['splits'])
    previous_end=0.;previous_source_end=None;scored_bodies=0;visual_bodies=0;curves=[];grid_compensations=[];rounding_fits=[]
    for i,(split,(a,r,n)) in enumerate(zip(nx['splits'],descriptors)):
        assert n==len(split['rows'])
        z=a+F(n,r);h=list(split['head']);h[6]=h[3]-previous_end
        source_start_ms=clock.seconds(a)*1000
        source_gap=source_start_ms-previous_source_end if previous_source_end is not None else 0.
        assert source_gap>=-1e-5,('Source split overlap',source_gap)
        pause_gap=i and source_gap>.001
        if i and h[6]<-.001:
            previous=nx['splits'][i-1];ph=list(previous['head']);nr=len(previous['rows']);pr=ph[8]&255
            overlap=-h[6];ulp=max(next_float32(h[3])-h[3],next_float32(ph[3])-ph[3])
            # Fit only proven float32 endpoint-rounding overlap. Real source
            # overlaps remain rejected; the original-.001 gate stays intact.
            if overlap<=min(.1,2*ulp):
                old_bpm=ph[4];desired=h[3]-ph[3];assert desired>0
                ph[4]=ceil_float32(nr*60000/(pr*desired))
                while ph[3]+nr*60000/ph[4]/pr>h[3]:ph[4]=next_float32(ph[4])
                previous['head']=tuple(ph);previous_end=ph[3]+nr*60000/ph[4]/pr;h[6]=h[3]-previous_end
                rounding_fits.append({'split':i-1,'old_bpm':old_bpm,'fitted_bpm':ph[4],
                    'float32_endpoint_ulp_ms':ulp,'removed_overlap_ms':overlap,'remaining_gap_ms':h[6]})
        assert i==0 or h[6]>=-.001,('Native split overlaps',{'split':i,'start_beat':str(a),'end_beat':str(z),
            'rows':n,'start_ms':h[3],'previous_end_ms':previous_end,'overlap_ms':-h[6]})
        begin=speeds.value(a);end=speeds.value(z,left=True);smooth=abs(end-begin)>1e-10
        if smooth and pause_gap:
            raise ValueError('Native ramp across pause requires explicit freeze mapping')
        target=end if smooth else begin
        h[7]=-target if pause_gap else target
        h[5]=at(scrolls,a)/r
        # E.build_nx emits only 0x400 plus its placement RPB; discard
        # transient high RPB bits before emitting bounded final native flags.
        h[8]=0x400|(0x10000 if smooth else 0)
        # A 48-row authored subdivision is a placement grid, not a request
        # for48 judged hold checkpoints. Keep every row/flag/time/distance,
        # with an equivalent NX BPM/RPB pair bounded by24. h5 retains the
        # original visual beat distance per row; tick masks use source beats.
        native_r=min(r,24)
        if native_r!=r:
            old_bpm=h[4];h[4]*=r/native_r;h[8]=(h[8]&~255)|native_r
            grid_compensations.append({'split':i,'source_grid_rpb':r,'nx_rpb':native_r,
                'source_bpm':old_bpm,'nx_bpm':h[4],'row_duration_ms':60000/old_bpm/r,
                'unchanged_visual_distance_per_row':h[5]})
        if native_r==r:h[8]=(h[8]&~255)|native_r
        h[4]=float32(h[4])
        split['head']=tuple(h)
        previous_end=h[3]+n*60000/h[4]/native_r
        previous_source_end=source_start_ms+n*60000/clock.bpm(a)/r
        curves.append({'start_beat':str(a),'end_beat':str(z),'speed_start':begin,'speed_end':end,
            'smooth':smooth,'scroll_ratio':at(scrolls,a),'judge_ticks_per_beat':int(at(ticks,a)),
            'source_gap_before_ms':source_gap,'serialized_gap_before_ms':h[6]})
        for j,row in enumerate(split['rows']):
            if row is None:continue
            beat=a+F(j,r);tick=int(at(ticks,beat));judge=tick>0 and (beat*tick).denominator==1
            changed=[]
            for cell in row:
                if cell&255==0x5b:
                    if judge:scored_bodies+=1
                    else:cell=(cell&~255)|0x3b;visual_bodies+=1
                changed.append(cell)
            split['rows'][j]=tuple(changed)
    raw=nx20.build(nx);parsed=nx20.parse(raw)
    actual=sorted((round(v[1],3),v[2],None if v[4] is None else round(v[4],3)) for v in Q.notes_of(parsed))
    desired=sorted((round(v['ms'],3),v['lane'],None if v['tail_ms'] is None else round(v['tail_ms'],3)) for v in notes)
    assert len(actual)==len(desired),'Native attack count changed'
    errors=[]
    for x,y in zip(actual,desired):
        assert x[1]==y[1] and (x[2] is None)==(y[2] is None),'Native panel/hold changed'
        errors.append(abs(x[0]-y[0]))
        if x[2] is not None:errors.append(abs(x[2]-y[2]))
    assert max(errors or [0])<.1,('Native timing changed',max(errors))
    proof={'experimental':True,'promoted':False,'sha256':hashlib.sha256(raw).hexdigest(),
        'source_signature':chart['signature'],'source_file_sha256':chart['source_file_sha256'],
        'native_panels_taps_and_holds_preserved':True,'note_count':len(desired),
        'maximum_onset_or_tail_error_ms':max(errors or [0]),'original_meter':int(float(chart['meter'])),
        'visual_curve_segments':curves,'speed_beat_quantization':speeds.quantization,
        'warp_tail_serialization':warp_tails,
        'placement_grid_compensations':grid_compensations,
        'float32_endpoint_fits':rounding_fits,
        'judged_hold_body_cells':scored_bodies,'visual_nonjudged_hold_body_cells':visual_bodies,
        'native_global_speed_probe_required':True,'native_hold_tick_judgment_probe_required':True,
        'native_scroll_geometry_probe_required':True}
    return raw,proof
