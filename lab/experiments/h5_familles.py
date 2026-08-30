"""h5 — élargir l'attaque algébrique aux générateurs réellement déployés.

h4 a montré que le rang combinatoire ne cache que 2,38 bits, et a résolu
la famille LCG en une seconde. Le même levier ouvre trois autres familles,
qui couvrent l'essentiel de ce qu'un backend web utilise vraiment :

  A. SORTIE INVERSIBLE (splitmix64, xorshift64*). Leur fonction de sortie
     est une bijection : on l'INVERSE pour retrouver l'état, puis on
     vérifie la transition. Deux tirages consécutifs suffisent — 36
     couples candidats, deux lignes d'arithmétique.

  B. java.util.Random — LCG 48 bits dont chaque sortie ne montre que les
     32 bits de POIDS FORT. Un rang de 64 bits = deux sorties. Les 16 bits
     bas du premier état sont énumérés (2^16), et la seconde sortie les
     filtre à ~1 survivant. C'est le générateur par défaut de toute une
     génération de backends — s'il était là, tout serait prévisible.

  C. Ce qui reste hors d'atteinte, dit franchement : MT19937 par rang
     (il faudrait 624 sorties exactes, donc 6^312 combinaisons), PCG64 et
     tout générateur à état plus large que sa sortie, et évidemment tout
     générateur cryptographique. Une attaque honnête nomme ses angles
     morts.

Chaque famille a son TÉMOIN POSITIF : une archive fabriquée par ce
générateur, que l'attaque doit récupérer, avec prédiction exacte du tirage
suivant. Sans ce témoin, « rien trouvé » ne voudrait rien dire.
"""

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import lab
from ranks import rank_of, unrank, M, candidates

T0 = time.time()
M64 = (1 << 64) - 1
MASK48 = (1 << 48) - 1


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def inv64(x: int) -> int:
    """Inverse modulo 2^64 (x impair)."""
    inv = 1
    for _ in range(7):
        inv = (inv * (2 - x * inv)) & M64
    return inv


def unxorshift_right(y: int, k: int) -> int:
    """Inverse de x -> x ^ (x >> k) sur 64 bits."""
    x = y
    for _ in range(64 // k + 1):
        x = y ^ (x >> k)
    return x & M64


def unxorshift_left(y: int, k: int) -> int:
    x = y
    for _ in range(64 // k + 1):
        x = (y ^ (x << k)) & M64
    return x


# --------------------------------------------------------------------------
# Famille A — sorties inversibles
# --------------------------------------------------------------------------

GOLDEN = 0x9E3779B97F4A7C15
SM_A, SM_B = 0xBF58476D1CE4E5B9, 0x94D049BB133111EB
XS_MUL = 0x2545F4914F6CDD1D


def splitmix_out(s: int) -> int:
    z = (s + GOLDEN) & M64
    w = z
    w = ((w ^ (w >> 30)) * SM_A) & M64
    w = ((w ^ (w >> 27)) * SM_B) & M64
    return w ^ (w >> 31)


def splitmix_state_from_out(o: int) -> int:
    """Inverse exact de la sortie splitmix64 : rend l'état DÉJÀ incrémenté."""
    w = unxorshift_right(o, 31)
    w = (w * inv64(SM_B)) & M64
    w = unxorshift_right(w, 27)
    w = (w * inv64(SM_A)) & M64
    return unxorshift_right(w, 30)


def xorshift64s_step(s: int) -> int:
    s ^= s >> 12
    s = (s ^ (s << 25)) & M64
    s ^= s >> 27
    return s


def xorshift64s_out(s: int):
    s2 = xorshift64s_step(s)
    return s2, (s2 * XS_MUL) & M64


FAMILY_A = {
    # nom: (état -> sortie, sortie -> « état intérieur », transition attendue)
    "splitmix64": (splitmix_out, splitmix_state_from_out,
                   lambda z1, z2: (z2 - z1) & M64 == GOLDEN),
    "xorshift64*": (lambda s: xorshift64s_out(s)[1],
                    lambda o: (o * inv64(XS_MUL)) & M64,
                    lambda z1, z2: xorshift64s_step(z1) == z2),
}


def attack_family_a(ranks, starts=60, confirm=20):
    for name, (out_of, state_of, ok_transition) in FAMILY_A.items():
        for b in (64,):
            for mapping in ("mod", "floor"):
                for t0 in range(min(starts, max(0, len(ranks) - confirm - 2))):
                    c0 = candidates(ranks[t0], b, mapping)
                    c1 = candidates(ranks[t0 + 1], b, mapping)
                    for o0 in c0:
                        z0 = state_of(o0)
                        for o1 in c1:
                            if not ok_transition(z0, state_of(o1)):
                                continue
                            # transition confirmée : on rejoue vers l'avant
                            z = state_of(o1)
                            good = True
                            for j in range(2, 2 + confirm):
                                if name == "splitmix64":
                                    z = (z + GOLDEN) & M64
                                    o = splitmix_out((z - GOLDEN) & M64)
                                else:
                                    z = xorshift64s_step(z)
                                    o = (z * XS_MUL) & M64
                                r = o % M if mapping == "mod" else (o * M) >> b
                                if r != ranks[t0 + j]:
                                    good = False
                                    break
                            if good:
                                return {"family": name, "mapping": mapping,
                                        "start": t0, "z": z}
    return None


# --------------------------------------------------------------------------
# Famille B — java.util.Random
# --------------------------------------------------------------------------

JA, JC = 0x5DEECE66D, 0xB


def java_next32(s: int):
    s = (s * JA + JC) & MASK48
    return s, s >> 16


def attack_java(ranks, starts=6, confirm=12):
    for mapping in ("mod", "floor"):
        for t0 in range(min(starts, max(0, len(ranks) - confirm - 1))):
            for v in candidates(ranks[t0], 64, mapping):
                hi, lo = v >> 32, v & 0xFFFFFFFF
                for k in range(1 << 16):
                    s1 = (hi << 16) | k
                    s2, out2 = java_next32(s1)
                    if out2 != lo:
                        continue
                    s = s2
                    good = True
                    for j in range(1, 1 + confirm):
                        s, a = java_next32(s)
                        s, bb = java_next32(s)
                        o = (a << 32) | bb
                        r = o % M if mapping == "mod" else (o * M) >> 64
                        if r != ranks[t0 + j]:
                            good = False
                            break
                    if good:
                        return {"family": "java.util.Random", "mapping": mapping,
                                "start": t0, "state": s}
    return None


# --------------------------------------------------------------------------
# 1. Témoins positifs
# --------------------------------------------------------------------------

rule("1. TÉMOINS POSITIFS — chaque famille doit être récupérée sur son "
     "propre générateur")

for name, (out_of, _, _) in FAMILY_A.items():
    for mapping in ("mod", "floor"):
        s = 0x0123456789ABCDEF
        ranks = []
        for _ in range(60):
            if name == "splitmix64":
                o = splitmix_out(s)
                s = (s + GOLDEN) & M64
            else:
                s = xorshift64s_step(s)
                o = (s * XS_MUL) & M64
            ranks.append(o % M if mapping == "mod" else (o * M) >> 64)
        t = time.time()
        res = attack_family_a(ranks, starts=4)
        pred = None
        if res:
            z = res["z"]
            if res["family"] == "splitmix64":
                z = (z + GOLDEN) & M64
                o = splitmix_out((z - GOLDEN) & M64)
            else:
                z = xorshift64s_step(z)
                o = (z * XS_MUL) & M64
            r = o % M if res["mapping"] == "mod" else (o * M) >> 64
            pred = unrank(r) == unrank(ranks[res["start"] + 22])
        say(f"   {name:<14} mapping {mapping:<6} récupéré "
            f"{'OUI' if res else 'NON':<4} prédiction exacte "
            f"{'OUI' if pred else 'NON':<4} ({time.time() - t:.2f}s)")

for mapping in ("mod", "floor"):
    s = (0x2A9F3B1C4D5E & MASK48)
    ranks = []
    for _ in range(40):
        s, a = java_next32(s)
        s, bb = java_next32(s)
        o = (a << 32) | bb
        ranks.append(o % M if mapping == "mod" else (o * M) >> 64)
    t = time.time()
    res = attack_java(ranks, starts=2)
    pred = None
    if res:
        st = res["state"]
        st, a = java_next32(st)
        st, bb = java_next32(st)
        o = (a << 32) | bb
        r = o % M if res["mapping"] == "mod" else (o * M) >> 64
        pred = unrank(r) == unrank(ranks[res["start"] + 13])
    say(f"   {'java.util.Random':<14} mapping {mapping:<6} récupéré "
        f"{'OUI' if res else 'NON':<4} prédiction exacte "
        f"{'OUI' if pred else 'NON':<4} ({time.time() - t:.1f}s)")


# --------------------------------------------------------------------------
# 2. Témoin négatif
# --------------------------------------------------------------------------

rule("2. TÉMOIN NÉGATIF — archives équitables, l'attaque doit se taire")
rng = np.random.default_rng(909)
fa = fj = 0
t = time.time()
for _ in range(8):
    m = lab.srs(60, rng)
    ranks = [rank_of([int(n) + 1 for n in np.flatnonzero(row)]) for row in m]
    if attack_family_a(ranks, starts=3) is not None:
        fa += 1
    if attack_java(ranks, starts=1) is not None:
        fj += 1
say(f"   sorties inversibles : {fa}/8 fausses récupérations")
say(f"   java.util.Random    : {fj}/8 fausses récupérations   ({time.time() - t:.0f}s)")


# --------------------------------------------------------------------------
# 3. L'archive réelle
# --------------------------------------------------------------------------

rule("3. L'ARCHIVE RÉELLE")
arch = lab.load()
ranks = [rank_of([int(n) + 1 for n in np.flatnonzero(row)]) for row in arch.mask]
say(f"   {len(ranks)} rangs")

t = time.time()
ra = attack_family_a(ranks, starts=200)
say(f"   sorties inversibles (splitmix64, xorshift64*) : "
    f"{'RÉCUPÉRÉ ' + str(ra) if ra else 'aucun'}   ({time.time() - t:.0f}s)")

t = time.time()
rj = attack_java(ranks, starts=8)
say(f"   java.util.Random : {'RÉCUPÉRÉ ' + str(rj) if rj else 'aucun'}"
    f"   ({time.time() - t:.0f}s)")

rule("4. LES ANGLES MORTS, NOMMÉS")
say("""   Ce que le rang NE permet PAS d'attaquer, et pourquoi :

   * MT19937 par rang : il faut 624 sorties 32 bits EXACTES pour inverser
     l'état. Chaque tirage en donne deux, à 6 candidats près — 6^312
     combinaisons. Hors d'atteinte, définitivement.
   * PCG64, xoshiro256**, tout générateur dont l'état est plus large que
     la sortie : la sortie ne détermine pas l'état, l'inversion n'existe
     pas. Il faudrait résoudre un système sur plusieurs sorties — possible
     en principe pour les familles GF(2)-linéaires, hors périmètre ici.
   * Tout générateur cryptographique : par construction.
   * Et surtout : si le tirage n'est PAS le dérangement d'une sortie unique
     — rejet, Fisher-Yates, tirage physique — le rang n'est pas la sortie
     du générateur, et toute cette classe d'attaques est muette. L'ordre de
     sortie des boules la rouvrirait (~124 bits contre 61,6) ; l'app le
     capture déjà quand l'API le publie.""")

rule(f"total {time.time() - T0:.0f}s")
