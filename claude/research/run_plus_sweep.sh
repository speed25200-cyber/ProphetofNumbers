#!/bin/sh
# xorshift128+ (V8 Math.random) and xoshiro256+ against the real archive.
# Their state update is F2-linear but the output is a sum, so only bit 0 is exactly
# linear — mode 9 uses that bit alone: one exact equation per draw, 128 or 256
# unknowns, so a few hundred draws suffice. W swept 1..64 covers layouts, extra words
# and interleaved streams.
for g in 8 9; do
  W=1
  while [ "$W" -le 64 ]; do
    ./lin_break "$g" 9 "$W" 4000 0 draws.bin || true
    W=$((W + 1))
  done
done
