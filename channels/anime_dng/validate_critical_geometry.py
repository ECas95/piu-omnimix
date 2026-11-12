"""Focused native scroll geometry against the independent source beat clock.

This never opens the game loop, writes images or promotes chart files.
"""
from pathlib import Path
from fractions import Fraction as F
import bisect,hashlib,json,re,subprocess
import simfile as SM
from nx_adapter import nx20

R=Path(__file__).resolve().parent
O=R/'research/native_critical_events'
C=Path('C:\Users\USER/.codex/workspaces/anime_channel_cache/native_build/native_critical_revision')

def source_beat(clock,ms):
    points=sorted({F(0)}|{b for b,v in clock.bpms})
    times=[clock.seconds(b)*1000 for b in points]
    i=max(0,bisect.bisect_right(times,ms)-1)
    return float(points[i])+(ms-times[i])*clock.bpm(points[i])/60000

def main():
    rows=json.loads((O/'result.json').read_text())['results'];results=[]
    for row in rows:
        if not row['pass_source']:continue
        path=Path(row['path']);raw=path.read_bytes();proof=json.loads(Path(row['proof']).read_text())
        assert hashlib.sha256(raw).hexdigest()==proof['sha256']
        song=json.loads((R/'chart_sources'/(row['song_id']+'.json')).read_text())
        c=next(c for c in song['native_pump_charts'] if c['signature']==row['signature'])
        clock=SM.Clock(c['timing']);assert not clock.stops and not clock.delays and not clock.warps
        scrolls=SM.pairs(c['timing'].get('SCROLLS','')) or [(F(0),1.)]
        splits=nx20.parse(raw)['splits'];samples=[]
        for first,last in zip(splits,splits[1:]):
            a=first['head'][3];z=last['head'][3]
            if z-a<.1:continue
            samples.extend(a+(z-a)*part for part in [.1,.5,.9])
        samplepath=C/(path.name+'.geometry.samples')
        samplepath.write_text('\n'.join(format(ms,'.12g') for ms in sorted(samples)))
        p=subprocess.run(['wsl','-d','Ubuntu','-u','root','--','chroot','/mnt/piu-anime-native-validation','/mnt/native_build/probe_native_geometry_samples','/mnt/native_build/full_validation_engine','/mnt/native_build/native_critical_revision/'+path.name,'/mnt/native_build/native_critical_revision/'+samplepath.name],capture_output=True,text=True,cwd=R)
        (O/(path.name+'.geometry.log')).write_text(p.stdout+'\n'+p.stderr)
        actual=[tuple(map(float,m)) for m in re.findall(r'^GEOM ([-\d.e+]+) ([-\d.e+]+) start=([-\d.e+]+)',p.stdout,re.M)]
        errors=[]
        for ms,distance,start in actual:
            a=source_beat(clock,start);b=source_beat(clock,ms)
            # Native row starts round to float32: choose the source SCROLLS
            # segment at the sample rather than one ulp before its marker.
            values=[v for beat,v in scrolls if float(beat)<=b]
            scroll=values[-1] if values else scrolls[0][1]
            expected=-(b-a)*scroll;errors.append(abs(distance-expected))
        maximum=max(errors,default=999.)
        result={k:row[k] for k in ['song_id','signature','title','mode','level']}
        result.update(pass_native_source_geometry=p.returncode==0 and len(actual)==len(samples) and maximum<.002,samples=len(actual),expected_samples=len(samples),maximum_scroll_beat_error=maximum,sha256=proof['sha256'],promoted=False)
        results.append(result);print(result,flush=True)
        (O/'native_geometry_result.json').write_text(json.dumps(dict(results=results,complete=False,promoted=False),indent=2))
    (O/'native_geometry_result.json').write_text(json.dumps(dict(results=results,complete=True,promoted=False,game_entrypoint='never',scope='Native within-row geometry versus source BPMS/SCROLLS. Full GPU render/manual playtest remains pending.'),indent=2))

if __name__=='__main__':main()
