"""h21 — les générateurs à sortie INVERSIBLE sous le rang ordonné.

La case que h12 n'a pas couverte
---------------------------------
h12 a testé trois modèles de source sous le rang ordonné, et les trois
supposent une récurrence AFFINE de l'état : s → a·s + c. C'est ce qui permet
d'y résoudre (a, c) au lieu de les énumérer.

Un générateur à sortie inversible échappe à ce cadre. splitmix64 avance son
état par une simple addition — s → s + γ, avec γ = 0x9E3779B97F4A7C15 fixé
et PUBLIC — mais sa sortie est un mélange non affine de l'état. Le solveur
de h12, qui cherche une relation affine entre les VALEURS PUBLIÉES, ne peut
donc rien en faire. Idem pour xorshift64*, dont l'état avance par des
décalages-xor et dont la sortie est une multiplication par une constante
impaire.

Or ces deux-là sont précisément les générateurs qu'on choisit aujourd'hui
quand on veut quelque chose de rapide et de moderne sans dépendance.

Le levier, et il est brutal
----------------------------
Sous le rang ordonné, un tirage publie 122,69 bits — assez pour contenir
DEUX sorties de 64 bits (théorème des deux états, h12). Et si la sortie est
inversible, chaque moitié se retourne en un état EXACT.

D'où un test qui tient en une ligne d'arithmétique : inverser les deux
moitiés, et vérifier que les deux états obtenus sont bien consécutifs.

    splitmix64   s₂ − s₁ doit valoir γ, une constante publique
    xorshift64*  s₂ doit valoir xorshift(s₁), une fonction publique

Il n'y a RIEN à résoudre, rien à énumérer, aucune constante à deviner : la
vérification est immédiate, et un seul tirage suffit. Sur ~40 candidats de
rang par tirage, la probabilité qu'un faux passe vaut 40·2⁻⁶⁴ ≈ 2·10⁻¹⁸.

C'est le test le moins cher et le plus décisif de tout le dossier — et il
manquait.
"""

import csv
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ordered import (DRAWN, MP, N128, POOL, candidates, order_rank,
                     order_unrank, rank_of, split_words)

T0 = time.time()
M64 = (1 << 64) - 1
GAMMA = 0x9E3779B97F4A7C15
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# --------------------------------------------------------------------------
# Les deux générateurs, et l'inversion exacte de leur sortie
# --------------------------------------------------------------------------

C1, C2 = 0xBF58476D1CE4E5B9, 0x94D049BB133111EB
C1_INV = pow(C1, -1, 1 << 64)
C2_INV = pow(C2, -1, 1 << 64)
XS_MUL = 2685821657736338717
XS_INV = pow(XS_MUL, -1, 1 << 64)


def unxorshift(y: int, shift: int) -> int:
    """Inverse de y = x ^ (x >> shift).

    En substituant x = y ^ (x >> s) dans elle-même jusqu'à épuisement du
    registre, il vient x = y ^ (y>>s) ^ (y>>2s) ^ (y>>3s) ^ … — les
    décalages avancent d'un PAS CONSTANT s, non par doublement. Écrire
    `out = x ^ (out >> s)` avec s qui double donne une fonction d'apparence
    plausible et fausse partout, ce que seul un aller-retour vérifie."""
    x = y
    sh = shift
    while sh < 64:
        x ^= y >> sh
        sh += shift
    return x & M64


def splitmix_out(s: int) -> int:
    z = (s + GAMMA) & M64
    z = ((z ^ (z >> 30)) * C1) & M64
    z = ((z ^ (z >> 27)) * C2) & M64
    return z ^ (z >> 31)


def splitmix_state_from_out(o: int) -> int:
    """L'état AVANT l'incrément, retrouvé depuis la sortie."""
    z = unxorshift(o, 31)
    z = (z * C2_INV) & M64
    z = unxorshift(z, 27)
    z = (z * C1_INV) & M64
    z = unxorshift(z, 30)
    return (z - GAMMA) & M64


def xs64s_step(x: int) -> int:
    x ^= x >> 12
    x = (x ^ (x << 25)) & M64
    x ^= x >> 27
    return x


def xs64s_out(x: int):
    y = xs64s_step(x)
    return y, (y * XS_MUL) & M64


def xs64s_state_from_out(o: int) -> int:
    """L'état APRÈS le pas de xorshift, retrouvé depuis la sortie."""
    return (o * XS_INV) & M64


# --------------------------------------------------------------------------
# Contrôle des inversions
# --------------------------------------------------------------------------

rule("0. CONTRÔLE — les inversions sont-elles exactes ?")

import random
rnd = random.Random(2026)
bad_sm = bad_xs = bad_ux = 0
for _ in range(4000):
    x = rnd.randrange(1 << 64)
    for sh in (11, 27, 30, 31):
        if unxorshift(x ^ (x >> sh), sh) != x:
            bad_ux += 1
    s = rnd.randrange(1 << 64)
    if splitmix_state_from_out(splitmix_out(s)) != s:
        bad_sm += 1
    y, o = xs64s_out(rnd.randrange(1, 1 << 64))
    if xs64s_state_from_out(o) != y:
        bad_xs += 1
say(f"   inverse de x ^= x>>k sur 16 000 essais : {bad_ux} échec(s)")
say(f"   splitmix64  sortie -> état, 4 000 essais : {bad_sm} échec(s)")
say(f"   xorshift64* sortie -> état, 4 000 essais : {bad_xs} échec(s)")
assert bad_ux == bad_sm == bad_xs == 0


# --------------------------------------------------------------------------
# Le test
# --------------------------------------------------------------------------

def check_draw(rank: int, mapping: str) -> list:
    """Rend les hypothèses compatibles avec un tirage ordonné isolé."""
    out = []
    for R in candidates(rank, mapping):
        for be in (True, False):
            w1, w2 = split_words(R, 2, 64, be)
            # splitmix64 : deux sorties consécutives => états distants de γ.
            s1 = splitmix_state_from_out(w1)
            s2 = splitmix_state_from_out(w2)
            if (s2 - s1) & M64 == GAMMA:
                out.append(("splitmix64", mapping, be, s1))
            # xorshift64* : le second état est le pas de xorshift du premier.
            x1 = xs64s_state_from_out(w1)
            x2 = xs64s_state_from_out(w2)
            if xs64s_step(x1) == x2:
                out.append(("xorshift64*", mapping, be, x1))
    return out


rule("1. TÉMOINS — le test voit-il un générateur quand il y en a un ?")

say("""   Tirages fabriqués en « générateur à sortie inversible + dérangement
   d'une valeur de 128 bits », c'est-à-dire exactement le modèle que h12
   testait pour les LCG et qui manquait pour ceux-ci.\n""")
say("   générateur     réduction   ordre   détecté   hypothèses retenues")
found_ok = 0
for name in ("splitmix64", "xorshift64*"):
    for mapping in ("mod", "floor"):
        for be in (True, False):
            seed = 0x0123456789ABCDEF
            if name == "splitmix64":
                o1 = splitmix_out(seed)
                o2 = splitmix_out((seed + GAMMA) & M64)
            else:
                y1, o1 = xs64s_out(seed)
                _, o2 = xs64s_out(y1)
            words = [o1, o2] if be else [o2, o1]
            R = (words[0] << 64) | words[1]
            if mapping == "mod":
                r = R % MP
            else:
                r = (R * MP) >> 128
            hits = [h for h in check_draw(r, mapping) if h[0] == name]
            ok = len(hits) >= 1
            found_ok += 1 if ok else 0
            say(f"   {name:<14} {mapping:<11} {'BE' if be else 'LE':<7} "
                f"{'OUI' if ok else 'NON':<9} {len(check_draw(r, mapping))}")

say(f"\n   -> {found_ok}/8 configurations détectées.")

say("\n   TÉMOIN NÉGATIF — ordres uniformes, aucun générateur derrière :")
faux = 0
tot = 0
for _ in range(60):
    seq = rnd.sample(range(1, POOL + 1), DRAWN)
    r = order_rank(seq)
    for mapping in ("mod", "floor"):
        tot += 1
        if check_draw(r, mapping):
            faux += 1
say(f"     fausses détections : {faux}/{tot}")
say(f"     attendu : ~{60 * 2 * 4 * 40 * 2 / 2 ** 64:.1e} — le test ne peut "
    f"pratiquement pas se tromper")


# --------------------------------------------------------------------------
# 2. Les tirages réels
# --------------------------------------------------------------------------

rule("2. LES CINQ TIRAGES ORDONNÉS RÉELS")

rows = []
with open(os.path.join(ROOT, "draws_ordered.csv")) as fh:
    for row in csv.DictReader(fh):
        rows.append((int(row["id"]),
                     [int(row[f"o{i}"]) for i in range(1, DRAWN + 1)]))
rows.sort()

total = 0
for did, order in rows:
    r = order_rank(order)
    hits = []
    for mapping in ("mod", "floor"):
        hits.extend(check_draw(r, mapping))
    total += len(hits)
    say(f"   tirage {did} : {len(hits)} hypothèse(s) compatible(s)"
        + ("   " + str(hits[:3]) if hits else ""))

rule("3. VERDICT")
if total:
    say(f"   {total} hypothèse(s) survivent — à vérifier sur les autres tirages.")
else:
    say("""   Aucune hypothèse compatible, sur les cinq tirages, les deux
   réductions et les deux ordres d'octets.

   La famille « générateur à sortie inversible + dérangement d'une valeur de
   128 bits » est donc écartée. C'était la case que h12 laissait vide : ses
   trois modèles supposaient une récurrence affine de l'état, ce que ni
   splitmix64 ni xorshift64* ne présentent au niveau de leurs SORTIES.

   Et ce test-ci n'a rien eu à résoudre ni à énumérer. Il inverse deux
   moitiés de rang et vérifie une identité publique — γ pour splitmix64, le
   pas de xorshift pour l'autre. Un seul tirage suffisait ; il y en a eu
   cinq.""")

rule(f"total {time.time() - T0:.0f}s")
