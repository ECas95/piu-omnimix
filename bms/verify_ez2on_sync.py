"""Independent sync check for ez2pattern-mode EZ2ON songs.
For each song with a measured lag: (time of the song object `02` in the BMS) - (BMS first-note time - JSON first-note time)
must equal -lag_ms (the lag is expressed in the JSON clock that the PIU conversion used)."""
import json,re,glob,os,collections
S=json.load(open(r'D:\EZ2ON_PIU\sync_final.json'))
def tables(t):
    base=float(re.search(r'^#BPM ([\d.]+)',t,re.M).group(1))
    tab={m.group(1).upper():float(m.group(2)) for m in re.finditer(r'^#BPM(\w\w) ([\d.]+)',t,re.M)}
    ln={int(m.group(1)):float(m.group(2)) for m in re.finditer(r'^#(\d{3})02:([\d.]+)',t,re.M)}
    ev=collections.defaultdict(list)
    for m in re.finditer(r'^#(\d{3})08:(\w+)',t,re.M):
        cs=[m.group(2)[k:k+2] for k in range(0,len(m.group(2)),2)]
        for k,c in enumerate(cs):
            if c!='00' and c.upper() in tab:ev[int(m.group(1))].append((k/len(cs),tab[c.upper()]))
    return base,ln,ev
def pos_time(t,mi,f):
    base,ln,ev=tables(t);bpm=base;tt=0.
    for m in range(mi+1):
        L=ln.get(m,1.);prev=0.;tgt=f if m==mi else 1.
        for ff,v in sorted(ev.get(m,[])):
            if ff>=tgt:break
            tt+=(ff-prev)*4*L*60/bpm;prev=ff;bpm=v
        tt+=(tgt-prev)*4*L*60/bpm
    return tt*1000
def first_note(t):
    notes=[]
    for m in re.finditer(r'^#(\d{3})(1[1-9]|5[1-9]):(\w+)$',t,re.M):
        cs=[m.group(3)[i:i+2] for i in range(0,len(m.group(3)),2)]
        notes+=[(int(m.group(1)),i/len(cs)) for i,c in enumerate(cs) if c!='00']
    return pos_time(t,*min(notes))
ok=bad=skip=trim=0;worst=[]
for d in sorted(glob.glob(r'D:\PIU_PRESERVADO\BMS_EZ2ON\*')):
    dn=os.path.join(d,'done.json')
    if not os.path.exists(dn) or json.load(open(dn)).get('mode')!='ez2pattern':continue
    name=os.path.basename(d);s=S.get(name);lag=(s or {}).get('lag_ms')
    if lag is None:skip+=1;continue
    for b in glob.glob(os.path.join(d,'*.bms'))[:1]:
        t=open(b,encoding='utf8').read()
        if '#WAV02 Song_sync.mp3' in t:trim+=1;continue   # lag so positive that the song is trimmed and placed at 0
        jf=rf"D:\eeez2abackup\ez2on_charts\{s['chart']}\{os.path.basename(b)[:-4]}.json"
        jt=min(n['time_ms'] for n in json.load(open(jf,encoding='utf8'))['notes'])
        m=re.search(r'^#(\d{3})01:(\w+)$',t,re.M);cs=[m.group(2)[k:k+2] for k in range(0,len(m.group(2)),2)]
        audio=pos_time(t,int(m.group(1)),cs.index('02')/len(cs))
        start_json=audio-(first_note(t)-jt)
        err=abs(start_json-(-lag))
        if err<=15:ok+=1
        else:bad+=1;worst.append((name,round(err,1)))
print('ok',ok,'off by >15 ms',bad,'trimmed',trim,'no measurement',skip);print(sorted(worst,key=lambda x:-x[1])[:10])
