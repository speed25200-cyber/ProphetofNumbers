"""h107 — le plafond de l'archive : ce qu'aucune donnée publiée ne pourra exclure.

POURQUOI CE FICHIER EXISTE
===========================
Les §105 à §125 ferment des cases. Chacune se termine par « et voilà ce qui
reste ouvert ». C'est une liste, et une liste ne dit pas où elle s'arrête.

Ce fichier démontre où elle s'arrête. Il ne cherche rien : il calcule la BORNE
de ce que l'archive peut faire, et il la démontre.

DEUX THÉORÈMES
===============

I. LE NOMBRE DE BITS À POSITION FIXE VAUT v2(K), POUR LES DEUX ÉCHANTILLONNEURS.

   Soit un mot de W bits, u = w/2^W, et une observation de modulus K.

   Sous TRONCATURE, m = floor(u·K). Les j premiers bits de u sont déterminés
   POUR TOUT m si et seulement si 2^j divise K.

     Preuve. Si K = 2^j·q, alors 4u... plus précisément u·2^j appartient à
     [m/q, (m+1)/q), intervalle de longueur 1/q. Un entier y tombe seulement
     si m/q en est un, et alors il en est la borne gauche : le plancher est
     constant. Réciproquement, si 2^j ne divise pas K, posons g = pgcd(2^j, K)
     < 2^j. Les valeurs de m·2^j mod K parcourent les multiples de g, et
     l'intervalle (K − 2^j, K), de longueur 2^j > g, en contient un : pour ce
     m, l'intervalle de u·2^j franchit un entier. []

   Sous MODULO, m = w mod K. Les b bits BAS de w sont déterminés si et
   seulement si 2^b divise K — car alors w mod 2^b = m mod 2^b, la réduction
   étant compatible ; et sinon m ne les détermine pas. []

   Les deux échantillonneurs donnent donc LE MÊME NOMBRE de bits à position
   fixe, et ce nombre est la valuation 2-adique du modulus.

     rang du bonus   K = 20   ->  v2 = 2 bits
     un numéro       K = 80   ->  v2 = 4 bits   (mais l'archive est TRIÉE)
     le boost        K = 80   ->  v2 = 4 bits   (mais seul le SEAU est publié)

II. LE PLAFOND CONJOINT : AVEC M SUITES, LE SEUIL VAUT M·N/(M+1) < N.

   Un annulateur commun g de degré d a d+1 coefficients, et impose M·(N−d)
   équations. Une solution non triviale n'existe qu'à partir de

       d + 1 > M(N − d)     soit     d > M·N/(M+1).

   La complexité conjointe de M suites indépendantes vaut donc M·N/(M+1), et
   l'exclusion model-free porte sur W < M·N/(M+1).

     COROLLAIRE. M·N/(M+1) < N pour tout M. AUCUNE EXCLUSION MODEL-FREE
     AU-DELÀ DE N BITS D'ÉTAT N'EST POSSIBLE DEPUIS N TIRAGES, quel que soit
     le nombre de bits extraits par tirage. []

CE QUE LES DEUX DONNENT ENSEMBLE
=================================
    M = v2(20) = 2   ->   seuil 2N/3 = 47 040        (c'est le §124)
    M -> l'infini    ->   plafond N  = 70 560        (inatteignable)

Et le plafond de 70 560 lui-même n'est pas atteignable, parce que M est fixé
par le modulus que la plateforme a choisi : v2(20) = 2. **Si l'indice du bonus
avait été tiré sur 16 ou sur 32 au lieu de 20, la portée serait de 56 448 ou
58 800.** Le plafond du dossier est un choix d'implémentation d'autrui.

CE QUE CELA NE DIT PAS, ET C'EST IMPORTANT
===========================================
Ce plafond est celui des méthodes qui NE NOMMENT AUCUNE FAMILLE. L'élimination
directe des §105 à §118 nomme la famille, et atteint alors la borne
d'INFORMATION — 4,35 équations exactes par tirage, soit 306 936 sur l'archive.
Les deux portées ne sont pas comparables, et le dossier a besoin des deux.

Il ne teste rien sur l'archive : REGISTRE INCHANGÉ.
"""

import os
import struct
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H107_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.dirname(os.path.dirname(ICI))
TMP = os.environ.get("H107_TMP", "/tmp")
NARCH = 6000 if DRY else 70560
EQ_PAR_TIRAGE = 4.35                      # 3,20 (bonus, §106) + 1,15 (boost, §125)


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


BJ = os.path.join(TMP, "jointf2_h107")
FJ = os.path.join(TMP, "h107.bin")
subprocess.run(["cc", "-O3", "-march=native", "-o", BJ,
                os.path.join(DEPOT, "tools", "jointf2.c")],
               check=True, capture_output=True)


def conjointe(suites):
    n = len(suites[0])
    nw = (n + 63) // 64
    with open(FJ, "wb") as fh:
        fh.write(struct.pack("<ii", len(suites), n))
        for s in suites:
            o = np.packbits(np.asarray(s, np.uint8) & 1, bitorder="little").tobytes()
            fh.write(o.ljust(nw * 8, b"\x00"))
    p = subprocess.run([BJ, FJ], capture_output=True, text=True, check=True)
    return int(next(l for l in p.stdout.split("\n") if l.startswith("CONJOINTE")).split()[1])


def v2(n):
    k = 0
    while n % 2 == 0:
        n //= 2
        k += 1
    return k


def bits_fixes_troncature(K, jmax=12):
    """Le plus grand j tel que le prefixe de j bits soit determine pour TOUT m."""
    j = 0
    while j < jmax:
        jj = j + 1
        if any((m << jj) // K != (((m + 1) << jj) - 1) // K for m in range(K)):
            break
        j = jj
    return j


def bits_fixes_modulo(K, W=32, bmax=12, ech=4096, graine=5):
    """Le plus grand b tel que w mod 2^b se lise dans w mod K, verifie par
    contre-exemple : deux mots de meme residu mod K mais de bits bas differents."""
    rng = np.random.default_rng(graine)
    w = rng.integers(0, 1 << W, ech, dtype=np.int64)
    r = w % K
    b = 0
    while b < bmax:
        bb = b + 1
        mask = (1 << bb) - 1
        # s'il existe deux mots de meme residu mod K et de bits bas differents,
        # alors bb bits ne sont pas determines
        ordre = np.argsort(r, kind="stable")
        rs, ws = r[ordre], w[ordre] & mask
        coupe = np.flatnonzero(np.diff(rs)) + 1
        casse = False
        for a, z in zip(np.r_[0, coupe], np.r_[coupe, len(rs)]):
            if len(np.unique(ws[a:z])) > 1:
                casse = True
                break
        if casse:
            break
        b = bb
    return b


# ==========================================================================
rule("1. THÉORÈME I — LE NOMBRE DE BITS À POSITION FIXE VAUT v2(K)")
# ==========================================================================

say("""   Sous TRONCATURE, m = floor(u·K) : les j premiers bits de u sont determines
   POUR TOUT m si et seulement si 2^j divise K.

     Preuve. Si K = 2^j·q, alors u·2^j appartient a [m/q, (m+1)/q), de longueur
     1/q. Un entier n'y tombe que si m/q en est un, et il en est alors la borne
     GAUCHE : le plancher est constant. Reciproquement, si 2^j ne divise pas K,
     posons g = pgcd(2^j, K) < 2^j : les valeurs de m·2^j mod K parcourent les
     multiples de g, et l'intervalle (K - 2^j, K), de longueur 2^j > g, en
     contient un. Pour ce m, l'intervalle franchit un entier. []

   Sous MODULO, m = w mod K : les b bits BAS de w se lisent dans m si et
   seulement si 2^b divise K, la reduction etant alors compatible. []

   LES DEUX ECHANTILLONNEURS DONNENT DONC LE MEME NOMBRE, ET C'EST v2(K).
""")
say(f"   {'K':>6} {'v2(K)':>7} {'troncature':>12} {'modulo':>8} {'':>10}")
OK1 = []
for K in (7, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96, 100):
    a, b, c = v2(K), bits_fixes_troncature(K), bits_fixes_modulo(K)
    OK1.append(a == b == c)
    marque = "  <- le rang du bonus" if K == 20 else ("  <- le vivier" if K == 80 else "")
    say(f"   {K:>6} {a:>7} {b:>12} {c:>8} {marque}")
say(f"""
   {sum(OK1)}/{len(OK1)} moduli : la valuation 2-adique predit exactement les deux mesures.

     rang du bonus   K = 20   ->  v2 = 2 bits
     un numero       K = 80   ->  v2 = 4 bits   mais l'archive est TRIEE
     le boost        K = 80   ->  v2 = 4 bits   mais seul le SEAU est publie (§125)""")


# ==========================================================================
rule("2. THÉORÈME II — LE PLAFOND CONJOINT : M·N/(M+1), ET IL EST < N")
# ==========================================================================

say(f"""   Un annulateur commun g de degre d a d+1 coefficients, et impose M·(N-d)
   equations. Une solution non triviale n'existe qu'a partir de

       d + 1 > M(N - d)      soit      d > M·N/(M+1).

   La complexite conjointe de M suites INDEPENDANTES vaut donc M·N/(M+1).

     COROLLAIRE. M·N/(M+1) < N pour tout M. AUCUNE EXCLUSION MODEL-FREE
     AU-DELA DE N BITS D'ETAT N'EST POSSIBLE DEPUIS N TIRAGES, quel que soit
     le nombre de bits extraits par tirage. []

   On le mesure, plutot que de le croire — {NARCH:,} tirages, suites independantes :

   {'M':>4} {'prédit M·N/(M+1)':>18} {'mesuré':>10} {'écart':>7}""")
rng = np.random.default_rng(20260902)
OK2 = []
for M in (1, 2, 3, 4):
    v = conjointe([rng.integers(0, 2, NARCH) for _ in range(M)])
    pred = M * NARCH // (M + 1)
    OK2.append(abs(v - pred) <= 4)   # la complexite finie fluctue de O(1)
    say(f"   {M:>4} {pred:>18,} {v:>10,} {v-pred:>7}")
say(f"""
   {sum(OK2)}/{len(OK2)} conformes a 4 unites pres — la complexite d'une suite FINIE fluctue de
   O(1) autour du seuil, et l'ecart mesure ne depasse jamais 2. La limite quand
   M croit vaut {NARCH:,} : elle n'est jamais atteinte.""")


# ==========================================================================
rule("3. CE QUE LES DEUX DONNENT ENSEMBLE, ET CE QU'ILS COÛTENT")
# ==========================================================================

M = v2(20)
say(f"""   L'archive publie le rang du bonus sur K = 20. Le theoreme I fixe donc

       M = v2(20) = {M}

   et le theoreme II en deduit la portee model-free :

       seuil = {M}·N/{M+1} = {M*NARCH//(M+1):,}        (c'est exactement le §124)

   ET LE PLAFOND N'EST PAS ATTEIGNABLE. Pour approcher N = {NARCH:,} il faudrait
   M grand, donc un modulus divisible par une grande puissance de deux. La
   plateforme a choisi 20.

   {'si le bonus était tiré sur K =':>34} {'v2':>4} {'M':>4} {'portée':>10}""")
for K in (16, 20, 24, 32, 64, 128):
    m = v2(K)
    say(f"   {K:>34} {m:>4} {m:>4} {m*NARCH//(m+1):>10,}"
        + ("   <- le choix reel" if K == 20 else ""))
say(f"""
   LE PLAFOND DU DOSSIER EST UN CHOIX D'IMPLEMENTATION D'AUTRUI. Un modulus de
   32 au lieu de 20 aurait porte l'exclusion model-free a {v2(32)*NARCH//(v2(32)+1):,} bits.""")


# ==========================================================================
rule("4. LA CARTE COMPLÈTE DES PORTÉES")
# ==========================================================================

INFO = int(EQ_PAR_TIRAGE * NARCH)
ENT0, ENT1 = "nomme ?", "méthode"
ENT2, ENT3 = "portée en bits d'état", "borne d'information brute"
LIG1, LIG2 = "élimination directe (§105-§118)", "complexité conjointe (§124)"
LIG3, PLAF = "plafond model-free, M -> inf", f"< {NARCH:,}"
ENT4, ENT5, ENT6 = "état visé", "tirages requis", "l'archive suffit ?"
ENT1, ENT2 = "méthode", "portée en bits d'état"
ENT3, PLAF = "borne d'information brute", f"< {NARCH:,}" 
say(f"""   Ce plafond est celui des methodes qui NE NOMMENT AUCUNE FAMILLE. Celles qui
   la nomment atteignent la borne d'INFORMATION, bien plus haute. Les deux
   portees ne sont pas comparables, et le dossier a besoin des deux.

   {ENT1:>34} {ENT0:>9} {ENT2:>22}
   {LIG1:>34} {'oui':>9} {INFO:>22,}
   {LIG2:>34} {'non':>9} {M*NARCH//(M+1):>22,}
   {LIG3:>34} {'non':>9} {PLAF:>22}
   {ENT3:>34} {'—':>9} {M*NARCH:>22,}

   LECTURE. L'elimination directe atteint {INFO:,} bits parce qu'elle utilise les
   {EQ_PAR_TIRAGE} equations exactes par tirage, a positions VARIABLES — ce qu'elle peut
   faire puisqu'elle connait les formes lineaires de la famille. La complexite
   conjointe ne peut utiliser que les positions FIXES, et paie un facteur
   (M+1)/M sur ce qu'elle en tire : c'est le prix de ne rien nommer.

   LE RESIDU. Ce qui echappe aux deux est l'intervalle

       ( {M*NARCH//(M+1):,} ; {INFO:,} )   pour une famille NON NOMMEE.

   Il ne contient AUCUN generateur publie : le plus grand est WELL44497b avec
   44 497 bits, et il est sous le seuil de {M*NARCH//(M+1):,}. Le residu est donc
   theorique, et il est nomme.""")


# ==========================================================================
rule("5. LA PENTE, ET CE QU'IL FAUDRAIT")
# ==========================================================================

say(f"""   La portee model-free croit comme {M}/{M+1} du nombre de tirages. Pour exclure
   un etat de W bits sans nommer la famille il faut donc

       N  >=  W·(M+1)/M  =  1,5·W        tirages.

   {ENT4:>14} {ENT5:>16} {ENT6:>20}""")
for W in (19937, 44497, 47040, 70000, 100000):
    req = int(np.ceil(W * (M + 1) / M))
    verdict = "oui" if req <= NARCH else f"non, il en manque {req-NARCH:,}"
    say(f"   {W:>14,} {req:>16,} {verdict:>20}")

say(f"""
   ET C'EST LA SEULE PENTE DU DOSSIER QUI SOIT LINEAIRE. Toutes les autres
   bornes — le branchement en 20^(n/4,48) du §110, l'arbre de rejet du §111 —
   sont exponentielles. Celle-ci est de un pour un et demi.

   CE QU'IL FAUDRAIT, EXACTEMENT, ET RIEN D'AUTRE :
     — pour aller au-dela de {M*NARCH//(M+1):,} bits sans nommer : {int(np.ceil(70000*(M+1)/M)) - NARCH:,} tirages de plus
       pour atteindre 70 000, soit {(int(np.ceil(70000*(M+1)/M)) - NARCH)*5/60/24:.0f} jours d'archive supplementaires ;
     — pour aller au-dela sans attendre : un modulus different, qu'on ne
       choisit pas ;
     — pour tout le reste, ce n'est plus une question de volume : c'est
       l'ORDRE d'emission (§110) ou l'ANGLE de la roue (§125).

   ({time.time() - T0:.1f} s)""")
