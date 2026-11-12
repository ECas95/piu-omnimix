"""Exact source provenance; no bulk extraction or modification of original packs."""
from pathlib import Path, PurePosixPath
import json, os, re, shutil, subprocess, time, zipfile
from collections import OrderedDict
from common import *

SEVEN = r'C:\Program Files\7-Zip\7z.exe'

def norm(value):
    return value.replace('\\', '/').casefold().strip('/')

def main():
    handle = lock('assemble.lock')
    inv = read_json(INVENTORY / 'discovery.json')
    selection = read_json(INVENTORY / 'selected_manifest.json')
    assert selection['summary']['selected_songs'] == EXPECTED_SONGS
    assert read_json(INVENTORY / 'inventory_validation.json')['pass']
    files = {x['id']: x for x in inv['files']}
    songs = {x['id']: x for x in inv['songs']}
    probes = read_json(INVENTORY / 'media_index.json')['records']
    assembly = read_json(INVENTORY / 'assembly_plan.json')
    needed = {x['source_file_id'] for x in assembly['assets']}
    images = {}; donor_inputs = {}
    image_ext = {'.png', '.jpg', '.jpeg', '.bmp', '.webp'}
    for s in selection['selected']:
        local = [f for f in files.values() if f['pack'] == s['pack'] and f['extension'] in image_ext
                 and f['kind'] == s['kind'] and norm(f['folder']) == norm(s['folder'])
                 and (s['kind'] == 'file' or f['container'] == s['container'])]
        wanted = []
        for v in s['variants']:
            for tag in ('BANNER', 'BACKGROUND', 'JACKET', 'CDIMAGE'):
                ref = v['metadata'].get(tag, '').replace('\\', '/')
                matches = [f for f in local if norm(PurePosixPath(f['member'] or f['container']).name) == norm(PurePosixPath(ref).name)]
                for f in matches: wanted.append({'file_id':f['id'], 'tag':tag, 'chart_file_id':v['file_id']})
        if not wanted:
            wanted = [{'file_id':f['id'], 'tag':'local_image_fallback'} for f in local
                      if not re.search(r'cdtitle|icon|logo|difficulty', f['logical'], re.I)]
        images[s['id']] = list({x['file_id']:x for x in wanted}.values())
        needed.update(x['file_id'] for x in images[s['id']])
        for sid in s['native_pump_donor_ids']:
            donor = songs[sid]
            assert s['pack'] != 'PACK5' or donor['pack'] == 'PACK5'
            # Stage donors for comparison; importing them requires exact audio equivalence later.
            ids = {c['id'] for c in donor['chart_files']} | {a['id'] for a in donor['audio_candidates']}
            needed.update(ids); donor_inputs[sid] = donor
    selection_hash = digest(INVENTORY / 'selected_manifest.json')
    plan_path = ROOT / 'integration_selection.json'
    if plan_path.exists():
        assert read_json(plan_path)['source_selection_sha256'] == selection_hash, 'Selection changed; review before resuming'
    else:
        write_json(plan_path, {'source_selection_sha256':selection_hash,'songs':selection['selected'],
                              'donor_candidates':donor_inputs,'images':images})
    # Exact virtual manifest: loose originals stay read-only, compressed assets
    # are leased onto the SSD only while a media worker needs that song.
    receipts={};errors=[]
    for fid in sorted(needed):
        f=files[fid]
        if f['kind']=='file':
            original=Path(f['container'])
            if not original.exists() or original.stat().st_size!=f['bytes']:
                errors.append({'file_id':fid,'error':'Original missing or size changed'})
        receipts[fid]={'original':f,'bytes':f['bytes'],'sha256':probes.get(fid,{}).get('sha256'),
                       'access':'read_only_original' if f['kind']=='file' else 'exact_member_on_demand_ssd'}
    manifest={'complete':not errors,'source_selection_sha256':selection_hash,
              'selection_plan':str(plan_path),'files':receipts,'errors':errors,
              'expected_files':len(needed),'expected_bytes':sum(files[k]['bytes'] for k in needed),
              'source_modified':False,'bulk_source_copy_required':False}
    write_json(ROOT/'source_assembly.json',manifest)
    state('source_worker_state.json','complete' if not errors else 'review_required',
          files=len(receipts),expected_files=len(needed),errors=errors)
    assert not errors,errors
    print('SOURCE_ASSEMBLY_COMPLETE',len(receipts),'exact virtual inputs; originals unchanged',flush=True)

if __name__=='__main__':main()
