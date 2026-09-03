#!/bin/sh
# Sweep every small F2-linear generator x channel x words-per-draw against the real
# archive. Each run is milliseconds: at most 512 unknowns against 2-5.2 bits per draw.
# Channels: 0 bonus=first ball (mulhi)   1 bonus=sorted rank (mulhi)   3 boost only
#           5 bonus rank via u%20        6 first ball via u%80         7 Floyd (k=61)
for g in 0 1 2 3 4 5 6 7; do
  for mode in 0 1 3 5 6 7; do
    for W in 20 21 22 23 24; do
      ./lin_break "$g" "$mode" "$W" 3000 0 draws.bin
    done
  done
done
