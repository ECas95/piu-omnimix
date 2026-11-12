from pathlib import Path
import json,traceback
import native_warp_critical as N
R=Path(__file__).resolve().parent;O=R/'research/native_warp_critical';O.mkdir(parents=True,exist_ok=True);rows=json.loads((R/'human_policy_remaining_charts.json').read_text())['native_chart_failures'];results=[];seen=set()
for row in rows:
    key=(row['song_id'],row['signature'])
    if key in seen:continue
    seen.add(key);song=json.loads((R/'chart_sources'/(key[0]+'.json')).read_text());c=next(c for c in song['native_pump_charts'] if c['signature']==key[1])
    if not c['timing'].get('WARPS','').strip():continue
    try:
        raw,proof=N.convert(c,song['output_seconds']);path=O/(key[0]+'_'+key[1][:12]+'.NX');path.write_bytes(raw);path.with_suffix('.proof.json').write_text(json.dumps(proof,indent=2));result=dict(song_id=key[0],signature=key[1],title=song['title'],mode=c['mode'],level=c['meter'],pass_source=True,path=str(path),proof=str(path.with_suffix('.proof.json')))
    except Exception as e:result=dict(song_id=key[0],signature=key[1],title=song['title'],pass_source=False,error=repr(e),traceback=traceback.format_exc())
    results.append(result);print({k:v for k,v in result.items() if k!='traceback'},flush=True)
    (O/'result.json').write_text(json.dumps(dict(results=results,complete=False,promoted=False),indent=2))
(O/'result.json').write_text(json.dumps(dict(results=results,complete=True,promoted=False),indent=2))
