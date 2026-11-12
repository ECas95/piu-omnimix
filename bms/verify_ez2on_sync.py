"""For every ez2pattern-mode EZ2ON song: the audio object (wav 02) must sit at -lag_ms (time in Song.mp3 = chart time + lag)."""
import json,re,glob,os,collections
S=json.load(open(r'D:\EZ2ON_PIU\sync_final.json'))
def pos_time(t,mi,i,n):
    base=float(re.search(r'^#BPM ([\d.]+)',t,re.M).group(1))
    tab={m.group(1).upper():float(m.group(2)) for m in re.finditer(r'^#BPM(\w\w) ([\d.]+)',t,re.M)}
    ln={int(m.group(1)):float(m.group(2)) for m in re.finditer(r'^#(\d{3})02:([\d.]+)',t,re.M)}
    ev=collections.defaultdict(list)
    for m in re.finditer(r'^#(\d{3})08:(\w+)',t,re.M):
        cs=[m.group(2)[k:k+2] for k in range(0,len(m.group(2)),2)]
        for k,c in enumerate(cs):
            if c!='00' and c.upper() in tab:ev[int(m.group(1))].append((k/len(cs),tab[c.upper()]))
    bpm=base;tt=0.
    for m in range(mi+1):
        L=ln.get(m,1.);prev=0.;tgt=(i/n) if m==mi else 1.
        for f,v in sorted(ev.get(m,[])):
            if f>=tgt:break
            tt+=(f-prev)*4*L*60/bpm;prev=f;bpm=v
        tt+=(tgt-prev)*4*L*60/bpm
        for f,v in ev.get(m,[]):
            if f>=tgt:continue
    return tt
ok=bad=skip=0;worst=[]
for d in sorted(glob.glob(r'D:\PIU_PRESERVADO\BMS_EZ2ON\*')):
    dn=os.path.join(d,'done.json')
    if not os.path.exists(dn) or json.load(open(dn)).get('mode')!='ez2pattern':continue
    name=os.path.basename(d);lag=(S.get(name) or {}).get('lag_ms')
    if lag is None:skip+=1;continue
    for b in glob.glob(os.path.join(d,'*.bms'))[:1]:
        t=open(b,encoding='utf8').read()
        if '#WAV02 Song_sync.mp3' in t:ok+=1;continue   # trimmed song at 0 (lag > 0)
        m=re.search(r'^#(\d{3})01:(\w+)$',t,re.M);cs=[m.group(2)[k:k+2] for k in range(0,len(m.group(2)),2)]
        tm=pos_time(t,int(m.group(1)),cs.index('02'),len(cs))
        err=abs(tm-(-lag/1000))*1000
        if err<=15:ok+=1
        else:bad+=1;worst.append((name,round(err,1)))
print('ok',ok,'off by >15 ms',bad,'no measurement',skip);print(sorted(worst,key=lambda x:-x[1])[:10])
