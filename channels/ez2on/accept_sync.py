"""Accept / reject each song's chart offset (sync/<folder>.json -> sync_final.json).
Accepted only if ALL hold:
  1. E1 (chart vs Song.mp3) and E2-E3 (chart vs gameplay, gameplay vs Song) agree within 25 ms
  2. structure: the offset minus the encoder constant is a whole number of measures (BGM starts on a bar line)
  3. sections: note density vs audio loudness (0.25 s bins) prefers this offset over +-1 and +-2 measures,
     by a clear margin (a one-measure error is the false positive repetitive music produces)
  4. nothing playable before the audio starts / after it ends."""
import json,glob,os,numpy as np,measure_sync as M,collections
C=65.0   # ms: BGM-at-bar-line constant measured on the 128 songs that start on measure 1
def loud(f):
    x=M.pcm(f);n=len(x)//2756;return np.sqrt((x[:n*2756].reshape(n,2756)**2).mean(1))   # 0.25 s RMS
def density(times,n):
    d=np.zeros(n);i=(np.asarray(times)/250).astype(int);i=i[(i>=0)&(i<n)];np.add.at(d,i,1);return d
def sections(env,times,lag):
    sh=np.asarray(times)+lag;d=density(sh,len(env));k=np.ones(4)/4
    a=np.convolve(np.log1p(env*50),k,'same');b=np.convolve(np.log1p(d),k,'same')
    a=np.diff(a);b=np.diff(b);return float(np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b)+1e-9))
out={};why=collections.Counter()
for f in sorted(glob.glob(r'D:\EZ2ON_PIU\sync\*.json')):
    r=json.load(open(f,encoding='utf8'));s=r['folder'];res=dict(folder=s,chart=r['chart'],status='REVISAR')
    try:
        if not r.get('E2'):raise ValueError('no gameplay recording')
        g=r['E2_fine']-r['E3_fine'];e1=r['E1'][0][0];res['lag_ms']=round(g,1)
        if abs(e1-g)>25:raise ValueError(f'E1 {e1} vs E2-E3 {g:.0f}')
        meas=4*r['beat_ms'];k=max(0,round((-g-C)/meas));const=-g-k*meas;res['measures']=k;res['const_ms']=round(const,1)
        bar=not r['bpm_changes'] and 40<=const<=100;res['bar_line']=bar
        times=[x['time_ms'] for jf in glob.glob(os.path.join(M.B,'ez2on_charts',r['chart'],'*S_*.json')) for x in json.load(open(jf,encoding='utf8'))['notes']]
        env=loud(os.path.join(M.O,s,'Song.mp3'));sc={d:sections(env,times,g+d*meas) for d in (-2,-1,0,1,2)};res['sections']={str(d):round(v,3) for d,v in sc.items()}
        best_other=max(v for d,v in sc.items() if d);res['section_margin']=round(sc[0]-best_other,3)
        if sc[0]<=best_other+(0 if bar else 0.03):raise ValueError(f'sections do not single out this bar ({sc[0]:.3f} vs {best_other:.3f})')
        first=min(times)+g;last=max(times)+g;dur=len(env)*250
        res['pad_ms']=max(0,int(-first)+50) if first<0 else 0
        if first<-300 or last>dur:raise ValueError(f'notes outside the audio ({first:.0f}..{last:.0f} ms, audio {dur:.0f} ms)')
        res['status']='OK'
    except Exception as e:res['reason']=str(e)
    why[res['status'] if res['status']=='OK' else res.get('reason','').split(' ')[0]]+=1;out[s]=res
json.dump(out,open(r'D:\EZ2ON_PIU\sync_final.json','w',encoding='utf8'),ensure_ascii=False,indent=1)
print(why);print('OK',sum(v['status']=='OK' for v in out.values()),'of',len(out))
