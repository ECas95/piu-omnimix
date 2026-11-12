"""EZ2ON REBOOT : R -> BMS package per song (D:\eeez2abackup\EZ2ON_ORGANIZADO -> D:\PIU_PRESERVADO\BMS_EZ2ON).
 A) songs with .ez (plain EZFF v8) : keysounded BMS straight from the game chart (sample names from <chart>_instrumentDic.json),
    one file per chart, <N>S_<DIFF>.bms, lanes Line1-5 -> 11-15, Line6 -> 18, Line7 -> 19, Scratch -> 16.
 B) songs with only the ez2pattern BMS : that BMS kept (Song.mp3 on measure 1, same clock as the game's 'mr' track), header completed.
 Media are hard links (same volume): Song.mp3, BGA.mp4, Banner.png, Cover.png, keysounds.
 BGA: object on ch04 at Song time start_s (D:\EZ2ON_PIU bga_video_sync / bga_sync, status OK) after the BGM start.
Usage: python -I ez2on_to_bms.py [song ...]"""
from pathlib import Path
from math import gcd
from fractions import Fraction as F
import sys,json,re,os,shutil,collections,struct,subprocess
sys.dont_write_bytecode=True
sys.path.insert(0,r'D:\PIU_PRESERVADO\tools')
import ezff
SYNC=json.loads(Path(r'D:\EZ2ON_PIU\sync_final.json').read_text())
SRC=Path(r'D:\eeez2abackup\EZ2ON_ORGANIZADO');OUT=Path(r'D:\PIU_PRESERVADO\BMS_EZ2ON')
B36='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ';B62=B36+'abcdefghijklmnopqrstuvwxyz'
b36=lambda n:B36[n//36]+B36[n%36]
DIFF={'ez':1,'nm':2,'hd':3,'shd':4}
def row(slots,n):
    g=n
    for p in slots:g=gcd(g,p)
    n//=g;s=['00']*n
    for p,c in slots.items():s[p//g]=c
    return ''.join(s)
def link(a,b):
    if b.exists():return
    try:os.link(a,b)
    except OSError:shutil.copy2(a,b)

def bga_start(song):
    for f,key in (('bga_video_sync.json','start_s'),('bga_sync.json','start_s')):
        d=json.loads(Path(rf'D:\EZ2ON_PIU\{f}').read_text()).get(song)
        if d and d.get('status')=='OK':return d[key]
    return None

def timing(c):
    tpm=c['ticks_per_measure'];tr=c['tracks']
    meas=sorted({p:rest[0][0] for _,ev in tr for (p,k,*rest) in ev if k==4}.items())
    bp=sorted({p:struct.unpack('<f',rest[0][:4])[0] for _,ev in tr for (p,k,*rest) in ev if k==3}.items())
    if not bp or bp[0][0]>0:bp=[(0,c['bpm'])]+bp
    if not meas or meas[0][0]>0:meas=[(0,4)]+meas
    def tobeat(t):
        b=F(0)
        for i,(at,n) in enumerate(meas):
            nxt=meas[i+1][0] if i+1<len(meas) else None
            if nxt is not None and t>nxt:b+=F(nxt-at)*n/tpm;continue
            return b+F(t-at)*n/tpm
    marks=[];s=0.;prev=None
    for t,b in bp:
        if prev:s+=float(tobeat(t)-tobeat(prev[0]))*60/prev[1]
        marks.append((t,s,b));prev=(t,b)
    def at(t):
        t0,s0,b=max((m for m in marks if m[0]<=t),key=lambda m:m[0]);return s0+float(tobeat(t)-tobeat(t0))*60/b
    def tick(sec):   # seconds -> tick (bisect on a monotone function)
        lo,hi=0,max(m[0] for m in marks)+int(sec*40)+tpm*4
        while hi-lo>1:
            mid=(lo+hi)//2
            if at(mid)<=sec:lo=mid
            else:hi=mid
        return lo
    return at,tick,bp,meas

def ez_chart(path,stem_files,title,artist,level,diff,gstart):
    c=ezff.parse(path);jp=Path(str(path).replace('_ez.ez','_instrumentDic.json'))
    names={int(i):s for i,s in json.loads(jp.read_text())} if jp.exists() else {i:re.sub(r'\.\w+$','',f) for i,f in ezff.ezi(str(path).replace('_ez.ez','_ezi.ezi')).items()}
    big=len(set(names.values()))>1290;B=B62 if big else B36
    b36=lambda n:B[n//len(B)]+B[n%len(B)]
    tpm=c['ticks_per_measure'];at,tick,bpms,meas=timing(c);wavs={};code={}
    def wavcode(sid):
        if sid in code:return code[sid]
        stem=names.get(sid)
        if stem is None:return None
        f=stem_files.get(stem.lower(),stem+'.ogg')
        if f not in wavs:wavs[f]=b36(len(wavs)+1)
        code[sid]=wavs[f];return code[sid]
    lanes={};bgm=collections.defaultdict(list);hold={};end=0;mr_tick=None
    for i,(tn,ev) in enumerate(c['tracks']):
        K=int(Path(path).name[0]);ch={3:11,4:12,5:13,6:14,7:15,8:18,9:19,10:16}.get(i) if 3<=i<3+K else None
        for e in ev:
            if e[1]!=1:continue
            p,_,sid,vel,pan,ln=e;cd=wavcode(sid)
            if cd is None:continue
            end=max(end,p)
            if mr_tick is None and names.get(sid,'').lower().startswith('mr'):mr_tick=p
            if ch is None:bgm[(p//tpm,p%tpm)].append(cd);continue
            lanes.setdefault(ch,{}).setdefault(p,cd)
            if ln>6:hold[(ch,p)]=(p+ln,cd)
    ln={}
    for (ch,p),(e,cd) in sorted(hold.items(),key=lambda x:x[0][1]):
        L=lanes[ch];last=ln.get(ch,[])
        if e in L or (last and p<last[-1]) or e<=p:continue
        ln.setdefault(ch,[]).extend([p,e]);L[e]=cd
    lnset={ch:set(v) for ch,v in ln.items()}
    # BGA trigger
    bga=None
    if gstart is not None:
        t0=at(mr_tick if mr_tick is not None else tpm)+gstart;t0=max(t0,0.);k=tick(t0);bga=(k//tpm,k%tpm)
    last_m=max(end//tpm,bga[0] if bga else 0)
    meas=[x for x in meas if x[0]<=(last_m+1)*tpm];bpms=[x for x in bpms if x[0]<=(last_m+1)*tpm]
    bym=collections.defaultdict(list)
    for (m2,r),cds in sorted(bgm.items()):bym[m2].append((r,cds))
    bpmcode={}
    for _,b in bpms:bpmcode.setdefault(round(b,4),b36(len(bpmcode)+1))
    two=any(ch>=20 for ch in lanes)
    h=['*---------------------- HEADER FIELD','#PLAYER '+('3' if two else '1'),'#GENRE EZ2ON','#TITLE '+title,'#SUBTITLE ['+Path(path).stem.split('_')[0].upper()+' '+diff.upper()+']','#ARTIST '+artist,f'#BPM {round(bpms[0][1],4)}',f'#PLAYLEVEL {level}','#DIFFICULTY '+str(DIFF.get(diff,4)),'#RANK 2','#LNTYPE 1']+(['#BASE 62'] if big else [])+['#STAGEFILE Banner.png','#BANNER Banner.png','#BMP01 BGA.mp4','*source: EZ2ON REBOOT R '+Path(path).name]
    for f,cd in wavs.items():h.append(f'#WAV{cd} {f}')
    for b,cd in bpmcode.items():h.append(f'#BPM{cd} {b}')
    body=['','*---------------------- MAIN DATA FIELD'];cur=4;mset={p//tpm for p,_ in meas}
    bpm_m=collections.defaultdict(dict)
    for p,b in bpms:
        if p>0:bpm_m[p//tpm][p%tpm]=bpmcode[round(b,4)]
    meas_m={}
    for p,n in meas:meas_m[p//tpm]=n
    lane_m=collections.defaultdict(lambda:collections.defaultdict(dict))
    for ch,L in lanes.items():
        for p,cd in L.items():lane_m[ch][p//tpm][p%tpm]=cd
    for mi in range(last_m+1):
        if mi in meas_m:cur=meas_m[mi]
        if mi in mset and cur!=4:body.append(f'#{mi:03d}02:{cur/4:g}')
        sl=bpm_m.get(mi)
        if sl:body.append(f'#{mi:03d}08:{row(sl,tpm)}')
        if bga and bga[0]==mi:body.append(f'#{mi:03d}04:{row({bga[1]:"01"},tpm)}')
        lay=[]
        for r,cds in bym.get(mi,()):
            for k,cd in enumerate(cds):
                while len(lay)<=k:lay.append({})
                lay[k][r]=cd
        for layer in lay:body.append(f'#{mi:03d}01:{row(layer,tpm)}')
        for ch,L in sorted(lanes.items()):
            sl=lane_m[ch].get(mi)
            if not sl:continue
            lp=lnset.get(ch,set());a={p:cd for p,cd in sl.items() if mi*tpm+p not in lp};b={p:cd for p,cd in sl.items() if mi*tpm+p in lp}
            if a:body.append(f'#{mi:03d}{ch:02d}:{row(a,tpm)}')
            if b:body.append(f'#{mi:03d}{ch+40:02d}:{row(b,tpm)}')
    return '\n'.join(h+body)+'\n',dict(chart=Path(path).stem,notes=sum(len(v) for v in lanes.values()),holds=sum(len(v)//2 for v in ln.values()),bga=bool(bga))

def song(name):
    d=SRC/name;out=OUT/name;mark=out/'done.json'
    if mark.exists():return json.loads(mark.read_text())
    out.mkdir(parents=True,exist_ok=True);res=dict(song=name,mode=None,charts=[],errors=[])
    for f in ('Song.mp3','Song.flac','Song.ogg','BGA.mp4','BGA.webm','Banner.png','Cover.png','PreviewAudio.ogg'):
        if (d/f).exists():link(d/f,out/f)
    snd=d/'Sound';stem_files={}
    if snd.is_dir():
        for f in snd.iterdir():
            link(f,out/f.name);stem_files[f.stem.lower()]=f.name
    ch=d/'Charts';ezs=sorted(ch.glob('*_ez.ez')) if ch.is_dir() else []
    js=sorted(ch.glob('*S_*.json')) if ch.is_dir() else []
    meta=json.loads(js[0].read_text(encoding='utf8')) if js else {}
    title=meta.get('title') or name;artist=meta.get('artist','')
    levels={}
    for j in js:
        m=json.loads(j.read_text(encoding='utf8'));levels[j.stem.lower()]=m.get('level',0)   # '4s_shd'
    gs=bga_start(name)
    if ezs:
        res['mode']='keysound'
        for e in ezs:
            n,dif=e.name.split('_')[:2]  # 4k,shd
            try:
                txt,info=ez_chart(e,stem_files,title,artist,levels.get(f'{n[0]}s_{dif}',0),dif,gs)
                (out/f'{n[0]}S_{dif.upper()}.bms').write_text(txt,encoding='utf8');res['charts'].append(info)
            except Exception as x:res['errors'].append(dict(chart=e.name,error=repr(x)[:200]))
    else:
        bms=sorted(d.glob('*.bms'))
        if bms:res['mode']='ez2pattern'
        for b in bms:
            t=b.read_text(encoding='utf8').splitlines();bpm=next((float(l.split()[1]) for l in t if l.startswith('#BPM ')),None)
            add=['#STAGEFILE Banner.png','#BANNER Banner.png','#BMP01 BGA.mp4']
            t=[l for l in t if not l.startswith(('#STAGEFILE','#BANNER','#BMP01'))]
            sy=SYNC.get(name);lag=sy.get('lag_ms') if sy else None;T0=None
            if lag is not None and (d/'Song.mp3').exists():
                # measured: time in Song.mp3 = chart time + lag  ->  Song.mp3 starts at chart time -lag
                T0=-lag/1000;sm=out/'Song_sync.mp3'
                if not sm.exists():
                    if T0>0:cmd=['ffmpeg','-v','error','-y','-i',str(d/'Song.mp3'),'-af',f'adelay={int(round(T0*1000))}:all=1','-q:a','2',str(sm)]
                    else:cmd=['ffmpeg','-v','error','-y','-ss',str(-T0),'-i',str(d/'Song.mp3'),'-q:a','2',str(sm)]
                    subprocess.run(cmd,check=True)
                t=[l for l in t if not re.match(r'^#\d{3}01:',l)]
                t=[('#WAV01 Song_sync.mp3' if l.startswith('#WAV01') else l) for l in t]
                res['sync']=sy.get('status')
            i=next((k for k,l in enumerate(t) if l.startswith('#WAV01')),1);t[i:i]=add
            j=next((q for q,l in enumerate(t) if l.startswith('*---') and 'MAIN' in l),len(t)-1)
            if T0 is not None:t.insert(j+1,'#00001:01')
            if gs is not None and bpm and (d/'BGA.mp4').exists():
                T=max((T0 if T0 is not None else 4*60/bpm)+gs,0.);beats=T*bpm/60;mi=int(beats//4);k=int(round((beats-4*mi)/4*192)) # constant first-BPM approximation
                if k>=192:mi+=1;k=0
                t.insert(j+1,f'#{mi:03d}04:{row({k:"01"},192)}')
            (out/b.name).write_text('\n'.join(t)+'\n',encoding='utf8');res['charts'].append(dict(chart=b.stem))
    mark.write_text(json.dumps(res,indent=1));return res

if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    songs=sys.argv[1:] or sorted(p.name for p in SRC.iterdir() if p.is_dir() and not p.name.startswith('_'))
    allres=[]
    for s in songs:
        r=song(s);allres.append(r);print('EZ2ON_BMS',s,r['mode'],len(r['charts']),'charts',r['errors'][:1],flush=True)
    (OUT/'resumen.json').write_text(json.dumps(allres,indent=1))
    print('DONE',len(allres),'songs',sum(len(r['charts']) for r in allres),'charts',sum(len(r['errors']) for r in allres),'errors')
