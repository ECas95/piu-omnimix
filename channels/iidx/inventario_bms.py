"""Own-BGA inventory of the BMS categories shown in the song select (bms_* of custom_categories.txt, without DJMAX/EZ2DJ).
Own = entry's movie exists and is not a byte copy of a generic (non-numeric) movie nor shared by several songs with the same content.
E: is only read. Output: inventario_bms_propios.csv, inventario_bms_todas.csv, resumen_bms.json"""
import json,re,os,csv,hashlib,subprocess,collections
from concurrent.futures import ThreadPoolExecutor
C=r'E:\IIDX222\001 - Proyecto IIDX\IIDX\LDJ-012-20231018\contents';M=C+r'\data\movie';O=r'D:\PIU_IIDX'
D=json.load(open(O+r'\inventario_bga.json',encoding='utf8'));E={x['id']:x for x in D['E']};F=D['files']
cats=[]
for l in open(C+r'\custom_categories.txt',encoding='utf8'):
    if l.startswith('#'):continue
    p=l.rstrip('\n').split('|')
    if len(p)>=6 and p[0].startswith('bms_') and p[0] not in('bms_djmax','bms_ez2dj'):cats.append((p[4],[int(x) for x in p[5].split(',') if x.strip()]))
print([(n,len(i)) for n,i in cats],flush=True)
rows=[];names=collections.Counter()
for label,ids in cats:
    for i in ids:
        x=E.get(i)
        if x:rows.append(dict(canal=label,id=i,titulo=x['title'],artista=x['artist'],genero=x['genre'],bga=x['bga']));names[x['bga'].lower()]+=1
print('rows',len(rows),collections.Counter(re.sub(r'[0-9]','9',r['bga'])[:6] for r in rows).most_common(12),flush=True)
isnum=lambda b:bool(re.fullmatch(r'\d+',b))
used={n+'.mp4' for n in names if n+'.mp4' in F}
gen={n:s for n,s in F.items() if not isnum(n[:-4])};bysize=collections.defaultdict(list)
for n,s in F.items():bysize[s].append(n)
tohash={n for n in used if len(bysize[F[n]])>1}|{m for n in used if len(bysize[F[n]])>1 for m in bysize[F[n]]}
print('hashing',len(tohash),'of',len(used),flush=True)
def sha(n):
    h=hashlib.sha256()
    with open(os.path.join(M,n),'rb') as f:
        for b in iter(lambda:f.read(1<<22),b''):h.update(b)
    return h.hexdigest()
with ThreadPoolExecutor(4) as ex:H=dict(zip(tohash,ex.map(sha,tohash)))
gh=collections.defaultdict(set);ah=collections.defaultdict(set)
for n,h in H.items():
    ah[h].add(n[:-4])
    if n in gen:gh[h].add(n[:-4])
def probe(n):
    r=subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=codec_name,width,height:format=duration','-of','json',os.path.join(M,n)],capture_output=True,text=True,timeout=120)
    try:
        j=json.loads(r.stdout);s=j['streams'][0];return dict(w=s.get('width'),h=s.get('height'),codec=s.get('codec_name'),seg=round(float(j['format']['duration']),1))
    except Exception:return dict(w=None,h=None,codec=None,seg=None)
with ThreadPoolExecutor(8) as ex:P=dict(zip(sorted(used),ex.map(probe,sorted(used))))
for r in rows:
    b=r['bga'].lower();n=b+'.mp4';p=P.get(n,{});h=H.get(n)
    if not r['bga']:tipo='sin_bga'
    elif n not in F:tipo='falta_video'
    elif n in gen:tipo='generico'
    elif h and gh.get(h):tipo='generico_renombrado'
    elif names[b]>=4 or (h and len(ah[h])>=4):tipo='compartido_muchas'   # a stock clip reused by the pack, not this song's own video
    else:tipo='propio'
    r.update(tipo=tipo,segundos=p.get('seg'),ancho=p.get('w'),alto=p.get('h'),codec=p.get('codec'),mb=round(F[n]/1e6,1) if n in F else None,nota=f"video usado por {names[b]} canciones" if names[b]>1 else '')
keys=['canal','id','titulo','artista','genero','bga','tipo','segundos','ancho','alto','codec','mb','nota']
for name,rs in (('inventario_bms_propios.csv',[r for r in rows if r['tipo']=='propio']),('inventario_bms_todas.csv',rows)):
    with open(os.path.join(O,name),'w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,keys);w.writeheader();w.writerows(rs)
res={}
for label,_ in cats:
    rs=[r for r in rows if r['canal']==label];pr=[r for r in rs if r['tipo']=='propio']
    res[label]=dict(total=len(rs),propios=len(pr),gb=round(sum(r['mb'] or 0 for r in pr)/1000,1),horas=round(sum(r['segundos'] or 0 for r in pr)/3600,1),**{k:v for k,v in collections.Counter(r['tipo'] for r in rs).items() if k!='propio'})
pr=[r for r in rows if r['tipo']=='propio'];s=sorted(r['segundos'] or 0 for r in pr)
json.dump(dict(por_canal=res,totales=collections.Counter(r['tipo'] for r in rows)),open(O+r'\resumen_bms.json','w',encoding='utf8'),ensure_ascii=False,indent=1)
print(collections.Counter(r['tipo'] for r in rows));print('unicos',len({r['bga'] for r in pr}),'horas',sum(s)/3600,'dur',s[:1],s[len(s)//2] if s else 0,s[-1:] if s else 0,collections.Counter((r['ancho'],r['alto']) for r in pr).most_common(8),collections.Counter(r['codec'] for r in pr).most_common(5))
for k,v in res.items():print(k,v)
print('BMS_DONE')
