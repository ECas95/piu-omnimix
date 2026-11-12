"""PUMP IT UP RISE noteskin 200000 -> selectable PRIME skin bank 47 (user 2026-10-26: only RISE 1 of the 5).

PRIME bank layout (read from the native PHOENIX bank 46, which is reused as the geometry reference):
  0.G-5.G  six animation frames, 480x288 RGBA = 5 lanes x 3 rows of 96: hold head (body only ABOVE the arrow,
           down to the native cut row of each lane: the same cell is the hold end, so no body may stick out below),
           tap, special note (tap + PRIME's own paw mark);
  6.G      480x192 receptor outlines (white / pressed glow);  BASE.G receptors idle / lit;
  HD1/HD2  Half-Double receptors (lanes LD-LU-C / C-RU-RD);   STEPFX00_0-4 512x512 RGB additive explosion;
  CFG/SPR  same geometry as bank 46 (identical 96 px cells). SD = HD scaled 2/3 (explosions 1/2).
Every RISE sprite is fitted to the native sprite's own bounding box lane by lane, so sizes and positions match.
Menu: COMMAND_ICON SKIN_RISE1 (ON/OFF/DIS) from the skin's arrows, plus its help text.
"""
from pathlib import Path
import sys,struct,json,hashlib,re
import numpy as np
from PIL import Image,ImageFilter,ImageChops
HERE=Path(__file__).resolve().parent;OUT=HERE/'payloads'
RISE=Path(r'E:\IIDX222\001 - Proyecto IIDX\DATA\PIU_RISE_assets\unity\sprites')
REF=Path(r'E:\Pump It Up Data\PIU\noteskin_updates\20261013\assets\USER_INTERFACE\PLAY\SKIN\46')
sys.dont_write_bytecode=True
sys.path[:0]=[r'E:\Pump It Up Data\PIU']
import build_noteskin_assets as N
SKINS=[200000];FIRST_BANK=47
LANES=['LeftDown','LeftUp','Center','RightUp','RightDown'];NUMPAD=[1,7,5,9,3]
def g_read(p):
    d=Path(p).read_bytes();fmt,w,h=struct.unpack_from('<IHH',d)
    return Image.frombytes({0x18:'RGB',0x1020:'RGBA'}[fmt],(w,h),d[8:]).convert('RGBA'),fmt
def g_write(path,im,fmt):
    im=im.convert('RGBA' if fmt==0x1020 else 'RGB');path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(struct.pack('<IHH',fmt,*im.size)+im.tobytes())
def bbox(im):return im.getchannel('A').point(lambda a:255 if a>24 else 0).getbbox()
def fit(src,box,cell=(96,96)):
    """src scaled (aspect kept) into the native sprite's bbox, centred on it, on a transparent cell."""
    src=src.crop(bbox(src));bw,bh=box[2]-box[0],box[3]-box[1];s=min(bw/src.width,bh/src.height)
    im=src.resize((max(1,round(src.width*s)),max(1,round(src.height*s))),Image.Resampling.LANCZOS)
    out=Image.new('RGBA',cell);out.alpha_composite(im,(box[0]+(bw-im.width)//2,box[1]+(bh-im.height)//2));return out
def frames(k,lane):
    i=LANES.index(lane)
    if k<200002:pat=[RISE/f'NOTESKIN_{lane}_{k}_{f:02d}.png' for f in range(7)]
    else:pat=[RISE/f'{k}_{NUMPAD[i]}_{f:02d}.png' for f in range(6)]
    fs=[p for p in pat if p.exists()];assert len(fs)>=6,(k,lane,len(fs));return [Image.open(p).convert('RGBA') for p in fs[:6]]
def long_strip(k,lane,f):
    i=LANES.index(lane)
    c=[RISE/f'NOTESKIN_{lane}_{k}_Long_{f:02d}.png',RISE/f'NOTESKIN_{lane}_{k}_Long.png',RISE/f'NOTESKIN_{lane}_{k}_Long_0.png',
       RISE/f'{k}_{NUMPAD[i]}_l_{f:02d}.png',RISE/f'{k}_{NUMPAD[i]}_l.png']
    return Image.open(next(p for p in c if p.exists())).convert('RGBA')
def base_cells(k,state):
    p=next(p for p in (RISE/f'{k}_base.s_{state}.png',RISE/f'{k}_base.s.png') if p.exists());im=Image.open(p).convert('RGBA')
    # RISE's receptor bar interlocks the diagonal arrows (no empty column between them): each receptor is
    # cut with its own arrow silhouette (frame 0 of the same lane), slid to the best-matching position.
    strip=np.asarray(im).astype(float);A=strip[:,:,3]/255;out=[];pitch=im.width/5
    for i,lane in enumerate(LANES):
        m=frames(k,lane)[0];m=m.resize((round(m.width*im.height/m.height),im.height),Image.Resampling.LANCZOS)
        mask=np.asarray(m.getchannel('A').filter(ImageFilter.MaxFilter(3))).astype(float)/255;mw=mask.shape[1]
        best=None
        for dx in range(-14,15):
            x0=round((i+.5)*pitch-mw/2)+dx
            if x0<0 or x0+mw>im.width:continue
            score=(A[:,x0:x0+mw]*mask).sum()-.5*(A[:,x0:x0+mw]*(1-mask)).sum()
            if best is None or score>best[0]:best=(score,x0)
        x0=best[1];cell=strip[:,x0:x0+mw].copy();cell[:,:,3]*=mask;out.append((Image.fromarray(cell.clip(0,255).astype('uint8'),'RGBA'),x0))
    return im,out   # whole strip + each receptor with its x position in the strip
def largest_part(im):
    """Keep only the largest 8-connected opaque region (the receptor itself), dropping neighbour slivers."""
    a=np.asarray(im).copy();m=a[:,:,3]>24;seen=np.zeros_like(m);best=None
    for y,x in zip(*np.nonzero(m)):
        if seen[y,x]:continue
        stack=[(y,x)];seen[y,x]=True;comp=[]
        while stack:
            cy,cx=stack.pop();comp.append((cy,cx))
            for dy in (-1,0,1):
                for dx in (-1,0,1):
                    ny,nx=cy+dy,cx+dx
                    if 0<=ny<m.shape[0] and 0<=nx<m.shape[1] and m[ny,nx] and not seen[ny,nx]:seen[ny,nx]=True;stack.append((ny,nx))
        if best is None or len(comp)>len(best):best=comp
    keep=np.zeros_like(m)
    if best:ys,xs=zip(*best);keep[list(ys),list(xs)]=True
    keep=np.asarray(Image.fromarray(keep.astype('uint8')*255).filter(ImageFilter.MaxFilter(3)))>0   # keep its soft edge
    a[~keep,3]=0;return Image.fromarray(a,'RGBA')
def fx_frames(k):
    src=k if any((RISE/f'{k}_fx_{n}.png').exists() for n in range(5)) else 200001   # 200000 ships no explosion: RISE's 200001 one
    if (RISE/f'{src}_fx_0.png').exists():return [Image.open(RISE/f'{src}_fx_{n}.png').convert('RGBA') for n in range(5)],1.0
    return [Image.open(RISE/f'{src}_fx_5_{n}.png').convert('RGBA') for n in range(5)],0.62   # per-lane glow: the centre one, ~native spark size

def build():
    ref_frame,_=g_read(REF/'HD/0.G');ref_base,_=g_read(REF/'HD/BASE.G');ref_six,_=g_read(REF/'HD/6.G')
    cell=lambda im,r,c:im.crop((c*96,r*96,c*96+96,r*96+96))
    tap_box=[bbox(cell(ref_frame,1,c)) for c in range(5)];six_box=[bbox(cell(ref_six,0,c)) for c in range(5)]
    strip_box=bbox(ref_base.crop((0,0,480,96)))   # PRIME's receptors are one interlocking strip, not 96 px cells
    body_x=[];body_end=[];paw=[]
    for c in range(5):
        top=np.asarray(cell(ref_frame,0,c))[0:4,:,3].mean(axis=0);xs=np.where(top>20)[0];body_x.append((int(xs.min()),int(xs.max())+1))
        r1=np.asarray(cell(ref_frame,1,c)).astype(int);r2=np.asarray(cell(ref_frame,2,c)).astype(int)
        r0=np.asarray(cell(ref_frame,0,c)).astype(int);body_end.append(int(np.where(((r0[:,:,3]>40)&(r1[:,:,3]<20)).any(1))[0].max())+1)   # last native body row
        mask=(np.abs(r2-r1).sum(axis=2)>90)&(r2[:,:,3]>40)
        p=np.zeros_like(r2);p[mask]=r2[mask];paw.append(Image.fromarray(p.astype('uint8'),'RGBA'))   # PRIME's special-note mark
    payload={}
    def emit(rel,im=None,fmt=0x1020,data=None):payload[rel]=(im,fmt,data)
    for n,k in enumerate(SKINS):
        bank=FIRST_BANK+n;D=f'USER_INTERFACE/PLAY/SKIN/{bank}/HD/'
        lanes={l:frames(k,l) for l in LANES}
        for f in range(6):
            tex=Image.new('RGBA',(480,288))
            for c,l in enumerate(LANES):
                tap=fit(lanes[l][f],tap_box[c])
                strip=long_strip(k,l,f);strip=strip.crop(bbox(strip) or (0,0,strip.width,strip.height))
                x0,x1=body_x[c];body=strip.resize((x1-x0,strip.height),Image.Resampling.LANCZOS)
                head=Image.new('RGBA',(96,96))
                for y in range(0,96,body.height):head.alpha_composite(body,(x0,y))
                a=np.asarray(head).copy();a[body_end[c]:,:,3]=0;head=Image.fromarray(a,'RGBA')
                head=Image.alpha_composite(head,tap)
                special=Image.alpha_composite(tap,paw[c])
                for r,im in enumerate((head,tap,special)):tex.alpha_composite(im,(c*96,r*96))
            emit(D+f'{f}.G',tex)
        # receptors: idle / lit; outlines (6.G) traced from each lane's own receptor shape
        base=Image.new('RGBA',(480,192));six=Image.new('RGBA',(480,192));hds={1:Image.new('RGBA',(480,192)),2:Image.new('RGBA',(480,192))}
        for row,state in ((0,0),(1,1)):
            strip_im,parts=base_cells(k,state)
            bw,bh=strip_box[2]-strip_box[0],strip_box[3]-strip_box[1];sc=min(bw/strip_im.width,bh/strip_im.height)
            ox=strip_box[0]+(bw-round(strip_im.width*sc))//2;oy=strip_box[1]+(bh-round(strip_im.height*sc))//2+row*96
            base.alpha_composite(strip_im.resize((round(strip_im.width*sc),round(strip_im.height*sc)),Image.Resampling.LANCZOS),(ox,oy))
            for hd,keep in ((1,(0,1,2)),(2,(2,3,4))):   # Half-Double: the 3 receptors of each side, cut with their silhouettes
                for c in keep:
                    im,x0=parts[c];hds[hd].alpha_composite(im.resize((round(im.width*sc),round(im.height*sc)),Image.Resampling.LANCZOS),(ox+round(x0*sc),oy))
            if state:continue
            for c in range(5):
                i0=fit(parts[c][0],six_box[c]);a=i0.getchannel('A').point(lambda v:255 if v>60 else 0)
                edge=ImageChops.subtract(a.filter(ImageFilter.MaxFilter(5)),a.filter(ImageFilter.MinFilter(3)))
                white=Image.new('RGBA',(96,96),(255,255,255,0));white.putalpha(edge)
                glow=Image.new('RGBA',(96,96),(255,170,40,0));glow.putalpha(ImageChops.lighter(edge,edge.filter(ImageFilter.GaussianBlur(3)).point(lambda v:min(255,v*2))))
                six.alpha_composite(white,(c*96,0));six.alpha_composite(glow,(c*96,96))
        emit(D+'BASE.G',base);emit(D+'6.G',six);emit(D+'HD1.G',hds[1]);emit(D+'HD2.G',hds[2])
        fx,scale=fx_frames(k)
        for i,im in enumerate(fx):
            canvas=Image.new('RGB',(512,512),(0,0,0))
            t=im.resize((round(512*scale),round(512*scale)),Image.Resampling.LANCZOS) if scale<1 else im.resize((512,512),Image.Resampling.LANCZOS)
            black=Image.new('RGBA',t.size,(0,0,0,255));black.alpha_composite(t);canvas.paste(black.convert('RGB'),((512-t.width)//2,(512-t.height)//2))
            emit(D+f'STEPFX00_{i}.G',canvas,0x18)
        for name in ('00.CFG','01.CFG','SPARK1.SPR'):emit(D+name,data=(REF/'HD'/name).read_bytes())
        emit(D+f'{bank}.CFG',data=(REF/'HD/00.CFG').read_bytes())
    # SD: same assets scaled 2/3 (explosions 1/2), SD geometry files of the reference bank
    for rel,(im,fmt,data) in list(payload.items()):
        sd=rel.replace('/HD/','/SD/')
        if data is not None:
            name=rel.rsplit('/',1)[1];payload[sd]=(None,0,(REF/'SD'/(name if not re.match(r'\d\d\.CFG',name) or name in ('00.CFG','01.CFG') else '00.CFG')).read_bytes());continue
        s=.5 if 'STEPFX' in rel else 2/3;payload[sd]=(im.resize((round(im.width*s),round(im.height*s)),Image.Resampling.LANCZOS),fmt,None)
    return payload

ICONS=Path(r'E:\Pump It Up Data\PIU\noteskin_updates\20261013\assets\USER_INTERFACE\SELECT\COMMAND\COMMAND_ICON');LOGO=Path(r'D:\Pump It Up Data\logo')
def logo_tile(tile,logo):
    """The tile's interior (inside its border) repainted with its own dark colour, the logo fitted inside it;
    the logo is dimmed like the tile itself (OFF / disabled states are darker than ON)."""
    a=np.asarray(tile).copy();inner=np.asarray(tile.getchannel('A').filter(ImageFilter.MinFilter(9)))>200
    rim=inner&~(np.asarray(Image.fromarray(inner.astype('uint8')*255).filter(ImageFilter.MinFilter(5)))>0)   # tile background only, not the arrow
    ys,xs=np.nonzero(inner);inner[ys.min():ys.max()+1,xs.min():xs.max()+1]=True;a[inner,:3]=np.median(a[rim][:,:3],axis=0).astype('uint8');out=Image.fromarray(a,'RGBA')
    box=(xs.min(),ys.min(),xs.max()+1,ys.max()+1);lg=Image.open(logo).convert('RGBA');lg=lg.crop(bbox(lg))
    lg=fit(lg,(0,0,box[2]-box[0],box[3]-box[1]),(box[2]-box[0],box[3]-box[1]))
    dim=np.asarray(tile)[ys,xs,:3].max()/max(1,np.asarray(g_read(ICONS/'HD/NS_PHOENIX_ON_0.G')[0])[...,:3].max())
    if dim<.95:lg=Image.merge('RGBA',(*[c.point(lambda v:round(v*dim)) for c in lg.split()[:3]],lg.getchannel('A')))
    out.alpha_composite(lg,box[:2]);return out
def icons(payload):
    """COMMAND_ICON entries, sized like the native SKIN_FIESTA2 icon of each quality."""
    sys.path[:0]=[r'E:\Pump It Up Data\PIU\nsde_channel']
    from current_parent import load
    P,g=load()
    def sprimage(folder,name):
        spr=g.get('/'+folder+'/'+name).decode();t=re.findall(r'T (\S+) 0 0 \d+ \d+ (\d+) (\d+) (\d+) (\d+)',spr)[-1]
        im,_=g_read_bytes(g.get('/'+folder+'/'+t[0].split('.')[0].upper()+'.G'));return im.crop(tuple(map(int,t[1:])))
    def g_read_bytes(d):
        fmt,w,h=struct.unpack_from('<IHH',d);return Image.frombytes({0x18:'RGB',0x1020:'RGBA'}[fmt],(w,h),d[8:]).convert('RGBA'),fmt
    for q in ('HD','SD'):
        folder=f'USER_INTERFACE/SELECT/COMMAND/COMMAND_ICON/{q}';w,h=sprimage(folder,'SKIN_FIESTA2_ON_EN.SPR').size
        # user 2026-10-29: PHOENIX and RISE icons show their logo (D:\Pump It Up Data\logo), on PHOENIX's own tile like the XX icon
        tex=lambda n:g_read(ICONS/q/f'NS_PHOENIX_{n}.G')[0]
        for name,logo in (('PHOENIX','phoenix.png'),('RISE1','rise.png')):
            for n in ('ON_0','OFF_0','DIS_1'):   # DIS_0 is the shared "forbidden" sign; SD = the HD icon scaled (61x47 -> 42x33)
                im=logo_tile(g_read(ICONS/'HD'/f'NS_PHOENIX_{n}.G')[0],LOGO/logo)
                if q=='SD':sd=Image.new('RGBA',(64,64));sd.alpha_composite(im.crop((0,0,61,47)).resize((42,33),Image.Resampling.LANCZOS));im=sd
                payload[f'{folder}/NS_{name}_{n}.G']=(im,0x1020,None)
            if name=='RISE1':
                payload[f'{folder}/NS_RISE1_DIS_0.G']=(tex('DIS_0'),0x1020,None)
                for st in ('ON','OFF','DIS'):payload[f'{folder}/SKIN_RISE1_{st}_EN.SPR']=(None,0,(ICONS/q/f'SKIN_PHOENIX_{st}_EN.SPR').read_bytes().replace(b'ns_phoenix_',b'ns_rise1_'))
        desc=sprimage(f'USER_INTERFACE/SELECT/COMMAND/COMMAND_REAL/{q}/EN','CWR_NOTESKIN_PRIME.SPR')
        text=N.text_like(desc,'Set PIU RISE Note Skin');payload[f'{folder}/NS_RISE_HELP.G']=(text.convert('RGBA'),0x1020,None)
        for st in ('ON','OFF','DIS'):payload[f'{folder}/SKIN_RISE_HELP_{st}_EN.SPR']=(None,0,f'TYPE tile\r\nNUM 1\r\nT ns_rise_help.tga 0 0 {desc.width} {desc.height} 0 0 {desc.width} {desc.height}\r\n'.encode())

def main():
    payload=build();icons(payload);records=[]
    for rel,(im,fmt,data) in sorted(payload.items()):
        p=OUT/rel
        if data is not None:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        else:g_write(p,im,fmt)
        b=p.read_bytes();records.append(dict(path='/'+rel,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
    for f in OUT.rglob('*.SPR'):   # every texture referenced by a sprite must exist
        for tex in re.findall(r'^T (\S+)',f.read_text(),re.M):
            assert (f.parent/(tex.split('.')[0].upper()+'.G')).is_file() or (REF/f.parent.name/(tex.split('.')[0].upper()+'.G')).is_file(),(f,tex)
    (HERE/'manifest.json').write_text(json.dumps(dict(skins=SKINS,banks=list(range(FIRST_BANK,FIRST_BANK+len(SKINS))),records=records),indent=1))
    print('RISE_NOTESKINS_BUILT',len(records))

if __name__=='__main__':main()
