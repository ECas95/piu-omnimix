"""Lead-in (user 2026-10-30): EZ2ON charts start almost at 0 s; every song gets silence in front so its first note
plays at >= LEAD_MS. The audio is padded, every chart split start (head[3]) and the first split's gap (head[6]) move by
the same amount, and the BGA starts that much later: notes keep their exact place against the music."""
import struct,sys
sys.path[:0]=[r'D:\Pump It Up Data\PIU\final_generation_v362',r'D:\Pump It Up Data\PIU\final_generation_v362\vendor_v363']
from hybrid import nx20,sources
LEAD_MS=2500
def first_ms(raw):return sources.events_of(nx20.parse(raw))[1][0]['ms']
def shift(raw,delta):
    nx=nx20.parse(raw)
    for i,s in enumerate(nx['splits']):
        h=list(s['head']);h[3]+=delta
        if i==0:h[6]+=delta
        s['head']=tuple(h)
    return nx20.build(nx)
if __name__=='__main__':   # self-check on every EZ2ON chart: each event moves by exactly delta
    import json
    sel=[r for r in json.load(open(r'D:\PIU_INFINITY\channels\selection.json',encoding='utf8'))['records'] if r['channel']=='EZ2ON'];worst=0;n=0
    for r in sel:
        for c in r['charts']:
            raw=open(c['nx'],'rb').read();a=sources.events_of(nx20.parse(raw))[1];b=sources.events_of(nx20.parse(shift(raw,1234.5)))[1]
            assert len(a)==len(b) and [e['lanes'] for e in a]==[e['lanes'] for e in b]
            worst=max(worst,max(abs(y['ms']-x['ms']-1234.5) for x,y in zip(a,b)));n+=1
    print('LEADIN_SELF_CHECK',n,'charts; worst deviation',worst,'ms')
