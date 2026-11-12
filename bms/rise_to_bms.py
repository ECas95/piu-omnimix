"""PIU RISE Season 2 (NX charts, no keysounds) -> BMS package per song.
Reads D:\PIU_PRESERVADO\ORIGINALES\RISE\<id - title>\{Audio,BGA,Charts,Previews}; writes D:\PIU_PRESERVADO\BMS_RISE\<id - title>\
  <chart>.bms (S03 / HD12 ...), song.mp3 (tema.mp3 shifted so BMS time 0 = NX beat 0), bga.mp4 (same shift), banner.png (portada), preview.mp3.
Lanes: 5 panels -> 11-15; 6 (half double) -> 11-15 + 18. Holds = LN type 1. BPM changes ch08, stops ch09 (#STOP, 1/192 whole note)."""
from pathlib import Path
from math import gcd
from fractions import Fraction as F
import sys,json,csv,subprocess,shutil
sys.dont_write_bytecode=True
sys.path[:0]=[r'D:\PIU_PRESERVADO\repos\piu-chart-generator\lib']
import nx_ssc as N
from hybrid import nx20
SRC=Path(r'D:\PIU_PRESERVADO\ORIGINALES\RISE');OUT=Path(r'D:\PIU_PRESERVADO\BMS_RISE')
B36='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ';b36=lambda n:B36[n//36]+B36[n%36]
LANE={5:[11,12,13,14,15],6:[11,12,13,14,15,18]}
def row(slots,n):
    g=n
    for p in slots:g=gcd(g,p)
    n//=g;s=['00']*n
    for p,c in slots.items():s[p//g]=c
    return ''.join(s)
def load(data):
    try:return nx20.parse(data)
    except Exception:   # variant with gimmick params in the branch head (Tanaka): lossless reader, params (speed/warp) are not BMS-expressible
        sys.path.insert(0,str(Path(__file__).resolve().parent));import rise_nx,struct
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
            if not v or k in (0,0x5B,0x3B):continue
            if k in (0x23,0x37,0x3F):fake.setdefault(N.q(beat),set()).add(l);continue
            if k not in N.SYMBOL:bad+=1;continue
            rows.setdefault(N.q(beat),['0']*nx['cols'])[l]=N.SYMBOL[k]
    assert not bad,bad
    origin,bpms,stops=N.timing(nx);cols=nx['cols'];lane=LANE[cols]
    # hold heads/tails -> LN pairs
    ev={};lnset=set()
    for b,r in rows.items():
        for l,v in enumerate(r):
            if v=='1':ev[(b,l)]='tap'
            elif v=='2':ev[(b,l)]='head'
            elif v=='3':ev[(b,l)]='tail'
    last=int(max([b for b,_ in ev]+list(fake))//4) if (ev or fake) else 0
    bc={};
    for _,v in bpms:bc.setdefault(round(v,4),b36(len(bc)+1))
    sc={}
    for b,s in stops:sc[b]=s
    stopcode={};
    for b,s in stops:
        k=round(s*bpms[0][1]/60*48);stopcode.setdefault(k,b36(len(stopcode)+1))
    h=['*---------------------- HEADER FIELD','#PLAYER 1','#GENRE PUMP IT UP RISE','#TITLE '+title,'#SUBTITLE ['+name+']','#ARTIST '+artist,f'#BPM {round(bpms[0][1],4)}',f'#PLAYLEVEL {level}','#RANK 3','#LNTYPE 1','#STAGEFILE banner.png','#BANNER banner.png','#BMP01 bga.mp4','#WAV01 song.mp3','*source: PIU RISE Season 2 NX '+name+' (fake notes = invisible channels 31-39)']
    for v,c in bc.items():h.append(f'#BPM{c} {v}')
    for k,c in stopcode.items():h.append(f'#STOP{c} {k}')
    body=['','*---------------------- MAIN DATA FIELD']
    for m in range(last+1):
        if m==0:body+=['#00001:01','#00004:01']
        sl={};
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

def song(d,meta):
    out=OUT/d.name;mark=out/'done.json'
    if mark.exists():return json.loads(mark.read_text())
    out.mkdir(parents=True,exist_ok=True);res=dict(song=d.name,charts=[],errors=[]);origins=set()
    for f in sorted((d/'Charts').glob('*.nx')):
        name=f.stem.replace('_RISE','');lv=int(''.join(c for c in name if c.isdigit()))
        try:
            nx=load(f.read_bytes());txt,o,n=chart(nx,meta['titulo'],meta['artista'],name,lv)
            (out/f'{name}.bms').write_text(txt,encoding='utf8');origins.add(round(o,1));res['charts'].append(dict(chart=name,notes=n,origin_ms=o))
        except Exception as e:res['errors'].append(dict(chart=name,error=repr(e)[:200]))
    o=sorted(origins)[0] if origins else 0;res['origins']=sorted(origins);s=o/1000
    # shift audio/video so that BMS time 0 = NX beat 0
    af=f'adelay={int(round(s*1000))}:all=1' if s>0 else 'anull';ss=['-ss',str(-s)] if s<0 else []
    subprocess.run(['ffmpeg','-v','error','-y',*ss,'-i',str(d/'Audio'/'tema.mp3'),'-af',af,'-q:a','2',str(out/'song.mp3')],check=True)
    vf=f'tpad=start_duration={s}:color=black' if s>0 else 'null'
    subprocess.run(['ffmpeg','-v','error','-y',*ss,'-i',str(d/'BGA'/'bga.webm'),'-an','-vf',vf,'-c:v','libx264','-crf','23','-preset','fast','-pix_fmt','yuv420p',str(out/'bga.mp4')],check=True)
    for a,b in (('Previews/portada.png','banner.png'),('Previews/preview.mp3','preview.mp3')):
        if (d/a).exists():shutil.copy2(d/a,out/b)
    mark.write_text(json.dumps(res,indent=1));return res

if __name__=='__main__':
    OUT.mkdir(exist_ok=True)
    meta={r['carpeta']:r for r in csv.DictReader(open(SRC/'INDICE.csv',encoding='utf-8-sig'))}
    allr=[]
    for name,m in meta.items():
        r=song(SRC/name,m);allr.append(r);print('RISE_BMS',name,len(r['charts']),'charts',r['origins'],r['errors'][:1],flush=True)
    (OUT/'resumen.json').write_text(json.dumps(allr,indent=1));print('DONE',len(allr),sum(len(r['charts']) for r in allr),'charts',sum(len(r['errors']) for r in allr),'errors')
