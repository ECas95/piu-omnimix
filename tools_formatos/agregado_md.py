"""Lista de lo agregado (selection.json + native_extra.json + POP quitado) -> D:\Pump It Up Data\PIU\AGREGADO_V376.md"""
import json,csv,sys
sys.path.insert(0,r'D:\Pump It Up Data\PIU\final_v363');from pop_removed import POP_REMOVED
d=json.load(open(r'D:\PIU_INFINITY\channels\selection.json',encoding='utf8'))['records']
native=json.load(open(r'D:\PIU_AUDIT\native_extra.json',encoding='utf8'))
removed=json.load(open(r'D:\PIU_AUDIT\removed_no_bga.json',encoding='utf8'))
CH={25:'1st',26:'2nd',27:'3rd/O.B.G',28:'S.E./Collection',29:'Perfect Collection',30:'Extra/Premiere/Prex',32:'Rebirth/Premiere 2-3',34:'Exceed/Prex 3',35:'Exceed',36:'Exceed 2',38:'Zero',39:'NX',40:'NX2',41:'NXA',42:'Fiesta 2010',43:'Fiesta EX',45:'K-POP',72:'EZ2ON'}
MERGED={'00001109':'+ chart de prueba "??" (antes entrada aparte 1150)','00001113':'+ chart de prueba "??" (antes 1155)','00001115':'+ chart de prueba "??" (antes 1157)',
        'A800002C':'+ 5 charts de "Mix 2-7 3rd step"','A800003C':'+ 2 charts de "Another Heart 3rd step"'}
lv=lambda r,m:' '.join(str(c['level']) for c in sorted(r['charts'],key=lambda c:c['level']) if m in c['mode'] or c['mode']==('native-1' if m=='single' else 'native-3')) or '-'
groups=[('fiesta2','Sacadas de los datos de Fiesta 2 (cada una en el canal de su versión original)'),('nxa_fex','Sacadas de NXA (charts de Fiesta / NXA)'),('ez2on','EZ2ON REBOOT : R')]
tot=lambda s:[r for r in d if r.get('source')==s]
o=['# Agregado en v379','',
   '## Qué probar primero','',
   '- [ ] **Fusiones** — cada una debe salir UNA sola vez, con preview y BGA:']
o+=[f"  - [ ] {r['title']} ({r['game_song_id']}, {CH.get(r['channel_id'])}) — {MERGED[r['game_song_id']]}" for r in d if r['game_song_id'] in MERGED]
o+=['  - [ ] Mistake (PRIME, canal Extra/Premiere) — 2 charts nuevos: '+', '.join(c['name'] for c in native)+' (movidos +36 ms al audio de PRIME)',
    '  - [ ] "We" y "Extravaganza 3rd step" ya NO deben aparecer (sus charts ya estaban en We Are / Extravaganza)',
    '- [ ] **Orden de charts**: en todas las agregadas, primero Single y luego Double, cada uno de menor a mayor nivel',
    '- [ ] **BGA y preview**: todas las de esta lista deben tener video propio en el fondo y en la preview',
    f'- [ ] **Quitadas por no tener BGA** ({len(removed)}): no deben aparecer (lista al final)',
    '- [ ] **Canal POP**: solo pop / K-POP (78 quitadas, lista al final)','',
    '- [ ] **Fiesta 2010 / Fiesta EX / Fiesta 2 / NX / NXA**: cada canción agregada con SU banner, BGA, preview y sonido (antes caían en los de otra canción)',
    '- [ ] **Monkey Magic** (canal Extra/Premiere): ahora con BGA y preview (película de Exceed, alineada al audio)',
    '- [ ] **EZ2ON**: las canciones arrancan con 2,5 s de margen antes de la primera nota',
    '- [ ] **Videos SD**: nuestros canales ya no llevan BGA/preview SD (solo HD)',
    '- [ ] **SABIN SOUND STAR**: banner = frame del BGA + título original del juego (título, compositor, visual); BGA de Please Please Me, Sunshine, Try Your Magic Spell, For One and Only You, Return to Universe y Brilliant Stars ahora con retraso medido; Bacardi on the Beach y The Future con 1,5 s (mediana del juego, revisar)',
    f'- [ ] **EZ2ON REBOOT R** (canal nuevo, después de SABIN SOUND STAR): {sum(1 for r in d if r.get("channel")=="EZ2ON")} canciones; revisar sincronía de charts y BGA, banner (Cover) y hexágono del canal',
    '',
    '## Canciones nuevas a probar (una por una)','','Revisar en cada una: aparece una sola vez, BGA y preview propios, título/artista correctos, charts Single→Double de menor a mayor, sincronía.','']
for s_,n in groups:
    o+=[f'### {n}','']+[f"- [ ] **{r['title']}**{' (FULL SONG)' if r['kind']=='FULL' else ''} — {r.get('artist','')} · {CH.get(r['channel_id'],r['channel_id'])} · S {lv(r,'single')} / D {lv(r,'double')}{(' · '+MERGED[r['game_song_id']]) if r['game_song_id'] in MERGED else ''}"
        for r in sorted(tot(s_),key=lambda r:(r['channel_id'],r['title'].lower()))]+['']
o+=[
    '## Resumen','','| Grupo | Canciones | Charts |','|---|---|---|']
o+=[f"| {n} | {len(tot(s))} | {sum(len(r['charts']) for r in tot(s))} |" for s,n in groups]
o+=[f'| Charts nuevos en canciones de PRIME | — | {len(native)} |',f'| Canal POP: quitadas | {len(POP_REMOVED)} | — |','']
for s,n in groups:
    o+=[f'## {n}','','| ID | Título | Artista | Canal | Tipo | Single | Double | Nota |','|---|---|---|---|---|---|---|---|']
    o+=[f"| {r['game_song_id']} | {r['title']} | {r.get('artist','')} | {CH.get(r['channel_id'],r['channel_id'])} | {r['kind']} | {lv(r,'single')} | {lv(r,'double')} | {MERGED.get(r['game_song_id'],'')} |"
        for r in sorted(tot(s),key=lambda r:(r['channel_id'],r['title'].lower()))]+['']
pop={r['gid']:r for r in csv.DictReader(open(r'D:\PIU_AUDIT\POP_REVISION.tsv',encoding='utf8'),delimiter='\t')}
o+=[f'## Canal POP — {len(POP_REMOVED)} quitadas','','| ID | Título | Artista | Motivo |','|---|---|---|---|']
o+=[f"| {g} | {pop.get(g,{}).get('titulo','?')} | {pop.get(g,{}).get('artista','')} | {pop.get(g,{}).get('motivo','')} |" for g in sorted(POP_REMOVED,key=lambda g:pop.get(g,{}).get('titulo','').lower())]
o+=['',f'## Quitadas por no tener BGA — {len(removed)}','',', '.join(f"{x['title']}" for x in removed)]
open(r'D:\Pump It Up Data\PIU\AGREGADO_V379.md','w',encoding='utf8').write('\n'.join(o)+'\n')
print('\n'.join(o[:30]))
