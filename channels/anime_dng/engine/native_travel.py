from pathlib import Path
import json,math
DATA=json.loads(Path(__file__).with_name('native_travel_calibration.json').read_text())
def speed(cols,level):
    band=min(26,(int(level)-1)//5*5+1);key=f'{cols}_{band}';row=DATA['bands'].get(key)
    base=5.+level*.10
    if row and row['compatible_phrases']>=20:return max(base,float(row['speed_p90'])),key
    return base,'original-low-density-bound'
def minimum_level(cols,required,estimated):
    level=int(estimated)
    while level<28 and speed(cols,level)[0]+1e-5<required:level+=1
    return level

def rhythm_level_floor(events,cols,estimated):
    # Eight fast, unheld attacks cannot stay on two fixed panels under the
    # reviewed vocabulary. An alternating foot needs at least one panel move.
    # Even the shortest distinct-panel move is sqrt(2) pitches; use the largest
    # available two-onset time as the most generous reposition opportunity.
    # This only selects an existing native difficulty band; it changes no bound.
    required=0.;worst=None
    for start in range(max(0,len(events)-7)):
        block=events[start:start+8]
        if any(e['holds'] for e in block):continue
        if any(not (0<b['beat']-a['beat']<=.50001 and 0<b['ms']-a['ms']<=400.) for a,b in zip(block,block[1:])):continue
        opportunity=max(block[i+2]['ms']-block[i]['ms'] for i in range(6))
        needed=(math.sqrt(2.)-.75)*1000./opportunity
        if needed>required:required=needed;worst={'first_index':block[0]['index'],'last_index':block[-1]['index'],'largest_two_onset_interval_ms':opportunity}
    level=minimum_level(cols,required,estimated)
    if speed(cols,level)[0]+1e-5<required:raise ValueError('Source burst exceeds the calibrated native travel bands')
    return {'level':level,'density_estimate_level':estimated,'minimum_reposition_speed':required,'worst_eight_onset_window':worst,
        'method':'reviewed eight-note diversity requires distinct-panel movement; most generous alternating-foot interval; existing native p90 bands'}
