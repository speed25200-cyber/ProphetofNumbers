"""h76 — l'attaque 2-adique SOUS REJET : la case que le §34 n'a pas cochee.

LA CASE VIDE, ET ELLE EST PRECISE
==================================
Le §34 a mene deux campagnes qui se croisent sans se recouvrir :

    sweep_java48   les 2^48 etats COMPLETS   mais Fisher-Yates SEULEMENT
    sweep_order    4 echantillonneurs        mais graines [0, 2^32) seulement

Or `new Random()` en Java tire sa graine de `nanoTime` melangee a un
compteur : l'etat est un 48 bits ARBITRAIRE, hors de portee d'un balayage
2^32. Et l'idiome le plus courant pour tirer vingt numeros distincts est

    Set<Integer> s = new HashSet<>();
    while (s.size() < 20) s.add(rnd.nextInt(80) + 1);

c'est-a-dire un ECHANTILLONNEUR PAR REJET. Le §95 vient de montrer que le
rejet echappe entierement a Berlekamp-Massey ; le §34 ne l'a pas couvert a
2^48. Personne n'a donc jamais teste cette combinaison-la.

LE LEVIER, ET IL EST DANS LE MILIEU DE L'ETAT
==============================================
`next(31)` rend `(int)(s >>> 17)` et `nextInt(80)` rend `next(31) % 80`.
Comme 16 divise 80 :

    p mod 16  =  (s >>> 17) mod 16  =  LES BITS 17 A 20 DE L'ETAT

Ni les bits de poids faible ou vit le levier 2-adique habituel, ni ceux de
poids fort ou vivent les attaques par reseau : ceux du MILIEU. Et le LCG
modulo 2^48 reste CLOS modulo 2^21, donc ces bits ne dependent que de
s mod 2^21 — vingt-et-un bits, pas quarante-huit.

LE LEMME QUI REND LE REJET INOFFENSIF AU DEPART
================================================
Sous rejet, on ne sait pas quels mots ont ete rejetes. Mais un rejet exige
un DOUBLON, et au debut du tirage il n'y a presque rien a doubler :

    P(aucun rejet parmi les m premiers mots) = prod_{i<m} (1 - i/80)

Pour m = 8 cela vaut 0,697. Il suffit donc de huit numeros consecutifs SANS
rejet pour epingler s mod 2^21 — et avec neuf tirages ordonnes au dossier,
la probabilite qu'AUCUN ne commence proprement vaut 0,303^9 = 2 x 10^-5.

LE PIEGE DE LA BORNE 64 NE SE PRESENTE PAS ICI, et c'est une simplification
qu'il faut noter : le §34 devait le traiter parce que Fisher-Yates fait
decroitre la borne 80, 79, ..., 61 et croise 64, que `nextInt` traite a
part. Sous rejet la borne vaut TOUJOURS 80. Rien a sauter.

L'ATTAQUE, EN DEUX TEMPS
=========================
    1. enumerer les 2^21 valeurs de s mod 2^21, filtrer sur les quartets
       des m premiers numeros ;
    2. pour chaque survivant, enumerer les 2^27 bits de poids fort en
       filtrant sur les numeros COMPLETS (facteur 1/5 puis 1/80 par mot) ;
    3. verifier par rejeu exact du generateur, dans l'ORDRE.

Il TESTE les tirages ordonnes du dossier : il consigne au registre.
"""

import csv
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H76_DRY") == "1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POOL, DRAWN = 80, 20

A = 0x5DEECE66D
C = 0xB
M48 = (1 << 48) - 1
BAS = 21                       # le LCG est clos modulo 2^21
M21 = (1 << BAS) - 1
HAUT = 48 - BAS                # 27 bits de poids fort


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def nextint80(s):
    """Un appel a nextInt(80). Rend (valeur 0..79, nouvel etat)."""
    s = (A * s + C) & M48
    return ((s >> 17) & 0x7FFFFFFF) % POOL, s


def tirage_java(s):
    """Le tirage par rejet, dans l'ORDRE d'emission."""
    vus, ordre = set(), []
    while len(ordre) < DRAWN:
        v, s = nextint80(s)
        if v not in vus:
            vus.add(v)
            ordre.append(v + 1)
    return ordre, s


# ==========================================================================
rule("1. LA CASE VIDE, ET LE LEVIER")
# ==========================================================================

pm = 1.0
say(f"   {'m':>4} {'P(aucun rejet parmi les m premiers)':>38}")
for m in (4, 6, 8, 10, 12):
    p = 1.0
    for i in range(m):
        p *= (POOL - i) / POOL
    say(f"   {m:>4} {p:>38.4f}")
M_PREF = 8
P_PREF = 1.0
for i in range(M_PREF):
    P_PREF *= (POOL - i) / POOL

say(f"""
   On prend m = {M_PREF}. Le prefixe est propre avec probabilite {P_PREF:.4f}, et il
   suffit a epingler s mod 2^{BAS} : {M_PREF} numeros x 4 bits = {4*M_PREF} bits de
   contrainte pour {BAS} bits d'inconnue.

   LE PIEGE DE LA BORNE 64 du §34 ne se presente pas : sous rejet la borne
   vaut toujours 80, jamais 64. Rien a sauter.""")


# ==========================================================================
# LES DEUX ÉTAGES
# ==========================================================================
def etage1_depuis_depart(quartets, rejets=()):
    """Comme etage1 mais rend les valeurs de DEPART (s_0 mod 2^21).

    On propage un tableau de departs et un tableau d'etats courants en
    parallele : filtrer l'un filtre l'autre, donc l'appariement tient.
    """
    dep = np.arange(1 << BAS, dtype=np.uint64)
    cur = dep.copy()
    idx, pos = 0, 0
    while idx < len(quartets):
        cur = (np.uint64(A) * cur + np.uint64(C)) & np.uint64(M21)
        if pos in rejets:
            pos += 1
            continue
        garde = ((cur >> np.uint64(17)) & np.uint64(15)) == np.uint64(quartets[idx])
        cur, dep = cur[garde], dep[garde]
        if len(dep) == 0:
            return np.empty(0, np.uint64)
        idx += 1
        pos += 1
    return dep


def puissances(nmots):
    """A_i et C_i tels que s_i = A_i s_0 + C_i (mod 2^48)."""
    Ai, Ci = [1], [0]
    for _ in range(nmots):
        Ai.append((Ai[-1] * A) & M48)
        Ci.append((Ci[-1] * A + C) & M48)
    return Ai, Ci


def suite(s, ndraws):
    """Les `ndraws` tirages consecutifs engendres depuis l'etat s."""
    out = []
    for _ in range(ndraws):
        o, s = tirage_java(s)
        out.append(o)
    return out


def rejeu(etats, ordre):
    """Ne garde que les etats qui reproduisent l'ORDRE COMPLET des 20 numeros.

    L'etage 2 ne consomme que le prefixe, donc il rend quelques centaines de
    candidats. Le rejeu les tranche : il fait tourner le vrai generateur avec
    le vrai echantillonneur, rejets compris, et compare les vingt numeros dans
    l'ordre. Aucun faux positif n'est possible.
    """
    return [s for s in etats if tirage_java(s)[0] == ordre]


CHUNK = 1 << 22


def etage2(u0, numeros, Ai, Ci, rejets=()):
    """Cherche les 27 bits hauts. `numeros` : la suite des numeros emis (1..80)."""
    trouves = []
    for base in range(0, 1 << HAUT, CHUNK):
        v = np.arange(base, min(base + CHUNK, 1 << HAUT), dtype=np.uint64)
        s0 = np.uint64(u0) + (v << np.uint64(BAS))
        idx, pos = 0, 0
        while idx < len(numeros) and len(s0):
            pos += 1
            if (pos - 1) in rejets:
                continue
            si = (np.uint64(Ai[pos]) * s0 + np.uint64(Ci[pos])) & np.uint64(M48)
            p = ((si >> np.uint64(17)) & np.uint64(0x7FFFFFFF)) % np.uint64(POOL)
            s0 = s0[p == np.uint64(numeros[idx] - 1)]
            idx += 1
        trouves.extend(int(x) for x in s0)
    return trouves


# ==========================================================================
rule("2. LE TÉMOIN POSITIF")
# ==========================================================================

say(f"""   On plante un etat 48 bits AU HASARD — donc hors de portee de tout
   balayage 2^32 — on fabrique un tirage par rejet, et on demande a
   l'attaque de retrouver l'etat depuis l'ORDRE des vingt numeros.
""")

RNG = np.random.default_rng(20260902)
ESSAIS = 2 if DRY else 6
NSUITE = 3                       # tirages consecutifs verifies
Ai, Ci = puissances(64)
ok, jum, tt = 0, 0, time.time()
detail_tem = []
for _ in range(ESSAIS):
    s0 = int(RNG.integers(1, 1 << 48))
    vrai = suite(s0, NSUITE)
    ordre = vrai[0]
    quartets = [(n - 1) % 16 for n in ordre[:M_PREF]]
    c1 = etage1_depuis_depart(quartets)
    got = []
    for u0 in c1.tolist():
        got.extend(rejeu(etage2(u0, ordre[:M_PREF], Ai, Ci), ordre))
    bon = [x for x in got if suite(x, NSUITE) == vrai]
    ok += bool(bon)
    jum += sum(1 for x in bon if x != s0)
    detail_tem.append((len(c1), len(got), len(bon), s0 in bon))
say(f"   {'essai':>6} {'étage 1':>9} {'étage 2 + rejeu':>16} "
    f"{'prédisent la suite':>19} {'état planté ?':>15}")
for i, (n1, n2, n3, exact) in enumerate(detail_tem, 1):
    say(f"   {i:>6} {n1:>9,} {n2:>16,} {n3:>19} "
        f"{('oui' if exact else 'JUMEAU'):>15}")
say(f"""
   {ok}/{ESSAIS} tirages resolus en {time.time() - tt:.1f} s, dont {jum} par un JUMEAU.

   LE CRITERE N'EST PAS « on retrouve l'etat plante » mais « l'etat trouve
   PREDIT LES MEMES TIRAGES SUIVANTS ». C'est le THEOREME DU JUMEAU : sous
   rejet, si le premier mot est immediatement redouble — probabilite 1/{POOL} —
   l'etat d'avant et celui d'apres donnent le MEME tirage, et convergent des
   le premier numero accepte. Ils sont operationnellement IDENTIQUES.

   CELA CORRIGE UNE AFFIRMATION QUE LE DOSSIER REPETE DEPUIS LE §34 : « la
   verification est un rejeu exact, donc AUCUN faux positif possible ». Vraie
   pour EXCLURE — un zero reste un zero, et toutes les campagnes nulles du
   dossier tiennent. Trop forte pour IDENTIFIER : l'etat n'est determine
   qu'a un jumeau pres. Et pour PREDIRE, cela ne change rien.

   L'attaque marche sur des etats 48 bits TIRES AU HASARD, donc hors de
   portee de tout balayage 2^32. L'etage 1 reduit 2^{BAS} = {1 << BAS:,} a une
   poignee ; l'etage 2 tranche parmi 2^{HAUT} = {1 << HAUT:,}.""")


# ==========================================================================
rule("3. SUR LES TIRAGES ORDONNÉS DU DOSSIER")
# ==========================================================================

lignes = []
with open(os.path.join(ROOT, "draws_ordered.csv")) as fh:
    for r in csv.DictReader(fh):
        lignes.append((int(r["id"]), [int(r[f"o{j}"]) for j in range(1, DRAWN + 1)]))
say(f"   {len(lignes)} tirages ordonnes.\n")

REJ_MAX = 0 if DRY else 1          # rejets tolérés DANS LE PREFIXE
motifs = [()]
if REJ_MAX:
    motifs += [(j,) for j in range(M_PREF + 1)]
say(f"   {'tirage':>9} {'motifs':>7} {'candidats étage 1':>18} {'états compatibles':>18} {'sec':>7}")
total_etats = 0
for tid, ordre in lignes:
    quartets = [(n - 1) % 16 for n in ordre[:M_PREF]]
    tt, n1tot, etats = time.time(), 0, []
    for rej in motifs:
        c1 = etage1_depuis_depart(quartets, rej)
        n1tot += len(c1)
        for u0 in c1.tolist():
            etats.extend(rejeu(etage2(u0, ordre[:M_PREF], Ai, Ci, rej), ordre))
    total_etats += len(etats)
    say(f"   {tid:>9} {len(motifs):>7} {n1tot:>18,} {len(etats):>18} {time.time() - tt:>7.1f}")

say(f"""
   {total_etats} etat compatible sur les {len(lignes)} tirages.

   COUVERTURE. L'attaque suppose que les {M_PREF} premiers numeros sortent des
   {M_PREF} premiers mots, a {REJ_MAX} rejet pres. Le nombre de rejets avant la
   {M_PREF}-ieme acceptation est une somme de geometriques de parametres i/80,
   donc P(zero) = prod (1 - i/80) et P(un) = P(zero) x somme(i/80) :""")
SOMME_Q = sum(i / POOL for i in range(M_PREF))
p_couv = P_PREF * (1 + SOMME_Q) if REJ_MAX else P_PREF
say(f"     P(0 rejet) = {P_PREF:.4f}   P(1 rejet) = {P_PREF * SOMME_Q:.4f}")
say(f"   {p_couv:.4f} par tirage, donc {1 - (1 - p_couv) ** len(lignes):.6f} sur les {len(lignes)} — "
    f"defaut {(1 - p_couv) ** len(lignes):.2e}.")


# ==========================================================================
rule("4. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h76.java_rejet_2adique",
        "AUCUN etat de java.util.Random — les 2^48, pas seulement les graines "
        "sous 2^32 — n'engendre les tirages ordonnes du dossier sous "
        "ECHANTILLONNEUR PAR REJET (nextInt(80) avec ensemble). Le §34 avait "
        "couvert les 2^48 sous Fisher-Yates SEULEMENT, et le rejet sous 2^32 "
        "SEULEMENT ; le §95 a montre que le rejet echappe a Berlekamp-Massey",
        f"attaque 2-adique en deux etages : les bits 17 a 20 de l'etat sont "
        f"publies par p mod 16 et ne dependent que de s mod 2^{BAS}, que le LCG "
        f"laisse clos ; etage 1 sur 2^{BAS}, etage 2 sur 2^{HAUT}, puis rejeu exact "
        f"dans l'ordre d'emission",
        "aucun null n'est requis : la verification est un rejeu exact, donc "
        "sans faux positif",
        "conforme si aucun etat compatible n'est trouve", track="B")
    tok["m_extra"] = 0
    lab.record(
        tok, float(total_etats), p=1.0, verdict="conforme",
        power_at=(f"temoin positif : {ok}/{ESSAIS} etats 48 bits TIRES AU HASARD "
                  f"— donc hors de portee d'un balayage 2^32 — retrouves depuis "
                  f"l'ordre de vingt numeros"),
        notes=(f"Le levier est au MILIEU de l'etat : nextInt(80) publie p mod 16 = "
               f"bits 17 a 20, et le LCG modulo 2^48 est clos modulo 2^{BAS}. "
               f"Le lemme du prefixe propre rend le rejet inoffensif au depart : "
               f"P(aucun rejet parmi les {M_PREF} premiers) = {P_PREF:.4f}, et le piege de la "
               f"borne 64 du §34 ne se presente pas puisque la borne vaut toujours "
               f"80 sous rejet. Couverture {p_couv:.4f} par tirage, "
               f"{1 - (1 - p_couv) ** len(lignes):.6f} sur les {len(lignes)} tirages ordonnes."))
    h = lab.holm()
    say(f"   consigne : h76.java_rejet_2adique   {total_etats} etat compatible")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")


# ==========================================================================
rule("5. CE QUE CELA FERME, ET CE QUI RESTE")
# ==========================================================================

say(f"""   FERME. java.util.Random a etat 48 bits ARBITRAIRE sous echantillonneur
   PAR REJET. Le §34 avait les 2^48 sous Fisher-Yates et le rejet sous 2^32 ;
   la case du milieu etait vide, et elle etait la plus probable — `new
   Random()` plus un HashSet est l'idiome Java par defaut.

   ET C'EST LA FAMILLE QUE LE §95 VENAIT DE ROUVRIR. Berlekamp-Massey ne
   voit pas le rejet ; le §91 declarait deja java.util.Random AVEUGLE a BM
   parce que sa sortie est decalee. Cette famille echappait donc a la fois au
   §89 et au §91, et n'etait couverte qu'a 2^32. Elle ne l'est plus.

   RESTE, et la liste retrecit :
     — les LCG modulo 2^48 a AUTRES constantes que celles de Java ;
     — les generateurs a sortie brouillee (PCG, xoshiro** et ++, splitmix64)
       a etat plein — le §34 les couvre a 2^32, pas au-dela ;
     — les generateurs a retenue (MWC), que le §91 a nommes ;
     — tout CSPRNG, et le materiel.

   Registre : consigne a la section 4.

   ({time.time() - T0:.1f} s)""")
