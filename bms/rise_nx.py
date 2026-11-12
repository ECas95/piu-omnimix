"""Lossless NX20 structure reader: starting column, branches and param lists.

Unlike the simple generation serializer, this preserves every original word,
including Half-Double offsets and non-default division structures.
"""
import struct,math
def parse(data):
 assert data[:4]==b'NX20';pos=4
 def take(n):
  nonlocal pos
  assert 0<=n<=10000000 and pos+n*4<=len(data)
  result=list(struct.unpack_from('<'+'I'*n,data,pos));pos+=n*4;return result
 start,cols,mode,nt=take(4);assert 0<cols<=10 and mode in (0,1);tags=[take(2) for _ in range(nt)];ns,=take(1);blocks=[]
 for _ in range(ns):
  system,nm=take(2);meta=[take(2) for _ in range(nm)];nb,=take(1);assert 0<nb<10000;branches=[]
  for b in range(nb):
   h=take(7);params=[take(2) for _ in range(h[6])];nr,=take(1);rows=[]
   for r in range(nr):
    first,=take(1);rows.append([first] if mode==1 or (first&255)==128 else [first]+take(cols-1))
   branches.append(dict(head=h,params=params,rows=rows))
  blocks.append(dict(system=system,meta=meta,branches=branches))
 pool_size=struct.unpack_from('<I',data,len(data)-4)[0];assert pos+pool_size==len(data),(pos,pool_size,len(data));pool=data[pos:-4]
 return dict(start_column=start,cols=cols,row_mode=mode,tags=tags,blocks=blocks,pool=pool)
def build(nx):
 out=bytearray(b'NX20')
 def emit(values):out.extend(struct.pack('<'+'I'*len(values),*values))
 emit([nx['start_column'],nx['cols'],nx['row_mode'],len(nx['tags'])])
 for t in nx['tags']:emit(t)
 emit([len(nx['blocks'])])
 for block in nx['blocks']:
  emit([block['system'],len(block['meta'])])
  for m in block['meta']:emit(m)
  emit([len(block['branches'])])
  for branch in block['branches']:
   emit(branch['head'])
   for p in branch['params']:emit(p)
   emit([len(branch['rows'])])
   for row in branch['rows']:emit(row)
 out.extend(nx['pool']);emit([len(nx['pool'])+4]);return bytes(out)
def f32(value):return struct.unpack('<f',struct.pack('<I',value))[0]
def duration(nx):
 end=0.
 for block in nx['blocks']:
  for branch in block['branches']:
   h=branch['head'];begin,bpm=f32(h[0]),f32(h[1]);rpb=h[5]&255;kind=h[5]>>16
   assert math.isfinite(begin) and math.isfinite(bpm) and bpm>0 and rpb>0
   interval=0 if kind in (2,3) else 60000/bpm/rpb
   end=max(end,begin+len(branch['rows'])*interval)
 return end/1000

def last_note_seconds(nx):
 end=0.
 for block in nx['blocks']:
  for branch in block['branches']:
   h=branch['head'];dt=0 if h[5]>>16 in (2,3) else 60000/f32(h[1])/(h[5]&255)
   for i,row in enumerate(branch['rows']):
    if any((v&255) in (0x43,0x57,0x5b,0x5f) for v in row):end=max(end,(f32(h[0])+i*dt)/1000)
 return end
