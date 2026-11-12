"""Compare the user's PRO / PRO 2 / INFINITY pack (C:\\DATA\\PJD\\DATA INF PRO PRO2) with the Infinity selection."""
from pathlib import Path
import json,re,unicodedata,hashlib,collections,os
PACK=Path(r'C:\DATA\PJD\DATA INF PRO PRO2');R=Path(__file__).resolve().parent
GROUPS={'01.PRO':'PRO1','02.PRO2':'PRO2','03.INFINITY':'INF'}
VIDEO_DIRS=[PACK/'PRO - PRO 2 BGAs',PACK/'06. INFINITY BGAs',PACK/'[RandomMovies] RandomMovies',PACK/'GenericBGA']
MODES=('pump-single','pump-double','pump-halfdouble')
def norm(t):
    t=unicodedata.normalize('NFKC',t).casefold()
    return re.sub(r'[^0-9a-z]','',t)
def parse(text):
    head=text.split('#NOTEDATA')[0]
    tag=lambda k,src=head:(m.group(1).strip() if (m:=re.search(r'#'+k+r':(.*?)(?:;|\n(?=#[A-Z]+:))',src,re.S)) else '')
    charts=[]
    for b in re.split(r'(?=#NOTEDATA:)',text)[1:]:
        st=tag('STEPSTYPE',b).lower()
        if st not in MODES:continue
        n=re.search(r'#NOTES:([^;]*);',b,re.S);notes=re.sub(r'//[^\n]*|\s','',n.group(1)) if n else ''
        charts.append(dict(type=st,meter=tag('METER',b),desc=tag('DESCRIPTION',b),notes=hashlib.sha1(notes.encode()).hexdigest()[:12],
                           timing=hashlib.sha1(''.join(tag(k,b) or tag(k) for k in ('OFFSET','BPMS','STOPS','DELAYS','WARPS','SPEEDS','SCROLLS','FAKES')).encode()).hexdigest()[:8]))
    return tag,charts
video_index={}
for d in VIDEO_DIRS:
    for f in d.rglob('*'):
        if f.suffix.lower() in ('.mpg','.mpeg','.avi','.mp4','.bik'):video_index.setdefault(f.name.lower(),f);video_index.setdefault(f.stem.lower(),f)
pack=[]
for g,ch in GROUPS.items():
    for ssc in (PACK/g).rglob('*.ssc'):
        text=ssc.read_text(encoding='utf-8-sig',errors='replace');tag,charts=parse(text)
        files={p.name.lower():p for p in ssc.parent.iterdir()}
        music=files.get(tag('MUSIC').lower()) or (lambda a:a[0] if len(a)==1 else None)([p for p in ssc.parent.iterdir() if p.suffix.lower() in ('.ogg','.mp3','.wav')])
        vids=[];missing=[]
        for e in tag('BGCHANGES').split(','):
            f=e.split('=')
            if len(f)>1 and re.search(r'\.(bik|avi|mpg|mpeg|mp4)$',f[1].strip(),re.I):
                name=os.path.basename(f[1].strip().replace('\\','/')).lower()
                hit=files.get(name) or video_index.get(name) or video_index.get(Path(name).stem)
                (vids if hit else missing).append(name)
        pack.append(dict(channel=ch,folder=ssc.parent.name,file=str(ssc),title=tag('TITLE'),artist=tag('ARTIST'),music=str(music) if music else None,
                         charts=charts,bga_refs=len(vids)+len(missing),bga_found=len(vids),bga_missing=missing[:5],preview=tag('PREVIEWVID')))
sel=json.loads((R/'selection.json').read_text(encoding='utf8'))['records']
mine={}
for s in sel:
    t=(R/'src'/s['source_group']/s['source_folder']).glob('*.ssc')
    tag,charts=parse(next(t).read_text(encoding='utf-8-sig',errors='replace'))
    mine[s['game_song_id']]=dict(s=s,charts=charts)
def key(x):return norm(x['title'])
bykey=collections.defaultdict(list)
for gid,m in mine.items():bykey[norm(m['s']['title'])].append(gid)
rows=[];matched=set()
for p in pack:
    cands=[g for g in bykey.get(key(p),[]) if g not in matched] or [g for g,m in mine.items() if m['s']['source_folder']==p['folder'] and g not in matched]
    gid=next((g for g in cands if mine[g]['s']['source_folder']==p['folder']),cands[0] if cands else None)
    if gid:matched.add(gid)
    m=mine.get(gid)
    ours={(c['type'],c['meter'],c['notes']) for c in m['charts']} if m else set()
    theirs={(c['type'],c['meter'],c['notes']) for c in p['charts']}
    rows.append(dict(p,gid=gid,our_title=m['s']['title'] if m else None,our_kind=m['s']['kind'] if m else None,
                     same_charts=len(ours&theirs),only_pack=len(theirs-ours),only_ours=len(ours-theirs),
                     our_video=bool(m and m['s']['video_segments']),our_policy=m['s'].get('video_policy') if m else None))
unmatched=[mine[g]['s']['title'] for g in mine if g not in matched]
(R/'pack_compare.json').write_text(json.dumps(dict(rows=rows,unmatched_ours=unmatched),ensure_ascii=False,indent=1),encoding='utf8')
c=collections.Counter()
for r in rows:
    c['pack_songs']+=1;c['matched' if r['gid'] else 'new_in_pack']+=1
    c['has_audio' if r['music'] else 'no_audio']+=1
    if r['gid'] and not r['our_video'] and r['bga_found']:c['gains_bga']+=1
    if r['bga_refs'] and not r['bga_found']:c['pack_bga_missing']+=1
    if r['only_pack']:c['songs_with_new_or_changed_charts']+=1
    if r['only_ours']:c['songs_where_ours_differ']+=1
print(c);print('our songs not in pack',len(unmatched),unmatched[:40])
print('pack songs not in ours',[(r['channel'],r['title']) for r in rows if not r['gid']][:60])
