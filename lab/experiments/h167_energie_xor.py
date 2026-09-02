"""h167 — l'énergie **XOR** : les générateurs F2-linéaires à deux termes
(THEORIE_ETAT §7.27 ; RAPPORT §182).

L'ANGLE MORT DES §177 À §181
===========================
Tous les détecteurs précédents mesurent une coïncidence **additive** : `u + v ∈ C`. Ils
voient donc les récurrences `r_i = α·r_{i-K} + β·r_{i-L} mod 2^32`. Ils sont **aveugles**
aux récurrences sur `GF(2)` — `r_i = r_{i-K} XOR r_{i-L}` — qui n'ont aucune retenue et
donc aucune structure additive : le témoin le confirme, un additif `(3,7)` donne `z = +16`
sur la statistique XOR contre `+162` sur l'additive, et réciproquement.

Or c'est la famille la plus répandue en logiciel : GFSR, xorshift, WELL, et la charpente
de Mersenne Twister.

CE QUE LA CLASSE GARDE DES BITS DE TÊTE
=======================================
Le XOR agit bit à bit, sans retenue : si `x_i = x_{i-K} XOR x_{i-L}`, alors les **bits de
tête** vérifient exactement la même relation. Il suffit donc de remonter de la classe aux
bits de tête. La classe `c` place `x` dans `[c·2^32/80, (c+1)·2^32/80)`, un intervalle de
largeur `2^25,68` ; sur six bits de tête (granularité `2^26`), cet intervalle chevauche une
ou deux cases. La classe détermine donc les six bits de tête **à une ambiguïté de deux
près**, et l'on compte les deux candidats plutôt que d'en choisir un.

    T_xor(g1, g2) = #{ (u,v) : b(u) XOR b(v) dans b(C_t) },  u dans C_{t-g1}, v dans C_{t-g2}

où `b(·)` est l'ensemble (un ou deux éléments) des têtes compatibles. Le calcul est une
convolution **de Walsh-Hadamard** — l'analogue XOR de la convolution circulaire des
sections précédentes.

PUISSANCE MESUREE (générateurs plantés, 2 500 tirages, ramenée aux 70 560 de l'archive)
======================================================================================
    GFSR XOR (3,7)    z = +257
    GFSR XOR (1,15)   z =  +79
    GFSR XOR (3,31)   z =  +33
    additif (3,7)     z =  +16   (le détecteur additif lui donne +162 : les deux
                                  instruments sont bien distincts)

CE QU'IL NE VOIT PAS, ET POURQUOI IL FAUT LE DIRE
=================================================
Mersenne Twister n'est pas une récurrence XOR à deux termes sur des MOTS : son pas mélange
deux mots par un masque puis décale d'un bit (`>> 1`), ce qui casse l'alignement des bits de
tête. Le tempering, lui, ne gêne pas — il est F2-linéaire, donc il préserve la relation.
Ce détecteur couvre les GFSR et les xorshift à deux termes ; il ne couvre pas MT19937, que
le §68 et le §99 traitent par d'autres moyens.
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import h164_energie_signee as S                                        # noqa: E402

POOL, DRAWN = 80, 20
M32 = 1 << 32
NB = 6
TB = 1 << NB
EXP_ID = "h167.energie_xor"
FJETON = "/tmp/h167_jeton.json"
REPS = 12
COUPLES = [g for g in S.COUPLES if abs(g[0]) <= 2 and abs(g[1]) <= 2]


def say(*a):
    print(*a, flush=True)


def _table():
    """B[c] : indicatrice des valeurs de tete compatibles avec la classe c (une ou deux)."""
    B = np.zeros((POOL, TB))
    for c in range(POOL):
        lo = (c * M32) // POOL
        hi = ((c + 1) * M32) // POOL - 1
        for b in range(lo >> (32 - NB), (hi >> (32 - NB)) + 1):
            B[c, b % TB] = 1.0
    return B


BP = _table()


def tetes(m):
    return (m.astype(np.float64) @ BP > 0).astype(np.float64)


def wht(X):
    X = X.copy()
    h = 1
    while h < TB:
        for i in range(0, TB, h * 2):
            a = X[:, i:i + h].copy()
            b = X[:, i + h:i + 2 * h].copy()
            X[:, i:i + h] = a + b
            X[:, i + h:i + 2 * h] = a - b
        h *= 2
    return X


def energie(mb, g1, g2):
    n = len(mb)
    lo, hi = min(0, g1, g2), max(0, g1, g2)
    deb, fin = max(0, hi), n + min(0, lo)
    A = wht(mb[deb - g1: fin - g1])
    B = wht(mb[deb - g2: fin - g2])
    conv = wht(A * B) / TB
    return (conv * mb[deb:fin]).sum(axis=1)


def plante(n, graine, K, L, xor=True):
    import random
    rng = random.Random(graine)
    r = [rng.randrange(M32) for _ in range(max(80, L + 1))]
    i = len(r)
    m = np.zeros((n, POOL), bool)
    for j in range(n):
        vus = set()
        while len(vus) < DRAWN:
            r.append((r[i - K] ^ r[i - L]) if xor else (r[i - K] + r[i - L]) % M32)
            i += 1
            vus.add((r[i - 1] * POOL) >> 32)
        m[j, list(vus)] = True
    return m


if __name__ == "__main__":
    import lab

    if "--puissance" in sys.argv:
        n = int(sys.argv[sys.argv.index("--nb") + 1]) if "--nb" in sys.argv else 2500
        say(f"h167 --puissance : {n} tirages plantes, aucune donnee reelle")
        rng = np.random.default_rng(47)
        mn = tetes(S.srs(n, rng))
        NUL = {}
        for g in COUPLES:
            t = energie(mn, *g)
            NUL[g] = (t.mean(), t.std(ddof=1) / np.sqrt(len(t)))
        say(f"{'generateur':>26} | {'couple':>9} | {'z sur 70 560':>13}")
        for K, L, x, nom in ((3, 7, True, "GFSR XOR (3,7)"), (1, 15, True, "GFSR XOR (1,15)"),
                             (3, 31, True, "GFSR XOR (3,31)"),
                             (3, 7, False, "additif (3,7)")):
            m = tetes(plante(n, 1234 + K + L, K, L, x))
            best, bz = None, 0.0
            for g in COUPLES:
                mu, sd = NUL[g]
                z = (energie(m, *g).mean() - mu) / sd
                if abs(z) > abs(bz):
                    best, bz = g, z
            say(f"{nom:>26} | {str(best):>9} | {bz*np.sqrt(70560/n):+13.1f}")
        sys.exit(0)

    if "--archive" not in sys.argv:
        print(__doc__)
        sys.exit(0)

    HYP = (f"Les tirages de l'archive n'ont, pour aucun des {len(COUPLES)} couples de "
           "decalages signes, d'exces ni de deficit d'energie XOR sur les six bits de tete : "
           "le nombre moyen de couples (u,v) de classes publiees dont le XOR des tetes est "
           "une tete publiee est celui d'un tirage SRS. C'est la trace que laisse une "
           "recurrence F2-lineaire a deux termes r_i = r_{i-K} XOR r_{i-L}, invisible aux "
           "detecteurs ADDITIFS des §177 a §181")
    STAT = (f"D = max sur les {len(COUPLES)} couples de |z| ; p bilateral corrige par "
            f"Bonferroni sur {len(COUPLES)}")
    NUL = (f"Simulation : {REPS} x 70 560 tirages SRS 20/80, moyenne et variance PAR TIRAGE ; "
           "ecart-type de la moyenne = sd/sqrt(n)")
    VER = "conforme si p > 0,05 apres Bonferroni"

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    A = lab.load()
    MB = tetes(np.asarray(A.mask))
    n = len(MB)
    obs = np.array([energie(MB, *g).mean() for g in COUPLES])
    say(f"h167 : {n} tirages, {len(COUPLES)} couples, {NB} bits de tete")

    rng = np.random.default_rng(20260907)
    s1 = np.zeros(len(COUPLES)); s2 = np.zeros(len(COUPLES)); cpt = 0
    for k in range(REPS):
        mb = tetes(S.srs(n, rng))
        for j, g in enumerate(COUPLES):
            t = energie(mb, *g).astype(np.float64)
            s1[j] += t.sum(); s2[j] += (t * t).sum()
        cpt += n
        say(f"   nulle {k+1}/{REPS}")
    mu = s1 / cpt
    sd = np.sqrt(np.maximum(s2 / cpt - mu * mu, 0) / n)
    z = (obs - mu) / sd
    from math import erfc, sqrt
    p1 = np.array([erfc(abs(v) / sqrt(2)) for v in z])
    p = min(1.0, len(COUPLES) * p1.min())
    jm = int(np.argmax(np.abs(z)))
    say(f"\n{'couple':>9} | {'archive':>10} | {'nulle':>10} | {'z':>8}")
    for j, g in enumerate(COUPLES):
        say(f"{str(g):>9} | {obs[j]:10.4f} | {mu[j]:10.4f} | {z[j]:+8.3f}")
    say(f"\n   |z| max = {abs(z[jm]):.3f} au couple {COUPLES[jm]} ; "
        f"p (Bonferroni sur {len(COUPLES)}) = {p:.4f}")
    TOK["m_extra"] = len(COUPLES) - 1
    lab.record(
        TOK, float(np.abs(z).max()), p=float(p),
        verdict="conforme" if p > 0.05 else "ECART",
        power_at=("PUISSANCE MESUREE sur generateurs plantes, 2 500 tirages, ramenee aux "
                  "70 560 de l'archive : GFSR XOR (3,7) z = +257 ; (1,15) +79 ; (3,31) +33. "
                  "Le temoin additif (3,7) n'y donne que +16 alors qu'il donne +162 sur la "
                  "statistique additive : les deux instruments sont bien distincts"),
        notes=("ENERGIE XOR (§182) : le XOR agit sans retenue, donc les BITS DE TETE d'une "
               "recurrence F2-lineaire verifient exactement la meme relation. La classe "
               "determine les six bits de tete a une ambiguite de deux pres (l'intervalle "
               "d'une classe est large de 2^25,68 contre 2^26 par case), et l'on compte les "
               "deux candidats. Convolution de Walsh-Hadamard. NE COUVRE PAS MT19937, dont "
               "le pas decale d'un bit et casse l'alignement des tetes ; le tempering, lui, "
               f"est F2-lineaire et ne gene pas. |z| max = {abs(z[jm]):.3f}."))
    say("   consigne.")
