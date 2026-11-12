"""Inventory of the packs in D:\\IIDX\\NEW: chart modes, own BGA, durations, duplicates inside the packs and against the game catalog. Writes inventario.json / inventario.csv. Read only on the packs."""
import sys,re,json,csv,hashlib,struct,subprocess,unicodedata,collections
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
H=Path(__file__).resolve().parent;ROOT=Path('D:/IIDX/NEW');B=Path('D:/Pump It Up Data/PIU');E=Path('E:/Pump It Up Data/PIU')
sys.path[:0]=[str(E),str(E/'nsde_channel'),str(B/'anime_channel_dng')]
sys.dont_write_bytecode=True
import build_omnimix as BO
import simfile as SM
sys.path.insert(0,str(H))
import carga
VID={'.mp4','.avi','.mpg','.mpeg','.mkv','.wmv','.mov','.flv','.webm','.m4v'};AUD={'.mp3','.ogg','.wav','.flac','.m4a'}
def norm(t):
    t=unicodedata.normalize('NFKC',t or '').lower()
    t=re.sub(r'\(.*?\)|\[.*?\]|～.*?～|~.*?~','',t) if re.sub(r'\(.*?\)|\[.*?\]|～.*?～|~.*?~','',t).strip() else t
    return re.sub(r'[^0-9a-z\u3040-\u30ff\u4e00-\u9fff\uac00-\ud7af]','',t)
def probe(p):
    r=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_type,codec_name,width,height,r_frame_rate','-of','json',str(p)],capture_output=True)
    try:j=json.loads(r.stdout)
    except Exception:return {}
    v=next((s for s in j.get('streams',[]) if s.get('codec_type')=='video'),{})
    return dict(seconds=float(j.get('format',{}).get('duration',0) or 0),codec=v.get('codec_name'),w=v.get('width'),h=v.get('height'),fps=v.get('r_frame_rate'))
def find(folder,name):
    if not name:return None
    name=name.replace('\\','/').split('/')[-1].lower()
    for f in folder.iterdir():
        if f.is_file() and f.name.lower()==name:return f
    return None
def simfile(folder,pack):
    fs=sorted(folder.glob('*.ssc'))+sorted(folder.glob('*.sm'));f=fs[0]
    try:tags,charts=carga.parse(f)
    except Exception as e:return dict(pack=pack,folder=str(folder),error='parse: '+repr(e)[:200])
    bg=[];
    for item in tags.get('BGCHANGES','').replace('\n','').split(','):
        p=item.strip().split('=')
        if len(p)>=2 and Path(p[1]).suffix.lower() in VID:bg.append((p[0],p[1],p[2] if len(p)>2 else '1'))
    video=None;vbeat=None;vrate=1.
    for b,n,rate in bg:
        v=find(folder,n)
        if v:video=v;vbeat=b;vrate=float(rate or 1);break
    # a video in the folder that the file does not name: StepMania would not play it, so it stands apart
    loose=[x for x in folder.iterdir() if x.is_file() and x.suffix.lower() in VID and 'preview' not in x.name.lower()]
    audio=find(folder,tags.get('MUSIC')) or next((x for x in sorted(folder.iterdir()) if x.suffix.lower() in AUD),None)
    modes=collections.Counter(c['mode'] for c in charts);m=[(c['mode'],c['meter'],c['difficulty'],sum(c['note_symbols'].get(x,0) for x in '124L')) for c in charts]
    return dict(pack=pack,folder=str(folder),file=f.name,kind='sm',title=tags.get('TITLE',''),translit=tags.get('TITLETRANSLIT',''),artist=tags.get('ARTIST',''),video=str(video) if video else None,video_beat=vbeat,video_rate=vrate,loose=[str(x) for x in loose],
        bg=len(bg),audio=str(audio) if audio else None,offset=tags.get('OFFSET'),bpms=tags.get('BPMS','')[:120],sample=tags.get('SAMPLESTART'),modes=dict(modes),charts=m,banner=tags.get('BANNER'),previewvid=tags.get('PREVIEWVID'))
def osu_head(f):
    t=f.read_bytes().decode('utf8','replace');o={}
    for k in ('Title','TitleUnicode','Artist','ArtistUnicode','Version','Mode','AudioFilename','PreviewTime','CircleSize'):
        m=re.search(rf'^{k}\s*:\s*(.*?)\s*$',t,re.M);o[k]=m[1] if m else ''
    m=re.search(r'^(?:Video|1),\s*(-?\d+)\s*,\s*"([^"]+)"',t,re.M);o['video']=(int(m[1]),m[2]) if m else None
    o['objects']=len(t.split('[HitObjects]')[-1].strip().splitlines()) if '[HitObjects]' in t else 0;return o
def osu(folder,pack):
    fs=sorted(folder.glob('*.osu'));heads=[(f,osu_head(f)) for f in fs];h0=heads[0][1]
    named=next((h['video'] for _,h in heads if h['video']),None);video=find(folder,named[1]) if named else None
    loose=[x for x in folder.iterdir() if x.is_file() and x.suffix.lower() in VID]
    audio=find(folder,h0['AudioFilename'])
    return dict(pack=pack,folder=str(folder),kind='osu',title=h0['Title'],translit='',title_unicode=h0['TitleUnicode'],artist=h0['Artist'],artist_unicode=h0['ArtistUnicode'],video=str(video) if video else None,video_offset_ms=named[0] if named else None,loose=[str(x) for x in loose],
        audio=str(audio) if audio else None,sample=h0['PreviewTime'],modes=dict(collections.Counter(h['Mode'] for _,h in heads)),charts=[(h['Mode'],h['CircleSize'],h['Version'],h['objects']) for _,h in heads],files=[f.name for f,_ in heads])
def catalog():
    pay=B/'final_v363/payloads/D';raw=(pay/'LIST').read_bytes();pool=list(BO.string_entries_from((pay/'LIST.0').read_bytes()));ns,_=struct.unpack_from('<II',raw);out=collections.defaultdict(list)
    for i in range(ns-1):
        s=struct.unpack_from('<9I',raw,44+i*36)
        if s[0]>>28==0xE or s[0]>>16==0xEF or s[1]>=len(pool):continue
        out[norm(pool[s[1]].decode('utf8','replace'))].append((f'{s[0]:08X}',pool[s[1]].decode('utf8','replace'),pool[s[2]].decode('utf8','replace') if s[2]<len(pool) else '',(s[5]&255)+24))
    return out
def main():
    jobs=[]
    for pack in sorted(p.name for p in ROOT.iterdir() if p.is_dir()):
        for f in sorted((ROOT/pack).rglob('*')):
            if f.is_file() and f.suffix.lower() in ('.ssc','.sm','.osu') :jobs.append((pack,f.parent))
    seen=[];[seen.append(j) for j in jobs if j not in seen]
    print('folders',len(seen),flush=True)
    def one(j):
        pack,folder=j
        try:r=osu(folder,pack) if not (list(folder.glob('*.ssc'))+list(folder.glob('*.sm'))) else simfile(folder,pack)
        except Exception as e:return dict(pack=pack,folder=str(folder),error=repr(e)[:300])
        r['sub']=folder.relative_to(ROOT/pack).parts[0] if len(folder.relative_to(ROOT/pack).parts)>1 else ''
        for k in ('video','audio'):
            if r.get(k):r[k+'_info']=probe(r[k])
        v=r.get('video') or (r.get('loose') or [None])[0]
        if v:
            with open(v,'rb') as fh:head=fh.read(4<<20)
            r['video_key']=hashlib.sha256(head).hexdigest()[:16]+str(Path(v).stat().st_size)
        return r
    with ThreadPoolExecutor(8) as ex:rows=list(ex.map(one,seen))
    cat=catalog();vk=collections.Counter(r.get('video_key') for r in rows if r.get('video_key'))
    for r in rows:
        if r.get('error'):continue
        n=norm(r.get('translit') or '');m=norm(r.get('title'))
        r['norm']=m;r['norm2']=n;r['in_game']=(cat.get(m,[]) if m else [])+([x for x in cat.get(n,[]) if n!=m] if n else [])
        r['video_shared']=vk.get(r.get('video_key'),0)
    (H/'inventario.json').write_text(json.dumps(rows,ensure_ascii=False,indent=0),encoding='utf8')
    with open(H/'inventario.csv','w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow('pack sub title artist kind video audio_s video_s video_shared modes in_game folder'.split())
        for r in rows:
            w.writerow([r['pack'],r.get('sub'),r.get('title'),r.get('artist'),r.get('kind'),'SI' if r.get('video') else ('SUELTO' if r.get('loose') else 'NO'),round(r.get('audio_info',{}).get('seconds',0)),round(r.get('video_info',{}).get('seconds',0)),r.get('video_shared'),json.dumps(r.get('modes')),'; '.join(f'{x[0]} {x[1]} ch{x[3]}' for x in r.get('in_game',[])),r['folder']])
    print('INVENTARIO_OK',len(rows),flush=True)
if __name__=='__main__':main()
