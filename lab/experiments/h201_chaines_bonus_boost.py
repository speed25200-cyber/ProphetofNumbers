"""h201 — LES CHAÎNES DU BONUS ET DU BOOST : le flux le plus propre de l'archive, testé
comme une chaîne de Markov (RAPPORT §222).

POURQUOI CE FLUX-LÀ, ET PAS UN AUTRE
====================================
Les vingt numéros d'un tirage sont un **ensemble** : l'ordre est perdu, et chaque numéro
n'est qu'un mot parmi une vingtaine, dilué (§7.34 : `2,70` bits utiles par mot).

Le **bonus** est autre chose. C'est **un seul symbole par tirage**, identifié, uniforme sur
les quatre-vingts, et il correspond à **un mot précis** du générateur. C'est l'observable la
plus propre de tout le dossier. Le §197 y a mesuré une **énergie** — des sommes de
corrélations à des retards choisis. Personne n'a mesuré sa **chaîne** :

> La table de contingence `80 × 80` de `b_t` vers `b_{t+d}` est-elle uniforme ?

C'est le test standard d'une structure de Markov, il est fin là où l'énergie est grossière,
et il n'exige aucune hypothèse sur la forme du générateur. Le **multiplicateur** subit le
même traitement sur sa grille à six valeurs, et le **rang du bonus** sur la sienne à vingt.

ET C'EST LA PRÉDICTION LA PLUS DIRECTE QUI SOIT
===============================================
Prédire le bonus, c'est **prédire un numéro** — pas vingt, pas cinq : un. La famille `D`
ajuste la chaîne sur la première moitié et joue les `k` meilleurs successeurs sur la
seconde. La nulle est exacte : `k/80`.

QUATRE FAMILLES
===============
  **A  LA CHAÎNE DU BONUS.** `80 × 80` cases à chaque retard `d = 1 … 20`, plus le `khi²`
     d'indépendance de chaque table (`6 241` degrés de liberté) et le `khi²` de la marge.
  **B  LA CHAÎNE DU MULTIPLICATEUR.** `6 × 6` à chaque retard, nulle exacte donnée par les
     secteurs `(41, 19, 12, 4, 2, 2)/80` établis au §106.
  **C  LA CHAÎNE DU RANG DU BONUS.** `20 × 20` à chaque retard, marge uniforme à `1/20`.
  **D  LE PRÉDICTEUR DU BONUS.** Top-`k` du successeur, hors échantillon, `k = 1, 2, 5, 10`.

La nulle de chaque case est **exacte** — sous SRS le bonus est uniforme sur les
quatre-vingts et indépendant d'un tirage à l'autre — mais les cases d'une table sont liées
par leurs marges, donc la loi du **maximum** est calibrée sur répliques (§7.32).
"""

import json
import os
import sys
from math import erfc, sqrt

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POOL, DRAWN = 80, 20
EXP_ID = "h201.chaines_bonus_boost"
FJETON = "/tmp/h201_jeton.json"
REPS = 200
RETARDS = tuple(range(1, 21))
KS = (1, 2, 5, 10)
SECTEURS = np.array([41, 19, 12, 4, 2, 2], np.float64) / POOL


def say(*a):
    print(*a, flush=True)


def table(x, d, m):
    """contingence m x m de x_t vers x_{t+d}."""
    return np.bincount(x[:len(x) - d] * m + x[d:], minlength=m * m).reshape(m, m)


def chaine(x, m, p):
    """max |z| et somme des khi2 sur tous les retards, pour un flux a m symboles."""
    zmax, khi = 0.0, 0.0
    arg = None
    att0 = np.outer(p, p)
    for d in RETARDS:
        n = len(x) - d
        A = att0 * n
        Z = (table(x, d, m) - A) / np.sqrt(A * (1 - att0))
        khi += float((((table(x, d, m) - A) ** 2) / A).sum())
        j = int(np.argmax(np.abs(Z)))
        if abs(Z.flat[j]) > abs(zmax):
            zmax, arg = float(Z.flat[j]), (d, j // m, j % m)
    return zmax, khi, arg


def resume(b, bo, rg):
    zA, kA, _ = chaine(b, POOL, np.full(POOL, 1.0 / POOL))
    zB, kB, _ = chaine(bo, 6, SECTEURS)
    zC, kC, _ = chaine(rg, DRAWN, np.full(DRAWN, 1.0 / DRAWN))
    return np.array([abs(zA), kA, abs(zB), kB, abs(zC), kC])


def predicteur(b, deb1, fin1, deb2, fin2):
    T = table(b[deb1:fin1], 1, POOL).astype(np.float64)
    ordre = np.argsort(-T, axis=1, kind="stable")
    src, cible = b[deb2:fin2 - 1], b[deb2 + 1:fin2]
    n = len(cible)
    out = {}
    for k in KS:
        h = int((ordre[src, :k] == cible[:, None]).any(axis=1).sum())
        p = k / POOL
        out[k] = (h, n, (h - n * p) / sqrt(n * p * (1 - p)))
    return out


if __name__ == "__main__":
    import lab

    A = lab.load()
    N = len(A.ids)
    NUMS = np.asarray(A.nums).astype(np.int64)
    b = np.asarray(A.bonus).astype(np.int64) - 1
    bo = np.asarray(A.boost).astype(np.int64)
    bo = np.searchsorted(np.array([1, 2, 3, 4, 5, 10]), bo)
    rg = np.argmax(NUMS == (b[:, None] + 1), axis=1)
    n2 = N // 2
    MTOT = (POOL * POOL + 6 * 6 + DRAWN * DRAWN) * len(RETARDS) + 3 + len(KS)

    HYP = ("Le bonus, le multiplicateur et le rang du bonus sont des suites sans memoire. "
           "Les vingt numeros d'un tirage sont un ENSEMBLE — l'ordre est perdu et chaque "
           "numero n'est qu'un mot dilue parmi une vingtaine. Le bonus est autre chose : un "
           "seul symbole par tirage, identifie, uniforme sur les quatre-vingts, "
           "correspondant a UN mot precis du generateur — l'observable la plus propre du "
           "dossier. Le §197 y a mesure une ENERGIE, c'est-a-dire des sommes de correlations "
           "a des retards choisis ; personne n'a mesure sa CHAINE, la table de contingence "
           "80x80 de b_t vers b_{t+d}, qui est le test standard d'une structure de Markov, "
           "fin la ou l'energie est grossiere, et qui n'exige aucune hypothese sur la forme "
           f"du generateur. Quatre familles : A la chaine du bonus, {POOL}x{POOL} cases a "
           f"chaque retard de 1 a {max(RETARDS)} plus le khi2 d'independance et celui de la "
           f"marge ; B celle du multiplicateur sur sa grille a six valeurs, de nulle exacte "
           f"(41,19,12,4,2,2)/80 etablie au §106 ; C celle du rang du bonus, {DRAWN}x{DRAWN}, "
           f"marge uniforme a 1/20 ; D le PREDICTEUR du bonus, qui ajuste la chaine sur une "
           f"moitie et joue les k meilleurs successeurs sur l'autre — predire le bonus, "
           f"c'est predire UN numero, pas vingt ni cinq")
    STAT = (f"max |z| et somme des khi2 sur les {len(RETARDS)} retards, pour chacune des "
            f"trois chaines, reduits par la loi EMPIRIQUE du maximum sur {REPS} repliques "
            f"chacune laissee hors de sa propre normalisation ; plus le z du predicteur "
            f"pour chaque k")
    NUL = ("EXACTE par case : sous SRS le bonus est uniforme sur les quatre-vingts et "
           "independant d'un tirage a l'autre, donc chaque case vaut n/6400 en moyenne ; le "
           "multiplicateur suit les secteurs du §106 ; le rang est uniforme sur vingt. Les "
           "cases d'une table etant liees par leurs marges, la loi du MAXIMUM est calibree "
           "sur repliques (§7.32). Famille D : k/80 exactement")
    VER = ("conforme si le maximum reduit reste sous le 95e centile de sa loi empirique et "
           "si aucun k du predicteur ne depasse le seuil de Bonferroni ; MEMOIRE sinon")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h201 : {N} tirages ; retards 1 a {max(RETARDS)} ; {MTOT} statistiques")
    mb = np.bincount(b, minlength=POOL)
    khimarge = float(((mb - N / POOL) ** 2 / (N / POOL)).sum())
    say(f"   marge du bonus : khi2 = {khimarge:.2f} sur {POOL-1} ddl "
        f"(attendu {POOL-1}, ecart-type {sqrt(2*(POOL-1)):.1f}, "
        f"z = {(khimarge-(POOL-1))/sqrt(2*(POOL-1)):+.2f})")
    say(f"   attendu par case : bonus {(N-1)/(POOL*POOL):.2f}, rang "
        f"{(N-1)/(DRAWN*DRAWN):.1f}, multiplicateur variable")

    obs = resume(b, bo, rg)
    noms = ("bonus max|z|", "bonus khi2", "boost max|z|", "boost khi2",
            "rang max|z|", "rang khi2")
    _, _, argA = chaine(b, POOL, np.full(POOL, 1.0 / POOL))
    say(f"\nARCHIVE   bonus : max |z| = {obs[0]:.3f} au retard {argA[0]}, "
        f"{argA[1]+1} -> {argA[2]+1}")

    # Les repliques passent par une ARCHIVE SRS complete et non par trois flux tires
    # independamment : dans l'archive le bonus et son rang sont couples — le rang est la
    # position du bonus dans le tirage trie — et la loi du maximum porte sur les six
    # statistiques a la fois. Simuler les flux separement casserait ce couplage et
    # fausserait la loi du maximum.
    V = np.empty((REPS, 6))
    rng = np.random.default_rng(0x201)
    for r in range(REPS):
        S = lab.srs(N, rng)
        NUs = np.nonzero(S)[1].reshape(N, DRAWN)
        rs = rng.integers(0, DRAWN, N)
        bs = NUs[np.arange(N), rs]
        V[r] = resume(bs, rng.choice(6, N, p=SECTEURS), rs)
        if (r + 1) % 50 == 0:
            say(f"   ... {r+1}/{REPS} repliques")

    s1, s2 = V.sum(axis=0), (V * V).sum(axis=0)
    mu, sd = V.mean(axis=0), V.std(axis=0)
    zr = (obs - mu) / np.maximum(sd, 1e-12)
    o = float(np.abs(zr).max())
    mx = np.empty(REPS)
    for r in range(REPS):
        m_ = (s1 - V[r]) / (REPS - 1)
        v_ = np.maximum((s2 - V[r] * V[r]) / (REPS - 1) - m_ * m_, 1e-12)
        mx[r] = float(np.abs((V[r] - m_) / np.sqrt(v_)).max())
    pA = float((1 + int((mx >= o).sum())) / (1 + REPS))
    say(f"\n   {'statistique':>14} | {'archive':>13} | {'repliques':>22} | {'z reduit':>9}")
    for i, nom in enumerate(noms):
        say(f"   {nom:>14} | {obs[i]:13.2f} | {mu[i]:13.2f} +/-{sd[i]:8.2f} | "
            f"{zr[i]:+9.3f}")
    say(f"   maximum reduit {o:.3f} ; 95e centile {np.percentile(mx, 95):.3f} ; "
        f"p = {pA:.4f}")

    say(f"\nD  LE PREDICTEUR DU BONUS (chaine ajustee sur une moitie, jouee sur l'autre)")
    say(f"   {'sens':>8} {'k':>3} | {'justes':>16} | {'taux':>9} | {'hasard':>8} | {'z':>7}")
    zD, detD = [], []
    for nom, (a1, b1, a2, b2) in (("H1->H2", (0, n2, n2, N)), ("H2->H1", (n2, N, 0, n2))):
        res = predicteur(b, a1, b1, a2, b2)
        for k in KS:
            h, n_, zz = res[k]
            zD.append(zz)
            detD.append(f"{nom} k={k} {100*h/n_:.4f} % z={zz:+.2f}")
            say(f"   {nom:>8} {k:3d} | {h:7d} / {n_:7d} | {100*h/n_:8.4f} % | "
                f"{100*k/POOL:7.3f} % | {zz:+7.2f}")

    lo, hi = 0.0, 40.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if erfc(mid / sqrt(2)) > 0.05 / len(zD):
            lo = mid
        else:
            hi = mid
    ZD = 0.5 * (lo + hi)
    zmax = max(zD, key=abs)
    pD = float(min(1.0, erfc(abs(zmax) / sqrt(2)) * len(zD)))
    p = float(min(pA, pD))
    verdict = "MEMOIRE" if (pA <= 0.05 or abs(zmax) > ZD) else "conforme"
    say(f"\n   max |z| predicteur = {zmax:+.3f}   seuil de Bonferroni sur {len(zD)} = "
        f"{ZD:.3f}")
    say(f"   p retenue = {p:.4f}   ->   {verdict}")

    TOK["m_extra"] = MTOT - 1
    lab.record(
        TOK, float(max(o, abs(zmax))), p=p, verdict=verdict,
        power_at=(f"chaine du bonus : {(N-1)/(POOL*POOL):.2f} attendus par case, ce qui est "
                  f"peu, mais le khi2 agrege sur {(POOL-1)**2} degres de liberte a une "
                  f"puissance tres superieure a celle d'une case isolee — c'est lui qui "
                  f"porte le test. Famille D : sur {N-n2-1} tirages hors echantillon, "
                  f"l'ecart-type du taux du top-1 vaut "
                  f"{100*sqrt((1/POOL)*(1-1/POOL)/(N-n2-1)):.4f} point, donc un predicteur "
                  f"a 2 % au lieu de 1,25 % sortirait a z = "
                  f"{0.0075/sqrt((1/POOL)*(1-1/POOL)/(N-n2-1)):.0f}"),
        notes=(f"LES CHAINES DU BONUS ET DU BOOST (§222) — le bonus est UN symbole par "
               f"tirage, identifie, uniforme sur 80, correspondant a un mot precis : "
               f"l'observable la plus propre du dossier. Le §197 y mesurait une energie ; "
               f"voici sa CHAINE. {MTOT} statistiques sur {len(RETARDS)} retards. Marge du "
               f"bonus khi2 = {khimarge:.2f} sur {POOL-1} ddl. Archive : bonus max |z| = "
               f"{obs[0]:.3f} au retard {argA[0]} ; maximum reduit {o:.3f} contre un 95e "
               f"centile de {np.percentile(mx, 95):.3f}, p = {pA:.4f}. Predicteur du bonus "
               f"hors echantillon : " + " ; ".join(detD)))
    say("   consigne.")
