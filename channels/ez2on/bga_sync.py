"""BGA <-> Song.mp3 for the confirmed songs -> bga_sync.json. video time 0 plays at Song.mp3 time `start_s`.
  same length (|bga - song| <= 0.15 s): made together -> start 0 (visual peak recorded as a check)
  otherwise: visual activity vs audio onsets must give one clear peak (2nd peak <= 0.9) -> that start
  anything else: not accepted (song left out)."""
import json,os,sys
from concurrent.futures import ProcessPoolExecutor,as_completed
sys.path.insert(0,r'D:\EZ2ON_PIU');import bga_probe as V,measure_sync as M
def one(k,bga):
    try:
        m=V.measure(k,os.path.join(M.O,k,bga));d=m['bga_s']-m['song_s']
        if abs(d)<=0.15:m.update(status='OK',start_s=0.0,rule='same length')
        elif len(m['peaks'])>1 and m['peaks'][1][1]<=0.9:m.update(status='OK',start_s=round(m['fine']/1000,3),rule='visual peak')
        else:m.update(status='REVISAR',rule='lengths differ and no clear visual peak')
    except Exception as e:m=dict(status='REVISAR',rule=repr(e)[:200])
    return k,m
if __name__=='__main__':
    d=json.load(open('D:/EZ2ON_PIU/sync_final.json',encoding='utf8'));f='D:/EZ2ON_PIU/bga_sync.json';out=json.load(open(f,encoding='utf8')) if os.path.exists(f) else {};done=set(out)   # resumable
    jobs=[(k,v['bga']) for k,v in d.items() if v['status'] in ('CONFIRMADO','CONFIRMADO_VIDEO') and v['bga'] and k not in done]
    with ProcessPoolExecutor(6) as ex:
        for i,f in enumerate(as_completed([ex.submit(one,*j) for j in jobs]),1):
            k,m=f.result();out[k]=m;print('BGA',i,len(jobs),k,m['status'],m['rule'],m.get('start_s'),flush=True)
    json.dump(out,open(r'D:\EZ2ON_PIU\bga_sync.json','w',encoding='utf8'),ensure_ascii=False,indent=1)
