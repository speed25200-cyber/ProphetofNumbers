"""h72 — le theoreme du convertisseur : ce qu'une fuite doit valoir, en francs.

LE TROU QUE CE FICHIER BOUCHE
==============================
Le dossier a deux moities qui ne se parlent pas.

    A GAUCHE   les §68 a §92. Ils reconstituent — ou echouent a reconstituer —
               l'etat du generateur. Leur sortie naturelle est une loi a
               posteriori sur le PROCHAIN TIRAGE ENTIER : une liste de
               tirages candidats, avec des poids.

    A DROITE   le §78 et toute l'application. Ils choisissent une grille a
               partir de MARGINALES : une probabilite par numero.

Personne n'a jamais demontre que la droite sait recevoir ce que la gauche
produit. Ce fichier montre qu'elle ne sait PAS, et donne le convertisseur
correct.

TROIS THEOREMES
================
1. LINEARISATION. Le gain espere est une combinaison lineaire EXACTE des
   probabilites d'inclusion pi(S) = P(S inclus dans le tirage), ponderee par
   les differences finies du bareme :

       E[g(h)] = somme_j  D^j g(0) * somme_{S inclus dans G, |S| = j}  pi(S)

   Ce n'est pas une approximation : c'est une identite, valable pour toute
   loi, sans aucune hypothese d'independance.

2. LE BAREME REEL IGNORE LES MARGINALES. Pour les mises 5, 6 et 7, les
   coefficients D^1 g(0) et D^2 g(0) sont NULS ; pour la mise 8, les trois
   premiers le sont. Le gain espere ne depend donc que des inclusions
   d'ordre >= 3 (>= 4 a la mise 8). Une prediction qui ne publie que des
   marginales ne fournit pas les arguments que la fonction prend.

3. DOMINATION. Deux grilles de MEMES marginales peuvent avoir des gains
   esperes dans un rapport de 60. La marginale ne classe donc pas les
   grilles — pas meme approximativement.

ET LE CONVERTISSEUR CORRECT
============================
Si la reconstitution laisse une loi a posteriori de MIN-ENTROPIE H (en bits)
sur le prochain tirage, jouer les k numeros du candidat le plus lourd
rapporte au moins g_k(k) * 2^-H. Le pari est donc favorable des que

    H  <  log2( g_k(k) / mise )

et ce seuil se lit dans le bareme. Le tirage complet en pese log2 C(80,20) =
61,6 : le theoreme dit exactement combien de bits il faut RETIRER.

Il ne teste rien sur l'archive : il ne consigne RIEN. C'est de l'arithmetique
et de l'algebre, pas de la statistique.
"""

import csv
import math
import os
import sys
import time
from fractions import Fraction
from itertools import combinations

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

T0 = time.time()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POOL, DRAWN = 80, 20
BAREME = os.path.join(ROOT, "bareme_observed.csv")
JACKPOTS = os.path.join(ROOT, "jackpots_observed.csv")


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def charger_bareme():
    """{k: [g(0), g(1), ..., g(k)]} depuis le releve d'ecran."""
    par_k = {}
    with open(BAREME) as fh:
        for r in csv.DictReader(l for l in fh if not l.startswith("#")):
            k, h = int(r["mise"]), int(r["hits"])
            par_k.setdefault(k, {})[h] = int(r["gain_base"])
    return {k: [v[h] for h in range(k + 1)] for k, v in sorted(par_k.items())}


def differences(g):
    """D^j g(0) pour j = 0..k, par la formule des differences finies."""
    return [sum((-1) ** (j - i) * math.comb(j, i) * g[i] for i in range(j + 1))
            for j in range(len(g))]


def reconstruire(c, h):
    """somme_j c_j C(h, j) — le barème rebâti depuis ses différences."""
    return sum(c[j] * math.comb(h, j) for j in range(len(c)))


BAR = charger_bareme()


# ==========================================================================
rule("1. LE THÉORÈME DE LINÉARISATION")
# ==========================================================================

say("""   THEOREME. Soit D le tirage (un 20-sous-ensemble aleatoire de [80]), G une
   grille de k numeros, h = |G inter D| le nombre de coincidences, et g le
   bareme. Posons pi(S) = P(S inclus dans D). Alors

       E[g(h)]  =  somme_{j=0}^{k}  D^j g(0)  *  somme_{S inclus dans G, |S|=j}  pi(S)

   ou D^j g(0) est la j-ieme difference finie de g en 0.

   PREUVE. Tout g sur {0..k} s'ecrit de facon unique dans la base de Newton
   g(h) = somme_j D^j g(0) C(h, j) — c'est l'interpolation de Newton, exacte
   sur k+1 points. Or C(h, j) COMPTE les j-sous-ensembles de G contenus dans
   D, donc

       C(h, j) = somme_{S inclus dans G, |S| = j}  1[S inclus dans D].

   L'esperance de l'indicatrice est pi(S) ; la somme finie s'echange avec
   l'esperance. []

   CE QUE CETTE IDENTITE VAUT. Elle est EXACTE — aucune independance, aucune
   approximation, aucune hypothese sur la loi. Elle dit que le gain espere
   n'est pas une fonction quelconque de la loi : c'est une FORME LINEAIRE
   sur les probabilites d'inclusion, et les coefficients sont lisibles dans
   le bareme.
""")


# ==========================================================================
rule("2. LE BARÈME RÉEL, DÉCOMPOSÉ")
# ==========================================================================

say("""   On decompose le bareme releve le 2026-08-30 (BOOST x1, gain de base).
   La ligne « ordre j » porte D^j g(0), le poids de TOUTES les inclusions de
   taille j.
""")

premiers = {}
for k, g in BAR.items():
    c = differences(g)
    assert all(reconstruire(c, h) == g[h] for h in range(k + 1)), \
        f"la reconstruction echoue a la mise {k}"
    nz = [j for j, x in enumerate(c) if x != 0]
    premiers[k] = min(nz) if nz else None
    say(f"   mise {k:>2}   gains {g}")
    say(f"            " + "  ".join(f"j={j}:{c[j]:+,}" for j in range(len(c))))
    say(f"            premier ordre non nul : {premiers[k]}\n")

say(f"""   LECTURE, ET C'EST LE POINT DU FICHIER.

     mise  5, 6, 7   les coefficients d'ordre 0, 1 et 2 sont NULS
     mise  8         les ordres 0, 1, 2 et 3 sont NULS
     mise 10         tous non nuls, a cause du lot de consolation g(0) = 2

   Pour les mises 5 a 8, LE GAIN ESPERE NE DEPEND PAS DES MARGINALES. Il ne
   depend que des inclusions d'ordre 3 ou plus. Ce n'est pas « les marginales
   comptent peu » : elles n'apparaissent PAS dans la formule.

   CONSEQUENCE IMMEDIATE. Un predicteur qui publie une probabilite par
   numero — chauds, froids, retards, essaim, reseau de neurones — ne fournit
   pas les arguments que E[g] prend. Il ne s'agit pas d'un predicteur faible :
   il s'agit d'un predicteur dont la sortie n'est pas du type attendu.

   CE QUI SAUVE LE §78. Le §78 travaille sur des CLASSES RESIDUELLES, et sa
   loi a posteriori est echangeable a l'interieur de chaque classe. Sous
   echangeabilite, pi(S) ne depend que du profil de S par classe, et le tri
   par comptes decroissants redevient optimal. Le §78 est donc un CAS
   PARTICULIER correct, et la section 3 montre que la regle generale, elle,
   est fausse.""")


# ==========================================================================
rule("3. LE THÉORÈME DE DOMINATION")
# ==========================================================================

say("""   THEOREME. Il existe une loi a posteriori et deux grilles de MEMES
   marginales dont les gains esperes sont dans un rapport superieur a 50.

   PREUVE PAR CONSTRUCTION. Soit D uniforme sur DEUX tirages seulement :

       D1 = {1, ..., 20}        avec probabilite 1/2
       D2 = {21, ..., 40}       avec probabilite 1/2

   Les marginales valent 1/2 pour tout numero de 1 a 40, et 0 au-dela.
   Prenons la mise 5 et deux grilles :

       G1 = {1, 2, 3, 4, 5}          entierement dans D1
       G2 = {1, 2, 3, 21, 22}        a cheval

   Elles ont la MEME somme de marginales : 5 x 1/2 = 2,5. []
""")

D1, D2 = set(range(1, 21)), set(range(21, 41))
LOI = [(Fraction(1, 2), D1), (Fraction(1, 2), D2)]
G1, G2 = {1, 2, 3, 4, 5}, {1, 2, 3, 21, 22}
g5 = BAR[5]


def esperance(G, loi, g):
    return sum(w * g[len(G & D)] for w, D in loi)


for nom, G in (("G1 = {1,2,3,4,5}", G1), ("G2 = {1,2,3,21,22}", G2)):
    marg = sum(sum(w for w, D in LOI if x in D) for x in G)
    e = esperance(G, LOI, g5)
    detail = " + ".join(f"1/2 x g({len(G & D)}) = {Fraction(1,2)*g5[len(G & D)]}"
                        for _, D in LOI)
    say(f"   {nom:>22}   somme des marginales {marg}   E[gain] = {detail} = CHF {float(e):g}")

r = esperance(G1, LOI, g5) / esperance(G2, LOI, g5)
say(f"""
   RAPPORT : {float(r):.0f}.

   Les deux grilles sont indiscernables pour un modele marginal, et l'une
   rapporte {float(r):.0f} fois l'autre. LA MARGINALE NE CLASSE PAS LES GRILLES — pas
   meme approximativement, pas meme a un facteur pres.

   ET CE N'EST PAS UN CONTRE-EXEMPLE ARTIFICIEL. Une loi a posteriori issue
   d'une reconstitution d'etat est EXACTEMENT de cette forme : quelques
   tirages candidats entiers, avec des poids. Elle ne ressemble jamais a un
   nuage de numeros independants legerement penches. Le convertisseur de
   l'application est donc concu pour une entree que la moitie gauche du
   dossier ne produit pas.""")

# Verification sous H0 : l'invariance doit se relire dans l'identite.
say(f"""
   CONTROLE DE COHERENCE. Sous H0 — D uniforme sur les 20-sous-ensembles —
   pi(S) ne depend que de |S| : pi(S) = C(80-|S|, 20-|S|) / C(80, 20). Le
   theoreme de linearisation donne alors le meme E[g] pour TOUTES les
   grilles de meme taille : c'est le theoreme d'invariance du §1, retrouve
   comme corollaire.
""")
say(f"   {'mise':>5} {'E[gain] sous H0':>18} {'espérance hypergéométrique':>28}")
for k, g in BAR.items():
    c = differences(g)
    par_lin = sum(c[j] * math.comb(k, j) * Fraction(math.comb(POOL - j, DRAWN - j),
                                                    math.comb(POOL, DRAWN))
                  for j in range(k + 1))
    direct = sum(Fraction(math.comb(k, h) * math.comb(POOL - k, DRAWN - h),
                          math.comb(POOL, DRAWN)) * g[h] for h in range(k + 1))
    assert par_lin == direct, f"incoherence a la mise {k}"
    say(f"   {k:>5} {float(par_lin):>18.4f} {float(direct):>28.4f}")


# ==========================================================================
rule("4. LE CONVERTISSEUR CORRECT : LE THÉORÈME DE LA MIN-ENTROPIE")
# ==========================================================================

say("""   Ce que produit une reconstitution partielle, c'est un ENSEMBLE de
   tirages candidats avec des poids : P = somme_m w_m delta_{D_m}. Posons

       H  =  - log2 ( max_m w_m )        la MIN-ENTROPIE du prochain tirage.

   THEOREME. Soit m* l'indice du candidat le plus lourd et G n'importe
   quelle grille de k numeros incluse dans D_{m*}. Alors

       E[g(h)]  >=  w_{m*} * g_k(k)  =  g_k(k) * 2^-H

   et le pari a la mise k est favorable des que

       H  <  log2 ( g_k(k) / prix du ticket ).

   PREUVE. E[g(h)] = somme_m w_m g(|G inter D_m|) >= w_{m*} g(k), tous les
   termes etant positifs ou nuls et le terme m* valant exactement g(k)
   puisque G est inclus dans D_{m*}. []

   DEUX REMARQUES QUI COMPTENT.

   1. C'EST UNE CONDITION SUFFISANTE, PAS NECESSAIRE. On jette tous les rangs
      intermediaires et tous les autres candidats. Le vrai seuil est donc
      PLUS BAS que celui annonce — l'inegalite ne peut que s'ameliorer, jamais
      se degrader. C'est le meme argument que le §29 sur le jackpot.

   2. LA GRILLE OPTIMALE, ELLE, est la solution de max_G somme_m w_m
      g(|G inter D_m|) : une couverture ponderee sur M candidats. Elle est
      calculable exactement des que M est enumerable — et M enumerable est
      PRECISEMENT le regime que le theoreme vise.
""")

C8020 = math.comb(POOL, DRAWN)
H_TIRAGE = math.log2(C8020)
say(f"   Un tirage complet pese log2 C(80,20) = log2 {C8020:.4g} = {H_TIRAGE:.2f} bits.\n")

jack = {}
with open(JACKPOTS) as fh:
    for r in csv.DictReader(l for l in fh if not l.startswith("#")):
        for k in BAR:
            v = r.get(f"j{k}")
            if v:
                jack[k] = int(v)               # le dernier releve l'emporte

say(f"   {'mise':>5} {'gain k/k':>10} {'H max @ CHF 1':>14} {'@ CHF 2':>9} "
    f"{'bits à retirer (CHF 2)':>24}")
for k, g in BAR.items():
    top = g[k]
    h1 = math.log2(top / 1.0)
    h2 = math.log2(top / 2.0)
    say(f"   {k:>5} {top:>10,} {h1:>14.2f} {h2:>9.2f} {H_TIRAGE - h2:>24.2f}")

say(f"""
   ET AVEC LA CAGNOTTE BANGO (releve du 2026-08-30, `jackpots_observed.csv`).
   On la suppose S'AJOUTER au rang plein fixe. Si elle le REMPLACE, le seuil
   baisse de moins de 0,3 bit a la mise 10 — le tableau ne change pas de
   nature.
""")
say(f"   {'mise':>5} {'cagnotte':>12} {'H max @ CHF 2':>14} {'bits à retirer':>16}")
meilleur = None
for k in sorted(jack):
    tot = BAR[k][k] + jack[k]
    h2 = math.log2(tot / 2.0)
    if meilleur is None or h2 > meilleur[1]:
        meilleur = (k, h2)
    say(f"   {k:>5} {jack[k]:>12,} {h2:>14.2f} {H_TIRAGE - h2:>16.2f}")

say(f"""
   LE CHIFFRE QUE LE DOSSIER CHERCHAIT DEPUIS LE §68.

     Le prochain tirage pese {H_TIRAGE:.1f} bits.
     Il faut le ramener sous {meilleur[1]:.1f} bits (mise {meilleur[0]}, cagnotte comprise,
     ticket a CHF 2).
     Il faut donc RETIRER {H_TIRAGE - meilleur[1]:.1f} BITS — et pas un de plus.

   Ce n'est pas « casser le generateur ». C'est reduire le prochain tirage a
   au plus 2^{meilleur[1]:.0f} candidats enumerables. La difference est enorme en
   pratique et personne, dans ce dossier, ne l'avait ecrite.""")


# ==========================================================================
rule("5. CE QUE CELA CHANGE POUR LES §80, §88 ET §92")
# ==========================================================================

MT = 19937
say(f"""   POUR UNE ATTAQUE LINEAIRE. Si le systeme lineaire laisse un espace de
   solutions de dimension d sur F2, le prochain tirage a au plus 2^d
   candidats, donc H <= d. La condition suffisante devient une condition sur
   le RANG :

       rang  >=  n - {meilleur[1]:.0f}          au lieu de     rang = n.

   Pour MT19937 (n = {MT:,}), cela demande un rang de {MT - int(meilleur[1]):,} au lieu de
   {MT:,}. L'economie est de {int(meilleur[1])} equations : elle est REELLE mais petite, et il
   faut le dire — le §80 montre que le rang sature brutalement, donc les
   derniers bits ne coutent presque rien a obtenir.

   LA VRAIE PORTEE EST AILLEURS : le critere d'arret cesse d'etre binaire.
   Le §88 s'arretait a « rang plein ou rien ». Il peut desormais s'arreter a
   « 2^{meilleur[1]:.0f} candidats », les enumerer, et JOUER — sans jamais identifier
   l'etat. C'est un critere d'arret operationnel, pas algebrique.

   ET H PEUT ETRE PLUS PETIT QUE d. Deux etats distincts peuvent produire le
   MEME tirage : les collisions ne coutent rien, elles rapportent. La borne
   H <= d est donc lache dans le bon sens.

   POUR LE §92. L'angle de la roue, s'il est tire, publie les bits de poids
   fort. La table du §92 donne 10,9 bits par tirage filme contre 1,9 pour le
   boost seul. Ce fichier dit a quoi ces bits servent : a descendre de {H_TIRAGE:.1f}
   sous {meilleur[1]:.1f}.""")


# ==========================================================================
rule("6. CE QUE CELA NE FAIT PAS")
# ==========================================================================

say(f"""   1. CELA NE PRODUIT AUCUNE FUITE. Le theoreme dit ce qu'une fuite doit
      valoir, pas qu'il en existe une. Les §68 a §92 n'en ont trouve aucune,
      et ce fichier ne change rien a ce bilan.
   2. CELA NE TESTE RIEN. Aucune statistique n'est calculee sur l'archive,
      donc RIEN N'EST CONSIGNE. Le registre est inchange, et c'est la seule
      facon honnete de traiter un resultat qui est un theoreme.
   3. LE BAREME EST UN RELEVE D'ECRAN, a BOOST x1, du 2026-08-30. Les
      coefficients de la section 2 en dependent. Le fait structurel — les
      ordres bas sont nuls — tient tant que le bareme ne paie rien en dessous
      de trois coincidences, ce qui est le cas sur tout le releve.
   4. LA GRILLE OPTIMALE EXACTE est une couverture ponderee, donc un probleme
      combinatoire. Le theoreme n'en donne qu'une MINORATION — celle qui
      suffit a decider de jouer.

   Registre : INCHANGE. h72 demontre, il ne teste pas.

   ({time.time() - T0:.1f} s)""")
