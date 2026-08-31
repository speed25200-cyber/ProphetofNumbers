"""h73 — le theoreme du contenu : ce que l'archive TRIEE publie vraiment.

L'AFFIRMATION QUE TOUT LE DOSSIER REPETE
=========================================
    §11  « l'archive est triee, l'ordre est perdu »
    §47  « contre toute hypothese d'ordre, la puissance est exactement nulle »
    §88  « l'ordre y est perdu. SAUF POUR UNE CHOSE » — le bonus, 4 bits

Les §68 a §92 en tirent tous la meme consequence : les attaques algebriques
ont besoin des NEUF tirages ordonnes, et l'archive de 70 560 lignes ne sert
qu'a une chose, le bonus.

C'EST FAUX, ET L'ERREUR SE VOIT DANS UNE IDENTITE
==================================================
                          80 = 16 x 5

Seize DIVISE quatre-vingts. Donc, pour l'echantillonneur « n = (out mod 80)
+ 1 » :

    (n - 1) mod 16  =  (out mod 80) mod 16  =  out mod 16

Le QUARTET DE POIDS FAIBLE de chaque numero tire est le quartet de poids
faible du mot de sortie — c'est-a-dire, pour un generateur F2-lineaire a
sortie brute, QUATRE FORMES LINEAIRES EXACTES de l'etat.

Et le MULTIENSEMBLE des vingt quartets est INVARIANT PAR PERMUTATION. Le tri
ne le detruit pas. Il est lisible sur chacune des 70 560 lignes.

COMBIEN CELA PESE, EXACTEMENT
==============================
Ce fichier le calcule en forme close, sans simulation :

    H(multiensemble des quartets)
        = log2 C(80,20)  -  16 x E[ log2 C(5, m) ]

ou m est le nombre de numeros tires dans une classe residuelle donnee. La
preuve est en trois lignes et n'utilise aucune independance (section 1).

Le resultat est 27,26 BITS PAR TIRAGE — contre les 4 du bonus. Le dossier
laissait dormir un facteur SIX VIRGULE HUIT, sur toutes ses lignes.

CE QUI NE MARCHE PAS, ET IL FAUT LE DEMONTRER AVANT
====================================================
La tentation immediate est la PARITE : le XOR des vingt quartets est la seule
fonctionnelle F2-LINEAIRE invariante par permutation. La section 3 demontre
qu'elle est DETRUITE par le rejet — les mots rejetes dupliquent des valeurs
acceptees, et le XOR des doublons parcourt F2^4. Ce qui reste est une
instance de « parite bruitee » a taux 0,46 : intraitable.

L'information est donc bien la, mais elle n'est pas LINEAIRE. C'est une
contrainte de multiensemble. La section 4 dit ce que cela change, et la
section 5 nomme l'angle mort du §89 que cela ouvre.

Il ne teste rien sur l'archive : il ne consigne RIEN. C'est de la theorie de
l'information exacte, plus une verification sur les donnees.
"""

import math
import os
import sys
import time
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
POOL, DRAWN = 80, 20
MOD = 16                       # le diviseur F2-pertinent de 80
PAR_CLASSE = POOL // MOD       # 5 numeros par classe residuelle


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# ==========================================================================
rule("1. LE THÉORÈME DU CONTENU")
# ==========================================================================

say(f"""   L'IDENTITE. {MOD} divise {POOL}. Donc pour l'echantillonneur par modulo,
   (n - 1) mod {MOD} = out mod {MOD} : le quartet de poids faible du numero EST
   celui du mot. Pour un generateur F2-lineaire a sortie brute, ce sont
   quatre formes lineaires exactes de l'etat.

   Le MULTIENSEMBLE des {DRAWN} quartets est invariant par permutation, donc
   lisible sur l'archive triee. Reste a savoir ce qu'il pese.

   THEOREME. Soit D un {DRAWN}-sous-ensemble uniforme de [{POOL}], et
   m = (m_0, ..., m_{MOD - 1}) le vecteur des comptes par classe residuelle
   modulo {MOD}. Alors

       H(m)  =  log2 C({POOL},{DRAWN})  -  {MOD} x E[ log2 C({PAR_CLASSE}, m_v) ]

   PREUVE. Le multiensemble des quartets est EQUIVALENT au vecteur m. La
   chaine H(D) = H(m) + E[ H(D | m) ] est exacte. Or CONDITIONNELLEMENT a m,
   D est uniforme sur les prod_v C({PAR_CLASSE}, m_v) tirages qui realisent ces
   comptes — chaque classe a exactement {PAR_CLASSE} membres et on en choisit m_v.
   Donc H(D | m) = log2 prod_v C({PAR_CLASSE}, m_v) = somme_v log2 C({PAR_CLASSE}, m_v),
   et la LINEARITE DE L'ESPERANCE donne E[H(D|m)] = {MOD} x E[log2 C({PAR_CLASSE},m_v)]
   par echange des classes. Aucune independance n'est invoquee — les m_v sont
   fortement dependants, et cela ne change rien. []
""")

# --- la loi marginale d'un compte de classe, en exact ---------------------
C = math.comb
TOT = C(POOL, DRAWN)
loi = [Fraction(C(PAR_CLASSE, k) * C(POOL - PAR_CLASSE, DRAWN - k), TOT)
       for k in range(PAR_CLASSE + 1)]
assert sum(loi) == 1, "la loi marginale ne somme pas a 1"

say(f"   {'m':>3} {'P(m)  exact':>34} {'P(m)':>10} {'log2 C(5,m)':>13}")
for k, p in enumerate(loi):
    say(f"   {k:>3} {str(p):>34} {float(p):>10.6f} {math.log2(C(PAR_CLASSE, k)):>13.5f}")

E_log = sum(float(p) * math.log2(C(PAR_CLASSE, k)) for k, p in enumerate(loi))
H_D = math.log2(TOT)
H_m = H_D - MOD * E_log

say(f"""
   E[ log2 C({PAR_CLASSE}, m) ]        = {E_log:.5f}
   {MOD} x E[...]                 = {MOD * E_log:.4f}   (la part NON publiee)
   H(D) = log2 C(80,20)     = {H_D:.4f}
   ------------------------------------------------
   H(multiensemble)         = {H_m:.4f} BITS PAR TIRAGE
""")


# ==========================================================================
rule("2. LA VÉRIFICATION INDÉPENDANTE, ET LA DÉCOMPOSITION DE 61,61")
# ==========================================================================

say("""   La section 1 utilise la linearite de l'esperance. On refait le calcul
   par une voie qui ne l'utilise pas : une programmation dynamique sur les
   seize classes, qui somme prod_v C(5,m_v) x somme_v log2 C(5,m_v) sur TOUS
   les vecteurs de comptes admissibles. Les deux voies doivent coincider au
   dernier chiffre.
""")

# A[s] = somme des prod C sur les assignations partielles totalisant s
# B[s] = somme des prod C x (somme des log2 C) sur les memes
A = [0] * (DRAWN + 1)
B = [0.0] * (DRAWN + 1)
A[0] = 1
for _ in range(MOD):
    nA = [0] * (DRAWN + 1)
    nB = [0.0] * (DRAWN + 1)
    for s in range(DRAWN + 1):
        if A[s] == 0 and B[s] == 0.0:
            continue
        for k in range(min(PAR_CLASSE, DRAWN - s) + 1):
            c = C(PAR_CLASSE, k)
            lg = math.log2(c)
            nA[s + k] += A[s] * c
            nB[s + k] += B[s] * c + A[s] * c * lg
    A, B = nA, nB

assert A[DRAWN] == TOT, f"la PD ne retrouve pas C(80,20) : {A[DRAWN]} vs {TOT}"
E_log_pd = B[DRAWN] / A[DRAWN]
H_m_pd = H_D - E_log_pd

say(f"   PD : somme des prod C          = {A[DRAWN]:,}   (doit valoir C(80,20) = {TOT:,})")
say(f"   PD : E[ somme_v log2 C ]       = {E_log_pd:.6f}")
say(f"   section 1 : 16 x E[log2 C]     = {MOD * E_log:.6f}")
say(f"   ecart                          = {abs(E_log_pd - MOD * E_log):.2e}")
# La PD accumule des flottants sur des entiers de l'ordre de 10^20 : la
# tolerance est celle de la double precision, pas celle du theoreme.
assert abs(E_log_pd - MOD * E_log) < 1e-6, "les deux voies divergent"
say(f"   H(multiensemble) par la PD     = {H_m_pd:.4f}   -> LES DEUX VOIES COINCIDENT")

say(f"""
   ET LA DECOMPOSITION EST EXACTE. Un tirage pese {H_D:.2f} bits. Ils se
   separent selon la factorisation 80 = 16 x 5 :

       {H_m:.2f} bits   la classe modulo 16 — F2-LINEAIRE pour un generateur
                     F2-lineaire a sortie brute, donc EXPLOITABLE
       {MOD * E_log:.2f} bits   « lequel des 5 dans la classe », c'est-a-dire la
                     part modulo 5 — non lineaire sur F2, donc muette
       ------
       {H_D:.2f} bits

   CE QUE LE DOSSIER UTILISAIT. Le §88 et le §89 n'exploitent que le bonus :
   UN numero, donc 4 bits par tirage.
""")

say(f"   {'source':>36} {'bits/tirage':>12} {'sur l archive':>16}")
say(f"   {'le bonus seul (§88, §89)':>36} {4.0:>12.2f} {4.0*70560:>16,.0f}")
say(f"   {'le multiensemble des quartets':>36} {H_m:>12.2f} {H_m*70560:>16,.0f}")
say(f"   {'rapport':>36} {H_m/4:>12.2f} {'':>16}")

say(f"""
   LE DOSSIER LAISSAIT DORMIR UN FACTEUR {H_m/4:.1f}, SUR CHACUNE DE SES
   70 560 LIGNES. Ce n'est pas une donnee qu'il faut aller filmer : elle est
   dans le fichier depuis le premier jour.""")


# ==========================================================================
rule("3. POURQUOI PERSONNE NE L'A PRISE : LE THÉORÈME DE LA PARITÉ")
# ==========================================================================

say(f"""   La tentation immediate est de chercher une FORME LINEAIRE invariante par
   permutation. Il n'y en a qu'une par position de bit : le XOR.

       P_b  =  XOR_{{i=1..20}}  bit_b(n_i - 1)

   Elle est observable sur l'archive triee. Et pour un generateur
   F2-lineaire elle vaut

       P_b  =  < e_b , (somme_{{j dans J}} L^j) x >

   ou J est l'ensemble des positions ACCEPTEES. C'est une forme lineaire de
   l'etat — DES QUE L'ON CONNAIT J.

   THEOREME (negatif). Sous l'echantillonneur par rejet, J est inconnu, et la
   forme ne porte aucune information exploitable.

   PREUVE. Notons W le nombre de mots consommes et r = W - 20 le nombre de
   rejets. La somme sur le PREFIXE COMPLET

       Q_b = XOR_{{j=1..W}} bit_b(out_j) = < e_b, (somme_{{j=1..W}} L^j) x >

   ne depend que de W — un seul entier inconnu. Or Q_b = P_b XOR R_b, ou R_b
   est le XOR des quartets des mots REJETES. Un mot rejete a, par definition,
   sa valeur mod 80 EGALE a une valeur deja acceptee : son quartet est donc
   celui d'un des vingt numeros observes. R = (R_0,R_1,R_2,R_3) est ainsi le
   XOR d'un sous-multiensemble de taille r des vingt quartets connus — mais
   LEQUEL est inconnu, et il parcourt le sous-espace qu'ils engendrent. []
""")

# Ce sous-espace, sur les vraies donnees.
arch = lab.load()
nib = (arch.nums.astype(int) - 1) % MOD          # (N, 20) quartets observes


def rang_f2(vals):
    """rang sur F2 de la famille de quartets (au plus 4)."""
    base = []
    for v in vals:
        for b in base:
            v = min(v, v ^ b)
        if v:
            base.append(v)
            base.sort(reverse=True)
    return len(base)


ECH = 3000
rangs = [rang_f2(nib[i]) for i in range(0, len(nib), max(1, len(nib) // ECH))]
plein = sum(1 for r in rangs if r == 4)
say(f"   Sur {len(rangs):,} tirages de l'archive, les vingt quartets engendrent "
    f"F2^4 dans {100*plein/len(rangs):.2f} % des cas.")
say(f"   Le bruit R n'est donc contraint par RIEN des que r >= 1.\n")

p0 = 1.0
for i in range(DRAWN):
    p0 *= (POOL - i) / POOL
esp_W = sum(POOL / (POOL - i) for i in range(DRAWN))

say(f"""   ET r VAUT RAREMENT ZERO. La probabilite qu'un tirage par rejet n'ait
   AUCUN doublon vaut prod_{{i=0..19}} (80-i)/80 = {p0:.4f}, soit {100*p0:.2f} %, et le
   nombre moyen de mots consommes vaut {esp_W:.2f} — donc {esp_W - DRAWN:.2f} rejets en moyenne.

   Les equations de parite forment donc une instance de PARITE BRUITEE
   (learning parity with noise) a taux d'erreur {(1-p0)/2:.3f} : chaque tirage donne
   une equation juste avec probabilite {p0:.4f}, fausse sinon, et RIEN NE DIT
   LAQUELLE. A cette dimension, c'est intraitable.

   VOILA POURQUOI L'INFORMATION DORT. Elle est presente — {H_m:.2f} bits par
   tirage, la section 1 le prouve — mais la seule voie LINEAIRE qui y mene
   est fermee par le rejet. Ce n'est pas une limite de calcul : c'est une
   propriete de l'echantillonneur, et il fallait la demontrer avant de
   pretendre que l'archive triee etait pauvre.""")


# ==========================================================================
rule("4. CE QUE COÛTE ET CE QUE RAPPORTE LA CONTRAINTE DE MULTIENSEMBLE")
# ==========================================================================

H_r = 3.0            # majorant genereux de l'entropie du nombre de rejets
say(f"""   La contrainte n'est pas lineaire, mais elle est EXACTEMENT VERIFIABLE :
   pour un etat candidat et un motif de pas donne, on calcule les vingt
   quartets predits et on les compare au multiensemble observe. Le test coute
   O(20) et rejette une hypothese fausse avec probabilite 1 - 2^-{H_m:.2f}.

   LE BUDGET, PAR TIRAGE :

     inconnues ajoutees   le nombre de rejets r du tirage, au plus {H_r:.0f} bits
     contraintes ajoutees le multiensemble, {H_m:.2f} bits
     ------------------------------------------------------------------
     GAIN NET             {H_m - H_r:.2f} bits par tirage
""")
say(f"   {'famille':>28} {'n bits':>8} {'tirages requis':>15} {'minutes de jeu':>15}")
for nom, n in (("xorshift32", 32), ("xorshift64", 64), ("xorshift128", 128),
               ("xoshiro256", 256), ("WELL512a", 512), ("MT19937", 19937)):
    k = n / (H_m - H_r)
    say(f"   {nom:>28} {n:>8,} {k:>15.1f} {k*5:>15,.0f}")

say(f"""
   A COMPARER AUX NEUF TIRAGES ORDONNES DU §86. Le §80 exigeait 343 tirages
   ORDONNES pour MT19937 ; le §61 en exigeait 6,4 pour WELL512a et n'en avait
   que cinq. Ici les tirages requis sont TRIES, et l'archive en contient
   70 560 — soit {70560/(19937/(H_m-H_r)):.0f} fois ce que MT19937 demande.

   CE QUI RESTE A PAYER, ET IL FAUT LE DIRE. La contrainte etant un
   multiensemble et non une equation, la resolution n'est pas une
   elimination de Gauss : c'est une RECHERCHE avec affectation. L'attaque
   naive fixe les quartets position par position ; le branchement vaut au
   plus {MOD} tant que le rang n'est pas plein, et il n'y a AUCUN elagage avant
   la saturation. Le cout est donc {MOD}^(n/4) = 2^n : pour n = 64 c'est
   exactement le cout de l'enumeration de l'etat, donc AUCUN GAIN. Ce fichier
   ne pretend pas le contraire, et une rencontre-au-milieu a 2^(n/2) n'est
   pas demontree ici.

   MAIS UNE PART DU CONTENU EST SANS AFFECTATION, ET C'EST ELLE QUI COMPTE.
   Pour chaque position de bit b, le COMPTE c_b = #{{i : bit_b(n_i - 1) = 1}}
   est observable, et c'est le poids de Hamming du vecteur des vingt formes
   < e_b, L^j x >. Le verifier ne demande AUCUNE affectation : on calcule les
   vingt formes et on compte.
""")

# Entropie des quatre comptes, en forme close : c_b ~ hypergeometrique(80,40,20)
loi_c = [Fraction(C(POOL // 2, k) * C(POOL // 2, DRAWN - k), TOT)
         for k in range(DRAWN + 1)]
assert sum(loi_c) == 1, "la loi du compte ne somme pas a 1"
H_c = -sum(float(p) * math.log2(float(p)) for p in loi_c if p)
say(f"   H(un compte c_b)  = {H_c:.4f} bits   (hypergeometrique 80, 40, 20, exacte)")
say(f"   quatre comptes    <= {4*H_c:.4f} bits par tirage, et <= {H_m:.2f} par le theoreme")
say(f"""
   Les quatre comptes valent donc a eux seuls jusqu'a {min(4*H_c, H_m):.1f} bits par tirage
   — {min(4*H_c, H_m)/4:.1f} fois le bonus — et ils se verifient en O(20) sans affectation.
   C'est la moitie utilisable du theoreme, et elle est immediate.

   LE THEOREME NE DONNE PAS L'ALGORITHME COMPLET. Il donne ce qu'aucune
   section du dossier n'avait : la certitude que l'information EST LA, sa
   mesure exacte, et la part qui se verifie sans rien chercher. Les §61 et
   §65 implementent deja la machinerie d'approfondissement iteratif — ils la
   faisaient tourner sur NEUF tirages parce qu'ils croyaient l'archive
   muette.""")


# ==========================================================================
rule("5. L'ANGLE MORT DU §89, QUE CECI OUVRE")
# ==========================================================================

say(f"""   Le §89 exclut tout generateur F2-lineaire d'etat sous 35 280 bits, par
   Berlekamp-Massey sur la suite des bonus. Sa portee a une condition que le
   §90 a verifiee pour W fixe — et une qu'il n'a pas nommee :

       BM ne voit une suite lineaire recurrente que si le PAS entre bonus
       consecutifs est CONSTANT.

   Sous FISHER-YATES, le pas vaut exactement 20 : le §89 s'applique.
   Sous REJET, le pas vaut 20 + r_t avec r_t ALEATOIRE : la suite des bonus
   est une decimation a positions irregulieres d'une suite lineaire, et une
   telle decimation N'EST PAS lineaire recurrente. LE §89 NE DIT RIEN DE
   L'ECHANTILLONNEUR PAR REJET.

   Or c'est l'implementation la plus idiomatique qui soit — le §76 l'appelle
   lui-meme « l'implementation naive par excellence » — et elle n'a jamais
   ete testee que sur NEUF tirages ordonnes (§86), faute de donnees.

   C'est exactement le trou que la section 4 remplit : {H_m:.2f} bits par tirage
   trie, sur 70 560 tirages, et le motif de pas comme seule inconnue
   supplementaire — {H_r:.0f} bits par tirage contre {H_m:.2f} de contrainte.""")


# ==========================================================================
rule("6. CE QUE CELA NE FAIT PAS")
# ==========================================================================

say(f"""   1. CELA NE RECONSTITUE AUCUN ETAT. Ce fichier mesure une capacite, il
      n'execute pas d'attaque. Aucune ligne ici ne contredit le bilan des
      §68 a §92 : zero etat compatible partout.
   2. CELA NE VAUT QUE POUR L'ECHANTILLONNEUR PAR MODULO. Sous troncature
      (§82) ou bits de poids fort (§87), le quartet du numero n'est PAS celui
      du mot, et l'identite 80 = 16 x 5 ne mord pas. Le §87 chiffre ces cas
      separement : 5,60 et 7,00 bits par mot.
   3. CELA NE VAUT QUE POUR UNE SORTIE BRUTE. Un generateur a sortie
      brouillee (PCG, xoshiro** ou ++, splitmix64) n'a pas de quartet
      lineaire, et le §91 le disait deja.
   4. LE FACTEUR {H_m/4:.1f} EST UN CONTENU, PAS UN ALGORITHME. La section 4 dit
      precisement ce qu'il reste a payer : une recherche avec affectation,
      pas une elimination.

   Registre : INCHANGE. h73 demontre et mesure, il ne teste pas.

   ({time.time() - T0:.1f} s)""")
