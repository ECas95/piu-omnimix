"""Apply explicit human source-difficulty exclusions without modifying source plans."""
def effective_jobs(song,policy):
 blocked={r['source_signature'] for r in policy.get('records',[]) if r['song_id']==song['song_id'] and r['algorithm_tier']=='HARD'}
 dance={c['signature']:c for c in song['dance_sources']};jobs=[];excluded=[]
 for index,job in enumerate(song['generation_jobs']):
  if job['algorithm_tier']=='HARD' and job['source_signature'] in blocked:
   assert job['source_signature'] in dance,'Native Pump must never be excluded'
   excluded.append({'original_job_index':index,'job':job,'reason':'Human-authorized blocked DDR source difficulty exclusion'})
  else:jobs.append((index,job))
 additions=[]
 if excluded:
  native_modes={(c['mode'],c['tier']) for c in song['native_pump_charts']}
  for mode in ('pump-single','pump-double'):
   if (mode,'HARD') in native_modes or any(j['mode']==mode and j['tier']=='HARD' for i,j in jobs):continue
   candidates=[c for c in song['dance_sources'] if c['signature'] not in blocked]
   assert candidates,'No permitted alternate DDR source for required mode/tier'
   chosen=max(candidates,key=lambda c:(float(c['meter']),c['signature']))
   job={'kind':'generated_missing','source_signature':chosen['signature'],'mode':mode,'label':'AUTOHARD_ALLOWED_SOURCE','tier':'HARD','algorithm_tier':'HARD'}
   index=len(song['generation_jobs'])+len(additions);jobs.append((index,job));additions.append({'job_index':index,'job':job,'reason':'Required missing mode/tier from highest-meter remaining permitted source; original source/timing retained'})
 return jobs,excluded,additions
