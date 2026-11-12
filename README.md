# PIU omnimix (PRIME) — investigación, implementación y desarrollo

Proyecto para convertir una imagen de **Pump It Up PRIME** en un *omnimix* autónomo para gabinete real (MK9, PIUIO, disco de 1 TB): canales personalizados con miles de canciones de otras versiones y juegos, charts generados o convertidos, BGA, banners y menús propios, todo dentro del motor original.

> **Aviso.** Este repositorio contiene **solo código, documentación e investigación**. No incluye imágenes de disco, binarios del juego, audio, video, charts oficiales, claves, ni código de descifrado, extracción de claves o emulación de protecciones/hardware. Para replicar necesitas tus propias copias obtenidas legalmente. Las partes omitidas se describen a nivel conceptual en `docs/`.

## Contenido

| Carpeta | Qué hay |
|---|---|
| `docs/` | Arquitectura, formatos, canales, proceso de build/parches, lecciones y límites |
| `build/` | Catálogo, empaquetado de AMF, finalize, parches 1-12, ampliación de disco, scripts de instalación |
| `build/runtime_merged17/` | Fuente C del módulo de runtime (selector, canales, noteskins) y su compilación |
| `channels/` | Pipelines de cada canal: IIDX, INFINITY/PRO, EZ2ON, Sabin Sound Star, RISE, TECHNO MOTION, canales nuevos, anime/DJMAX |
| `tools_formatos/` | Lectores de formatos antiguos de PIU (STX, NOT, clásicos) y utilidades |
| `bms/` | Conversores a BMS (SSS, EZ2ON, RISE) y lector EZFF |

El generador de pasos vive en su propio repositorio: **[piu-chart-generator](https://github.com/ECas95/piu-chart-generator)**.

## Cómo se replica (visión general)
1. Preparar tu imagen PRIME y entender el contenedor AMF (`docs/FORMATOS.md`).
2. Convertir cada fuente a un registro de canción común (audio, BGA, banner, charts NX) con el pipeline de `channels/<fuente>/`.
3. Generar/convertir charts (piu-chart-generator para las que no traen charts PIU).
4. `build/build_catalog.py` → `build/package.py` → `build/finalize.py` producen AMF adicionales y la LIST.
5. Compilar el runtime (`build/runtime_merged17/compile_runtime.py`) y aplicar parches en orden (`docs/BUILD_Y_PARCHES.md`).

Las rutas de unidad están fijas en muchos scripts (`D:\`, `E:\`): ajústalas a tu entorno.

## Licencia
MIT para el código propio. Los juegos, marcas y contenidos citados pertenecen a sus titulares.
