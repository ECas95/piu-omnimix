"""Preserve native Pump charts and run frozen V5 on DDR/missing tiers."""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import argparse, hashlib, json, os, re, sys, time, traceback
from common import *
sys.path[:0]=[str(ROOT/'engine'),str(ROOT.parent)]
import nx20, quality_charting as Q
from difficulty_model import estimate
from native_travel import minimum_level, rhythm_level_floor
from musical_policy import select_phrases
from nx_adapter import native_nx, source_grid, musical_grid

PROFILES=read_json(ROOT/'engine/official_profiles.json')['profiles']
MOTIFS=read_json(ROOT/'engine/official_phrase_motifs.json')
ADAPTER_VERSION='anime-sm-adapter-1'

def measurements(events):
    times=[e['ms'] for e in events];span=max(1,(times[-1]-times[0])/1000)
    count=sum(min(2,len(e['lanes'])) for e in events)
    return {'row_nps':len(times)/span,'note_nps':count/span,'peak_row_1s':Q._peak(times,1),
            'peak_row_4s':Q._peak(times,4),'peak_row_8s':Q._peak(times,8),
            'jump_rows':sum(len(e['lanes'])>1 for e in events)/len(times),
            'hold_heads':sum(bool(e['holds']) for e in events)/max(1,count),
            'offbeat_rows':sum(abs(e['beat']-round(e['beat']))>1e-5 for e in events)/len(times),
            'sixteenth_rows':sum(abs(e['beat']*2-round(e['beat']*2))>1e-5 for e in events)/len(times)}

def generated(source, beats, chart, job, song):
    cols=5 if job['mode']=='pump-single' else 10;tier=job['algorithm_tier']
    with musical_grid(beats,source):
        events=Q._source(source)[1];hard_level,_=estimate(measurements(events),cols)
        provisional=hard_level if tier=='HARD' else max(1,hard_level-(5 if tier=='MEDIUM' else 10))
        minimum=0. if tier=='HARD' else max(100,260-8*hard_level) if tier=='MEDIUM' else max(180,420-12*hard_level)
        chosen,_=select_phrases(events,2*len(events),{'tier':tier,'minimum_interval_ms':minimum},0,provisional)
        metrics=measurements(chosen);level,_=estimate(metrics,cols);profile_key=f'{cols}_{level}'
        if profile_key not in PROFILES:
            options=[k for k in PROFILES if k.startswith(f'{cols}_') and k.split('_')[1].isdigit()]
            profile_key=min(options,key=lambda k:(abs(int(k.split('_')[1])-level),int(k.split('_')[1])))
        profile=dict(PROFILES[profile_key])
        for metric in ('row_nps','note_nps','peak_row_1s','peak_row_4s','peak_row_8s'):
            profile[metric+'_cap']=max(metrics[metric]*(2.1 if metric=='note_nps' else 1.01),1.)
        profile.update(minimum_interval_ms=minimum,beam_width=24,rapid_jack_ratio_cap=.08)
        velocity_floor=rhythm_level_floor(chosen,cols,level);level=velocity_floor['level']
        seed=int.from_bytes(hashlib.sha256((song['song_id']+chart['signature']+str(cols)+job['label']+job['kind']+Q.VERSION).encode()).digest()[:4],'little')
        band=f'{cols}_{min(21,(level-1)//5*5+1)}';motifs=MOTIFS.get(band) or MOTIFS[f'{cols}_11']
        nx,proof=Q.generate(source,cols,level,tier,2*len(events),profile,motifs,seed)
        actual=Q._source(nx)[1];final_level,calibration=estimate(measurements(actual),cols)
        final_level=minimum_level(cols,proof['verification']['max_required_travel_speed'],final_level)
        nx['tags']=[(k,final_level if k==1001 else v) for k,v in nx['tags']]
        raw=nx20.build(nx);parsed=nx20.parse(raw)
        check=Q.validate(parsed,source,proof['footsteps'],proof['limits']);assert check['pass'],check['errors']
        rhythm=Q.rhythm_audit(events,Q._source(parsed)[1]);assert tier!='HARD' or rhythm['source_onset_coverage']==1.,rhythm
        assert tier!='HARD' or not rhythm['source_sixteenth_or_finer_onsets'] or rhythm['fine_onset_retention']==1.,rhythm
        spatial=Q.spatial_audit(Q._source(parsed)[1],cols)
        # For fewer than 13 windows an 8% maximum cannot be attained even when every window is unique.
        # spatial_audit measures consecutive SINGLE onsets; jump rows do not
        # contribute windows and cannot enlarge the denominator of its census.
        single_onsets=sum(len(e['lanes'])==1 for e in actual)
        windows=max(1,single_onsets-7);dominance_limit=max(.08,1/windows)
        assert spatial['most_common_eight_note_window_share']<=dominance_limit+1e-9,spatial
        assert len(actual)<8 or spatial['panel_entropy_normalized']>=.70,spatial
        assert max(s['head'][8]&255 for s in parsed['splits'])<=24
        proof.update(verification=check,rhythm=rhythm,spatial=spatial,sha256=hashlib.sha256(raw).hexdigest(),
                     source_signature=chart['signature'],source_file_sha256=chart['source_file_sha256'],
                     original_step_type=chart['mode'],original_difficulty=chart['difficulty'],original_meter=chart['meter'],
                     level=final_level,level_calibration=calibration,velocity_floor=velocity_floor,
                     musical_grid_beats=beats,native_profile_key=profile_key,native_motif_band=band,
                     adapter_version=ADAPTER_VERSION,job=job,short_chart_distinct_window_floor=dominance_limit,
                     spatial_single_onsets=single_onsets,spatial_single_windows=max(0,single_onsets-7))
        return raw,proof,final_level

def run_song(path):
    song=read_json(path);dest=CACHE/'chart_staging/D'/song['game_song_id']/song['game_song_id'];dest.mkdir(parents=True,exist_ok=True)
    receipts=ROOT/'chart_receipts'/song['song_id'];receipts.mkdir(parents=True,exist_ok=True)
    sources={c['signature']:c for c in song['native_pump_charts']+song['dance_sources']}
    records=[];grids={}
    from chart_exclusion_policy import effective_jobs
    policy_path=ROOT/'ddr_chart_exclusions.json'
    policy=read_json(policy_path) if policy_path.exists() else {}
    jobs,excluded,additions=effective_jobs(song,policy)
    if excluded:write_json(ROOT/'effective_chart_plans'/(song['song_id']+'.json'),{'song_id':song['song_id'],'source_plan_sha256':digest(path),'exclusion_policy_sha256':digest(policy_path),'excluded_jobs':excluded,'additional_jobs':additions,'original_source_plan_modified':False})
    for c in song['native_pump_charts']:
        mode='S' if c['mode']=='pump-single' else 'D';level=int(float(c['meter']))
        filename=f'{mode}{level}_NATIVE_{c["signature"][:12].upper()}'
        target=dest/(filename+'.NX');raw,proof=native_nx(c,song['output_seconds'])
        if target.exists():assert target.read_bytes()==raw,('Previously written native chart differs',str(target))
        else:target.write_bytes(raw)
        write_json(receipts/(filename+'.native.json'),proof)
        records.append({'name':filename.lower(),'type':0 if mode=='S' else 2,'level':level,'tier':c['tier'],
                        'origin':'native_pump','source_signature':c['signature'],'source_file_id':c['source_file_id'],
                        'path':str(target),'sha256':proof['sha256'],'notes':proof['note_count'],'proof':str(receipts/(filename+'.native.json'))})
    for index,job in jobs:
        c=sources[job['source_signature']];tag=f'{"S" if job["mode"]=="pump-single" else "D"}_{index:03}_{c["signature"][:10]}'
        receipt=receipts/(tag+'.json')
        if receipt.exists():
            old=read_json(receipt)
            if old.get('adapter_version')==ADAPTER_VERSION and old['job']==job and Path(old['record']['path']).exists() and digest(old['record']['path'])==old['record']['sha256']:
                records.append(old['record']);continue
        if c['signature'] not in grids:
            grids[c['signature']]=source_grid(c)
        source,beats,audit=grids[c['signature']]
        raw,proof,level=generated(source,beats,c,job,song)
        filename=f'{"S" if job["mode"]=="pump-single" else "D"}{level}_AUTO{re.sub("[^A-Z0-9]","",job["label"].upper())[:12]}_{index:03}'
        target=dest/(filename+'.NX');target.write_bytes(raw);proof['source_grid_audit']=audit
        record={'name':filename.lower(),'type':0 if job['mode']=='pump-single' else 2,'level':level,'tier':job['tier'],
                'origin':job['kind'],'source_signature':c['signature'],'source_file_id':c['source_file_id'],
                'path':str(target),'sha256':proof['sha256'],'notes':proof['verification']['notes'],'proof':str(receipt)}
        proof['record']=record;write_json(receipt,proof);records.append(record)
        print('CHART',song['title'],filename,record['notes'],flush=True)
    assert len(records)==len(song['native_pump_charts'])+len(jobs)
    assert {(r['type'],r['tier']) for r in records}>={(m,t) for m in (0,2) for t in ('EASY','MEDIUM','HARD')}
    output={'song_id':song['song_id'],'game_song_id':song['game_song_id'],'title':song['title'],'channel_index':song['channel_index'],
            'complete':True,'records':records,'native_charts':len(song['native_pump_charts']),'generated_charts':len(jobs),'excluded_generation_jobs':excluded,'additional_generation_jobs':additions,'final_hard_retention_revision_accepted':False}
    write_json(ROOT/'chart_results'/(song['song_id']+'.json'),output)
    return output

def main():
    p=argparse.ArgumentParser();p.add_argument('--songs',nargs='*');p.add_argument('--available',action='store_true');p.add_argument('--workers',type=int,default=3);a=p.parse_args()
    handle=lock('chart_worker.lock')
    snap=read_json(ROOT/'engine_snapshot.json')
    for name,sha in snap['files'].items():assert digest(ROOT/'engine'/name)==sha,('Frozen engine changed',name)
    paths=sorted((ROOT/'chart_sources').glob('*.json'))
    if a.songs:paths=[f for f in paths if f.stem in a.songs]
    elif a.available:
        preflight=read_json(ROOT/'source_preflight.json')
        paths=[Path(r['path']) for r in preflight['records']]
    else:
        preflight=read_json(ROOT/'source_preflight.json');assert preflight['complete'],preflight['errors']
        assert len(paths)==EXPECTED_SONGS
    records=[];errors=[];song_results=[]
    state('chart_worker_state.json','generating',songs=0,charts=0,expected_songs=len(paths),complete=False)
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        jobs={pool.submit(run_song,str(path)):path.stem for path in paths}
        for job in as_completed(jobs):
            sid=jobs[job]
            try:
                result=job.result();song_results.append({'song_id':sid,'charts':len(result['records'])});records.extend(result['records'])
            except Exception as ex:
                errors.append({'song_id':sid,'error':repr(ex),'traceback':traceback.format_exc()});print('CHART_REVIEW',sid,repr(ex),flush=True)
            state('chart_worker_state.json','generating',songs=len(song_results),charts=len(records),expected_songs=len(paths),complete=False,errors=errors)
    result={'complete':not errors and len(song_results)==len(paths) and (bool(a.songs) or len(song_results)==EXPECTED_SONGS),'songs':len(song_results),'records':records,'errors':errors,
            'adapter_version':ADAPTER_VERSION,'engine_snapshot_sha256':digest(ROOT/'engine_snapshot.json'),'pilot':bool(a.songs)}
    write_json(ROOT/('pilot_chart_manifest.json' if a.songs else 'chart_manifest.json'),result)
    state('chart_worker_state.json','generated' if result['complete'] else 'review_required',songs=len(song_results),charts=len(records),expected_songs=len(paths),complete=result['complete'],errors=errors)

if __name__=='__main__':main()
