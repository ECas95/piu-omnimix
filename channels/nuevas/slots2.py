"""What do the fc_box_N hexagon-file sprites hold, and do the screen scenes use them? Read only."""
import sys,json,struct
from pathlib import Path
from PIL import Image
E=Path('E:/Pump It Up Data/PIU');F=Path('D:/Pump It Up Data/PIU/final_v363');V45=E/'anime_final_v8/channel_style_v45_merged17'
sys.path[:0]=[str(E),str(E/'nsde_channel'),str(V45)]
sys.dont_write_bytecode=True
from current_parent import load
from build_next_media_chunk import attach
import build_channel_assets as A
P,g=load()
for x in json.loads((F/'package/archives.json').read_text())['archives']:attach(P,g,F/'package' if x['folder']=='package' else F/'package'/x['folder'])
for f in ('patch','patch3','patch4','patch5_rise','patch6'):attach(P,g,F/f/'archive')
for a in json.loads((F/'patch7/patch.json').read_text())['archives']:attach(P,g,F/'patch7'/a['folder'])
for f in ('patch8','patch9'):attach(P,g,F/f/'archive')
rel='/USER_INTERFACE/SELECT/MAIN_FULL_C/HD/EN';bga=g.get(rel+'/.BGA');slots=A.bga_slots(bga);print('head',bga[:16].hex())
files=[k.decode() for k in g.index.files if k.startswith(rel.encode()+b'/')];print(len(files),'files; FC_BOX:',[f.split('/')[-1] for f in files if 'FC_BOX' in f or 'FC_D' in f])
sheet=Image.new('RGBA',(1100,120),(40,40,60,255));x=4
for i in [15,17,26,78,88]+list(range(90,100)):
    o,sz=slots[i];nm=bga[o:o+64].split(b'\0')[0].decode().upper();first=bga[o+68:o+68+100]
    print(i,nm,'frame0',struct.unpack_from('<25I',first)[:12])
    try:
        spr=g.get(rel+'/'+nm).decode(errors='replace').splitlines();print('   ',spr[2][:90]);p=spr[2].split();tex=p[1].rsplit('.',1)[0].upper();d=g.get(f'{rel}/{tex}.G');fmt,w,h=struct.unpack_from('<IHH',d);mode='RGB' if fmt==0x18 else 'RGBA';im=Image.frombytes(mode,(w,h),d[8:8+w*h*len(mode)]).convert('RGBA');c=im.crop(tuple(map(int,p[6:10]))) if len(p)>9 else im
        print('    tex',tex,(w,h),'crop',c.size,'alpha max',c.getchannel('A').getextrema());c.thumbnail((68,100));sheet.alpha_composite(c,(x,4));x+=72
    except Exception as e:print('    no sprite file',repr(e)[:80])
sheet.save(Path(__file__).parent/'slots2.png')
sc=bga[slots[-1][0]+slots[-1][1]:];o=6+4+4;print(sc[:6],struct.unpack_from('<2I',sc,6))
print(sc[14:14+64].split(b'\0')[0],struct.unpack_from('<12I',sc,14+64))
