"""Reads the Full Mode dumps and reports, per custom channel, how far each one is from A-Z by the displayed title."""
import struct,sys,re,unicodedata
from pathlib import Path
E=Path('E:/Pump It Up Data/PIU');sys.path[:0]=[str(E),str(E/'nsde_channel')]
import build_omnimix as B
pay=Path(__file__).resolve().parents[1]/'payloads/D'
raw=(pay/'LIST').read_bytes();pool=list(B.string_entries_from((pay/'LIST.0').read_bytes()))
ns,_=struct.unpack_from('<II',raw);songs={};
for i in range(ns):
    s=struct.unpack_from('<9I',raw,44+i*36);songs[s[0]]=pool[s[1]].decode('utf8','replace') if s[1]<len(pool) else ''
def key(t):
    s=unicodedata.normalize('NFKD',t.casefold());s=''.join(c for c in s if not unicodedata.combining(c))
    return ' '.join(''.join(c if c.isalnum() else ' ' for c in s).split())
for f in sys.argv[1:]:
    print('==',f);ch=None;lists={}
    for l in Path(f).read_text().splitlines():
        if l.startswith('CHANNEL'):ch=l.split()[1];lists[ch]=[]
        else:lists[ch].append(int(l,16))
    for c,ids in lists.items():
        if not ids:continue
        t=[songs[i] for i in ids];k=[key(x) for x in t];bad=[i for i in range(1,len(k)) if k[i]<k[i-1]]
        print(c,'songs',len(ids),'A-Z' if not bad else f'OUT OF ORDER {len(bad)}',t[:4] if bad else '', [(t[i-1][:18],t[i][:18]) for i in bad[:3]])
