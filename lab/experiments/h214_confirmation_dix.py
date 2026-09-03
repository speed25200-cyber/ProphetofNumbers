"""h214 — LA CONFIRMATION : la règle du §236 s'est déclenchée, et ma nulle avait un défaut
(RAPPORT §237).

CE QUI S'EST PASSÉ
==================
Le §236 a pré-enregistré : *« conforme si aucun `k` ne dépasse le 95ᵉ centile de son taux sous
SRS ; BIAIS EXPLOITABLE sinon »*. Sur l'archive, `k = 10` a rendu `2,51276` justes contre un
95ᵉ centile de `2,50883`. **La règle s'est déclenchée**, à `z = +1,99`, `p = 0,059`.

Elle est consignée comme telle. Et la première chose à faire devant une règle qui se
déclenche n'est pas de l'expliquer — c'est de **vérifier la nulle contre laquelle elle s'est
déclenchée**.

LE DÉFAUT, ET C'EST LE MÊME QU'AU §222
======================================
Les répliques du §236 tirent une archive SRS synthétique **mais gardent les colonnes `bonus`
et `boost` réelles**. Or, sur l'archive, le bonus est **toujours l'un des vingt numéros du
tirage** (§77). Le trait « était le bonus au tirage précédent » y est donc un sous-ensemble
strict du trait « sorti au tirage précédent ». Dans les répliques, il n'a **aucun** rapport
avec le tirage synthétique.

> L'archive et sa nulle n'avaient pas la même géométrie de traits. Un modèle ajusté sur l'une
> et sur l'autre ne fait pas le même travail, et comparer leurs taux de justes compare deux
> choses différentes.

C'est **exactement** la faute que le §222 avait corrigée avant son lancement — ses répliques
passaient par une archive SRS complète pour que bonus et rang restent couplés. Je l'ai
refaite trois sections plus loin.

CE QUE CETTE SECTION FAIT
=========================
  **La nulle est réparée.** Chaque réplique tire une archive SRS *complète* : les vingt
     numéros, **puis** un bonus uniforme parmi ces vingt, **puis** un multiplicateur tiré de
     la grille exacte `(41, 19, 12, 4, 2, 2)/80` du §106. Le couplage de l'archive est
     reproduit.
  **La puissance est doublée** : `40` répliques au lieu de `16`, parce qu'un 95ᵉ centile
     estimé sur seize points ne vaut pas grand-chose — son erreur type est de l'ordre du
     tiers de l'écart-type qu'il mesure.
  **Le test est dédoublé.** La tranche de mesure est coupée en deux moitiés disjointes. Un
     biais réel apparaît dans les deux ; un artefact d'ajustement, dans une seule.

Le pré-enregistrement porte sur `k = 10` **seul** — celui qui a déclenché — plus les deux
demi-tranches. On ne rejoue pas les quatre `k` : ce serait se redonner quatre chances.
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import h213_modele_non_lineaire as H13                                 # noqa: E402

POOL, DRAWN = 80, 20
EXP_ID = "h214.confirmation_dix"
FJETON = "/tmp/h214_jeton.json"
REPS = 40
K = 10
SECTEURS = np.array([41, 19, 12, 4, 2, 2]) / 80.0
VALEURS = np.array([1, 2, 3, 4, 5, 10])


def say(*a):
    print(*a, flush=True)


def archive_srs(n, rng):
    """archive SRS COMPLETE : 20 numeros, PUIS un bonus pris parmi eux, PUIS un
    multiplicateur tire de la grille exacte du §106. C'est le couplage que le §236
    n'avait pas reproduit."""
    M = np.zeros((n, POOL), bool)
    idx = np.argsort(rng.random((n, POOL)), axis=1)[:, :DRAWN]
    M[np.arange(n)[:, None], idx] = True
    tire = rng.integers(0, DRAWN, n)
    bonus = np.sort(idx, axis=1)[np.arange(n), tire] + 1
    boost = VALEURS[rng.choice(len(VALEURS), size=n, p=SECTEURS)]
    return M, bonus.astype(np.int64), boost.astype(np.int64)


if __name__ == "__main__":
    import lab

    A = lab.load()
    M = np.asarray(A.mask)
    TS = np.asarray(A.ts).astype(np.int64)
    BONUS = np.asarray(A.bonus).astype(np.int64)
    BOOST = np.asarray(A.boost).astype(np.int64)
    N = len(M)
    veille = np.zeros(N, np.int8)
    veille[np.r_[0, np.flatnonzero(np.diff(TS) > 1000) + 1]] = 1
    coupe = H13.CHAUFFE + int((N - H13.CHAUFFE) * H13.PART)
    milieu = coupe + (N - coupe) // 2

    HYP = (f"L'exces de justes vu au §236 sur une grille de dix (2,51276 contre un 95e "
           f"centile de 2,50883, z = +1,99, p = 0,059) ne survit pas a une nulle reparee. "
           f"LE DEFAUT : les repliques du §236 tirent une archive SRS synthetique mais "
           f"GARDENT LES COLONNES bonus ET boost REELLES. Or sur l'archive le bonus est "
           f"toujours l'un des vingt numeros du tirage (§77), donc le trait 'etait le bonus "
           f"au tirage precedent' y est un sous-ensemble strict du trait 'sorti au tirage "
           f"precedent' ; dans les repliques il n'a aucun rapport avec le tirage "
           f"synthetique. L'archive et sa nulle n'avaient pas la meme geometrie de traits, "
           f"et comparer leurs taux de justes comparait deux choses differentes. C'est "
           f"EXACTEMENT la faute que le §222 avait corrigee avant son lancement — ses "
           f"repliques passaient par une archive SRS complete pour que bonus et rang "
           f"restent couples — et je l'ai refaite trois sections plus loin. Ici chaque "
           f"replique tire une archive SRS COMPLETE : 20 numeros, puis un bonus uniforme "
           f"parmi ces vingt, puis un multiplicateur tire de la grille exacte "
           f"(41,19,12,4,2,2)/80 du §106. La puissance passe de 16 a {REPS} repliques, un "
           f"95e centile estime sur seize points ne valant pas grand-chose. Et le test est "
           f"dedouble : la tranche de mesure est coupee en deux moities disjointes, un biais "
           f"reel apparaissant dans les deux et un artefact d'ajustement dans une seule")
    STAT = (f"taux de justes d'une grille des k = {K} meilleurs, sur la tranche de mesure "
            f"entiere et sur chacune de ses deux moities, contre {REPS} repliques d'archives "
            f"SRS COMPLETES rejouant toute la chaine")
    NUL = (f"{REPS} archives SRS completes — numeros, bonus pris parmi les vingt, "
           f"multiplicateur sur la grille exacte du §106 — rejouant traits, levier de "
           f"co-occurrence, expansion a 90 colonnes, Newton et selection des dix meilleurs. "
           f"L'esperance reste le theoreme k/4 = 2,5")
    VER = (f"CONFIRME si le taux de la tranche entiere depasse le 95e centile sous la nulle "
           f"reparee ET que les deux moities le depassent chacune ; INFIRME sinon, auquel "
           f"cas le declenchement du §236 s'explique par sa nulle mal couplee")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="A")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    def chaine3(Mx, bx, box):
        Xb = H13.base(Mx, bx, box, veille, H13.CHAUFFE, coupe)
        nf = Xb.shape[2]
        w, b, mu, sd = H13.ajuster(
            Xb[H13.CHAUFFE:coupe].reshape(-1, nf),
            Mx[H13.CHAUFFE:coupe].reshape(-1).astype(np.float64))
        S = H13.scorer(Xb[coupe:].reshape(-1, nf), w, b, mu, sd)
        del Xb
        n1 = (milieu - coupe) * POOL
        return (H13.justes(S, Mx, coupe, N, K),
                H13.justes(S[:n1], Mx, coupe, milieu, K),
                H13.justes(S[n1:], Mx, milieu, N, K))

    say(f"h214 : k = {K}, mesure {coupe}..{N} ; moities {coupe}..{milieu} et {milieu}..{N}")
    say("\n   controle du couplage sur une archive SRS complete :")
    Mc, bc, boc = archive_srs(3000, np.random.default_rng(1))
    dedans = int((Mc[np.arange(3000), bc - 1]).sum())
    say(f"      bonus dans le tirage : {dedans}/3000   (l'archive : 70560/70560)")
    say(f"      grille du multiplicateur : "
        f"{[int(round(80*(boc == v).mean())) for v in VALEURS]}   (le §106 : [41,19,12,4,2,2])")
    if dedans != 3000:
        say("      couplage rate — on s'arrete")
        sys.exit(1)

    tot, m1, m2 = chaine3(M, BONUS, BOOST)
    say(f"\n   archive : total {tot:.5f}   moitie 1 {m1:.5f}   moitie 2 {m2:.5f}"
        f"   (nulle exacte {K/4:.2f})")

    V = np.empty((REPS, 3))
    rng = np.random.default_rng(0x214)
    for r in range(REPS):
        Mr, br, bor = archive_srs(N, rng)
        V[r] = chaine3(Mr, br, bor)
        if (r + 1) % 10 == 0:
            say(f"   ... {r+1}/{REPS} repliques")

    noms = ("tranche entiere", "premiere moitie", "seconde moitie")
    obs = (tot, m1, m2)
    say(f"\n   {'':>17} | {'archive':>9} | {'sous SRS complet':>24} | {'z':>7} | "
        f"{'95e centile':>12} | {'p':>7}")
    passe = []
    for i, nm in enumerate(noms):
        mu_, sd_ = float(V[:, i].mean()), float(V[:, i].std())
        z = (obs[i] - mu_) / max(sd_, 1e-12)
        q = float(np.quantile(V[:, i], 0.95))
        p = float((np.sum(V[:, i] >= obs[i]) + 1) / (REPS + 1))
        passe.append(obs[i] > q)
        say(f"   {nm:>17} | {obs[i]:9.5f} | {mu_:9.5f} +/-{sd_:9.5f} | {z:+7.2f} | "
            f"{q:12.5f} | {p:7.4f}")

    verdict = "CONFIRME" if all(passe) else "INFIRME"
    ptot = float((np.sum(V[:, 0] >= tot) + 1) / (REPS + 1))
    say(f"\n   {verdict}")
    if verdict == "INFIRME":
        say("   -> le declenchement du §236 s'explique par sa nulle mal couplee")

    TOK["m_extra"] = 2
    lab.record(
        TOK, float(tot), p=float(ptot), verdict=verdict,
        power_at=(f"le temoin plante du §236 donne l'echelle sur la meme chaine : une marge "
                  f"de 0,25477 sur dix numeros rend 2,5131 justes et une marge de 0,25923 en "
                  f"rend 2,5809. L'ecart-type du taux sous la nulle reparee vaut "
                  f"{float(V[:, 0].std()):.5f}, donc le test voit un exces de "
                  f"{3*float(V[:, 0].std()):.5f} juste. Le seuil de RENTABILITE, lui, est a "
                  f"+0,162 juste (hypergeometrique non centrale de Fisher, mise la moins "
                  f"chere a CHF 1,50) : sept fois plus haut que le seuil de detection"),
        notes=(f"LA CONFIRMATION (§237) — la regle pre-enregistree du §236 s'est declenchee "
               f"a k = 10 (z = +1,99, p = 0,059) et la premiere chose a faire est de "
               f"verifier la NULLE contre laquelle elle s'est declenchee. Defaut trouve : "
               f"les repliques du §236 gardaient les colonnes bonus et boost REELLES sur des "
               f"tirages synthetiques, alors que sur l'archive le bonus est toujours l'un "
               f"des vingt (§77) — l'archive et sa nulle n'avaient pas la meme geometrie de "
               f"traits. Meme faute qu'au §222, corrigee la-bas avant lancement. Ici : "
               f"archives SRS COMPLETES (bonus parmi les vingt, multiplicateur sur la grille "
               f"du §106), {REPS} repliques au lieu de 16, et test dedouble sur deux moities "
               f"disjointes. Archive : {tot:.5f} juste au total, {m1:.5f} et {m2:.5f} par "
               f"moitie, contre {float(V[:, 0].mean()):.5f} +/- {float(V[:, 0].std()):.5f} "
               f"sous la nulle reparee. {verdict}."))
    say("   consigne.")
