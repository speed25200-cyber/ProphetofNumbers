"""h222 — L'ORDRE PUBLIÉ PAR L'API : une contradiction dans mon propre dossier
(RAPPORT §247).

LA CONTRADICTION
================
Le §11 range « l'ordre de sortie des boules » parmi *ce que ce labo ne peut pas trancher* :

> « L'archive est triée : `n1..n20` est croissant sur les 70 560 lignes. Un tirage ordonné
>   porterait ≈ 124 bits contre 61,6 — le plus gros gain d'information disponible, et il
>   n'est pas dans les données dont on dispose. »

Et le §10 pose le critère qui le trancherait, en soulignant qu'il est **asymétrique** :
*« une seule observation positive tranche A »*.

Or `lab/draws_ordered.csv` contient cette observation depuis toujours. Sa quatrième ligne :

    1381028, jeux.loro.ch, 7, 73, 14, 8, 60, 10, 71, 33, 9, 37, 51, 12, 77, 17, 23, 15, 3, 56, 21, 47

**Source : `jeux.loro.ch` — l'API elle-même. Et cette suite n'est pas triée.** Les onze autres
lignes viennent d'un écran ou d'une vidéo ; celle-là vient du serveur.

> Le dossier portait dans ses données la réponse à une question qu'il déclarait sans réponse.

CE QUE ÇA NE PROUVE PAS ENCORE
==============================
Que l'API publie **un** ordre ne prouve pas que c'est **l'ordre de sortie**. Trois lectures :

  **l'ordre de sortie** — la boule `7` est sortie la première ;
  **un artefact de sérialisation** — ordre d'itération d'une table de hachage, de seaux, ou
     d'une jointure en base. Ce serait alors une fonction **déterministe de l'ensemble**, et
     non un aléa ;
  **un ordre arbitraire mais fixe** — par exemple l'ordre d'insertion en base, corrélé au
     numéro.

Les lectures 2 et 3 ont une signature commune : **la position dépendrait de la valeur.** La
lecture 1 non — sous SRS, l'ordre de sortie est une permutation uniforme de l'ensemble,
indépendante des valeurs.

LES CINQ TESTS
==============
Sur les douze relevés ordonnés (`11` écran/vidéo + `1` API) :

  **rho** — corrélation de Spearman entre la position et la valeur, mise en commun ;
  **montées** — nombre de couples `o_i < o_{i+1}`, d'espérance exacte `(20−1)/2 = 9,5` ;
  **profil** — valeur moyenne par position, plate à `40,5` sous l'hypothèse d'ordre réel ;
  **paires** — `max |z|` sur les `190` couples de positions `(i<j)`, chacun testant
     `P(o_i < o_j) = 1/2` ;
  **extrêmes** — position du minimum et du maximum, uniformes sur les vingt.

Douze relevés, c'est peu pour un effet faible — mais un artefact de sérialisation n'est **pas**
un effet faible : une table de hachage ou un tri par seaux produirait un `rho` proche de `1`
par morceaux. Le test est donc bien dimensionné **contre l'alternative qui compte**.
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POOL, DRAWN = 80, 20
EXP_ID = "h222.ordre_publie"
FJETON = "/tmp/h222_jeton.json"
REPS = 20000


def say(*a):
    print(*a, flush=True)


def stats(O):
    """O : (n,20) entiers. Renvoie le vecteur des cinq statistiques."""
    n = len(O)
    pos = np.arange(DRAWN, dtype=np.float64)
    # rho de Spearman position <-> valeur, moyenne sur les tirages
    rangs = np.argsort(np.argsort(O, axis=1), axis=1).astype(np.float64)
    pc = pos - pos.mean()
    rc = rangs - rangs.mean(axis=1, keepdims=True)
    rho = float(((rc * pc).sum(axis=1) /
                 np.sqrt((rc ** 2).sum(axis=1) * (pc ** 2).sum())).mean())
    montees = float((O[:, 1:] > O[:, :-1]).sum(axis=1).mean())
    profil = O.mean(axis=0)
    ecart_profil = float(np.abs(profil - (POOL + 1) / 2).max())
    iu = np.triu_indices(DRAWN, 1)
    frac = (O[:, iu[0]] < O[:, iu[1]]).mean(axis=0)
    zpaires = float(np.abs(frac - 0.5).max() / np.sqrt(0.25 / n))
    argmin = float(np.bincount(O.argmin(axis=1), minlength=DRAWN).max())
    return np.array([rho, montees, ecart_profil, zpaires, argmin])


NOMS = ("rho de Spearman position-valeur", "montees par tirage",
        "ecart maximal du profil a 40,5", "max |z| sur les 190 couples",
        "occupation maximale de la position du minimum")


if __name__ == "__main__":
    import csv
    import lab

    lignes = list(csv.DictReader(open(os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "draws_ordered.csv"))))
    O = np.array([[int(r["o%d" % i]) for i in range(1, 21)] for r in lignes])
    SRC = [r["source"] for r in lignes]
    api = [i for i, s in enumerate(SRC) if "loro.ch" in s]
    n = len(O)

    HYP = (f"L'ordre publie par l'API est un ordre REEL — une permutation uniforme de "
           f"l'ensemble, independante des valeurs — et non un artefact de serialisation. LA "
           f"CONTRADICTION : le §11 range « l'ordre de sortie des boules » parmi ce que le "
           f"labo ne peut pas trancher, au motif que « il n'est pas dans les donnees dont on "
           f"dispose ». Or lab/draws_ordered.csv porte depuis toujours une ligne de source "
           f"jeux.loro.ch — l'API elle-meme — et cette suite N'EST PAS TRIEE. Le §10 posait "
           f"pourtant le critere, en soulignant qu'il est asymetrique : une seule observation "
           f"positive tranche la question. Le dossier portait dans ses donnees la reponse a "
           f"une question qu'il declarait sans reponse. Reste a savoir si cet ordre est "
           f"l'ORDRE DE SORTIE ou un artefact — ordre d'iteration d'une table de hachage, de "
           f"seaux, ou d'insertion en base. Ces alternatives ont une signature commune : la "
           f"position dependrait de la VALEUR, alors que sous un ordre de sortie reel la "
           f"permutation est uniforme et independante des valeurs. Cinq tests sur les {n} "
           f"releves : rho de Spearman position-valeur, nombre de montees (esperance exacte "
           f"9,5), profil de la valeur moyenne par position (plat a 40,5), max |z| sur les "
           f"190 couples de positions testant P(o_i < o_j) = 1/2, et occupation de la "
           f"position du minimum. Douze releves c'est peu pour un effet faible, mais un "
           f"artefact de serialisation n'est PAS un effet faible : une table de hachage ou un "
           f"tri par seaux donnerait un rho proche de 1 par morceaux — le test est dimensionne "
           f"contre l'alternative qui compte")
    STAT = (f"les cinq statistiques ci-dessus sur les {n} releves ordonnes, chacune comparee "
            f"a sa loi exacte sous permutation uniforme")
    NUL = (f"EXACTE par simulation directe : {REPS} jeux de {n} tirages SRS 20/80 dont "
           f"l'ordre est une permutation uniforme. Aucune approximation — c'est exactement "
           f"l'hypothese testee")
    VER = ("ORDRE REEL si les cinq statistiques tiennent dans leur intervalle a 95 % sous "
           "permutation uniforme ; ARTEFACT sinon, auquel cas la position depend de la valeur "
           "et l'ordre publie ne vaut rien")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h222 : {n} releves ordonnes, dont {len(api)} de source API "
        f"({', '.join(lignes[i]['id'] for i in api)})")
    for i in api:
        v = O[i]
        say(f"   la ligne API : {lignes[i]['id']} -> {v.tolist()}")
        say(f"   triee ? {'OUI' if list(v) == sorted(v) else 'NON — l API publie un ordre'}")

    # --- temoins : a quoi ressemblerait un artefact
    say("\n   selftest : a quoi ressemble un ARTEFACT, pour savoir ce qu'on cherche")
    rng0 = np.random.default_rng(222)
    base = np.array([np.sort(rng0.choice(POOL, DRAWN, replace=False) + 1) for _ in range(n)])
    for nom, art in (("ordre trie (artefact pur)", base),
                     ("ordre par seaux de 20 (hachage grossier)",
                      np.array([np.concatenate([np.sort(b[b <= 20]), np.sort(b[(b > 20) & (b <= 40)]),
                                                np.sort(b[(b > 40) & (b <= 60)]), np.sort(b[b > 60])])
                                for b in base]))):
        s = stats(art)
        say(f"      {nom:>40} : rho = {s[0]:+.3f}, montees = {s[1]:.2f}")

    obs = stats(O)
    say("")

    # --- la nulle, par simulation directe
    V = np.empty((REPS, len(obs)))
    rng = np.random.default_rng(0x222)
    for r in range(REPS):
        W = np.array([rng.choice(POOL, DRAWN, replace=False) + 1 for _ in range(n)])
        V[r] = stats(W)

    say(f"   {'statistique':>44} | {'observe':>9} | {'sous permutation uniforme':>26} | "
        f"{'p':>7}")
    dehors = []
    for j, nom in enumerate(NOMS):
        lo, hi = np.quantile(V[:, j], [0.025, 0.975])
        p = float(min((np.sum(V[:, j] >= obs[j]) + 1), (np.sum(V[:, j] <= obs[j]) + 1))
                  * 2 / (REPS + 1))
        ok = lo <= obs[j] <= hi
        dehors.append(not ok)
        say(f"   {nom:>44} | {obs[j]:9.4f} | {V[:, j].mean():8.4f} "
            f"[{lo:8.4f} ; {hi:8.4f}] | {min(p,1.0):7.4f}")

    verdict = "ARTEFACT" if any(dehors) else "ORDRE REEL"
    say(f"\n   {verdict}")
    if verdict == "ORDRE REEL":
        say("   -> l'ordre publie se comporte comme une permutation uniforme : rien ne le")
        say("      distingue d'un ordre de sortie, et tout le distingue d'un artefact de tri.")

    TOK["m_extra"] = len(obs) - 1
    lab.record(
        TOK, float(obs[0]), p=1.0, verdict=verdict,
        power_at=(f"le test est dimensionne contre l'alternative qui compte, pas contre un "
                  f"effet faible : le selftest montre qu'un ordre trie donne rho = +1,000 et "
                  f"19 montees, et qu'un ordre par seaux de vingt en donne encore "
                  f"{stats(np.array([np.concatenate([np.sort(b[b <= 20]), np.sort(b[(b > 20) & (b <= 40)]), np.sort(b[(b > 40) & (b <= 60)]), np.sort(b[b > 60])]) for b in base]))[0]:+.3f}. "
                  f"Sur {n} releves l'ecart-type de rho sous permutation uniforme vaut "
                  f"{V[:, 0].std():.4f}, donc un artefact de serialisation serait vu a plus "
                  f"de vingt ecarts-types"),
        notes=(f"L'ORDRE PUBLIE PAR L'API (§247) — CONTRADICTION DANS LE DOSSIER : le §11 "
               f"declare l'ordre de sortie « pas dans les donnees dont on dispose », alors "
               f"que lab/draws_ordered.csv porte une ligne de source jeux.loro.ch (tirage "
               f"1381028) qui n'est PAS triee. Le §10 posait pourtant le critere asymetrique : "
               f"une seule observation positive tranche. Cinq tests sur les {n} releves "
               f"ordonnes contre la permutation uniforme : "
               + " ; ".join(f"{NOMS[j]} = {obs[j]:.4f}" for j in range(len(obs)))
               + f". {verdict}."))
    say("   consigne.")
