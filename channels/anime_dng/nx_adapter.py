"""StepMania -> NX timing; native Pump placement stays exact, DDR feeds V5."""
import contextlib, hashlib, math, sys
from fractions import Fraction as F
from common import ROOT
sys.path[:0]=[str(ROOT/'engine'),str(ROOT.parent)]
import nx20, quality_charting as Q
import ez2_convert as E
import simfile as SM

def native_source_cells(chart,notes,clock):
    """Place pre-warp hold tails at the equivalent-time warp exit.

    The frozen serializer skips all cells inside a warp, including valid tails
    of holds that began before it. Relocate only those releases, keeping the
    exact original panel and millisecond timing; source rows remain unchanged.
    """
    valid_tails={(F(n['tail_beat']),n['lane']) for n in notes if n['tail_beat'] is not None}
    source=[];repairs=[]
    for b,row in chart['rows']:
        beat=F(b)
        for lane,ch in enumerate(row):
            if ch not in '1234':continue
            out=beat
            if ch=='3' and (beat,lane) in valid_tails:
                for a,z in clock.warps:
                    if a<=out<z:out=z
                if out!=beat:
                    assert abs(clock.seconds(out)-clock.seconds(beat))<1e-8,'Warp-tail release time changed'
                    repairs.append({'lane':lane,'authored_tail_beat':str(beat),'serialized_tail_beat':str(out),
                        'unchanged_release_ms':clock.seconds(beat)*1000})
            source.append((out,lane,ch))
    cells={}
    for beat,lane,ch in source:
        if any(a<=beat<z for a,z in clock.warps):continue
        key=(beat,lane)
        assert key not in cells,('Native cells collide at warp exit',key,cells.get(key),ch)
        cells[key]=ch
    return sorted(source,key=lambda n:(n[0],n[1])),repairs

def native_nx(chart, seconds):
    cols=SM.COLS[chart['mode']]
    if cols not in (5,10):raise ValueError('Native Pump mode needs explicit mapping: '+chart['mode'])
    for field in ('SCROLLS','SPEEDS'):
        if any(v!=1 for _,v in SM.pairs(chart['timing'].get(field,''))):
            raise ValueError('Preserve native Pump '+field+' through dedicated gimmick import; review required')
    notes,_=SM.events(chart,native=True);clock=SM.Clock(chart['timing'])
    source,warp_tails=native_source_cells(chart,notes,clock)
    level=int(float(chart['meter']));assert 1<=level<=99,('Native meter',chart['meter'])
    raw=E.build_nx(source,clock.bpms,dict(clock.stops),dict(clock.delays),-clock.offset*1000,level,cols,seconds*1000,
                  warps={a:b-a for a,b in clock.warps})
    nx=nx20.parse(raw);end=0.;negative=[]
    for i,s in enumerate(nx['splits']):
        h=list(s['head']);h[6]=h[3]-end
        if i and h[6]<-.001:negative.append(i)
        end=h[3]+len(s['rows'])*60000/h[4]/(h[8]&255);s['head']=tuple(h)
    if negative:raise ValueError('Overlapping native timing splits '+str(negative))
    raw=nx20.build(nx);nx=nx20.parse(raw)
    actual=sorted((round(n[1],3),n[2],None if n[4] is None else round(n[4],3)) for n in Q.notes_of(nx))
    desired=sorted((round(n['ms'],3),n['lane'],None if n['tail_ms'] is None else round(n['tail_ms'],3)) for n in notes)
    assert len(actual)==len(desired),('Native note count changed',len(actual),len(desired))
    errors=[]
    for a,b in zip(actual,desired):
        assert a[1]==b[1] and (a[2] is None)==(b[2] is None),'Native panel/hold changed'
        errors.append(abs(a[0]-b[0]))
        if a[2] is not None:errors.append(abs(a[2]-b[2]))
    assert max(errors or [0])<.1,('Native timing changed',max(errors))
    return raw,{'source_signature':chart['signature'],'source_file_sha256':chart['source_file_sha256'],
                'note_count':len(desired),'native_panels_preserved':True,'native_taps_and_holds_preserved':True,
                'maximum_onset_or_tail_error_ms':max(errors or [0]),'original_meter':level,
                'sha256':hashlib.sha256(raw).hexdigest(),'warp_tail_serialization':warp_tails}

def source_grid(chart):
    notes,_=SM.events(chart);clock=SM.Clock(chart['timing'])
    if not notes:raise ValueError('No attacks in source')
    cells={};holds=[]
    for n in notes:
        a=F(n['beat']);key=(a,n['lane'])
        if key in cells:raise ValueError('Two source attacks share one panel')
        cells[key]=Q.HEAD if n['tail_beat'] else Q.TAP
        if n['tail_beat']:
            b=F(n['tail_beat']);holds.append((a,b,n['lane']))
    for a,b,lane in holds:
        if (b,lane) in cells:raise ValueError('Source tail and new attack overlap; needs explicit review')
        cells[b,lane]=Q.TAIL
    important={b for b,l in cells};first=min(F(0),min(important));last=max(important)+4
    boundaries=sorted({first,last}|important|{b for b,_ in clock.bpms+clock.stops+clock.delays if first<b<last}
                      |{b for a,z in clock.warps for b in (a,z) if first<b<last})
    cols=max(5,SM.COLS[chart['mode']]);splits=[];musical=[];end=0.;bridges=[]
    for a,b in zip(boundaries,boundaries[1:]):
        at=clock.seconds(a)*1000;until=clock.seconds(b)*1000;elapsed=until-at
        if elapsed<=1e-8:
            if any(beat==a and value in (Q.TAP,Q.HEAD) for (beat,lane),value in cells.items()):
                raise ValueError('Judgable attacks at collapsed warp boundary')
            continue
        delta=b-a;exact=[r for r in range(1,25) if (delta*r).denominator==1]
        r=min(exact) if exact else 24
        count=max(1,int(delta*r));bpm=clock.bpm(a);nominal=count*60000/bpm/r;scroll=1.
        if nominal>elapsed+1e-6:
            bpm=count*60000/elapsed/r;scroll=clock.bpm(a)/bpm
            bridges.append({'start_beat':str(a),'end_beat':str(b),'start_ms':at,'end_ms':until,'effective_bpm':bpm,'visual_speed_compensation':scroll})
        rows=[]
        for j in range(count):
            # The first row is exact. Extra rows are body/filler only; no attack is snapped.
            beat=a+delta*F(j,count)
            row=[cells.get((a,lane),0) if j==0 else 0 for lane in range(cols)]
            for h,t,lane in holds:
                if h<beat<t and not row[lane]:row[lane]=Q.BODY
            rows.append(tuple(row) if any(row) else None);musical.append(float(beat))
        h=(0,0,1,at,bpm,1/r,at-end,scroll,0x400|r,0,count)
        if splits and h[6]<-.001:raise ValueError('Negative split overlap in exact source adapter')
        splits.append({'head':h,'rows':rows});end=at+count*60000/bpm/r
    nx=nx20.parse(nx20.build({'cols':cols,'unk':0,'tags':[(1000,1),(1001,1)],'splits':splits,'pool':b''}))
    actual=sorted(n[1] for n in Q.notes_of(nx));wanted=sorted(n['ms'] for n in notes)
    assert len(actual)==len(wanted),('Source attacks lost',len(actual),len(wanted))
    error=max(abs(a-b) for a,b in zip(actual,wanted));assert error<.1,error
    return nx,musical,{'maximum_tickcount':max(s['head'][8]&255 for s in nx['splits']),
                        'source_attacks':len(notes),'source_distinct_onsets':len(set(wanted)),
                        'maximum_onset_error_ms':error,'tempo_grid_bridges':bridges,'notes_omitted':0,
                        'musical_beat_reference':'original SM beats; explicit split-time residues'}

@contextlib.contextmanager
def musical_grid(beats,reference):
    """Provide SM musical phase to the unchanged algorithm for source/output grids.

    NX stores elapsed-time residues separately. Those are clock offsets/pauses,
    and must not change the musical phrase accent of an imported SM chart.
    """
    original=Q.grid;shape=tuple((s['head'],len(s['rows'])) for s in reference['splits'])
    def grid(nx):
        result=original(nx)
        if tuple((s['head'],len(s['rows'])) for s in nx['splits'])==shape:
            assert len(result)==len(beats)
            return [(beat,*row[1:]) for beat,row in zip(beats,result)]
        return result
    Q.grid=grid
    try:yield
    finally:Q.grid=original
