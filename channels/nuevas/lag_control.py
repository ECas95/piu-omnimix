"""Control for lag_banda: IIDX and EZ2ON charts come from keysounded originals, so their notes sit on the sound. Same measure, gives the method's bias and spread."""
import json,random,statistics as st,collections
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import lag_banda as L
R=json.load(open('D:/PIU_INFINITY/channels/selection.json',encoding='utf8'))['records'];random.seed(1);S=[]
for c in ('IIDX','EZ2ON'):S+=[(c,r) for r in random.sample([r for r in R if r['channel']==c],40)]
def one(x):
    c,r=x;a=r['audio'];ch=r['charts'] if isinstance(r['charts'],list) else [];ch=[k for k in ch if k.get('nx') and k.get('mode')=='pump-single'] or ch;ch=sorted(ch,key=lambda k:k.get('level',0))[:2]
    try:
        bb=L.onset(L.pcm(a));lo=L.onset(L.pcm(a,'lowpass=f=150,lowpass=f=150'));o=[]
        for k in ch:
            n=sorted({q[1] for q in L.Q.notes_of(L.nx20.parse(Path(k['nx']).read_bytes()))});t=np.array(n)/1000;o.append((L.pk(*L.curve(bb,t))['lag'],L.pk(*L.curve(lo,t))['lag']))
        return c,r['title'][:24],o
    except Exception as e:return c,r['title'][:24],repr(e)[:100]
with ThreadPoolExecutor(6) as ex:out=list(ex.map(one,S))
for c in ('IIDX','EZ2ON'):
    v=[o for k,t,o in out if k==c and isinstance(o,list) and o];b=[x[0][0] for x in v];l=[x[0][1] for x in v];print(c,len(v),'broad median',st.median(b),'hist',sorted(collections.Counter(20*round(y/20) for y in b).items()));print('   bass median',st.median(l),'hist',sorted(collections.Counter(20*round(y/20) for y in l).items()))
print([o for k,t,o in out if not isinstance(o,list)][:3]);print('CONTROL_DONE')
