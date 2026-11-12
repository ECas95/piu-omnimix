"""Musical structure policies; onset selection is separate from panel assignment."""
from collections import Counter,defaultdict
import math,random
from pattern_rules import curated_pool

def select_phrases(events,target,limits,seed,level):
    if limits.get("tier")=="HARD":
        return list(events),max(int(target),len(events))
    tier=limits.get("tier","MEDIUM");groups=defaultdict(list)
    for e in events:groups[int(e["beat"]//4)].append(e)
    # Simplify a whole rhythmic phrase on a consistent subdivision. Never rank
    # isolated accents and silently break every sixteenth-note run into eighths.
    desired=.38 if tier=="EASY" else .72
    selected=[]
    for number,group in sorted(groups.items()):
        candidates=[]
        for subdivision in (1,2,3,4,6,8,12,16,24):
            chosen=[e for e in group if abs(e["beat"]*subdivision-round(e["beat"]*subdivision))<1e-4]
            if not chosen:continue
            gaps=[b["ms"]-a["ms"] for a,b in zip(chosen,chosen[1:])]
            if gaps and min(gaps)<limits["minimum_interval_ms"]-1e-5:continue
            coverage=len(chosen)/len(group)
            cost=abs(coverage-desired)+.001*subdivision
            candidates.append((cost,subdivision,chosen))
        if candidates:chosen=min(candidates,key=lambda x:(x[0],x[1]))[2]
        else:chosen=[group[0]]
        # Medium keeps complete short bursts when its physical interval allows,
        # preserving their musical shape instead of taking alternating notes.
        if tier=="MEDIUM":
            runs=[];run=[group[0]]
            for e in group[1:]:
                if e["beat"]-run[-1]["beat"]<=.25001:run.append(e)
                else:runs.append(run);run=[e]
            runs.append(run)
            for run in runs:
                if 3<=len(run)<=8 and all(b["ms"]-a["ms"]>=limits["minimum_interval_ms"] for a,b in zip(run,run[1:])):
                    chosen=list({e["index"]:e for e in chosen+run}.values())
        selected.extend(chosen)
    selected.sort(key=lambda e:e["index"])
    # At phrase boundaries use the same explicit minimum interval. No invented
    # onsets, no global target quota, and no quantization of surviving notes.
    out=[]
    for e in selected:
        if not out or e["ms"]-out[-1]["ms"]>=limits["minimum_interval_ms"]-1e-5:out.append(e)
    return out,max(int(target),len(out))

def phrase_preferences(events,cols,motifs,seed):
    pool=[m for m in motifs or [] if len(m.get("lanes",[])) in (8,12) and all(0<=l<cols for l in m["lanes"])]
    if not pool:raise ValueError("Long native phrase library is required")
    rng=random.Random(seed);preferred=[];used=Counter();last=None;blocks=0
    mirror=[4,3,2,1,0] if cols==5 else [9,8,7,6,5,4,3,2,1,0]
    # The seed differs by song/mode/tier; repeated rhythm never maps to one
    # cached four-note loop. Penalize phrase reuse within this chart.
    indexed=defaultdict(list)
    for m in pool:indexed[len(m["lanes"])].append(m)
    while len(preferred)<len(events):
        begin=len(preferred);size=12 if rng.random()<.4 and len(events)-begin>=12 else 8
        block=events[begin:begin+size]
        if len(block)<size:
            tail=last or pool[rng.randrange(len(pool))]["lanes"]
            preferred.extend(tail[:len(block)]);break
        gaps=[round(b["beat"]-a["beat"],4) for a,b in zip(block,block[1:])]
        vocabulary=curated_pool(cols,size) if max(gaps,default=1)<=.50001 else []
        # Mix reviewed visual vocabulary with official longer phrases. Geometry
        # and hold anchors remain checked by the assigning beam, never bypassed.
        candidate_pool=vocabulary if vocabulary and rng.random()<.55 else indexed.get(size,indexed[8])
        scored=[]
        for m in candidate_pool:
            if len(m["gaps"])!=len(gaps):continue
            distance=sum(abs(math.log((a+.05)/(b+.05))) for a,b in zip(m["gaps"],gaps))/len(gaps)
            identity=tuple(m["lanes"])
            scored.append((distance+.22*used[identity]+rng.random()*.08,m))
        scored.sort(key=lambda x:x[0]);choices=scored[:40]
        # Flatten corpus frequencies so extremely common patterns cannot dominate.
        m=rng.choices([m for _,m in choices],weights=[math.sqrt(1+math.log1p(m.get("count",1)))*math.exp(-2*d) for d,m in choices])[0]
        used[tuple(m["lanes"])]+=1
        lanes=list(m["lanes"])
        if rng.getrandbits(1):lanes=[mirror[l] for l in lanes]
        preferred.extend(lanes);last=lanes;blocks+=1
    return preferred,blocks

def rhythm_audit(source,output):
    source={e["index"]:e for e in source};kept={e["index"] for e in output}
    source_fine={i for i,e in source.items() if abs(e["beat"]*2-round(e["beat"]*2))>1e-5}
    seq=sorted(source.values(),key=lambda e:e["index"]);pairs=[(a,b) for a,b in zip(seq,seq[1:]) if 0<b["beat"]-a["beat"]<=.25001]
    return {"source_onsets":len(source),"output_onsets":len(kept),"source_onset_coverage":len(kept&source.keys())/max(1,len(source)),"source_sixteenth_or_finer_onsets":len(source_fine),"retained_sixteenth_or_finer_onsets":len(source_fine&kept),"fine_onset_retention":len(source_fine&kept)/max(1,len(source_fine)),"source_fast_adjacent_pairs":len(pairs),"retained_fast_adjacent_pairs":sum(a["index"] in kept and b["index"] in kept for a,b in pairs)}

def spatial_audit(events,cols):
    singles=[e["lanes"][0] for e in events if len(e["lanes"])==1]
    hist=Counter(singles);patterns=Counter(tuple(singles[i:i+8]) for i in range(max(0,len(singles)-7)))
    total=sum(hist.values());entropy=-sum((n/total)*math.log2(n/total) for n in hist.values()) if total else 0
    return {"used_panels":len(hist),"panel_entropy_normalized":entropy/math.log2(cols),"distinct_eight_note_windows":len(patterns),"most_common_eight_note_window_share":max(patterns.values(),default=0)/max(1,sum(patterns.values())),"top_eight_note_windows":[{"lanes":k,"count":n} for k,n in patterns.most_common(8)]}
