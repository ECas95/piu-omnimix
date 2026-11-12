"""M de PIU XX: 4 dobles rondas ChaCha (16,20,24,25) + suma final."""
import struct
M32=0xFFFFFFFF
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def p32(v): return struct.pack('<I',v&M32)
def ror(x,n): return ((x>>n)|(x<<(32-n)))&M32
def _qr(s,a,b,c,d):
    s[a]=(s[a]+s[b])&M32; s[d]^=s[a]; s[d]=ror(s[d],16)
    s[c]=(s[c]+s[d])&M32; s[b]^=s[c]; s[b]=ror(s[b],20)
    s[a]=(s[a]+s[b])&M32; s[d]^=s[a]; s[d]=ror(s[d],24)
    s[c]=(s[c]+s[d])&M32; s[b]^=s[c]; s[b]=ror(s[b],25)
def M(ent16):
    s=list(ent16)
    for _ in range(4):
        _qr(s,0,4,8,12); _qr(s,1,5,9,13); _qr(s,2,6,10,14); _qr(s,3,7,11,15)
        _qr(s,0,5,10,15); _qr(s,1,6,11,12); _qr(s,2,7,8,13); _qr(s,3,4,9,14)
    return s
def entrada(base_key, name, desc):
    import zlib
    seed=zlib.adler32(name.encode() if isinstance(name,str) else name,
                      (desc+0xF12E)&M32)&M32
    acc=seed; out=[]
    for i in range(16):
        acc=(acc+u32(base_key,i*4))&M32; out.append(acc)
    return out
def clave_fichero(base_key, name, desc):
    e=entrada(base_key,name,desc)
    m=M(e)
    return b''.join(p32((e[i]+m[i])&M32) for i in range(16))
def base_desde_entrada(ent_bytes, name, desc):
    import zlib
    seed=zlib.adler32(name.encode() if isinstance(name,str) else name,(desc+0xF12E)&M32)&M32
    prev=seed; out=[]
    for i in range(16):
        w=u32(ent_bytes,i*4); out.append((w-prev)&M32); prev=w
    return b''.join(p32(v) for v in out)
