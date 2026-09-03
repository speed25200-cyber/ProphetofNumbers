"""h212 — LE CODEUR EXACT : la borne du §227, refaite sur la bonne référence
(RAPPORT §235).

LA FAIBLESSE DU §227, TROUVÉE DANS MON PROPRE TRAVAIL
=====================================================
Le §227 mesure la perte logarithmique des meilleurs modèles du dossier contre

    80 · H(1/4) = 64,902250 bits par tirage

Or ce n'est **pas** l'entropie d'un tirage. Un tirage n'est pas quatre-vingts pièces
indépendantes à `1/4` : c'est un sous-ensemble de **exactement vingt** numéros parmi
quatre-vingts, et son entropie vaut

    log₂ C(80,20) = 61,616545 bits par tirage

**La référence du §227 est trop haute de `3,285705` bit par tirage.** Ses modèles n'en
profitent pas — ils ignorent la contrainte et rendent `ΔH ≈ 0` — mais la borne qu'il en tire
est adossée à un plafond faux. Un modèle qui apprendrait *seulement* que vingt numéros
sortent afficherait `+3,29` bit de « gain » sans rien savoir d'exploitable.

LE CODEUR EXACT
===============
On code le tirage **séquentiellement**, numéro par numéro de `1` à `80`. À la position `n`,
`j` numéros ayant déjà été placés, la probabilité SRS **exacte** que `n` sorte vaut

    p₀(n, j) = (20 − j) / (80 − n)

et la longueur de code totale vaut `log₂ C(80,20)` **exactement, pour tout tirage** — c'est
une identité, pas une moyenne. Voilà la vraie référence : le meilleur code possible sous SRS,
sans un bit de gras.

**Tout ce qui descend en dessous est de l'information réellement extraite**, mesurée en bits
par tirage, directement comparable aux `61,6` que le tirage contient.

CE QUE LE MODÈLE A LE DROIT DE VOIR, ET POURQUOI C'EST NOUVEAU
==============================================================
Le décodeur, à la position `n` du tirage `t`, connaît **tous les tirages précédents** et
**les positions `< n` du tirage courant**. Le modèle a donc droit à la même chose — et cette
seconde moitié est neuve dans le dossier.

> Tous les prédicteurs du dossier sont **marginaux** : ils donnent `P(n sort au tirage t)`
> sans conditionner sur ce que le tirage a déjà révélé. Celui-ci conditionne sur le tirage
> **partiellement dévoilé**, donc il teste la **loi jointe** — celle dont le §7.37 dit qu'elle
> est ce qui paie.

Deux familles de traits en profitent :

  * **le voisinage dans le tirage courant** — `n−1` et `n−2` sont-ils déjà sortis ? C'est le
    test direct de la structure des numéros consécutifs, à l'intérieur d'un tirage ;
  * **le recouvrement en cours avec le tirage précédent** — parmi les numéros déjà placés,
    combien venaient du tirage `t−1` ? C'est le §229 vu de l'intérieur d'un tirage.

Il faut le dire tout de suite : un gain venant de ces traits-là **n'est pas** directement un
avantage au jeu, puisqu'un joueur mise avant que le moindre numéro soit révélé. C'est une
preuve de **structure**, pas un ticket. Mais s'il y en avait une, on saurait enfin où chercher
— et c'est le premier instrument du dossier capable de la voir.

LA NULLE
========
La même chaîne complète — construction des traits, ajustement sur la première tranche, mesure
sur la seconde — rejouée sur des archives SRS. C'est ce qui capture le sur-apprentissage
résiduel, comme au §227.
"""

import json
import os
import sys
from math import comb, log2

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POOL, DRAWN = 80, 20
EXP_ID = "h212.codeur_exact"
FJETON = "/tmp/h212_jeton.json"
REPS = 30
PART = 0.6                 # part de la tranche hors chauffe servant a l'ajustement
CHAUFFE = 2000
IDEAL = log2(comb(POOL, DRAWN))


def say(*a):
    print(*a, flush=True)


def base_exacte(M):
    """p0(n,j) = (20-j)/(80-n) : la loi SRS exacte du codage sequentiel.

    Renvoie (p0, y) de forme (N,80). La longueur de code de p0 vaut log2 C(80,20)
    par tirage EXACTEMENT, quel que soit le tirage — c'est une identite.
    """
    y = M.astype(np.float32)
    j = np.zeros_like(y)
    j[:, 1:] = np.cumsum(y, axis=1)[:, :-1]          # places avant la position n
    reste = (POOL - np.arange(POOL, dtype=np.float32))[None, :]
    p0 = (DRAWN - j) / reste
    return np.clip(p0, 0.0, 1.0), y


def traits(M, bonus, boost, veille):
    """(N,80,F) float32. A la position n du tirage t, on n'utilise QUE les tirages < t
    et les positions < n du tirage t — exactement ce que le decodeur connait."""
    N = len(M)
    Mf = M.astype(np.float32)
    C = np.cumsum(Mf, axis=0, dtype=np.float32)
    Cp = np.zeros_like(C)
    Cp[1:] = C[:-1]                                   # cumul STRICTEMENT avant t
    t = np.arange(N, dtype=np.float32)[:, None]

    F = []
    # --- passe historique, marginale (ce que le dossier sait deja faire)
    prev = np.zeros_like(Mf)
    prev[1:] = Mf[:-1]
    F.append(prev)                                     # sorti au tirage precedent
    for w in (10, 50, 200, 1000):
        A = np.full_like(Mf, 0.25)
        A[w:] = (Cp[w:] - Cp[:-w]) / w
        F.append(A)
    F.append(Cp / np.maximum(t, 1.0))                   # taux historique du numero
    idx = np.where(Mf > 0, np.arange(N, dtype=np.float32)[:, None], -1.0)
    der = np.maximum.accumulate(idx, axis=0)
    derp = np.zeros_like(der)
    derp[1:] = der[:-1]
    derp[0] = -1.0
    F.append(np.log1p(np.maximum(t - derp, 0.0)) / 10.0)   # ecart depuis la sortie

    # --- contexte DANS le tirage courant : la nouveaute
    v1 = np.zeros_like(Mf)
    v1[:, 1:] = Mf[:, :-1]                              # n-1 deja sorti
    F.append(v1)
    v2 = np.zeros_like(Mf)
    v2[:, 2:] = Mf[:, :-2]                              # n-2 deja sorti
    F.append(v2)
    # recouvrement en cours avec le tirage precedent, centre sur son attente
    com = Mf * prev
    ccom = np.zeros_like(com)
    ccom[:, 1:] = np.cumsum(com, axis=1)[:, :-1]
    n = np.arange(POOL, dtype=np.float32)[None, :]
    F.append(ccom - DRAWN * DRAWN / POOL * (n / POOL))
    # ecart au rythme SRS (controle : sous SRS son poids doit rester nul)
    jj = np.zeros_like(Mf)
    jj[:, 1:] = np.cumsum(Mf, axis=1)[:, :-1]
    F.append((jj - DRAWN * n / POOL) / 4.0)

    # --- canaux annexes
    bp = np.zeros(N, np.int64)
    bp[1:] = bonus[:-1]
    est_bonus = np.zeros_like(Mf)
    est_bonus[np.arange(N), np.maximum(bp - 1, 0)] = 1.0
    est_bonus[0] = 0.0
    F.append(est_bonus)                                  # etait le bonus au tirage d'avant
    bo = np.zeros(N, np.float32)
    bo[1:] = boost[:-1].astype(np.float32)
    F.append(np.repeat((bo / 10.0)[:, None], POOL, axis=1))
    F.append(np.repeat(veille[:, None].astype(np.float32), POOL, axis=1))

    X = np.stack(F, axis=2)
    return np.ascontiguousarray(X)


def ajuster(X, y, p0, iters=12, ridge=1e-6):
    """Newton (IRLS) sur la log-vraisemblance, avec logit(p0) en decalage FIXE.

    Quatorze traits : la hessienne fait 14 x 14, donc Newton coute moins qu'une descente
    de gradient bien reglee et converge sans reglage du tout.
    """
    ok = (p0 > 1e-6) & (p0 < 1 - 1e-6)
    Xf = X[ok]
    yf = y[ok].astype(np.float64)
    off = np.log(p0[ok] / (1 - p0[ok])).astype(np.float64)
    mu = Xf.mean(axis=0)
    sd = Xf.std(axis=0) + 1e-6
    Z = ((Xf - mu) / sd).astype(np.float64)
    w = np.zeros(Z.shape[1])
    for _ in range(iters):
        pr = 1.0 / (1.0 + np.exp(-(off + Z @ w)))
        pds = np.maximum(pr * (1 - pr), 1e-9)
        H = (Z * pds[:, None]).T @ Z + ridge * len(Z) * np.eye(Z.shape[1])
        g = Z.T @ (yf - pr)
        pas = np.linalg.solve(H, g)
        w += pas
        if float(np.abs(pas).max()) < 1e-9:
            break
    return w.astype(np.float64), mu, sd


def bits(X, y, p0, w, mu, sd):
    """longueur de code moyenne, en bits par tirage."""
    ok = (p0 > 1e-6) & (p0 < 1 - 1e-6)
    off = np.log(p0[ok] / (1 - p0[ok])).astype(np.float64)
    z = ((X[ok] - mu) / sd) @ w
    p = 1.0 / (1.0 + np.exp(-(off + z)))
    p = np.clip(p, 1e-9, 1 - 1e-9)
    yy = y[ok]
    L = -(yy * np.log2(p) + (1 - yy) * np.log2(1 - p)).sum()
    return float(L / (len(y) / POOL))          # bits par TIRAGE


if __name__ == "__main__":
    import lab

    A = lab.load()
    M = np.asarray(A.mask)
    TS = np.asarray(A.ts).astype(np.int64)
    BONUS = np.asarray(A.bonus).astype(np.int64)
    BOOST = np.asarray(A.boost).astype(np.int64)
    N = len(M)
    veille = np.zeros(N, np.int8)
    veille[np.r_[0, np.flatnonzero(np.diff(TS) > 1000) + 1]] = 1
    coupe = CHAUFFE + int((N - CHAUFFE) * PART)
    nmes = N - coupe

    HYP = (f"L'archive ne se code pas en moins de log2 C(80,20) = {IDEAL:.6f} bits par "
           f"tirage, meme par un modele qui voit le tirage PARTIELLEMENT DEVOILE. Deux "
           f"choses sont neuves. (1) LA REFERENCE. Le §227 mesure contre 80 H(1/4) = "
           f"64,902250 bits par tirage, qui n'est PAS l'entropie d'un tirage : un tirage "
           f"n'est pas 80 pieces independantes a 1/4 mais un sous-ensemble de EXACTEMENT 20 "
           f"numeros, d'entropie log2 C(80,20) = 61,616545. La reference du §227 est trop "
           f"haute de 3,285705 bit par tirage ; ses modeles n'en profitent pas mais la borne "
           f"est adossee a un plafond faux. Le codeur sequentiel exact, p0(n,j) = "
           f"(20-j)/(80-n), atteint log2 C(80,20) EXACTEMENT pour tout tirage — c'est une "
           f"identite, pas une moyenne — et c'est la vraie reference. (2) CE QUE LE MODELE "
           f"VOIT. Tous les predicteurs du dossier sont MARGINAUX : ils donnent P(n sort au "
           f"tirage t) sans conditionner sur ce que le tirage a deja revele. Celui-ci "
           f"conditionne sur le tirage partiellement devoile — voisinage n-1 et n-2 dans le "
           f"tirage courant, recouvrement en cours avec le tirage precedent — donc il teste "
           f"la LOI JOINTE, celle dont le §7.37 dit qu'elle est ce qui paie. Un gain venant "
           f"de ces traits ne serait PAS directement un avantage au jeu (un joueur mise "
           f"avant que le moindre numero soit revele) mais une preuve de structure, et le "
           f"premier instrument du dossier capable de la voir")
    STAT = (f"longueur de code hors echantillon en bits par tirage sur les {nmes} tirages de "
            f"la tranche de mesure, contre la reference exacte {IDEAL:.6f}")
    NUL = (f"EXACTE pour la reference : le codeur sequentiel SRS rend log2 C(80,20) bits "
           f"pour tout tirage, identiquement. La loi du gain sous la nulle vient de {REPS} "
           f"archives SRS completes rejouant la MEME chaine — traits, ajustement, mesure — "
           f"ce qui capture le sur-apprentissage residuel")
    VER = ("conforme si le gain de l'archive ne depasse pas le 95e centile du gain sous SRS ; "
           "STRUCTURE JOINTE sinon, auquel cas le poids des traits intra-tirage dit ou elle "
           "se trouve")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    # ------------------------------------------------------------------ selftest
    say("\n   selftest : l'identite du codeur exact, sur du synthetique")
    rng0 = np.random.default_rng(212)
    W = lab.srs(500, rng0)
    p0, y = base_exacte(W)
    ok = (p0 > 1e-6) & (p0 < 1 - 1e-6)
    terme = np.zeros_like(p0, np.float64)
    pc = np.clip(p0.astype(np.float64), 1e-12, 1 - 1e-12)
    terme[ok] = -(y[ok] * np.log2(pc[ok]) + (1 - y[ok]) * np.log2(1 - pc[ok]))
    parligne = terme.sum(axis=1)
    par_tirage = float(parligne.mean())
    say(f"      codeur exact sur 500 tirages SRS : {par_tirage:.9f} bits/tirage")
    say(f"      log2 C(80,20)                    : {IDEAL:.9f}")
    if abs(par_tirage - IDEAL) > 1e-6:
        say("      IDENTITE FAUSSE — on s'arrete")
        sys.exit(1)
    ecart = float(np.abs(parligne - IDEAL).max())
    say(f"      ecart maximal TIRAGE PAR TIRAGE  : {ecart:.2e}   (identite, pas moyenne)")

    say("\n   selftest : temoin plante — on colle les numeros consecutifs")
    Wp = lab.srs(20000, rng0).copy()
    for i in range(len(Wp)):
        d = np.flatnonzero(Wp[i])
        if len(d) < DRAWN:
            continue
        a = int(d[0])
        if a + 1 < POOL and not Wp[i, a + 1]:
            occ = np.flatnonzero(Wp[i])
            occ = occ[(occ != a) & (occ != a + 1)]
            Wp[i, a + 1] = True
            Wp[i, int(occ[-1])] = False        # on RETIRE un numero tire, pas une case vide

    def mesurer(Mx, bx, box):
        p0x, yx = base_exacte(Mx)
        X = traits(Mx, bx, box, veille[:len(Mx)])
        w, mu, sd = ajuster(X[CHAUFFE:coupe].reshape(-1, X.shape[2]),
                            yx[CHAUFFE:coupe].reshape(-1),
                            p0x[CHAUFFE:coupe].reshape(-1))
        b = bits(X[coupe:].reshape(-1, X.shape[2]), yx[coupe:].reshape(-1),
                 p0x[coupe:].reshape(-1), w, mu, sd)
        del X
        return b, w

    cp, cc = coupe, N
    coupe = CHAUFFE + int((20000 - CHAUFFE) * PART)
    bw, _ = mesurer(Wp, BONUS[:20000], BOOST[:20000])
    b0, _ = mesurer(lab.srs(20000, rng0), BONUS[:20000], BOOST[:20000])
    say(f"      SRS pur              : {b0:.6f} bits/tirage  (gain {IDEAL-b0:+.6f})")
    say(f"      consecutifs colles   : {bw:.6f} bits/tirage  (gain {IDEAL-bw:+.6f})")
    if IDEAL - bw < 0.01:
        say("      le temoin plante n'est PAS vu — l'instrument est aveugle, on s'arrete")
        sys.exit(1)
    coupe = cp
    del Wp

    # ------------------------------------------------------------------ archive
    say(f"\n   archive : ajustement {CHAUFFE}..{coupe}, mesure {coupe}..{N} "
        f"({nmes} tirages)")
    bobs, wobs = mesurer(M, BONUS, BOOST)
    say(f"   longueur de code hors echantillon : {bobs:.6f} bits/tirage")
    say(f"   reference exacte                  : {IDEAL:.6f}")
    say(f"   gain                              : {IDEAL - bobs:+.6f} bit/tirage")

    noms = ["sorti au tirage precedent", "fenetre 10", "fenetre 50", "fenetre 200",
            "fenetre 1000", "taux historique", "ecart depuis la sortie",
            "n-1 deja sorti (INTRA)", "n-2 deja sorti (INTRA)",
            "recouvrement en cours (INTRA)", "ecart au rythme SRS (controle)",
            "etait le bonus", "multiplicateur precedent", "debut de nuit"]
    say("\n   poids appris (standardises) :")
    for nm, wv in sorted(zip(noms, wobs.tolist()), key=lambda p: -abs(p[1])):
        say(f"      {nm:>34} : {wv:+.5f}")

    # ------------------------------------------------------------------ nulle
    gains = np.empty(REPS)
    rng = np.random.default_rng(0x212)
    for r in range(REPS):
        Mr = lab.srs(N, rng)
        br, _ = mesurer(Mr, BONUS, BOOST)
        gains[r] = IDEAL - br
        if (r + 1) % 10 == 0:
            say(f"   ... {r+1}/{REPS} repliques")

    g = IDEAL - bobs
    mu_, sd_ = float(gains.mean()), float(gains.std())
    z = (g - mu_) / max(sd_, 1e-12)
    seuil = float(np.quantile(gains, 0.95))
    p = float((np.sum(gains >= g) + 1) / (REPS + 1))
    say(f"\n   gain archive       : {g:+.6f} bit/tirage")
    say(f"   gain sous SRS      : {mu_:+.6f} +/- {sd_:.6f}   (95e centile {seuil:+.6f})")
    say(f"   z = {z:+.2f}   p = {p:.4g}")
    say(f"   soit au plus {100*max(g, seuil)/IDEAL:.4f} % des {IDEAL:.2f} bits d'un tirage")

    verdict = "STRUCTURE JOINTE" if g > seuil else "conforme"
    say(f"\n   {verdict}")

    TOK["m_extra"] = 0
    lab.record(
        TOK, float(g), p=float(p), verdict=verdict,
        power_at=(f"le temoin plante mesure la sensibilite : coller un numero consecutif "
                  f"dans chaque tirage fait gagner {IDEAL-bw:.4f} bit par tirage, la ou le "
                  f"SRS pur en donne {IDEAL-b0:+.4f}. L'ecart-type du gain sous SRS vaut "
                  f"{sd_:.2e} bit/tirage, donc l'instrument voit une structure valant "
                  f"{3*sd_:.2e} bit par tirage sur les {IDEAL:.1f} qu'il contient. Et la "
                  f"reference est EXACTE, pas estimee : le codeur sequentiel SRS rend "
                  f"log2 C(80,20) pour chaque tirage, a {ecart:.1e} pres"),
        notes=(f"LE CODEUR EXACT (§235) — le §227 mesurait contre 80 H(1/4) = 64,902250 "
               f"bits/tirage, qui n'est pas l'entropie d'un tirage : la vraie reference est "
               f"log2 C(80,20) = {IDEAL:.6f}, soit 3,285705 bit de moins. Le codeur "
               f"sequentiel exact l'atteint identiquement. Et le modele conditionne sur le "
               f"tirage PARTIELLEMENT DEVOILE (voisins n-1, n-2 ; recouvrement en cours avec "
               f"le tirage precedent), ce qu'aucun predicteur marginal du dossier ne pouvait "
               f"faire : il teste la loi JOINTE. Gain hors echantillon sur {nmes} tirages : "
               f"{g:+.6f} bit/tirage contre {mu_:+.6f} +/- {sd_:.6f} sous {REPS} repliques "
               f"SRS, z = {z:+.2f}, p = {p:.4g}."))
    say("   consigne.")
