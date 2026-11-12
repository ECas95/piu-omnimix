"""Five new channels in every place that lists channels: module sources, native harness, UI, catalog (songs that move), media rates. Refuses to run twice."""
from pathlib import Path
from PIL import Image
F=Path('D:/Pump It Up Data/PIU/final_v363');H=Path(__file__).resolve().parent;U=Path('D:/PIU_IIDX/ui')
def sub(p,pairs):
    s=p.read_bytes().decode('utf8')
    for o,n in pairs:
        assert s.count(o)==1,(p.name,o[:80],s.count(o));s=s.replace(o,n)
    p.write_bytes(s.encode('utf8'))
for kind in ('cabinet','trial'):
    d=F/f'runtime_merged17/{kind}_runtime_source'
    sub(d/'channels.c',[
    ('#define LAST_ID 0x49','#define LAST_ID 0x4e'),
    ('static const char *const eff_inf[6]={"EFF_CH65","EFF_CH66","EFF_CH67","EFF_CH68","EFF_CH69","EFF_CH70"};','static const char *const eff_inf[11]={"EFF_CH65","EFF_CH66","EFF_CH67","EFF_CH68","EFF_CH69","EFF_CH70","EFF_CH71","EFF_CH72","EFF_CH73","EFF_CH74","EFF_CH75"};'),
    ('{0x48, 0x49}, {0x49, 0x30}','{0x48, 0x49}, {0x49, 0x4a}, {0x4a, 0x4b}, {0x4b, 0x4c}, {0x4c, 0x30}'),
    ('{0x42, 0x43}};','{0x42, 0x43}, {0x43, 0x4d}, {0x4d, 0x4e}};'),
    ('if(current_channel>=0x2f && current_channel<=0x49) {','if(current_channel>=0x2f && current_channel<=LAST_ID) {'),
    ('code = mmap(NULL, 8192,','code = mmap(NULL, 16384,'),
    ('const unsigned inf_visual_slots[6]={37,43,21,22,25,16}; /* MAIN_FULL_C: retired NSDE, unused WPF, empty slots */','const unsigned inf_visual_slots[11]={37,43,21,22,25,16,78,88,97,98,99}; /* MAIN_FULL_C: retired NSDE, unused WPF, empty slots; 78/88 hidden stock channels, 97-99 digit sprites no selector code reads */'),
    ('for (unsigned i=0;i<6;i++) { unsigned slot=67+i;','for (unsigned i=0;i<11;i++) { unsigned slot=67+i;'),
    ])
    s=(d/'channels.c').read_bytes().decode('utf8');assert s.count('c < 27')==2;(d/'channels.c').write_bytes(s.replace('c < 27','c < 32').encode('utf8'))
    sub(d/'channel_policy.h',[('static const unsigned ids[27] = {','static const unsigned ids[32] = {'),('0x47, 0x48, 0x49};','0x47, 0x48, 0x49, 0x4a, 0x4b, 0x4c, 0x4d, 0x4e};'),('v <= 0x31 ?','v <= 0x36 ?')])
sub(F/'runtime_merged17/prepare_and_validate.py',[
("ALPHA=[0x35,0x36,0x37,0x38,0x3d,0x3e,0x3f,0x40,0x41,0x42,0x43,0x44,0x45,0x46,0x47,0x48,0x49]","ALPHA=[0x35,0x36,0x37,0x38,0x3d,0x3e,0x3f,0x40,0x41,0x42,0x43,0x44,0x45,0x46,0x47,0x48,0x49,0x4a,0x4b,0x4c,0x4d,0x4e]"),
("MENU=[0x44,0x45,0x46,0x2f,0x32,0x33,0x3e,0x34,0x47,0x48,0x49,0x30,0x3d,0x3b,0x31,0x40,0x37,0x38,0x3f,0x35,0x36,0x42,0x43]","MENU=[0x44,0x45,0x46,0x2f,0x32,0x33,0x3e,0x34,0x47,0x48,0x49,0x4a,0x4b,0x4c,0x30,0x3d,0x3b,0x31,0x40,0x37,0x38,0x3f,0x35,0x36,0x42,0x43,0x4d,0x4e]"),
("if 0x35<=ch<=0x49:by.setdefault(ch,[]).append(o)","if 0x35<=ch<=0x4e:by.setdefault(ch,[]).append(o)"),
("for ch in range(0x35,0x4a)]","for ch in range(0x35,0x4f)]"),
("if 0x35<=(songs[o-1][5]&255)+24<=0x49 and","if 0x35<=(songs[o-1][5]&255)+24<=0x4e and"),
("""         ('for(int channel=0;channel<=0x48;channel++)for','for(int channel=0;channel<=0x49;channel++)for')]""","""         ('for(int channel=0;channel<=0x48;channel++)for','for(int channel=0;channel<=0x49;channel++)for'),
         # 2026-11: IIDX in four parts (0x4a-0x4c after 0x49), CINDERELLA GIRLS 0x4d and MAIN SELECTIONS 0x4e after PROJECT SEKAI -> 28 custom channels, 25 after PRIME
         ('int expected[21]=','int expected[26]='),('found[74]={0}','found[79]={0}'),('channel<=0x49;channel++){','channel<=0x4e;channel++){'),
         ('(channel>=0x41 && channel<=0x49)','(channel>=0x41 && channel<=0x4e)'),('assert(menu[i][0]<=0x49)','assert(menu[i][0]<=0x4e)'),
         ('for(int i=0;i<21;i++)assert(found[0x35+i]','for(int i=0;i<26;i++)assert(found[0x35+i]'),
         ('0x2f,0x32,0x33,0x3e,0x34,0x47,0x48,0x49,0x30,','0x2f,0x32,0x33,0x3e,0x34,0x47,0x48,0x49,0x4a,0x4b,0x4c,0x30,'),
         ('0x3f,0x35,0x36,0x42,0x43};','0x3f,0x35,0x36,0x42,0x43,0x4d,0x4e};'),
         ('custom==23 && anchor+20<total); for(int j=0;j<20;j++)','custom==28 && anchor+25<total); for(int j=0;j<25;j++)'),
         ('for(int channel=0;channel<=0x49;channel++) {','for(int channel=0;channel<=0x4e;channel++) {'),
         ('for(int channel=0;channel<=0x49;channel++)for','for(int channel=0;channel<=0x4e;channel++)for')]"""),
])
# hexagon art: the user's images have a black margin around the frame
for src,dst in (('IIDX PARTE 1','part1'),('IIDX PARTE 2','part2'),('IIDX PARTE 3','part3'),('IIDX PARTE 4','part4'),('IMASTER CINDERELLA GIRLS','imas'),('MAIN SEL','mainsel')):
    im=Image.open(Path('D:/PIU_IIDX')/(src+'.png')).convert('RGB');box=im.convert('L').point(lambda v:255 if v>40 else 0).getbbox();im.crop(box).save(U/(dst+'.png'));print(dst,box)
sub(F/'infinity/build_ui.py',[
("""          (0x49,'BEATMANIA IIDX','BEATMANIA IIDX',r'D:\\PIU_IIDX\\ui\\banner_infinitas.png',16,(r'D:\\PIU_IIDX\\canal\\songs\\31000\\preview.wav',0),'73_BEATMANIA_IIDX.WAV')]""",
"""          (0x49,'BEATMANIA IIDX 1','BEATMANIA IIDX 1',r'D:\\PIU_IIDX\\ui\\part1.png',16,(r'D:\\PIU_IIDX\\canal\\songs\\31000\\preview.wav',0),'73_BEATMANIA_IIDX.WAV'),
          # 2026-11: IIDX in four parts, CINDERELLA GIRLS and MAIN SELECTIONS. Hexagon slots: 78 and 88 belong to stock channels the menu never shows; 97-99 held digit sprites no selector code reads
          (0x4a,'BEATMANIA IIDX 2','BEATMANIA IIDX 2',r'D:\\PIU_IIDX\\ui\\part2.png',78,(r'D:\\PIU_IIDX\\canal\\songs\\31000\\preview.wav',0),'74_BEATMANIA_IIDX_2.WAV'),
          (0x4b,'BEATMANIA IIDX 3','BEATMANIA IIDX 3',r'D:\\PIU_IIDX\\ui\\part3.png',88,(r'D:\\PIU_IIDX\\canal\\songs\\31000\\preview.wav',0),'75_BEATMANIA_IIDX_3.WAV'),
          (0x4c,'BEATMANIA IIDX 4','BEATMANIA IIDX 4',r'D:\\PIU_IIDX\\ui\\part4.png',97,(r'D:\\PIU_IIDX\\canal\\songs\\31000\\preview.wav',0),'76_BEATMANIA_IIDX_4.WAV'),
          (0x4d,'CINDERELLA GIRLS','CINDERELLA GIRLS',r'D:\\PIU_IIDX\\ui\\imas.png',98,(r'D:\\PIU_NUEVAS\\songs\\0f124c7d77e7\\audio.wav',54),'77_CINDERELLA_GIRLS.WAV'),
          (0x4e,'MAIN SELECTIONS','MAIN SELECTIONS',r'D:\\PIU_IIDX\\ui\\mainsel.png',99,(r'D:\\IIDX\\NEW\\SEL\\BLUE ZONE\\Song.mp3',40),'78_MAIN_SELECTIONS.WAV')]"""),
("DIRECT={0x48,0x49}","DIRECT={0x48,0x49,0x4a,0x4b,0x4c,0x4d,0x4e}"),
("""            if not spr:   # one sprite name per empty slot""","""            if spr.startswith('FC_BOX_'):   # the slot keeps its layout under a name of its own
                spr=f'MC_CH{cid:X}.SPR';bga=bga[:offset]+spr.lower().encode().ljust(64,b'\\0')+bga[offset+64:];emit(rel+'/.BGA',bga)
            if not spr:   # one sprite name per empty slot"""),
])
sub(F/'build_catalog.py',[("""    import basic_original   # user 2026-11-06: Basic Mode exactly as the original PRIME
""","""    # user 2026-11-06: the mod's own copies of the CINDERELLA GIRLS pack songs move to that channel (0x4d)
    moved=set(json.loads((OUT/'cinderella_moved.json').read_text()));assert all(any(f'{s[0]:08X}'==g for s in songs) for g in moved)
    for s in songs:
        if f'{s[0]:08X}' in moved:s[5]=(s[5]&~255)|(0x4d-24)
    import basic_original   # user 2026-11-06: Basic Mode exactly as the original PRIME
""")])
(F/'cinderella_moved.json').write_text((H/'mover_imas.json').read_text())
sub(Path('D:/PIU_INFINITY/channels/prepare_media.py'),[("RATES={'EZ2ON':('3500k','1000k'),'IIDX':('2600k','600k')}","RATES={'EZ2ON':('3500k','1000k'),'IIDX':('2600k','600k'),'IMAS':('2600k','600k'),'MAINSEL':('2600k','600k'),'LL':('2600k','600k')}"),
 ("    if s['channel']!='IIDX':   # IIDX ships HD only","    if s['channel'] not in HD_ONLY:   # IIDX ships HD only"),
 ("[:1 if s['channel']=='IIDX' else 2]:","[:1 if s['channel'] in HD_ONLY else 2]:"),
 ("OUT=R/'media';LOGS=R/'logs/media'","HD_ONLY={'IIDX','IMAS','MAINSEL','LL'}\nOUT=R/'media';LOGS=R/'logs/media'")])
print('APLICADO')
