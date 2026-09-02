"""h168 — l'énergie additive à TROIS TERMES : `r_i = r_{i-a} + r_{i-b} + r_{i-c}`
(THEORIE_ETAT §7.28 ; RAPPORT §183).

CE QUI RESTAIT
==============
Les §177 à §182 testent des récurrences à **deux** termes. Or les générateurs additifs à
trois taps existent et servent : pentanômes de rétroaction, `add-with-carry` à plusieurs
retards, Fibonacci retardés généralisés. Ils n'ont aucune coïncidence de la forme
`u + v ∈ C` — il leur en faut une à quatre corps :

    T3(g1, g2, g3) = #{ (u,v,w) : u + v + w + δ (mod 80) dans C_t , δ dans {0,1,2} }
                      u dans C_{t-g1}, v dans C_{t-g2}, w dans C_{t-g3}

Le support de `δ` passe de deux à trois valeurs — deux retenues au lieu d'une — et la nulle
monte de `200` à `6 012` par tirage : le bruit croît comme la racine du comptage, donc la
puissance baisse d'un facteur `√30 ≈ 5,5`. Elle reste très suffisante.

PUISSANCE MESUREE (générateurs plantés, 2 500 tirages, ramenée aux 70 560 de l'archive)
======================================================================================
    r_i = r_{i-2} + r_{i-5} + r_{i-7}      triplet (0, 0, 0)     z = +31
    r_i = r_{i-7} + r_{i-15} + r_{i-22}    triplet (1, 1, 1)     z = +23
    r_i = r_{i-24} + r_{i-55} + r_{i-80}   triplet (3, 3, -1)    z = +25
    r_i = r_{i-3} + r_{i-7}  (témoin à deux termes)               z = +40

La règle de portée du §7.28 s'applique telle quelle : `g_j ≈ retard_j / 22,85`. Le
générateur à retards `24, 55, 80` sort en `(3, 3, -1)` — `80/22,85 = 3,5`, `55/22,85 = 2,4`,
et le troisième décalage est négatif parce que la relation se relit avec la somme dans un
tirage antérieur, exactement comme au §179.
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
EXP_ID = "h168.energie_trois_termes"
FJETON = "/tmp/h168_jeton.json"
REPS = 12
DELTAS = (0, 1, 2)
TRIPLETS = [(a, b, c) for a in range(-1, 4) for b in range(-1, a + 1)
            for c in range(-1, b + 1)]


def say(*a):
    print(*a, flush=True)


def energie(m, g):
    n = len(m)
    lo, hi = min(0, *g), max(0, *g)
    deb, fin = max(0, hi), n + min(0, lo)
    F = [np.fft.rfft(m[deb - x: fin - x].astype(np.float64), axis=1) for x in g]
    conv = np.rint(np.fft.irfft(F[0] * F[1] * F[2], n=POOL, axis=1)).astype(np.int64)
    C = m[deb:fin]
    s = np.zeros(len(C), np.int64)
    for d in DELTAS:
        w = (np.arange(POOL) - d) % POOL
        s += (conv[:, w] * C).sum(axis=1)
    return s


def plante(n, graine, taps):
    import random
    rng = random.Random(graine)
    r = [rng.randrange(M32) for _ in range(max(120, max(taps) + 1))]
    i = len(r)
    m = np.zeros((n, POOL), bool)
    for j in range(n):
        vus = set()
        while len(vus) < DRAWN:
            r.append(sum(r[i - t] for t in taps) % M32)
            i += 1
            vus.add((r[i - 1] * POOL) >> 32)
        m[j, list(vus)] = True
    return m


if __name__ == "__main__":
    import lab

    if "--puissance" in sys.argv:
        n = int(sys.argv[sys.argv.index("--nb") + 1]) if "--nb" in sys.argv else 2500
        say(f"h168 --puissance : {n} tirages plantes, aucune donnee reelle")
        rng = np.random.default_rng(53)
        mn = S.srs(n, rng)
        NUL = {}
        for g in TRIPLETS:
            t = energie(mn, g)
            NUL[g] = (t.mean(), t.std(ddof=1) / np.sqrt(len(t)))
        say(f"   {len(TRIPLETS)} triplets ; nulle T3 = {NUL[(0,0,0)][0]:.1f} par tirage")
        say(f"{'generateur':>34} | {'triplet':>13} | {'z sur 70 560':>13}")
        for taps, nom in (((2, 5, 7), "r_i = r_2 + r_5 + r_7"),
                          ((7, 15, 22), "r_i = r_7 + r_15 + r_22"),
                          ((24, 55, 80), "r_i = r_24 + r_55 + r_80"),
                          ((3, 7), "r_i = r_3 + r_7 (deux termes)")):
            m = plante(n, 3210 + sum(taps), taps)
            best, bz = None, 0.0
            for g in TRIPLETS:
                mu, sd = NUL[g]
                z = (energie(m, g).mean() - mu) / sd
                if abs(z) > abs(bz):
                    best, bz = g, z
            say(f"{nom:>34} | {str(best):>13} | {bz*np.sqrt(70560/n):+13.1f}")
        sys.exit(0)

    if "--archive" not in sys.argv:
        print(__doc__)
        sys.exit(0)

    HYP = (f"Les tirages de l'archive n'ont, pour aucun des {len(TRIPLETS)} triplets de "
           "decalages signes, d'exces ni de deficit d'energie additive A TROIS TERMES : le "
           "nombre moyen de triplets (u,v,w) de classes publiees par les tirages t-g1, t-g2 "
           "et t-g3 dont la somme u+v+w, +1 ou +2 est publiee par le tirage t est celui d'un "
           "tirage SRS. C'est la trace d'une recurrence additive a TROIS taps, que les §177 a "
           "§182 ne couvrent pas puisqu'ils n'en testent que deux")
    STAT = (f"D = max sur les {len(TRIPLETS)} triplets de |z| ; p bilateral corrige par "
            f"Bonferroni sur {len(TRIPLETS)}")
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
    M = np.asarray(A.mask)
    n = len(M)
    obs = np.array([energie(M, g).mean() for g in TRIPLETS])
    say(f"h168 : {n} tirages, {len(TRIPLETS)} triplets")

    rng = np.random.default_rng(20260908)
    s1 = np.zeros(len(TRIPLETS)); s2 = np.zeros(len(TRIPLETS)); cpt = 0
    for k in range(REPS):
        m = S.srs(n, rng)
        for j, g in enumerate(TRIPLETS):
            t = energie(m, g).astype(np.float64)
            s1[j] += t.sum(); s2[j] += (t * t).sum()
        cpt += n
        say(f"   nulle {k+1}/{REPS}")
    mu = s1 / cpt
    sd = np.sqrt(np.maximum(s2 / cpt - mu * mu, 0) / n)
    z = (obs - mu) / sd
    from math import erfc, sqrt
    p1 = np.array([erfc(abs(v) / sqrt(2)) for v in z])
    p = min(1.0, len(TRIPLETS) * p1.min())
    jm = int(np.argmax(np.abs(z)))
    say("\n   les six plus grands |z| :")
    for j in np.argsort(-np.abs(z))[:6]:
        say(f"   {str(TRIPLETS[j]):>13} | archive {obs[j]:11.4f} | nulle {mu[j]:11.4f} | "
            f"z {z[j]:+7.3f}")
    say(f"\n   |z| max = {abs(z[jm]):.3f} au triplet {TRIPLETS[jm]} ; "
        f"p (Bonferroni sur {len(TRIPLETS)}) = {p:.4f}")
    TOK["m_extra"] = len(TRIPLETS) - 1
    lab.record(
        TOK, float(np.abs(z).max()), p=float(p),
        verdict="conforme" if p > 0.05 else "ECART",
        power_at=("PUISSANCE MESUREE sur generateurs plantes, 2 500 tirages, ramenee aux "
                  "70 560 de l'archive : r_2+r_5+r_7 z = +31 en (0,0,0) ; r_7+r_15+r_22 "
                  "z = +23 en (1,1,1) ; r_24+r_55+r_80 z = +25 en (3,3,-1) ; temoin a deux "
                  "termes (3,7) z = +40"),
        notes=("ENERGIE A TROIS TERMES (§183) : deux retenues au lieu d'une, donc delta a "
               "trois valeurs, et la nulle monte de 200 a 6 012 par tirage — le bruit croit "
               "comme la racine du comptage, la puissance baisse d'un facteur 5,5 et reste "
               "tres suffisante. La regle de portee du §7.28 s'applique telle quelle : "
               f"g_j = retard_j / 22,85. |z| max = {abs(z[jm]):.3f}."))
    say("   consigne.")
