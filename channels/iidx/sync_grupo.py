"""Long-range answer by groups: per delay value, the mean correlation between a movie's cuts and its audio's onsets at each lag. One song is noise; dozens with the same delay show the true shift.
+ lag = the movie's event comes later than its sound in the raw movie. Control: delay 0 must peak at 0. Saves sync_grupo.json (per song correlograms stay in memory only)."""
import json,subprocess,collections
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import numpy as np
H=Path(__file__).resolve().parent;R=30;MAX=10
sel={r['source_folder']:r for r in json.load(open('D:/PIU_INFINITY/channels/selection.json',encoding='utf8'))['records'] if r['channel']=='IIDX'}
ids=[f.stem for f in (H/'cache_cortes').glob('*.npy')]
lags=np.arange(-MAX*R,MAX*R+1)
def one(sid):
    d=np.load(H/'cache_cortes'/f'{sid}.npy').astype(np.float64);e=np.clip(d-np.convolve(d,np.ones(9)/9,'same'),0,None)
    x=np.frombuffer(subprocess.run(['ffmpeg','-v','error','-i',str(H/'canal/songs'/sid/'audio.wav'),'-ac','1','-ar','8000','-f','f32le','-'],capture_output=True).stdout,np.float32)
    hop=8000//R;env=np.sqrt(np.convolve(x**2,np.ones(hop)/hop,'same')[::hop]);a=np.clip(np.diff(env),0,None)
    n=min(len(e),len(a))
    if n<R*20:return None
    p=(e[:n]-e[:n].mean())/(e[:n].std()+1e-9);q=(a[:n]-a[:n].mean())/(a[:n].std()+1e-9);N=2*n;cc=np.fft.irfft(np.fft.rfft(p,N)*np.conj(np.fft.rfft(q,N)),N)/n
    return sid,round(sel[sid]['video_segments'][0]['seconds']*1000),cc[lags%N]
with ThreadPoolExecutor(6) as ex:rows=[r for r in ex.map(one,ids) if r]
g=collections.defaultdict(list)
for sid,dl,c in rows:g[dl].append(c)
print('songs',len(rows));out={}
def report(name,v):
    m=np.mean(v,axis=0);m=m-np.median(m);k=int(np.argmax(m));z=(m[k]-m.mean())/(m.std()+1e-9);top=[round(float(lags[i]/R),2) for i in np.argsort(m)[::-1][:5]];print(name,'n',len(v),'peak lag',round(float(lags[k]/R),3),'z',round(float(z),1),'next',top);return float(lags[k]/R),float(z)
report('delay 0',g[0])
for dl,v in sorted(g.items(),key=lambda x:-len(x[1])):
    if dl!=0 and len(v)>=5:out[dl]=report(f'delay {dl}',v)
# all nonzero aligned under each unit hypothesis: shift each correlogram by delay*unit, then average
for u in (1,2,5,10,1000/60,20,1000/30,50):
    for sign in (1,-1):
        st=[]
        for sid,dl,c in rows:
            if abs(dl)<20:continue
            s=int(round(sign*dl*u/1000*R))
            if abs(s)>MAX*R:continue
            st.append(np.roll(c,-s))
        m=np.mean(st,axis=0);m=m-np.median(m);k=int(np.argmax(m));print(f'unit {u:6.2f} {sign:+d}: n {len(st)} value at 0 lag {float(m[len(m)//2]):.4f}  peak {float(lags[k]/R):+.2f} s value {float(m[k]):.4f}',flush=True)
(H/'sync_grupo.json').write_text(json.dumps({str(k):v for k,v in out.items()}))
