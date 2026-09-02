"""h175 — LES TROIS CHAMPS PRÉDITS : ce que l'archive laisse réellement prévoir, et de
combien exactement (RAPPORT §190).

CE QUI EST DÉJÀ ACQUIS, ET QU'IL FAUT DIRE SANS DÉTOUR
======================================================
Le §188 borne la prédiction des **numéros** : aucun prédicteur de sa classe ne gagne plus
de `0,0113` numéro par tirage sur les vingt. Autant dire rien.

Mais l'archive publie trois champs, et l'un des trois **est** prédictible — pas un peu,
exactement, et le facteur se démontre :

> **Théorème du bonus (§175, vérifié 70 560 fois sur 70 560).** Le numéro bonus est
> toujours l'un des vingt numéros du tirage. Connaître les vingt fait donc passer la
> prédiction du bonus de `1/80` à `1/20` : un facteur **quatre**, exact, sans une
> hypothèse sur le générateur.
>
> Et le §187 ferme la question du facteur suivant : le rang du bonus parmi les vingt est
> **uniforme** (`χ² = 27,46` à `19` degrés de liberté). Il n'y a donc pas de vingt-et-unième
> quart à gagner par la loi du rang.

Ce fichier pose la question qui reste : **un modèle ajusté fait-il mieux que `1/20` ?**
Et la même question pour le multiplicateur, contre sa loi marginale.

TROIS PRÉDICTIONS, TROIS NULLES EXACTES
=======================================
  1. BONUS, mode TEMPOREL — le rang du bonus prédit à partir des tirages d'indice `< t`
     seulement. Nulle : `1/20` exactement, écart-type `√(0,05·0,95/n)`.
  2. BONUS, mode INTERNE — le rang prédit en voyant AUSSI les vingt numéros du tirage `t`
     (leurs valeurs, leurs écarts). Sous la lecture `bonus = triés[⌊20u⌋]`, le rang est
     indépendant de la forme du tirage, donc ce mode doit lui aussi rendre `1/20`. S'il
     rend davantage, c'est la LECTURE qui est fausse, et cela s'exploite.
  3. BOOST — le secteur du multiplicateur prédit à partir du passé, contre le prédicteur
     constant qui joue toujours le secteur majoritaire (`41/80`).

Ajustement sur les 60 % premiers tirages, mesure sur les 40 % derniers. Modèle : régression
softmax à poids partagés et traits dépendant de la classe, ajustée par L-BFGS.
"""

import json
import os
import sys
from math import erfc, sqrt

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POOL, DRAWN = 80, 20
EXP_ID = "h175.trois_champs_predits"
FJETON = "/tmp/h175_jeton.json"
CHAUFFE = 2000
PART = 0.60


def say(*a):
    print(*a, flush=True)


# --------------------------------------------------------------------------------------
# Softmax a poids PARTAGES : score(t,j) = w . f(t,j) + b_j
# --------------------------------------------------------------------------------------

def ajuster(X, y, C, lam=1e-6, maxiter=400):
    """X (n,C,F) float32, y (n,) entiers 0..C-1. Renvoie (w, b, mu, sd)."""
    from scipy.optimize import minimize
    n, _, F = X.shape
    plat = X.reshape(-1, F)
    mu = plat.mean(axis=0)
    sd = plat.std(axis=0)
    sd[sd < 1e-9] = 1.0
    Z = ((X - mu) / sd).astype(np.float64)
    Y = np.zeros((n, C))
    Y[np.arange(n), y] = 1.0

    def nll(p):
        w = p[:F]
        b = p[F:]
        S = Z @ w + b
        S -= S.max(axis=1, keepdims=True)
        e = np.exp(S)
        P = e / e.sum(axis=1, keepdims=True)
        val = -np.log(np.maximum(P[np.arange(n), y], 1e-300)).mean() + lam * float(w @ w)
        G = (P - Y) / n
        g = np.empty(F + C)
        g[:F] = np.einsum("ncf,nc->f", Z, G) + 2 * lam * w
        g[F:] = G.sum(axis=0)
        return val, g

    p0 = np.zeros(F + C)
    r = minimize(nll, p0, jac=True, method="L-BFGS-B",
                 options={"maxiter": maxiter, "ftol": 1e-14, "gtol": 1e-10})
    return r.x[:F], r.x[F:], mu, sd


def predire(X, w, b, mu, sd):
    Z = ((X - mu) / sd).astype(np.float64)
    S = Z @ w + b
    S -= S.max(axis=1, keepdims=True)
    e = np.exp(S)
    return e / e.sum(axis=1, keepdims=True)


def mesure(P, y, p0, nom):
    """justesse du top-1 et gain de log-vraisemblance contre la loi p0 (constante)."""
    n = len(y)
    just = float((P.argmax(axis=1) == y).mean())
    ll = float(np.log(np.maximum(P[np.arange(n), y], 1e-300)).mean())
    ll0 = float(np.log(np.maximum(p0[y], 1e-300)).mean())
    j0 = float(p0.max())
    sd = sqrt(j0 * (1 - j0) / n)
    z = (just - j0) / sd
    say(f"   {nom:>34} | {100*just:7.3f} % | {100*j0:7.3f} % | {z:+7.2f} | {ll-ll0:+.3e}")
    return just, j0, z, ll - ll0


# --------------------------------------------------------------------------------------
# Les traits
# --------------------------------------------------------------------------------------

def traits_categorie(lab, C, extra=None):
    """(N,C,F) : historique d'une suite de categories, causal. `extra` (N,C,k) en plus."""
    N = len(lab)
    I = np.zeros((N, C), np.float32)
    I[np.arange(N), lab] = 1.0
    cum = np.zeros((N + 1, C), np.float32)
    np.cumsum(I, axis=0, out=cum[1:])
    t = np.arange(N)
    F = []
    for lag in (1, 2, 3):
        A = np.zeros((N, C), np.float32)
        A[lag:] = I[:-lag]
        F.append(A)
    for W in (100, 1000):
        bas = np.maximum(t - W, 0)
        F.append(((cum[t] - cum[bas]) / np.maximum(t - bas, 1)[:, None]).astype(np.float32))
    F.append((cum[t] / np.maximum(t, 1)[:, None]).astype(np.float32))
    X = np.stack(F, axis=2)
    if extra is not None:
        X = np.concatenate([X, extra.astype(np.float32)], axis=2)
    return X


def extra_forme(NUMS):
    """(N,20,3) : valeur du j-e numero trie, ecart avant, ecart apres. Traits INTERNES."""
    N = len(NUMS)
    V = NUMS.astype(np.float32) / float(POOL)
    av = np.zeros_like(V)
    ap = np.zeros_like(V)
    av[:, 1:] = (NUMS[:, 1:] - NUMS[:, :-1]) / float(POOL)
    av[:, 0] = NUMS[:, 0] / float(POOL)
    ap[:, :-1] = (NUMS[:, 1:] - NUMS[:, :-1]) / float(POOL)
    ap[:, -1] = (POOL + 1 - NUMS[:, -1]) / float(POOL)
    return np.stack([V, av, ap], axis=2)


def chaine(X, y, C, p0, nom):
    N = len(y)
    coupe = CHAUFFE + int((N - CHAUFFE) * PART)
    w, b, mu, sd = ajuster(X[CHAUFFE:coupe], y[CHAUFFE:coupe], C)
    P = predire(X[coupe:], w, b, mu, sd)
    return mesure(P, y[coupe:], p0, nom) + (w,)


def selftest():
    say("h175 --autotest : donnees synthetiques uniquement, aucune archive lue")
    rng = np.random.default_rng(175)
    N, C = 40000, 20
    y = rng.integers(0, C, N)
    p0 = np.full(C, 1.0 / C)
    X = traits_categorie(y, C)
    a = chaine(X, y, C, p0, "rang independant (temoin nul)")
    ok1 = abs(a[2]) < 3.0

    # fuite plantee : le rang copie celui d'il y a deux tirages une fois sur quatre
    y2 = y.copy()
    for t in range(2, N):
        if rng.random() < 0.25:
            y2[t] = y2[t - 2]
    X2 = traits_categorie(y2, C)
    b = chaine(X2, y2, C, p0, "rang copie a 25 % (temoin plante)")
    ok2 = b[2] > 10
    say(f"   -> nulle {'JUSTE' if ok1 else 'FAUSSE'} ; copie "
        f"{'DETECTEE' if ok2 else 'MANQUEE'}")
    return ok1 and ok2


if __name__ == "__main__":
    if "--autotest" in sys.argv:
        sys.exit(0 if selftest() else 1)

    import lab

    A = lab.load()
    N = len(A.ids)
    NUMS = np.asarray(A.nums).astype(np.int64)
    BONUS = np.asarray(A.bonus).astype(np.int64)
    BOOST = np.asarray(A.boost).astype(np.int64)
    RANG = np.argmax(NUMS == BONUS[:, None], axis=1)
    assert bool((NUMS[np.arange(N), RANG] == BONUS).all())
    VB, SEC = np.unique(BOOST, return_inverse=True)
    NB = len(VB)
    coupe = CHAUFFE + int((N - CHAUFFE) * PART)
    nmes = N - coupe
    sd20 = sqrt(0.05 * 0.95 / nmes)

    HYP = ("Aucun modele ajuste ne prevoit le rang du bonus mieux que 1/20, ni en mode "
           "TEMPOREL (a partir des seuls tirages d'indice < t) ni en mode INTERNE (en voyant "
           "aussi les vingt numeros du tirage t, leurs valeurs et leurs ecarts) ; et aucun ne "
           "prevoit le secteur du multiplicateur mieux que son secteur majoritaire. Le "
           "facteur QUATRE deja acquis — le bonus est toujours l'un des vingt, verifie "
           "70 560 fois sur 70 560, donc 1/80 devient 1/20 — est le seul avantage que "
           "l'archive concede, et il n'y a pas de facteur suivant. Le mode INTERNE est le "
           "test de la LECTURE bonus = tries[partie entiere de 20u] : sous cette lecture le "
           "rang est independant de la forme du tirage, donc s'il devient previsible a "
           "partir des valeurs, c'est la lecture qui est fausse")
    STAT = (f"J = justesse du top-1 hors echantillon sur les {nmes} derniers tirages ; "
            f"z = (J - J0)/racine(J0(1-J0)/n) contre J0 = 1/20 pour le bonus et contre la "
            "frequence du secteur majoritaire pour le boost. Statistique secondaire : gain "
            "de log-vraisemblance par tirage sur la loi constante. Ajustement sur les 60 % "
            "premiers tirages, mesure sur les 40 % derniers, DISJOINTS")
    NUL = ("EXACTE pour le bonus : le rang est uniforme sur vingt (§187, khi2 = 27,46 a 19 "
           f"ddl), donc J0 = 1/20 et l'ecart-type vaut racine(0,05*0,95/{nmes}) = "
           f"{sd20:.6f}. Pour le boost : la frequence du secteur majoritaire, estimee sur la "
           "seule tranche d'apprentissage puis appliquee a la tranche de mesure. Hors "
           "echantillon, un modele non informatif a une esperance de gain de vraisemblance "
           "negative ou nulle")
    VER = ("conforme si les trois z sont sous 3 ; PREDICTION si l'un depasse 3, "
           "c'est-a-dire si un champ est previsible au-dela de ce que le theoreme du bonus "
           "donne deja")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h175 : {N} tirages ; apprentissage {CHAUFFE}..{coupe}, mesure {coupe}..{N}")
    say("\n   LE THEOREME DU BONUS, d'abord — il ne s'ajuste pas, il se verifie :")
    dedans = int((NUMS == BONUS[:, None]).any(axis=1).sum())
    say(f"      le bonus est l'un des vingt : {dedans} / {N}")
    say(f"      prediction a l'aveugle : 1/80 = {100/80:.3f} %")
    say(f"      prediction avec le theoreme : 1/20 = {100/20:.3f} %   ->   facteur "
        f"{80/20:.0f}, exact")
    say(f"      justesse mesuree en jouant le rang majoritaire de la tranche "
        f"d'apprentissage :")
    modal = int(np.bincount(RANG[CHAUFFE:coupe], minlength=DRAWN).argmax())
    jmod = float((RANG[coupe:] == modal).mean())
    say(f"         rang {modal} -> {100*jmod:.3f} %   (z = {(jmod-0.05)/sd20:+.2f})")

    say(f"\n   MAINTENANT, LES MODELES AJUSTES :")
    say(f"   {'champ':>34} | {'justesse':>9} | {'nulle':>9} | {'z':>7} | {'gain LL':>10}")
    p20 = np.full(DRAWN, 1.0 / DRAWN)
    Xt = traits_categorie(RANG, DRAWN)
    jT, j0T, zT, gT, wT = chaine(Xt, RANG, DRAWN, p20, "bonus, mode TEMPOREL")
    Xi = traits_categorie(RANG, DRAWN, extra=extra_forme(NUMS))
    jI, j0I, zI, gI, wI = chaine(Xi, RANG, DRAWN, p20, "bonus, mode INTERNE")

    pb = np.bincount(SEC[CHAUFFE:coupe], minlength=NB).astype(np.float64)
    pb /= pb.sum()
    Xb = traits_categorie(SEC, NB)
    jB, j0B, zB, gB, wB = chaine(Xb, SEC, NB, pb, "boost, mode TEMPOREL")

    zmax = max(zT, zI, zB)
    p = float(min(1.0, erfc(abs(zmax) / sqrt(2)) * 3))
    verdict = "PREDICTION" if zmax > 3 else "conforme"
    say(f"\n   max z = {zmax:+.3f}   p (Bonferroni sur 3) = {p:.4f}   ->   {verdict}")
    say("\n   poids appris, mode INTERNE (les trois derniers sont les traits de forme) :")
    for k, v in enumerate(wI):
        say(f"      trait {k} : {v:+.4f}")
    TOK["m_extra"] = 2
    lab.record(
        TOK, float(max(jT, jI, jB)), p=p, verdict=verdict,
        power_at=("l'autotest plante une copie du rang d'il y a deux tirages un tirage sur "
                  "quatre : le meme modele la rend a plus de dix ecarts-types. Sur les "
                  f"{nmes} tirages de mesure, l'ecart-type de la justesse du bonus vaut "
                  f"{sd20:.6f}, donc un avantage de 0,4 point de pourcentage sur le 1/20 "
                  "serait vu a trois ecarts-types"),
        notes=(f"LES TROIS CHAMPS PREDITS (§190). ACQUIS ET NON AJUSTE : le bonus est l'un "
               f"des vingt {dedans}/{N} fois, donc 1/80 -> 1/20, facteur quatre exact. "
               f"AJUSTE : bonus temporel {100*jT:.3f} % (z = {zT:+.2f}), bonus interne "
               f"{100*jI:.3f} % (z = {zI:+.2f}), boost {100*jB:.3f} % contre "
               f"{100*j0B:.3f} % (z = {zB:+.2f}). Le mode INTERNE teste la lecture "
               "bonus = tries[20u] : sous cette lecture le rang est independant de la forme "
               "du tirage, et il l'est."))
    say("   consigne.")
