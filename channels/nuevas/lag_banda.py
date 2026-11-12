"""Chart lag with a wider window (+-120 ms), broadband and bass only: kicks fall on the beat, so the bass reading is not fooled by off-beat hats. Prints per song; lag_banda.json."""
import json,sys,subprocess,collections,statistics as st
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import numpy as np
H=Path(__file__).resolve().parent;B=Path('D:/Pump It Up Data/PIU');sys.path[:0]=[str(B/'anime_channel_dng/engine'),str(B)]
sys.dont_write_bytecode=True
import nx20,quality_charting as Q
AR=500;W=60   # 2 ms, +-120 ms
def pcm(p,af=None):
    a=['ffmpeg','-v','error','-i',str(p)]+(['-af',af] if af else [])+['-ac','1','-ar','8000','-f','f32le','-'];return np.frombuffer(subprocess.run(a,capture_output=True,timeout=900).stdout,np.float32)
def onset(x):
    hop=8000//AR;e=np.sqrt(np.convolve(x**2,np.ones(hop*2)/(hop*2),'same')[::hop]);o=np.clip(np.diff(e),0,None);return o/(o.mean()+1e-9)
def curve(on,t):
    ls=np.arange(-W,W+1);sc=[]
    for l in ls:
        i=np.rint(t*AR).astype(int)+l;i=i[(i>=0)&(i<len(on))];sc.append(on[i].mean())
    return ls*1000//AR,np.array(sc)
def pk(ls,sc):
    k=int(np.argmax(sc));return dict(lag=int(ls[k]),score=round(float(sc[k]),2),at0=round(float(sc[W]),2),edge=k in(0,len(sc)-1))
def one(f):
    r=json.loads(f.read_text(encoding='utf8'));a=H/'songs'/r['key']/'audio.wav';good=sorted([c for c in r['refs'] if 'nx' in c],key=lambda c:c.get('heads',0))
    out=dict(key=r['key'],pack=(r.get('sub') or r['pack'])[-22:],title=r['tags'].get('TITLE','')[:30],bpm=str(r.get('bpm'))[:14].replace('\n',''))
    try:
        bb=onset(pcm(a));lo=onset(pcm(a,'lowpass=f=150,lowpass=f=150'));R=[]
        for c in good[:4]:
            n=sorted({x[1] for x in Q.notes_of(nx20.parse(Path(c['nx']).read_bytes()))})
            if len(n)<20:continue
            t=np.array(n)/1000;R.append((pk(*curve(bb,t)),pk(*curve(lo,t))))
        out['bb']=R[0][0];out['lo']=R[0][1];out['bb_all']=[x[0]['lag'] for x in R];out['lo_all']=[x[1]['lag'] for x in R]
    except Exception as e:out['error']=repr(e)[:200]
    return out
if __name__=='__main__':
    fs=sorted((H/'songs').glob('*/result.json'))
    with ThreadPoolExecutor(6) as ex:o=list(ex.map(one,fs))
    (H/'lag_banda.json').write_text(json.dumps(o,ensure_ascii=False,indent=0),encoding='utf8')
    g=collections.defaultdict(list)
    for x in o:
        if 'bb' in x:g[x['pack']].append(x)
    for k,v in g.items():
        L=[st.median(x['lo_all']) for x in v];B2=[st.median(x['bb_all']) for x in v];print(k,len(v),'bass median',st.median(L),'hist',sorted(collections.Counter(20*round(y/20) for y in L).items()),'| broad median',st.median(B2));
    print('LAG_DONE',len(o))
