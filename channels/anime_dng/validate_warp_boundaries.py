"""Focused warp boundary branch selection and loaded-distance accounting.

Does not call the renderer, open the game, modify an image or promote charts.
"""
from pathlib import Path
from fractions import Fraction as F
import sys,json,hashlib,struct,subprocess,re,shutil,math
import simfile as SM
from validate_warp_geometry import source_beat
R=Path(__file__).resolve().parent;O=R/'research/native_warp_critical'
C=Path(r'C:\Users\USER\.codex\workspaces\anime_channel_cache\native_build');B=C/'native_warp_revision'
def f32(x):return struct.unpack('<f',struct.pack('<f',x))[0]
def around(x,d):
 bits=struct.unpack('<I',struct.pack('<f',x))[0];return struct.unpack('<f',struct.pack('<I',bits+d))[0]
def integral(scrolls,a,b):
 if b<a:return -integral(scrolls,b,a)
 cuts=sorted({a,b}|{float(k) for k,v in scrolls if a<float(k)<b});result=0.
 for x,y in zip(cuts,cuts[1:]):
  values=[v for beat,v in scrolls if float(beat)<=x];result+=(y-x)*(values[-1] if values else scrolls[0][1])
 return result
def main():
 shutil.copy2(O/'probe_loaded_warp_boundaries.c',B/'probe_loaded_warp_boundaries.c')
 prefix=['wsl','-d','Ubuntu','-u','root','--','chroot','/mnt/piu-anime-native-validation']
 p=subprocess.run(prefix+['env','TMPDIR=/mnt/native_build/tmp','gcc','-m32','-fPIE','-pie','-O2','-msse2','-I/mnt/native_build','/mnt/native_build/native_warp_revision/probe_loaded_warp_boundaries.c','-o','/mnt/native_build/probe_loaded_warp_boundaries','-lm'],cwd=r'C:\Windows',capture_output=True,text=True)
 (O/'boundary_compile.log').write_text(p.stdout+p.stderr);assert p.returncode==0,p.stderr
 results=[]
 for row in json.loads((O/'result.json').read_text())['results']:
  if not row['pass_source']:continue
  raw=Path(row['path']).read_bytes();proof=json.loads(Path(row['proof']).read_text());assert hashlib.sha256(raw).hexdigest()==proof['sha256']
  song=json.loads((R/'chart_sources'/(row['song_id']+'.json')).read_text());chart=next(c for c in song['native_pump_charts'] if c['signature']==row['signature']);clock=SM.Clock(chart['timing']);scrolls=SM.pairs(chart['timing'].get('SCROLLS','')) or [(F(0),1.)]
  warps=[c for c in proof['curves'] if c.get('zero_time_warp')];samples=sorted({around(c['start_ms'],d) for c in warps for d in (-2,-1,0,1,2)})
  samplepath=B/(Path(row['path']).name+'.boundaries.samples');samplepath.write_text('\n'.join(format(x,'.12g') for x in samples))
  p=subprocess.run(prefix+['/mnt/native_build/probe_loaded_warp_boundaries','/mnt/native_build/full_validation_engine','/mnt/native_build/native_warp_revision/'+Path(row['path']).name,'/mnt/native_build/native_warp_revision/'+samplepath.name],cwd=r'C:\Windows',capture_output=True,text=True)
  (O/(Path(row['path']).name+'.boundary.log')).write_text(p.stdout+p.stderr)
  actual=[]
  pattern=r'^BOUNDARY ([-\d.e+]+) split=(\d+) row=(\d+) start=([-\d.e+]+) duration=([-\d.e+]+) rowdistance=([-\d.e+]+) local=([-\d.e+]+) loaded_prefix=([-\d.e+]+) loaded_position=([-\d.e+]+)'
  for match in re.finditer(pattern,p.stdout,re.M):
   ms,split,idx,start,duration,distance,local,prefixdistance,position=map(float,match.groups())
   # Native printf emits nine significant decimal digits: they round-trip to
   # float32, but treating that decimal as a float64 time can put an exact warp
   # sample on the other side of the discontinuity. Recover the actual native
   # float argument; do not shift its timestamp or snap arbitrary nearby times.
   ms=f32(ms);start=f32(start);beat=source_beat(clock,ms);expected=integral(scrolls,0.,beat)
   actual.append(dict(ms=ms,split=int(split),row=int(idx),native_branch_start=start,native_branch_duration=duration,native_row_distance=distance,loaded_position=position,source_position=expected,error=abs(position-expected)))
  maximum=max([x['error'] for x in actual],default=math.inf)
  results.append(dict(title=row['title'],mode=row['mode'],level=row['level'],sha256=proof['sha256'],native_process_success=p.returncode==0,samples=len(actual),expected_samples=len(samples),maximum_loaded_distance_error=maximum,pass_loaded_boundary_distance=p.returncode==0 and len(actual)==len(samples) and maximum<.002,observations=actual,renderer_executed=False,promoted=False))
 report=dict(complete=True,results=results,all_loaded_boundary_distances_pass=all(r['pass_loaded_boundary_distance'] for r in results),scope='Original native loader, branch selector and local distance; cumulative prefix reconstructed from loaded branches. Actual renderer traversal and GPU output remain unverified.',game_opened=False,images_modified=False,promoted=False)
 (O/'native_boundary_result.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='results'}));print([(x['title'],x['mode'],x['maximum_loaded_distance_error']) for x in results])
if __name__=='__main__':main()
