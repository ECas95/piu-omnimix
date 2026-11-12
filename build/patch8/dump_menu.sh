#!/bin/bash
cd "$(dirname "$0")"
B=/mnt/c/Users/USER/.codex/workspaces/anime_channel_cache/native_build
gcc -m32 -fPIE -pie -O1 -msse2 -I$B/merged17_v363_filter dump_menu.c -o /tmp/p8_dump_menu -ldl -lpthread -lrt 2>/dev/null
timeout 200 /tmp/p8_dump_menu $B/full_validation_engine ../payloads/D/LIST 2>/tmp/p8_menu.err > menu.txt;echo "rc $?"
tail -1 /tmp/p8_menu.err | cut -c1-150
