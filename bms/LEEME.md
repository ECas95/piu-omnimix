# PIU_PRESERVADO

| Carpeta | Contenido |
|---|---|
| `BMS_SSS\<cancion>\` | Sabin Sound Star: un `.bms` por chart original (`1e/1n/1h`, `2n/2h`, `3e/3n/3h`...), keysounds decodificados (`.wav`), `song.mp3` (mezcla autoplay), `banner.png`, `bga.mp4` |
| `BMS_EZ2ON\<cancion>\` | EZ2ON REBOOT R: `<N>S_<DIFF>.bms` (+ keysounds `.ogg/.flac`, `Song.mp3`, `BGA.mp4`, `Banner.png`, `Cover.png`) |
| `tools\` | `sss_to_bms.py`, `ez2on_to_bms.py`, `ezff.py` (lector EZFF) |
| `MANIFIESTO_LIMPIEZA.csv` | lista de lo que se borra / conserva (nada borrado hasta aprobarla) |

## Mapa de carriles BMS
- SSS (pistas del .sss -> canal BMS): 3-7 -> 11-15, 8 -> 18, 9 -> 19, 10 -> 16 (scratch), 11 -> 17 (pedal); 2P: 12-16 -> 21-25, 17 -> 28, 18 -> 29, 19 -> 26, 20 -> 27. Modo 1 = pistas {3-8,11}, modo 2 = {3-8,11,12-16,19}, modo 3 (percusion) = {8,9,10,17,18,19}. El rol exacto de cada pista no esta confirmado contra el juego.
- EZ2ON: Line 1-5 -> 11-15, Line 6 -> 18, Line 7 -> 19, Scratch -> 16.
- Holds = LN tipo 1 (canales 5x/6x). `#PLAYLEVEL` de SSS = 0 (el .sss no trae nivel).

## Limites conocidos
- EZ2ON: solo las canciones con `.ez` (`Charts\`) llevan keysounds; el resto usa el BMS de ez2pattern (sin keysounds) con `Song.mp3` como BGM. 108 canciones no tienen ningun chart.
- BGA EZ2ON en BMS de ez2pattern: posicion calculada con el primer BPM (aproximacion si hay cambios de BPM antes del inicio del BGA).
- BGA SSS: pre-relleno negro hasta el `.del` del juego (o la sincronizacion medida).
