"""h179 — LA PRÉDICTION, ÉCRITE ET NOTÉE : un fichier de prédictions réelles pour des
tirages réels de l'archive, et leur note (RAPPORT §195).

POURQUOI CE FICHIER EXISTE
==========================
Tout le dossier parle de prédiction en `z`, en bornes et en pourcentages. C'est juste, mais
c'est abstrait. La question posée était « prédire les tirages de l'archive » : voici donc
des **prédictions écrites**, tirage par tirage, avec leur note en face.

Rien n'est ajusté sur ce qu'on prédit. Le modèle est celui du §192 — trente et un traits,
neuf témoins plantés passés — ajusté sur les tirages `2 000..43 136` et appliqué en marche
avant aux `27 424` suivants, qu'il n'a jamais vus. Les cinq champs sont prédits selon le
§194 :

    identifiant     `id(t-1) + 1`
    horodatage      `ts(t-1) + 300`, ou `+ 25 500` après le 204e tirage de la nuit
    multiplicateur  le mode de la tranche d'apprentissage
    vingt numéros   les vingt de plus fort score du modèle du §192
    bonus           **post hoc** : sachant les vingt vrais numéros, un rang au hasard
                    parmi vingt. La colonne est marquée comme telle, parce que cette
                    prédiction-là n'est possible qu'APRÈS le tirage et qu'il serait
                    malhonnête de la compter comme les autres.

CE QUE LE FICHIER PRODUIT DOIT MONTRER
======================================
Deux choses opposées, et les deux sont vraies :

  * les trois champs déterministes tombent juste presque à chaque fois ;
  * les vingt numéros tombent juste `5` fois sur `20`, c'est-à-dire exactement ce que
    donnerait un ticket rempli au hasard.

Un lecteur qui ne regarderait que la première ligne du résumé croirait à une réussite. Le
fichier est donc écrit pour qu'on ne puisse pas s'y tromper.
"""

import os
import sys
from math import sqrt

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import h173_predicteur_appris as B                                      # noqa: E402
import h176_borne_elargie as H                                          # noqa: E402

POOL, DRAWN = 80, 20
SORTIE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "prediction_archive.txt")
DETAIL = 40                       # nombre de tirages detailles a la fin du fichier


def say(*a):
    print(*a, flush=True)


if __name__ == "__main__":
    import lab

    A = lab.load()
    N = len(A.ids)
    IDS = np.asarray(A.ids).astype(np.int64)
    TS = np.asarray(A.ts).astype(np.int64)
    NUMS = np.asarray(A.nums).astype(np.int64)
    BONUS = np.asarray(A.bonus).astype(np.int64)
    BOOST = np.asarray(A.boost).astype(np.int64)
    M = np.asarray(A.mask)
    BOR = np.r_[0, np.flatnonzero(np.diff(TS) > 1000) + 1, N]
    coupe = H.CHAUFFE + int((N - H.CHAUFFE) * H.PART)

    say(f"h179 : ajustement sur {H.CHAUFFE}..{coupe}, prediction sur {coupe}..{N}")
    X = H.construire(M, BOR, BONUS)
    w, mu, sd = B.ajuster(X[H.CHAUFFE:coupe].reshape(-1, H.NF),
                          M[H.CHAUFFE:coupe].reshape(-1))
    S = B.scorer(X, w, mu, sd)
    del X
    say("   modele ajuste.")

    # --- le multiplicateur : le mode de la seule tranche d'apprentissage --------------
    vb, cb = np.unique(BOOST[H.CHAUFFE:coupe], return_counts=True)
    mode_boost = int(vb[cb.argmax()])

    # --- les nuits, pour la regle d'horodatage ---------------------------------------
    est_debut = np.zeros(N, bool)
    est_debut[BOR[:-1]] = True

    rng = np.random.default_rng(179)
    nid = nts = nts5 = nbo = nbon = 0
    rec = np.empty(N - coupe, np.int64)
    lignes = []
    for i, t in enumerate(range(coupe, N)):
        top = np.argpartition(-S[t], DRAWN)[:DRAWN]
        pred = np.sort(top + 1)
        vrai = NUMS[t]
        rec[i] = int(M[t][top].sum())

        p_id = int(IDS[t - 1] + 1)
        p_ts = int(TS[t - 1] + (25500 if est_debut[t] else 300))
        p_bon = int(vrai[rng.integers(DRAWN)])          # POST HOC, sachant les vingt

        nid += p_id == IDS[t]
        nts += p_ts == TS[t]
        nts5 += abs(p_ts - TS[t]) <= 5
        nbo += mode_boost == BOOST[t]
        nbon += p_bon == BONUS[t]

        if t >= N - DETAIL:
            lignes.append((t, p_id, IDS[t], p_ts, TS[t], mode_boost, int(BOOST[t]),
                           pred, vrai, rec[i], p_bon, int(BONUS[t])))

    n = N - coupe
    sd1 = B.SD1
    z = (rec.mean() - 5.0) / (sd1 / sqrt(n))

    with open(SORTIE, "w", encoding="utf-8") as f:
        e = f.write
        e("=" * 78 + "\n")
        e("PREDICTIONS ECRITES POUR DES TIRAGES REELS DE L'ARCHIVE, ET LEUR NOTE\n")
        e("=" * 78 + "\n\n")
        e(f"modele          celui du §192 : {H.NF} traits, neuf temoins plantes passes\n")
        e(f"ajuste sur      les tirages {H.CHAUFFE} a {coupe-1} "
          f"(identifiants {IDS[H.CHAUFFE]} a {IDS[coupe-1]})\n")
        e(f"predit          les tirages {coupe} a {N-1} "
          f"(identifiants {IDS[coupe]} a {IDS[N-1]}), soit {n} tirages\n")
        e("                que l'ajustement n'a JAMAIS vus. Aucun trait ne lit le\n")
        e("                tirage qu'il predit.\n\n")

        e("-" * 78 + "\n")
        e("LE RESULTAT, CHAMP PAR CHAMP\n")
        e("-" * 78 + "\n\n")
        e(f"{'champ':<24}{'juste':>10}{'sur':>9}{'taux':>12}   reference aveugle\n")
        e(f"{'identifiant':<24}{nid:>10}{n:>9}{100*nid/n:>11.4f} %   —\n")
        e(f"{'horodatage (exact)':<24}{nts:>10}{n:>9}{100*nts/n:>11.4f} %   —\n")
        e(f"{'horodatage (+/- 5 s)':<24}{nts5:>10}{n:>9}{100*nts5/n:>11.4f} %   —\n")
        e(f"{'multiplicateur':<24}{nbo:>10}{n:>9}{100*nbo/n:>11.4f} %   "
          f"1,250 % (grille 1/80)\n")
        e(f"{'bonus (POST HOC)':<24}{nbon:>10}{n:>9}{100*nbon/n:>11.4f} %   "
          f"1,250 % — mais voir ci-dessous\n")
        e("\n")
        e(f"{'les vingt numeros':<24}{'recouvrement moyen':>19}"
          f"{rec.mean():>12.5f}   sur 20\n")
        e(f"{'':<24}{'attendu au hasard':>19}{5.0:>12.5f}   "
          f"(hypergeometrique EXACT)\n")
        e(f"{'':<24}{'ecart normalise':>19}{z:>+12.3f}\n")
        e(f"{'':<24}{'meilleur tirage':>19}{rec.max():>12d}   sur 20\n")
        e(f"{'':<24}{'pire tirage':>19}{rec.min():>12d}   sur 20\n\n")

        e("-" * 78 + "\n")
        e("COMMENT LIRE CE TABLEAU — ET COMMENT NE PAS LE LIRE\n")
        e("-" * 78 + "\n\n")
        e("Les trois premieres lignes sont du CALENDRIER. L'identifiant s'incremente,\n")
        e("l'horaire avance de cinq minutes, la nuit se coupe a heure fixe. Les\n")
        e("prevoir n'a aucune valeur et ne dit rien du generateur.\n\n")
        e("La ligne du multiplicateur est une LOI DE PAIEMENT, pas une prediction :\n")
        e("elle se prevoit a sa frequence et rien ne fait mieux — ni memoire (§189),\n")
        e("ni quota de nuit (§187), ni modele ajuste (§190).\n\n")
        e("La ligne du bonus est POST HOC et ne compte pas comme les autres. Elle\n")
        e("suppose les vingt numeros DEJA CONNUS, c'est-a-dire d'etre apres le tirage.\n")
        e("Le theoreme du §175 — le bonus est toujours l'un des vingt, 70 560 fois sur\n")
        e("70 560 — fait passer sa prediction de 1/80 a 1/20, un facteur quatre exact.\n")
        e("Mais un facteur quatre sur un champ qu'on ne peut prevoir qu'apres coup ne\n")
        e("vaut rien non plus.\n\n")
        e("LA SEULE LIGNE QUI AURAIT DE LA VALEUR EST LA DERNIERE, ET ELLE DIT NON.\n")
        e(f"Vingt numeros predits, {rec.mean():.5f} justes en moyenne au lieu de 5,00000.\n")
        e("C'est le resultat d'un ticket rempli au hasard. La borne du §192 le chiffre :\n")
        e("au plus +0,0191 numero par tirage a 95 % de confiance, soit 0,38 %.\n\n")

        e("-" * 78 + "\n")
        e(f"LES {DETAIL} DERNIERS TIRAGES DE L'ARCHIVE, EN DETAIL\n")
        e("-" * 78 + "\n\n")
        for (t, pid, vid, pts, vts, pb, vbo, pn, vn, r, pbn, vbn) in lignes:
            e(f"tirage {vid}   ({r} numeros justes sur 20)\n")
            e(f"   identifiant    predit {pid}   reel {vid}   "
              f"{'juste' if pid == vid else 'FAUX'}\n")
            e(f"   horodatage     predit {pts}   reel {vts}   "
              f"{'juste' if pts == vts else 'ecart de %+d s' % (vts - pts)}\n")
            e(f"   multiplicateur predit {pb:2d}          reel {vbo:2d}          "
              f"{'juste' if pb == vbo else 'FAUX'}\n")
            e(f"   bonus          predit {pbn:2d}          reel {vbn:2d}          "
              f"{'juste' if pbn == vbn else 'FAUX'}   (post hoc)\n")
            e(f"   predits  {' '.join(f'{x:2d}' for x in pn)}\n")
            e(f"   sortis   {' '.join(f'{x:2d}' for x in vn)}\n")
            justes = sorted(set(pn.tolist()) & set(vn.tolist()))
            e(f"   justes   {' '.join(f'{x:2d}' for x in justes) if justes else '(aucun)'}"
              f"\n\n")

        e("-" * 78 + "\n")
        e("EN UNE PHRASE\n")
        e("-" * 78 + "\n\n")
        e("Quatre champs sur cinq se predisent, et aucun des quatre n'a de valeur.\n")
        e("Le seul qui aurait de la valeur — les vingt numeros — ne cede rien, et\n")
        e("c'est mesure sur 27 424 tirages que le modele n'avait jamais vus.\n")

    say(f"\n   ecrit : {SORTIE}")
    say(f"   identifiant    {100*nid/n:8.4f} %")
    say(f"   horodatage     {100*nts/n:8.4f} % (exact), {100*nts5/n:.4f} % a 5 s")
    say(f"   multiplicateur {100*nbo/n:8.4f} %")
    say(f"   bonus post hoc {100*nbon/n:8.4f} %")
    say(f"   vingt numeros  {rec.mean():8.5f} sur 20   (z = {z:+.3f})")
