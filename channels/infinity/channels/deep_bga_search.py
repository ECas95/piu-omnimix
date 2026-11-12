"""Deep search for movies of the songs that still have no BGA, in the user's pack and the Infinity data only."""
from pathlib import Path
import json,re,unicodedata,collections
R=Path(__file__).resolve().parent;PACK=Path(r'C:\DATA\PJD\DATA INF PRO PRO2')
VID=re.compile(r'\.(bik|mpg|mpeg|mp4|avi|wmv|m2v|webm|mkv|mov|ogv|flv)$',re.I)
sel=json.loads((R/'selection.json').read_text(encoding='utf8'))['records']
todo=[s for s in sel if not s['video_segments']]
words=lambda t:[w for w in re.findall(r'[a-z0-9]{3,}',unicodedata.normalize('NFKC',t).casefold()) if w not in ('the','short','cut','full','song','mix','remix','version')]
pack_videos=[p for p in PACK.rglob('*') if p.is_file() and VID.search(p.name)]
idx=json.loads((R.parent/'infinity_file_index.json').read_text(encoding='utf8'))
inf_videos=[k for k in idx if VID.search(k)]
out=[]
for s in todo:
    folder=next((p for p in PACK.rglob(s['source_folder']) if p.is_dir()),None)
    local=[p for p in folder.iterdir() if VID.search(p.name)] if folder else []
    lua=[]
    if folder:
        for l in folder.rglob('*.lua'):
            t=l.read_text(encoding='utf-8',errors='replace');lua+=[(l.name,m) for m in re.findall(r'["\']([^"\']+\.(?:bik|mpg|mp4|avi|wmv|m2v|webm))["\']',t,re.I)]
    ids=[i.lower() for i in re.findall(r'\b(PE\d+[A-Z]?|IN\d+[A-Z]?|[0-9A-F]{3,4})\b',s['source_folder'])]
    w=words(s['title'])
    by_id=[str(p) for p in pack_videos if any(p.stem.lower().startswith(i) for i in ids)]+[k for k in inf_videos if any(Path(k).stem.lower().startswith(i) or Path(k).stem.lower().lstrip('p').startswith(i) for i in ids)]
    by_title=[str(p) for p in pack_videos if w and all(x in p.stem.lower().replace(' ','') or x in p.stem.lower() for x in w[:2])]+[k for k in inf_videos if w and all(x in k.lower() for x in w[:2])]
    out.append(dict(gid=s['game_song_id'],title=s['title'],folder=s['source_folder'],local=[p.name for p in local],lua=lua,by_id=by_id[:6],by_title=by_title[:6]))
(R/'deep_bga_search.json').write_text(json.dumps(out,ensure_ascii=False,indent=1),encoding='utf8')
for o in out:
    hit=o['local'] or o['lua'] or o['by_id'] or o['by_title']
    print('+' if hit else '-',o['title'],'|',o['folder'],'|',o['local'][:3],o['lua'][:2],o['by_id'][:2],o['by_title'][:2])
