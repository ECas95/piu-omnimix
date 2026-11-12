# Arquitectura

## Idea
El motor de PRIME carga un catálogo (`LIST`) y archivos empaquetados (AMF) por versión de canal. El omnimix **añade canales** (versiones nuevas con ids propios) sin tocar el catálogo nativo, y un módulo de runtime inyectado ajusta menús, orden y recursos.

## Piezas
1. **Registro de canción** (`channels/*`): cada fuente produce un registro con `title, artist, audio, preview_audio, video_segments, still/banner, charts[]`.
2. **Catálogo** (`build/build_catalog.py`): asigna ids de juego por canal (p. ej. `A6000001+` INFINITY, `AA000001+` EZ2ON, `AB000001+` IIDX), niveles, orden y filas auxiliares.
3. **Empaquetado** (`build/package.py`): genera AMF adicionales (≤ 7 GiB) con media y charts; solo se empaqueta la media de las canciones de `selection.json`. Todas las rutas del juego van en MAYÚSCULAS (el motor aplica `toupper`).
4. **Runtime** (`build/runtime_merged17`): módulo C compilado dentro del guest. Reordena canales, filtra nativos, añade entradas de menú, relocaliza la tabla de noteskins y corrige un fallo de memoria sin inicializar en el selector.
5. **Parches** (`build/patchN`): cada parche añade un AMF y/o cambia LIST/runtime; se aplican en orden sobre el disco.
6. **Disco** (`build/ampliar_disco`, `build/cabinet`): ampliación de la partición de juego y escritura al disco físico.

## Canales (resumen)
Ids de canal 0x35-0x4e: OTAKU'S DREAM 1/2, ANIME MIX 1-3, INEDIT, DSS, ANIME MIX ULTIMATE, POP, PROJECT SEKAI, PUMP IT UP PRO/PRO 2/INFINITY (0x44-0x46), SABIN SOUND STAR (0x47), EZ2ON REBOOT R (0x48), IIDX (0x49-0x4c, ordenado A-Z en 4 partes), CINDERELLA GIRLS (0x4d), MAIN SELECTIONS (0x4e). Excluidos por decisión de diseño: PRIME 2, XX, PHOENIX, RISE nativo (conservan su orden original).

## Reglas de diseño
- Hasta 8 charts por canción personalizada: 4 Single + 4 Double en bandas de nivel 1-5 / 6-12 / 13-17 / 18-20.
- Solo canciones con BGA propio y preview; charts extra de una canción existente se fusionan en ella; orden Single luego Double por nivel.
- Basic Mode debe ser exactamente el PRIME original (comparador del motor: nivel del primer chart, luego id).
- Todos los canales personalizados ordenados A-Z por título (excepto los nativos excluidos).
