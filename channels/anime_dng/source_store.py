"""Read original loose inputs; lease only exact compressed members on the SSD."""
from contextlib import contextmanager
from pathlib import Path
import os, shutil, subprocess, threading, zipfile
from common import CACHE, INVENTORY, digest, read_json

class SourceStore:
    def __init__(self,inventory=None,cache=None):
        inventory=Path(inventory) if inventory is not None else INVENTORY
        cache=Path(cache) if cache is not None else CACHE
        self.files={f['id']:f for f in read_json(inventory/'discovery.json')['files']}
        self.expected={k:v.get('sha256') for k,v in read_json(inventory/'media_index.json')['records'].items()}
        self.root=cache/'media_input_cache'/str(os.getpid())
        self.root.mkdir(parents=True,exist_ok=True)
        self.guard=threading.RLock();self.local=threading.local()
        self.references={};self.paths={};self.verified={}

    @contextmanager
    def song(self):
        assert not getattr(self.local,'ids',None),'Nested source lease'
        self.local.ids=set()
        try:yield self
        finally:
            with self.guard:
                for fid in self.local.ids:
                    self.references[fid]-=1
                    if not self.references[fid] and self.files[fid]['kind']!='file':
                        p=self.paths.pop(fid)
                        assert p.resolve().parent==self.root.resolve()
                        p.unlink(missing_ok=True)
                self.local.ids=None

    def path(self,fid):
        assert getattr(self.local,'ids',None) is not None,'Source input needs song lease'
        with self.guard:
            f=self.files[fid]
            if fid in self.local.ids:return self.paths[fid]
            if fid not in self.paths:
                if f['kind']=='file':
                    p=Path(f['container']);stat=p.stat()
                    assert stat.st_size==f['bytes'],('Source size changed',fid)
                    token=(stat.st_size,stat.st_mtime_ns)
                    if self.verified.get(fid)!=token:
                        sha=digest(p);expected=self.expected.get(fid)
                        assert not expected or sha==expected,('Source hash changed',fid)
                        self.verified[fid]=token
                else:
                    assert shutil.disk_usage(self.root).free > f['bytes']+(2<<30),'SSD input cache needs 2 GiB reserve'
                    p=self.root/(fid+f['extension']);tmp=p.with_name(p.name+'.partial')
                    assert p.parent.resolve()==self.root.resolve()
                    if f['kind']=='zip':
                        with zipfile.ZipFile(f['container']) as z,z.open(f['member']) as src,tmp.open('wb') as out:
                            shutil.copyfileobj(src,out,8<<20)
                    else:
                        with tmp.open('wb') as out:
                            result=subprocess.run([r'C:\Program Files\7-Zip\7z.exe','x','-so','-spd','--',f['container'],f['member']],
                                stdout=out,stderr=subprocess.PIPE,cwd=r'C:\Windows',creationflags=subprocess.CREATE_NO_WINDOW)
                        assert result.returncode==0,result.stderr.decode(errors='replace')[-1000:]
                    assert tmp.stat().st_size==f['bytes'],('Extracted size differs',fid)
                    expected=self.expected.get(fid)
                    assert not expected or digest(tmp)==expected,('Extracted hash differs',fid)
                    os.replace(tmp,p)
                self.paths[fid]=p
            self.local.ids.add(fid);self.references[fid]=self.references.get(fid,0)+1
            return self.paths[fid]
