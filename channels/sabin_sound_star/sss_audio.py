"""SSS song audio (keysounded game): mix of every note of the hardest Percussion chart (BGM + background tracks +
the 6 pads) at its tick on the chart clock (sss.seconds, tick 0 = 0 s, same as the reference charts' OFFSET 0).
Velocity = a[1]/127, pan = a[2] (64 centre); each sample plays to its end. Output audio/<song>.wav, 48 kHz stereo."""
from pathlib import Path
import sys,json,subprocess,collections
import numpy as np
from concurrent.futures import ThreadPoolExecutor
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H));import sss
SR=48000
def load(p):
    raw=subprocess.run(['ffmpeg','-v','error','-f','wav','-i','-','-f','f32le','-ac','2','-ar',str(SR),'-'],input=sss.wav(p),capture_output=True,check=True).stdout
    return np.frombuffer(raw,np.float32).reshape(-1,2)

def render(song,chart):
    c=sss.parse(chart);at=sss.seconds(c);files={p.name.lower():p for p in chart.parent.iterdir()};cache={};hits=[]
    for i,(name,ev) in enumerate(c['tracks']):
        if i==0:continue
        for p,k,a in ev:
            if k!=1 or a[0] not in c['sounds']:continue
            f=files.get(c['sounds'][a[0]][1].lower())
            if f:hits.append((at(p),f,a[1]/127,a[2]))
    for f in {h[1] for h in hits}:cache[f]=load(f)
    end=max(t+len(cache[f])/SR for t,f,_,_ in hits);mix=np.zeros((int(end*SR)+SR,2),np.float32)
    for t,f,vel,pan in hits:
        x=cache[f];o=int(round(t*SR));g=np.array([min(1,(127-pan)/63),min(1,pan/64)],np.float32)*vel
        mix[o:o+len(x)]+=x*g
    peak=float(np.abs(mix).max());rms=float(np.sqrt(np.mean(mix**2))) or 1.
    mix*=10**(-14/20)/rms   # official-song loudness (RMS -14 dBFS); the limiter catches the few summed peaks
    out=H/'audio'/(song+'.wav');out.parent.mkdir(exist_ok=True)
    subprocess.run(['ffmpeg','-v','error','-y','-f','f32le','-ac','2','-ar',str(SR),'-i','-','-af','alimiter=limit=0.97:attack=1:release=50:level=false','-c:a','pcm_s16le',str(out)],input=mix.tobytes(),check=True)
    return dict(song=song,chart=chart.name,notes=len(hits),samples=len(cache),seconds=round(len(mix)/SR,3),peak_before=round(peak,3),wav=str(out))

def main():
    refs=collections.defaultdict(list)
    for r in json.loads((H/'refs.json').read_text())['records']:refs[r['song']].append(r)
    jobs=[(s,Path(max(rs,key=lambda r:r['heads'])['source'])) for s,rs in refs.items() if not (H/'audio'/(s+'.wav')).exists() or sys.argv[1:]]
    if sys.argv[1:]:jobs=[j for j in jobs if j[0] in sys.argv[1:]]
    res=[]
    with ThreadPoolExecutor(4) as ex:
        for r in ex.map(lambda j:render(*j),jobs):res.append(r);print('SSS_AUDIO',r['song'],r['seconds'],'s',r['notes'],'notes',flush=True)
    old=json.loads((H/'audio.json').read_text()) if (H/'audio.json').exists() else {}
    old.update({r['song']:r for r in res});(H/'audio.json').write_text(json.dumps(old,indent=1));print('SSS_AUDIO_DONE',len(old))
if __name__=='__main__':main()
