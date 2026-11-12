# BMS preservation converters

Convert the source games' charts to **BMS** (keysounds where the source has them), keeping MP3, banner and BGA.

| Script | Source | Output per song |
|---|---|---|
| `sss_to_bms.py` | Sabin Sound Star `.sss` (keyboard 1x/2x and percussion 3x) | one `.bms` per chart, decoded keysounds, `song.mp3` (autoplay mix), `banner.png`, `bga.mp4` |
| `ez2on_to_bms.py` | EZ2ON REBOOT R (`.ez` + `.ezi`/instrumentDic, or ez2pattern BMS) | `<N>S_<DIFF>.bms`, keysounds, `Song.mp3`, `BGA.mp4`, `Banner.png`, `Cover.png` |
| `rise_to_bms.py` | PIU RISE Season 2 NX charts | `<chart>.bms`, `song.mp3`, `bga.mp4`, `banner.png`, `preview.mp3` |
| `ezff.py` | EZFF reader (EZ2ON `.ez`, shared container with SSS/DJMAX) | — |

## Lane maps
- **SSS** (track → BMS channel; best effort, not confirmed against the game): 3–7 → 11–15, 8 → 18, 9 → 19, 10 → 16 (scratch), 11 → 17 (pedal); 2P: 12–16 → 21–25, 17 → 28, 18 → 29, 19 → 26, 20 → 27. Mode 1 = tracks {3–8, 11}, mode 2 = {3–8, 11, 12–16, 19}, mode 3 (percussion) = {8, 9, 10, 17, 18, 19}. `#PLAYLEVEL` is 0 (the `.sss` carries no level).
- **EZ2ON**: tracks 3.. → 11–15, then 18, 19, 16 (4K/5K/6K/8K).
- **RISE**: 5 panels → 11–15; 6 (half-double) → 11–15 + 18. Fake notes go to the invisible channels 31–39.
- Holds are LN type 1 (channels 5x/6x).

## Synchronisation
- Keysounded EZ2ON charts use the game's own timeline (self-consistent).
- EZ2ON charts that exist only as ez2pattern BMS are aligned to `Song.mp3` with the measured per-song lag (`time in Song.mp3 = chart time + lag`). In these files wav `01` is a silent placeholder (`blank.wav`) used by every note and wav `02` is the song: the `02` object is placed at chart time `-lag` (following the file's own BPM and measure-length changes), and the BGA object at `-lag + BGA start`. If the lag is positive the song is trimmed (`Song_sync.mp3`) and placed at 0. `verify_ez2on_sync.py` checks every song (245/245 within 15 ms). Songs without a measurement keep the original assumption (song on measure 1).
- RISE: `song.mp3`/`bga.mp4` are shifted so that BMS time 0 = NX beat 0.
- SSS: BGA is padded with black up to the game's `.del` value (or the measured synchronisation).

## Known limits
- EZ2ON: only songs with `.ez` charts get keysounds; the rest use the ez2pattern BMS with `Song.mp3` as BGM. Some songs have no chart at all.
- ez2pattern BGA position uses the first BPM (approximate if the BPM changes before the BGA starts).
- RISE charts with gimmick parameters (speed/warp) keep only their notes.
- A few songs reference samples that are not in the source banks; those BMS load but are incomplete.
