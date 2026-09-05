#!/bin/sh
# Seeds derived from a nanosecond clock at the draw moment. Draw 0 is at unix
# 1757829900, so the window is +/- 0.5 s around it: 10^9 candidate seeds, which is
# what a system seeding from nanotime would actually have. Beyond the 2^32 sweep.
LO=1757829899500000000
HI=1757829900500000000
for g in 0 1 2 3 4 5 6 7 8 9 10 11 14 15; do
  ./seedhunt 0 "$LO" "$HI" 4 "$g"
done
