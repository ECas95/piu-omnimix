"""Compares the lists of every channel, built by the engine's real qsort + comparator, before (full_antes.txt) and after (full_despues.txt) the new module.
Fails unless every custom channel is A-Z by title with the same songs, and PRIME 2, XX, PHOENIX, RISE and every stock channel are unchanged."""
import struct,sys,unicodedata
from pathlib import Path
E=Path('E:/Pump It Up Data/PIU');sys.path[:0]=[str(E),str(E/'nsde_channel')]
import build_omnimix as B
H=Path(__file__).resolve().parent;pay=H.parent/'payloads/D'
KEEP={0x2f:'PRIME 2',0x32:'XX',0x33:'PHOENIX',0x3e:'RISE'}
raw=(pay/'LIST').read_bytes();pool=list(B.string_entries_from((pay/'LIST.0').read_bytes()));ns,_=struct.unpack_from('<II',raw);title={}
for i in range(ns):
    s=struct.unpack_from('<9I',raw,44+i*36);title[s[0]]=pool[s[1]].decode('utf8','replace') if s[1]<len(pool) else ''
def key(t):   # order_key of runtime_merged17/prepare_and_validate.py
    s=unicodedata.normalize('NFKD',t.casefold());s=''.join(c for c in s if not unicodedata.combining(c))
    return ' '.join(''.join(c if c.isalnum() else ' ' for c in s).split())
def read(p):
    out={};ch=None
    for l in Path(p).read_text().splitlines():
        if l.startswith('CHANNEL'):ch=int(l.split()[1],16);out[ch]=[]
        else:out[ch].append(int(l,16))
    return out
a,b=read(H/'full_antes.txt'),read(H/'full_despues.txt');assert a.keys()==b.keys();bad=0
for c in a:
    if c<0x2f or c in KEEP:
        same=a[c]==b[c];bad+=not same
        if c in KEEP or not same:print(f'{c:02x}',KEEP.get(c,'stock'),len(b[c]),'unchanged' if same else 'CHANGED')
    elif b[c]:
        k=[(key(title[i]),i) for i in b[c]];ok=k==sorted(k) and sorted(a[c])==sorted(b[c]);bad+=not ok
        print(f'{c:02x}',len(b[c]),'A-Z' if ok else 'FAIL',title[b[c][0]][:24],'...',title[b[c][-1]][:24])
print('stock channels',sum(c<0x2f for c in a),'all unchanged' if all(a[c]==b[c] for c in a if c<0x2f) else 'SOME CHANGED')
assert not bad,bad
print('ORDEN_OK')
