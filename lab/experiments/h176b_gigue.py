"""h176b — LA GIGUE DE CONSOMMATION : pourquoi une relation à l'échelle du tirage est
invisible à un trait de convolution, alors qu'une relation courte ne l'est pas.

DONNÉES SYNTHÉTIQUES UNIQUEMENT. Ce fichier ne lit pas l'archive et ne se consigne pas au
registre : c'est une étude d'instrument, pas un test d'hypothèse.

LE FAIT QUE JE CROYAIS AVOIR À EXPLIQUER
========================================
Un premier essai, à `N = 20 000` et avec un jeu de triplets qui ne contenait pas `(3, 2, 1)`,
donnait `z = +0,85` à un additif de retards en mots `(23, 46, 69)` — portée `(1, 2, 3)` —
alors que des retards courts `(2, 3, 7)` se voyaient sans peine. J'en ai tiré une hypothèse,
et il se trouve que **le fait à expliquer n'existait pas** : à la taille de l'archive et
avec le bon triplet, le même générateur rend `z = +6,72` (§192).

L'hypothèse mérite quand même d'être tranchée, parce qu'elle porte sur la validité de la
règle de portée elle-même et donc sur tous les détecteurs des §177 à §184.

L'HYPOTHÈSE, MAINTENANT TESTÉE POUR ELLE-MÊME
=============================================
La machine consomme `E[N] = 22,8487` mots par tirage avec un écart-type de `1,8525`
(§7.27, exact). L'indice du premier mot du tirage `t` est donc `W_t = Σ_{s<t} N_s`, une
**marche aléatoire** de moyenne `22,85·t` et d'écart-type `1,85·√t`. Un partenaire situé
`d` mots en arrière ne tombe donc pas à un décalage de tirages FIXE : il flotte.

Un trait de convolution au niveau des tirages suppose au contraire que le partenaire est
toujours dans le tirage `t−g`. Si le flottement dépasse la largeur d'un tirage, la relation
se répartit sur plusieurs tirages et le trait ne voit plus qu'une moyenne.

LE TEST, QUI TRANCHE — ET SA PREMIÈRE VERSION, QUI ÉTAIT FAUSSE
================================================================
La première écriture de ce fichier comparait le même générateur, retards `(45, 90, 135)`,
sous les deux régimes. **C'était confondu.** Sous le régime à gigue, `E[N] = 22,85` mots par
tirage, donc la portée de retards `(45, 90, 135)` vaut `(1,97 ; 3,94 ; 5,91)` — ni entière,
ni même présente dans la liste des triplets du trait. Le régime A échouait pour une raison
qui n'avait rien à voir avec la gigue, et le verdict « c'est la gigue » ne valait rien.

La comparaison correcte fixe la **portée nominale** dans les deux régimes et ne laisse
varier que la gigue :

  A  GIGUE      — échantillonneur naturel (`E[N] = 22,85`), retards en mots
                  `(23, 46, 69)`, donc portée `(1,006 ; 2,013 ; 3,019)`. L'écart-type du
                  flottement vaut `1,85·√g`, soit `1,85`, `2,62` et `3,21` mots.
  B  SANS GIGUE — on consomme exactement `45` mots par tirage et l'on garde les vingt
                  premières classes distinctes ; retards `(45, 90, 135)`, donc portée
                  **exactement** `(1, 2, 3)` et flottement nul.

Les deux visent le même triplet `(3, 2, 1)` du trait. La seule différence est le
flottement.

  si B s'allume et pas A  ->  c'est la gigue, et la règle de portée a une clause manquante
  si aucun des deux      ->  l'explication est ailleurs, et il faut la chercher
"""

import os
import sys
from math import sqrt

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import h173_predicteur_appris as B                                      # noqa: E402
import h176_borne_elargie as H                                          # noqa: E402

POOL, DRAWN = 80, 20
M32 = 1 << 32


def say(*a):
    print(*a, flush=True)


def engendre(n, graine, retards, bloc=None):
    """`bloc=None` : on consomme jusqu'a vingt classes distinctes (GIGUE).
    `bloc=k`    : on consomme exactement k mots et l'on garde les vingt premieres
                  classes distinctes (SANS GIGUE). Renvoie (masque, replis, N moyen)."""
    import random
    r0 = random.Random(graine)
    L = max(retards)
    r = [r0.randrange(M32) for _ in range(L + 1)]
    i = len(r)
    m = np.zeros((n, POOL), bool)
    replis = 0
    total = 0

    def suivant():
        nonlocal i
        v = 0
        for d in retards:
            v += r[i - d]
        r.append(v % M32)
        i += 1
        return (r[i - 1] * POOL) >> 32

    for j in range(n):
        vus = []
        vu = set()
        if bloc is None:
            while len(vu) < DRAWN:
                c = suivant()
                total += 1
                if c not in vu:
                    vu.add(c)
                    vus.append(c)
        else:
            for _ in range(bloc):
                c = suivant()
                if c not in vu and len(vu) < DRAWN:
                    vu.add(c)
                    vus.append(c)
            total += bloc
            while len(vu) < DRAWN:            # repli : ne devrait jamais servir
                replis += 1
                c = suivant()
                total += 1
                if c not in vu:
                    vu.add(c)
                    vus.append(c)
        m[j, vus] = True
    return m, replis, total / n


def mesure(m, cols, etiq):
    N = len(m)
    BOR = np.array([0, N])
    coupe = B.CHAUFFE + int((N - B.CHAUFFE) * B.PART)
    X = H.construire(m, BOR, None)[:, :, cols]
    w, mu, sd = B.ajuster(X[B.CHAUFFE:coupe].reshape(-1, len(cols)),
                          m[B.CHAUFFE:coupe].reshape(-1))
    S = B.scorer(X, w, mu, sd)
    del X
    rec, _ = B.mesurer(m, S, coupe, N)
    z = (rec.mean() - 5.0) / (B.SD1 / sqrt(len(rec)))
    say(f"   {etiq:>40} | {rec.mean():9.5f} | {z:+8.2f}")
    return z


if __name__ == "__main__":
    N = 70560
    T3 = [26]                       # le trait « T trois termes » seul
    say("h176b : donnees SYNTHETIQUES uniquement, aucune archive lue")
    say(f"   A : r_i = r_(i-23) + r_(i-46) + r_(i-69), echantillonneur naturel")
    say(f"   B : r_i = r_(i-45) + r_(i-90) + r_(i-135), bloc fixe de 45 mots")
    say(f"   meme portee nominale (1,2,3) dans les deux cas ; {N} tirages")
    say(f"   {'regime':>40} | {'recouvr.':>9} | {'z':>8}")

    mA, rA, nA = engendre(N, 77, (23, 46, 69), bloc=None)
    say(f"      A gigue    : N moyen {nA:.3f} mots par tirage (attendu 22,849) ; "
        f"portee {23/nA:.3f}, {46/nA:.3f}, {69/nA:.3f}")
    zA = mesure(mA, T3, "A  GIGUE, portee (1,2,3) flottante")
    del mA

    mB, rB, nB = engendre(N, 77, (45, 90, 135), bloc=45)
    say(f"      B sans gigue : N constant {nB:.3f} mots, {rB} repli(s)")
    zB = mesure(mB, T3, "B  SANS GIGUE, portee (1,2,3) exacte")
    del mB

    # controle : le meme regime B sur un generateur SANS relation
    rng = np.random.default_rng(776)
    zC = mesure(B.srs(N, rng), T3, "C  controle SRS, regime indifferent")

    say("")
    if zB > 3 and zA < 3:
        say("   VERDICT : c'est la GIGUE. La regle de portee du §7.28 a une clause "
            "manquante —")
        say("   la portee doit etre entiere ET la consommation par tirage doit etre "
            "constante,")
        say("   sans quoi le partenaire flotte et un trait au niveau des tirages ne voit "
            "qu'une moyenne.")
    elif zB > 3 and zA > 3:
        say("   VERDICT : les deux s'allument — la gigue n'explique pas l'invisibilite du "
            "§192.")
    else:
        say("   VERDICT : meme sans gigue le trait ne voit rien — l'explication est "
            "AILLEURS.")
        say("   Le trait a trois termes ne couvre alors PAS la portee (1,2,3), et la borne "
            "du §192")
        say("   doit le dire.")
    say(f"   (A {zA:+.2f} | B {zB:+.2f} | controle {zC:+.2f})")
