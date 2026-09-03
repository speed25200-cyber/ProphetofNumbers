"""h196 — LES DEUX QUEUES : le barème paie aussi pour ZÉRO (RAPPORT §217).

CE QUE LE BARÈME DIT, ET QUE PERSONNE N'AVAIT LU
================================================
Le barème relevé sur l'écran (`lab/bareme_observed.csv`) a deux propriétés que tout le
dossier avait ignorées, parce que tout le dossier cherchait à prédire les numéros qui
**sortent** :

  * **l'option EXTRA n'est pas monotone.** À *chaque* taille de grille, `1` juste paie plus
    que `2` justes — `12` contre `7` pour une grille de cinq, `12` contre `4` pour une
    grille de dix. C'est une console volontaire, et elle récompense l'échec presque total.

  * **à dix numéros, ZÉRO juste paie.** `2` en base et `2` en EXTRA. C'est la mise
    classique du keno sur la queue basse.

Or un gain est une fonction **convexe aux deux bouts**. Le §213 a fermé la queue haute :
`P(les k sortent)` ne s'écarte pas. Personne n'a jamais mesuré l'autre :

> **`P(aucun des k ne sort)`, hors échantillon, pour une grille choisie froide.**

Le §210 avait bien mesuré une grille froide, mais son **taux de sortie moyen** — c'est-à-dire
la moyenne, la seule chose que les marges bornent déjà. Ici on mesure la **queue**, qui
dépend de la loi jointe et que rien dans le dossier ne borne.

CE QUI EST MESURÉ
=================
Pour les cinq tailles du barème — `k = 5, 6, 7, 8, 10` — et dans les deux sens de découpage :

  **QUEUE HAUTE.** La grille qui maximise le nombre de `k/k` sur une moitié, jouée sur
  l'autre. Nulle exacte : `P_k = ∏_{j<k} (20−j)/(80−j)`.

  **QUEUE BASSE.** La grille qui maximise le nombre de `0/k` sur une moitié, jouée sur
  l'autre. Nulle exacte : `Q_k = ∏_{j<k} (60−j)/(80−j)`.

La recherche est un **faisceau** de largeur `100` : elle n'est pas exhaustive et ne prétend
pas l'être. L'honnêteté du test ne vient pas de l'optimalité de la recherche mais de la
**disjonction des fenêtres** — quelle que soit la façon dont la grille a été trouvée sur la
première moitié, son taux sur la seconde a une nulle binomiale exacte.

POURQUOI CE N'EST PAS UNE REDITE DU §213
========================================
Le §213 cherchait la grille la plus **positivement liée** et regardait `P(tous sortent)`.
Une dépendance **négative** — des numéros qui s'évitent — laisse elle aussi les marges
intactes, ne se voit pas dans la queue haute, et **paie** sur ce barème-ci. C'est une
seconde brèche du même argument, symétrique de la première, et elle était ouverte.
"""

import json
import os
import sys
from fractions import Fraction as F
from math import erfc, sqrt

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POOL, DRAWN = 80, 20
EXP_ID = "h196.les_deux_queues"
FJETON = "/tmp/h196_jeton.json"
TAILLES = (5, 6, 7, 8, 10)
FAISCEAU = 100


def say(*a):
    print(*a, flush=True)


def p_haute(k):
    """P(les k numeros sortent tous), EXACTE."""
    v = F(1)
    for j in range(k):
        v *= F(DRAWN - j, POOL - j)
    return v


def p_basse(k):
    """P(aucun des k ne sort), EXACTE."""
    v = F(1)
    for j in range(k):
        v *= F(POOL - DRAWN - j, POOL - j)
    return v


def faisceau(A, k, haute):
    """recherche par faisceau de la grille de k maximisant la queue demandee, sur A seul.

    Un etat est (grille, sous-ensemble des tirages encore compatibles). Pour la queue
    haute c'est l'ensemble des tirages qui CONTIENNENT toute la grille ; pour la queue
    basse, ceux qui n'en contiennent AUCUN membre. Dans les deux cas l'ajout d'un numero
    ne fait que restreindre, ce qui rend le faisceau bien defini.
    """
    n = len(A)
    etats = [(np.empty(0, np.int64), np.arange(n))]
    for _ in range(k):
        cand = []
        for g, R in etats:
            if len(R) == 0:
                continue
            c = A[R].sum(axis=0).astype(np.int64)      # combien de R contiennent x
            c[g] = -1 if haute else n + 1              # ne jamais reprendre un membre
            score = c if haute else -c
            for x in np.argsort(-score)[:8]:
                x = int(x)
                if x in g.tolist():
                    continue
                R2 = R[A[R, x]] if haute else R[~A[R, x]]
                cand.append((len(R2), np.r_[g, x], R2))
        if not cand:
            break
        vus, etats = set(), []
        for taille, g, R in sorted(cand, key=lambda t: -t[0]):
            cle = tuple(sorted(g.tolist()))
            if cle in vus:
                continue
            vus.add(cle)
            etats.append((g, R))
            if len(etats) >= FAISCEAU:
                break
    g, R = etats[0]
    return np.sort(g), len(R)


def mesurer(B, g, haute):
    """compte de la queue demandee pour la grille g sur B."""
    d = B[:, g]
    return int(d.all(axis=1).sum()) if haute else int((~d).all(axis=1).sum())


if __name__ == "__main__":
    import lab

    A = lab.load()
    M = np.asarray(A.mask)
    N = len(M)
    n2 = N // 2
    MTOT = 2 * 2 * len(TAILLES)

    HYP = ("Aucune grille choisie sur une moitie de l'archive n'a, sur l'autre, une QUEUE "
           "qui s'ecarte de sa valeur SRS — ni la queue haute P(les k sortent) ni la queue "
           "basse P(aucun des k ne sort). Le barbeme releve sur l'ecran a deux proprietes "
           "que tout le dossier avait ignorees parce qu'il cherchait a predire les numeros "
           "qui SORTENT : l'option EXTRA n'est pas monotone, un juste payant plus que deux "
           "justes a CHAQUE taille de grille (12 contre 7 a cinq numeros, 12 contre 4 a "
           "dix) ; et a dix numeros ZERO juste paie, 2 en base et 2 en EXTRA. Un gain est "
           "donc convexe AUX DEUX BOUTS. Le §213 a ferme la queue haute ; personne n'avait "
           "mesure l'autre. Le §210 avait bien mesure une grille froide, mais son taux de "
           "sortie MOYEN, c'est-a-dire la seule chose que les marges bornent deja. Une "
           "dependance NEGATIVE — des numeros qui s'evitent — laisse les marges intactes, "
           "ne se voit pas dans la queue haute, et paie sur ce bareme")
    STAT = (f"pour les cinq tailles du bareme (k = 5, 6, 7, 8, 10) et dans les deux sens de "
            f"decoupage, le z binomial exact du compte de queue de la grille choisie sur "
            f"l'autre moitie, soit {MTOT} statistiques. La recherche est un faisceau de "
            f"largeur {FAISCEAU}, non exhaustive et sans pretention de l'etre : l'honnetete "
            "du test ne vient pas de l'optimalite de la recherche mais de la DISJONCTION "
            "des fenetres")
    NUL = ("EXACTE, aucune simulation : les tirages etant independants, le compte de queue "
           "d'une grille FIXE est binomial de parametre P_k = produit (20-j)/(80-j) pour la "
           "queue haute et Q_k = produit (60-j)/(80-j) pour la queue basse")
    VER = (f"conforme si tous les |z| restent sous le seuil de Bonferroni sur {MTOT} ; "
           "QUEUE EXPLOITABLE sinon, en precisant laquelle")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    lo, hi = 0.0, 40.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if erfc(mid / sqrt(2)) > 0.05 / MTOT:
            lo = mid
        else:
            hi = mid
    ZC = 0.5 * (lo + hi)

    say(f"h196 : {N} tirages, moities de {n2} ; {MTOT} statistiques ; seuil {ZC:.3f}")
    say(f"\n   {'k':>3} | {'P(k/k) exacte':>14} | {'P(0/k) exacte':>14} | "
        f"{'attendus haut':>13} | {'attendus bas':>12}")
    for k in TAILLES:
        ph, pb = float(p_haute(k)), float(p_basse(k))
        say(f"   {k:3d} | {ph:14.6e} | {pb:14.6e} | {n2*ph:13.2f} | {n2*pb:12.2f}")

    zs, detail = [], []
    for nom, (a1, b1, a2, b2) in (("H1->H2", (0, n2, n2, N)), ("H2->H1", (n2, N, 0, n2))):
        say(f"\n   === {nom} ===")
        say(f"   {'k':>3} {'queue':>6} | {'grille':>34} | {'choix':>12} | "
            f"{'mesure':>16} | {'z':>7}")
        for k in TAILLES:
            for haute in (True, False):
                g, c1 = faisceau(M[a1:b1], k, haute)
                ob = mesurer(M[a2:b2], g, haute)
                nb = b2 - a2
                pk = float(p_haute(k) if haute else p_basse(k))
                z = (ob - nb * pk) / sqrt(nb * pk * (1 - pk))
                zs.append(z)
                detail.append(f"{nom} k={k} {'haute' if haute else 'basse'} "
                              f"{sorted((g+1).tolist())} {ob}/{nb} z={z:+.2f}")
                say(f"   {k:3d} {'haute' if haute else 'basse':>6} | "
                    f"{str(sorted((g+1).tolist())):>34} | {c1:6d}/{b1-a1:5d} | "
                    f"{ob:6d}/{nb:6d} | {z:+7.2f}")

    zmax = max(zs, key=abs)
    p = float(min(1.0, erfc(abs(zmax) / sqrt(2)) * MTOT))
    quelle = detail[int(np.argmax(np.abs(zs)))]
    verdict = "QUEUE EXPLOITABLE" if abs(zmax) > ZC else "conforme"
    say(f"\n   max |z| = {zmax:+.3f}  ({quelle})")
    say(f"   p (Bonferroni sur {MTOT}) = {p:.4f}   ->   {verdict}")
    TOK["m_extra"] = MTOT - 1
    lab.record(
        TOK, float(abs(zmax)), p=p, verdict=verdict,
        power_at=(f"queue basse a dix numeros : {n2*float(p_basse(10)):.1f} zeros attendus "
                  f"sur {n2} tirages d'ecart-type "
                  f"{sqrt(n2*float(p_basse(10))*(1-float(p_basse(10)))):.1f}, donc le test "
                  f"voit un ecart relatif de "
                  f"{100*ZC*sqrt(n2*float(p_basse(10))*(1-float(p_basse(10))))/(n2*float(p_basse(10))):.1f} "
                  f"%. Queue haute a cinq numeros : {n2*float(p_haute(5)):.1f} attendus "
                  f"d'ecart-type {sqrt(n2*float(p_haute(5))*(1-float(p_haute(5)))):.1f}, "
                  f"soit un ecart relatif de "
                  f"{100*ZC*sqrt(n2*float(p_haute(5))*(1-float(p_haute(5))))/(n2*float(p_haute(5))):.0f} "
                  "%. La queue basse est de loin la plus puissante des deux, parce qu'elle "
                  "est bien plus probable"),
        notes=(f"LES DEUX QUEUES (§217) — le bareme paie aussi pour ZERO. A chaque taille "
               f"de grille l'option EXTRA paie plus pour un juste que pour deux, et a dix "
               f"numeros zero juste paie. Le gain est donc convexe AUX DEUX BOUTS ; le §213 "
               f"a ferme la queue haute, celle-ci etait ouverte. Le §210 avait mesure une "
               f"grille froide mais par son taux MOYEN, que les marges bornent deja. "
               f"{MTOT} statistiques, nulle binomiale EXACTE, faisceau de largeur "
               f"{FAISCEAU} sur une moitie et mesure sur l'autre. max |z| = {zmax:+.3f}. "
               + " ; ".join(detail)))
    say("   consigne.")
