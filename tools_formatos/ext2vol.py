#!/usr/bin/env python3
"""
Lector ext2/ext3/ext4 (solo lectura) sobre un objeto con .read(offset, size).

Minimo pero suficiente: superbloque, descriptores de grupo, tablas de inodos,
directorios, bloques directos/indirectos y extents. Sin journal (solo lectura).
"""
import struct

S_IFMT = 0xF000
S_IFDIR = 0x4000
S_IFREG = 0x8000
S_IFLNK = 0xA000


class Ext2Error(Exception):
    pass


class Ext2:
    def __init__(self, dev):
        self.dev = dev
        sb = dev.read(1024, 1024)
        self.sb = sb
        if struct.unpack("<H", sb[56:58])[0] != 0xEF53:
            raise Ext2Error("magic ext2 invalido")
        self.inodes_count = struct.unpack("<I", sb[0:4])[0]
        self.blocks_count = struct.unpack("<I", sb[4:8])[0]
        self.first_data_block = struct.unpack("<I", sb[20:24])[0]
        self.log_block_size = struct.unpack("<I", sb[24:28])[0]
        self.block_size = 1024 << self.log_block_size
        self.blocks_per_group = struct.unpack("<I", sb[32:36])[0]
        self.inodes_per_group = struct.unpack("<I", sb[40:44])[0]
        self.inode_size = struct.unpack("<H", sb[88:90])[0] or 128
        self.feature_incompat = struct.unpack("<I", sb[96:100])[0]
        self.feature_ro_compat = struct.unpack("<I", sb[100:104])[0]
        self.desc_size = struct.unpack("<H", sb[254:256])[0] if \
            (self.feature_incompat & 0x80) else 32
        if self.desc_size == 0:
            self.desc_size = 32
        self.label = sb[120:136].split(b"\0")[0].decode(errors="replace")
        self.uuid = sb[104:120].hex()
        self.num_groups = (self.blocks_count - self.first_data_block +
                           self.blocks_per_group - 1) // self.blocks_per_group
        self._gtbl_block = self.first_data_block + 1
        self._gdt = None
        self._inode_cache = {}

    # ---------- estructuras basicas ----------
    def _group_desc(self, g):
        if self._gdt is None:
            n = self.num_groups * self.desc_size
            tbl_bytes = self.block_size - (self._gtbl_block * self.block_size
                                           - self._gtbl_block * self.block_size)
            need = self.num_groups * self.desc_size
            # la tabla puede ocupar varios bloques
            blocks = (need + self.block_size - 1) // self.block_size
            raw = self.dev.read(self._gtbl_block * self.block_size,
                                blocks * self.block_size)
            self._gdt = raw
        o = g * self.desc_size
        d = self._gdt
        blk_bitmap = struct.unpack("<I", d[o:o + 4])[0]
        inode_bitmap = struct.unpack("<I", d[o + 4:o + 8])[0]
        inode_table = struct.unpack("<I", d[o + 8:o + 12])[0]
        return blk_bitmap, inode_bitmap, inode_table

    def inode(self, n):
        """Inodo 1-based."""
        if n in self._inode_cache:
            return self._inode_cache[n]
        g = (n - 1) // self.inodes_per_group
        idx = (n - 1) % self.inodes_per_group
        _, _, itbl = self._group_desc(g)
        off = itbl * self.block_size + idx * self.inode_size
        raw = self.dev.read(off, self.inode_size)
        i = {
            "num": n,
            "mode": struct.unpack("<H", raw[0:2])[0],
            "size": struct.unpack("<I", raw[4:8])[0],
            "flags": struct.unpack("<I", raw[32:36])[0],
            "block": raw[40:100],
        }
        # i_size_high (32 bits altos) vive en el offset 108 para ficheros
        # regulares, independientemente del tamano de inodo.
        size_high = struct.unpack("<I", raw[108:112])[0]
        if (i["mode"] & S_IFMT) == S_IFREG and size_high:
            i["size"] = i["size"] | (size_high << 32)
        if i["flags"] & 0x80000:  # EXT4_EXTENTS_FL
            i["extents"] = raw[40:40 + 60]
            i["blocks"] = None
        else:
            i["extents"] = None
            i["blocks"] = list(struct.unpack("<15I", raw[40:100]))
        self._inode_cache[n] = i
        return i

    # ---------- mapa de bloques ----------
    def _extent_find(self, node, lb):
        """Busca el bloque fisico de `lb` recorriendo el arbol de extents."""
        magic, entries, max_e, depth, _ = struct.unpack("<HHHHI", node[:12])
        if magic != 0xF30A:
            raise Ext2Error("extent magic invalido %#x" % magic)
        o = 12
        for _ in range(entries):
            if depth == 0:
                ee_block, ee_len, hi, lo = struct.unpack("<IHHI", node[o:o + 12])
                length = ee_len & 0x7FFF
                if ee_len > 0x8000:
                    length = 0
                if ee_block <= lb < ee_block + length:
                    return ((hi << 32) | lo) + (lb - ee_block)
                o += 12
            else:
                ei_block, leaf_lo, leaf_hi, _u = struct.unpack("<IIHH", node[o:o + 12])
                child = (leaf_hi << 32) | leaf_lo
                sub = self.dev.read(child * self.block_size, self.block_size)
                m, e, mx, d, _ = struct.unpack("<HHHHI", sub[:12])
                # ultima entrada cuyo ei_block <= lb
                last = None
                p = 12
                for _j in range(e):
                    eb = struct.unpack("<I", sub[p:p + 4])[0]
                    if eb <= lb:
                        last = p
                    p += 12
                if last is not None:
                    r = self._extent_find(sub, lb)
                    if r is not None:
                        return r
                o += 12
        return None

    def _extent_map(self, node, out, max_blocks=None):
        magic, entries, max_e, depth, _ = struct.unpack("<HHHHI", node[:12])
        if magic != 0xF30A:
            raise Ext2Error("extent magic invalido %#x" % magic)
        o = 12
        for _ in range(entries):
            if depth == 0:
                ee_block, ee_len, ee_start_hi, ee_start_lo = \
                    struct.unpack("<IHHI", node[o:o + 12])
                length = ee_len & 0x7FFF
                if ee_len > 0x8000:  # unwritten
                    length = 0
                start = (ee_start_hi << 32) | ee_start_lo
                for k in range(length):
                    out[ee_block + k] = start + k
                o += 12
            else:
                ei_block, leaf_lo, leaf_hi, _u = \
                    struct.unpack("<IIHH", node[o:o + 12])
                child = (leaf_hi << 32) | leaf_lo
                self._extent_map(self.dev.read(child * self.block_size,
                                               self.block_size), out)
                o += 12
        return out

    def phys_block(self, inode, lb):
        """Bloque fisico del bloque logico `lb`, o None."""
        if inode.get("extents"):
            return self._extent_find(inode["extents"], lb)
        p = self.block_size // 4
        blks = inode["blocks"]
        if lb < 12:
            return blks[lb] or None
        n = lb - 12
        for level, idx in ((1, 12), (2, 13), (3, 14)):
            span = p ** level
            if n < span:
                if not blks[idx]:
                    return None
                cur = blks[idx]
                for lv in range(level, 0, -1):
                    ptrs = self._read_ptr_block(cur)
                    step = p ** (lv - 1)
                    j = n // step
                    if j >= len(ptrs) or not ptrs[j]:
                        return None
                    cur = ptrs[j]
                    n -= j * step
                return cur or None
            n -= span
        return None

    def block_map(self, inode, limit=None):
        """Devuelve {logical_block: physical_block}."""
        m = {}
        if inode.get("extents"):
            self._extent_map(inode["extents"], m)
            return m
        p = self.block_size // 4
        blks = inode["blocks"]
        nblocks = (inode["size"] + self.block_size - 1) // self.block_size
        for i in range(min(12, nblocks)):
            if blks[i]:
                m[i] = blks[i]
        n = 12
        for level, idx in ((1, 12), (2, 13), (3, 14)):
            if n >= nblocks or not blks[idx]:
                break
            ptrs = self._read_ptr_block(blks[idx])
            span = p ** level
            base = n
            for j, pb in enumerate(ptrs):
                lb = base + j * (p ** (level - 1))
                if lb >= nblocks:
                    break
                if level == 1:
                    if pb:
                        m[lb] = pb
                else:
                    sub = self._walk(pb, level - 1, p)
                    for k, sb2 in sub.items():
                        if lb + k < nblocks:
                            m[lb + k] = sb2
            n = base + span
        return m

    def _read_ptr_block(self, b):
        raw = self.dev.read(b * self.block_size, self.block_size)
        return list(struct.unpack("<%dI" % (self.block_size // 4), raw))

    def _walk(self, b, level, p):
        out = {}
        ptrs = self._read_ptr_block(b)
        if level == 1:
            for j, pb in enumerate(ptrs):
                if pb:
                    out[j] = pb
        else:
            for j, pb in enumerate(ptrs):
                if pb:
                    for k, v in self._walk(pb, level - 1, p).items():
                        out[j * (p ** (level - 1)) + k] = v
        return out

    def extent_list(self, inode):
        """[(logical_start, phys_start, length), ...] cacheado por inodo."""
        key = ("ext", inode["num"])
        c = self._inode_cache.get(key)
        if c is not None:
            return c
        out = []
        if inode.get("extents"):
            self._collect_extents(inode["extents"], out)
            out.sort()
        self._inode_cache[key] = out
        return out

    def _collect_extents(self, node, out):
        magic, entries, max_e, depth, _ = struct.unpack("<HHHHI", node[:12])
        if magic != 0xF30A:
            raise Ext2Error("extent magic invalido %#x" % magic)
        o = 12
        for _ in range(entries):
            if depth == 0:
                ee_block, ee_len, hi, lo = struct.unpack("<IHHI", node[o:o + 12])
                length = ee_len & 0x7FFF
                if ee_len > 0x8000:
                    length = 0
                if length:
                    out.append((ee_block, (hi << 32) | lo, length))
                o += 12
            else:
                ei_block, leaf_lo, leaf_hi, _u = struct.unpack("<IIHH", node[o:o + 12])
                child = (leaf_hi << 32) | leaf_lo
                self._collect_extents(self.dev.read(child * self.block_size,
                                                    self.block_size), out)
                o += 12

    # ---------- lectura de ficheros ----------
    def read_inode(self, inode, offset=0, size=None):
        total = inode["size"]
        if size is None:
            size = total - offset
        size = max(0, min(size, total - offset))
        if size == 0:
            return b""
        bs = self.block_size
        exts = self.extent_list(inode) if inode.get("extents") else None
        out = bytearray()
        pos = offset
        end = offset + size
        while pos < end:
            lb = pos // bs
            within = pos % bs
            pb = None
            run = 1
            if exts is not None:
                for ls, ps, ln in exts:
                    if ls <= lb < ls + ln:
                        pb = ps + (lb - ls)
                        # extender el tramo dentro del mismo extent
                        avail = ln - (lb - ls)
                        need = (end - pos + within + bs - 1) // bs
                        run = max(1, min(avail, need))
                        break
            else:
                pb = self.phys_block(inode, lb)
            n = min(run * bs - within, end - pos)
            if pb is None:
                out += b"\0" * n
            else:
                out += self.dev.read(pb * bs + within, n)
            pos += n
        return bytes(out)

    def read_file(self, path):
        return self.read_inode(self.inode(self.resolve(path)))

    # ---------- directorios ----------
    def _iter_dir(self, inode):
        data = self.read_inode(inode)
        o = 0
        while o + 8 <= len(data):
            ino, rec_len, name_len, ftype = struct.unpack("<IHBB", data[o:o + 8])
            if rec_len < 8:
                break
            name = data[o + 8:o + 8 + name_len]
            if ino:
                yield ino, name, ftype
            o += rec_len

    def listdir(self, path):
        ino = self.resolve(path)
        inode = self.inode(ino)
        if (inode["mode"] & S_IFMT) != S_IFDIR:
            raise Ext2Error("%s no es un directorio" % path)
        return [(n.decode(errors="replace"), i, t)
                for i, n, t in self._iter_dir(inode)]

    def resolve(self, path):
        if path in ("/", ""):
            return 2
        cur = 2
        for part in path.strip("/").split("/"):
            found = None
            for ino, name, ftype in self._iter_dir(self.inode(cur)):
                if name.decode(errors="replace") == part:
                    found = ino
                    break
            if found is None:
                raise Ext2Error("no existe: %s (en %s)" % (part, path))
            cur = found
        return cur

    def stat(self, path):
        return self.inode(self.resolve(path))

    def is_dir(self, inode):
        return (inode["mode"] & S_IFMT) == S_IFDIR
