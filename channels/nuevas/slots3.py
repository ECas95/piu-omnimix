"""Original PRIME names of MAIN_FULL_C slots and how often the screen scene references each index. Read only."""
import sys,json,struct,re
from pathlib import Path
E=Path('E:/Pump It Up Data/PIU');V45=E/'anime_final_v8/channel_style_v45_merged17'
sys.path[:0]=[str(E),str(E/'nsde_channel'),str(V45)]
sys.dont_write_bytecode=True
from current_parent import load
import build_channel_assets as A
P,g=load()
rel='/USER_INTERFACE/SELECT/MAIN_FULL_C/HD/EN'
for src,b in (('PRIME',(A.PRIME/'USER_INTERFACE/SELECT/MAIN_FULL_C/HD/EN/.BGA').read_bytes() if (A.PRIME/'USER_INTERFACE/SELECT/MAIN_FULL_C/HD/EN/.BGA').exists() else None),('parent',g.get(rel+'/.BGA'))):
    if b is None:print(src,'none');continue
    s=A.bga_slots(b);sc=b[s[-1][0]+s[-1][1]:]
    print(src,len(s),'scene',len(sc))
    for i in range(10,27):
        o,sz=s[i];print(' ',i,b[o:o+64].split(b'\0')[0],'frames',struct.unpack_from('<I',b,o+64)[0])
    print('  scene u32 values',sorted({struct.unpack_from('<I',sc,k)[0] for k in range(6,len(sc)-3) if struct.unpack_from('<I',sc,k)[0]<100}))
