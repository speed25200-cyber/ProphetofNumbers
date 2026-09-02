"""h172 — LA NUIT EST-ELLE UN BUDGET ? (RAPPORT §187, théorie THEORIE_ETAT §7.30).

CE QU'ON CHERCHE, ET POURQUOI CE N'EST PAS UN TEST DE GÉNÉRATEUR
================================================================
Tout le dossier jusqu'ici attaque le GÉNÉRATEUR : sa famille, son état, ses relations. Le
§186 vient de fermer la question la plus élémentaire — aucune autocorrélation, à aucun des
6 889 050 couples (numéro, décalage), ni en indice ni en horloge.

Ce fichier change de cible et attaque LE PROTOCOLE. Les loteries qui ont été cassées ne
l'ont presque jamais été par leur RNG ; elles l'ont été parce que l'exploitant contraignait
le résultat pour des raisons comptables. La forme la plus banale de cette contrainte est le
BUDGET : « il sortira exactement tant de multiplicateurs x10 cette nuit ». Un budget est
invisible dans les marges — la fréquence globale reste juste — et il est parfaitement
visible dans la DISPERSION : une source sans mémoire fait varier le compte d'une nuit à
l'autre, un budget ne le fait pas.

Et un budget est EXPLOITABLE : quand la nuit avance et que le quota est consommé, ce qui
reste devient prévisible. C'est pourquoi ce test compte : il ne cherche pas une trace, il
cherche une CONTRAINTE.

LA STATISTIQUE
==============
L'archive a 346 nuits (345 de 204 tirages, 1 de 180). Pour un symbole `s` de fréquence
globale `π_s = M_s/N`, on compte son nombre d'occurrences `X_ks` dans la nuit `k` et on
forme l'INDICE DE DISPERSION

        D_s = somme_k  (X_ks - n_k π_s)² / (n_k π_s (1 - π_s))       .

Sous une source sans mémoire, `D_s` vaut en moyenne le nombre de nuits. Un budget le fait
CHUTER (sous-dispersion) ; une contagion le fait monter. Le signe compte donc autant que la
taille, et c'est le signe NÉGATIF qui est l'objet de la chasse.

LA NULLE EST UNE PERMUTATION, DONC EXACTE SOUS ÉCHANGEABILITÉ
=============================================================
On ne suppose ni binomiale ni χ² asymptotique : on PERMUTE l'ordre des tirages et l'on
recalcule `D_s`. C'est la nulle exacte de l'hypothèse testée — « l'affectation des symboles
aux nuits est échangeable » — et elle absorbe automatiquement la fréquence globale, qui est
conservée par la permutation. Aucune fréquence n'est donc estimée puis réutilisée.

QUATRE FAMILLES, 107 STATISTIQUES
=================================
  A  les 80 numéros                      (π = 1/4)
  B  les valeurs du multiplicateur       (π mesuré, conservé par la permutation)
  C  les 20 rangs du bonus               (π ≈ 1/20)
  D  l'histogramme GLOBAL des rangs du bonus contre l'uniforme — une seule statistique,
     mais la seule qui donne directement un pari : si un rang domine, on parie ce rang et
     l'on bat le 1/20 que le modèle `bonus = triés[⌊u·20⌋]` impose.
"""

import json
import os
import sys
from math import erfc, sqrt

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POOL, DRAWN = 80, 20
EXP_ID = "h172.budget_de_nuit"
FJETON = "/tmp/h172_jeton.json"
REPS = 400


def say(*a):
    print(*a, flush=True)


def seuil_bonferroni(m, alpha=0.05):
    lo, hi = 0.0, 40.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if erfc(mid / sqrt(2)) > alpha / m:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def dispersion(ind, bornes, pi):
    """D_s pour chaque symbole. `ind` : (N,S) 0/1 ; `bornes` : debuts de nuit + [N]."""
    X = np.add.reduceat(ind, bornes[:-1], axis=0).astype(np.float64)      # (K,S)
    nk = np.diff(bornes).astype(np.float64)[:, None]
    att = nk * pi[None, :]
    var = att * (1.0 - pi[None, :])
    return ((X - att) ** 2 / np.maximum(var, 1e-12)).sum(axis=0)


def nulle_permutation(ind, bornes, pi, reps, rng, etiq=""):
    """moyenne et ecart-type de D_s sous permutation de l'ordre des tirages."""
    S = ind.shape[1]
    s1 = np.zeros(S)
    s2 = np.zeros(S)
    for r in range(reps):
        D = dispersion(ind[rng.permutation(len(ind))], bornes, pi)
        s1 += D
        s2 += D * D
        if (r + 1) % max(1, reps // 4) == 0:
            say(f"      nulle {etiq} {r+1}/{reps}")
    mu = s1 / reps
    sd = np.sqrt(np.maximum(s2 / reps - mu * mu, 1e-12))
    return mu, sd


def famille(nom, ind, bornes, rng, reps=REPS):
    pi = ind.mean(axis=0)
    obs = dispersion(ind, bornes, pi)
    mu, sd = nulle_permutation(ind, bornes, pi, reps, rng, etiq=nom)
    z = (obs - mu) / sd
    j = int(np.argmax(np.abs(z)))
    say(f"   {nom} : {len(z)} symboles ; max |z| = {z[j]:+.3f} au symbole {j} "
        f"(D = {obs[j]:.1f}, nulle {mu[j]:.1f} +- {sd[j]:.1f})")
    say(f"      z : min {z.min():+.2f}, max {z.max():+.2f}, moyenne {z.mean():+.3f}, "
        f"ecart-type {z.std():.3f}")
    return z


def selftest():
    """donnees SYNTHETIQUES : la nulle est-elle juste, et le budget se voit-il ?"""
    say("h172 --autotest : donnees synthetiques uniquement, aucune archive lue")
    rng = np.random.default_rng(172)
    K, nk, S = 120, 204, 6
    BOR = np.arange(K + 1) * nk
    pi = np.array([0.5, 0.2, 0.15, 0.08, 0.05, 0.02])

    # (1) la nulle, sur la GEOMETRIE REELLE : 346 nuits de 204 tirages SRS 20/80.
    #     80 symboles, assez pour que la moyenne et l'ecart-type des z soient lisibles.
    K0, n0 = 346, 204
    B0 = np.arange(K0 + 1) * n0
    srs = np.zeros((K0 * n0, POOL), np.int8)
    idx = np.argsort(rng.random((K0 * n0, POOL)), axis=1)[:, :DRAWN]
    np.put_along_axis(srs, idx, np.int8(1), axis=1)
    z = famille("SRS 20/80", srs, B0, rng, reps=200)
    ok1 = abs(z.mean()) < 0.25 and 0.75 < z.std() < 1.30
    say(f"   -> nulle {'JUSTE' if ok1 else 'FAUSSE'} (moyenne {z.mean():+.3f}, "
        f"ecart-type {z.std():.3f} ; attendus 0 et 1)")

    # budget : chaque nuit recoit EXACTEMENT round(nk*pi) exemplaires de chaque symbole
    quota = np.rint(nk * pi).astype(int)
    quota[0] += nk - quota.sum()
    lib = np.concatenate([np.repeat(np.arange(S), quota) for _ in range(K)])
    for k in range(K):
        rng.shuffle(lib[k * nk:(k + 1) * nk])
    ind = (lib[:, None] == np.arange(S)[None, :]).astype(np.int8)
    z = famille("budget   ", ind, BOR, rng, reps=200)
    ok2 = z.min() < -8.0
    say(f"   -> budget {'DETECTE' if ok2 else 'MANQUE'} (z min {z.min():+.2f}, "
        f"attendu tres negatif)")

    # budget PARTIEL : un seul symbole plafonne a son quota, les autres libres
    lib = rng.choice(S, size=K * nk, p=pi)
    for k in range(K):
        bl = lib[k * nk:(k + 1) * nk]
        cible = 5
        idx = np.flatnonzero(bl == cible)
        q = int(round(nk * pi[cible]))
        if len(idx) > q:
            bl[rng.choice(idx, len(idx) - q, replace=False)] = 0
        elif len(idx) < q:
            libres = np.flatnonzero(bl == 0)
            bl[rng.choice(libres, q - len(idx), replace=False)] = cible
    ind = (lib[:, None] == np.arange(S)[None, :]).astype(np.int8)
    z = famille("partiel  ", ind, BOR, rng, reps=200)
    ok3 = z[5] < -6.0
    say(f"   -> plafond sur le symbole 5 {'DETECTE' if ok3 else 'MANQUE'} "
        f"(z_5 = {z[5]:+.2f})")
    return ok1 and ok2 and ok3


if __name__ == "__main__":
    if "--autotest" in sys.argv:
        sys.exit(0 if selftest() else 1)

    import lab

    A = lab.load()
    N = len(A.ids)
    TS = np.asarray(A.ts).astype(np.int64)
    BOR = np.r_[0, np.flatnonzero(np.diff(TS) > 1000) + 1, N]
    K = len(BOR) - 1

    M = np.asarray(A.mask).astype(np.int8)                                # (N,80)
    BOOST = np.asarray(A.boost).astype(np.int64)
    NUMS = np.asarray(A.nums).astype(np.int64)
    BONUS = np.asarray(A.bonus).astype(np.int64)
    RANG = np.argmax(NUMS == BONUS[:, None], axis=1)
    assert bool((NUMS[np.arange(N), RANG] == BONUS).all()), "bonus hors du tirage"
    VB = np.unique(BOOST)
    IB = (BOOST[:, None] == VB[None, :]).astype(np.int8)                  # (N,|VB|)
    IR = (RANG[:, None] == np.arange(DRAWN)[None, :]).astype(np.int8)     # (N,20)

    MTOT = POOL + len(VB) + DRAWN + 1
    ZC = seuil_bonferroni(MTOT)

    HYP = ("L'exploitant ne contraint pas la nuit par un BUDGET. Autrement dit, pour chacun "
           "des 80 numeros, chacune des valeurs du multiplicateur et chacun des 20 rangs du "
           "bonus, le nombre d'occurrences par nuit se disperse exactement comme une "
           "affectation echangeable des tirages aux nuits — ni moins (budget, quota, "
           "plafond) ni plus (contagion). Et l'histogramme global des rangs du bonus est "
           "uniforme sur 20, comme l'impose la lecture bonus = tries[partie entiere de "
           "20u]. C'est une attaque du PROTOCOLE et non du generateur : une loterie cassee "
           "l'a presque toujours ete par une contrainte comptable, invisible dans les "
           "marges et visible dans la dispersion, et une contrainte est EXPLOITABLE parce "
           "qu'un quota consomme rend previsible ce qui reste")
    STAT = (f"D = nombre de statistiques |z| > Zc = {ZC:.2f} (Bonferroni bilateral a 5 % sur "
            f"{MTOT}), et le max signe. z = (D_s - moyenne nulle) / ecart-type nul, ou "
            "D_s = somme_k (X_ks - n_k pi_s)^2 / (n_k pi_s (1-pi_s)) sur les 346 nuits. Le "
            "SIGNE compte : z tres negatif = sous-dispersion = budget. Famille D : khi2 "
            "d'uniformite de l'histogramme des rangs du bonus, 19 ddl, rendu lui aussi en z")
    NUL = (f"Permutation : {REPS} permutations aleatoires de l'ordre des 70 560 tirages, "
           "moyenne et ecart-type de D_s par symbole. C'est la nulle EXACTE de "
           "l'echangeabilite et elle conserve les frequences globales, donc aucune "
           "frequence n'est estimee puis reutilisee. Famille D : multinomiale uniforme "
           "exacte simulee de meme effectif")
    VER = ("conforme si D = 0 ; BUDGET si une statistique passe sous -Zc (sous-dispersion) ; "
           "ECART sinon")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h172 : {N} tirages, {K} nuits ({np.diff(BOR).min()} a {np.diff(BOR).max()} "
        f"tirages) ; {len(VB)} valeurs de multiplicateur")
    say(f"   seuil de Bonferroni sur {MTOT} statistiques : |z| > {ZC:.3f}")

    rng = np.random.default_rng(20260902)
    zA = famille("A numeros   ", M, BOR, rng)
    zB = famille("B boost     ", IB, BOR, rng)
    zC = famille("C rang bonus", IR, BOR, rng)

    # famille D : uniformite globale du rang du bonus
    obs = np.bincount(RANG, minlength=DRAWN).astype(np.float64)
    att = N / DRAWN
    khi = float(((obs - att) ** 2 / att).sum())
    s1 = s2 = 0.0
    for _ in range(4000):
        c = rng.multinomial(N, np.full(DRAWN, 1.0 / DRAWN)).astype(np.float64)
        v = ((c - att) ** 2 / att).sum()
        s1 += v
        s2 += v * v
    mu = s1 / 4000
    sd = sqrt(max(s2 / 4000 - mu * mu, 1e-12))
    zD = (khi - mu) / sd
    say(f"   D rang bonus (uniformite globale) : khi2 = {khi:.2f}, nulle {mu:.2f} +- "
        f"{sd:.2f}  ->  z = {zD:+.3f}")
    say(f"      rang le plus frequent : {int(np.argmax(obs))} avec {int(obs.max())} "
        f"({100*obs.max()/N:.3f} %, uniforme = 5,000 %)")

    tous = np.r_[zA, zB, zC, [zD]]
    D = int((np.abs(tous) > ZC).sum())
    sous = int((tous < -ZC).sum())
    j = int(np.argmax(np.abs(tous)))
    zmax = float(tous[j])
    p = float(min(1.0, erfc(abs(zmax) / sqrt(2)) * MTOT))
    say(f"\n   max |z| = {zmax:+.3f}   seuil {ZC:.3f}   p (Bonferroni sur {MTOT}) = {p:.4f}")
    verdict = "BUDGET" if sous else ("ECART" if D else "conforme")
    say(f"   D = {D} ({sous} en sous-dispersion)  ->  {verdict}")
    TOK["m_extra"] = MTOT - 1
    lab.record(
        TOK, abs(zmax), p=p, verdict=verdict,
        power_at=("346 nuits de 204 tirages. Un budget PARFAIT sur un symbole de frequence "
                  "pi rendrait D_s = 0, soit z = -346/26 = -13,3 : hors de portee du "
                  "hasard. Un budget PARTIEL qui ne retirerait que 10 % de la variance "
                  "donnerait deja z = -2,4, et 20 % z = -4,8, au-dela du seuil de "
                  f"{ZC:.2f}. La famille D voit un rang excedentaire de 0,3 point de "
                  "pourcentage"),
        notes=(f"BUDGET DE NUIT (§187) — attaque du PROTOCOLE et non du generateur. "
               f"{MTOT} statistiques de dispersion sur {K} nuits, nulle par permutation "
               f"({REPS} tirages). max |z| = {zmax:+.3f}, D = {D}, sous-dispersions = "
               f"{sous}. Familles : A numeros max |z| {np.abs(zA).max():.2f} (min "
               f"{zA.min():+.2f}), B boost {np.abs(zB).max():.2f} (min {zB.min():+.2f}), "
               f"C rang bonus {np.abs(zC).max():.2f} (min {zC.min():+.2f}), D uniformite "
               f"des rangs z = {zD:+.3f}."))
    say("   consigne.")
