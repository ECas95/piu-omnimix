"""v369 source: the user's PRO / PRO 2 / INFINITY pack (C:\\DATA\\PJD\\DATA INF PRO PRO2), user 2026-10-26.

Songs: every song of the pack (01.PRO -> PRO1, 02.PRO2 -> PRO2, 03.INFINITY -> INF) plus any song of the
Infinity-image selection the pack lacks. Charts: official Pro and Infinity charts only (description/chart name
'pro' or 'infinity'); no UCS, quest, music-train, co-op (-p), routine or lights charts. A song whose pack
charts are none of those keeps the official charts of the Infinity image (also without UCS/quest/train).
Writes src_pack/<channel>/<folder>/ (filtered .ssc + audio copy) and selection_pack_raw.json.
"""
from pathlib import Path
import json,re,shutil,unicodedata,hashlib,collections
PACK=Path(r'C:\DATA\PJD\DATA INF PRO PRO2');R=Path(__file__).resolve().parent;OUT=R/'src_pack'
GROUPS={'01.PRO':'PRO1','02.PRO2':'PRO2','03.INFINITY':'INF'}
KIND={'ARCADE':'ARCADE','SPECIAL':'ARCADE','FULLSONG':'FULL','REMIX':'REMIX','SHORTCUT':'SHORT'}
MODES=('pump-single','pump-double','pump-halfdouble')
EXCLUDE=re.compile(r'ucs|quest|train',re.I)   # canceled Pro 2 'Gauntlet' songs are official (J. Dread); 'gauntlet train' is a train
def tag(k,src):
    m=re.search(r'#'+k+r':(.*?)(?:;|\n(?=#[A-Z]+:))',src,re.S);return m.group(1).strip() if m else ''
def blocks(text):
    head,*bl=re.split(r'(?=#NOTEDATA:)',text);return head,bl
def notes_hash(b):
    n=re.search(r'#NOTES:([^;]*);',b,re.S);return hashlib.sha1(re.sub(r'//[^\n]*|\s','',n.group(1) if n else '').encode()).hexdigest()
def official(b):
    words=(tag('DESCRIPTION',b)+' '+tag('CHARTNAME',b)).lower()
    if EXCLUDE.search(words):return None
    return 'pro' if re.search(r'\bpro\b',words) else 'infinity' if 'infinity' in words else None
STAFF=re.compile(r'^\s*$|j\.?\s*dread|k\.?\s*ward|hidden',re.I)   # Pro's own step makers / hidden-song charts
def core(title):
    t=unicodedata.normalize('NFKC',title).casefold()
    t=re.sub(r'[žπ]-[ÿρ]','pi-rho',t).replace('c.t.m.)','c.t.mix)')   # mis-encoded Pi-Rho; C.T.M. = C.T.Mix
    t=re.sub(r'^the ','',t)
    t=re.sub(r'-\s*(full song|short cut)\s*-|\((full song|shortcut|short cut|long ver\.?)\)|\bfull\b','',t)
    return re.sub(r'[^0-9a-z]','',t)
def kind_of(head,title,folder=''):
    t=(title+' '+folder).upper()
    if 'FULL SONG' in t or 'LONG VER' in t:return 'FULL'   # the title / folder marker wins over a generic SONGTYPE
    if 'SHORT CUT' in t or 'SHORTCUT' in t:return 'SHORT'
    k=KIND.get(tag('SONGTYPE',head).upper())
    return k or ('REMIX' if 'REMIX' in t else 'ARCADE')

def main():
    old=json.loads((R/'selection.json').read_text(encoding='utf8'))['records'];olds={}
    for s in old:olds.setdefault((core(s['title']),s['kind']),[]).append(s)
    oldsrc={s['game_song_id']:next((R/'src'/s['source_group']/s['source_folder']).glob('*.ssc')) for s in old}
    out=[];used=set();stats=collections.Counter()
    for g,ch in GROUPS.items():
        for ssc in sorted((PACK/g).rglob('*.ssc')):
            text=ssc.read_text(encoding='utf-8-sig',errors='replace');head,bl=blocks(text);title=tag('TITLE',head)
            kind=kind_of(head,title,ssc.parent.name)
            cands=[s for s in olds.get((core(title),kind),[]) if s['game_song_id'] not in used]
            m=next((s for s in cands if s['source_folder']==ssc.parent.name),cands[0] if cands else None)
            if m:used.add(m['game_song_id'])
            image_hashes={notes_hash(b) for b in blocks(oldsrc[m['game_song_id']].read_text(encoding='utf-8-sig',errors='replace'))[1]} if m else set()
            keep=[];why=collections.Counter()
            for b in bl:
                if tag('STEPSTYPE',b).lower() not in MODES:why['other_mode']+=1;continue
                o=official(b)
                if o:keep.append(b);why[o]+=1
                elif notes_hash(b) in image_hashes and not EXCLUDE.search(tag('DESCRIPTION',b)+tag('CHARTNAME',b)):keep.append(b);why['as_in_infinity_image']+=1
                else:why['excluded']+=1
            source='pack'
            if not keep:   # untagged official charts: Pro's step makers (J. Dread / K. Ward) and hidden songs; level 99 'mini-mix' items cannot be shown
                for b in bl:
                    if tag('STEPSTYPE',b).lower() in MODES and not EXCLUDE.search(tag('DESCRIPTION',b)+tag('CHARTNAME',b)) and STAFF.search(tag('DESCRIPTION',b)+' '+tag('CREDIT',b)) and float(tag('METER',b) or 99)<30:
                        keep.append(b);why['pro_staff_or_hidden']+=1
            if not keep and m:   # no official pack chart: the Infinity image's official charts
                ih,ib=blocks(oldsrc[m['game_song_id']].read_text(encoding='utf-8-sig',errors='replace'))
                keep=[b for b in ib if tag('STEPSTYPE',b).lower() in MODES and not EXCLUDE.search(tag('DESCRIPTION',b)+tag('CHARTNAME',b))];source='infinity_image_charts'
            stats[source if keep else 'no_charts']+=1
            if not keep:continue
            dest=OUT/ch/ssc.parent.name;dest.mkdir(parents=True,exist_ok=True)
            (dest/ssc.name).write_text(head+''.join(keep),encoding='utf-8')
            files={p.name.lower():p for p in ssc.parent.iterdir()}
            audio=files.get(tag('MUSIC',head).lower()) or (lambda a:a[0] if len(a)==1 else None)([p for p in ssc.parent.iterdir() if p.suffix.lower() in ('.ogg','.mp3','.wav')])
            if audio and not (dest/audio.name).exists():shutil.copy2(audio,dest/audio.name)
            out.append(dict(group=ch,folder=ssc.parent.name,file='/'+ssc.name,pack_ssc=str(ssc),title=title,artist=tag('ARTIST',head),channel=ch,kind=kind,
                            previous_gid=m['game_song_id'] if m else None,chart_source=source,chart_counts=dict(why),audio=str(audio) if audio else None))
    for s in old:   # songs of the Infinity image the pack does not have
        if s['game_song_id'] in used:continue
        dest=OUT/s['channel']/s['source_folder'];dest.mkdir(parents=True,exist_ok=True);src=oldsrc[s['game_song_id']]
        h,b=blocks(src.read_text(encoding='utf-8-sig',errors='replace'))
        (dest/src.name).write_text(h+''.join(x for x in b if not EXCLUDE.search(tag('DESCRIPTION',x)+tag('CHARTNAME',x))),encoding='utf-8')
        a=Path(s['audio']);shutil.copy2(a,dest/a.name) if not (dest/a.name).exists() else None
        out.append(dict(group=s['channel'],folder=s['source_folder'],file='/'+src.name,pack_ssc=None,title=s['title'],artist=s['artist'],channel=s['channel'],kind=s['kind'],
                        previous_gid=s['game_song_id'],chart_source='infinity_image_only',audio=str(a)));stats['infinity_image_only']+=1
    (R/'selection_pack_raw.json').write_text(json.dumps(out,ensure_ascii=False,indent=1),encoding='utf8')
    print('PACK_SELECTION',len(out),dict(stats),collections.Counter((s['channel'],s['kind']) for s in out))
    print('image-only songs:',[s['title'] for s in out if s['chart_source']=='infinity_image_only'])

if __name__=='__main__':main()
