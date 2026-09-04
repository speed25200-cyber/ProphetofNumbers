"""h220 — LA CHASSE 3 AU TRIPLET (3,1,1) : huit blocs disjoints, et un partage par nuits
(RAPPORT §245).

LE SEUL FIL DU DOSSIER QUI AIT RÉPLIQUÉ
=======================================
Sur deux cent quatre-vingt-onze lignes de registre, **un seul** écart s'est reproduit sur des
données disjointes : l'énergie additive à trois termes au triplet `(3,1,1)`.

    §183  (h168)   z = +3,267 sur l'archive entière      p = 0,0381 après Bonferroni sur 35
    §183a (h168b)  z₁ = +3,145 / z₂ = +2,196 sur deux moitiés disjointes, mêmes signes
    §183b (h168c)  z = +2,520 sur les quadruplets intra-nuit                « PERSISTE »

C'est la meilleure piste du dossier. Elle n'est significative après Holm ni de près ni de
loin — mais la règle ici est de ne pas laisser un écart sans suite.

UNE CORRECTION, D'ABORD, ET ELLE EST DE MON CÔTÉ
=================================================
**Le §183b n'est pas une réplication indépendante.** Il mesure le même triplet sur les
quadruplets *intra-nuit*, c'est-à-dire sur `69 474` des `70 557` quadruplets de l'archive
entière — **`98,5 %` des mêmes données**. Un « PERSISTE » y était presque acquis d'avance :
retirer un centième et demi d'un échantillon ne peut pas défaire un `z` de `+3,3`.

> La chaîne « ÉCART → réplique → PERSISTE » compte donc **une** mesure, **une** vraie
> réplication en deux moitiés, et **un quasi-doublon**. Ce n'est pas trois confirmations, et
> le dossier le présentait comme si.

CE QUE CETTE SECTION FAIT
=========================
  **Huit blocs chronologiques disjoints** de `8 820` tirages. Un effet réel de `z = +3,267`
     sur l'archive entière donne `+3,267/√8 = +1,155` par bloc, et surtout **huit signes
     positifs**. Une fluctuation donne quatre positifs et quatre négatifs.
  **Un partage par NUITS alternées** — les nuits paires contre les nuits impaires. C'est une
     partition orthogonale à la coupure chronologique : elle ne peut pas être portée par une
     dérive lente, et elle ne partage aucun quadruplet avec sa jumelle.
  **Le triplet reste celui du §183**, fixé bien avant, jamais rechoisi. C'est ce qui
     distingue une chasse d'une pêche — et c'est la troisième fois qu'on le chasse sans
     jamais en changer.

La règle de décision porte sur l'**agrégat** `Z = Σ z_q/√8` et sur le **compte des signes**,
dont la nulle est exactement binomiale.
"""

import json
import os
import sys
from math import comb, erfc, sqrt

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import h164_energie_signee as S                                        # noqa: E402
import h168_energie_trois_termes as T                                  # noqa: E402

EXP_ID = "h220.chasse_triplet_huit"
FJETON = "/tmp/h220_jeton.json"
CIBLE = (3, 1, 1)          # fixe par le §183, jamais rechoisi depuis
NBLOC = 8
REPS = 40


def say(*a):
    print(*a, flush=True)


if __name__ == "__main__":
    import lab

    A = lab.load()
    M = np.asarray(A.mask)
    TS = np.asarray(A.ts).astype(np.int64)
    N = len(M)
    BOR = np.r_[0, np.flatnonzero(np.diff(TS) > 1000) + 1, N]
    nb = N // NBLOC

    HYP = (f"L'ecart du triplet {CIBLE} du §183 est une fluctuation. C'est le SEUL fil du "
           f"dossier qui ait replique sur des donnees disjointes : z = +3,267 sur l'archive "
           f"(§183), puis z1 = +3,145 et z2 = +2,196 sur deux moities disjointes avec les "
           f"memes signes (§183a), puis z = +2,520 intra-nuit (§183b). CORRECTION DE MON "
           f"COTE : le §183b n'est PAS une replication independante — il mesure le meme "
           f"triplet sur 69 474 des 70 557 quadruplets, soit 98,5 % des memes donnees, et un "
           f"« PERSISTE » y etait presque acquis d'avance. La chaine compte donc UNE mesure, "
           f"UNE vraie replication en deux moities, et UN quasi-doublon. On tranche ici par "
           f"deux partitions : {NBLOC} blocs chronologiques disjoints de {nb} tirages — un "
           f"effet reel donne +3,267/racine(8) = +1,155 par bloc et surtout HUIT SIGNES "
           f"POSITIFS, une fluctuation en donne quatre — et un partage par NUITS ALTERNEES, "
           f"partition orthogonale a la coupure chronologique, qui ne peut pas etre portee "
           f"par une derive lente. Le triplet reste celui du §183, fixe bien avant et jamais "
           f"rechoisi : c'est la troisieme chasse sans changement de cible")
    STAT = (f"Z = somme des {NBLOC} z de bloc / racine({NBLOC}), le compte des z positifs "
            f"(nulle binomiale exacte), et les deux z du partage par nuits alternees")
    NUL = (f"Simulation : {REPS} archives SRS de {nb} tirages, moyenne et variance PAR "
           f"TIRAGE de l'energie a trois termes ; l'ecart-type d'un bloc vaut sd/racine(n). "
           f"Le compte des signes a une nulle EXACTE : binomiale(8, 1/2)")
    VER = (f"CONFIRME si Z > 3 ET au moins 7 des {NBLOC} z sont positifs ; FLUCTUATION sinon, "
           f"auquel cas l'ecart du §183 est clos apres trois chasses")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h220 : triplet {CIBLE}, {NBLOC} blocs de {nb} tirages, plus les nuits alternees")

    # --- la nulle, une fois pour toutes : moyenne et variance PAR TIRAGE
    rng = np.random.default_rng(0x220)
    s1 = s2 = 0.0
    cpt = 0
    for k in range(REPS):
        t = T.energie(S.srs(nb, rng), CIBLE).astype(np.float64)
        s1 += t.sum()
        s2 += float((t * t).sum())
        cpt += len(t)
        if (k + 1) % 10 == 0:
            say(f"   nulle {k+1}/{REPS}")
    mu = s1 / cpt
    va = max(s2 / cpt - mu * mu, 0.0)
    say(f"   nulle par tirage : moyenne {mu:.4f}, ecart-type {sqrt(va):.4f} "
        f"({cpt} tirages simules)")

    def zed(bloc):
        t = T.energie(bloc, CIBLE).astype(np.float64)
        return (float(t.mean()) - mu) / (sqrt(va / len(t)) if va > 0 else 1e-9), len(t)

    # --- huit blocs chronologiques
    say(f"\n   {'bloc':>6} | {'tirages':>8} | {'quadruplets':>12} | {'z':>8}")
    zs = []
    for q in range(NBLOC):
        a, b = q * nb, (q + 1) * nb if q < NBLOC - 1 else N
        z, ln = zed(M[a:b])
        zs.append(z)
        say(f"   {q+1:6d} | {b-a:8d} | {ln:12d} | {z:+8.3f}")
    zs = np.array(zs)
    Z = float(zs.sum() / sqrt(NBLOC))
    pos = int((zs > 0).sum())
    psigne = sum(comb(NBLOC, i) for i in range(pos, NBLOC + 1)) / (1 << NBLOC)
    say(f"\n   agregat Z = {Z:+.3f}   (un effet reel donnerait +3,27)")
    say(f"   signes positifs : {pos}/{NBLOC}   p binomial exact = {psigne:.4f}")

    # --- nuits alternees
    nuits = [(BOR[i], BOR[i + 1]) for i in range(len(BOR) - 1)]
    for par in (0, 1):
        parts = [M[a:b] for i, (a, b) in enumerate(nuits) if i % 2 == par and b - a > 10]
        bloc = np.concatenate(parts, axis=0)
        # on recalcule la nulle a cette taille-la : la moyenne par tirage ne depend pas
        # de la taille, seul l'ecart-type de la moyenne en depend
        z, ln = zed(bloc)
        say(f"   nuits {'paires' if par == 0 else 'impaires'} : {len(parts)} nuits, "
            f"{ln} quadruplets, z = {z:+.3f}")
        if par == 0:
            zp = z
        else:
            zi = z

    pZ = float(erfc(abs(Z) / sqrt(2)))
    confirme = Z > 3.0 and pos >= NBLOC - 1
    verdict = "CONFIRME" if confirme else "FLUCTUATION"
    say(f"\n   {verdict}")
    if not confirme:
        say("   -> apres trois chasses sur cible fixe, l'ecart du §183 est clos.")

    TOK["m_extra"] = NBLOC + 2
    lab.record(
        TOK, float(Z), p=float(min(pZ, psigne)), verdict=verdict,
        power_at=(f"un effet reel de z = +3,267 sur l'archive entiere donne +1,155 par bloc "
                  f"de {nb} tirages et huit signes positifs ; la probabilite d'obtenir au "
                  f"moins sept positifs par hasard vaut {9/256:.4f}, donc le test des signes "
                  f"seul a une puissance de 0,74 contre un effet de cette taille. "
                  f"L'agregat Z reproduit exactement le z de l'archive entiere si l'effet "
                  f"est homogene"),
        notes=(f"CHASSE 3 AU TRIPLET {CIBLE} (§245) — le seul fil du dossier qui ait "
               f"replique. CORRECTION D'ABORD : le §183b n'etait pas une replication "
               f"independante, il reutilisait 98,5 % des memes quadruplets (69 474 sur "
               f"70 557), et le dossier le presentait comme une troisieme confirmation. "
               f"Ici : {NBLOC} blocs chronologiques disjoints, z = "
               + ", ".join(f"{v:+.2f}" for v in zs.tolist())
               + f" ; agregat Z = {Z:+.3f} contre +3,27 attendu si l'effet est reel ; "
               f"{pos}/{NBLOC} signes positifs, p binomial exact {psigne:.4f}. Partage par "
               f"nuits alternees, partition orthogonale : nuits paires z = {zp:+.3f}, nuits "
               f"impaires z = {zi:+.3f}. {verdict}."))
    say("   consigne.")
