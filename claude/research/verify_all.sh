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
gcc -O3 -march=native -o lowlcg        lowlcg.c                  2>/dev/null
gcc -O3 -march=native -o lowlcg2       lowlcg2.c                 2>/dev/null
gcc -O3 -march=native -o lowlcg3       lowlcg3.c                 2>/dev/null
gcc -O3 -march=native -o lcgrank       lcgrank.c                 2>/dev/null
gcc -O3 -march=native -o rankmix       rankmix.c                 2>/dev/null
gcc -O3 -march=native -o rankxo        rankxo.c                  2>/dev/null
gcc -O3 -march=native -o bm            bm.c                      2>/dev/null
gcc -O3 -march=native -o ranklfg       ranklfg.c                 2>/dev/null
gcc -O3 -march=native -o rankw32       rankw32.c                 2>/dev/null
gcc -O3 -march=native -o rankw32       rankw32.c                 2>/dev/null
gcc -O3 -march=native -o rankmwc       rankmwc.c       -lm       2>/dev/null
gcc -O3 -march=native -o rankxo2       rankxo.c                  2>/dev/null
gcc -O3 -march=native -o mrgkiss       mrgkiss.c       -lpthread 2>/dev/null
gcc -O3 -march=native -o multibm       multibm.c                 2>/dev/null
gcc -O3 -march=native -o rankseed2     rankseed.c      -lpthread 2>/dev/null
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
echo "=== 7. lcg_lll at java's modulus: same controls, 2^48 instead of 2^64 ==="
./lcg_lll_c selftest m48

echo
echo "=== 8. lowlcg: a planted state must be recovered in every family ==="
./lowlcg selftest
echo "    (broadened variant: extra nibble positions and the bonus-rank channel)"
./lowlcg2 selftest | tail -4

echo
echo "=== 8 bis. lowlcg3: the increment unknown too — the observable only fixes the"
echo "    orbit up to a translation, so the control asks that nothing be lost, nothing"
echo "    spurious be found, and that survivors predict held-out nibbles ==="
./lowlcg3 selftest | tail -4

echo
echo "=== 8 ter. the sorted draw read as a combinatorial rank (61.6 bits, not 4) ==="
python3 rank.py 2>&1 | grep -E "verified|match exact"
echo "    an arbitrary LCG must be recovered from 3 ranks, mixed streams rejected:"
./lcgrank selftest | grep mode
echo "    an additive state under 6 bijective finalizers:"
./rankmix selftest | grep -E "splitmix|murmur|moremur|rrmxmx|identity|xor-shift"
echo "    the ** scramblers, peeled off by inversion:"
./rankxo  selftest | grep -E "xoshiro|xoroshiro"
echo "    lagged Fibonacci (glibc random(), Boost, add-with-carry):"
./ranklfg selftest | grep -E "glibc|Boost|subtract|xor lagged"
echo "    the rank assembled from two machine words:"
./rankw32 selftest | grep -E "2 x"
echo "    multiply-with-carry, by carry consistency:"
./rankmwc selftest | grep "a="
echo "    MRG32k3a and KISS99, seeded as a programmer seeds them:"
./mrgkiss selftest | tail -2
echo "    both reductions: EVERY rank tool must pass under mulhi too"
for M in 0 1; do
  printf '      reduction %s : ' "$M"
  printf 'ranklfg %s  rankmwc %s  rankw32 %s  rankmix %s  rankxo %s\n' \
    "$(./ranklfg selftest $M | grep -c PASS)" "$(./rankmwc selftest $M | grep -c PASS)" \
    "$(./rankw32 selftest $M | grep -c PASS)" "$(./rankmix selftest $M | grep -c PASS)" \
    "$(./rankxo2 selftest $M | grep -c PASS)"
done
echo "    (expected 4 3 4 6 3 on both lines)"
echo "    the older per-tool spot checks:"
./ranklfg selftest 1 | grep -E "glibc|Boost"
./rankmwc selftest 1 | grep "a=" | head -1
echo "    the 2^32 seed sweep, for this architecture (20 generators):"
./rankseed2 selftest | tail -3
echo "    provably-fair unranking, 23520 schemes:"
python3 rankhash.py 2>&1 | tail -3

echo
echo "=== 8 quinquies. multi-sequence: several planes, ONE recurrence."
echo "    Lifts BM's n/2 bound by noting every linear functional of an F2-linear state"
echo "    obeys the same minimal recurrence. The cut must be two-sided and exact ==="
./multibm selftest | grep -E "planted order|random bits"
echo "    (below the planted order: INCONSISTENT; at or above it: consistent;"
echo "     random bits: INCONSISTENT at every order)"

echo
echo "=== 8 quater. Berlekamp-Massey: the whole F2-linear class without enumerating."
echo "    Complexity must equal the state size, and sit at n/2 for a non-linear source ==="
./bm selftest | tail -4

echo
echo "=== 9. redhash: the reduced compression function must equal hashlib at R=64 ==="
python3 -c "
import sys; sys.path.insert(0, '.')
from redhash import sha256_reduced
import hashlib
m = bytes(range(32))
print('    R=64 matches hashlib:', sha256_reduced(m, 64).hex() == hashlib.sha256(m).hexdigest())"

echo
echo
echo "=== 9 bis. the measurements that constrain the implementation ==="
python3 modbias.py  2>&1 | tail -3
python3 quantize.py 2>&1 | grep "multiples of 512" | head -1
python3 shufbias.py 2>&1 | grep -E "naive shuffle|sort\(random" 
python3 blockseed.py 2>&1 | tail -2

echo
echo "=== 11. bonusseed: the bonus position, the archive's one unsorted channel."
echo "    Fourteen configurations must recover a planted seed WITH its stride and lead,"
echo "    each confirmed by 24/24 boosts; and every reduction must be able to produce"
echo "    all 20 positions -- the surjectivity control that a promoted 32-bit output"
echo "    silently failed (2^32 mod 20 = 16, gcd 4, so only 5 positions reachable) ==="
gcc -O2 -o bonusseed bonusseed.c -lm 2>/dev/null && ./bonusseed selftest | tail -6

echo
echo "=== 12. selsamp: the third architecture (Knuth 3.4.2 S). The numbers come out"
echo "    already sorted, one call per candidate, every threshold computable from the"
echo "    published draw. A planted seed must be recovered in both stop variants ==="
gcc -O2 -o selsamp selsamp.c -lm 2>/dev/null && ./selsamp selftest | tail -5

echo
echo "=== 13. pcg64seed: PCG64 at 128 bits, seeded case, XSL-RR and DXSM ==="
gcc -O2 -o pcg64seed pcg64seed.c 2>/dev/null && ./pcg64seed selftest | tail -4

echo
echo "=== 14. lcgident: the identity d1^2 = d0*d2 covers EVERY LCG mod 2^64 --"
echo "    any multiplier, any increment, any stride -- with no unknowns. Planted LCGs"
echo "    must be seen, uniform ranks must not ==="
python3 lcgident.py 2>&1 | grep -E "RECOVERED|PASS|FAIL" | head -5

echo
echo "=== 15. rankgaps: the output width. A planted lattice must be recovered from"
echo "    24 up to 58 bits -- the 58 is the one that matters, three bits from the"
echo "    61.6-bit ceiling -- and a uniform stream must show none ==="
python3 rankgaps.py 2>&1 | grep -E "RECOVERED|FAIL|controles" | head -8

echo
echo "=== 16. poslll: the lattice on the bonus position. The usable K is the smallest"
echo "    that recovers AND rejects a wrong multiplier, a wrong stride and pure noise."
echo "    K=12 recovers but accepts all three, so it proves nothing ==="
gcc -O2 -o poslll poslll.c -lm 2>/dev/null && ./poslll selftest | tail -4

echo
echo "=== 17. multibm: the multi-sequence bound, controlled AT THE SIZE CLAIMED."
echo "    The small selftest cannot see the failure that mattered: at n=6000 one plane"
echo "    already supplies enough rows, so a rank deficiency never shows ==="
gcc -O2 -o multibm5 multibm.c 2>/dev/null && ./multibm5 selftest | tail -7

echo
echo "=== 18. backtest: the question as asked. A biased archive must be beaten by"
echo "    'hot numbers'; a fair one must not be beaten by anything ==="
python3 backtest.py 2>&1 | grep -E "CONTROLE PASSE|CONTROLE ECHOUE|plus grand" | head -4

echo
echo "=== 10. calibration: a breakable xorshift32 is statistically invisible ==="
echo "    (see calib.py; it takes a few minutes, run it separately)"

echo
echo "All controls above must read as stated in RECHERCHE.md. They are what makes the"
echo "negative results on the real archive mean anything."
