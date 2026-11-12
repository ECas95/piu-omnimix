"""SSS Percussion -> PIU charts with the v366 faithful algorithm (user 2026-10-29: "similar a DJMax").
Per song: every original Percussion difficulty -> one Single (all its original note times; panels by the v363
planner; DJMAX chord rule: chords inside streams keep one of their own notes) + its Double (PumpDoublify, repaired
by the gate; fallback: same rhythm on 10 panels). Fewer than 4 distinct levels -> subsets of the hardest original
(faithful.reductions) fill the missing tiers. Nothing is added or moved. Output runs/<song>/<mode>_T<k>.NX."""
from pathlib import Path
import sys,json,hashlib,time,argparse,collections
from concurrent.futures import ProcessPoolExecutor,as_completed
H=Path(__file__).resolve().parent;GEN=Path(r'D:\Pump It Up Data\PIU\final_generation_v362')
sys.path[:0]=[str(GEN),str(GEN/'vendor_v363')]
sys.dont_write_bytecode=True

def events_of(raw,nx20,sources,simplify,concurrency_hold_keys):
    src=nx20.parse(raw);keys=concurrency_hold_keys(src)
    src,_=simplify(src,keys,band=4,verify=False,structural=keys)   # 3rd simultaneous hold -> tap (two feet)
    tl,ev=sources.events_of(src);return src,tl[0][0],ev

def song(job):
    import faithful as Fa,generate_nx_band as G,playability
    from hybrid import composer,sources,nx20
    from easy_hold_policy import simplify,concurrency_hold_keys
    from pumpdoublify_adapter import convert
    from generate import travel
    from doublify_doubles import strip_rows
    out=Path(job['out']);out.mkdir(parents=True,exist_ok=True)
    if (out/'song.json').exists() and (cached:=json.loads((out/'song.json').read_text()))['charts']:return cached   # a song with no charts is retried, not reused
    t0=time.time();res=dict(song=job['song'],charts=[],errors=[])
    try:
        est=lambda evs,origin:G.MODEL.estimate(G.metrics([dict(e,lanes=e['lanes'][:2]) for e in evs],origin),5)[0]
        pick=[]
        for r in job['refs']:
            src,origin,ev=events_of(Path(r['nx']).read_bytes(),nx20,sources,simplify,concurrency_hold_keys)
            ev=Fa.stream_chords_to_single(ev);pick.append(dict(lv=est(ev,origin),name='original '+r['chart'],evs=ev,src=src,origin=origin,ref=r))
        hard=max(pick,key=lambda p:(p['lv'],len(p['evs'])))
        if len({p['lv'] for p in pick})<4:   # fill with subsets of the hardest original, farthest from the levels taken
            cands,_=Fa.reductions(hard['evs']);taken={p['lv'] for p in pick}
            extra=sorted({est(e,hard['origin']):(n,e) for n,e in cands if n!='full'}.items())
            while len(taken)<4 and extra:
                lv,(n,e)=max(((lv,x) for lv,x in extra if lv not in taken),key=lambda x:min(abs(x[0]-t) for t in taken),default=(None,(None,None)))
                if lv is None:break
                pick.append(dict(hard,lv=lv,name='subset of '+hard['ref']['chart']+' '+n,evs=e));taken.add(lv);extra=[x for x in extra if x[0]!=lv]
        pick.sort(key=lambda p:(p['lv'],len(p['evs'])))
        seed=int.from_bytes(hashlib.sha256(job['song'].encode()).digest()[:4],'little')
        for tier,p in enumerate(pick):
            _,w=Fa.reductions(p['evs']);evs=Fa.chords_for_easy(p['evs'],w,p['lv'])
            chart,meta=Fa.plan(evs,p['src'],5,p['lv'],seed+tier,composer,sources,playability,travel)
            if chart is None:res['errors'].append(dict(mode='Single',tier=tier,chart=p['name'],error=meta));continue
            res['charts'].append(dict(Fa.save(out,'Single',tier,p['name'],chart,meta,dict(file=p['ref']['nx']),G,nx20,sources,p['origin'],len(p['evs']),len(evs)),source_chart=p['ref']['chart']))
            try:   # Double = PumpDoublify of this Single, flagged spots removed from the Single input (same as faithful.py)
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
    a=argparse.ArgumentParser();a.add_argument('--workers',type=int,default=8);a.add_argument('--songs',nargs='*');a=a.parse_args()
    refs=collections.defaultdict(list)
    for r in json.loads((H/'refs.json').read_text())['records']:refs[r['song']].append(r)
    jobs=[dict(song=s,refs=rs,out=str(H/'runs'/s)) for s,rs in refs.items() if not a.songs or s in a.songs];done=0;t=time.time()
    with ProcessPoolExecutor(a.workers) as ex:
        for f in as_completed([ex.submit(song,j) for j in jobs]):
            r=f.result();done+=1;print('SSS_SONG',done,len(jobs),r['song'],len(r['charts']),'charts',len(r['errors']),'errors','%.0fs'%(time.time()-t),flush=True)
    print('SSS_CHARTS_FINISHED',done,flush=True)
if __name__=='__main__':main()
