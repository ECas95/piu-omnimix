"""Which MEASURE is right: visual activity at the judgement area of the gameplay video (notes arriving + hit
explosions, any skin) vs the played chart's note density, at the candidate offsets g + k*measure (k=-3..3).
g = audio-measured offset (E2-E3, video audio timeline). Used only to choose between whole-measure candidates;
the fine phase stays the audio measurement. Validated on CONFIRMADO songs first."""
import json,os,sys,subprocess,numpy as np
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0,r'D:\EZ2ON_PIU');import measure_sync as M
FPS=30
def activity(v):   # playfield centre band around the judgement line (x 230-410, y 200-300 of 640x360)
    raw=subprocess.check_output([M.FF,'-v','error','-i',v,'-an','-vf',f'fps={FPS},crop=180:100:230:200,scale=90:50,format=gray','-f','rawvideo','-'])
    f=np.frombuffer(raw,np.uint8).reshape(-1,50*90).astype(np.float32);d=np.abs(np.diff(f,axis=0)).mean(1)
    return np.convolve(d,np.ones(6)/6,'same')
def density(times,n):
    t=np.zeros(n);i=(np.asarray(times)/1000*FPS).astype(int);i=i[(i>=0)&(i<n)];np.add.at(t,i,1);return np.convolve(t,np.ones(6)/6,'same')
def score(a,times,lag_v):
    d=density(np.asarray(times)+lag_v,len(a));x=a-a.mean();y=d-d.mean();return float(np.dot(x,y)/(np.linalg.norm(x)*np.linalg.norm(y)+1e-9))
def one(k,vid):
    s=json.load(open(rf'D:\EZ2ON_PIU\sync\{k}.json',encoding='utf8'))
    js=os.path.join(M.B,'ez2on_charts',s['chart'],s['played'] or '4S_SHD.json')
    if not os.path.exists(js):return k,dict(error='no played chart')
    times=[x['time_ms'] for x in json.load(open(js,encoding='utf8'))['notes']];a=activity(vid)
    beat=s['beat_ms'];g=s['E2_fine']   # video timeline = chart + E2 (E2 is measured on this recording's audio)
    sc={kk/2:score(a,times,g+kk/2*beat) for kk in range(-24,25)}   # half-beat steps, +-3 measures
    best=max(sc,key=sc.get);second=max(v for kk,v in sc.items() if kk!=best)
    np.save(f'D:/EZ2ON_PIU/activity/{k}.npy',a)
    return k,dict(scores={str(kk):round(v,4) for kk,v in sc.items()},best=best,margin=round(sc[best]-second,4))
if __name__=='__main__':
    ids=json.load(open(r'D:\EZ2ON_PIU\videos_ids.json'))
    if os.path.exists(r'D:\EZ2ON_PIU\videos_ids2.json'):ids.update(json.load(open(r'D:\EZ2ON_PIU\videos_ids2.json')))
    jobs=[(k,rf'D:\EZ2ON_PIU\gameplay_video\{i}.mp4') for k,i in ids.items() if os.path.exists(rf'D:\EZ2ON_PIU\gameplay_video\{i}.mp4') and (len(sys.argv)<2 or k in sys.argv[1:])]
    out_f='D:/EZ2ON_PIU/video_beat.json';out=json.load(open(out_f)) if os.path.exists(out_f) else {}
    todo=[j for j in jobs if j[0] not in out]
    with ProcessPoolExecutor(6) as ex:
        for k,r in (ex.map(one,*zip(*todo)) if todo else []):out[k]=r
    json.dump(out,open(out_f,'w'),indent=1)
    fin=json.load(open(r'D:\EZ2ON_PIU\sync_final.json',encoding='utf8'))
    conf=[(k,r) for k,r in out.items() if 'best' in r and fin[k]['status']=='CONFIRMADO']
    print('confirmed',len(conf),'video picks the accepted offset to the half beat:',sum(r['best']==0 for _,r in conf),
          'margin>=0.01:',sum(r['best']==0 and r['margin']>=0.01 for _,r in conf),'| wrong:',[(k,r['best'],r['margin']) for k,r in conf if r['best']!=0][:12])
