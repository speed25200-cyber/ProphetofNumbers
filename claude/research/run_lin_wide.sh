#!/bin/sh
# Wide sweep over words-per-draw. A large W also covers interleaved streams: if two
# servers alternate draws, one stream sees every second draw, which is the same thing
# as doubling W. Sweeping W from 1 to 64 therefore covers layouts, extra words, and
# interleaving up to three ways, for every small F2-linear generator and channel.
for g in 0 1 2 3 4 5 6 7; do
  for mode in 0 1 5 6 7 8 3; do
    W=1
    while [ "$W" -le 64 ]; do
      ./lin_break "$g" "$mode" "$W" 4000 0 draws.bin
      W=$((W + 1))
    done
  done
done
