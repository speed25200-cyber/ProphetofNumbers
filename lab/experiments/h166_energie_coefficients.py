"""h166 — l'énergie additive à COEFFICIENTS : `r_i = α·r_{i-K} + β·r_{i-L}`
(THEORIE_ETAT §7.27 ; RAPPORT §181).

CE QUI RESTAIT
==============
Les §177 à §180 testent la relation `r_i = r_{i-K} ± r_{i-L}` : coefficients `±1`. Or la
famille des récurrences à deux termes ne s'arrête pas là. Les générateurs à
**multiplication et retenue** de Marsaglia (`x_i = a·x_{i-1} + retenue`), les Fibonacci
retardés multiplicatifs, et plus généralement tout `r_i = α·r_{i-K} + β·r_{i-L} mod 2^32`
à petits coefficients, échappent à un détecteur qui suppose `α = β = 1`.

LA GÉNÉRALISATION EST IMMÉDIATE
===============================
La classe est quasi-homogène autant qu'elle est quasi-additive :

    c(α·x mod 2^32) = α·c(x) + δ_α   (mod 80),   δ_α dans {0, ..., α-1}

(et `δ` dans `{-|α|+1, ..., 0}` pour `α < 0`). Le support de `δ` pour un couple `(α, β)`
est donc de taille `|α| + |β| - 1` au plus — six valeurs au pire pour `α, β` dans
`{±1, ±2}`, soit encore `log2(80/6) = 3,74` bits d'élagage par coïncidence.

    T_{α,β}(g1, g2) = #{ (u,v) : α·u + β·v + δ (mod 80) dans C_t }
                      u dans C_{t-g1}, v dans C_{t-g2}, δ dans supp(α, β)

Le calcul reste une convolution : il suffit de DILATER l'indicatrice — `A_α[k]` compte les
`u` de `C` tels que `α·u ≡ k` — avant de convoluer. La dilatation est un produit par une
matrice `80 × 80` fixe, et elle ne dépend pas du couple de décalages : on la calcule une
fois par `α`, pas une fois par statistique.

PUISSANCE MESUREE (générateurs plantés, 3 000 tirages, ramenée aux 70 560 de l'archive)
======================================================================================
    r_i = 2·r_{i-3} + r_{i-7}      couple (α,β) = (1,2), décalages (0,0)   z =  +92
    r_i = r_{i-3} - 2·r_{i-7}      (1,2), (0,0)                            z =  +96
    r_i = 2·r_{i-1} + r_{i-2}      (1,2), (0,0)                            z = +137
    r_i = r_{i-3} + r_{i-7}        (1,1), (0,0)  — témoin                  z = +121

Le couple gagnant est `(1,2)` et non `(2,1)` : la relation `r_i = 2a + b` se lit aussi
`b = r_i - 2a`, et le détecteur trouve la forme où la somme tombe dans le tirage courant.
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import h164_energie_signee as S                                        # noqa: E402

POOL, DRAWN = 80, 20
EXP_ID = "h166.energie_coefficients"
FJETON = "/tmp/h166_jeton.json"
REPS = 6
COEFS = (1, 2, -1, -2)
PAIRES = [(a, b) for a in COEFS for b in COEFS]
COUPLES = S.COUPLES
CLES = [(ab, g) for ab in PAIRES for g in COUPLES]
_P = {}


def say(*a):
    print(*a, flush=True)


def matrice(a):
    if a not in _P:
        Q = np.zeros((POOL, POOL))
        for u in range(POOL):
            Q[u, (a * u) % POOL] += 1.0
        _P[a] = Q
    return _P[a]


def deltas(al, be):
    def rg(c):
        return range(0, c) if c > 0 else range(c + 1, 1)
    return sorted({(x + y) % POOL for x in rg(al) for y in rg(be)})


def spectres(m):
    """rfft de l'indicatrice DILATEE, une fois par coefficient — pas une fois par
    statistique. C'est ce qui rend les 448 statistiques abordables."""
    return {a: np.fft.rfft(m.astype(np.float64) @ matrice(a), axis=1) for a in COEFS}


def energie(m, sp, al, be, g1, g2):
    n = len(m)
    lo, hi = min(0, g1, g2), max(0, g1, g2)
    deb, fin = max(0, hi), n + min(0, lo)
    conv = np.rint(np.fft.irfft(sp[al][deb - g1: fin - g1] * sp[be][deb - g2: fin - g2],
                                n=POOL, axis=1)).astype(np.int64)
    C = m[deb:fin]
    s = np.zeros(len(C), np.int64)
    for d in deltas(al, be):
        w = (np.arange(POOL) - d) % POOL
        s += (conv[:, w] * C).sum(axis=1)
    return s


def plante(n, graine, pas, saut=80):
    import random
    M32 = 1 << 32
    rng = random.Random(graine)
    r = [rng.randrange(M32) for _ in range(saut)]
    i = saut
    m = np.zeros((n, POOL), bool)
    for j in range(n):
        vus = set()
        while len(vus) < DRAWN:
            r.append(pas(r, i) % M32)
            i += 1
            vus.add((r[i - 1] * POOL) >> 32)
        m[j, list(vus)] = True
    return m


if __name__ == "__main__":
    import lab

    if "--puissance" in sys.argv:
        say("h166 --puissance : generateurs plantes, aucune donnee reelle")
        n = int(sys.argv[sys.argv.index("--nb") + 1]) if "--nb" in sys.argv else 3000
        rng = np.random.default_rng(37)
        mn = S.srs(n, rng)
        spn = spectres(mn)
        NUL = {}
        for ab in PAIRES:
            for g in COUPLES:
                t = energie(mn, spn, *ab, *g)
                NUL[(ab, g)] = (t.mean(), t.std(ddof=1) / np.sqrt(len(t)))
        M32 = 1 << 32
        CAS = [("r_i = 2 r_{i-3} + r_{i-7}", lambda r, i: 2 * r[i - 3] + r[i - 7]),
               ("r_i = r_{i-3} - 2 r_{i-7}", lambda r, i: r[i - 3] - 2 * r[i - 7]),
               ("r_i = 2 r_{i-1} + r_{i-2}", lambda r, i: 2 * r[i - 1] + r[i - 2]),
               ("r_i = r_{i-3} + r_{i-7}", lambda r, i: r[i - 3] + r[i - 7])]
        say(f"{'generateur':>28} | {'(a,b)':>9} {'couple':>9} | {'z sur 70 560':>13}")
        for nom, pas in CAS:
            m = plante(n, 4444, pas)
            sp = spectres(m)
            best, bz = None, 0.0
            for ab in PAIRES:
                for g in COUPLES:
                    mu, sd = NUL[(ab, g)]
                    z = (energie(m, sp, *ab, *g).mean() - mu) / sd
                    if abs(z) > abs(bz):
                        best, bz = (ab, g), z
            say(f"{nom:>28} | {str(best[0]):>9} {str(best[1]):>9} | "
                f"{bz*np.sqrt(70560/n):+13.1f}")
        sys.exit(0)

    if "--archive" not in sys.argv:
        print(__doc__)
        sys.exit(0)

    HYP = (f"Les tirages de l'archive n'ont, pour aucune des {len(CLES)} statistiques "
           "T_{alpha,beta}(g1,g2) — coefficients alpha, beta dans {1, 2, -1, -2} croises "
           "avec les 28 couples de decalages signes — d'exces ni de deficit d'energie "
           "additive. C'est l'extension aux recurrences a COEFFICIENTS "
           "r_i = alpha r_{i-K} + beta r_{i-L}, que les §177 a §180 ne couvrent pas "
           "puisqu'ils supposent alpha = beta = 1")
    STAT = (f"D = max sur les {len(CLES)} statistiques de |z| ; p bilateral corrige par "
            f"Bonferroni sur {len(CLES)}")
    NUL = (f"Simulation : {REPS} x 70 560 = {REPS*70560} tirages SRS 20/80, moyenne et "
           "variance PAR TIRAGE de chaque statistique ; ecart-type de la moyenne = "
           "sd/sqrt(n). Six replicats suffisent : c'est la loi par tirage qui est estimee, "
           "sur plus de quatre cent mille tirages")
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
    spM = spectres(M)
    obs = np.array([energie(M, spM, *ab, *g).mean() for ab, g in CLES])
    say(f"h166 : {n} tirages, {len(CLES)} statistiques "
        f"({len(PAIRES)} couples de coefficients x {len(COUPLES)} decalages)")

    rng = np.random.default_rng(20260906)
    s1 = np.zeros(len(CLES)); s2 = np.zeros(len(CLES)); cpt = 0
    for k in range(REPS):
        m = S.srs(n, rng)
        sp = spectres(m)
        for j, (ab, g) in enumerate(CLES):
            t = energie(m, sp, *ab, *g).astype(np.float64)
            s1[j] += t.sum(); s2[j] += (t * t).sum()
        cpt += n
        say(f"   nulle {k+1}/{REPS}")
    mu = s1 / cpt
    sd = np.sqrt(np.maximum(s2 / cpt - mu * mu, 0) / n)
    z = (obs - mu) / sd
    from math import erfc, sqrt
    p1 = np.array([erfc(abs(v) / sqrt(2)) for v in z])
    p = min(1.0, len(CLES) * p1.min())
    jm = int(np.argmax(np.abs(z)))
    say("\n   les six plus grands |z| :")
    for j in np.argsort(-np.abs(z))[:6]:
        say(f"   (a,b) = {str(CLES[j][0]):>9}  decalages {str(CLES[j][1]):>9} | "
            f"archive {obs[j]:10.4f} | nulle {mu[j]:10.4f} | z {z[j]:+7.3f}")
    say(f"\n   |z| max = {abs(z[jm]):.3f} en {CLES[jm]} ; "
        f"p (Bonferroni sur {len(CLES)}) = {p:.4f}")
    TOK["m_extra"] = len(CLES) - 1
    lab.record(
        TOK, float(np.abs(z).max()), p=float(p),
        verdict="conforme" if p > 0.05 else "ECART",
        power_at=("PUISSANCE MESUREE sur generateurs plantes, 3 000 tirages, ramenee aux "
                  "70 560 de l'archive : r_i = 2 r_{i-3} + r_{i-7} z = +92 ; "
                  "r_i = r_{i-3} - 2 r_{i-7} z = +96 ; r_i = 2 r_{i-1} + r_{i-2} (forme "
                  "multiplication-et-retenue) z = +137 ; temoin additif (3,7) z = +121"),
        notes=("ENERGIE ADDITIVE A COEFFICIENTS (§181) : la classe est quasi-homogene autant "
               "qu'elle est quasi-additive, c(alpha x) = alpha c(x) + delta avec delta dans "
               "{0,...,alpha-1}, donc le detecteur se generalise en DILATANT l'indicatrice "
               "avant de convoluer. La dilatation ne depend pas du couple de decalages : une "
               f"fois par coefficient, pas une fois par statistique. {len(CLES)} statistiques, "
               f"|z| max = {abs(z[jm]):.3f}."))
    say("   consigne.")
