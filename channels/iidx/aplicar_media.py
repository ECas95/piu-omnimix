from pathlib import Path
import shutil
M=Path('D:/PIU_INFINITY/channels/prepare_media.py');b=M.with_name(M.name+'.before_iidx')
if not b.exists():shutil.copy2(M,b)
s=M.read_bytes().decode('utf8');crlf='\r\n' in s;s=s.replace('\r\n','\n')
def rep(o,n):
    global s
    assert s.count(o)==1,o[:70];s=s.replace(o,n)
rep("RATES={'EZ2ON':('3500k','1000k')}","RATES={'EZ2ON':('3500k','1000k'),'IIDX':('2600k','600k')}   # IIDX: PRIME's own HD rate (1356 songs)")
rep("    for i,g in enumerate(segs,1):\n","    crop='crop=iw:iw*9/16,' if s.get('crop_16_9') else ''   # user 2026-11: 4:3 movies cut top and bottom to 16:9\n    for i,g in enumerate(segs,1):\n")
rep("fps=30,scale=1280:720,setsar=1,format=yuv420p,trim=start=","fps=30,{crop}scale=1280:720,setsar=1,format=yuv420p,trim=start=")
i=s.index("    sd=dest/'V/SD/.V'");j=s.index("    # preview movies",i);block=s[i:j]
s=s[:i]+"    if s['channel']!='IIDX':   # IIDX ships HD only: its SD movies would never be packed\n"+''.join(' '+l for l in block.splitlines(True))+s[j:]
rep("    for q,w,h in (('HD',464,264),('SD',312,176)):\n","    for q,w,h in (('HD',464,264),('SD',312,176))[:1 if s['channel']=='IIDX' else 2]:\n")
M.write_bytes((s.replace('\n','\r\n') if crlf else s).encode('utf8'))
p=Path('D:/SSS/sss_charts.py');b=p.with_name(p.name+'.before_iidx')
if not b.exists():shutil.copy2(p,b)
t=p.read_bytes().decode('utf8');o="key=lambda x:min(abs(x[0]-t) for t in taken),default=(None,None))"
if o in t:p.write_bytes(t.replace(o,"key=lambda x:min(abs(x[0]-t) for t in taken),default=(None,(None,None)))").encode('utf8'))
print('ok')
