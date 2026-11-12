"""BGA start through the gameplay VIDEO (the BGA plays full-frame, dimmed, behind the lanes):
  lag_v = where BGA frame 0 appears in the gameplay video (frame matching on the side areas, per-frame normalised)
  E3    = gameplay audio time - Song.mp3 time (sync/<folder>.json)
  -> BGA time 0 plays at Song.mp3 time  lag_v - E3.
Accepted only with a clear match (best diagonal correlation >= 0.6 and second peak (> 1 s away) <= 0.8 of it)."""
import json,os,sys,subprocess,numpy as np
from concurrent.futures import ProcessPoolExecutor,as_completed
sys.path.insert(0,r'D:\EZ2ON_PIU');import measure_sync as M
FPS=20;W,H=64,36
def frames(f,crop=None):
    vf=(f'crop={crop},' if crop else '')+f'fps={FPS},scale={W}:{H},format=gray'
    raw=subprocess.check_output([M.FF,'-v','error','-i',f,'-an','-vf',vf,'-f','rawvideo','-'])
    return np.frombuffer(raw,np.uint8).reshape(-1,H,W).astype(np.float32)
def feat(v):   # side areas only (lanes in the centre, HUD at the bottom): x<38% or x>66%, y<78%
    m=np.zeros((H,W),bool);m[:int(H*.78),:int(W*.38)]=1;m[:int(H*.78),int(W*.66):]=1
    x=v[:,m];x=x-x.mean(1,keepdims=True);return x/(np.linalg.norm(x,axis=1,keepdims=True)+1e-6)
def match(G,B,lo,hi):
    out=[]
    for lag in range(lo,hi):   # gameplay frame t+lag shows BGA frame t
        a=max(0,-lag);b=min(len(B),len(G)-lag)
        out.append((np.einsum('ij,ij->i',G[a+lag:b+lag],B[a:b]).mean() if b-a>FPS*20 else -1))
    return np.arange(lo,hi),np.array(out)
def one(folder,vid):
    s=json.load(open(rf'D:\EZ2ON_PIU\sync\{folder}.json',encoding='utf8'));d=os.path.join(M.O,folder)
    bga=next(os.path.join(d,x) for x in ('BGA.mp4','BGA.webm') if os.path.exists(os.path.join(d,x)))
    G=feat(frames(vid));B=feat(frames(bga))
    L,S=match(G,B,-FPS*40,FPS*40);i=int(S.argmax());second=S[np.abs(L-L[i])>FPS].max()
    lag_v=L[i]/FPS;start=lag_v-s['E3_fine']/1000
    ok=(S[i]>=0.6 and second<=0.8*S[i]) or (S[i]>=0.5 and second<=0.5*S[i])   # sharp peak with a dimmer BGA
    return folder,dict(status='OK' if ok else 'REVISAR',rule='gameplay video',corr=round(float(S[i]),3),second=round(float(second/S[i]),3),lag_v=lag_v,start_s=round(start,3))
if __name__=='__main__':
    ids=json.load(open(r'D:\EZ2ON_PIU\videos_ids.json'));out_f=r'D:\EZ2ON_PIU\bga_video_sync.json'
    out=json.load(open(out_f,encoding='utf8')) if os.path.exists(out_f) else {}
    if os.path.exists(r'D:\EZ2ON_PIU\videos_ids2.json'):ids.update(json.load(open(r'D:\EZ2ON_PIU\videos_ids2.json')))   # second batch (PROBABLE / REVISAR)
    jobs=[(k,rf'D:\EZ2ON_PIU\gameplay_video\{i}.mp4') for k,i in ids.items() if k not in out and os.path.exists(rf'D:\EZ2ON_PIU\gameplay_video\{i}.mp4') and (len(sys.argv)<2 or k in sys.argv[1:])]
    with ProcessPoolExecutor(4) as ex:
        for f in as_completed([ex.submit(one,*j) for j in jobs]):
            try:k,r=f.result()
            except Exception as e:print('ERR',e);continue
            out[k]=r;print('BGAV',k,r,flush=True)
    json.dump(out,open(out_f,'w',encoding='utf8'),indent=1)
