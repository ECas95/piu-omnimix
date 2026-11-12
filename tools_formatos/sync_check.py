"""Per classic version: first-note ms of our converted charts vs PRIME's chart with the same note count (same song id)."""
import sys,json,re,statistics as st,collections
sys.path[:0]=[r'D:\Pump It Up Data\PIU\final_generation_v362',r'D:\Pump It Up Data\PIU\final_generation_v362\vendor_v363',r'E:\Pump It Up Data\PIU',r'E:\Pump It Up Data\PIU\nsde_channel']
from hybrid import nx20,sources
from current_parent import load
import build_classic as B
P,game=load()
first=lambda b:(lambda ev:(sum(len(e['lanes']) for e in ev),ev[0]['ms']))(sources.events_of(nx20.parse(b))[1])
prime=collections.defaultdict(dict)
for x in game.index.files:
    m=re.match(rb'/D/([0-9A-F]{3,4})/\1/([^/]+)\.NX$',x)
    if m and not m[2].startswith(b'REV_'):
        try:n,t=first(game.get(x.decode()));prime[m[1].decode()][n]=t
        except Exception:pass
res=collections.defaultdict(list)
for v in ('A00','850','800','750','700','650','600','550','500','450','400'):
    files=[n for n,*_ in B.fs.listdir(f'{B.root(v)}/STEP')]
    for sid in sorted({re.split(r'[._]',f)[0] for f in files}):
        if sid not in prime:continue
        try:cs=B.charts_of(v,[f for f in files if re.split(r'[._]',f)[0]==sid])
        except Exception:continue
        for c in cs:
            r=B.to_nx(c)
            if not r:continue
            n,t=first(r[0])
            if n in prime[sid]:res[v].append((prime[sid][n]-t,sid))
for v,d in res.items():
    ds=[x for x,_ in d];print(v,len(d),'median',round(st.median(ds)),'p10/p90',[round(q) for q in st.quantiles(ds,n=10)[::8]] if len(ds)>2 else ds,'worst',sorted(d,key=lambda x:-abs(x[0]))[:3])
