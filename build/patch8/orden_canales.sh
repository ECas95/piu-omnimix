#!/bin/bash
set -eu
cd "$(dirname "$0")"
B=/mnt/c/Users/USER/.codex/workspaces/anime_channel_cache/native_build
gcc -m32 -fPIE -pie -O1 -msse2 -I$B/merged17_v363_filter dump_full.c -o /tmp/p8_dump_full -ldl -lpthread -lrt 2>/dev/null
timeout 280 /tmp/p8_dump_full $B/full_validation_engine ../payloads/D/LIST 0 2>/tmp/p8_full.err > "$1";echo "$1 rc $? lines $(wc -l < "$1")"
