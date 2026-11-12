"""Final BGA inventory: IIDX 1st..34 + INFINITAS only. A BGA counts as the song's own when its file is numeric-named (data/movie/<id>.mp4)
and its content is not a byte copy of a generic movie. Songs sharing a movie with another song are flagged. E: is only read.
Output: inventario_bga_propios.csv, inventario_bga_todas.csv, resumen.json"""
import json,re,os,csv,hashlib,subprocess,collections
from concurrent.futures import ThreadPoolExecutor
M=r'E:\IIDX222\001 - Proyecto IIDX\IIDX\LDJ-012-20231018\contents\data\movie';O=r'D:\PIU_IIDX'
D=json.load(open(O+r'\inventario_bga.json',encoding='utf8'));E=D['E'];cat={int(k):v for k,v in D['cat'].items()};non=set(D['non']);F=D['files']
NAMES={0:'1st style',1:'substream',2:'2nd style',3:'3rd style',4:'4th style',5:'5th style',6:'6th style',7:'7th style',8:'8th style',9:'9th style',10:'10th style',11:'IIDX RED',12:'HAPPY SKY',13:'DistorteD',14:'GOLD',15:'DJ TROOPERS',16:'EMPRESS',17:'SIRIUS',18:'Resort Anthem',19:'Lincle',20:'tricoro',21:'SPADA',22:'PENDUAL',23:'copula',24:'SINOBUZ',25:'CANNON BALLERS',26:'Rootage',27:'HEROIC VERSE',28:'BISTROVER',29:'CastHour',30:'RESIDENT',31:'EPOLIS',32:'PINKY CRUSH',33:'SPARKLE SHOWER',34:'ZINRAI',80:'INFINITAS'}
ORDER=sorted(NAMES,key=lambda v:(v==80,v))
I=[dict(x,ver=cat.get(x['id'],x['v'])) for x in E if x['id'] not in non and 'TUTORIAL' not in x['title'].upper()]
isnum=lambda b:bool(re.fullmatch(r'\d+',b))
def sha(n):
    h=hashlib.sha256()
    with open(os.path.join(M,n),'rb') as f:
        for b in iter(lambda:f.read(1<<22),b''):h.update(b)
    return h.hexdigest()
gen={n:s for n,s in F.items() if not isnum(n[:-4])};bysize=collections.defaultdict(list)
for n,s in gen.items():bysize[s].append(n)
nums={x['bga'].lower()+'.mp4' for x in I if isnum(x['bga']) and x['bga'].lower()+'.mp4' in F}
# same-size groups only: hashing every movie of a failing drive is not needed
sizes=collections.defaultdict(list)
for n in nums:sizes[F[n]].append(n)
tohash={n for s,l in sizes.items() if len(l)>1 or s in bysize for n in l}|{g for s,l in sizes.items() if s in bysize for g in bysize[s]}
print('hashing',len(tohash),'of',len(nums),flush=True)
with ThreadPoolExecutor(4) as ex:H=dict(zip(tohash,ex.map(sha,tohash)))
gh=collections.defaultdict(list)
for n,h in H.items():
    if n in gen:gh[h].append(n[:-4])
nh=collections.defaultdict(list)
for n in nums:
    if n in H:nh[H[n]].append(n[:-4])
def probe(n):
    r=subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=codec_name,width,height,r_frame_rate:format=duration','-of','json',os.path.join(M,n)],capture_output=True,text=True,timeout=120)
    try:
        j=json.loads(r.stdout);s=j['streams'][0];return dict(w=s.get('width'),h=s.get('height'),codec=s.get('codec_name'),seg=round(float(j['format']['duration']),1))
    except Exception:return dict(w=None,h=None,codec=None,seg=None)
with ThreadPoolExecutor(8) as ex:P=dict(zip(sorted(nums),ex.map(probe,sorted(nums))))
bga_count=collections.Counter(x['bga'] for x in I if isnum(x['bga']))
rows=[]
for x in I:
    b=x['bga'];n=b.lower()+'.mp4';p=P.get(n,{});h=H.get(n);copyof=[g for g in gh.get(h,[])] if h else []
    same=[o for o in nh.get(h,[]) if o!=b] if h else []
    if not isnum(b):tipo='generico'
    elif n not in F:tipo='falta_video'
    elif copyof:tipo='generico_renombrado'
    else:tipo='propio'
    others=[y for y in I if y['bga']==b and y['id']!=x['id']] if isnum(b) and bga_count[b]>1 else []
    nota=[]
    if others:nota.append('comparte video con: '+', '.join(f"{y['id']} {y['title']}" for y in others))
    if same:nota.append('mismo contenido que: '+', '.join(same))
    if copyof:nota.append('copia de: '+', '.join(copyof))
    if isnum(b) and int(b)!=x['id']:nota.append(f'usa el video {b}')
    rows.append(dict(version=NAMES.get(x['ver'],str(x['ver'])),ver=x['ver'],id=x['id'],titulo=x['title'],titulo_ascii=x['ascii'],artista=x['artist'],genero=x['genre'],bga=b,tipo=tipo,segundos=p.get('seg'),ancho=p.get('w'),alto=p.get('h'),codec=p.get('codec'),mb=round(F[n]/1e6,1) if n in F else None,nota=' | '.join(nota)))
rows.sort(key=lambda r:(ORDER.index(r['ver']) if r['ver'] in ORDER else 99,r['id']))
keys=[k for k in rows[0] if k!='ver']
for name,rs in (('inventario_bga_propios.csv',[r for r in rows if r['tipo']=='propio']),('inventario_bga_todas.csv',rows)):
    with open(os.path.join(O,name),'w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,keys,extrasaction='ignore');w.writeheader();w.writerows(rs)
res=collections.OrderedDict()
for v in ORDER:
    rs=[r for r in rows if r['ver']==v];pr=[r for r in rs if r['tipo']=='propio'];res[NAMES[v]]=dict(total=len(rs),propios=len(pr),genericos=sum(r['tipo']=='generico' for r in rs),renombrados=sum(r['tipo']=='generico_renombrado' for r in rs),falta=sum(r['tipo']=='falta_video' for r in rs),gb=round(sum(r['mb'] or 0 for r in pr)/1000,1))
tot=collections.Counter(r['tipo'] for r in rows);pr=[r for r in rows if r['tipo']=='propio']
dist=collections.Counter((r['ancho'],r['alto']) for r in pr);short=[(r['id'],r['titulo'],r['segundos']) for r in pr if (r['segundos'] or 999)<30]
uniq=len({r['bga'] for r in pr});gb=sum({r['bga']:r['mb'] or 0 for r in pr}.values())/1000
json.dump(dict(por_version=res,totales=tot,resoluciones={str(k):v for k,v in dist.items()},cortos=short,videos_unicos=uniq,gb_unicos=gb,sin_probe=sum(r['segundos'] is None for r in pr)),open(O+r'\resumen.json','w',encoding='utf8'),ensure_ascii=False,indent=1)
print(tot,uniq,round(gb,1),dist.most_common(6),'cortos',len(short),short[:6],'sinprobe',sum(r['segundos'] is None for r in pr))
for k,v in res.items():print(k,v)
print('renamed sample',[(r['id'],r['titulo'],r['nota'][:40]) for r in rows if r['tipo']=='generico_renombrado'][:8])
print('missing',[(r['id'],r['titulo']) for r in rows if r['tipo']=='falta_video'])
print('generic names not numeric unused',len(gen))
