"""Typographic channel emblem (no official logo file on hand): replace D:/PIU_IIDX/ui/iidx.png with any art and re-run build_ui to change it."""
from PIL import Image,ImageDraw,ImageFont,ImageFilter,ImageChops
W,H=1200,520;F='C:/Windows/Fonts/'
im=Image.new('RGB',(W,H),(6,8,22));d=ImageDraw.Draw(im)
for y in range(H):d.line((0,y,W,y),fill=(8+int(20*y/H),8+int(10*y/H),30+int(70*y/H)))
for i in range(-H,W,70):d.line((i,0,i+H,H),fill=(30,34,80),width=2)
def text(t,font,y,fill,glow):
    m=Image.new('L',(W,H));ImageDraw.Draw(m).text((W/2,y),t,font=font,fill=255,anchor='mm')
    g=Image.new('RGB',(W,H),glow);im.paste(g,(0,0),m.filter(ImageFilter.GaussianBlur(14)));im.paste(g,(0,0),m.filter(ImageFilter.GaussianBlur(5)))
    grad=Image.new('RGB',(W,H));gd=ImageDraw.Draw(grad)
    for yy in range(H):
        k=(yy-(y-90))/180;k=max(0,min(1,k));gd.line((0,yy,W,yy),fill=tuple(int(a+(b-a)*k) for a,b in zip(fill[0],fill[1])))
    im.paste(grad,(0,0),m)
text('beatmania',ImageFont.truetype(F+'arialbi.ttf',118),150,((255,255,255),(170,215,255)),(0,120,255))
text('IIDX',ImageFont.truetype(F+'ariblk.ttf',235),335,((255,245,190),(255,110,40)),(255,70,0))
im.save('D:/PIU_IIDX/ui/iidx.png');print('ok')
