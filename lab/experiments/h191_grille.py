"""h191 — LA GRILLE : peut-on choisir cinq numéros qui valent mieux que cinq au hasard ?
(RAPPORT §210).

LA QUESTION, POSÉE COMME UN JOUEUR LA POSE
==========================================
Tout le dossier demande « le générateur a-t-il un défaut ». Ce fichier demande autre
chose, et c'est la seule question qui a une valeur pratique :

> **Existe-t-il un petit ensemble de numéros — cinq, dix, ou moins — qui sorte plus
> souvent que le hasard ?**

On ne mise pas sur vingt numéros. On mise sur une grille de deux à dix. Et un joueur n'a
besoin d'aucune théorie du générateur : il lui suffit que *certains numéros sortent plus*.

TROIS FAMILLES, ET LA TROISIÈME EST LA VRAIE
============================================
  **A  LES MARGES.** Le taux de sortie de chacun des quatre-vingts numéros sur les
     `70 560` tirages. Nulle exacte : sous SRS chaque numéro sort avec probabilité
     `20/80 = 1/4` exactement, donc `z = (compte − N/4)/√(N·3/16)`. C'est la borne
     ultime : si aucun numéro ne dévie, aucune grille fixe ne peut gagner.

  **B  LE CRÉNEAU.** Le taux de sortie de chaque numéro à chaque **position dans la
     nuit** — `204 × 80 = 16 320` cases, `346` observations chacune. Si la machine faisait
     quoi que ce soit de particulier au premier tirage de la nuit, au centième, au dernier,
     cela s'y verrait. Rien dans le dossier ne l'avait mesuré ainsi.

  **C  LA GRILLE HORS ÉCHANTILLON.** La seule qui tranche vraiment. On prend les `k`
     numéros de plus fort taux **sur la première moitié**, et on les joue sur la seconde,
     qu'ils n'ont jamais vue. Pour `k = 1, 2, 3, 5, 10`. C'est exactement ce qu'un joueur
     ferait, et c'est un test honnête parce que le choix et la mesure sont disjoints.

     On mesure aussi la grille **anti-**choisie (les `k` plus faibles), parce qu'éviter
     des numéros est aussi une stratégie.

NULLE EXACTE PARTOUT
====================
Famille A et B : binomiale de paramètre `1/4` exact. Famille C : `k` numéros contiennent
un nombre de gagnants **hypergéométrique**, moyenne `k/4`, variance
`k(1/4)(3/4)(80−k)/79` ; sur `n` tirages indépendants l'écart-type du total suit. Aucune
simulation nulle part.
"""

import json
import os
import sys
from math import erfc, sqrt

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POOL, DRAWN = 80, 20
EXP_ID = "h191.grille"
FJETON = "/tmp/h191_jeton.json"
KS = (1, 2, 3, 5, 10)


def say(*a):
    print(*a, flush=True)


def seuil(m, alpha=0.05):
    lo, hi = 0.0, 40.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if erfc(mid / sqrt(2)) > alpha / m:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def sd_hyper(n, k):
    return sqrt(n * k * (DRAWN / POOL) * ((POOL - DRAWN) / POOL)
                * ((POOL - k) / (POOL - 1)))


if __name__ == "__main__":
    import lab

    A = lab.load()
    M = np.asarray(A.mask)
    TS = np.asarray(A.ts).astype(np.int64)
    N = len(M)
    BOR = np.r_[0, np.flatnonzero(np.diff(TS) > 1000) + 1, N]
    K = len(BOR) - 1
    pos = np.zeros(N, np.int64)
    for k in range(K):
        pos[BOR[k]:BOR[k + 1]] = np.arange(BOR[k + 1] - BOR[k])
    LMAX = int(pos.max()) + 1
    n2 = N // 2

    MTOT = POOL + LMAX * POOL + 2 * len(KS)
    ZC = seuil(MTOT)

    HYP = ("Aucun petit ensemble de numeros ne sort plus souvent que le hasard. Trois "
           "familles : (A) le taux de sortie de chacun des 80 numeros sur les 70 560 "
           "tirages, borne ultime puisque si aucun numero ne devie, aucune grille fixe ne "
           f"peut gagner ; (B) le taux de chaque numero a chaque POSITION DANS LA NUIT, "
           f"{LMAX} x 80 cases, jamais mesure ainsi dans le dossier — si la machine faisait "
           "quoi que ce soit de particulier au premier tirage de la nuit, au centieme ou au "
           "dernier, cela s'y verrait ; (C) la GRILLE HORS ECHANTILLON, la seule qui "
           "tranche : on prend les k numeros de plus fort taux sur la PREMIERE moitie et on "
           "les joue sur la seconde, qu'ils n'ont jamais vue, pour k = 1, 2, 3, 5, 10 — "
           "c'est exactement ce qu'un joueur ferait, et le choix et la mesure sont "
           "disjoints. La grille anti-choisie (les k plus faibles) est mesuree aussi, "
           "eviter des numeros etant aussi une strategie")
    STAT = (f"D = nombre de statistiques dont le |z| depasse Zc = {ZC:.2f} (Bonferroni "
            f"bilateral a 5 % sur {MTOT}). Familles A et B : z = (compte - n/4)/"
            "racine(n 3/16). Famille C : z = (gagnants - n k/4)/racine(n k (3/16)(80-k)/79) "
            f"sur les {N - n2} tirages de la seconde moitie")
    NUL = ("EXACTE partout, aucune simulation. Sous SRS chaque numero sort avec probabilite "
           "20/80 = 1/4 exactement (familles A et B, binomiale) ; et k numeros contiennent "
           "un nombre de gagnants hypergeometrique de moyenne k/4 et de variance "
           "k(1/4)(3/4)(80-k)/79 (famille C)")
    VER = (f"conforme si D = 0 ; GRILLE GAGNANTE si un k de la famille C depasse +{ZC:.2f}")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h191 : {N} tirages, {K} nuits, positions 0..{LMAX-1} ; {MTOT} statistiques")
    say(f"   seuil de Bonferroni |z| > {ZC:.3f}")

    # ---- A : les marges
    cnt = M.sum(axis=0).astype(np.float64)
    zA = (cnt - N / 4) / sqrt(N * 3 / 16)
    o = np.argsort(-zA)
    say(f"\nA  LES MARGES ({POOL} numeros ; ecart-type {sqrt(N*3/16):.1f} sorties, "
        f"soit {100*sqrt(3/(16*N)):.4f} point)")
    say(f"   {'rang':>5} {'numero':>7} {'sorties':>8} {'taux':>9} {'z':>7}")
    for r in list(range(3)) + list(range(POOL - 3, POOL)):
        v = o[r]
        say(f"   {r+1:5d} {v+1:7d} {int(cnt[v]):8d} {100*cnt[v]/N:8.4f} % {zA[v]:+7.2f}")
    say(f"   max |z| = {np.abs(zA).max():.3f}")

    # ---- B : le creneau
    zB = np.zeros((LMAX, POOL))
    for p in range(LMAX):
        sel = pos == p
        np_ = int(sel.sum())
        c = M[sel].sum(axis=0).astype(np.float64)
        zB[p] = (c - np_ / 4) / sqrt(np_ * 3 / 16)
    ip = np.unravel_index(int(np.argmax(np.abs(zB))), zB.shape)
    say(f"\nB  LE CRENEAU ({LMAX} positions x {POOL} numeros = {LMAX*POOL} cases)")
    say(f"   max |z| = {zB[ip]:+.3f} a la position {ip[0]}, numero {ip[1]+1}")
    say(f"   moyenne des z {zB.mean():+.4f}, ecart-type {zB.std():.4f} (attendus 0 et 1)")
    say(f"   position 0 (premier tirage de la nuit) : max |z| "
        f"{np.abs(zB[0]).max():.3f}")

    # ---- C : la grille hors echantillon
    c1 = M[:n2].sum(axis=0)
    ordre = np.argsort(-c1)
    nm = N - n2
    say(f"\nC  LA GRILLE HORS ECHANTILLON (choix sur {n2} tirages, mesure sur {nm})")
    say(f"   {'k':>3} | {'grille CHAUDE':>34} | {'z':>7} | {'grille FROIDE':>20} | {'z':>7}")
    zC = []
    for k in KS:
        hot = ordre[:k]
        cold = ordre[-k:]
        gh = int(M[n2:][:, hot].sum())
        gc = int(M[n2:][:, cold].sum())
        att = nm * k / 4
        s = sd_hyper(nm, k)
        zh, zc = (gh - att) / s, (gc - att) / s
        zC += [zh, zc]
        say(f"   {k:3d} | {gh:8d} / {nm*k:8d} = {100*gh/(nm*k):7.4f} % | {zh:+7.2f} | "
            f"{100*gc/(nm*k):7.4f} % | {zc:+7.2f}")

    tous = np.r_[zA, zB.ravel(), np.array(zC)]
    D = int((np.abs(tous) > ZC).sum())
    j = int(np.argmax(np.abs(tous)))
    zmax = float(tous[j])
    p = float(min(1.0, erfc(abs(zmax) / sqrt(2)) * MTOT))
    gagnante = any(z > ZC for z in zC[::2])
    verdict = "GRILLE GAGNANTE" if gagnante else ("ECART" if D else "conforme")
    say(f"\n   max |z| toutes familles = {zmax:+.3f}   seuil {ZC:.3f}")
    say(f"   p (Bonferroni sur {MTOT}) = {p:.4f}   ->   {verdict}")
    TOK["m_extra"] = MTOT - 1
    lab.record(
        TOK, abs(zmax), p=p, verdict=verdict,
        power_at=(f"famille A : l'ecart-type d'un compte vaut {sqrt(N*3/16):.1f} sorties "
                  f"sur {N}, donc un numero biaise de 1 % en valeur relative sortirait a "
                  f"z = {0.01*N/4/sqrt(N*3/16):.1f} ; le test voit un biais relatif de "
                  f"{100*ZC*sqrt(N*3/16)/(N/4):.2f} %. Famille C : l'ecart-type du taux "
                  f"d'une grille de cinq vaut {100*sd_hyper(nm,5)/(nm*5):.3f} point, donc "
                  "une grille a 26 % au lieu de 25 % serait vue a "
                  f"{0.01*nm*5/sd_hyper(nm,5):.0f} ecarts-types"),
        notes=(f"LA GRILLE (§210) — la question posee comme un joueur la pose : existe-t-il "
               f"cinq numeros qui valent mieux que cinq au hasard ? {MTOT} statistiques, "
               f"nulle EXACTE partout. A : marges des {POOL} numeros, max |z| = "
               f"{np.abs(zA).max():.3f}. B : creneau, {LMAX}x{POOL} cases, max |z| = "
               f"{zB[ip]:+.3f} (position {ip[0]}, numero {ip[1]+1}). C : grille hors "
               f"echantillon, choix sur la premiere moitie et mesure sur la seconde. "
               f"D = {D}."))
    say("   consigne.")
