"""h173 — LE PRÉDICTEUR APPRIS : on cesse de deviner la forme du défaut, on la fait
apprendre (RAPPORT §188, théorie THEORIE_ETAT §7.31).

CE QUI MANQUE AU DOSSIER
========================
Tous les tests menés jusqu'ici — et il y en a bien plus de six cents — ont la même
faiblesse : **chacun suppose la forme du défaut**. Le crible de classes suppose un Fibonacci
retardé ; les détecteurs d'énergie supposent une relation à deux ou trois termes ; le §186
suppose une autocorrélation ; le §187 suppose un quota. Un défaut d'une forme non prévue
passe entre tous.

La parade est de ne plus rien supposer et de laisser **ajuster** un prédicteur sur une
première tranche de l'archive, puis de le mesurer sur une seconde qu'il n'a jamais vue.
C'est la seule construction qui teste d'un coup toute une classe de défauts, y compris ceux
auxquels je n'ai pas pensé — et c'est aussi, littéralement, une tentative de prédiction.

LE MODÈLE
=========
Pour chaque tirage `t` et chaque numéro `v`, une régression logistique donne

    P(v sort au tirage t)  =  σ( β·f(t,v) )

où `f(t,v)` ne contient QUE des quantités calculables à partir des tirages d'indice `< t` :

  1  écart      log(1 + nombre de tirages depuis la dernière sortie de v)
  2  chaud 20   fréquence de v sur les 20 derniers tirages
  3  chaud 100  idem sur 100
  4  chaud 1000 idem sur 1000
  5  marge      fréquence de v depuis le début de l'archive (biais de long terme)
  6  hier       v est-il sorti au tirage t-1
  7  avant-hier v est-il sorti au tirage t-2
  8  t-3        v est-il sorti au tirage t-3
  9  voisins    v-1 ou v+1 sont-ils sortis au tirage t-1
 10  nuit       position dans la nuit, ramenée à [0,1]
 11  quota      fréquence de v depuis le DÉBUT DE LA NUIT (le §187 en forme prédictive)
 12  créneau    fréquence de v à la MÊME position, sur toutes les nuits précédentes
 13  bonus      v était-il le numéro bonus du tirage t-1
 14  énergie    le score du §185 lui-même, `S_t(v) = #{(u,w) ∈ C_{t-g1}×C_{t-g2} :
                u+w+δ ≡ v-1}`, sur six couples strictement passés

Le trait 14 rend le prédicteur appris **sur-ensemble** du prédicteur du §185 : s'il existe
une trace de Fibonacci retardé, ce modèle peut au moins faire aussi bien, et il choisit le
poids lui-même au lieu de le poser à la main.

L'ENTRAÎNEMENT ET LA MESURE SONT DISJOINTS
==========================================
`β` est ajusté sur les 60 % PREMIERS tirages, et mesuré sur les 40 % DERNIERS, que
l'ajustement n'a jamais vus. Il n'y a donc aucune fuite possible : ni du futur vers le
passé (les traits sont causaux), ni de la mesure vers l'ajustement (les tranches sont
disjointes).

DEUX MESURES, DEUX NULLES EXACTES
=================================
  * RECOUVREMENT — on prend les vingt numéros de plus fort score et l'on compte les
    numéros justes. Sous SRS, moyenne `5` et écart-type `1,6876` par tirage : la nulle
    hypergéométrique exacte du §185.
  * GAIN DE VRAISEMBLANCE — la log-vraisemblance par ligne, moins celle du modèle constant
    `P = 1/4`. Sur des données hors échantillon, un modèle non informatif a une espérance
    de gain **négative ou nulle** : un gain positif significatif ne peut pas venir du
    sur-ajustement.

UN CONTRÔLE ET DEUX TÉMOINS
===========================
  * CONTRÔLE — la même chaîne complète sur une archive SRS de même taille doit rendre
    `5,000` et un gain nul. Si elle rend plus, c'est la chaîne qui fuit, pas l'archive.
  * TÉMOIN 1, MAIN CHAUDE — une archive où un numéro sorti au tirage précédent est
    réintroduit avec probabilité `0,30`. Elle ne charge que les traits classiques et
    valide donc la moitié classique du modèle.
  * TÉMOIN 2, FIBONACCI RETARDÉ — une archive engendrée par `r_i = r_{i-3} + r_{i-7}`.
    Elle ne charge que le trait d'énergie et valide donc l'autre moitié.

Il faut les DEUX : un modèle qui apprend la main chaude peut être aveugle au générateur
additif, et réciproquement. C'est exactement ce qui s'est produit à la première écriture de
ce fichier — sans le trait 14, le témoin additif rendait `z = -1,07`, c'est-à-dire rien.
"""

import json
import os
import sys
from math import erfc, sqrt

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POOL, DRAWN = 80, 20
M32 = 1 << 32
EXP_ID = "h173.predicteur_appris"
FJETON = "/tmp/h173_jeton.json"
CHAUFFE = 2000                       # tirages de mise en route, jamais notes
PART = 0.60                          # part d'entrainement
SD1 = float(np.sqrt(DRAWN * (DRAWN / POOL) * ((POOL - DRAWN) / POOL)
                    * ((POOL - DRAWN) / (POOL - 1))))
NOMS = ("ecart", "chaud20", "chaud100", "chaud1000", "marge", "hier", "avant-hier",
        "t-3", "voisins", "nuit", "quota", "creneau", "bonus", "energie")
NF = len(NOMS)
# le trait « energie » est le score du §185 lui-meme : le predicteur appris CONTIENT donc
# le predicteur d'energie comme cas particulier, et peut lui donner le poids qu'il merite.
COUPLES = ((1, 1), (2, 1), (2, 2), (3, 1), (3, 2), (3, 3))


def say(*a):
    print(*a, flush=True)


# --------------------------------------------------------------------------------------
# Les traits. TOUS causaux : la ligne (t,v) ne lit que des tirages d'indice < t.
# --------------------------------------------------------------------------------------

def construire(M, bornes, bonus=None):
    """(N,80,NF) float32. `M` (N,80) bool, `bornes` debuts de nuit + [N]."""
    N = len(M)
    Mi = M.astype(np.int32)
    cum = np.zeros((N + 1, POOL), np.int32)
    np.cumsum(Mi, axis=0, out=cum[1:])                      # cum[t] = comptes sur 0..t-1

    X = np.zeros((N, POOL, NF), np.float32)
    t = np.arange(N)

    # 1 ecart : nombre de tirages depuis la derniere sortie, vu STRICTEMENT avant t
    idx = np.where(M, t[:, None], -1).astype(np.int32)
    der = np.maximum.accumulate(idx, axis=0)                 # derniere sortie <= t
    der = np.vstack([np.full((1, POOL), -1, np.int32), der[:-1]])   # decalage : < t
    X[:, :, 0] = np.log1p(np.minimum(t[:, None] - der, 400)).astype(np.float32)

    # 2-4 chaleur sur fenetres glissantes
    for j, W in enumerate((20, 100, 1000), start=1):
        bas = np.maximum(t - W, 0)
        X[:, :, j] = ((cum[t] - cum[bas]) / np.maximum(t - bas, 1)[:, None]).astype(np.float32)

    # 5 marge de long terme
    X[:, :, 4] = (cum[t] / np.maximum(t, 1)[:, None]).astype(np.float32)

    # 6-8 memoire courte
    for j, lag in enumerate((1, 2, 3), start=5):
        X[lag:, :, j] = Mi[:-lag]

    # 9 voisins au tirage precedent
    vois = np.zeros((N, POOL), np.float32)
    vois[:, 1:] += Mi[:, :-1]
    vois[:, :-1] += Mi[:, 1:]
    X[1:, :, 8] = np.minimum(vois[:-1], 1.0)

    # 10 position dans la nuit, et 11 quota consomme depuis le debut de la nuit
    deb = np.zeros(N, np.int64)
    lon = np.zeros(N, np.int64)
    pos = np.zeros(N, np.int64)
    nid = np.zeros(N, np.int64)
    for k in range(len(bornes) - 1):
        a, b = bornes[k], bornes[k + 1]
        deb[a:b] = a
        lon[a:b] = b - a
        pos[a:b] = np.arange(b - a)
        nid[a:b] = k
    X[:, :, 9] = (pos / lon).astype(np.float32)[:, None]
    X[:, :, 10] = ((cum[t] - cum[deb]) / np.maximum(pos, 1)[:, None]).astype(np.float32)

    # 12 creneau : frequence de v a la MEME position, sur les nuits precedentes
    K = len(bornes) - 1
    Lm = int(np.diff(bornes).max())
    G = np.zeros((K, Lm, POOL), np.int16)
    V = np.zeros((K, Lm), np.int16)
    for k in range(K):
        a, b = bornes[k], bornes[k + 1]
        G[k, :b - a] = Mi[a:b]
        V[k, :b - a] = 1
    Gc = np.cumsum(G, axis=0, dtype=np.int32)
    Vc = np.cumsum(V, axis=0, dtype=np.int32)
    Gc = np.concatenate([np.zeros((1, Lm, POOL), np.int32), Gc[:-1]], axis=0)
    Vc = np.concatenate([np.zeros((1, Lm), np.int32), Vc[:-1]], axis=0)
    X[:, :, 11] = (Gc[nid, pos] / np.maximum(Vc[nid, pos], 1)[:, None]).astype(np.float32)

    # 13 le bonus du tirage precedent
    if bonus is not None:
        B = np.zeros((N, POOL), np.float32)
        ok = bonus >= 1
        B[np.flatnonzero(ok), bonus[ok] - 1] = 1.0
        X[1:, :, 12] = B[:-1]

    # 14 l'energie du §185 : S_t(v) = #{(u,w) dans C_{t-g1} x C_{t-g2} : u+w+d = v-1}.
    #    Calculee pour tous les t d'un coup par convolution circulaire, decalages
    #    STRICTEMENT passes (g1 >= g2 >= 1), donc causale.
    F = np.fft.rfft(Mi.astype(np.float64), axis=1)
    E = np.zeros((N, POOL), np.float64)
    for g1, g2 in COUPLES:
        lo = max(g1, g2)
        C = np.rint(np.fft.irfft(F[lo - g1:N - g1] * F[lo - g2:N - g2], n=POOL, axis=1))
        E[lo:] += C + np.roll(C, 1, axis=1)
    e0 = E[CHAUFFE:].mean()
    e1 = E[CHAUFFE:].std()
    X[:, :, 13] = ((E - e0) / max(e1, 1e-9)).astype(np.float32)
    return X


# --------------------------------------------------------------------------------------
# Regression logistique : L-BFGS sur la log-vraisemblance, traits centres-reduits
# --------------------------------------------------------------------------------------

def ajuster(Xa, ya, lam=1e-6):
    from scipy.optimize import minimize
    n, F = Xa.shape
    mu = Xa.mean(axis=0)
    sd = Xa.std(axis=0)
    sd[sd < 1e-9] = 1.0
    Z = ((Xa - mu) / sd).astype(np.float64)      # float64 explicite : sinon le produit
    y = ya.astype(np.float64)                    # mixte fabrique une copie geante

    def nll(w):
        s = Z @ w[:F] + w[F]
        # log(1+e^s) stable
        lse = np.logaddexp(0.0, s)
        val = (lse - y * s).sum() / n + lam * float(w[:F] @ w[:F])
        p = 1.0 / (1.0 + np.exp(-s))
        g = np.empty(F + 1)
        g[:F] = Z.T @ (p - y) / n + 2 * lam * w[:F]
        g[F] = (p - y).sum() / n
        return val, g

    w0 = np.zeros(F + 1)
    w0[F] = np.log(0.25 / 0.75)
    r = minimize(nll, w0, jac=True, method="L-BFGS-B",
                 options={"maxiter": 500, "ftol": 1e-14, "gtol": 1e-10})
    return r.x, mu, sd


def scorer(X, w, mu, sd, bloc=4096):
    """par blocs de tirages : sinon le produit float32 x float64 fabrique une copie
    de (N, 80, NF) en double precision, soit plusieurs gigaoctets."""
    F = X.shape[-1]
    v = w[:F].astype(np.float64)
    S = np.empty(X.shape[:2], np.float64)
    for a in range(0, len(X), bloc):
        b = min(a + bloc, len(X))
        S[a:b] = ((X[a:b] - mu) / sd).astype(np.float64) @ v + w[F]
    return S


def mesurer(M, S, deb, fin):
    """recouvrement top-20 et gain de log-vraisemblance par ligne, sur [deb,fin)."""
    rec = np.empty(fin - deb, np.int64)
    for i, t in enumerate(range(deb, fin)):
        top = np.argpartition(-S[t], DRAWN)[:DRAWN]
        rec[i] = int(M[t][top].sum())
    s = S[deb:fin].ravel()
    y = M[deb:fin].ravel().astype(np.float64)
    ll = -(np.logaddexp(0.0, s) - y * s).mean()
    ll0 = 0.25 * np.log(0.25) + 0.75 * np.log(0.75)
    return rec, float(ll - ll0)


def chaine(M, bornes, bonus, etiq):
    """ajuste sur les 60 % premiers, mesure sur les 40 % derniers. Renvoie (rec, gain, w)."""
    N = len(M)
    coupe = CHAUFFE + int((N - CHAUFFE) * PART)
    X = construire(M, bornes, bonus)
    Xa = X[CHAUFFE:coupe].reshape(-1, NF)
    ya = M[CHAUFFE:coupe].reshape(-1)
    w, mu, sd = ajuster(Xa, ya)
    S = scorer(X, w, mu, sd)
    rec, gain = mesurer(M, S, coupe, N)
    z = (rec.mean() - 5.0) / (SD1 / sqrt(len(rec)))
    say(f"   {etiq:>22} | {rec.mean():9.5f} | {z:+7.2f} | {gain:+.3e} | "
        f"{coupe - CHAUFFE} appris, {N - coupe} mesures")
    return rec, gain, w, z


def srs(n, rng):
    out = np.zeros((n, POOL), bool)
    idx = np.argsort(rng.random((n, POOL)), axis=1)[:, :DRAWN]
    np.put_along_axis(out, idx, True, axis=1)
    return out


def plante_chaud(n, rng, eps):
    """SRS, puis MAIN CHAUDE : avec probabilite eps un numero sorti au tirage precedent
    est reintroduit au tirage courant. Charge les traits classiques (hier, chaud20, ecart)
    et AUCUN trait d'energie — c'est le temoin de la moitie classique du modele."""
    m = srs(n, rng)
    for t in range(1, n):
        if rng.random() < eps:
            hier = np.flatnonzero(m[t - 1] & ~m[t])
            ici = np.flatnonzero(m[t] & ~m[t - 1])
            if len(hier) and len(ici):
                m[t, hier[rng.integers(len(hier))]] = True
                m[t, ici[rng.integers(len(ici))]] = False
    return m


def plante(n, graine, K, L, signe=1):
    import random
    r0 = random.Random(graine)
    r = [r0.randrange(M32) for _ in range(max(80, L + 1))]
    i = len(r)
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

    A = lab.load()
    M = np.asarray(A.mask)
    TS = np.asarray(A.ts).astype(np.int64)
    N = len(M)
    BOR = np.r_[0, np.flatnonzero(np.diff(TS) > 1000) + 1, N]
    BONUS = np.asarray(A.bonus).astype(np.int64)
    coupe = CHAUFFE + int((N - CHAUFFE) * PART)
    nmes = N - coupe

    HYP = (f"Un predicteur AJUSTE — regression logistique sur {NF} traits causaux (ecart "
           "depuis la derniere sortie, chaleur sur 20/100/1000 tirages, marge de long "
           "terme, sorties aux tirages t-1/t-2/t-3, voisins, position dans la nuit, quota "
           "consomme depuis le debut de la nuit, frequence au meme creneau des nuits "
           f"precedentes, bonus precedent, ET le score d energie du 185 lui-meme, ce qui "
           "fait du predicteur appris un SUR-ENSEMBLE du predicteur du 185) entraine sur "
           f"les {coupe-CHAUFFE} premiers "
           f"tirages ne bat pas le hasard sur les {nmes} derniers, qu'il n'a jamais vus : "
           "son recouvrement moyen vaut 5, la valeur hypergeometrique, et son gain de "
           "log-vraisemblance sur le modele constant P = 1/4 est nul. C'est le seul test du "
           "dossier qui ne suppose PAS la forme du defaut — tous les autres la supposent, "
           "et un defaut d'une forme non prevue leur echappe par construction")
    STAT = ("R = recouvrement moyen des vingt numeros de plus fort score avec le tirage "
            f"reel, sur les {nmes} tirages de la tranche de mesure ; z = (R-5)/(1,6876/"
            "racine(n)). Statistique secondaire : G = gain de log-vraisemblance par ligne "
            "sur le modele constant, hors echantillon. Tranches d'entrainement et de mesure "
            "DISJOINTES, traits STRICTEMENT causaux")
    NUL = ("EXACTE pour R : le recouvrement de deux sous-ensembles de vingt parmi "
           "quatre-vingts est hypergeometrique, moyenne 5, ecart-type 1,6876 par tirage. "
           "Pour G : hors echantillon, un modele non informatif a une esperance de gain "
           "negative ou nulle, donc G > 0 significatif ne peut pas venir du sur-ajustement. "
           "CONTROLE : la meme chaine complete sur une archive SRS de meme taille, qui doit "
           "rendre 5,000 et un gain nul")
    VER = ("conforme si |z| < 3 et G <= 0 au controle pres ; PREDICTION si z > 3, "
           "c'est-a-dire si le predicteur appris bat le hasard hors echantillon")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h173 : {N} tirages, {len(BOR)-1} nuits, {NF} traits ; "
        f"apprentissage {CHAUFFE}..{coupe}, mesure {coupe}..{N}")
    say(f"{'source':>22} | {'recouvr.':>9} | {'z':>7} | {'gain LL':>10} | tranches")

    rng = np.random.default_rng(173)
    B0 = np.array([0, N])
    recC, gainC, wC, zC = chaine(srs(N, rng), BOR, None, "CONTROLE  SRS")
    recH, gainH, wH, zH = chaine(plante_chaud(N, rng, 0.30), BOR, None,
                                 "TEMOIN  main chaude")
    recT, gainT, wT, zT = chaine(plante(N, 21, 3, 7), BOR, None,
                                 "TEMOIN  additif(3,7)")
    recA, gainA, wA, zA = chaine(M, BOR, BONUS, "ARCHIVE")

    say("\n   poids appris sur l'archive (traits centres-reduits) :")
    o = np.argsort(-np.abs(wA[:NF]))
    for j in o:
        say(f"      {NOMS[j]:>10} : {wA[j]:+.4f}")
    say(f"      {'constante':>10} : {wA[NF]:+.4f}   (log(1/3) = {np.log(1/3):+.4f})")

    from math import comb
    P = [comb(DRAWN, k) * comb(POOL - DRAWN, DRAWN - k) / comb(POOL, DRAWN)
         for k in range(DRAWN + 1)]
    say(f"\n   loi du recouvrement sur l'archive (min {recA.min()}, max {recA.max()}) :")
    say(f"{'k':>4} | {'observe':>8} | {'attendu':>9} | {'z':>7}")
    for k in range(1, 13):
        o_ = int((recA == k).sum()); a_ = len(recA) * P[k]
        if a_ > 5:
            say(f"{k:4d} | {o_:8d} | {a_:9.1f} | {(o_-a_)/sqrt(a_*(1-P[k])):+7.2f}")

    p = float(erfc(abs(zA) / sqrt(2)))
    verdict = "PREDICTION" if zA > 3 else "conforme"
    say(f"\n   archive : z = {zA:+.3f}   p = {p:.4f}   ->   {verdict}")
    TOK["m_extra"] = 1
    lab.record(
        TOK, float(recA.mean()), p=p, verdict=verdict,
        power_at=(f"DEUX TEMOINS, chacun de {N} tirages, meme decoupage que l archive. Main "
                  f"chaude (30 %) : recouvrement "
                  f"{recH.mean():.4f}, z = {zH:+.1f} — la moitie classique du modele "
                  f"apprend. Additif (3,7) : {recT.mean():.4f}, "
                  f"z = {zT:+.1f} — le trait d energie apprend. CONTROLE : sur SRS la "
                  f"chaine rend "
                  f"{recC.mean():.5f} (z = {zC:+.2f}) et un gain de {gainC:+.2e} — elle ne "
                  f"fuit pas. Sur {nmes} tirages de mesure, l'ecart-type de la moyenne vaut "
                  f"{SD1/sqrt(nmes):.5f}, donc un avantage de 0,02 numero par tirage serait "
                  "vu a plus de trois ecarts-types"),
        notes=(f"PREDICTEUR APPRIS (§188) : le seul test du dossier qui ne suppose pas la "
               f"forme du defaut. Regression logistique a {NF} traits causaux, entrainee "
               f"sur {coupe-CHAUFFE} tirages et mesuree sur {nmes} DISJOINTS. Archive : "
               f"recouvrement {recA.mean():.5f}, z = {zA:+.3f}, gain LL {gainA:+.3e}. "
               f"Controle SRS {recC.mean():.5f} (z = {zC:+.2f}, gain {gainC:+.2e}). "
               f"Temoins : main chaude {recH.mean():.4f} (z = {zH:+.1f}), additif (3,7) "
               f"{recT.mean():.4f} (z = {zT:+.1f}, gain {gainT:+.2e}). "
               f"Plus fort poids appris sur l'archive : {NOMS[o[0]]} a {wA[o[0]]:+.4f}."))
    say("   consigne.")
