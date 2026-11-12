"""One SM folder per Technomotion song (sm/NN title/song.sm + audio.wav) and canciones.json for convertir.py --home D:/PIU_TECHNO.
Charts: the 5-arrow type (Pump layout) of EASY / NORMAL / HARD, set A, both sections (section 1 = plain, section 0 = denser), as pump-single; duplicates dropped.
Note time = row time + one row + a per-song lag measured on the audio (medir: broad-band onsets, 2 ms). Meter = native difficulty model. Writes sm_report.json."""
import sys,json,wave
from pathlib import Path
from fractions import Fraction as F
import numpy as np
import tm
B=Path('D:/Pump It Up Data/PIU');sys.path[:0]=[str(B/'anime_channel_dng/engine'),str(B/'anime_channel_dng')];sys.dont_write_bytecode=True
import quality_charting as Q
from difficulty_model import estimate
H=Path(__file__).resolve().parent;OUT=H/'sm'
def onset(x):
    m=x.astype(np.float32).mean(1);m=m[:len(m)//88*88].reshape(-1,88);e=np.sqrt((m**2).mean(1)+1e-9);on=np.clip(np.diff(e),0,None);return on/(on.mean()+1e-9)
def lag(on,times,row_ms):
    """One row plus a residual in -30..+130 ms: a wider window lands on the next 8th."""
    t=np.array(times,float);offs=list(range(int(row_ms)-30,int(row_ms)+132,2));sc=[]
    for off in offs:
        i=np.rint((t+off)*44100/88/1000).astype(int);i=i[i<len(on)];sc.append(on[i].mean())
    k=int(np.argmax(sc));return offs[k],round(float(sc[k]),2)
def measurements(ev):
    times=[e['ms'] for e in ev];span=max(1,(times[-1]-times[0])/1000);count=sum(min(2,len(e['lanes'])) for e in ev)
    return {'row_nps':len(times)/span,'note_nps':count/span,'peak_row_1s':Q._peak(times,1),'peak_row_4s':Q._peak(times,4),'peak_row_8s':Q._peak(times,8),'jump_rows':sum(len(e['lanes'])>1 for e in ev)/len(times),
            'hold_heads':0,'offbeat_rows':sum(e['beat']%1!=0 for e in ev)/len(times),'sixteenth_rows':0}
def main():
    OUT.mkdir(exist_ok=True);recs=[];rep=[]
    for s in tm.songs():
        R=tm.rows(s['stp']);x=tm.audio(s['tmm']);d=OUT/f"{s['index']:02d} {s['title'].replace('!','').replace(':','')}";d.mkdir(exist_ok=True)
        charts=[];seen=set()
        for mode,base in tm.MODES.items():
            for sec,var in ((1,''),(0,' EXPERT')):
                col=base+tm.TYPES['5'];rows=[(i,[(v>>b)&1 for b in tm.LANES5]) for i,(ms,bpm,a,bb) in enumerate(R) for v in [(bb if sec else a)[col]] if v]
                sig=tuple((i,tuple(l)) for i,l in rows)
                if len(rows)<16 or sig in seen:continue
                seen.add(sig);charts.append(dict(name=mode+var,rows=rows))
        all_t=sorted({R[i][0] for c in charts for i,_ in c['rows']});row_ms=30000/R[0][1];lag_ms,score=lag(onset(x),all_t,row_ms)
        # timing: beat = row index / 2; BPM changes where the rows' BPM field changes; one row (half a beat) later + residual lag
        # the BPM field is rounded (Staring: 176.2 for ~176.12); the game schedules by the stored times, so each segment's tempo comes from them
        cut=[0]+[i+1 for i in range(1,len(R)) if abs(R[i][1]-R[i-1][1])>1e-4]+[len(R)-1];bpms=[]   # a new BPM field takes effect one row later (Staring)
        for a,b in zip(cut,cut[1:]):bpms.append((F(a,2),round(30000*(b-a)/(R[b][0]-R[a][0]),4)))
        off=lag_ms/1000;clock_err=0.;cur=0.;secs=[]   # seconds of row i from the BPM list (the file's 2 ms times round, so check the drift)
        bi=0
        for i in range(len(R)):
            secs.append(cur);bpm=[b for a,b in bpms if a<=F(i,2)][-1];cur+=30/bpm
        clock_err=max(abs(secs[i]*1000-R[i][0]) for i in range(len(R)))
        sm=[f"#TITLE:{s['title']};",f"#ARTIST:{s['artist']};","#GENRE:TECHNO MOTION;",f"#OFFSET:{-off:.6f};","#SAMPLESTART:45.000;","#SAMPLELENGTH:12.000;",
            "#BPMS:"+','.join(f"{float(a):.6f}={b:.6f}" for a,b in bpms)+";"]
        info=[]
        for c in charts:
            ev=[dict(ms=secs[i]*1000+lag_ms,lanes=[k for k in range(5) if l[k]],holds=[],beat=F(i,2)) for i,l in c['rows']];lvl,_=estimate(measurements(ev),5)
            last=max(i for i,_ in c['rows']);meas=last//8+1;cells={i:''.join(map(str,l)) for i,l in c['rows']};body=[]
            for m in range(meas):body.append('\n'.join(cells.get(m*8+k,'00000') for k in range(8)))
            sm+=["","//---------------pump-single - ----------------","#NOTES:","     pump-single:",f"     {c['name']}:","     Hard:",f"     {lvl}:","     0,0,0,0,0:",'\n,\n'.join(body)+"\n;"]
            info.append(dict(chart=c['name'],level=lvl,notes=sum(sum(l) for _,l in c['rows']),rows=len(c['rows'])))
        (d/'song.sm').write_text('\n'.join(sm)+'\n',encoding='utf8')
        wav=d/'audio.wav'
        if not wav.exists():
            with wave.open(str(wav),'wb') as w:w.setnchannels(2);w.setsampwidth(2);w.setframerate(44100);w.writeframes(x.tobytes())
        recs.append(dict(pack='TECHNO MOTION',sub='',folder=str(d),title=s['title'],artist=s['artist'],channel='TECHNO',keep=True,reason='',video=str(H/'bga'/f"{s['index']:02d}.mp4"),video_how='rendered',audio=str(wav)))
        rep.append(dict(index=s['index'],title=s['title'],lag_ms=lag_ms,lag_score=score,row_ms=round(row_ms,1),residual_ms=round(lag_ms-row_ms,1),clock_drift_ms=round(clock_err,2),bpms=len(bpms),charts=info))
        print(s['index'],s['title'][:20].ljust(20),'lag',lag_ms,score,'resid',round(lag_ms-row_ms,1),'drift',round(clock_err,2),'bpms',len(bpms),[(i['chart'],i['level'],i['notes']) for i in info],flush=True)
    (H/'canciones.json').write_text(json.dumps(recs,ensure_ascii=False,indent=0),encoding='utf8');(H/'sm_report.json').write_text(json.dumps(rep,ensure_ascii=False,indent=1),encoding='utf8');print('SM_DONE',len(recs))
if __name__=='__main__':main()
