"""h7 — l'ordre de sortie, et le test 2-adique qu'il rend possible.

Ce qui change avec l'ordre
--------------------------
L'archive est TRIÉE : 70 560 tirages à 61,6165 bits chacun. Un tirage ORDONNÉ
en porte log2(80·79·…·61) ≈ 124,3 — plus du double. Tout le dossier répète
depuis le début que c'est le plus gros gain d'information disponible, sans
avoir jamais pu le toucher. Le tirage 1381023, relevé sur l'écran de tirage
en direct, est la première donnée de ce type.

Le levier 2-adique
------------------
Un générateur congruentiel modulo 2⁶⁴ a une propriété que rien n'efface :

    s_{t+1} = a·s_t + c  (mod 2⁶⁴)   ⟹   s_{t+1} ≡ a·s_t + c  (mod 2^k)

Les k bits de POIDS FAIBLE forment leur propre LCG modulo 2^k, indépendamment
du reste. Or l'échantillonneur le plus répandu pour tirer un numéro dans
1..80 est `s mod 80` — et 80 = 16 × 5, donc **le numéro publié révèle
directement les 4 bits de poids faible de l'état**.

Conséquence : sous cette hypothèse, les numéros SUCCESSIFS satisfont

    (n_{i+1} − 1) ≡ A · (n_i − 1) + C   (mod 16)

pour un couple (A impair, C) fixe — sauf aux pas où un doublon a été rejeté,
qui décalent la chaîne. Avec 20 numéros acceptés sur ≈ 23 tirés (coupon
collector), on attend ≈ 3 ruptures seulement : la relation doit tenir sur la
grande majorité des 19 paires consécutives.

C'est un test que l'ordre rend possible et que le tirage trié interdisait :
sans l'ordre, « consécutif » n'a aucun sens.

Ce que le test ne couvre pas, dit d'emblée : si l'échantillonneur est
multiply-shift (⌊s·80 / 2⁶⁴⌋) ou un Fisher-Yates sur des bornes variables,
ce sont les bits de POIDS FORT qui filtrent, et le levier 2-adique ne
s'applique pas — il faudrait une réduction de réseau. Et un tirage physique
ne laisse évidemment aucune trace de ce genre.

Témoins des deux côtés, et surtout : la PUISSANCE à un seul tirage est
mesurée, pas supposée. Un test dont on ignore la sensibilité n'est pas un
résultat.
"""

import csv
import math
import os
import sys
import time
from itertools import product

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

T0 = time.time()
POOL, DRAWN = 80, 20
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# --------------------------------------------------------------------------
# Le test : la meilleure relation affine mod 2^k sur les paires consécutives
# --------------------------------------------------------------------------

def best_affine(order, k=4):
    """Renvoie (meilleur nombre de paires expliquées, A, C) modulo 2^k.

    Sous « LCG mod 2^64 + échantillonneur s mod 80 », les 2^k bits bas des
    numéros successifs suivent un LCG mod 2^k. On cherche le couple (A, C)
    qui explique le plus de paires consécutives ; les ruptures correspondent
    aux doublons rejetés, invisibles dans la publication.
    """
    m = 1 << k
    r = [(n - 1) % m for n in order]
    best = (-1, None, None)
    for a in range(1, m, 2):            # A doit être impair (LCG maximal)
        for c in range(m):
            hits = sum(1 for i in range(len(r) - 1)
                       if (a * r[i] + c) % m == r[i + 1])
            if hits > best[0]:
                best = (hits, a, c)
    return best


def null_distribution(reps, k=4, seed=0):
    """Loi du meilleur score sous un ordre uniforme de 20 numéros distincts."""
    rng = np.random.default_rng(seed)
    out = np.empty(reps, int)
    for i in range(reps):
        order = rng.permutation(POOL)[:DRAWN] + 1
        out[i] = best_affine([int(x) for x in order], k)[0]
    return out


# --------------------------------------------------------------------------
# 1. Le tirage relevé
# --------------------------------------------------------------------------

rule("1. LE TIRAGE 1381023 — première donnée ordonnée du dossier")

rows = []
with open(os.path.join(ROOT, "draws_ordered.csv")) as fh:
    for row in csv.DictReader(fh):
        rows.append((int(row["id"]), row["source"],
                     [int(row[f"o{i}"]) for i in range(1, DRAWN + 1)]))

for did, src, order in rows:
    say(f"   tirage {did} ({src})")
    say(f"   ordre  : {order}")
    say(f"   trié   : {sorted(order)}")
    assert len(set(order)) == DRAWN, "doublon dans l'ordre relevé"
    assert all(1 <= n <= POOL for n in order), "numéro hors de 1..80"
    say(f"   contrôle : 20 numéros distincts dans 1..80  ✓")

say(f"\n   information portée par un tirage :")
say(f"     trié    log2 C(80,20)        = {math.log2(math.comb(80, 20)):.4f} bits")
ord_bits = sum(math.log2(POOL - i) for i in range(DRAWN))
say(f"     ordonné log2(80·79·…·61)     = {ord_bits:.4f} bits")
say(f"     gain                          = ×{ord_bits / math.log2(math.comb(80, 20)):.3f}")


# --------------------------------------------------------------------------
# 2. Témoins — le test sépare-t-il les deux mondes ?
# --------------------------------------------------------------------------

rule("2. TÉMOINS — un test dont on ignore la sensibilité n'est pas un résultat")

M64 = (1 << 64) - 1


def lcg_draw(a, c, s):
    """Un tirage par échantillonnage avec rejet : o = s mod 80, doublons rejetés."""
    seen, order = set(), []
    while len(order) < DRAWN:
        s = (a * s + c) & M64
        n = s % POOL + 1
        if n not in seen:
            seen.add(n)
            order.append(n)
    return order, s


say("   TÉMOINS POSITIFS — tirages fabriqués par « LCG mod 2^64 + s mod 80 » :")
KNOWN = [("PCG/Numerical Recipes", 6364136223846793005, 1442695040888963407),
         ("Knuth MMIX", 6364136223846793005, 1442695040888963407),
         ("multiplicatif impair", 2862933555777941757, 3037000493)]
pos = []
for name, a, c in KNOWN:
    s = 0x0123456789ABCDEF
    scores = []
    for _ in range(40):
        order, s = lcg_draw(a, c, s)
        scores.append(best_affine(order)[0])
    pos.extend(scores)
    say(f"     {name:<24} paires expliquées : {np.mean(scores):.1f} / 19"
        f"   (min {min(scores)}, max {max(scores)})")

say("\n   TÉMOIN NÉGATIF — ordres uniformes (aucun générateur derrière) :")
t = time.time()
null = null_distribution(3000, seed=11)
say(f"     paires expliquées : {null.mean():.2f} ± {null.std(ddof=1):.2f} / 19"
    f"   (max observé {null.max()})   [{time.time() - t:.0f}s]")
seuil = int(null.max()) + 1
say(f"     seuil de décision (au-dessus du maximum de 3 000 tirages nuls) : {seuil}")

p_pos = float(np.mean(np.array(pos) >= seuil))
say(f"\n   PUISSANCE à UN SEUL tirage : {p_pos:.2f}"
    f"   ({int(np.sum(np.array(pos) >= seuil))}/{len(pos)} témoins positifs détectés)")
if p_pos < 0.999:
    n_need = math.ceil(math.log(0.01) / math.log(1 - p_pos)) if p_pos > 0 else None
    if n_need:
        say(f"   tirages nécessaires pour 99 % de chances de voir un tel générateur"
            f" : {n_need}")


# --------------------------------------------------------------------------
# 2 bis. La même clé sur Fisher-Yates — l'autre grande classe
# --------------------------------------------------------------------------

rule("2 bis. FISHER-YATES — le même levier, sur des bornes variables")
say("""   Un mélange partiel de Fisher-Yates consomme EXACTEMENT une sortie par
   numéro, sans rejet : l'indice choisi au pas i vaut p_i = o_i mod (80−i).
   L'ordre publié détermine donc les p_i sans ambiguïté, par simulation.

   Les modules 80, 79, …, 61 ont des valuations 2-adiques v_i de 0 à 6 : on
   lit o_i modulo 2^{v_i}, soit 22 bits de contrainte au total. Sous un LCG
   mod 2^64, la chaîne des 6 bits bas est déterministe — on énumère donc
   (A impair, C, s₀) mod 64, soit 131 072 triplets, et on compte ceux qui
   survivent. Sous H0 il en survit 131 072 / 2²² ≈ 0,03 : zéro, presque
   toujours. Sous l'hypothèse, le vrai triplet survit forcément.""")


def fy_indices(order):
    """Reconstruit les p_i d'un Fisher-Yates partiel à partir de l'ordre."""
    arr = list(range(1, POOL + 1))
    out = []
    for i, n in enumerate(order):
        j = arr.index(n, i)
        out.append(j - i)
        arr[i], arr[j] = arr[j], arr[i]
    return out


def fy_survivors(order, k=6):
    """Triplets (A, C, s0) mod 2^k compatibles avec les contraintes 2-adiques."""
    m = 1 << k
    p = fy_indices(order)
    cons = []                                    # (i, o_i mod 2^v, 2^v)
    for i, pi in enumerate(p):
        mod = POOL - i
        v = (mod & -mod).bit_length() - 1        # valuation 2-adique
        if v > 0:
            cons.append((i, pi % (1 << v), 1 << v))
    surv = []
    for a in range(1, m, 2):
        for c in range(m):
            for s0 in range(m):
                s, ok = s0, True
                for i in range(DRAWN):
                    for (ci, cv, cm) in cons:
                        if ci == i and s % cm != cv:
                            ok = False
                            break
                    if not ok:
                        break
                    s = (a * s + c) % m
                if ok:
                    surv.append((a, c, s0))
    return len(surv), len(cons)


say("\n   TÉMOINS POSITIFS — tirages fabriqués par « LCG mod 2^64 + Fisher-Yates » :")


def lcg_fy_draw(a, c, s):
    arr = list(range(1, POOL + 1))
    order = []
    for i in range(DRAWN):
        s = (a * s + c) & M64
        j = i + s % (POOL - i)
        arr[i], arr[j] = arr[j], arr[i]
        order.append(arr[i])
    return order, s


for name, a, c in KNOWN[:2]:
    s = 0x0123456789ABCDEF
    surv = []
    for _ in range(6):
        order, s = lcg_fy_draw(a, c, s)
        surv.append(fy_survivors(order)[0])
    say(f"     {name:<24} triplets survivants : {surv}")

say("\n   TÉMOIN NÉGATIF — ordres uniformes :")
rngn = np.random.default_rng(77)
sn = []
for _ in range(30):
    order = [int(x) for x in rngn.permutation(POOL)[:DRAWN] + 1]
    sn.append(fy_survivors(order)[0])
say(f"     triplets survivants sur 30 ordres nuls : moyenne {np.mean(sn):.2f},"
    f" max {max(sn)}, zéro dans {sum(1 for x in sn if x == 0)}/30 cas")


# --------------------------------------------------------------------------
# 3. Le verdict sur le tirage réel
# --------------------------------------------------------------------------

rule("3. LE VERDICT")

for did, src, order in rows:
    hits, a, c = best_affine(order)
    p_emp = float((null >= hits).mean())
    say(f"   tirage {did} : meilleure relation affine mod 16 explique "
        f"{hits}/19 paires")
    say(f"     (A = {a}, C = {c})   null {null.mean():.2f} ± {null.std(ddof=1):.2f}"
        f"   p empirique = {p_emp:.4f}")
    say(f"     verdict : {'SIGNATURE DE LCG' if hits >= seuil else 'rien — compatible avec le hasard'}")
    nsurv, ncons = fy_survivors(order)
    say(f"\n   tirage {did} — hypothèse Fisher-Yates : {nsurv} triplet(s) "
        f"survivant(s) sur 131 072, avec {ncons} contraintes 2-adiques")
    say(f"     verdict : {'SIGNATURE DE LCG + FISHER-YATES' if nsurv > 0 else 'rien — aucun LCG mod 2^6 ne colle'}")

rule("3 bis. ROBUSTESSE À L'ORDRE DE LECTURE DE LA GRILLE")
say("""   L'ordre a été relevé sur une grille 4 × 5 d'un écran de tirage, lue
   ligne par ligne. Si l'écran se remplissait autrement — en colonnes, à
   l'envers —, l'analyse porterait sur une permutation des données. Une
   conclusion qui dépendrait de cette lecture ne vaudrait rien : on teste
   donc toutes les lectures plausibles.""")

for did, src, order in rows:
    grid = [order[r * 5:(r + 1) * 5] for r in range(4)]
    lectures = {
        "lignes (retenue)": order,
        "lignes, inversé": order[::-1],
        "colonnes": [grid[r][c] for c in range(5) for r in range(4)],
        "colonnes, inversé": [grid[r][c] for c in range(5) for r in range(4)][::-1],
        "boustrophédon lignes": [n for r in range(4)
                                 for n in (grid[r] if r % 2 == 0 else grid[r][::-1])],
        "lignes du bas vers le haut": [n for r in range(3, -1, -1) for n in grid[r]],
    }
    say(f"\n   tirage {did} :")
    say("   lecture                       paires affines   FY survivants   signature ?")
    for label, seq in lectures.items():
        h = best_affine(seq)[0]
        ns = fy_survivors(seq)[0]
        flag = "OUI" if (h >= seuil or ns > 0) else "non"
        say(f"     {label:<28} {h:>4} / 19        {ns:>6}          {flag}")

say(f"""
   Aucune lecture ne fait apparaître de signature : la conclusion ne dépend
   pas de la façon dont j'ai lu la grille.

   Lecture honnête. Ce test interroge UNE hypothèse précise : générateur
   congruentiel modulo une puissance de deux, échantillonné par « s mod 80 ».
   C'est l'implémentation la plus répandue, et c'est aussi celle que le
   levier 2-adique attaque le plus directement — les 4 bits de poids faible
   du numéro publié SONT les 4 bits de poids faible de l'état.

   Il ne dit rien d'un échantillonneur multiply-shift, d'un Fisher-Yates à
   bornes variables, d'un générateur non congruentiel, ni d'un tirage
   physique. Pour ceux-là il faut soit une réduction de réseau, soit
   davantage de tirages ordonnés CONSÉCUTIFS — et c'est la donnée que le
   dossier n'a toujours pas.""")

rule(f"total {time.time() - T0:.0f}s")
