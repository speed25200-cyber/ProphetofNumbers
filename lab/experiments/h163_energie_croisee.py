"""h163 — l'ENERGIE ADDITIVE CROISEE : la relation à trois termes quand ses trois indices
tombent dans trois tirages différents (THEORIE_ETAT §7.27 ; RAPPORT §178).

CE QUE LE §177 LAISSE OUVERT
===========================
Le §177 mesure, dans CHAQUE tirage, le nombre de couples `(u,v)` de classes publiées dont
`u+v` ou `u+v+1` est publié aussi. C'est la trace qu'un Fibonacci retardé additif laisse
quand ses trois indices `i-L`, `i-K`, `i` tombent dans le même tirage — et un tirage ne
consomme que `E[N] = 22,85` mots. Au-delà du degré 22, la trace sort du tirage et la
statistique ne voit plus rien : TYPE_3 `(3,31)` et TYPE_4 `(1,63)` y échappent.

Or ils n'en sortent pas : ils passent simplement dans le tirage PRECEDENT. Un mot d'indice
`i-L` avec `L = 31` est à `31/22,85 = 1,36` tirage en arrière ; avec `L = 63`, à `2,76`.
Il suffit donc de laisser chacun des deux antécédents choisir SON tirage.

LA FAMILLE COMPLETE
===================
Pour un décalage `(g1, g2)` avec `g1 >= g2 >= 0` :

    T(g1, g2) = #{ (u,v) dans C_{t-g1} x C_{t-g2} : (u+v+d) mod 80 dans C_t, d dans {0,1} }

`(0,0)` redonne la statistique du §177. Le couple qui porte le signal se lit sur le
générateur : `g1 = round(L/22,85)`, `g2 = round(K/22,85)`. Quinze couples avec
`g1 <= 4` couvrent tous les degrés jusqu'à `~90`.

PUISSANCE MESUREE (générateurs plantés, 4 000 tirages, troncature avec rejet)
============================================================================
    (K, L)      meilleur couple    z sur 4 000    z sur 70 560
    (3, 7)  TYPE_1     (0, 0)           +37,4          +157
    (1, 15) TYPE_2     (1, 0)           +28,2          +118
    (3, 17)            (1, 0)           +29,0          +122
    (2, 21)            (1, 0)           +37,7          +158
    (3, 25)            (1, 0)           +38,7          +163
    (3, 31) TYPE_3     (1, 0)           +28,5          +120
    (13, 31)           (2, 1)           +21,7           +91
    (1, 63) TYPE_4     (3, 0)           +34,1          +143
    (31, 63)           (3, 1)           +26,5          +111

Le couple (13,31) et le couple (31,63) montrent pourquoi le balayage doit etre COMPLET :
leur signal n'est visible qu'en `g2 >= 1`, c'est-a-dire quand l'antecedent `i-K` lui aussi
tombe dans un tirage anterieur. Un balayage limite a `(g, 0)` les manquerait tous les deux.

Sur les 70 560 tirages de l'archive, ces z sont multipliés par `sqrt(70560/4000) = 4,20`.
Le test voit donc TYPE_2, TYPE_3 et TYPE_4 à plus de cent écarts-types — là où le crible
de classes du §172 s'arrête au degré 7 et le §177 au degré 21. Et il coûte des secondes.

CE QUE CE N'EST PAS
===================
Ce n'est pas un crible : il ne rend pas d'état, il ne prédit rien par lui-même. C'est un
DETECTEUR. Sa valeur est d'écarter — ou de désigner — une famille entière en trois secondes,
pour que le crible, lui, ne soit lancé que là où il y a quelque chose à trouver.
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POOL, DRAWN = 80, 20
EXP_ID = "h163.energie_croisee"
FJETON = "/tmp/h163_jeton.json"
REPS = 40
GMAX = 4
COUPLES = [(g1, g2) for g1 in range(GMAX + 1) for g2 in range(g1 + 1)]


def say(*a):
    print(*a, flush=True)


def energie(m, g1, g2):
    """moyenne de T(g1,g2) sur les tirages ou le couple est defini.

    `m` : (n, 80) booleen. Convolution circulaire des indicatrices decalees de g1 et g2,
    puis produit avec l'indicatrice du tirage courant.
    """
    n = len(m)
    d = max(g1, g2)
    A = m[d - g1: n - g1]
    B = m[d - g2: n - g2]
    C = m[d:]
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


def plante(K, L, n, graine, lecture="tronc"):
    import random
    M32 = 1 << 32
    rng = random.Random(graine)
    r = [rng.randrange(M32) for _ in range(L)]
    i = L
    m = np.zeros((n, POOL), bool)
    for j in range(n):
        vus = set()
        while len(vus) < DRAWN:
            r.append((r[i - K] + r[i - L]) % M32)
            i += 1
            x = r[i - 1]
            vus.add((x * POOL) >> 32 if lecture == "tronc" else x % POOL)
        m[j, list(vus)] = True
    return m


if __name__ == "__main__":
    import lab

    if "--puissance" in sys.argv:
        say("h163 --puissance : generateurs plantes, aucune donnee reelle")
        n = int(sys.argv[sys.argv.index("--nb") + 1]) if "--nb" in sys.argv else 4000
        rng = np.random.default_rng(11)
        mn = srs(n, rng)
        NUL = {}
        for g in COUPLES:
            t = energie(mn, *g)
            NUL[g] = (t.mean(), t.std(ddof=1) / np.sqrt(len(t)))
        say(f"   nulle SRS sur {n} tirages ; {len(COUPLES)} couples (g1, g2)")
        say(f"{'K,L':>8} | {'meilleur couple':>16} | {'z':>8} | {'z sur 70 560':>13}")
        for K, L in ((3, 7), (1, 15), (3, 17), (2, 21), (3, 25), (3, 31), (13, 31),
                     (1, 63), (31, 63)):
            m = plante(K, L, n, 4321 + K + L)
            best, bz = None, 0.0
            for g in COUPLES:
                mu, sd = NUL[g]
                z = (energie(m, *g).mean() - mu) / sd
                if abs(z) > abs(bz):
                    best, bz = g, z
            say(f"{K:3d},{L:4d} | {str(best):>16} | {bz:+8.2f} | "
                f"{bz * np.sqrt(70560 / n):+13.1f}")
        sys.exit(0)

    if "--archive" not in sys.argv:
        print(__doc__)
        sys.exit(0)

    HYP = ("Les tirages de l'archive n'ont, pour AUCUN couple de decalages (g1, g2) avec "
           "0 <= g2 <= g1 <= 4, d'exces ni de deficit d'energie additive croisee : le nombre "
           "moyen de couples (u,v) de classes publiees par les tirages t-g1 et t-g2 dont la "
           "somme u+v ou u+v+1 est publiee par le tirage t est celui d'un tirage SRS. C'est "
           "la trace que laisse la relation c_i = c_{i-K} + c_{i-L} + delta quand ses trois "
           "indices tombent dans trois tirages differents — la seule forme sous laquelle "
           "TYPE_3 (3,31) et TYPE_4 (1,63) restent visibles")
    STAT = (f"D = max sur les {len(COUPLES)} couples de |z|, z = (moyenne archive - moyenne "
            "SRS) / ecart-type SRS de la moyenne, la loi par tirage etant estimee sur "
            f"{REPS} x 70 560 tirages SRS ; p bilateral corrige par Bonferroni sur les "
            f"{len(COUPLES)} couples")
    NUL = (f"Simulation : {REPS} x 70 560 tirages SRS 20/80 independants, dont on tire la "
           "moyenne et la variance PAR TIRAGE de chaque statistique ; ecart-type de la "
           "moyenne = sd(par tirage)/sqrt(n)")
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
    say(f"h163 : {n} tirages, {len(COUPLES)} couples")

    rng = np.random.default_rng(20260903)
    s1 = np.zeros(len(COUPLES)); s2 = np.zeros(len(COUPLES)); cpt = 0
    for k in range(REPS):
        m = srs(n, rng)
        for j, g in enumerate(COUPLES):
            t = energie(m, *g).astype(np.float64)
            s1[j] += t.sum(); s2[j] += (t * t).sum()
        cpt += len(energie(m, 0, 0))
        if (k + 1) % 10 == 0:
            say(f"   nulle {k+1}/{REPS}")
    mu = s1 / cpt
    sd = np.sqrt(np.maximum(s2 / cpt - mu * mu, 0) / n)
    z = (obs - mu) / sd
    from math import erfc, sqrt
    p1 = np.array([erfc(abs(v) / sqrt(2)) for v in z])
    p = min(1.0, len(COUPLES) * p1.min())
    say(f"\n{'(g1,g2)':>9} | {'archive':>10} | {'nulle':>10} | {'sd':>8} | {'z':>8}")
    for j, g in enumerate(COUPLES):
        say(f"{str(g):>9} | {obs[j]:10.4f} | {mu[j]:10.4f} | {sd[j]:8.4f} | {z[j]:+8.3f}")
    say(f"\n   |z| max = {np.abs(z).max():.3f} au couple {COUPLES[int(np.argmax(np.abs(z)))]}"
        f" ; p (Bonferroni sur {len(COUPLES)}) = {p:.4f}")
    TOK["m_extra"] = len(COUPLES) - 1
    lab.record(
        TOK, float(np.abs(z).max()), p=float(p),
        verdict="conforme" if p > 0.05 else "ECART",
        power_at=("PUISSANCE MESUREE sur generateurs plantes, 4 000 tirages, troncature avec "
                  "rejet, |z| au meilleur couple, ramene aux 70 560 tirages de l'archive : "
                  "(3,7) TYPE_1 +157 en (0,0) ; (1,15) TYPE_2 +118 en (1,0) ; (3,17) +122 ; "
                  "(2,21) +158 ; (3,25) +163 ; (3,31) TYPE_3 +120 en (1,0) ; (13,31) +91 en "
                  "(2,1) ; (1,63) TYPE_4 +143 en (3,0) ; (31,63) +111 en (3,1). Les QUATRE "
                  "types de la glibc sont vus a plus de cent ecarts-types, la ou le crible de "
                  "classes du §172 s'arrete au degre 7 et le §177 au degre 21"),
        notes=("ENERGIE ADDITIVE CROISEE (§178) : la relation a trois termes quand ses trois "
               "indices tombent dans trois tirages differents. Quinze couples (g1,g2), "
               f"g1 <= {GMAX}. z max = {np.abs(z).max():.3f}. Ce n'est pas un crible : il ne "
               "rend pas d'etat. C'est un detecteur, et sa valeur est d'ecarter une famille "
               "entiere en trois secondes."))
    say("   consigne.")
