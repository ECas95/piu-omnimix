"""Population test with the cached frame differences: how much of each movie's change falls on the beat grid when the movie is shifted by delay x unit? A right unit lifts the mean comb score
of songs with a delay to the level of songs with delay 0. Comb score = mean difference on the beat frames (half beats too) / mean difference overall. + shift = the raw movie's content comes later than the sound."""
import json,sys
from pathlib import Path
import numpy as np
H=Path(__file__).resolve().parent;R=30
F=json.loads((H/'sync_fase.json').read_text(encoding='utf8'));ok=[r for r in F if 'phase' in r]
def comb(d,T,off,shift):
    """Score at raw-movie times off+shift+k*T/2."""
    n=len(d);t0=(off+shift)%(T/2);ks=np.arange(int(n/R/(T/2))+1);fr=np.rint((t0+ks*T/2)*R).astype(int)-1;fr=fr[(fr>=0)&(fr<n)]
    return float(d[fr].mean()/(d.mean()+1e-6)) if len(fr) else 0.
S=[]
for r in ok:
    res=json.loads((H/'canal/songs'/r['id']/'result.json').read_text(encoding='utf8'));ref=max(res['refs'],key=lambda x:x['heads']);d=np.load(H/'cache_cortes'/f"{r['id']}.npy").astype(np.float64)
    # sharp changes only: motion is smooth, a cut is not
    k=np.convolve(d,np.ones(9)/9,'same');e=np.clip(d-k,0,None);S.append(dict(r,off=ref['offset_s'],e=e))
print('songs',len(S),flush=True)
Z=[s for s in S if s['delay']==0];N=[s for s in S if abs(s['delay'])>=20]
print('zero',len(Z),'score at 0',round(np.mean([comb(s['e'],s['T'],s['off'],0) for s in Z]),3),'at +150ms',round(np.mean([comb(s['e'],s['T'],s['off'],.15) for s in Z]),3),'at half phase',round(np.mean([comb(s['e'],s['T'],s['off'],s['T']/4) for s in Z]),3))
print('nonzero',len(N),'score ignoring delay',round(np.mean([comb(s['e'],s['T'],s['off'],0) for s in N]),3),'at half phase',round(np.mean([comb(s['e'],s['T'],s['off'],s['T']/4) for s in N]),3))
for u in (1,2,4,5,8,10,1000/60,20,1000/30,50,1000/15,100):
    for sign in (1,-1):
        print(f'unit {u:6.2f} sign {sign:+d}: {np.mean([comb(s["e"],s["T"],s["off"],sign*s["delay"]*u/1000) for s in N]):.3f}',flush=True)
# best free shift per song in the population
sh=np.arange(-.3,.301,1/R);print('zero: mean score by constant shift',[(round(float(x)*1000),round(float(np.mean([comb(s['e'],s['T'],s['off'],x) for s in Z])),3)) for x in sh[::2]])
np.save(H/'peine_ok.npy',np.array([1]))
