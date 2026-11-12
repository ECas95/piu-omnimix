"""RISE Season 2 material (E:\EZO\PIU_RISE_dataassets_20261029 + the 5 Minus 2 charts of ..._20261105), named by the game's own
formula (SHA-256 of AUDIO<id>, STEP<id>_<type>_<level>...). Writes D:\PIU_RISE_nuevo\<ID> - <Title>\{Audio,BGA,Charts,Previews},
INDICE.csv, songs.json (selection records) and extra_charts.json. E: is only read; charts stay byte-identical."""
import hashlib,json,re,os,shutil,sys,csv
from pathlib import Path
sys.path.insert(0,r'E:\Pump It Up Data\PIU\rise_channel')
import rise_nx
A=Path(r'E:\EZO\PIU_RISE_dataassets_20261029');B=Path(r'E:\EZO\PIU_RISE_dataassets_20261105');U=Path(r'D:\PIU_RISE_assets_20261105\addressables');O=Path(r'D:\PIU_RISE_nuevo')
H=lambda s:hashlib.sha256(s.encode()).hexdigest().upper()
# id: title, artist, bpm (db.bin; ASCII so the selector font can draw them). 18xx are XX/PHOENIX songs RISE re-released
SONGS={1827:('Yo! Say!! Fairy!!!','MYUKKE.'),1851:('Earendel','Palami feat.neur6sia'),1852:('Hymn of Golden Glory','Essbee'),1854:('Murdoch vs Otada','ESPITZ vs WONDERTRAVELER Project'),1858:('Doppelganger','MonstDeath'),
 10047:('untitled','Apo11o program & NOMA ft.Hana Kagenui'),10053:('ELEVATE','Jorts'),10121:('Tanaka','RISH feat.Choko'),11042:('Stay (TAK Remix)','TAK'),11043:('Say That U','Ruby Tuesday'),11044:('Minus 2','CROOVE'),11045:('Toy War','M2U'),
 11046:('The Prince of Darkness','M2U'),11047:('A Site De La Rue','STREME REVERIE'),11048:('BEDLAM','SANY-ON'),11049:('INFINITY','Lunatic Sounds'),11050:('JUSTITIA','Cosmograph vs. Lunatic Sounds (feat. NieN)'),11051:('Legend of Moonlight','Memme'),
 11052:('INSTANT Vampire StartKit','Dr.ReB'),11053:('Chaotic Neutral','aran'),11054:('TRPNO','Nauts'),11055:('ApolloN','sun3'),11056:('R.F.C. II','ND Lee'),11057:('Now Future is Here','Cosmograph'),11058:('LIMBO','Mori'),11059:('Fallen','Zekk'),11060:('MAX301','NAOKI underground'),11061:('SUPERGLIDE','Getty')}
EXTRA={10026:'A4000018',10033:'A400001F',10120:'A4000037'}
def find(s,ext):
    for d in (A,B):
        p=d/(H(s)+ext)
        if p.exists():return p
def charts(i):
    out=[]
    for ty,pre in (('Single','S'),('HalfDouble','HD')):
        for lv in range(1,31):
            p=find(f'STEP{i}_{ty}_{lv}','.nx')
            if p:
                data=p.read_bytes();nx=rise_nx.parse(data);assert rise_nx.build(nx)==data and dict(map(tuple,nx['tags'])).get(1001)==lv,p
                out.append(dict(ty=ty,lv=lv,name=f'{pre}{lv:02d}',src=p,cols=nx['cols'],data=data))
    return out
def main():
    rows=[];recs=[];used=set();gid=0xA4000041
    for i,(title,artist) in SONGS.items():
        dest=O/''.join(c for c in f'{i} - {title}' if c not in '\/:*?"<>|');[ (dest/x).mkdir(parents=True,exist_ok=True) for x in ('Audio','BGA','Charts','Previews')]
        def put(src,rel):
            t=dest/rel
            if not t.exists() or t.stat().st_size!=Path(src).stat().st_size:shutil.copy2(src,t)
            used.add(Path(src).name);return str(t)
        audio=put(find(f'AUDIO{i}','.mp3'),'Audio/tema.mp3');pa=put(find(f'PREVIEWAUDIO{i}','.mp3'),'Previews/preview.mp3');bga=put(find(f'VIDEO{i}','.webm'),'BGA/bga.webm')
        cover=put(U/f'preview_assets_{i}/sprites/{i}_steam.png','Previews/portada.png');pv=put(U/f'preview_assets_{i}/videos/{i}_steam.webm','Previews/preview.webm')
        cs=charts(i);assert cs,i;ch=[]
        for c in cs:
            f=put(c['src'],f"Charts/{c['name']}_RISE.nx");assert (c['ty']=='Single' and c['cols']==5) or (c['ty']=='HalfDouble' and c['cols']==6),(i,c['name'],c['cols'])
            ch.append(dict(name=c['name'],mode='pump-single' if c['ty']=='Single' else 'pump-halfdouble',level=c['lv'],nx=f,sha256=hashlib.sha256(c['data']).hexdigest(),native=True,source=f"STEP{i}_{c['ty']}_{c['lv']}"))
        g=f'{gid:08X}';gid+=1
        recs.append(dict(game_song_id=g,channel='RISE',channel_id=62,channel_name='PUMP IT UP RISE',kind='ARCADE',source_group='RISE_S2',source_folder=str(i),source='rise_season2',title=title,artist=artist,bpm='',audio=audio,preview_audio=pa,sample_start=30.,sample_length=10.,
            video_segments=[dict(beat='0',seconds=0.,file=bga,rate=1.)],video_policy='RISE own BGA from 0 s',preview_video=pv,still=cover,banner=None,charts=ch,skipped_charts=[]))
        rows.append(dict(id=i,game_song_id=g,titulo=title,artista=artist,charts_single=sum(c['ty']=='Single' for c in cs),charts_halfdouble=sum(c['ty']=='HalfDouble' for c in cs),niveles=' '.join(c['name'] for c in cs),carpeta=dest.name))
    extra=[]
    for i,g in EXTRA.items():
        for c in charts(i):
            d=O/'charts_sueltos';d.mkdir(exist_ok=True);f=d/f"{i}_{c['name']}_RISE.nx";shutil.copy2(c['src'],f);used.add(c['src'].name)
            extra.append(dict(game_song_id=g,name=f"{c['name']}_S2",mode='pump-single' if c['ty']=='Single' else 'pump-halfdouble',level=c['lv'],nx=str(f),sha256=hashlib.sha256(c['data']).hexdigest(),source=f"STEP{i}_{c['ty']}_{c['lv']}"))
    (O/'songs.json').write_text(json.dumps(recs,ensure_ascii=False,indent=1),encoding='utf8');(O/'extra_charts.json').write_text(json.dumps(extra,ensure_ascii=False,indent=1),encoding='utf8')
    with (O/'INDICE.csv').open('w',newline='',encoding='utf-8-sig') as f:w=csv.DictWriter(f,rows[0].keys());w.writeheader();w.writerows(rows)
    left=[n for d in (A,B) for n in os.listdir(d) if n not in used and not re.search(r'',n) is None]
    bg={H(f'BGAEFFECTMAP{i}') for i in list(SONGS)};real=[n for n in left if n.split('.')[0] not in bg]
    print('SONGS',len(recs),'CHARTS',sum(len(r['charts']) for r in recs),'EXTRA',[(e['game_song_id'],e['name'],e['level']) for e in extra]);print('NOT_USED',real)
    for r in rows:print(r['id'],r['game_song_id'],r['titulo'],r['niveles'])
if __name__=='__main__':main()
