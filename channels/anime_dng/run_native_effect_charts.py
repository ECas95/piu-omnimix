from pathlib import Path
import sys,importlib.util
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R))
import generate_charts as G,nx_adapter as A
p=R.parent/'anime_channel/generator_revision_exact_heads/quality_charting_mode_policy.py'
spec=importlib.util.spec_from_file_location('quality_charting_dng_review',p);Q=importlib.util.module_from_spec(spec);sys.modules[spec.name]=Q;spec.loader.exec_module(Q);G.Q=Q;A.Q=Q;G.ADAPTER_VERSION='anime-dng-manual-reviewed-mode-v2'
import copy
import native_gimmicks as N
original_native=A.native_nx
def native_with_effects(chart,seconds):
 if chart['mode']=='pump-halfdouble':
  c=copy.deepcopy(chart);c['mode']='pump-double';c['rows']=[(beat,'00'+row+'00') for beat,row in c['rows']]
  raw,proof=N.convert(c,seconds);proof.update(source_step_type='pump-halfdouble',halfdouble_panel_map=[2,3,4,5,6,7],panel_map_reference='https://raw.githubusercontent.com/stepmania/stepmania/5_1-new/src/GameManager.cpp',native_physical_panels_preserved=True)
  return raw,proof
 try:return original_native(chart,seconds)
 except ValueError as ex:
  if not any(s in str(ex) for s in ['Preserve native Pump SCROLLS','Preserve native Pump SPEEDS','Overlapping native timing splits']):raise
  return N.convert(chart,seconds)
G.native_nx=native_with_effects
if __name__=='__main__':G.main()
