# Formatos y hallazgos de ingeniería inversa

(Solo estructura de formatos; no se incluyen claves ni procedimientos de descifrado.)

## Charts
- **NX (PRIME)**: splits con cabecera (`head[3]` = inicio en ms, `head[4]` = BPM, `head[8]` = filas por beat) y filas de celdas (`0x43` tap, `0x57` cabeza de hold, `0x5B` cuerpo, `0x5F` cola). Reloj float32: un split a <0,05 de paso de rejilla se alinea a esa línea.
- **STX/STF4** (Exceed, 700-850): inicio = `hdr@12*10+16` ms. **.NOT**: inicio = `a0*10+80` ms. **'pump 5.0' NOT** (550/650): arrays u16 planos. Lectores en `tools_formatos/`.
- **SSC/SM** de salida (`piu-chart-generator/lib/nx_ssc.py`): rejilla de 48 filas por beat, un timing por chart; `check()` reproduce cada nota y devuelve la desviación máxima en ms.
- **EZFF** (Sabin Sound Star `.sss` v6 con clave aditiva de 128 B; EZ2ON `.ez` v8 sin cifrar): cabecera, pistas `EZTR` y eventos de 11 B (v6) o 13 B (v8): `pos u32, tipo u8, id de sample, vel, pan, longitud u16`. Tipo 3 = BPM float, 4 = compases de n/4. Carriles: pistas `(1P)Line n`/`Scratch`. Longitud > 6 ticks = hold. Implementación: `bms/ezff.py`.
- **BMS de salida** (`bms/`): LNTYPE 1, BPM por canal 08, stops canal 09, BGA canal 04.

## Contenedores y media
- **AMF**: contenedor con índice por versión; offsets `0x1000 + bloque*0x1000` (la convención equivocada da basura silenciosa).
- **LIST**: cabecera de 8 B, filas de canción de 36 B y de chart de 32 B.
- Video: HD 3,5 Mbps para EZ2ON frente a ~2,6 Mbps de los nativos; no se envían SD.
- Banners: placas de título del propio juego sobre un fotograma del BGA (SSS, IIDX).
- Sincronía: el BGA/audio se miden por cruce de correlación (previews con vídeo+audio muxeado, vídeos de gameplay, activity del área de juicio); `bga_delay` de IIDX = 1/60 s.

## Trampas conocidas
- `-stream_loop -1` en ffmpeg con WMV3/ASF y algunos AVI nunca termina: recodificar a H.264 antes.
- El motor pone en mayúsculas toda ruta; nombres en minúsculas no se encuentran.
- Ids nativos con ceros iniciales: las rutas usan el id en hex sin ceros (`/D/1020/`).
- Un tempo IIDX es sin signo (40000/100 = 400 BPM).
- Un `.ifs` y una carpeta con `.2dx` pueden contener canciones distintas con el mismo id.
- Heredocs de la herramienta de shell colapsan barras invertidas: escribir Python en archivos.

## Nota sobre SSS
`sss.py` (decodificador del `.sss`/`.wav` ofuscados del juego, con archivo de clave externo) no se publica; el diseno de la estructura EZFF esta en `docs/FORMATOS.md` y `bms/ezff.py`. `bms/sss_to_bms.py` lo importa: aporta tu propio decodificador compatible.
