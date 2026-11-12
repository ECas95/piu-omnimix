"""Verify BMS_DJMAX: note heads vs the pipeline's own parser (respect_chart.py), missing keysound files, media presence."""
import sys,re,os,glob,json,collections
PD=r'D:\PIU_PRESERVADO\ORIGINALES\DJMAX_RESPECT\pipeline_data'
sys.path.insert(0,PD);sys.dont_write_bytecode=True
import respect_chart as R
PLAY={4:[3,4,5,6],5:[3,4,5,6,7],6:[3,4,5,6,7,8],8:[3,4,5,6,7,8,10,11]}
O=r'D:\PIU_PRESERVADO\BMS_DJMAX'
ok=bad=0;badl=[];miss=0;nomedia=collections.Counter();wavmiss=collections.Counter()
for d in sorted(glob.glob(O+'\\*\\')):
    s=os.path.basename(d.rstrip('\\'))
    for k in ('bga.mp4','banner.png','song.mp3'):
        if not os.path.exists(d+k):nomedia[k]+=1
    for b in glob.glob(d+'*.bms'):
        t=open(b,encoding='utf8').read();m=re.match(r'(\d)B_(\w+)\.bms',os.path.basename(b));K=int(m.group(1))
        heads=0
        for mm in re.finditer(r'^#\d{3}(\d\d):(\w+)$',t,re.M):
            ch=int(mm.group(1));n=sum(1 for i in range(0,len(mm.group(2)),2) if mm.group(2)[i:i+2]!='00')
            if ch in (11,12,13,14,15,16,18,19):heads+=n
            elif 51<=ch<=69:heads+=n/2
        c=R.parse(open(f'{PD}\\charts\\{s}\\{s}_{K}b_{m.group(2).lower()}.bytes','rb').read(),'x')
        ref=sum(len(c['tracks'][i]['notes']) for i in PLAY[K])
        if abs(ref-heads)<=1:ok+=1
        else:bad+=1;badl.append((s,os.path.basename(b),ref,heads))
        if [w for w in re.findall(r'^#WAV\w\w (.+)$',t,re.M) if not os.path.exists(d+w.strip())]:wavmiss[s]+=1
print('charts ok',ok,'bad',bad,badl[:8]);print('charts with a missing keysound file',sum(wavmiss.values()),'in',len(wavmiss),'songs',list(wavmiss.items())[:6]);print('songs lacking media',dict(nomedia))
