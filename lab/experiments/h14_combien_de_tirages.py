"""h14 — combien de tirages ordonnés faut-il, et lesquels faut-il capturer ?

La question, et pourquoi elle est la bonne
-------------------------------------------
h12 a montré qu'une attaque par le rang ordonné récupère un générateur à
constantes inconnues, et que sur les cinq tirages disponibles elle ne trouve
rien. Mais elle a aussi montré une chose gênante : cinq tirages ne laissent
pas UN générateur, ils en laissent une classe de 8 à 17. Autrement dit,
même si l'attaque avait mordu, la prédiction n'aurait pas forcément été
unique.

D'où la question que ce fichier tranche, et qui est la seule dont la réponse
change ce qu'il faut FAIRE : combien de tirages ordonnés faut-il pour que la
solution soit unique — et l'espacement des tirages capturés change-t-il
quelque chose ?

C'est une question de plan d'expérience, pas de mathématiques nouvelles.
Elle a une réponse chiffrée, et cette réponse est un protocole de collecte.

Ce qui fait varier le résultat
-------------------------------
Le nombre de vérifications INDÉPENDANTES, et lui seul. Pour le modèle A,
le trio à écart constant consomme deux équations pour définir (A, C) : sur
n tirages il ne reste donc que n−3 contrôles indépendants, chacun valant
un facteur M' ≈ 10³⁶ contre une solution fausse. Le solveur explore
≈ 40³ × relèvements ≈ 2²² candidats ; il faut donc n−3 ≥ 1 pour que la
classe se referme, et davantage pour qu'elle se referme sur un seul élément.

Les modèles B et C n'ont pas cette dépense : leur équation y = a·x + c vit
À L'INTÉRIEUR d'un tirage, donc chaque tirage supplémentaire est un
contrôle net.

L'espacement, lui, n'agit pas sur le compte mais sur la FAISABILITÉ : le
modèle A exige trois tirages également espacés. Des captures d'espacements
quelconques peuvent le rendre inapplicable — ce qui, sur le terrain, est
une consigne : capturer des tirages CONSÉCUTIFS ne coûte rien et garantit
l'applicabilité.
"""

import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ordered import (MP, POOL, DRAWN, N128, make_draws, next_order,
                     order_rank, order_unrank, rank_of, solve_a, solve_b,
                     solve_c)

T0 = time.time()
LCG128 = ("Knuth 128", 47026247687942121848144207491837523525,
          117397592171526113268558934119004209487)
LCG64 = ("MMIX / PCG", 6364136223846793005, 1442695040888963407)
LCG32 = ("Numerical Recipes", 1664525, 1013904223)
SEED128 = 0x0123456789ABCDEF0123456789ABCDEF
SEED64 = 0x0123456789ABCDEF
SEED32 = 0x89ABCDEF


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def offsets(kind: str, n: int) -> list:
    """Les schémas de capture qu'un opérateur humain peut réellement viser."""
    if kind == "consécutifs":
        return list(range(n))
    if kind == "pas 2":
        return [2 * i for i in range(n)]
    if kind == "pas 3":
        return [3 * i for i in range(n)]
    if kind == "réel":
        base = [0, 3, 5, 7, 8]
        out = base[:n] if n <= 5 else base + list(range(9, 9 + n - 5))
        return out
    rnd = random.Random(1000 + n)
    out, cur = [0], 0
    for _ in range(n - 1):
        cur += rnd.randint(1, 4)
        out.append(cur)
    return out


def regular_run(offs) -> bool:
    g = [offs[i + 1] - offs[i] for i in range(len(offs) - 1)]
    return any(g[i] == g[i + 1] for i in range(len(g) - 1))


CAP = 64


def verdict(sols, want, pred_fn):
    """(taille de classe, unanime ?, la vraie prédiction est-elle dedans ?)"""
    if not sols:
        return 0, False, False
    preds = {tuple(pred_fn(r)) for r in sols}
    return len(sols), len(preds) == 1, tuple(want) in preds


def cell(size, uni, good):
    if size == 0:
        return "rien"
    tag = "OK" if uni and good else ("~" if good else "X")
    return (f">={size}{tag}" if size >= CAP else f"{size}{tag}")


# --------------------------------------------------------------------------
# 1. Modèle A — le plus exigeant, et le seul sensible à l'espacement
# --------------------------------------------------------------------------

rule("1. MODÈLE A — LCG 128 bits, une sortie par tirage")
say("   « classe » = générateurs distincts reproduisant TOUS les rangs observés.")
say("   « unanime » = tous prédisent le même tirage suivant. C'est le critère")
say("   qui compte : une classe de 3 unanime prédit aussi bien qu'une classe de 1.")

name, a, c = LCG128
for mapping in ("mod", "floor"):
    say(f"\n   réduction « {mapping} »")
    say("   schéma        n=3     n=4     n=5     n=6     n=7     n=8")
    for kind in ("consécutifs", "pas 2", "pas 3", "réel", "aléatoires"):
        cells = []
        for n in range(3, 9):
            offs = offsets(kind, n)
            if not regular_run(offs):
                cells.append("inapp.")
                continue
            d, s_after = make_draws(a, c, SEED128, offs, mapping, 1, 128, True)
            want = order_unrank(rank_of((a * s_after + c) % N128, mapping))
            sols = solve_a(d, mapping, collect=True, runs_limit=1)
            size, uni, good = verdict(
                sols, want,
                lambda r: order_unrank(rank_of((r["a"] * r["last"] + r["c"])
                                               % N128, mapping)))
            cells.append(cell(size, uni, good))
        say(f"   {kind:<13} " + "  ".join(f"{x:<6}" for x in cells))

say("\n   OK = classe unanime et juste   ~ = juste mais non unanime")
say("   X = la vraie solution n'est pas dans la classe")
say("   >=64 = plafond d'énumération atteint, la classe est plus grande encore")
say("   inapp. = pas de trio à écart constant, le modèle A ne s'applique pas")


# --------------------------------------------------------------------------
# 2. Modèles B et C — l'équation vit dans le tirage
# --------------------------------------------------------------------------

rule("2. MODÈLES B ET C — chaque tirage est un contrôle net")

for label, (nm, a, c), seed, w, bits, solver in (
        ("B  LCG 64 bits, 2 sorties", LCG64, SEED64, 2, 64, solve_b),
        ("C  LCG 32 bits, 4 sorties", LCG32, SEED32, 4, 32, solve_c)):
    say(f"\n   {label} — {nm}")
    say("   schéma        n=1     n=2     n=3     n=4     n=5     n=6")
    for kind in ("consécutifs", "réel", "aléatoires"):
        cells = []
        for n in range(1, 7):
            offs = offsets(kind, n)
            d, s_after = make_draws(a, c, seed, offs, "floor", w, bits, True)
            want = next_order(a, c, s_after, "floor", w, bits, True)
            sols = solver(d, "floor", True, collect=True)
            size, uni, good = verdict(
                sols, want,
                lambda r: next_order(r["a"], r["c"], r["last"], "floor",
                                     w, bits, True))
            cells.append(cell(size, uni, good))
        say(f"   {kind:<13} " + "  ".join(f"{x:<6}" for x in cells))


# --------------------------------------------------------------------------
# 3. Le compte de faux positifs ne remonte pas quand n baisse
# --------------------------------------------------------------------------

rule("3. TÉMOIN NÉGATIF À CHAQUE n — le risque de conclure à tort")

say("   Un protocole qui exige moins de tirages ne vaut que si le risque de")
say("   fausse récupération n'explose pas. Suites uniformes, aucun générateur.")
rnd = random.Random(4242)
say("\n   n    modèle A (mod)   modèle A (floor)   modèle B   modèle C")
for n in range(3, 9):
    offs = offsets("consécutifs", n)
    fa = {"mod": 0, "floor": 0}
    fb = fc = 0
    reps = 3
    for _ in range(reps):
        d = [(o, order_rank(rnd.sample(range(1, POOL + 1), DRAWN)))
             for o in offs]
        for mapping in ("mod", "floor"):
            if solve_a(d, mapping, collect=True, runs_limit=1):
                fa[mapping] += 1
        if solve_b(d, "floor", True):
            fb += 1
        if solve_c(d, "floor", True):
            fc += 1
    say(f"   {n:<4} {fa['mod']}/{reps:<14} {fa['floor']}/{reps:<16} "
        f"{fb}/{reps:<8} {fc}/{reps}")


# --------------------------------------------------------------------------
# 4. Le protocole
# --------------------------------------------------------------------------

rule("4. CE QU'IL FAUT CAPTURER")

say("""   Trois consignes tombent des tableaux, et aucune n'était devinable
   avant de les avoir faits.

   1. LA PARITÉ DU PAS DÉCIDE DE TOUT — et c'est le résultat le plus net.
      Un pas de 2 ne converge JAMAIS : la classe reste à 24 (ou au-delà du
      plafond) de n = 4 à n = 8, et elle n'est jamais unanime. La raison est
      structurelle : trois tirages à écart 2 ne déterminent que a², et tous
      les tirages suivants étant eux aussi à des décalages PAIRS, aucun
      n'apporte la moindre information sur a lui-même. On peut capturer
      autant de tirages qu'on veut à pas régulier pair, on n'apprend rien de
      plus. Un pas IMPAIR — 1 ou 3 — referme la classe sur 3 à 10 éléments
      unanimes.

      Sur le terrain la consigne est donc : capturer des tirages
      CONSÉCUTIFS. C'est le pas impair le plus simple à viser, c'est le plus
      convergent des quatre schémas testés (classe 3 à 4), et c'est aussi ce
      que h10 demandait pour le test 2-adique. Une même consigne sert les
      deux.

   2. QUATRE TIRAGES AU MINIMUM, CINQ POUR ÊTRE TRANQUILLE. À n = 3 il ne
      reste ZÉRO vérification indépendante — le trio dépense ses deux
      équations à définir (A, C) — et le §3 le confirme brutalement : sur
      des suites uniformes, la réduction « floor » produit une fausse
      récupération 3 fois sur 3. Ce n'est pas une anomalie, c'est
      l'arithmétique : sans contrôle, tout candidat passe. À partir de
      n = 4, le compte de faux positifs retombe à 0 partout et y reste.

   3. NE PAS VISER PLUS QUE NÉCESSAIRE POUR B ET C. Leur équation
      y = a·x + c vit à l'intérieur d'un tirage : le modèle C se résout et
      se vérifie sur UN SEUL tirage, le modèle B sur DEUX, et la solution y
      est unique d'emblée quel que soit l'espacement. Accumuler des tirages
      pour ces deux familles ne sert à rien.

   Ce que ces trois consignes valent ensemble : cinq tirages consécutifs
   couvrent les trois modèles, avec une classe unanime pour le plus exigeant
   et un risque de fausse récupération nul. Les cinq tirages réellement
   capturés (écarts 3, 2, 2, 1) sont un schéma « réel » : ils marchent, mais
   ils laissent une classe de 8 à 17 là où cinq tirages consécutifs
   laisseraient 3 ou 4.

   Réserve. Tout ceci dit combien de tirages il faudrait POUR IDENTIFIER un
   générateur de ces familles. Cela ne dit pas qu'il y en a un : les cinq
   tirages réels n'ont rien donné, et rien ici ne le contredit. Le protocole
   sert à ce que, le jour où une attaque mordrait, la prédiction soit
   unique — pas à rendre plus probable qu'elle morde.""")

rule(f"total {time.time() - T0:.0f}s")
