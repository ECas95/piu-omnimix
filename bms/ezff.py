"""EZFF reader for EZ2ON .ez (plain, v8: 13-byte events pos u32 / type u8 / sample id u16 / vel / pan / 0 / length u16).
Same container as sss.parse minus the additive key and the keysound text list (that is the .ezi next to it)."""
import struct,re
from pathlib import Path
def parse(p):
    e=Path(p).read_bytes();assert e[:4]==b'EZFF',p
    ver=e[5];tpm,=struct.unpack_from('<H',e,0x86);bpm,=struct.unpack_from('<f',e,0x88);ntr,=struct.unpack_from('<H',e,0x8c)
    o=0x96;sizes=[]
    for k in range(ntr):
        size,=struct.unpack_from('<I',e,o+0x4a);sizes.append(size);o+=0x4e+size
    stride=next((st for st in ((13,11,12) if ver>=7 else (11,13,12)) if all(z%st==0 for z in sizes)),13 if ver>=7 else 11)
    o=0x96;tracks=[]
    for k in range(ntr):
        assert e[o:o+4]==b'EZTR',(p,k,o);name=e[o+6:o+0x46].split(b'\0')[0].decode('latin1');size,=struct.unpack_from('<I',e,o+0x4a);o+=0x4e
        ev=[]
        for j in range(0,size,stride):
            pos,typ=struct.unpack_from('<IB',e,o+j)
            if typ==1 and stride==13:sid,vel,pan,_,ln=struct.unpack_from('<HBBBH',e,o+j+5);ev.append((pos,typ,sid,vel,pan,ln))
            elif typ==1:a=e[o+j+5:o+j+stride];ev.append((pos,typ,a[0],a[1],a[2],struct.unpack_from('<H',a,4)[0]))
            else:ev.append((pos,typ,e[o+j+5:o+j+stride]))
        tracks.append((name,ev));o+=size
    return dict(version=ver,ticks_per_measure=tpm,bpm=bpm,tracks=tracks,rest=len(e)-o,name=e[6:0x46].split(b'\0')[0].decode('latin1'))
def ezi(p):
    return {int(m.group(1)):m.group(3).strip() for m in (re.match(r'(\d+)\s+(\d+)\s+(.+)$',l) for l in Path(p).read_text('latin1').splitlines()) if m}
if __name__=='__main__':
    import sys,collections
    for p in sys.argv[1:]:
        c=parse(p);print(p,'v',c['version'],c['name'],'tpm',c['ticks_per_measure'],'bpm',round(c['bpm'],3),'tracks',len(c['tracks']),'rest',c['rest'])
        for i,(n,ev) in enumerate(c['tracks']):
            if ev:print(' ',i,repr(n),len(ev),dict(collections.Counter(x[1] for x in ev)),ev[:2])
