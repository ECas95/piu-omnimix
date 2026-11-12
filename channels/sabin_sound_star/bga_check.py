"""SSS BGA start (Song time at which movie frame 0 plays): visual activity of the .bik vs audio onsets.
Validated against the songs whose <movie>.del gives the game's own delay; then measured for the ones without .del."""
import json,os,sys,numpy as np
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0,r'D:\EZ2ON_PIU');import measure_sync as M,bga_probe as V
def one(r):
    b=r['video_segments'][0]['file'];d=b[:-4]+'.del';dl=int(open(d).read().strip())/1000 if os.path.exists(d) else None
    sb=M.bands(r['audio']).sum(1);va=V.vact(b)
    va=np.interp(np.arange(0,len(va)*100/M.FPS,100/M.FPS)[:int(len(va)*M.FPS/100)],np.arange(len(va)),va)
    L,S=M.xcorr(sb,va,-3000,8000);pk=M.peaks(L,S)
    return dict(song=r['source_folder'],title=r['title'],del_s=dl,visual_s=round(M.refine(L,S,int(np.argmax(S)))/1000,3),second=pk[1][1] if len(pk)>1 else 0)
if __name__=='__main__':
    sel=[r for r in json.load(open(r'D:\PIU_INFINITY\channels\selection.json',encoding='utf8'))['records'] if r['channel']=='SSS']
    with ProcessPoolExecutor(6) as ex:out=list(ex.map(one,sel))
    json.dump(out,open(r'D:\SSS\bga_check.json','w'),indent=1)
    ok=[o for o in out if o['del_s'] is not None];err=np.array([o['visual_s']-o['del_s'] for o in ok])
    print('with .del',len(ok),'|visual-del|<=0.05:',(abs(err)<=.05).sum(),'<=0.1:',(abs(err)<=.1).sum(),'median err',np.median(err).round(3))
    sharp=[o for o in ok if o['second']<=0.85];e2=np.array([o['visual_s']-o['del_s'] for o in sharp]);print('sharp peaks',len(sharp),'within 0.1:',(abs(e2)<=.1).sum())
    for o in out:
        if o['del_s'] is None:print(o)
