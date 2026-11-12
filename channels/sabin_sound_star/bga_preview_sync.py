"""SSS BGA start from the game's own preview movies (movie/preview/<song>.bik = video + audio muxed, so in sync):
  v = where the preview's frames sit inside the full BGA (.bik)        (frame matching)
  a = where the preview's audio sits inside our Song audio (audio/*.wav) (64-band spectrum NCC)
  -> BGA frame 0 plays at Song time a - v. Validated against the songs that have the game's .del."""
import json,os,sys,subprocess,tempfile,numpy as np
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0,r'D:\EZ2ON_PIU');import measure_sync as M,preview_sync as P
PRE=r'E:\ARCADES\EZ2\3S\Sabin Sound Star - Renascence Burst\Game Data\movie\preview'
def one(r):
    b=r['video_segments'][0]['file'];stem=os.path.splitext(os.path.basename(b))[0];d=b[:-4]+'.del'
    dl=int(open(d).read().strip())/1000 if os.path.exists(d) else None
    pv=next((os.path.join(PRE,f) for f in os.listdir(PRE) if f.lower()==stem.lower()+'.bik'),None)
    if not pv:return dict(song=r['source_folder'],del_s=dl,error='no preview')
    wav=os.path.join(tempfile.gettempdir(),f'sss_prev_{stem}.wav')
    subprocess.run([M.FF,'-v','error','-y','-i',pv,'-vn','-ac','1','-ar','22050',wav],check=True)
    v,ev,ev2=P.locate_video(pv,b);a,ar=P.locate_audio(wav,r['audio'],maxs=40)
    return dict(song=r['source_folder'],title=r['title'],del_s=dl,start_s=round(a-v,3),video_at=v,video_err=round(ev,2),video_err_2nd=round(ev2,2),audio_at=round(a,3),audio_2nd=round(ar,3))
if __name__=='__main__':
    sel=[r for r in json.load(open(r'D:\PIU_INFINITY\channels\selection.json',encoding='utf8'))['records'] if r['channel']=='SSS']
    with ProcessPoolExecutor(6) as ex:out=list(ex.map(one,sel))
    json.dump(out,open(r'D:\SSS\bga_preview_sync.json','w'),indent=1)
    ok=[o for o in out if o.get('del_s') is not None and 'start_s' in o];e=np.array([o['start_s']-o['del_s'] for o in ok])
    print('validated on',len(ok),'| within 0.05 s:',(abs(e)<=.05).sum(),'| 0.1 s:',(abs(e)<=.1).sum(),'| median err',np.median(e).round(3))
    for o in out:
        if o.get('del_s') is None:print(o)
