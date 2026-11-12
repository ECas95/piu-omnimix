import numpy as np,tm
AR=500
def onset(x):
    m=x.astype(np.float32).mean(1);m=m[:len(m)//88*88].reshape(-1,88);e=np.sqrt((m**2).mean(1)+1e-9)   # 2 ms frames (44100/88 ~ 501 Hz)
    on=np.clip(np.diff(e),0,None);return on/(on.mean()+1e-9)
res=[]
for s in tm.songs():
    on=onset(tm.audio(s['tmm']));R=tm.rows(s['stp']);t=[];rl=[]
    for i,(ms,bpm,a,b) in enumerate(R):
        if any(a[c] for c in (2,20,38)) or any(b[c] for c in (2,20,38)):t.append(ms)
    t=np.array(t,float);row=30000/R[0][1];sc=[]
    for off in range(0,400,2):
        i=np.rint((t+off)*44100/88/1000).astype(int);i=i[i<len(on)];sc.append(on[i].mean())
    k=int(np.argmax(sc));res.append((k*2-row));print(s['index'],s['title'][:18].ljust(18),'notes',len(t),'last note s',round(t.max()/1000,1),'best ms',k*2,'row ms',round(row,1),'best-row',round(k*2-row,1),'score',round(sc[k],2),'at row',round(sc[int(row/2)],2))
print('median best-row',np.median(res))
