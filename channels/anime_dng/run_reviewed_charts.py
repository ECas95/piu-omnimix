from pathlib import Path
import sys,importlib.util
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R))
import generate_charts as G,nx_adapter as A
p=R.parent/'anime_channel/generator_revision_exact_heads/quality_charting_mode_policy.py'
spec=importlib.util.spec_from_file_location('quality_charting_dng_review',p);Q=importlib.util.module_from_spec(spec);sys.modules[spec.name]=Q;spec.loader.exec_module(Q);G.Q=Q;A.Q=Q;G.ADAPTER_VERSION='anime-dng-manual-reviewed-mode-v2'
if __name__=='__main__':G.main()
