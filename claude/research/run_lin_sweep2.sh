#!/bin/sh
# Second sweep: what if the boost and bonus come from their OWN generator instance
# rather than the one drawing the numbers? Then they advance one word per draw, not
# twenty-something, so W is small. Channels at r=0: 0,1,5,6,7 for bonus, 8 for boost.
for g in 0 1 2 3 4 5 6 7; do
  for mode in 0 1 5 6 7 8; do
    for W in 1 2 3 4; do
      ./lin_break "$g" "$mode" "$W" 4000 0 draws.bin
    done
  done
done
