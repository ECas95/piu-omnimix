"""Onset strength at each lag for one finished song: mean onset under the note times, per chart source. Prints the profile peaks so an off-beat peak is not read as a chart offset."""
import json,sys
from pathlib import Path
import numpy as np
H=Path(__file__).resolve().parent;B=Path('D:/Pump It Up Data/PIU');sys.path[:0]=[str(B/'anime_channel_dng/engine'),str(B)]
sys.dont_write_bytecode=True
import nx20,quality_charting as Q,sync_nuevas as S
AR=S.AR
for f in sorted((H/'songs').glob('*/result.json')):
    r=json.loads(f.read_text(encoding='utf8'));t=r['tags'].get('TITLE','')
    if sys.argv[1:] and not any(a in t for a in sys.argv[1:]):continue
    x=S.pcm(H/'songs'/r['key']/'audio.wav');hop=8000//AR;env=np.sqrt(np.convolve(x**2,np.ones(hop)/hop,'same')[::hop]);on=np.clip(np.diff(env),0,None);on=on/(on.mean()+1e-9)
    print(t[:30],'bpm',str(r.get('bpm'))[:30].replace('\n',''),'first offset tag',r['tags'].get('OFFSET'),'audio',str(r.get('audio'))[-30:])
    for c in r['refs']:
        if 'nx' not in c:continue
        ns=sorted({n[1] for n in Q.notes_of(nx20.parse(Path(c['nx']).read_bytes()))});tt=np.array(ns)/1000;ls=np.arange(-60,61);sc=[]
        for l in ls:
            i=np.rint(tt*AR).astype(int)+l;i=i[(i>=0)&(i<len(on))];sc.append(on[i].mean())
        sc=np.array(sc);pk=[int(ls[k]*5) for k in range(1,len(ls)-1) if sc[k]>sc[k-1] and sc[k]>=sc[k+1] and sc[k]>sc.mean()+sc.std()]
        print('  ',c['chart'][:24],'notes',len(ns),'peak',int(ls[sc.argmax()]*5),'ms',round(sc.max(),2),'at0',round(sc[60],2),'local peaks ms',pk)
