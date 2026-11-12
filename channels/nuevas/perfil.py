import os,sys,time,glob,cProfile,pstats,faulthandler
faulthandler.enable()
import convertir as C
from pathlib import Path
if __name__=='__main__':
    A,env=C.grid_env();f=sorted(Path(sys.argv[1]).glob('*.osu'))[0]
    pr=cProfile.Profile();t=time.time();pr.enable();raw,i=C.osu_chart(f,A,env);pr.disable();print('osu_chart',round(time.time()-t,1),len(raw),i,flush=True)
    pstats.Stats(pr).sort_stats('cumtime').print_stats(10)
