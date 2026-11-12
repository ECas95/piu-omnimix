"""Isolated authored Pump conversion with explicit pause-time boundaries.

No installed files are changed. Warps and second-based speed ramps stay blocked.
"""
from fractions import Fraction as F
import hashlib,math
import simfile as SM
import native_gimmicks_tick_compensation as D
from nx_adapter import nx20,Q

def convert(c,seconds):
    clock=SM.Clock(c['timing'])
    assert c['mode'] in ('pump-single','pump-double')
    notes,_=SM.events(c,native=True);cols=SM.COLS[c['mode']]
    scrolls=SM.pairs(c['timing'].get('SCROLLS','')) or [(F(0),1.)]
    ticks=SM.pairs(c['timing'].get('TICKCOUNTS','')) or [(F(0),4.)]
    assert all(v>=0 and int(v)==v for b,v in ticks),'Invalid source tick count'
    old=D.canonical_beat;D.canonical_beat=F
    try:speeds=D.Speeds(c['timing'].get('SPEEDS',''))
    finally:D.canonical_beat=old
    points={F(0)}|{b for b,v in clock.bpms+clock.stops+clock.delays+scrolls+ticks}|{b for a,z,x,y in speeds.segments for b in (a,z)}
    points|={b for a,z in clock.warps for b in (a,z)}
    cells={};expected_ticks=[]
    for note in notes:
        a=F(note['beat']);points.add(a);ms=D.float32(note['ms']);key=(ms,note['lane']);assert key not in cells
        cells[key]=nx20.HOLD_START if note['tail_beat'] is not None else nx20.TAP
        if note['tail_beat'] is None:continue
        z=F(note['tail_beat']);points.add(z);key=(D.float32(note['tail_ms']),note['lane']);assert key not in cells;cells[key]=nx20.HOLD_END
        for i,(start,tick) in enumerate(ticks):
            tick=int(tick)
            if tick<=0:continue
            end=ticks[i+1][0] if i+1<len(ticks) else z
            for k in range(math.ceil(max(a,start)*tick),math.ceil(min(z,end)*tick)):
                beat=F(k,tick)
                if a<beat<z and clock.judgable(beat):
                    points.add(beat);expected_ticks.append((note['lane'],clock.seconds(beat)*1000))
    last=max(points);points.add(last+max(F(4),F(str(max(0,seconds-clock.seconds(last))*clock.bpm(last)/60))))
    nodes={}
    def node(ms,beat):nodes.setdefault(D.float32(ms),set()).add(beat)
    for b in sorted(points):node(clock.seconds(b)*1000,b)
    pauses=[]
    for b,value in clock.delays:
        if value:
            end=clock.seconds(b)*1000;node(end-value*1000,b);pauses.append(dict(kind='delay',beat=str(b),start=end-value*1000,end=end))
    for b,value in clock.stops:
        if value:
            start=clock.seconds(b)*1000;node(start+value*1000,b);pauses.append(dict(kind='stop',beat=str(b),start=start,end=start+value*1000))
    grouped=sorted(nodes.items());judged={(lane,D.float32(ms)) for lane,ms in expected_ticks};splits=[];body_times=[];previous_end=0.;curves=[]
    for (ms,beats),(next_ms,next_beats) in zip(grouped,grouped[1:]):
        a=max(beats);z=min(next_beats);assert z>=a
        # A warp changes visible beat distance while consuming no source time.
        # Preserve that displacement in an empty NX split whose bounded high
        # BPM duration is below a float timestamp ulp; the next split resets its
        # start to the original source time. Never add or remove a note row.
        low=min(beats)
        if low<a:
            skipped=sum(clock.integral(max(low,start),min(a,end)) for start,end in clock.warps if max(low,start)<min(a,end))
            assert abs(clock.integral(low,a)-skipped)*1000<.1,'Collapsed boundary spans unaccounted musical time'
            cuts=sorted({low,a}|{b for b,v in scrolls if low<b<a})
            jump=sum(float(y-x)*D.at(scrolls,x) for x,y in zip(cuts,cuts[1:]))
            h=(0,0,1,ms,1.0e12,jump,ms-previous_end,speeds.value(a),0x401,0,1)
            splits.append(dict(head=h,rows=[None]));previous_end=ms
            curves.append(dict(start_ms=ms,end_ms=ms,start_beat=str(low),end_beat=str(a),distance=jump,zero_time_warp=True,speed_target=speeds.value(a)))
        duration=next_ms-ms;assert duration>0
        row=[cells.get((ms,lane),0) for lane in range(cols)]
        for note in notes:
            lane=note['lane']
            if note['tail_ms'] is not None and D.float32(note['ms'])<ms<D.float32(note['tail_ms']) and not row[lane]:
                is_tick=(lane,ms) in judged;row[lane]=nx20.HOLD_BODY if is_tick else 0x33b
                if is_tick:body_times.append((lane,ms))
        bpm=D.ceil_float32(60000/duration)
        while ms+60000/bpm>next_ms:bpm=D.next_float32(bpm)
        begin=speeds.value(a);target=speeds.value(z,left=True);smooth=abs(target-begin)>1e-10
        distance=float(z-a)*D.at(scrolls,a)
        # Pauses consume time with zero musical displacement. Their speed stays
        # at the source beat, rather than advancing a ramp through the pause.
        if a==z:target=begin;smooth=False
        head=(0,0,1,ms,bpm,distance,ms-previous_end,target,0x401|(0x10000 if smooth else 0),0,1)
        splits.append(dict(head=head,rows=[tuple(row) if any(row) else None]));previous_end=ms+60000/bpm
        curves.append(dict(start_ms=ms,end_ms=next_ms,start_beat=str(a),end_beat=str(z),distance=distance,pause=a==z,speed_start=begin,speed_target=target))
    raw=nx20.build(dict(cols=cols,unk=0,tags=[(1000,1),(1001,int(float(c['meter'])))],splits=splits,pool=b''));parsed=nx20.parse(raw)
    actual=sorted((n[1],n[2],n[4]) for n in Q.notes_of(parsed));wanted=sorted((n['ms'],n['lane'],n['tail_ms']) for n in notes)
    assert len(actual)==len(wanted),('Pause source attack count changed',len(actual),len(wanted))
    error=0.
    for x,y in zip(actual,wanted):
        assert x[1]==y[1] and (x[2] is None)==(y[2] is None),'Pause source panel/hold changed';error=max(error,abs(x[0]-y[0]))
        if x[2] is not None:error=max(error,abs(x[2]-y[2]))
    assert error<.1,('Pause source time changed',error)
    expected_ticks.sort();body_times.sort();assert len(body_times)==len(expected_ticks),('Pause hold tick count changed',len(body_times),len(expected_ticks));tick_error=0.
    for x,y in zip(body_times,expected_ticks):assert x[0]==y[0];tick_error=max(tick_error,abs(x[1]-y[1]))
    assert tick_error<.1
    return raw,dict(sha256=hashlib.sha256(raw).hexdigest(),source_signature=c['signature'],source_file_sha256=c['source_file_sha256'],source_heads=len(notes),hold_ticks=len(expected_ticks),maximum_source_attack_tail_error_ms=error,maximum_source_tick_error_ms=tick_error,pauses=pauses,curves=curves,final_rpb=1,source_patterns_preserved=True,promoted=False,native_probes_pending=True,warps=[(str(a),str(z)) for a,z in clock.warps],zero_time_distance_rows=sum(bool(x.get("zero_time_warp")) for x in curves))
