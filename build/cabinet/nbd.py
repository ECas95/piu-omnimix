"""Cabinet preparation: WSL bridge to native Windows QCOW2 I/O (image in target.json). No game is launched."""
from pathlib import Path
import json,subprocess,psutil,socket,time
ROOT=Path(__file__).resolve().parent
SERVER=Path(r'C:\Program Files\qemu\qemu-nbd.exe')
def start(read_only=False):
    assert json.loads(Path(r'E:\Pump It Up Data\PIU\anime_final_v8\USER_PLAYTEST_ACTIVE.json').read_text())['active'] is False, 'User is testing'
    state=ROOT/'native_nbd_server.json';assert not state.exists(),'Inspect existing NBD server before starting another'
    # These mount points must be free before Windows opens the image.
    subprocess.run(['wsl','-d','Ubuntu','-u','root','--','bash','-c','! mountpoint -q /mnt/piu-cabinet-game && ! mountpoint -q /mnt/piu-cabinet-root'],check=True,cwd=r'E:\Pump It Up Data\PIU')
    routes=subprocess.check_output(['wsl','-d','Ubuntu','-u','root','--','ip','-j','route','show','default'],text=True,cwd=r'E:\Pump It Up Data\PIU')
    host=json.loads(routes)[0]['gateway'];port=10864
    image=Path(json.loads((ROOT/'target.json').read_text())['image'])
    args=[str(SERVER),'--bind='+host,'--port='+str(port),'--format=qcow2','--cache=writeback',str(image)]
    if read_only:args.insert(1,'--read-only')
    log=(ROOT/'logs/native_nbd_server.log').open('ab')
    process=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    report={'pid':process.pid,'image':str(image),'endpoint':f'nbd://{host}:{port}','args':args,'started_unix':time.time()}
    state.write_text(json.dumps(report,indent=2))
    for _ in range(30):
        if process.poll() is not None:raise RuntimeError('Native NBD exited: inspect logs/native_nbd_server.log')
        if any(c.status==psutil.CONN_LISTEN for c in psutil.Process(process.pid).net_connections(kind='inet')):break
        time.sleep(.2)
    else:raise RuntimeError('Native NBD listener did not start')
    print('NATIVE NBD READY',process.pid,flush=True)
def stop():
    state=ROOT/'native_nbd_server.json'
    if not state.exists():return
    subprocess.run(['wsl','-d','Ubuntu','-u','root','--','bash','-c','! mountpoint -q /mnt/piu-cabinet-game && ! mountpoint -q /mnt/piu-cabinet-root'],check=True,cwd=r'E:\Pump It Up Data\PIU')
    data=json.loads(state.read_text())
    try:
        p=psutil.Process(data['pid'])
        assert p.name().lower()=='qemu-nbd.exe' and data['image'] in p.cmdline()
        # A single-client server exits itself after NBD disconnect and drains
        # driver metadata caches. Never use TerminateProcess on a writable disk.
        p.wait(30)
    except psutil.NoSuchProcess:pass
    (ROOT/'native_nbd_last_server.json').write_text(json.dumps(dict(data,stopped_unix=time.time()),indent=2));state.unlink()
    print('NATIVE NBD CLOSED',flush=True)
if __name__=='__main__':
    import sys
    {'start':start,'stop':stop}[sys.argv[1]]()

