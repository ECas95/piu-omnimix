import struct,capstone,sys
b=open(sys.argv[1],'rb').read()
e_phoff=struct.unpack_from('<I',b,28)[0];n=struct.unpack_from('<H',b,44)[0];segs=[]
for i in range(n):
    t,off,va,pa,fs,ms,fl,al=struct.unpack_from('<8I',b,e_phoff+i*32)
    if t==1:segs.append((off,va,fs,fl))
v2o=lambda v:next(off+v-va for off,va,fs,fl in segs if va<=v<va+fs)
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
a=int(sys.argv[2],16);ln=int(sys.argv[3])
for i in md.disasm(b[v2o(a):v2o(a)+ln],a):print(hex(i.address),i.mnemonic,i.op_str)
