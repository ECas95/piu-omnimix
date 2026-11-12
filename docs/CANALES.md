# Pipelines por canal

| Canal | Carpeta | Fuente | Notas |
|---|---|---|---|
| Sabin Sound Star (0x47) | `channels/sabin_sound_star` | juego `.sss` + `.bik` | charts de percusión (6 pads) → NX con el mismo `source_grid` que DJMAX; audio = mezcla autoplay de keysounds; banner = placa de título + fotograma |
| EZ2ON REBOOT R (0x48) | `channels/ez2on` | ez2pattern + extracción de assets | offset del chart solo con 3 mediciones concordantes + BGM sobre línea de compás + test de sección; BGA por duración igual o fotograma en vídeos de gameplay; lead-in de 2,5 s |
| IIDX (0x49-0x4c) | `channels/iidx` | LDJ-012 (`music_omni`) | 1355 canciones con BGA propio; mezcla autoplay (atenuación 2dx ~1 dB/unidad, pan @16); vídeos recortados a 16:9 |
| PUMP IT UP PRO/PRO 2/INFINITY (0x44-0x46) | `channels/infinity` | imagen Infinity | 239 canciones, 1867 charts originales |
| RISE Season 2 | `channels/rise` | assets con nombre SHA-256 de `AUDIO<id>` / `STEP<id>_<tipo>_<nivel>` | charts NX byte-idénticos |
| TECHNO MOTION | `channels/techno` | TMM/Stp/VSL | formato decodificado, BGA 3D |
| Canales nuevos (0x4d-0x4e, ANIME, POP, SEKAI) | `channels/nuevas`, `channels/anime_dng` | varias | decisiones y conversión por canción |

Cada pipeline es reanudable (resultados por canción en `result.json`) y deja un registro de problemas.
