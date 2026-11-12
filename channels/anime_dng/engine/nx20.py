#!/usr/bin/env python3
"""PIU NX20 chart format (PRIME / PRIME 2), as reversed from stock charts.

    "NX20", u32 0, u32 columns, u32 ?, u32 ntags, ntags x (u32 key, u32 value)
    u32 nsplits, then per split:
        u32 ?, u32 ?, u32 ?, f32 start_ms, f32 bpm, f32 beat_per_row, f32 ?, f32 speed,
        u32 rows_per_beat | 0x400, u32 0, u32 nrows, rows
    row: u32 0x80 (empty row) or `columns` u32 cells (0 empty, tap 0x343, hold 0x357/0x35b/0x35f)
    string pool, u32 pool size (including this u32); tag 0x14 = offset of the generic BGA name.
Tags: 0x3e8 = 1, 0x3e9 = level.
"""

import struct

EMPTY_ROW = 0x80
TAP, HOLD_START, HOLD_BODY, HOLD_END = 0x343, 0x357, 0x35B, 0x35F


def parse(b: bytes) -> dict:
    magic, _, cols, unk, ntags = struct.unpack_from("<4sIIII", b, 0)
    assert magic == b"NX20", magic
    pos = 20
    tags = [struct.unpack_from("<II", b, pos + 8 * i) for i in range(ntags)]
    pos += 8 * ntags
    nsplits, = struct.unpack_from("<I", b, pos)
    pos += 4
    splits = []
    for _ in range(nsplits):
        head = struct.unpack_from("<3I5f3I", b, pos)
        pos += 44
        rows = []
        for _ in range(head[10]):
            w, = struct.unpack_from("<I", b, pos)
            if w == EMPTY_ROW:
                rows.append(None)
                pos += 4
            else:
                rows.append(struct.unpack_from(f"<{cols}I", b, pos))
                pos += 4 * cols
        splits.append({"head": head, "rows": rows})
    pool_size, = struct.unpack_from("<I", b, len(b) - 4)
    assert pos == len(b) - pool_size, (pos, len(b), pool_size)
    return {"cols": cols, "unk": unk, "tags": tags, "splits": splits, "pool": b[pos:len(b) - 4]}


def build(chart: dict) -> bytes:
    out = bytearray(struct.pack("<4sIIII", b"NX20", 0, chart["cols"], chart["unk"], len(chart["tags"])))
    for t in chart["tags"]:
        out += struct.pack("<II", *t)
    out += struct.pack("<I", len(chart["splits"]))
    for s in chart["splits"]:
        h = list(s["head"])
        h[10] = len(s["rows"])
        out += struct.pack("<3I5f3I", *h)
        for r in s["rows"]:
            out += struct.pack("<I", EMPTY_ROW) if r is None else struct.pack(f"<{chart['cols']}I", *r)
    out += chart["pool"] + struct.pack("<I", len(chart["pool"]) + 4)
    return bytes(out)


if __name__ == "__main__":
    import sys
    for f in sys.argv[1:]:
        b = open(f, "rb").read()
        c = parse(b)
        assert build(c) == b, f
        print(f, c["cols"], c["tags"], [(s["head"][3:10], len(s["rows"])) for s in c["splits"]][:4])
