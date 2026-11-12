"""Sabin Sound Star -> BMS, every song / every chart (keyboard 1x, 2x and percussion 3x).
Per song folder: <chart>.bms, decoded keysound wavs, song.mp3 (autoplay mix), banner.png, bga.mp4 (start padded to the game's .del)
Lane map (track -> BMS channel; best effort, documented in LEEME): 3-7 keys1-5 (11-15), 8 key6 (18), 9 key7 (19), 10 scratch (16),
11 pedal (17); 2P: 12-16 (21-25), 17 (28), 18 (29), 19 (26), 20 pedal (27). Playable tracks depend on the mode digit.
Usage: python -I sss_to_bms.py [song ...]"""
from pathlib import Path
from math import gcd
import sys,json,re,subprocess,shutil,os
from concurrent.futures import ProcessPoolExecutor
sys.dont_write_bytecode=True
sys.path[:0]=[r'D:\SSS']
import sss
OUT=Path(r'D:\PIU_PRESERVADO\BMS_SSS');SSS=Path(r'D:\SSS')
MAP={3:11,4:12,5:13,6:14,7:15,8:18,9:19,10:16,11:17,12:21,13:22,14:23,15:24,16:25,17:28,18:29,19:26,20:27}
PLAY={'1':{3,4,5,6,7,8,11},'2':{3,4,5,6,7,8,11,12,13,14,15,16,19},'3':{8,9,10,17,18,19}}
B36='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
def b36(n):return B36[n//36]+B36[n%36]
def row(slots,n):   # {pos:code} in n slots -> reduced string
    g=n
    for p in slots:g=gcd(g,p)
    n//=g;s=['00']*n
    for p,c in slots.items():s[p//g]=c
    return ''.join(s)

def build(path,title,artist):
    c=sss.parse(path);name=path.stem.split('_',1)[-1];m=re.search(r'\d',name);play=PLAY.get(m.group(0) if m else '3',PLAY['3'])
    tpm=c['ticks_per_measure'];tobeat,bpms,_=sss.timing(c)
    ids=sorted(c['sounds']);wavs={};real={q.name.lower():q.name for q in path.parent.iterdir()}
    for i in ids:
        f=c['sounds'][i][1];c['sounds'][i]=(c['sounds'][i][0],real.get(f.lower(),f));f=c['sounds'][i][1]
        if f not in wavs:wavs[f]=b36(len(wavs)+1)
    code=lambda a:wavs[c['sounds'][a[0]][1]] if a[0] in c['sounds'] else None
    tr=c['tracks'];meas=sorted({p:a[0] for t in tr for p,k,a in t[1] if k==4}.items())
    lanes={};bgm={};hold={}
    end=0
    for i,(tn,ev) in enumerate(tr):
        if i==0:continue
        ch=MAP.get(i) if i in play and i in MAP else None
        for p,k,a in ev:
            if k!=1:continue
            cd=code(a)
            if cd is None:continue
            end=max(end,p)
            if ch is None:bgm.setdefault((p//tpm,p%tpm),[]).append(cd);continue
            length=int.from_bytes(a[4:6],'little')
            lanes.setdefault(ch,{}).setdefault(p,cd)
            if length>6:hold[(ch,p)]=(p+length,cd)
    # holds -> LN pairs (channel +40); a tail on an existing note or an overlap stays a tap
    ln={};
    for (ch,p),(e,cd) in sorted(hold.items(),key=lambda x:x[0][1]):
        L=lanes[ch];last=ln.get(ch,[])
        if e in L or (last and p<last[-1]) or e<=p:continue
        ln.setdefault(ch,[]).extend([p,e]);L[e]=cd;lanes[ch].pop(p);L[p]=cd
    lnset={ch:set(v) for ch,v in ln.items()}
    last_m=max(end//tpm,max((p//tpm for p,_ in meas),default=0),max((p//tpm for p,_ in bpms),default=0))
    bpmcode={};
    for _,b in bpms:bpmcode.setdefault(round(b,4),b36(len(bpmcode)+1))
    h=['*---------------------- HEADER FIELD','#PLAYER '+('3' if any(25>=x>=21 or x in(26,27,28,29) for x in lanes) else '1'),'#GENRE Sabin Sound Star','#TITLE '+title,'#SUBTITLE ['+name+']','#ARTIST '+artist,f'#BPM {round(bpms[0][1],4)}','#PLAYLEVEL 0','#RANK 3','#LNTYPE 1','#STAGEFILE banner.png','#BANNER banner.png','#BACKBMP banner.png','#BMP01 bga.mp4','#DIFFICULTY '+{'e':'1','n':'2','h':'3'}.get(name[1:2].lower() if m else '', '4'),
       '*source: Sabin Sound Star Renascence Burst '+path.name]
    for f,cd in wavs.items():h.append(f'#WAV{cd} {f}')
    for b,cd in bpmcode.items():h.append(f'#BPM{cd} {b}')
    body=['','*---------------------- MAIN DATA FIELD']
    mlen=dict(meas)
    cur=4
    cache={}
    for mi in range(last_m+1):
        for p,n in meas:
            if p//tpm==mi:cur=n
        if cur!=4 or (mi in {p//tpm for p,_ in meas}):body.append(f'#{mi:03d}02:{cur/4:g}')
        # BPM changes
        sl={p%tpm:bpmcode[round(b,4)] for p,b in bpms if p//tpm==mi and p>0}
        if sl:body.append(f'#{mi:03d}08:{row(sl,tpm)}')
        if mi==0:body.append('#00004:01')
        lay=[[ ]];
        for (m2,r),cds in sorted(bgm.items()):
            if m2!=mi:continue
            for k,cd in enumerate(cds):
                while len(lay)<=k:lay.append([])
                lay[k].append((r,cd))
        for layer in lay:
            if layer:body.append(f'#{mi:03d}01:{row(dict(layer),tpm)}')
        for ch,L in sorted(lanes.items()):
            sl={p%tpm:cd for p,cd in L.items() if p//tpm==mi}
            if not sl:continue
            lnp={q for q in lnset.get(ch,())}
            a={p:cd for p,cd in sl.items() if not any(q==mi*tpm+p for q in lnp)}
            b={p:cd for p,cd in sl.items() if any(q==mi*tpm+p for q in lnp)}
            if a:body.append(f'#{mi:03d}{ch:02d}:{row(a,tpm)}')
            if b:body.append(f'#{mi:03d}{ch+40:02d}:{row(b,tpm)}')
    return '\n'.join(h+body)+'\n',dict(chart=name,notes=sum(len(v) for v in lanes.values()),bgm=sum(len(v) for v in bgm.values()),holds=sum(len(v)//2 for v in ln.values()),lanes=sorted(lanes))

def start_s(song):
    d=sss.GAME/'movie'/(song+'.del')
    if d.exists():return int(d.read_text().strip())/1000
    ov=json.loads((SSS/'bga_delay_override.json').read_text())
    return ov.get(song,{}).get('start_s',1.5)

def one(song):
    out=OUT/song;marker=out/'done.json'
    if marker.exists():return json.loads(marker.read_text())
    out.mkdir(parents=True,exist_ok=True);src=sss.GAME/'data'/song;res=dict(song=song,charts=[],errors=[])
    titles=json.loads((SSS/'titles.json').read_text(encoding='utf8')).get(song,{})
    title=titles.get('display') or titles.get('title') or song;artist=titles.get('artist','')
    for f in src.glob('*.wav'):(out/f.name).write_bytes(sss.wav(f))
    for f in sorted(src.glob('*.sss')):
        try:
            txt,info=build(f,title,artist);(out/(f.stem.split('_',1)[-1]+'.bms')).write_text(txt,encoding='utf8');res['charts'].append(info)
        except Exception as e:res['errors'].append(dict(chart=f.name,error=repr(e)[:200]))
    # audio mix
    wav=SSS/'audio'/(song+'.wav')
    if not wav.exists() and res['charts']:
        import sss_audio
        best=max(sorted(src.glob('*.sss')),key=lambda p:p.stat().st_size)
        try:sss_audio.render(song,best)
        except Exception as e:res['errors'].append(dict(audio=repr(e)[:200]))
    if wav.exists():subprocess.run(['ffmpeg','-v','error','-y','-i',str(wav),'-q:a','2',str(out/'song.mp3')],check=True)
    # bga
    bik=sss.GAME/'movie'/(song+'.bik')
    if bik.exists():
        d=start_s(song);vf='tpad=start_duration=%s:color=black'%d if d>0 else 'null';ss=['-ss',str(-d)] if d<0 else []
        af=[]
        subprocess.run(['ffmpeg','-v','error','-y',*ss,'-i',str(bik),'-an','-vf',vf,'-c:v','libx264','-crf','23','-preset','fast','-pix_fmt','yuv420p',str(out/'bga.mp4')],check=True)
        res['bga_start_s']=d
    # banner
    st=SSS/'stills'/(song+'.png')
    if st.exists():shutil.copy(st,out/'banner.png')
    else:
        import sss_banners as B
        p=next((x for x in (B.plate(n) for n in (song,titles.get('exe_title',''))if n) if x),None)
        if p is not None and bik.exists():B.card(p,bik).save(out/'banner.png')
        elif bik.exists():
            subprocess.run(['ffmpeg','-v','error','-y','-ss','25','-i',str(bik),'-frames:v','1',str(out/'banner.png')])
    marker.write_text(json.dumps(res,indent=1));return res

if __name__=='__main__':
    songs=sys.argv[1:] or sorted(p.name for p in (sss.GAME/'data').iterdir() if p.is_dir())
    OUT.mkdir(parents=True,exist_ok=True);allres=[]
    with ProcessPoolExecutor(3) as ex:
        for r in ex.map(one,songs):allres.append(r);print('SSS_BMS',r['song'],len(r['charts']),'charts',r['errors'][:2],flush=True)
    (OUT/'resumen.json').write_text(json.dumps(allres,indent=1))
    print('DONE',len(allres),'songs',sum(len(r['charts']) for r in allres),'charts',sum(len(r['errors']) for r in allres),'errors')
