"""Per song: first sound, first picture, comb score by shift, and the same over the whole population for the current treatment. usage: sync_caso.py ids..."""
import json,subprocess,sys
from pathlib import Path
import numpy as np
H=Path(__file__).resolve().parent;R=30
sel={r['source_folder']:r for r in json.load(open('D:/PIU_INFINITY/channels/selection.json',encoding='utf8'))['records'] if r['channel']=='IIDX'}
def comb(e,T,off,shift):
    n=len(e);t0=(off+shift)%(T/2);fr=np.rint((t0+np.arange(int(n/R/(T/2))+1)*T/2)*R).astype(int)-1;fr=fr[(fr>=0)&(fr<n)];return float(e[fr].mean()/(e.mean()+1e-6))
for sid in sys.argv[1:]:
    r=sel[sid];res=json.loads((H/'canal/songs'/sid/'result.json').read_text(encoding='utf8'));ref=max(res['refs'],key=lambda x:x['heads']);T=60/ref['bpms'][0][1];off=ref['offset_s']
    d=np.load(H/'cache_cortes'/f'{sid}.npy').astype(np.float64);e=np.clip(d-np.convolve(d,np.ones(9)/9,'same'),0,None)
    x=np.frombuffer(subprocess.run(['ffmpeg','-v','error','-i',str(H/'canal/songs'/sid/'audio.wav'),'-ac','1','-ar','8000','-f','f32le','-'],capture_output=True).stdout,np.float32);a=np.abs(x);first=int(np.argmax(a>.02))/8000
    active=np.nonzero(d>2)[0];print(sid,r['title'],'delay',round(r['video_segments'][0]['seconds']*1000),'bpm',ref['bpms'][:2],'T',round(T,3),'first sound',round(first,2),'first picture change',round(active[0]/R,2) if len(active) else None,'movie',round(len(d)/R,1),'audio',round(len(x)/8000,1))
    sh=np.arange(-T/2,T/2,1/R);sc=[comb(e,T,off,s) for s in sh];k=int(np.argmax(sc));print('   comb best shift ms',round(sh[k]*1000),'score',round(sc[k],2),'at 0:',round(comb(e,T,off,0),2),'at -delay',round(comb(e,T,off,-r['video_segments'][0]['seconds']),2),'at +delay',round(comb(e,T,off,r['video_segments'][0]['seconds']),2))
    ev=e[:int(90*R)];big=np.nonzero(ev>np.percentile(ev,99))[0]/R;print('   strong cuts s',[round(float(v),2) for v in big[:16]],'beats',[round(float(v/T),2) for v in big[:16]])
