"""Stock channel voices (EFF_CH*) in the base game: format and level, to match the user's new channel voices. Read only."""
import sys,re,io,wave,subprocess,json
from pathlib import Path
import numpy as np
E=Path('E:/Pump It Up Data/PIU');sys.path[:0]=[str(E),str(E/'nsde_channel')]
sys.dont_write_bytecode=True
from current_parent import load
P,g=load();t=g.get('/CONFIG/SFX/SELECT.TXT').decode('latin1')
m=re.findall(r'(EFF_CH\d+)\s*=\s*"([^"]+)"',t);print(len(m),m[:6],m[-4:])
for k,f in m[:20]:
    try:b=g.get('/'+f.upper())
    except Exception as e:print(k,f,'missing');continue
    x=subprocess.run(['ffmpeg','-v','error','-i','-','-ac','1','-ar','48000','-f','f32le','-'],input=b,capture_output=True).stdout;a=np.frombuffer(x,np.float32)
    hdr=subprocess.run(['ffprobe','-v','error','-show_entries','stream=codec_name,sample_rate,channels','-of','csv=p=0','-'],input=b,capture_output=True,text=False).stdout.decode().strip()
    v=a[np.abs(a)>0.01];print(k,f,hdr,'dur',round(len(a)/48000,2),'peak dB',round(20*np.log10(np.abs(a).max()+1e-9),1),'rms(active) dB',round(10*np.log10((v**2).mean()+1e-12),1))
