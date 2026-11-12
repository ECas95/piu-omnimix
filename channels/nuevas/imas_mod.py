"""iDOLM@STER songs already in the mod: catalog songs by Cinderella-related artists, and pack folders against all anime channels by romaji folder name. Read only."""
import json,re,sys,struct,collections,unicodedata
from pathlib import Path
E=Path('E:/Pump It Up Data/PIU');sys.path[:0]=[str(E),str(E/'nsde_channel')]
sys.dont_write_bytecode=True
import build_omnimix as BO
pay=Path('D:/Pump It Up Data/PIU/final_v363/payloads/D');raw=(pay/'LIST').read_bytes();pool=list(BO.string_entries_from((pay/'LIST.0').read_bytes()));ns,_=struct.unpack_from('<II',raw)
S=lambda i:pool[i].decode('utf8','replace') if i<len(pool) else ''
def norm(t):
    t=unicodedata.normalize('NFKC',t or '').lower();t=re.sub(r'\[.*?\]|\(.*?\)','',t);return re.sub(r'[^0-9a-z\u3040-\u30ff\u4e00-\u9fff]','',t)
art=re.compile(r"cinderella|idolm|im@s|imas|\bcv\b|deremas|lipps|triad primus|new generations|love ?laika|riamu|masquerade|tropical\*?star|p\.?c\.?s|rosenburg|kanzaki|shimamura|shibuya rin|honda mio|akagi miria|kaede|mika|krosaki|\bcandy island\b|asterisk|\*\(asterisk\)|decoration|flowers|kbyd|memories|moiw|miyamoto|sagisawa|takagaki|ichinose|koshimizu|maekawa",re.I)
C=[];
for i in range(ns-1):
    s=struct.unpack_from('<9I',raw,44+i*36)
    if s[0]>>28==0xE or s[0]>>16==0xEF or s[1]>=len(pool):continue
    C.append(dict(id=f'{s[0]:08X}',t=S(s[1]),a=S(s[2]),ch=(s[5]&255)+24,n=norm(S(s[1]))))
hits=[c for c in C if art.search(c['a'])]
print('catalog by artist',len(hits))
for c in sorted(hits,key=lambda c:(c['ch'],c['a'])):print(' ',c['id'],c['ch'],c['t'][:36].ljust(36),'|',c['a'][:34])
K=json.loads((Path(__file__).parent/'canciones.json').read_text(encoding='utf8'));byn=collections.defaultdict(list)
for c in C:
    if c['ch']>=47:byn[c['n']].append(c)
print('pack folder names vs catalog titles')
for a in K:
    if a['channel']!='IMAS':continue
    f=re.sub(r'\s*\((X10SV|iamsmcs)\)\s*$','',Path(a['folder']).name);f=re.sub(r'^\(Barry\)\s*','',f);n=norm(f)
    if n and n in byn and a['norm']!=n:print(' ',('KEEP' if a['keep'] else 'SKIP'),f[:34],'|',a['artist'][:26],'->',[(x['id'],x['t'][:24],x['a'][:22],x['ch']) for x in byn[n]])
