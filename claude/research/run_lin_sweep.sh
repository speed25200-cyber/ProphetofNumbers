#!/bin/sh
# Sweep every small F2-linear generator x channel x words-per-draw against the real archive.
# Each run is milliseconds: 5.2 bits per draw against at most 512 unknowns.
for g in 0 1 2 3 4 5 6 7; do
  for mode in 0 1 3; do
    for W in 20 21 22 23 24; do
      ./lin_break "$g" "$mode" "$W" 3000 0 draws.bin
    done
  done
done
