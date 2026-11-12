"""DJMAX RESPECT (PS4) -> BMS package per song, every mode (4B/5B/6B/8B x NM/HD/MX/SC), keysounds, BGA and art.
Stage 'charts': .bytes charts (u32 ticks, 13-byte events) -> <K>B_<DIFF>.bms + raw_charts/ + media (bga.mp4, banner.png, song.mp3, gallery, preview, metadata.json)
Stage 'sounds': keysound AudioClips of the song's sound banks (kind 's') -> .ogg
Sources: pipeline_data (copied from E:\DJMPS4\GAME\pump_pipeline) and E:\DJMPS4\GAME\main\data\Media\StreamingAssets.
Lanes (tracks): 4B 3-6, 5B 3-7, 6B 3-8, 8B 3-8 + 10,11. BMS: 3-7 -> 11-15, 8 -> 18, 10 -> 16 (side L), 11 -> 19 (side R). Other tracks = BGM (ch01).
Usage: python -I djmax_to_bms.py charts|sounds [song ...]"""
from pathlib import Path
from math import gcd
import sys,json,re,os,shutil,struct,math,subprocess,collections,bisect
sys.dont_write_bytecode=True
PD=Path(r'D:\PIU_PRESERVADO\ORIGINALES\DJMAX_RESPECT\pipeline_data');OUT=Path(r'D:\PIU_PRESERVADO\BMS_DJMAX')
SA=Path(r'E:\DJMPS4\GAME\main\data\Media\StreamingAssets');CATALOG=Path(r'E:\DJMPS4\GAME\pump_pipeline\catalog_audio')
B36='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ';B62=B36+'abcdefghijklmnopqrstuvwxyz'
LANE={3:11,4:12,5:13,6:14,7:15,8:18,10:16,11:19}
PLAY={4:[3,4,5,6],5:[3,4,5,6,7],6:[3,4,5,6,7,8],8:[3,4,5,6,7,8,10,11]}
DIFF={'nm':2,'hd':3,'mx':4,'sc':5}
def row(slots,n):
    g=n
    for p in slots:g=gcd(g,p)
    n//=g;s=['00']*n
    for p,c in slots.items():s[p//g]=c
    return ''.join(s)

def parse(data,name=''):
    """respect_chart.parse + time-signature events (opcode 4)."""
    rd=lambda f,o:struct.unpack_from(f,data,o)
    sign,end=rd('<II',0);ins,tw,res,tempo,last,pt,et,unk=rd('<HHHfIfII',end);count=tw&255
    pos=8;sounds={}
    for _ in range(ins):
        sid,flag,text=rd('<HB64s',pos);pos+=67;sounds[sid]=text.split(b'\0')[0].decode('utf8')
    tracks=[];bpms={0:tempo};meters={}
    for i in range(count):
        pos+=2;text,bound,events=rd('<64sII',pos);pos+=72;notes=[]
        for _ in range(events):
            tick,code=rd('<IB',pos)
            if code==1:
                sid,vol,pan,attr,ln,pad=rd('<HBBBHB',pos+5);notes.append((tick,sid,ln))
            elif code==3:bpms[tick]=rd('<f',pos+5)[0]
            elif code==4:meters[tick]=data[pos+5:pos+13].hex()
            pos+=13
        tracks.append(notes)
    return dict(name=name,res=res,tempo=tempo,sounds=sounds,tracks=tracks,bpms=sorted(bpms.items()),meters=meters,end_tick=et)

def tick_seconds(bpms,tpb,tick):
    t=0.;start=0;bpm=bpms[0][1]
    for at,v in bpms[1:]:
        if at>tick:break
        t+=(at-start)*60/(bpm*tpb);start=at;bpm=v
    return t+(tick-start)*60/(bpm*tpb)
def seconds_tick(bpms,tpb,sec):
    lo,hi=0,int(sec*400)+192*8
    while hi-lo>1:
        mid=(lo+hi)//2
        if tick_seconds(bpms,tpb,mid)<=sec:lo=mid
        else:hi=mid
    return lo

def build(c,K,diff,meta,level,bga_s,real):
    tpm=c['res'];tpb=tpm/4;play=PLAY[K];sounds=c['sounds']
    big=len({s.lower() for s in sounds.values() if s})>1290;B=B62 if big else B36;code36=lambda n:B[n//len(B)]+B[n%len(B)]
    wavs={};cd={}
    def wav(sid):
        if sid in cd:return cd[sid]
        f=sounds.get(sid)
        if not f:return None
        f=real.get(Path(f).stem.lower(),Path(f).stem+'.wav')   # keysounds are always exported as <name>.wav
        if f not in wavs:wavs[f]=code36(len(wavs)+1)
        cd[sid]=wavs[f];return cd[sid]
    lanes={};bgm=collections.defaultdict(list);hold={};end=0
    for i,notes in enumerate(c['tracks']):
        ch=LANE.get(i) if i in play else None
        for tick,sid,ln in notes:
            w=wav(sid)
            if w is None:
                if i not in play:continue          # unresolved BGM event: silent anyway
                if 'blank.wav' not in wavs:wavs['blank.wav']=code36(len(wavs)+1)
                w=wavs['blank.wav']                # playable note without a keysound stays a (silent) note
            end=max(end,tick)
            if ch is None:bgm[(tick//tpm,tick%tpm)].append(w);continue
            lanes.setdefault(ch,{}).setdefault(tick,w)
            if ln>6:hold[(ch,tick)]=(tick+ln,w)
    ln={}
    for (ch,p),(e,w) in sorted(hold.items(),key=lambda x:x[0][1]):
        L=lanes[ch];last=ln.get(ch,[])
        if e in L or (last and p<last[-1]) or e<=p:continue
        ln.setdefault(ch,[]).extend([p,e]);L[e]=w
    lnset={ch:set(v) for ch,v in ln.items()}
    bpms=[x for x in c['bpms'] if x[0]<=end+tpm*4] or c['bpms'][:1]
    bga=None
    if bga_s is not None:
        k=seconds_tick(c['bpms'],tpb,max(bga_s,0.));bga=(k//tpm,k%tpm)
    last_m=max(end//tpm,bga[0] if bga else 0)
    bpmcode={}
    for _,b in bpms:bpmcode.setdefault(round(b,4),code36(len(bpmcode)+1))
    h=['*---------------------- HEADER FIELD','#PLAYER 1','#GENRE '+str(meta.get('genre','DJMAX RESPECT')),'#TITLE '+meta['title'],f'#SUBTITLE [{K}B {diff.upper()}]','#ARTIST '+meta['artist'],f'#BPM {round(bpms[0][1],4)}',f'#PLAYLEVEL {level}','#RANK 3',f'#DIFFICULTY {DIFF.get(diff,4)}','#LNTYPE 1']+(['#BASE 62'] if big else [])+['#STAGEFILE banner.png','#BANNER banner.png','#BACKBMP banner.png','#BMP01 bga.mp4','*source: DJMAX RESPECT '+c['name']]
    for f,w in wavs.items():h.append(f'#WAV{w} {f}')
    for b,w in bpmcode.items():h.append(f'#BPM{w} {b}')
    bym=collections.defaultdict(list)
    for (m,r),ws in sorted(bgm.items()):bym[m].append((r,ws))
    bpm_m=collections.defaultdict(dict)
    for p,b in bpms:
        if p>0:bpm_m[p//tpm][p%tpm]=bpmcode[round(b,4)]
    lane_m=collections.defaultdict(lambda:collections.defaultdict(dict))
    for ch,L in lanes.items():
        for p,w in L.items():lane_m[ch][p//tpm][p%tpm]=w
    body=['','*---------------------- MAIN DATA FIELD']
    for mi in range(last_m+1):
        if bga and bga[0]==mi:body.append(f'#{mi:03d}04:{row({bga[1]:"01"},tpm)}')
        if bpm_m.get(mi):body.append(f'#{mi:03d}08:{row(bpm_m[mi],tpm)}')
        lay=[]
        for r,ws in bym.get(mi,()):
            for k,w in enumerate(ws):
                while len(lay)<=k:lay.append({})
                lay[k][r]=w
        for layer in lay:body.append(f'#{mi:03d}01:{row(layer,tpm)}')
        for ch in sorted(lane_m):
            sl=lane_m[ch].get(mi)
            if not sl:continue
            lp=lnset.get(ch,set());a={p:w for p,w in sl.items() if mi*tpm+p not in lp};b={p:w for p,w in sl.items() if mi*tpm+p in lp}
            if a:body.append(f'#{mi:03d}{ch:02d}:{row(a,tpm)}')
            if b:body.append(f'#{mi:03d}{ch+40:02d}:{row(b,tpm)}')
    heads=sum(len(L) for L in lanes.values())-sum(len(v)//2 for v in ln.values())
    return '\n'.join(h+body)+'\n',dict(chart=c['name'],notes=heads,holds=sum(len(v)//2 for v in ln.values()),unresolved=sum(1 for t in c['tracks'] for _,sid,_ in t if sid and sid not in sounds),meters=len(c['meters']))

def link(a,b):
    if b.exists():return
    try:os.link(a,b)
    except OSError:shutil.copy2(a,b)

def load_all():
    inv=json.loads((PD/'inventory.json').read_text(encoding='utf8'));meta=json.loads((PD/'official_song_metadata.json').read_text(encoding='utf8'))
    lv={}
    for line in (PD/'respectdata.txt').read_text(encoding='cp932',errors='replace').splitlines():
        f=line.split('\t')
        if len(f)>=16:lv[f[0]]=[[int(x) for x in f[4+3*g:7+3*g]] for g in range(4)]
    return inv,meta,lv

def stage_charts(song,inv,meta,lv):
    out=OUT/song;mark=out/'charts_done.json'
    if mark.exists():return json.loads(mark.read_text())
    out.mkdir(parents=True,exist_ok=True);res=dict(song=song,charts=[],errors=[]);m=meta.get(song,{});title=m.get('title',song)
    md=dict(title=title,artist=m.get('artist',''),genre=m.get('genre','DJMAX RESPECT'))
    ks={f.stem.lower():f.name for f in out.glob('*.wav') if f.name!='preview.wav'}
    a=None
    try:a=json.loads((PD/'catalog_audio'/(song+'.json')).read_text(encoding='utf8'))
    except Exception:pass
    bga_s=a.get('bga_start_seconds') if a else None
    raw=out/'raw_charts';raw.mkdir(exist_ok=True)
    for f in sorted((PD/'charts'/song).glob('*.bytes')):
        shutil.copy2(f,raw/f.name);st=f.stem
        mm=re.match(r'^(.*)_(\d)b_(nm|hd|mx|sc)$',st)
        if not mm:continue
        K=int(mm.group(2));d=mm.group(3)
        try:
            c=parse(f.read_bytes(),st);gi={4:0,5:1,6:2,8:3}[K];lvl=(lv.get(song) or [[0]*3]*4)[gi][{'nm':0,'hd':1,'mx':2}.get(d,0)] if d!='sc' else 0
            if not lvl and K==5 and d!='sc':lvl=(m.get('five_key_levels') or {}).get(d.upper(),0)
            txt,info=build(c,K,d,md,lvl,bga_s,ks);(out/f'{K}B_{d.upper()}.bms').write_text(txt,encoding='utf8');res['charts'].append(info)
        except Exception as e:res['errors'].append(dict(chart=st,error=repr(e)[:200]))
    # media
    bn=m.get('bga_name',song);mv=next((Path(x['path']) for x in inv['movies'] if x['song']==bn),None)
    if mv and mv.exists() and not (out/'bga.mp4').exists():shutil.copy2(mv,out/'bga.mp4')
    if not (out/'blank.wav').exists():
        import wave
        with wave.open(str(out/'blank.wav'),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(44100);w.writeframes(bytes(4410))
    for src,dst in ((SA/'Eyecatch'/f'eyecatch_{song}.png','banner.png'),):
        if src.exists():shutil.copy2(src,out/dst)
    for p in sorted((SA/'Gallery').glob(f'Gallery_{song}_*.png')):(out/'gallery').mkdir(exist_ok=True);shutil.copy2(p,out/'gallery'/p.name)
    if not (out/'banner.png').exists():   # songs without an Eyecatch: first gallery image, else a BGA frame
        g=sorted((out/'gallery').glob('*.png'))
        if g:shutil.copy2(g[0],out/'banner.png')
        elif (out/'bga.mp4').exists():subprocess.run(['ffmpeg','-v','error','-y','-ss','20','-i',str(out/'bga.mp4'),'-frames:v','1',str(out/'banner.png')])
    p=SA/'Collection'/f'{song}.mp4'
    if p.exists():shutil.copy2(p,out/'collection.mp4')
    for ext in ('ogg','wav'):
        p=SA/'Preview'/f'{song}.{ext}'
        if p.exists():shutil.copy2(p,out/f'preview.{ext}')
    fl=CATALOG/f'{song}.flac'
    if fl.exists() and not (out/'song.mp3').exists():subprocess.run(['ffmpeg','-v','error','-y','-i',str(fl),'-q:a','2',str(out/'song.mp3')],check=True)
    (out/'metadata.json').write_text(json.dumps(dict(meta=m,levels=lv.get(song),audio_audit=a),ensure_ascii=False,indent=1),encoding='utf8')
    mark.write_text(json.dumps(res,indent=1));return res

def stage_sounds(song,inv):
    import UnityPy
    out=OUT/song;mark=out/'sounds_done.json'
    if mark.exists():return json.loads(mark.read_text())
    out.mkdir(parents=True,exist_ok=True);n=0;err=[]
    for f in out.glob('*.ogg'):f.unlink()   # earlier test exports
    banks=sorted((e for e in inv['bundles'] if e['song']==song and e['kind']=='s'),key=lambda e:(e['pack']!='base',e['path']))
    for e in banks:
        try:
            for o in UnityPy.load(e['path']).objects:
                if o.type.name!='AudioClip':continue
                a=o.read();t=out/(a.m_Name+'.wav')
                if t.exists():continue
                for _,raw in a.samples.items():
                    t.write_bytes(raw);n+=1;break   # the bundle's PCM exactly as stored (WAV)
        except Exception as x:err.append(repr(x)[:160])
    r=dict(song=song,clips=n,errors=err);mark.write_text(json.dumps(r));return r

if __name__=='__main__':
    stage=sys.argv[1];inv,meta,lv=load_all();OUT.mkdir(exist_ok=True)
    songs=sys.argv[2:] or sorted(meta)
    allr=[]
    for s in songs:
        try:r=stage_charts(s,inv,meta,lv) if stage=='charts' else stage_sounds(s,inv)
        except Exception as e:r=dict(song=s,errors=[repr(e)[:200]],charts=[])
        allr.append(r);print('DJMAX',stage,s,len(r.get('charts',[])),r.get('clips',''),r['errors'][:1],flush=True)
    print('DONE',len(allr))
