"""Review sheet: native bank 46 (reference) and RISE banks 47-51 (frame 0, receptors, outlines, explosion, icon)."""
from pathlib import Path
import struct
from PIL import Image,ImageDraw
HERE=Path(__file__).resolve().parent
REF=Path(r'E:\Pump It Up Data\PIU\noteskin_updates\20261013\assets\USER_INTERFACE\PLAY\SKIN\46\HD')
def g(p):
    d=Path(p).read_bytes();fmt,w,h=struct.unpack_from('<IHH',d);return Image.frombytes({0x18:'RGB',0x1020:'RGBA'}[fmt],(w,h),d[8:]).convert('RGBA')
rows=[('PHOENIX 46',REF,None)]+[(f'RISE {n} (bank {46+n})',HERE/f'payloads/USER_INTERFACE/PLAY/SKIN/{46+n}/HD',HERE/f'payloads/USER_INTERFACE/SELECT/COMMAND/COMMAND_ICON/HD/NS_RISE{n}_ON_0.G') for n in range(1,2)]
H=300;sheet=Image.new('RGBA',(480+480+480+170+90+40,H*len(rows)),(45,45,55,255));d=ImageDraw.Draw(sheet)
for i,(label,folder,icon) in enumerate(rows):
    y=i*H;d.text((4,y+2),label,fill=(255,255,0,255));x=4
    for name in ('0.G','BASE.G','6.G'):
        im=g(folder/name);sheet.alpha_composite(im,(x,y+14));x+=im.width+10
    fx=g(folder/'STEPFX00_2.G').resize((160,160));sheet.alpha_composite(fx,(x,y+14));x+=170
    if icon:sheet.alpha_composite(g(icon).resize((122,94)),(x,y+14))
sheet.save(HERE/'review_noteskins.png');print(sheet.size)
