import json,random,collections,statistics as st
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import lag_banda as L
L.W=125   # +-250 ms
R=[r for r in json.load(open('D:/PIU_INFINITY/channels/selection.json',encoding='utf8'))['records'] if r['channel']=='EZ2ON'];random.seed(2);S=random.sample(R,60)
print({k:str(v)[:70] for k,v in S[0].items() if k in('source','source_group','source_folder','audio','video_policy')})
def one(r):
    bb=L.onset(L.pcm(r['audio']));o=[]
    for k in sorted([k for k in r['charts'] if k.get('nx')],key=lambda k:k.get('level',0))[:3]:
        n=sorted({q[1] for q in L.Q.notes_of(L.nx20.parse(Path(k['nx']).read_bytes()))})
        if len(n)<20:continue
        ls,sc=L.curve(bb,np.array(n)/1000);m=int(np.argmax(sc));o.append((int(ls[m]),round(float(sc[m]),1),round(float(sc[125]),1)))
    return r['title'][:22],r.get('bpm'),r.get('source_group'),o
with ThreadPoolExecutor(6) as e:out=list(e.map(one,S))
for x in out[:24]:print(x)
b=[st.median([y[0] for y in x[3]]) for x in out if x[3]];print(sorted(collections.Counter(20*round(y/20) for y in b).items()));print(collections.Counter(x[2] for x in out))
