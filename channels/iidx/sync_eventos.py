"""Event types of the IIDX chart files, first occurrences: is there a movie event, and when does the first bar/sound come? usage: sync_eventos.py ids..."""
import sys,struct,collections,os
os.environ['PIU_IIDX_OUT']='canal'
sys.path.insert(0,'D:/PIU_IIDX')
import iidx
for s in sys.argv[1:]:
    sid=int(s);d=iidx.source_dir(sid);raw=(d/f'{sid:05d}.1').read_bytes();ch=iidx.sp_charts(raw);k=max(ch,key=lambda x:sum(e[1]==0 for e in ch[x]));ev=ch[k]
    c=collections.Counter(e[1] for e in ev);first={};last={}
    for t,ty,p,v in ev:
        if t!=2147483647:first.setdefault(ty,(t,p,v));last[ty]=(t,p,v)
    print(sid,'slot',k,'types',dict(sorted(c.items())));print('  first',dict(sorted(first.items())));print('  last',{k:last[k] for k in sorted(last) if k not in(0,2,7)});print('  notes first',[e[0] for e in ev if e[1]==0][:3],'bars',[e[0] for e in ev if e[1]==12][:4],'tempos',[(e[0],e[2],e[3]&0xffff) for e in ev if e[1]==4][:3],'others',[(e[0],e[1],e[2],e[3]) for e in ev if e[1] not in(0,1,2,4,7,12)][:10])
