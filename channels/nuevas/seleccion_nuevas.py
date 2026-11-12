"""Adds the new songs to selection.json and splits IIDX into four channels by title (0x49..0x4c). IDs AC000001+ frozen in gid_map.json. Banner: frame of the song's own movie, dark band with its title and artist
(the SSS/IIDX style, image, so Japanese titles stay); SEL and Aniart use their own title art. Catalog text: romanized title (TITLETRANSLIT, then the folder name when the title is not Latin).
SEL keeps its original pump charts: the F Single made from the same chart at that level is dropped, the original takes its place. usage: seleccion_nuevas.py [--dry]"""
from pathlib import Path
import json,re,subprocess,sys,unicodedata,hashlib,os,tempfile,struct
from concurrent.futures import ThreadPoolExecutor
from PIL import Image,ImageDraw,ImageFont,ImageOps
H=Path(__file__).resolve().parent;SEL=Path('D:/PIU_INFINITY/channels/selection.json');STILLS=H/'stills';FONT='C:/Windows/Fonts/YuGothB.ttc';FONT2='C:/Windows/Fonts/YuGothM.ttc'
CH={'EZ2ON':(0x48,'EZ2ON','EZ2ON REBOOT : R'),'IMAS':(0x4d,'IMAS','CINDERELLA GIRLS'),'LL':(0x40,'LL','ANIME MIX ULTIMATE'),'SEL':(0x4e,'MAINSEL','MAIN SELECTIONS')}
IIDX_PARTS=[0x49,0x4a,0x4b,0x4c]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ascii_text(t):
    t=unicodedata.normalize('NFKC',t or '');t=''.join(c if ' '<=c<='~' else ' ' for c in t);return re.sub(r'\s+',' ',t).strip(' ')
def latin(t):
    a=ascii_text(t);return len(a)>=max(1,len(re.sub(r'\s','',t or ''))*.7)
def order_key(title):   # as prepare_and_validate.order_key
    s=unicodedata.normalize('NFKD',title.casefold());s=''.join(c for c in s if not unicodedata.combining(c));return ' '.join(''.join(c if c.isalnum() else ' ' for c in s).split())
def folder_title(f):
    n=Path(f).name;n=re.sub(r'^\d{5,}\s+','',n);n=re.sub(r'^\([^)]*\)\s*','',n);n=re.sub(r'\s*\([^)]*\)\s*$','',n);n=re.sub(r'\s*\[[^\]]*\]\s*$','',n);return ascii_text(n.replace('_',' '))
def one_line(t):return re.split(r'[\r\n#]',t or '')[0].strip()
def title_of(r):
    t=r['tags'];a=one_line(t.get('TITLETRANSLIT'));b=one_line(t.get('TITLE'))
    if a and latin(a):return ascii_text(a)
    if b and latin(b):return ascii_text(b)
    return folder_title(r['folder']) or ascii_text(b) or 'Untitled'
def artist_of(r):
    t=r['tags'];a=one_line(t.get('ARTISTTRANSLIT'));b=one_line(t.get('ARTIST'))
    if a and latin(a):return ascii_text(a)
    if b and latin(b):return ascii_text(b)
    return {'IMAS':'THE IDOLM@STER CINDERELLA GIRLS','LL':'Love Live!'}.get(r['channel'],'Unknown')
def display(r):
    t=r['tags'];return one_line(t.get('TITLE_UNICODE') or t.get('TITLE')) or title_of(r),one_line(t.get('ARTIST_UNICODE') or t.get('ARTIST')) or artist_of(r)
def fit(text,path,size,width):
    while size>14:
        f=ImageFont.truetype(path,size)
        if f.getlength(text)<=width:return f
        size-=2
    return ImageFont.truetype(path,14)
def size_of(v):
    p=subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height','-of','csv=p=0',v],capture_output=True,text=True).stdout.strip().split(',');return int(p[0]),int(p[1])
def narrow(v):
    w,h=size_of(v);return h>w*9/16*1.02
def banner(r,own=None):
    out=STILLS/(r['key']+'.png')
    if out.exists():return out
    if own:
        ImageOps.fit(Image.open(own).convert('RGB'),(1280,720),Image.Resampling.LANCZOS).save(out);return out
    tmp=os.path.join(tempfile.gettempdir(),f"new_frame_{r['key']}.png");crop='crop=iw:iw*9/16,' if narrow(r['video']) else ''
    for at in (25,10,3,0):
        p=subprocess.run(['ffmpeg','-v','error','-y','-ss',str(at),'-i',r['video'],'-vf',crop+'scale=1280:720','-frames:v','1',tmp],capture_output=True)
        if p.returncode==0 and Path(tmp).exists() and Path(tmp).stat().st_size>10000:break
    im=Image.open(tmp).convert('RGB');band=round(720*.24);y0=720-band;d=ImageDraw.Draw(im);d.rectangle((0,y0,1280,720),fill=(14,16,40));ti,ar=display(r)
    d.text((640,y0+band*.38),ti,font=fit(ti,FONT,74,1220),fill=(245,245,255),anchor='mm');d.text((640,y0+band*.78),ar,font=fit(ar,FONT2,40,1220),fill=(190,200,235),anchor='mm')
    im.save(out);os.remove(tmp);return out
def main():
    dry='--dry' in sys.argv;STILLS.mkdir(exist_ok=True);res=[json.loads(f.read_text(encoding='utf8')) for f in (H/'songs').glob('*/result.json')];res=[r for r in res if r['charts']];res.sort(key=lambda r:r['folder']);print('songs',len(res),flush=True)
    gp=H/'gid_map.json';gmap=json.loads(gp.read_text()) if gp.exists() else {};nxt=max([int(g,16) for g in gmap.values()]+[0xAC000000])+1;recs=[]
    def still(r):
        d=Path(r['folder']);own=next((str(x) for x in sorted(d.iterdir()) if x.name.lower() in('title.jpg','banner.jpg')),None) if r['channel'] in('EZ2ON',) or r['pack']=='SEL' else None
        return banner(r,own)
    with ThreadPoolExecutor(8) as ex:stills=dict(zip([r['key'] for r in res],ex.map(still,res)))
    bad=[]
    for r in res:
        k=r['key']
        if k not in gmap:gmap[k]=f'{nxt:08X}';nxt+=1
        cid,cname,cfull=CH[r['channel']];charts=[];names=set();native=[n for n in r.get('native',[]) if 'nx' in n];drop={(c['mode'],c['level']) for c in []}
        fc=list(r['charts'])
        if native:   # the F Single of the same chart gives way to the original
            top=max((c for c in fc if c['mode']=='Single' and c.get('reduction') in(None,'full')),key=lambda c:c['level'],default=None)
            if top:fc.remove(top)
        def add(name,mode,level,nx,generated,special):
            j=0
            while name+('' if not j else chr(64+j)) in names:j+=1
            name+='' if not j else chr(64+j);names.add(name);charts.append(dict(name=name,mode=mode,level=level,nx=nx,sha256=sha(nx),generated=generated,special=special))
        for n in native:add(('S' if n['mode']=='pump-single' else 'D')+f"{n['level']:02d}",n['mode'],n['level'],n['nx'],False,dict(original=True))
        for c in sorted(fc,key=lambda c:(c['mode'],c['level'],c['tier'])):
            add(('S' if c['mode']=='Single' else 'D')+f"{c['level']:02d}",'pump-single' if c['mode']=='Single' else 'pump-double',c['level'],c['nx'],True,dict(source_chart=c.get('source_chart'),reduction=c.get('reduction'),omitted_conflicts=c.get('omitted_conflicts')))
        bp=[float(x) for x in re.findall(r'=\s*([\d.]+)',r.get('bpm') or '')] or [float(x) for x in re.findall(r'[\d.]+',r.get('bpm') or '')]
        fm=lambda v:f'{v:.2f}'.rstrip('0').rstrip('.');bpm=(fm(bp[0]) if min(bp)==max(bp) else fm(min(bp))+'-'+fm(max(bp))) if bp else '120'
        vid=r['video'];sec=r['video_seconds'];policy=f"own BGA {Path(vid).name} from {sec:.3f}s"
        if k==H.joinpath('x').name:pass
        ani=H/'aniart/bga.mp4'
        if r['channel']=='EZ2ON':assert ani.exists();vid=str(ani);policy='own BGA, first 5 s black (logo)'
        recs.append(dict(game_song_id=gmap[k],channel=cname,channel_id=cid,channel_name=cfull,kind='ARCADE',source_group=r['pack'],source_folder=k,source=r['pack'],title=title_of(r),artist=artist_of(r),bpm=bpm,audio=str(H/'songs'/k/'audio.wav'),preview_audio=None,sample_start=max(0.,float(r.get('sample') or 30)),sample_length=10.,
            video_segments=[dict(beat='0',seconds=sec,file=vid,rate=r.get('video_rate') or 1.)],crop_16_9=narrow(vid),video_policy=policy,preview_video=None,still=str(stills[k]),banner=None,charts=charts,skipped_charts=[]))
    S=json.loads(SEL.read_text(encoding='utf8'));keep=[x for x in S['records'] if x['channel'] not in('IMAS','MAINSEL','LL') and not (x['channel']=='EZ2ON' and x['source_group']=='AGREGAR A EZ2ON')]
    I=sorted((x for x in keep if x['channel']=='IIDX'),key=lambda x:(order_key(x['title']),x['game_song_id']));n=len(I)
    for i,x in enumerate(I):
        p=IIDX_PARTS[i*4//n];x['channel_id']=p;x['channel_name']=f'BEATMANIA IIDX {IIDX_PARTS.index(p)+1}'
    import collections;print('IIDX parts',sorted(collections.Counter(x['channel_id'] for x in I).items()),[I[i*n//4]['title'][:18] for i in range(4)],flush=True)
    print('new',collections.Counter(x['channel'] for x in recs),'charts',sum(len(x['charts']) for x in recs),'crop',sum(x['crop_16_9'] for x in recs),flush=True)
    for x in recs[:0]:print(x)
    if dry:return
    gp.write_text(json.dumps(gmap,indent=1));S['records']=keep+recs;S['songs']=len(S['records']);SEL.write_text(json.dumps(S,ensure_ascii=False,indent=1),encoding='utf8');(H/'selection_ids.txt').write_text(' '.join(x['game_song_id'] for x in recs));print('NUEVAS_SELECTION',len(recs),flush=True)
if __name__=='__main__':main()
