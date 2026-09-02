"""h135 — TÉMOIN : l'état bas du Fibonacci retardé devant un solveur SAT à
raisonnement XOR, sur 204 tirages TRIÉS à pas constant (les deux mots sûrs).

CE QUE LE §153 A LAISSÉ
=======================
Le §153 donne à z3 les 5L bits bas de la récurrence r_i = r_{i-K} + r_{i-L}
mod 2^32 et l'appartenance des nibbles (v-1) mod 16 aux classes présentes ;
à L = 7 le solveur rend `unknown` en 300 s là où l'énumération (§155) fait
2^35 en 20 s. Sa conclusion : une contrainte d'appartenance ne propage rien
tant que les antécédents ne sont pas fixés, et un solveur générique retombe
sur l'énumération.

CE QUE CE TÉMOIN ESSAIE
=======================
La même question posée AUTREMENT : (i) le problème est écrit au niveau du
BIT, l'additionneur mod 32 en portes XOR/majorité, et non en vecteurs de
bits pour un solveur SMT ; (ii) le solveur est CryptoMiniSat, qui porte les
XOR en natif (élimination de Gauss-Jordan pendant la recherche), et CaDiCaL
en comparaison ; (iii) le régime est celui de l'archive à pas constant :
204 tirages consécutifs, deux mots sûrs par tirage (positions 0 et 16, lemme
du §152), soit 408 nibbles contraints et 152 bits d'information.

Le théorème des trois plans muets (THEORIE_ETAT §7.10) dit pourquoi cela
peut marcher : les plans 0..2 fixés, les plans 3 et 4 sont AFFINES sur F_2
— chaque nibble forcé donne une équation linéaire, et c'est précisément ce
que Gauss-Jordan propage. Il dit aussi le coût de l'énumération des plans
0..2 : 2^{3L}, 2^45 pour TYPE_2 (1, 15) — hors d'une session. La question
est donc : le solveur fait-il mieux que 2^{3L} ?

CE QU'IL MESURE
===============
Pour (K, L) = (3, 7) TYPE_1, (1, 15) TYPE_2, (3, 31) TYPE_3 : un état 32 bits
planté, 204 tirages par Fisher-Yates partiel (modulo, pas 20), masques au
format de l'archive ; le solveur doit rendre l'état bas planté, puis, l'état
bloqué, rendre UNSAT (unicité = puissance d'exclusion). Un jeu de masques
d'un AUTRE état (contrôle) doit rendre UNSAT — sauf quand 5L dépasse les 152
bits d'information (TYPE_3 : 155 inconnues), où des solutions parasites sont
attendues et comptées.

TÉMOIN D'OUTIL : aucune donnée du dossier n'est lue, aucune ligne de registre.
Réglages : H135_TIMEOUT (s, défaut 1800 ; borne effective de CryptoMiniSat),
H135_CONF (budget de conflits de CaDiCaL, défaut 3·10^6 — son minuteur est
inopérant, l'extension gardant le GIL), H135_LAGS ("3,7 1,15 3,31"),
H135_SOLVEURS ("cms cadical"), H135_N (tirages, défaut 204).
"""

import os
import random
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lfg_releve import suite_basse  # noqa: E402  (référence pour l'état bas)

T0 = time.time()
POOL, DRAWN = 80, 20
PAS = 20
SURS = (0, 16)                      # les deux mots sûrs du Fisher-Yates par modulo
TIMEOUT = float(os.environ.get("H135_TIMEOUT", "1800"))
LAGS = [tuple(int(x) for x in s.split(",")) for s in os.environ.get("H135_LAGS", "3,7 1,15 3,31").split()]
SOLVEURS = os.environ.get("H135_SOLVEURS", "cms cadical").split()
N = int(os.environ.get("H135_N", "204"))
GRAINE = int(os.environ.get("H135_GRAINE", "20260902"))
CONF_BUDGET = int(os.environ.get("H135_CONF", "3000000"))   # budget de conflits de CaDiCaL


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78 + ("\n" + t if t else "") + ("\n" + "=" * 78 if t else ""))


# ---------------------------------------------------------------- générateur

def lfg(etat, K, L, n):
    """r_i = r_{i-K} + r_{i-L} mod 2^32 ; rend les n premiers mots (dont les L initiaux)."""
    r = list(etat)
    for i in range(L, n):
        r.append((r[i - K] + r[i - L]) & 0xFFFFFFFF)
    return r


def tirage_modulo(seq, p):
    arr = list(range(1, POOL + 1))
    out = []
    for k in range(DRAWN):
        j = k + (seq[p + k] >> 1) % (POOL - k)
        arr[k], arr[j] = arr[j], arr[k]
        out.append(arr[k])
    return sorted(out), p + DRAWN


def masques_de(etat, K, L, n):
    seq = lfg(etat, K, L, n * PAS)
    ms, p = [], 0
    for _ in range(n):
        S, p = tirage_modulo(seq, p)
        m = 0
        for v in S:
            m |= 1 << ((v - 1) % 16)
        ms.append(m)
    return ms


# ---------------------------------------------------------------- encodage

class Cnf:
    """Formule au niveau du bit : 5 variables par mot, retenues, XOR natifs ou en CNF."""

    def __init__(self, xor_natif):
        self.nv = 0
        self.clauses = []
        self.xors = []               # (liste de variables, parité) : XOR(vars) = parité
        self.xor_natif = xor_natif

    def var(self):
        self.nv += 1
        return self.nv

    def xor(self, vs, parite):
        if self.xor_natif:
            self.xors.append((list(vs), parite))
            return
        # XOR(vs) = parite en CNF : toute affectation de parité opposée est interdite
        k = len(vs)
        for m in range(1 << k):
            bits = [(m >> j) & 1 for j in range(k)]
            if sum(bits) % 2 != parite:
                self.clauses.append([(-v if b else v) for v, b in zip(vs, bits)])

    def et(self, c, a, b):
        self.clauses += [[-c, a], [-c, b], [c, -a, -b]]

    def maj(self, c, a, b, d):
        self.clauses += [[-c, a, b], [-c, a, d], [-c, b, d], [c, -a, -b], [c, -a, -d], [c, -b, -d]]


def encode(K, L, masques, xor_natif):
    """Rend (formule, mots) : mots[i] = les 5 variables (bits 0..4) du mot i."""
    f = Cnf(xor_natif)
    n_mots = (len(masques) - 1) * PAS + max(SURS) + 1
    mots = [[f.var() for _ in range(5)] for _ in range(n_mots)]
    for i in range(L, n_mots):
        a, b, s = mots[i - K], mots[i - L], mots[i]
        c = f.var()                                   # retenue vers le bit 1
        f.xor([s[0], a[0], b[0]], 0)
        f.et(c, a[0], b[0])
        for k in range(1, 5):
            f.xor([s[k], a[k], b[k], c], 0)
            if k < 4:
                c2 = f.var()
                f.maj(c2, a[k], b[k], c)
                c = c2
    for t, m in enumerate(masques):
        for k in SURS:
            s = mots[t * PAS + k]
            for u in range(16):
                if not (m >> u) & 1:               # résidu absent : nibble != u
                    f.clauses.append([(-s[1 + j] if (u >> j) & 1 else s[1 + j]) for j in range(4)])
    return f, mots


# ---------------------------------------------------------------- résolution

def resoudre(nom, f, mots, L, timeout, bloques=()):
    """Rend ('sat', état bas [r_0..r_{L-1}] mod 32) | ('unsat', None) | ('timeout', None), secondes."""
    t0 = time.time()
    init = [v for w in mots[:L] for v in w]
    if nom == "cms":
        import pycryptosat
        s = pycryptosat.Solver(threads=1, time_limit=timeout)
        for c in f.clauses:
            s.add_clause(c)
        for vs, p in f.xors:
            s.add_xor_clause(vs, bool(p))
        for bl in bloques:
            s.add_clause(bl)
        res, sol = s.solve()
        dt = time.time() - t0
        if res is None:
            return "timeout", None, dt
        if not res:
            return "unsat", None, dt
        etat = [sum((1 << k) for k in range(5) if sol[mots[i][k]]) for i in range(L)]
        return "sat", etat, dt
    from pysat.solvers import Solver
    s = Solver(name="cadical195")
    for c in f.clauses:
        s.add_clause(c)
    for bl in bloques:
        s.add_clause(bl)
    # Le minuteur seul est inopérant : l'extension C garde le GIL pendant solve_limited et
    # le fil du minuteur ne s'exécute jamais (constaté : 50 min sans interruption). La borne
    # effective est un budget de CONFLITS (H135_CONF, défaut 3·10^6 ≈ 300 s sur cette machine).
    s.conf_budget(CONF_BUDGET)
    timer = threading.Timer(timeout, lambda: s.interrupt())
    timer.start()
    res = s.solve_limited(expect_interrupt=True)
    timer.cancel()
    dt = time.time() - t0
    if res is None:
        s.delete()
        return "timeout", None, dt
    if not res:
        s.delete()
        return "unsat", None, dt
    model = set(v for v in s.get_model() if v > 0)
    etat = [sum((1 << k) for k in range(5) if mots[i][k] in model) for i in range(L)]
    s.delete()
    return "sat", etat, dt


def clause_blocage(mots, L, etat):
    return [(-mots[i][k] if (etat[i] >> k) & 1 else mots[i][k]) for i in range(L) for k in range(5)]


# ---------------------------------------------------------------- témoin

def main():
    rng = random.Random(GRAINE)
    rule("1. LE PROBLÈME POSÉ AU BIT PRÈS")
    say(f"   {N} tirages consécutifs, Fisher-Yates par modulo au pas {PAS}, mots sûrs {SURS} ;")
    say(f"   {2 * N} nibbles contraints, {2 * N * 0.372:.0f} bits d'information ; masques au format")
    say(f"   de l'archive (16 · 0,773 = 12,4 résidus permis). Timeout {TIMEOUT:.0f} s par appel.")
    say(f"   solveurs : {SOLVEURS} ; retards : {LAGS}")
    say("\n   {:>3} {:>3} {:>5} {:>8} {:>9} {:>8}  {:<8} {:<10} {:>8}  {}".format(
        "K", "L", "bas", "vars", "clauses", "xors", "solveur", "cas", "s", "résultat"))
    bilan = []
    for K, L in LAGS:
        nom = {(3, 7): "TYPE_1", (1, 15): "TYPE_2", (3, 31): "TYPE_3", (1, 63): "TYPE_4"}.get((K, L), "")
        etat = [rng.getrandbits(32) for _ in range(L)]
        bas = [x & 31 for x in etat]
        ms = masques_de(etat, K, L, N)
        autre = [rng.getrandbits(32) for _ in range(L)]
        ms_ctrl = masques_de(autre, K, L, N)
        assert suite_basse(bas, K, L, 40) == [x & 31 for x in lfg(etat, K, L, 40)]
        for solveur in SOLVEURS:
            natif = solveur == "cms"
            f, mots = encode(K, L, ms, natif)
            f_ctrl, mots_ctrl = encode(K, L, ms_ctrl, natif)
            info = f"{K:>3} {L:>3} {5 * L:>5} {f.nv:>8} {len(f.clauses):>9} {len(f.xors):>8}  {solveur:<8}"
            # (a) planté : doit rendre l'état bas planté
            res, sol, dt = resoudre(solveur, f, mots, L, TIMEOUT)
            ok = res == "sat" and sol == bas
            say(f"{info} {'planté':<10} {dt:>8.1f}  {res}" + (" = l'état planté" if ok else
                (f" ≠ planté ! {sol}" if res == "sat" else "")))
            bilan.append((K, L, solveur, "planté", res, dt, ok))
            # (b) unicité : l'état trouvé bloqué, il ne doit pas y en avoir d'autre
            #     (au-dessous de 152 bits d'information ; TYPE_3 en a 155 : parasites attendus)
            nb_autres = 0
            if res == "sat":
                bloques = [clause_blocage(mots, L, sol)]
                while True:
                    res2, sol2, dt2 = resoudre(solveur, f, mots, L, TIMEOUT, bloques)
                    if res2 != "sat":
                        say(f"{info} {'bloqué':<10} {dt2:>8.1f}  {res2}"
                            + (f"  ({nb_autres} autre(s) solution(s))" if nb_autres else "  — unique"))
                        bilan.append((K, L, solveur, "bloqué", res2, dt2, res2 == "unsat"))
                        break
                    nb_autres += 1
                    bloques.append(clause_blocage(mots, L, sol2))
                    say(f"{info} {'bloqué':<10} {dt2:>8.1f}  sat — autre solution {sol2[:4]}…"
                        f" (regénère les masques : {masques_de([x for x in sol2], K, L, N) == ms})")
                    if nb_autres >= 16:
                        say(f"{info} {'bloqué':<10} {'':>8}  arrêt à 16 solutions parasites")
                        break
            # (c) contrôle : masques d'un autre état
            res3, sol3, dt3 = resoudre(solveur, f_ctrl, mots_ctrl, L, TIMEOUT)
            say(f"{info} {'contrôle':<10} {dt3:>8.1f}  {res3}"
                + ("  (attendu : unsat)" if 5 * L <= 150 else "  (155 > 152 bits : sat possible)"))
            bilan.append((K, L, solveur, "contrôle", res3, dt3, res3 == "unsat"))
    rule("2. LECTURE")
    for K, L in LAGS:
        for solveur in SOLVEURS:
            r = [b for b in bilan if b[0] == K and b[1] == L and b[2] == solveur]
            pl = [b for b in r if b[3] == "planté"]
            if pl:
                say(f"   ({K}, {L}) {solveur:<8} planté : {pl[0][4]} en {pl[0][5]:.1f} s"
                    + (", état exact" if pl[0][6] else ""))
    say(f"\n   ({time.time() - T0:.1f} s)")


if __name__ == "__main__":
    main()
