"""Real lists of every channel (engine qsort + comparator, patch8/orden_canales.sh) after patch 10, against the lists before it (patch8/full_despues.txt).
Fails unless every custom channel is A-Z, PRIME 2 / XX / PHOENIX / RISE and every stock channel are unchanged, and IIDX parts / new channels hold the expected songs."""
import struct,sys,unicodedata,json,collections
from pathlib import Path
E=Path('E:/Pump It Up Data/PIU');sys.path[:0]=[str(E),str(E/'nsde_channel')]
sys.dont_write_bytecode=True
import build_omnimix as B
H=Path(__file__).resolve().parent;F=H.parent;pay=F/'payloads/D'
KEEP={0x2f:'PRIME 2',0x32:'XX',0x33:'PHOENIX',0x3e:'RISE'}
raw=(pay/'LIST').read_bytes();pool=list(B.string_entries_from((pay/'LIST.0').read_bytes()));ns,_=struct.unpack_from('<II',raw);title={}
for i in range(ns):
    s=struct.unpack_from('<9I',raw,44+i*36);title[s[0]]=pool[s[1]].decode('utf8','replace') if s[1]<len(pool) else ''
def key(t):
    s=unicodedata.normalize('NFKD',t.casefold());s=''.join(c for c in s if not unicodedata.combining(c));return ' '.join(''.join(c if c.isalnum() else ' ' for c in s).split())
def read(p):
    out={};ch=None
    for l in Path(p).read_text().splitlines():
        if l.startswith('CHANNEL'):ch=int(l.split()[1],16);out[ch]=[]
        else:out[ch].append(int(l,16))
    return out
a,b=read(F/'patch8/full_despues.txt'),read(sys.argv[1]);bad=0
recs=json.loads(Path('D:/PIU_INFINITY/channels/selection.json').read_text(encoding='utf8'))['records'];want=collections.defaultdict(set)
for r in recs:
    if not r.get('media_only'):want[r['channel_id']].add(int(r['game_song_id'],16))
moved={int(g,16) for g in json.loads((F/'cinderella_moved.json').read_text())}
for c in sorted(b):
    if c<0x2f or c in KEEP:
        same=a.get(c,[])==b[c];bad+=not same
        if c in KEEP or not same:print(f'{c:02x}',KEEP.get(c,'stock'),len(b[c]),'unchanged' if same else 'CHANGED')
    elif b[c]:
        k=[(key(title[i]),i) for i in b[c]];ok=k==sorted(k);bad+=not ok
        extra=''
        if c>=0x47:
            w=want[c]|(moved if c==0x4d else set());ok2=set(b[c])==w;bad+=not ok2;extra='songs OK' if ok2 else f'SONGS DIFFER {len(set(b[c])^w)}'
        print(f'{c:02x}',len(b[c]),'A-Z' if ok else 'FAIL',title[b[c][0]][:22],'...',title[b[c][-1]][:22],extra)
print('stock channels',sum(c<0x2f for c in b));assert not bad,bad;print('ORDEN_OK')
