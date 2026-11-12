from pathlib import Path
import json,time,subprocess,re,shutil,hashlib
R=Path(__file__).resolve().parent;OUT=R/'research/native_pause_critical';CACHE=Path(r'C:\Users\USER/.codex/workspaces/anime_channel_cache/native_build/native_pause_revision');CACHE.mkdir(exist_ok=True)
while not (OUT/'result.json').exists() or not json.loads((OUT/'result.json').read_text())['complete']:time.sleep(3)
d=json.loads((OUT/'result.json').read_text());results=[]
for row in d['results']:
 if not row['pass_source']:continue
 row['hold_ticks']=json.loads(Path(row['proof']).read_text())['hold_ticks']
 name=row['song_id']+'_'+row['signature'][:12]+'.NX';source=OUT/name;assert hashlib.sha256(source.read_bytes()).hexdigest()==json.loads(source.with_suffix('.proof.json').read_text())['sha256'];shutil.copyfile(source,CACHE/name)
 command=['wsl','-d','Ubuntu','-u','root','--','chroot','/mnt/piu-anime-native-validation','/mnt/native_build/probe_native_hold_rows','/mnt/native_build/full_validation_engine','/mnt/native_build/native_pause_revision/'+name]
 p=subprocess.run(command,capture_output=True,text=True,cwd=R);(OUT/(name+'.native.log')).write_text(p.stdout+'\n'+p.stderr);match=re.search(r'HOLD_ROWS_PASS cols=(\d+) judged=(\d+) visual_only=(\d+)',p.stdout)
 okay=p.returncode==0 and match is not None and int(match[2])==row['hold_ticks'];results.append(dict(song_id=row['song_id'],signature=row['signature'],title=row['title'],mode=row['mode'],level=row['level'],pass_native_hold_mask=okay,expected_ticks=row['hold_ticks'],native_judged_ticks=int(match[2]) if match else None,returncode=p.returncode,game_opened=False,promoted=False));(OUT/'native_hold_mask_result.json').write_text(json.dumps(dict(results=results,complete=False,promoted=False),indent=2));print(results[-1],flush=True)
(OUT/'native_hold_mask_result.json').write_text(json.dumps(dict(results=results,complete=True,promoted=False),indent=2))
