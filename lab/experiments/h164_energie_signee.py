"""h164 — l'énergie additive à décalages SIGNÉS : les Fibonacci SOUSTRACTIFS, Knuth compris
(THEORIE_ETAT §7.27 ; RAPPORT §179).

CE QUE LE §178 LAISSE OUVERT
===========================
Le §178 balaie les couples `(g1, g2)` avec `g1 >= g2 >= 0` : la SOMME est cherchée dans le
tirage courant, les deux opérandes dans des tirages antérieurs ou le même. Cela couvre les
Fibonacci ADDITIFS, `r_i = r_{i-K} + r_{i-L}`, du degré 7 au degré 63.

Mais un Fibonacci SOUSTRACTIF, `r_i = r_{i-K} - r_{i-L}`, satisfait la même coïncidence
additive écrite autrement :

    r_i = r_{i-K} - r_{i-L}      <=>      r_i + r_{i-L} = r_{i-K}

La somme n'est plus `r_i` : c'est `r_{i-K}`, qui tombe dans un tirage ANTÉRIEUR aux deux
opérandes. Vu depuis le tirage de la somme, l'un des opérandes est dans le FUTUR.

Quand `K` est petit — TYPE_1 `(3,7)`, TYPE_3 `(3,31)` — les trois indices restent assez
proches pour que le balayage positif les attrape quand même : le soustractif `(3,7)` sort à
`z = +163`, le `(3,31)` à `+129`. Mais dès que `K` dépasse un tirage, il échappe. Le cas qui
compte est celui de **Knuth**, `r_i = r_{i-24} - r_{i-55}` — le `ran_array` du volume 2, le
générateur soustractif le plus répandu, et un candidat naturel pour une loterie : `K = 24`
vaut `1,05` tirage. Le §178 lui donne `z = -6,9`. Il passe à travers.

LA CORRECTION TIENT EN UN SIGNE
===============================
Il suffit d'autoriser les décalages NÉGATIFS :

    T(g1, g2) = #{ (u,v) dans C_{t-g1} x C_{t-g2} : (u+v+d) mod 80 dans C_t, d dans {0,1} }
    avec g1, g2 dans {-2, ..., 4},  g1 >= g2

Vingt-huit couples au lieu de quinze. Et Knuth ressort au couple `(1, -1)` à `z = +167`.

PUISSANCE MESUREE (générateurs plantés, 4 000 tirages, ramenée aux 70 560 de l'archive)
======================================================================================
    SOUSTRACTIF (24,55) Knuth   couple (1, -1)    z = +167
    SOUSTRACTIF (37,100)        couple (3, -1)    z = +106
    SOUSTRACTIF (3,31)          couple (1,  0)    z = +129
    SOUSTRACTIF (7,10)          couple (0,  0)    z = +134
    SOUSTRACTIF (3,7)           couple (0,  0)    z = +163
    additif    (24,55)          couple (2,  1)    z = +164

Le détecteur couvre donc, en une passe de trois minutes, les Fibonacci retardés ADDITIFS et
SOUSTRACTIFS du degré 7 au degré 100 — soit tout ce que la littérature des générateurs de
loterie propose dans cette famille, `ran_array` de Knuth et les quatre types de la glibc
compris.
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POOL, DRAWN = 80, 20
EXP_ID = "h164.energie_signee"
FJETON = "/tmp/h164_jeton.json"
REPS = 40
GMIN, GMAX = -2, 4
COUPLES = [(a, b) for a in range(GMIN, GMAX + 1) for b in range(GMIN, GMAX + 1) if a >= b]


def say(*a):
    print(*a, flush=True)


def energie(m, g1, g2):
    """T(g1,g2) par tirage. Un décalage NÉGATIF désigne un tirage POSTÉRIEUR.

    Les bornes sont calculées pour que les trois indices `t-g1`, `t-g2` et `t` restent
    dans la fenêtre : c'est le seul point délicat du calcul signé.
    """
    n = len(m)
    lo, hi = min(0, g1, g2), max(0, g1, g2)
    deb, fin = max(0, hi), n + min(0, lo)
    A = m[deb - g1: fin - g1]
    B = m[deb - g2: fin - g2]
    C = m[deb:fin]
    fA = np.fft.rfft(A.astype(np.float64), axis=1)
    fB = np.fft.rfft(B.astype(np.float64), axis=1)
    conv = np.rint(np.fft.irfft(fA * fB, n=POOL, axis=1)).astype(np.int64)
    s = np.zeros(len(C), np.int64)
    for dec in (0, 1):
        w = (np.arange(POOL) - dec) % POOL
        s += (conv[:, w] * C).sum(axis=1)
    return s


def srs(n, rng):
    idx = np.argpartition(rng.random((n, POOL)), DRAWN, axis=1)[:, :DRAWN]
    m = np.zeros((n, POOL), bool)
    m[np.arange(n)[:, None], idx] = True
    return m


def plante(K, L, n, graine, signe=1):
    import random
    M32 = 1 << 32
    rng = random.Random(graine)
    r = [rng.randrange(M32) for _ in range(L)]
    i = L
    m = np.zeros((n, POOL), bool)
    for j in range(n):
        vus = set()
        while len(vus) < DRAWN:
            r.append((r[i - K] + signe * r[i - L]) % M32)
            i += 1
            vus.add((r[i - 1] * POOL) >> 32)
        m[j, list(vus)] = True
    return m


if __name__ == "__main__":
    import lab

    if "--puissance" in sys.argv:
        say("h164 --puissance : generateurs plantes, aucune donnee reelle")
        n = int(sys.argv[sys.argv.index("--nb") + 1]) if "--nb" in sys.argv else 4000
        rng = np.random.default_rng(29)
        mn = srs(n, rng)
        NUL = {}
        for g in COUPLES:
            t = energie(mn, *g)
            NUL[g] = (t.mean(), t.std(ddof=1) / np.sqrt(len(t)))
        say(f"   {len(COUPLES)} couples signes, nulle SRS sur {n} tirages")
        say(f"{'generateur':>26} | {'couple':>9} | {'z':>8} | {'z sur 70 560':>13}")
        CAS = [(3, 7, -1, "SOUSTR. (3,7)"), (7, 10, -1, "SOUSTR. (7,10)"),
               (3, 31, -1, "SOUSTR. (3,31)"), (24, 55, -1, "SOUSTR. (24,55) Knuth"),
               (37, 100, -1, "SOUSTR. (37,100)"), (24, 55, 1, "additif (24,55)"),
               (1, 63, -1, "SOUSTR. (1,63)"), (3, 7, 1, "additif (3,7) TYPE_1")]
        for K, L, sg, nom in CAS:
            m = plante(K, L, n, 555 + K + L, sg)
            best, bz = None, 0.0
            for g in COUPLES:
                mu, sd = NUL[g]
                z = (energie(m, *g).mean() - mu) / sd
                if abs(z) > abs(bz):
                    best, bz = g, z
            say(f"{nom:>26} | {str(best):>9} | {bz:+8.2f} | {bz*np.sqrt(70560/n):+13.1f}")
        sys.exit(0)

    if "--archive" not in sys.argv:
        print(__doc__)
        sys.exit(0)

    HYP = ("Les tirages de l'archive n'ont, pour AUCUN couple de decalages SIGNES (g1, g2) "
           "avec -2 <= g2 <= g1 <= 4, d'exces ni de deficit d'energie additive : le nombre "
           "moyen de couples (u,v) de classes publiees par les tirages t-g1 et t-g2 dont la "
           "somme u+v ou u+v+1 est publiee par le tirage t est celui d'un tirage SRS. Les "
           "decalages NEGATIFS sont ce qui distingue cette grille du §178 : ils rendent "
           "visibles les Fibonacci SOUSTRACTIFS a grand K, dont le ran_array de Knuth "
           "r_i = r_{i-24} - r_{i-55}, que le balayage positif manque")
    STAT = (f"D = max sur les {len(COUPLES)} couples de |z|, z = (moyenne archive - moyenne "
            f"SRS) / ecart-type SRS de la moyenne, loi par tirage estimee sur {REPS} x 70 560 "
            f"tirages SRS ; p bilateral corrige par Bonferroni sur les {len(COUPLES)} couples")
    NUL = (f"Simulation : {REPS} x 70 560 tirages SRS 20/80 independants, moyenne et variance "
           "PAR TIRAGE de chaque statistique ; ecart-type de la moyenne = sd/sqrt(n)")
    VER = "conforme si p > 0,05 apres Bonferroni"

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    A = lab.load()
    M = np.asarray(A.mask)
    n = len(M)
    obs = np.array([energie(M, *g).mean() for g in COUPLES])
    say(f"h164 : {n} tirages, {len(COUPLES)} couples signes")

    rng = np.random.default_rng(20260904)
    s1 = np.zeros(len(COUPLES)); s2 = np.zeros(len(COUPLES)); cpt = 0
    for k in range(REPS):
        m = srs(n, rng)
        for j, g in enumerate(COUPLES):
            t = energie(m, *g).astype(np.float64)
            s1[j] += t.sum(); s2[j] += (t * t).sum()
        cpt += n
        if (k + 1) % 10 == 0:
            say(f"   nulle {k+1}/{REPS}")
    mu = s1 / cpt
    sd = np.sqrt(np.maximum(s2 / cpt - mu * mu, 0) / n)
    z = (obs - mu) / sd
    from math import erfc, sqrt
    p1 = np.array([erfc(abs(v) / sqrt(2)) for v in z])
    p = min(1.0, len(COUPLES) * p1.min())
    say(f"\n{'(g1,g2)':>10} | {'archive':>10} | {'nulle':>10} | {'z':>8}")
    for j, g in enumerate(COUPLES):
        say(f"{str(g):>10} | {obs[j]:10.4f} | {mu[j]:10.4f} | {z[j]:+8.3f}")
    jm = int(np.argmax(np.abs(z)))
    say(f"\n   |z| max = {abs(z[jm]):.3f} au couple {COUPLES[jm]} ; "
        f"p (Bonferroni sur {len(COUPLES)}) = {p:.4f}")
    TOK["m_extra"] = len(COUPLES) - 1
    lab.record(
        TOK, float(np.abs(z).max()), p=float(p),
        verdict="conforme" if p > 0.05 else "ECART",
        power_at=("PUISSANCE MESUREE sur generateurs plantes, 4 000 tirages, troncature avec "
                  "rejet, ramenee aux 70 560 de l'archive : SOUSTRACTIF (24,55) de Knuth "
                  "z = +167 au couple (1,-1) — invisible au §178 qui lui donnait -6,9 ; "
                  "SOUSTRACTIF (37,100) +106 en (3,-1) ; SOUSTRACTIF (3,31) +129 ; "
                  "SOUSTRACTIF (3,7) +163 ; additif (24,55) +164. Le detecteur couvre les "
                  "Fibonacci retardes ADDITIFS et SOUSTRACTIFS du degre 7 au degre 100"),
        notes=("ENERGIE ADDITIVE A DECALAGES SIGNES (§179) : un Fibonacci soustractif "
               "r_i = r_{i-K} - r_{i-L} s'ecrit r_i + r_{i-L} = r_{i-K}, donc sa SOMME tombe "
               "dans un tirage anterieur aux operandes — vue depuis le tirage de la somme, "
               "l'un des operandes est dans le FUTUR. D'ou les decalages negatifs. "
               f"28 couples, |z| max = {abs(z[jm]):.3f} au couple {COUPLES[jm]}."))
    say("   consigne.")
