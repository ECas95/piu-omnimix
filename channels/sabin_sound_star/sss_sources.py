"""SSS Percussion references (user 2026-10-29): every Percussion chart (*_3*.sss, 6 pads) of every song with a BGA
-> one 6-lane reference NX through the same source_grid DJMAX used (original ticks/BPMs, holds = notes longer than
the 6-tick tap envelope). Output: refs/<song>/<chart>.NX + refs.json. Nothing is added or moved."""
from pathlib import Path
from fractions import Fraction as F
from collections import defaultdict
import sys,json,inspect,hashlib,struct,re
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;B=Path(r'D:\Pump It Up Data\PIU')
sys.path[:0]=[str(H),str(B/'anime_channel_dng'),str(B)]
import sss,nx_adapter as A
PADS=[8,9,10,17,18,19]   # 1P Line 6 / Line 7 / Scratch, 2P Line 6 / Line 7 / Scratch = red-green-blue | blue-green-red
code=inspect.getsource(A.source_grid).split('\n    actual=sorted')[0]+'\n    return nx,musical\n';env=dict(A.__dict__);exec(compile(code,'<SSS_chart_grid>','exec'),env)

def reference(path):
    c=sss.parse(path);tr=c['tracks'];tobeat,bpms,tpb=sss.timing(c)
    cells=defaultdict(dict);holds=heads=0
    for lane,t in enumerate(PADS):
        for p,k,a in tr[t][1]:
            if k!=1:continue
            length=struct.unpack_from('<H',a,4)[0];beat=tobeat(p)
            if lane in cells[beat]:continue   # same pad twice at one tick in the original: one note
            heads+=1;held=length>6;cells[beat][lane]='2' if held else '1'
            if held:
                end=tobeat(p+length)
                if lane in cells[end]:cells[beat][lane]='1';continue   # tail lands on the next note: tap
                cells[end][lane]='3';holds+=1
    chart=dict(mode='dance-solo',meter='20',rows=[(str(b),''.join(cells[b].get(l,'0') for l in range(6))) for b in sorted(cells)],
               timing={'BPMS':','.join(f'{tobeat(at)}={bpm:.4f}'.rstrip('0').rstrip('.') for at,bpm in bpms),'OFFSET':'0'})
    nx,_=env['source_grid'](chart);return A.nx20.build(nx),dict(heads=heads,holds=holds,bpms=[(p,round(b,4)) for p,b in bpms],ticks_per_beat=str(tpb))

def main():
    inv=json.loads((H/'inventory.json').read_text());out=[];err=[]
    for s in inv:
        for f in sorted((sss.GAME/'data'/s['song']).glob('*.sss')):
            name=f.stem.split('_',1)[-1]
            if not name.lower().startswith('3'):continue
            try:
                raw,info=reference(f);p=H/'refs'/s['song']/(name+'.NX');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
                out.append(dict(song=s['song'],chart=name,source=str(f),nx=str(p),sha256=hashlib.sha256(raw).hexdigest(),**info))
            except Exception as e:err.append(dict(song=s['song'],chart=name,error=repr(e)[:300]))
    (H/'refs.json').write_text(json.dumps(dict(records=out,errors=err),indent=1));print('SSS_REFS',len(out),'errors',len(err),err[:5])
if __name__=='__main__':main()
