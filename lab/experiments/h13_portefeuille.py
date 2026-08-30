"""h13 — la brèche du théorème d'invariance : la loi JOINTE d'un portefeuille.

Où le mur s'arrête exactement
------------------------------
Le théorème d'invariance dit ceci, et rien de plus :

    Pour TOUTE grille de k numéros, le nombre de bons numéros H suit la même
    loi hypergéométrique. Donc E[gain d'une grille] ne dépend pas des numéros
    choisis, quel que soit le barème.

C'est un énoncé sur la loi MARGINALE d'UNE grille. Tout le dossier jusqu'ici
a tenté de le contourner par la seule porte qu'il laisse ouverte du côté du
hasard : montrer que le tirage n'est pas uniforme (h4…h12). Cette porte est
restée fermée.

Mais il existe une seconde porte, et elle n'a jamais été poussée : le
théorème ne dit **rien** de la loi jointe de plusieurs grilles jouées
ensemble. Or un joueur ne joue jamais une grille isolée — il joue un
portefeuille, et c'est la loi jointe qui décide de ce qu'il touche.

Trois résultats exacts
-----------------------
1. LOI DE COVARIANCE. Deux grilles de k numéros qui se recoupent sur ω
   numéros ont
        Cov(H₁, H₂) = ω·p(1−p) − (k²−ω)·p(N−D)/(N(N−1))
   avec N=80, D=20, p=D/N. Elle s'annule EXACTEMENT en ω* = k²/N, qui est
   aussi le recouvrement moyen de deux grilles tirées au hasard.
        -> ω < k²/N : grilles anticorrélées.  ω > k²/N : corrélées.

2. CONSERVATION. Une PARTITION des 80 numéros en 80/k grilles disjointes
   vérifie Σ Hᵢ = 20 identiquement : la variance du total est NULLE. Le
   même argent placé sur des grilles identiques donne une variance de
   n²·Var(H). Même espérance, variance de 0 à 106.

3. AMPLIFICATION. Pour l'événement « au moins une grille est PLEINE »
   (k bons sur k, le rang qui porte le jackpot), n grilles disjointes valent
   ≈ n·p là où n grilles identiques valent p. **Facteur n, à budget et à
   espérance identiques.**

Et le point qui change le signe
--------------------------------
Tant que le gain est fixe, le facteur n ne porte que sur la PROBABILITÉ, pas
sur l'espérance : n grilles identiques gagnantes touchent n fois le prix. Mais
dès que le rang est PARTAGÉ entre les gagnants — ce qui est le cas d'un
jackpot progressif — détenir n tickets gagnants ne rapporte plus n parts
pleines mais n/(n+W) du pot, alors que la version disjointe touche 1/(1+W)
avec n fois plus de chances. Le rapport des espérances devient

        E[1/(1+W)] / E[1/(n+W)]   ≈  n   quand la foule W est petite

et l'espérance elle-même augmente. C'est exactement la troisième hypothèse
que h3 avait isolée — « le gain d'une grille ne dépend pas des autres
joueurs » — et c'est par là que l'invariance tombe.

Ce que ce fichier ne prétend pas
---------------------------------
Il ne donne aucune espérance absolue : le barème de Loto Express n'est pas
connu (cf. h9). Tous les résultats sont des RAPPORTS entre portefeuilles de
même coût, ce qui ne demande pas le barème. Et la loi de covariance comme la
conservation sont vérifiées numériquement contre du Monte-Carlo, pas
seulement dérivées.
"""

import itertools
import math
import os
import sys
import time
from math import comb

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

T0 = time.time()
N, D = 80, 20
P = D / N
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# --------------------------------------------------------------------------
# Les briques exactes
# --------------------------------------------------------------------------

VAR1 = P * (1 - P)                                  # Var(1_i)
GAMMA = -P * (N - D) / (N * (N - 1))                # Cov(1_i, 1_j), i≠j


def cov_hits(k: int, omega: int) -> float:
    """Cov(H₁,H₂) pour deux grilles de k numéros se recoupant sur ω."""
    return omega * VAR1 + (k * k - omega) * GAMMA


def var_hits(k: int) -> float:
    """Var(H) hypergéométrique pour une grille de k numéros."""
    return k * P * (1 - P) * (N - k) / (N - 1)


def p_hits(k: int, h: int) -> float:
    return comb(k, h) * comb(N - k, D - h) / comb(N, D)


def p_at_least(k: int, m: int) -> float:
    return sum(p_hits(k, h) for h in range(m, min(k, D) + 1))


def p_joint_full(k: int, m: int, j: int) -> float:
    """P(H₁≥m, …, H_j≥m) pour j blocs DISJOINTS de k numéros."""
    total = 0

    def rec(idx, used, ways):
        nonlocal total
        if idx == j:
            rest = N - j * k
            need = D - used
            if 0 <= need <= rest:
                total += ways * comb(rest, need)
            return
        for h in range(m, min(k, D - used) + 1):
            rec(idx + 1, used + h, ways * comb(k, h))

    rec(0, 0, 1)
    return total / comb(N, D)


def p_max_partition(k: int, m: int, blocks: int) -> float:
    """P(au moins un bloc atteint m) pour `blocks` blocs disjoints, exact."""
    tot = 0.0
    for j in range(1, blocks + 1):
        if j * m > D:
            break
        term = comb(blocks, j) * p_joint_full(k, m, j)
        tot += term if j % 2 else -term
    return tot


# --------------------------------------------------------------------------
# 1. La loi de covariance
# --------------------------------------------------------------------------

rule("1. LA LOI DE COVARIANCE, ET SON POINT NEUTRE")

say(f"   Var(1ᵢ) = p(1−p) = {VAR1:.6f}")
say(f"   Cov(1ᵢ,1ⱼ) = −p(N−D)/(N(N−1)) = {GAMMA:.8f}")
say(f"\n   Point neutre théorique : ω* = k²/N")

rng = np.random.default_rng(20260830)
NMC = 400_000
draws = np.zeros((NMC, N + 1), dtype=bool)
for i in range(NMC):
    draws[i, rng.choice(np.arange(1, N + 1), D, replace=False)] = True

say("\n   k    ω*=k²/N   ω   Cov théorique   Cov Monte-Carlo   écart")
for k in (5, 10):
    base = list(range(1, k + 1))
    Hb = draws[:, base].sum(axis=1)
    for omega in (0, 1, 2, k):
        other = base[:omega] + list(range(k + 1, k + 1 + (k - omega)))
        Ho = draws[:, other].sum(axis=1)
        emp = float(np.cov(Hb, Ho, ddof=1)[0, 1])
        th = cov_hits(k, omega)
        say(f"   {k:<4} {k * k / N:<9.3f} {omega:<3} {th:>+13.6f}   "
            f"{emp:>+15.6f}   {abs(th - emp):.5f}")

say(f"\n   Vérification indépendante par CONSERVATION : une partition des 80")
for k in (5, 10, 20):
    nb = N // k
    lhs = nb * var_hits(k) + nb * (nb - 1) * cov_hits(k, 0)
    say(f"     k={k:<3} {nb} blocs : Σ Var + Σ Cov = {lhs:+.10f}"
        f"   (doit valoir 0 car ΣHᵢ = 20)")
    assert abs(lhs) < 1e-9

say(f"\n   Et le point neutre : Cov(k, ω*) doit valoir 0.")
for k in (4, 8, 10, 16):
    say(f"     k={k:<3} ω* = {k * k / N:<6.2f}   Cov = {cov_hits(k, k * k / N):+.2e}")


# --------------------------------------------------------------------------
# 2. Trois portefeuilles de MÊME coût et de MÊME espérance
# --------------------------------------------------------------------------

rule("2. TROIS PORTEFEUILLES DE MÊME COÛT — ET CE QUI LES SÉPARE")

K, NB = 10, 8
say(f"   {NB} grilles de {K} numéros, donc {NB * K} = {N} numéros en tout.")
say("   P — partition : les 8 grilles sont disjointes et couvrent tout.")
say("   H — hasard    : 8 grilles tirées au hasard, indépendamment.")
say("   I — identiques: la même grille jouée 8 fois.")

part = [list(range(1 + i * K, 1 + (i + 1) * K)) for i in range(NB)]
Hpart = np.stack([draws[:, b].sum(axis=1) for b in part], axis=1)
ident = np.stack([draws[:, part[0]].sum(axis=1)] * NB, axis=1)
rand_blocks = [list(rng.choice(np.arange(1, N + 1), K, replace=False))
               for _ in range(NB)]
Hrand = np.stack([draws[:, b].sum(axis=1) for b in rand_blocks], axis=1)

say("\n   portefeuille   E[Σ H]   Var(Σ H)   E[max H]   ω moyen")
for name, Hm, blocks in (("P partition", Hpart, part),
                         ("H hasard   ", Hrand, rand_blocks),
                         ("I identique", ident, [part[0]] * NB)):
    tot = Hm.sum(axis=1)
    om = [len(set(blocks[i]) & set(blocks[j]))
          for i in range(NB) for j in range(i + 1, NB)]
    say(f"   {name}   {tot.mean():6.3f}   {tot.var(ddof=1):8.3f}   "
        f"{Hm.max(axis=1).mean():8.3f}   {np.mean(om):7.3f}")

say(f"\n   L'espérance du total est la MÊME partout : c'est le théorème")
say(f"   d'invariance, et il tient. La variance va de 0 à {ident.sum(axis=1).var(ddof=1):.0f}.")
say(f"   La partition a variance exactement nulle : Σ Hᵢ = 20 toujours.")
assert Hpart.sum(axis=1).min() == 20 and Hpart.sum(axis=1).max() == 20


# --------------------------------------------------------------------------
# 3. L'amplification, calculée exactement
# --------------------------------------------------------------------------

rule("3. « AU MOINS UNE GRILLE PLEINE » — LE FACTEUR n, EXACT")

say("   Probabilité qu'AU MOINS UNE grille du portefeuille atteigne m bons,")
say("   calculée exactement (inclusion-exclusion sur les blocs disjoints).\n")
say("   k   n   m    identiques        partition       gain")
for K, m in ((10, 10), (10, 9), (10, 8), (8, 8), (5, 5), (4, 4)):
    nb = N // K
    p_id = p_at_least(K, m)
    p_pa = p_max_partition(K, m, nb)
    say(f"   {K:<3} {nb:<3} {m:<4} {p_id:.6e}   {p_pa:.6e}   ×{p_pa / p_id:.3f}")

say("""
   Lecture. À budget identique et à espérance identique, jouer n grilles
   DISJOINTES multiplie par ≈ n la probabilité de toucher le rang plein.
   Le gain se dégrade légèrement quand m descend, parce que plusieurs blocs
   peuvent alors être servis simultanément et l'union cesse d'être une
   somme — mais au rang PLEIN, celui qui porte le jackpot, le facteur est
   quasiment exact.""")


# --------------------------------------------------------------------------
# 4. Le partage, et le moment où l'ESPÉRANCE change
# --------------------------------------------------------------------------

rule("4. AVEC UN RANG PARTAGÉ, C'EST L'ESPÉRANCE QUI BOUGE")

say("""   Si le rang plein est partagé entre les gagnants — c'est le cas d'un
   jackpot progressif — alors détenir n tickets gagnants IDENTIQUES ne
   rapporte pas n parts mais n/(n+W) du pot, avec W le nombre d'autres
   gagnants. La version disjointe touche 1/(1+W), mais n fois plus souvent.

   Avec W ~ Poisson(λ), E[1/(j+W)] se calcule exactement (h3) :""")


def e_inv_shift(lam: float, j: int, kmax: int = 400) -> float:
    """E[1/(j+W)] pour W ~ Poisson(λ)."""
    if lam == 0:
        return 1.0 / j
    tot, logp = 0.0, -lam
    for w in range(kmax):
        tot += math.exp(logp) / (j + w)
        logp += math.log(lam) - math.log(w + 1)
    return tot


say("\n   λ (autres gagnants)   E[1/(1+W)]   E[1/(8+W)]   rapport disjoint/identique")
for lam in (0.0, 0.1, 0.5, 1.0, 3.0, 10.0):
    a = e_inv_shift(lam, 1)
    b = e_inv_shift(lam, 8)
    say(f"   {lam:<21.1f} {a:<12.5f} {b:<12.5f} ×{a / b:.2f}")

say("""
   Le rapport des ESPÉRANCES vaut E[1/(1+W)] / E[1/(n+W)], et il est > 1
   pour tout λ. Ce n'est plus un gain de probabilité à espérance constante :
   c'est un gain d'espérance. L'invariance ne l'interdit pas, parce que son
   troisième présupposé — « le gain d'une grille ne dépend pas des autres
   joueurs » — est faux dès qu'un rang est partagé.

   C'est le premier endroit de tout le dossier où l'espérance bouge sans
   qu'il faille supposer quoi que ce soit sur le générateur.""")


# --------------------------------------------------------------------------
# 5. Le théorème de bascule
# --------------------------------------------------------------------------

rule("5. LE THÉORÈME DE BASCULE — la géométrie dépend du signe de l'espérance")

say("""   Tous les portefeuilles de même coût ont la même espérance (§2). Ils ne
   diffèrent que par la FORME de la loi du gain total, et cette forme est
   ordonnée : le portefeuille identique est un étalement à moyenne conservée
   du portefeuille en partition. Donc, mécaniquement :

     • objectif CONVEXE — « atteindre un objectif avant la ruine », typique
       d'un jeu à espérance négative — l'étalement est préférable :
       CONCENTRER (peu de grilles, fortement recouvrantes).

     • objectif CONCAVE — maximiser le taux de croissance (Kelly), ce qui
       n'a de sens qu'à espérance positive — la concentration est
       pénalisante : ÉTALER (grilles disjointes).

   Et le signe de l'espérance est précisément ce que h9 mesure : il bascule
   quand la cagnotte franchit mise/P(k/k). D'où la règle opérationnelle :

     cagnotte SOUS le seuil  -> jeu défavorable -> si l'on joue quand même,
        objectif « toucher le gros lot au moins une fois » : la partition
        reste le bon choix, parce qu'elle multiplie par n la probabilité de
        l'atteindre sans rien coûter en espérance (§3).
     cagnotte AU-DESSUS      -> jeu favorable -> Kelly, donc étalement
        maximal : partition + numéros impopulaires (h3), qui cumule le
        facteur n de §3 et le facteur de partage de §4.

   Dans les DEUX régimes la partition gagne ou égale. C'est le seul conseil
   du dossier qui ne dépende d'aucune hypothèse sur le générateur.""")


# --------------------------------------------------------------------------
# 6. La construction concrète
# --------------------------------------------------------------------------

rule("6. LA CONSTRUCTION — un portefeuille utilisable")

say("""   Contrainte de conception, tirée de §1 : garder tous les recouvrements
   par paires STRICTEMENT sous ω* = k²/N. Quand n·k ≤ 80 c'est réalisable à
   ω = 0 (partition partielle). Quand n·k > 80 le mieux possible est un
   plan équilibré : chaque numéro couvert ⌊nk/80⌋ ou ⌈nk/80⌉ fois, ce qui
   minimise Σω à n et k fixés.""")


def portfolio(k: int, n: int, unpopular_first: bool = True) -> list:
    """n grilles de k numéros : couverture équilibrée, recouvrement max minimal.

    Choix glouton, numéro par numéro, sur trois clés dans cet ordre :
      1. la couverture déjà accumulée du numéro — c'est elle qui garantit le
         plan équilibré, donc la somme des recouvrements minimale ;
      2. le recouvrement maximal que l'ajout induirait avec une grille déjà
         construite — c'est elle qui empêche une grille de se répéter ;
      3. le rang d'impopularité (h3), qui départage sans rien coûter.

    Le simple découpage séquentiel échouait ici : dès que n·k dépasse 80 il
    reboucle et reproduit la grille 1 à l'identique, soit ω = k.
    """
    order = (list(range(32, N + 1)) + list(range(1, 32))) if unpopular_first \
        else list(range(1, N + 1))
    rank = {x: i for i, x in enumerate(order)}
    grids, cover = [], {x: 0 for x in order}
    for _ in range(n):
        g = set()
        for _ in range(k):
            best, key_best = None, None
            for x in order:
                if x in g:
                    continue
                trial = g | {x}
                ov = max((len(gg & trial) for gg in grids), default=0)
                key = (cover[x], ov, rank[x])
                if key_best is None or key < key_best:
                    key_best, best = key, x
            g.add(best)
        for x in g:
            cover[x] += 1
        grids.append(g)
    return [sorted(g) for g in grids]


say("\n   Exemple : 8 grilles de 10, numéros impopulaires d'abord (h3) —")
pf = portfolio(10, 8)
for i, g in enumerate(pf):
    say(f"     grille {i + 1} : {g}")
oms = [len(set(pf[i]) & set(pf[j])) for i in range(len(pf)) for j in range(i + 1, len(pf))]
say(f"   recouvrement max = {max(oms)}, moyen = {np.mean(oms):.3f}"
    f"   (seuil neutre ω* = {100 / N:.2f})")

say("\n   Le même générateur, à d'autres formats. « ω moyen minimal » est la")
say("   borne inférieure atteignable à couverture équilibrée : Σ C(cₓ,2)/C(n,2).")
say("   k    n    ω max   ω moyen   minimal   ω*      couverture")
for k, n in ((10, 8), (10, 12), (10, 16), (8, 10), (6, 13), (5, 16), (4, 20)):
    pf2 = portfolio(k, n)
    o2 = [len(set(pf2[i]) & set(pf2[j]))
          for i in range(n) for j in range(i + 1, n)]
    cover = {}
    for g in pf2:
        for x in g:
            cover[x] = cover.get(x, 0) + 1
    base, rem = divmod(n * k, N)
    lo = (rem * comb(base + 1, 2) + (N - rem) * comb(base, 2)) / comb(n, 2)
    say(f"   {k:<4} {n:<4} {max(o2):<7} {np.mean(o2):<9.3f} {lo:<9.3f} "
        f"{k * k / N:<7.2f} {min(cover.values())}–{max(cover.values())} fois")
    assert max(o2) < k, "une grille se répète"

say("""
   Réserve honnête. Ce portefeuille ne prédit AUCUN numéro et ne prétend pas
   le faire : le théorème d'invariance interdit cela et n'a pas été mis en
   défaut. Il réorganise la mise pour que, à coût et à espérance égaux, la
   probabilité de toucher le rang plein soit multipliée par n — et pour que,
   sur un rang partagé, l'espérance elle-même augmente. C'est une brèche
   dans le mur, pas une porte : elle ne rend pas le jeu favorable, elle rend
   un jeu donné strictement meilleur qu'un autre de même prix.""")

rule(f"total {time.time() - T0:.0f}s")
