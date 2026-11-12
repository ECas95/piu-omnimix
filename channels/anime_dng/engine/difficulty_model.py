"""Provisional level estimate from nearest native charts, not fixed tier labels."""
from pathlib import Path
import json,math
import numpy as np
ROOT=Path(__file__).resolve().parent
SOURCE=Path(r"D:\Pump It Up Data\PIU\chart_quality_research\official_chart_metrics.json")
FEATURES=("row_nps","note_nps","peak_row_1s","peak_row_4s","peak_row_8s","jump_rows","hold_heads","offbeat_rows","sixteenth_rows")
WEIGHTS=np.array([.9,.8,.4,.9,.9,.25,.25,.25,.45])
_CACHE={}
def vector(m):return np.array([math.log1p(max(0,float(m.get(k,0)))) for k in FEATURES])
def corpus(cols):
    if cols not in _CACHE:
        records=json.loads(SOURCE.read_text())["charts"];refs={}
        for r in sorted(records,key=lambda r:r["game"]!="PH"):
            if r["mode"]==(0 if cols==5 else 2):refs.setdefault((r["song"],r["mode"],r["level"]),r)
        rows=list(refs.values());x=np.array([vector(r) for r in rows]);scale=np.maximum(np.std(x,axis=0),.05)
        _CACHE[cols]=(rows,x,scale)
    return _CACHE[cols]
def estimate(m,cols,exclude_song=None):
    rows,x,scale=corpus(cols);dist=np.sum(((x-vector(m))/scale*WEIGHTS)**2,axis=1)
    if exclude_song is not None:
        dist=np.where(np.array([r["song"]==exclude_song for r in rows]),np.inf,dist)
    ix=np.argsort(dist)[:21];weights=1/(.2+np.sqrt(dist[ix]));labels=np.array([rows[i]["level"] for i in ix]);value=float(np.sum(labels*weights)/sum(weights))
    return max(1,min(28,round(value))),{"estimate":round(value,2),"provisional":True,"method":"21 nearest deduplicated official XX/PH charts; weighted log features","native_references":[{"title":rows[i]["title"],"level":rows[i]["level"],"distance":round(float(dist[i]),3)} for i in ix[:5]]}
def calibrate():
    report={}
    for cols in (5,10):
        rows,_,_=corpus(cols);sample=rows[::max(1,len(rows)//250)];errors=[abs(estimate(r,cols,r["song"])[0]-r["level"]) for r in sample]
        report[str(cols)]={"reference_charts":len(rows),"held_out_charts":len(sample),"holdout":"exclude every chart of the tested song","mean_absolute_level_error":round(float(np.mean(errors)),3),"within_two_levels":round(float(np.mean(np.array(errors)<=2)),3)}
    return report
