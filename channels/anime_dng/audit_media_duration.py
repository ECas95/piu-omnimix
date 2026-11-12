"""Audit media duration independently of chart-conversion acceptance."""
import argparse,hashlib
from common import *
import simfile as SM

def audit(sid):
 selection_path=INVENTORY/"selected_manifest.json"
 song=next(s for s in read_json(selection_path)["selected"] if s["id"]==sid)
 assert not song["native_pump_donor_ids"],"Donor clocks require dedicated audit"
 files={f["id"]:f for f in read_json(INVENTORY/"discovery.json")["files"]}
 probe=read_json(INVENTORY/"media_index.json")["records"][song["selected_audio_id"]]
 reader=SM.Reader();records=[];last=0.
 try:
  for entry in song["chart_files"]:
   if entry["format"]==".dwi":continue
   raw=reader.read(files[entry["id"]]);meta,charts=SM.parse(raw,entry["encoding"],entry["format"])
   for chart in charts:
    if not chart["mode"].startswith(("pump-","dance-")):continue
    # native=False is solely a clock census: L is retained as a timed event.
    # This does NOT accept, convert, or serialize any native chart.
    notes,ignored=SM.events(chart,native=False)
    end=max([n["tail_ms"] if n["tail_ms"] is not None else n["ms"] for n in notes],default=0)/1000
    last=max(last,end)
    records.append({"source_file_id":entry["id"],"source_sha256":hashlib.sha256(raw).hexdigest(),"signature":chart["signature"],"last_note_or_tail_seconds":end,"lift_events":sum(n["symbol"]=="L" for n in notes),"non_attack_audit":ignored})
 finally:reader.close()
 assert records
 result={"song_id":sid,"title":song["title"],"selected_audio_id":song["selected_audio_id"],"audio_source_sha256":probe["sha256"],"audio_source_seconds":probe["duration"],"output_seconds":max(probe["duration"],last+1),"source_selection_sha256":digest(selection_path),"records":records,"chart_acceptance":False,"native_lift_still_gated":True,"purpose":"Media duration only; no chart payload or source mutation"}
 write_json(ROOT/"media_timing"/(sid+".json"),result)
 return result
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("song_id");print(audit(p.parse_args().song_id))
