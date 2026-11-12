# Architecture

## Idea
PRIME's engine loads a catalogue (`LIST`) and packed archives (AMF) per channel version. The omnimix **adds channels** (new versions with their own ids) without touching the native catalogue, and an injected runtime module adjusts menus, ordering and resources.

## Pieces
1. **Song record** (`channels/*`): each source produces a record with `title, artist, audio, preview_audio, video_segments, still/banner, charts[]`.
2. **Catalogue** (`build/build_catalog.py`): assigns game ids per channel (e.g. `A6000001+` INFINITY, `AA000001+` EZ2ON, `AB000001+` IIDX), levels, ordering and helper rows.
3. **Packaging** (`build/package.py`): produces extra AMFs (≤ 7 GiB) with media and charts; only the media of the songs in `selection.json` is packaged. Every game path is UPPER-CASE (the engine applies `toupper`).
4. **Runtime** (`build/runtime_merged17`): a C module compiled inside the guest. It reorders channels, filters natives, adds menu entries, relocates the noteskin table and fixes an uninitialised-memory bug in the selector.
5. **Patches** (`build/patchN`): each patch adds an AMF and/or changes the LIST/runtime; they are applied in order on the disk.
6. **Disk** (`build/ampliar_disco`, `build/cabinet`): growth of the game partition and writing to the physical disk.

## Channels (summary)
Channel ids 0x35–0x4e: OTAKU'S DREAM 1/2, ANIME MIX 1–3, INEDIT, DSS, ANIME MIX ULTIMATE, POP, PROJECT SEKAI, PUMP IT UP PRO/PRO 2/INFINITY (0x44–0x46), SABIN SOUND STAR (0x47), EZ2ON REBOOT R (0x48), IIDX (0x49–0x4c, A–Z in 4 parts), CINDERELLA GIRLS (0x4d), MAIN SELECTIONS (0x4e). Excluded by design: PRIME 2, XX, PHOENIX, native RISE (they keep their original order).

## Design rules
- Up to 8 charts per custom song: 4 Single + 4 Double in level bands 1–5 / 6–12 / 13–17 / 18–20.
- Only songs with their own BGA and preview; extra charts of an existing song are merged into it; Single then Double, ordered by level.
- Basic Mode must be exactly original PRIME (engine comparator: level of the first chart, then id).
- All custom channels sorted A–Z by title (except the excluded native ones).
