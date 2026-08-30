"""h11 — l'attaque par réseau sur multiply-shift, et une erreur de h10 corrigée.

L'erreur à corriger d'abord
----------------------------
h10 concluait : « il n'existe aucun point de fonctionnement pour LLL sur
cette famille ». Le raisonnement comparait la marge du réseau (≈ ×18) au
facteur d'approximation de LLL, pris à 2^(d/4) — soit 2¹⁰ en dimension 41.

C'est la borne PIRE CAS, et c'est la mauvaise à utiliser. En pratique LLL
atteint un facteur d'Hermite racine δ₀ ≈ 1,0219, donc un facteur
d'approximation δ₀^d — soit **×2,4 en dimension 40**, pas ×1024. Face à une
marge de ×18, l'attaque est largement dans le domaine du faisable.

h10 se trompait donc, et la seule façon honnête de trancher est d'écrire
l'attaque et de la passer aux témoins.

L'attaque
---------
Hypothèse : Fisher-Yates dont l'indice au pas i est calculé en
multiply-shift, p_i = ⌊s_i·m_i / 2⁶⁴⌋ avec m_i = 80−i, les s_i étant des
sorties consécutives d'un LCG mod 2⁶⁴ de constantes (a, c) connues.

L'ordre publié détermine les p_i par simulation. Chacun borne son état :

    s_i ∈ [⌈p_i·2⁶⁴/m_i⌉, ⌈(p_i+1)·2⁶⁴/m_i⌉)   — largeur ≈ 2⁶⁴/m_i

Avec (a, c) connus, s_i = a^(i)·x + c_i où x = s_1. Chaque contrainte s'écrit
donc (A_i·x − B_i) mod 2⁶⁴ ∈ [0, W_i) : un problème du vecteur le plus proche
dans un réseau de dimension d+1. Babai le résout approximativement.

**LLL propose, l'arithmétique exacte dispose.** Chaque candidat x est rejoué
en entiers exacts contre les 20 numéros observés ; un candidat faux est
rejeté, jamais accepté. La perte de précision de la Gram-Schmidt flottante
est donc sans conséquence sur la correction du résultat.

Si un candidat survit, l'état est connu — et le tirage suivant se prédit
exactement.
"""

import csv
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lll import babai, hermite_factor, lll

T0 = time.time()
POOL, DRAWN = 80, 20
N = 1 << 64
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# --------------------------------------------------------------------------
# Le générateur supposé, et la reconstruction des indices
# --------------------------------------------------------------------------

def ms_draw(a, c, s):
    """Un tirage Fisher-Yates à indice multiply-shift. Rend (ordre, état final)."""
    arr = list(range(1, POOL + 1))
    order = []
    for i in range(DRAWN):
        s = (a * s + c) % N
        p = (s * (POOL - i)) >> 64
        j = i + p
        arr[i], arr[j] = arr[j], arr[i]
        order.append(arr[i])
    return order, s


def fy_indices(order):
    """Les p_i, reconstruits sans ambiguïté depuis l'ordre publié."""
    arr = list(range(1, POOL + 1))
    out = []
    for i, n in enumerate(order):
        j = arr.index(n, i)
        out.append(j - i)
        arr[i], arr[j] = arr[j], arr[i]
    return out


def replay(a, c, x, order):
    """Le candidat x = s_1 reproduit-il EXACTEMENT l'ordre observé ?"""
    arr = list(range(1, POOL + 1))
    s = x
    for i, n in enumerate(order):
        if i:
            s = (a * s + c) % N
        p = (s * (POOL - i)) >> 64
        j = i + p
        if j >= POOL:
            return False
        arr[i], arr[j] = arr[j], arr[i]
        if arr[i] != n:
            return False
    return True


# --------------------------------------------------------------------------
# Le réseau
# --------------------------------------------------------------------------

def solve_draw(a, c, order, d=DRAWN, extra=6):
    """Cherche x = s_1 compatible avec l'ordre. Rend x ou None."""
    p = fy_indices(order)[:d]
    m = [POOL - i for i in range(d)]
    L = [(p[i] * N + m[i] - 1) // m[i] for i in range(d)]
    W = [((p[i] + 1) * N + m[i] - 1) // m[i] - L[i] for i in range(d)]
    W = [max(1, w) for w in W]

    # s_i = A_i·x + C_i  (mod N), avec A_0 = 1, C_0 = 0.
    A, C = [1], [0]
    for _ in range(1, d):
        A.append(A[-1] * a % N)
        C.append((C[-1] * a + c) % N)

    lam = [N // W[i] for i in range(d)]
    dim = d + 1
    basis = [[0] * dim for _ in range(dim)]
    basis[0][0] = 1
    for i in range(d):
        basis[0][i + 1] = lam[i] * A[i] % (lam[i] * N)
        basis[i + 1][i + 1] = lam[i] * N
    target = [N // 2] + [lam[i] * ((L[i] + W[i] // 2 - C[i]) % N) for i in range(d)]

    v, _ = babai(basis, target)
    base_x = v[0]
    # Babai rend un point proche ; on balaie quelques décalages entiers autour
    # de x, puis on VÉRIFIE exactement. Un faux candidat est rejeté.
    for off in range(-extra, extra + 1):
        x = (base_x + off) % N
        if replay(a, c, x, order):
            return x
    return None


# --------------------------------------------------------------------------
# 1. LLL fonctionne-t-il ?
# --------------------------------------------------------------------------

rule("1. CONTRÔLE DE L'OUTIL — LLL réduit-il vraiment ?")
say("   Base « connue difficile » : un réseau de q-ary aléatoire, dim 12.")
import random
rnd = random.Random(7)
q = 1 << 32
dimq = 12
bq = [[0] * dimq for _ in range(dimq)]
for i in range(dimq):
    bq[i][i] = q if i else 1
for j in range(1, dimq):
    bq[0][j] = rnd.randrange(q)
t = time.time()
red = lll(bq)
before = min(math.sqrt(sum(float(x) ** 2 for x in r)) for r in bq)
after = min(math.sqrt(sum(float(x) ** 2 for x in r)) for r in red)
say(f"   plus court vecteur : {before:.3e} avant, {after:.3e} après"
    f"   (gain ×{before / after:.1f})   [{time.time() - t:.1f}s]")
say(f"   facteur d'Hermite racine empirique : {hermite_factor(bq):.4f}"
    f"   (attendu ≈ 1,02 pour LLL)")


# --------------------------------------------------------------------------
# 2. Témoins de l'attaque
# --------------------------------------------------------------------------

rule("2. TÉMOINS — l'attaque récupère-t-elle un générateur qu'elle connaît ?")

# Multiplicateurs 64 bits publiés : Knuth (MMIX et la table de TAOCP vol. 2),
# L'Ecuyer 1999, PCG, et la sélection spectrale de Steele & Vigna 2021.
MULTIPLIERS = [
    ("MMIX / PCG", 6364136223846793005),
    ("L'Ecuyer 64", 2862933555777941757),
    ("Knuth 3935", 3935559000370003845),
    ("Steele-Vigna d134", 0xD134_2543_DE82_EF95),
    ("Steele-Vigna af25", 0xAF25_1AF3_B0F0_25B5),
    ("Steele-Vigna ff1c", 0xFF1C_D035_980C_D3EF),
    ("Steele-Vigna 2c6f", 0x2C6F_E96E_E78B_6955),
    ("Steele-Vigna 369d", 0x369D_EA0F_31A5_3F85),
    ("nombre d'or", 0x9E37_79B9_7F4A_7C15),
    ("Numerical Recipes", 0x27BB_2EE6_87B0_B0FD),
]
# Incréments : les trois formes qu'on rencontre en pratique.
INCREMENTS = [("+1", 1),
              ("Weyl", 1442695040888963407),
              ("classique", 1013904223)]

KNOWN = [(f"{ma} {ic}", a, c)
         for ma, a in MULTIPLIERS for ic, c in INCREMENTS]
# Les témoins n'ont pas besoin de la liste entière — trois suffisent, et
# le balayage complet est réservé aux données réelles.
CONTROLS = [("MMIX / PCG", 6364136223846793005, 1442695040888963407),
            ("L'Ecuyer 64", 2862933555777941757, 3037000493),
            ("Knuth 3935", 3935559000370003845, 2691343689449507681)]

say("   TÉMOINS POSITIFS — tirages fabriqués en « LCG + Fisher-Yates "
    "multiply-shift » :")
ok_pos = 0
tot_pos = 0
for name, a, c in CONTROLS:
    s = 0x0123456789ABCDEF
    hits, preds = 0, 0
    for _ in range(3):
        order, s_after = ms_draw(a, c, s)
        t = time.time()
        x = solve_draw(a, c, order)
        tot_pos += 1
        if x is not None:
            hits += 1
            ok_pos += 1
            # Prédiction du tirage SUIVANT depuis l'état retrouvé.
            s_end = x
            for _ in range(DRAWN - 1):
                s_end = (a * s_end + c) % N
            nxt_true, _ = ms_draw(a, c, s_after)
            nxt_pred, _ = ms_draw(a, c, s_end)
            if nxt_pred == nxt_true:
                preds += 1
        s = s_after
    say(f"     {name:<16} récupéré {hits}/3   prédiction exacte du suivant "
        f"{preds}/3   ({time.time() - t:.1f}s/tirage)")

say("\n   TÉMOIN NÉGATIF — ordres uniformes (aucun générateur derrière) :")
rnd2 = random.Random(99)
faux = 0
for _ in range(6):
    order = rnd2.sample(range(1, POOL + 1), DRAWN)
    if solve_draw(CONTROLS[0][1], CONTROLS[0][2], order) is not None:
        faux += 1
say(f"     fausses récupérations : {faux}/6")

if ok_pos == 0:
    say("\n   -> L'ATTAQUE NE RÉCUPÈRE MÊME PAS SON PROPRE TÉMOIN.")
    say("      Elle n'est donc pas applicable aux données réelles : un « rien")
    say("      trouvé » ne voudrait rien dire. C'est le résultat, et il est")
    say("      négatif sur l'outil, pas sur l'archive.")


# --------------------------------------------------------------------------
# 3. Les données réelles
# --------------------------------------------------------------------------

if ok_pos > 0:
    rule("3. LES TIRAGES ORDONNÉS RÉELS")
    rows = []
    with open(os.path.join(ROOT, "draws_ordered.csv")) as fh:
        for row in csv.DictReader(fh):
            rows.append((int(row["id"]),
                         [int(row[f"o{i}"]) for i in range(1, DRAWN + 1)]))
    rows.sort()
    say(f"   balayage : {len(rows)} tirages × {len(KNOWN)} jeux de constantes "
        f"({len(MULTIPLIERS)} multiplicateurs × {len(INCREMENTS)} incréments)")
    found = []
    t = time.time()
    for did, order in rows:
        for name, a, c in KNOWN:
            x = solve_draw(a, c, order)
            if x is not None:
                found.append((did, name, x))
                say(f"   {did} — {name} : ÉTAT RETROUVÉ x = {x}")
        say(f"     {did} : rien   ({time.time() - t:.0f}s cumulés)")
    if not found:
        say(f"\n   {len(rows)} tirages × {len(KNOWN)} jeux de constantes : "
            f"aucun état compatible.")
        say("   L'hypothèse « LCG à constantes connues + Fisher-Yates")
        say("   multiply-shift » est écartée sur les tirages disponibles.")

rule(f"total {time.time() - T0:.0f}s")
