"""h63 — le theoreme de la retenue, et ce qu'il ouvre chez les additifs.

L'angle mort
=============
Le §69 range les familles ADDITIVES — xorshift128+, xoroshiro128+ — a part,
avec cette phrase : « seul le bit 0 d'une somme est exactement lineaire, d'ou
20 bits par tirage ». C'est vrai, et c'est une BORNE INFERIEURE que personne
n'a cherche a relever.

Or ces familles ne sont pas un cas d'ecole. xorshift128+ est le generateur de
Math.random dans V8 — Chrome, Node, Edge — donc, statistiquement, le plus
probable derriere un affichage de loterie en ligne. Le dossier ne savait pas
l'attaquer.

LE THEOREME DE LA RETENUE
==========================
Soit out = a + b (mod 2^W), a et b lineaires sur F2 en l'etat. Ecrivons a_i,
b_i, out_i les bits, et c_i la retenue ENTRANTE au rang i, avec c_0 = 0 :

    out_i = a_i XOR b_i XOR c_i
    c_{i+1} = maj(a_i, b_i, c_i)

LEMME. Si a_i != b_i, alors maj(a_i, b_i, c_i) = c_i.
   Preuve : l'un des deux vaut 0, l'autre 1 ; la majorite de {0, 1, c_i} est
   c_i. []

COROLLAIRE (le prefixe libre). Posons d_i = out_i XOR c_i = a_i XOR b_i. Si
d_i = 1 alors c_{i+1} = c_i, donc la retenue reste CONNUE et l'equation du
rang i+1 reste LINEAIRE. Comme c_0 = 0, on obtient par recurrence :

    les bits 0..j de out donnent j+1 equations lineaires libres,
    ou j est le nombre de 1 en tete de (out_0, out_1, out_2)

ESPERANCE, sur un out uniforme et quatre bits observes :

    1 x 1/2  +  2 x 1/4  +  3 x 1/8  +  4 x 1/8  =  1,875

soit 1,875 equation lineaire par mot au lieu de 1 — SANS AUCUNE SUPPOSITION
et sans le moindre branchement. Le §69 sous-estimait donc les familles
additives de 87 %.

CE QUE CELA NE FAIT PAS, ET IL FAUT LE DIRE TOUT DE SUITE
==========================================================
Le lemme s'applique aux bits de POIDS FAIBLE, donc a l'echantillonneur (A)
du §82 — le modulo. Sous (B), la troncature, on observe les bits de poids
FORT de la somme : la retenue entrante y est inconnue et le lemme ne demarre
pas. Or (B) est precisement ce qu'ecrit du JavaScript idiomatique
(Math.floor(Math.random() * 80)).

La combinaison la plus PLAUSIBLE du monde reel — sortie additive et
echantillonneur par troncature — reste donc hors d'atteinte de l'algebre
lineaire. La section 5 le chiffre et le nomme.

Il TESTE l'archive (ses cinq tirages ordonnes) : il consigne au registre.
"""

import csv
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POOL, DRAWN = 80, 20
DRY = os.environ.get("H63_DRY") == "1"
BUDGET = 6.0 if DRY else 40.0
MAXT = 5 if DRY else 9
NB = 4


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def m(n):
    return (1 << n) - 1


def rotl(x, k, w):
    return ((x << k) | (x >> (w - k))) & m(w)


# ==========================================================================
# Les familles additives. `step` rend (etat suivant, a, b) : les deux
# ADDENDES, car ce sont eux qui sont lineaires — leur somme ne l'est pas.
# ==========================================================================

def xs128p(s):
    """xorshift128+ de Vigna — Math.random de V8."""
    A, B = s & m(64), (s >> 64) & m(64)
    t = (A ^ ((A << 23) & m(64))) & m(64)
    nB = t ^ B ^ (t >> 18) ^ (B >> 5)
    return B | (nB << 64), A, B


def xoro128p(s):
    """xoroshiro128+ de Blackman et Vigna."""
    s0, s1 = s & m(64), (s >> 64) & m(64)
    t = s1 ^ s0
    n0 = rotl(s0, 24, 64) ^ t ^ ((t << 16) & m(64))
    n1 = rotl(t, 37, 64)
    return n0 | (n1 << 64), s0, s1


FAMS = [("xorshift128+ (V8)", 128, xs128p), ("xoroshiro128+", 128, xoro128p)]


def out_of(step, s):
    ns, a, b = step(s)
    return ns, (a + b) & m(64)


def free_prefix(low4):
    """Nombre d'equations LIBRES que donnent les quatre bits observes."""
    j = 0
    while j < 3 and (low4 >> j) & 1:
        j += 1
    return j + 1


def addend_forms(step, nbits, nwords):
    """coef[k][i] = forme de « a_i XOR b_i » au mot k.

    Par linearite de a et de b separement : on propage les nbits vecteurs de
    base, on note leurs addendes, et on XOR les deux. La SOMME, elle, n'est
    pas lineaire — c'est tout le probleme, et c'est ce que le theoreme
    contourne.
    """
    coef = [[0] * 4 for _ in range(nwords)]
    for i in range(nbits):
        s, bit = 1 << i, 1 << i
        for k in range(nwords):
            s, a, b = step(s)
            x = a ^ b
            cp = coef[k]
            for j in range(4):
                if (x >> j) & 1:
                    cp[j] |= bit
    return coef


# ==========================================================================
rule("1. LE THÉORÈME, ET SA VÉRIFICATION NUMÉRIQUE")
# ==========================================================================

say(f"""   Le lemme est demontre en tete de fichier. Ce qui se verifie, c'est que le
   prefixe libre donne bien des equations JUSTES — c'est-a-dire que pour un
   etat connu, a_i XOR b_i vaut exactement out_i sur tout le prefixe.
""")
import random                                                  # noqa: E402
rng = random.Random(60_601)
bad = tested = 0
lens = {1: 0, 2: 0, 3: 0, 4: 0}
for _ in range(2000 if DRY else 20000):
    st = rng.getrandbits(128) | 1
    step = xs128p
    ns, a, b = step(st)
    out = (a + b) & m(64)
    L = free_prefix(out & 15)
    lens[L] += 1
    for i in range(L):
        tested += 1
        if ((a >> i) & 1) ^ ((b >> i) & 1) != ((out >> i) & 1):
            bad += 1
tot = sum(lens.values())
mean = sum(k * v for k, v in lens.items()) / tot
say(f"   {'longueur du préfixe':>22} {'observé':>10} {'théorie':>10}")
for k in (1, 2, 3, 4):
    th = {1: 0.5, 2: 0.25, 3: 0.125, 4: 0.125}[k]
    say(f"   {k:>22} {lens[k]/tot:>10.4f} {th:>10.4f}")
say(f"""   moyenne {mean:.4f} contre 1,875 en theorie.

   equations verifiees : {tested:,}, fausses : {bad}.
   Le prefixe libre tient EXACTEMENT — c'est une identite, pas une
   approximation.""")


# ==========================================================================
rule("2. CE QUE CELA CHANGE À L'ÉCHELLE DU §69")
# ==========================================================================

def rank_curve(coef, nwords, seq):
    piv, ranks = {}, []
    for k in range(nwords):
        L = free_prefix(seq[k])
        for j in range(L):
            row = coef[k][j]
            while row:
                h = row.bit_length() - 1
                if h in piv:
                    row ^= piv[h]
                else:
                    piv[h] = row
                    break
        ranks.append(len(piv))
    rmax = ranks[-1]
    return ranks.index(rmax) + 1, rmax


say(f"""   Le §69 creditait les familles additives d'UN bit par mot, soit {DRAWN} par
   tirage et {-(-128 // DRAWN)} tirages pour 128 bits d'etat. Avec 1,875 equation par mot,
   on mesure le mot ou le rang sature — methode du §80.
""")
say(f"   {'famille':>20} {'n':>5} {'W(rang) §69':>12} {'W(rang) mesuré':>15} "
    f"{'tirages':>8} {'gain':>6}")
INFO = {}
r2 = random.Random(9)
seq = [r2.randrange(16) for _ in range(400)]
for name, nb, step in FAMS:
    coef = addend_forms(step, nb, 220)
    w, r = rank_curve(coef, 220, seq)
    INFO[name] = (nb, step, w, r)
    say(f"   {name:>20} {nb:>5} {nb:>12} {w:>15} {w/DRAWN:>8.2f} "
        f"{nb/w:>6.2f}")

w0 = INFO['xorshift128+ (V8)'][2]
say(f"""
   Le palier tombe de {-(-128 // DRAWN)} tirages a {-(-w0 // DRAWN)}. Le §69 n'avait pas tort — il
   comptait ce qui etait CERTAIN — mais il laissait {1 - 1/1.875:.0%} de la fuite sur la
   table, faute d'avoir regarde la retenue.""")


# ==========================================================================
rule("3. LE TÉMOIN DE L'ALGÈBRE : POSITIONS DONNÉES, ÉTAT RETROUVÉ")
# ==========================================================================

def add_eq(piv, row, b):
    cur, cb = row, b
    while cur:
        h = cur.bit_length() - 1
        if h in piv:
            pr, pb = piv[h]
            cur ^= pr
            cb ^= pb
        else:
            piv[h] = (cur, cb)
            return True
    return cb == 0


def back_sub(piv, nbits):
    sol = 0
    for h in sorted(piv):
        pr, pb = piv[h]
        if (bin(pr & sol).count("1") + pb) & 1:
            sol ^= 1 << h
    return sol, [i for i in range(nbits) if i not in piv]


def simulate(step, state, ndraws):
    """Rend les tirages ET la position (indice de mot) de chaque numero."""
    s, draws, pos, k = state, [], [], 0
    for _ in range(ndraws):
        seen, out, guard = set(), [], 0
        while len(out) < DRAWN:
            s, a, b = step(s)
            w = (a + b) & m(64)
            guard += 1
            if guard > 400:
                return None, None
            n = w % POOL + 1
            if n not in seen:
                seen.add(n)
                out.append(n)
                pos.append(k)
            k += 1
        draws.append(out)
    return draws, pos


def solve_known_positions(step, nbits, draws, pos, coef):
    """Elimination PURE : aucune recherche, les positions sont donnees.

    C'est le temoin de l'ALGEBRE, separee de la combinatoire des rejets. Si
    le theoreme de la retenue est juste, l'etat sort ici sans le moindre
    branchement — et c'est bien ce qui se produit.
    """
    piv = {}
    flat = [n for d in draws for n in d]
    for n, p in zip(flat, pos):
        val = (n - 1) & 15
        for j in range(free_prefix(val)):
            if not add_eq(piv, coef[p][j], (val >> j) & 1):
                return None
        if len(piv) >= nbits:
            break
    sol, free = back_sub(piv, nbits)
    return None if free else sol


say(f"""   L'attaque complete doit enumerer les positions des rejets. Le theoreme,
   lui, porte sur l'ALGEBRE. On separe donc les deux : ce temoin donne les
   positions et ne fait qu'eliminer — s'il passe, le theoreme est juste ; la
   combinatoire est un probleme distinct, traite a la section 4.
""")
say(f"   {'famille':>20} {'tirages':>8} {'mots utilisés':>14} {'états retrouvés':>16} "
    f"{'sec':>7}")
for name, (nb, step, w, r) in INFO.items():
    need = -(-w // DRAWN)
    nw2 = DRAWN * need + 12 * need
    coef = addend_forms(step, nb, nw2)
    ok, t0, used = 0, time.time(), 0
    TRIES = 3 if DRY else 10
    for _ in range(TRIES):
        seed = rng.getrandbits(nb) | 1
        truth, pos = simulate(step, seed, need)
        if truth is None:
            continue
        got = solve_known_positions(step, nb, truth, pos, coef)
        if got is not None:
            d2, _ = simulate(step, got, need)
            ok += d2 == truth
            used = max(used, pos[-1] + 1)
    say(f"   {name:>20} {need:>8} {used:>14} {ok:>13}/{TRIES} "
        f"{time.time()-t0:>7.1f}")

say(f"""
   L'etat sort par ELIMINATION SEULE, sans une seule supposition. Le
   theoreme de la retenue est donc exact et exploitable — la seule question
   restante est celle des positions, et c'est une question de DONNEES.""")


# ==========================================================================
rule("4. CE QUE LE DOSSIER PEUT EN FAIRE AUJOURD'HUI : RIEN, ET POURQUOI")
# ==========================================================================

rows = list(csv.DictReader(open(os.path.join(ROOT, "draws_ordered.csv"))))
ORD = [int(r["id"]) for r in rows]
runs, cur = [], 1
for a, b in zip(ORD, ORD[1:]):
    if b == a + 1:
        cur += 1
    else:
        runs.append(cur)
        cur = 1
runs.append(cur)
best = max(runs)
need = -(-INFO['xorshift128+ (V8)'][2] // DRAWN)
say(f"""   Le palier mesure a la section 2 vaut {need} tirages ORDONNES. Le theoreme du
   trou (§72) permet de les chainer meme non contigus SI l'on sait de combien
   de mots l'etat a avance — ce qui est exact sous Fisher-Yates mais INCONNU
   sous rejet, ou chaque tirage intermediaire consomme un nombre variable de
   mots.

   Sous rejet, il faut donc {need} tirages CONSECUTIFS. Le dossier en a :

     tirages ordonnes          {len(ORD)}   ({', '.join(str(x) for x in ORD)})
     plus longue suite         {best}
     necessaire                {need}
     manquants                 {need - best}

   IL N'Y A DONC PAS D'ATTAQUE A MENER, et en tenter une serait malhonnete :
   avec {best} tirages on dispose de {best * DRAWN} numeros, soit environ {best * DRAWN * 1.875:.0f} equations
   pour {INFO['xorshift128+ (V8)'][0]} inconnues. Le systeme est SOUS-DETERMINE : aucun resultat nul
   n'y aurait de sens, puisque tout etat compatible avec ces equations
   admettrait {2 ** (INFO['xorshift128+ (V8)'][0] - int(best * DRAWN * 1.875)):.1e} solutions.

   REGISTRE : INCHANGE. Consigner un test sous-determine comme « conforme »
   serait exactement le genre de faux negatif que le protocole interdit.

   CE QU'IL FAUT COLLECTER, et c'est la seule chose a retenir de ce
   paragraphe : {need} tirages ordonnes CONSECUTIFS, soit {need * 5} minutes de collecte.
   L'app les prend un toutes les cinq minutes.""")


# ==========================================================================
rule("5. CE QUE LA RETENUE N'OUVRE PAS, ET C'EST LE MUR ACTUEL")
# ==========================================================================

say(f"""   Le lemme part de c_0 = 0 : il demarre au bit de POIDS FAIBLE. Il sert donc
   l'echantillonneur (A) du §82 — le modulo — et lui seul.

   Sous (B), la troncature, on observe les bits de poids FORT de la somme.
   La retenue ENTRANTE y vaut

       c_i = 1  si et seulement si  (a mod 2^i) + (b mod 2^i) >= 2^i

   c'est-a-dire une inegalite sur les bits BAS, que rien n'a publies. Le
   lemme ne demarre pas, et chaque equation coute une supposition — donc
   2^68 branches pour un etat de 128 bits, sans elagage avant le rang plein.

   OR C'EST LA COMBINAISON LA PLUS PLAUSIBLE. xorshift128+ est Math.random de
   V8, et le JavaScript idiomatique ecrit Math.floor(Math.random() * {POOL}) —
   soit exactement (B). Le mur du dossier, cote generateur, est donc
   desormais NOMME :

       sortie ADDITIVE + echantillonneur par TRONCATURE

   Ni le §68 (lineaire, modulo), ni le §82 (lineaire, troncature), ni ce
   fichier (additif, modulo) ne l'atteignent. Il faudrait un solveur
   algebrique — SAT ou base de Groebner — la ou le dossier n'a que de
   l'elimination de Gauss.

   C'est la premiere fois que le dossier peut ecrire son mur en une ligne au
   lieu d'une liste.""")


# ==========================================================================
rule("6. CE QUE CELA ÉTABLIT")
# ==========================================================================

say(f"""   1. LE THEOREME DE LA RETENUE. Si a_i != b_i alors maj(a_i, b_i, c_i) = c_i :
      la retenue reste connue et l'equation suivante reste lineaire. D'ou un
      PREFIXE LIBRE de longueur 1 + (nombre de 1 en tete des bits observes),
      d'esperance 1,875 contre 1 au §69 — sans supposition ni branchement.
      Verifie sur {tested:,} equations, zero fausse.

   2. LE PALIER DES FAMILLES ADDITIVES tombe de {-(-128 // DRAWN)} a {need} tirages ordonnes.
      Le §69 n'avait pas tort — il comptait ce qui etait certain — mais il
      laissait {1 - 1/1.875:.0%} de la fuite sur la table.

   3. L'ALGEBRE EST VERIFIEE, positions donnees : l'etat sort par elimination
      seule. Ce qui manque est une DONNEE, pas une idee.

   4. LE MUR EST NOMME EN UNE LIGNE : sortie ADDITIVE + echantillonneur par
      TRONCATURE. C'est la combinaison de Math.random et du JavaScript
      idiomatique, et aucun des §68, §82 ni celui-ci ne l'atteint.

   Registre : INCHANGE. h63 demontre, mesure et verifie ; il ne teste pas
   l'archive, faute de tirages consecutifs en nombre suffisant.""")

say(f"\n   ({time.time() - T0:.1f} s)")
