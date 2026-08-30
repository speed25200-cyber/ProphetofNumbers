"""h54 — la carte de couverture, et l'hypothese silencieuse qui la porte.

Pourquoi ce fichier
====================
Cinq sections (§68 a §72) ont ete ajoutees vite, chacune fermant une case. Il
faut maintenant (a) dire exactement ce qui est couvert et ce qui ne l'est pas,
sans qu'une case fermee par hypothese passe pour fermee tout court, et (b)
nommer une hypothese qui porte TOUT l'edifice et qu'aucune des cinq n'a
ecrite.

L'HYPOTHESE SILENCIEUSE
========================
Le theoreme de la fuite exige l'ORDRE DE SORTIE : il dit quel mot du
generateur a produit quel numero. Les cinq tirages ordonnes du dossier
viennent de `parseMatrix` (LoroClient.swift), qui preserve l'ordre du tableau
`main` renvoye par l'API.

    Rien n'etablit que cet ordre soit celui du GENERATEUR.

Il pourrait etre l'ordre d'AFFICHAGE d'une animation, un ordre de tri
secondaire, ou l'ordre d'insertion dans une structure. Si c'est le cas, les
§68 a §72 testent une permutation sans rapport avec la sortie du generateur,
et leurs « 0 etat compatible » ne valent rien.

Ce fichier ne peut pas trancher — il faudrait la documentation de l'operateur
ou une observation de l'animation. Il fait deux choses a la place : il ECRIT
l'hypothese, et il chiffre ce qu'un ordre FAUX couterait, ce qui donne la
puissance reelle des cinq sections.

Il ne teste pas l'archive : il cartographie. Registre : inchange.
"""

import csv
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

T0 = time.time()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POOL, DRAWN = 80, 20


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


REJ_BITS = DRAWN * v2(POOL)
FY_BITS = sum(v2(POOL - i) for i in range(DRAWN))


# ==========================================================================
rule("1. L'HYPOTHÈSE QUI PORTE LES §68 À §72")
# ==========================================================================

rows = list(csv.DictReader(open(os.path.join(ROOT, "draws_ordered.csv"))))
ORD = {int(r["id"]): [int(r[f"o{i}"]) for i in range(1, DRAWN + 1)] for r in rows}
ids = sorted(ORD)
sorted_count = sum(1 for i in ids if ORD[i] == sorted(ORD[i]))

say(f"""   Le theoreme exige l'ORDRE DE SORTIE — quel mot du generateur a produit
   quel numero. Les cinq tirages ordonnes viennent de `parseMatrix`, qui
   preserve l'ordre du tableau `main` de l'API.

   RIEN N'ETABLIT QUE CET ORDRE SOIT CELUI DU GENERATEUR.

   Ce qu'on peut verifier ici, et c'est peu :
     tirages ordonnes disponibles        {len(ids)}
     dont l'ordre est deja trie          {sorted_count}   (0 attendu si l'ordre est reel)
     sources                             {sorted(set(r['source'] for r in rows))}

   Un ordre trie aurait signale un artefact ; il n'y en a pas. Cela exclut le
   cas le plus grossier, et RIEN DE PLUS. L'ordre pourrait rester celui d'une
   animation d'affichage, d'un tri secondaire, ou d'une insertion — toutes
   des permutations non triviales et sans rapport avec le generateur.""")


# ==========================================================================
rule("2. CE QU'UN ORDRE FAUX COÛTERAIT — la puissance réelle")
# ==========================================================================

say(f"""   Supposons l'ordre enregistre faux : une permutation inconnue de l'ordre
   vrai. Les equations du §68 associent alors le mauvais mot a chaque numero,
   et le systeme devient incoherent — l'attaque ne trouve rien, exactement
   comme si le generateur n'etait pas de la famille.

   Un « 0 etat compatible » a donc DEUX lectures, et le dossier doit le dire :

     (a) le generateur n'appartient a aucune famille testee ;
     (b) l'ordre enregistre n'est pas celui du generateur.

   Ces deux lectures sont INDISCERNABLES par les §68 a §72. Ce que les cinq
   sections etablissent est donc exactement :

     « SI l'ordre enregistre est celui du generateur, ALORS aucune des
       familles testees ne produit ces tirages, pour aucune graine. »

   Et rien de plus fort. Ce qui LEVERAIT l'ambiguite, par ordre de cout :

     1. Un temoin d'ordre : faire tirer l'operateur et comparer a l'animation.
        Cout nul, une observation.
     2. La documentation technique du systeme de tirage.
     3. Un tirage dont l'ordre serait retrouve par une AUTRE voie — par
        exemple si l'attaque trouvait un etat compatible, ce qui validerait
        l'ordre retrospectivement. C'est la seule voie interne, et elle n'a
        pas abouti.""")


# ==========================================================================
rule("3. LA CARTE DE COUVERTURE")
# ==========================================================================

say(f"""   Chaque case est (famille x echantillonneur), avec ce qui la ferme et a
   quelle condition. « toute graine » signifie que l'espace de graines n'est
   pas enumere mais RESOLU.
""")

CASES = [
    ("LCG mod 2^48 (java.util.Random)", "rejet / FY modulaire",
     "§34", "2-adique, 2^48 COMPLETS, toute graine"),
    ("LCG a constantes connues", "multiply-shift",
     "§24", "reseau LLL + Babai, 9/9 temoins"),
    ("LCG a constantes INCONNUES", "ordonne",
     "§25", "theoreme des deux etats, (a,c) calcules"),
    ("12 familles (LCG, xorshift, pcg, splitmix)", "4 echantillonneurs",
     "§34", "graines [0, 2^32) enumerees"),
    ("8 familles", "4 echantillonneurs",
     "§63", "graine = horloge ou compteur, par tirage"),
    ("8 familles", "4 echantillonneurs",
     "§65", "amorcage unique + course continue"),
    ("F2-lineaires <= 128 bits", "rejet modulo 80",
     "§68", "RESOLU, toute graine, couverture 46-99 %"),
    ("F2-lineaires <= 128 bits", "Fisher-Yates modulaire",
     "§71", "RESOLU, toute graine, couverture 100 %"),
    ("F2-lineaires <= 110 bits", "FY, tirages NON voisins",
     "§72", "RESOLU, trous traverses gratuitement"),
]
say(f"   {'famille':<38} {'échantillonneur':<24} {'§':<5} condition")
for fam, samp, sec, cond in CASES:
    say(f"   {fam:<38} {samp:<24} {sec:<5} {cond}")

say(f"""
   CE QUI RESTE, ET POURQUOI AUCUNE COLLECTE N'Y CHANGERA RIEN :""")
OPEN = [
    ("PCG (XSH-RR, XSL-RR)", "l'etat avance par LCG mod 2^64 : la TRANSITION "
     "n'est pas F2-lineaire, les equations ne se chainent pas"),
    ("xoshiro ** et ++", "le brouillage de sortie est multiplicatif ou additif"),
    ("splitmix64", "mixeur non lineaire a deux multiplications"),
    ("MT19937", "F2-lineaire, mais 19 937 bits : 250 tirages sous rejet, "
     "907 sous FY — et une session n'en compte que 204 (§69)"),
    ("tout CSPRNG (AES-CTR, ChaCha, HMAC-DRBG)", "casser la famille = casser "
     "la primitive ; il n'y a pas de graine a chercher"),
    ("materiel (TRNG)", "aucun etat, donc rien a resoudre"),
]
for nom, why in OPEN:
    say(f"     {nom:<42} {why}")


# ==========================================================================
rule("4. LE BUDGET, EN UNE FORMULE")
# ==========================================================================

say(f"""   Tout le volet « fuite » tient en une ligne. Pour N tirages ordonnes,
   pas necessairement voisins, d'un generateur F2-lineaire :

       bits disponibles = N x somme des v2(module au pas i)

   soit {REJ_BITS} bits par tirage sous rejet modulo {POOL}, {FY_BITS} sous Fisher-Yates.
   Une famille d'etat B est resoluble des que N x bits >= B.
""")
say(f"   {'N tirages':>10} {'rejet mod 80':>14} {'Fisher-Yates':>14}   ce que N ouvre (FY)")
for n in (1, 2, 5, 10, 20, 50, 204, 907):
    r, f = n * REJ_BITS, n * FY_BITS
    what = ("xorshift32" if f >= 32 else "—")
    for b, nm in ((64, "xorshift64"), (96, "xorshift96"), (128, "xorshift128"),
                  (256, "état 256 bits"), (19937, "MT19937")):
        if f >= b:
            what = nm
    say(f"   {n:>10} {r:>14,} {f:>14,}   {what}")

say(f"""
   Le dossier est a N = {len(ids)} ({len(ids) * FY_BITS} bits sous FY). MT19937 demanderait
   N = {-(-19937 // FY_BITS)} sous Fisher-Yates ou N = {-(-19937 // REJ_BITS)} sous rejet — et sous rejet les
   trous coutent une enumeration, donc il les faudrait VOISINS, ce qu'une
   session de 204 tirages ne permet pas.""")


# ==========================================================================
rule("5. CE QUE CE FICHIER ÉTABLIT")
# ==========================================================================

say(f"""   1. L'edifice §68-§72 repose sur une hypothese qu'aucune de ses sections
      n'ecrivait : que l'ordre enregistre soit celui du generateur. Elle est
      desormais ecrite, et sa falsification est nommee (un temoin d'ordre,
      cout nul).

   2. Un « 0 etat compatible » a deux lectures indiscernables — mauvaise
      famille, ou mauvais ordre. Les cinq sections etablissent une
      IMPLICATION, pas un fait : si l'ordre est le bon, alors aucune famille
      testee ne convient.

   3. La couverture se resume a une formule, N x bits par tirage, et la carte
      dit ce qui est ferme par RESOLUTION (toute graine) et ce qui l'est par
      ENUMERATION (graines bornees).

   4. Ce qui reste ouvert ne l'est pas faute de donnees mais faute de
      STRUCTURE : PCG, xoshiro brouille, splitmix64 et les CSPRNG n'ont pas
      la linearite que le theoreme exige, et aucune collecte ne la leur
      donnera.

   Registre : inchange. h54 ne teste pas l'archive — il cartographie.

   ({time.time() - T0:.2f} s)""")
