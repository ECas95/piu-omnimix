"""Stock channel id -> header sprite (MAIN_FULL_A3) and hexagon slot (MAIN_FULL_C), from the engine's 47-entry table. Read only."""
import sys,struct
from pathlib import Path
E=Path('E:/Pump It Up Data/PIU');sys.path[:0]=[str(E),str(E/'nsde_channel'),str(E/'anime_final_v8/channel_style_v45_merged17')]
sys.dont_write_bytecode=True
import build_channel_assets as A
elf=Path('C:\Users\USER/.codex/workspaces/anime_channel_cache/native_build/full_validation_engine').read_bytes();ph,=struct.unpack_from('<I',elf,28);n,=struct.unpack_from('<H',elf,44);ld=[struct.unpack_from('<IIIIII',elf,ph+i*32) for i in range(n)]
off=next(o+0x081f7b60-v for t,o,v,_,fs,_m in ld if t==1 and v<=0x081f7b60<v+fs)
a3=(A.PRIME/'USER_INTERFACE/SELECT/MAIN_FULL_A3/HD/EN/.BGA').read_bytes();c=(A.PRIME/'USER_INTERFACE/SELECT/MAIN_FULL_C/HD/EN/.BGA').read_bytes();sa,sc=A.bga_slots(a3),A.bga_slots(c)
nm=lambda b,s,i:b[s[i][0]:s[i][0]+64].split(b'\0')[0].decode() if i<len(s) else '?'
for i in range(47):
    e=struct.unpack_from('<5I',elf,off+i*20);print(f'{e[0]:02x}',nm(a3,sa,e[1]),nm(c,sc,e[2]),e[2])
