"""h179 — LE SECOND FLUX MINCE : le multiplicateur, et une nulle exacte sans une seule
simulation (RAPPORT §198).

L'ARCHIVE EN A DEUX, PAS UN
==========================
Le §197 traite le bonus comme un flux mince : son rang fixe la classe d'un mot identifié à
quatre valeurs sur quatre-vingts. Le multiplicateur en est un second, et il est **encore
plus net** par endroits.

Le §106 a établi que la loi du multiplicateur est portée par la grille `1/80` en six
secteurs de tailles `(41, 19, 12, 4, 2, 2)`, et par aucune grille strictement plus
grossière. La valeur publiée est donc `m = f(c)` où `c` est la classe d'**un mot précis** —
le `(N+2)`-ième du tirage, immédiatement après celui du bonus — et `f` une partition de
`Z/80` en six blocs de ces tailles.

> Quand le multiplicateur prend l'une de ses deux valeurs les plus rares, il fixe la classe
> de ce mot à **deux valeurs sur quatre-vingts** : `5,32` bits sur un mot identifié, contre
> `4,32` pour le bonus et `2,70` pour les numéros.

CE QU'ON PEUT TESTER SANS CONNAÎTRE `f`
=======================================
La partition `f` est inconnue : on sait qu'il y a un bloc de `41` classes, un de `19`, et
ainsi de suite, mais pas lesquelles. Toute statistique qui **dépend** de `f` est donc hors
d'atteinte — l'énergie additive, notamment, puisqu'elle a besoin des classes elles-mêmes.

Reste ce qui est **invariant par renommage des blocs** : l'autocorrélation de la suite des
valeurs. Si le mot du multiplicateur portait une trace — une période, un cycle de
réamorçage, une réutilisation de flux — elle apparaîtrait dans la suite `(m_t)` quelle que
soit `f`.

LA NULLE EST EXACTE, ET SANS UNE SEULE SIMULATION
=================================================
C'est le point qui rend ce test différent du §189, où l'autocorrélation du boost avait dû
être calibrée par permutation et seulement jusqu'au décalage `100`.

Le §106 donne les probabilités **théoriques exactes** `p_j = 41/80, 19/80, 12/80, 4/80,
2/80, 2/80`. On peut donc centrer sur la valeur **vraie** et non sur une moyenne estimée,
et le théorème du §7.29 s'applique tel quel :

    x_j[t] = 1(m_t = j) − p_j ,     C_j(d) = Σ_t x_j[t]·x_j[t+d] ,

    E[C_j(d)] = 0        et        Var(C_j(d)) = n_d · (p_j(1−p_j))²        exactement,

la covariance des termes partageant un tirage s'annulant identiquement parce que `x` est
centré sur la vraie valeur. **Centrer sur la moyenne empirique détruirait l'exactitude** —
c'est pourquoi le §189 avait besoin de permutations et pas ce fichier.

Six valeurs × `35 280` décalages = `211 680` cases, six transformées de Fourier, aucune
simulation. Et le balayage va à `35 280` là où le §189 s'arrêtait à `100`.
"""

import json
import os
import sys
from math import erfc, sqrt

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POOL, DRAWN = 80, 20
EXP_ID = "h179.flux_boost"
FJETON = "/tmp/h179_jeton.json"
SECTEURS = (41, 19, 12, 4, 2, 2)          # §106, grille 1/80, ordre des valeurs croissantes


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


def autocorr_exacte(lab, p, dmax):
    """(zmax, argmax, tous les z par valeur) — nulle EXACTE, centrage sur le p THEORIQUE."""
    N = len(lab)
    nfft = 1 << int(np.ceil(np.log2(2 * N)))
    cnt = np.arange(N - 1, N - dmax - 1, -1).astype(np.float64)
    zmax, arg = -1.0, None
    pics = []
    for j, pj in enumerate(p):
        x = (lab == j).astype(np.float64) - pj
        F = np.fft.rfft(x, n=nfft)
        C = np.fft.irfft(F * np.conjugate(F), n=nfft)[1:dmax + 1]
        z = C / (pj * (1.0 - pj) * np.sqrt(cnt))
        k = int(np.argmax(np.abs(z)))
        pics.append((j, k + 1, float(z[k])))
        if abs(z[k]) > zmax:
            zmax, arg = abs(z[k]), (j, k + 1, float(z[k]))
    return zmax, arg, pics


def selftest():
    say("h179 --autotest : donnees synthetiques uniquement, aucune archive lue")
    p = np.array(SECTEURS, np.float64) / POOL
    rng = np.random.default_rng(179)
    n, dmax = 60000, 2000

    lib = rng.choice(len(p), n, p=p)
    zA, argA, _ = autocorr_exacte(lib, p, dmax)
    att = seuil(len(p) * dmax, 0.5)
    say(f"   suite libre : max |z| = {zA:.2f} sur {len(p)*dmax} cases "
        f"(mediane du maximum sous la nulle {att:.2f})")
    ok1 = zA < att + 1.5

    # verification directe de la nulle : moyenne et ecart-type des z, sur les six valeurs
    tous = []
    for j, pj in enumerate(p):
        x = (lib == j).astype(np.float64) - pj
        nfft = 1 << int(np.ceil(np.log2(2 * n)))
        F = np.fft.rfft(x, n=nfft)
        C = np.fft.irfft(F * np.conjugate(F), n=nfft)[1:dmax + 1]
        tous.append(C / (pj * (1 - pj) * np.sqrt(np.arange(n - 1, n - dmax - 1, -1))))
    tous = np.concatenate(tous)
    say(f"   nulle exacte : moyenne des z {tous.mean():+.4f}, ecart-type {tous.std():.4f}"
        f"   (attendus 0 et 1 EXACTEMENT)")
    ok2 = abs(tous.mean()) < 0.03 and abs(tous.std() - 1) < 0.03

    # periode plantee : la valeur revient a l'identique un tirage sur dix, 204 plus tard
    per = lib.copy()
    for t in range(204, n):
        if rng.random() < 0.10:
            per[t] = per[t - 204]
    zB, argB, _ = autocorr_exacte(per, p, dmax)
    say(f"   periode 204 plantee a 10 % : max |z| = {zB:.1f} "
        f"(valeur {argB[0]}, decalage {argB[1]})")
    ok3 = zB > 10 and argB[1] == 204
    say(f"   -> nulle {'EXACTE VERIFIEE' if ok2 else 'FAUSSE'} ; "
        f"suite libre {'OK' if ok1 else 'SUSPECTE'} ; "
        f"periode {'DETECTEE' if ok3 else 'MANQUEE'}")
    return ok1 and ok2 and ok3


if __name__ == "__main__":
    if "--autotest" in sys.argv:
        sys.exit(0 if selftest() else 1)

    import lab

    A = lab.load()
    N = len(A.ids)
    BOOST = np.asarray(A.boost).astype(np.int64)
    VAL = np.unique(BOOST)
    LAB = np.searchsorted(VAL, BOOST)
    ordre = np.argsort(-np.bincount(LAB, minlength=len(VAL)))
    # les secteurs du §106 sont donnes par frequence decroissante : on les apparie ainsi
    P = np.empty(len(VAL))
    for rang, j in enumerate(ordre):
        P[j] = SECTEURS[rang] / POOL
    DMAX = N // 2
    MTOT = len(VAL) * DMAX
    ZC = seuil(MTOT)

    HYP = ("Le SECOND flux mince — celui du multiplicateur — ne porte aucune trace. Le §106 "
           "etablit que la loi du multiplicateur est portee par la grille 1/80 en six "
           "secteurs (41, 19, 12, 4, 2, 2), donc que sa valeur est une fonction "
           "deterministe de la classe d'un mot precis, le (N+2)-ieme du tirage. La "
           "partition n'est pas connue, ce qui interdit l'energie additive ; mais "
           "l'autocorrelation de la suite des valeurs est INVARIANTE par renommage des "
           "blocs et reste donc lisible. On la balaye a tous les decalages jusqu'a "
           f"{DMAX}, la ou le §189 s'arretait a 100, et contre une nulle EXACTE au lieu "
           "d'une permutation")
    STAT = (f"D = nombre de cases |z| > Zc = {ZC:.2f} (Bonferroni bilateral a 5 % sur "
            f"{MTOT}), et le max. z_j(d) = C_j(d) / (p_j(1-p_j) racine(n_d)) avec "
            "C_j(d) = somme_t (1(m_t=j) - p_j)(1(m_(t+d)=j) - p_j), pour les six valeurs "
            f"et les {DMAX} decalages")
    NUL = ("EXACTE, aucune simulation. Le §106 donne les probabilites THEORIQUES exactes "
           "p_j = 41/80, 19/80, 12/80, 4/80, 2/80, 2/80, donc le centrage se fait sur la "
           "vraie valeur et non sur une moyenne estimee. Le theoreme du §7.29 s'applique "
           "alors tel quel : la covariance de deux termes partageant un tirage vaut "
           "E[x]E[x^2]E[x] = 0 puisque x est centre, d'ou Var(C_j(d)) = n_d (p_j(1-p_j))^2 "
           "exactement. Centrer sur la moyenne empirique detruirait l'exactitude — c'est "
           "pourquoi le §189 avait besoin de permutations et pas celui-ci")
    VER = "conforme si D = 0 ; ECART sinon"

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h179 : {N} tirages ; {MTOT} cases ({len(VAL)} valeurs x {DMAX} decalages)")
    say(f"   seuil de Bonferroni : |z| > {ZC:.3f}")
    say(f"   {'valeur':>8} | {'secteur':>8} | {'p theorique':>12} | {'p mesure':>10} "
        f"| {'max |z|':>8} | decalage")
    zmax, arg, pics = autocorr_exacte(LAB, P, DMAX)
    for j, d, z in pics:
        say(f"{int(VAL[j]):9d} | {round(P[j]*POOL):8d} | {P[j]:12.5f} | "
            f"{float((LAB == j).mean()):10.5f} | {z:+8.3f} | {d}")

    D = 0
    for j, d, z in pics:
        D += int(abs(z) > ZC)
    p = float(min(1.0, erfc(zmax / sqrt(2)) * MTOT))
    say(f"\n   max |z| = {arg[2]:+.3f} (valeur {int(VAL[arg[0]])}, decalage {arg[1]})"
        f"   seuil {ZC:.3f}")
    say(f"   p (Bonferroni sur {MTOT}) = {p:.4f}   ->   {'ECART' if D else 'conforme'}")
    TOK["m_extra"] = MTOT - 1
    lab.record(
        TOK, float(zmax), p=p, verdict="ECART" if D else "conforme",
        power_at=("l'autotest plante une periode de 204 tirages a 10 % : le balayage la "
                  "rend a plus de dix ecarts-types ET designe le bon decalage. Sur les "
                  f"{N} tirages, un exces de repetition de 1 % en valeur relative sur la "
                  f"valeur majoritaire donnerait z = "
                  f"{0.01*float(P[ordre[0]])*np.sqrt(N)/(float(P[ordre[0]])*(1-float(P[ordre[0]]))):.0f}"),
        notes=(f"SECOND FLUX MINCE (§198) : le multiplicateur. {MTOT} cases, nulle EXACTE "
               "sans une simulation grace au centrage sur les p THEORIQUES du §106 "
               "(41/80, 19/80, 12/80, 4/80, 2/80, 2/80). Balayage a tous les decalages "
               f"jusqu'a {DMAX}, contre 100 au §189, et sans permutation. max |z| = "
               f"{arg[2]:+.3f} a la valeur {int(VAL[arg[0]])}, decalage {arg[1]}, pour un "
               f"seuil de {ZC:.3f}. D = {D}. L'energie additive reste hors d'atteinte sur "
               "ce flux : elle demanderait de connaitre la partition de Z/80 en six blocs, "
               "que rien ne donne."))
    say("   consigne.")
