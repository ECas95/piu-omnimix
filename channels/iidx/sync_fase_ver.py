import json,collections
from pathlib import Path
import numpy as np
R=json.loads((Path(__file__).parent/'sync_fase.json').read_text(encoding='utf8'));G=[r for r in R if 'phase' in r]
print('total',len(R),'measured',len(G),'skips',collections.Counter((r.get('skip') or '').split(':')[0] for r in R if 'skip' in r).most_common(6))
L=[r for r in G if r['R']>=.55];print('locked R>=.55',len(L),'zero',sum(r['delay']==0 for r in L),'nonzero',sum(r['delay']!=0 for r in L))
def wrap(x,T):return (x+T/2)%T-T/2
Z=[r for r in L if r['delay']==0];ph=np.array([r['phase'] for r in Z]);print('delay 0: phase median ms',round(float(np.median(ph))*1000),'IQR',[round(float(x)*1000) for x in np.percentile(ph,[25,75])],'within 50ms',int(np.sum(np.abs(ph)<.05)),'of',len(ph))
N=[r for r in L if r['delay']!=0]
for u in (0,1,2,4,5,10,1000/60,1000/30,1000/15,100):
    for sign in (1,-1):
        if u==0 and sign<0:continue
        e=np.array([wrap(r['phase']-sign*r['delay']*u/1000,r['T']) for r in N]);m=float(np.median(e));print(f'unit {u:6.2f} sign {sign:+d}: within 40ms {int(np.sum(np.abs(e)<.04))} within 70ms {int(np.sum(np.abs(e)<.07))} of {len(e)} median {m*1000:.0f}ms')
for r in sorted(N,key=lambda r:r['delay'])[:14]+sorted(N,key=lambda r:r['delay'])[-14:]:print(r['id'],r['title'][:22].ljust(22),'delay',r['delay'],'T',round(r['T'],3),'phase',round(r['phase'],3),'R',round(r['R'],2),'n',r['n'])
print('asked',[(r['id'],r.get('title'),r.get('delay'),round(r.get('phase',0),3),round(r.get('R',0),2),r.get('n'),r.get('T') and round(r['T'],3),r.get('skip')) for r in R if r['id'] in('24051','31162','4002','16002')])
print('by delay value (locked):')
by=collections.defaultdict(list)
for r in N:by[r['delay']].append(r)
for d,v in sorted(by.items(),key=lambda x:-len(x[1]))[:12]:print(d,len(v),[(round(x['phase'],3),round(x['T'],3)) for x in v][:10])
