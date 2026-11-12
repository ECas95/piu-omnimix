from pathlib import Path
import re,hashlib
from common import *
import simfile as SM

def audit(sid):
 sp=INVENTORY/'selected_manifest.json';song=next(s for s in read_json(sp)['selected'] if s['id']==sid);d=read_json(INVENTORY/'discovery.json');files={f['id']:f for f in d['files']};songs={s['id']:s for s in d['songs']};probe=read_json(INVENTORY/'media_index.json')['records'][song['selected_audio_id']];reader=SM.Reader();records=[];last=0.
 def clock_notes(match):
  out=[]
  for line in match[2].splitlines(keepends=True):
   value=re.sub(r'//.*','',line).strip()
   if value and re.fullmatch(r'(?:[01234MLFKABHXYZxyzSUV]|\{[^}]+\})+',value):
    tokens=re.findall(r'\{[^}]+\}|[^\s]',value);value=''.join('0' if t=='0' else '1' for t in tokens);out.append(value+'\n')
   else:out.append(line)
  return match[1]+''.join(out)+';'
 try:
  seen=set()
  for source in [song]+[songs[x] for x in song['native_pump_donor_ids']]:
   for entry in source['chart_files']:
    if entry['format'] not in ['.sm','.ssc'] or entry['id'] in seen:continue
    seen.add(entry['id']);raw=reader.read(files[entry['id']]);text=raw.decode(entry.get('encoding','utf-8-sig'));normalized=re.sub(r'(#NOTES:)(.*?)(?<!\\);',clock_notes,text,flags=re.S|re.I);meta,charts=SM.parse(normalized.encode('utf8'),'utf8',entry['format'])
    for c in charts:
     if not c['mode'].startswith(('pump-','dance-')):continue
     clock=SM.Clock(c['timing']);end=max((clock.seconds(beat) for beat,row in c['rows'] if any(x!='0' for x in row)),default=0.);last=max(last,end);records.append(dict(source_file_id=entry['id'],source_sha256=hashlib.sha256(raw).hexdigest(),clock_census_signature=c['signature'],source_mode=c['mode'],last_nonzero_source_row_seconds=end,clock_only_cell_normalization=True))
 finally:reader.close()
 assert records
 result=dict(song_id=sid,title=song['title'],selected_audio_id=song['selected_audio_id'],audio_source_sha256=probe['sha256'],audio_source_seconds=probe['duration'],output_seconds=max(probe['duration'],last+1),source_selection_sha256=digest(sp),records=records,chart_acceptance=False,native_effects_still_gated=True,purpose='Media duration only from original row positions and timing; extended owner/mine/roll/brace symbols retained in original source, never converted or accepted here')
 write_json(ROOT/'media_timing'/(sid+'.json'),result);return result
