"""EZ2ON (ez2pattern) chart -> reference NX on Song.mp3's timeline, same source_grid as DJMAX / SSS.
Original ticks (60 per beat) and BPM changes; 'long' notes = holds; nothing is added or moved.
offset: time in Song.mp3 = chart time_ms + lag_ms (sync.json) -> beat 0 at lag_ms."""
from fractions import Fraction as F
from collections import defaultdict
from pathlib import Path
import sys,json,inspect,hashlib
sys.dont_write_bytecode=True
B=Path(r'D:\Pump It Up Data\PIU');sys.path[:0]=[str(B/'anime_channel_dng'),str(B)]
import nx_adapter as A
code=inspect.getsource(A.source_grid).split('\n    actual=sorted')[0]+'\n    return nx,musical\n';env=dict(A.__dict__);exec(compile(code,'<EZ2_chart_grid>','exec'),env)
MODE={4:'dance-single',5:'pump-single',6:'dance-solo',8:'dance-double'}

def reference(js,lag_ms):
    d=json.loads(Path(js).read_text(encoding='utf8'));tpb=d['ticks_per_beat'];beat=lambda t:F(str(t))/tpb   # some files store ticks as floats (10800.0)
    cells=defaultdict(dict);holds=0
    for n in d['notes']:
        b=beat(n['abs_tick']);lane=n['lane']-1
        if lane in cells[b]:continue   # same lane twice at one tick: one note
        if n['type']=='long' and n['end']['abs_tick']>n['abs_tick']:
            e=beat(n['end']['abs_tick'])
            if lane in cells[e]:cells[b][lane]='1';continue   # tail on the next note: tap
            cells[b][lane]='2';cells[e][lane]='3';holds+=1
        else:cells[b][lane]='1'
    bpms=[(0,d['initial_bpm'])]+[(c['abs_tick'],c['bpm']) for c in d['bpm_changes'] if c['abs_tick']>0]
    chart=dict(mode=MODE[d['keys']],meter=str(d['level']),rows=[(str(b),''.join(cells[b].get(l,'0') for l in range(d['keys']))) for b in sorted(cells)],
               timing={'BPMS':','.join(f'{beat(t)}={v:.4f}' for t,v in bpms),'OFFSET':f'{-lag_ms/1000:.6f}'})
    nx,_=env['source_grid'](chart);raw=A.nx20.build(nx)
    return raw,dict(mode=d['mode'],difficulty=d['difficulty'],ez2_level=d['level'],notes=len(d['notes']),holds=holds,bpms=bpms)
