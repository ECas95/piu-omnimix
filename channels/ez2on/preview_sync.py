"""BGA <-> Song.mp3 through the game's own preview pair (Preview.webm is cut from BGA.mp4, PreviewAudio.ogg from the
song; the select screen plays them together):
  v = where Preview.webm starts inside BGA.mp4      (frame matching, 32x18 gray @ 20 fps)
  a = where PreviewAudio.ogg starts inside Song.mp3 (8-band onset envelopes)
  -> BGA time 0 plays at Song.mp3 time a - v."""
import measure_sync as M,numpy as np,subprocess,os,sys,json
def frames(f,fps=20,w=64,h=36):
    raw=subprocess.check_output([M.FF,'-v','error','-i',f,'-an','-vf',f'fps={fps},scale={w}:{h},format=gray','-f','rawvideo','-'])
    return np.frombuffer(raw,np.uint8).reshape(-1,h*w).astype(np.float32)
def locate_video(pre,bga,fps=20):
    P=frames(pre,fps);B=frames(bga,fps);n=min(len(P),fps*8);P=P[:n]
    P=P-P.mean(1,keepdims=True);B=B-B.mean(1,keepdims=True)
    err=np.array([np.abs(B[i:i+n]-P).mean() for i in range(len(B)-n)]);i=int(err.argmin());s=np.sort(err)
    second=err[np.abs(np.arange(len(err))-i)>fps].min()
    return i/fps,float(err[i]),float(second)
def logspec(f,nb=64):
    x=M.pcm(f);n=(len(x)-1024)//M.HOP;idx=np.arange(1024)[None,:]+M.HOP*np.arange(n)[:,None]
    S=np.abs(np.fft.rfft(x[idx]*np.hanning(1024),axis=1));e=np.unique(np.geomspace(2,512,nb+1).astype(int))
    return np.log1p(1000*np.stack([S[:,a:b].mean(1) for a,b in zip(e,e[1:])],1))
def locate_audio(pre,song,maxs=8):
    A=logspec(song);P=logspec(pre);q=int(M.FPS*1);m=int(min(len(P)-2*q,M.FPS*maxs));P=P[q:q+m]   # skip a possible fade-in / fade-out
    P=P-P.mean(0);P/=np.linalg.norm(P)+1e-9;n=len(A)-m
    num=np.zeros(n);[num.__iadd__(np.convolve(A[:,k],P[::-1,k],'valid')[:n]) for k in range(A.shape[1])]
    c=np.cumsum(np.vstack([np.zeros((1,A.shape[1])),A]),0);c2=np.cumsum(np.vstack([np.zeros((1,A.shape[1])),A*A]),0)
    mu=(c[m:m+n]-c[:n])/m;var=((c2[m:m+n]-c2[:n])-m*mu*mu).sum(1);ncc=num/np.sqrt(var+1e-9)
    i=int(ncc.argmax());second=ncc[np.abs(np.arange(n)-i)>M.FPS*0.5].max()
    return (i-q)/M.FPS,float(second/ncc[i])
def measure(folder):
    d=os.path.join(M.O,folder);bga=next(os.path.join(d,x) for x in ('BGA.mp4','BGA.webm') if os.path.exists(os.path.join(d,x)))
    v,ev,ev2=locate_video(os.path.join(d,'Preview.webm'),bga);a,ar=locate_audio(os.path.join(d,'PreviewAudio.ogg'),os.path.join(d,'Song.mp3'))
    return dict(video_at=round(v,3),video_err=round(ev,2),video_err_2nd=round(ev2,2),audio_at=round(a,3),audio_2nd=round(ar,3),start_s=round(a-v,3))
if __name__=='__main__':
    for s in sys.argv[1:]:print(s,measure(s))
