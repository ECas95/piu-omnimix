"""EZ2ON chart <-> Song.mp3 offset, measured three independent ways per song (no assumption about measure 1):
  E1  chart notes  vs Song.mp3 onsets            (direct; phase is good, whole-beat shifts are ambiguous)
  E2  chart notes  vs gameplay recording onsets  (the game fires each keysound at its note time)
  E3  Song.mp3     vs gameplay recording audio   (audio-to-audio, 8-band onset envelopes)
Offset convention: time in Song.mp3 = chart time_ms + lag. Every peak is kept for the acceptance step.
Output: sync/<folder>.json"""
import json,glob,os,re,csv,sys,urllib.parse,numpy as np,subprocess
from concurrent.futures import ProcessPoolExecutor,as_completed
B=r'D:\eeez2abackup';O=B+r'\EZ2ON_ORGANIZADO';OUT=r'D:\EZ2ON_PIU\sync'
FF=glob.glob(os.path.expandvars('%LOCALAPPDATA%/Microsoft/WinGet/Packages/Gyan.FFmpeg*/ffmpeg-*/bin/ffmpeg.exe'))[0]
SR=11025;HOP=110;FPS=SR/HOP

def pcm(f):return np.frombuffer(subprocess.check_output([FF,'-v','error','-i',f,'-vn','-ac','1','-ar',str(SR),'-f','f32le','-']),np.float32)
def bands(f,nb=8):
    x=pcm(f);n=(len(x)-1024)//HOP;idx=np.arange(1024)[None,:]+HOP*np.arange(n)[:,None]
    S=np.log1p(100*np.abs(np.fft.rfft(x[idx]*np.hanning(1024),axis=1)))
    e=np.unique(np.geomspace(2,512,nb+1).astype(int));Bd=np.stack([S[:,a:b].mean(1) for a,b in zip(e,e[1:])],1)
    F=np.maximum(np.diff(Bd,axis=0),0);F-=np.stack([np.convolve(F[:,k],np.ones(50)/50,'same') for k in range(F.shape[1])],1)
    F=np.maximum(F,0);return F/(F.std(0)+1e-9)
def train(times,n):
    t=np.zeros(n);i=np.round(np.asarray(times)/1000*FPS).astype(int);i=i[(i>=0)&(i<n)];np.add.at(t,i,1)
    return np.convolve(t,[.25,.5,1,.5,.25],'same')
def xcorr(a,b,lo_ms,hi_ms):
    """score[lag] = sum a[t+lag]*b[t] (a,b: (n,) or (n,k)); lags in ms -> (lags, scores)"""
    a=a if a.ndim==2 else a[:,None];b=b if b.ndim==2 else b[:,None];n=1<<int(np.ceil(np.log2(len(a)+len(b))))
    c=np.fft.irfft((np.fft.rfft(a,n,axis=0)*np.conj(np.fft.rfft(b,n,axis=0))).sum(1),n)
    ls=np.arange(int(lo_ms/1000*FPS),int(hi_ms/1000*FPS));return ls/FPS*1000,c[ls%n]
def peaks(L,S,k=6,sep=60):
    o=np.argsort(-S);out=[]
    for i in o:
        if 0<i<len(S)-1 and S[i]>=S[i-1] and S[i]>=S[i+1] and all(abs(L[i]-l)>sep for l,_ in out):out.append((float(L[i]),float(S[i])))
        if len(out)>=k:break
    return [(round(l,1),round(s/out[0][1],4)) for l,s in out]

def refine(L,S,i):   # parabolic sub-frame peak
    if 0<i<len(S)-1:
        d=S[i-1]-2*S[i]+S[i+1];return L[i]+(0.5*(S[i-1]-S[i+1])/d if d else 0)*1000/FPS
    return L[i]

def mapping():
    import unicodedata;nk=lambda t:re.sub(r'[^0-9a-z]','',unicodedata.normalize('NFKC',t or '').lower())   # v379: 'TRUE' vs 'True'
    yt={}
    for r in csv.DictReader(open(B+r'\ez2pattern_youtube.csv',encoding='utf-8-sig')):
        vid=r['youtube_id'] if re.fullmatch(r'[\w-]{11}',r['youtube_id']) else (re.search(r'v=([\w-]{11})',r['youtube_url']) or [None,None])[1]   # '#NAME?' cells: id from the URL
        if r['status']=='ok' and vid:yt.setdefault(nk(r['folder']),vid)
    cf={nk(d):d for d in os.listdir(os.path.join(B,'ez2on_charts'))}   # 'E2O' -> 'E 2 O'
    web={}
    for f in os.listdir(B+r'\ez2on_charts_mp3'):
        m=re.search(r'\[([\w-]{11})\]\.webm$',f)
        if m:web[m[1]]=os.path.join(B,'ez2on_charts_mp3',f)
    out=[]
    for s in sorted(os.listdir(O)):
        p=os.path.join(O,s)
        if not os.path.isdir(p) or s.startswith('_'):continue
        b=[x for x in os.listdir(p) if x.endswith('.bms')];fs=set(os.listdir(p))
        if not b or 'Song.mp3' not in fs:continue
        u=re.search(r'ez2pattern\.kr/chart/([^/]+)/',open(os.path.join(p,b[0]),encoding='utf8',errors='replace').read())
        ch=urllib.parse.unquote(u[1]);ch=ch if os.path.isdir(os.path.join(B,'ez2on_charts',ch)) else cf.get(nk(ch),ch);w=web.get(yt.get(nk(ch)))
        out.append(dict(folder=s,chart=ch,gameplay=w,bga=next((x for x in ('BGA.mp4','BGA.webm') if x in fs),None)))
    return out

def played(web,files):   # which chart the recording plays: "{B} title 4K SHD 14"
    m=re.search(r'(\d)K\s+(EZ|NM|HD|SHD)\b',os.path.basename(web))
    if m:
        f=[x for x in files if os.path.basename(x)==f'{m[1]}S_{m[2]}.json']
        if f:return f[0]
    return None

def song(job):
    out=os.path.join(OUT,job['folder']+'.json')
    if os.path.exists(out):return json.load(open(out,encoding='utf8'))
    r=dict(job);files=sorted(glob.glob(os.path.join(B,'ez2on_charts',job['chart'],'*S_*.json')))
    try:
        notes={os.path.basename(f):[x['time_ms'] for x in json.load(open(f,encoding='utf8'))['notes']] for f in files}
        j=json.load(open(files[0],encoding='utf8'));r['beat_ms']=60000/j['initial_bpm'];r['bpm_changes']=len(j['bpm_changes'])
        sb=bands(os.path.join(O,job['folder'],'Song.mp3'));so=sb.sum(1)
        allt=sorted({t for v in notes.values() for t in v});r['E1']=peaks(*xcorr(so,train(allt,len(so)),-15000,15000))
        if job['gameplay']:
            gb=bands(job['gameplay']);go=gb.sum(1)
            L,S=xcorr(gb,sb,-30000,90000);r['E3']=peaks(L,S);r['E3_fine']=round(refine(L,S,int(np.argmax(S))),1)
            pf=played(job['gameplay'],files);r['played']=pf and os.path.basename(pf)
            t=notes[os.path.basename(pf)] if pf else allt
            L,S=xcorr(go,train(t,len(go)),-30000,90000);r['E2']=peaks(L,S);r['E2_fine']=round(refine(L,S,int(np.argmax(S))),1)
    except Exception as e:r['error']=repr(e)[:300]
    json.dump(r,open(out,'w',encoding='utf8'),ensure_ascii=False,indent=1);return r

if __name__=='__main__':
    os.makedirs(OUT,exist_ok=True);jobs=mapping();json.dump(jobs,open(r'D:\EZ2ON_PIU\mapping.json','w',encoding='utf8'),ensure_ascii=False,indent=1)
    jobs=[j for j in jobs if j['bga'] and (len(sys.argv)<2 or j['folder'] in sys.argv[1:])];done=0
    with ProcessPoolExecutor(6) as ex:
        for f in as_completed([ex.submit(song,j) for j in jobs]):
            done+=1;r=f.result();print('SYNC',done,len(jobs),r['folder'],r.get('E1',[None])[0],r.get('E2',[None])[0],r.get('E3',[None])[0],r.get('error',''),flush=True)
