import re,struct,sys
B=open('root_game/infinity_1_10_final_full','rb').read()
e_phoff=struct.unpack_from('<I',B,28)[0];n=struct.unpack_from('<H',B,44)[0]
segs=[]
for i in range(n):
    t,off,va,pa,fsz,msz,fl,al=struct.unpack_from('<8I',B,e_phoff+i*32)
    if t==1:segs.append((va,off,fsz))
def s_at(a):
    for va,off,fsz in segs:
        if va<=a<va+fsz:
            o=off+a-va;e=B.find(b'\0',o,o+200)
            if e>o:
                s=B[o:e]
                if all(32<=c<127 or c in (9,10) for c in s) and len(s)>=3:return s.decode()
    return None
lo,hi=int(sys.argv[1],16),int(sys.argv[2],16)
for line in open('dis.txt'):
    m=re.match(r'\s*([0-9a-f]+):',line)
    if not m:continue
    a=int(m.group(1),16)
    if a<lo:continue
    if a>=hi:break
    line=line.rstrip()
    for imm in re.findall(r'\$0x([0-9a-f]{7,8})',line):
        s=s_at(int(imm,16))
        if s:line+='   ; "'+s[:80].replace('\n','\n')+'"'
    print(line)
