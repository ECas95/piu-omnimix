"""PRO 1 / PRO 2 / INFINITY: original Single / Double / Half-Double charts -> PRIME NX (exact notes, panels, times).

Same converters as the NSDE import (nsde_channel/prepare_native_charts.py): plain charts use
nx_adapter.native_nx; warps / speeds / scrolls use the native critical converters; Half-Double
is played on the 6 centre panels of a Double chart (source lane i -> double lane i+2).
Run with python -B (nothing is written on E:). Output: channels/charts/<song key>/<file>.NX + receipt.
"""
from pathlib import Path
import sys,json,hashlib,subprocess,re,traceback
E=Path(r'E:\Pump It Up Data\PIU');R=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.path[:0]=[str(E/'anime_channel_dng'),str(E/'anime_channel')]
import nx_adapter as A
import simfile as SM
import native_pause_seconds as NPS
import native_pause_critical as NPC
import native_warp_critical as NWC
MODES={'pump-single':'S','pump-double':'D','pump-halfdouble':'HD'}
import os   # v369: the user's PRO/PRO 2/INFINITY pack is converted from its own selection/source folders
SEL=os.environ.get('INF_SEL','selection_raw.json');SRC=os.environ.get('INF_SRC','src');CHARTS=os.environ.get('INF_CHARTS','charts');REPORT=os.environ.get('INF_REPORT','charts_report.json')

def seconds_of(audio):
    p=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','json',str(audio)],capture_output=True,timeout=90)
    return float(json.loads(p.stdout)['format']['duration'])

def convert(c,seconds):
    hd=c['mode']=='pump-halfdouble'
    timing=c['timing'];clock=SM.Clock(timing)
    plain=not hd and not clock.warps and all(v==1 for f in ('SCROLLS','SPEEDS') for _,v in SM.pairs(timing.get(f,'')))
    if plain:
        try:return A.native_nx(c,seconds)
        except ValueError as e:
            if 'Overlapping native timing splits' not in str(e):raise   # stops/delays the simple adapter cannot place
    ramps=[p.strip().split('=') for p in timing.get('SPEEDS','').split(',') if p.strip()]
    second=any(len(p)>3 and int(p[3])==1 and float(p[2])>0 for p in ramps)
    conv=NWC if clock.warps else NPS if second else NPC
    chart=dict(c,mode='pump-double',rows=[[b,'00'+row+'00'] for b,row in c['rows']]) if hd else c
    raw,proof=conv.convert(chart,seconds)
    proof['converter']=conv.__name__
    if hd:proof.update(halfdouble_physical_lane_mapping='source lane i -> double lane i+2',halfdouble_original_mode=c['mode'])
    return raw,proof

def main():
    sel=json.loads((R/SEL).read_text(encoding='utf8'))
    only=set(sys.argv[1:])
    ok=fail=0;report=[]
    for s in sel:
        key=s['group']+'/'+s['folder']
        if only and s['folder'] not in only:continue
        try:song(s,key,report)
        except Exception as e:report.append(dict(song=key,ok=False,mode='song',error='song: '+repr(e)[:300]))
    ok=sum(1 for r in report if r['ok']);fail=len(report)-ok
    (R/(REPORT if not only else 'charts_report_partial.json')).write_text(json.dumps(report,ensure_ascii=False,indent=1),encoding='utf8')
    print('CHARTS_CONVERTED',ok,'FAILED',fail,flush=True)

def song(s,key,report):
        special=[]
        src=R/SRC/s['group']/s['folder'];ssc=src/Path(s['file']).name
        out=R/CHARTS/s['group']/s['folder'];out.mkdir(parents=True,exist_ok=True)
        text=ssc.read_bytes().decode('utf-8-sig',errors='replace')
        if ssc.suffix.lower()=='.ssc':   # keep only Single / Double / Half-Double blocks (user 2026-10-25: no Routine / Co-op / lights)
            head,*blocks=re.split(r'(?=#NOTEDATA:)',text)
            keep=[];special=[]
            for b in blocks:
                b=re.sub(r'^(#[A-Z]+:[^;\r\n]*)(\r?\n)(?=#)',lambda x:x.group(1)+';'+x.group(2),b,flags=re.M)   # tag line missing its ';'
                m=re.search(r'#STEPSTYPE:([^;]*);',b)
                if not m or m.group(1).strip().lower() not in MODES:continue
                notes=re.search(r'#NOTES:([^;]*);',b,re.S)
                if notes and '{' in notes.group(1):   # StepF2 annotated note '{1...}': the base note stays, other items are not steps
                    b=b.replace(notes.group(1),re.sub(r'\{([^}]*)\}',lambda x:x.group(1)[:1] if x.group(1)[:1] in '1234MF' else '0',notes.group(1)),1)
                    notes=re.search(r'#NOTES:([^;]*);',b,re.S)
                rows=[l.strip() for l in re.sub(r'//[^\n]*','',notes.group(1) if notes else '').splitlines() if l.strip() and l.strip()!=',']
                if {len(r) for r in rows}-{len(r) for r in rows if len(r) in ({5:{5},10:{10},6:{6,10}}[{'pump-single':5,'pump-double':10,'pump-halfdouble':6}[m.group(1).strip().lower()]])}:
                    report.append(dict(song=s['group']+'/'+s['folder'],ok=False,mode=m.group(1).strip().lower(),name=None,level=None,error='malformed note rows (width) in source chart'));continue
                widths={len(l.strip()) for l in re.sub(r'//[^\n]*','',notes.group(1) if notes else '').splitlines() if l.strip() and l.strip()!=','}
                if m.group(1).strip().lower()=='pump-halfdouble' and widths=={10}:
                    # Half-Double already written on 10 columns: must use only the 6 centre panels
                    rows=[l.strip() for l in notes.group(1).splitlines() if len(l.strip())==10]
                    assert all(r[:2]=='00' and r[8:]=='00' for r in rows),'10-wide Half-Double uses outer panels'
                    b=b.replace(m.group(0),'#STEPSTYPE:pump-double;').replace('#DESCRIPTION:','#DESCRIPTION:HD10|',1)
                if notes:   # PRIME has no mines / fakes / rolls: mines and fakes are dropped (never judged), a roll is held as a hold
                    body=notes.group(1)
                    fake_mod=len(re.findall(r'[0-9A-Z]\*F',body));items=len(re.findall(r'[A-EG-KN-Z]',re.sub(r'\*[A-Z]','',body)))
                    clean=re.sub(r'[0-9A-Z]\*F','0',body)              # Infinity '1*F' / 'M*F' = fake note
                    clean=re.sub(r'([0-9A-Z])[*][A-Z]',lambda m:m.group(1),clean)   # other attribute (e.g. '1*B'): the plain note stays
                    clean=re.sub(r'[A-EG-KN-Z]','0',clean)             # Infinity special items (S, E, I...): not steps
                    special.append(dict(chart_block=len(keep),mines_removed=clean.count('M'),fakes_removed=clean.count('F')+fake_mod,special_items_removed=items,rolls_as_holds=clean.count('4')))
                    clean=re.sub(r'[MF]','0',clean).replace('4','2')
                    b=b.replace(body,clean,1)
                keep.append(b)
            text=head+''.join(keep)
        tags,charts=SM.parse(text.encode('utf-8'),extension=ssc.suffix.lower())
        file_sha=hashlib.sha256(ssc.read_bytes()).hexdigest()
        for c in charts:
            c['source_file_sha256']=file_sha
            if c['description'].startswith('HD10|'):c.update(description=c['description'][5:],hd_wide=True)
        music=next((p for p in src.iterdir() if p.name.lower()==tags.get('MUSIC','').lower()),None) or (lambda a:a[0] if len(a)==1 else None)([p for p in src.iterdir() if p.suffix.lower() in ('.ogg','.mp3','.wav')])
        seconds=seconds_of(music) if music else float(tags.get('MUSICLENGTH') or 0)
        used=set()
        for i,c in enumerate(charts):
            if c['mode'] not in MODES:continue
            try:level=int(float(c['meter']))
            except ValueError:level=0
            name=f"{'HD' if c.get('hd_wide') else MODES[c['mode']]}{level:02d}"
            while name in used:name+='B'
            used.add(name);rec=dict(special=special[i] if 'special' in dir() and i<len(special) else None,song=key,chart_index=i,mode='pump-halfdouble' if c.get('hd_wide') else c['mode'],level=level,description=c['description'],difficulty=c['difficulty'],name=name)
            try:
                raw,proof=convert(c,seconds)
                (out/(name+'.NX')).write_bytes(raw);rec.update(ok=True,nx=str(out/(name+'.NX')),sha256=hashlib.sha256(raw).hexdigest(),proof=proof)
            except Exception as e:
                rec.update(ok=False,error=repr(e)[:300])
            report.append(rec)
        (out/'receipt.json').write_text(json.dumps(dict(song=key,audio=str(music) if music else None,seconds=seconds,charts=[r for r in report if r['song']==key]),ensure_ascii=False,indent=1),encoding='utf8')

if __name__=='__main__':main()
