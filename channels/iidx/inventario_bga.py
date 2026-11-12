"""Inventory of beatmania IIDX songs (1st..34 + INFINITAS) with their own BGA, from the data the game really loads (music_omni.bin).
Reads E: only. Writes D:\PIU_IIDX\inventario_bga.json. Series = custom_categories.txt lists for 32/33/34/INFINITAS and every other
game/BMS category, otherwise the version field of the entry."""
import struct,re,os,json,collections,subprocess
from concurrent.futures import ThreadPoolExecutor
C=r'E:\IIDX222\001 - Proyecto IIDX\IIDX\LDJ-012-20231018\contents';M=C+r'\data\movie';OUT=r'D:\PIU_IIDX\inventario_bga.json'
d=open(C+r'\data\info\1\music_omni.bin','rb').read();print(d[:4],struct.unpack_from('<I',d,4));n,mx=struct.unpack_from('<HH',d,8)
head=struct.unpack_from('<I',d,12)[0];print('n',n,'mx',mx,'h',head,len(d))
n2=n
for hdr in (16+mx*2,):
    SZ=(len(d)-hdr)/n2;print('size?',SZ)
SZ=1324;base=16+mx*2;count=(len(d)-base)//SZ;print('entries',count,(len(d)-base)%SZ)
cat={};non=set()
for l in open(C+r'\custom_categories.txt',encoding='utf8'):
    if l.startswith('#'):continue
    p=l.rstrip('\n').split('|')
    if len(p)<6:continue
    ids={int(x) for x in p[5].split(',') if x.strip()}
    if p[0] in('32th','33th','34th','80th'):
        for i in ids:cat[i]={'32th':32,'33th':33,'34th':34,'80th':80}[p[0]]
    else:non|=ids
print('categories',collections.Counter(cat.values()),'non-iidx ids',len(non))
files={e.name.lower():e.stat().st_size for e in os.scandir(M) if e.is_file()};print('movies',len(files))
E=[]
for i in range(count):
    e=d[base+i*SZ:base+(i+1)*SZ];t=lambda o,l=64:e[o:o+l].split(b'\0')[0].decode('cp932','replace')
    sid=struct.unpack_from('<I',e,0x3b0)[0]
    if not t(0):continue
    E.append(dict(id=sid,title=t(0),ascii=t(0x40),genre=t(0x80),artist=t(0xc0),v=struct.unpack_from('<H',e,0x118)[0],bga=t(0x3c4,32)))
print('titled',len(E),sorted(collections.Counter(x['v'] for x in E).items())[:50])
print('overlap',len({x['id'] for x in E}&non),len({x['id'] for x in E}&set(cat)),[i for i in cat if i not in {x['id'] for x in E}][:10])
print(sorted(collections.Counter(x['id']//1000 for x in E).items())[:45])
json.dump(dict(E=E,cat={str(k):v for k,v in cat.items()},non=sorted(non),files=files),open(OUT,'w',encoding='utf8'),ensure_ascii=False)
