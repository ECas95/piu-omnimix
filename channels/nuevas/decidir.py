"""Decision per folder of the inventory: keep/skip with the reason, channel, source video. Writes canciones.json + DECISIONES.csv. Rules (user 2026-11-06):
- only songs with their own BGA (the video covers at least half of the song); repeated song inside a pack: one copy (most charts, then best video).
- EZ2ON pack -> EZ2ON. IDOLMASTER -> new channel; a song already in the mod moves there instead of being added. Love Live -> ANIME MIX ULTIMATE, not added if already in the mod.
- SEL and Song Mix 1 -> Main Selections (the user did not ask to skip songs present elsewhere there)."""
import json,csv,re,collections,unicodedata,struct,sys,subprocess
from pathlib import Path
H=Path(__file__).resolve().parent
R=json.loads((H/'inventario.json').read_text(encoding='utf8'))
CH={'AGREGAR A EZ2ON':'EZ2ON','IDOLMASTER':'IMAS','Love Live AC And DLC':'LL','SEL':'SEL','Song Mix 1':'SEL'}
CV=re.compile(r'cv|cinderella|imas|idolm|シンデレラ|デレ',re.I)
LLW=re.compile(r"μ|muse|aqours|nijigasaki|liella|love ?live|ラブライブ|saint snow|printemps|lily ?white|bibi|guilty kiss|azalea|cyaron|a-rise|arise",re.I)
MIN_COVER=.5
def dur(f):
    try:return float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(f)],capture_output=True,text=True,timeout=120).stdout)
    except ValueError:return 0.
def video_of(r):
    if r.get('video'):return r['video'],'named'
    L=[Path(x) for x in r.get('loose',[])]
    # animated banners are not the BGA
    L=[x for x in L if not re.search(r'(bn|banner|preview|jacket)',x.stem,re.I)]
    if not L:return None,None
    return str(max(L,key=lambda x:x.stat().st_size)),'loose'
def mode_score(r):return sum(1 for c in r.get('charts',[]) if str(c[0]) in('dance-single','dance-solo','pump-single','pump-double','dance-double','3'))
def strip_folder(n):
    n=re.sub(r'\s*\((X10SV|iamsmcs|Barry|[A-Za-z0-9_]+)\)\s*$','',n);n=re.sub(r'^\(Barry\)\s*','',n);return n.strip()
out=[]
for r in R:
    a=dict(pack=r['pack'],sub=r.get('sub',''),folder=r['folder'],title=r.get('title',''),translit=r.get('translit',''),artist=r.get('artist',''),channel=CH[r['pack']],keep=False,reason='')
    if r.get('error'):a['reason']='error: '+r['error'][:100];out.append(a);continue
    v,how=video_of(r);a.update(video=v,video_how=how,audio=r.get('audio'),in_game=r.get('in_game',[]),norm=r.get('norm'),norm2=r.get('norm2',''))
    if 'Backup' in r['folder']:a['reason']='folder Backup';out.append(a);continue
    if not v:a['reason']='no BGA';out.append(a);continue
    if not r.get('audio') and r['pack']!='AGREGAR A EZ2ON':a['reason']='no audio';out.append(a);continue
    vs,au=dur(v),dur(r['audio']) if r.get('audio') else 0
    a.update(video_s=round(vs,1),audio_s=round(au,1))
    if au and vs<au*MIN_COVER:a['reason']=f'no BGA: video {vs:.0f} s of {au:.0f} s';out.append(a);continue   # a banner clip or a short intro, not the song's BGA
    if r.get('video_shared',0)>1:a['shared']=r['video_shared']
    a['keep']=True;a['score']=mode_score(r);a['pix']=(r.get('video_info') or {}).get('w') or 0;out.append(a)
# reviewed by hand against the catalog (parecidos.py): pack title -> the mod's own copy, which moves or stays and is not added again
MOVE={'A100058C':r'^Star!!','A500004F':r'^ØωØver','A5000011':r'^お願い！シンデレラ','A5000085':r'^夕映えプレゼント','A200002E':r'^Snow Wings','A2000030':r'^ガールズ.イン.ザ.フロンティア','A2000031':r'^Shine!!','A50000D7':r'^Tulip','A50000D4':r'^Love∞Destiny','A500006B':r'^TOKIMEKIエスカレート','A5000091':r'^OTAHEN','A500003B':r'^-LEGNE-','A500007F':r'^秘密のトワレ','A500004E':r'^輝く世界の魔法','A500002E':r'^Trancing Pulse','A500006A':r'^Orange Sapphire','A200002F':r'^メルヘンデビュー','A500004C':r'^あんずのうた','A500003D':r'^Nation Blue'}
LL_DUP={'A2000073':r'^Aozora Jumping Heart','A2000070':r'^Bokutachi wa Hitotsu','A200006F':r'^Kira Kira Sensation'}
for a in out:
    pairs=MOVE if a['channel']=='IMAS' else LL_DUP if a['channel']=='LL' else {}
    for g,rx in pairs.items():
        if re.search(rx,a['title'].strip()):a['keep']=False;a['reason']='in the mod: '+g;a['mod_id']=g
def title_key(a):
    t=unicodedata.normalize('NFKC',a['title']).lower();t=re.sub(r'[♯#]','',t);t=re.sub(r'[—―ー~〜]','ー',t);return re.sub(r'[^0-9a-z぀-ヿ一-鿿가-힯∀]','',t) or a['folder']
# one copy per title inside each channel
for ch in ('IMAS','LL','SEL'):
    g=collections.defaultdict(list)
    for a in out:
        if a['keep'] and a['channel']==ch:g[title_key(a)].append(a)
    for k,v in g.items():
        if len(v)<2:continue
        v.sort(key=lambda a:(a['video_how']=='named',a['pix'],a['score']),reverse=True)
        for x in v[1:]:x['keep']=False;x['reason']='repeated: kept '+Path(v[0]['folder']).name
(H/'mover_imas.json').write_text(json.dumps(sorted(MOVE)));(H/'canciones.json').write_text(json.dumps(out,ensure_ascii=False,indent=0),encoding='utf8')
with open(H/'DECISIONES.csv','w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow('canal paquete titulo artista queda motivo video en_juego carpeta'.split())
    for a in out:w.writerow([a['channel'],a['sub'] or a['pack'],a['title'],a['artist'],'SI' if a['keep'] else 'NO',a['reason'],a.get('video_how'),'; '.join(f'{x[0]} {x[1]} ch{x[3]}' for x in a.get('in_game',[])),a['folder']])
c=collections.Counter((a['channel'],a['keep']) for a in out);print(sorted(c.items()));print(collections.Counter((a['channel'],a['reason'].split(':')[0]) for a in out if not a['keep']))
print('IMAS kept with same title in game (check by hand):')
for a in out:
    if a['keep'] and a['channel'] in('IMAS','LL') and a.get('in_game'):print(' ',a['channel'],a['title'][:26],'|',a['artist'][:30],'->',[(x[0],x[1][:20],x[2][:24],x[3]) for x in a['in_game']])
