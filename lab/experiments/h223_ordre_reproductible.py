"""h223 — L'ORDRE EST-IL LE MÊME À CHAQUE FOIS ? le test qui tue tous les artefacts
(RAPPORT §247 addendum).

CE QUE LE §247 NE COUVRE PAS
============================
Les cinq tests du §247 comparent l'ordre publié à une permutation uniforme et ne trouvent
rien. Mais ils ont un angle mort, et il faut le dire : ils sont dimensionnés contre les
artefacts **monotones** — un tri, un tri par seaux — qui donnent `rho = +1`. Un **ordre de
hachage** (`valeur × K mod 2³²`, puis tri) n'est pas monotone : il ressemble à une permutation
uniforme et passerait les cinq tests sans être pour autant un ordre de sortie.

LE TEST QUI LE TUE, ET IL EST EXACT
===================================
Un artefact — hachage, seaux, ordre d'insertion, jointure — est une **fonction déterministe
de la valeur**. Donc :

> Si les numéros `u` et `v` apparaissent ensemble dans deux tirages différents, un ordre
> déterministe les place **toujours dans le même sens**. Un ordre de sortie les place dans le
> même sens **une fois sur deux**.

On recense donc tous les couples `(u,v)` co-occurrents dans au moins deux relevés, et l'on
compte les **accords**. La nulle est exactement binomiale : chaque comparaison
indépendante vaut `1/2`.

    ordre de sortie réel        ->  taux d'accord 1/2
    artefact déterministe       ->  taux d'accord 1, sans exception

Il n'y a pas de zone grise : une seule paire discordante réfute déjà tout ordre déterministe
de la valeur, et le taux mesure de combien.
"""

import json
import os
import sys
from collections import defaultdict
from math import comb, erfc, sqrt

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POOL, DRAWN = 80, 20
EXP_ID = "h223.ordre_reproductible"
FJETON = "/tmp/h223_jeton.json"


def say(*a):
    print(*a, flush=True)


def accords(O):
    """pour chaque couple de valeurs vu dans >= 2 releves, compte les paires de releves
    qui les ordonnent DANS LE MEME SENS. Renvoie (accords, comparaisons)."""
    sens = defaultdict(list)
    for ligne in O:
        pos = {int(v): i for i, v in enumerate(ligne)}
        vals = sorted(pos)
        for i in range(len(vals)):
            for j in range(i + 1, len(vals)):
                u, v = vals[i], vals[j]
                sens[(u, v)].append(1 if pos[u] < pos[v] else 0)
    acc = tot = 0
    for s in sens.values():
        k = len(s)
        if k < 2:
            continue
        for i in range(k):
            for j in range(i + 1, k):
                tot += 1
                acc += int(s[i] == s[j])
    return acc, tot


if __name__ == "__main__":
    import csv
    import lab

    lignes = list(csv.DictReader(open(os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "draws_ordered.csv"))))
    O = np.array([[int(r["o%d" % i]) for i in range(1, 21)] for r in lignes])
    n = len(O)

    HYP = (f"L'ordre publie n'est pas une fonction deterministe de la valeur. Les cinq tests "
           f"du §247 comparent cet ordre a une permutation uniforme et ne trouvent rien, mais "
           f"ils ont un angle mort qu'il faut dire : ils sont dimensionnes contre les "
           f"artefacts MONOTONES — un tri, un tri par seaux — qui donnent rho = +1. Un ordre "
           f"de HACHAGE (valeur x K mod 2^32 puis tri) n'est pas monotone : il ressemble a une "
           f"permutation uniforme et passerait les cinq tests sans etre un ordre de sortie. Le "
           f"test qui le tue est exact : un artefact, quel qu'il soit, est une fonction "
           f"DETERMINISTE de la valeur, donc si les numeros u et v apparaissent ensemble dans "
           f"deux releves differents il les place TOUJOURS dans le meme sens, tandis qu'un "
           f"ordre de sortie les place dans le meme sens une fois sur deux. On recense tous "
           f"les couples co-occurrents dans au moins deux des {n} releves et l'on compte les "
           f"accords ; la nulle est exactement binomiale a 1/2. Il n'y a pas de zone grise : "
           f"une seule paire discordante refute deja tout ordre deterministe de la valeur")
    STAT = ("taux d'accord sur toutes les comparaisons de couples co-occurrents, et le z "
            "binomial correspondant")
    NUL = ("EXACTE et binomiale : sous un ordre de sortie reel, chaque comparaison vaut 1/2 "
           "independamment. Sous un ordre deterministe de la valeur, elle vaut 1 sans "
           "exception")
    VER = ("ARTEFACT DETERMINISTE si le taux d'accord vaut 1 ; ORDRE REEL si le taux est "
           "compatible avec 1/2")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    # --- temoins : trois artefacts, dont un que le §247 ne voit pas
    say("\n   selftest : trois artefacts, dont un invisible aux cinq tests du §247")
    rng = np.random.default_rng(223)
    ens = [np.sort(rng.choice(POOL, DRAWN, replace=False) + 1) for _ in range(n)]
    K = 2654435761
    arts = (("ordre trie", [np.sort(b) for b in ens]),
            ("ordre par hachage (valeur x K mod 2^32)",
             [np.array(sorted(b.tolist(), key=lambda v: (v * K) % (1 << 32))) for b in ens]),
            ("ordre de sortie simule (permutation uniforme)",
             [rng.permutation(b) for b in ens]))
    for nom, A in arts:
        a, t = accords(np.array(A))
        say(f"      {nom:>44} : {a}/{t} = {a/max(t,1):.4f}")

    acc, tot = accords(O)
    taux = acc / tot
    z = (acc - tot / 2) / sqrt(tot / 4)
    p = float(erfc(abs(z) / sqrt(2)))
    say(f"\n   les {n} releves : {acc} accords sur {tot} comparaisons = {taux:.4f}")
    say(f"   nulle exacte 0,5000 ; z = {z:+.2f} ; p = {p:.4f}")
    disc = tot - acc
    say(f"   comparaisons DISCORDANTES : {disc}   "
        f"(une seule suffit a refuter un ordre deterministe)")

    verdict = "ARTEFACT DETERMINISTE" if disc == 0 else "ORDRE REEL"
    say(f"\n   {verdict}")

    TOK["m_extra"] = 0
    lab.record(
        TOK, float(taux), p=float(p), verdict=verdict,
        power_at=(f"le test est DECISIF et non probabiliste contre tout ordre deterministe "
                  f"de la valeur : le temoin « hachage » — celui que les cinq tests du §247 "
                  f"ne voient pas — rend un taux d'accord de 1,0000 sur toutes ses "
                  f"comparaisons, et une seule comparaison discordante suffit a le refuter. "
                  f"L'archive en porte {disc} sur {tot}"),
        notes=(f"L'ORDRE EST-IL LE MEME A CHAQUE FOIS (§247 addendum) — les cinq tests du "
               f"§247 sont dimensionnes contre les artefacts MONOTONES et ne verraient pas un "
               f"ordre de hachage. Celui-ci tue tous les ordres deterministes de la valeur "
               f"d'un coup : si u et v co-occurrent dans deux releves, un ordre deterministe "
               f"les place toujours dans le meme sens. {acc} accords sur {tot} comparaisons = "
               f"{taux:.4f}, z = {z:+.2f} contre une nulle binomiale exacte a 1/2, "
               f"{disc} discordances. {verdict}."))
    say("   consigne.")
