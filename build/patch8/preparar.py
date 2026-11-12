"""First step of patch 8: keeps the last official catalog and its Basic Mode rows in oficial/, and backs up what the rebuild replaces. Run once."""
import sys,json,struct,shutil,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;FINAL=HERE.parent;E=Path('E:/Pump It Up Data/PIU');sys.path[:0]=[str(E),str(E/'nsde_channel')]
import build_omnimix as B
SRC=Path(sys.argv[1]);OF=HERE/'oficial';OF.mkdir(exist_ok=True)
for n in ('official.LIST','official.LIST.0'):shutil.copy2(SRC/'official'/n,OF/n)
shutil.copy2(SRC/'official_basic_files.json',OF/'official_basic_files.json')
raw=(OF/'official.LIST').read_bytes();pool=list(B.string_entries_from((OF/'official.LIST.0').read_bytes()))
ns,nc=struct.unpack_from('<II',raw);songs=[struct.unpack_from('<9I',raw,44+i*36) for i in range(ns)];rows=[struct.unpack_from('<9I',raw,44+ns*36+i*36) for i in range(nc-1)]
helper={i+1 for i,s in enumerate(songs) if s[0]>>28==0xE}
out=[dict(hi=songs[(r[0]>>16)-1][0],lo=songs[(r[0]&65535)-1][0],name=pool[r[1]].decode(),rest=list(r[2:])) for r in rows if r[0]&65535 in helper and r[0]>>16!=r[0]&65535]
assert len(out)==220 and len({r['lo'] for r in out})==57 and all(r['lo']&0xFFFF==r['hi'] for r in out)
(OF/'official_basic.json').write_text(json.dumps(dict(source='f2_1589344650.amf',catalog_sha256=hashlib.sha256(raw).hexdigest(),rows=out),indent=0))
B0=HERE/'respaldo_antes';(B0/'D').mkdir(parents=True,exist_ok=True)
for p in (FINAL/'payloads/D').glob('LIST*'):
    if p.is_file():shutil.copy2(p,B0/'D'/p.name)
for p in (FINAL/'catalog_manifest.json',FINAL/'runtime_merged17/native_filter_result.json',FINAL/'runtime_merged17/cabinet_runtime_source/anime_title_order.h',FINAL/'runtime_merged17/trial_runtime_source/anime_title_order.h'):
    shutil.copy2(p,B0/(p.parent.name+'__'+p.name))
print('PREPARADO',len(out),'rows')
