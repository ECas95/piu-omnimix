"""Technomotion 2nd PC readers: song list (MUSICSET.CFG + titles from Sound.pdf), TMM audio, Stp charts (see memory piu-technomotion-format)."""
import struct,re
from pathlib import Path
import numpy as np
G=Path('D:/Pump It Up Data/Techmomotion 2nd PC/Game')
# index -> (title, artist), Sound.pdf
TITLES={0:('A Man Tales','Honey Family'),1:('Another True Heart','Novasonic'),2:('Heartlessness','Chae Jeong-An'),3:('Broken Heart','Koyotae'),4:('Wa!','Lee Jeong-Hyun'),5:('Freedom','O-24'),
 6:('Hatred','Novasonic'),7:('Recollection','Turbo'),8:('Bump','NRG'),9:('C.O.C','Keoun So-young'),10:('Dream','Hyeon SeungMin'),11:('Emotion','Yoo Chae-young'),12:('Flower','Yoo Chae-young'),
 13:('Funky Tonight','CLON'),14:('Get Up','Baby Vox'),15:('Killer','Baby Vox'),16:('Loner','TTma'),17:('Love Story','See U'),18:('Party Party','Koyotae'),19:('Shadow','NRG'),20:('Tell me Tell me','S#arp'),
 21:('Win Win','BROS'),22:('Change','Lee Jeong-Hyun'),23:('Closely','S#arp'),24:('Starian','Duke'),25:('Cyber Lover','Turbo'),26:('I am garbage','NEXT'),27:('Pierrot','Lee Hyeon-Do'),28:('Staring At The Sun','The Offspring'),29:('First Love','CLON')}
MODES={'EASY':0,'NORMAL':18,'HARD':36}
TYPES={'4':0,'5':2,'8':4}
LANES5=(13,7,11,9,15)   # Pump single DL UL C UR DR
def ifind(folder,name):
    for p in folder.iterdir():
        if p.name.lower()==name.lower():return p
    raise FileNotFoundError(folder/name)
def songs():
    t=(G/'MUSICSET.CFG').read_bytes().decode('cp949','replace');mus={};nt={}
    sec=None
    for l in t.splitlines():
        l=l.split(';')[0].strip()
        if l.startswith('MUSIC_NUM'):sec='m';continue
        if l.startswith('NT_NUM'):sec='n';continue
        if l.endswith('_MODE') or l.startswith('DEMO_MODE'):sec=None
        p=l.split()
        if not p or not p[0].isdigit() or sec is None:continue
        if sec=='m':mus[int(p[0])]=dict(tmm=p[1],bmp=p[5] if len(p)>5 else '',folder=p[6] if len(p)>6 else '')
        else:nt[int(p[0])]=dict(folder=p[1],stp=p[2],vsl=p[3])
    out=[]
    for i in sorted(mus):
        m,n=mus[i],nt[i];folder=ifind(G,n['folder']);out.append(dict(index=i,title=TITLES[i][0],artist=TITLES[i][1],bpm_name=m['tmm'],tmm=ifind(G/'music2nd',m['tmm']),folder=folder,stp=ifind(folder,n['stp']),vsl=next(iter([x for x in folder.iterdir() if x.name.lower()==n['vsl'].lower()] or [x for x in folder.iterdir() if x.suffix.lower()=='.vsl']))))
    return out
def audio(tmm):
    b=Path(tmm).read_bytes();n=struct.unpack_from('<I',b,0x2c)[0];assert b[:16]==b'F2system Music F' and len(b)-1024==n;return np.frombuffer(b[1024:],'<i2').reshape(-1,2)
def rows(stp):
    """[(time_ms, bpm, (sec0 54 u16), (sec1 54 u16))] for rows 1..n-1 (row 0 = header)."""
    b=Path(stp).read_bytes();n=struct.unpack_from('<I',b,0x20)[0];assert len(b)>=0x20+n*0xe0
    return [(struct.unpack_from('<I',b,o)[0]*2,struct.unpack_from('<f',b,o+4)[0],struct.unpack_from('<54H',b,o+8),struct.unpack_from('<54H',b,o+116)) for o in (0x20+i*0xe0 for i in range(1,n))]
if __name__=='__main__':
    S=songs();assert len(S)==30
    for s in S:r=rows(s['stp']);print(s['index'],s['title'],s['folder'].name,s['stp'].name,len(r),round(r[0][1],2),round(len(audio(s['tmm']))/44100,1))
