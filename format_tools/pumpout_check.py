"""Pump Out 'removed in version X' lists (D:\PIU_AUDIT\pumpout\v<ver>[_p<n>].html) vs our omnimix:
song present? (song id; else title+artist), and each listed chart (mode+level) present on that song?
Our side = installed catalog dump (ours.json) + every record now in selection.json."""
import re,html,json,glob,os,unicodedata,collections,csv
P=r'D:\PIU_AUDIT\pumpout'
n=lambda t:re.sub(r'[^0-9a-z]','',unicodedata.normalize('NFKC',html.unescape(t or '')).lower())
rows=[]
for f in sorted(glob.glob(P+r'\v*.html')):
    ver=re.match(r'v(\d+)',os.path.basename(f))[1];s=open(f,encoding='utf8',errors='replace').read()
    for blk in s.split('<div class="list-group-item')[1:]:
        m=re.search(r'<div class="media-body">\s*(.*?)\s*<span class="label bg-inverse">ID:\s*([^<]+)</span>',blk,re.S)
        if not m:continue
        art=re.search(r'<span class="label bg-primary"[^>]*>([^<]*)</span>',blk);kind=re.findall(r'badge bg-inverse[^>]*>([^<]*)<',blk)
        charts=re.findall(r'<!--<span class="label bg-inverse" href="">([^<]+)</span>-->',blk)
        rows.append(dict(ver=ver,title=html.unescape(m[1]).strip(),id=m[2].strip(),artist=html.unescape(art[1]).strip() if art else '',kind=kind[0] if kind else '',charts=charts))
ours=json.load(open(r'D:\PIU_AUDIT\ours.json',encoding='utf8'))
sel=json.load(open(r'D:\PIU_INFINITY\channels\selection.json',encoding='utf8'))['records']
songs={}
for x in ours:songs[x['gid']]=dict(title=x['title'],artist=x['artist'],charts=set(c for c in x['charts']),src='catalog',kind=x['kind'])
MODE={'pump-single':'S','pump-double':'D','native-1':'SP','native-3':'DP'}
for r in sel:songs[r['game_song_id']]=dict(title=r['title'],artist=r.get('artist',''),charts={MODE.get(c['mode'],'?')+str(c['level']) for c in r['charts']},src=r.get('source'),kind={'ARCADE':2,'FULL':4,'SHORT':1,'REMIX':3}.get(r['kind']))
bytitle=collections.defaultdict(list)
for g,x in songs.items():bytitle[n(x['title'])].append(g)
KIND={'Arcade':2,'Full Song':4,'Short Cut':1,'Remix':3}
out=[]
for r in rows:
    gid=f'{int(r["id"],16):08X}' if re.fullmatch(r'[0-9A-Fa-f]{1,8}',r['id']) else None
    cand=[gid] if gid in songs else [g for g in bytitle.get(n(r['title']),[]) if n(songs[g]['artist'])[:5]==n(r['artist'])[:5] and songs[g]['kind'] in (None,KIND.get(r['kind']))]   # no id: same title AND same artist
    if not cand:out.append(dict(r,status='FALTA CANCION',ours=''));continue
    g=cand[0];have=songs[g]['charts']
    # PRIME re-rated many old charts: compare how many Single / Double charts the song has, not the level numbers
    cnt=lambda cs,k:sum(1 for c in cs if re.fullmatch(k+r'\d+',c))
    miss=[f"{k} {cnt(r['charts'],k)} vs {cnt(have,k)}" for k in ('S','D') if cnt(r['charts'],k)>cnt(have,k)]
    out.append(dict(r,status='OK' if not miss else 'FALTAN CHARTS',ours=f"{g} {songs[g]['title']} [{songs[g]['src']}]",missing=miss))
c=collections.Counter(o['status'] for o in out);print(len(rows),'entries',c)
with open(r'D:\PIU_AUDIT\PUMPOUT_REMOVALS.tsv','w',encoding='utf8',newline='') as f:
    w=csv.writer(f,delimiter='\t');w.writerow(['version','id','titulo','artista','tipo','charts_pumpout','estado','nuestro','faltan'])
    for o in sorted(out,key=lambda o:(o['status'],int(o['ver']),o['title'].lower())):w.writerow([o['ver'],o['id'],o['title'],o['artist'],o['kind'],' '.join(o['charts']),o['status'],o['ours'],' '.join(o.get('missing',[]))])
for o in out:
    if o['status']!='OK':print(o['status'],o['ver'],o['id'],o['title'],'|',o['kind'],'|',o.get('missing',''),'|',o['ours'])
