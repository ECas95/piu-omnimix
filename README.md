# PIU omnimix (PRIME) — research, implementation and development

A project that turns a **Pump It Up PRIME** image into a self-contained *omnimix* for a real cabinet (MK9, PIUIO, 1 TB disk): custom channels with thousands of songs from other versions and games, generated or converted charts, BGA, banners and custom menus, all inside the original engine.

> **Notice.** This repository contains **code, documentation and research only**. It does not include disk images, game binaries, audio, video, official charts, keys, or any code for decryption, key extraction, or emulation of protections/hardware. To reproduce the work you need your own legally obtained copies. The omitted parts are described only conceptually in `docs/`.

## Contents

| Folder | What is in it |
|---|---|
| `docs/` | Architecture, formats, channels, build/patch process, lessons and limits |
| `build/` | Catalogue, AMF packaging, finalize, patches 1–12, disk growth, install scripts |
| `build/runtime_merged17/` | C source of the runtime module (selector, channels, noteskins) and its build |
| `channels/` | Per-channel pipelines: IIDX, INFINITY/PRO, EZ2ON, Sabin Sound Star, RISE, TECHNO MOTION, new-song batches, anime/DJMAX |
| `format_tools/` | Readers for old PIU formats (STX, NOT, classic) and utilities |
| `bms/` | BMS converters (Sabin Sound Star, EZ2ON, RISE, DJMAX RESPECT) and the EZFF reader |

The step-chart generator lives in its own repository: **[piu-chart-generator](https://github.com/ECas95/piu-chart-generator)**.

## How to reproduce (overview)
1. Prepare your PRIME image and understand the AMF container (`docs/FORMATS.md`).
2. Convert each source into a common song record (audio, BGA, banner, NX charts) with the pipeline in `channels/<source>/`.
3. Generate/convert charts (piu-chart-generator for songs without PIU charts).
4. `build/build_catalog.py` → `build/package.py` → `build/finalize.py` produce the extra AMFs and the LIST.
5. Build the runtime (`build/runtime_merged17/compile_runtime.py`) and apply the patches in order (`docs/BUILD_AND_PATCHES.md`).

Many scripts hard-code drive paths (`D:\`, `E:\`) and some keep Spanish identifiers, file names and comments from the original working notes: adjust them to your environment.

## License
MIT for the original code. Games, trademarks and content mentioned belong to their owners.
