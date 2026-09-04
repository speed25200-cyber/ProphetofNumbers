"""SAT state recovery for splitmix64 — the delta-chain move applied to the draw feed.

GF(2) elimination reaches the F2-linear generators; lattice reduction reaches a 64-bit
LCG with a truncated output. Neither touches a generator whose output is a bijective
*mix*: splitmix64 advances its state by a constant and pushes it through two 64-bit
multiplications, which is precisely the carry barrier the sibling delta-chain repo
studies. There, the tool of choice is SAT, so that is what this does.

Setup. The state is a counter: s_d = s_0 + d*Delta (mod 2^64) with Delta = W*gamma,
so there is exactly one unknown, the 64 bits of s_0. If the bonus is the first ball
drawn then bonus-1 = (u*80)>>32 pins u to an interval, i.e. about 6.3 leading bits of
the mix output per draw — eleven draws over-determine 64 unknowns. No Fisher-Yates
array has to be encoded at all, only the mix and one interval comparison.

Encoding notes. Multiplication is by a *constant*, so it is a shift-and-add tree over
the set bits of the constant rather than a general 64x64 multiplier: 31 ripple-carry
additions instead of 4096 partial products. Xorshifts are pure wiring and cost nothing.

Run the self-test first: if SAT cannot recover a synthetic splitmix64 whose parameters
are known, no negative result on the real archive means anything.

  python3 satmix.py selftest [ndraws] [timeout_s]
  python3 satmix.py real     [ndraws] [timeout_s] [maxW]
"""
import sys, time
from pysat.formula import CNF
from pysat.solvers import Cadical153

M64 = (1 << 64) - 1
GAMMA = 0x9E3779B97F4A7C15
C1 = 0xBF58476D1CE4E5B9
C2 = 0x94D049BB133111EB

def splitmix_next(state):
    state = (state + GAMMA) & M64
    z = state
    z = ((z ^ (z >> 30)) * C1) & M64
    z = ((z ^ (z >> 27)) * C2) & M64
    return state, (z ^ (z >> 31)) & M64

class Enc:
    """Bit-blasting helper. A 'word' is a list of 64 literals, index 0 = LSB.
    Literal 0 is the constant false, -0 is unusable, so a dedicated FALSE var is kept."""
    def __init__(self):
        self.cnf = CNF(); self.n = 0
        self.FALSE = self.new(); self.cnf.append([-self.FALSE])
        self.TRUE = -self.FALSE
    def new(self):
        self.n += 1; return self.n
    def word(self): return [self.new() for _ in range(64)]
    def xor(self, a, b):
        z = self.new()
        self.cnf.extend([[-z, a, b], [-z, -a, -b], [z, -a, b], [z, a, -b]])
        return z
    def and2(self, a, b):
        z = self.new()
        self.cnf.extend([[-z, a], [-z, b], [z, -a, -b]])
        return z
    def maj(self, a, b, c):
        z = self.new()
        self.cnf.extend([[-z, a, b], [-z, a, c], [-z, b, c],
                         [z, -a, -b], [z, -a, -c], [z, -b, -c]])
        return z
    def wxor(self, A, B): return [self.xor(a, b) for a, b in zip(A, B)]
    def wshr(self, A, k): return A[k:] + [self.FALSE]*k          # logical right shift
    def wshl(self, A, k): return [self.FALSE]*k + A[:64-k]
    def wadd(self, A, B):
        out = []; carry = self.FALSE
        for i in range(64):
            s = self.xor(self.xor(A[i], B[i]), carry)
            out.append(s)
            if i < 63: carry = self.maj(A[i], B[i], carry)
        return out
    def wadd_const(self, A, k):
        """A + k with k a literal constant: the constant bit picks the gate, so this
        costs one xor and one and/or per position instead of a full adder."""
        out = []; carry = self.FALSE
        for i in range(64):
            t = self.xor(A[i], carry)
            if (k >> i) & 1:
                out.append(-t)                          # sum bit = A ^ carry ^ 1
                if i < 63:
                    c = self.new()                      # carry out = A OR carry
                    self.cnf.extend([[-c, A[i], carry], [c, -A[i]], [c, -carry]])
                    carry = c
            else:
                out.append(t)                           # sum bit = A ^ carry
                if i < 63:
                    carry = self.and2(A[i], carry)      # carry out = A AND carry
        return out
    def wmul_const(self, A, k):
        acc = None
        for i in range(64):
            if (k >> i) & 1:
                term = self.wshl(A, i)
                acc = term if acc is None else self.wadd(acc, term)
        return acc if acc is not None else [self.FALSE]*64
    def fix_range(self, A, lo, hi):
        """Constrain the 64-bit word A to [lo, hi] by fixing the bits lo and hi share."""
        x = lo ^ hi
        nb = 64 - x.bit_length() if x else 64
        for b in range(63, 63-nb, -1):
            self.cnf.append([A[b]] if ((lo >> b) & 1) else [-A[b]])
        return nb

def build(centres_lo_hi, W, ndraws):
    """centres_lo_hi[d] = (lo, hi) interval the d-th mix output must land in."""
    e = Enc()
    s0 = e.word()
    delta = (W * GAMMA) & M64
    known = 0
    for d in range(ndraws):
        state = s0 if d == 0 else e.wadd_const(s0, (d*delta) & M64)
        z = e.wxor(state, e.wshr(state, 30)); z = e.wmul_const(z, C1)
        z = e.wxor(z, e.wshr(z, 27));         z = e.wmul_const(z, C2)
        out = e.wxor(z, e.wshr(z, 31))
        lo, hi = centres_lo_hi[d]
        known += e.fix_range(out, lo, hi)
    return e, s0, known

def interval_from_bonus(j):
    """u = out >> 32 and bonus-1 = (u*80)>>32, so out lies in this 64-bit interval."""
    lo = (j << 32)//80 + (1 if ((j << 32) % 80) else 0)
    hi = ((j+1) << 32)//80 + (1 if (((j+1) << 32) % 80) else 0) - 1
    return lo << 32, (hi << 32) | 0xFFFFFFFF

def run(intervals, W, ndraws, budget, expect=None):
    t0 = time.time()
    e, s0, known = build(intervals, W, ndraws)
    built = time.time()-t0
    print("    %d draws, %d known bits, %d vars, %d clauses  [built in %.1fs]"
          % (ndraws, known, e.n, len(e.cnf.clauses), built))
    t0 = time.time()
    with Cadical153(bootstrap_with=e.cnf) as sol:
        sol.conf_budget(budget)
        r = sol.solve_limited(expect_interrupt=False)
        el = time.time()-t0
        if r is None:
            print("    -> budget exhausted after %.0fs (no verdict)" % el); return None
        if not r:
            print("    -> UNSAT in %.0fs" % el); return False
        mod = sol.get_model(); pos = set(x for x in mod if x > 0)
        got = 0
        for i, v in enumerate(s0):
            if v in pos: got |= 1 << i
        print("    -> SAT in %.0fs, s0 = 0x%016X%s" % (el, got,
              "" if expect is None else ("  MATCHES" if got == expect else "  (other solution)")))
        return got

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "selftest"
    nd = int(sys.argv[2]) if len(sys.argv) > 2 else 14
    budget = int(sys.argv[3]) if len(sys.argv) > 3 else 400000
    if mode == "selftest":
        W = 21
        # S_d is the state value mixed at draw d; S_{d+1} = S_d + W*GAMMA.
        S0 = 0xC0FFEE1234567890
        delta = (W*GAMMA) & M64
        ivs = []
        for d in range(nd):
            Sd = (S0 + d*delta) & M64
            z = Sd
            z = ((z ^ (z >> 30))*C1) & M64
            z = ((z ^ (z >> 27))*C2) & M64
            out = (z ^ (z >> 31)) & M64
            j = ((out >> 32)*80) >> 32
            lo, hi = interval_from_bonus(j)
            assert lo <= out <= hi, "interval must contain the true output"
            ivs.append((lo, hi))
        print("selftest: synthetic splitmix64, W=%d, bonus = first ball, hidden s0" % W)
        print("  a positive result is required before any real run\n")
        run(ivs, W, nd, budget, expect=S0)
    else:
        from load import load
        ids, ts, nums, boost, bonus = load()
        maxW = int(sys.argv[4]) if len(sys.argv) > 4 else 4
        print("real archive, splitmix64 hypothesis, %d draws, W = 1..%d\n" % (nd, maxW))
        for W in range(1, maxW+1):
            ivs = [interval_from_bonus(int(bonus[d])-1) for d in range(nd)]
            print("  W=%d" % W)
            run(ivs, W, nd, budget)
