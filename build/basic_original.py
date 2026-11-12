"""Basic Mode exactly as the original PRIME (user 2026-11-06), from the last official catalog f2_1589344650 (patch8/oficial).
restore_rows: the helper rows (lo = E000 song, hi = media song) become the official 220 rows of the official 57 songs, which point at the official
NX files still in the chain. Full Mode reads the primary rows (hi == lo) and is not touched.
fix_parents: song field 4 of an E000 helper is the ordinal of its media song. It was never remapped when songs were inserted, so a helper named one
song and played the preview video of another (Pandora showed On and On). The order needs nothing: the engine sorts by first chart level, then id."""
import json
from pathlib import Path
ROWS=json.loads((Path(__file__).resolve().parent/'patch8/oficial/official_basic.json').read_text())['rows']
is_helper=lambda s:s[0]>>28==0xE
def restore_rows(songs,rows,text):
    ordinal={s[0]:i+1 for i,s in enumerate(songs)}
    alias=lambda c:c[0]>>16!=c[0]&65535 and 0<c[0]&65535<=len(songs) and is_helper(songs[(c[0]&65535)-1])
    kept=[c for c in rows if not alias(c)]
    # appended in official order: the catalog's stable sort by media song keeps each helper's charts in that order
    return kept+[[(ordinal[r['hi']]<<16)|ordinal[r['lo']],text(r['name']),*r['rest']] for r in ROWS]
def fix_parents(songs):
    ordinal={s[0]:i+1 for i,s in enumerate(songs)}
    for s in songs:
        if is_helper(s) and s[0]&0xFFFF in ordinal:s[4]=ordinal[s[0]&0xFFFF]
