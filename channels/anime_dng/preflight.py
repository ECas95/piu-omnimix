"""Parse every selected chart without media rewrites; preserve all source definitions."""
import json, os, traceback
from pathlib import Path
from collections import Counter
from common import *
import simfile as SM

def tier(c):
    return {'beginner':'EASY','easy':'EASY','medium':'MEDIUM','hard':'HARD','challenge':'HARD','edit':'HARD'}.get(c['difficulty'].casefold(),'HARD')

def main():
    handle=lock('preflight.lock');reader=SM.Reader()
    selection=read_json(INVENTORY/'selected_manifest.json')['selected']
    discovery=read_json(INVENTORY/'discovery.json');files={f['id']:f for f in discovery['files']};all_songs={s['id']:s for s in discovery['songs']}
    probes=read_json(INVENTORY/'media_index.json')['records'];mapping=read_json(ROOT/'channel_plan.json')['song_mapping']
    parsed_cache={};records=[];errors=[];donor_review=[]
    def charts_of(song):
        charts={}
        for source in sorted(song['chart_files'],key=lambda c:c['format']!='.ssc'):
            fid=source['id']
            if source['format']=='.dwi':continue # SM/SSC definitions are present for all selected entries.
            if fid not in parsed_cache:
                raw=reader.read(files[fid]);meta,cc=SM.parse(raw,source['encoding'],source['format'])
                for c in cc:c.update(source_file_id=fid,source_file_sha256=__import__('hashlib').sha256(raw).hexdigest(),song_metadata=meta)
                parsed_cache[fid]=cc
            for c in parsed_cache[fid]:
                if c['signature'] not in charts:charts[c['signature']]=dict(c,source_alias_ids=[fid])
                elif fid not in charts[c['signature']]['source_alias_ids']:charts[c['signature']]['source_alias_ids'].append(fid)
        return list(charts.values())
    for i,s in enumerate(selection):
        out=ROOT/'chart_sources'/(s['id']+'.json')
        try:
            if out.exists():
                record=read_json(out)
                assert record['selected_audio_id']==s['selected_audio_id']
                assert record['selected_video_id']==s['selected_video_id']
                assert record['game_song_id']==mapping[s['id']]['game_song_id']
                assert record['channel_index']==mapping[s['id']]['channel_index']
                records.append({'song_id':s['id'],'title':s['title'],'path':str(out),
                    'native_charts':len(record['native_pump_charts']),'generated_charts':len(record['generation_jobs']),
                    'channel_index':record['channel_index'],'output_seconds':record['output_seconds']})
                continue
            charts=charts_of(s);native=[c for c in charts if c['mode'].startswith('pump-')]
            for donor_id in s['native_pump_donor_ids']:
                donor=all_songs[donor_id];assert s['pack']!='PACK5' or donor['pack']=='PACK5'
                matches=[a['id'] for a in donor['audio_candidates'] if probes.get(a['id'],{}).get('sha256')==probes[s['selected_audio_id']]['sha256']]
                if not matches:
                    donor_review.append({'song_id':s['id'],'donor_id':donor_id,'reason':'Native Pump alternative audio differs; do not shift/rewrite original chart or assume synchronization'})
                    continue
                for c in charts_of(donor):
                    if c['mode'].startswith('pump-') and c['signature'] not in {v['signature'] for v in native}:
                        native.append(dict(c,donor_song_id=donor_id))
            dance=[c for c in charts if c['mode'].startswith('dance-')]
            if not native and not dance:raise ValueError('No playable Pump/DDR chart definitions')
            natives=[];adapt=[];max_note=0
            for c in native+dance:
                notes,ignored=SM.events(c,native=c in native)
                if not notes:continue
                max_note=max(max_note,max(n['tail_ms'] or n['ms'] for n in notes)/1000)
                item={**c,'attack_events':notes,'non_attack_audit':ignored,'tier':tier(c)}
                (natives if c in native else adapt).append(item)
            if not natives and not adapt:raise ValueError('Source contains no judgable attacks')
            have={(c['mode'],c['tier']) for c in natives};native_have=set(have)
            # Adapt every distinct DDR source chart into its corresponding Pump mode.
            # Native Pump tiers take precedence; DDR copies do not replace them.
            jobs=[]
            for c in adapt:
                mode='pump-double' if c['mode'] in {'dance-double','dance-couple'} else 'pump-single'
                if (mode,c['tier']) in native_have:continue
                jobs.append({'kind':'adapt_ddr','source_signature':c['signature'],'mode':mode,'label':c['difficulty'] or 'EDIT',
                             'tier':c['tier'],'algorithm_tier':'HARD'})
                have.add((mode,c['tier']))
            sources=natives+adapt
            def strength(c):
                rank={'beginner':0,'easy':1,'medium':2,'hard':3,'challenge':4,'edit':4}
                return (rank.get(c['difficulty'].casefold(),3),len(c['attack_events']))
            hardest=max(sources,key=strength)
            for mode in ('pump-single','pump-double'):
                for t in ('EASY','MEDIUM','HARD'):
                    if (mode,t) not in have:
                        jobs.append({'kind':'fill_missing','source_signature':hardest['signature'],'mode':mode,'label':t,'tier':t,'algorithm_tier':t})
                        have.add((mode,t))
            audio_seconds=probes[s['selected_audio_id']]['duration']
            record={'song_id':s['id'],'title':s['title'],'artist':s['artist'],'pack':s['pack'],**mapping[s['id']],
                    'native_pump_charts':natives,'dance_sources':adapt,'generation_jobs':jobs,
                    'selected_audio_id':s['selected_audio_id'],'selected_video_id':s['selected_video_id'],
                    'audio_source_seconds':audio_seconds,'output_seconds':max(audio_seconds,max_note+1),
                    'added_trailing_silence_seconds':max(0,max_note+1-audio_seconds),'native_layout_timing_unchanged':True}
            write_json(out,record)
            records.append({'song_id':s['id'],'title':s['title'],'path':str(out),'native_charts':len(natives),'generated_charts':len(jobs),
                            'channel_index':record['channel_index'],'output_seconds':record['output_seconds']})
        except Exception as ex:
            errors.append({'song_id':s['id'],'title':s['title'],'error':repr(ex),'traceback':traceback.format_exc()})
            print('PREFLIGHT_ERROR',s['title'],repr(ex),flush=True)
        if i%25==0:
            state('preflight_state.json','parsing',songs_checked=i+1,expected_songs=len(selection),errors=len(errors));print('PARSED',i+1,'/',len(selection),flush=True)
    reader.close()
    report={'complete':not errors and len(records)==EXPECTED_SONGS,'records':records,'errors':errors,'native_donor_audio_review':donor_review,
            'source_selection_sha256':digest(INVENTORY/'selected_manifest.json'),'expected_songs':EXPECTED_SONGS,
            'expected_native_charts':sum(r['native_charts'] for r in records),'expected_generated_charts':sum(r['generated_charts'] for r in records),
            'original_sources_modified':False,'game_launched':False}
    write_json(ROOT/'source_preflight.json',report)
    state('preflight_state.json','complete' if report['complete'] else 'source_review_required',songs_checked=len(records),errors=errors)
    print('PREFLIGHT',len(records),'SONGS',report['expected_native_charts'],'NATIVE',report['expected_generated_charts'],'GENERATED',len(errors),'ERRORS',flush=True)

if __name__=='__main__':main()
