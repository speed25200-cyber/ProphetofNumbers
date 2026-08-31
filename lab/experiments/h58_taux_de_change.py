"""h58 — le taux de change : ce qu'un bit du generateur vaut en numeros.

Le trou que ce fichier comble
==============================
Le dossier tient deux theoremes qui ne se parlent pas.

  Le theoreme d'INVARIANCE (cote table) dit que sous echangeabilite
  E[touches] = k/4, quelle que soit la grille jouee. C'est une identite : elle
  ne tombe que si l'echangeabilite tombe.

  Le theoreme de la FUITE (§68, cote generateur) dit que 80 = 16 x 5 entraine
  out == n - 1 (mod 16) : chaque numero publie QUATRE bits du mot de sortie.

Entre les deux, rien. Aucune section du dossier ne dit combien de touches
achete un bit de fuite. On sait attaquer le generateur et on sait borner la
table, mais on ignore le TAUX DE CHANGE entre les deux — donc on ignore
QUELLE PARTIE du generateur il faut reproduire pour que le pari bascule.

Ce fichier etablit ce taux, exactement.

LE THEOREME DE CONVERSION
==========================
Soit un generateur qui publie b bits de chaque mot, et l'echantillonnage par
rejet modulo 80. Les 80 numeros se partagent alors en M = 2^b classes de
s = 80/M membres, la classe de n etant (n-1) mod M.

Supposons connus les residus des r PREMIERS numeros tires (r <= 20), soit les
comptes m_c par classe. Alors, pour x membre de la classe c :

    P(x tire | m) = [ m_c + (s - m_c)(20 - r)/(80 - r) ] / s          (*)

PREUVE. Conditionnellement aux comptes, l'identite des r premiers est
uniforme dans chaque classe, donc P(x parmi les r premiers) = m_c/s. Sinon x
reste dans le vivier de 80 - r numeros dont 20 - r seront tires, d'ou
P(x parmi les suivants) = (1 - m_c/s)(20 - r)/(80 - r). Somme. []

TROIS LECTURES DE (*), ET LA TROISIEME EST LE RESULTAT.

  1. r = 0 rend P = 1/4 pour tout x : le theoreme d'invariance est un CAS
     PARTICULIER du theoreme de conversion, celui ou l'on ne sait rien.

  2. La somme de (*) sur les 80 numeros vaut EXACTEMENT 20, pour tout m et
     tout r. Le theoreme d'invariance n'est donc pas viole : il est
     CONTOURNE. La masse totale reste 20 ; c'est sa REPARTITION qui cesse
     d'etre uniforme, et jouer les k plus grandes en recolte plus que k/4.

  3. P est croissante en m_c, donc la grille optimale se lit sans recherche :
     trier les classes par m_c decroissant et les remplir dans l'ordre. Le
     probleme de decision est resolu en fermeture, pas par optimisation.

LA LOI COMPLETE, PAS SEULEMENT L'ESPERANCE
===========================================
(*) donne l'esperance ; le bareme, lui, paie des RANGS. Il faut donc la loi
entiere du nombre de touches, et un Monte-Carlo ne la donne pas : le rang
plein a k = 8 vaut CHF 10 000 pour une probabilite de l'ordre de 10^-5, et
aucun echantillon raisonnable ne le mesure. Une premiere version de ce
fichier a produit des taux de retour faux pour cette raison exacte.

La section 2 calcule donc la loi EXACTEMENT, par une decomposition en trois
etages : partitions des comptes observes, hypergeometrique multivariee des
numeros restants, hypergeometrique simple pour la classe entamee. Aucun
tirage aleatoire n'intervient dans les sections 3 a 5.

LE RESULTAT, EN UNE LIGNE
==========================
TROIS BITS SUFFISENT. Connaitre les trois bits de poids faible du SEUL mot
qui produira le premier numero du prochain tirage, et jouer les dix numeros
de sa classe residuelle, porte le taux de retour de 0,583 a 1,309 — hors
cagnotte. Quatre bits le portent a 1,765 en ne jouant que cinq numeros.

Pour comparaison : connaitre UN bit des vingt numeros — vingt fois plus
d'observations — ne franchit pas le seuil (0,964). Ce n'est pas le volume
d'information qui decide, c'est la valuation 2-adique du vivier.

Le dossier cherchait a resoudre 19 937 inconnues (§77). Il en faut trois. Et
predire trois formes lineaires n'est pas une condition de RANG mais une
condition d'APPARTENANCE : le mur du §77 et celui-ci n'ont ni la meme
hauteur ni la meme nature.

Ce fichier ne teste pas l'archive : il DERIVE, verifie sa derivation par
simulation independante, puis chiffre. Registre : inchange.
"""

import csv
import os
import sys
import time
from functools import lru_cache
from math import comb

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

T0 = time.time()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POOL, DRAWN = 80, 20
DRY = os.environ.get("H58_DRY") == "1"
NMC = 40_000 if DRY else 400_000
RNG = np.random.default_rng(20260931)
PRICE = 2.0                       # CHF, etabli au §63 (reglement officiel)


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def load_bareme():
    tab = {}
    with open(os.path.join(ROOT, "bareme_observed.csv")) as f:
        for row in csv.DictReader(l for l in f if not l.startswith("#")):
            tab.setdefault(int(row["mise"]), {})[int(row["hits"])] = \
                float(row["gain_base"])
    return tab


BAREME = load_bareme()
STAKES = sorted(BAREME)


def pay(k, h):
    return BAREME[k].get(h, 0.0)


# ==========================================================================
rule("1. LE PONT QUI MANQUAIT")
# ==========================================================================

say(f"""   Le dossier sait deux choses et ne les relie pas :

     invariance  E[touches] = k/4     — identite, cote table
     fuite       out == n-1 (mod 16)  — egalite, cote generateur

   La question que personne n'a posee : COMBIEN DE TOUCHES ACHETE UN BIT ?

   Sans reponse, « franchir le mur » n'a pas de sens quantitatif — on ne sait
   pas si reproduire un quart du generateur suffit, ni si le reproduire
   entierement est necessaire. Le theoreme de conversion repond, et sa
   reponse est une formule fermee : voir l'en-tete, equation (*).

   Deux regimes le rendent concret, et le dossier les possede tous les deux.

     REGIME A — etat resolu. §68 : un generateur F2-lineaire cede son etat
     par elimination de Gauss des qu'on a l'ordre. On predit alors TOUT :
     b = 4 et r = 20. La section 6 le fait pour de vrai.

     REGIME B — bits de poids faible seuls. §76 : un LCG modulo 2^k a ses
     bits bas FERMES — la suite des nibbles est un LCG modulo 16, de periode
     16, determinee par trois observations, MEME SI l'etat complet reste
     hors d'atteinte. On connait alors les residus sans connaitre l'etat.

   C'est le regime B qui donne son sens aux valeurs intermediaires de b, et
   c'est lui que ce fichier chiffre.""")


# ==========================================================================
rule("2. LA LOI EXACTE DU NOMBRE DE TOUCHES")
# ==========================================================================

def parts_iter(total, nparts, maxpart):
    """Suites NON CROISSANTES de longueur <= nparts, termes <= maxpart, de
    somme `total`. C'est l'ensemble des vecteurs de comptes A PERMUTATION
    PRES : les classes etant echangeables, tout ce qui suit ne depend que de
    la suite triee."""
    if total == 0:
        yield ()
        return
    if nparts == 0:
        return
    for v in range(min(maxpart, total), 0, -1):
        if v * nparts < total:
            break
        for rest in parts_iter(total - v, nparts - 1, v):
            yield (v,) + rest


def sorted_counts_law(r, M, s):
    """Loi EXACTE du vecteur trie des comptes des r premiers numeros.

    Les comptes suivent une hypergeometrique multivariee de parametres
    ([s] * M, r), dont la probabilite d'un vecteur DONNE vaut le produit des
    C(s, m_c) divise par C(M*s, r). Le nombre de vecteurs realisant une suite
    triee donnee est le coefficient multinomial des multiplicites."""
    denom = comb(M * s, r)
    out = []
    for p in parts_iter(r, M, s):
        vec = p + (0,) * (M - len(p))
        mult = 1
        rest_slots = M
        for v in sorted(set(vec)):
            c = vec.count(v)
            mult *= comb(rest_slots, c)
            rest_slots -= c
        w = mult
        for v in vec:
            w *= comb(s, v)
        out.append((vec, w / denom))
    return out


@lru_cache(maxsize=None)
def hits_law(mtop, r, k, M, s):
    """Loi EXACTE du nombre de touches, sachant les comptes des SEULES
    classes jouees.

    Trois etages, tous exacts.

      1. La grille prend nfull classes entieres puis `rem` membres de la
         suivante (lecture 3 de (*)). Seules ces nfull+1 classes comptent.
      2. Les 20-r numeros encore a tirer se repartissent entre ces classes et
         « le reste » selon une hypergeometrique multivariee — dont la
         marginale sur un sous-ensemble de classes est encore une
         hypergeometrique multivariee, le complement etant agrege.
      3. Dans la classe ENTAMEE, les membres tires sont, conditionnellement a
         leur nombre, un sous-ensemble uniforme : la part qui tombe dans les
         `rem` membres joues suit une hypergeometrique simple.
    """
    nfull, rem = divmod(k, s)
    t = nfull + (1 if rem else 0)
    mm = list(mtop[:t])
    sizes = [s - x for x in mm]
    rest = (POOL - r) - sum(sizes)
    ndr = DRAWN - r
    denom = comb(POOL - r, ndr)
    law = {}

    def rec(i, used, w, full):
        if i == t:
            left = ndr - used
            if left < 0 or left > rest:
                return
            p = w * comb(rest, left) / denom
            if p == 0.0:
                return
            base = sum(full[:nfull])
            if rem:
                ml = full[nfull]
                dh = comb(s, rem)
                for h in range(max(0, rem - (s - ml)), min(rem, ml) + 1):
                    q = comb(ml, h) * comb(s - ml, rem - h) / dh
                    law[base + h] = law.get(base + h, 0.0) + p * q
            else:
                law[base] = law.get(base, 0.0) + p
            return
        for e in range(min(sizes[i], ndr - used) + 1):
            rec(i + 1, used + e, w * comb(sizes[i], e), full + [mm[i] + e])

    rec(0, 0, 1, [])
    return law


def exact(r, k, b):
    """(E[touches], TRR) exacts pour b bits par mot et r residus connus."""
    M, s = 1 << b, POOL >> b
    nfull, rem = divmod(k, s)
    t = nfull + (1 if rem else 0)
    agg = {}
    for vec, p in sorted_counts_law(r, M, s):
        agg[vec[:t]] = agg.get(vec[:t], 0.0) + p
    eh = eg = tot = 0.0
    for top, p in agg.items():
        for h, q in hits_law(top, r, k, M, s).items():
            eh += p * q * h
            eg += p * q * pay(k, h)
            tot += p * q
    return eh, eg / PRICE, tot


# --- verification 1 : les lois somment a 1, et l'invariance est retrouvee ---
say("""   Trois controles avant d'employer la machine.

   (a) NORMALISATION et INVARIANCE. A r = 0 la loi doit rendre exactement
       k/4 — c'est le theoreme d'invariance, qui devient ainsi un cas
       particulier VERIFIE et non une hypothese.
""")
say(f"   {'k':>4} {'somme des probas':>18} {'E[touches]':>12} {'k/4':>8} {'écart':>10}")
bad = 0.0
for k in STAKES:
    eh, _, tot = exact(0, k, 0)
    bad = max(bad, abs(tot - 1), abs(eh - k / 4))
    say(f"   {k:>4} {tot:>18.12f} {eh:>12.6f} {k/4:>8.2f} {abs(eh-k/4):>10.2e}")
say(f"   ecart maximal {bad:.2e} — arithmetique exacte, aux erreurs d'arrondi pres.")

# --- verification 2 : Monte-Carlo independant sur l'esperance ---
say(f"""
   (b) MONTE-CARLO INDEPENDANT. La moyenne, elle, se mesure sans peine. On
       tire {NMC:,} tirages ORDONNES sous SRS exact, on applique la regle de la
       lecture 3, et on compare a l'esperance calculee.
""")


def mc_hits(ordered, r, k, b):
    M, s = 1 << b, POOL >> b
    n = len(ordered)
    mask = np.zeros((n, POOL), np.int8)
    np.put_along_axis(mask, ordered, np.int8(1), axis=1)
    m3 = mask.reshape(n, s, M)
    tot, pref = m3.sum(1), np.cumsum(m3, axis=1)
    if r:
        idx = (np.arange(n)[:, None] * M + ordered[:, :r] % M).ravel()
        mr = np.bincount(idx, minlength=n * M).reshape(n, M)
    else:
        mr = np.zeros((n, M), np.int64)
    order = np.argsort(-mr, axis=1, kind="stable")
    nfull, rem = divmod(k, s)
    hits = np.zeros(n, np.int64)
    for i in range(nfull):
        hits += np.take_along_axis(tot, order[:, i:i + 1], 1)[:, 0]
    if rem:
        hits += pref[np.arange(n), rem - 1, order[:, nfull]]
    return hits


ORD = np.argsort(RNG.random((NMC, POOL)), axis=1)[:, :DRAWN]
say(f"   {'b':>2} {'r':>3} {'k':>3} {'E exacte':>11} {'Monte-Carlo':>13} {'écart':>9} {'σ MC':>8}")
worst_z = 0.0
for b, r, k in [(0, 0, 10), (1, 20, 10), (2, 20, 10), (4, 20, 10),
                (4, 20, 5), (4, 10, 8), (3, 5, 7), (4, 1, 10), (2, 8, 6)]:
    eh, _, _ = exact(r, k, b)
    h = mc_hits(ORD, r, k, b)
    mu, se = float(h.mean()), float(h.std(ddof=1)) / np.sqrt(NMC)
    worst_z = max(worst_z, abs(mu - eh) / se)
    say(f"   {b:>2} {r:>3} {k:>3} {eh:>11.5f} {mu:>13.5f} {mu-eh:>+9.5f} {se:>8.5f}")
say(f"""   Ecart maximal {worst_z:.2f} ecart-type. Les deux calculs — algebrique et
   empirique — concordent : la loi exacte est la bonne.

   (c) LE MONTE-CARLO NE SUFFIT PAS POUR LES RANGS. A k = 8, b = 4, r = 20 :
""")
law8 = {}
M4, s4 = 16, 5
for vec, p in sorted_counts_law(DRAWN, M4, s4):
    for h, q in hits_law(vec[:2], DRAWN, 8, M4, s4).items():
        law8[h] = law8.get(h, 0.0) + p * q
h8 = mc_hits(ORD, DRAWN, 8, 4)
say(f"   {'touches':>8} {'proba exacte':>15} {'gain CHF':>10} {'contribution':>13} {'MC (n)':>9}")
for h in range(8, 3, -1):
    say(f"   {h:>8} {law8.get(h,0):>15.3e} {pay(8,h):>10,.0f} "
        f"{law8.get(h,0)*pay(8,h):>13.4f} {int((h8==h).sum()):>9,}")
say(f"""   Le rang plein pese {law8.get(8,0)*pay(8,8)/PRICE:.3f} dans le taux de retour a lui seul, pour une
   probabilite de {law8.get(8,0):.2e}. Sur {NMC:,} tirages le Monte-Carlo en voit {int((h8==8).sum())} : son
   erreur relative sur CE rang est de l'ordre de {1/max(1,np.sqrt((h8==8).sum())):.0%}. C'est pourquoi les
   sections 3 a 5 n'emploient AUCUN tirage aleatoire.""")


# ==========================================================================
rule("3. LE TAUX DE CHANGE, EN TOUCHES")
# ==========================================================================

say(f"""   Combien de touches pour b bits par mot, tous les {DRAWN} residus connus ?
   La colonne b = 0 est le theoreme d'invariance : k/4, et rien d'autre.
""")
say("   " + f"{'k joués':>8}" + "".join(f"{'b='+str(b):>10}" for b in range(5))
    + f"{'gain ×':>9}")
E = {}
for k in STAKES:
    line = f"   {k:>8}"
    for b in range(5):
        E[(b, k)] = exact(DRAWN if b else 0, k, b)[0]
        line += f"{E[(b,k)]:>10.4f}"
    say(line + f"{E[(4,k)]/E[(0,k)]:>9.2f}")

say(f"""
   LECTURE. Le taux n'est pas lineaire en b : il s'emballe au dernier bit.

   A k = 10, de {E[(0,10)]:.2f} touches a {E[(4,10)]:.2f} — un facteur {E[(4,10)]/E[(0,10)]:.1f}. Le premier bit
   rapporte {E[(1,10)]-E[(0,10)]:.2f} touche, le quatrieme {E[(4,10)]-E[(3,10)]:.2f}, soit {(E[(4,10)]-E[(3,10)])/(E[(1,10)]-E[(0,10)]):.1f} fois plus.

   La raison est arithmetique, pas statistique, et elle tient a la TAILLE DE
   CLASSE s = 80/2^b — c'est-a-dire au fait que jouer « une classe » coute s
   numeros. Une classe est une grille toute faite : la jouer entierement
   convertit chaque numero tire de cette classe en une touche.

   Or connaitre un compte m_c ne vaut que rapporte a s. A b = 4, s = 5 et un
   seul residu observe rend deja P(x tire) = (1 + 4x19/79)/5 = {(1+4*19/79)/5:.4f},
   contre 1/4 — la grille de cinq membres passe de 1,25 a {5*(1+4*19/79)/5:.3f} touche.
   A b = 3, s = 10 : le meme residu observe se dilue sur dix membres et ne
   donne que {10*(1+9*19/79)/10:.3f} touches pour dix numeros joues, soit MOINS par franc mise.

   Le coude tombe donc quand s devient comparable au nombre de numeros qu'on
   veut jouer — cinq a dix ici. Et s = 5 est atteint exactement a
   b = v2(80) = 4, la valuation qui gouverne aussi la fuite (§68). Les deux
   coincident parce que c'est le meme entier qui les produit : celui-la meme
   dont le §74 montrait qu'un vivier impair l'annulerait.""")


# ==========================================================================
rule("4. LE COÛT DE L'ALIGNEMENT")
# ==========================================================================

say(f"""   Le regime B ne donne pas r = {DRAWN} gratuitement. Connaitre le nibble de
   CHAQUE mot du flux ne dit pas QUELS mots ont ete acceptes : le rejet en
   consomme ~2,85 de plus par tirage (§74), et leur position est inconnue.

   Le premier mot, lui, est TOUJOURS accepte — aucun doublon n'est encore
   possible. Donc r >= 1 sans aucune hypothese. Au-dela, l'alignement se
   paie. La courbe en r est l'intervalle honnete du regime B.
""")
say("   " + f"{'r connus':>9}" + "".join(f"{'k='+str(k):>10}" for k in STAKES))
R1 = {}
for r in (0, 1, 2, 3, 5, 8, 12, 16, 20):
    line = f"   {r:>9}"
    for k in STAKES:
        R1[(r, k)] = exact(r, k, 4)[0]
        line += f"{R1[(r,k)]:>10.4f}"
    say(line)
say(f"""
   ET VOICI CE QUI SAUTE AUX YEUX, que je n'attendais pas. A b = 4,
   connaitre UN SEUL residu — celui du premier numero, le seul qui soit
   gratuit — porte k = 5 de {R1[(0,5)]:.2f} a {R1[(1,5)]:.4f} touches, soit +{R1[(1,5)]/R1[(0,5)]-1:.0%}. Sur k = 10
   le meme residu ne donne que +{R1[(1,10)]/R1[(0,10)]-1:.0%}.

   La raison est la meme qu'a la section 3 : a b = 4 la classe compte cinq
   membres, donc la grille de CINQ numeros est exactement une classe, et le
   residu connu y place une touche CERTAINE. Etendre a dix numeros dilue
   cette certitude dans une seconde classe dont on ne sait rien.

   Le regime B a donc une lecture minimale qui ne coute presque rien : un
   residu, cinq numeros. La section 5 la chiffre en francs.""")


# ==========================================================================
rule("5. EN FRANCS : OÙ LE PARI BASCULE")
# ==========================================================================

say(f"""   Le bareme releve au §56 et le prix du ticket etabli au §63 (CHF {PRICE:.0f})
   transforment la loi des touches en taux de retour :

       TRR = E[gain(k, touches)] / prix

   Hors cagnotte BANGO : chaque chiffre ci-dessous est une BORNE INFERIEURE.
""")
say("   " + f"{'b':>2} {'r':>3}" + "".join(f"{'k='+str(k):>10}" for k in STAKES)
    + "   franchi")
for b in range(5):
    r = DRAWN if b else 0
    line, best = f"   {b:>2} {r:>3}", 0.0
    for k in STAKES:
        v = exact(r, k, b)[1]
        best = max(best, v)
        line += f"{v:>10.4f}"
    say(line + ("   OUI" if best > 1 else "   non"))

say(f"""
   LE CAS MINIMAL, ET C'EST LE RESULTAT DE CE FICHIER. Supposons qu'on ne
   sache RIEN du generateur sauf les b bits de poids faible de son PREMIER
   mot — celui qui produit le premier numero, toujours accepte, jamais
   ambigu. Un seul mot, b bits. Que vaut ce minimum absolu ?
""")
say("   " + f"{'b bits du mot 0':>16}" + "".join(f"{'k='+str(k):>10}" for k in STAKES))
for b in range(5):
    line = f"   {b:>16}"
    for k in STAKES:
        line += f"{exact(1 if b else 0, k, b)[1]:>10.4f}"
    say(line)
bmin = next(b for b in range(5)
            if max(exact(1 if b else 0, k, b)[1] for k in STAKES) > 1)
kmin = max(STAKES, key=lambda k: exact(1, k, bmin)[1])
say(f"""
   LE MINIMUM ABSOLU EST DE {bmin} BITS. Un seul mot, {bmin} bits de poids faible, et le
   taux de retour passe de {exact(0,5,0)[1]:.3f} a {exact(1,kmin,bmin)[1]:.3f} en jouant k = {kmin} : le pari bascule.
   Deux bits n'y suffisent pas ({max(exact(1,k,2)[1] for k in STAKES):.3f}), quatre donnent {max(exact(1,k,4)[1] for k in STAKES):.3f}.

   Le seuil est a {bmin} parce que la classe compte alors {POOL >> bmin} membres : une grille
   de {kmin} numeros en couvre {kmin/(POOL>>bmin):.0%}, et le residu connu y place une touche
   presque certaine. A deux bits la classe en compte {POOL >> 2} et la grille s'y
   dilue ; a quatre elle n'en compte que {POOL >> 4}, et la grille la couvre en entier.

   COMPARAISON QUI FIXE L'ORDRE DE GRANDEUR. Connaitre les VINGT residus a
   b = 1 — quatre-vingts observations, vingt mots — ne franchit pas le seuil
   ({max(exact(20,k,1)[1] for k in STAKES):.3f}). Connaitre {bmin} bits d'UN SEUL mot le franchit. TROIS BITS BIEN
   PLACES VALENT MIEUX QUE VINGT BITS MAL PLACES : c'est la valuation
   2-adique du vivier qui decide, pas le volume d'information.""")

say("\n   A b = 4, en fonction du nombre de residus connus :\n")
say("   " + f"{'r':>3}" + "".join(f"{'k='+str(k):>10}" for k in STAKES)
    + "   franchi")
cross = None
for r in range(0, DRAWN + 1):
    line, best, bk = f"   {r:>3}", 0.0, None
    for k in STAKES:
        v = exact(r, k, 4)[1]
        if v > best:
            best, bk = v, k
        line += f"{v:>10.4f}"
    if best > 1 and cross is None:
        cross = (r, bk, best)
    say(line + ("   OUI" if best > 1 else "   non"))

if cross:
    r0, k0, v0 = cross
    say(f"""
   LE SEUIL, ET C'EST LA REPONSE CHIFFREE A « QUEL MUR FAUT-IL FRANCHIR ».

     ce qu'il faut          {bmin} bits — les {bmin} bits de poids faible d'UN mot,
                            celui qui produira le PREMIER numero du prochain
                            tirage
     la grille              k = {kmin} : les {POOL >> bmin} numeros de la classe residuelle
     ce que cela rend       taux de retour {exact(1,kmin,bmin)[1]:.3f} contre {exact(0,kmin,0)[1]:.3f}, hors cagnotte

     sur ce que publie §68  {bmin} sur {4*DRAWN} bits par tirage, soit {bmin/(4*DRAWN):.1%}
     sur l'etat d'un xs64   {bmin} sur 64, soit {bmin/64:.1%}
     sur l'etat de MT19937  {bmin} sur 19 937, soit {bmin/19937:.3%}

   Le dossier cherchait a resoudre 19 937 inconnues (§77). Il en faut {bmin} —
   et non pas {bmin} inconnues quelconques, mais {bmin} FORMES LINEAIRES PRECISES.

   C'est un probleme entierement different, et bien plus faible : predire {bmin}
   bits ne demande pas que le systeme soit de rang plein, seulement que ces
   {bmin} formes appartiennent a l'espace engendre par celles deja observees.
   Le §77 butait sur un mur de RANG ; ce mur-ci est un mur d'APPARTENANCE, et
   les deux n'ont ni la meme hauteur ni la meme nature.

   Pour memoire, connaitre les {DRAWN} residus complets (r = {DRAWN}, b = 4) porte
   le taux a {max(exact(DRAWN,k,4)[1] for k in STAKES):.1f} — mais ce n'est plus le mur, c'est le luxe. Le mur, c'est
   la ligne du dessus, et le premier chiffre franchi l'est a {bmin} bits.""")
else:
    say(f"""
   AUCUN SEUIL FRANCHI hors cagnotte, meme a b = 4 et r = {DRAWN}. Resultat
   NEGATIF et informatif : le bareme fixe ne suffit pas, c'est la cagnotte
   BANGO qui porterait la bascule.""")


# ==========================================================================
rule("6. LE RÉGIME A, POUR DE VRAI : UN TIRAGE, PUIS LA PRÉDICTION")
# ==========================================================================

say("""   Les sections 3 a 5 SUPPOSENT les residus connus. Le regime A les
   PRODUIT : on resout l'etat par elimination de Gauss (§68), puis on rejoue
   le generateur. Voici la chaine complete, sur xorshift64.
""")


def m64(n):
    return (1 << n) - 1


def xs64(s):
    s ^= (s << 13) & m64(64)
    s ^= s >> 7
    s ^= (s << 17) & m64(64)
    return s, s


def words_from(step, state, count):
    out, s = [], state
    for _ in range(count):
        s, w = step(s)
        out.append(w)
    return out


def simulate(step, state, ndraws):
    s, draws = state, []
    for _ in range(ndraws):
        seen, out = set(), []
        while len(out) < DRAWN:
            s, w = step(s)
            n = w % POOL + 1
            if n not in seen:
                seen.add(n)
                out.append(n)
        draws.append(out)
    return draws


def basis_bits(step, nbits, nwords):
    cols = [words_from(step, 1 << i, nwords) for i in range(nbits)]
    coef = [[0] * 4 for _ in range(nwords)]
    for i in range(nbits):
        ci, bit = cols[i], 1 << i
        for pos in range(nwords):
            w, cp = ci[pos], coef[pos]
            if w & 1: cp[0] |= bit
            if w & 2: cp[1] |= bit
            if w & 4: cp[2] |= bit
            if w & 8: cp[3] |= bit
    return coef


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


def back_substitute(piv, nbits):
    sol = 0
    for h in sorted(piv):
        pr, pb = piv[h]
        if (bin(pr & sol).count("1") + pb) & 1:
            sol ^= 1 << h
    return sol, [i for i in range(nbits) if i not in piv]


def attack(step, nbits, draw, coef, nwords, max_rej):
    """Retrouve l'etat depuis UN tirage ordonne. Les rejets sont enumeres en
    profondeur avec elimination incrementale : une branche incoherente meurt
    des la premiere equation, une branche de rang plein remonte aussitot."""
    found = []

    def dfs(pos, k, nrej, piv):
        if found:
            return
        if len(piv) >= nbits or k == DRAWN:
            sol, free = back_substitute(piv, nbits)
            if not free and simulate(step, sol, 1)[0] == draw:
                found.append(sol)
            return
        if pos >= nwords:
            return
        p2 = dict(piv)
        val, cp, ok = (draw[k] - 1) & 15, coef[pos], True
        for b in range(4):
            if not add_eq(p2, cp[b], (val >> b) & 1):
                ok = False
                break
        if ok:
            dfs(pos + 1, k + 1, nrej, p2)
        if found:
            return
        if nrej < max_rej and k >= 1:
            dfs(pos + 1, k, nrej + 1, piv)

    dfs(0, 0, 0, {})
    return found[0] if found else None


NSEED = 20 if DRY else 80
MAX_REJ, NBITS = 8, 64
NW = DRAWN + MAX_REJ
COEF = basis_bits(xs64, NBITS, NW)
rng = np.random.default_rng(4242)
ok_state = ok_pred = 0
hits10 = []
for _ in range(NSEED):
    truth = simulate(xs64, int(rng.integers(1, 1 << 63)) | 1, 2)
    got = attack(xs64, NBITS, truth[0], COEF, NW, MAX_REJ)
    if got is None:
        continue
    ok_state += 1
    pred = simulate(xs64, got, 2)[1]
    ok_pred += pred == truth[1]
    hits10.append(len(set(pred[:10]) & set(truth[1])))

say(f"""   {NSEED} graines de 64 bits, tirees au hasard. Pour chacune : UN tirage
   ordonne est observe, l'etat est resolu, le tirage SUIVANT est predit.

     etats retrouves            {ok_state:>3} / {NSEED}
     tirages suivants predits   {ok_pred:>3} / {NSEED}   (les vingt numeros, dans l'ordre)
     touches en jouant 10       {np.mean(hits10) if hits10 else 0:>5.1f} / 10   (contre {E[(0,10)]:.2f} sous invariance)

   Taux de retour correspondant a k = 10 : {BAREME[10][10]/PRICE:,.0f} fois la mise, hors cagnotte.

   Ce n'est PAS un resultat sur le jeu reel. C'est la preuve que la chaine
   « ordre -> equations -> etat -> prediction -> grille » est complete et
   sans trou des que le generateur est F2-lineaire. Le §68 donnait le maillon
   algebrique ; celui-ci le prolonge jusqu'au bulletin.""")


# ==========================================================================
rule("7. CE QUE CELA ÉTABLIT, ET CE QUE CELA NE FAIT PAS")
# ==========================================================================

say(f"""   ETABLIT.

   1. LE THEOREME DE CONVERSION (*) : la loi a posteriori d'un numero
      sachant r residus, en forme fermee. Il CONTIENT le theoreme
      d'invariance comme cas r = 0 — verifie a {bad:.0e} pres — et montre que ce
      dernier n'est jamais VIOLE (la masse reste 20) mais CONTOURNE par sa
      repartition.

   2. LA LOI COMPLETE des touches, exacte, sans Monte-Carlo. Necessaire :
      les rangs pleins pesent lourd au bareme et sont invisibles a
      l'echantillonnage.

   3. LA GRILLE OPTIMALE se lit sans optimisation : trier les classes par
      compte decroissant. Le probleme de decision est ferme.

   4. LE MUR EST CHIFFRE, ET IL EST PETIT. Le dossier disait « il faut
      reproduire le generateur ». Faux : {bmin} bits d'UN SEUL mot suffisent a
      porter le taux de retour de {exact(0,kmin,0)[1]:.3f} a {exact(1,kmin,bmin)[1]:.3f} (section 5). Le programme
      de recherche change donc de nature — il ne s'agit plus de RESOUDRE un
      etat de 19 937 bits mais de PREDIRE {bmin} formes lineaires, ce qui est une
      condition d'APPARTENANCE et non de RANG.

   5. UN COROLLAIRE NEGATIF QUI ORIENTE : vingt bits mal places (b = 1 sur
      les vingt numeros) ne franchissent pas le seuil, quand {bmin} bits bien
      places le franchissent. La valuation 2-adique du vivier decide, le
      volume d'information non.

   NE FAIT PAS.

   a. Les colonnes r > 1 supposent le rejet modulo le vivier. Sous
      Fisher-Yates la fuite tombe a 22 bits (§71) et les residus portent sur
      des INDICES dans un tableau deja permute : la classe (n-1) mod 16 n'y
      est plus definie a partir du deuxieme numero.

      MAIS LE CAS r = 1 SURVIT AUX DEUX ECHANTILLONNEURS, et c'est
      justement celui du resultat. Au pas 0, Fisher-Yates lit le tableau
      INTACT 1..80 et tire modulo 80 : le premier numero vaut
      (out_0 mod 80) + 1 exactement, comme sous rejet (§77). Le mot 0 publie
      donc v2(80) = 4 bits du premier numero DANS LES DEUX CAS, et le mur de
      la section 5 — {bmin} bits d'un seul mot — ne depend pas de
      l'echantillonneur. C'est le seul endroit du volet §68-§78 dont ce soit
      vrai.

   b. Rien ne dit que le tirage reel est vulnerable. Les tests d'archive —
      §76 sur les {70560:,} tirages, §68 et §77 sur les cinq tirages ordonnes —
      n'ont rien trouve. Ce fichier chiffre la VALEUR d'une porte ; il n'en
      ouvre aucune.

   c. La cagnotte BANGO n'entre pas dans le taux de retour : bornes
      inferieures partout.

   Registre : INCHANGE. h58 derive, verifie, et chiffre.

   ({time.time() - T0:.1f} s)""")
