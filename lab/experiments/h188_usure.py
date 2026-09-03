"""h188 — L'USURE ET LA RÉPARATION : la machine dérive-t-elle, ou a-t-elle été réglée ?
(RAPPORT §207).

CE QUE TOUT LE DOSSIER SUPPOSE SANS LE DIRE
===========================================
Deux cent six sections cherchent un défaut **algorithmique** : une récurrence, une graine,
une relation. Toutes supposent que la machine est un programme, et qu'un programme ne
change pas.

Une machine réelle n'est jamais infaillible, et elle n'est pas infaillible de **deux
façons** que rien ici n'a testées :

  * elle **s'use** — une bille qui se ponce, un axe qui prend du jeu, une source qui
    vieillit : la fréquence d'un numéro **dérive lentement** ;
  * on la **répare** — une bille remplacée, un réglage, une mise à jour logicielle : la
    fréquence **rompt d'un coup**.

C'est exactement comme cela que de vraies loteries ont été battues, et c'est la seule
famille de défauts qui ne demande aucune hypothèse sur le générateur.

POURQUOI LE §186 NE LES VOIT PAS
================================
Le §186 balaye l'autocorrélation à tous les décalages. Une **période** y saute aux yeux.
Une **tendance monotone** n'y est presque pas visible : elle se répartit sur tous les
décalages longs à la fois et n'en charge aucun. Une **rupture** encore moins. Il faut les
statistiques faites pour cela.

LES DEUX STATISTIQUES
=====================
Sur les `346` nuits, pour chaque symbole `s` (les `80` numéros, les `6` secteurs du
multiplicateur, les `20` rangs du bonus) :

  **DÉRIVE**   la pente de la régression du compte par nuit `X_ks` sur l'indice de nuit
               `k`, normalisée. Une usure lente la rend non nulle.

  **RUPTURE**  le maximum, sur toutes les coupures `k₀`, de l'écart normalisé entre la
               moyenne avant et la moyenne après. Un remplacement la rend grande.

LA NULLE EST UNE PERMUTATION DE L'ORDRE DES NUITS
=================================================
On permute l'**ordre** des nuits. C'est la nulle exacte de l'hypothèse voulue — *les nuits
sont échangeables, donc rien ne dépend de leur rang chronologique* — et elle conserve
exactement les comptes de chaque nuit. Une dérive comme une rupture sont détruites ; tout
le reste survit.

Et le seuil se lit sur la **loi du maximum sous permutation** (§7.32), pas sur un
Bonferroni gaussien : la statistique de rupture est un maximum sur `344` coupures, donc sa
queue n'a rien de normal. C'est la cinquième fois dans ce dossier ; la leçon a fini par
rentrer.
"""

import json
import os
import sys
from math import erfc, sqrt

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POOL, DRAWN = 80, 20
EXP_ID = "h188.usure"
FJETON = "/tmp/h188_jeton.json"
REPS = 2000


def say(*a):
    print(*a, flush=True)


def stats(X, nk):
    """X (K,S) comptes par nuit ; nk (K,) tailles de nuit.
    Renvoie (pentes normalisees, ruptures normalisees) — deux vecteurs de taille S."""
    K, S = X.shape
    T = X / nk[:, None]                       # taux par tirage, pour absorber la nuit courte
    k = np.arange(K, dtype=np.float64)
    kc = k - k.mean()
    pente = (kc[:, None] * (T - T.mean(axis=0))).sum(axis=0) / (kc * kc).sum()

    # rupture : max sur les coupures du contraste de moyenne, normalise par sa propre echelle
    cum = np.cumsum(T, axis=0)
    tot = cum[-1]
    n1 = np.arange(1, K, dtype=np.float64)[:, None]
    n2 = K - n1
    m1 = cum[:-1] / n1
    m2 = (tot - cum[:-1]) / n2
    poids = np.sqrt(n1 * n2 / K)
    rupture = np.abs((m1 - m2) * poids).max(axis=0)
    return pente, rupture


def nulle(X, nk, reps, rng):
    """permutation de l'ORDRE des nuits ; renvoie les lois de chaque statistique et
    celles de leur MAXIMUM (loi exacte du max, §7.32)."""
    K = len(X)
    P, R = [], []
    for r in range(reps):
        o = rng.permutation(K)
        p, q = stats(X[o], nk[o])
        P.append(p)
        R.append(q)
        if (r + 1) % 500 == 0:
            say(f"      nulle {r+1}/{reps}")
    return np.array(P), np.array(R)


def z_et_max(obs, V):
    """z par statistique, et loi du max sous la nulle, chaque replicat laisse de cote."""
    R = len(V)
    s1 = V.sum(axis=0)
    s2 = (V * V).sum(axis=0)
    mu = s1 / R
    sd = np.sqrt(np.maximum(s2 / R - mu * mu, 1e-18))
    z = (obs - mu) / sd
    mx = np.empty(R)
    for r in range(R):
        m_ = (s1 - V[r]) / (R - 1)
        v_ = np.maximum((s2 - V[r] * V[r]) / (R - 1) - m_ * m_, 1e-18)
        mx[r] = np.abs((V[r] - m_) / np.sqrt(v_)).max()
    return z, mx


def selftest():
    say("h188 --autotest : donnees synthetiques uniquement, aucune archive lue")
    rng = np.random.default_rng(188)
    K, S = 346, 80
    nk = np.full(K, 204.0)

    # (1) nuits echangeables
    X = rng.binomial(204, 0.25, size=(K, S)).astype(np.float64)
    p, q = stats(X, nk)
    P, R = nulle(X, nk, 300, rng)
    zp, mxp = z_et_max(p, P)
    zr, mxr = z_et_max(q, R)
    ok1 = (np.abs(zp).max() < np.quantile(mxp, 0.99)
           and np.abs(zr).max() < np.quantile(mxr, 0.99))
    say(f"   libre : max |z| derive {np.abs(zp).max():.2f} (95e centile du max "
        f"{np.quantile(mxp, 0.95):.2f}) ; rupture {np.abs(zr).max():.2f} "
        f"({np.quantile(mxr, 0.95):.2f})")

    # (2) usure plantee : le numero 7 derive de 0,25 a 0,27 sur les 346 nuits
    X2 = X.copy()
    taux = 0.25 + 0.02 * np.arange(K) / K
    X2[:, 7] = rng.binomial(204, taux)
    p2, _ = stats(X2, nk)
    z2, _ = z_et_max(p2, P)
    # le garde-fou est la REGLE DE DECISION reelle — depasser le 95e centile du maximum
    # permute et etre l'argmax — et non un seuil rond invente pour l'occasion.
    ok2 = abs(z2[7]) > np.quantile(mxp, 0.95) and abs(z2[7]) == np.abs(z2).max()
    say(f"   usure plantee sur le numero 7 : z derive = {z2[7]:+.1f} "
        f"(max ailleurs {np.abs(np.delete(z2, 7)).max():.2f}, seuil "
        f"{np.quantile(mxp, 0.95):.2f})")

    # (3) reparation plantee : le numero 42 passe de 0,25 a 0,28 a la nuit 200
    X3 = X.copy()
    X3[:200, 42] = rng.binomial(204, 0.25, 200)
    X3[200:, 42] = rng.binomial(204, 0.28, K - 200)
    _, q3 = stats(X3, nk)
    z3, _ = z_et_max(q3, R)
    ok3 = abs(z3[42]) > np.quantile(mxr, 0.95) and abs(z3[42]) == np.abs(z3).max()
    say(f"   reparation plantee sur le numero 42 : z rupture = {z3[42]:+.1f} "
        f"(max ailleurs {np.abs(np.delete(z3, 42)).max():.2f}, seuil "
        f"{np.quantile(mxr, 0.95):.2f})")
    say(f"   -> nulle {'JUSTE' if ok1 else 'FAUSSE'} ; usure "
        f"{'DETECTEE' if ok2 else 'MANQUEE'} ; reparation "
        f"{'DETECTEE' if ok3 else 'MANQUEE'}")
    return ok1 and ok2 and ok3


if __name__ == "__main__":
    if "--autotest" in sys.argv:
        sys.exit(0 if selftest() else 1)

    import lab

    A = lab.load()
    N = len(A.ids)
    TS = np.asarray(A.ts).astype(np.int64)
    M = np.asarray(A.mask).astype(np.int8)
    NUMS = np.asarray(A.nums).astype(np.int64)
    BONUS = np.asarray(A.bonus).astype(np.int64)
    BOOST = np.asarray(A.boost).astype(np.int64)
    RANG = np.argmax(NUMS == BONUS[:, None], axis=1)
    VB = np.unique(BOOST)

    BOR = np.r_[0, np.flatnonzero(np.diff(TS) > 1000) + 1, N]
    K = len(BOR) - 1
    nk = np.diff(BOR).astype(np.float64)
    IB = (BOOST[:, None] == VB[None, :]).astype(np.int8)
    IR = (RANG[:, None] == np.arange(DRAWN)[None, :]).astype(np.int8)
    IND = np.concatenate([M, IB, IR], axis=1)
    NOMS = ([f"numero {v+1}" for v in range(POOL)]
            + [f"boost {int(v)}" for v in VB]
            + [f"rang {j}" for j in range(DRAWN)])
    X = np.add.reduceat(IND, BOR[:-1], axis=0).astype(np.float64)
    S = X.shape[1]
    MTOT = 2 * S

    HYP = (f"La machine ne s'use pas et n'a pas ete reglee. Sur les {K} nuits de l'archive, "
           f"aucun des {S} symboles — les 80 numeros, les {len(VB)} secteurs du "
           "multiplicateur, les 20 rangs du bonus — ne montre ni DERIVE monotone de sa "
           "frequence (usure : une bille qui se ponce, un axe qui prend du jeu, une source "
           "qui vieillit) ni RUPTURE nette (reparation : une bille remplacee, un reglage, "
           "une mise a jour). C'est la seule famille de defauts qui ne demande aucune "
           "hypothese sur le generateur, et c'est ainsi que de vraies loteries ont ete "
           "battues. Le §186 ne les voit pas : une tendance monotone se repartit sur tous "
           "les decalages longs et n'en charge aucun")
    STAT = (f"D = nombre de statistiques dont le |z| depasse le 95e centile de la loi du "
            f"MAXIMUM sous permutation. Deux familles de {S} : la pente normalisee de la "
            "regression du taux par nuit sur l'indice de nuit (derive), et le maximum sur "
            f"les {K-1} coupures du contraste de moyenne pondere par racine(n1 n2/K) "
            "(rupture)")
    NUL = (f"Permutation de l'ORDRE des {K} nuits, {REPS} fois. C'est la nulle exacte de "
           "l'echangeabilite chronologique : elle conserve exactement les comptes de chaque "
           "nuit et detruit exactement ce qui depend de leur rang. Le seuil se lit sur la "
           "LOI DU MAXIMUM sous permutation, chaque replicat laisse de cote dans sa propre "
           "normalisation (§7.32) — la statistique de rupture etant deja un maximum sur "
           f"{K-1} coupures, sa queue n'a rien de gaussien et un Bonferroni normal serait "
           "faux")
    VER = ("conforme si D = 0 ; USURE si une pente depasse ; REPARATION si une rupture "
           "depasse")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h188 : {K} nuits, {S} symboles, {MTOT} statistiques, {REPS} permutations")
    pente, rupture = stats(X, nk)
    rng = np.random.default_rng(20260903)
    P, R = nulle(X, nk, REPS, rng)
    zp, mxp = z_et_max(pente, P)
    zr, mxr = z_et_max(rupture, R)

    sp = float(np.quantile(mxp, 0.95))
    sr = float(np.quantile(mxr, 0.95))
    ip = int(np.argmax(np.abs(zp)))
    ir = int(np.argmax(np.abs(zr)))
    say(f"\n   DERIVE   : max |z| = {zp[ip]:+.3f} ({NOMS[ip]}) ; seuil "
        f"(95e centile du max permute) {sp:.3f}")
    say(f"   RUPTURE  : max |z| = {zr[ir]:+.3f} ({NOMS[ir]}) ; seuil {sr:.3f}")
    say(f"   loi du max sous permutation : derive mediane {np.median(mxp):.2f}, "
        f"rupture mediane {np.median(mxr):.2f}")

    pp = float((1 + int((mxp >= abs(zp[ip])).sum())) / (1 + REPS))
    pr = float((1 + int((mxr >= abs(zr[ir])).sum())) / (1 + REPS))
    D = int(abs(zp[ip]) > sp) + int(abs(zr[ir]) > sr)
    p = float(min(1.0, 2 * min(pp, pr)))
    verdict = ("USURE" if abs(zp[ip]) > sp else
               ("REPARATION" if abs(zr[ir]) > sr else "conforme"))
    say(f"\n   p derive = {pp:.4f} ; p rupture = {pr:.4f} ; p global = {p:.4f}")
    say(f"   ->   {verdict}")
    TOK["m_extra"] = MTOT - 1
    lab.record(
        TOK, float(max(abs(zp[ip]), abs(zr[ir]))), p=p, verdict=verdict,
        power_at=("l'autotest plante une USURE (le numero 7 derive de 0,250 a 0,270 sur les "
                  "346 nuits) et une REPARATION (le numero 42 passe de 0,250 a 0,280 a la "
                  "nuit 200) : la derive sort a z = +4,7 pour un seuil de 3,48 et la "
                  "rupture a z = +17,4 pour un seuil de 4,11, chacune en designant le BON "
                  "symbole. La sensibilite mesuree est donc : une derive de DEUX points de "
                  "pourcentage etalee sur les 346 nuits, ou une rupture de TROIS points, "
                  "sont vues. Une derive plus lente ne le serait pas, et il faut le dire"),
        notes=(f"USURE ET REPARATION (§207) — la seule famille de defauts qui ne demande "
               f"aucune hypothese sur le generateur, et celle par laquelle de vraies "
               f"loteries ont ete battues. {MTOT} statistiques sur {K} nuits : pente de "
               f"regression (derive) et maximum de contraste sur {K-1} coupures (rupture), "
               f"pour les 80 numeros, {len(VB)} secteurs de multiplicateur et 20 rangs de "
               f"bonus. Nulle par permutation de l'ORDRE des nuits, seuil sur la loi du "
               f"maximum permute. Derive max |z| = {zp[ip]:+.3f} ({NOMS[ip]}), rupture max "
               f"|z| = {zr[ir]:+.3f} ({NOMS[ir]}), seuils {sp:.2f} et {sr:.2f}. D = {D}."))
    say("   consigne.")
