"""v369 frozen selection from the user's PRO / PRO 2 / INFINITY pack (charts from charts_report_pack.json).

Movie per song, in order: the pack's own BGCHANGES timeline (song folder, PRO-PRO 2 BGAs, INFINITY BGAs,
RandomMovies; a clip absent from the pack is skipped so the previous clip keeps playing, as StepMania does);
else the pack movie named after the song ID (Pe01, In01...); else the v368 movie (Infinity image / base version /
generic); else a PRIME generic HD movie for full songs and remixes; else the background still.
Existing song IDs are kept; new songs continue the A6 range.
"""
from pathlib import Path
import sys,json,re,collections
R=Path(__file__).resolve().parent;PACK=Path(r'C:\DATA\PJD\DATA INF PRO PRO2')
sys.dont_write_bytecode=True
sys.path.insert(0,r'E:\Pump It Up Data\PIU\anime_channel_dng')
import simfile as SM
CHANNELS={'PRO1':(0x44,'PUMP IT UP PRO'),'PRO2':(0x45,'PUMP IT UP PRO 2'),'INF':(0x46,'PUMP IT UP INFINITY')}
KIND_ORDER={'ARCADE':0,'REMIX':1,'FULL':2,'SHORT':3}
VIDEO=re.compile(r'\.(bik|avi|mpg|mpeg|mp4|m2v)$',re.I)
GENERIC=[r'E:\Pump It Up Data\PIU\rise_channel\into_remix_bga_v30\sources\010.m2v',r'E:\Pump It Up Data\PIU\rise_channel\into_remix_bga_v30\sources\011.m2v']
STEMS={}
for d in (PACK/'PRO - PRO 2 BGAs',PACK/'06. INFINITY BGAs',PACK/'[RandomMovies] RandomMovies'):
    for f in d.iterdir():
        if VIDEO.search(f.name):STEMS.setdefault(f.stem.lower(),f)
def tagger(text):
    head=text.split('#NOTEDATA')[0]
    return lambda k:(m.group(1).strip() if (m:=re.search(r'#'+k+r':(.*?)(?:;|\n(?=#[A-Z]+:))',head,re.S)) else '')

def main():
    raw=json.loads((R/'selection_pack_raw.json').read_text(encoding='utf8'))
    report=json.loads((R/'charts_report_pack.json').read_text(encoding='utf8'))
    old={s['game_song_id']:s for s in json.loads((R/'selection.json').read_text(encoding='utf8'))['records']}
    ids=json.loads((R/'gid_map.json').read_text(encoding='utf8')) if (R/'gid_map.json').exists() else {}   # frozen song IDs (never renumber)
    nxt=max([int(g,16) for g in old]+[int(g,16) for g in ids.values()])+1;out=[];skipped=[];why=collections.Counter();gen=0
    for s in sorted(raw,key=lambda s:(list(CHANNELS).index(s['channel']),KIND_ORDER[s['kind']],s['folder'].casefold())):
        key=s['group']+'/'+s['folder'];charts=[c for c in report if c['song']==key and c['ok']]
        if not charts:skipped.append(dict(song=key,title=s['title'],reason='no convertible official chart'));continue
        src=R/'src_pack'/s['group']/s['folder'];ssc=src/s['file'].lstrip('/')
        text=ssc.read_text(encoding='utf-8-sig',errors='replace');tag=tagger(text)
        folder=Path(s['pack_ssc']).parent if s['pack_ssc'] else None
        files={p.name.lower():p for p in folder.iterdir()} if folder else {}
        fstems={p.stem.lower():p for p in folder.iterdir() if VIDEO.search(p.name)} if folder else {}
        prev=old.get(s['previous_gid']) if s['previous_gid'] else None
        segments=[];policy=None
        if folder:
            clock=SM.Clock({k:tag(k) for k in SM.TIMING})
            for e in tag('BGCHANGES').split(','):
                f=e.split('=')
                if len(f)<2 or not VIDEO.search(f[1].strip()) or 'black' in f[1].lower():continue
                name=Path(f[1].strip().replace('\\','/'));hit=files.get(name.name.lower()) or fstems.get(name.stem.lower()) or STEMS.get(name.stem.lower())
                if hit:segments.append(dict(beat=f[0].strip(),seconds=clock.seconds(f[0].strip()),file=str(hit),rate=float(f[2] or 1) if len(f)>2 and f[2].strip() else 1.))
            if segments:policy='pack BGCHANGES timeline'
            if not segments:
                ids=re.findall(r'\b(PE\d+[A-Z]?|IN\d+[A-Z]?)\b',s['folder'],re.I)
                hit=next((STEMS[i.lower()] for i in ids if i.lower() in STEMS),None) or next((STEMS[i.lower()[:2]+i[2:].lstrip('0').zfill(2)] for i in ids if i.lower()[:2]+i[2:].lstrip('0').zfill(2) in STEMS),None)
                if hit:segments=[dict(beat='0',seconds=0.,file=str(hit),rate=1.)];policy='pack movie of the song ID '+hit.name
        if not segments and prev and prev['video_segments']:segments=prev['video_segments'];policy=prev.get('video_policy') or 'Infinity image movie (v368)'
        if not segments and s['kind'] in ('FULL','REMIX'):segments=[dict(beat='0',seconds=0.,file=GENERIC[gen%2],rate=1.)];policy='PRIME generic BGA '+Path(GENERIC[gen%2]).stem;gen+=1
        why[policy.split(' ')[0]+' '+policy.split(' ')[1] if policy else 'still']+=1
        bg=tag('BACKGROUND');still=files.get(bg.lower()) or files.get(Path(bg).stem.lower()+'-wide.png') or files.get(tag('BANNER').lower()) if folder else None
        if still and still.suffix.lower() not in ('.png','.jpg','.jpeg','.bmp'):still=None   # animated (lua) backgrounds are not stills
        if not still:still=next((p for p in (folder.iterdir() if folder else []) if p.suffix.lower() in ('.png','.jpg') and 'wide' in p.name.lower()),None)
        pv=files.get(tag('PREVIEWVID').lower()) if folder else None
        audio=next((p for p in src.iterdir() if p.suffix.lower() in ('.ogg','.mp3','.wav')),None)
        gid=ids.get(f"{s['channel']}|{s['kind']}|{s['folder']}") or s['previous_gid'] or f'{nxt:08X}'
        if gid==f'{nxt:08X}':nxt+=1
        cid,cname=CHANNELS[s['channel']]
        title=re.sub(r'\u017e-\u0178','Pi-Rho',s['title'])
        out.append(dict(game_song_id=gid,channel=s['channel'],channel_id=cid,channel_name=cname,kind=s['kind'],source_group=s['group'],source_folder=s['folder'],
            source='pack' if s['pack_ssc'] else 'infinity_image',title=title,artist=s['artist'] or (prev or {}).get('artist',''),bpm=tag('DISPLAYBPM') or tag('BPMS'),
            audio=str(audio),sample_start=float(tag('SAMPLESTART') or 0),sample_length=float(tag('SAMPLELENGTH') or 12),
            video_segments=sorted(segments,key=lambda x:x['seconds']),video_policy=policy,
            preview_video=str(pv) if pv else (prev or {}).get('preview_video'),still=str(still) if still else (prev or {}).get('still'),banner=(prev or {}).get('banner'),
            charts=[dict(name=c['name'],mode=c['mode'],level=c['level'],nx=c['nx'],sha256=c['sha256'],special=c.get('special')) for c in charts],
            skipped_charts=[dict(name=c.get('name'),mode=c['mode'],level=c.get('level'),reason=c['error']) for c in report if c['song']==key and not c['ok']]))
    (R/'selection.json').write_text(json.dumps(dict(frozen=True,version='v369 pack',songs=len(out),skipped_songs=skipped,records=out),ensure_ascii=False,indent=1),encoding='utf8')
    print('SELECTION_V369',len(out),collections.Counter(r['channel'] for r in out),'charts',sum(len(r['charts']) for r in out),dict(why),'skipped',skipped)

if __name__=='__main__':main()
