"""h189 — LE HAUT DU CLASSEMENT : et si le modèle n'avait raison que sur ses premiers
choix ? (RAPPORT §208).

LA FAUTE DE MÉTHODE QUE CE FICHIER CORRIGE
==========================================
Les §188 et §192 mesurent un prédicteur par le **recouvrement du top-20** : on prend les
vingt numéros de plus fort score et l'on compte les justes. C'est une moyenne sur les
quatre-vingts numéros, et elle a un défaut grave qu'aucune section n'avait relevé :

> Un modèle peut n'avoir **aucune** information en moyenne et en avoir sur ses **tout
> premiers choix**. Le top-20 dilue cette information dans dix-neuf autres décisions et la
> détruit.

Prendre les vingt premiers, c'est aussi la mauvaise question du point de vue du joueur :
on ne mise pas sur vingt numéros, on mise sur deux, trois ou cinq. Une avance qui
n'existerait que sur le premier choix serait **économiquement réelle et statistiquement
invisible** au §192.

CE QUI EST MESURÉ ICI
=====================
Le même modèle qu'au §192 — trente et un traits causaux, ajusté sur les `60 %` premiers
tirages — mais évalué autrement sur les `40 %` derniers :

  * le taux de réussite du **top-`k`** pour `k = 1, 2, 3, 5, 10, 20` ;
  * le taux du **bas** du classement pour les mêmes `k` — éviter un numéro est aussi une
    prédiction ;
  * la **courbe de calibration** entière : les `2 193 920` couples (tirage, numéro) de la
    tranche de mesure, rangés par score et découpés en vingt tranches d'effectif égal, avec
    le taux de sortie réel de chacune.

LA NULLE EST EXACTE
===================
Sous SRS, `k` numéros choisis sans regarder contiennent un nombre de gagnants
**hypergéométrique** : moyenne `k/4` et variance `k·(1/4)·(3/4)·(80−k)/79`. Les tirages
étant indépendants, l'écart-type du total sur `n` tirages vaut
`√(n·k·(3/16)·(80−k)/79)`. Aucune simulation.

Pour la courbe de calibration, chaque tranche a la même nulle avec `k` = son effectif par
tirage.

CE QUE ÇA CHANGE SI ÇA MARCHE
=============================
Un top-1 à `27 %` au lieu de `25 %` serait une prédiction — partielle, mais réelle, et
mesurée hors échantillon. C'est exactement ce que le recouvrement du top-20 ne peut pas
voir.
"""

import json
import os
import sys
from math import erfc, sqrt

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import h173_predicteur_appris as P                                     # noqa: E402
import h176_borne_elargie as E                                         # noqa: E402

POOL, DRAWN = 80, 20
EXP_ID = "h189.haut_du_classement"
FJETON = "/tmp/h189_jeton.json"
KS = (1, 2, 3, 5, 10, 20)
NTRANCHE = 20


def say(*a):
    print(*a, flush=True)


def sd_hyper(n, k):
    """ecart-type EXACT du nombre de gagnants parmi k numeros, sur n tirages."""
    return sqrt(n * k * (DRAWN / POOL) * ((POOL - DRAWN) / POOL)
                * ((POOL - k) / (POOL - 1)))


def evaluer(M, S, deb, fin):
    """taux du top-k, du bas-k, et courbe de calibration, sur [deb, fin)."""
    n = fin - deb
    Sm = S[deb:fin]
    Mm = M[deb:fin].astype(np.int64)
    ordre = np.argsort(-Sm, axis=1, kind="stable")
    lignes = np.arange(n)[:, None]
    haut, bas = {}, {}
    for k in KS:
        haut[k] = int(Mm[lignes, ordre[:, :k]].sum())
        bas[k] = int(Mm[lignes, ordre[:, -k:]].sum())
    # calibration : tout le nuage (tirage, numero) range par score
    plat_s = Sm.ravel()
    plat_y = Mm.ravel()
    o = np.argsort(plat_s)
    tail = len(o) // NTRANCHE
    cal = []
    for t in range(NTRANCHE):
        idx = o[t * tail:(t + 1) * tail]
        cal.append((float(plat_s[idx].mean()), float(plat_y[idx].mean()), len(idx)))
    return haut, bas, cal


if __name__ == "__main__":
    import lab

    A = lab.load()
    M = np.asarray(A.mask)
    TS = np.asarray(A.ts).astype(np.int64)
    N = len(M)
    BOR = np.r_[0, np.flatnonzero(np.diff(TS) > 1000) + 1, N]
    BONUS = np.asarray(A.bonus).astype(np.int64)
    coupe = P.CHAUFFE + int((N - P.CHAUFFE) * P.PART)
    nmes = N - coupe

    HYP = ("Le modele a 31 traits du §192 n'a pas davantage d'information sur ses PREMIERS "
           "choix que sur l'ensemble. Le §192 le mesure au recouvrement du top-20, "
           "c'est-a-dire par une moyenne sur les quatre-vingts numeros ; or un modele peut "
           "n'avoir aucune information en moyenne et en avoir sur son tout premier choix, "
           "et le top-20 dilue alors cette information dans dix-neuf autres decisions et la "
           "detruit. C'est aussi la mauvaise question du point de vue du joueur, qui ne "
           "mise pas sur vingt numeros mais sur deux ou trois. On mesure donc le taux de "
           "reussite du top-k et du bas-k pour k = 1, 2, 3, 5, 10, 20, et la courbe de "
           f"calibration entiere sur les {nmes * POOL} couples (tirage, numero) de la "
           "tranche de mesure")
    STAT = (f"taux de sortie des k numeros de plus fort score, sur les {nmes} tirages hors "
            "echantillon, pour chaque k ; z = (observe - k/4 * n) / racine(n k (3/16) "
            "(80-k)/79). Idem pour les k plus faibles. Et le taux de sortie de chacune des "
            f"{NTRANCHE} tranches de score d'effectif egal")
    NUL = ("EXACTE, aucune simulation : sous SRS, k numeros choisis sans regarder "
           "contiennent un nombre de gagnants hypergeometrique de moyenne k/4 et de "
           "variance k (1/4)(3/4)(80-k)/79 ; les tirages etant independants, l'ecart-type "
           "du total suit. Ajustement sur les 60 % premiers tirages, mesure sur les 40 % "
           "derniers, DISJOINTS")
    VER = (f"conforme si tous les |z| restent sous le seuil de Bonferroni pour "
           f"{2*len(KS) + NTRANCHE} statistiques ; PREDICTION PARTIELLE si un top-k le "
           "depasse par le haut")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    MTOT = 2 * len(KS) + NTRANCHE
    lo, hi = 0.0, 40.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if erfc(mid / sqrt(2)) > 0.05 / MTOT:
            lo = mid
        else:
            hi = mid
    ZC = 0.5 * (lo + hi)

    say(f"h189 : ajustement {P.CHAUFFE}..{coupe}, mesure {coupe}..{N} ({nmes} tirages)")
    say(f"   {MTOT} statistiques ; seuil de Bonferroni |z| > {ZC:.3f}")

    X = E.construire(M, BOR, BONUS)
    w, mu, sd = P.ajuster(X[P.CHAUFFE:coupe].reshape(-1, E.NF),
                          M[P.CHAUFFE:coupe].reshape(-1))
    S = P.scorer(X, w, mu, sd)
    del X
    haut, bas, cal = evaluer(M, S, coupe, N)

    say(f"\n   {'k':>4} | {'HAUT du classement':>28} | {'z':>7} | "
        f"{'BAS du classement':>26} | {'z':>7}")
    zmax, arg = 0.0, None
    for k in KS:
        att = nmes * k * DRAWN / POOL
        s = sd_hyper(nmes, k)
        zh = (haut[k] - att) / s
        zb = (bas[k] - att) / s
        say(f"   {k:4d} | {haut[k]:8d} / {nmes*k:8d} = {100*haut[k]/(nmes*k):6.3f} % "
            f"| {zh:+7.2f} | {100*bas[k]/(nmes*k):6.3f} % ({bas[k]:7d}) | {zb:+7.2f}")
        for z in (zh, zb):
            if abs(z) > abs(zmax):
                zmax, arg = z, f"k={k} {'haut' if z == zh else 'bas'}"

    say(f"\n   COURBE DE CALIBRATION ({NTRANCHE} tranches d'effectif egal) :")
    say(f"   {'tranche':>8} | {'score moyen':>12} | {'taux reel':>10} | {'z':>7}")
    for t, (sm, taux, cnt) in enumerate(cal):
        # chaque tranche melange des tirages : la nulle par tirage est hypergeometrique,
        # mais sur un effectif si grand la binomiale de parametre 1/4 est une borne sure
        z = (taux - 0.25) * sqrt(cnt) / sqrt(0.25 * 0.75)
        if t % 1 == 0:
            say(f"   {t:8d} | {sm:12.4f} | {100*taux:9.3f} % | {z:+7.2f}")
        if abs(z) > abs(zmax):
            zmax, arg = z, f"tranche {t}"

    p = float(min(1.0, erfc(abs(zmax) / sqrt(2)) * MTOT))
    verdict = ("PREDICTION PARTIELLE" if (zmax > ZC and arg and "haut" in str(arg))
               else ("ECART" if abs(zmax) > ZC else "conforme"))
    say(f"\n   max |z| = {zmax:+.3f} ({arg})   seuil {ZC:.3f}")
    say(f"   p (Bonferroni sur {MTOT}) = {p:.4f}   ->   {verdict}")
    TOK["m_extra"] = MTOT - 1
    lab.record(
        TOK, float(abs(zmax)), p=p, verdict=verdict,
        power_at=(f"sur {nmes} tirages, l'ecart-type du taux du top-1 vaut "
                  f"{100*sd_hyper(nmes,1)/nmes:.3f} point de pourcentage : un top-1 a "
                  f"27 % au lieu de 25 % sortirait a z = "
                  f"{(0.02*nmes)/sd_hyper(nmes,1):.0f}. Le test voit donc une avance de "
                  f"{100*ZC*sd_hyper(nmes,1)/nmes:.2f} point sur le premier choix — ce que "
                  "le recouvrement du top-20 du §192 ne pouvait pas voir"),
        notes=(f"LE HAUT DU CLASSEMENT (§208) — correction d'une faute de methode : les "
               f"§188 et §192 mesurent au recouvrement du TOP-20, une moyenne sur les "
               f"quatre-vingts numeros, qui detruit toute information concentree sur les "
               f"premiers choix. Ici, taux du top-k et du bas-k pour k = 1, 2, 3, 5, 10, 20 "
               f"et courbe de calibration en {NTRANCHE} tranches, nulle hypergeometrique "
               f"EXACTE, hors echantillon sur {nmes} tirages. top-1 "
               f"{100*haut[1]/nmes:.3f} %, top-3 {100*haut[3]/(3*nmes):.3f} %, bas-1 "
               f"{100*bas[1]/nmes:.3f} %. max |z| = {zmax:+.3f} ({arg})."))
    say("   consigne.")
