"""h165 — le même détecteur pour l'échantillonneur à MODULO : le carré complet
(THEORIE_ETAT §7.27 ; RAPPORT §180).

CE QUI RESTAIT
==============
Les §177, §178 et §179 mesurent la coïncidence additive avec `δ` dans `{0, 1}`. Ce jeu de
`δ` est celui de la lecture par TRONCATURE, `v = 1 + ((x·80) >> 32)`. L'échantillonneur à
MODULO, `v = 1 + (x mod 80)`, en a un autre : comme `2^32 mod 80 = 16`,

    c(a + b mod 2^32) = c(a) + c(b) - 16·e   (mod 80),   e dans {0, 1},

d'où `δ` dans `{0, -16}` au décalage 0, et dans `{0, 1, -48, -47}` au décalage 1 (le bit
perdu ajoute sa propre retenue). Un Fibonacci retardé lu par modulo est donc INVISIBLE au
détecteur des sections précédentes — il faut lui donner son jeu de `δ`.

Ce fichier ferme le carré : deux échantillonneurs (troncature au §179, modulo ici) × deux
signes (additif, soustractif) × les degrés 7 à 100 × les vingt-huit couples de décalages
signés.

PUISSANCE MESUREE (générateurs plantés, 4 000 tirages, ramenée aux 70 560 de l'archive)
======================================================================================
    additif (3,7)   lu par MODULO s0    couple (0,  0)    z = +129
    TYPE_2 (1,15)   lu par MODULO s0    couple (1,  0)    z = +132
    TYPE_3 (3,31)   lu par MODULO s0    couple (1,  0)    z = +130
    Knuth (24,55)   lu par MODULO s0    couple (1, -1)    z = +161   (soustractif)
    TYPE_2 (1,15)   lu par MODULO s1    couple (1,  0)    z =  +86

Le décalage 1 perd du terrain — son `δ` a quatre valeurs au lieu de deux, donc la
coïncidence est quatre fois plus banale — mais `+86` écarts-types laissent de la marge.
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import h164_energie_signee as S                                        # noqa: E402

POOL, DRAWN = 80, 20
EXP_ID = "h165.energie_modulo"
FJETON = "/tmp/h165_jeton.json"
REPS = 40
COUPLES = S.COUPLES
# les deux lectures que le §179 ne couvre pas
JEUX = (("modulo s0", (0, -16)), ("modulo s1", (0, 1, -48, -47)))
CLES = [(nom, g) for nom, _ in JEUX for g in COUPLES]


def say(*a):
    print(*a, flush=True)


def energie(m, g1, g2, deltas):
    """T(g1,g2) avec un jeu de `δ` quelconque. Décalage négatif = tirage postérieur."""
    n = len(m)
    lo, hi = min(0, g1, g2), max(0, g1, g2)
    deb, fin = max(0, hi), n + min(0, lo)
    A = m[deb - g1: fin - g1]
    B = m[deb - g2: fin - g2]
    C = m[deb:fin]
    conv = np.rint(np.fft.irfft(
        np.fft.rfft(A.astype(np.float64), axis=1) * np.fft.rfft(B.astype(np.float64), axis=1),
        n=POOL, axis=1)).astype(np.int64)
    s = np.zeros(len(C), np.int64)
    for d in deltas:
        w = (np.arange(POOL) - d) % POOL
        s += (conv[:, w] * C).sum(axis=1)
    return s


def plante(K, L, n, graine, signe=1, shift=0):
    """lu par MODULO : la classe est `(x >> shift) mod 80`."""
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
            vus.add((r[i - 1] >> shift) % POOL)
        m[j, list(vus)] = True
    return m


if __name__ == "__main__":
    import lab

    if "--puissance" in sys.argv:
        say("h165 --puissance : generateurs plantes lus par MODULO, aucune donnee reelle")
        n = int(sys.argv[sys.argv.index("--nb") + 1]) if "--nb" in sys.argv else 4000
        rng = np.random.default_rng(31)
        mn = S.srs(n, rng)
        NUL = {}
        for nom, dl in JEUX:
            for g in COUPLES:
                t = energie(mn, *g, dl)
                NUL[(nom, g)] = (t.mean(), t.std(ddof=1) / np.sqrt(len(t)))
        say(f"{'generateur':>30} | {'lecture':>10} {'couple':>9} | {'z sur 70 560':>13}")
        CAS = [(3, 7, 1, 0, "additif (3,7)"), (1, 15, 1, 0, "TYPE_2 (1,15)"),
               (3, 31, 1, 0, "TYPE_3 (3,31)"), (24, 55, -1, 0, "Knuth (24,55) soustractif"),
               (1, 63, 1, 0, "TYPE_4 (1,63)"), (1, 15, 1, 1, "TYPE_2 (1,15) decalage 1")]
        for K, L, sg, sh, nom in CAS:
            m = plante(K, L, n, 777 + K + L, sg, sh)
            best, bz = None, 0.0
            for jn, dl in JEUX:
                for g in COUPLES:
                    mu, sd = NUL[(jn, g)]
                    z = (energie(m, *g, dl).mean() - mu) / sd
                    if abs(z) > abs(bz):
                        best, bz = (jn, g), z
            say(f"{nom:>30} | {best[0]:>10} {str(best[1]):>9} | "
                f"{bz*np.sqrt(70560/n):+13.1f}")
        sys.exit(0)

    if "--archive" not in sys.argv:
        print(__doc__)
        sys.exit(0)

    HYP = ("Les tirages de l'archive n'ont, pour AUCUN des 56 couples (lecture, decalages) — "
           "deux jeux de delta propres a l'echantillonneur a MODULO, delta dans {0,-16} au "
           "decalage 0 et {0,1,-48,-47} au decalage 1, croises avec les 28 couples de "
           "decalages signes du §179 — d'exces ni de deficit d'energie additive. C'est la "
           "moitie du carre que les §177 a §179 ne couvrent pas : ils supposent tous la "
           "lecture par troncature, dont le delta vaut {0,1}")
    STAT = (f"D = max sur les {len(CLES)} statistiques de |z| ; p bilateral corrige par "
            f"Bonferroni sur {len(CLES)}")
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
    DL = dict(JEUX)
    obs = np.array([energie(M, *g, DL[nom]).mean() for nom, g in CLES])
    say(f"h165 : {n} tirages, {len(CLES)} statistiques (2 lectures x {len(COUPLES)} couples)")

    rng = np.random.default_rng(20260905)
    s1 = np.zeros(len(CLES)); s2 = np.zeros(len(CLES)); cpt = 0
    for k in range(REPS):
        m = S.srs(n, rng)
        for j, (nom, g) in enumerate(CLES):
            t = energie(m, *g, DL[nom]).astype(np.float64)
            s1[j] += t.sum(); s2[j] += (t * t).sum()
        cpt += n
        if (k + 1) % 10 == 0:
            say(f"   nulle {k+1}/{REPS}")
    mu = s1 / cpt
    sd = np.sqrt(np.maximum(s2 / cpt - mu * mu, 0) / n)
    z = (obs - mu) / sd
    from math import erfc, sqrt
    p1 = np.array([erfc(abs(v) / sqrt(2)) for v in z])
    p = min(1.0, len(CLES) * p1.min())
    jm = int(np.argmax(np.abs(z)))
    ordre = np.argsort(-np.abs(z))[:6]
    say(f"\n   les six plus grands |z| :")
    for j in ordre:
        say(f"   {CLES[j][0]:>10} {str(CLES[j][1]):>9} | archive {obs[j]:10.4f} | "
            f"nulle {mu[j]:10.4f} | z {z[j]:+7.3f}")
    say(f"\n   |z| max = {abs(z[jm]):.3f} en {CLES[jm]} ; "
        f"p (Bonferroni sur {len(CLES)}) = {p:.4f}")
    TOK["m_extra"] = len(CLES) - 1
    lab.record(
        TOK, float(np.abs(z).max()), p=float(p),
        verdict="conforme" if p > 0.05 else "ECART",
        power_at=("PUISSANCE MESUREE sur generateurs plantes lus par MODULO, 4 000 tirages, "
                  "ramenee aux 70 560 de l'archive : additif (3,7) z = +129 ; TYPE_2 (1,15) "
                  "+132 ; TYPE_3 (3,31) +130 ; Knuth (24,55) soustractif +161 ; TYPE_2 au "
                  "decalage 1 +86 (son delta a quatre valeurs, la coincidence est quatre fois "
                  "plus banale). Le detecteur voit donc la lecture par modulo comme il voit "
                  "celle par troncature"),
        notes=("ENERGIE ADDITIVE, LECTURE PAR MODULO (§180) : 2^32 mod 80 = 16, donc delta "
               "vaut {0,-16} au decalage 0 et {0,1,-48,-47} au decalage 1. Les §177 a §179 "
               "supposaient tous {0,1}, c'est-a-dire la troncature : cette section ferme "
               f"l'autre moitie du carre. {len(CLES)} statistiques, |z| max = "
               f"{abs(z[jm]):.3f} en {CLES[jm]}."))
    say("   consigne.")
