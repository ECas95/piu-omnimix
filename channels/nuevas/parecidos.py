"""Fuzzy title match of the IDOLMASTER and Love Live pack folders against the anime channels of the catalog, for review by hand. Read only."""
import json,re,sys,struct,difflib,unicodedata
from pathlib import Path
E=Path('E:/Pump It Up Data/PIU');sys.path[:0]=[str(E),str(E/'nsde_channel')]
sys.dont_write_bytecode=True
import build_omnimix as BO
pay=Path('D:/Pump It Up Data/PIU/final_v363/payloads/D');raw=(pay/'LIST').read_bytes();pool=list(BO.string_entries_from((pay/'LIST.0').read_bytes()));ns,_=struct.unpack_from('<II',raw)
S=lambda i:pool[i].decode('utf8','replace') if i<len(pool) else ''
def norm(t):
    t=unicodedata.normalize('NFKC',t or '').lower();t=re.sub(r'\[.*?\]|\(.*?\)|tv ?size|full ?song|anime side|bootleg','',t);return re.sub(r'[^0-9a-z]','',t)
C=[]
for i in range(ns-1):
    s=struct.unpack_from('<9I',raw,44+i*36);ch=(s[5]&255)+24
    if s[0]>>28==0xE or s[0]>>16==0xEF or s[1]>=len(pool) or ch<47:continue
    C.append(dict(id=f'{s[0]:08X}',t=S(s[1]),a=S(s[2]),ch=ch,n=norm(S(s[1]))))
K=json.loads((Path(__file__).parent/'canciones.json').read_text(encoding='utf8'));seen=set()
for a in K:
    if a['channel'] not in('IMAS','LL'):continue
    f=Path(a['folder']).name;f=re.sub(r'^\([^)]*\)\s*','',f);f=re.sub(r'\s*\((X10SV|Suee|iamsmcs|idolmann|Producer|X10SV[^)]*)\)\s*$','',f);f=re.sub(r'\[.*?\]','',f)
    for n in {norm(f),norm(a['translit']),norm(a['title'])}:
        if len(n)<4 or (a['channel'],n) in seen:continue
        seen.add((a['channel'],n))
        hits=[(difflib.SequenceMatcher(None,n,c['n']).ratio(),c) for c in C if c['n'] and (c['n'] in n or n in c['n'] or abs(len(c['n'])-len(n))<=4)]
        hits=[h for h in hits if h[0]>=.78 or (h[1]['n'] in n and len(h[1]['n'])>=6) or (n in h[1]['n'] and len(n)>=6)]
        for r,c in sorted(hits,key=lambda h:-h[0])[:3]:
            print(a['channel'],f[:30].ljust(30),'|',a['artist'][:18].ljust(18),'->',c['id'],c['ch'],c['t'][:32],'|',c['a'][:24],round(r,2),flush=True)
