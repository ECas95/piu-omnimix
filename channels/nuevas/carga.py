"""Simfile loader for the new packs: simfile.parse is strict, these packs carry StepF2 note attributes, keyboard charts and stray bytes."""
import re,sys
from pathlib import Path
sys.path.insert(0,'D:/Pump It Up Data/PIU/anime_channel_dng')
sys.dont_write_bytecode=True
import simfile as SM
def clean(raw):
    t=raw.decode('utf-8-sig',errors='replace')
    # keyboard and other step types the game cannot use: whole NOTES block out
    def block(m):
        return m[0] if m[1].strip().lower() in SM.COLS else ''
    t=re.sub(r'#NOTES:\s*([^:;]*):[^;]*;',block,t)
    t=re.sub(r'#NOTEDATA:;(?:(?!#NOTEDATA)[\s\S])*?#STEPSTYPE:\s*([^;]*);[\s\S]*?#NOTES:[^;]*;',lambda m:m[0] if m[1].strip().lower() in SM.COLS else '',t)
    # StepF2 attribute cells {2|s|0|0} = the note 2; inline {...} and <...> never occupy a panel by themselves
    t=re.sub(r'\{([0-9A-Za-z])\|[^}]*\}',r'\1',t)
    t=re.sub(r'<[^>\r\n]*>','',t)
    return t.encode('utf8')
def legacy_warps(t):
    """Negative BPMs (the old warp trick) -> WARPS and positive BPMs, as StepMania reads them: time runs backward through the negative section and the beats until it returns to where it was are skipped. Beats inside a warp take no time, so the tempo there does not matter."""
    bpms=SM.pairs(t.get('BPMS',''))
    if not any(v<0 for _,v in bpms):return t
    have=[(b,b+SM.F(str(v))) for b,v in SM.pairs(t.get('WARPS','')) if v>0];new=[]
    for n,(b0,v0) in enumerate(bpms):
        if v0>=0 or n and bpms[n-1][1]<0 or any(x<=b0<y for x,y in have+new):continue
        owed=0.   # seconds run backward and not yet won back
        for (cur,v),(nxt,_) in zip(bpms[n:],bpms[n+1:]+[(None,0)]):
            if v<0:owed+=float(nxt-cur)*60/-v;continue
            if nxt is None or owed*v/60<=float(nxt-cur):end=cur+SM.F(round(owed*v/60*192),192);break
            owed-=float(nxt-cur)*60/v
        new.append((b0,end))
    all_=sorted(have+new);out=dict(t);out['BPMS']=','.join(f'{b}={abs(v)}' for b,v in bpms);out['WARPS']=','.join(f'{x}={float(y-x)}' for x,y in all_);return out
def parse(path):
    p=Path(path);tags,charts=SM.parse(clean(p.read_bytes()),extension=p.suffix.lower())
    return legacy_warps(tags),[dict(c,timing=legacy_warps(c['timing'])) for c in charts]
if __name__=='__main__':
    for w in ('', '160.000=12.000,172.000=12.000'):   # HEADSHOT: the warps its .ssc stores are the ones derived from its .sm
        x=legacy_warps({'BPMS':'0=134,159=268,160=-67,164=134,172=-67,176=134,281=268,282=134','STOPS':'159=.056,160=.896,172=.224,184=.224','WARPS':w})
        assert [(float(b),v) for b,v in SM.pairs(x['WARPS'])]==[(160.,12.),(172.,12.)],x['WARPS'];assert '-' not in x['BPMS'];c=SM.Clock(x);assert abs(c.seconds(184)-c.seconds(160)-.896-.224)<1e-3,c.seconds(184)-c.seconds(160)
    print('legacy_warps OK')
