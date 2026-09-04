#!/bin/sh
# wait for the 16-generator sweep to finish, then cover the four modern ones
while pgrep -f "rankseed rank_colex0" >/dev/null 2>&1; do sleep 60; done
echo "=== modern generators, exhaustive 2^32, draw 0 ==="
./rankseed2 rank_colex0.bin 0 0 4294967296 4 16 20
