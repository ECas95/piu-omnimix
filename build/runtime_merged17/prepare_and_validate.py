"""17-channel runtime (ANIME NSDE merged into ANIME PIU) + native catalog harness.

1. copy the installed v38 runtime sources and unlink channel 0x41 from the menu chain
2. build the native filter harness for 17 channels and run it, with the ORIGINAL engine,
   against final_v363/payloads/D/LIST (counts, exact A-Z order, 2P slots, menu order)
Host only: the game images are not mounted or written here.
"""
from pathlib import Path
import json,hashlib,subprocess,shutil,struct,re,ast,sys,unicodedata
HERE=Path(__file__).resolve().parent;FINAL=HERE.parent;E=Path(r'E:\Pump It Up Data\PIU')
SRC=E/'nsde_channel/additional_v38/runtime_candidate'
CACHE=Path(r'C:\Users\USER\.codex\workspaces\anime_channel_cache\native_build');BUILD=CACHE/'merged17_v363_filter'
OLDH=CACHE/'nsde_fractional41_filter'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def unix(p):return '/mnt/'+str(p)[0].lower()+str(p)[2:].replace('\\','/')
ALPHA=[0x35,0x36,0x37,0x38,0x3d,0x3e,0x3f,0x40,0x41,0x42,0x43,0x44,0x45,0x46,0x47,0x48,0x49,0x4a,0x4b,0x4c,0x4d,0x4e]   # harness-verified order (counts cover 0x35-0x48)
MENU=[0x44,0x45,0x46,0x2f,0x32,0x33,0x3e,0x34,0x47,0x48,0x49,0x4a,0x4b,0x4c,0x30,0x3d,0x3b,0x31,0x40,0x37,0x38,0x3f,0x35,0x36,0x42,0x43,0x4d,0x4e]   # v372: SABIN SOUND STAR (0x47) after DJMAX (0x34); v378: EZ2ON (0x48) after it

def sources():
    for kind in ('trial','cabinet'):
        dst=HERE/(kind+'_runtime_source');dst.mkdir(exist_ok=True)
        for p in (SRC/(kind+'_runtime_source')).iterdir():
            if p.is_file():shutil.copy2(p,dst/p.name)
        c=dst/'channels.c';s=c.read_text()
        old='{0x36, 0x41}, {0x41, 0x42}, {0x42, 0x43}};'
        assert s.count(old)==1,kind
        s=s.replace(old,'{0x36, 0x42}, {0x42, 0x43}};  /* v363: ANIME NSDE (0x41) merged into ANIME PIU (0x40); id retired, never reused */')
        # user 2026-10-24: every song of every added channel (0x2f-0x43) in alphabetical order
        cond='if(current_channel>=0x35 && current_channel<=0x38 || current_channel==0x3d || current_channel==0x3e || current_channel==0x3f || current_channel==0x40 || (current_channel>=0x41 && current_channel<=0x43)) {'
        assert s.count(cond)==1,kind
        s=s.replace(cond,'if(current_channel>=0x2f && current_channel<=0x48) {')
        # v368: PUMP IT UP PRO / PRO 2 / INFINITY = channels 0x44-0x46 (versions 0x2c-0x2e), menu right after PHOENIX
        # v372: SABIN SOUND STAR = channel 0x47 (version 0x2f), menu right after DJMAX (0x34); same table pattern
        for o,n in [('#define LAST_ID 0x43','#define LAST_ID 0x48'),
                    ('static uint32_t jump_table[LAST_ID + 1];','static const char *const eff_inf[5]={"EFF_CH65","EFF_CH66","EFF_CH67","EFF_CH68","EFF_CH69"};\nstatic uint32_t jump_table[LAST_ID + 1];'),
                    ('    memcpy(jump_table, jt, 48 * 4);','    const unsigned inf_visual_slots[5]={37,43,21,22,25}; /* MAIN_FULL_C: retired NSDE, unused WPF, empty slots */\n    for (unsigned i=0;i<5;i++) { unsigned slot=67+i; table[slot*5]=0x44+i; table[slot*5+1]=73+i; table[slot*5+2]=inf_visual_slots[i]; table[slot*5+3]=0x44+i; table[slot*5+4]=(uint32_t)(uintptr_t)eff_inf[i]; }\n    memcpy(jump_table, jt, 48 * 4);'),
                    ('{0x13, 0x2f}','{0x11, 0x44}, {0x44, 0x45}, {0x45, 0x46}, {0x13, 0x2f}'),   # user: PRO/PRO 2/INFINITY between FIESTA EX (0x11) and FIESTA 2 (0x12)
                    ('{0x34, 0x30}','{0x34, 0x47}, {0x47, 0x48}, {0x48, 0x30}')]:   # v378: EZ2ON REBOOT R (0x48, version 0x30) after SSS
            assert s.count(o)==1,(kind,o);s=s.replace(o,n)
        assert s.count('c < 21')==2 and '8192' in s,kind;s=s.replace('c < 21','c < 26')   # 26 filter stubs ~ 7210 of the 8192 reserved bytes
        c.write_text(s,newline='\n')
        p=dst/'channel_policy.h';s=p.read_text()
        for o,n in [('ids[21]','ids[26]'),('0x41, 0x42, 0x43};','0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48};'),('v <= 0x2b','v <= 0x30')]:
            assert s.count(o)==1,(kind,o);s=s.replace(o,n)
        p.write_text(s,newline='\n')
        sys.path.insert(0,str(HERE));import noteskin_rise_patch as NR   # v370: RISE noteskins (banks 47-51)
        p=dst/'noteskin.c';p.write_text(NR.patch(p.read_text()),newline='\n')
        p=dst/'wallpapers.c';s=p.read_text()   # Infinity loading wallpapers prime_29..38
        assert s.count('#define WALLPAPERS 28')==1;p.write_text(s.replace('#define WALLPAPERS 28','#define WALLPAPERS 38').replace('PHOENIX 22..28 (HD and SD).','PHOENIX 22..28, INFINITY 29..38 (HD and SD).'),newline='\n')

def order_key(title):   # same key as anime_final_v8/display_text_v19 (case/accents folded, punctuation ignored)
    s=unicodedata.normalize('NFKD',title.casefold());s=''.join(c for c in s if not unicodedata.combining(c))
    return ' '.join(''.join(c if c.isalnum() else ' ' for c in s).split())

def title_table(raw,pool):
    """Sort keys for EVERY catalog song (the runtime binary-searches by id)."""
    ns,_=struct.unpack_from('<II',raw);ids={}
    for i in range(ns):
        s=struct.unpack_from('<9I',raw,44+i*36)
        if s[1]!=0xffffffff and s[1]<len(pool):ids[s[0]]=order_key(pool[s[1]].decode('utf8','replace'))
    h='// v367: sort keys for every catalog song\nstatic const struct anime_title_key {uint32_t id;const char *key;} anime_title_keys[] = {\n'+''.join(' {0x%08Xu,%s},\n'%(i,json.dumps(k,ensure_ascii=True)) for i,k in sorted(ids.items()))+'};\n'
    for kind in ('trial','cabinet'):(HERE/(kind+'_runtime_source')/'anime_title_order.h').write_text(h,encoding='utf8',newline='\n')

def keys():
    text=(HERE/'cabinet_runtime_source/anime_title_order.h').read_text(encoding='utf8')
    out={}
    for m in re.finditer(r'\{0x([0-9A-Fa-f]+)u,("(?:[^"\\]|\\.)*")\}',text):
        lit=m.group(2)
        try:key=ast.literal_eval('b'+lit)
        except SyntaxError:key=ast.literal_eval(lit).encode('utf8')
        out[int(m.group(1),16)]=key
    return out

def expected(raw,pool):
    ns,nc=struct.unpack_from('<II',raw)
    songs=[struct.unpack_from('<9I',raw,44+i*36) for i in range(ns)]
    rows=[struct.unpack_from('<9I',raw,44+ns*36+i*36) for i in range(nc-1)]
    listed={c[0]>>16 for c in rows if c[1]!=0xffffffff and (c[0]>>16)==(c[0]&65535)}   # bit 21 is now the NEW tag, not a listing marker
    k=keys();by={}
    for o in sorted(listed):
        s=songs[o-1];ch=(s[5]&255)+24
        if 0x35<=ch<=0x4e:by.setdefault(ch,[]).append(o)
    lines=[]
    for ch in ALPHA:
        def sortkey(o):
            s=songs[o-1];return (k.get(s[0]) if s[0] in k else (pool[s[1]] if s[1]!=0xffffffff else b''),s[0])
        for o in sorted(by.get(ch,[]),key=sortkey):lines.append(f'{ch:x} {songs[o-1][0]:X}')
    counts=[len(by.get(ch,[])) for ch in range(0x35,0x4f)]
    return counts,'\n'.join(lines)+'\n',sum(1 for o in listed if 0x35<=(songs[o-1][5]&255)+24<=0x4e and songs[o-1][0] not in k)

def harness(counts):
    BUILD.mkdir(exist_ok=True)
    for p in (HERE/'cabinet_runtime_source').iterdir():
        if p.is_file():shutil.copy2(p,BUILD/p.name)
    shutil.copy2(OLDH/'test_channels.c',BUILD/'test_channels.c')
    t=(OLDH/'test_nsde.c').read_text()
    rep=[(re.search(r'int expected\[15\]=\{[0-9,]+\}',t).group(0),'int expected[15]={'+','.join(map(str,counts))+'}'),
         ('0x3f,0x35,0x36,0x41,0x42,0x43};','0x3f,0x35,0x36,0x42,0x43};'),
         ('custom==18 && anchor+18<total','custom==17 && anchor+17<total'),('j<18;j++','j<17;j++'),
         ('18 custom channels including NSDE','17 custom channels, NSDE merged into ANIME PIU'),
         # v368: + PUMP IT UP PRO / PRO 2 / INFINITY (0x44-0x46) after PHOENIX -> 20 custom channels
         ('int expected[15]=','int expected[18]='),('found[68]={0}','found[71]={0}'),('channel<=0x43;channel++){','channel<=0x46;channel++){'),
         ('(channel>=0x41 && channel<=0x43)','(channel>=0x41 && channel<=0x46)'),('assert(menu[i][0]<=0x43)','assert(menu[i][0]<=0x46)'),
         ('for(int i=0;i<15;i++)assert(found[0x35+i]','for(int i=0;i<18;i++)assert(found[0x35+i]'),
         ('custom==17 && anchor+17<total','custom==20 && anchor+17<total'),
         ('for(int j=0;j<17;j++)assert(menu[anchor+1+j][0]==wanted[j]); }','for(int j=0;j<17;j++)assert(menu[anchor+1+j][0]==wanted[j]); int fx=-1; for(int i=0;i<total;i++)if(menu[i][0]==0x11)fx=i; assert(fx>=0 && fx+4<total && menu[fx+1][0]==0x44 && menu[fx+2][0]==0x45 && menu[fx+3][0]==0x46 && menu[fx+4][0]==0x12); }'),
         ('for(int channel=0;channel<=0x43;channel++) {','for(int channel=0;channel<=0x46;channel++) {'),
         ('for(int channel=0;channel<=0x43;channel++)for','for(int channel=0;channel<=0x46;channel++)for'),
         # v372: + SABIN SOUND STAR (0x47) right after DJMAX (0x34) -> 21 custom channels, 18 after PRIME
         ('int expected[18]=','int expected[19]='),('found[71]={0}','found[72]={0}'),('channel<=0x46;channel++){','channel<=0x47;channel++){'),
         ('(channel>=0x41 && channel<=0x46)','(channel>=0x41 && channel<=0x47)'),('assert(menu[i][0]<=0x46)','assert(menu[i][0]<=0x47)'),
         ('for(int i=0;i<18;i++)assert(found[0x35+i]','for(int i=0;i<19;i++)assert(found[0x35+i]'),
         ('0x2f,0x32,0x33,0x3e,0x34,0x30,','0x2f,0x32,0x33,0x3e,0x34,0x47,0x30,'),
         ('custom==20 && anchor+17<total); for(int j=0;j<17;j++)','custom==21 && anchor+18<total); for(int j=0;j<18;j++)'),
         ('for(int channel=0;channel<=0x46;channel++) {','for(int channel=0;channel<=0x47;channel++) {'),
         ('for(int channel=0;channel<=0x46;channel++)for','for(int channel=0;channel<=0x47;channel++)for'),
         # v378: + EZ2ON REBOOT R (0x48) right after SABIN SOUND STAR -> 22 custom channels, 19 after PRIME
         ('int expected[19]=','int expected[20]='),('found[72]={0}','found[73]={0}'),('channel<=0x47;channel++){','channel<=0x48;channel++){'),
         ('(channel>=0x41 && channel<=0x47)','(channel>=0x41 && channel<=0x48)'),('assert(menu[i][0]<=0x47)','assert(menu[i][0]<=0x48)'),
         ('for(int i=0;i<19;i++)assert(found[0x35+i]','for(int i=0;i<20;i++)assert(found[0x35+i]'),
         ('0x2f,0x32,0x33,0x3e,0x34,0x47,0x30,','0x2f,0x32,0x33,0x3e,0x34,0x47,0x48,0x30,'),
         ('custom==21 && anchor+18<total); for(int j=0;j<18;j++)','custom==22 && anchor+19<total); for(int j=0;j<19;j++)'),
         ('for(int channel=0;channel<=0x47;channel++) {','for(int channel=0;channel<=0x48;channel++) {'),
         ('for(int channel=0;channel<=0x47;channel++)for','for(int channel=0;channel<=0x48;channel++)for'),
         # 2026-11: + BEATMANIA IIDX (0x49) right after EZ2ON -> 23 custom channels, 20 after PRIME
         ('int expected[20]=','int expected[21]='),('found[73]={0}','found[74]={0}'),('channel<=0x48;channel++){','channel<=0x49;channel++){'),
         ('(channel>=0x41 && channel<=0x48)','(channel>=0x41 && channel<=0x49)'),('assert(menu[i][0]<=0x48)','assert(menu[i][0]<=0x49)'),
         ('for(int i=0;i<20;i++)assert(found[0x35+i]','for(int i=0;i<21;i++)assert(found[0x35+i]'),
         ('0x2f,0x32,0x33,0x3e,0x34,0x47,0x48,0x30,','0x2f,0x32,0x33,0x3e,0x34,0x47,0x48,0x49,0x30,'),
         ('custom==22 && anchor+19<total); for(int j=0;j<19;j++)','custom==23 && anchor+20<total); for(int j=0;j<20;j++)'),
         ('for(int channel=0;channel<=0x48;channel++) {','for(int channel=0;channel<=0x49;channel++) {'),
         ('for(int channel=0;channel<=0x48;channel++)for','for(int channel=0;channel<=0x49;channel++)for'),
         # 2026-11: IIDX in four parts (0x4a-0x4c after 0x49), CINDERELLA GIRLS 0x4d and MAIN SELECTIONS 0x4e after PROJECT SEKAI -> 28 custom channels, 25 after PRIME
         ('int expected[21]=','int expected[26]='),('found[74]={0}','found[79]={0}'),('channel<=0x49;channel++){','channel<=0x4e;channel++){'),
         ('(channel>=0x41 && channel<=0x49)','(channel>=0x41 && channel<=0x4e)'),('assert(menu[i][0]<=0x49)','assert(menu[i][0]<=0x4e)'),
         ('for(int i=0;i<21;i++)assert(found[0x35+i]','for(int i=0;i<26;i++)assert(found[0x35+i]'),
         ('0x2f,0x32,0x33,0x3e,0x34,0x47,0x48,0x49,0x30,','0x2f,0x32,0x33,0x3e,0x34,0x47,0x48,0x49,0x4a,0x4b,0x4c,0x30,'),
         ('0x3f,0x35,0x36,0x42,0x43};','0x3f,0x35,0x36,0x42,0x43,0x4d,0x4e};'),
         ('custom==23 && anchor+20<total); for(int j=0;j<20;j++)','custom==28 && anchor+25<total); for(int j=0;j<25;j++)'),
         ('for(int channel=0;channel<=0x49;channel++) {','for(int channel=0;channel<=0x4e;channel++) {'),
         ('for(int channel=0;channel<=0x49;channel++)for','for(int channel=0;channel<=0x4e;channel++)for')]
    for o,n in rep:
        assert t.count(o)==1,o;t=t.replace(o,n)
    (BUILD/'test_nsde.c').write_text(t,newline='\n')

def main():
    sources()
    sys.path[:0]=[str(E),str(E/'nsde_channel')]
    from current_parent import load
    P,_=load()
    raw=(FINAL/'payloads/D/LIST').read_bytes();pool=P.B.string_entries_from((FINAL/'payloads/D/LIST.0').read_bytes())
    title_table(raw,pool)
    counts,order,unkeyed=expected(raw,pool)
    harness(counts)
    shutil.copy2(FINAL/'payloads/D/LIST',BUILD/'LIST');(BUILD/'expected_order.txt').write_text(order,newline='\n')
    engine=CACHE/'full_validation_engine';assert sha(engine)=='9abb6563927eeaae4fe5272446ab382f35a1b106312a972155278f46cc35e746'
    p=subprocess.run(['wsl','-d','Ubuntu','-u','root','--','gcc','-m32','-fPIE','-pie','-O2','-msse2','-I'+unix(BUILD),unix(BUILD/'test_nsde.c'),'-o',unix(BUILD/'test_nsde'),'-ldl','-lpthread','-lrt'],cwd=r'C:\Windows',capture_output=True,timeout=180)
    (HERE/'native_filter_compile.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0,(p.stdout+p.stderr)[-2000:]
    p=subprocess.run(['wsl','-d','Ubuntu','-u','root','--',unix(BUILD/'test_nsde'),unix(engine),unix(BUILD/'LIST'),unix(BUILD/'expected_order.txt')],cwd=r'C:\Windows',capture_output=True,timeout=300)
    (HERE/'native_filter.log').write_bytes(p.stdout+p.stderr)
    ok=p.returncode==0 and b'BASIC_ZERO_CUSTOM_FULL_EXCLUSIVE_ALL_STOCK_FILTERS_BOOT_PASS' in p.stdout
    # v370: RISE noteskins in the selectable noteskin menu, checked in the original engine (both players)
    import noteskin_rise_patch as NR
    (BUILD/'test_noteskins_rise.c').write_text(NR.TEST,newline='\n')
    q=subprocess.run(['wsl','-d','Ubuntu','-u','root','--','bash','-c',f"gcc -m32 -fPIE -pie -O2 -I'{unix(BUILD)}' -o '{unix(BUILD/'test_noteskins_rise')}' '{unix(BUILD/'test_noteskins_rise.c')}' && '{unix(BUILD/'test_noteskins_rise')}' '{unix(engine)}'"],cwd=r'C:\Windows',capture_output=True,timeout=300)
    (HERE/'noteskin_rise_test.log').write_bytes(q.stdout+q.stderr)
    skins_ok=q.returncode==0 and b'RISE_NOTESKINS_PASS' in q.stdout
    print('RISE_NOTESKIN_ENGINE_TEST','PASS' if skins_ok else 'FAIL',(q.stdout+q.stderr)[-300:].decode('utf8','replace'),flush=True)
    ok=ok and skins_ok
    (HERE/'native_filter_result.json').write_text(json.dumps(dict(pass_=ok,noteskins_rise_pass=skins_ok,returncode=p.returncode,catalog_sha256=sha(FINAL/'payloads/D/LIST'),channel_counts_0x35_0x43=counts,songs_without_title_key=unkeyed,menu=[hex(c) for c in MENU],tail=(p.stdout+p.stderr)[-1500:].decode('utf8','replace')),indent=1))
    print('MERGED17_NATIVE_FILTER','PASS' if ok else 'FAIL',counts,'unkeyed',unkeyed,flush=True)

if __name__=='__main__':main()
