"""h171 — le balayage d'autocorrélation EXACT, numéro par numéro et décalage par décalage
(RAPPORT §186, théorie THEORIE_ETAT §7.29).

POURQUOI CE TEST EXISTE
=======================
Les six détecteurs des §177-§184 cherchent une RELATION entre les classes (`c_i = c_j + c_k`).
Ils supposent donc déjà la forme du générateur. Le §144 balaye bien tous les décalages, mais
sur UN SEUL scalaire par tirage — le contraste de parité — et contre une nulle simulée.

Ici on ne suppose rien du tout. On demande, pour chacun des quatre-vingts numéros `v` et
chacun des décalages `d` :

    « le numéro v revient-il plus (ou moins) souvent d tirages après lui-même
      que le hasard ne le voudrait ? »

C'est la question la plus élémentaire qu'on puisse poser à une archive de loterie, et c'est
aussi la SEULE dont une réponse positive donne immédiatement une règle de pari :
« v est sorti au tirage t-d, donc joue (ou évite) v au tirage t ».

LA NULLE EST EXACTE — ET C'EST UN PETIT THÉORÈME
================================================
Posons `x[t,v] = m[t,v] - 1/4` (le numéro v est sorti ou non, centré : E[m] = 20/80 = 1/4),
et
                     C_v(d) = somme_t  x[t,v] · x[t+d,v] .

Sous SRS 20/80 indépendants d'un tirage à l'autre :

  (i)   E[C_v(d)] = 0 EXACTEMENT, par indépendance des tirages t et t+d.

  (ii)  Var(x_t x_{t+d}) = E[x²]² = (3/16)², car les deux facteurs sont indépendants et
        centrés, et Var(m) = (1/4)(3/4) = 3/16.

  (iii) LES TERMES SONT DEUX À DEUX NON CORRÉLÉS. Deux termes ne partagent un tirage que si
        leurs indices diffèrent de d, et alors

            Cov(x_t x_{t+d}, x_{t+d} x_{t+2d}) = E[x_t · x²_{t+d} · x_{t+2d}]
                                               = E[x_t] · E[x²] · E[x_{t+2d}] = 0 ,

        puisque `x` est centré. La covariance s'annule IDENTIQUEMENT. C'est ce point — et
        lui seul — qui rend la variance exacte sans une seule simulation :

            Var(C_v(d)) = (n - d) · (3/16)²        ,        z_v(d) = C_v(d) / ((3/16)·√(n-d)).

  (iv)  La somme sur les quatre-vingts numéros redonne le RECOUVREMENT :
            S(d) = somme_v C_v(d) = somme_t (|A_t ∩ A_{t+d}| - 5) ,
        dont la variance exacte est (n-d)·Var hypergéométrique = (n-d)·2,8481 — la même
        nulle exacte qu'au §185, obtenue par un autre chemin. Les deux familles se
        contrôlent l'une l'autre.

QUATRE FAMILLES
===============
  A  numéro par numéro, décalage d'INDICE de tirage,  d = 1..n/2      (80 × 35 280)
  B  somme sur les numéros, décalage d'indice                          (35 280)
  C  numéro par numéro, décalage d'HORLOGE (pas de 300 s), avec masque des trous
  D  somme sur les numéros, décalage d'horloge

A et C ne coïncident pas : l'archive a 343 coupures de nuit de 25 500 s. Un générateur
réensemencé sur l'heure laisserait une trace en horloge et aucune en indice ; un générateur
qui coule sans interruption fait l'inverse.

LE SEUIL EST DÉCLARÉ AVANT
==========================
`M` statistiques au total, seuil de Bonferroni bilatéral à 5 % : `|z| > Φ⁻¹(1 - 0,025/M)`.
Toute case au-dessus est CHASSÉE (h171b) : on la fixe, on la rejoue sur une moitié
disjointe, et si elle survit on en fait un pari mesuré.
"""

import json
import os
import sys
from math import erfc, sqrt

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POOL, DRAWN = 80, 20
EXP_ID = "h171.autocorrelation_exacte"
FJETON = "/tmp/h171_jeton.json"
SDX = 3.0 / 16.0                      # ecart-type de x = m - 1/4, exact
VARX = float(DRAWN * (DRAWN / POOL) * ((POOL - DRAWN) / POOL)
             * ((POOL - DRAWN) / (POOL - 1)))     # 2,8481 : variance du recouvrement


def say(*a):
    print(*a, flush=True)


def zscore_normal_quantile(m):
    """seuil bilateral de Bonferroni pour m statistiques, par bissection sur erfc."""
    cible = 0.05 / m
    lo, hi = 0.0, 40.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if erfc(mid / sqrt(2)) > cible:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def autocorr_masquee(x, msk, nfft):
    """(numerateur, compte) des produits x[t]·x[t+d] sur les positions presentes.

    `x` est deja centre et MIS A ZERO hors masque. On renvoie, pour tout d >= 0,
    somme_t x[t]x[t+d]  et  #{t : msk[t] et msk[t+d]}.
    """
    F = np.fft.rfft(x, n=nfft)
    num = np.fft.irfft(F * np.conjugate(F), n=nfft)
    G = np.fft.rfft(msk, n=nfft)
    cnt = np.fft.irfft(G * np.conjugate(G), n=nfft)
    return num, np.rint(cnt)


def famille(M, dmax, nom, msk=None, taille=None):
    """Renvoie (zmax_par_numero, argmax, z_somme, argmax_somme) pour une famille.

    `M` : (T,80) float, deja centre et annule hors masque.
    `msk` : (T,) float 0/1 ; None => tout present.
    """
    T = len(M)
    nfft = 1 << (int(np.ceil(np.log2(2 * T))))
    if msk is None:
        msk = np.ones(T, np.float64)
    _, cnt = autocorr_masquee(np.zeros(T), msk, nfft)
    cnt = cnt[1:dmax + 1]
    ok = cnt >= 500                                   # decalages assez peuples
    somme = np.zeros(dmax, np.float64)
    zbest = -1.0
    arg = None
    for v in range(POOL):
        num, _ = autocorr_masquee(M[:, v], msk, nfft)
        c = num[1:dmax + 1]
        somme += c
        z = np.where(ok, c / np.maximum(SDX * np.sqrt(np.maximum(cnt, 1)), 1e-300), 0.0)
        j = int(np.argmax(np.abs(z)))
        if abs(z[j]) > zbest:
            zbest, arg = abs(z[j]), (v, j + 1, float(z[j]), int(cnt[j]))
    zs = np.where(ok, somme / np.maximum(np.sqrt(np.maximum(cnt, 1) * VARX), 1e-300), 0.0)
    js = int(np.argmax(np.abs(zs)))
    nA = int(ok.sum()) * POOL
    nB = int(ok.sum())
    say(f"   {nom} : {nA} cases (numero x decalage) + {nB} (somme)")
    say(f"      max |z| numero  : {arg[2]:+.3f}  au numero {arg[0]+1}, decalage {arg[1]} "
        f"({arg[3]} paires)")
    say(f"      max |z| somme   : {zs[js]:+.3f}  au decalage {js+1} ({int(cnt[js])} paires)")
    return arg, (js + 1, float(zs[js]), int(cnt[js])), nA, nB


def zs_famille(M, dmax, msk=None):
    """toutes les valeurs z_v(d), sans max : pour l'autotest."""
    T = len(M)
    nfft = 1 << (int(np.ceil(np.log2(2 * T))))
    if msk is None:
        msk = np.ones(T, np.float64)
    _, cnt = autocorr_masquee(np.zeros(T), msk, nfft)
    cnt = cnt[1:dmax + 1]
    Z = np.zeros((POOL, dmax), np.float64)
    for v in range(POOL):
        num, _ = autocorr_masquee(M[:, v], msk, nfft)
        Z[v] = num[1:dmax + 1] / (SDX * np.sqrt(np.maximum(cnt, 1)))
    return Z, cnt


def _srs(n, rng):
    out = np.zeros((n, POOL), bool)
    idx = np.argsort(rng.random((n, POOL)), axis=1)[:, :DRAWN]
    np.put_along_axis(out, idx, True, axis=1)
    return out


def _plante_repetition(n, rng, v0, d0, eps):
    """SRS, puis on force le numero v0 a se repeter au decalage d0 avec un exces eps."""
    m = _srs(n, rng)
    for t in range(d0, n):
        if m[t - d0, v0] and rng.random() < eps and not m[t, v0]:
            # on echange v0 avec un numero sorti tire au hasard : le tirage reste 20/80
            sortis = np.flatnonzero(m[t])
            m[t, sortis[rng.integers(len(sortis))]] = False
            m[t, v0] = True
    return m


def selftest():
    say("h171 --autotest : donnees SYNTHETIQUES uniquement, aucune archive lue")
    rng = np.random.default_rng(171)
    n, dmax = 20000, 300
    Z, cnt = zs_famille(_srs(n, rng).astype(np.float64) - 0.25, dmax)
    say(f"   SRS {n} tirages, {POOL}x{dmax} cases : moyenne des z {Z.mean():+.4f}, "
        f"ecart-type {Z.std():.4f}   (attendu 0 et 1 EXACTEMENT)")
    ok1 = abs(Z.mean()) < 0.03 and abs(Z.std() - 1.0) < 0.03
    say(f"   -> nulle exacte {'VERIFIEE' if ok1 else 'FAUSSE'}")

    ok2 = True
    say(f"{'v0':>4} {'d0':>5} {'eps':>7} | {'z plante':>9} | {'z max ailleurs':>15}")
    # eps = exces conditionnel : P(v0 en t | v0 en t-d0) passe de 1/4 a 1/4 + eps*3/4,
    # ce qui donne z attendu ~ eps*0,75*0,25*n / ((3/16) racine(n)) = eps*racine(n)
    for v0, d0, eps in ((37, 5, 0.06), (12, 97, 0.08), (63, 1, 0.05)):
        m = _plante_repetition(n, np.random.default_rng(1000 + d0), v0, d0, eps)
        Z, _ = zs_famille(m.astype(np.float64) - 0.25, dmax)
        zp = Z[v0, d0 - 1]
        A = Z.copy()
        A[v0, d0 - 1] = 0.0
        say(f"{v0:4d} {d0:5d} {eps:7.3f} | {zp:+9.2f} | {np.abs(A).max():15.2f}")
        ok2 &= zp > 6.0 and zp > np.abs(A).max()
    say(f"   -> detection {'OK' if ok2 else 'ECHEC'}")
    return ok1 and ok2


if __name__ == "__main__":
    if "--autotest" in sys.argv:
        sys.exit(0 if selftest() else 1)

    import lab

    A = lab.load()
    M = np.asarray(A.mask)
    TS = np.asarray(A.ts).astype(np.int64)
    n = len(M)
    dmax_i = n // 2

    # --- famille horloge : on pose les tirages sur la grille de 300 s ------------------
    slot = np.rint((TS - TS[0]) / 300.0).astype(np.int64)
    assert len(np.unique(slot)) == n, "collision de creneau"
    Tm = int(slot[-1]) + 1
    dmax_h = Tm // 2

    mA = 0
    # comptes declares AVANT de regarder : on les calcule sans toucher aux valeurs
    for d, T in ((dmax_i, n), (dmax_h, Tm)):
        pass
    # nombre exact de cases : calcule apres coup dans famille(), declare ici en borne
    MTOT = POOL * (dmax_i + dmax_h) + (dmax_i + dmax_h)
    ZC = zscore_normal_quantile(MTOT)

    HYP = ("Aucune case du balayage d'autocorrelation exact ne depasse le seuil de "
           f"Bonferroni : pour tout numero v de 1 a 80 et tout decalage d, la statistique "
           "C_v(d) = somme_t (m[t,v]-1/4)(m[t+d,v]-1/4), de moyenne NULLE et de variance "
           "EXACTE (n-d)(3/16)^2 sous SRS, reste sous |z| = "
           f"{ZC:.2f}. Le balayage porte sur le decalage d'INDICE de tirage et sur le "
           "decalage d'HORLOGE (grille de 300 s, trous masques), et sur la somme des "
           "quatre-vingts numeros, qui redonne le recouvrement de variance exacte 2,8481. "
           "C'est le test le plus elementaire qu'on puisse poser a une archive de loterie et "
           "le seul dont une reponse positive donne immediatement une regle de pari")
    STAT = ("D = nombre de cases |z| > Zc, et max |z| par famille. z_v(d) = C_v(d) / "
            "((3/16) racine(n_d)) pour les familles par numero ; z_S(d) = somme_v C_v(d) / "
            "racine(n_d * 2,8481) pour les familles de somme. n_d = nombre de paires "
            "reellement presentes (masque des trous de nuit en horloge). Decalages retenus : "
            "n_d >= 500")
    NUL = ("EXACTE, aucune simulation. Sous SRS 20/80 independants : E[C_v(d)] = 0 par "
           "independance ; Var(x_t x_{t+d}) = (3/16)^2 ; et la covariance de deux termes "
           "partageant un tirage vaut E[x_t] E[x^2] E[x_{t+2d}] = 0 puisque x est centre — "
           "les termes sont donc deux a deux NON CORRELES et la variance est (n_d)(3/16)^2 "
           "exactement. Pour la somme, Var = n_d * 20*(20/80)*(60/80)*(60/79)")
    VER = (f"conforme si D = 0 ; ECART si D >= 1, auquel cas la case est FIXEE et chassee "
           "sur une moitie disjointe (h171b)")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h171 : {n} tirages, grille d'horloge {Tm} creneaux ({100*n/Tm:.1f} % pleins)")
    say(f"   seuil de Bonferroni sur {MTOT} cases : |z| > {ZC:.3f}")

    X = M.astype(np.float64) - 0.25
    argA, argB, nA, nB = famille(X, dmax_i, "A/B  decalage d'indice ")

    Y = np.zeros((Tm, POOL), np.float64)
    Y[slot] = X
    msk = np.zeros(Tm, np.float64)
    msk[slot] = 1.0
    argC, argD, nC, nD = famille(Y, dmax_h, "C/D  decalage d'horloge", msk=msk)

    zmax = max(abs(argA[2]), abs(argB[1]), abs(argC[2]), abs(argD[1]))
    D = sum(1 for z in (argA[2], argB[1], argC[2], argD[1]) if abs(z) > ZC)
    p = float(min(1.0, erfc(zmax / sqrt(2)) * MTOT))
    say(f"\n   max |z| toutes familles : {zmax:.3f}   seuil {ZC:.3f}")
    say(f"   p (Bonferroni sur {MTOT}) = {p:.4f}")
    say(f"   {'ECART' if D else 'conforme'}")
    TOK["m_extra"] = MTOT - 1
    lab.record(
        TOK, float(zmax), p=p, verdict="ECART" if D else "conforme",
        power_at=(f"chaque case d'indice porte jusqu'a {n-1} paires : un biais de repetition "
                  f"de 1 % en valeur relative (P(v|v a d) = 0,2525 au lieu de 0,25) donnerait "
                  f"z = {0.0025*np.sqrt(n)/SDX:.1f} sur le plus peuple des decalages, donc "
                  f"tres au-dela du seuil {ZC:.2f} ; le balayage voit un biais relatif de "
                  f"{100*ZC*SDX/np.sqrt(n)/0.25:.2f} % au decalage 1"),
        notes=(f"BALAYAGE D'AUTOCORRELATION EXACT (§186) : {MTOT} cases, nulle EXACTE sans "
               "une simulation grace a l'annulation identique de la covariance des termes "
               "partageant un tirage (§7.29 (iii)). Familles A/B decalage d'indice "
               f"(d <= {dmax_i}), C/D decalage d'horloge (d <= {dmax_h}, {Tm} creneaux de "
               f"300 s dont {n} pleins). max |z| : A {argA[2]:+.3f} (numero {argA[0]+1}, "
               f"d = {argA[1]}), B {argB[1]:+.3f} (d = {argB[0]}), C {argC[2]:+.3f} "
               f"(numero {argC[0]+1}, d = {argC[1]}), D {argD[1]:+.3f} (d = {argD[0]}). "
               f"D = {D} case(s) au-dessus du seuil {ZC:.3f}."))
    say("   consigne.")
