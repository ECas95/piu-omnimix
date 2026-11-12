"""Select-screen assets for the PRO 1 / PRO 2 / INFINITY channels (ids 0x44-0x46) + Infinity loading wallpapers.

Host only; reads the installed game view (read-only) and the 17-channel UI payloads, writes ui_payloads/.
- MAIN_FULL_A3 header (slot cid+5) and MAIN_FULL_C2 description (slot cid): same native-glyph lettering as
  the other channels (channel_style_v45_merged17); 'Y' is composed from the native V and I glyphs.
- MAIN_FULL_C hexagon: the official Infinity group emblem (Graphics/GroupFolders), fitted to PRIME's hexagon
  bounds like the other channel banners; slots 37 (retired NSDE), 43 (unused WPF) and 21 (empty).
- EFF_CH65-67 channel sounds (2.5 s stings from Infinity's own intro/attract/title audio).
- Loading wallpapers prime_29..38 = Infinity _loading pic3..pic12 (the ten the Infinity theme shows).
"""
from pathlib import Path
import numpy as np
import sys,json,hashlib,subprocess,importlib.util
from PIL import Image,ImageOps,ImageDraw,ImageFilter,ImageChops
HERE=Path(__file__).resolve().parent;E=Path(r'E:\Pump It Up Data\PIU');SRC=Path(r'D:\PIU_INFINITY\channels\ui_src')
sys.dont_write_bytecode=True
V45=E/'anime_final_v8/channel_style_v45_merged17'
sys.path[:0]=[str(E),str(E/'nsde_channel'),str(V45)]
import build_channel_assets as A
import prepare_native_headers as H
spec=importlib.util.spec_from_file_location('v45_ui',V45/'prepare_ui_candidate.py');U=importlib.util.module_from_spec(spec);spec.loader.exec_module(U)
from current_parent import load
CHANNELS=[(0x44,'PUMP IT UP PRO','PIU PRO','08 Pump It Up Pro 1.png',37,(r'D:\Pump It Up Data\SPEECH\Pump It Up Pro.mp3',0),'68_PUMP_IT_UP_PRO.WAV'),
          (0x45,'PUMP IT UP PRO 2','PIU PRO 2','09 Pump It Up Pro 2.png',43,(r'D:\Pump It Up Data\SPEECH\Pump It Up Pro 2.mp3',0),'69_PUMP_IT_UP_PRO_2.WAV'),
          (0x46,'PUMP IT UP INFINITY','PIU INFINITY','10 Pump It Up Infinity.png',21,(r'D:\Pump It Up Data\SPEECH\Pump It Up Infinity.mp3',0),'70_PUMP_IT_UP_INFINITY.WAV'),
          # v372: the game's own title screen (3S logo) and its title music
          (0x47,'SABIN SOUND STAR','SABIN SOUND STAR',r'D:\SSS\ui\title.png',22,(r'D:\Pump It Up Data\SPEECH\Sabin Sound Star.mp3',0),'71_SABIN_SOUND_STAR.WAV'),
          # v378: the user's neon hexagon banner, EZ2ON's own title intro; hexagon slot 25 (empty, next to fc_dummy)
          (0x48,'EZ2ON REBOOT R','EZ2ON REBOOT R',r'D:/Pump It Up Data/Marco hexagonal neón EZ2ON REBOOT_R.png',25,(r'D:\Pump It Up Data\SPEECH\EZ2ON Reboot R.mp3',0),'72_EZ2ON_REBOOT_R.WAV'),
          # 2026-11: BEATMANIA IIDX, hexagon slot 16 (the only empty one)
          (0x49,'BEATMANIA IIDX 1','BEATMANIA IIDX 1',r'D:\PIU_IIDX\ui\part1.png',16,(r'D:\Pump It Up Data\SPEECH\Beatmania IIDX Part 1.mp3',0),'73_BEATMANIA_IIDX.WAV'),
          # 2026-11 (patch 12): IIDX parts 2-4 on 85/80/81 = RANDOM/TRAIN/MISSION hexagons, those channels taken off the Full Mode menu (user). Before: IIDX in four parts sharing hexagon 16 (MAIN_FULL_C has 100 slots and 90-99 are the description digits: patch 10 put art there and it showed under every description); CINDERELLA GIRLS and MAIN SELECTIONS on 78/88, the stock FAVORITE/UCS hexagons (shown only with a profile / UCS data)
          (0x4a,'BEATMANIA IIDX 2','BEATMANIA IIDX 2',r'D:\PIU_IIDX\ui\part2.png',85,(r'D:\Pump It Up Data\SPEECH\Beatmania IIDX Part 2.mp3',0),'74_BEATMANIA_IIDX_2.WAV'),
          (0x4b,'BEATMANIA IIDX 3','BEATMANIA IIDX 3',r'D:\PIU_IIDX\ui\part3.png',80,(r'D:\Pump It Up Data\SPEECH\Beatmania IIDX Part 3.mp3',0),'75_BEATMANIA_IIDX_3.WAV'),
          (0x4c,'BEATMANIA IIDX 4','BEATMANIA IIDX 4',r'D:\PIU_IIDX\ui\part4.png',81,(r'D:\Pump It Up Data\SPEECH\Beatmania IIDX Part 4.mp3',0),'76_BEATMANIA_IIDX_4.WAV'),
          (0x4d,'CINDERELLA GIRLS','CINDERELLA GIRLS',r'D:\PIU_IIDX\ui\imas.png',78,(r'D:\Pump It Up Data\SPEECH\The Idolmaster Cinderella Girls.mp3',0),'77_CINDERELLA_GIRLS.WAV'),
          (0x4e,'MAIN SELECTIONS','MAIN SELECTIONS',r'D:\PIU_IIDX\ui\mainsel.png',88,(r'D:\Pump It Up Data\SPEECH\Main Selections.mp3',0),'78_MAIN_SELECTIONS.WAV')]
CORE={0x47:(.14,.1,.9,.9)}   # emblem area shown in the hexagon (fractions); default = inside the Infinity emblems' frame
DIRECT={0x48,0x49,0x4a,0x4b,0x4c,0x4d,0x4e}   # banner already drawn as a framed hexagon: the whole image fills PRIME's hexagon silhouette

def hex_direct(ref,banner):
    """The banner (already a framed hexagon) stretched onto the hexagon's own bounds inside the reference, then cut to its silhouette."""
    alpha=ref.getchannel('A');box=alpha.point(lambda a:255 if a>8 else 0).getbbox()
    out=Image.new('RGBA',ref.size,(0,0,0,0));out.paste(banner.convert('RGBA').resize((box[2]-box[0],box[3]-box[1]),Image.Resampling.LANCZOS),box[:2])
    out.putalpha(ImageChops.multiply(out.getchannel('A'),alpha));return out
OUT=HERE/'ui_payloads';payload={}
sha=lambda b:hashlib.sha256(b).hexdigest()
def emit(path,data):payload[path]=data

def glyph_y(glyphs):
    """Native-style Y: upper arms of the native V over the lower stem of the native I (same colour and glow)."""
    v,vw=glyphs['V'];i,iw=glyphs['I']
    out=Image.new('RGBA',v.size);out.alpha_composite(v.crop((0,0,v.width,21)),(0,0))
    stem=i.crop((0,20,i.width,i.height));out.alpha_composite(stem,((v.width-i.width)//2,20))
    return out,vw

SPEECH=r'D:\Pump It Up Data\SPEECH'
OLD_VOICES={'EFF_CH45':'EZ2Dancer','EFF_CH46':'Rave It Out','EFF_CH49':'DJ Max Respect','EFF_CH50':"Otaku's Dream Collection Part 1",'EFF_CH51':"Otaku's Dream Collection Part 2",'EFF_CH52':'Anime Mix Part 1','EFF_CH53':'Anime Mix Part 2',
            'EFF_CH56':'Pump It Up The Inedit Plus','EFF_CH58':'Dance Super Station','EFF_CH59':'Pump It Up Rise','EFF_CH60':'Anime Mix Part 3','EFF_CH61':'Anime Mix Ultimate','EFF_CH63':'Pop Culture','EFF_CH64':'Project Sekai Colorful Stage'}
def voice_wav(src,out):
    """A channel voice as the stock ones: whole recording, 48 kHz stereo 16-bit, speech level of PRIME's own voices (active RMS about -10.5 dBFS), peaks limited."""
    x=np.frombuffer(subprocess.run(['ffmpeg','-v','error','-i',str(src),'-ac','1','-ar','48000','-f','f32le','-'],capture_output=True,check=True).stdout,np.float32)
    v=x[np.abs(x)>.01];g=10**(-10.5/20)/max(float(np.sqrt((v**2).mean())) if len(v) else 1.,1e-6)
    subprocess.run(['ffmpeg','-v','error','-y','-f','f32le','-ar','48000','-ac','1','-i','-','-af','alimiter=limit=0.97:attack=1:release=50:level=false','-ar','48000','-ac','2','-c:a','pcm_s16le',str(out)],input=(x*g).astype(np.float32).tobytes(),check=True)

def glyph_4(glyphs):
    """Native 4 of the LV.4 level label, brought to the cap height of the native 3 (the atlas rescales LV.3 the same way)."""
    def cap(g):
        m=np.array(g);ys=np.where(((m[:,:,3]>200)&(m[:,:,0]>200)).any(1))[0];return ys.max()-ys.min()+1,ys.min()
    g,w=glyphs['4'];c4,_=cap(g);c3,top3=cap(glyphs['3'][0]);k=c3/c4
    g=g.resize((max(1,round(g.width*k)),max(1,round(g.height*k))),Image.Resampling.LANCZOS);_,top=cap(g)
    out=Image.new('RGBA',(g.width,40));out.alpha_composite(g,(0,max(0,top3-top)));return out,max(1,round(w*k))

def glyph_b(glyphs):
    """Native-style B (SABIN): the square native P (stem, top bowl, middle bar) united with the native D (right side, bottom bar)."""
    p,pw=glyphs['P'];d,_=glyphs['D'];out=Image.new('RGBA',p.size);dd=Image.new('RGBA',p.size);dd.alpha_composite(d,(0,0))
    return ImageChops.lighter(p,dd),pw

def hex_art(ref,emblem,area=(.085,.27,.915,.73)):
    """PRIME's own channel hexagon frame (MC_PR) filled with the channel emblem's art and full logo."""
    alpha=ref.getchannel('A');inner=alpha.point(lambda a:255 if a>200 else 0).filter(ImageFilter.MinFilter(max(3,ref.width//80)*2+1));box=inner.getbbox()
    w,h=emblem.size;core=emblem.crop((int(w*area[0]),int(h*area[1]),int(w*area[2]),int(h*area[3])))   # default: inside the Infinity emblem's metal frame
    bw,bh=box[2]-box[0],box[3]-box[1];layer=Image.new('RGBA',ref.size,(0,0,0,255))
    bg=ImageOps.fit(core,(bw,bh),Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(bw/23));bg=Image.blend(bg,Image.new('RGBA',bg.size,(0,0,0,255)),.45)
    layer.alpha_composite(bg,box[:2])
    logo=ImageOps.contain(core,(int(bw*.98),int(bh*.98)),Image.Resampling.LANCZOS)
    fw=max(2,logo.width//14);fade=Image.new('L',logo.size,0);ImageDraw.Draw(fade).rectangle((fw,fw//2,logo.width-fw,logo.height-fw//2),fill=255)
    fade=fade.filter(ImageFilter.GaussianBlur(fw/2));logo.putalpha(ImageChops.darker(logo.getchannel('A'),fade))
    layer.alpha_composite(logo,(box[0]+(bw-logo.width)//2,box[1]+(bh-logo.height)//2))
    out=ref.copy();out.paste(layer,(0,0),inner);return out

def main():
    if ('FA_CH_L04','LV.4') not in H.SOURCES:H.SOURCES.append(('FA_CH_L04','LV.4'))   # native 4 for BEATMANIA IIDX 4
    P,game=load();glyphs,_=H.atlas();glyphs['Y']=glyph_y(glyphs);glyphs['B']=glyph_b(glyphs);glyphs['4']=glyph_4(glyphs)
    review=HERE/'ui_review';review.mkdir(parents=True,exist_ok=True)
    heads={cid:H.render(label,glyphs) for cid,label,*_ in CHANNELS}
    descs={cid:U.description(short)[0] for cid,_,short,*_ in CHANNELS}
    for cid,*_ in CHANNELS:heads[cid].save(review/f'header_{cid}.png');descs[cid].save(review/f'description_{cid}.png')
    # headers + descriptions: start from the 17-channel layouts (V45 payloads) so every existing slot is kept
    for mode,template,kind in (('MAIN_FULL_A3','FA_CH_PRIME.SPR','HEAD'),('MAIN_FULL_C2','FC2_PR.SPR','DESC')):
        for folder in sorted((A.PRIME/'USER_INTERFACE/SELECT'/mode).glob('*/*')):
            rel='/'+folder.relative_to(A.PRIME).as_posix();v45=V45/'payloads'/rel.lstrip('/')/'.BGA'
            bga=v45.read_bytes() if v45.exists() else game.get(rel+'/.BGA');before=[bga[o:o+n] for o,n in A.bga_slots(bga)];size=A.crop(folder,template).size
            changed=[]
            for cid,*_ in CHANNELS:
                slot=cid+5 if mode=='MAIN_FULL_A3' else cid;name=f'V45_{cid}_{kind}'
                art=(heads if kind=='HEAD' else descs)[cid]
                if art.size!=size:art=art.resize(size,Image.Resampling.LANCZOS)
                canvas=Image.new('RGBA',(A.pot(art.width),A.pot(art.height)));canvas.alpha_composite(art)
                emit(rel+'/'+name+'.G',A.save_g(canvas));emit(rel+'/'+name+'.SPR',A.spr(name.lower()+'.tga',*size))
                bga=A.bga_with_sprite(bga,slot,template.lower(),name.lower()+'.spr');changed.append(slot)
            after=[bga[o:o+n] for o,n in A.bga_slots(bga)]
            assert len(after)==len(before) and all(a==b for k,(a,b) in enumerate(zip(before,after)) if k not in changed)
            emit(rel+'/.BGA',bga)
    # hexagon emblems
    done=set()
    for cid,label,short,emblem,slot,*_ in CHANNELS:
        if slot in done:continue   # shared hexagon
        done.add(slot)
        art=Image.open(SRC/'Graphics/GroupFolders'/emblem).convert('RGBA');art=art.crop(art.getbbox())
        for folder in sorted((A.PRIME/'USER_INTERFACE/SELECT/MAIN_FULL_C').glob('*/*')):
            rel='/'+folder.relative_to(A.PRIME).as_posix()
            bga=payload.get(rel+'/.BGA') or game.get(rel+'/.BGA');offset,_=A.bga_slots(bga)[slot]
            spr=bga[offset:offset+64].split(b'\0')[0].decode().upper()
            if spr.startswith('FC_BOX_'):   # the slot keeps its layout under a name of its own
                spr=f'MC_CH{cid:X}.SPR';bga=bga[:offset]+spr.lower().encode().ljust(64,b'\0')+bga[offset+64:];emit(rel+'/.BGA',bga)
            if not spr:   # one sprite name per empty slot (v374: SSS reused MC_INF.SPR, left slot 22 empty and overwrote Infinity's art)
                spr='MC_INF.SPR' if cid==0x46 else f'MC_CH{cid:X}.SPR';bga=A.bga_with_sprite(bga,slot,'mc_pr.spr',spr.lower());emit(rel+'/.BGA',bga)
            values=list(map(int,game.get(rel+'/MC_PR.SPR').decode().splitlines()[2].split()[2:10]));w,h=values[2]-values[0],values[3]-values[1]
            reference=A.crop(folder,'MC_PR.SPR');assert (w,h)==reference.size
            factor=3 if folder.parent.name=='HD' else 2;pw,ph=w*factor,h*factor
            ref=reference.resize((pw,ph),Image.Resampling.LANCZOS)
            canvas=Image.new('RGBA',(A.pot(pw),A.pot(ph)));canvas.alpha_composite(hex_direct(ref,art) if cid in DIRECT else hex_art(ref,art,*([CORE[cid]] if cid in CORE else [])))
            name=f'FINAL_BANNER_{cid}'
            emit(rel+'/'+name+'.G',A.save_g(canvas))
            emit(rel+'/'+spr,('TYPE tile\r\nNUM 1\r\nT '+name.lower()+'.tga '+' '.join(map(str,values[:4]))+f' 0 0 {pw} {ph}\r\n').encode())
            if folder.parent.name=='HD' and folder.name=='EN':canvas.crop((0,0,pw,ph)).resize((w,h),Image.Resampling.LANCZOS).save(review/f'banner_{cid}.png')
    # channel sounds
    sfx=game.get('/CONFIG/SFX/SELECT.TXT');tmp=HERE/'wav';tmp.mkdir(exist_ok=True)
    for n,(cid,label,short,emblem,slot,sound,wav) in enumerate(CHANNELS):
        key=f'EFF_CH{65+n}'.encode();assert key not in sfx
        out=tmp/wav
        voice_wav(SRC/sound[0],out)
        emit('/WAVE/'+wav,out.read_bytes());sfx+=b'\r\n'+key+b'\t= "WAVE/'+wav.encode()+b'"\r\n'
    # voices of the channels older than PRO (user 2026-11-07): a key on a shared sound (S_C_MOVE.WAV) gets a file of its own, never the shared one overwritten
    import re
    for key,name in OLD_VOICES.items():
        m=re.search(rb'(?m)^'+key.encode()+rb'\s*=\s*"([^"]+)"',sfx);assert m,key;f=m[1].decode()
        if len(re.findall(rb'"'+re.escape(m[1])+rb'"',sfx))>1:
            f=f'WAVE/V_{key}.WAV';sfx=sfx[:m.start(1)]+f.encode()+sfx[m.end(1):]
        out=tmp/Path(f).name;voice_wav(Path(SPEECH)/(name+'.mp3'),out);emit('/'+f.upper(),out.read_bytes())
    emit('/CONFIG/SFX/SELECT.TXT',sfx)
    # loading wallpapers
    for n,pic in enumerate(['pic3.png','pic4.jpg','pic5.jpg','pic6.jpg','pic7.jpg','pic8.jpg','pic9.jpg','pic10.jpg','pic11.jpg','pic12.png'],29):
        im=Image.open(SRC/'BGAnimations/_loading'/pic).convert('RGB')
        for q,size in (('HD',(1280,720)),('SD',(640,480))):
            native=game.get(f'/USER_INTERFACE/LOADING/{q}/PRIME_01.G');assert native[:8]==bytes.fromhex('18000000')+size[0].to_bytes(2,'little')+size[1].to_bytes(2,'little')
            emit(f'/USER_INTERFACE/LOADING/{q}/PRIME_{n:02d}.G',native[:8]+im.resize(size,Image.Resampling.LANCZOS).tobytes())
    records=[]
    for path,data in sorted(payload.items()):
        t=OUT/path.lstrip('/');t.parent.mkdir(parents=True,exist_ok=True);t.write_bytes(data);records.append(dict(path=path,bytes=len(data),sha256=sha(data)))
    (HERE/'ui_manifest.json').write_text(json.dumps(dict(prepared=True,installed=False,channels=[c[:2] for c in CHANNELS],records=records,parent_archive=game.names[-1]),indent=1))
    print('INFINITY_UI_PREPARED',len(records),flush=True)

if __name__=='__main__':main()
