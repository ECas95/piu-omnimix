from pathlib import Path
import inspect,json
import run_human_policy_charts as W
import generate_charts as G
G.native_nx=W.native_with_effects
text=inspect.getsource(G.run_song)
text=text.replace('records=[];grids={}', 'records=[];grids={};chart_errors=[]')
text=text.replace("target=dest/(filename+'.NX');raw,proof=native_nx(c,song['output_seconds'])", "target=dest/(filename+'.NX')\n        try:raw,proof=native_nx(c,song['output_seconds'])\n        except Exception as e:\n            chart_errors.append(dict(mode=c['mode'],level=c['meter'],signature=c['signature'],error=repr(e)));continue")
a=text.index("        if c['signature'] not in grids:");z=text.index("        record={'name':filename.lower()",a)
block=text[a:z]
text=text[:a]+"        try:\n"+''.join('    '+line+'\n' for line in block.splitlines())+"        except Exception as e:\n            chart_errors.append(dict(job=job,error=repr(e)));continue\n"+text[z:]
text=text.replace("    assert len(records)==len(song['native_pump_charts'])+len(jobs)","    complete=len(records)==len(song['native_pump_charts'])+len(jobs) and not chart_errors")
text=text.replace("    assert {(r['type'],r['tier']) for r in records}>={(m,t) for m in (0,2) for t in ('EASY','MEDIUM','HARD')}","    complete=complete and {(r['type'],r['tier']) for r in records}>={(m,t) for m in (0,2) for t in ('EASY','MEDIUM','HARD')}")
text=text.replace("'complete':True,'records':records", "'complete':complete,'chart_errors':chart_errors,'records':records")
text=text.replace("write_json(ROOT/'chart_results'/(song['song_id']+'.json'),output)","write_json(ROOT/('chart_results' if complete else 'chart_partial_results')/(song['song_id']+'.json'),output)")
exec(text,G.__dict__)
if __name__=='__main__':G.main()
