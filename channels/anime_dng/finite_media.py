"""Bound source video repetition while preserving the complete scene interval."""
import math

def required_video_loops(source_seconds,start_seconds,output_seconds,rate):
 if not all(math.isfinite(v) for v in (source_seconds,start_seconds,output_seconds,rate)) or source_seconds<=0 or min(start_seconds,output_seconds,rate)<0:
  raise ValueError('Invalid finite video interval')
 # FFmpeg stream_loop counts repeats AFTER the first complete presentation.
 # Freeze scenes need only their selected source frame, not repeating playback.
 needed=start_seconds+(output_seconds*rate if rate else 0)
 return max(0,math.ceil((needed+1/30)/source_seconds)-1)
