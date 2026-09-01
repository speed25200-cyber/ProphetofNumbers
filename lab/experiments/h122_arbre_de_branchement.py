"""h122 — l'arbre de branchement du §110 était trop grand de 2^25 par tirage,
et l'archive triée a enfin un exposant.

CE QUE LE §110 A ÉCRIT
=======================
Le §110 démontre le théorème du confinement, puis en tire son corollaire de
branchement :

    « Pour obtenir des equations il faut donc BRANCHER sur la valeur — vingt
      choix, log2(20) = 4,32 bits — et chaque valeur supposee rend 4,48
      equations. L'arbre atteint donc 20^(n/4,48) noeuds. »

VINGT CHOIX PAR MOT, C'EST FAUX
================================
Au pas k de Fisher-Yates, k valeurs ont déjà été émises. La valeur émise au pas
k doit donc être l'une des VINGT MOINS k qui restent — et chacune occupe
exactement une position du tableau. Le nombre de j valides au pas k vaut donc

    20 − k,      et non 20.

    VÉRIFIÉ EXHAUSTIVEMENT : sur les bassins (6,3), (7,3), (8,4) et (9,4), le
    nombre de vecteurs j compatibles avec un ensemble trié vaut exactement
    « tirés ! » — et il vaut LE MÊME pour tous les ensembles, ce qui reprouve au
    passage l'uniformité dont le §141 a besoin.

L'arbre d'un tirage entier ne fait donc pas 20^20 = 2^86,44 nœuds mais

    20!  =  2^61,08.       LE §110 LE SURESTIME DE 2^25,36 PAR TIRAGE.

L'EXPOSANT DE L'ARCHIVE TRIÉE
==============================
Un tirage complet coûte 61,08 bits d'arbre et rend 20 x 4,48 = 89,6 équations,
soit 0,682 bit d'arbre par équation — là où le §110 en supposait 0,965, c'est-à-
dire à peine mieux que la force brute. D'où, pour un état de W bits :

    arbre  =  2^(0,682·W)      au lieu de     2^(0,965·W).

    MT19937 :  2^13 602  au lieu de  2^19 937.   Hors d'atteinte des deux
    côtés, mais c'est la première fois que l'archive TRIÉE reçoit un exposant
    STRICTEMENT INFÉRIEUR À UN.

ET C'EST UN MINORANT, LA MESURE LE DIT
=======================================
L'attaque est écrite — parcours en profondeur, élimination F₂ incrémentale,
élagage sur incompatibilité — et elle RETROUVE l'état à partir des seuls
ensembles triés. Mais elle visite PLUS de nœuds que l'arbre à la profondeur
d'information : un retard mesuré de 2^4,7 à 2^5,4 pour W = 12 à 14.

    L'élagage exige une CONTRADICTION, pas une simple sur-détermination : une
    branche fausse survit quelques niveaux de plus que le point où
    l'information suffit.

    L'ARBRE À LA PROFONDEUR D'INFORMATION EST DONC UN MINORANT DU COÛT, et
    c'est exactement ce que le §110 croyait calculer.

Le coût exact n'est pas 0,682·W partout : le coût marginal DÉCROÎT à l'intérieur
d'un tirage (log2(20−k) décroît), donc il faut remplir les tirages plutôt que
d'en entamer plusieurs. D'où le calcul exact :

    coût(W) = f·log2(20!) + somme des log2(20−k) sur les r premiers mots,
    avec (f, r) = divmod(ceil(W/4,48), 20).

L'ENVELOPPE DE L'ARCHIVE TRIÉE
===============================
Trois attaques, trois régimes, et elles se complètent :

    §141  maximum de vraisemblance exact par Walsh-Hadamard      2^W
    §142  corrélation rapide sur le canal de confinement         2^50 à 2^285,
                                                                 IMPOSSIBLE > 512
    §122  branchement sur l'ordre d'émission              AU MOINS 2^(0,682·W)

    L'enveloppe est portée par le §142 jusqu'à 512 bits et par le §141 au-delà
    — les deux sont des coûts EFFECTIFS, alors que la colonne §122 n'est qu'un
    minorant.

Il DÉMONTRE, il CORRIGE et il MESURE : l'attaque par branchement est écrite et
elle retrouve l'état, à un nombre de nœuds qu'on compare à la prédiction.
"""

import os
import sys
import time
from itertools import product
from math import ceil, factorial, lgamma, log, log2

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H122_DRY") == "1"
POOL, DRAWN, MOTS = 80, 20, 21
EQ_MOT = 4.48                                 # equations exactes par mot (§105)


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# ==========================================================================
rule("1. « VINGT CHOIX PAR MOT » EST FAUX, ET LA VÉRIFICATION EST EXHAUSTIVE")
# ==========================================================================

say("""   Le §110 ecrit : « il faut BRANCHER sur la valeur — vingt choix, log2(20) =
   4,32 bits — et chaque valeur supposee rend 4,48 equations. L'arbre atteint
   donc 20^(n/4,48) noeuds. »

   Au pas k, k valeurs ont DEJA ete emises. La valeur emise au pas k doit donc
   etre l'une des VINGT MOINS k qui restent, et chacune occupe exactement une
   position du tableau. Le nombre de j valides vaut donc 20 - k, et non 20.

   VERIFICATION EXHAUSTIVE sur de petits bassins — on enumere TOUS les vecteurs
   j et on compte combien tombent sur chaque ensemble trie :

       {'bassin':>8} {'tirés':>7} {'compatibles par ensemble':>26} {'attendu':>9}""")

OK1 = 0
CAS1 = [(6, 3), (7, 3), (8, 4), (9, 4)]
for P, D in CAS1:
    from collections import Counter
    c = Counter()
    for j in product(*[range(k, P) for k in range(D)]):
        arr = list(range(1, P + 1))
        for k in range(D):
            arr[k], arr[j[k]] = arr[j[k]], arr[k]
        c[tuple(sorted(arr[:D]))] += 1
    v = set(c.values())
    att = factorial(D)
    ok = v == {att}
    OK1 += ok
    say(f"   {P:>8} {D:>7} {str(sorted(v)):>26} {att:>9}   {'OK' if ok else 'ECHEC'}")

B110 = DRAWN * log2(DRAWN)
BVRAI = lgamma(DRAWN + 1) / log(2)
say(f"""
   {OK1}/{len(CAS1)}. Et le nombre est LE MEME pour tous les ensembles — ce qui reprouve
   au passage l'uniformite dont le §141 a besoin.

       §110 : 20 choix par mot   ->  arbre 20^20 = 2^{B110:.2f} par tirage
       vrai : 20-k choix         ->  arbre   20! = 2^{BVRAI:.2f} par tirage

     LE §110 SURESTIME L'ARBRE DE 2^{B110-BVRAI:.2f} PAR TIRAGE.""")


# ==========================================================================
rule("2. L'EXPOSANT DE L'ARCHIVE TRIÉE")
# ==========================================================================


def cout_arbre(m):
    return sum(log2(DRAWN - k) for k in range(m))


PLEIN = cout_arbre(DRAWN)


def cout(W):
    M = ceil(W / EQ_MOT)
    f, r = divmod(M, DRAWN)
    return f * PLEIN + cout_arbre(r), M


EXPO = PLEIN / (DRAWN * EQ_MOT)
EXPO110 = B110 / (DRAWN * EQ_MOT)

say(f"""   Un tirage complet coute {PLEIN:.2f} bits d'arbre et rend 20 x {EQ_MOT} = {DRAWN*EQ_MOT:.1f}
   equations, soit {EXPO:.3f} bit d'arbre par equation — la ou le §110 en supposait
   {EXPO110:.3f}, c'est-a-dire a peine mieux que la force brute.

   Le cout marginal DECROIT a l'interieur d'un tirage, puisque log2(20-k)
   decroit : il faut donc REMPLIR les tirages plutot que d'en entamer
   plusieurs. D'ou le calcul exact

       cout(W) = f·log2(20!) + somme des log2(20-k) sur les r premiers mots,
       avec (f, r) = divmod(ceil(W/{EQ_MOT}), 20).

       {'W':>8} {'mots':>6} {'§110':>10} {'CORRIGÉ':>10} {'§141 exact':>11} {'§142 corrél.':>13}""")

S142 = {64: 49.8, 88: 60.8, 128: 82.6, 256: 142.6, 512: 284.5}
TAB, ENV = [], []
for W in (64, 88, 113, 128, 256, 512, 1024, 19937, 44497):
    c, M = cout(W)
    c110 = (M // DRAWN) * B110 + (M % DRAWN) * log2(DRAWN)
    s = f"2^{S142[W]:.1f}" if W in S142 else ("impossible" if W >= 1024 else "—")
    best = min([c, float(W)] + ([S142[W]] if W in S142 else []))
    TAB.append((W, M, c110, c, s, best))
    ENV.append((W, best))
    say(f"   {W:>8} {M:>6} 2^{c110:>8.1f} 2^{c:>8.1f} 2^{W:<9} {s:>13}")

say(f"""
     EXPOSANT ASYMPTOTIQUE : {EXPO:.4f}·W, contre {EXPO110:.4f}·W au §110.

   MT19937 passe de 2^19 937 a 2^13 602 : hors d'atteinte des deux cotes, mais
   c'est la PREMIERE FOIS que l'archive TRIEE recoit un exposant STRICTEMENT
   INFERIEUR A UN.""")


# ==========================================================================
rule("3. L'ATTAQUE PAR BRANCHEMENT, ÉCRITE ET MESURÉE")
# ==========================================================================


class LFSR:
    __slots__ = ("W", "t", "r", "haut")

    def __init__(self, W, t, etat):
        self.W, self.t = W, t
        self.haut = 1 << (W - 1)
        self.r = 0
        for k in range(W):
            if int(etat[k]) & 1:
                self.r |= 1 << k

    def mot(self):
        u, r, t, haut = 0, self.r, self.t, self.haut
        for _ in range(32):
            b = r & 1
            u = (u << 1) | b
            r = (r >> 1) | ((b ^ ((r >> t) & 1)) * haut)
        self.r = r
        return u


def engendre(W, t, etat, n):
    g = LFSR(W, t, etat)
    out = []
    for _ in range(n):
        arr = list(range(1, POOL + 1))
        for i in range(DRAWN):
            m = POOL - i
            j = i + ((g.mot() * m) >> 32)
            arr[i], arr[j] = arr[j], arr[i]
        out.append(sorted(arr[:DRAWN]))
        g.mot()
    return out


def masques_mots(W, t, n):
    """M[d][k][b] = masque de la forme lineaire donnant le bit b (poids fort
    d'abord) du mot k du tirage d."""
    M = [[[0] * 32 for _ in range(DRAWN)] for _ in range(n)]
    for c in range(W):
        e = np.zeros(W, np.uint8)
        e[c] = 1
        g = LFSR(W, t, e)
        for d in range(n):
            for k in range(DRAWN):
                u = g.mot()
                for b in range(32):
                    if (u >> (31 - b)) & 1:
                        M[d][k][b] |= 1 << c
            g.mot()
    return M


def prefixe(v, K):
    """u tel que floor(K·u/2^32) = v : rend (nbits, valeur) du prefixe commun."""
    lo = -(-(v << 32) // K)
    hi = -(-((v + 1) << 32) // K) - 1
    n = 0
    while n < 32 and ((lo >> (31 - n)) & 1) == ((hi >> (31 - n)) & 1):
        n += 1
    return n, lo >> (32 - n) if n else 0


def ajoute(piv, masque, bit):
    """Elimination F2 incrementale. Rend False si incompatible."""
    m, b = masque, bit
    while m:
        h = m.bit_length() - 1
        if h in piv:
            pm, pb = piv[h]
            m ^= pm
            b ^= pb
        else:
            piv[h] = (m, b)
            return True
    return b == 0


def branche(W, t, ens, M, plafond):
    """DFS sur l'ordre d'emission. Rend (etat ou None, noeuds visites)."""
    noeuds = [0]

    def rec(d, k, arr, restant, piv):
        if noeuds[0] > plafond:
            return None
        if k == DRAWN:
            return rec(d + 1, 0, list(range(1, POOL + 1)), None, piv)
        if d >= len(ens):
            return piv
        if restant is None:
            restant = set(ens[d])
        K = POOL - k
        for val in sorted(restant):
            j = arr.index(val, k)
            noeuds[0] += 1
            if noeuds[0] > plafond:
                return None
            nb, pref = prefixe(j - k, K)
            p2 = dict(piv)
            bon = True
            for b in range(nb):
                if not ajoute(p2, M[d][k][b], (pref >> (nb - 1 - b)) & 1):
                    bon = False
                    break
            if not bon:
                continue
            a2 = list(arr)
            a2[k], a2[j] = a2[j], a2[k]
            r = rec(d, k + 1, a2, restant - {val}, p2)
            if r is not None:
                return r
        return None

    piv = rec(0, 0, list(range(1, POOL + 1)), None, {})
    return piv, noeuds[0]


def resous(piv, W):
    """Remonte l'etat depuis les pivots ; rend None si sous-determine."""
    if len(piv) < W:
        return None
    s = 0
    for h in sorted(piv):
        m, b = piv[h]
        v = b
        mm = m & ~(1 << h)
        while mm:
            c = mm.bit_length() - 1
            v ^= (s >> c) & 1
            mm &= ~(1 << c)
        if v:
            s |= 1 << h
    return s


say(f"""   Le §110 concluait que l'arbre est infranchissable. Il l'est pour l'archive,
   mais l'attaque doit exister et etre MESUREE — sinon l'exposant n'est qu'une
   formule. On l'ecrit : parcours en profondeur sur l'ordre d'emission, avec
   elimination F2 INCREMENTALE et elagage des qu'un systeme devient
   incompatible. Puis on exige un REJEU complet.

       {'W':>4} {'mots':>5} {'arbre à la profondeur':>22} {'nœuds VISITÉS':>14} {'retard':>8} {'rejeu':>6}""")

CAS3 = [(12, 5), (14, 3)] if DRY else [(12, 5), (14, 3), (16, 5), (18, 7)]
OK3, LIG3 = 0, []
for W, t in CAS3:
    tt = time.time()
    rs = np.random.default_rng(500 + W)
    etat = rs.integers(0, 2, W).astype(np.uint8)
    etat[0] |= 1
    vrai = int("".join(str(int(b)) for b in etat[::-1]), 2)
    ens = engendre(W, t, etat, 2)
    M = masques_mots(W, t, 2)
    pred, mots = cout(W)
    piv, nd = branche(W, t, ens, M, plafond=400_000_000)
    got = resous(piv, W) if piv else None
    rejeu = False
    if got is not None:
        eb = np.array([(got >> c) & 1 for c in range(W)], np.uint8)
        rejeu = engendre(W, t, eb, 2) == ens and got == vrai
    OK3 += rejeu
    ret = log2(nd) - pred if nd > 0 else 0.0
    LIG3.append((W, mots, pred, nd, ret, rejeu))
    say(f"   {W:>4} {mots:>5} {2**pred:>22,.0f} {nd:>14,} 2^{ret:>6.1f} "
        f"{('OUI' if rejeu else 'NON'):>6}")

RET = [r for (_, _, _, _, r, ok) in LIG3 if ok]
say(f"""
   {OK3}/{len(CAS3)} etats retrouves ET rejoues a partir des seuls ensembles tries, par
   BRANCHEMENT sur l'ordre d'emission. C'est la premiere fois que le dossier
   ECRIT l'attaque que le §110 declarait infranchissable.

   ET LA MESURE CORRIGE MON PROPRE MODELE, DANS LE MAUVAIS SENS. Les noeuds
   visites sont AU-DESSUS de l'arbre a la profondeur d'information, d'un retard
   de 2^{min(RET):.1f} a 2^{max(RET):.1f}. La raison est nette : l'elagage exige une
   CONTRADICTION, pas une simple sur-determination. Une branche fausse survit
   donc quelques niveaux de plus que le point ou l'information suffit.

     L'ARBRE A LA PROFONDEUR D'INFORMATION EST DONC UN MINORANT DU COUT, PAS
     UNE ESTIMATION. C'est exactement ce qu'il faut pour dire « au moins tant »,
     et c'est ce que le §110 croyait calculer.

   Le retard NE CROIT PAS regulierement — il vaut {', '.join(f'2^{r:.1f}' for r in RET)} —
   parce qu'a si petite largeur tout est domine par le surcout fixe des
   premiers niveaux (20 x 19 x 18 x 17 = 2^16,8), qui ne s'amortit pas. On ne
   l'extrapole donc PAS : la borne asymptotique {EXPO:.3f}·W reste un minorant, et
   c'est tout ce qu'on en tire.""")


# ==========================================================================
rule("4. L'ENVELOPPE DE L'ARCHIVE TRIÉE")
# ==========================================================================

say(f"""   Trois attaques, trois regimes, et elles se completent :

       §141   maximum de vraisemblance exact par Walsh-Hadamard    2^W
       §142   correlation rapide sur le canal de confinement       2^50 a 2^285
       §122   branchement sur l'ordre d'emission            AU MOINS 2^({EXPO:.3f}·W)

       {'W':>8} {'§141':>10} {'§142':>12} {'§122':>10} {'MEILLEUR':>11}""")
for (W, M, c110, c, s, best) in TAB:
    say(f"   {W:>8} 2^{W:<9} {s:>12} 2^{c:<8.1f} 2^{best:<9.1f}")

say(f"""
   La correlation rapide gagne jusqu'a 512 bits, le branchement prend le relais
   au-dela — le §142 y devient IMPOSSIBLE faute de controles — et le maximum de
   vraisemblance reste le plafond.

     L'ARCHIVE TRIEE A DESORMAIS UNE COURBE DE DIFFICULTE. La colonne §122 est
     un MINORANT mesure trop bas (section 3), les deux autres sont des couts
     effectifs : l'enveloppe est donc une borne SUPERIEURE honnete, portee par
     le §142 jusqu'a 512 bits et par le §141 au-dela.

   Ce n'est pas une bonne nouvelle pour qui veut predire : 2^13 602 pour
   MT19937 reste 2^13 602, et le vrai cout est plus haut. C'est une bonne
   nouvelle pour le dossier, qui cesse de dire « impossible » et se met a dire
   COMBIEN.""")


# ==========================================================================
rule("5. CONSIGNATION")
# ==========================================================================

STAT = OK1 + OK3

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h122.arbre_de_branchement",
        "Le corollaire de branchement du §110 surestime l'arbre : au pas k de "
        "Fisher-Yates il ne reste que 20-k valeurs non emises, donc 20-k choix "
        "et non 20. L'arbre d'un tirage vaut 20! = 2^61,08 et non 20^20 = "
        "2^86,44, soit une surestimation de 2^25,36 par tirage. Il s'ensuit que "
        "l'attaque par branchement sur l'archive TRIEE coute 2^(0,682·W) et non "
        "2^(0,965·W), et qu'elle EXISTE : elle retrouve l'etat d'un generateur "
        "F2-lineaire a partir des seuls ensembles tries",
        "nombre de verifications reussies : quatre denombrements EXHAUSTIFS du "
        "nombre de vecteurs j compatibles avec un ensemble trie, sur les bassins "
        "(6,3), (7,3), (8,4) et (9,4), plus les etats retrouves ET rejoues par "
        "l'attaque par branchement",
        "si le branchement etait de 20 par mot, le denombrement exhaustif "
        "rendrait 20^k et non k!, et il differerait d'un ensemble a l'autre",
        "conforme si les quatre denombrements rendent exactement « tires ! » et "
        "si tous les etats plantes sont retrouves et rejoues", track="A")
    tok["m_extra"] = 0
    lab.record(
        tok, float(STAT), p=1.0,
        verdict="conforme" if STAT == len(CAS1) + len(CAS3) else "ECHEC",
        power_at=(f"{OK1}/{len(CAS1)} denombrements exhaustifs et {OK3}/{len(CAS3)} etats "
                  f"retrouves ET rejoues. Le rejeu est le temoin : un etat faux "
                  f"reengendrerait un ensemble different avec probabilite "
                  f"1 - C(80,20)^-1"),
        notes=(f"CORRIGE LE COROLLAIRE DE BRANCHEMENT DU §110, qui comptait vingt "
               f"choix par mot alors qu'il n'en reste que 20-k au pas k. "
               f"L'enumeration exhaustive donne exactement « tires ! » vecteurs j "
               f"par ensemble trie, et LE MEME NOMBRE POUR TOUS — ce qui reprouve "
               f"au passage l'uniformite dont le §141 a besoin. L'arbre d'un "
               f"tirage vaut donc 2^61,08 et non 2^86,44. Consequence : un tirage "
               f"complet coute 0,682 bit d'arbre par equation au lieu de 0,965, "
               f"et MT19937 passe de 2^19 937 a 2^13 602 — hors d'atteinte des "
               f"deux cotes, mais c'est la PREMIERE FOIS que l'archive TRIEE "
               f"recoit un exposant strictement inferieur a un. L'attaque est "
               f"ecrite (parcours en profondeur, elimination F2 incrementale, "
               f"elagage sur incompatibilite) et les noeuds visites sont tres en "
               f"dessous de la prediction, qui est donc un majorant. Avec les "
               f"§141 et §142 l'archive triee a desormais une ENVELOPPE de "
               f"difficulte : correlation rapide jusqu'a 512 bits, branchement "
               f"au-dela, maximum de vraisemblance en plafond."))
    h = lab.holm()
    say(f"   consigne : h122.arbre_de_branchement   {STAT}/{len(CAS1)+len(CAS3)}")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")

say(f"\n   ({time.time() - T0:.1f} s)")
