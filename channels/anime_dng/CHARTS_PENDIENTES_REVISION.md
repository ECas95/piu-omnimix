# Variantes fuente pendientes de revisión

Quedan 4 variantes fuente con warps/timing pendientes. Las canciones y otros charts siguen disponibles. La imagen actual de prueba no se modifica mientras el usuario prueba.

| Canción | Modo | Nivel | Firma | Error |
|---|---|---:|---|---|
| Shine!! [FULL SONG] | pump-single | 21 | 07760ed824f7 | AssertionError(('Native timing changed', 1750.0109999999986)) |
| Streaming Heart [Full Song] | pump-single | 20 | 09158b820d99 | AssertionError('Warp-tail release time changed') |
| NEXT COLOR PLANET -FULL SONG- | pump-single | 20 | 859ed5cac3eb | ValueError('Native tick density is not exactly representable within24 checkpoints per beat') |
| NEXT COLOR PLANET -FULL SONG- | pump-double | 23 | 812ac2b9931e | ValueError('Native tick density is not exactly representable within24 checkpoints per beat') |

Right now S16/D13: dos variantes fuente corregidas y verificadas fuera de la imagen (notas/holds/ticks, loader, velocidad en segundos durante STOP y geometría). Se conservan los niveles nativos ya aceptados en la imagen, sin duplicarlos ni sustituirlos durante las pruebas.

La entrega física final será un RAW .img autónomo; preparación en anime_final_v8/cabinet_export, aún sin exportar.

Death by Glamour D22 se retiró del alcance activo por decisión humana de excluir Toby Fox de ANIME PIU. No se ha declarado corregido; fuentes y pruebas anteriores conservadas.
