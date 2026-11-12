"""Full IIDX channel conversion: every song of inventario_bga_propios.csv -> reference NX, audio mix, 8 F charts. Resumable (songs/<id>/result.json).
E: is only read; the copied source of a song is deleted once done, except its official preview (preview.wav).
usage: convertir_todo.py [--workers 8] [--limit N] [ids...]"""
import os
os.environ['PIU_VARIANT']='F';os.environ['PIU_IIDX_OUT']='canal'
import sys,csv,json,time,shutil,struct,subprocess,argparse,traceback
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H))
import iidx

def one(job):
    sid,meta=job;work=iidx.OUT/'songs'/str(sid);done=work/'result.json';t=time.time()
    if done.exists():return json.loads(done.read_text(encoding='utf8'))
    r=dict(id=sid,title=meta['title'],ascii=meta['ascii'],artist=meta['artist'],genre=meta['genre'],bga=meta['bga'],delay=meta['delay'],charts=[],errors=[])
    try:
        work.mkdir(parents=True,exist_ok=True);refs,a=iidx.prepare(sid,meta);p=json.loads((work/'prepare.json').read_text())
        r.update(refs=refs,arreglos=p.get('arreglos'),hardest=p.get('hardest'))
        d=iidx.OUT/'src'/str(sid);pre=d/f'{sid:05d}_pre.2dx'
        if pre.exists():
            c,st=iidx.preview_check(sid);r.update(preview_corr=c,sample_start=max(0.,st))
            raw=pre.read_bytes();o=struct.unpack_from('<I',raw,0x48)[0];(work/'preview.wav').write_bytes(raw[o+24:o+24+struct.unpack_from('<I',raw,o+8)[0]])
        res=iidx.charts_job(sid,refs);r['charts']=res['charts'];r['errors']=res['errors']
    except Exception as e:r['errors'].append(dict(error=repr(e)[:400],trace=traceback.format_exc()[-400:]))
    r['seconds']=round(time.time()-t)
    if r['charts']:   # a failed song stays retryable
        done.write_text(json.dumps(r,ensure_ascii=False,indent=1),encoding='utf8');shutil.rmtree(iidx.OUT/'src'/str(sid),ignore_errors=True)
    else:(work/'error.json').write_text(json.dumps(r,ensure_ascii=False,indent=1),encoding='utf8')
    return r

def main():
    a=argparse.ArgumentParser();a.add_argument('--workers',type=int,default=8);a.add_argument('--limit',type=int);a.add_argument('ids',nargs='*',type=int);a=a.parse_args()
    D=iidx.db();rows=list(csv.DictReader(open(H/'inventario_bga_propios.csv',encoding='utf-8-sig')));ids=a.ids or [int(r['id']) for r in rows]
    if a.limit:ids=ids[:a.limit]
    t=time.time();n=0;bad=[];charts=0
    with ProcessPoolExecutor(a.workers) as ex:
        fut={ex.submit(one,(s,D[s])):s for s in ids}
        for f in as_completed(fut):
            s=fut[f];n+=1
            try:r=f.result()
            except Exception as e:r=dict(id=s,charts=[],errors=[dict(error=repr(e)[:300])])
            charts+=len(r['charts'])
            if not r['charts'] or r['errors']:bad.append(dict(id=s,title=r.get('ascii'),errors=str(r['errors'])[:300]));print('PROBLEM',s,r.get('ascii'),str(r['errors'])[:300],flush=True)
            if n%25==0 or n==len(ids):print('PROGRESS',n,len(ids),'charts',charts,'problems',len(bad),'%.0fs'%(time.time()-t),flush=True)
    (iidx.OUT/'problemas.json').write_text(json.dumps(bad,ensure_ascii=False,indent=1),encoding='utf8');print('CONVERT_DONE',n,'charts',charts,'problems',len(bad),'%.0fs'%(time.time()-t),flush=True)
if __name__=='__main__':main()
