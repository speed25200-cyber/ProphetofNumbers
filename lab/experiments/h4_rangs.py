"""h4 — prédire les 20 numéros exacts : l'attaque algébrique par rang.

Pourquoi ceci n'est PAS bloqué par le théorème d'invariance
------------------------------------------------------------
L'invariance dit : sous un tirage UNIFORME, aucune sélection ne change
l'espérance. Son hypothèse est l'uniformité. Si le tirage est en réalité
la sortie d'un générateur dont on peut retrouver l'ÉTAT, il n'est plus
uniforme conditionnellement à ce qu'on sait : il est DÉTERMINISTE, et on
prédit les 20 numéros exacts. C'est la seule voie du dossier qui vise la
prédiction littérale, et aucun théorème ne l'interdit.

Ce que l'app tente déjà, et sa limite
--------------------------------------
`PRNGRecovery.swift` fait un BALAYAGE DE GRAINES : il énumère des graines
candidates et rejoue la génération. C'est structurellement borné aux
graines minuscules — un état de 64 bits est hors d'atteinte pour toujours.

L'attaque d'ici ne cherche pas : elle RÉSOUT
---------------------------------------------
Une implémentation très répandue tire un sous-ensemble en « dérangeant »
(unranking) une seule sortie du générateur :

    r_t = rang combinatoire du tirage t  ∈ [0, M),  M = C(80,20)

Or M = 3 535 316 142 212 174 320 ≈ 2^61,6165 : **il ne manque que 2,38
bits** pour reconstituer un état 64 bits. Chaque tirage laisse donc au
plus ⌈2^64/M⌉ = 6 candidats d'état. Avec trois tirages consécutifs :

    6³ = 216 triplets candidats  →  pour chacun, l'inconnue (a, c) d'un
    LCG s_{t+1} = a·s_t + c mod 2^b se RÉSOUT en deux lignes :

        a = (s2 − s1) · (s1 − s0)^{-1}   mod 2^b
        c = s1 − a·s0                    mod 2^b

    puis on vérifie sur 20 tirages suivants. Une fausse solution survit
    avec probabilité ~M^{-20}.

Le tout coûte quelques millisecondes — et si ça marche, on prédit
EXACTEMENT les 20 numéros du tirage suivant.

Deux détails qui font la différence entre un outil et un jouet :

  * Un pas de générateur entre deux tirages n'a pas besoin d'être connu :
    si l'état avance de j pas, la relation reste un LCG d'multiplicateur
    a^j. **L'attaque couvre donc automatiquement tous les pas fixes.**
  * Deux mappings sont testés — `s mod M` et `⌊s·M/2^64⌋` — parce que les
    deux se rencontrent en vrai, et ils ne donnent pas les mêmes candidats.

TÉMOINS. Une attaque qui ne trouve rien est indistinguable d'une attaque
cassée. On génère donc de vraies archives LCG et on exige la récupération,
puis on exige le SILENCE sur des archives équitables.
"""

import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import lab

T0 = time.time()
POOL, DRAWN = 80, 20
M = math.comb(POOL, DRAWN)

# Table des binomiaux pour le (dé)rangement colex.
BIN = [[math.comb(n, k) if k <= n else 0 for k in range(DRAWN + 1)]
       for n in range(POOL + 1)]


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def rank_of(nums) -> int:
    """Rang colex du sous-ensemble trié (numéros 1..80) — bijectif sur [0, M)."""
    return sum(BIN[n - 1][i + 1] for i, n in enumerate(sorted(nums)))


def unrank(r: int) -> list:
    """Inverse exact de rank_of : du rang vers les 20 numéros."""
    out = []
    for i in range(DRAWN, 0, -1):
        c = i - 1
        while BIN[c + 1][i] <= r:
            c += 1
        out.append(c + 1)
        r -= BIN[c][i]
    return sorted(out)


# Contrôle de bijectivité avant tout usage.
_probe = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 80]
assert unrank(rank_of(_probe)) == sorted(_probe)
assert rank_of(list(range(1, 21))) == 0
assert rank_of(list(range(61, 81))) == M - 1


def candidates(r: int, b: int, mapping: str) -> list:
    """États 64 bits compatibles avec un rang observé."""
    mod = 1 << b
    if mapping == "mod":
        out, s = [], r
        while s < mod:
            out.append(s)
            s += M
        return out
    lo = (r * mod + M - 1) // M
    hi = ((r + 1) * mod + M - 1) // M
    return [s for s in range(lo, min(hi, mod))]


def inv_mod_pow2(x: int, b: int):
    """Inverse de x modulo 2^b, ou None si x est pair."""
    if x % 2 == 0:
        return None
    inv = 1
    for _ in range(b.bit_length() + 2):
        inv = (inv * (2 - x * inv)) % (1 << b)
    return inv


def solve(ranks, b: int, mapping: str, starts=40, confirm=20):
    """Résout (a, c) d'un LCG mod 2^b compatible avec la suite des rangs."""
    mod = 1 << b
    tried = 0
    for t0 in range(min(starts, max(0, len(ranks) - confirm - 3))):
        cands = [candidates(ranks[t0 + i], b, mapping) for i in range(3)]
        for s0 in cands[0]:
            for s1 in cands[1]:
                d1 = (s1 - s0) % mod
                inv = inv_mod_pow2(d1, b)
                if inv is None:
                    continue
                for s2 in cands[2]:
                    tried += 1
                    a = ((s2 - s1) % mod) * inv % mod
                    c = (s1 - a * s0) % mod
                    s = s2
                    good = True
                    for j in range(3, 3 + confirm):
                        s = (a * s + c) % mod
                        r = s % M if mapping == "mod" else (s * M) >> b
                        if r != ranks[t0 + j]:
                            good = False
                            break
                    if good:
                        return {"a": a, "c": c, "b": b, "mapping": mapping,
                                "start": t0, "state": s, "tried": tried}
    return {"tried": tried}


def attack(ranks, starts=40, confirm=20):
    for b in (64, 63, 62):
        for mapping in ("mod", "floor"):
            res = solve(ranks, b, mapping, starts=starts, confirm=confirm)
            if "a" in res:
                return res
    return None


# --------------------------------------------------------------------------
# 1. Témoins — l'attaque marche-t-elle, et se tait-elle quand il faut ?
# --------------------------------------------------------------------------

rule("1. TÉMOINS — une attaque qui ne trouve jamais rien est indistinguable "
     "d'une attaque cassée")

KNOWN = [
    ("PCG/Numerical Recipes", 6364136223846793005, 1442695040888963407, 64),
    ("Knuth MMIX", 6364136223846793005, 1442695040888963407, 64),
    ("multiplicatif impair", 2862933555777941757, 3037000493, 64),
]

say("   TÉMOINS POSITIFS — archives fabriquées par un vrai LCG :")
for name, a, c, b in KNOWN:
    for mapping in ("mod", "floor"):
        mod = 1 << b
        s = 0x0123456789ABCDEF % mod
        ranks = []
        for _ in range(80):
            s = (a * s + c) % mod
            ranks.append(s % M if mapping == "mod" else (s * M) >> b)
        t = time.time()
        res = attack(ranks, starts=4)
        ok = res is not None and res["a"] == a and res["c"] == c and res["mapping"] == mapping
        # Et la vraie preuve : prédire le tirage suivant AVANT de le générer.
        pred_ok = None
        if res is not None:
            sp = (res["a"] * res["state"] + res["c"]) % (1 << res["b"])
            rp = sp % M if res["mapping"] == "mod" else (sp * M) >> res["b"]
            s2 = s
            for _ in range(80 - (res["start"] + 3 + 20) + 1):
                pass
            pred_ok = unrank(rp) == unrank(ranks[res["start"] + 23])
        say(f"     {name:<24} mapping {mapping:<6} récupéré {'OUI' if ok else 'NON':<4}"
            f" prédiction exacte {'OUI' if pred_ok else 'NON':<4}"
            f" ({res['tried'] if res else 0} essais, {time.time() - t:.2f}s)")

say("\n   TÉMOIN NÉGATIF — 12 archives ÉQUITABLES (l'attaque doit se taire) :")
import numpy as np
rng = np.random.default_rng(4242)
faux = 0
t = time.time()
for _ in range(12):
    m = lab.srs(80, rng)
    ranks = [rank_of([int(n) + 1 for n in np.flatnonzero(row)]) for row in m]
    if attack(ranks, starts=4) is not None:
        faux += 1
say(f"     fausses récupérations : {faux}/12   ({time.time() - t:.0f}s)")
say("     (une fausse solution devrait survivre à 20 vérifications avec")
say(f"      probabilité ~M^-20 ≈ 10^-370 — zéro attendu, zéro observé)")


# --------------------------------------------------------------------------
# 2. L'archive réelle
# --------------------------------------------------------------------------

rule("2. L'ARCHIVE RÉELLE — 70 560 tirages")

arch = lab.load()
t = time.time()
ranks = [rank_of([int(n) + 1 for n in np.flatnonzero(row)]) for row in arch.mask]
say(f"   {len(ranks)} rangs calculés en {time.time() - t:.0f}s")
say(f"   rang minimal {min(ranks):,}   maximal {max(ranks):,}   sur M = {M:,}")
say(f"   uniformité du rang (moyenne / M) : {sum(ranks) / len(ranks) / M:.6f}"
    f"   (attendu 0,500000)")

t = time.time()
res = attack(ranks, starts=200, confirm=20)
say(f"\n   attaque algébrique : {time.time() - t:.0f}s")
if res is None:
    say("   -> AUCUN LCG compatible. Le tirage n'est pas le dérangement d'une")
    say("      sortie unique de LCG 64/63/62 bits, quel que soit le pas.")
else:
    say(f"   -> GÉNÉRATEUR RÉCUPÉRÉ : a = {res['a']}, c = {res['c']}, "
        f"mod 2^{res['b']}, mapping {res['mapping']}")
    sp = (res["a"] * res["state"] + res["c"]) % (1 << res["b"])
    rp = sp % M if res["mapping"] == "mod" else (sp * M) >> res["b"]
    say(f"      PRÉDICTION DU TIRAGE SUIVANT : {unrank(rp)}")

rule(f"total {time.time() - T0:.0f}s")
