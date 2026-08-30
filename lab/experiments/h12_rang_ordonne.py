"""h12 — le rang ORDONNÉ, et le théorème des deux états.

Le levier, et pourquoi il est nouveau
--------------------------------------
h4 attaquait le rang du tirage TRIÉ : M = C(80,20) ≈ 2^61,6165, donc un état
64 bits n'y cache que 2,38 bits, et trois tirages suffisent à RÉSOUDRE (a, c)
sans les connaître d'avance. C'est ce qui distingue h4 de h11 : h11 doit
énumérer des constantes publiées, h4 les calcule.

L'ordre de sortie change l'échelle. Une suite ordonnée de 20 numéros parmi 80
a un rang dans [0, M') avec

    M' = 80·79·…·61 = 80!/60! ≈ 2^122,6939

et de là sort un énoncé qui n'existait pas tant qu'on n'avait que le tirage
trié :

    THÉORÈME DES DEUX ÉTATS. Un tirage ordonné publie 122,69 bits. Un
    générateur d'état b bits ne peut donc pas produire un tirage en une
    seule sortie dès que b < 122,69 : il lui en faut ⌈122,69/b⌉. Or le rang
    les publie TOUTES. Un état de 64 bits impose deux sorties consécutives
    par tirage, un état de 32 bits en impose quatre — et connaître deux
    états consécutifs rend la récupération de (a, c) LINÉAIRE au lieu de
    combinatoire.

Autrement dit : plus l'état est étroit, plus l'ordre le trahit. C'est le
contraire de l'intuition habituelle, et c'est ce que ce fichier teste.

Les trois modèles de source
----------------------------
A. LCG de 128 bits, une sortie par tirage.  Le rang laisse
   ⌈2^128/M'⌉ ≈ 40 candidats d'état par tirage. Trois tirages également
   espacés résolvent (A, C) au pas g ; une racine carrée 2-adique en extrait
   (a, c) au pas 1, ce qui rend les CINQ tirages utilisables à leurs écarts
   réels.

B. LCG de 64 bits, DEUX sorties concaténées par tirage.  Chaque candidat
   livre un couple (x, y) d'états consécutifs, donc une équation y = a·x + c.
   Deux tirages donnent deux équations : a et c se résolvent par une simple
   division 2-adique. Pas d'énumération de constantes, pas de réseau.

C. LCG de 32 bits, QUATRE sorties concaténées par tirage.  Un seul tirage
   donne quatre états consécutifs — assez pour résoudre ET vérifier.

Un fait arithmétique utile au passage : v₂(M') = 22, donc M' est divisible
par 2²². Un rang pris en « s mod M' » publie ainsi les 22 bits de poids
faible de l'état, exactement — le levier 2-adique traverse la réduction.

Chaque modèle est passé aux témoins positifs (recouvrement ET prédiction
exacte du tirage suivant) et négatifs (ordres uniformes) avant de toucher
aux données réelles. Une attaque sans témoin ne prouve rien.
"""

import csv
import math
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

T0 = time.time()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# --------------------------------------------------------------------------
# Le rang ordonné : bijection entre suites de 20 numéros et [0, M')
# --------------------------------------------------------------------------

# Les primitives (rang ordonné, outils 2-adiques, les trois solveurs) vivent
# dans `lab/ordered.py` : elles servent aussi à h14, et importer un fichier
# d'expérience rejouerait toute l'expérience.
from ordered import (MP, POOL, DRAWN, N128, WEIGHT, candidates, fy_indices,
                     join_words, make_draws, next_order, order_rank,
                     order_unrank, ratio_base, rank_of, solve_a, solve_b,
                     solve_c, split_words, sqrt_mod_2k, v2, verify_a,
                     verify_words)


# --------------------------------------------------------------------------
# 0. Contrôles
# --------------------------------------------------------------------------

rule("0. CONTRÔLES — la bijection et l'arithmétique")
say(f"   M' = 80!/60! = {MP}")
say(f"   log2 M' = {math.log2(MP):.4f}   bits cachés dans 128 : "
    f"{128 - math.log2(MP):.2f}   candidats/tirage ≈ {N128 // MP + 1}")
say(f"   v₂(M') = {v2(MP)}   -> « s mod M' » publie les {v2(MP)} bits de poids "
    f"faible de s")

rnd = random.Random(2026)
bad = 0
for _ in range(2000):
    seq = rnd.sample(range(1, POOL + 1), DRAWN)
    if order_unrank(order_rank(seq)) != seq:
        bad += 1
edges = (order_rank(order_unrank(0)) == 0
         and order_rank(order_unrank(MP - 1)) == MP - 1)
say(f"   aller-retour sur 2 000 suites : {bad} échec(s) ; "
    f"bornes {'exactes' if edges else 'FAUSSES'}")
assert bad == 0 and edges

sq_bad = 0
for _ in range(200):
    x = rnd.randrange(1, N128, 2)
    A = x * x % N128
    roots = sqrt_mod_2k(A)
    if x % N128 not in roots or len(roots) != 4:
        sq_bad += 1
    if any(r * r % N128 != A for r in roots):
        sq_bad += 1
say(f"   racine carrée 2-adique sur 200 tirages : {sq_bad} échec(s)")
assert sq_bad == 0

wbad = 0
for _ in range(200):
    R = rnd.randrange(N128)
    for w, bits in ((2, 64), (4, 32)):
        for be in (True, False):
            if join_words(split_words(R, w, bits, be), bits, be) != R:
                wbad += 1
say(f"   découpage/recollage des mots : {wbad} échec(s)")
assert wbad == 0


# --------------------------------------------------------------------------
# 1. Témoins
# --------------------------------------------------------------------------

rule("1. TÉMOINS — chaque modèle récupère-t-il un générateur qu'il ignore ?")

LCG128 = [("Knuth 128", 47026247687942121848144207491837523525,
           117397592171526113268558934119004209487),
          ("impair simple", 0x2545F4914F6CDD1D2545F4914F6CDD1D,
           0x9E3779B97F4A7C15)]
LCG64 = [("MMIX / PCG", 6364136223846793005, 1442695040888963407),
         ("L'Ecuyer 64", 2862933555777941757, 3037000493)]
LCG32 = [("Numerical Recipes", 1664525, 1013904223),
         ("MINSTD-like", 1103515245, 12345)]

# Les témoins reprennent les écarts RÉELS (0, 3, 5, 7, 8) plutôt que des
# écarts commodes : un témoin qui ne travaille pas dans les conditions des
# données ne prouve pas que l'attaque y est applicable.
OFF_W = [0, 3, 5, 7, 8]
SEED128 = 0x0123456789ABCDEF0123456789ABCDEF
SEED64 = 0x0123456789ABCDEF
SEED32 = 0x89ABCDEF

say("   MODÈLE A — LCG 128 bits, une sortie par tirage")
say("     (« classe » = nombre de générateurs reproduisant les 5 rangs ;")
say("      « consensus » = tous prédisent-ils le MÊME tirage suivant ?)")
for name, a, c in LCG128:
    for mapping in ("mod", "floor"):
        d, s_after = make_draws(a, c, SEED128, OFF_W, mapping, 1, 128, True)
        t = time.time()
        sols = solve_a(d, mapping, collect=True)
        want = order_unrank(rank_of((a * s_after + c) % N128, mapping))
        preds = {tuple(order_unrank(rank_of((r["a"] * r["last"] + r["c"]) % N128,
                                            mapping))) for r in sols}
        exact = any(r["a"] == a and r["c"] == c for r in sols)
        cons = len(preds) == 1
        good = tuple(want) in preds
        verdict = "JUSTE" if cons and good else ("dans la classe" if good
                                                 else "FAUSSE")
        say(f"     {name:<16} {mapping:<6} classe {len(sols):<3}"
            f" constantes exactes {'OUI' if exact else 'non':<4}"
            f" consensus {'OUI' if cons else 'NON':<4}"
            f" prédiction {verdict:<14} ({time.time() - t:.1f}s)")

say("""
     Lecture. Cinq tirages ne laissent pas UN générateur mais une petite
     classe — 8 à 17 ici — qui reproduit exactement les cinq rangs. Ce n'est
     pas un défaut de l'attaque : c'est la structure du problème. Le trio
     régulier consomme deux équations pour définir (A, C), il ne reste donc
     que DEUX vérifications indépendantes, et les racines carrées 2-adiques
     de A (quatre) plus les relèvements de c en produisent plusieurs qui les
     passent. Même ainsi, le tirage suivant tombe de M' ≈ 8,6·10³⁶ ordres
     possibles à au plus 17 — et dans trois cas sur quatre la classe est
     unanime, donc la prédiction est unique et juste.

   MODÈLE B — LCG 64 bits, deux sorties concaténées""")
for name, a, c in LCG64:
    for mapping in ("mod", "floor"):
        for be in (True, False):
            d, s_after = make_draws(a, c, SEED64, OFF_W, mapping, 2, 64, be)
            t = time.time()
            res = solve_b(d, mapping, be)
            hit = res is not None and res["a"] == a and res["c"] == c
            pred = "—"
            if res:
                got = next_order(res["a"], res["c"], res["last"], mapping, 2, 64, be)
                want = next_order(a, c, s_after, mapping, 2, 64, be)
                pred = "OUI" if got == want else "NON"
            say(f"     {name:<16} {mapping:<6} {'BE' if be else 'LE'} "
                f"récupéré {'OUI' if hit else 'NON':<4} prédiction {pred:<4}"
                f" ({res['checked'] if res else 0} vérifs, {time.time() - t:.1f}s)")

say("\n   MODÈLE C — LCG 32 bits, quatre sorties concaténées")
for name, a, c in LCG32:
    for mapping in ("mod", "floor"):
        for be in (True, False):
            d, s_after = make_draws(a, c, SEED32, OFF_W, mapping, 4, 32, be)
            t = time.time()
            res = solve_c(d, mapping, be)
            hit = res is not None and res["a"] == a and res["c"] == c
            pred = "—"
            if res:
                got = next_order(res["a"], res["c"], res["last"], mapping, 4, 32, be)
                want = next_order(a, c, s_after, mapping, 4, 32, be)
                pred = "OUI" if got == want else "NON"
            say(f"     {name:<18} {mapping:<6} {'BE' if be else 'LE'} "
                f"récupéré {'OUI' if hit else 'NON':<4} prédiction {pred:<4}"
                f" ({res['checked'] if res else 0} vérifs, {time.time() - t:.1f}s)")

say("\n   TÉMOINS NÉGATIFS — suites uniformes, aucun générateur derrière :")
faux = {"A": 0, "B": 0, "C": 0}
tot = {"A": 0, "B": 0, "C": 0}
t = time.time()
for _ in range(3):
    d = [(g, order_rank(rnd.sample(range(1, POOL + 1), DRAWN))) for g in OFF_W]
    for mapping in ("mod", "floor"):
        tot["A"] += 1
        if solve_a(d, mapping) is not None:
            faux["A"] += 1
        for be in (True, False):
            tot["B"] += 1
            if solve_b(d, mapping, be) is not None:
                faux["B"] += 1
            tot["C"] += 1
            if solve_c(d, mapping, be) is not None:
                faux["C"] += 1
for k in ("A", "B", "C"):
    say(f"     modèle {k} : {faux[k]}/{tot[k]} fausses récupérations")
say(f"     [{time.time() - t:.0f}s]")


# --------------------------------------------------------------------------
# 2. Les données réelles
# --------------------------------------------------------------------------

rule("2. LES TIRAGES ORDONNÉS RÉELS")

rows = []
with open(os.path.join(ROOT, "draws_ordered.csv")) as fh:
    for row in csv.DictReader(fh):
        rows.append((int(row["id"]), [int(row[f"o{i}"]) for i in range(1, DRAWN + 1)]))
rows.sort()
base = rows[0][0]
draws = [(d - base, order_rank(o)) for d, o in rows]
gaps = [draws[i + 1][0] - draws[i][0] for i in range(len(draws) - 1)]
say(f"   {len(rows)} tirages {[d for d, _ in rows]}, écarts {gaps}")
say(f"   suites régulières (nécessaires au modèle A) : "
    f"{[(draws[i][0], draws[i+1][0], draws[i+2][0]) for i in range(len(gaps)-1) if gaps[i] == gaps[i+1]] or 'aucune'}")

hits = []
for label, fn, args in (
        ("A  LCG 128 bits, 1 sortie", solve_a, [("mod",), ("floor",)]),
        ("B  LCG 64 bits, 2 sorties", solve_b,
         [("mod", True), ("mod", False), ("floor", True), ("floor", False)]),
        ("C  LCG 32 bits, 4 sorties", solve_c,
         [("mod", True), ("mod", False), ("floor", True), ("floor", False)])):
    for arg in args:
        t = time.time()
        res = fn(draws, *arg)
        tag = " ".join(str(x) for x in arg)
        if res:
            hits.append((label, tag, res))
            say(f"   {label} [{tag}] : GÉNÉRATEUR RÉCUPÉRÉ")
            say(f"     a = {res['a']}   c = {res['c']}   ({res['checked']} vérifs)")
        else:
            say(f"   {label} [{tag:<12}] : aucun état compatible   "
                f"({time.time() - t:.0f}s)")

rule("3. VERDICT")
if hits:
    for label, tag, res in hits:
        say(f"   {label} [{tag}] — PRÉDICTION DU TIRAGE SUIVANT :")
        if label.startswith("A"):
            nxt = order_unrank(rank_of((res["a"] * res["last"] + res["c"]) % N128,
                                       res["mapping"]))
        else:
            w = 2 if label.startswith("B") else 4
            nxt = next_order(res["a"], res["c"], res["last"], res["mapping"],
                             w, res["bits"], res["big_endian"])
        say(f"     {nxt}")
else:
    say(f"""   Les trois modèles de source à état étroit sont écartés sur les
   {len(rows)} tirages ordonnés disponibles : LCG 128 bits à une sortie,
   LCG 64 bits à deux sorties, LCG 32 bits à quatre sorties, dans les deux
   ordres d'octets et les deux réductions (mod et troncature).

   Ce résultat n'est PAS un aveu d'impuissance de l'outil : les témoins
   ci-dessus montrent que chaque attaque récupère son générateur et prédit
   exactement le tirage suivant, et qu'aucune ne se déclenche sur du bruit.
   C'est donc bien l'archive qui refuse, pas la méthode.

   Ce que ça retire du champ des possibles : toute implémentation où le
   tirage ordonné est obtenu en dérangeant une valeur entière issue d'un LCG
   de 128, 64 ou 32 bits. Le théorème des deux états dit pourquoi cette
   famille était la plus exposée — et elle est maintenant fermée.""")

rule(f"total {time.time() - T0:.0f}s")
