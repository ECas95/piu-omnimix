"""Frozen selection for the PRO 1 / PRO 2 / INFINITY channels: song IDs, metadata, charts, media sources."""
from pathlib import Path
import sys,json,re
R=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.path.insert(0,r'E:\Pump It Up Data\PIU\anime_channel_dng')
import simfile as SM
CHANNELS={'PRO1':(0x44,'PUMP IT UP PRO'),'PRO2':(0x45,'PUMP IT UP PRO 2'),'INF':(0x46,'PUMP IT UP INFINITY')}
KIND_ORDER={'ARCADE':0,'REMIX':1,'FULL':2,'SHORT':3}
VIDEO=re.compile(r'\.(bik|avi|mpg|mp4)$',re.I)

def main():
    sel=json.loads((R/'selection_raw.json').read_text(encoding='utf8'))
    report=json.loads((R/'charts_report.json').read_text(encoding='utf8'))
    out=[];n=0;skipped=[]
    for s in sorted(sel,key=lambda s:(list(CHANNELS).index(s['channel']),KIND_ORDER[s['kind']],s['folder'].casefold())):
        key=s['group']+'/'+s['folder'];folder=R/'src'/s['group']/s['folder']
        files={p.name.lower():p for p in folder.iterdir()}
        text=(folder/Path(s['file']).name).read_text(encoding='utf-8-sig',errors='replace')
        head=text.split('#NOTEDATA')[0]   # global tags only; a missing ';' ends at the next tag line
        tag=lambda k:(m.group(1).strip() if (m:=re.search(r'#'+k+r':(.*?)(?:;|\n(?=#[A-Z]+:))',head,re.S)) else '')
        timing={k:tag(k) for k in SM.TIMING}
        clock=SM.Clock(timing)
        segments=[]
        for e in tag('BGCHANGES').split(','):
            f=e.split('=')
            if len(f)>1 and VIDEO.search(f[1].strip()) and f[1].strip().lower()!='black.bik' and f[1].strip().lower() in files:
                segments.append(dict(beat=f[0].strip(),seconds=clock.seconds(f[0].strip()),file=str(files[f[1].strip().lower()]),rate=float(f[2] or 1) if len(f)>2 else 1.))
        bg=files.get(tag('BACKGROUND').lower());wide=files.get(Path(tag('BACKGROUND')).stem.lower()+'-wide.png') if tag('BACKGROUND') else None
        banner=files.get(tag('BANNER').lower())
        still=wide or bg or banner
        charts=[c for c in report if c['song']==key and c['ok']]
        audio=files.get(tag('MUSIC').lower()) or (lambda a:a[0] if len(a)==1 else None)([f for f in files.values() if f.suffix.lower() in ('.ogg','.mp3','.wav')])   # StepMania: the folder's only audio file
        if not charts or audio is None:   # no playable chart, or the audio is absent from the game data
            skipped.append(dict(song=key,title=s['title'],reason='no audio file in source data' if charts else 'no convertible chart'));continue
        n+=1;cid,cname=CHANNELS[s['channel']]
        out.append(dict(game_song_id=f'{0xA6000000+n:08X}',channel=s['channel'],channel_id=cid,channel_name=cname,kind=s['kind'],
            source_group=s['group'],source_folder=s['folder'],title=s['title'],artist=s['artist'],bpm=tag('DISPLAYBPM') or s.get('bpms',''),
            audio=str(audio),sample_start=float(tag('SAMPLESTART') or 0),sample_length=float(tag('SAMPLELENGTH') or 12),
            video_segments=sorted(segments,key=lambda x:x['seconds']),preview_video=str(files[tag('PREVIEWVID').lower()]) if tag('PREVIEWVID').lower() in files else None,
            still=str(still) if still else None,banner=str(banner) if banner else None,
            charts=[dict(name=c['name'],mode=c['mode'],level=c['level'],nx=c['nx'],sha256=c['sha256'],special=c.get('special')) for c in charts],
            skipped_charts=[dict(name=c.get('name'),mode=c['mode'],level=c.get('level'),reason=c['error']) for c in report if c['song']==key and not c['ok']]))
    (R/'selection.json').write_text(json.dumps(dict(frozen=True,songs=len(out),skipped_songs=skipped,records=out),ensure_ascii=False,indent=1),encoding='utf8')
    import collections
    print('SELECTION',len(out),collections.Counter(r['channel'] for r in out),'charts',sum(len(r['charts']) for r in out),
          'video',sum(bool(r['video_segments']) for r in out),'still_only',sum(not r['video_segments'] and bool(r['still']) for r in out),'skipped',skipped)

if __name__=='__main__':main()
