import sync_probe as P,json,glob,numpy as np,os,sys
def peaks(L,S,ref,beat):
    pk=[i for i in range(1,len(S)-1) if S[i]>=S[i-1] and S[i]>=S[i+1]];pk=sorted(pk,key=lambda i:-S[i])
    b=pk[0];alt=next((i for i in pk[1:] if abs(L[i]-L[b])>60),None)
    return round(L[b]),round(S[alt]/S[b],3) if alt is not None else 0,round((L[alt]-L[b])/beat,2) if alt is not None else None
def xc(a,b,lo,hi):   # audio time in a = time in b + lag
    a=(a-a.mean())/a.std();b=(b-b.mean())/b.std();ls=np.arange(int(lo/1000*P.SR/P.HOP),int(hi/1000*P.SR/P.HOP));n=min(len(a),len(b))
    S=np.array([np.dot(a[max(0,l):n+min(0,l)],b[max(0,-l):n-max(0,l)])/n for l in ls]);return ls*P.HOP/P.SR*1000,S
for org,ch,yt in [x.split('|') for x in sys.argv[1:]]:
    song=P.onset(rf'D:\eeez2abackup\EZ2ON_ORGANIZADO\{org}\Song.mp3')
    web=glob.glob(rf'D:\eeez2abackup\ez2on_charts_mp3\*[[]{yt}[]].webm')[0];gp=P.onset(web)
    files=glob.glob(rf'D:\eeez2abackup\ez2on_charts\{ch}\*_*.json');d=json.load(open(files[0],encoding='utf8'));beat=60000/d['initial_bpm']
    L,S=xc(gp,song,-20000,60000);a=peaks(L,S,0,beat)
    print(org,'gameplay = song +',a,os.path.basename(web)[:60])
    tag=os.path.basename(web).split('}')[1].split('[')[0].strip().split()   # title ... 4K SHD 14
    for f in files:
        j=json.load(open(f,encoding='utf8'));t=[x['time_ms'] for x in j['notes']]
        L2,S2=xc(gp,P.train(t,len(gp)),-20000,60000);b=peaks(L2,S2,0,beat)
        print('   ',os.path.basename(f),'gameplay = chart +',b,' => song = chart +',b[0]-a[0])
