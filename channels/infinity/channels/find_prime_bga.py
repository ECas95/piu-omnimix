"""Find PRIME catalog songs (native Fiesta 2010 / Fiesta EX / Fiesta 2 / ... and imports) that match the
PRO / PRO 2 / INFINITY songs without their own movie, and whose PRIME entry carries a movie (/D/<id>/V/...)."""
from pathlib import Path
import sys,json,re,struct,unicodedata,collections
R=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.path[:0]=[r'E:\Pump It Up Data\PIU',r'E:\Pump It Up Data\PIU\nsde_channel']
from current_parent import load
P,game=load()
F=Path(r'D:\Pump It Up Data\PIU\final_v363\payloads\D\LIST')
raw=F.read_bytes();ns,nc=struct.unpack_from('<II',raw);pool=P.B.string_entries_from(Path(str(F)+'.0').read_bytes())
def core(t):
    t=unicodedata.normalize('NFKC',t).casefold()
    t=re.sub(r'-\s*(full song|short cut)\s*-|\((full song|shortcut|short cut|the trinity)\)|\[.*?\]','',t)
    return re.sub(r'[^0-9a-z]','',t)
def kind(t):
    t=t.upper();return 'FULL' if 'FULL SONG' in t or 'LONG VER' in t else 'SHORT' if 'SHORT CUT' in t or 'SHORTCUT' in t else 'OTHER'
prime=collections.defaultdict(list)
for i in range(ns-1):
    s=struct.unpack_from('<9I',raw,44+i*36)
    if s[1]>=len(pool) or (s[0]>>24)==0xA6:continue
    title=pool[s[1]].decode('utf8','replace');gid=f'{s[0]:X}'
    movie=next((p for p in (f'/D/{gid}/V/HD/.V',f'/D/{gid}/V/.V',f'/D/{gid}/V/SD/.V') if p.encode() in game.index.files),None)
    if movie:prime[(core(title),kind(title))].append(dict(id=gid,title=title,artist=pool[s[2]].decode('utf8','replace') if s[2]<len(pool) else '',channel=(s[5]&255)+24,movie=movie))
sel=json.loads((R/'selection.json').read_text(encoding='utf8'))['records']
weak=[s for s in sel if not s['video_segments'] or (s.get('video_policy') or '').startswith(('PRIME generic','Infinity BGA of the base'))]
found=[];missing=[]
for s in weak:
    k=(core(s['title']),'FULL' if s['kind']=='FULL' else 'SHORT' if s['kind']=='SHORT' else 'OTHER')
    art=lambda a:set(re.findall(r'[a-z0-9]{3,}',unicodedata.normalize('NFKC',a).casefold()))
    same=lambda h:bool(art(h['artist'])&art(s['artist'])) or not art(s['artist'])   # same song = some artist word in common
    hits=[h for h in prime.get(k,[]) if same(h)]
    if not hits:hits=[dict(h,from_other_kind=True) for kk in ('OTHER','FULL','SHORT') for h in prime.get((k[0],kk),[]) if same(h)]   # full / shortcut: the arcade movie
    (found if hits else missing).append(dict(gid=s['game_song_id'],title=s['title'],kind=s['kind'],channel=s['channel_name'],now=s.get('video_policy') or 'still',prime=hits))
(R/'prime_bga_matches.json').write_text(json.dumps(dict(found=found,missing=missing),ensure_ascii=False,indent=1),encoding='utf8')
print('WEAK',len(weak),'FOUND_IN_PRIME',len(found),'STILL_MISSING',len(missing))
for f in found:print(' +',f['channel'],'|',f['title'],'|',f['now'],'->',[(h['title'],h['artist'],h['channel'],h['id']) for h in f['prime']][:3])
print('missing:',len(missing))
