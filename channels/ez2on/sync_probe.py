"""Offset between an ez2pattern chart (time_ms, t=0 = measure 1) and Song.mp3: cross-correlate the chart's note
train with the audio onset envelope. Each mode (4S/5S/6S/8S...) is an independent measurement."""
import json,glob,os,subprocess,sys,numpy as np
FF=glob.glob(os.path.expandvars('%LOCALAPPDATA%/Microsoft/WinGet/Packages/Gyan.FFmpeg*/ffmpeg-*/bin/ffmpeg.exe'))[0]
SR=11025;HOP=110   # ~10 ms frames
def onset(mp3):
    x=np.frombuffer(subprocess.check_output([FF,'-v','error','-i',mp3,'-ac','1','-ar',str(SR),'-f','f32le','-']),np.float32)
    n=(len(x)-1024)//HOP;idx=np.arange(1024)[None,:]+HOP*np.arange(n)[:,None]
    S=np.abs(np.fft.rfft(x[idx]*np.hanning(1024),axis=1));S=np.log1p(100*S)
    f=np.maximum(np.diff(S,axis=0),0).sum(1);f=f-np.convolve(f,np.ones(50)/50,'same')   # local-mean removed flux
    return np.maximum(f,0)/ (f.std()+1e-9)
def train(times,n):
    t=np.zeros(n);i=(np.asarray(times)/1000*SR/HOP).astype(int);i=i[(i>=0)&(i<n)];np.add.at(t,i,1)
    return np.convolve(t,[.25,.5,1,.5,.25],'same')
def lag(env,times,lo=-3000,hi=8000):
    n=len(env);tr=train(times,n);ls=np.arange(int(lo/1000*SR/HOP),int(hi/1000*SR/HOP))
    sc=np.array([np.dot(env[max(0,l):n+min(0,l)],tr[max(0,-l):n-max(0,l)]) for l in ls])/max(1,len(times))
    b=sc.argmax();ms=ls[b]*HOP/SR*1000
    mask=np.abs(ls-ls[b])>int(0.06*SR/HOP);second=sc[mask].max()
    return ms,sc[b],sc[b]/second,ls*HOP/SR*1000,sc
if __name__=='__main__':
    org,ch=sys.argv[1],sys.argv[2]
    env=onset(os.path.join(r'D:\eeez2abackup\EZ2ON_ORGANIZADO',org,'Song.mp3'))
    for jf in sorted(glob.glob(os.path.join(r'D:\eeez2abackup\ez2on_charts',ch,'*_*.json'))):
        d=json.load(open(jf,encoding='utf8'));t=[x['time_ms'] for x in d['notes']]
        ms,s,r,_,_=lag(env,t);print(os.path.basename(jf),'bpm',d['initial_bpm'],'lag_ms',round(ms),'score',round(s,2),'peak/2nd',round(r,2),'beat_ms',round(60000/d['initial_bpm']))
