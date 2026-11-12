"""Second acceptance pass for PROBABLE / REVISAR songs, with the gameplay video (validated 155/156 on CONFIRMADO).
offset = E2 + k*beat/2 - E3, k = the half-beat candidate the video's judgement-area activity prefers (margin >= 0.02);
accepted only if a peak of E1 (chart vs Song.mp3 itself) sits within 25 ms of it and every note lies inside the audio
(<= 300 ms before the start is padded). Updates sync_final.json: status CONFIRMADO_VIDEO."""
import json,os,glob
H='D:/EZ2ON_PIU';fin=json.load(open(f'{H}/sync_final.json',encoding='utf8'));vb=json.load(open(f'{H}/video_beat.json'))
B=r'D:\eeez2abackup';n=0;why={}
for k,v in fin.items():
    if v['status'] not in ('PROBABLE','REVISAR') or k not in vb or 'best' not in vb[k]:continue
    s=json.load(open(f'{H}/sync/{k}.json',encoding='utf8'));r=vb[k]
    if r['margin']<0.02:why[k]=f"video undecided ({r['margin']})";continue
    lag=s['E2_fine']+r['best']*s['beat_ms']-s['E3_fine']
    if not any(abs(p[0]-lag)<=25 for p in s['E1']):why[k]=f'E1 has no peak at {lag:.0f}';continue
    times=[x['time_ms'] for f in glob.glob(os.path.join(B,'ez2on_charts',s['chart'],'*S_*.json')) for x in json.load(open(f,encoding='utf8'))['notes']]
    import subprocess,measure_sync as M
    dur=float(subprocess.run([M.FF.replace('ffmpeg.exe','ffprobe.exe'),'-v','error','-show_entries','format=duration','-of','csv=p=0',os.path.join(M.O,k,'Song.mp3')],capture_output=True,text=True).stdout)*1000
    first=min(times)+lag;last=max(times)+lag
    if first<-3000 or last>dur:why[k]=f'notes outside the audio ({first:.0f}..{last:.0f})';continue
    v.update(status='CONFIRMADO_VIDEO',lag_ms=round(lag,1),pad_ms=max(0,int(-first)+50) if first<0 else 0,video_half_beats=r['best'],video_margin=r['margin']);n+=1
json.dump(fin,open(f'{H}/sync_final.json','w',encoding='utf8'),ensure_ascii=False,indent=1)
print('CONFIRMADO_VIDEO',n,'| not accepted',len(why),list(why.items())[:10])
