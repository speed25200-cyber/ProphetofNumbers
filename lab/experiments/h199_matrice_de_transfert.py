"""h199 — LA MATRICE DE TRANSFERT : le numéro `i` aujourd'hui dit-il quelque chose du
numéro `j` demain ? (RAPPORT §220).

LA CASE VIDE DU TABLEAU
=======================
Rangeons ce que le dossier a mesuré selon deux axes — même numéro ou numéros différents,
même tirage ou tirages différents :

|  | **même tirage** | **tirages différents** |
|---|---|---|
| **même numéro** | trivial | §194, autocorrélation exacte à tous les retards |
| **numéros différents** | §213, paires et triplets | **rien** |

La case en bas à droite est vide. Le §209 regarde bien des tirages différents, mais par un
**recouvrement agrégé** ; le §194 balaie tous les retards, mais seulement pour `i = j`.
Personne n'a jamais demandé :

> **Le numéro `17` au tirage `t` rend-il le numéro `43` plus probable au tirage `t+1` ?**

Or c'est exactement ce qu'un générateur à état produirait s'il en produisait quoi que ce
soit — l'état survit d'un tirage au suivant, et sa trace est une dépendance **croisée**
entre numéros de tirages voisins. Et c'est immédiatement exploitable : une seule case qui
s'écarte, et l'on sait quoi jouer après avoir vu le tirage précédent.

TROIS FAMILLES, ET LA TROISIÈME EST CELLE QU'ON A DEMANDÉE
==========================================================
  **A  LA MATRICE.** `C_ij(d) = #{t : i ∈ D_t et j ∈ D_{t+d}}` pour les `80 × 80` couples
     et les retards `d = 1 … 10`, soit `64 000` cases. Nulle **exacte** : les tirages
     étant indépendants, chaque case est binomiale de paramètre `p = (1/4)(1/4) = 1/16`
     **exactement**, y compris la diagonale, puisque `t` et `t+d` sont des tirages
     distincts.

  **B  LA RÈGLE DE PARI, HORS ÉCHANTILLON.** Le couple `(i, j)` le plus fort de la
     première moitié, joué sur la seconde — et énoncé sous la forme que lit un joueur :
     *« quand `i` sort, joue `j` au tirage suivant »*, avec son taux. Conditionnellement au
     nombre de tirages contenant `i`, chacun de leurs successeurs contient `j` avec
     probabilité `1/4` exactement et indépendamment : la nulle est donc exacte, et c'est la
     mesure la plus nette du lot. Le témoin y donne `28,62 %` contre `25 %`, `z = +7,24`.

  **C  LE PRÉDICTEUR DE TRANSFERT.** On ajuste `T` sur la première moitié, puis pour chaque
     tirage de la seconde on note chaque numéro `j` par `Σ_{i ∈ D_t} T_ij` et l'on joue les
     `k` meilleurs sur le tirage **suivant**, pour `k = 1, 2, 3, 5, 10`. C'est
     littéralement « prédire cinq numéros à partir du tirage d'avant », et la nulle est
     l'hypergéométrique exacte du §208.

     Deux variantes, **brute** et **seuillée** à `|z| ≥ 3`. Le témoin montre pourquoi : un
     transfert réel unique, vu à `z = +10,7` dans la matrice, ne rend que `z = +2,9` en
     prédiction si l'on note avec les six mille quatre cents cases — la seule vraie se
     noie dans le bruit des autres. Mettre à zéro les cases non significatives *sur la
     moitié d'ajustement* la fait ressortir, et la mesure sur l'autre moitié reste honnête
     puisque rien de ce choix n'a vu les données de mesure.

POURQUOI LA LOI DU MAXIMUM EST EMPIRIQUE
========================================
Les cases ne sont pas indépendantes : la somme d'une ligne vaut `20 × #{t : i ∈ D_t}`,
donc les quatre-vingts cases d'une ligne sont liées, et les retards se recouvrent. Un
Bonferroni gaussien serait faux dans les deux sens (§7.32).
"""

import json
import os
import sys
from math import erfc, sqrt

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POOL, DRAWN = 80, 20
EXP_ID = "h199.matrice_de_transfert"
FJETON = "/tmp/h199_jeton.json"
REPS = 200
RETARDS = tuple(range(1, 11))
KS = (1, 2, 3, 5, 10)
SEUILS = (0.0, 3.0)                                       # brut, puis seuille a |z| >= 3
P2 = (DRAWN / POOL) ** 2                                  # 1/16 exactement


def say(*a):
    print(*a, flush=True)


def sd_hyper(n, k):
    return sqrt(n * k * (DRAWN / POOL) * ((POOL - DRAWN) / POOL)
                * ((POOL - k) / (POOL - 1)))


def transfert(M, d):
    """C_ij(d), en float32 : les comptes valent ~4 410, tres en dessous de 2^24."""
    F = M.astype(np.float32)
    return (F[:len(M) - d].T @ F[d:]).astype(np.float64)


def zmat(M):
    """les 64 000 z de la famille A, aplatis dans l'ordre des retards."""
    out = []
    for d in RETARDS:
        n = len(M) - d
        out.append(((transfert(M, d) - n * P2)
                    / sqrt(n * P2 * (1 - P2))).ravel())
    return np.concatenate(out)


def resume(M):
    """deux scalaires par archive : le max de |z| et l'energie."""
    z = zmat(M)
    return np.array([float(np.abs(z).max()), float((z * z).sum())]), z


def regle_conditionnelle(M, i, j, d=1):
    """« quand tu vois i, joue j au tirage suivant » — le taux, et sa nulle EXACTE.

    Conditionnellement au nombre de tirages contenant i, chacun de leurs successeurs
    contient j avec probabilite 20/80 = 1/4 exactement et independamment. C'est la forme
    sous laquelle un joueur lit le resultat, et c'est plus net qu'un compte brut.
    """
    ou = np.flatnonzero(M[:len(M) - d, i])
    ni = len(ou)
    if ni < 50:
        return 0, 0, 0.0
    h = int(M[ou + d, j].sum())
    return h, ni, (h - ni * DRAWN / POOL) / sqrt(ni * (DRAWN / POOL) * (1 - DRAWN / POOL))


def predicteur(M, deb1, fin1, deb2, fin2, seuil=0.0):
    """famille C : T ajustee sur [deb1,fin1), jouee sur [deb2,fin2).

    `seuil > 0` met a zero toute case dont le |z| d'ajustement reste sous le seuil. Ce
    n'est pas un raffinement cosmetique : le temoin montre qu'un transfert reel unique,
    vu a `z = +10,7` dans la matrice, ne rend que `z = +2,9` en prediction quand on note
    avec les six mille quatre cents cases — la seule vraie se noie dans le bruit des
    autres. Le seuillage est choisi ENTIEREMENT sur la premiere moitie, donc la mesure sur
    la seconde reste honnete quel qu'il soit.
    """
    A = M[deb1:fin1]
    n1 = len(A) - 1
    T = (transfert(A, 1) - n1 * P2) / sqrt(n1 * P2 * (1 - P2))
    if seuil > 0:
        T = np.where(np.abs(T) >= seuil, T, 0.0)
    B = M[deb2:fin2]
    S = B[:-1].astype(np.float64) @ T                      # note du tirage suivant
    cible = B[1:]
    n = len(cible)
    ordre = np.argsort(-S, axis=1, kind="stable")
    lignes = np.arange(n)[:, None]
    # « le modele parle » : au moins une case non nulle s'applique au tirage courant. Un
    # transfert i -> j ne peut rien dire des tirages qui ne contiennent pas i, et ils sont
    # les trois quarts ; mesurer le taux sur TOUS les tirages dilue donc l'avantage d'un
    # facteur quatre. Le sous-ensemble est choisi par la matrice ajustee sur l'autre moitie
    # et par le tirage COURANT, jamais par le tirage cible : la nulle hypergeometrique y
    # reste donc exacte.
    parle = S.max(axis=1) > 0
    out = {}
    for k in KS:
        h = int(cible[lignes, ordre[:, :k]].sum())
        out[k] = (h, n, (h - n * k / 4) / sd_hyper(n, k))
    np_ = int(parle.sum())
    if np_ >= 50:
        hp = int(cible[np.flatnonzero(parle)[:, None], ordre[parle][:, :1]].sum())
        out["parle"] = (hp, np_, (hp - np_ / 4) / sd_hyper(np_, 1))
    else:
        out["parle"] = (0, np_, 0.0)
    return out, T, int((T != 0).sum())


if __name__ == "__main__":
    import lab

    A = lab.load()
    M = np.asarray(A.mask)
    N = len(M)
    n2 = N // 2
    NA = POOL * POOL * len(RETARDS)
    MTOT = NA + 2 + 4 + 2 * len(SEUILS) * (len(KS) + 1)

    HYP = ("Le numero i au tirage t ne dit rien du numero j au tirage t+d. Le dossier a "
           "mesure le meme numero a des tirages differents (§194, autocorrelation exacte a "
           "tous les retards) et des numeros differents au meme tirage (§213, paires et "
           "triplets), mais JAMAIS des numeros differents a des tirages differents : le "
           "§209 regarde bien des tirages voisins, mais par un recouvrement agrege. Or "
           "c'est exactement ce qu'un generateur a etat produirait s'il produisait quoi que "
           "ce soit — l'etat survit d'un tirage au suivant et sa trace est une dependance "
           "CROISEE entre numeros de tirages voisins — et c'est immediatement exploitable, "
           "une seule case qui s'ecarte disant quoi jouer apres avoir vu le tirage "
           f"precedent. Trois familles : A la matrice C_ij(d) pour les {POOL}x{POOL} "
           f"couples et les retards 1 a {max(RETARDS)}, soit {NA} cases ; B le couple le "
           "plus fort de la premiere moitie joue sur la seconde ; C le PREDICTEUR de "
           "transfert, ou l'on ajuste T sur la premiere moitie puis on note chaque numero j "
           "par la somme des T_ij sur les i du tirage courant et l'on joue les k meilleurs "
           "sur le tirage SUIVANT, pour k = 1, 2, 3, 5, 10 — c'est litteralement predire "
           "cinq numeros a partir du tirage d'avant")
    STAT = (f"max |z| et energie somme z² sur les {NA} cases, reduits par la loi EMPIRIQUE "
            f"du maximum sur {REPS} repliques SRS chacune laissee hors de sa propre "
            f"normalisation ; plus le z du couple hors echantillon et les z du predicteur "
            f"pour chaque k")
    NUL = (f"EXACTE : les tirages etant independants, chaque case C_ij(d) est binomiale de "
           f"parametre p = (20/80)² = 1/16 EXACTEMENT — y compris la diagonale, puisque t "
           f"et t+d sont des tirages distincts. Famille C : hypergeometrique exacte, k "
           f"numeros contiennent k/4 gagnants en moyenne et k(1/4)(3/4)(80-k)/79 en "
           f"variance. Les cases n'etant PAS independantes entre elles — la somme d'une "
           f"ligne vaut 20 fois le nombre de sorties de i, et les retards se recouvrent — "
           f"la loi du MAXIMUM est calibree sur repliques et non par Bonferroni (§7.32)")
    VER = ("conforme si le maximum reduit reste sous le 95e centile de sa loi empirique ET "
           "si aucun k du predicteur ne depasse le seuil de Bonferroni ; TRANSFERT sinon")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h199 : {N} tirages ; {NA} cases de transfert ; {MTOT} statistiques")
    say(f"   nulle exacte p = (20/80)² = 1/16 ; attendu {(N-1)*P2:.1f} par case, "
        f"ecart-type {sqrt((N-1)*P2*(1-P2)):.2f}")

    obs, z = resume(M)
    j = int(np.argmax(np.abs(z)))
    d0, r0 = RETARDS[j // (POOL * POOL)], (j % (POOL * POOL))
    say(f"\nA  LA MATRICE")
    say(f"   max |z| = {z[j]:+.3f} : numero {r0 // POOL + 1} -> numero {r0 % POOL + 1} "
        f"au retard {d0}")
    say(f"   energie somme z² = {obs[1]:.1f}   (attendue ~{NA})")
    say(f"   moyenne des z {z.mean():+.4f}, ecart-type {z.std():.4f}")

    V = np.empty((REPS, 2))
    rng = np.random.default_rng(0x199)
    for r in range(REPS):
        V[r] = resume(lab.srs(N, rng))[0]
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
    say(f"\n   {'statistique':>14} | {'archive':>12} | {'repliques':>20} | {'z reduit':>9}")
    for i, nom in enumerate(("max |z|", "energie")):
        say(f"   {nom:>14} | {obs[i]:12.3f} | {mu[i]:12.3f} +/-{sd[i]:8.3f} | "
            f"{(obs[i]-mu[i])/max(sd[i],1e-12):+9.3f}")
    say(f"   maximum reduit {o:.3f} ; 95e centile des repliques "
        f"{np.percentile(mx, 95):.3f} ; p = {pA:.4f}")

    # ---- B : le couple hors echantillon
    say(f"\nB  LE COUPLE HORS ECHANTILLON")
    zB = []
    for nom, (a1, b1, a2, b2) in (("H1->H2", (0, n2, n2, N)), ("H2->H1", (n2, N, 0, n2))):
        C1 = transfert(M[a1:b1], 1)
        k1 = int(np.argmax(C1))
        i0, j0 = k1 // POOL, k1 % POOL
        n1 = b1 - a1 - 1
        z1 = (C1.flat[k1] - n1 * P2) / sqrt(n1 * P2 * (1 - P2))
        C2 = transfert(M[a2:b2], 1)
        n_ = b2 - a2 - 1
        z2 = float((C2[i0, j0] - n_ * P2) / sqrt(n_ * P2 * (1 - P2)))
        zB.append(z2)
        h, ni, zc = regle_conditionnelle(M[a2:b2], i0, j0)
        say(f"   {nom} : couple ({i0+1} -> {j0+1})   en echantillon z = {z1:+.2f}   "
            f"hors echantillon z = {z2:+.2f}")
        say(f"            regle « si {i0+1} sort, jouer {j0+1} au suivant » : "
            f"{h}/{ni} = {100*h/max(ni,1):.4f} %  contre 25,0000 %   z = {zc:+.2f}")
        zB.append(zc)

    # ---- C : le predicteur
    say(f"\nC  LE PREDICTEUR DE TRANSFERT (T ajustee sur une moitie, jouee sur l'autre)")
    say(f"   {'sens':>8} {'seuil':>6} {'cases':>6} {'k':>3} | {'justes':>16} | "
        f"{'taux':>9} | {'z':>7}")
    zC, detC = [], []
    for nom, (a1, b1, a2, b2) in (("H1->H2", (0, n2, n2, N)), ("H2->H1", (n2, N, 0, n2))):
        for seuil in SEUILS:
            res, _, ncase = predicteur(M, a1, b1, a2, b2, seuil)
            for k in KS:
                h, n_, zz = res[k]
                zC.append(zz)
                detC.append(f"{nom} seuil {seuil:.0f} k={k} {100*h/(n_*k):.4f} % "
                            f"z={zz:+.2f}")
                say(f"   {nom:>8} {seuil:6.0f} {ncase:6d} {k:3d} | {h:7d} / {n_*k:7d} | "
                    f"{100*h/(n_*k):8.4f} % | {zz:+7.2f}")
            hp, npp, zp = res["parle"]
            if npp:
                zC.append(zp)
                detC.append(f"{nom} seuil {seuil:.0f} k=1 SUR LES {npp} TIRAGES OU LE "
                            f"MODELE PARLE {100*hp/npp:.4f} % z={zp:+.2f}")
                say(f"   {nom:>8} {seuil:6.0f} {ncase:6d}  1*| {hp:7d} / {npp:7d} | "
                    f"{100*hp/npp:8.4f} % | {zp:+7.2f}   (* seulement les tirages ou le "
                    f"modele parle)")

    lo, hi = 0.0, 40.0
    m_ = len(zB) + len(zC)
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if erfc(mid / sqrt(2)) > 0.05 / m_:
            lo = mid
        else:
            hi = mid
    ZC_ = 0.5 * (lo + hi)
    zmax = max(zB + zC, key=abs)
    pBC = float(min(1.0, erfc(abs(zmax) / sqrt(2)) * m_))
    say(f"\n   max |z| familles B et C = {zmax:+.3f}   seuil de Bonferroni sur {m_} = "
        f"{ZC_:.3f}")

    p = float(min(pA, pBC))
    verdict = "TRANSFERT" if (pA <= 0.05 or abs(zmax) > ZC_) else "conforme"
    say(f"   p retenue = {p:.4f}   ->   {verdict}")
    TOK["m_extra"] = MTOT - 1
    lab.record(
        TOK, float(max(o, abs(zmax))), p=p, verdict=verdict,
        power_at=(f"famille A : {(N-1)*P2:.0f} attendus par case avec un ecart-type de "
                  f"{sqrt((N-1)*P2*(1-P2)):.1f}, donc le test voit un transfert relatif de "
                  f"{100*4.7*sqrt((N-1)*P2*(1-P2))/((N-1)*P2):.1f} % sur une case isolee. "
                  f"Famille C : sur {N-n2-1} tirages hors echantillon, l'ecart-type du taux "
                  f"du top-1 vaut {100*sd_hyper(N-n2-1,1)/(N-n2-1):.3f} point, donc un "
                  f"predicteur a 27 % au lieu de 25 % sortirait a z = "
                  f"{0.02*(N-n2-1)/sd_hyper(N-n2-1,1):.0f}"),
        notes=(f"LA MATRICE DE TRANSFERT (§220) — la case vide du tableau : le dossier avait "
               f"mesure le meme numero a des tirages differents (§194) et des numeros "
               f"differents au meme tirage (§213), jamais des numeros DIFFERENTS a des "
               f"tirages DIFFERENTS. {NA} cases, nulle binomiale exacte p = 1/16. Archive : "
               f"max |z| = {z[j]:+.3f} ({r0//POOL+1} -> {r0%POOL+1} au retard {d0}), energie "
               f"{obs[1]:.1f} pour {NA} attendus ; maximum reduit {o:.3f}, p = {pA:.4f}. "
               f"Predicteur de transfert hors echantillon : " + " ; ".join(detC)))
    say("   consigne.")
