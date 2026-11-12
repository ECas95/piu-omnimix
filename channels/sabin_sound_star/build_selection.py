"""SABIN SOUND STAR channel (id 0x47, version 0x2f) records, appended to D:\PIU_INFINITY\channels\selection.json
(same schema as PRO / PRO 2 / INFINITY, so prepare_media / catalog_ext / package handle them unchanged).
Songs: every song with a Percussion chart AND its own BGA (user 2026-10-29). Titles/artists: the user's song list
(Desktop CSV; Korean/Japanese titles -> their English title, PRIME's font is Latin only). Movie: <song>.bik from
the time in <song>.del (ms). Charts: sss_charts output, generated -> NEW tag. IDs A7000001+ frozen in gid_map.json."""
from pathlib import Path
import json,hashlib,collections,subprocess
H=Path(__file__).resolve().parent;SEL=Path(r'D:\PIU_INFINITY\channels\selection.json')
import sys;sys.path.insert(0,str(H));import sss
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
OVERRIDE=json.loads((H/'bga_delay_override.json').read_text())   # v378: BGA start for the songs whose .del is missing

def main():
    titles=json.loads((H/'titles.json').read_text(encoding='utf8'));inv={x['song']:x for x in json.loads((H/'inventory.json').read_text())}
    refs=collections.defaultdict(list)
    for r in json.loads((H/'refs.json').read_text())['records']:refs[r['song']].append(r)
    gmap=json.loads((H/'gid_map.json').read_text()) if (H/'gid_map.json').exists() else {}
    nxt=max([int(g,16) for g in gmap.values()]+[0xA7000000])+1;recs=[];skipped=[]
    for song in sorted(refs,key=str.lower):
        res=json.loads((H/'runs'/song/'song.json').read_text());audio=H/'audio'/(song+'.wav')
        if not res['charts'] or not audio.exists():skipped.append(song);continue
        if song not in gmap:gmap[song]=f'{nxt:08X}';nxt+=1
        bik=sss.GAME/'movie'/inv[song]['movie'];dl=bik.with_suffix('.del');delay=int(dl.read_text().strip())/1000 if dl.exists() else 0.
        if not dl.exists() and song in OVERRIDE:delay=OVERRIDE[song]['start_s']   # v378: .del missing from this dump (bga_delay_override.json)
        dur=float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(audio)],capture_output=True,text=True).stdout)
        still=H/'stills'/(song+'.png');still.parent.mkdir(exist_ok=True)
        if not still.exists():subprocess.run(['ffmpeg','-v','error','-y','-ss','25','-i',str(bik),'-frames:v','1',str(still)],check=True)
        bp=sorted({round(b,2) for r in refs[song] for _,b in r['bpms']});fmt=lambda v:f'{v:.2f}'.rstrip('0').rstrip('.')
        charts=[];names=set()
        for c in sorted(res['charts'],key=lambda c:(c['mode'],c['level'],c['tier'])):
            name=('S' if c['mode']=='Single' else 'D')+f"{c['level']:02d}";k=0
            while name+('' if not k else chr(96+k)) in names:k+=1
            name+='' if not k else chr(96+k);names.add(name)
            assert sha(c['nx'])==c['sha256']
            charts.append(dict(name=name,mode='pump-single' if c['mode']=='Single' else 'pump-double',level=c['level'],nx=c['nx'],sha256=c['sha256'],generated=True,
                               special=dict(source_chart=c['source_chart'],reduction=c['reduction'],omitted_conflicts=c['omitted_conflicts'])))
        t=titles[song]
        recs.append(dict(game_song_id=gmap[song],channel='SSS',channel_id=0x47,channel_name='SABIN SOUND STAR',kind='ARCADE',source_group='SSS',source_folder=song,
            source='sabin_sound_star',title=t['display'],artist=t['artist'],bpm=fmt(bp[0]) if len(bp)==1 else fmt(bp[0])+'-'+fmt(bp[-1]),audio=str(audio),
            sample_start=round(dur*.35,3),sample_length=12.,video_segments=[dict(beat='0',seconds=delay,file=str(bik),rate=1.)],video_policy=f'SSS own BGA {bik.name} from {delay:.3f}s (.del)',
            preview_video=None,still=str(still),banner=None,charts=charts,skipped_charts=[]))
    (H/'gid_map.json').write_text(json.dumps(gmap,indent=1))
    S=json.loads(SEL.read_text(encoding='utf8'));S['records']=[r for r in S['records'] if r['channel']!='SSS']+recs;S['songs']=len(S['records'])
    SEL.write_text(json.dumps(S,ensure_ascii=False,indent=1),encoding='utf8')
    print('SSS_SELECTION',len(recs),'songs',sum(len(r['charts']) for r in recs),'charts','skipped',skipped)
if __name__=='__main__':main()
