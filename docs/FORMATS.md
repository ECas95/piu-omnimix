# Formats and reverse-engineering findings

(Structure only; no keys and no decryption procedures are included.)

## Charts
- **NX (PRIME)**: splits with a header (`head[3]` = start in ms, `head[4]` = BPM, `head[8]` = rows per beat) and rows of cells (`0x43` tap, `0x57` hold head, `0x5B` hold body, `0x5F` hold tail; `0x23/0x37/0x3F` = fake notes). Float32 clock: a split within 0.05 of a grid step snaps to that line. RISE charts can also carry gimmick parameters in the branch head.
- **STX/STF4** (Exceed, 700–850): start = `hdr@12*10+16` ms. **.NOT**: start = `a0*10+80` ms. **'pump 5.0' NOT** (550/650): flat u16 arrays. Readers in `format_tools/`.
- **SSC/SM** output (`piu-chart-generator/lib/nx_ssc.py`): 48 rows per beat, one timing per chart; `check()` replays every note and returns the worst deviation in ms.
- **EZFF** (Sabin Sound Star `.sss` v6 with a 128-byte additive key; EZ2ON `.ez` v7/v8 and DJMAX RESPECT charts, unencrypted): header, `EZTR` tracks and events of 11 bytes (v6) or 13 bytes (v7/v8): `pos u32, type u8, sample id, volume, pan, length u16`. Type 3 = float BPM, 4 = measures of n/4. Lanes: tracks 3.. (keys), then extra buttons/scratch. Length > 6 ticks = hold. Implementation: `bms/ezff.py`.
- **BMS output** (`bms/`): LNTYPE 1, BPM on channel 08, stops on channel 09, BGA on channel 04, fake notes on invisible channels 31–39, `#BASE 62` when a song has more than 1,295 samples.

## Containers and media
- **AMF**: container with a per-version index; offsets `0x1000 + block*0x1000` (the wrong convention silently yields garbage).
- **LIST**: 8-byte header, 36-byte song rows and 32-byte chart rows.
- Video: HD 3.5 Mbps for EZ2ON versus ~2.6 Mbps for natives; SD is not shipped.
- Banners: the game's own title plates over a BGA frame (SSS, IIDX).
- Sync: BGA/audio are measured by correlation (previews with muxed video+audio, gameplay videos, judgement-area activity). EZ2ON `ez2pattern` charts are aligned to `Song.mp3` with a measured per-song lag (`time in Song.mp3 = chart time + lag`); IIDX `bga_delay` = 1/60 s.

## Known traps
- `-stream_loop -1` in ffmpeg with WMV3/ASF and some AVI never ends: re-encode to H.264 first.
- The engine upper-cases every path; lower-case names are never found.
- Native ids with leading zeros: paths use the plain-hex id (`/D/1020/`).
- An IIDX tempo is unsigned (40000/100 = 400 BPM).
- An `.ifs` and a folder with `.2dx` can hold different songs under the same id.
- Shell heredocs collapse backslashes: write Python to files.
- The Sabin Sound Star decoder (`sss.py`, external key file) is not published; `bms/sss_to_bms.py` imports it, so provide your own compatible decoder.
