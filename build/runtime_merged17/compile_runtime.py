"""Compile the 17-channel trial + cabinet runtimes with the verified original-ABI builder.

Reuses anime_final_v8/channel_visibility_v35/compile_runtime.py (chroot of the PRIME RAW.img
root partition mounted read-only in WSL), exactly as the v38 runtime was built.
"""
from pathlib import Path
import json,inspect,importlib.util
HERE=Path(__file__).resolve().parent;V=Path(r'E:\Pump It Up Data\PIU\anime_final_v8')
res=json.loads((HERE/'native_filter_result.json').read_text())
assert res['pass_'],'native filter harness must pass first'
(HERE/'native_filter_verified.json').write_text(json.dumps(dict(pass_=True,source=str(HERE/'native_filter_result.json')),indent=1))
if not (HERE/'prepared_review.json').exists():(HERE/'prepared_review.json').write_text(json.dumps(dict(prepared=True,installed=False),indent=1))
spec=importlib.util.spec_from_file_location('verified_abi_builder',V/'channel_visibility_v35/compile_runtime.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
source=inspect.getsource(module.main)
for old,new in [('channel_visibility35_runtime','merged17_v363_runtime'),('compile_channel_visibility35_original_abi.sh','compile_merged17_v363_original_abi.sh'),
                ('SD26_ORIGINAL_ABI_TRIAL_CABINET_CONSTRUCTORS_PASS','MERGED17_ORIGINAL_ABI_TRIAL_CABINET_CONSTRUCTORS_PASS'),
                ('SD26_TARGET_ABI_BOTH_MODULES_VERIFIED','MERGED17_TARGET_ABI_BOTH_MODULES_VERIFIED'),
                ("image=R.parents[1]/'PRIME RAW.img'","image=V.parent/'PRIME RAW.img'")]:
    assert old in source,old;source=source.replace(old,new)
env=dict(module.__dict__);env.update(R=HERE,OUT=HERE,V=V,B=module.CACHE/'native_build/merged17_v363_runtime')
exec(source,env);env['main']()
