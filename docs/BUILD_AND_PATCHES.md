# Build, patches and lessons

## Build chain
`channels/<source>` → `selection.json` → `build/build_catalog.py` → `build/package.py` (extra AMFs) → `build/finalize.py` → build the runtime (`runtime_merged17/compile_runtime.py`) → `build/patchN/build_patchN.py`.
`build_ui.py` (UI/hexagons/voices) is **not** run by `finalize.py`: run it first. Under WSL the cold start can exhaust the runtime-compile timeout; retry.

## Patches (apply order)
| Patch | Content |
|---|---|
| 1–2 | base and selector/memory fixes |
| 3 | variant-F charts and upper-case names |
| 4 | ANIME MIX names |
| 5 / 5_rise | RISE Season 2 (28 songs, 215 charts) |
| 6 | removal of 35 StepMania songs from EZ2DANCER |
| 7 | IIDX (1,355 songs, 63 GB) |
| 8 | Basic Mode = original PRIME; A–Z by title ordering |
| 9 | sprites; ANIME MIX ULTIMATE rename |
| 10 | new channels, IIDX in 4 parts, CINDERELLA, MAIN SELECTIONS |
| 11–12 | shared hexagons, menu without RANDOM/TRAIN/MISSION |

A new patch must attach the AMFs of all previous ones. On disk: `ampliar_disco/AMPLIAR_DISCO.bat` (grow the partition), then `APLICAR_PARCHE_N.bat` (apply patch N).

## Lessons
- **Real-hardware crash**: the selector read the cursor (+0x38 of a `new(0xf40)`) before initialising it; with a large catalogue the heap reuses dirty memory and the cabinet powered off. Fix: zero `_Znwj/_Znaj` (`selector_resources.c`). QEMU never reproduced it: verify on hardware.
- The engine sorts with `qsort` after the enumerator (comparator `0x8091100`); `channels.c` replaces the comparator. A harness that skips `qsort` does not prove the real order: use `patch8/orden_canales.sh` + `verificar_orden.py`.
- Menu: no hexagon slot is truly free (slots 90–99 are the digits of the description box).
- Space: the game partition ended ~95 % full; free or grow space before adding channels.
- 1 TB disk: write with `qemu-img convert` and compare afterwards; do not regenerate the child image until the disk is written.
- BGA Dark (menu option): research in the patch-5 notes (`bga_diag.c`); the modifier table is relocated in `noteskin.c`.

## Not published
Dongle/AES keys, AMF/ENC2/image decryption, emulation of protections and hardware (CAT702, EEPROM, sentinel), compiled module binaries. Anyone reproducing this must rebuild them with their own means and rights.
