# Build, parches y lecciones

## Cadena de build
`channels/<fuente>` → `selection.json` → `build/build_catalog.py` → `build/package.py` (AMF extra) → `build/finalize.py` → compilar runtime (`runtime_merged17/compile_runtime.py`) → `build/patchN/build_patchN.py`.
`build_ui.py` (UI/hexágonos/voces) **no** lo ejecuta `finalize.py`: correrlo antes. En WSL el arranque en frío puede agotar el tiempo de la compilación del runtime; reintentar.

## Parches (orden de aplicación)
| Parche | Contenido |
|---|---|
| 1-2 | base y correcciones de selector/memoria |
| 3 | charts variante F y nombres en mayúsculas |
| 4 | nombres ANIME MIX |
| 5 / 5_rise | RISE Season 2 (28 canciones, 215 charts) |
| 6 | retiro de 35 canciones StepMania de EZ2DANCER |
| 7 | IIDX (1355 canciones, 63 GB) |
| 8 | Basic Mode = PRIME original; orden A-Z por título |
| 9 | sprites; renombre ANIME MIX ULTIMATE |
| 10 | canales nuevos, IIDX en 4 partes, CINDERELLA, MAIN SELECTIONS |
| 11-12 | hexágonos compartidos, menú sin RANDOM/TRAIN/MISSION |

Un parche nuevo debe adjuntar los AMF de todos los anteriores. Sobre disco: `ampliar_disco/AMPLIAR_DISCO.bat`, luego `APLICAR_PARCHE_N.bat`.

## Lecciones
- **Fallo en hardware real**: el selector leía el cursor (+0x38 de un `new(0xf40)`) antes de inicializarlo; con un catálogo grande el heap reutiliza memoria sucia y el gabinete se apagaba. Solución: poner a cero `_Znwj/_Znaj` (`selector_resources.c`). QEMU nunca lo reprodujo: verificar en hardware.
- El motor ordena con `qsort` tras el enumerador (comparador `0x8091100`); `channels.c` reemplaza el comparador. Un arnés que salta el `qsort` no prueba el orden real: usar `patch8/orden_canales.sh` + `verificar_orden.py`.
- Menú: ningún slot de hexágono está realmente libre (los slots 90-99 son dígitos de la caja de descripción).
- Espacio: la partición de juego quedó ~95 % llena; liberar o ampliar antes de añadir canales.
- Disco de 1 TB: se escribe con `qemu-img convert` y comparación posterior; no regenerar la imagen hijo hasta escribir el disco.
- BGA Dark (opción de menú): investigación en `docs/` del parche 5 (`bga_diag.c`); tabla de modificadores relocalizada en `noteskin.c`.

## Lo que no se publica
Claves de dongle/AES, descifrado de AMF/ENC2/imágenes, emulación de protecciones y de hardware (CAT702, EEPROM, sentinel), binarios compilados del módulo. Quien replique debe reconstruirlos con sus propios medios y derechos.
