"""Video cuts against the beat grid, for constant-tempo IIDX songs: cuts are edited on the beat, so their phase in the beat says where the movie sits against the audio.
Per song: phase (s, in +-T/2) and lock R. The frame differences stay in cache_cortes/ so later tests need no decoding. Writes sync_fase.json. + phase = cuts late against the beat in the raw movie."""
import json,subprocess,sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import numpy as np
H=Path(__file__).resolve().parent;R=30;CACHE=H/'cache_cortes';CACHE.mkdir(exist_ok=True)
sel={r['source_folder']:r for r in json.load(open('D:/PIU_INFINITY/channels/selection.json',encoding='utf8'))['records'] if r['channel']=='IIDX'}
def diffs(sid):
    c=CACHE/f'{sid}.npy'
    if c.exists():return np.load(c)
    m=sel[sid]['video_segments'][0]['file']
    v=subprocess.run(['ffmpeg','-v','error','-i',m,'-vf',f'fps={R},scale=32:24,format=gray','-f','rawvideo','-'],capture_output=True,timeout=900).stdout
    fr=np.frombuffer(v,np.uint8);fr=fr[:len(fr)//768*768].reshape(-1,768).astype(np.float32);d=np.abs(np.diff(fr,axis=0)).mean(axis=1).astype(np.float32);np.save(c,d);return d
def cuts(d):
    """Frames that jump far above their neighbourhood (hard cuts, not motion)."""
    if len(d)<R*5:return np.array([])
    k=15;med=np.array([np.median(d[max(0,i-k):i+k+1]) for i in range(len(d))]);mad=np.median(np.abs(d-med))+1e-3
    peak=(d>med+8*mad)&(d>6)&(d>=np.roll(d,1))&(d>=np.roll(d,-1));return np.nonzero(peak)[0]+1
def one(sid):
    r=sel[sid]
    try:
        res=json.loads((H/'canal/songs'/sid/'result.json').read_text(encoding='utf8'));ref=max(res['refs'],key=lambda x:x['heads']);bp=ref['bpms']
        if len({round(b,2) for _,b in bp})!=1:return dict(id=sid,skip='tempo changes')
        T=60/bp[0][1];d=diffs(sid);c=cuts(d)
        if len(c)<12:return dict(id=sid,skip='few cuts',n=int(len(c)))
        t=c/R-ref['offset_s'];z=np.exp(2j*np.pi*t/T);m=z.mean();ph=float(np.angle(m))*T/(2*np.pi)
        # half-beat cuts are common: the same at T/2 when it locks better
        return dict(id=sid,title=r['title'],delay=int(round(r['video_segments'][0]['seconds']*1000)),T=T,n=int(len(c)),R=float(abs(m)),phase=ph)
    except Exception as e:return dict(id=sid,skip=repr(e)[:120])
def main():
    ids=sorted(sel,key=int);print(len(ids),flush=True);out=[]
    with ThreadPoolExecutor(6) as ex:
        for k,x in enumerate(ex.map(one,ids)):
            out.append(x)
            if k%100==0:print(k,flush=True)
    (H/'sync_fase.json').write_text(json.dumps(out,ensure_ascii=False,indent=0));print('FASE_DONE',len(out),flush=True)
if __name__=='__main__':main()
