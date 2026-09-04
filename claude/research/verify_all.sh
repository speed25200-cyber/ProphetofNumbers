#!/bin/sh
# Every negative result in RECHERCHE.md rests on a tool actually working. This runs
# each tool's positive control (it must find a planted answer) and its negative
# controls (it must reject wrong hypotheses). If any line below is wrong, the
# corresponding exclusion in the write-up is worthless and must be withdrawn.
set -e
cd "$(dirname "$0")"

echo "=== building ==="
gcc -O3 -march=native -o seedhunt      seedhunt.c      -lpthread 2>/dev/null
gcc -O3 -march=native -o pairs         pairs.c         -lpthread -lm 2>/dev/null
gcc -O3 -march=native -o mtbreak       mtbreak.c                 2>/dev/null
gcc -O3 -march=native -o keno_break    keno_break.c              2>/dev/null
gcc -O3 -march=native -o channel_break channel_break.c -lpthread 2>/dev/null
gcc -O3 -march=native -o lin_break     lin_break.c               2>/dev/null
gcc -O3               -o lcg_lll_c     lcg_lll.c       -lm       2>/dev/null
python3 mkdata.py >/dev/null

echo
echo "=== 1. seedhunt: plant a known seed, it must be recovered ==="
./seedhunt 0 0 3000000 4 -1 "0,1,0,1234567" 2>&1 | grep -E "!!|minstd16807    mulhi        fisher_yates_fwd"

echo
echo "=== 2. mtbreak: MT19937 from 400 ordered draws, future draws must be predicted ==="
./mtbreak 400 0xC0FFEE42 0 2>&1 | tail -2

echo
echo "=== 3. keno_break: must name the sampler AND refuse a sorted feed ==="
python3 make_demo_capture.py >/dev/null
./keno_break scanfile ordered_demo.txt 2>&1 | tail -2
./keno_break scanfile sorted_demo.txt  2>&1 | tail -1

echo
echo "=== 4. channel_break: right model consistent, wrong W rejected ==="
python3 make_channel_synth.py 5500 173 >/dev/null
./channel_break 0 22 5500 1 0 0 1 draws_synth.bin 2>&1 | grep -E "p=|BREAK|no consistent"
./channel_break 0 21 5500 1 0 0 1 draws_synth.bin 2>&1 | grep -E "p=|BREAK|no consistent"

echo
echo "=== 5. lin_break: right generator consistent, three wrong ones rejected ==="
python3 make_lin_synth.py 300 >/dev/null
./lin_break 0 0 21 60 0 draws_lin.bin
./lin_break 1 0 21 60 0 draws_lin.bin || true
./lin_break 2 0 21 60 0 draws_lin.bin || true
./lin_break 0 0 20 60 0 draws_lin.bin || true

echo
echo "=== 6. lcg_lll: LCG64 recovered, wrong W / wrong multiplier / random data rejected ==="
./lcg_lll_c selftest

echo
echo "=== 7. calibration: a breakable xorshift32 is statistically invisible ==="
echo "    (see calib.py; it takes a few minutes, run it separately)"

echo
echo "All controls above must read as stated in RECHERCHE.md. They are what makes the"
echo "negative results on the real archive mean anything."
