"""Mod songs whose recorded source is an iDOLM@STER pack, from the id reservation ledger of the NSDE import. Read only."""
import json,re,sys,struct
from pathlib import Path
E=Path('E:/Pump It Up Data/PIU');sys.path[:0]=[str(E),str(E/'nsde_channel')]
sys.dont_write_bytecode=True
import build_omnimix as BO
J=json.loads((E/'nsde_channel/reserved_game_ids.json').read_text(encoding='utf-8-sig'))
def walk(x,path=()):
    if isinstance(x,dict):
        for k,v in x.items():yield from walk(v,path+(k,))
    elif isinstance(x,list):
        for i,v in enumerate(x):yield from walk(v,path+(i,))
    else:yield path,x
print(type(J),list(J)[:12] if isinstance(J,dict) else len(J))
s=json.dumps(J,ensure_ascii=False);i=s.find('A500004E');print(s[max(0,i-400):i+300])
pay=Path('D:/Pump It Up Data/PIU/final_v363/payloads/D');raw=(pay/'LIST').read_bytes();pool=list(BO.string_entries_from((pay/'LIST.0').read_bytes()));ns,_=struct.unpack_from('<II',raw);T={}
for i in range(ns-1):
    q=struct.unpack_from('<9I',raw,44+i*36)
    if q[1]<len(pool):T[f'{q[0]:08X}']=(pool[q[1]].decode('utf8','replace'),pool[q[2]].decode('utf8','replace') if q[2]<len(pool) else '',(q[5]&255)+24)
hits={}
for m in re.finditer(r'"([^"]*(?:idolm|im@s|imas|cinderella|deremas)[^"]*)"',s,re.I):
    w=s[max(0,m.start()-500):m.end()+500]
    for g in re.findall(r'A[0-9A-F]{7}',w):hits.setdefault(g,m.group(1)[:70])
print('ids near an idolmaster source',len(hits))
for g,v in sorted(hits.items()):
    if g in T:print(' ',g,T[g][2],T[g][0][:34].ljust(34),'|',T[g][1][:24],'|',v[:60])
