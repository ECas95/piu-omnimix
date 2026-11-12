"""Keyboard test of the BURNED cabinet disk without writing it: a throw-away qcow2 layer over \\.\PhysicalDriveN gets the
trial (keyboard) module matching what the disk holds (v379 or v379 + patch 1); QEMU then boots that layer.
Run elevated (PROBAR_CON_TECLADO.bat). The disk itself is opened read-only through the layer and never changed."""
from pathlib import Path
import json,subprocess,sys,hashlib,importlib.util,shutil
HERE=Path(__file__).resolve().parent;FINAL=HERE.parent;Q=r'C:\Program Files\qemu\qemu-img.exe'
LAYER=HERE/'teclado_capa.qcow2'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main(n,variant='trial'):
    if LAYER.exists():LAYER.unlink()
    subprocess.run([Q,'create','-f','qcow2','-F','raw','-b',rf'\\.\PhysicalDrive{n}',str(LAYER)],check=True)   # no size: the layer takes the whole disk's (the game partition may have been grown)
    patch=json.loads((FINAL/'patch/patch.json').read_text());v379=json.loads((HERE/'cabinet_verified.json').read_text())
    pick=FINAL/'diag/m_fx.so' if variant=='fx' else FINAL/'patch5/m_bga_diag.so' if variant=='bga' else FINAL/'patch2/m_trial.so'   # fx = PIUIO only, no button board (MK9 FX)
    known=[patch['m_cabinet_sha256'],sha(FINAL/'diag/m_diag.so'),patch['m_trial_sha256'],sha(FINAL/'patch2/m_cabinet.so'),sha(FINAL/'diag/m_diag2.so')]   # modules the patched disk may hold
    trials={k:pick for k in known}
    for d in ('patch5_rise','patch6','patch7','patch8','patch10','patch11','patch12'):   # patches 5 and 6 change the module: each has its own keyboard build
        p5=FINAL/d/'m_cabinet.so'
        if p5.exists():trials[sha(p5)]=FINAL/d/'m_trial.so' if variant=='trial' else pick
    (HERE/'teclado_map.json').write_text(json.dumps({k:str(v).replace('D:\\','/mnt/d/').replace('\\','/') for k,v in trials.items()}))
    (HERE/'target.json').write_text(json.dumps(dict(image=str(LAYER))))
    spec=importlib.util.spec_from_file_location('nbd',HERE/'nbd.py');N=importlib.util.module_from_spec(spec);spec.loader.exec_module(N)
    N.start()
    try:subprocess.run(['wsl','-d','Ubuntu','-u','root','--','bash','/mnt/d/Pump It Up Data/PIU/final_v363/cabinet/teclado.sh'],check=True,cwd=r'C:\Windows')
    finally:N.stop()
    print('TECLADO_CAPA_LISTA',flush=True)
if __name__=='__main__':main(int(sys.argv[1]),*(sys.argv[2:3]))
