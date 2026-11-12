"""Channel list: order from menu.txt (real builder + hooks), sound names from the engine table + CONFIG/SFX/SELECT.TXT, song counts from full_despues.txt."""
import struct,re
from pathlib import Path
H=Path(__file__).resolve().parent
elf=Path('C:\Users\USER/.codex/workspaces/anime_channel_cache/native_build/full_validation_engine').read_bytes()
phoff,=struct.unpack_from('<I',elf,28);phnum,=struct.unpack_from('<H',elf,44);ld=[]
for i in range(phnum):
    t,off,va,_,fs,ms=struct.unpack_from('<IIIIII',elf,phoff+i*32)
    if t==1:ld.append((va,off,fs))
def fo(v):
    for va,off,fs in ld:
        if va<=v<va+fs:return off+v-va
cs=lambda v:elf[fo(v):elf.index(b'\0',fo(v))].decode()
eff={}
for i in range(47):
    id_,a,c,c2,e=struct.unpack_from('<5I',elf,fo(0x081f7b60)+i*20)
    eff[id_]=cs(e) if fo(e) else ''
sel=(H.parent/'infinity/ui_payloads/CONFIG/SFX/SELECT.TXT').read_bytes().decode('utf8','replace')
wav={m[1]:m[2] for m in re.finditer(r'(EFF_\w+)\s*=\s*"?WAVE/([^"\r\n]+)',sel)}
counts={}
for l in (H/'full_despues.txt').read_text().splitlines():
    if l.startswith('CHANNEL'):p=l.split();counts[int(p[1],16)]=int(p[2][6:])
for l in (H/'menu.txt').read_text().splitlines():
    c=int(l.split()[0],16);e=eff.get(c,'')
    print(f'{c:02x}',counts.get(c,'-'),e,wav.get(e,''))
