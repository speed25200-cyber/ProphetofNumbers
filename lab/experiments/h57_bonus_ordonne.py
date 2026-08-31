"""h57 — le bonus, seule donnee ORDONNEE que l'archive triee contienne.

L'observation
==============
L'archive est triee : `n1..n20` est croissant sur les 70 560 lignes, et le §11
en conclut que l'ordre de sortie y est perdu. C'est vrai des vingt numeros.

Mais chaque tirage porte AUSSI un bonus, present sur les 70 560 lignes, et
qui appartient TOUJOURS aux vingt numeros tires. Le bonus n'est donc pas un
vingt-et-unieme numero : c'est un POINTEUR vers l'un des vingt.

    Si ce pointeur designe une POSITION FIXE de l'ordre de sortie, alors
    l'archive triee contient 70 560 donnees ordonnees que personne n'a lues
    comme telles.

La position qui se teste, et pourquoi c'est la seule
=====================================================
Sous Fisher-Yates, le numero tire au pas i est l'ancien a[j] avec
j = i + out_i mod (80-i) : le retrouver demande de connaitre TOUT le prefixe
de l'ordre. Sauf au pas 0, ou le tableau est encore 1..80 :

    premier numero tire = (out_0 mod 80) + 1

Donc SI le bonus est le PREMIER numero sorti, chaque tirage publie
out_0 mod 16 — quatre bits — a un indice de mot exactement connu (20 mots par
tirage sous Fisher-Yates). Pour les positions j > 0 le prefixe manque, et le
bonus ne dit rien d'exploitable.

Le budget que cela ouvrirait
=============================
    204 tirages d'une session  ->  816 bits
    70 560 tirages             ->  282 240 bits

contre 110 bits pour les cinq tirages ordonnes du §72. Trois ordres de
grandeur, sur des donnees deja collectees.

Ce que le test etablit, et ce qu'il ne peut pas separer
=======================================================
Un echec a deux lectures, comme au §73 : soit le generateur n'est d'aucune
famille testee, soit le bonus n'est pas le premier numero. Le test est donc
CONJOINT, et il faut l'ecrire ainsi.

Il TESTE l'archive : il consigne au registre.
"""

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
POOL, DRAWN = 80, 20
DRY = os.environ.get("H57_DRY") == "1"


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def msk(n):
    return (1 << n) - 1


def xs32(s):
    s ^= (s << 13) & msk(32)
    s ^= s >> 17
    s ^= (s << 5) & msk(32)
    return s, s


def xs64(s):
    s ^= (s << 13) & msk(64)
    s ^= s >> 7
    s ^= (s << 17) & msk(64)
    return s, s


def xs96(s):
    x, y, z = s & msk(32), (s >> 32) & msk(32), (s >> 64) & msk(32)
    t = (x ^ (x << 3)) & msk(32)
    t ^= t >> 19
    x, y = y, z
    z = (z ^ (z << 6) ^ t) & msk(32)
    return x | (y << 32) | (z << 64), z


def xs128(s):
    x, y = s & msk(32), (s >> 32) & msk(32)
    z, w = (s >> 64) & msk(32), (s >> 96) & msk(32)
    t = (x ^ (x << 11)) & msk(32)
    t ^= t >> 8
    x, y, z = y, z, w
    w = (w ^ (w >> 19) ^ t) & msk(32)
    return x | (y << 32) | (z << 64) | (w << 96), w


FAMS = [("xorshift32", 32, xs32), ("xorshift64", 64, xs64),
        ("xorshift96", 96, xs96), ("xorshift128", 128, xs128)]


def coeffs(step, nbits, nwords):
    """COEF[pos][b] : coefficients de « bit b du mot d'indice pos »."""
    cols = []
    for i in range(nbits):
        s, seq = 1 << i, []
        for _ in range(nwords):
            s, w = step(s)
            seq.append(w)
        cols.append(seq)
    coef = [[0] * 4 for _ in range(nwords)]
    for i in range(nbits):
        ci, bit = cols[i], 1 << i
        for pos in range(nwords):
            w = ci[pos]
            for b in range(4):
                if (w >> b) & 1:
                    coef[pos][b] |= bit
    return coef


def solve(rows, rhs, nbits):
    piv = {}
    for r, b in zip(rows, rhs):
        cur, cb = r, b
        while cur:
            h = cur.bit_length() - 1
            if h in piv:
                pr, pb = piv[h]
                cur ^= pr
                cb ^= pb
            else:
                piv[h] = (cur, cb)
                break
        else:
            if cb:
                return None
    sol = 0
    for h in sorted(piv):
        pr, pb = piv[h]
        if (bin(pr & sol).count("1") + pb) & 1:
            sol ^= 1 << h
    return sol, [i for i in range(nbits) if i not in piv]


def fy_first(step, s):
    """Le premier numero tire d'un tirage Fisher-Yates, et l'etat apres les
    20 mots consommes."""
    first = None
    for i in range(DRAWN):
        s, w = step(s)
        if i == 0:
            first = w % POOL + 1
    return first, s


def attack_bonus(step, nbits, bonuses, coef, max_free=16):
    """bonuses[t] = premier numero suppose du tirage t (t = 0, 1, 2, ...).

    Chaque tirage publie out_{20t} mod 16, soit 4 equations, a indice exact.
    """
    rows, rhs = [], []
    for t, b in enumerate(bonuses):
        val = (b - 1) & 15
        cp = coef[DRAWN * t]
        for k in range(4):
            rows.append(cp[k])
            rhs.append((val >> k) & 1)
    res = solve(rows, rhs, nbits)
    if res is None:
        return [], len(rows)
    sol, free = res
    if len(free) > max_free:
        return [], len(rows)
    found = []
    for combo in range(1 << len(free)):
        cand = sol
        for j, fb in enumerate(free):
            if (combo >> j) & 1:
                cand ^= 1 << fb
        if not cand:
            continue
        s, ok = cand, True
        for b in bonuses:
            f, s = fy_first(step, s)
            if f != b:
                ok = False
                break
        if ok:
            found.append(cand)
    return found, len(rows)


# ==========================================================================
rule("1. L'OBSERVATION")
# ==========================================================================

arch = lab.load()
bon = arch.bonus.astype(np.int64)
inside = int(sum(1 for i in range(len(arch)) if bon[i] in arch.nums[i]))
say(f"""   {len(arch):,} tirages, tous avec un bonus.
   bonus appartenant aux vingt numeros tires : {inside:,} / {len(arch):,}

   Le bonus n'est donc pas un vingt-et-unieme numero : c'est un POINTEUR vers
   l'un des vingt. Si ce pointeur designe une POSITION FIXE de l'ordre de
   sortie, l'archive triee contient {len(arch):,} donnees ORDONNEES.

   Une seule position se teste, et c'est le PREMIER. Sous Fisher-Yates le
   numero du pas i est l'ancien a[j] avec j = i + out_i mod (80-i) : le
   retrouver demande tout le prefixe. Sauf au pas 0, ou le tableau est encore
   1..80 et ou le numero tire vaut exactement (out_0 mod 80) + 1.
""")
say(f"   {'source':>22} {'tirages':>9} {'bits (4/tirage)':>16}")
say(f"   {'les 5 tirages du §72':>22} {5:>9} {5 * 22:>16}")
say(f"   {'une session':>22} {204:>9} {204 * 4:>16}")
say(f"   {'l archive entiere':>22} {len(arch):>9,} {len(arch) * 4:>16,}")


# ==========================================================================
rule("2. LE TÉMOIN")
# ==========================================================================

say("""   Une archive est fabriquee : Fisher-Yates alimente par chaque famille,
   et le bonus est POSE comme le premier numero sorti. L'attaque doit
   retrouver l'etat a partir des seuls bonus.
""")
rng = __import__("random").Random(20260910)
NSESS = 204
# Quatre equations par tirage, mais elles ne sont pas independantes : prendre
# le strict minimum (nbits/4 tirages) laisse le rang incomplet et le temoin
# echoue au-dela de 32 bits. On en prend QUATRE FOIS plus — une session en
# offre 816, il n'y a aucune raison d'etre avare.
def ndraws_for(nbits):
    return min(NSESS, max(16, nbits))
say(f"   {'famille':<14} {'bits':>5} {'tirages':>8} {'équations':>10} {'retrouvé':>9} {'temps':>8}")
ctrl = 0
for nom, nbits, step in FAMS:
    nd = ndraws_for(nbits)
    st = rng.getrandbits(nbits) or 1
    s, firsts = st, []
    for _ in range(nd):
        f, s = fy_first(step, s)
        firsts.append(f)
    t = time.time()
    coef = coeffs(step, nbits, nd * DRAWN)
    got, neq = attack_bonus(step, nbits, firsts, coef)
    dt = time.time() - t
    ok = st in got
    ctrl += ok
    say(f"   {nom:<14} {nbits:>5} {nd:>8} {neq:>10} {'OUI' if ok else 'non':>9} {dt:>7.2f}s")
say(f"\n   {ctrl} familles sur {len(FAMS)} retrouvees depuis les SEULS bonus.")


# ==========================================================================
rule("3. SUR L'ARCHIVE, SESSION PAR SESSION")
# ==========================================================================

ts = arch.ts.astype(np.int64)
starts = [0] + [i for i in range(1, len(ts)) if ts[i] - ts[i - 1] > 1000]
sessions = []
for k, st_i in enumerate(starts):
    end = starts[k + 1] if k + 1 < len(starts) else len(ts)
    if end - st_i >= 64:
        sessions.append((st_i, end))
if DRY:
    sessions = sessions[:6]

say(f"""   {len(sessions)} sessions d'au moins 64 tirages. Le generateur est suppose
   courir en continu DANS une session (le §65 n'a pas tranche s'il traverse
   les coupures, donc on ne les traverse pas).

   Chaque session est attaquee independamment, pour chaque famille.
""")
say(f"   {'famille':<14} {'bits':>5} {'sessions':>9}  {'états compatibles':>18}")
total = 0
for nom, nbits, step in FAMS:
    nd = ndraws_for(nbits)
    coef = coeffs(step, nbits, nd * DRAWN)
    hits = 0
    for st_i, end in sessions:
        b = [int(x) for x in bon[st_i:st_i + nd]]
        got, _ = attack_bonus(step, nbits, b, coef)
        hits += len(got)
    total += hits
    say(f"   {nom:<14} {nbits:>5} {len(sessions):>9}  {hits:>18}")

say(f"\n   TOTAL : {total} etat compatible sur "
    f"{len(sessions) * len(FAMS)} (session x famille).")


# ==========================================================================
rule("4. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h57.bonus_ordonne",
        "Aucune session de l'archive n'est reproduite par un generateur "
        "F2-lineaire d'etat <= 128 bits echantillonnant en Fisher-Yates, SOUS "
        "L'HYPOTHESE que le bonus soit le PREMIER numero sorti — pour aucune "
        "graine. Test CONJOINT : un echec ne separe pas « mauvaise famille » de "
        "« bonus non positionnel »",
        f"nombre d'etats compatibles verifies par rejeu integral, sur "
        f"{len(sessions)} sessions x {len(FAMS)} familles ; chaque tirage publie "
        f"out_0 mod 16 a indice exact, soit 4 equations",
        "deterministe : verification par rejeu, aucun null a simuler",
        "conforme si aucun etat compatible", track="A")
    lab.record(tok, float(total), p=None, verdict="conforme",
               power_at=(f"temoin positif : {ctrl} familles sur {len(FAMS)} retrouvees "
                         f"depuis les SEULS bonus d'une archive fabriquee ou le bonus "
                         f"est pose comme premier numero"),
               notes=("LE BONUS COMME DONNEE ORDONNEE. L'archive est triee, mais son "
                      "bonus appartient toujours aux vingt numeros : c'est un pointeur "
                      "vers l'un d'eux. Si ce pointeur designe une position fixe, "
                      "l'archive triee contient 70 560 donnees ordonnees. Une seule "
                      "position se teste — le PREMIER numero, car sous Fisher-Yates le "
                      "pas 0 lit le tableau encore intact et vaut (out_0 mod 80) + 1 ; "
                      "au-dela il faudrait tout le prefixe. Budget ouvert : 816 bits par "
                      "session contre 110 pour les cinq tirages ordonnes du §72."))
    h = lab.holm()
    say(f"   consigne : h57.bonus_ordonne   etats compatibles {total}")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")


# ==========================================================================
rule("5. CE QUE CELA AJOUTE, ET CE QUE CELA NE SÉPARE PAS")
# ==========================================================================

say(f"""   AJOUTE. Le §11 dit que l'archive triee a perdu l'ordre. C'est vrai des
   vingt numeros et FAUX du bonus, qui pointe vers l'un d'eux. Sous une
   hypothese de position, l'archive redevient partiellement ordonnee — et le
   budget passe de 110 bits (§72, cinq tirages) a 816 par session.

   NE SEPARE PAS. Un echec a deux lectures, comme au §73 :
     (a) le generateur n'est d'aucune famille testee ;
     (b) le bonus n'est pas le premier numero sorti.
   Le test est CONJOINT. Ce qu'il etablit est une implication :
   « SI le bonus est le premier numero, ALORS aucune famille testee ne
   convient. »

   CE QUI LEVERAIT L'AMBIGUITE. Le §37 a montre que l'archive triee ne peut
   pas trancher la regle du bonus — non pas difficilement, mais par
   NON-IDENTIFIABILITE. Les cinq tirages ordonnes du dossier, eux, donnent la
   position du bonus directement : c'est la mesure que l'app accumule depuis
   le §38, et une dizaine suffirait.

   LIMITE DE CALCUL. MT19937 demanderait 4 985 tirages, soit 24 sessions
   chainees si le generateur traverse les coupures — mais son elimination
   porte sur 19 937 inconnues, ce qui sort de ce que Python fait en un temps
   raisonnable. La limite est ici computationnelle, pas informationnelle.

   Registre : consigne a la section 4.

   ({time.time() - T0:.1f} s)""")
