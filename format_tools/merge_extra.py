"""v376 (user 2026-10-30): entries that only carry extra charts of a song are merged into that song, never a second song.
  in selection : child record's charts move into the parent record, child removed (same audio / same version timing)
  into PRIME   : charts PRIME doesn't already have (by note count) -> native_extra.json, shifted onto PRIME's timeline
                 by the offset of a chart both share; build_catalog adds them to the native song."""
import sys,json,re,hashlib
from pathlib import Path
H=Path(__file__).resolve().parent;sys.path[:0]=[str(H),r'D:\Pump It Up Data\PIU\final_generation_v362',r'D:\Pump It Up Data\PIU\final_generation_v362\vendor_v363',r'E:\Pump It Up Data\PIU',r'E:\Pump It Up Data\PIU\nsde_channel']
from hybrid import nx20,sources
from current_parent import load
import build_classic as B
SEL=Path(r'D:\PIU_INFINITY\channels\selection.json');OUT=Path(r'D:\PIU_AUDIT\native_extra');NATIVE=Path(r'D:\PIU_AUDIT\native_extra.json')
IN_SEL={'00001150':'00001109','00001155':'00001113','00001157':'00001115',   # Fiesta 2 arcade entries with only extra charts
        'Mix 2-7 3rd step':'Mix 2-7','Another Heart 3rd step':'Another Heart 2nd step'}
RETITLE={'Another Heart 2nd step':'Another Heart'}
TO_PRIME={'We':'318','Self-reproach':'909','Extravaganza 3rd step':'205'}   # classic id == PRIME song id / same audio
first=lambda b:(lambda ev:(sum(len(e['lanes']) for e in ev),ev[0]['ms']))(sources.events_of(nx20.parse(b))[1])
sha=lambda b:hashlib.sha256(b).hexdigest()

doc=json.loads(SEL.read_text(encoding='utf8'));recs=doc['records']
key=lambda r:r['game_song_id'] if r.get('source')=='fiesta2' else r['title']
by={key(r):r for r in recs if r.get('source') in ('fiesta2','classic')}
drop=set()
for child,parent in IN_SEL.items():
    c,p=by[child],by[parent];names={x['name'] for x in p['charts']}
    assert not names&{x['name'] for x in c['charts']};p['charts']+=c['charts'];drop.add(c['game_song_id'])
    print('merged',c['game_song_id'],c['title'],'->',p['game_song_id'],len(c['charts']),'charts')
for t,n in RETITLE.items():by[t]['title']=n
P,game=load();plan={p['title']:p for p in json.load(open(r'D:\PIU_AUDIT\classic_plan.json',encoding='utf8'))};native=[]
for title,sid in TO_PRIME.items():
    r=by[title];drop.add(r['game_song_id']);p=plan[title]
    prime={}
    for x in game.index.files:
        if x.startswith(f'/D/{sid}/{sid}/'.encode()) and x.endswith(b'.NX') and b'/REV_' not in x:
            try:prime.__setitem__(*first(game.get(x.decode())))
            except Exception:pass   # a few PRIME files use NX variants nx20 doesn't parse
    mine=[(c,B.to_nx(c)) for c in B.charts_of(p['version'],p['charts'])];mine=[(c,x) for c,x in mine if x and x[2]>=30]
    shared=[prime[first(x[0])[0]]-first(x[0])[1] for c,x in mine if first(x[0])[0] in prime]
    assert shared,title;delta=round(sorted(shared)[len(shared)//2]);seen=set()
    for c,x in mine:
        if first(x[0])[0] in prime or x[2] in seen:continue   # PRIME already has it / same chart in two slots
        seen.add(x[2]);c=dict(c,start=c['start']+delta);raw,dbl,n,secs=B.to_nx(c);lv=B.level(n,secs,dbl)
        nm=f"{'D' if dbl else 'S'}{lv}_CL{c['src'].replace('.STX#','_').split('.')[0]}";f=OUT/sid/f'{nm}.NX';f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(raw)
        native.append(dict(game_song_id=f'{int(sid,16):08X}',name=nm,mode='pump-double' if dbl else 'pump-single',level=lv,nx=str(f),sha256=sha(raw),source=f"{p['version']}{c['src']}",shift_ms=delta))
    print('into PRIME',sid,title,'shift',delta,'ms; new charts',[x['name'] for x in native if x['game_song_id']==f'{int(sid,16):08X}'])
doc['records']=[r for r in recs if r['game_song_id'] not in drop];SEL.write_text(json.dumps(doc,ensure_ascii=False,indent=1),encoding='utf8')
NATIVE.write_text(json.dumps(native,ensure_ascii=False,indent=1),encoding='utf8')
print('removed records',sorted(drop))
