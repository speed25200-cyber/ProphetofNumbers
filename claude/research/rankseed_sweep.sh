#!/bin/sh
# The 2^32 sweep for the unranking architecture, plus the clock windows that reach
# past 2^32 (millisecond and nanosecond seeds are 1.76e12 and 1.76e18, out of range).
set -e
echo "=== exhaustive 2^32, draw 0 ==="
./rankseed rank_colex0.bin 0 0 4294967296 4
for IDX in 0 1 35280 70559; do
  T=$(python3 -c "
from load import load
ids,ts,nums,boost,bonus=load(); print(int(ts[$IDX]))")
  echo "=== draw $IDX, ts=$T : millisecond window +/-1e7 ==="
  ./rankseed rank_colex0.bin $IDX $(( T*1000 - 10000000 )) $(( T*1000 + 10000000 )) 4
  echo "=== draw $IDX, ts=$T : nanosecond window +/-1e7 ==="
  ./rankseed rank_colex0.bin $IDX $(( T*1000000000 - 10000000 )) $(( T*1000000000 + 10000000 )) 4
done
echo "=== also the draw id as seed, exact and offset, over all draws ==="
./rankseed rank_colex0.bin 0 1309614 1309615 1
