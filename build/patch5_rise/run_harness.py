"""prepare_and_validate.main() without its sources() step: that step recopies the v38 sources and would drop the patch 2 fixes
(zeroing operator new, event mode in channels.c), which live only in runtime_merged17/*_runtime_source."""
import importlib.util,sys
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'runtime_merged17/prepare_and_validate.py'
sys.path.insert(0,str(p.parent))
spec=importlib.util.spec_from_file_location('pv',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.sources=lambda:None
m.main()
