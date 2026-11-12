#!/usr/bin/env python3
"""Convert EZ2Dancer StepMania songs (.sm/.sma, ez2-single / ez2-double) into PRIME song folders.

    python ez2_convert.py SONG_DIR ID OUT_DIR [--no-video]

Writes OUT_DIR/D/<ID>/... (AMF paths) and OUT_DIR/D/<ID>/song.json (LIST data for build_omnimix).
ez2-single columns (FootLeft, HandLeft, FootDown, HandRight, FootRight) land 1:1 on PIU
(DL, UL, C, UR, DR): feet stay low, hands go to the upper panels. ez2-double = two singles.
ez2-real (7 columns, extra lower hands) has no PIU layout and is skipped.
"""

from __future__ import annotations

import json
import math
import re
import struct
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

import nx20

VERSION = 0x18  # LIST version byte for EZ2Dancer songs (own channel filters on it)
STYLES = {"ez2-single": ("S", 0, 5), "ez2-double": ("D", 2, 10), "ez2-real": ("S", 0, 5)}
REAL_FOLD = [0, 1, 1, 2, 3, 3, 4]  # ez2-real 7 columns -> PIU single: lower hand sensors join the upper ones


def ez2_mode(chart: dict) -> str | None:
    """EZ2Dancer mode of a pack chart: EASY / HARD (single), REAL, CLUB (double); None = skip (Edit)."""
    diff = chart["difficulty"].lower()
    if diff == "edit":
        return None
    if chart["style"] == "ez2-double":
        return "CLUB"
    if chart["style"] == "ez2-real":
        return "REAL"
    return "EASY" if diff in ("beginner", "easy") else "HARD"


def fold_real(notes: str) -> str:
    rows = []
    for line in notes.split("\n"):
        t = line.strip()
        if len(t) >= 7 and all(c not in ",;" for c in t[:7]):
            out = ["0"] * 5
            for c, ch in enumerate(t[:7]):
                if ch != "0" and out[REAL_FOLD[c]] == "0":
                    out[REAL_FOLD[c]] = ch
            rows.append("".join(out))
        else:
            rows.append(t)
    return "\n".join(rows)


TIMING = ("OFFSET", "BPMS", "STOPS", "DELAYS", "ROWSPERBEAT")
RPB_CHOICES =(1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 192)


# ---------------------------------------------------------------- .sm / .sma parsing

def parse_sm(path: Path) -> tuple[dict, list[dict]]:
    text = re.sub(r"//[^\n]*", "", path.read_text(encoding="utf-8", errors="replace"))
    song, charts, local = {}, [], {}
    for key, value in re.findall(r"#([A-Z0-9]+):(.*?);", text, re.S):
        if key == "NOTES":
            parts = [p.strip() for p in value.split(":")]
            timing = {k: local.get(k, song.get(k, "")) for k in TIMING}
            charts.append({"style": parts[0], "difficulty": parts[2], "meter": int(float(parts[3] or 1)),
                           "notes": parts[5], **timing})
            local = {}
        elif key in TIMING and (charts or key in song):  # .sma: per-chart timing repeats the song's keys
            local[key] = value.strip()
        else:
            song[key] = value.strip()
    return song, charts


def beat_of(token: str, rows_per_beat: int) -> Fraction:
    token = token.strip()
    return Fraction(token[:-1]) / rows_per_beat if token.endswith("r") else Fraction(token)


def pairs(value: str, rows_per_beat: int) -> list[tuple[Fraction, float]]:
    out = []
    for item in value.split(","):
        if "=" in item:
            b, v = item.split("=")[:2]
            out.append((beat_of(b, rows_per_beat), float(v)))
    return sorted(out)


def parse_notes(notes: str, cols: int) -> list[tuple[Fraction, int, str]]:
    out = []
    for m, measure in enumerate(notes.split(",")):
        lines = [l.strip() for l in measure.split("\n") if l.strip()]
        for i, line in enumerate(lines):
            for c, ch in enumerate(line[:cols]):
                if ch in "1234":
                    out.append((Fraction(4 * m) + Fraction(4 * i, len(lines)), c, ch))
    return out


# ---------------------------------------------------------------- chart -> NX20

def pick_rpb(start: Fraction, end: Fraction, beats: list[Fraction]) -> int:
    for r in RPB_CHOICES:
        if all(((b - start) * r).denominator == 1 for b in beats + [end]):
            return r
    return 192


def to_nx(chart: dict, level: int, cols: int, audio_ms: float) -> bytes:
    rpb_decl = int(chart["ROWSPERBEAT"].split("=")[-1] or 48) if chart["ROWSPERBEAT"] else 48
    bpms = pairs(chart["BPMS"], rpb_decl) or [(Fraction(0), 120.0)]
    stops = dict(pairs(chart["STOPS"], rpb_decl))
    delays = dict(pairs(chart["DELAYS"], rpb_decl))
    offset_ms = -float(chart["OFFSET"] or 0) * 1000
    return build_nx(parse_notes(chart["notes"], cols), bpms, stops, delays, offset_ms, level, cols, audio_ms)


PLAYER_BITS = (0x40010000, 0x80020000)  # co-op cells: owner player 1 / 2 (stock DP50 charts)


def build_nx(notes: list[tuple], bpms: list[tuple[Fraction, float]], stops: dict,
             delays: dict, offset_ms: float, level: int, cols: int, audio_ms: float, tags=None,
             warps: dict | None = None) -> bytes:
    """notes: (beat, column, SM note char[, co-op player 0/1]); beat 0 plays at offset_ms into the audio.
    warps: {beat: length in beats} (SM5): the warped beats take no time and their notes are skipped."""
    warps = warps or {}
    warped = lambda beat: any(b <= beat < b + n for b, n in warps.items())
    notes = [n for n in notes if not warped(n[0])]
    # cell values per (beat, column): hold heads/tails from SM 2/4 ... 3, taps from 1
    cells: dict[tuple[Fraction, int], int] = {}
    holds: list[tuple[int, Fraction, Fraction, int]] = []
    open_hold: dict[int, Fraction] = {}
    for beat, col, ch, *player in notes:
        bits = PLAYER_BITS[player[0]] if player else 0
        if ch == "1":
            cells[(beat, col)] = nx20.TAP | bits
        elif ch in "24":
            open_hold[col] = beat
        elif ch == "3" and col in open_hold:
            holds.append((col, open_hold.pop(col), beat, bits))
    for col, a, b, bits in holds:
        cells[(a, col)], cells[(b, col)] = nx20.HOLD_START | bits, nx20.HOLD_END | bits

    bounds = sorted({b for b, _ in bpms if b > 0} | {b for b in stops} | {b for b in delays}
                    | {b for w in warps.items() for b in (w[0], w[0] + w[1])})
    last = max([b for b, _ in cells] + [b for _, _, b, _ in holds] + [Fraction(0)])
    first = min([Fraction(0)] + [b for b, _ in cells])

    def ms(beat: Fraction) -> float:
        return raw_ms(beat) - sum(raw_ms(min(beat, b + n)) - raw_ms(b) for b, n in warps.items() if b < beat)

    def raw_ms(beat: Fraction) -> float:
        """SM time of `beat` without warps (delays at beat included, stops at beat excluded)."""
        t, prev_b, bpm = offset_ms, Fraction(0), bpms[0][1]
        for b, v in bpms:
            if b >= beat:
                break
            if b > prev_b:
                t += float(b - prev_b) * 60000 / bpm
                prev_b = b
            bpm = v
        t += float(beat - prev_b) * 60000 / bpm
        t += sum(v * 1000 for b, v in stops.items() if b < beat)
        t += sum(v * 1000 for b, v in delays.items() if b <= beat)
        return t

    def bpm_at(beat: Fraction) -> float:
        return [v for b, v in bpms if b <= beat][-1] if any(b <= beat for b, _ in bpms) else bpms[0][1]

    splits = []
    edges = [first] + [b for b in bounds if b > first]
    for i, s in enumerate(edges):
        e = edges[i + 1] if i + 1 < len(edges) else None
        if warped(s) and e is not None:  # warped beats get no rows: the next split starts at the same time
            continue
        bpm = bpm_at(s)
        inside = sorted({b for b, _ in cells if b >= s and (e is None or b < e)}
                        | {b for _, a, z, _ in holds for b in (a, z) if b >= s and (e is None or b < e)})
        if e is None:  # run the last split to the end of the audio (or 4 beats past the last note)
            tail_beats = max(Fraction(4), Fraction(math.ceil(max(0.0, audio_ms - ms(last)) * bpm / 60000)))
            e_eff = last + tail_beats if last >= s else s + tail_beats
        else:
            e_eff = e
        r = pick_rpb(s, e_eff, inside)
        row_ms = 60000 / bpm / r
        beats = [s + Fraction(k, r) for k in range(int((e_eff - s) * r))]
        if s in stops and beats:  # the row on the stop plays before the pause, the rest after it
            splits.append((ms(s), bpm, r, beats[:1]))
            splits.append((ms(s) + stops[s] * 1000 + row_ms, bpm, r, beats[1:]))
        else:
            splits.append((ms(s), bpm, r, beats))

    splits = [sp for sp in splits if sp[3]]  # PRIME crashes on a split without rows (a stop one row before a change)
    held = set(holds)
    out_splits = []
    for n, (start, bpm, r, beats) in enumerate(splits):
        rows = []
        for beat in beats:
            row = [cells.get((beat, c), 0) for c in range(cols)]
            for col, a, b, bits in held:
                if a < beat < b:
                    row[col] = nx20.HOLD_BODY | bits
            rows.append(tuple(row) if any(row) else None)
        head = (0, 0, 1, start, bpm, 1.0 / r, start if n == 0 else 0.0, 1.0, 0x400 | r, 0, len(rows))
        out_splits.append({"head": head, "rows": rows})
    return nx20.build({"cols": cols, "unk": 0, "tags": tags or [(1000, 1), (1001, level)], "splits": out_splits, "pool": b""})


# ---------------------------------------------------------------- media

def ffprobe_ms(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip()) * 1000


def ffmpeg(*args: str) -> None:
    if Path(args[-1]).exists():  # outputs are deterministic: keep what an earlier run encoded
        return
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


MPEG2 = ["-an", "-c:v", "mpeg2video", "-pix_fmt", "yuv420p", "-r", "30", "-g", "15", "-bf", "2",
         "-flags", "+cgop", "-sc_threshold", "1000000000", "-f", "mpeg2video"]
BGA_RATES = (("HD", 1280, 720, "6M"), ("SD", 640, 480, "3M"))
FIT = "scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1"


def find(folder: Path, *patterns: str) -> Path | None:
    for pattern in patterns:
        hits = sorted(p for p in folder.iterdir() if re.fullmatch(pattern, p.name, re.I))
        if hits:
            return hits[0]
    return None


def write_song(out: Path, sid: str, music_in: list[str], media: Path | None, start: float, charts: list[tuple],
               meta: dict, audio_ms: float, video: bool = True, image: Path | None = None,
               bga_file: Path | None = None, version: int = VERSION, sd_bga: Path | None = None,
               preview_bga: Path | None = None, bga_rates=BGA_RATES, bga_shift: float = 0.0, extra: dict | None = None) -> dict:
    """charts: (prefix "S"/"D", LIST type, level, tag, NX bytes); music_in: ffmpeg input args for the song audio;
    media: pack folder with BGA / eye / preview (None = select art left black, generic BGA)."""
    root = out / "D" / sid
    (root / sid).mkdir(parents=True, exist_ok=True)
    records, names, written = [], set(), set()
    for prefix, kind, level, tag, data in charts:
        if data in written:  # some arcade folders ship a copy of EASY as HARD: keep the first
            continue
        written.add(data)
        name = f"{prefix}{level}_{re.sub(r'[^A-Z0-9]', '', tag.upper()) or 'EZ2'}"
        while name in names:
            name += "X"
        names.add(name)
        (root / sid / f"{name}.NX").write_bytes(data)
        records.append({"name": name.lower(), "type": kind, "level": level})

    (root / "A").mkdir(exist_ok=True)
    ffmpeg(*music_in, "-vn", "-ar", "48000", "-ac", "2", "-b:a", "192k", "-f", "mp3", str(root / "A" / ".A"))
    (root / "P" / "A").mkdir(parents=True, exist_ok=True)
    preview = find(media, r"preview.*\.mp3") if media else None
    src = ["-i", str(preview)] if preview else ["-ss", str(start), "-t", "10", *music_in]
    ffmpeg(*src, "-vn", "-ar", "48000", "-ac", "2", "-b:a", "192k", "-f", "mp3", str(root / "P" / "A" / ".A"))

    eye = image or find(media, r"eye.*\.(bmp|png|jpg)", r".*background.*\.(bmp|png|jpg)", r"disc.*\.(png|bmp|jpg)",
               r".*banner.*\.(png|bmp|jpg)") if media else None
    from PIL import Image
    img = Image.open(eye).convert("RGB").resize((1280, 720), Image.LANCZOS) if eye else Image.new("RGB", (1280, 720))
    (root / "P" / ".G").write_bytes(struct.pack("<IHH", 0x18, 1280, 720) + img.tobytes())

    bga = bga_file or find(media, r"bga\.(avi|mpg|mpeg|mp4|wmv)", r".*\.(avi|mpg|mpeg|mp4|wmv)") if media else None
    if bga and video:
        # bga_shift: seconds into the song where the video starts (negative: its first part is cut)
        trim = ["-ss", f"{-bga_shift:.3f}"] if bga_shift < 0 else []
        length = ffprobe_ms(bga) / 1000
        if length < audio_ms / 1000 - 10:  # a short loop clip: PRIME does not loop videos, so loop it here
            trim = ["-stream_loop", "-1", "-t", f"{audio_ms / 1000:.3f}", *trim]
        pad = f"tpad=start_duration={bga_shift:.3f}:color=black," if bga_shift > 0 else ""
        for q, w, h, rate in bga_rates:
            (root / "V" / q).mkdir(parents=True, exist_ok=True)
            src = sd_bga if q == "SD" and sd_bga else bga
            ffmpeg(*trim, "-i", str(src), "-vf", pad + FIT.format(w=w, h=h), "-b:v", rate, "-maxrate", rate,
                   "-bufsize", "4M", *MPEG2, str(root / "V" / q / ".V"))
        for q, w, h in (("HD", 464, 264), ("SD", 312, 176)):
            (root / "P" / "V" / q).mkdir(parents=True, exist_ok=True)
            src = ["-t", "10", "-i", str(preview_bga)] if preview_bga else ["-ss", str(start % max(length - 10, 1)), "-t", "10", "-i", str(bga)]
            ffmpeg(*src, "-vf", FIT.format(w=w, h=h), "-b:v", "3M", *MPEG2, str(root / "P" / "V" / q / ".V"))

    info = {"id": sid, "version": version, **meta, **(extra or {}), "preview": start, "seconds": audio_ms / 1000, "charts": records}
    (root / "song.json").write_text(json.dumps(info, indent=1, ensure_ascii=False), encoding="utf-8")
    return info


def convert(song_dir: Path, sid: str, out: Path, video: bool = True, level=None, signature: str | None = None) -> dict:
    """A StepMania-pack song; level(chart, cols) overrides the pack meter when given."""
    sm = find(song_dir, r".*\.sma", r".*\.sm")
    song, charts = parse_sm(sm)
    music = song_dir / song.get("MUSIC", "")
    if not song.get("MUSIC") or not music.exists():
        music = find(song_dir, r".*\.(ogg|mp3|wav)")
    audio_ms = ffprobe_ms(music)
    out_charts = []
    # pack difficulty names do not follow EZ2's modes (UK Move calls EASY "Medium"): among the singles,
    # the easiest is EASY and the rest HARD; a lone single follows the official signature (E without H)
    singles = sorted((c for c in charts if c["style"] == "ez2-single" and ez2_mode(c)), key=lambda c: c["meter"])
    single_mode = {id(c): "EASY" if i == 0 and (len(singles) > 1 or ("E" in signature and "H" not in signature))
                   else "HARD" for i, c in enumerate(singles)} if signature is not None else {}
    for chart in charts:
        mode = ez2_mode(chart) if chart["style"] in STYLES else None
        if not mode:
            continue
        mode = single_mode.get(id(chart), mode)
        if chart["style"] == "ez2-real":
            chart = {**chart, "notes": fold_real(chart["notes"])}
        prefix, kind, cols = STYLES[chart["style"]]
        lv = max(1, min(level(chart, cols) if level else chart["meter"], 99))
        out_charts.append((prefix, kind, lv, mode, to_nx(chart, lv, cols, audio_ms)))
    bpms = sorted({round(v) for _, v in pairs(charts[0]["BPMS"] if charts else song.get("BPMS", ""), 192)}) or [0]
    meta = {"title": song.get("TITLE", song_dir.name), "artist": song.get("ARTIST", ""),
            "bpm": str(bpms[0]) if len(bpms) == 1 else f"{bpms[0]}~{bpms[-1]}", "source": str(song_dir)}
    return write_song(out, sid, ["-i", str(music)], song_dir, float(song.get("SAMPLESTART") or 30),
                      out_charts, meta, audio_ms, video)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    print(json.dumps(convert(Path(args[0]), args[1].upper(), Path(args[2]), "--no-video" not in sys.argv), indent=1, ensure_ascii=False))
