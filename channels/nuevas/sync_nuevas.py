"""Sync review of the new songs. Chart: mean audio onset on the note times at each small lag (0 = the chart sits on the sound). Video: cuts against audio onsets at each lag, with the movie placed where it will play
(0 = the movie sits on the sound). Writes sync_nuevas.json + SYNC_REVISION.csv. Only measures; corrections are decided from the report."""
import json,subprocess,sys,csv
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import numpy as np
H=Path(__file__).resolve().parent;B=Path('D:/Pump It Up Data/PIU');sys.path[:0]=[str(B/'anime_channel_dng/engine'),str(B)]
sys.dont_write_bytecode=True
import nx20,quality_charting as Q
R=30;MAX=8;AR=200
def pcm(p):return np.frombuffer(subprocess.run(['ffmpeg','-v','error','-i',str(p),'-ac','1','-ar','8000','-f','f32le','-'],capture_output=True,timeout=900).stdout,np.float32)
def chart_lag(x,paths):
    """Best lag inside +-60 ms per chart, median over the charts: wider windows pick off-beat peaks (a 16th at 180 BPM is 83 ms) in dense charts."""
    hop=8000//AR;env=np.sqrt(np.convolve(x**2,np.ones(hop)/hop,'same')[::hop]);on=np.clip(np.diff(env),0,None);on=on/(on.mean()+1e-9);ls=np.arange(-12,13);best=[];sc0=[]
    for p in paths:
        notes=sorted({n[1] for n in Q.notes_of(nx20.parse(Path(p).read_bytes()))})
        if len(notes)<20:continue
        t=np.array(notes)/1000;sc=[]
        for l in ls:
            i=np.rint(t*AR).astype(int)+l;i=i[(i>=0)&(i<len(on))];sc.append(on[i].mean())
        k=int(np.argmax(sc));best.append(int(ls[k]*1000/AR));sc0.append((sc[k],sc[12]))
    if not best:return None
    return dict(lag_ms=int(np.median(best)),score=round(float(np.mean([a for a,_ in sc0])),2),at0=round(float(np.mean([b for _,b in sc0])),2),per_chart=best)
def video_lag(x,v,start):
    d=subprocess.run(['ffmpeg','-v','error','-i',v,'-vf',f'fps={R},scale=32:24,format=gray','-f','rawvideo','-'],capture_output=True,timeout=1200).stdout
    fr=np.frombuffer(d,np.uint8);fr=fr[:len(fr)//768*768].reshape(-1,768).astype(np.float32);dd=np.abs(np.diff(fr,axis=0)).mean(axis=1).astype(np.float64);e=np.clip(dd-np.convolve(dd,np.ones(9)/9,'same'),0,None)
    hop=8000//R;env=np.sqrt(np.convolve(x**2,np.ones(hop)/hop,'same')[::hop]);a=np.clip(np.diff(env),0,None);n=min(len(e),len(a))
    if n<R*10:return None
    p=(e[:n]-e[:n].mean())/(e[:n].std()+1e-9);q=(a[:n]-a[:n].mean())/(a[:n].std()+1e-9);N=2*n;cc=np.fft.irfft(np.fft.rfft(p,N)*np.conj(np.fft.rfft(q,N)),N)/n;ls=np.arange(-MAX*R,MAX*R+1);v2=cc[ls%N];k=int(np.argmax(v2))
    # raw lag l: the movie's event comes l after its sound in the raw movie; placed at start it plays at l+start
    return dict(raw_lag=round(float(ls[k]/R),2),placed=round(float(ls[k]/R+start),2),z=round(float((v2[k]-v2.mean())/(v2.std()+1e-9)),1),movie_s=round(len(fr)/R,1),audio_s=round(len(x)/8000,1))
def one(f):
    r=json.loads(f.read_text(encoding='utf8'));o=dict(key=r['key'],pack=r['pack'],sub=r.get('sub'),title=r['tags'].get('TITLE','')[:40],start=round(r.get('video_seconds',0),3),how=r.get('video_how'))
    try:
        x=pcm(H/'songs'/r['key']/'audio.wav');good=[c for c in r['refs'] if 'nx' in c];o['chart']=chart_lag(x,[c['nx'] for c in good]);o['video']=video_lag(x,r['video'],r.get('video_seconds',0))
    except Exception as e:o['error']=repr(e)[:200]
    return o
def main():
    fs=sorted((H/'songs').glob('*/result.json'))
    with ThreadPoolExecutor(8) as ex:out=list(ex.map(one,fs))
    (H/'sync_nuevas.json').write_text(json.dumps(out,ensure_ascii=False,indent=0),encoding='utf8')
    with open(H/'SYNC_REVISION.csv','w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow('paquete titulo inicio_video chart_lag_ms chart_score chart_a0 video_lag_colocado z video_s audio_s video_tipo'.split())
        for o in out:
            c=o.get('chart') or {};v=o.get('video') or {};w.writerow([o['sub'] or o['pack'],o['title'],o['start'],c.get('lag_ms'),c.get('score'),c.get('at0'),v.get('placed'),v.get('z'),v.get('movie_s'),v.get('audio_s'),o.get('how')])
    print('SYNC_NUEVAS',len(out),flush=True)
if __name__=='__main__':main()
