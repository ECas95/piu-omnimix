"""Chart <-> gameplay VIDEO through the 4 lane buttons (they light up when the player hits a note).
Per lane: brightness rise of its button (640x360 layout, buttons at y 281-296, x 252-388 split in 4) vs that lane's
note times of the played chart (4K recordings). Lane patterns are not periodic, so the peak is unique.
  lag_v = video time - chart time;  chart->Song = lag_v - E3 (E3 = gameplay audio - Song, same YouTube timeline).
Output lane_sync.json; validated against the CONFIRMADO offsets before being trusted."""
import json,os,sys,subprocess,numpy as np
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0,r'D:\EZ2ON_PIU');import measure_sync as M
FPS=30;X0,X1,Y0,Y1=252,388,280,296   # even sizes (yuv crop)
def buttons(v):
    raw=subprocess.check_output([M.FF,'-v','error','-i',v,'-an','-vf',f'fps={FPS},crop={X1-X0}:{Y1-Y0}:{X0}:{Y0},format=gray','-f','rawvideo','-'])
    f=np.frombuffer(raw,np.uint8).reshape(-1,Y1-Y0,X1-X0).astype(np.float32);w=(X1-X0)/4
    lanes=np.stack([f[:,:,int(i*w+3):int((i+1)*w-3)].mean((1,2)) for i in range(4)],1)
    d=np.maximum(np.diff(lanes,axis=0,prepend=lanes[:1]),0);return d/(d.std(0)+1e-6)
def trains(js,n):
    t=np.zeros((n,4))
    for x in json.load(open(js,encoding='utf8'))['notes']:
        i=int(round(x['time_ms']/1000*FPS))
        if 0<=i<n and 1<=x['lane']<=4:t[i,x['lane']-1]+=1
    return t
def one(k,vid):
    s=json.load(open(rf'D:\EZ2ON_PIU\sync\{k}.json',encoding='utf8'))
    if not s.get('played','') or not s['played'].startswith('4S'):return k,dict(error='not a 4K recording')
    B=buttons(vid);T=trains(os.path.join(M.B,'ez2on_charts',s['chart'],s['played']),len(B)+FPS*120)
    lags=np.arange(-FPS*30,FPS*90);n=len(B)
    sc=np.array([sum(np.dot(B[max(0,l):min(n,l+len(T)),c],T[max(0,-l):max(0,-l)+min(n,l+len(T))-max(0,l),c]) for c in range(4)) for l in lags])
    i=int(sc.argmax());second=sc[np.abs(lags-lags[i])>3].max()
    off=(i>0 and i<len(sc)-1) and 0.5*(sc[i-1]-sc[i+1])/(sc[i-1]-2*sc[i]+sc[i+1]) or 0
    lag_v=(lags[i]+off)/FPS*1000
    return k,dict(lag_v_ms=round(lag_v,1),second=round(float(second/sc[i]),3),chart_to_song=round(lag_v-s['E3_fine'],1),E1=[p[0] for p in s['E1'][:4]])
if __name__=='__main__':
    ids=json.load(open(r'D:\EZ2ON_PIU\videos_ids.json'))
    jobs=[(k,rf'D:\EZ2ON_PIU\gameplay_video\{i}.mp4') for k,i in ids.items() if os.path.exists(rf'D:\EZ2ON_PIU\gameplay_video\{i}.mp4') and (len(sys.argv)<2 or k in sys.argv[1:])]
    out_f=r'D:\EZ2ON_PIU\lane_sync.json';out=json.load(open(out_f)) if os.path.exists(out_f) else {}
    with ProcessPoolExecutor(6) as ex:
        todo=[j for j in jobs if j[0] not in out]
        for k,r in (ex.map(one,*zip(*todo)) if todo else []):out[k]=r
    json.dump(out,open(out_f,'w'),indent=1)
    fin=json.load(open(r'D:\EZ2ON_PIU\sync_final.json',encoding='utf8'))
    v=[(k,r['chart_to_song'],fin[k]['lag_ms'],r['second']) for k,r in out.items() if 'chart_to_song' in r and fin[k]['status']=='CONFIRMADO']
    e=np.array([a-b for _,a,b,_ in v]);print('validated',len(v),'|err|<=20ms',(abs(e)<=20).sum(),'<=40',(abs(e)<=40).sum(),'median',np.median(e).round(1),'second pct',np.percentile([x[3] for x in v],[50,90]).round(3))
    print('worst',sorted(v,key=lambda x:-abs(x[1]-x[2]))[:6])
