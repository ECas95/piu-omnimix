import json,collections
from pathlib import Path
import numpy as np
R=[r for r in json.loads((Path(__file__).parent/'sync_bga.json').read_text(encoding='utf8')) if 'lag' in r]
print('songs',len(R),'errors',sum(1 for r in json.loads((Path(__file__).parent/'sync_bga.json').read_text(encoding='utf8')) if 'lag' not in r))
good=lambda r:r['peak']>=5
Z=[r for r in R if r['delay']==0];N=[r for r in R if r['delay']!=0]
print('zero delay',len(Z),'good peaks',sum(map(good,Z)));print(' lag histogram (delay 0, good peak):',sorted(collections.Counter(round(r['lag'],1) for r in Z if good(r)).items(),key=lambda x:-x[1])[:12])
print('nonzero',len(N),'good',sum(map(good,N)))
print('delay values',collections.Counter(r['delay'] for r in N).most_common(25))
for u in (1,2,10,16.67,33.3,100):
    g=[r for r in N if good(r)];e=[abs(r['lag']-(-r['delay']*u/1000)) for r in g];e2=[abs(r['lag']-(r['delay']*u/1000)) for r in g]
    print('unit',u,'ms: median |lag + delay*u|',round(float(np.median(e)),3),'within 70ms',sum(x<.07 for x in e),'| lag - delay*u',round(float(np.median(e2)),3),'within 70ms',sum(x<.07 for x in e2),'of',len(g))
g=[r for r in N if good(r)];x=np.array([r['delay'] for r in g],float);y=np.array([r['lag'] for r in g],float)
A=np.vstack([x,np.ones_like(x)]).T;print('least squares lag=a*delay+b',np.linalg.lstsq(A,y,rcond=None)[0]);print('robust median lag/delay',np.median(y[x!=0]/x[x!=0]))
for r in sorted(g,key=lambda r:r['delay'])[:30]+sorted(g,key=lambda r:r['delay'])[-30:]:print(r['id'],r['title'][:22].ljust(22),'delay',r['delay'],'lag',r['lag'],'peak',round(r['peak'],1),'bpm',r['bpm'])
print('asked');[print(r['id'],r['title'],r['delay'],r['lag'],round(r['peak'],1),round(r['movie_s']),round(r['audio_s'])) for r in R if r['id'] in('24051','31162','4002','16002')]
print('audio-movie gap by delay sign: delay0',np.median([r['audio_s']-r['movie_s'] for r in Z]),'nonzero',np.median([r['audio_s']-r['movie_s'] for r in N]))
