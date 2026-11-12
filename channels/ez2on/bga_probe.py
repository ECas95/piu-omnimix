"""BGA.mp4 <-> Song.mp3: video activity (frame-to-frame change at 100 fps-equivalent) vs audio onset envelope.
time in Song.mp3 = video time + lag."""
import measure_sync as M,numpy as np,subprocess,os,sys,json
FP=M.FF.replace('ffmpeg.exe','ffprobe.exe')
def dur(f):return float(subprocess.run([FP,'-v','error','-show_entries','format=duration','-of','csv=p=0',f],capture_output=True,text=True).stdout)
def vact(f,w=32,h=18,fps=50):
    raw=subprocess.check_output([M.FF,'-v','error','-i',f,'-an','-vf',f'fps={fps},scale={w}:{h},format=gray','-f','rawvideo','-'])
    v=np.frombuffer(raw,np.uint8).reshape(-1,h*w).astype(np.float32);d=np.abs(np.diff(v,axis=0)).mean(1)
    d=np.repeat(d,2)   # 50 fps -> 100 Hz frames (~M.FPS)
    d-=np.convolve(d,np.ones(50)/50,'same');return np.maximum(d,0)/(d.std()+1e-9)
def measure(folder,bga):
    song=os.path.join(M.O,folder,'Song.mp3');sb=M.bands(song).sum(1);va=vact(bga)
    va=np.interp(np.arange(0,len(va)*100/M.FPS,100/M.FPS)[:int(len(va)*M.FPS/100)],np.arange(len(va)),va)   # resample 100 Hz -> FPS
    L,S=M.xcorr(sb,va,-15000,15000);return dict(song_s=dur(song),bga_s=dur(bga),peaks=M.peaks(L,S),fine=round(M.refine(L,S,int(np.argmax(S))),1))
if __name__=='__main__':
    for s in sys.argv[1:]:print(s,measure(s,os.path.join(M.O,s,'BGA.mp4')))
