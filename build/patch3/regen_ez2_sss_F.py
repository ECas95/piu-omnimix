"""PATCH 3, EZ2ON + SABIN SOUND STAR: regenerates every installed chart of those channels (selection.json, generated
charts) with variant F through their own generators (ez2_charts / sss_charts via ssc_export/regen_ssc.job_for), applies the
same lead-in shift the installed EZ2ON chart had, and writes ez2_sss_F.json: game path -> new NX, read by build_patch3.py.
Songs already generated are reused (resumable)."""
import os;os.environ['PIU_VARIANT']='F'   # before the workers spawn
from pathlib import Path
import sys,json,re,ast
from concurrent.futures import ProcessPoolExecutor,as_completed
HERE=Path(__file__).resolve().parent;sys.path.insert(0,r'D:\Pump It Up Data\PIU\ssc_export')
import regen_ssc as R

def main():
    sel=[r for r in json.loads(R.SEL.read_text(encoding='utf8'))['records'] if r['channel'] in ('EZ2ON','SSS') and not r.get('media_only')]
    recs={r['game_song_id']:r for r in sel};out=[];missing=[];dst=HERE/'ez2_sss';dst.mkdir(exist_ok=True)
    jobs=[R.job_for(r['channel'],r['game_song_id'],'vF_full_01',recs) for r in sel];done=0
    with ProcessPoolExecutor(int(sys.argv[1]) if sys.argv[1:] else 8) as ex:
        for f in as_completed([ex.submit(R.run_job,j) for j in jobs]):
            j,res=f.result();done+=1;r=recs[j['gid']];gid=int(j['gid'],16)
            new={Path(c['nx']).name:Path(c['nx']) for c in res['charts']}
            for c in (r['charts'] if isinstance(r['charts'],list) else ast.literal_eval(r['charts'])):
                if not c.get('generated'):continue
                base=re.sub(r'^\d+_','',Path(c['nx']).name);path=f'/D/{gid:X}/{gid:X}/{c["name"]}.NX'
                if base not in new:missing.append(dict(path=path,reason='not regenerated'));continue
                raw=new[base].read_bytes()
                if j.get('lead') and Path(c['nx']).parent.name=='lead':import leadin;raw=leadin.shift(raw,j['lead'])
                f2=dst/f"{j['gid']}_{c['name']}.NX";f2.write_bytes(raw);out.append(dict(path=path,nx=str(f2),installed=c['nx'],mode=c['mode'],level=c['level']))
            if done%25==0:print('EZ2SSS_PROGRESS',done,len(jobs),flush=True)
    (HERE/'ez2_sss_F.json').write_text(json.dumps(dict(charts=out,missing=missing),indent=1),encoding='utf8')
    print('EZ2SSS_DONE',len(out),'charts',len(missing),'missing',flush=True)

if __name__=='__main__':main()
