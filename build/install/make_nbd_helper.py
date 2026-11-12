"""Derive the v363 NBD helper from the verified hybrid36 helper (paths/port/mount names only)."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
src=Path(r'E:\Pump It Up Data\PIU\anime_final_v8\djmax_hybrid_test_v36\native_nbd_server.py').read_text(encoding='utf8')
gate=r"E:\Pump It Up Data\PIU\anime_final_v8\USER_PLAYTEST_ACTIVE.json"
rep=[("assert json.loads((ROOT.parent/'USER_PLAYTEST_ACTIVE.json').read_text())['active'] is False, 'User is testing'",
      "assert json.loads(Path(r'"+gate+"').read_text())['active'] is False, 'User is testing'"),
     ("piu-hybrid36","piu-v363"),("port=10859","port=10863"),
     ("image=ROOT.parent/'PRIME_DJMAX_HYBRID_TEST.qcow2'","image=ROOT.parent/'PRIME_V363_REVIEW.qcow2'")]
for o,n in rep:
    assert o in src,o[:40];src=src.replace(o,n)
(HERE/'native_nbd_server.py').write_text(src,encoding='utf8');print('nbd helper ok')
