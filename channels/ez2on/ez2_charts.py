"""EZ2ON REBOOT : R -> PIU charts with our algorithm (same per-song pipeline as SABIN SOUND STAR, D:\SSS\sss_charts.py).
Per confirmed song (sync_final.json CONFIRMADO):
  refs   every ez2pattern chart -> reference NX on Song.mp3's timeline (ez2_refs, measured offset + start padding)
  pick   up to 4 originals with well-spread estimated levels (the frozen difficulty model); fewer than 4 distinct
         levels -> subsets of the hardest original (faithful.reductions) fill the missing tiers
  Single v363 planner on the original note times (stream chords keep one of their own notes)
  Double PumpDoublify of that Single, repaired by the playability gate; fallback: same rhythm on 10 panels
Nothing is added or moved. Output runs/<folder>/<mode>_T<k>.NX + song.json"""
from pathlib import Path
import sys,json,hashlib,time,argparse,glob,os
from concurrent.futures import ProcessPoolExecutor,as_completed
H=Path(__file__).resolve().parent;GEN=Path(r'D:\Pump It Up Data\PIU\final_generation_v362')
sys.path[:0]=[str(H),str(GEN),str(GEN/'vendor_v363'),r'D:\SSS']
sys.dont_write_bytecode=True
CH=Path(r'D:\eeez2abackup\ez2on_charts')

def refs(folder,chart,lag):
    import ez2_refs as R
    out=[]
    for js in sorted(CH.glob(f'{glob.escape(chart)}/*S_*.json')):
        raw,info=R.reference(js,lag);p=H/'refs'/folder/(js.stem+'.NX');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
        out.append(dict(song=folder,chart=js.stem,source=str(js),nx=str(p),sha256=hashlib.sha256(raw).hexdigest(),**info))
    return out

def song(job):
    import faithful as Fa,generate_nx_band as G,playability
    from hybrid import composer,sources,nx20
    from sss_charts import events_of
    from easy_hold_policy import simplify,concurrency_hold_keys
    from pumpdoublify_adapter import convert
    from generate import travel
    from doublify_doubles import strip_rows
    out=Path(job['out']);out.mkdir(parents=True,exist_ok=True)
    if (out/'song.json').exists():return json.loads((out/'song.json').read_text())
    t0=time.time();res=dict(song=job['song'],charts=[],errors=[])
    try:
        rs=refs(job['song'],job['chart'],job['lag']);res['refs']=rs
        est=lambda evs,origin:G.MODEL.estimate(G.metrics([dict(e,lanes=e['lanes'][:2]) for e in evs],origin),5)[0]
        cand=[]
        for r in rs:
            src,origin,ev=events_of(Path(r['nx']).read_bytes(),nx20,sources,simplify,concurrency_hold_keys)
            ev=Fa.stream_chords_to_single(ev);cand.append(dict(lv=est(ev,origin),name='original '+r['chart'],evs=ev,src=src,origin=origin,ref=r))
        pick=[]   # spread: hardest first, then the level farthest from those taken (ties -> fewer lanes, closer to 5 panels)
        for c in sorted(cand,key=lambda c:(-c['lv'],abs(c['ref']['notes']))):
            if len(pick)>=4:break
            if all(abs(c['lv']-p['lv'])>=2 for p in pick):pick.append(c)
        hard=max(cand,key=lambda p:(p['lv'],len(p['evs'])))
        if len({p['lv'] for p in pick})<4:
            cands,_=Fa.reductions(hard['evs']);taken={p['lv'] for p in pick}
            extra=sorted({est(e,hard['origin']):(n,e) for n,e in cands if n!='full'}.items())
            while len(taken)<4 and extra:
                lv,(n,e)=max(((lv,x) for lv,x in extra if lv not in taken),key=lambda x:min(abs(x[0]-t) for t in taken),default=(None,None))
                if lv is None:break
                pick.append(dict(hard,lv=lv,name='subset of '+hard['ref']['chart']+' '+n,evs=e));taken.add(lv);extra=[x for x in extra if x[0]!=lv]
        pick.sort(key=lambda p:(p['lv'],len(p['evs'])))
        seed=int.from_bytes(hashlib.sha256(job['song'].encode()).digest()[:4],'little')
        for tier,p in enumerate(pick):
            _,w=Fa.reductions(p['evs']);evs=Fa.chords_for_easy(p['evs'],w,p['lv'])
            chart,meta=Fa.plan(evs,p['src'],5,p['lv'],seed+tier,composer,sources,playability,travel)
            if chart is None:res['errors'].append(dict(mode='Single',tier=tier,chart=p['name'],error=meta));continue
            res['charts'].append(dict(Fa.save(out,'Single',tier,p['name'],chart,meta,dict(file=p['ref']['nx']),G,nx20,sources,p['origin'],len(p['evs']),len(evs)),source_chart=p['ref']['chart']))
            try:
                single=chart;repaired=[]
                for attempt in range(10):
                    dbl,_,_=convert(single,level=max(3,meta['level']),seed=seed+tier,beam=32,verify=False)
                    g=playability.gate(sources.events_of(dbl)[1],10,4)
                    if g['pass'] or not g['problem_ms']:break
                    single,removed=strip_rows(single,g['problem_ms']);repaired+=removed
                if not g['pass']:raise ValueError('doublify gate')
                dchart,dmeta=dbl,dict(meta,method='PumpDoublify of the faithful Single',gate=g,omitted_conflicts=meta.get('omitted_conflicts',[])+repaired)
            except Exception:
                _,sev=sources.events_of(chart)
                dchart,dmeta=Fa.plan(sev,chart,10,meta['level'],seed+tier+99,composer,sources,playability,travel)
                if dchart is None:res['errors'].append(dict(mode='Double',tier=tier,chart=p['name'],error=dmeta));continue
                dmeta['method']='same faithful rhythm composed on 10 panels (PumpDoublify failed)'
            res['charts'].append(dict(Fa.save(out,'Double',tier,p['name'],dchart,dmeta,dict(file=p['ref']['nx']),G,nx20,sources,p['origin'],len(p['evs']),None),source_chart=p['ref']['chart']))
    except Exception as e:res['errors'].append(dict(error=repr(e)[:300]))
    res['seconds']=time.time()-t0;(out/'song.json').write_text(json.dumps(res,indent=1));return res

def main():
    a=argparse.ArgumentParser();a.add_argument('--workers',type=int,default=6);a.add_argument('--songs',nargs='*');a=a.parse_args()
    d=json.loads((H/'sync_final.json').read_text(encoding='utf8'))
    jobs=[dict(song=k,chart=v['chart'],lag=v['lag_ms']+v['pad_ms'],out=str(H/'runs'/k)) for k,v in d.items() if v['status'] in ('CONFIRMADO','CONFIRMADO_VIDEO') and (not a.songs or k in a.songs)]
    done=0;t=time.time()
    with ProcessPoolExecutor(a.workers) as ex:
        for f in as_completed([ex.submit(song,j) for j in jobs]):
            r=f.result();done+=1;print('EZ2_SONG',done,len(jobs),r['song'],len(r['charts']),'charts',len(r['errors']),'errors','%.0fs'%(time.time()-t),flush=True)
    print('EZ2_CHARTS_FINISHED',done,flush=True)
if __name__=='__main__':main()
