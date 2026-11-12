"""Host-only final catalog for the v363 charts (no image access).

Reads the installed catalog (E:, read-only) and writes to this folder:
  payloads/D/LIST, LIST.0-5 and every new NX at /D/<GID>/<GID>/<NAME>.NX
  catalog_manifest.json  (every change, every skipped chart and why)
Rules (user decisions 2026-10-22/23):
  - ANIME NSDE (65) merged into ANIME PIU (64)
  - hide songs in DUPLICATE_DECISIONS + any same-channel duplicate created by the merge
  - Pump customs: keep every original chart, add generated bands
  - DDR/DJMAX/DSS: a mode with generated charts replaces that mode's old charts
  - one visible chart per (song, mode, level): a generated chart moves to the nearest
    free level inside its band, otherwise it is skipped and reported
"""
from pathlib import Path
import sys,json,struct,hashlib,collections,re,unicodedata
E=Path(r'E:\Pump It Up Data\PIU');D=Path(r'D:\Pump It Up Data\PIU');G=D/'final_generation_v362';OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(E),str(E/'nsde_channel'),str(G),str(G/'vendor_v363')]
from current_parent import load
from hybrid import nx20,sources
import playability
BANDS=[(1,5),(6,12),(13,17),(18,20)];MODE={'Single':0,'Double':2}
NEW=0x200000   # chart-row bit 21 = NEW tag (native PRIME sets it only on charts added in a later update)
strip_new=lambda c:[c[0],c[1],c[2]&~NEW,*c[3:]]   # user 2026-10-24: originals of custom songs carry no tag
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
sha=lambda b:hashlib.sha256(b).hexdigest()

def norm(t):
    t=unicodedata.normalize('NFKC',t).lower()
    return re.sub(r'[^0-9a-z\u3040-\u30ff\u4e00-\u9fff\uac00-\ud7af]','',t)

def main():
    P,game=load();raw=game.get('/D/LIST');parent_sha=sha(raw)
    ns,nc=struct.unpack_from('<II',raw)
    songs=[list(struct.unpack_from('<9I',raw,44+i*36)) for i in range(ns)]
    charts=[list(struct.unpack_from('<9I',raw,44+ns*36+i*36)) for i in range(nc-1)]
    pools=[list(P.B.string_entries_from(game.get(f'/D/LIST.{i}'))) for i in range(6)]
    strings={b:i for i,b in enumerate(pools[0])}
    def text(value):
        b=value.encode('utf-8')
        if b not in strings:
            strings[b]=len(pools[0])
            for pool in pools:pool.append(b)
        return strings[b]
    S=lambda i:pools[0][i].decode('utf8','replace')
    gid_of=lambda o:songs[o-1][0];cid_of=lambda o:(songs[o-1][5]&255)+24
    def old_nx(o,c):
        for name in (S(c[1]),S(c[1]).upper()):
            try:return game.get(f'/D/{gid_of(o):X}/{gid_of(o):X}/{name}.NX')
            except Exception:pass
        return None
    jobs={j['key']:j for j in read(G/'generation_jobs.json')['jobs']}
    policy={p['game_song_id']:p['source_policy'] for p in read(G/'generation_jobs.json')['song_plans']}
    scope=set(read(G/'USER_CHANNEL_SCOPE.json')['song_ids'])
    hidden=dict(read(G/'DUPLICATE_DECISIONS.json')['hidden'])
    # user 2026-10-24: removed from the game entirely (song row + every chart)
    REMOVED={'A50002B0':'Pomp and Circumstance','A50002CF':'[Full Song] STAGE OF SEKAI','A1000336':'Kyouki Chinden','0000E25B':'Sister Sister',
             'A10003AF':'Meteor Impact','A5000252':'the EmpErroR','0000D9D8':'STALKER','A1000537':'Shinryaku No Susume*',
             'A20000CD':'Streaming Heart [Full Song]','A1000002':'00.WOAH-OH-OH-AH-AH-AH-AAAA-HA-AH-AH-AH'}
    hidden.update({g:dict(title=t,reason='removed by user 2026-10-24') for g,t in REMOVED.items()})
    from pop_removed import POP_REMOVED   # user 2026-10-29: POP channel keeps only pop / K-POP (no anime, games, doujin, rock, memes)
    hidden.update({g:dict(title=t,reason='POP channel: not pop/K-POP (user 2026-10-29)') for g,t in POP_REMOVED.items()})
    from ez2_series_removed import EZ2_SERIES_REMOVED   # user 2026-11-05: EZ2DANCER keeps only the arcade songs
    hidden.update({g:dict(title=t,reason='EZ2DANCER: StepMania EZ2 series pack removed by user 2026-11-05') for g,t in EZ2_SERIES_REMOVED.items()})
    registry=read(G/'FAITHFUL_REGISTRY.json')['records']  # v364 faithful charts (original rhythm)
    manifest=dict(parent_catalog_sha256=parent_sha,parent_archive=game.names[-1],moved=[],hidden_songs=[],replaced_rows=[],added=[],skipped=[],fallback_kept_old_mode=[])
    # 1. merge NSDE -> ANIME PIU (channel byte = cid-24)
    for o in range(1,ns):
        if cid_of(o)==65:
            before=list(songs[o-1]);songs[o-1][5]=(songs[o-1][5]&~255)|(64-24)
            manifest['moved'].append(dict(game_song_id=f'{gid_of(o):08X}',title=S(songs[o-1][1]),before=before[5],after=songs[o-1][5]))
    # 2. duplicates created by the merge (same channel now): keep the entry with more charts
    rows_by=collections.defaultdict(list)
    for c in charts:rows_by[c[0]>>16].append(c)
    groups=collections.defaultdict(list)
    for o in range(1,ns):
        g=f'{gid_of(o):08X}'
        if cid_of(o)==64 and g not in hidden:groups[(norm(S(songs[o-1][1])),norm(S(songs[o-1][2])))].append(o)
    for key,os_ in groups.items():
        if len(os_)<2:continue
        keep=max(os_,key=lambda o:(len(rows_by[o]),-gid_of(o)))
        for o in os_:
            if o!=keep:hidden[f'{gid_of(o):08X}']=dict(title=S(songs[o-1][1]),reason='same-channel duplicate after NSDE merge',kept=f'{gid_of(keep):08X}')
    # 3. chart rows per song (v364 faithful). DDR/DJMAX/DSS: a mode with faithful charts is
    # replaced by them (old charts only fill up to 4 if they pass the anti-spin gate).
    # Pump customs: every original stays; faithful charts with new levels fill up to 4 per mode.
    gen_by=collections.defaultdict(list)
    for k,r in registry.items():
        if r['game_song_id'] in scope and r['game_song_id'] not in hidden:gen_by[r['game_song_id']].append(r)
    new_rows=[];payloads={}
    lv=lambda c:(c[2]>>8)&255;md=lambda c:(c[2]>>16)&15
    for o in range(1,ns):
        g=f'{gid_of(o):08X}';rows=rows_by[o]
        if g in hidden:continue
        gens=gen_by.get(g,[])
        if not gens:new_rows+=[strip_new(c) if g in scope else c for c in rows];continue
        pol=policy.get(g,'');keep_rows=list(rows);adds=[]
        for mode in ('Single','Double'):
            mine=sorted([r for r in gens if r['mode']==mode],key=lambda r:r['tier'])
            if not mine:continue
            existing=[c for c in keep_rows if md(c)==MODE[mode] and c[0]>>16==c[0]&65535]
            if pol!='retain_original_pump_fill_missing_bands':
                fill=[]
                if len(mine)<4:
                    for c in sorted(existing,key=lv):
                        if len(mine)+len(fill)>=4:break
                        if lv(c) in {r['level'] for r in mine}:continue
                        data=old_nx(o,c)
                        try:ok=data is not None and playability.gate(sources.events_of(nx20.parse(data))[1],10 if MODE[mode]==2 else 5,1 if lv(c)<=5 else 2 if lv(c)<=12 else 3 if lv(c)<=17 else 4)['pass']
                        except Exception:ok=False
                        if ok:fill.append(c);manifest['fallback_kept_old_mode'].append(dict(game_song_id=g,name=S(c[1]),level=lv(c),mode=mode))
                drop=[c for c in existing if c not in fill]
                keep_rows=[c for c in keep_rows if c not in drop]
                manifest['replaced_rows']+=[dict(game_song_id=g,name=S(c[1]),level=lv(c),mode=mode) for c in drop]
                adds+=mine
            else:
                have={lv(c) for c in existing};need=max(0,4-len(existing))
                cand=list(mine)   # new levels first; a colliding one still fills (nearest free level below)
                for _ in range(need):
                    if not cand:break
                    best=max(cand,key=lambda r:min([abs(r['level']-h) for h in have] or [99]))
                    adds.append(best);cand.remove(best);have.add(best['level'])
        taken={(md(c),lv(c)) for c in keep_rows}
        template=next((c for c in rows if (c[2]>>21)&1),rows[0] if rows else None)
        if template is None:manifest['skipped'].append(dict(game_song_id=g,reason='song has no chart row to use as template'));new_rows+=rows;continue
        added=[]
        for r in sorted(adds,key=lambda r:(r['mode'],r['tier'])):
            m=MODE[r['mode']];want=int(r['level'])
            free=[l for l in sorted(range(max(1,want-2),min(28,want+2)+1),key=lambda l:(abs(l-want),-l)) if (m,l) not in taken]
            if not free:free=[l for l in sorted(range(1,29),key=lambda l:(abs(l-want),-l)) if (m,l) not in taken][:1]   # every custom song keeps 4+4
            if not free:manifest['skipped'].append(dict(game_song_id=g,mode=r['mode'],tier=r['tier'],reason=f'levels {want-2}-{want+2} already used for this mode'));continue
            level=free[0];taken.add((m,level))
            data=Path(r['nx']).read_bytes();nx=nx20.parse(data)
            if dict(nx['tags']).get(1001)!=level:
                nx['tags']=[(k,level if k==1001 else v) for k,v in nx['tags']];data=nx20.build(nx)
            name=f"{'S' if m==0 else 'D'}{level}_V364_T{r['tier']}"
            path=f'/D/{gid_of(o):X}/{gid_of(o):X}/{name}.NX'
            assert path.encode() not in game.index.files,path
            payloads[path]=data
            row=list(template);row[0]=(o<<16)|o;row[1]=text(name)
            row[2]=(template[2]&~0x000FFF00&~0x00F00000)|NEW|(m<<16)|(level<<8)   # generated chart: NEW tag
            added.append(row)
            manifest['added'].append(dict(game_song_id=g,mode=r['mode'],tier=r['tier'],reduction=r.get('reduction'),level=level,real_level=want,name=name,path=path,sha256=sha(data)))
        new_rows+=[strip_new(c) for c in keep_rows]+added
    # 3b. v368: PRO 1 / PRO 2 / INFINITY channels (original Infinity charts; titles limited to the selector font)
    sys.path[:0]=[str(OUT/'infinity'),str(E/'anime_final_v8/display_text_v19')]
    import catalog_ext;from prepare_display import safe_text
    cm=read(E/'anime_final_v8/display_text_v19/font_cmaps.json');coverage=set.intersection(*(set(v) for k,v in cm.items() if k.endswith(('MYRIADPRO-REGULAR.TTF','NXPT.TTF'))))
    payloads.update(catalog_ext.extend(songs,new_rows,text,lambda t:safe_text(t,coverage),manifest))
    # user 2026-11-06: the mod's own copies of the CINDERELLA GIRLS pack songs move to that channel (0x4d)
    moved=set(json.loads((OUT/'cinderella_moved.json').read_text()));assert all(any(f'{s[0]:08X}'==g for s in songs) for g in moved)
    for s in songs:
        if f'{s[0]:08X}' in moved:s[5]=(s[5]&~255)|(0x4d-24)
    import basic_original   # user 2026-11-06: Basic Mode exactly as the original PRIME
    new_rows=basic_original.restore_rows(songs,new_rows,text)
    # 4. remove hidden songs and remap ordinals
    remap={0:0};kept=[]
    for o,s in enumerate(songs,1):
        if o<ns and f'{s[0]:08X}' in hidden:
            manifest['hidden_songs'].append(dict(game_song_id=f'{s[0]:08X}',title=S(s[1]),**{k:v for k,v in hidden[f'{s[0]:08X}'].items() if k!='title'}));continue
        remap[o]=len(kept)+1;kept.append(s)
    basic_original.fix_parents(kept)
    final_rows=[]
    for c in new_rows:
        hi,lo=c[0]>>16,c[0]&65535   # lo!=hi rows are Basic/mission aliases: remap each half
        if hi not in remap or lo not in remap:continue
        n=list(c);n[0]=(remap[hi]<<16)|remap[lo];final_rows.append(n)
    final_rows.sort(key=lambda c:c[0]>>16)  # rows grouped by song ordinal, as in the parent
    header=bytearray(raw[:44]);struct.pack_into('<II',header,0,len(kept),len(final_rows)+1)
    catalog=bytes(header)+b''.join(struct.pack('<9I',*s) for s in kept)+b''.join(struct.pack('<9I',*c) for c in final_rows)
    files={'/D/LIST':catalog,**{f'/D/LIST.{i}':P.B.encode_string_entries(p) for i,p in enumerate(pools)},**payloads}
    for path,data in files.items():
        t=OUT/'payloads'/path.lstrip('/');t.parent.mkdir(parents=True,exist_ok=True);tmp=t.with_suffix(t.suffix+'.tmp');tmp.write_bytes(data);tmp.replace(t)
    # sanity: one visible chart per song/mode/level among customs
    vis=collections.Counter(((c[0]>>16),(c[2]>>16)&15,(c[2]>>8)&255) for c in final_rows if (kept[(c[0]>>16)-1][5]&255)+24 not in (47,50,51,62) and (kept[(c[0]>>16)-1][5]&255)+24>=47)
    manifest.update(candidate_catalog_sha256=sha(catalog),songs=len(kept)-1,chart_rows=len(final_rows),new_payloads=len(payloads),
                    visible_duplicate_slots=sum(v>1 for v in vis.values()),installed=False,images_accessed='read-only host view')
    (OUT/'catalog_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=1),encoding='utf8')
    print(json.dumps({k:(len(v) if isinstance(v,list) else v) for k,v in manifest.items()},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
