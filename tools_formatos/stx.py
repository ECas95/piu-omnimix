"""Andamiro STF4 (.STX) charts (Exceed era): 8 slots, each a zlib block = 132-byte header
(f32 BPM, u32 ?, u32 rows-per-beat, u32 cols, ..., u32 start ms @96, u32 rows @128) + 13-byte rows (10 panels + 3)."""
import struct,zlib
def parse(b):
    assert b[:4]==b'STF4'
    out=[]
    for k,o in enumerate(struct.unpack_from('<8I',b,0xfc)):
        z=b.find(b'\x78\x9c',o);x=zlib.decompressobj().decompress(b[z:])
        bpm,_,split,cols=struct.unpack_from('<f3I',x,0);start=struct.unpack_from('<I',x,96)[0];n=struct.unpack_from('<I',x,128)[0]
        rows=[x[132+i*13:145+i*13] for i in range(n)]
        notes=[(i,j) for i,r in enumerate(rows) for j in range(10) if r[j]]
        out.append(dict(slot=k,bpm=bpm,split=split,cols=cols,start_ms=start,rows=n,notes=notes,
                        lanes=10 if any(j>=5 for i,j in notes if j<10) and sum(j>=5 for i,j in notes)>len(notes)*.2 else 5))
    return out
def first_ms(c):
    return c['start_ms']+c['notes'][0][0]/c['split']*60000/c['bpm'] if c['notes'] else None
