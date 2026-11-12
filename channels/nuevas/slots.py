"""Which MAIN_FULL_C hexagon slots hold what, and which channel uses each. Read only."""
import sys,json,struct,collections
from pathlib import Path
E=Path('E:/Pump It Up Data/PIU');F=Path('D:/Pump It Up Data/PIU/final_v363');V45=E/'anime_final_v8/channel_style_v45_merged17'
sys.path[:0]=[str(E),str(E/'nsde_channel'),str(V45)]
sys.dont_write_bytecode=True
from current_parent import load
from build_next_media_chunk import attach
import build_channel_assets as A
P,g=load()
for x in json.loads((F/'package/archives.json').read_text())['archives']:attach(P,g,F/'package' if x['folder']=='package' else F/'package'/x['folder'])
for f in ('patch','patch3','patch4','patch5_rise','patch6'):attach(P,g,F/f/'archive')
for a in json.loads((F/'patch7/patch.json').read_text())['archives']:attach(P,g,F/'patch7'/a['folder'])
for f in ('patch8','patch9'):attach(P,g,F/f/'archive')
print(g.names[-1])
elf=Path('C:\Users\USER/.codex/workspaces/anime_channel_cache/native_build/full_validation_engine').read_bytes();ph,=struct.unpack_from('<I',elf,28);n,=struct.unpack_from('<H',elf,44);ld=[struct.unpack_from('<IIIIII',elf,ph+i*32) for i in range(n)]
off=next(o+0x081f7b60-v for t,o,v,_,fs,_m in ld if t==1 and v<=0x081f7b60<v+fs)
use=collections.defaultdict(list)
for i in range(47):
    c=struct.unpack_from('<5I',elf,off+i*20);use[c[2]].append(f'{c[0]:02x}')
rel='/USER_INTERFACE/SELECT/MAIN_FULL_C/HD/EN';bga=g.get(rel+'/.BGA');slots=A.bga_slots(bga);print('slots',len(slots))
for i,(o,sz) in enumerate(slots):
    nm=bga[o:o+64].split(b'\0')[0].decode('latin1');k=struct.unpack_from('<I',bga,o+64)[0];print(i,repr(nm),'stock users',use.get(i),'frames',k,'size',sz)
print('after slots',bga[slots[-1][0]+slots[-1][1]:][:40])
for md in ('MAIN_FULL_A3','MAIN_FULL_C2'):
    b=g.get(f'/USER_INTERFACE/SELECT/{md}/HD/EN/.BGA');s=A.bga_slots(b);print(md,'slots',len(s),[b[o:o+64].split(b'\0')[0].decode('latin1') for o,_ in s][-8:])
sc=bga[slots[-1][0]+slots[-1][1]:];print('scene bytes',len(sc))
import re
for i in list(range(0,12))+[13,15,17,23,26,44,71,78,84,88,90,91,92,95,99]:
    k=struct.pack('<I',i);hits=[m.start() for m in re.finditer(re.escape(k),sc) if m.start()%4==0];print(i,bga[slots[i][0]:slots[i][0]+24].split(b'\0')[0],'hits',len(hits),hits[:4])
print(sc[:200].hex());j=sc.find(b'SCENE',10);print('2nd scene at',j,sc[j:j+60])
names=[m.group(0) for m in re.finditer(rb'[a-z_0-9]{3,20}\x00',sc)][:40];print(names)
