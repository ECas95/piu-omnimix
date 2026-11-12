"""Channel 0x49 records for D:\\PIU_INFINITY\\channels\\selection.json (same schema as SSS). Banner: frame of the song's own movie (cut to 16:9), dark band below with its
title and artist as the SSS channel (image, so the Japanese originals stay). Catalog text: ASCII title of the game, artist reduced to what the selector font can draw.
IDs AB000001+ frozen in gid_map.json. usage: seleccion_canal.py [--banners-only id...]"""
from pathlib import Path
import json,re,subprocess,sys,unicodedata,hashlib,tempfile,os
from concurrent.futures import ThreadPoolExecutor
from PIL import Image,ImageDraw,ImageFont
H=Path(__file__).resolve().parent;CANAL=H/'canal';SEL=Path('D:/PIU_INFINITY/channels/selection.json');MOVIE=Path('E:/IIDX222/001 - Proyecto IIDX/IIDX/LDJ-012-20231018/contents/data/movie')
STILLS=H/'canal/stills';FONT='C:/Windows/Fonts/YuGothB.ttc';FONT2='C:/Windows/Fonts/YuGothM.ttc'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ascii_text(t):
    t=unicodedata.normalize('NFKC',t or '');t=''.join(c if ' '<=c<='~' else ' ' for c in t)
    return re.sub(r'\s+',' ',t).strip(' ')
def fit(text,path,size,width):
    while size>14:
        f=ImageFont.truetype(path,size)
        if f.getlength(text)<=width:return f
        size-=2
    return ImageFont.truetype(path,14)
def banner(r):
    out=STILLS/f"{r['id']}.png"
    if out.exists():return out
    tmp=os.path.join(tempfile.gettempdir(),f"iidx_frame_{r['id']}.png")
    subprocess.run(['ffmpeg','-v','error','-y','-ss','25','-i',str(MOVIE/(r['bga']+'.mp4')),'-vf','crop=iw:iw*9/16,scale=1280:720','-frames:v','1',tmp],check=True)
    im=Image.open(tmp).convert('RGB');band=round(720*.24);y0=720-band;d=ImageDraw.Draw(im);d.rectangle((0,y0,1280,720),fill=(14,16,40))
    t=fit(r['title'],FONT,74,1220);a=fit(r['artist'],FONT2,40,1220)
    d.text((640,y0+band*.38),r['title'],font=t,fill=(245,245,255),anchor='mm');d.text((640,y0+band*.78),r['artist'],font=a,fill=(190,200,235),anchor='mm')
    im.save(out);os.remove(tmp);return out
def main():
    STILLS.mkdir(parents=True,exist_ok=True);res=[json.loads(f.read_text(encoding='utf8')) for f in (CANAL/'songs').glob('*/result.json')]
    res=[r for r in res if r['charts']];res.sort(key=lambda r:r['id']);print('songs',len(res),flush=True)
    with ThreadPoolExecutor(8) as ex:stills=dict(zip([r['id'] for r in res],ex.map(banner,res)))
    gp=H/'gid_map.json';gmap=json.loads(gp.read_text()) if gp.exists() else {};nxt=max([int(g,16) for g in gmap.values()]+[0xAB000000])+1;recs=[];noart=0
    for r in res:
        k=str(r['id'])
        if k not in gmap:gmap[k]=f'{nxt:08X}';nxt+=1
        charts=[];names=set()
        for c in sorted(r['charts'],key=lambda c:(c['mode'],c['level'],c['tier'])):
            name=('S' if c['mode']=='Single' else 'D')+f"{c['level']:02d}";j=0
            while name+('' if not j else chr(64+j)) in names:j+=1     # upper case: the game upper-cases every path
            name+='' if not j else chr(64+j);names.add(name);assert sha(c['nx'])==c['sha256']
            charts.append(dict(name=name,mode='pump-single' if c['mode']=='Single' else 'pump-double',level=c['level'],nx=c['nx'],sha256=c['sha256'],generated=True,special=dict(source_chart=c.get('source_chart'),reduction=c.get('reduction'),omitted_conflicts=c.get('omitted_conflicts'))))
        bp=sorted({round(b,2) for x in r['refs'] for _,b in x['bpms']});fmt=lambda v:f'{v:.2f}'.rstrip('0').rstrip('.')
        art=ascii_text(r['artist']);noart+=not art;d=r['delay']/60   # bga_delay is in 1/60 s (sync_grupo.py)
        pv=CANAL/'songs'/k/'preview.wav'
        recs.append(dict(game_song_id=gmap[k],channel='IIDX',channel_id=0x49,channel_name='BEATMANIA IIDX',kind='ARCADE',source_group='IIDX',source_folder=k,source='beatmania_iidx',title=ascii_text(r['ascii'] or r['title']) or f"IIDX {k}",artist=art or 'beatmania IIDX',
            bpm=fmt(bp[0]) if len(bp)==1 else fmt(bp[0])+'-'+fmt(bp[-1]),audio=str(CANAL/'songs'/k/'audio.wav'),preview_audio=str(pv) if pv.exists() else None,sample_start=r.get('sample_start',30.),sample_length=10.,
            video_segments=[dict(beat='0',seconds=d,file=str(MOVIE/(r['bga']+'.mp4')),rate=1.)],crop_16_9=True,video_policy=f"IIDX own BGA {r['bga']}.mp4 from {d:.3f}s, cut to 16:9",preview_video=None,still=str(stills[r['id']]),banner=None,charts=charts,skipped_charts=[]))
    gp.write_text(json.dumps(gmap,indent=1));S=json.loads(SEL.read_text(encoding='utf8'));S['records']=[x for x in S['records'] if x['channel']!='IIDX']+recs;S['songs']=len(S['records'])
    SEL.write_text(json.dumps(S,ensure_ascii=False,indent=1),encoding='utf8');print('IIDX_SELECTION',len(recs),'songs',sum(len(x['charts']) for x in recs),'charts; artist replaced',noart,flush=True)
if __name__=='__main__':main()
