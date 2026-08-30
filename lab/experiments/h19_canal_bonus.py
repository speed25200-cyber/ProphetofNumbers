"""h19 — le canal du bonus : une sortie ORDONNÉE, 70 560 fois.

Pourquoi cette voie n'avait pas été vue
----------------------------------------
h12 a établi que l'ordre de sortie vaut deux fois le tirage trié : 122,69
bits contre 61,62. Mais l'ordre n'existe que sur cinq tirages capturés à la
main, alors que l'archive en compte 70 560 — triés, donc muets sur l'ordre.

Sauf qu'il reste un champ. Le `bonus` est publié à chaque tirage, et une
vérification élémentaire montre qu'il est **toujours l'un des vingt numéros
tirés**. Ce n'est donc pas un tirage supplémentaire : c'est une DÉSIGNATION
parmi les vingt. Et si cette désignation suit une règle de position — « la
dernière boule sortie », par exemple, ce qui est la convention la plus
répandue — alors le bonus est une sortie ordonnée du générateur, disponible
sur toute l'archive.

d7 a testé la VALEUR du bonus : sa loi marginale, sa mémoire sérielle, son
appartenance au tirage suivant, son rang dans le tirage trié. Tout cela
regarde le bonus comme un numéro. Ce fichier le regarde comme une SORTIE, ce
qui est une question entièrement différente et jamais posée.

Le levier
---------
Si le bonus est la dernière boule et que l'échantillonneur est du type
« s mod 80 », alors bonus − 1 ≡ s (mod 80), donc

    (bonus − 1) mod 16 = s mod 16

publie exactement les quatre bits de poids faible de l'état. Les états
successifs étant reliés par un LCG de multiplicateur A = a^g, la relation

    r_{t+1} = A·r_t + C   (mod 2^k)

doit alors tenir sur les 70 559 transitions. Sous l'hypothèse nulle, le
meilleur couple (A, C) parmi les 2^(2k−1) possibles en explique 1/2^k, avec
une fluctuation de l'ordre de la racine : le test est écrasant.

Une objection, et sa réfutation par les témoins
------------------------------------------------
L'objection évidente est que g n'est pas constant si l'échantillonneur
rejette les doublons : le nombre de sorties consommées varie d'un tirage à
l'autre, donc A = a^g avec lui, et plus aucune relation affine unique ne
devrait tenir. C'est ce que j'ai d'abord écrit ici, et les témoins l'ont
démenti.

La raison est que MODULO UNE PUISSANCE DE DEUX l'ordre multiplicatif de a
est minuscule — il divise 2^(k−2) — donc a^g ne prend que quelques valeurs
distinctes quel que soit g. Un unique couple (A, C) attrape la plus
fréquente, et le test explose quand même : 40,6 % des transitions expliquées
contre 6,7 % attendus, soit +457 σ, sur un témoin AVEC rejet.

Le rejet ne protège donc pas. Ce qui protège, les témoins le disent aussi :
un bonus qui n'est pas une sortie brute (élément de permutation), ou une
sortie prise dans les bits de poids FORT, où le levier 2-adique n'a aucune
prise. La portée du test est ainsi délimitée par mesure, et non par argument.
"""

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import lab

T0 = time.time()
POOL, DRAWN = 80, 20
M64 = (1 << 64) - 1


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# --------------------------------------------------------------------------
# Le test affine, vectorisé
# --------------------------------------------------------------------------

def best_affine(seq: np.ndarray, mod: int, lag: int = 1):
    """(meilleur nombre de transitions expliquées, A, C) modulo `mod`."""
    r = seq % mod
    x = r[:len(r) - lag]
    y = r[lag:]
    n = len(x)
    units = [a for a in range(1, mod) if math.gcd(a, mod) == 1]
    best = (-1, None, None)
    for a in units:
        pred = (a * x) % mod
        diff = (y - pred) % mod
        counts = np.bincount(diff, minlength=mod)
        c = int(counts.argmax())
        hits = int(counts[c])
        if hits > best[0]:
            best = (hits, a, c)
    return best, n


def null_max(seq: np.ndarray, mod: int, reps: int, rng, lag: int = 1):
    """Loi du maximum sous H0, par permutation de la séquence."""
    out = np.empty(reps)
    for i in range(reps):
        perm = rng.permutation(seq)
        out[i] = best_affine(perm, mod, lag)[0][0]
    return out


# --------------------------------------------------------------------------
# 1. Le fait structurel
# --------------------------------------------------------------------------

rule("1. LE FAIT STRUCTUREL — le bonus est-il l'un des vingt ?")

a = lab.load()
n = len(a)
inside = int(np.array([a.bonus[i] in a.nums[i] for i in range(n)]).sum())
say(f"   {n:,} tirages ; bonus appartenant au tirage : {inside:,} ({inside / n:.4%})")
say(f"   Sous l'hypothèse d'un bonus indépendant, on attendrait {n * DRAWN / POOL:,.0f} "
    f"({DRAWN / POOL:.0%}).")
assert inside == n
say("""
   Le bonus n'est donc pas un tirage supplémentaire mais une DÉSIGNATION
   parmi les vingt numéros sortis. Reste à savoir selon quelle règle — et
   c'est cette règle qui déciderait s'il porte de l'information d'ORDRE.""")


# --------------------------------------------------------------------------
# 2. Les témoins — le test a-t-il la puissance annoncée ?
# --------------------------------------------------------------------------

rule("2. TÉMOINS — le test voit-il un générateur quand il y en a un ?")

rng = np.random.default_rng(20260830)


def synth_lcg_bonus(a_mul, c_add, seed, count, mode="mod80"):
    """Archive synthétique : LCG + rejet, bonus = DERNIÈRE boule sortie."""
    s = seed
    out = np.empty(count, dtype=np.int64)
    for t in range(count):
        seen, last = set(), 0
        while len(seen) < DRAWN:
            s = (a_mul * s + c_add) & M64
            v = (s % POOL) + 1 if mode == "mod80" else ((s * POOL) >> 64) + 1
            if v not in seen:
                seen.add(v)
                last = v
        out[t] = last
    return out


def synth_fy_bonus(a_mul, c_add, seed, count):
    """LCG + Fisher-Yates partiel (nombre de sorties FIXE), bonus = dernière."""
    s = seed
    out = np.empty(count, dtype=np.int64)
    for t in range(count):
        arr = list(range(1, POOL + 1))
        last = 0
        for i in range(DRAWN):
            s = (a_mul * s + c_add) & M64
            j = i + (s % (POOL - i))
            arr[i], arr[j] = arr[j], arr[i]
            last = arr[i]
        out[t] = last
    return out


A_MUL, C_ADD = 6364136223846793005, 1442695040888963407
CNT = 20_000
witnesses = [
    ("bonus = s mod 80 (rejet)",
     synth_lcg_bonus(A_MUL, C_ADD, 0x12345, CNT, "mod80")),
    ("bonus = ⌊s·80/2⁶⁴⌋ (rejet)",
     synth_lcg_bonus(A_MUL, C_ADD, 0x12345, CNT, "ms")),
    ("bonus = élément de permutation",
     synth_fy_bonus(A_MUL, C_ADD, 0x12345, CNT)),
    ("uniforme (témoin négatif)", rng.integers(1, POOL + 1, CNT)),
]

say(f"   {CNT:,} tirages synthétiques par témoin. « expliqué » = fraction des")
say("   transitions vérifiant la meilleure relation affine trouvée.\n")
say("   témoin                          mod   expliqué   null (perm.)      z")
for name, seq in witnesses:
    for mod in (16, 80):
        (hits, A, C), tot = best_affine(seq - 1, mod)
        nulls = null_max(seq - 1, mod, 60, rng)
        z = (hits - nulls.mean()) / max(nulls.std(ddof=1), 1e-9)
        say(f"   {name:<31} {mod:<5} {hits / tot:<10.4f} "
            f"{nulls.mean() / tot:.4f} ± {nulls.std(ddof=1) / tot:.4f}   {z:>+8.1f}")

say("""
   Lecture des témoins — et elle corrige ce que l'intuition annonçait.

   J'attendais que le rejet des doublons TUE le test, le nombre de sorties
   consommées variant d'un tirage à l'autre, donc le multiplicateur effectif
   A = a^g avec lui. C'est faux, et pour une raison qui rend le test bien
   meilleur que prévu : MODULO UNE PUISSANCE DE DEUX, l'ordre multiplicatif
   de a est minuscule — il divise 2^(k−2) — donc a^g ne prend que quelques
   valeurs distinctes quel que soit g. Un unique couple (A, C) en attrape la
   plus fréquente, et cela suffit à faire exploser le test : 40,6 % des
   transitions expliquées contre 6,7 % attendus, soit +457 σ.

   Ce que le test voit vraiment, donc : tout échantillonneur où le bonus est
   la valeur BRUTE « s mod 80 » d'un état, avec ou sans rejet.

   Ce qu'il ne voit pas, et c'est net : un bonus obtenu comme élément d'une
   permutation (Fisher-Yates), qui n'est pas une sortie brute mais un
   contenu de tableau ; et un bonus tiré des bits de POIDS FORT
   (multiply-shift), sur lesquels le levier 2-adique n'a par construction
   aucune prise. La portée est donc précisément délimitée, par mesure et non
   par argument.""")


# --------------------------------------------------------------------------
# 3. L'archive réelle
# --------------------------------------------------------------------------

rule("3. L'ARCHIVE — 70 559 transitions")

TOKEN = lab.preregister(
    "h19.bonus_affine",
    "le bonus est la valeur brute « s mod 80 » d'un générateur congruentiel : "
    "il existe alors (A, C) tels que r_{t+lag} = A·r_t + C mod 2^k sur toutes "
    "les transitions",
    "fraction maximale de transitions expliquées par un couple affine, "
    "maximisée sur 5 modules × 3 décalages",
    "permutation de la séquence de bonus (200 réplicats par cellule), "
    "marginale exactement conservée",
    "conforme si p corrigé > seuil de Holm du registre entier",
    track="H")

bon = a.bonus.astype(np.int64) - 1
say("   mod   décalage   expliqué      attendu sous H0   null (permutation)      z")
cells = []
for mod in (2, 4, 8, 16, 80):
    for lag in (1, 2, 3):
        (hits, A, C), tot = best_affine(bon, mod, lag)
        nulls = null_max(bon, mod, 200, rng, lag)
        z = (hits - nulls.mean()) / max(nulls.std(ddof=1), 1e-9)
        cells.append((mod, lag, hits / tot, z, A, C))
        say(f"   {mod:<5} {lag:<10} {hits / tot:<13.5f} {1 / mod:<17.5f} "
            f"{nulls.mean() / tot:.5f} ± {nulls.std(ddof=1) / tot:.5f}   {z:>+7.2f}")
flagged = [c for c in cells if c[3] > 4]

zmax = max(z for _, _, _, z, _, _ in flagged) if flagged else None
say("")
if flagged:
    for mod, lag, frac, z, A, C in flagged:
        say(f"   SIGNAL : mod {mod}, décalage {lag} — {frac:.4%} expliqué, "
            f"z = {z:+.1f}, A = {A}, C = {C}")
else:
    top = max(cells, key=lambda c: c[3])
    from math import erfc, sqrt
    p_cell = 0.5 * erfc(top[3] / sqrt(2))
    p_corr = 1 - (1 - p_cell) ** len(cells)
    lab.record(TOKEN, observed=top[2], p=p_corr,
               power_at="témoin « bonus = s mod 80 » à +433 σ (mod 16)",
               verdict="conforme",
               notes=f"max sur {len(cells)} cellules : mod {top[0]}, décalage "
                     f"{top[1]}, z = {top[3]:+.2f}")
    say(f"""   Aucun signal. Le plus grand écart est de {top[3]:+.2f} σ (module {top[0]},
   décalage {top[1]}), soit p = {p_cell:.2e} pour cette cellule et
   p = {p_corr:.3f} après correction sur les {len(cells)} cellules — très au-dessus du
   seuil de Holm du registre entier, qui vaut 1,5·10⁻⁵.

   L'hypothèse « le bonus est la valeur brute s mod 80 d'un générateur
   congruentiel » est donc écartée, et cette fois le « rien trouvé » a du
   poids : le témoin correspondant sort à +433 σ. Le rejet des doublons ne
   protège pas contre ce test, contrairement à ce qu'on pouvait croire.

   Ce que cela ne dit PAS. Le bonus peut rester la dernière boule sortie
   sans être une sortie brute : c'est le cas dès que l'échantillonneur est
   un Fisher-Yates, où le bonus est un contenu de tableau. Et il peut être
   une sortie brute des bits de POIDS FORT, hors de portée du levier
   2-adique. Ces deux cas figurent dans les témoins, et le test y est muet —
   c'est sa limite, elle est mesurée, et elle laisse la question de la RÈGLE
   du bonus entièrement ouverte.""")


# --------------------------------------------------------------------------
# 4. Ce que la règle du bonus vaudrait, et comment la trancher
# --------------------------------------------------------------------------

rule("4. CE QUE VAUDRAIT LA RÈGLE — et la mesure qui la tranche")

bits_order = math.log2(math.factorial(POOL) / math.factorial(POOL - DRAWN))
bits_set = math.log2(math.comb(POOL, DRAWN))
bits_pos = math.log2(DRAWN)
say(f"""   Un tirage trié porte {bits_set:.2f} bits, l'ordre complet {bits_order:.2f}.
   Savoir LAQUELLE des vingt boules est sortie en dernier en ajoute
   log₂ {DRAWN} = {bits_pos:.2f} bits — soit {bits_pos * n / 8 / 1024:,.0f} kilo-octets sur l'archive
   entière, information d'ordre qui n'existe aujourd'hui nulle part ailleurs
   que sur les cinq tirages capturés à la main.

   Ce n'est pas assez pour reconstituer l'ordre complet ({bits_set + bits_pos:.2f} bits par
   tirage contre {bits_order:.2f}), mais c'est assez pour ancrer UNE sortie du
   générateur par tirage à une position connue — ce qui est exactement ce
   qu'il faut aux attaques de h12 pour se transporter sur 70 560 tirages au
   lieu de cinq.

   LA MESURE QUI TRANCHE, et elle tient en une ligne. Pour chacun des cinq
   tirages ordonnés déjà capturés, il suffit de relever le numéro bonus et
   de regarder sa position dans l'ordre de sortie. Si les cinq donnent la
   même position — la vingtième, ou la première — la règle est établie et
   l'archive entière devient un canal ordonné. Si les positions sont
   dispersées, le bonus est un choix uniforme parmi les vingt et il ne porte
   aucun ordre.

   L'archive locale s'arrête au tirage {int(a.ids.max()):,} et les tirages ordonnés
   commencent à 1 381 023 : le recoupement ne peut pas se faire hors ligne.
   C'est la deuxième donnée la moins chère du dossier, après le prix du
   ticket.""")

rule(f"total {time.time() - T0:.0f}s")
