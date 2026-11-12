"""Export the verified cabinet child to ONE standalone RAW image on D: and verify it.

qemu-img convert (whole backing chain flattened) -> qemu-img compare -> SHA-256 of the RAW.
No physical disk is written: burning the RAW to the cabinet disk is done by the user.
"""
from pathlib import Path
import json,subprocess,hashlib,shutil,time,sys
HERE=Path(__file__).resolve().parent;FINAL=HERE.parent;Q=r'C:\Program Files\qemu\qemu-img.exe'
SRC=FINAL/'PRIME_V363_CABINET.qcow2';OUT=Path(r'D:\Pump It Up Data\PIU_PRIME_OMNIMIX_V363_CABINET.img')
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))

def main():
    v=read(HERE/'cabinet_verified.json');assert v['pass'] and Path(v['image'])==SRC
    info=json.loads(subprocess.check_output([Q,'info','--output=json',str(SRC)]));size=info['virtual-size'];assert size==858993459200
    assert not OUT.exists(),'RAW already exists: verify it instead of overwriting'
    assert shutil.disk_usage(OUT.parent).free>size+(2<<30),'not enough free space on D: for the full RAW'
    t=time.time()
    with (HERE/'logs/export.log').open('ab') as log:
        subprocess.run([Q,'convert','-p','-f','qcow2','-O','raw',str(SRC),str(OUT)],check=True,stdout=log,stderr=subprocess.STDOUT)
        assert OUT.stat().st_size==size
        subprocess.run([Q,'compare','-f','qcow2','-F','raw',str(SRC),str(OUT)],check=True,stdout=log,stderr=subprocess.STDOUT)
    h=hashlib.sha256()
    with OUT.open('rb') as f:
        for b in iter(lambda:f.read(64<<20),b''):h.update(b)
    proof=dict(pass_=True,raw=str(OUT),bytes=size,sha256=h.hexdigest(),source_child=str(SRC),qemu_img_compare_identical=True,
               standalone_no_backing=True,seconds=round(time.time()-t),physical_disk_written=False,
               next_step='User burns this RAW to the 1TB cabinet disk (e.g. Win32 Disk Imager / dd), then tests on the MK9.')
    (HERE/'RAW_EXPORT_VERIFIED.json').write_text(json.dumps(proof,indent=1));print('V363_RAW_EXPORTED_VERIFIED',h.hexdigest(),flush=True)

if __name__=='__main__':main()
