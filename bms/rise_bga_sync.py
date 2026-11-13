"""RISE BGA start from the game's own preview clips (Previews/preview.mp3 + preview.webm come from the same moment of the song):
  a = where preview.mp3 sits inside Audio/tema.mp3        (cross-correlation of the audio)
  v = where preview.webm's frames sit inside BGA/bga.webm (frame matching on 64x36 gray frames)
  -> BGA frame 0 plays at audio time (a - v).  Output: bga_sync.json  {song: {a, v, bga_start_s, corr_a, corr_v}}"""
import sys,json,subprocess,glob,os
import numpy as np
from concurrent.futures import ProcessPoolExecutor
sys.dont_write_bytecode=True
SRC=r'D:\PIU_PRESERVADO\ORIGINALES\RISE';FF='ffmpeg'
SR=11025
def pcm(path):
    raw=subprocess.run([FF,'-v','error','-i',path,'-vn','-ac','1','-ar',str(SR),'-f','f32le','-'],capture_output=True,check=True).stdout
    return np.frombuffer(raw,np.float32)
def frames(path,fps=20,w=64,h=36):
    raw=subprocess.run([FF,'-v','error','-i',path,'-an','-vf',f'fps={fps},scale={w}:{h},format=gray','-f','rawvideo','-'],capture_output=True,check=True).stdout
    a=np.frombuffer(raw,np.uint8);n=len(a)//(w*h);return a[:n*w*h].reshape(n,w*h).astype(np.float32)
def audio_offset(song,prev):
    # envelope cross-correlation (hop 10 ms) then refinement on the waveform
    hop=SR//100
    def env(x):
        n=len(x)//hop;e=np.sqrt((x[:n*hop].reshape(n,hop)**2).mean(1));return (e-e.mean())/(e.std()+1e-9)
    es,ep=env(song),env(prev);n=len(es)+len(ep)
    c=np.fft.irfft(np.fft.rfft(es,2*n)*np.conj(np.fft.rfft(ep,2*n)))[:len(es)-len(ep)+1]
    k=int(np.argmax(c));corr=float(c[k]/len(ep))
    lo=max(0,(k-5)*hop);seg=song[lo:lo+len(prev)+12*hop];m=len(seg)+len(prev)
    c2=np.fft.irfft(np.fft.rfft(seg,2*m)*np.conj(np.fft.rfft(prev,2*m)))[:len(seg)-len(prev)+1]
    return (lo+int(np.argmax(c2)))/SR,corr
def video_offset(bga,prev):
    def norm(f):
        f=f-f.mean(1,keepdims=True);return f/(np.linalg.norm(f,axis=1,keepdims=True)+1e-6)
    B,P=norm(bga),norm(prev);n=len(P);best=(-1,0)
    # mean per-frame correlation along every diagonal (FFT over frames is overkill: ~2k x 200 frames)
    G=B@P.T          # (nb, np) frame similarities
    for off in range(0,len(B)-n+1):
        s=float(np.mean(np.diagonal(G,-off)[:n]) ) if off<=len(B) else -1
        if s>best[0]:best=(s,off)
    return best[1]/20.0,best[0]
def one(name):
    d=os.path.join(SRC,name)
    try:
        song=pcm(d+r'\Audio\tema.mp3');prev=pcm(d+r'\Previews\preview.mp3')
        a,ca=audio_offset(song,prev)
        v,cv=video_offset(frames(d+r'\BGA\bga.webm'),frames(d+r'\Previews\preview.webm'))
        return name,dict(a=round(a,3),v=round(v,3),bga_start_s=round(a-v,3),corr_a=round(ca,3),corr_v=round(cv,3))
    except Exception as e:return name,dict(error=repr(e)[:160])
if __name__=='__main__':
    names=sys.argv[1:] or sorted(os.path.basename(p.rstrip('\\')) for p in glob.glob(SRC+'\\*\\') if os.path.exists(p+'BGA\\bga.webm') and os.path.exists(p+'Previews\\preview.webm'))
    res={}
    out=r'D:\PIU_PRESERVADO\rise_bga_sync.json'
    if os.path.exists(out):res=json.load(open(out))
    todo=[n for n in names if n not in res]
    with ProcessPoolExecutor(3) as ex:
        for n,r in ex.map(one,todo):
            res[n]=r;print(n,r,flush=True)
            json.dump(res,open(out,'w'),indent=1,ensure_ascii=False)
    print('DONE',len(res))
