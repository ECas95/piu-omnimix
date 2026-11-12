import sys,json
sys.path[:0]=['E:/Pump It Up Data/PIU','E:/Pump It Up Data/PIU/nsde_channel','D:/Pump It Up Data/PIU/final_v363/infinity','E:/Pump It Up Data/PIU/anime_final_v8/channel_style_v45_merged17']
from pathlib import Path
import build_channel_assets as A
from current_parent import load
P,game=load();F=Path('D:/Pump It Up Data/PIU/final_v363/infinity/ui_payloads')
for mode,sl in (('MAIN_FULL_C','HD/EN'),('MAIN_FULL_A3','HD/EN'),('MAIN_FULL_C2','HD/EN')):
    f=F/f'USER_INTERFACE/SELECT/{mode}/{sl}/.BGA';b=f.read_bytes() if f.exists() else game.get(f'/USER_INTERFACE/SELECT/{mode}/{sl}/.BGA');s=A.bga_slots(b)
    names=[b[o:o+64].split(b'\0')[0].decode('latin1') for o,n in s]
    print(mode,len(s),'empty',[i for i,n in enumerate(names) if not n][:40]);print(' ',[(i,names[i]) for i in (21,22,25,37,43,72,73,74,77,78,79) if i<len(names)])
