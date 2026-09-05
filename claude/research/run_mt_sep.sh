#!/bin/sh
# MT19937 under the "bonus/boost have their own generator instance" hypothesis:
# they advance a small number of words per draw instead of twenty-something.
# Draw counts are sized so each channel supplies well past the 19937 bits needed.
for W in 1 2 3 4; do
  ./channel_break 0 "$W"  6000 1 0 0 1 draws.bin | grep -E 'p=|BREAK|no consistent' | tr '\n' ' '
  echo "   <- mode 0 (bonus=first ball, mulhi) W=$W"
  ./channel_break 1 "$W"  9000 1 0 0 1 draws.bin | grep -E 'p=|BREAK|no consistent' | tr '\n' ' '
  echo "   <- mode 1 (bonus=sorted rank, mulhi) W=$W"
  ./channel_break 6 "$W"  7500 1 0 0 1 draws.bin | grep -E 'p=|BREAK|no consistent' | tr '\n' ' '
  echo "   <- mode 6 (bonus=first ball, u%80) W=$W"
  ./channel_break 7 "$W"  6500 1 0 0 1 draws.bin | grep -E 'p=|BREAK|no consistent' | tr '\n' ' '
  echo "   <- mode 7 (bonus=first ball, Floyd k=61) W=$W"
  ./channel_break 8 "$W" 26000 1 0 0 1 draws.bin | grep -E 'p=|BREAK|no consistent' | tr '\n' ' '
  echo "   <- mode 8 (boost, own stream) W=$W"
done
