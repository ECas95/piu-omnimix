#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""indice_f15.py - index of the F15 (PRIME) AMF containers, per region.

F15 has TWO data sets (two regions), each with its own chain of containers
and its own block numbering:

    /mnt/game/F15/INT/  24 containers F2_*.AMF  (~52 GB)
    /mnt/game/F15/JPY/  19 containers F2_*.AMF  (~30 GB)

The AMF header is the same as in F17/F19:

    A = block 0 ; adler32(A[4:0x1000], 41973) == u32(A[0:4])
    nxt = u32(A[0xffc]) ^ u32(A[4:8])
    D   = A ^ block((nxt+1)*0x1000) ; u32(D[0xffc]) == 0xA3A3F5F5
    f8,f12,f16,f20 = u32(D[8:24]) ; name = D[128:128+0x400]

Only 2 blocks are read per container (8 KB), so the I/O is negligible.

Usage:
    python3 indice_f15.py [/mnt/game/F15] [analysis/data]
"""
import json
import os
import struct
import sys
import zlib

BLOQUE = 0x1000
SEMILLA = 41973
MAGIC = 0xA3A3F5F5
BASE = "/mnt/game/F15"
SALIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datos")
REGIONES = ("INT", "JPY")


def cabecera(fh):
    fh.seek(0)
    a = fh.read(BLOQUE)
    if len(a) < BLOQUE:
        return None
    if (zlib.adler32(a[4:], SEMILLA) & 0xFFFFFFFF) != struct.unpack_from("<I", a, 0)[0]:
        return None
    nxt = struct.unpack_from("<I", a, 0xFFC)[0] ^ struct.unpack_from("<I", a, 4)[0]
    if not (0 < nxt < 1 << 27):
        return None
    for cand in (nxt + 1, nxt):
        fh.seek(cand * BLOQUE)
        b = fh.read(BLOQUE)
        if len(b) < BLOQUE:
            continue
        d = bytes(x ^ y for x, y in zip(a, b))
        if struct.unpack_from("<I", d, 0xFFC)[0] == MAGIC:
            f8, f12, f16, f20 = struct.unpack_from("<4I", d, 8)
            nombre = d[128:128 + 0x400].split(b"\0")[0].decode("latin1", "replace")
            return {"f8": f8, "f12": f12, "f16": f16, "n_ficheros": f20,
                    "nombre": nombre, "nxt": nxt, "bloque_datos": cand}
    return None


def indice_region(base, region):
    d = os.path.join(base, region)
    out = []
    for nombre in sorted(os.listdir(d)):
        if not nombre.upper().endswith(".AMF"):
            continue
        ruta = os.path.join(d, nombre)
        sz = os.path.getsize(ruta)
        with open(ruta, "rb") as fh:
            h = cabecera(fh)
        if not h:
            print("  %-26s SIN CABECERA VALIDA" % nombre)
            continue
        ts = int(nombre.split("_")[1].split(".")[0])
        ok = "OK" if ts == h["f12"] else "TIMESTAMP!=f12(%d vs %d)" % (ts, h["f12"])
        out.append({"bin": nombre, "sz": sz, "bloques": sz // BLOQUE,
                    "nombre": h["nombre"], "f8": h["f8"], "f12": h["f12"],
                    "f16": h["f16"], "f20": h["n_ficheros"], "nxt": h["nxt"]})
        print("  %-26s %8.1f MB  bloques=%-9d f8=%-3d f12=%-11d %s" %
              (nombre, sz / 1048576, sz // BLOQUE, h["f8"], h["f12"], ok))
    return out


def main(argv):
    base = argv[1] if len(argv) > 1 else BASE
    salida = argv[2] if len(argv) > 2 else SALIDA
    os.makedirs(salida, exist_ok=True)
    for region in REGIONES:
        print("=== %s ===" % region)
        out = indice_region(base, region)
        c = sorted(out, key=lambda y: (y["f8"], y["f12"]))
        mal = [x["bin"] for i, x in enumerate(c) if x["f8"] != i]
        rep = [x["bin"] for x in c if [y["f8"] for y in c].count(x["f8"]) > 1]
        print("%s: %d contenedores, f8 %d..%d, f8 consecutivo=%s, f8 repetidos=%s"
              % (region, len(c), c[0]["f8"], c[-1]["f8"], not mal, rep or "ninguno"))
        # cadena real por enlaces f16 (igual que en F17 por si hay huerfanos)
        por_ts = {x["f12"]: x for x in c}
        act = max(c, key=lambda x: x["f12"])
        rev, visto = [], set()
        while act is not None and act["bin"] not in visto:
            visto.add(act["bin"])
            rev.append(act)
            act = por_ts.get(act["f16"])
        cad = list(reversed(rev))
        print("   cadena por f16: %d contenedores %s" %
              (len(cad), "== f8" if len(cad) == len(c) else "!= f8 (%d)" % len(c)))
        dump = os.path.join(salida, "contenedores_f15_%s.json" % region.lower())
        json.dump(out, open(dump, "w"), indent=1)
        print("-> %s" % dump)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
