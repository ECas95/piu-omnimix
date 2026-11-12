#!/bin/bash
# Fails unless the new catalog, with our module's hooks, gives in every Basic Mode channel the very list the bare engine gives on the official catalog
# (same songs, same order, same charts in the same order). build_patch8.py checks that each helper's field 4 names its own media song.
set -eu
cd "$(dirname "$0")"
B=/mnt/c/Users/USER/.codex/workspaces/anime_channel_cache/native_build
gcc -m32 -fPIE -pie -O1 -msse2 -I$B/merged17_v363_filter dump_basic.c -o /tmp/p8_dump_basic -ldl -lpthread -lrt 2>/dev/null
timeout 200 /tmp/p8_dump_basic $B/full_validation_engine oficial/official.LIST stock 2>/dev/null > /tmp/p8_official.txt
timeout 200 /tmp/p8_dump_basic $B/full_validation_engine ../payloads/D/LIST hooks 2>/dev/null > /tmp/p8_new.txt
echo "official $(grep -m1 CHANNEL /tmp/p8_official.txt)  new $(grep -m1 CHANNEL /tmp/p8_new.txt)"
cmp /tmp/p8_official.txt /tmp/p8_new.txt
python3 - <<'PY'
ok=0
for l in open('/tmp/p8_new.txt'):
    if l.startswith('CHANNEL'):continue
    p=l.split();i=int(p[1][3:],16);ok+=1   # the engine groups these runs by media song; every chart must come from that song's own helper
    assert all(int(c.split(':')[0],16)==i and int(c.split(':')[1],16)==0xE0000000|i for c in p[3:]),l
print('every chart comes from its own song',ok)
PY
echo BASIC_IGUAL_AL_ORIGINAL
