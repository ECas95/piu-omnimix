"""Check keysounded EZ2ON BMS against ez2pattern JSON (same chart): note-head count and referenced files."""
import json,re,os,glob,sys
from pathlib import Path
O=Path(r'D:\PIU_PRESERVADO\BMS_EZ2ON');S=Path(r'D:\eeez2abackup\EZ2ON_ORGANIZADO')
ok=bad=nojson=miss=0;badl=[]
for d in sorted(O.iterdir()):
    dn=d/'done.json'
    if not dn.exists() or json.loads(dn.read_text()).get('mode')!='keysound':continue
    for b in d.glob('*.bms'):
        t=b.read_text(encoding='utf8').replace(chr(13),'');heads=0
        for m in re.finditer(r'^#\d{3}(\d\d):(\w+)$',t,re.M):
            ch=int(m.group(1));cells=[m.group(2)[i:i+2] for i in range(0,len(m.group(2)),2)]
            n=sum(c!='00' for c in cells)
            if 11<=ch<=29 and ch%10!=0:heads+=n
            elif 51<=ch<=69:heads+=n/2
        for w in re.findall(r'^#WAV\w\w (.+)$',t,re.M):
            if not (d/w).exists():miss+=1;break
        j=S/d.name/'Charts'/(b.stem+'.json')
        if not j.exists():nojson+=1;continue
        n=len(json.loads(j.read_text(encoding='utf8'))['notes'])
        if abs(n-heads)<=max(2,n*0.005):ok+=1
        else:bad+=1;badl.append((d.name,b.name,n,heads))
print('ok',ok,'bad',bad,'no json',nojson,'charts with missing wav',miss);print(badl[:15])
