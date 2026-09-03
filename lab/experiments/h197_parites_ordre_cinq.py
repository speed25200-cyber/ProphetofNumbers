"""h197 — LES PARITÉS D'ORDRE CINQ : le dernier ordre qui a un sens économique
(RAPPORT §218).

POURQUOI CINQ, ET POURQUOI ON S'ARRÊTE LÀ
=========================================
Le §215 exclut toute relation de parité entre **quatre** numéros. Il se termine en
nommant ce qui reste : une dépendance d'ordre **cinq ou plus** dont toutes les marges
d'ordre inférieur seraient exactement uniformes.

Il y a une tour infinie d'ordres, et la question honnête est : où s'arrête-t-on ? La
réponse n'est pas statistique, elle est **économique**. Le barème de l'opérateur
(`lab/bareme_observed.csv`) vend des grilles de `5, 6, 7, 8, 10` numéros. **Cinq est la
plus petite grille qu'on puisse acheter.** Une dépendance d'ordre cinq est donc exactement
« le jackpot de la grille la moins chère » — le dernier ordre dont un écart se convertirait
directement en francs sur ce barème-là. Au-delà, la même structure devient une hypothèse
sur un objet que personne ne vend seul.

CE QUE CE FICHIER AJOUTE AU §213 D, QUI MESURAIT DÉJÀ `P(5/5)`
==============================================================
Le §213 D et le §217 mesurent, hors échantillon, le taux de `5/5` d'une grille de cinq
cherchée sur l'autre moitié. C'est un **comptage** : il voit une dépendance qui rend la
coïncidence complète plus probable, et il ne voit qu'un **doublement**
(`22,75` attendus, écart-type `4,77`).

La parité est un instrument différent et, sur une structure algébrique, bien plus
sensible :

    W_S = (1/N) · Σ_t (−1)^{|S ∩ D_t|}

Elle somme les cinq indicateurs **avec des signes** au lieu d'exiger leur coïncidence, de
sorte qu'une relation portée par une fraction `ε` des tirages sort à `z ≈ 260 · ε`. Elle
voit donc une relation portée par **deux tirages sur cent**, et surtout elle balaie les
`C(80,5) = 24 040 016` parties avec une loi du maximum propre, là où le §213 D en
choisissait une seule pour la mesurer.

LE CALCUL, ET LE SYSTÈME DE NUMÉRATION COMBINATOIRE
===================================================
Même identité qu'au §215 :

    N · W_S  =  Σ_{T ⊆ S} (−2)^{|T|} · C_T

soit, pour `|S| = 5` : `1` terme constant, `5` singletons, `10` paires, `10` triplets,
`5` quadruplets et `1` quintuplet. L'indexation à plat en base `80` du §215 demanderait
`80⁵ = 3,3 × 10⁹` cases. On utilise donc le **rang colexicographique**

    rang({a₁<…<a_k}) = Σ_i C(a_i, i)

qui numérote les parties de taille `k` exactement sur `0 … C(80,k)−1`. Le tableau des
quintuplets tient alors en `24 040 016` cases au lieu de `3,3 × 10⁹`, et l'assemblage se
fait par tranches pour ne jamais matérialiser les trente et un index à la fois.

LA NULLE EST EXACTE
===================
    E₅ = Σ_h (−1)^h C(5,h)·C(75,20−h)/C(80,20) = 3079/158158 = 0,01946787

et non `(1/2)⁵ = 0,03125`. Le produit valant `±1`, `Var = 1 − E₅²` exactement.
"""

import json
import os
import sys
from fractions import Fraction as F
from itertools import combinations
from math import sqrt

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POOL, DRAWN = 80, 20
EXP_ID = "h197.parites_ordre_cinq"
FJETON = "/tmp/h197_jeton.json"
REPS = 25
ORDRE = 5
TRANCHE = 1 << 20                  # parties traitees par tranche a l'assemblage


def say(*a):
    print(*a, flush=True)


def binom(n, r):
    v = F(1)
    for i in range(r):
        v *= F(n - i, i + 1)
    return v


def parite_exacte(k):
    return sum((-1) ** h * binom(k, h) * binom(POOL - k, DRAWN - h) / binom(POOL, DRAWN)
               for h in range(k + 1))


# tables du systeme de numeration combinatoire : TAB[k][i] = C(i, k+1)
TAB = [np.array([int(binom(i, k)) for i in range(POOL + 1)], np.int64)
       for k in range(1, ORDRE + 1)]


def rang(cols):
    """rang colexicographique d'une partie donnee par ses colonnes triees croissantes."""
    r = TAB[0][cols[0]]
    for i in range(1, len(cols)):
        r = r + TAB[i][cols[i]]
    return r


def toutes_parties(n, k):
    """les C(n,k) parties triees, engendrees sans passer par une liste Python."""
    idx = np.arange(n, dtype=np.int8)[:, None]
    for _ in range(k - 1):
        dern = idx[:, -1].astype(np.int64)
        cnt = n - 1 - dern
        garde = cnt > 0
        idx, dern, cnt = idx[garde], dern[garde], cnt[garde]
        rep = np.repeat(np.arange(len(idx)), cnt)
        base = np.repeat(np.cumsum(cnt) - cnt, cnt)
        offs = np.arange(int(cnt.sum())) - base
        nouveau = (np.repeat(dern, cnt) + 1 + offs).astype(np.int8)
        idx = np.column_stack([idx[rep], nouveau])
    return idx


def comptes_ordre(NU, k, bloc=256):
    """C_T pour toutes les parties T de taille k des tirages, indexees par rang colex."""
    idx = np.array(list(combinations(range(DRAWN), k))).T
    acc = np.zeros(int(binom(POOL, k)), np.int64)
    for d in range(0, len(NU), bloc):
        Q = NU[d:d + bloc]
        acc += np.bincount(rang([Q[:, idx[j]] for j in range(k)]).ravel(),
                           minlength=len(acc))
    return acc


def parites(NU, N, S, sortie=None):
    """N * W_S pour les parties S (tableau (m,5) trie), par tranches.

    `sortie` permet de reutiliser un tampon entre repliques.
    """
    C = [np.bincount(NU.ravel(), minlength=POOL).astype(np.int64)]
    for k in range(2, ORDRE + 1):
        C.append(comptes_ordre(NU, k))
    m = len(S)
    out = np.empty(m, np.float64) if sortie is None else sortie
    for a in range(0, m, TRANCHE):
        T = S[a:a + TRANCHE].astype(np.int64)
        s = np.full(len(T), float(N))
        for k, signe in ((1, -2.0), (2, 4.0), (3, -8.0), (4, 16.0), (5, -32.0)):
            for sous in combinations(range(ORDRE), k):
                if k == 1:
                    s += signe * C[0][T[:, sous[0]]]
                else:
                    s += signe * C[k - 1][rang([T[:, j] for j in sous])]
        out[a:a + TRANCHE] = s
    return out


def selftest():
    import lab
    say("h197 --autotest : donnees synthetiques uniquement, aucune archive lue")
    ok = True

    say("\n   (1) LE SYSTEME DE NUMERATION COMBINATOIRE")
    for n, k in ((8, 3), (12, 4), (20, 5)):
        A = toutes_parties(n, k)
        att = np.array(list(combinations(range(n), k)), np.int8)
        bon = A.shape == att.shape and bool((A == att).all())
        r = rang([A[:, j].astype(np.int64) for j in range(k)])
        bij = bool((np.sort(r) == np.arange(int(binom(n, k)))).all())
        say(f"       C({n},{k}) = {len(A):7d} parties : engendrees {'OK' if bon else 'FAUX'}"
            f" ; rangs = 0..C-1 sans trou {'OK' if bij else 'FAUX'}")
        ok &= bon and bij

    say("\n   (2) L'IDENTITE N.W_S = somme_(T inclus dans S) (-2)^|T| C_T")
    rng = np.random.default_rng(197)
    M = lab.srs(2000, rng)
    NU = np.nonzero(M)[1].reshape(2000, DRAWN).astype(np.int64)
    S = toutes_parties(POOL, ORDRE)
    say(f"       {len(S)} parties de cinq engendrees")
    W = parites(NU, 2000, S)
    Y = 1 - 2 * M.astype(np.int64)
    ech = rng.choice(len(S), 30, replace=False)
    direct = np.array([Y[:, S[j].astype(np.int64)].prod(axis=1).sum() for j in ech],
                      np.float64)
    ecart = float(np.abs(direct - W[ech]).max())
    say(f"       30 parties tirees au hasard, ecart maximal a la parite directe : {ecart:g}")
    ok &= ecart == 0.0

    say("\n   (3) LA NULLE EXACTE, et sa variance")
    E5 = float(parite_exacte(ORDRE))
    ferme = sum((-1) ** h * binom(DRAWN, h) * binom(POOL - DRAWN, ORDRE - h)
                for h in range(ORDRE + 1)) / binom(POOL, ORDRE)
    say(f"       E5 = {parite_exacte(ORDRE)} = {E5:.8f}   ((1/2)^5 = {0.5**5:.8f})")
    say(f"       forme fermee somme_h (-1)^h C(20,h) C(60,5-h) / C(80,5) = {ferme}")
    ok &= ferme == parite_exacte(ORDRE)
    R, n = 25, 5000
    tem = rng.choice(len(S), 3, replace=False)
    V = np.empty((R, 3))
    for r in range(R):
        Sm = lab.srs(n, rng)
        NUs = np.nonzero(Sm)[1].reshape(n, DRAWN).astype(np.int64)
        V[r] = parites(NUs, n, S[tem]) / n
    att = sqrt((1 - E5 * E5) / n)
    mes = float(V.std(axis=0).mean())
    say(f"       ecart-type de W_S sur {R} repliques de {n} tirages : {mes:.6f} "
        f"contre racine((1-E5²)/n) = {att:.6f}")
    bon = abs(mes - att) / att < 0.30
    say(f"       -> {'VARIANCE CONFIRMEE' if bon else 'VARIANCE FAUSSE'}")
    ok &= bon

    say("\n   (4) LE TEMOIN : une parite plantee sur une partie de cinq")
    NT, EPS = 30000, 0.06
    CIBLE = np.array([9, 24, 41, 58, 73])
    M = lab.srs(NT, rng)
    for i in np.flatnonzero(rng.random(NT) < EPS):
        if int(M[i, CIBLE].sum()) % 2 == 1:
            dedans = CIBLE[M[i, CIBLE]]
            if len(dedans):
                M[i, int(rng.choice(dedans))] = False
                M[i, int(rng.choice(np.flatnonzero(~M[i])))] = True
            else:
                pris = np.flatnonzero(M[i] & ~np.isin(np.arange(POOL), CIBLE))
                M[i, int(rng.choice(pris))] = False
                M[i, int(rng.choice(CIBLE))] = True
    NU = np.nonzero(M)[1].reshape(NT, DRAWN).astype(np.int64)
    W = parites(NU, NT, S) / NT
    z = (W - E5) / sqrt((1 - E5 * E5) / NT)
    j = int(np.argmax(np.abs(z)))
    trouve = S[j].astype(np.int64).tolist()
    say(f"       plantee {list(CIBLE)} a {100*EPS:.0f} % ; maximum |z| = {z[j]:+.2f} "
        f"sur {trouve}")
    bon = trouve == CIBLE.tolist() and abs(z[j]) > 8
    say(f"       -> {'TEMOIN RETROUVE' if bon else 'TEMOIN MANQUE'}")
    ok &= bon

    say(f"\n   -> {'CALIBRE 4/4' if ok else 'DEFAILLANT'}")
    return ok


if __name__ == "__main__":
    if "--autotest" in sys.argv:
        sys.exit(0 if selftest() else 1)

    import lab

    A = lab.load()
    M = np.asarray(A.mask)
    N = len(M)
    NU = np.nonzero(M)[1].reshape(N, DRAWN).astype(np.int64)
    n2 = N // 2
    E5 = float(parite_exacte(ORDRE))
    SD = sqrt((1 - E5 * E5) / N)
    NS = int(binom(POOL, ORDRE))

    HYP = ("Aucune relation de parite d'ordre cinq ne lie les numeros d'un tirage. Le §215 "
           "exclut l'ordre quatre et nomme ce qui reste : une dependance d'ordre cinq ou "
           "plus dont toutes les marges inferieures seraient exactement uniformes. On "
           "s'arrete a cinq pour une raison economique et non statistique — le bareme de "
           "l'operateur vend des grilles de 5, 6, 7, 8 et 10 numeros, donc CINQ est la plus "
           "petite grille achetable, et une dependance d'ordre cinq est exactement le "
           "jackpot de la grille la moins chere. Le §213 D mesurait deja P(5/5) hors "
           "echantillon, mais par un COMPTAGE qui ne voit qu'un doublement (22,75 attendus, "
           "ecart-type 4,77) et sur une seule grille choisie ; la parite somme les cinq "
           "indicateurs AVEC DES SIGNES, de sorte qu'une relation portee par une fraction "
           "eps des tirages sort a z d'environ 260 eps, et elle balaie les "
           f"{NS} parties avec une loi du maximum propre")
    STAT = (f"max |z| sur les {NS} parties de cinq, ou z = (W_S - E5)/racine((1-E5²)/N) et "
            f"W_S = (1/N) somme_t (-1)^|S inter D_t|, reduit par la loi EMPIRIQUE du "
            f"maximum sur {REPS} repliques SRS chacune laissee hors de sa propre "
            f"normalisation ; plus l'energie somme (W_S - E5)²")
    NUL = (f"EXACTE : E5 = {parite_exacte(ORDRE)} = {E5:.8f} et non (1/2)^5 = 0,03125, "
           f"l'ecart venant de la contrainte exactement vingt par tirage ; le produit "
           f"valant +/-1 sa variance vaut 1 - E5² exactement, d'ou un ecart-type de "
           f"{SD:.8f} sur {N} tirages independants. Les repliques ne servent qu'a la loi du "
           "MAXIMUM, la correlation entre parties chevauchantes interdisant un Bonferroni")
    VER = ("conforme si le maximum reduit reste sous le 95e centile de sa loi empirique ; "
           "RELATION DE PARITE sinon")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h197 : {N} tirages ; {NS} parties de cinq")
    say(f"   nulle exacte E5 = {parite_exacte(ORDRE)} = {E5:.8f} ; ecart-type {SD:.8f}")
    S = toutes_parties(POOL, ORDRE)
    say(f"   parties engendrees : {S.shape}")

    tampon = np.empty(NS, np.float64)
    W = parites(NU, N, S, tampon) / N
    z = (W - E5) / SD
    j = int(np.argmax(np.abs(z)))
    obs = np.array([float(np.abs(z).max()), float(((W - E5) ** 2).sum() * N)])
    partie = (S[j].astype(np.int64) + 1).tolist()
    say(f"\nARCHIVE   max |z| = {z[j]:+.3f} sur la partie {partie}")
    say(f"          energie N.somme (W-E5)² = {obs[1]:.1f}   (attendue ~{NS})")
    say(f"          moyenne des z {z.mean():+.4f}, ecart-type {z.std():.4f}")

    V = np.empty((REPS, 2))
    rng = np.random.default_rng(0x197)
    for r in range(REPS):
        Sm = lab.srs(N, rng)
        NUs = np.nonzero(Sm)[1].reshape(N, DRAWN).astype(np.int64)
        Ws = parites(NUs, N, S, tampon) / N
        V[r] = (float(np.abs((Ws - E5) / SD).max()), float(((Ws - E5) ** 2).sum() * N))
        say(f"   ... {r+1}/{REPS} repliques   max {V[r,0]:.3f}")

    s1, s2 = V.sum(axis=0), (V * V).sum(axis=0)
    mu, sd = V.mean(axis=0), V.std(axis=0)
    o = float(np.abs((obs - mu) / np.maximum(sd, 1e-12)).max())
    mx = np.empty(REPS)
    for r in range(REPS):
        m_ = (s1 - V[r]) / (REPS - 1)
        v_ = np.maximum((s2 - V[r] * V[r]) / (REPS - 1) - m_ * m_, 1e-12)
        mx[r] = float(np.abs((V[r] - m_) / np.sqrt(v_)).max())
    p = float((1 + int((mx >= o).sum())) / (1 + REPS))

    say(f"\n   {'statistique':>16} | {'archive':>14} | {'repliques':>22} | {'z reduit':>9}")
    for i, nom in enumerate(("max |z|", "energie")):
        say(f"   {nom:>16} | {obs[i]:14.3f} | {mu[i]:14.3f} +/-{sd[i]:8.3f} | "
            f"{(obs[i]-mu[i])/max(sd[i],1e-12):+9.3f}")
    say(f"   maximum reduit {o:.3f} ; median des repliques {np.median(mx):.3f} ; "
        f"95e centile {np.percentile(mx, 95):.3f}")

    W1 = parites(NU[:n2], n2, S) / n2
    j1 = int(np.argmax(np.abs(W1 - E5)))
    z1 = (W1[j1] - E5) / sqrt((1 - E5 * E5) / n2)
    del W1
    W2 = parites(NU[n2:], N - n2, S[j1:j1 + 1]) / (N - n2)
    z2 = float((W2[0] - E5) / sqrt((1 - E5 * E5) / (N - n2)))
    say(f"\n   HORS ECHANTILLON : partie {(S[j1].astype(np.int64)+1).tolist()} choisie sur "
        f"la premiere moitie")
    say(f"      en echantillon z = {z1:+.2f}   hors echantillon z = {z2:+.2f}")

    verdict = "RELATION DE PARITE" if p <= 0.05 else "conforme"
    say(f"\n   p (loi empirique du maximum, {REPS} repliques) = {p:.4f}   ->   {verdict}")
    TOK["m_extra"] = NS - 1
    lab.record(
        TOK, o, p=p, verdict=verdict,
        power_at=(f"l'ecart-type de W_S vaut {SD:.6f} sur {N} tirages, donc une relation "
                  f"portee par une fraction eps des tirages sort a z = eps(1-E5)/{SD:.6f} "
                  f"= {(1-E5)/SD:.0f} eps : le test voit une relation portee par "
                  f"{100*5.6*SD/(1-E5):.1f} % des tirages. A comparer au comptage du §213 D "
                  f"qui, sur une SEULE grille choisie, ne voyait qu'un doublement de "
                  f"P(5/5). Le temoin plante une parite a 6 % sur 30 000 tirages et la "
                  f"retrouve a la bonne partie"),
        notes=(f"LES PARITES D'ORDRE CINQ (§218) — le dernier ordre qui a un sens "
               f"economique, cinq etant la plus petite grille que le bareme vende. {NS} "
               f"parties, nulle EXACTE E5 = {parite_exacte(ORDRE)}, rang colexicographique "
               f"pour ramener le tableau des quintuplets de 80^5 = 3,3e9 cases a {NS}. "
               f"Archive : max |z| = {z[j]:+.3f} sur {partie}, energie {obs[1]:.1f} pour "
               f"{NS} attendus ; maximum reduit {o:.3f} contre un 95e centile de "
               f"{np.percentile(mx, 95):.3f}, p = {p:.4f}. Hors echantillon, la partie la "
               f"plus extreme de la premiere moitie passe de z = {z1:+.2f} a "
               f"z = {z2:+.2f}."))
    say("   consigne.")
