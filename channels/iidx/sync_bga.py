"""Measures, per IIDX song, the lag between the raw movie's scene changes and the audio's onsets (+ = picture late in the raw movie: the same scene comes l seconds after its sound).
Evidence for the unit of bga_delay. Writes sync_bga.json. usage: sync_bga.py [--all]"""
import json,subprocess,sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import numpy as np
H=Path(__file__).resolve().parent;R=30;MAX=8
sel={r['source_folder']:r for r in json.load(open('D:/PIU_INFINITY/channels/selection.json',encoding='utf8'))['records'] if r['channel']=='IIDX'}
def one(sid):
    r=sel[sid];m=r['video_segments'][0]['file'];au=H/'canal/songs'/sid/'audio.wav'
    v=subprocess.run(['ffmpeg','-v','error','-i',m,'-vf',f'fps={R},scale=32:24,format=gray','-f','rawvideo','-'],capture_output=True).stdout
    fr=np.frombuffer(v,np.uint8);fr=fr[:len(fr)//768*768].reshape(-1,768).astype(np.float32);vd=np.abs(np.diff(fr,axis=0)).mean(axis=1)
    x=np.frombuffer(subprocess.run(['ffmpeg','-v','error','-i',str(au),'-ac','1','-ar','8000','-f','f32le','-'],capture_output=True).stdout,np.float32)
    hop=8000//R;env=np.sqrt(np.convolve(x**2,np.ones(hop)/hop,'same')[::hop]);ad=np.clip(np.diff(env),0,None)
    n=min(len(vd),len(ad));
    if n<R*10:return dict(id=sid,error='short')
    a=(vd[:n]-vd[:n].mean())/(vd[:n].std()+1e-9);b=(ad[:n]-ad[:n].mean())/(ad[:n].std()+1e-9)
    N=2*n;cc=np.fft.irfft(np.fft.rfft(a,N)*np.conj(np.fft.rfft(b,N)),N)/n   # cc[l] = sum a[i+l] b[i]
    lags=np.arange(-MAX*R,MAX*R+1);vals=cc[lags%N];k=int(np.argmax(vals));second=np.sort(vals)[-int(R*.5)] if len(vals)>R else 0
    return dict(id=sid,title=r['title'],delay=int(round(r['video_segments'][0]['seconds']*1000)),lag=float(lags[k]/R),score=float(vals[k]),med=float(np.median(vals)),spread=float(vals.std()),peak=float((vals[k]-np.median(vals))/(vals.std()+1e-9)),movie_s=len(fr)/R,audio_s=len(x)/8000,bpm=r['bpm'])
def main():
    ids=sorted(sel,key=int)
    if '--all' not in sys.argv:
        nz=[i for i in ids if abs(sel[i]['video_segments'][0]['seconds'])>0];z=[i for i in ids if i not in nz];ids=nz+z[::8]
    print('songs',len(ids),flush=True);out=[]
    with ThreadPoolExecutor(8) as ex:
        for k,x in enumerate(ex.map(one,ids)):
            out.append(x)
            if k%50==0:print(k,flush=True)
    (H/'sync_bga.json').write_text(json.dumps(out,ensure_ascii=False,indent=0));print('SYNC_DONE',len(out),flush=True)
if __name__=='__main__':main()
