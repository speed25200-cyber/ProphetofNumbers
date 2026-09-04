"""SAT state recovery for an F2-linear generator from SORTED keno draws.

The brute-force sweep (seedhunt) covers every state of 32 bits or fewer. This goes
past that without needing the draw order, using one fact about Fisher-Yates:

    the array starts as the identity, so the FIRST ball drawn is exactly j0+1,
    where j0 = (u*80) >> 32 for the first 32-bit output u of that draw.

So "the first ball is one of the 20 published numbers" is a constraint on u alone —
no array logic, no ordering. Keeping only the top 7 bits of u, the constraint is
    "w = u>>25 lies in an allowed subset of 128".  On the 70,560 published
sets, the subset has mean size 44.147 and carries 1.5376 bits per draw.  See
``sorted_prefix_audit.py``; the older 1.9-bit estimate was too optimistic.
Each output bit of an F2-linear generator is a XOR of state bits, so the whole thing
is a CNF over B unknowns: chain the XORs with Tseitin variables, forbid the
disallowed 7-bit prefixes, and let CaDiCaL search.

Usage: python3 satbreak.py [B ...]      (default 32 48 64 80 96 128)
"""
import math, random, sys, time
from pysat.formula import CNF
from pysat.solvers import Cadical153

# ---------------------------------------------------------------- generators
def lfsr_step_matrix(B):
    """Galois LFSR over B bits with a primitive-ish tap set; returns the step as a
    list of B masks (row i = which current bits XOR into new bit i)."""
    taps = {32: [32,22,2,1], 48: [48,47,21,20], 64: [64,63,61,60], 80: [80,79,43,42],
            96: [96,94,49,47], 128: [128,127,126,121]}[B]
    rows = []
    for i in range(B):
        if i > 0:
            rows.append(1 << (i-1))                    # shift
        else:
            rows.append(0)
    fb = 1 << (B-1)                                    # feedback comes from the top bit
    for t in taps:
        if t <= B:
            rows[B-t] ^= fb if (B-t) != B-1 else 0
    rows[0] ^= fb
    return rows

def step(state, rows, B):
    out = 0
    for i in range(B):
        v = state & rows[i]
        out |= (bin(v).count("1") & 1) << i
    return out

def out32(state, B):
    """32-bit output: bits B-1..B-32 of the state (a plain linear window)."""
    if B >= 32:
        return (state >> (B-32)) & 0xffffffff
    return (state << (32-B)) & 0xffffffff

# ---------------------------------------------------------------- symbolic
def sym_forms(B, rows, nout, stride):
    """Linear forms (as B-bit masks over the initial state) of the top 7 bits of the
    first output of each of `nout` draws, the draws being `stride` outputs apart."""
    cur = [1 << i for i in range(B)]                   # bit i = state bit i
    forms = []
    for d in range(nout):
        top = []
        for b in range(32):
            src = (B-32) + b if B >= 32 else b - (32-B)
            top.append(cur[src] if 0 <= src < B else 0)
        forms.append(top[25:32])                       # bits 25..31 -> the 7-bit prefix
        for _ in range(stride):
            nxt = []
            for i in range(B):
                acc = 0
                m = rows[i]
                j = 0
                while m:
                    if m & 1:
                        acc ^= cur[j]
                    m >>= 1; j += 1
                nxt.append(acc)
            cur = nxt
    return forms

def allowed_prefixes(sorted_set):
    """7-bit prefixes w such that some u with u>>25 == w gives a first ball in the set."""
    ok = set()
    for w in range(128):
        lo = w << 25; hi = ((w+1) << 25) - 1
        for u in (lo, hi):
            if ((u*80) >> 32) + 1 in sorted_set:
                ok.add(w); break
        else:
            j0 = (lo*80) >> 32; j1 = (hi*80) >> 32
            if any(j+1 in sorted_set for j in range(j0, j1+1)):
                ok.add(w)
    return ok

# ---------------------------------------------------------------- CNF
class Enc:
    def __init__(self, B):
        self.n = B; self.cnf = CNF()
    def new(self):
        self.n += 1; return self.n
    def xor_chain(self, mask):
        """Variable equal to the XOR of the state bits selected by mask."""
        bits = [i+1 for i in range(mask.bit_length()) if (mask >> i) & 1]
        if not bits:
            z = self.new(); self.cnf.append([-z]); return z
        acc = bits[0]
        for b in bits[1:]:
            z = self.new()
            self.cnf.extend([[-z, acc, b], [-z, -acc, -b], [z, -acc, b], [z, acc, -b]])
            acc = z
        return acc

def build_and_solve(B, ndraws, draws_prefix_sets, forms, budget=900):
    e = Enc(B)
    ws = []
    for d in range(ndraws):
        ws.append([e.xor_chain(m) for m in forms[d]])
    for d in range(ndraws):
        ok = draws_prefix_sets[d]
        for w in range(128):
            if w in ok: continue
            e.cnf.append([(-ws[d][b] if (w >> b) & 1 else ws[d][b]) for b in range(7)])
    t0 = time.time()
    with Cadical153(bootstrap_with=e.cnf) as s:
        r = s.solve()
        el = time.time()-t0
        if not r:
            return None, el, len(e.cnf.clauses), e.n
        mod = s.get_model()
        st = 0
        for i in range(B):
            if mod[i] > 0: st |= 1 << i
        return st, el, len(e.cnf.clauses), e.n

# ---------------------------------------------------------------- driver
def run(B, verbose=True):
    rows = lfsr_step_matrix(B)
    rng = random.Random(0xBEEF + B)
    true_state = rng.getrandbits(B) | 1
    st = true_state
    sets = []
    for d in range(400):
        a = list(range(1, 81)); row = []
        for i in range(20):
            u = out32(st, B); st = step(st, rows, B)
            j = i + ((u*(80-i)) >> 32)
            a[i], a[j] = a[j], a[i]; row.append(a[i])
        sets.append(sorted(row))
    all_pref = [allowed_prefixes(set(row)) for row in sets]
    mean_information = sum(7 - math.log2(len(ok)) for ok in all_pref) / len(all_pref)
    need = int((B + 12) / mean_information) + 1
    forms = sym_forms(B, rows, need, 20)
    pref = all_pref[:need]
    got, el, nc, nv = build_and_solve(B, need, pref, forms)
    ok = (got is not None) and (got == true_state)
    if got is not None and not ok:
        # a different state may still generate the same draws; check that instead
        s2 = got; agree = True
        for d in range(min(40, need)):
            a = list(range(1, 81)); row = []
            for i in range(20):
                u = out32(s2, B); s2 = step(s2, rows, B)
                j = i + ((u*(80-i)) >> 32); a[i], a[j] = a[j], a[i]; row.append(a[i])
            if sorted(row) != sets[d]: agree = False; break
        ok = agree
    print("  B=%3d  draws=%3d  vars=%6d clauses=%7d  solve=%7.2fs  %s"
          % (B, need, nv, nc, el, "STATE RECOVERED" if ok else
             ("wrong state" if got is not None else "UNSAT")))
    return ok, el

if __name__ == "__main__":
    Bs = [int(x) for x in sys.argv[1:]] or [32, 48, 64, 80, 96, 128]
    print("SAT recovery of an F2-linear PRNG state from SORTED keno draws")
    print("  (only first-ball membership is used; information is measured, not assumed)")
    for B in Bs:
        try:
            run(B)
        except Exception as ex:
            print("  B=%3d  failed: %s" % (B, ex))
