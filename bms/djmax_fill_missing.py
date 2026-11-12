"""For songs whose BMS reference keysounds that are not in their sound banks, look for the clips in the song's other bundles (master 'm', any pack)."""
import sys,re,os,glob,json
sys.dont_write_bytecode=True
import UnityPy
PD=r'D:\PIU_PRESERVADO\ORIGINALES\DJMAX_RESPECT\pipeline_data';O=r'D:\PIU_PRESERVADO\BMS_DJMAX'
inv=json.load(open(PD+r'\inventory.json',encoding='utf8'))
rep={}
for d in sorted(glob.glob(O+'\\*\\')):
    s=os.path.basename(d.rstrip('\\'));need=set()
    for b in glob.glob(d+'*.bms'):
        for w in re.findall(r'^#WAV\w\w (.+)$',open(b,encoding='utf8').read(),re.M):
            w=w.strip()
            if not os.path.exists(d+w):need.add(w)
    if not need:continue
    want={Path_stem.lower():Path_stem for Path_stem in (os.path.splitext(w)[0] for w in need)}
    found=set()
    for e in [e for e in inv['bundles'] if e['song']==s and e['kind'] in ('m','s')]:
        try:
            for o in UnityPy.load(e['path']).objects:
                if o.type.name!='AudioClip':continue
                a=o.read()
                if a.m_Name.lower() in want and a.m_Name.lower() not in found:
                    raw=next(iter(a.samples.values()));open(d+want[a.m_Name.lower()]+'.wav','wb').write(raw);found.add(a.m_Name.lower())
        except Exception as x:print('ERR',s,repr(x)[:100])
    rep[s]=dict(needed=len(want),found=len(found),still_missing=sorted(set(want)-found)[:6])
    print(s,rep[s],flush=True)
json.dump(rep,open(r'D:\PIU_PRESERVADO\djmax_missing_keysounds.json','w'),indent=1)
print('DONE',len(rep))
