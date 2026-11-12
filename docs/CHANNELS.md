# Per-channel pipelines

| Channel | Folder | Source | Notes |
|---|---|---|---|
| Sabin Sound Star (0x47) | `channels/sabin_sound_star` | game `.sss` + `.bik` | percussion charts (6 pads) → NX through the same `source_grid` as DJMAX; audio = autoplay mix of keysounds; banner = title plate + frame |
| EZ2ON REBOOT R (0x48) | `channels/ez2on` | ez2pattern + extracted assets | chart offset only when 3 measurements agree + BGM on a bar line + section test; BGA by equal duration or frame matching in gameplay videos; 2.5 s lead-in |
| IIDX (0x49–0x4c) | `channels/iidx` | LDJ-012 (`music_omni`) | 1,355 songs with their own BGA; autoplay mix (2dx attenuation ~1 dB/unit, pan @16); movies cropped to 16:9 |
| PUMP IT UP PRO/PRO 2/INFINITY (0x44–0x46) | `channels/infinity` | Infinity image | 239 songs, 1,867 original charts |
| RISE Season 2 | `channels/rise` | assets named by the SHA-256 of `AUDIO<id>` / `STEP<id>_<type>_<level>` | byte-identical NX charts |
| TECHNO MOTION | `channels/techno` | TMM/Stp/VSL | format decoded, 3D BGA |
| New batches (0x4d–0x4e, ANIME, POP, SEKAI) | `channels/nuevas`, `channels/anime_dng` | various | per-song decisions and conversion |

Each pipeline is resumable (per-song results in `result.json`) and logs its problems.

## BMS preservation converters (`bms/`)
Sabin Sound Star, EZ2ON, RISE and DJMAX RESPECT are also converted to BMS with keysounds (where the source has them), BGA, banner and MP3. See `bms/README.md`.
