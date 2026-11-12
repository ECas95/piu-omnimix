import measure_sync as M,json,numpy as np,sys,os
for s in sys.argv[1:]:
    r=json.load(open(f'sync/{s}.json',encoding='utf8'));sb=M.bands(os.path.join(M.O,s,'Song.mp3'));gb=M.bands(r['gameplay'])
    out=[]
    for a in range(0,len(sb)-2000,1500):   # 20 s windows of the song
        seg=np.zeros_like(sb);seg[a:a+2000]=sb[a:a+2000]
        L,S=M.xcorr(gb,seg,r['E3_fine']-3000,r['E3_fine']+3000);i=int(np.argmax(S));out.append((round(a/M.FPS),round(M.refine(L,S,i)),round(float(S[i]/np.sort(S)[-50]),2)))
    print(s,out)
