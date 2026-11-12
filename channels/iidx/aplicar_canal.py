"""Wires channel 0x49 BEATMANIA IIDX into the sources (same pattern as 0x48 EZ2ON), crop + no-SD in prepare_media, and the sss_charts fix. Backups *.before_iidx. Idempotent."""
from pathlib import Path
import shutil
F=Path('D:/Pump It Up Data/PIU/final_v363');R=F/'runtime_merged17'
def edit(p,rep):
    p=Path(p);b=p.with_name(p.name+'.before_iidx')
    if not b.exists():shutil.copy2(p,b)
    s=p.read_text(encoding='utf8',newline='') if False else p.read_bytes().decode('utf8')
    for o,n,*c in rep:
        if n in s and o not in s:continue
        k=c[0] if c else 1;assert s.count(o)==k,(p.name,o[:60],s.count(o));s=s.replace(o,n)
    p.write_bytes(s.encode('utf8'));print('OK',p.name)
for kind in ('trial','cabinet'):
    d=R/f'{kind}_runtime_source'
    edit(d/'channels.c',[('#define LAST_ID 0x48','#define LAST_ID 0x49'),('current_channel<=0x48)','current_channel<=0x49)'),
        ('eff_inf[5]={"EFF_CH65","EFF_CH66","EFF_CH67","EFF_CH68","EFF_CH69"}','eff_inf[6]={"EFF_CH65","EFF_CH66","EFF_CH67","EFF_CH68","EFF_CH69","EFF_CH70"}'),
        ('inf_visual_slots[5]={37,43,21,22,25};','inf_visual_slots[6]={37,43,21,22,25,16};'),('for (unsigned i=0;i<5;i++) { unsigned slot=67+i;','for (unsigned i=0;i<6;i++) { unsigned slot=67+i;'),
        ('{0x48, 0x30}','{0x48, 0x49}, {0x49, 0x30}'),('c < 26','c < 27',2)])
    edit(d/'channel_policy.h',[('ids[26]','ids[27]'),('0x47, 0x48};','0x47, 0x48, 0x49};'),('v <= 0x30','v <= 0x31')])
edit(R/'prepare_and_validate.py',[("0x45,0x46,0x47,0x48]   # harness","0x45,0x46,0x47,0x48,0x49]   # harness"),("0x34,0x47,0x48,0x30,0x3d","0x34,0x47,0x48,0x49,0x30,0x3d"),
    ("if 0x35<=ch<=0x48:","if 0x35<=ch<=0x49:"),("<=(songs[o-1][5]&255)+24<=0x48 and","<=(songs[o-1][5]&255)+24<=0x49 and"),
    ("         ('for(int channel=0;channel<=0x47;channel++)for','for(int channel=0;channel<=0x48;channel++)for')]",
     "         ('for(int channel=0;channel<=0x47;channel++)for','for(int channel=0;channel<=0x48;channel++)for'),\n"
     "         # 2026-11: + BEATMANIA IIDX (0x49) right after EZ2ON -> 23 custom channels, 20 after PRIME\n"
     "         ('int expected[20]=','int expected[21]='),('found[73]={0}','found[74]={0}'),('channel<=0x48;channel++){','channel<=0x49;channel++){'),\n"
     "         ('(channel>=0x41 && channel<=0x48)','(channel>=0x41 && channel<=0x49)'),('assert(menu[i][0]<=0x48)','assert(menu[i][0]<=0x49)'),\n"
     "         ('for(int i=0;i<20;i++)assert(found[0x35+i]','for(int i=0;i<21;i++)assert(found[0x35+i]'),\n"
     "         ('0x2f,0x32,0x33,0x3e,0x34,0x47,0x48,0x30,','0x2f,0x32,0x33,0x3e,0x34,0x47,0x48,0x49,0x30,'),\n"
     "         ('custom==22 && anchor+19<total); for(int j=0;j<19;j++)','custom==23 && anchor+20<total); for(int j=0;j<20;j++)'),\n"
     "         ('for(int channel=0;channel<=0x48;channel++) {','for(int channel=0;channel<=0x49;channel++) {'),\n"
     "         ('for(int channel=0;channel<=0x48;channel++)for','for(int channel=0;channel<=0x49;channel++)for')]")])
edit(F/'infinity/build_ui.py',[("'72_EZ2ON_REBOOT_R.WAV')]","'72_EZ2ON_REBOOT_R.WAV'),\n          # 2026-11: BEATMANIA IIDX, hexagon slot 16 (the only empty one)\n          (0x49,'BEATMANIA IIDX','BEATMANIA IIDX',r'D:\\PIU_IIDX\\ui\\iidx.png',16,(r'D:\\PIU_IIDX\\canal\\songs\\31000\\preview.wav',0),'73_BEATMANIA_IIDX.WAV')]"),
    ("CORE={0x47:(.14,.1,.9,.9)}","CORE={0x47:(.14,.1,.9,.9),0x49:(0,0,1,1)}")])
M=Path('D:/PIU_INFINITY/channels/prepare_media.py')
edit(M,[("RATES={'EZ2ON':('3500k','1000k')}","RATES={'EZ2ON':('3500k','1000k'),'IIDX':('2600k','600k')}   # IIDX: PRIME's own HD rate, 1356 songs"),
    ("fps=30,scale=1280:720,setsar=1,format=yuv420p,trim=start=","fps=30,{crop}scale=1280:720,setsar=1,format=yuv420p,trim=start="),
    ("    sd=dest/'V/SD/.V';sd.parent.mkdir(parents=True,exist_ok=True)\n","    sd=dest/'V/SD/.V';sd.parent.mkdir(parents=True,exist_ok=True)\n    if s['channel']!='IIDX':   # IIDX ships HD only: its SD would never be packed\n     ff_sd=1\n")])
s=M.read_bytes().decode('utf8')
# f-string segment: define crop; IIDX skips the SD movies
a="    for i,g in enumerate(segs,1):\n"
if "crop=" not in s[:s.index(a)+60]:s=s.replace(a,"    crop='crop=iw:iw*9/16,' if s.get('crop_16_9') else ''   # user 2026-11: 4:3 movies cut top and bottom to 16:9\n"+a,1)
a="     ff_sd=1\n    ff(['-threads','2','-i',str(hd),'-vf','fps=30,scale=640:480"
if a in s:
    i=s.index(a);j=s.index("    # preview movies",i);block=s[i+len("     ff_sd=1\n"):j]
    s=s[:i]+''.join('     '+l.lstrip() if False else ' '+l for l in block.splitlines(True))+s[j:]
s=s.replace("    for q,w,h in (('HD',464,264),('SD',312,176)):\n","    for q,w,h in (('HD',464,264),('SD',312,176))[:1 if s['channel']=='IIDX' else 2]:\n")
M.write_bytes(s.encode('utf8'));print('prepare_media ok')
edit('D:/SSS/sss_charts.py',[("key=lambda x:min(abs(x[0]-t) for t in taken),default=(None,None))","key=lambda x:min(abs(x[0]-t) for t in taken),default=(None,(None,None)))")])
