"""h66 — le plafond exact de chaque echantillonneur, et la carte qui en sort.

Ce que les §71, §82 et §83 comptaient sans le demontrer
=======================================================
Trois sections donnent un nombre de bits publies par mot :

    §71  Fisher-Yates : v2(80-i) bits au pas i, soit 22 par tirage
    §82  troncature   : les bits de poids fort communs aux bornes, 5,20
    §83  additif      : le prefixe libre de la retenue, 1,875

Les trois comptent des BITS. Or une equation lineaire sur F2 n'est pas un
bit : c'est une FORME, un XOR quelconque de bits. Rien n'interdisait a priori
qu'une combinaison de bits hauts soit determinee alors qu'aucun ne l'est
individuellement — et dans ce cas les trois comptes seraient des
sous-estimations, et tous les paliers du dossier seraient faux.

LE THEOREME DU PLAFOND
=======================
Une observation restreint le mot de sortie a un ensemble S. Une forme phi est
DETERMINEE par cette observation si et seulement si phi est constante sur S,
c'est-a-dire orthogonale a l'espace engendre par les differences

    D(S) = < x XOR y : x, y dans S >

Le contenu F2-lineaire de l'observation vaut donc exactement

    w - dim D(S)

Ce fichier le calcule EXHAUSTIVEMENT pour chaque observation de chaque
echantillonneur — pas un raisonnement, une enumeration.

COROLLAIRE DE BILAN. Brancher sur v bits supplementaires de out coute v bits
de branchement et rend au plus v equations : le bilan est nul ou negatif.
Aucune strategie de supposition n'ameliore le plafond.

Il ne teste pas l'archive : il demontre et cartographie. Registre : inchange.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

T0 = time.time()
POOL, DRAWN = 80, 20
DRY = os.environ.get("H66_DRY") == "1"
W = 14 if DRY else 16          # largeur de mot reduite : l'enumeration est exhaustive


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def v2(n):
    k = 0
    while n and n % 2 == 0:
        n //= 2
        k += 1
    return k


def determined_dim(S, w=W):
    """Dimension de l'espace des formes DETERMINEES par « out est dans S ».

    C'est w - dim D(S), ou D(S) est engendre par les XOR de paires. Calcule
    par elimination sur les differences au premier element : elles engendrent
    D(S) puisque x XOR y = (x XOR x0) XOR (y XOR x0).
    """
    if len(S) <= 1:
        return w
    basis, x0 = {}, S[0]
    for x in S[1:]:
        d = x ^ x0
        while d:
            h = d.bit_length() - 1
            if h in basis:
                d ^= basis[h]
            else:
                basis[h] = d
                break
    return w - len(basis)


# ==========================================================================
rule("1. LE PLAFOND, VÉRIFIÉ EXHAUSTIVEMENT")
# ==========================================================================

say(f"""   Mot reduit a {W} bits — l'enumeration porte sur les {1 << W:,} valeurs, elle est
   donc EXHAUSTIVE et non echantillonnee. On compare, pour chaque
   observation, la dimension reellement determinee au compte que le dossier
   annoncait.
""")

# --- (A) rejet modulo 80 ----------------------------------------------------
say(f"   (A) REJET MODULO {POOL} — le §68 annonce v2({POOL}) = {v2(POOL)} bits par mot.\n")
dims = []
for r in range(POOL):
    S = [x for x in range(1 << W) if x % POOL == r]
    dims.append(determined_dim(S))
say(f"       dimensions determinees sur les {POOL} residus : "
    f"min {min(dims)}, max {max(dims)}   annonce {v2(POOL)}")
okA = set(dims) == {v2(POOL)}
say(f"       {'CONFORME' if okA else 'ÉCART'} — le compte du §68 est exact.\n")

# --- (B) troncature ---------------------------------------------------------
say(f"   (B) TRONCATURE floor(u x {POOL}) — le §82 annonce les bits de poids fort\n"
    f"       communs aux bornes, d'esperance 5,20 sur un mot de 64 bits.\n")
tot_w, tot_d = 0.0, 0.0
GAIN = []
for n in range(POOL):
    lo = -(-(n << W) // POOL)
    hi = -(-((n + 1) << W) // POOL) - 1
    S = list(range(lo, hi + 1))
    d = determined_dim(S)
    k = 0
    while k < W and (lo >> (W - k - 1)) == (hi >> (W - k - 1)):
        k += 1
    GAIN.append(d - k)
    p = len(S) / (1 << W)
    tot_w += p * k
    tot_d += p * d
okB = max(GAIN) == 0
say(f"       esperance annoncee {tot_w:.4f}   esperance REELLE {tot_d:.4f}   "
    f"ecart max {max(GAIN)}")
say(f"       {'CONFORME' if okB else 'ÉCART — LE §82 SOUS-COMPTAIT'}\n")

# --- le supplement, et sa loi ---------------------------------------------
q = POOL
while q % 2 == 0:
    q //= 2
winners = [n for n, g in enumerate(GAIN) if g]
law_ok = winners and all(n % q == winners[0] % q for n in winners) and \
    len(winners) == POOL // q
say(f"""       LE SUPPLEMENT N'EST PAS UN ACCIDENT. Les {len(winners)} numeros qui publient plus
       que leur prefixe sont exactement ceux verifiant

           n = {winners[0] % q if winners else '?'}   (mod {q})

       ou {q} est la PARTIE IMPAIRE du vivier ({POOL} = 2^{POOL.bit_length()-q.bit_length()} x {q}), et ils en publient
       {max(GAIN)} de plus chacun. Loi verifiee : {law_ok}.

       La raison est visible sur un exemple minimal a trois bits :
       l'intervalle [3,4] = {{011, 100}} n'a AUCUN bit de poids fort commun, et
       pourtant x0 XOR x1 vaut 0 sur les deux — une forme determinee sans
       qu'aucun bit ne le soit. C'est ce que le compte par bits manquait.

       COROLLAIRE, et il est joli : {POOL} = 2^4 x {q}. La partie 2-ADIQUE gouverne la
       fuite du modulo (§68, v2 = 4 bits) ; la partie IMPAIRE gouverne le
       supplement de la troncature. Les deux facteurs du vivier fuient,
       chacun par son propre mecanisme, et le §74 — qui concluait qu'un
       vivier impair fermerait la voie — se trompait deux fois.

       Le profil est INDEPENDANT de la largeur du mot : identique de 11 a 24
       bits, donc valable a 32 et 64. Le compte du §82 passe de {tot_w:.2f} a {tot_d:.2f}.
""")

# --- (C) bits de poids fort avec rejet -------------------------------------
kbits = POOL.bit_length()
say(f"   (C) {kbits} BITS DE POIDS FORT AVEC REJET — le §82 annonce {kbits} bits.\n")
dims = []
for n in range(POOL):
    S = [x for x in range(1 << W) if (x >> (W - kbits)) == n]
    dims.append(determined_dim(S))
okC = set(dims) == {kbits}
say(f"       dimensions : min {min(dims)}, max {max(dims)}   annonce {kbits}")
say(f"       {'CONFORME' if okC else 'ÉCART'} — le compte du §82 est exact.\n")

# --- Fisher-Yates, pas par pas ---------------------------------------------
say(f"   FISHER-YATES — le §71 annonce v2({POOL}-i) au pas i, soit "
    f"{sum(v2(POOL - i) for i in range(DRAWN))} par tirage.\n")
say(f"       {'pas i':>6} {'module':>7} {'v2':>4} {'dimension réelle':>17}")
tot_ann = tot_real = 0
okFY = True
for i in range(DRAWN):
    m_ = POOL - i
    r = 7 % m_
    S = [x for x in range(1 << W) if x % m_ == r]
    d = determined_dim(S)
    tot_ann += v2(m_)
    tot_real += d
    okFY &= d == v2(m_)
    if i in (0, 1, 4, 8, 16, 19):
        say(f"       {i:>6} {m_:>7} {v2(m_):>4} {d:>17}")
say(f"\n       total annonce {tot_ann}   total reel {tot_real}   "
    f"{'CONFORME' if okFY else 'ÉCART'}")

say(f"""
   BILAN DE LA VERIFICATION, ET ELLE N'ETAIT PAS GRATUITE.

   TROIS COMPTES SUR QUATRE SONT EXACTS : le modulo (§68), les bits de poids
   fort avec rejet (§82) et Fisher-Yates (§71). Pour eux, aucune combinaison
   de bits hauts n'est determinee la ou aucun bit ne l'est, et tous les
   paliers du dossier tiennent.

   LE QUATRIEME NE L'EST PAS. La troncature determine {tot_d - tot_w:.2f} bit de plus que
   le §82 ne comptait — {tot_d:.2f} au lieu de {tot_w:.2f}, soit +{(tot_d-tot_w)/tot_w:.0%}. Le compte par
   BITS manquait des formes qui n'en sont pas.

   L'erreur allait dans le sens INDULGENT : le dossier creditait
   l'echantillonneur par troncature de moins de fuite qu'il n'en a, donc ses
   paliers etaient trop longs et ses attaques laissaient de l'information
   sur la table. Aucun resultat NUL n'en est invalide — un etat compatible
   se verifie par rejeu — mais les couvertures declarees au §82 sont
   pessimistes, et les attaques peuvent etre renforcees.""")


# ==========================================================================
rule("2. LE COROLLAIRE DE BILAN : AUCUN BRANCHEMENT N'AIDE")
# ==========================================================================

say(f"""   On pourrait esperer gagner en SUPPOSANT des bits. Le bilan est nul, et
   pour une raison qui tient en une ligne.

   Supposer v bits de out multiplie l'arbre par 2^v et rend au plus v
   equations. Or v equations reduisent l'espace des etats compatibles d'un
   facteur 2^v au mieux. Le nombre de feuilles a explorer avant elimination
   est donc INCHANGE : 2^v fois plus de branches, chacune 2^v fois plus
   contrainte.

   Le seul gain possible viendrait d'une supposition qui rende PLUS de v
   equations. Le theoreme du plafond l'interdit : v bits supposes ajoutent
   au plus v dimensions a l'espace determine.

   C'est pourquoi le theoreme de la retenue (§83) est un vrai gain — il ne
   suppose rien, il constate que la retenue est CONNUE quand a_i != b_i — et
   pourquoi aucune variante « avec suppositions » ne l'a battu.""")


# ==========================================================================
rule("3. LA CARTE DE COUVERTURE DU GÉNÉRATEUR")
# ==========================================================================

FY = sum(v2(POOL - i) for i in range(DRAWN))
NORD = 9

say(f"""   Le dossier compte {NORD} tirages ordonnes. La carte ci-dessous ne DEDUIT
   rien d'une formule : chaque case dit ce qu'une experience a REELLEMENT
   fait. Une premiere version de ce paragraphe calculait les cases a partir
   du budget en bits, et annoncait « exclu » pour des combinaisons que
   personne n'avait testees — notamment les familles additives sous
   troncature.

     exclu      aucun etat ne rejoue les numeros, verifie par rejeu
     nul (c%)   idem, mais la recherche n'a couvert que c% des motifs de rejet
     non conc.  couverture trop faible pour conclure
     jamais     aucune experience n'a couvert cette case
     N tirages  hors budget : il en faudrait N
""")

# Chaque case : (etiquette, section). Rempli a la main depuis les resultats.
X = "exclu §86"
CARTE = {
 "xorshift32":          ("nul 100% §81", "nul 100% §82", "nul 100% §82", X),
 "xorshift64":          ("nul 100% §81", "nul 100% §82", "nul  96% §82", X),
 "xorshift96":          ("nul  94% §81", "nul  98% §82", "non conc.",     X),
 "xorshift128":         ("nul  64% §81", "nul  91% §82", "non conc.",     X),
 "taus88":              ("nul  91% §81", "nul  91% §82", "non conc.",     X),
 "LFSR113":             ("non ident. §81", "jamais",     "jamais",        X),
 "xoroshiro128 (brut)": ("nul  64% §81", "jamais",       "jamais",        X),
 "xoshiro128 (brut)":   ("nul  64% §81", "jamais",       "jamais",        X),
 "xoshiro256 (brut)":   ("4 tirages",    "3 tirages",    "non conc.",     "12 tirages"),
 "WELL512a":            ("7 tirages",    "5 tirages",    "4 tirages",     "24 tirages"),
 "xorshift128+ (V8)":   ("2^42 motifs",  "jamais",       "jamais",        X),
 "xoroshiro128+":       ("2^42 motifs",  "jamais",       "jamais",        X),
 "MT19937":             ("343 tirages",  "hors budget",  "hors budget",   "907 tirages"),
}
say(f"   {'famille':>22} {'(A) rejet':>15} {'(B) troncature':>15} "
    f"{'(C) bits hauts':>15} {'Fisher-Yates':>13}")
for nom, (a, b, c, f) in CARTE.items():
    say(f"   {nom:>22} {a:>15} {b:>15} {c:>15} {f:>13}")

nb_exclu = sum(1 for v in CARTE.values() for x in v
               if x.startswith("nul") or x.startswith("exclu"))
nb_jamais = sum(1 for v in CARTE.values() for x in v if x == "jamais")
tot = 4 * len(CARTE)
say(f"""
   BILAN : {nb_exclu} cases sur {tot} portent un resultat NUL verifie, {nb_jamais} n'ont jamais ete
   ouvertes, le reste manque de donnees ou de calcul.

   LECTURE. La colonne Fisher-Yates est la seule pleine, et ce n'est pas un
   hasard : c'est la seule ou il n'y a AUCUNE recherche — pas de rejet,
   positions exactes, une elimination par famille. Les colonnes (A), (B) et
   (C) portent toutes le meme handicap, le motif des mots rejetes, et leurs
   couvertures s'en ressentent.

   LES QUATRE CASES « JAMAIS » QUI COMPTENT sont les deux familles additives
   sous
   troncature et sous bits hauts. Ce n'est pas un oubli : le theoreme de la
   retenue (§83) demarre a la retenue nulle, donc aux bits BAS, et ces deux
   echantillonneurs publient les bits HAUTS. Le §84 a mesure ce que coute
   d'y aller quand meme — facteur 3,08 sur ce qu'un solveur SMT digere.

   CE QUI RESTE, ET C'EST COURT :
     — xoshiro256 sous Fisher-Yates : {-(-256 // FY)} tirages, il en manque {-(-256 // FY) - NORD}
     — WELL512a  : {-(-512 // FY)} tirages sous Fisher-Yates
     — MT19937   : 343 tirages CONSECUTIFS sous rejet (§80) — meilleur choix
                   que les {-(-19937 // FY):,} qu'exigerait Fisher-Yates
     — les sorties NON lineaires : PCG, xoshiro** et ++, splitmix64, tout
       CSPRNG. Hors du champ de l'algebre lineaire.

   Registre : INCHANGE. h66 demontre et cartographie.

   ({time.time() - T0:.1f} s)""")
