import measure_sync as M,json,numpy as np,sys,glob,os
for s in sys.argv[1:]:
    r=json.load(open(f'sync/{s}.json',encoding='utf8'))
    sb=M.bands(os.path.join(M.O,s,'Song.mp3'));gb=M.bands(r['gameplay'])
    lag=int(round(r['E3_fine']/1000*M.FPS))   # gameplay[t+lag] ~ song[t]
    al=np.zeros_like(gb);a0=max(0,lag);n=min(len(gb)-a0,len(sb)-max(0,-lag));al[a0:a0+n]=sb[max(0,-lag):max(0,-lag)+n]
    k=(gb*al).sum(0)/((al*al).sum(0)+1e-9);res=np.maximum(gb-al*k,0).sum(1)
    files=glob.glob(os.path.join(M.B,'ez2on_charts',r['chart'],r['played'] or '*S_*.json'))
    t=[x['time_ms'] for f in files for x in json.load(open(f,encoding='utf8'))['notes']]
    L,S=M.xcorr(res,M.train(t,len(res)),-30000,90000);pk=M.peaks(L,S)
    print(s,'beat',round(r['beat_ms']),'E2 residual',pk[:4],'=> song=chart+',round(pk[0][0]-r['E3_fine'],1),'| E2 plain',r['E2'][:2])
