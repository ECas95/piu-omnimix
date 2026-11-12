"""After a keyboard test: copies /SETTINGS/PIU/bga.log out of the throw-away layer to logs/bga.log."""
from pathlib import Path
import subprocess,importlib.util
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('nbd',HERE/'nbd.py');N=importlib.util.module_from_spec(spec);spec.loader.exec_module(N)
N.start()
try:subprocess.run(['wsl','-d','Ubuntu','-u','root','--','bash','/mnt/d/Pump It Up Data/PIU/final_v363/cabinet/teclado_log.sh'],check=True,cwd=r'C:\Windows')
finally:N.stop()
