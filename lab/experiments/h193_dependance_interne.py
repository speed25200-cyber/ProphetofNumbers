"""h193 — LA DÉPENDANCE INTERNE : deux numéros sortent-ils ENSEMBLE plus souvent qu'ils
ne devraient ? (RAPPORT §213).

LA BRÈCHE QUE LE §210 A LAISSÉE OUVERTE DANS SON PROPRE ARGUMENT
================================================================
Le §210 conclut, et c'est juste :

> « Une grille ne peut pas battre le hasard si aucun de ses membres n'est biaisé. »

Le nombre **moyen** de numéros gagnants d'une grille fixe est la somme des taux de sortie
de ses membres — rien d'autre. Les marges étant conformes (`max |z| = 2,72` sur quatre-
vingts numéros), aucune grille ne peut battre la moyenne. C'est démontré.

Mais **on n'est pas payé à la moyenne.** Un keno paie sur `4/5`, sur `5/5` — jamais sur
« 1,25 en espérance ». Le gain est une fonction **convexe** du nombre de justes, et

    P(les cinq sortent) ne dépend PAS des marges. Elle dépend de la loi JOINTE.

Deux grilles aux marges identiques, l'une aux membres indépendants, l'autre aux membres
positivement liés, ont **la même espérance de justes et des taux de jackpot différents**.
La seconde est rentable là où la première ne l'est pas.

Or aucune section du dossier n'a jamais mesuré la loi jointe **à l'intérieur d'un
tirage**. Tout ce qui a été fait est soit par numéro à travers le temps (marges §210 A,
autocorrélation §194, budget de nuit §195), soit agrégé entre tirages (recouvrements
§209). La question « les numéros `17` et `43` sortent-ils ensemble trop souvent ? » n'a
jamais été posée.

C'est exactement la brèche que l'argument du §210 laisse, et ce fichier la ferme.

QUATRE FAMILLES
===============
  **A  LES PAIRES.** Les `C(80,2) = 3 160` paires, comptées sur les `70 560` tirages.
     Nulle **exacte** : sous SRS, `P(i et j) = 20·19/(80·79)` exactement, et les tirages
     étant indépendants le compte est binomial.

  **B  LES TRIPLETS.** Les `C(80,3) = 82 160` triplets. `P = 20·19·18/(80·79·78)`.

  **C  L'ENSEMBLE.** La somme des `z²` sur les paires, puis sur les triplets — une
     dépendance diffuse, répartie sur des milliers de couples et invisible sur chacun,
     se voit là et nulle part ailleurs.

  **D  LA GRILLE CONVEXE, HORS ÉCHANTILLON.** La seule qui parle d'argent. On cherche sur
     la **première moitié** la grille de `k` numéros au plus fort taux de `k/k` — la plus
     positivement liée — et on la joue sur la **seconde**, qu'elle n'a jamais vue. Pour
     `k = 2, 3, 4` la recherche est **exhaustive** ; pour `k = 5` elle étend les meilleures
     grilles de quatre. Puis le découpage à l'envers, ce qui fait huit mesures.

     Ce n'est pas la même chose que le §210 C, qui choisissait les numéros de plus forte
     **marge** et mesurait une **moyenne**. Ici on choisit sur la **liaison** et l'on
     mesure un **jackpot**.

LA LOI DU MAXIMUM EST EMPIRIQUE, PAS BONFERRONI
===============================================
Les comptes de paires ne sont pas indépendants : deux paires qui partagent un numéro sont
liées, et une paire est liée à la marge de ses membres. Un Bonferroni gaussien serait faux
dans les deux sens (§7.32). Le maximum est donc calibré sur des répliques SRS, chacune
laissée **hors de sa propre normalisation**.
"""

import json
import os
import sys
from itertools import combinations
from math import erfc, sqrt

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POOL, DRAWN = 80, 20
EXP_ID = "h193.dependance_interne"
FJETON = "/tmp/h193_jeton.json"
REPS = 120
KS = (2, 3, 4, 5)
NEXT4 = 2000                      # meilleures grilles de quatre etendues vers cinq


def say(*a):
    print(*a, flush=True)


def p_exact(k):
    """P(les k numeros d'une grille fixe sortent tous) sous SRS, EXACTE."""
    v = 1.0
    for j in range(k):
        v *= (DRAWN - j) / (POOL - j)
    return v


IA, IB, IC = np.array(list(combinations(range(DRAWN), 3))).T


def comptes(M, NU):
    """comptes de paires (80,80) et de triplets (80^3,) — memes conventions partout."""
    F = M.astype(np.float32)
    P = (F.T @ F).astype(np.float64)
    T = np.zeros(POOL ** 3, np.int64)
    for d in range(0, len(NU), 4096):
        Q = NU[d:d + 4096].astype(np.int64)
        T += np.bincount((Q[:, IA] * POOL * POOL + Q[:, IB] * POOL + Q[:, IC]).ravel(),
                         minlength=POOL ** 3)
    return P, T


def stats(P, T, n, iu, it):
    """max |z| des paires, max |z| des triplets, et les deux sommes de z²."""
    p2, p3 = p_exact(2), p_exact(3)
    z2 = (P[iu] - n * p2) / sqrt(n * p2 * (1 - p2))
    z3 = (T[it] - n * p3) / sqrt(n * p3 * (1 - p3))
    return (float(np.abs(z2).max()), float(np.abs(z3).max()),
            float((z2 * z2).sum()), float((z3 * z3).sum()))


def maxloo(V, obs):
    """loi du maximum EMPIRIQUE : chaque replique hors de sa propre normalisation (§7.32).

    V est (REPS, S) — S statistiques par replique. Renvoie le maximum observe reduit et
    la p-valeur `(1 + #{m_r >= obs})/(1 + R)`.
    """
    R = len(V)
    s1, s2 = V.sum(axis=0), (V * V).sum(axis=0)
    mu, sd = V.mean(axis=0), V.std(axis=0)
    o = float(np.abs((obs - mu) / np.maximum(sd, 1e-12)).max())
    mx = np.empty(R)
    for r in range(R):
        m_ = (s1 - V[r]) / (R - 1)
        v_ = np.maximum((s2 - V[r] * V[r]) / (R - 1) - m_ * m_, 1e-12)
        mx[r] = float(np.abs((V[r] - m_) / np.sqrt(v_)).max())
    return o, float((1 + int((mx >= o).sum())) / (1 + R)), mx


def grille_convexe(M, deb1, fin1, deb2, fin2):
    """choix sur [deb1,fin1), mesure sur [deb2,fin2). Renvoie {k: (grille, obs, n, z)}."""
    A = M[deb1:fin1]
    B = M[deb2:fin2]
    nB = len(B)
    NUa = np.nonzero(A)[1].reshape(len(A), DRAWN).astype(np.int64)
    out = {}

    # --- k = 2 : exhaustif par produit matriciel
    F = A.astype(np.float32)
    C2 = (F.T @ F).astype(np.int64)
    np.fill_diagonal(C2, -1)
    i2 = int(np.argmax(C2))
    best = {2: (np.array([i2 // POOL, i2 % POOL]), int(C2.flat[i2]))}

    # --- k = 3 et 4 : exhaustif par comptage direct des sous-ensembles de chaque tirage
    for k in (3, 4):
        idx = np.array(list(combinations(range(DRAWN), k))).T
        acc = np.zeros(POOL ** k, np.int64)
        poids = POOL ** np.arange(k - 1, -1, -1)
        for d in range(0, len(NUa), 2048):
            Q = NUa[d:d + 2048]
            plat = np.zeros((len(Q), idx.shape[1]), np.int64)
            for j in range(k):
                plat += Q[:, idx[j]] * poids[j]
            acc += np.bincount(plat.ravel(), minlength=POOL ** k)
        j = int(np.argmax(acc))
        g = []
        for w in poids:
            g.append(j // w)
            j %= w
        best[k] = (np.array(g), int(acc.max()))
        if k == 4:
            part = np.argpartition(-acc, NEXT4)[:NEXT4]
            ordre4 = part[np.argsort(-acc[part])]
        del acc

    # --- k = 5 : extension des NEXT4 meilleures grilles de quatre, choix toujours sur A
    meilleur5, c5 = None, -1
    for j in ordre4:
        g = []
        jj = int(j)
        for w in POOL ** np.arange(3, -1, -1):
            g.append(jj // w)
            jj %= w
        g = np.array(g)
        if len(np.unique(g)) < 4:
            continue
        sel = A[:, g].all(axis=1)
        if not sel.any():
            continue
        c = A[sel].sum(axis=0)
        c[g] = -1
        x = int(np.argmax(c))
        if int(c[x]) > c5:
            c5, meilleur5 = int(c[x]), np.sort(np.r_[g, x])
    best[5] = (meilleur5, c5)

    for k in KS:
        g = best[k][0]
        pk = p_exact(k)
        obs = int(B[:, g].all(axis=1).sum())
        z = (obs - nB * pk) / sqrt(nB * pk * (1 - pk))
        out[k] = (np.sort(g + 1), obs, nB, float(z), best[k][1], len(A))
    return out


if __name__ == "__main__":
    import lab

    A = lab.load()
    M = np.asarray(A.mask)
    N = len(M)
    NU = np.nonzero(M)[1].reshape(N, DRAWN)
    n2 = N // 2

    iu = np.triu_indices(POOL, 1)
    it = np.array([a * POOL * POOL + b * POOL + c
                   for a, b, c in combinations(range(POOL), 3)], np.int64)
    NP, NT = len(iu[0]), len(it)
    MTOT = NP + NT + 2 + 2 * len(KS)

    HYP = ("Les numeros d'un MEME tirage sont mutuellement independants au sens de la loi "
           "SRS. Le §210 a demontre qu'une grille ne peut pas battre la MOYENNE, le nombre "
           "moyen de justes n'etant que la somme des taux de sortie de ses membres, tous "
           "conformes. Mais on n'est pas paye a la moyenne : un keno paie sur 4/5 et sur "
           "5/5, le gain est une fonction CONVEXE du nombre de justes, et P(les cinq "
           "sortent) ne depend pas des marges mais de la loi JOINTE. Deux grilles aux "
           "marges identiques, l'une aux membres independants et l'autre aux membres "
           "positivement lies, ont la meme esperance de justes et des taux de jackpot "
           "DIFFERENTS. Or aucune section du dossier n'a mesure la loi jointe A "
           "L'INTERIEUR d'un tirage : tout est soit par numero a travers le temps, soit "
           f"agrege entre tirages. Quatre familles : (A) les {NP} paires ; (B) les {NT} "
           "triplets ; (C) les deux sommes de z², qui voient une dependance diffuse "
           "invisible sur chaque couple ; (D) la GRILLE CONVEXE hors echantillon, la seule "
           "qui parle d'argent — on cherche sur une moitie la grille de k numeros au plus "
           "fort taux de k/k, donc la plus positivement liee, et on la joue sur l'autre, "
           "pour k = 2, 3, 4, 5 et dans les deux sens")
    STAT = (f"max |z| reduit par la loi EMPIRIQUE du maximum sur {REPS} repliques SRS, "
            f"chacune laissee hors de sa propre normalisation ; separement pour les {NP} "
            f"paires, les {NT} triplets et les deux sommes de z². Et, famille D, le z "
            "binomial exact du taux de k/k de la grille choisie sur l'autre moitie")
    NUL = ("EXACTE pour chaque statistique : sous SRS P(i et j) = 20.19/(80.79) et "
           "P(i,j,k) = 20.19.18/(80.79.78) exactement, les tirages etant independants les "
           "comptes sont binomiaux, et P(les k sortent) = produit de (20-j)/(80-j). Les "
           "comptes de paires n'etant PAS independants entre eux — deux paires qui "
           "partagent un numero sont liees — la loi du MAXIMUM est calibree sur repliques "
           "SRS et non par Bonferroni gaussien, qui serait faux dans les deux sens (§7.32)")
    VER = ("conforme si aucun maximum ne depasse le 95e centile de sa loi empirique ET si "
           "aucune des huit grilles de la famille D ne depasse le seuil de Bonferroni sur "
           "huit ; DEPENDANCE INTERNE si A, B ou C depasse ; GRILLE CONVEXE si D depasse")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h193 : {N} tirages ; {NP} paires, {NT} triplets ; {MTOT} statistiques")
    for k in KS:
        say(f"   P({k}/{k}) exacte = {p_exact(k):.8f}   attendu sur {N - n2} tirages : "
            f"{(N - n2) * p_exact(k):8.2f} +/- {sqrt((N-n2)*p_exact(k)*(1-p_exact(k))):.2f}")

    Pa, Ta = comptes(M, NU)
    obs = np.array(stats(Pa, Ta, N, iu, it))
    say(f"\nARCHIVE   max|z| paires {obs[0]:.3f}   max|z| triplets {obs[1]:.3f}   "
        f"somme z² paires {obs[2]:.1f}   triplets {obs[3]:.1f}")
    say(f"   (sommes attendues : {NP} et {NT} si les z etaient unitaires)")

    V = np.empty((REPS, 4))
    rng = np.random.default_rng(0x193)
    for r in range(REPS):
        S = lab.srs(N, rng)
        NUs = np.nonzero(S)[1].reshape(N, DRAWN)
        Ps, Ts = comptes(S, NUs)
        V[r] = stats(Ps, Ts, N, iu, it)
        if (r + 1) % 20 == 0:
            say(f"   ... {r+1}/{REPS} repliques")

    o, pmax, mx = maxloo(V, obs)
    say(f"\n   {'statistique':>22} | {'archive':>10} | {'repliques':>18} | {'z reduit':>9}")
    for j, nom in enumerate(("max|z| paires", "max|z| triplets",
                             "somme z² paires", "somme z² triplets")):
        say(f"   {nom:>22} | {obs[j]:10.3f} | {V[:,j].mean():9.3f} +/-{V[:,j].std():6.3f} "
            f"| {(obs[j]-V[:,j].mean())/max(V[:,j].std(),1e-12):+9.3f}")
    say(f"   maximum reduit observe {o:.3f} ; median des repliques {np.median(mx):.3f} ; "
        f"95e centile {np.percentile(mx, 95):.3f}")
    say(f"   p (loi empirique du maximum, {REPS} repliques) = {pmax:.4f}")

    say(f"\nD  LA GRILLE CONVEXE HORS ECHANTILLON")
    say(f"   {'sens':>10} {'k':>2} | {'grille':>26} | {'choix':>13} | "
        f"{'mesure k/k':>18} | {'z':>7}")
    zD, detail = [], []
    for nom, (a1, b1, a2, b2) in (("H1 -> H2", (0, n2, n2, N)), ("H2 -> H1", (n2, N, 0, n2))):
        res = grille_convexe(M, a1, b1, a2, b2)
        for k in KS:
            g, ob, nb, z, c1, na = res[k]
            zD.append(z)
            detail.append(f"{nom} k={k} {list(g)} {ob}/{nb} z={z:+.2f}")
            say(f"   {nom:>10} {k:2d} | {str(list(g)):>26} | {c1:6d}/{na:6d} | "
                f"{ob:6d}/{nb:6d} = {100*ob/nb:6.3f} % | {z:+7.2f}")

    lo, hi = 0.0, 40.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if erfc(mid / sqrt(2)) > 0.05 / len(zD):
            lo = mid
        else:
            hi = mid
    ZD = 0.5 * (lo + hi)
    zDmax = max(zD, key=abs)
    pD = float(min(1.0, erfc(abs(zDmax) / sqrt(2)) * len(zD)))
    say(f"\n   max |z| grilles = {zDmax:+.3f}   seuil de Bonferroni sur {len(zD)} = {ZD:.3f}")

    depend = pmax <= 0.05
    convexe = any(z > ZD for z in zD)
    verdict = ("GRILLE CONVEXE" if convexe else
               ("DEPENDANCE INTERNE" if depend else "conforme"))
    p = float(min(pmax, pD))
    say(f"\n   p retenue = {p:.4f}   ->   {verdict}")
    TOK["m_extra"] = MTOT - 1
    lab.record(
        TOK, float(max(o, abs(zDmax))), p=p, verdict=verdict,
        power_at=(f"famille A : l'ecart-type d'un compte de paire vaut "
                  f"{sqrt(N*p_exact(2)*(1-p_exact(2))):.1f} sur {N*p_exact(2):.0f} "
                  f"attendus, donc une paire liee a 1 % en valeur relative sort a z = "
                  f"{0.01*N*p_exact(2)/sqrt(N*p_exact(2)*(1-p_exact(2))):.1f} et le test "
                  f"voit une liaison relative de "
                  f"{100*4.5*sqrt(N*p_exact(2)*(1-p_exact(2)))/(N*p_exact(2)):.1f} %. "
                  f"Famille D, k = 5 : {(N-n2)*p_exact(5):.1f} jackpots attendus sur "
                  f"{N-n2} tirages d'ecart-type {sqrt((N-n2)*p_exact(5)*(1-p_exact(5))):.1f}"
                  f", donc le test ne voit qu'un DOUBLEMENT du taux de jackpot — il tranche "
                  "sur une dependance forte, non sur une dependance fine ; c'est la famille "
                  "A, bien plus puissante, qui borne celle-ci"),
        notes=(f"LA DEPENDANCE INTERNE (§213) — la breche que le §210 laisse dans son "
               f"propre argument : il demontre qu'aucune grille ne bat la MOYENNE, les "
               f"marges etant conformes, mais on n'est pas paye a la moyenne et P(les cinq "
               f"sortent) ne depend pas des marges. {NP} paires, {NT} triplets, deux sommes "
               f"de z², loi du maximum EMPIRIQUE sur {REPS} repliques. Archive : max|z| "
               f"paires {obs[0]:.3f}, triplets {obs[1]:.3f} ; maximum reduit {o:.3f} contre "
               f"un 95e centile de {np.percentile(mx, 95):.3f}, p = {pmax:.4f}. Grilles "
               f"convexes hors echantillon : " + " ; ".join(detail)))
    say("   consigne.")
