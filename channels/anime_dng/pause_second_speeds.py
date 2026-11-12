"""Time-based final SPEED ramp entirely inside an authored STOP.

This narrow adapter retains independent source-time boundaries. Other mixtures
of time-based ramps still fail explicitly instead of being flattened.
"""
from fractions import Fraction as F
import native_gimmicks_tick_compensation as D

class PauseSecondSpeeds:
    def __init__(self,text,clock):
        rows=[p.strip().split('=') for p in text.split(',') if p.strip()]
        second=[p for p in rows if len(p)>3 and int(p[3])==1 and F(p[2])>0]
        assert len(second)==1,'Review multiple second-based ramps separately'
        p=second[0];self.beat=F(p[0]);self.target=float(p[1]);duration=float(p[2])*1000
        assert self.target>=0 and all(F(x[0])<=self.beat for x in rows),'Second ramp must be last'
        ordinary=[x for x in rows if x is not p]
        old=D.canonical_beat;D.canonical_beat=F
        try:self.base=D.Speeds(','.join('='.join(x) for x in ordinary))
        finally:D.canonical_beat=old
        assert all(z<=self.beat for a,z,x,y in self.base.segments),'Previous beat ramp overlaps final time ramp'
        self.start=clock.seconds(self.beat)*1000;self.end=self.start+duration
        stop=sum(v for b,v in clock.stops if b==self.beat)*1000
        assert duration<=stop,'Second ramp must end inside its authored STOP'
        self.begin=self.base.value(self.beat)
        self.segments=self.base.segments;self.extra_beats={self.beat}
        self.time_nodes=[(self.end,self.beat)]
    def value_at(self,ms,beat,left=False):
        if ms<self.start-.01:return self.base.value(beat,left=left)
        part=max(0,min(1,(ms-self.start)/(self.end-self.start)))
        return self.begin+(self.target-self.begin)*part
    def changes_during_pause(self,ms,end_ms):
        return ms<self.end and end_ms>self.start
    def ledger(self):
        return dict(kind='source_seconds_inside_stop',beat=str(self.beat),start_ms=self.start,end_ms=self.end,begin=self.begin,target=self.target)
