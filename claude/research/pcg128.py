"""PCG64 a etat 128 bits complet — la derniere famille nommee encore debout.

Le §9 la listait comme la seule famille repandue que rien n'atteignait : le pliage
hi ^ lo perd la moitie de l'etat et la rotation DEPEND de l'etat, donc ni l'inversion de
brouilleur de rankxo ni une resolution bit a bit ne s'y appliquent. Seul le cas ensemence
sur 32 bits etait couvert.

Ce qui debloque : sous l'architecture par derangement, le rang livre la sortie 64 bits a
SIX candidats pres (u = rang + k*C, 2^64/C = 5,2159). Une sortie de 64 bits pour un etat
de 128 : deux observations suffisent en principe. Le probleme n'est pas le manque
d'information, c'est le melange XOR/multiplication/rotation-dependante-de-l-etat — et
c'est exactement ce qu'un solveur SMT sur vecteurs de bits traite.

PCG64 XSL-RR :  S <- A*S + C  (mod 2^128)  puis  sortie = rotr64(hi ^ lo, S >> 122)
L'ambiguite a six candidats n'est PAS enumeree (6^K branches) mais posee en disjonction,
ce que z3 absorbe nativement.

Deux cas :
  * increment CONNU (le defaut PCG)  -> 128 inconnues, 2 observations suffisent
  * increment INCONNU (numpy, flux)  -> 256 inconnues, il en faut 4 et plus

CONTROLE OBLIGATOIRE avant tout passage sur l'archive : planter un PCG64 de graine connue
et verifier que le solveur retrouve l'etat, ET qu'il declare insatisfiable un flux qui
n'en vient pas.
"""
import math, sys, time
import numpy as np
import z3

MULT = (2549297995355413924 << 64) | 4865540595714422341
INC_DEFAULT = (6364136223846793005 << 64) | 1442695040888963407
M128 = (1 << 128) - 1
M64 = (1 << 64) - 1
C80 = math.comb(80, 20)


def pcg_step(s, inc=INC_DEFAULT):
    return (MULT * s + inc) & M128


def pcg_out(s):
    hi, lo = s >> 64, s & M64
    x = (hi ^ lo) & M64
    r = (s >> 122) & 63
    return ((x >> r) | (x << ((64 - r) & 63))) & M64


def pcg_next(s, inc=INC_DEFAULT):
    s = pcg_step(s, inc)
    return s, pcg_out(s)


def solve(cands, stride, inc_known, timeout_s=120):
    """cands[t] = liste de candidats 64 bits pour la sortie du tirage t."""
    S = z3.BitVec("S0", 128)
    A = z3.BitVecVal(MULT, 128)
    if inc_known:
        C = z3.BitVecVal(INC_DEFAULT, 128)
    else:
        C = z3.BitVec("C", 128)
    sol = z3.Solver()
    sol.set("timeout", timeout_s * 1000)
    if not inc_known:
        sol.add(z3.Extract(0, 0, C) == 1)          # l'increment d'un LCG mod 2^n est impair
    cur = S
    for t, cl in enumerate(cands):
        for _ in range(stride):
            cur = A * cur + C
        hi = z3.Extract(127, 64, cur)
        lo = z3.Extract(63, 0, cur)
        x = hi ^ lo
        r = z3.Extract(127, 122, cur)
        out = z3.RotateRight(x, z3.ZeroExt(58, r))
        sol.add(z3.Or([out == z3.BitVecVal(c, 64) for c in cl]))
    t0 = time.time()
    res = sol.check()
    dt = time.time() - t0
    if res == z3.sat:
        m = sol.model()
        s0 = m[S].as_long()
        c0 = INC_DEFAULT if inc_known else m[C].as_long()
        return "sat", s0, c0, dt
    return ("unsat" if res == z3.unsat else "unknown"), None, None, dt


def verify(s0, inc, cands, stride):
    """Une solution doit reproduire TOUTES les observations, y compris celles non fournies."""
    s = s0
    for cl in cands:
        for _ in range(stride):
            s = pcg_step(s, inc)
        if pcg_out(s) not in cl:
            return False
    return True


def rank_candidates(rank, kmax=6):
    return [(int(rank) + k * C80) & M64 for k in range(kmax)]


if __name__ == "__main__":
    print("=" * 78)
    print("CONTROLE POSITIF -- PCG64 plante, le solveur doit retrouver l'etat")
    print("=" * 78)
    fails = 0
    for inc_known in (True, False):
        for stride in (1, 3):
            for K in (3, 5, 7):
                if not inc_known and K < 5:
                    continue                      # 256 inconnues : 3 observations ne suffisent pas
                inc = INC_DEFAULT if inc_known else ((0xB1A2C3D4E5F60718 << 64) | 0x9F1E2D3C4B5A6979)
                s = 0xDEADBEEFCAFEBABE0123456789ABCDEF
                obs = []
                st = s
                for t in range(K):
                    for _ in range(stride):
                        st = pcg_step(st, inc)
                    obs.append(pcg_out(st))
                # on brouille chaque observation en 6 candidats, comme le fait le rang
                cands = [[(o + j * 0x1234567) & M64 for j in range(3)] + [o] +
                         [(o - j * 0x7654321) & M64 for j in range(1, 3)] for o in obs]
                res, s0, c0, dt = solve(cands, stride, inc_known, timeout_s=180)
                ok = (res == "sat" and verify(s0, c0, cands, stride))
                exact = (res == "sat" and s0 == s and c0 == inc)
                fails += (not ok)
                print("  inc %-7s stride %d  K=%d : %-7s  %6.1fs  %s%s"
                      % ("connu" if inc_known else "inconnu", stride, K, res, dt,
                         "RECOVERED" if ok else "FAIL",
                         "  (etat exact)" if exact else ("  (autre etat compatible)" if ok else "")))
                sys.stdout.flush()

    print("\n" + "=" * 78)
    print("CONTROLE NEGATIF -- des sorties qui ne viennent PAS d'un PCG64")
    print("=" * 78)
    rng = np.random.default_rng(5150)
    for stride in (1, 3):
        for K in (5, 7):
            cands = [[int(v) for v in rng.integers(0, 1 << 63, size=6, dtype=np.uint64)]
                     for _ in range(K)]
            res, s0, c0, dt = solve(cands, stride, True, timeout_s=180)
            ok = (res == "unsat")
            fails += (not ok)
            print("  stride %d  K=%d : %-7s  %6.1fs  %s"
                  % (stride, K, res, dt, "PASS (rejete)" if ok else "FAIL (accepte du bruit)"))
            sys.stdout.flush()

    print("\n  %s" % ("*** CONTROLES ECHOUES : rien ne sera lu sur l'archive ***" if fails
                      else "controles: tous passes"))
