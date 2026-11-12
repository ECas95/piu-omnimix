"""Audio shift for songs whose chart clearly sits off the sound. Broad-band onset lag (lag_banda.json); the control (keysounded IIDX charts) reads 0 with this measure. A song moves only if: every chart agrees (within 10 ms), the peak is clear (1.3x the reading at 0), 20 ms <= |lag|, and |lag| < 3/4 of a 16th (a whole 16th is an off-beat false peak).
Sound early (lag<0): silence in front. Sound late (lag>0): head cut. Notes and movie stay. Original kept as audio_orig.wav; rerunning uses it. Writes ajustes_sync.json."""
import json,re,statistics as st,subprocess
from pathlib import Path
H=Path(__file__).resolve().parent
def bpm_of(r):   # first tempo: SM '0.000=180.000,...', osu list or '101.01,110.02'
    b=r.get('bpm');b=' '.join(map(str,b)) if isinstance(b,list) else str(b or '');b=re.sub(r'[\d.]+\s*=','',b);n=[float(x) for x in re.findall(r'\d+(?:\.\d+)?',b)]
    return n[0] if n else 0
assert bpm_of({'bpm':'0.000=180.000,264.000=90.000'})==180 and bpm_of({'bpm':'101.01,110.02'})==101.01 and bpm_of({'bpm':[155.0]})==155
def decide(lags,score,at0,bpm):
    m=st.median(lags);six=15000/bpm if bpm else 0
    if max(lags)-min(lags)>10 or score<at0*1.3 or abs(m)<20:return 0
    return m if six and abs(m)<six*.75 else 0
assert decide([-40,-40],2.5,1.,150)==-40 and decide([-40,10],2.5,1.,150)==0 and decide([-40],1.2,1.,150)==0 and decide([10],3,1,150)==0 and decide([90],3,1,180)==0
out={};n=0
for x in json.loads((H/'lag_banda.json').read_text(encoding='utf8')):
    if 'bb' not in x:continue
    w=H/'songs'/x['key'];r=json.loads((w/'result.json').read_text(encoding='utf8'));lag=decide(x['bb_all'],x['bb']['score'],x['bb']['at0'],bpm_of(r));a,o=w/'audio.wav',w/'audio_orig.wav'
    if not lag:continue
    if not o.exists():a.rename(o)
    af=f'adelay={-lag}|{-lag}' if lag<0 else f'atrim=start={lag/1000:.3f},asetpts=PTS-STARTPTS'
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(o),'-af',af,'-c:a','pcm_s16le',str(a)],check=True,timeout=300);out[x['key']]=dict(title=x['title'],pack=x['pack'],lag_ms=lag,bpm=bpm_of(r));n+=1
(H/'ajustes_sync.json').write_text(json.dumps(out,ensure_ascii=False,indent=0),encoding='utf8');print('AJUSTES',n)
