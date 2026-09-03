"""h200 — LE TRANSFERT DE NUIT : la signature qu'un réamorçage nocturne laisserait
(RAPPORT §221).

L'ARCHIVE A UNE COUPURE, ET ELLE EST ÉNORME
===========================================
Le §1 du harnais le vérifie à chaque exécution : `345` coupures, dont `343` de `25 500`
secondes exactement — **sept heures cinq minutes** d'arrêt entre la fin d'une nuit et le
début de la suivante, `204` tirages plus tard. C'est la seule discontinuité structurelle de
tout le dossier, et c'est le moment où une machine se réamorcerait si elle se réamorçait.

Si elle le fait, sa trace n'est pas au retard `1` mais au retard **`204`** — et pas sur la
diagonale, mais en travers :

> Le numéro `i` au tirage `t` rend-il le numéro `j` plus probable au tirage `t + 204`,
> c'est-à-dire à la **même position de la nuit suivante** ?

Aucun instrument du dossier ne l'atteint. Le §194 balaie tous les retards, y compris ceux
d'une journée, mais seulement pour `i = j`. Le §220 balaie les couples `i ≠ j`, mais
s'arrête au retard `10`. La conjonction — **couples croisés × retards de nuit** — est
vierge.

TROIS FAMILLES
==============
  **A  LA MATRICE AUX RETARDS DE NUIT.** `C_ij(204k)` pour `k = 1 … 10`, soit les `64 000`
     mêmes cases qu'au §220 mais à des retards de une à dix nuits. Nulle **exacte** :
     `p = (1/4)(1/4) = 1/16`.

  **B  LA RÈGLE DE PARI À UNE NUIT.** Le couple le plus fort au retard `204` sur la
     première moitié, joué sur la seconde, énoncé comme au §220 : *« quand `i` sort, joue
     `j` au même créneau demain »*.

  **C  LES PREMIERS TIRAGES DE NUIT.** La sous-suite des `346` premiers tirages de chaque
     nuit — celle qui suivrait immédiatement un réamorçage. On y mesure les `6 400` cases
     de transfert d'une nuit à la suivante, plus le recouvrement moyen entre nuits
     consécutives.

     **Sa puissance est faible et il faut le dire** : `345` paires seulement, donc `21,6`
     attendus par case. C'est la famille la plus ciblée du dossier et la moins puissante ;
     elle exclut un réamorçage grossier, pas un réamorçage fin.
"""

import json
import os
import sys
from math import erfc, sqrt

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import h199_matrice_de_transfert as X                                   # noqa: E402

POOL, DRAWN = 80, 20
EXP_ID = "h200.transfert_de_nuit"
FJETON = "/tmp/h200_jeton.json"
REPS = 200
NUITS = 10
P2 = X.P2


def say(*a):
    print(*a, flush=True)


def zmat_nuit(M, L):
    out = []
    for k in range(1, NUITS + 1):
        d = L * k
        n = len(M) - d
        out.append(((X.transfert(M, d) - n * P2) / sqrt(n * P2 * (1 - P2))).ravel())
    return np.concatenate(out)


def resume(M, L):
    z = zmat_nuit(M, L)
    return np.array([float(np.abs(z).max()), float((z * z).sum())]), z


if __name__ == "__main__":
    import lab

    A = lab.load()
    M = np.asarray(A.mask)
    TS = np.asarray(A.ts).astype(np.int64)
    N = len(M)
    BOR = np.r_[0, np.flatnonzero(np.diff(TS) > 1000) + 1, N]
    LON = np.diff(BOR)
    L = int(np.bincount(LON).argmax())
    PREM = M[BOR[:-1]]                                     # les 346 premiers de nuit
    n2 = N // 2
    NA = POOL * POOL * NUITS
    MTOT = NA + 2 + 2 + POOL * POOL + 1

    HYP = (f"Un reamorcage nocturne ne laisse aucune trace. L'archive a une coupure "
           f"structurelle unique — 345 coupures dont 343 de 25 500 secondes exactement, "
           f"soit sept heures cinq minutes d'arret entre la fin d'une nuit et le debut de "
           f"la suivante, {L} tirages plus tard — et c'est le moment ou une machine se "
           f"reamorcerait si elle se reamorcait. Sa trace ne serait alors ni au retard 1 ni "
           f"sur la diagonale, mais au retard {L} et EN TRAVERS : le numero i au tirage t "
           f"rend-il le numero j plus probable au tirage t+{L}, c'est-a-dire a la meme "
           f"position de la nuit suivante ? Aucun instrument ne l'atteint — le §194 balaie "
           f"tous les retards mais seulement pour i = j, le §220 balaie les couples croises "
           f"mais s'arrete au retard 10. Trois familles : A la matrice C_ij({L}k) pour k = 1 "
           f"a {NUITS}, soit {NA} cases ; B la regle de pari a une nuit, couple le plus fort "
           f"sur une moitie joue sur l'autre ; C les {len(PREM)} PREMIERS tirages de nuit, "
           f"la sous-suite qui suivrait immediatement un reamorcage, avec ses {POOL*POOL} "
           f"cases de transfert d'une nuit a la suivante et le recouvrement moyen entre "
           f"nuits consecutives")
    STAT = (f"max |z| et energie somme z² sur les {NA} cases de A, reduits par la loi "
            f"EMPIRIQUE du maximum sur {REPS} repliques SRS chacune laissee hors de sa "
            f"propre normalisation ; le z de la regle de pari hors echantillon ; et pour C "
            f"le max |z| sur {POOL*POOL} cases plus le recouvrement moyen")
    NUL = (f"EXACTE : les tirages etant independants, chaque case est binomiale de "
           f"parametre p = 1/16 exactement. Famille C : {len(PREM)-1} paires seulement, "
           f"donc {(len(PREM)-1)*P2:.1f} attendus par case — la famille la plus ciblee du "
           f"dossier et la MOINS PUISSANTE, elle exclut un reamorcage grossier et non un "
           f"reamorcage fin. Recouvrement moyen entre nuits consecutives : 5 exactement, "
           f"d'ecart-type 1,6876 (hypergeometrique)")
    VER = ("conforme si le maximum reduit reste sous le 95e centile de sa loi empirique et "
           "si la regle de pari ne depasse pas le seuil de Bonferroni ; REAMORCAGE sinon")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h200 : nuits de {L} tirages ; retards {L} a {L*NUITS} ; {MTOT} statistiques")

    obs, z = resume(M, L)
    j = int(np.argmax(np.abs(z)))
    k0, r0 = j // (POOL * POOL) + 1, j % (POOL * POOL)
    say(f"\nA  LA MATRICE AUX RETARDS DE NUIT")
    say(f"   max |z| = {z[j]:+.3f} : numero {r0//POOL+1} -> numero {r0%POOL+1} "
        f"apres {k0} nuit(s) (retard {L*k0})")
    say(f"   energie somme z² = {obs[1]:.1f}   (attendue ~{NA})")

    V = np.empty((REPS, 2))
    rng = np.random.default_rng(0x200)
    for r in range(REPS):
        V[r] = resume(lab.srs(N, rng), L)[0]
        if (r + 1) % 50 == 0:
            say(f"   ... {r+1}/{REPS} repliques")
    s1, s2 = V.sum(axis=0), (V * V).sum(axis=0)
    mu, sd = V.mean(axis=0), V.std(axis=0)
    o = float(np.abs((obs - mu) / np.maximum(sd, 1e-12)).max())
    mx = np.empty(REPS)
    for r in range(REPS):
        m_ = (s1 - V[r]) / (REPS - 1)
        v_ = np.maximum((s2 - V[r] * V[r]) / (REPS - 1) - m_ * m_, 1e-12)
        mx[r] = float(np.abs((V[r] - m_) / np.sqrt(v_)).max())
    pA = float((1 + int((mx >= o).sum())) / (1 + REPS))
    for i, nom in enumerate(("max |z|", "energie")):
        say(f"   {nom:>10} archive {obs[i]:12.3f}   repliques {mu[i]:12.3f} "
            f"+/-{sd[i]:8.3f}   z reduit {(obs[i]-mu[i])/max(sd[i],1e-12):+7.3f}")
    say(f"   maximum reduit {o:.3f} ; 95e centile {np.percentile(mx, 95):.3f} ; "
        f"p = {pA:.4f}")

    say(f"\nB  LA REGLE DE PARI A UNE NUIT")
    zB = []
    for nom, (a1, b1, a2, b2) in (("H1->H2", (0, n2, n2, N)), ("H2->H1", (n2, N, 0, n2))):
        C1 = X.transfert(M[a1:b1], L)
        k1 = int(np.argmax(C1))
        i0, j0 = k1 // POOL, k1 % POOL
        n1 = b1 - a1 - L
        z1 = (C1.flat[k1] - n1 * P2) / sqrt(n1 * P2 * (1 - P2))
        h, ni, zc = X.regle_conditionnelle(M[a2:b2], i0, j0, L)
        zB.append(zc)
        say(f"   {nom} : couple ({i0+1} -> {j0+1}) au retard {L}   en echantillon "
            f"z = {z1:+.2f}")
        say(f"            regle « si {i0+1} sort, jouer {j0+1} demain au meme creneau » : "
            f"{h}/{ni} = {100*h/max(ni,1):.4f} %  contre 25,0000 %   z = {zc:+.2f}")

    say(f"\nC  LES {len(PREM)} PREMIERS TIRAGES DE NUIT (famille ciblee, peu puissante)")
    nP = len(PREM) - 1
    CP = X.transfert(PREM, 1)
    zP = (CP - nP * P2) / sqrt(nP * P2 * (1 - P2))
    jp = int(np.argmax(np.abs(zP)))
    rec = float((PREM[:-1] & PREM[1:]).sum(axis=1).mean())
    zrec = (rec - 5.0) / (1.687632 / sqrt(nP))
    say(f"   {nP} paires de nuits consecutives ; {nP*P2:.1f} attendus par case")
    say(f"   max |z| = {zP.flat[jp]:+.3f} ({jp//POOL+1} -> {jp%POOL+1})")
    say(f"   recouvrement moyen entre premiers tirages de nuits consecutives : "
        f"{rec:.5f} contre 5,00000   z = {zrec:+.2f}")

    m_ = len(zB) + 2
    lo, hi = 0.0, 40.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if erfc(mid / sqrt(2)) > 0.05 / m_:
            lo = mid
        else:
            hi = mid
    ZC_ = 0.5 * (lo + hi)
    zmax = max(zB + [zrec], key=abs)
    pB = float(min(1.0, erfc(abs(zmax) / sqrt(2)) * m_))
    p = float(min(pA, pB))
    verdict = "REAMORCAGE" if (pA <= 0.05 or abs(zmax) > ZC_) else "conforme"
    say(f"\n   max |z| familles B et C = {zmax:+.3f}   seuil de Bonferroni sur {m_} = "
        f"{ZC_:.3f}")
    say(f"   p retenue = {p:.4f}   ->   {verdict}")

    TOK["m_extra"] = MTOT - 1
    lab.record(
        TOK, float(max(o, abs(zmax))), p=p, verdict=verdict,
        power_at=(f"famille A : {(N-L)*P2:.0f} attendus par case, ecart-type "
                  f"{sqrt((N-L)*P2*(1-P2)):.1f}, donc un transfert relatif de "
                  f"{100*4.7*sqrt((N-L)*P2*(1-P2))/((N-L)*P2):.1f} % est vu. Famille C au "
                  f"contraire : {nP*P2:.1f} attendus par case seulement, donc elle ne voit "
                  f"qu'un transfert de "
                  f"{100*3.9*sqrt(nP*P2*(1-P2))/(nP*P2):.0f} % — c'est la famille la plus "
                  f"ciblee du dossier et de loin la moins puissante, et le recouvrement "
                  f"moyen entre nuits consecutives, d'ecart-type {1.687632/sqrt(nP):.4f}, "
                  f"est le seul chiffre de C qui ait une vraie puissance"),
        notes=(f"LE TRANSFERT DE NUIT (§221) — la coupure de 25 500 s est la seule "
               f"discontinuite structurelle du dossier et le moment ou une machine se "
               f"reamorcerait. Sa trace serait au retard {L} ET EN TRAVERS, ce qu'aucun "
               f"instrument n'atteignait : le §194 fait tous les retards mais i = j, le "
               f"§220 fait les couples croises mais s'arrete a 10. A : {NA} cases aux "
               f"retards {L} a {L*NUITS}, max |z| = {z[j]:+.3f}, maximum reduit {o:.3f} "
               f"contre un 95e centile de {np.percentile(mx, 95):.3f}, p = {pA:.4f}. "
               f"B : regles de pari a une nuit, z = "
               + ", ".join(f"{x:+.2f}" for x in zB) + f". C : {nP} paires de nuits, "
               f"recouvrement moyen {rec:.5f} contre 5, z = {zrec:+.2f}."))
    say("   consigne.")
