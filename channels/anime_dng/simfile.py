"""Lossless simfile parsing and an independent absolute musical clock."""
from fractions import Fraction as F
from pathlib import Path
import bisect, hashlib, json, math, re, subprocess, zipfile
from collections import Counter, OrderedDict

TIMING = {'OFFSET','BPMS','STOPS','DELAYS','WARPS','FAKES','SPEEDS','SCROLLS','TICKCOUNTS','TIMESIGNATURES','COMBOS'}
COLS = {'pump-single':5,'pump-double':10,'pump-halfdouble':6,'pump-couple':10,
        'dance-single':4,'dance-double':8,'dance-solo':6,'dance-couple':8}

class Reader:
    def __init__(self): self.archives=OrderedDict()
    def read(self, f):
        if f['kind']=='file':return Path(f['container']).read_bytes()
        if f['kind']=='zip':
            if f['container'] not in self.archives:
                self.archives[f['container']]=zipfile.ZipFile(f['container'])
                if len(self.archives)>12:self.archives.popitem(last=False)[1].close()
            return self.archives[f['container']].read(f['member'])
        return subprocess.check_output([r'C:\Program Files\7-Zip\7z.exe','x','-so','-spd','--',f['container'],f['member']])
    def close(self):
        for z in self.archives.values():z.close()

def unescape(value):
    return re.sub(r'\\([\\:;,=])',lambda m:m[1],value)

def tags(text):
    text=re.sub(r'(?<!:)//[^\r\n]*','',text)
    pos=0
    while True:
        found=re.search(r'#([A-Za-z0-9_]+):',text[pos:])
        if not found:return
        start=pos+found.end();i=start
        while i<len(text):
            if text[i]=='\\' and i+1<len(text):i+=2;continue
            if text[i]==';':break
            i+=1
        if i==len(text):raise ValueError('Unterminated tag '+found[1])
        yield found[1].upper(),text[start:i].strip()
        pos=i+1

def parse(raw, encoding='utf-8-sig', extension='.ssc'):
    try:text=raw.decode(encoding)
    except (UnicodeDecodeError,LookupError):text=raw.decode('cp1252')
    global_tags={};charts=[];current=None;local={}
    for k,v in tags(text):
        if k=='NOTEDATA':current={};continue
        if k=='NOTES':
            # SSC writers can emit #NOTES:// measure 0 without whitespace.
            # The global URL guard preserves that colon-adjacent comment, so
            # strip comments again inside the note grid where URLs are invalid.
            v=re.sub(r'//[^\r\n]*','',v)
            if current is not None:
                c={'mode':current.get('STEPSTYPE','').lower(),'difficulty':unescape(current.get('DIFFICULTY','')),
                   'meter':current.get('METER','1'),'description':unescape(current.get('DESCRIPTION',current.get('CHARTNAME',''))),
                   'notes':v,'timing':{key:current.get(key,global_tags.get(key,'')) for key in TIMING}}
                current=None
            else:
                pieces=re.split(r'(?<!\\):',v,maxsplit=5)
                if len(pieces)!=6:
                    # Some old SM writers used a literal trailing backslash as
                    # the entire chart description. Accept only a structurally
                    # valid six-field header in that legacy case.
                    legacy=v.split(':',5)
                    if len(legacy)!=6 or legacy[0].strip().lower() not in COLS or legacy[1].strip()!='\\':
                        raise ValueError('Malformed SM NOTES record')
                    float(legacy[3].strip());pieces=legacy
                c={'mode':pieces[0].strip().lower(),'difficulty':unescape(pieces[2].strip()),'meter':pieces[3].strip(),
                   'description':unescape(pieces[1].strip()),'notes':pieces[5],
                   'timing':{key:local.get(key,global_tags.get(key,'')) for key in TIMING}}
                local={}
            if c['mode'] not in COLS:raise ValueError('Unsupported step type '+c['mode'])
            rows=[]
            for measure,grid in enumerate(c['notes'].split(',')):
                lines=[line.strip() for line in grid.splitlines() if line.strip()]
                for row,line in enumerate(lines):
                    # Old inline keysound annotations do not occupy a panel.
                    clean=re.sub(r'\[[^\]]*\]','',line)
                    if len(clean)!=COLS[c['mode']]:raise ValueError('Invalid note-row width '+repr(line))
                    if any(ch not in '01234MLFKABH' for ch in clean):raise ValueError('Unknown note type '+repr(line))
                    rows.append([str(F(4*measure)+F(4*row,len(lines))),clean])
            c['rows']=rows
            canonical={k:([(str(b),v) for b,v in pairs(value)] if k in {'BPMS','STOPS','DELAYS','WARPS','FAKES'}
                          else float(value or 0) if k=='OFFSET' else re.sub(r'\s+','',value)) for k,value in c['timing'].items()}
            active=[(b,row) for b,row in rows if any(ch!='0' for ch in row)]
            c['signature']=hashlib.sha256(json.dumps([c['mode'],active,canonical],sort_keys=True).encode()).hexdigest()
            c['note_symbols']=dict(Counter(ch for _,row in rows for ch in row if ch!='0'))
            if any(c['note_symbols'].get(ch,0) for ch in '124L'):charts.append(c)
        elif current is not None:current[k]=v
        elif k in TIMING and charts and extension!='.ssc':local[k]=v
        else:global_tags[k]=v
    return {k:unescape(v) for k,v in global_tags.items()},charts

def pairs(value):
    result=[]
    for item in value.split(','):
        if not item.strip():continue
        fields=item.strip().split('=')
        if len(fields)<2:raise ValueError('Malformed timing '+item)
        beat=F(fields[0][:-1])/48 if fields[0].strip().endswith('r') else F(fields[0])
        result.append((beat,float(fields[1])))
    return sorted(result)

class Clock:
    """SM: delay at the marker is included; stop at the marker is excluded.

    Warp beat movement consumes no time; pauses inside a warp still consume time.
    Reference: stepmania/stepmania 5_1-new/src/TimingData.cpp.
    """
    def __init__(self,timing):
        self.offset=float(timing.get('OFFSET') or 0)
        self.bpms=pairs(timing.get('BPMS','')) or [(F(0),120.)]
        if any(v<=0 or not math.isfinite(v) for _,v in self.bpms):raise ValueError('Nonpositive legacy BPM needs explicit review')
        self.stops=pairs(timing.get('STOPS',''));self.delays=pairs(timing.get('DELAYS',''))
        if any(v<0 for _,v in self.stops+self.delays):raise ValueError('Negative stop needs explicit legacy-warp resolution')
        self.warps=[]
        for b,length in pairs(timing.get('WARPS','')):
            end=b+F(str(length))
            if length<=0:continue
            if self.warps and self.warps[-1][1]>=b:self.warps[-1]=(self.warps[-1][0],max(end,self.warps[-1][1]))
            else:self.warps.append((b,end))
        self.fakes=[(b,b+F(str(v))) for b,v in pairs(timing.get('FAKES','')) if v>0]
        self._bpm_beats=[b for b,_ in self.bpms]
        self._points=sorted({F(0)}|set(self._bpm_beats))
        self._prefix=[0.]
        for a,b in zip(self._points,self._points[1:]):self._prefix.append(self._prefix[-1]+float(b-a)*60/self.bpm(a))
        self._zero=self._prefix[self._points.index(F(0))]
        self._stop_beats=[b for b,_ in self.stops];self._delay_beats=[b for b,_ in self.delays]
        self._stop_sums=[0.];self._delay_sums=[0.]
        for _,v in self.stops:self._stop_sums.append(self._stop_sums[-1]+v)
        for _,v in self.delays:self._delay_sums.append(self._delay_sums[-1]+v)
        self._cache={}
    def bpm(self,beat):
        i=bisect.bisect_right([b for b,_ in self.bpms],beat)-1
        return self.bpms[max(0,i)][1]
    def integral(self,start,end):
        def primitive(beat):
            i=max(0,bisect.bisect_right(self._points,beat)-1)
            return self._prefix[i]+float(beat-self._points[i])*60/self.bpm(self._points[i])-self._zero
        return primitive(end)-primitive(start)
    def seconds(self,beat):
        beat=F(beat)
        if beat in self._cache:return self._cache[beat]
        value=-self.offset+self.integral(F(0),beat)
        for start,end in self.warps:
            if start<beat:value-=self.integral(start,min(beat,end))
        value+=self._stop_sums[bisect.bisect_left(self._stop_beats,beat)]
        value+=self._delay_sums[bisect.bisect_right(self._delay_beats,beat)]
        self._cache[beat]=value
        return value
    def judgable(self,beat):
        beat=F(beat)
        if any(a<=beat<b for a,b in self.fakes):return False
        warped=any(a<=beat<b for a,b in self.warps)
        paused=any(b==beat and v for b,v in self.stops+self.delays)
        return not warped or paused

def events(chart, native=False):
    clock=Clock(chart['timing']);notes=[];opened={};counts=Counter();errors=[]
    for b,row in chart['rows']:
        beat=F(b)
        for lane,ch in enumerate(row):
            if ch=='0':continue
            if ch in 'MFKABH':
                counts['non_attack_'+ch]+=1
                if native:errors.append('Unsupported native Pump note '+ch)
                continue
            if ch=='3' and lane in opened:
                note=opened.pop(lane);at=clock.seconds(beat)*1000
                if note is None:continue
                note.update(tail_beat=str(beat),tail_ms=at)
                if at<=note['ms']:errors.append('Nonpositive hold duration')
                continue
            if not clock.judgable(beat):
                counts['warped_or_fake_cells']+=1
                if ch in '24':opened[lane]=None
                continue
            at=clock.seconds(beat)*1000
            if ch in '1L':
                if ch=='L':
                    counts['lift_attacks']+=1
                    if native:errors.append('Native Pump lift requires dedicated NX representation')
                notes.append({'beat':str(beat),'ms':at,'lane':lane,'symbol':ch,'tail_beat':None,'tail_ms':None})
            elif ch in '24':
                if lane in opened:errors.append('Overlapping hold lane '+str(lane))
                if ch=='4' and native:errors.append('Native Pump roll requires dedicated NX representation')
                note={'beat':str(beat),'ms':at,'lane':lane,'symbol':ch,'tail_beat':None,'tail_ms':None}
                opened[lane]=note;notes.append(note)
            elif ch=='3':
                if lane not in opened:
                    counts['unmatched_non_attack_tails']+=1
                    if native:errors.append('Orphan tail lane '+str(lane))
                    continue
                note=opened.pop(lane);note.update(tail_beat=str(beat),tail_ms=at)
                if at<=note['ms']:errors.append('Nonpositive hold duration')
    if opened:errors.append('Unclosed holds '+str(sorted(opened)))
    if errors:raise ValueError('; '.join(sorted(set(errors))))
    return notes,dict(counts)
