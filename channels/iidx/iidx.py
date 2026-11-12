"""beatmania IIDX song -> PIU: chart references, audio mix, F charts, StepP1 test song. E: is only read; everything is written to D:.
Source per song: data/sound/<id>/ or <id>.ifs (.1 charts, .s3p or .2dx keysounds). .1 = 12 (offset,size) chart slots, SP first; each chart = 8-byte
events (int ms, type, param, value): 0 note P1 (param lane, 7 = scratch; value = hold ms), 2 keysound of a lane, 4 tempo (value/param BPM),
7 background sample, 12 bar line. No music file exists: the song is the mix of the hardest SP chart's samples, as the game plays it on autoplay.
usage: iidx.py [ids...]"""
import os
os.environ['PIU_VARIANT']='F'   # before the composer loads (also in the workers)
from pathlib import Path
from fractions import Fraction as F
from concurrent.futures import ThreadPoolExecutor,ProcessPoolExecutor,as_completed
import sys,json,struct,subprocess,hashlib,inspect,re,time
import numpy as np
H=Path(__file__).resolve().parent;OUT=H/os.environ.get('PIU_IIDX_OUT','piloto');C=Path('E:/IIDX222/001 - Proyecto IIDX/IIDX/LDJ-012-20231018/contents');SOUND=C/'data/sound';MOVIE=C/'data/movie'
PACK=Path('D:/003 - StepP1/SP2/stepp1-plus-2.0.0/Songs/PIU IIDX PILOTO')
B=Path('D:/Pump It Up Data/PIU');sys.path[:0]=[str(B/'anime_channel_dng'),str(B),'D:/SSS',str(B/'ssc_export'),str(B/'final_generation_v362'),str(B/'final_generation_v362/vendor_v363')]
sys.dont_write_bytecode=True
SR=48000;MAX_MS=3.;DELAY_UNIT_MS=1.   # bga_delay unit: see measure() (ms until shown otherwise)
TAP,HOLD,BPM,BG,BAR,KEY=0,0,4,7,12,2

def source_dir(sid):
    d=OUT/'src'/str(sid)
    if d.exists() and any(d.iterdir()):return d
    d.mkdir(parents=True,exist_ok=True);n=f'{sid:05d}';folder=SOUND/n
    if folder.is_dir() and not (sid>=30000 and (folder/(n+'.2dx')).exists() and (SOUND/(n+'.ifs')).exists()):   # 2dx folder over an .ifs in the s3p era: other song or silent stub under this id, the .ifs is the real one
        for f in folder.iterdir():
            if f.is_file():(d/f.name).write_bytes(f.read_bytes())
        return d
    from ifstools import IFS
    p0=SOUND/(n+'-p0.ifs')   # newer overlay of the same song: holds every file of the base plus later charts
    i=IFS(str(p0 if p0.exists() else SOUND/(n+'.ifs')))
    for f in i.tree.all_files:(d/f.name).write_bytes(f.load())
    return d

def events(raw,slot):
    off,size=struct.unpack_from('<2I',raw,slot*8)
    return [struct.unpack_from('<iBBh',raw,off+k*8) for k in range(size//8)] if size else []

def sp_charts(raw):
    """Every SP slot with notes -> {slot: events}. Slots are named by note count (the hardest is the mix and the top chart)."""
    out={}
    for s in range(6):
        ev=events(raw,s)
        if sum(e[1]==0 for e in ev):out[s]=ev
    return out

def clock(ev):
    """Tempo map on a grid whose integer beats are the chart's bar lines. Returns (bpm list [(beat,bpm)], offset s, to_beat(ms))."""
    tempos=sorted({(e[0],(e[3]&0xFFFF)/(e[2] or 1)) for e in ev if e[1]==BPM and e[3]})   # value is unsigned: 40000/100 = 400 BPM reads negative as i16
    if not tempos:raise ValueError('no tempo')
    bars=sorted({e[0] for e in ev if e[1]==BAR and e[0]>=0});t0=bars[0] if bars else tempos[0][0]
    if tempos[0][0]>t0:t0=tempos[0][0]
    # segment start ms -> exact beat from bar 0 at t0
    seg=[];beat=F(0);base=[t for t in tempos if t[0]<=t0][-1];cur=(t0,base[1])
    seg.append((cur[0],F(0),cur[1]))
    for t,b in tempos:
        if t<=t0:continue
        beat+=F(t-cur[0])*F(cur[1]).limit_denominator(1000)/60000;beat=F(round(beat*192),192);seg.append((t,beat,b));cur=(t,b)
    def to_beat(ms):
        k=[s for s in seg if s[0]<=ms];s=k[-1] if k else seg[0]
        return s[1]+F(ms-s[0])*F(s[2]).limit_denominator(1000)/60000
    return [(b,bp) for _,b,bp in seg],t0/1000,to_beat

def snap(b,bpm):
    """Nearest 48th of a beat when that moves the note under 2 ms (real rhythm), else nearest 192nd."""
    c=F(round(b*48),48)
    return c if abs(float(c-b))*60000/bpm<2 else F(round(b*192),192)

def reference(ev,env,A):
    bpms,offset,to_beat=clock(ev);cells={};orig=[]
    bpm_at=lambda bt:[p for b,p in bpms if b<=bt][-1] if [p for b,p in bpms if b<=bt] else bpms[0][1]
    heads=holds=0
    for t,ty,lane,val in ev:
        if ty!=0 or lane>7 or t==2147483647:continue
        b=to_beat(t);bt=snap(b,bpm_at(b));row=cells.setdefault(bt,{})
        if lane in row:continue
        heads+=1;row[lane]='2' if val>0 else '1';orig.append((bt,t))
        if val>0:
            e=to_beat(t+val);et=snap(e,bpm_at(e))
            if et<=bt or lane in cells.get(et,{}):row[lane]='1';continue
            cells.setdefault(et,{})[lane]='3';holds+=1
    chart=dict(mode='pump-double',meter='20',rows=[(str(b),''.join(cells[b].get(l,'0') for l in range(10))) for b in sorted(cells)],
               timing={'BPMS':','.join(f'{b}={p:.6f}' for b,p in bpms),'OFFSET':f'{-offset:.6f}'})
    nx,_=env['source_grid'](chart);raw=A.nx20.build(nx)
    # the note's clock on the rebuilt timing must stay on the original's
    seconds=A.SM.Clock(chart['timing']).seconds;worst=max(abs(float(seconds(b))*1000-t) for b,t in orig)
    return raw,dict(heads=heads,holds=holds,bpms=[(float(b),round(p,3)) for b,p in bpms],offset_s=offset,worst_ms=round(worst,2))

def bank_file(d,sid,slot,top=0):
    """Sound bank of a chart: <id>.s3p or <id>.2dx, or per difficulty on old songs (<id>1 normal, <id>2 hyper, <id>a another)."""
    n=f'{sid:05d}'
    if (d/(n+'.s3p')).exists():return d/(n+'.s3p')
    pref={2:('a','2','1',''),0:('2','1','a',''),1:('1','2','a',''),3:('1','2','a','')}.get(slot,('','1','2','a'))
    for dx in [d/f'{n}{x}.2dx' for x in pref]+sorted(f for f in d.glob('*.2dx') if '_pre' not in f.name):
        if dx.exists() and struct.unpack_from('<I',dx.read_bytes(0x18) if False else dx.open('rb').read(0x18),0x14)[0]>=top:return dx
    raise ValueError('sin banco de sonidos: '+', '.join(sorted(f.name for f in d.iterdir())))

def samples(f):
    """[(format, bytes, gain, pan)]. 2dx carries per-sample attenuation (1 = full; 1 dB per unit, fitted against the official previews) and pan (64 = centre)."""
    raw=f.read_bytes()
    if f.suffix=='.s3p':
        c=struct.unpack_from('<I',raw,4)[0];t=struct.unpack_from(f'<{c*2}I',raw,8)
        return [('asf',raw[t[i*2]+struct.unpack_from('<I',raw,t[i*2]+4)[0]:t[i*2]+t[i*2+1]],1.,64) for i in range(c)]
    c=struct.unpack_from('<I',raw,0x14)[0];t=struct.unpack_from(f'<{c}I',raw,0x48);out=[]
    for o in t:
        pan,att=struct.unpack_from('<2h',raw,o+16);out.append(('wav',raw[o+24:o+24+struct.unpack_from('<I',raw,o+8)[0]],10**(-max(0,att-1)/20),pan or 64))
    return out

def decode(item):
    fmt,blob,gain,pan=item
    r=subprocess.run(['ffmpeg','-v','error','-f',fmt,'-i','-','-f','f32le','-ac','2','-ar',str(SR),'-'],input=blob,capture_output=True)
    return np.frombuffer(r.stdout,np.float32).reshape(-1,2)*np.array([min(1,(127-pan)/63),min(1,pan/64)],np.float32)*gain if r.stdout else np.zeros((1,2),np.float32)

def render(d,sid,ev,wav,slot=None):
    f=bank_file(d,sid,slot,max(e[3] for e in ev if e[1] in (KEY,BG)))
    print('BANK',sid,f.name,'slot',slot,flush=True)
    """Autoplay of the chart: background samples plus each lane's current keysound on its notes; a sample replayed cuts its previous play."""
    bank=samples(f);cur={};hits=[]
    for t,ty,p,v in sorted(ev,key=lambda e:(e[0],e[1]!=KEY)):   # a keysound change at the same ms applies to that note
        if t==2147483647:continue
        if ty==KEY:cur[p]=v
        elif ty==BG and v:hits.append((t,v))
        elif ty==0 and p<=7 and cur.get(p):hits.append((t,cur[p]))
    used=sorted({v for _,v in hits if 0<v<=len(bank)})
    with ThreadPoolExecutor(6) as ex:dec=dict(zip(used,ex.map(decode,[bank[v-1] for v in used])))
    hits=sorted(h for h in hits if h[1] in dec);end=max(t/1000+len(dec[v])/SR for t,v in hits);mix=np.zeros((int(end*SR)+SR,2),np.float32)
    nxt={};
    for i,(t,v) in enumerate(hits):nxt.setdefault(v,[]).append(i)
    for k,(t,v) in enumerate(hits):
        x=dec[v];o=int(round(t*SR/1000));l=nxt[v];j=l.index(k)
        if j+1<len(l):x=x[:max(0,int(round(hits[l[j+1]][0]*SR/1000))-o)]
        mix[o:o+len(x)]+=x
    # trailing silence off, official-song loudness (RMS -14 dBFS) as the SSS channel
    a=np.abs(mix).max(axis=1);last=int(np.nonzero(a>1e-4)[0][-1])+SR//2;mix=mix[:last];peak=float(a.max());mix*=10**(-14/20)/(float(np.sqrt(np.mean(mix**2))) or 1.)
    wav.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run(['ffmpeg','-v','error','-y','-f','f32le','-ac','2','-ar',str(SR),'-i','-','-af','alimiter=limit=0.97:attack=1:release=50:level=false','-c:a','pcm_s16le',str(wav)],input=mix.tobytes(),check=True)
    return dict(samples=len(used),bank=len(bank),hits=len(hits),seconds=round(len(mix)/SR,2),peak=round(peak,2))

def db():
    d=(C/'data/info/1/music_omni.bin').read_bytes();n,mx=struct.unpack_from('<HH',d,8);base=16+mx*2;out={}
    for i in range(n):
        e=d[base+i*1324:base+(i+1)*1324];t=lambda o,l=64:e[o:o+l].split(b'\0')[0].decode('cp932','replace')
        out[struct.unpack_from('<I',e,0x3b0)[0]]=dict(title=t(0),ascii=t(0x40),artist=t(0xc0),genre=t(0x80),bga=t(0x3c4,32),delay=struct.unpack_from('<h',e,0x3c2)[0])
    return out

def prepare(sid,meta):
    """Reference NX per SP chart + audio (no generation)."""
    work=OUT/'songs'/str(sid);work.mkdir(parents=True,exist_ok=True);d=source_dir(sid)
    import inspect,nx_adapter as A
    code=inspect.getsource(A.source_grid).split('\n    actual=sorted')[0]+'\n    return nx,musical\n';env=dict(A.__dict__);exec(compile(code,'<iidx_grid>','exec'),env)
    raw=(d/f'{sid:05d}.1').read_bytes();charts=sp_charts(raw);refs=[];info={}
    notes=lambda s:sum(e[1]==0 for e in charts[s])
    banks={s:bank_file(d,sid,s,max(e[3] for e in charts[s] if e[1] in (KEY,BG))) for s in charts};fam={}
    for s,f in banks.items():fam.setdefault(f.name,[]).append(s)
    wav=work/'audio.wav';ainfo={};score={}
    if len(fam)==1:hardest=max(charts,key=notes);ainfo=render(d,sid,charts[hardest],wav,hardest) if not wav.exists() else {}
    else:   # old song with one bank per difficulty: ANOTHER can be another arrangement of the song
        # Each family is rendered from its hardest chart. Two charts of one family must give the same song (autoplay is complete on any difficulty):
        # that is the check when the official preview comes from the other arrangement. The family with the hardest chart wins if it passes.
        def pcm(w):return np.frombuffer(subprocess.run(['ffmpeg','-v','error','-i',str(w),'-ac','1','-ar','8000','-f','f32le','-'],capture_output=True).stdout,np.float32)
        check={}
        for name,ss in fam.items():
            k=max(ss,key=notes);w=work/f'audio_{name}.wav';render(d,sid,charts[k],w,k);score[name]=preview_check(sid,w)[0]
            others=[x for x in ss if x!=k]
            if others:
                o=max(others,key=notes);w2=work/f'check_{name}.wav';render(d,sid,charts[o],w2,o);x,y=pcm(w),pcm(w2);n=min(len(x),len(y));check[name]=round(float(np.corrcoef(x[:n],y[:n])[0,1]),3);w2.unlink()
        top=max(fam,key=lambda n:max(notes(x) for x in fam[n]))
        best=top if check.get(top,0)>=.8 or score[top]>=.3 else max(score,key=score.get)
        (work/f'audio_{best}.wav').replace(wav);print('ARREGLOS',sid,'preview',score,'consistencia',check,'->',best,flush=True)
        for name in score:(work/f'audio_{name}.wav').unlink(missing_ok=True)
        same={n for n in fam if struct.unpack_from('<I',(d/n).open('rb').read(0x18),0x14)[0]==struct.unpack_from('<I',(d/best).open('rb').read(0x18),0x14)[0]}
        keep=[x for n in same for x in fam[n]];charts={k:v for k,v in charts.items() if k in keep};hardest=max(charts,key=notes)
    for s,ev in charts.items():
        data,i=reference(ev,env,A);p=work/f'sp{s}.NX';p.write_bytes(data);refs.append(dict(song=str(sid),chart=f'SP slot {s}',nx=str(p),**i));info[s]=i
    (work/'prepare.json').write_text(json.dumps(dict(refs=refs,audio=ainfo,hardest=hardest,arreglos=score),indent=1))
    return refs,ainfo

def measure(sid,meta):
    """Lag between the movie's scene changes and the audio's onsets: evidence for the unit of bga_delay. + = picture late."""
    w=OUT/'songs'/str(sid)/'audio.wav';m=MOVIE/(meta['bga']+'.mp4');R=30
    v=subprocess.run(['ffmpeg','-v','error','-i',str(m),'-vf',f'fps={R},scale=32:24,format=gray','-f','rawvideo','-'],capture_output=True).stdout
    fr=np.frombuffer(v,np.uint8).reshape(-1,24*32).astype(np.float32);vd=np.abs(np.diff(fr,axis=0)).mean(axis=1)
    a=subprocess.run(['ffmpeg','-v','error','-i',str(w),'-ac','1','-ar','8000','-f','f32le','-'],capture_output=True).stdout
    x=np.frombuffer(a,np.float32);hop=8000//R;env=np.sqrt(np.convolve(x**2,np.ones(hop)/hop,'same')[::hop]);ad=np.clip(np.diff(env),0,None)
    n=min(len(vd),len(ad));vd=(vd[:n]-vd[:n].mean())/(vd[:n].std()+1e-9);ad=(ad[:n]-ad[:n].mean())/(ad[:n].std()+1e-9)
    best=sorted(((float(np.dot(vd[max(0,l):n+min(0,l)],ad[max(0,-l):n-max(0,l)]))/n,l/R) for l in range(-R*3,R*3+1)),reverse=True)[:3]
    return dict(delay_field=meta['delay'],best=[(round(c,3),round(l,3)) for c,l in best])

def preview_check(sid,wav=None):
    """The official preview is a cut of the real song: finding it inside our mix proves samples, order and timing. Returns (correlation, start s)."""
    d=OUT/'src'/str(sid);pre=d/f'{sid:05d}_pre.2dx';raw=pre.read_bytes();c=struct.unpack_from('<I',raw,0x14)[0];o=struct.unpack_from(f'<{c}I',raw,0x48)[0]
    w=subprocess.run(['ffmpeg','-v','error','-i','-','-ac','1','-ar','8000','-f','f32le','-'],input=raw[o+24:o+24+struct.unpack_from('<I',raw,o+8)[0]],capture_output=True).stdout
    m=subprocess.run(['ffmpeg','-v','error','-i',str(wav or OUT/'songs'/str(sid)/'audio.wav'),'-ac','1','-ar','8000','-f','f32le','-'],capture_output=True).stdout
    x=np.frombuffer(w,np.float32);y=np.frombuffer(m,np.float32);x=x[800:min(len(x),8000*12)];x=x-x.mean();n=len(y)+len(x)
    cc=np.fft.irfft(np.fft.rfft(y,n)*np.conj(np.fft.rfft(x,n)),n);l=int(np.argmax(cc[:len(y)]));seg=y[l:l+len(x)]
    if len(seg)<len(x):x=x[:len(seg)]
    r=float(np.corrcoef(seg,x)[0,1]) if len(seg)>100 else 0.
    return round(r,3),round((l-800)/8000,2)

def charts_job(sid,refs):
    import sss_charts
    return sss_charts.song(dict(song=str(sid),refs=refs,out=str(OUT/'songs'/str(sid)/'run')))

def ssc(sid,meta,res,refs,sample=30.):
    import nx_ssc
    from hybrid import nx20
    work=OUT/'songs'/str(sid);name=re.sub(r'[\\/:*?"<>|]','',f"{sid} - {meta['ascii'] or meta['title']}").strip();d=PACK/name;d.mkdir(parents=True,exist_ok=True)
    rows=[]
    for c in res['charts']:rows.append((nx20.parse(Path(c['nx']).read_bytes()),f"{'S' if c['mode']=='Single' else 'D'}{c['level']} F",c['level'],f"F T{c.get('tier')} {c.get('reduction')} de {c.get('source_chart')}",'omnimix F'))
    worst=max(nx_ssc.check(r[0]) for r in rows);assert worst<nx_ssc.MAX_MS,worst
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(work/'audio.wav'),'-c:a','libvorbis','-q:a','6',str(d/'Song.ogg')],check=True)
    origin,bpms,_=nx_ssc.timing(rows[0][0]);lead=origin/1000-meta['delay']*DELAY_UNIT_MS/1000   # movie time at beat 0
    m=MOVIE/(meta['bga']+'.mp4');vf='scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30'
    args=['ffmpeg','-v','error','-y']
    if lead>=0:args+=['-ss',f'{lead:.3f}','-i',str(m),'-vf',vf]
    else:args+=['-i',str(m),'-vf',vf+f',tpad=start_duration={-lead:.3f}:start_mode=add:color=black']
    subprocess.run(args+['-an','-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p',str(d/'bga.mp4')],check=True)
    subprocess.run(['ffmpeg','-v','error','-y','-ss','25','-i',str(d/'bga.mp4'),'-frames:v','1',str(d/'banner.png')],check=True)
    text=nx_ssc.song_ssc(meta['ascii'] or meta['title'],meta['artist'],'Song.ogg','banner.png',sample,rows)
    text=re.sub(r'(#MUSIC:[^;]*;)',r'\1'+'\n#BGCHANGES:0.000=bga.mp4=1.000=1=0=0=StretchNoLoop==CrossFade==;',text,count=1)
    (d/'song.ssc').write_text(text,encoding='utf8');return name,len(rows),round(worst,2)

def main():
    ids=[int(x) for x in sys.argv[1:]] or [1000,12000,20002,31000,31002];D=db();t=time.time();report=[];prep={}
    with ThreadPoolExecutor(2) as ex:
        for sid,(refs,a) in zip(ids,ex.map(lambda s:prepare(s,D[s]),ids)):
            prep[sid]=refs;print('PREPARE',sid,D[sid]['ascii'],[(r['chart'],r['heads'],r['holds'],r['worst_ms'],r['bpms'][:2]) for r in refs],a,'%.0fs'%(time.time()-t),flush=True)
    for sid in ids:print('DELAY',sid,measure(sid,D[sid]),flush=True)
    sample={}
    for sid in ids:
        r,st=preview_check(sid);sample[sid]=max(0.,st);print('PREVIEW',sid,'corr',r,'start',st,flush=True)
    with ProcessPoolExecutor(5) as ex:
        fut={ex.submit(charts_job,s,prep[s]):s for s in ids};res={}
        for f in as_completed(fut):res[fut[f]]=f.result();print('CHARTS',fut[f],len(res[fut[f]]['charts']),'errors',res[fut[f]]['errors'][:2],'%.0fs'%(time.time()-t),flush=True)
    for sid in ids:
        n=ssc(sid,D[sid],res[sid],prep[sid],sample[sid]);report.append(dict(id=sid,folder=n[0],charts=n[1],worst_ms=n[2]));print('SSC',n,flush=True)
    (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=1));print('PILOT_DONE','%.0fs'%(time.time()-t),flush=True)
if __name__=='__main__':main()
