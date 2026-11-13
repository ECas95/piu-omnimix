"""PIU RISE (NX charts, no keysounds) -> BMS package per song: every RISE / ARCADE / mission chart.
Reads ORIGINALES\RISE\<id - title>\{Audio,BGA,Charts,Previews} (+ indice_canciones.csv); writes BMS_RISE\<id - title>\
  <chart>.bms (S08_RISE, HD14_RISE, S15_ARCADE, D17_ARCADE, mision_*), song.mp3 + bga.mp4 shifted so that BMS time 0 = NX beat 0, banner.png, preview.mp3.
NX beat 0 happens at audio time `origin` (head[3] of the first split), so the first `origin` ms of the audio/video are cut (origin < 0: padded).
Charts of one song with different origins get their own song_<ms>.mp3 / bga_<ms>.mp4.
Lanes: 5 panels -> 11-15; 6 (half double) -> 11-15 + 18; 10 (double) -> 1P 11-15 + 2P 21-25. Fake notes -> invisible channels. Holds = LN type 1."""
from pathlib import Path
from math import gcd
import sys,json,csv,subprocess,shutil,re
from concurrent.futures import ProcessPoolExecutor
sys.dont_write_bytecode=True
sys.path[:0]=[r'D:\PIU_PRESERVADO\repos\piu-chart-generator\lib',str(Path(__file__).resolve().parent)]
import nx_ssc as N
from hybrid import nx20
SRC=Path(r'D:\PIU_PRESERVADO\ORIGINALES\RISE');OUT=Path(r'D:\PIU_PRESERVADO\BMS_RISE')
B36='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ';b36=lambda n:B36[n//36]+B36[n%36]
LANE={5:[11,12,13,14,15],6:[11,12,13,14,15,18],10:[11,12,13,14,15,21,22,23,24,25]}
def row(slots,n):
    g=n
    for p in slots:g=gcd(g,p)
    n//=g;s=['00']*n
    for p,c in slots.items():s[p//g]=c
    return ''.join(s)
def load(data):
    try:return nx20.parse(data)
    except Exception:   # variant with gimmick params in the branch head: lossless reader (params such as speed/warp are not BMS-expressible)
        import rise_nx,struct
        r=rise_nx.parse(data);f32=lambda w:struct.unpack('<f',struct.pack('<I',w))[0];sp=[]
        for bl in r['blocks']:
            for br in bl['branches']:
                h=br['head'];rows=[None if (x[0]&255)==128 else tuple(x) for x in br['rows']]
                sp.append({'head':(0,0,1,f32(h[0]),f32(h[1]),f32(h[2]),f32(h[3]),f32(h[4]),h[5],h[6],len(rows)),'rows':rows})
        return {'cols':r['cols'],'splits':sp}
def chart(nx,title,artist,name,level):
    rows={};bad=0;fake={}
    for beat,ms,r in N.placed(nx):
        for l,v in enumerate(r):
            k=v&255
            if not v or k==0:continue
            # kind byte: low nibble = type (1/3 tap, 7 hold head, B hold body, F hold tail), bit 0x40 = real (judged) note, otherwise a fake;
            # the high bytes of the cell are mission/item markers that BMS cannot express
            nib=k&15
            if nib==0xB:continue
            sym={1:'1',3:'1',7:'2',0xF:'3'}.get(nib)
            if sym is None:bad+=1;continue
            if not k&0x40:fake.setdefault(N.q(beat),set()).add(l);continue
            rows.setdefault(N.q(beat),['0']*nx['cols'])[l]=sym
    assert not bad,bad
    origin,bpms,stops=N.timing(nx);cols=nx['cols'];lane=LANE[cols]
    ev={}
    for b,r in rows.items():
        for l,v in enumerate(r):
            if v=='1':ev[(b,l)]='tap'
            elif v=='2':ev[(b,l)]='head'
            elif v=='3':ev[(b,l)]='tail'
    last=int(max([b for b,_ in ev]+list(fake))//4) if (ev or fake) else 0
    bc={}
    for _,v in bpms:bc.setdefault(round(v,4),b36(len(bc)+1))
    stopcode={}
    for b,s in stops:
        k=round(s*bpms[0][1]/60*48);stopcode.setdefault(k,b36(len(stopcode)+1))
    h=['*---------------------- HEADER FIELD','#PLAYER '+('3' if cols==10 else '1'),'#GENRE PUMP IT UP RISE','#TITLE '+title,'#SUBTITLE ['+name+']','#ARTIST '+artist,f'#BPM {round(bpms[0][1],4)}',f'#PLAYLEVEL {level}','#RANK 3','#LNTYPE 1','#STAGEFILE banner.png','#BANNER banner.png','#BMP01 @BGA@','#WAV01 blank.wav','#WAV02 @SONG@','*source: PIU RISE NX '+name+' (fake notes = invisible channels 31-39)']
    for v,c in bc.items():h.append(f'#BPM{c} {v}')
    for k,c in stopcode.items():h.append(f'#STOP{c} {k}')
    body=['','*---------------------- MAIN DATA FIELD']
    for m in range(last+1):
        if m==0:body+=['#00001:02','#00004:01']   # wav 01 = silent placeholder used by every note, wav 02 = the song
        sl={}
        for b,v in bpms:
            if b>0 and int(b//4)==m:sl[int((b-4*m)*48)]=bc[round(v,4)]
        if sl:body.append(f'#{m:03d}08:{row(sl,192)}')
        sl={int((b-4*m)*48):stopcode[round(s*bpms[0][1]/60*48)] for b,s in stops if int(b//4)==m}
        if sl:body.append(f'#{m:03d}09:{row(sl,192)}')
        for l in range(cols):
            a={};t={}
            for (b,ll),k in ev.items():
                if ll!=l or int(b//4)!=m:continue
                p=int((b-4*m)*48)
                (t if k in('head','tail') else a)[p]='01'
            ch=lane[l]
            fk={int((b-4*m)*48):'01' for b,ls in fake.items() if l in ls and int(b//4)==m}
            if fk:body.append(f'#{m:03d}{ch+20:02d}:{row(fk,192)}')
            if a:body.append(f'#{m:03d}{ch:02d}:{row(a,192)}')
            if t:body.append(f'#{m:03d}{ch+40:02d}:{row(t,192)}')
    return '\n'.join(h+body)+'\n',origin,sum(1 for k in ev.values() if k!='tail')

def shifted(src_audio,src_video,out_audio,out_video,origin_ms):
    s=origin_ms/1000
    # beat 0 is at audio time `origin`: cut the first `origin` ms (negative origin: pad)
    a=['-ss',f'{s:.3f}'] if s>0 else []
    af=['-af',f'adelay={int(round(-origin_ms))}:all=1'] if s<0 else []
    if src_audio and not out_audio.exists():subprocess.run(['ffmpeg','-v','error','-y',*a,'-i',str(src_audio),*af,'-q:a','2',str(out_audio)],check=True)
    if src_video and not out_video.exists():
        vf=['-vf',f'tpad=start_duration={-s:.3f}:color=black'] if s<0 else []
        subprocess.run(['ffmpeg','-v','error','-y',*a,'-i',str(src_video),'-an',*vf,'-c:v','libx264','-crf','24','-preset','veryfast','-pix_fmt','yuv420p',str(out_video)],check=True)

def song(args):
    name,meta=args;d=SRC/name;out=OUT/name;mark=out/'done.json'
    if mark.exists():return json.loads(mark.read_text())
    out.mkdir(parents=True,exist_ok=True);res=dict(song=name,charts=[],errors=[],origins=[]);parsed=[]
    for f in sorted((d/'Charts').glob('*.nx')):
        stem=f.stem
        if stem.startswith('luces'):continue            # cabinet light maps, not charts
        m=re.match(r'^(?:S|HD|D)(\d+)_',stem);lv=int(m.group(1)) if m else 0
        try:
            nx=load(f.read_bytes());txt,o,n=chart(nx,meta['titulo'],meta['artista'],stem,lv);parsed.append((stem,txt,round(o,1),n))
        except Exception as e:res['errors'].append(dict(chart=stem,error=repr(e)[:200]))
    origins=sorted({p[2] for p in parsed});res['origins']=origins
    audio=d/'Audio'/'tema.mp3';video=d/'BGA'/'bga.webm'
    for i,o in enumerate(origins):
        sfx='' if i==0 else f'_{o:g}'
        try:shifted(audio if audio.exists() else None,video if video.exists() else None,out/f'song{sfx}.mp3',out/f'bga{sfx}.mp4',o)
        except Exception as e:res['errors'].append(dict(media=sfx or 'main',error=repr(e)[:200]))
    for stem,txt,o,n in parsed:
        sfx='' if o==origins[0] else f'_{o:g}'
        (out/f'{stem}.bms').write_text(txt.replace('@SONG@',f'song{sfx}.mp3').replace('@BGA@',f'bga{sfx}.mp4'),encoding='utf8')
        res['charts'].append(dict(chart=stem,notes=n,origin_ms=o))
    if not (out/'blank.wav').exists():
        import wave
        with wave.open(str(out/'blank.wav'),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(44100);w.writeframes(bytes(4410))
    for a,b in (('Previews/portada.png','banner.png'),('Previews/preview.mp3','preview.mp3')):
        if (d/a).exists():shutil.copy2(d/a,out/b)
    mark.write_text(json.dumps(res,indent=1));return res

if __name__=='__main__':
    OUT.mkdir(exist_ok=True)
    meta={r['carpeta']:r for r in csv.DictReader(open(SRC/'indice_canciones.csv',encoding='utf-8-sig'))}
    names=sys.argv[1:] or [n for n in meta if (SRC/n/'Charts').is_dir()]
    allr=[]
    with ProcessPoolExecutor(3) as ex:
        for r in ex.map(song,[(n,meta[n]) for n in names]):
            allr.append(r);print('RISE_BMS',r['song'],len(r['charts']),'charts',r['origins'],r['errors'][:1],flush=True)
    (OUT/'resumen.json').write_text(json.dumps(allr,indent=1));print('DONE',len(allr),sum(len(r['charts']) for r in allr),'charts',sum(len(r['errors']) for r in allr),'errors')
