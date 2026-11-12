from pathlib import Path
import hashlib, json, os, time

# Unattended workers must receive an I/O exception instead of waiting behind a
# hidden Windows critical-error dialog (for example an unavailable drive in PATH).
if os.name == 'nt':
    import ctypes
    ctypes.windll.kernel32.SetErrorMode(0x0001 | 0x8000)

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
CACHE = ROOT / 'cache'
INVENTORY_ORIGINAL = BASE / 'anime_inventory'
INVENTORY = ROOT / 'inventory'
PYTHON = Path(r'C:\Users\USER\AppData\Local\Programs\Python\Python311\python.exe')
PIPE = Path(r'E:\DJMPS4\GAME\pump_pipeline')

def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def write_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp.' + str(os.getpid()))
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf8')
    for attempt in range(100):
        try:
            os.replace(tmp, path); return
        except PermissionError:
            time.sleep(.1)
    raise RuntimeError('Could not commit checkpoint: ' + str(path))

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(8 << 20), b''): h.update(chunk)
    return h.hexdigest()

def lock(name):
    import msvcrt
    handle = (ROOT / name).open('a+b')
    if not handle.tell(): handle.write(b'0'); handle.flush()
    handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    return handle

def state(name, phase, **kwargs):
    value = dict(phase=phase, pid=os.getpid(), updated_unix=time.time(), **kwargs)
    write_json(ROOT / 'checkpoints' / name, value)
    return value

EXPECTED_SONGS = 246
