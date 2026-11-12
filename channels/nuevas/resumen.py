import json,collections
from pathlib import Path
R=json.loads((Path(__file__).parent/'inventario.json').read_text(encoding='utf8'))
print('total',len(R),'errors',sum(1 for r in R if r.get('error')))
for r in R:
    if r.get('error'):print(' ERR',r['pack'],r['folder'][-60:],r['error'][:150])
for pack in sorted({r['pack'] for r in R}):
    P=[r for r in R if r['pack']==pack and not r.get('error')]
    print('==',pack,len(P),'video named',sum(bool(r.get('video')) for r in P),'loose only',sum(bool(not r.get('video') and r.get('loose')) for r in P),'no video',sum(not r.get('video') and not r.get('loose') for r in P),'no audio',sum(not r.get('audio') for r in P),'shared video',sum(r.get('video_shared',0)>1 for r in P),'in game',sum(bool(r.get('in_game')) for r in P))
    print('  modes',collections.Counter(m for r in P for m in r.get('modes',{})).most_common(8))
    print('  subs',collections.Counter(r.get('sub') for r in P).most_common(8))
    print('  codecs',collections.Counter(r.get('video_info',{}).get('codec') for r in P if r.get('video')).most_common(6),'size',collections.Counter((r.get('video_info',{}).get('w'),r.get('video_info',{}).get('h')) for r in P if r.get('video')).most_common(6))
    gap=[round(r['audio_info']['seconds']-r['video_info']['seconds']) for r in P if r.get('video') and r.get('audio_info') and r.get('video_info')]
    print('  audio-video s: under -5',sum(g<-5 for g in gap),'-5..5',sum(-5<=g<=5 for g in gap),'5..30',sum(5<g<=30 for g in gap),'over 30',sum(g>30 for g in gap))
    dup=collections.Counter(r.get('norm') for r in P if r.get('video') or r.get('loose'));print('  repeated titles inside the pack',sum(v>1 for v in dup.values()),[k for k,v in dup.items() if v>1][:12])
    print('  in game:',[(r['title'][:24],[(x[3],x[1][:20]) for x in r['in_game']][:2]) for r in P if r.get('in_game')][:30])
print('== SEL detail');[print(' ',r['title'][:30],'|',r['artist'][:18],r.get('modes'),'bg',r.get('bg'),'beat',r.get('video_beat'),'offs',r.get('offset'),'v',round(r.get('video_info',{}).get('seconds',0)),'a',round(r.get('audio_info',{}).get('seconds',0)),[(c[0][5:7],c[1]) for c in r['charts']][:16],'ingame',[x[3] for x in r['in_game']]) for r in R if r['pack']=='SEL' and not r.get('error')]
L=[r for r in R if r['pack']=='Love Live AC And DLC' and not r.get('error')];print('== LL no video:',[r['title'] for r in L if not r.get('video')])
M=[r for r in R if r['pack']=='Song Mix 1' and not r.get('error')];print('== MIX video offsets',collections.Counter(r.get('video_offset_ms') for r in M if r.get('video')).most_common(10));print(' MIX modes per chart',collections.Counter((c[0],c[1]) for r in M for c in r['charts']).most_common(12))
print(' MIX no video:',len([r for r in M if not r.get('video')]),[r['title'][:22] for r in M if not r.get('video')][:20])
I=[r for r in R if r['pack']=='IDOLMASTER' and not r.get('error')]
print('== IM by sub',[(s,sum(1 for r in I if r.get('sub')==s),sum(1 for r in I if r.get('sub')==s and r.get('video'))) for s in sorted({r.get('sub') for r in I})])
print(' IM no video sample',[r['title'][:22] for r in I if not r.get('video')][:15]);print(' IM beats',collections.Counter(str(r.get('video_beat'))[:6] for r in I if r.get('video')).most_common(8))
print(' LL beats',collections.Counter(str(r.get('video_beat'))[:6] for r in L if r.get('video')).most_common(8))
