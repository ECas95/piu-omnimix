"""New packs -> reference NX, loudness-matched audio, F charts (songs/<key>/result.json, resumable). SM/SSC: every chart a reference; pump charts also kept as original NX. OSU: mania charts are references;
a set with no mania uses its standard or taiko hit times (rhythm only). Video start comes from BGCHANGES (SM) or the Video event (OSU). usage: convertir.py [--workers 8] [--limit N] [--match text] [--filter 'mode']"""
import os
os.environ['PIU_VARIANT']='F'
import sys,json,re,time,hashlib,subprocess,argparse,traceback,inspect
from pathlib import Path
from fractions import Fraction as F
from concurrent.futures import ThreadPoolExecutor,as_completed
import numpy as np
H=Path(__file__).resolve().parent;B=Path('D:/Pump It Up Data/PIU')
sys.path[:0]=[str(H),str(B/'anime_channel_dng'),str(B),'D:/SSS',str(B/'ssc_export'),str(B/'final_generation_v362'),str(B/'final_generation_v362/vendor_v363')]
sys.dont_write_bytecode=True
import carga
SR=48000;TIMEOUT=7200;MAX_REFS=10
def key_of(folder):return hashlib.sha1(folder.encode('utf8')).hexdigest()[:12]
def grid_env():
    import nx_adapter as A
    code=inspect.getsource(A.source_grid).split('\n    actual=sorted')[0]+'\n    return nx,musical\n';env=dict(A.__dict__);exec(compile(code,'<grid>','exec'),env);return A,env
def audio(src,wav):
    if wav.exists():return
    x=np.frombuffer(subprocess.run(['ffmpeg','-v','error','-i',str(src),'-ac','2','-ar',str(SR),'-f','f32le','-'],capture_output=True,timeout=900).stdout,np.float32).copy()
    if len(x)<SR:raise ValueError('audio unreadable or short: '+str(src))
    x*=10**(-14/20)/(float(np.sqrt(np.mean(x**2))) or 1.)   # official-song loudness (RMS -14 dBFS), as the SSS and IIDX channels
    subprocess.run(['ffmpeg','-v','error','-y','-f','f32le','-ac','2','-ar',str(SR),'-i','-','-af','alimiter=limit=0.97:attack=1:release=50:level=false','-c:a','pcm_s16le',str(wav)],input=x.tobytes(),check=True,timeout=900)
def sm_song(a,work,A,env):
    files=sorted(Path(a['folder']).glob('*.ssc'))+sorted(Path(a['folder']).glob('*.sm'));f=files[0];tags,charts=carga.parse(f);refs=[];native=[];seen=set()
    charts=[no_warp_holds(c) for c in charts];singles=[c for c in charts if SM_COLS(c)<=6];use=singles or charts
    for n,c in enumerate(use):
        if c['signature'] in seen:continue
        seen.add(c['signature']);notes=sum(c['note_symbols'].get(x,0) for x in '124L')
        if notes<16:continue
        name=f"{c['mode']} {c['meter']} {c['difficulty']}".strip()
        try:nx,_=env['source_grid'](c);p=work/f'ref{n}.NX';p.write_bytes(A.nx20.build(nx));refs.append(dict(song=key_of(a['folder']),chart=name,nx=str(p),heads=notes))
        except Exception as e:refs.append(dict(chart=name,error=repr(e)[:200]))
        if c['mode'] in('pump-single','pump-double'):
            try:
                keep=dict(c,rows=[[b,re.sub('[MFKAH]','0',row)] for b,row in c['rows']],timing=dict(c['timing'],SPEEDS='',SCROLLS=''),source_file_sha256=hashlib.sha256(f.read_bytes()).hexdigest())
                raw,info=A.native_nx(keep,len(c['rows']) and 3600);p=work/f'native{n}.NX';p.write_bytes(raw);native.append(dict(nx=str(p),mode=c['mode'],level=int(float(c['meter'])),notes=info['note_count']))
            except Exception as e:native.append(dict(error=repr(e)[:300],mode=c['mode'],level=c['meter']))
    # the video's start: first video in BGCHANGES, even when the named file is another in the folder
    video_s=0.;rate=1.
    for item in tags.get('BGCHANGES','').replace('\r','').replace('\n','').split(','):
        p=item.strip().split('=')
        if len(p)>=2 and Path(p[1]).suffix.lower() in('.mp4','.avi','.mpg','.mpeg','.mkv','.wmv','.mov','.flv','.webm','.m4v'):
            clock=A.SM.Clock(use[0]['timing']);video_s=clock.seconds(F(p[0]));rate=float(p[2] or 1) if len(p)>2 else 1.;break
    return dict(tags={k:tags.get(k,'') for k in('TITLE','TITLETRANSLIT','SUBTITLE','ARTIST','ARTISTTRANSLIT','SAMPLESTART','BPMS','DISPLAYBPM')},refs=refs,native=native,video_seconds=video_s,video_rate=rate,bpm=tags.get('BPMS',''),sample=float(tags.get('SAMPLESTART') or 30) or 30.)
def no_warp_holds(c):
    """A hold that starts, ends or runs through a warp collapses on the time line and can overlap the next note of its lane: it stays as a tap on its head."""
    w=[(a,a+F(str(v))) for a,v in carga.SM.pairs(c['timing'].get('WARPS','')) if v>0]
    if not w:return c
    rows=[[F(b),list(r)] for b,r in c['rows']];opened={}
    for b,r in rows:
        for l,ch in enumerate(r):
            if ch in '24':opened[l]=(b,r)
            elif ch=='3' and l in opened:
                h,hr=opened.pop(l)
                if any(h<=y and b>=x for x,y in w):hr[l]='1';r[l]='0'
    return dict(c,rows=[[str(b),''.join(r)] for b,r in rows])
def SM_COLS(c):return carga.SM.COLS[c['mode']]
def osu_parse(f):
    t=f.read_bytes().decode('utf8','replace');sec={};cur=None
    for l in t.splitlines():
        l=l.strip()
        if l.startswith('[') and l.endswith(']'):cur=l[1:-1];sec[cur]=[]
        elif cur and l and not l.startswith('//'):sec[cur].append(l)
    head={}
    for s in ('General','Metadata','Difficulty'):
        for l in sec.get(s,[]):
            if ':' in l:k,v=l.split(':',1);head[k.strip()]=v.strip()
    tp=[]
    for l in sec.get('TimingPoints',[]):
        p=l.split(',');
        if len(p)>=2 and (len(p)<7 or p[6].strip()=='1') and float(p[1])>0:tp.append((float(p[0]),float(p[1])))
    return head,sec,sorted(tp)
def osu_chart(f,A,env):
    """Rows on the map's own beat grid. Each tempo section gets a tempo that lands exactly on a 192nd, so times never drift; a note moves under 2 ms at most."""
    head,sec,tp=osu_parse(f);mode=int(head.get('Mode',0));k=int(float(head.get('CircleSize',4))) if mode==3 else 1
    if mode==3 and k<1:raise ValueError(f'{k} keys')
    if not tp:raise ValueError('no timing')
    tempos=[tp[0]]
    for x in tp[1:]:
        if abs(x[1]-tempos[-1][1])>1e-6 and x[0]>tempos[-1][0]:tempos.append(x)
    seg=[];beat=F(0)
    for i,(t,bl) in enumerate(tempos):
        if i:beat=seg[-1][1]+F(round((t-seg[-1][0])/seg[-1][2]*192),192)
        seg.append((t,beat,bl))
    for i in range(len(seg)-1):   # exact landing on the next section
        d=seg[i+1][1]-seg[i][1];seg[i]=(seg[i][0],seg[i][1],(seg[i+1][0]-seg[i][0])/float(d) if d>0 else seg[i][2])
    def to_beat(ms):
        s=[x for x in seg if x[0]<=ms];s=s[-1] if s else seg[0];return s[1]+F((ms-s[0])/s[2]).limit_denominator(1920000)
    def snap(b,bl):
        c=F(round(b*48),48);return c if abs(float(c-b))*bl<2 else F(round(b*192),192)
    def bl_at(ms):s=[x for x in seg if x[0]<=ms];return (s[-1] if s else seg[0])[2]
    cells={};orig=[]
    for l in sec.get('HitObjects',[]):
        p=l.split(',')
        if len(p)<4:continue
        x=int(float(p[0]));ms=float(p[2]);ty=int(p[3]);lane=min(k-1,x*k//512)%10 if mode==3 else 0;hold=None
        if mode==3 and k<=10 and ty&128:hold=float(p[5].split(':')[0])
        b=snap(to_beat(ms),bl_at(ms));row=cells.setdefault(b,{})
        while lane in row and mode!=3 and lane<9:lane+=1
        if lane in row:continue
        row[lane]='2' if hold and hold>ms else '1';orig.append((b,ms))
        if hold and hold>ms:
            e=snap(to_beat(hold),bl_at(hold))
            if e<=b or lane in cells.get(e,{}):row[lane]='1';continue
            cells.setdefault(e,{})[lane]='3'
    chart=dict(mode='pump-double',meter='20',rows=[(str(b),''.join(cells[b].get(l,'0') for l in range(10))) for b in sorted(cells)],timing={'BPMS':','.join(f'{b}={60000/bl:.6f}' for _,b,bl in seg),'OFFSET':f'{-seg[0][0]/1000:.6f}'})
    nx,_=env['source_grid'](chart);secs=A.SM.Clock(chart['timing']).seconds;worst=max(abs(float(secs(b))*1000-t) for b,t in orig)
    return A.nx20.build(nx),dict(heads=len(orig),worst_ms=round(worst,2),mode=mode,keys=k,version=head.get('Version',''),bpm=[round(60000/x[2],2) for x in seg][:6])
def osu_song(a,work,A,env):
    fs=sorted(Path(a['folder']).glob('*.osu'));heads=[(f,osu_parse(f)) for f in fs];mania=[f for f,(h,_,_) in heads if h.get('Mode')=='3'];use=mania or [f for f,(h,_,_) in heads if h.get('Mode') in('0','1')] or fs;refs=[]
    for n,f in enumerate(use):
        try:
            raw,i=osu_chart(f,A,env)
            if i['heads']<16:continue
            p=work/f'ref{n}.NX';p.write_bytes(raw);refs.append(dict(song=key_of(a['folder']),chart=f"{i['keys']}K {i['version']}"[:60],nx=str(p),**i))
        except Exception as e:refs.append(dict(chart=f.name[-40:],error=repr(e)[:200]))
    t=heads[0][1][0];video=0.;bpm=[]
    for f,(h,sec,tp) in heads:
        for l in sec.get('Events',[]):
            m=re.match(r'^(?:Video|1)\s*,\s*(-?\d+)\s*,',l)
            if m:video=int(m[1])/1000;break
    for r in refs:
        if r.get('bpm'):bpm=r['bpm'];break
    pv=int(float(t.get('PreviewTime') or -1));return dict(tags={'TITLE':t.get('Title',''),'TITLETRANSLIT':t.get('Title',''),'TITLE_UNICODE':t.get('TitleUnicode',''),'ARTIST':t.get('Artist',''),'ARTIST_UNICODE':t.get('ArtistUnicode','')},refs=refs,native=[],video_seconds=video,video_rate=1.,bpm=','.join(map(str,bpm)),sample=pv/1000 if pv>0 else 30.)
def one(a):
    k=key_of(a['folder']);work=H/'songs'/k;done=work/'result.json'
    if done.exists():return json.loads(done.read_text(encoding='utf8'))
    work.mkdir(parents=True,exist_ok=True);t=time.time();r=dict(key=k,pack=a['pack'],sub=a['sub'],channel=a['channel'],folder=a['folder'],video=a['video'],video_how=a.get('video_how'),charts=[],errors=[])
    try:
        A,env=grid_env()
        info=sm_song(a,work,A,env) if (list(Path(a['folder']).glob('*.ssc'))+list(Path(a['folder']).glob('*.sm'))) else osu_song(a,work,A,env);r.update(info)
        src=a.get('audio') or next((str(x) for x in sorted(Path(a['folder']).iterdir()) if x.suffix.lower() in('.mp3','.ogg','.wav','.flac')),None);r['audio']=src;audio(src,work/'audio.wav')
        good=[x for x in r['refs'] if 'nx' in x]
        if not good:raise ValueError('no usable chart: '+str(r['refs'])[:200])
        good=sorted(good,key=lambda c:c.get('heads',0));good=[good[round(i*(len(good)-1)/(MAX_REFS-1))] for i in range(MAX_REFS)] if len(good)>MAX_REFS else good
        import sss_charts
        res=sss_charts.song(dict(song=k,refs=good,out=str(work/'run')));r['charts']=res['charts'];r['errors']=res['errors']
    except Exception as e:r['errors'].append(dict(error=repr(e)[:400],trace=traceback.format_exc()[-500:]))
    r['seconds']=round(time.time()-t)
    (done if r['charts'] else work/'error.json').write_text(json.dumps(r,ensure_ascii=False,indent=1),encoding='utf8');return r
def run_one(x):
    """A song in its own process: a crash or hang there costs that song, not the whole run."""
    k=key_of(x['folder']);work=H/'songs'/k;done=work/'result.json'
    if done.exists():return json.loads(done.read_text(encoding='utf8'))
    work.mkdir(parents=True,exist_ok=True)
    with open(work/'proc.log','wb') as log:
        try:rc=subprocess.run([sys.executable,'-B','-X','faulthandler',str(H/'convertir.py'),'--one',x['folder']],stdout=log,stderr=subprocess.STDOUT,timeout=TIMEOUT,creationflags=0x4000).returncode   # BELOW_NORMAL
        except subprocess.TimeoutExpired:rc='timeout'
    for f in (done,work/'error.json'):
        if f.exists():return json.loads(f.read_text(encoding='utf8'))
    return dict(charts=[],errors=[dict(error=f'process ended {rc}: '+(work/'proc.log').read_bytes()[-300:].decode('utf8','replace'))])
def main():
    a=argparse.ArgumentParser();a.add_argument('--workers',type=int,default=8);a.add_argument('--limit',type=int);a.add_argument('--match');a.add_argument('--one');a=a.parse_args()
    K=[x for x in json.loads((H/'canciones.json').read_text(encoding='utf8')) if x['keep']]
    if a.one:
        one(next(x for x in K if x['folder']==a.one));return
    if a.match:K=[x for x in K if re.search(a.match,x['folder'])]
    if a.limit:K=K[:a.limit]
    t=time.time();n=c=0;bad=[]
    with ThreadPoolExecutor(a.workers) as ex:
        fut={ex.submit(run_one,x):x for x in K}
        for f in as_completed(fut):
            x=fut[f];n+=1
            try:r=f.result()
            except Exception as e:r=dict(charts=[],errors=[dict(error=repr(e)[:300])])
            c+=len(r['charts'])
            if not r['charts'] or r['errors']:bad.append(dict(folder=x['folder'],errors=str(r['errors'])[:300]));print('PROBLEM',Path(x['folder']).name[:40],str(r['errors'])[:300],flush=True)
            if n%10==0 or n==len(K):print('PROGRESS',n,len(K),'charts',c,'problems',len(bad),'%.0fs'%(time.time()-t),flush=True)
    (H/'problemas.json').write_text(json.dumps(bad,ensure_ascii=False,indent=1),encoding='utf8');print('CONVERT_DONE',n,'charts',c,'problems',len(bad),'%.0fs'%(time.time()-t),flush=True)
if __name__=='__main__':main()
