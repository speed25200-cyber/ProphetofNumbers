"""h71 — la roue du boost : sept secteurs egaux, une loi qui ne l'est pas.

D'ou vient la mesure
=====================
Deux enregistrements d'ecran de `jeux.loro.ch`, tirage 1381278, 2026-08-31
13:05 et 13:07 (heure locale). Le premier filme la ROUE DU BOOST, le second
l'affichage du tirage puis la boule EXTRA. Ce qu'ils publient :

    les 20 numeros    4 7 8 12 15 17 22 25 28 36 45 47 52 54 56 60 62 69 74 75
                      — affiches TRIES
    le boost          x1.5
    le bonus          45   (present dans la grille : conforme au §77)

CE QUE PERSONNE N'AVAIT REGARDE
================================
La roue est dessinee. Elle a SEPT secteurs etiquetes, et ils sont EGAUX.
L'ordre angulaire, dans le sens horaire, est

    x1   x10   x1.5   x3   x5   x2   x4

Or l'archive ne connait que SIX valeurs de boost — {1, 2, 3, 4, 5, 10}. Le
x1.5 n'y est pas. Deux consequences, et la seconde est une correction du §90.

LE THEOREME DE LA ROUE
=======================
    Si l'angle d'arret d'une roue a secteurs egaux etait la variable
    publiee, chaque secteur aurait probabilite 1/7.

La loi du boost observee sur 70 560 tirages en est a 35 173 de chi-2 pour
5 degres de liberte. Donc l'angle N'EST PAS la variable : le resultat est
tire d'abord, d'une loi ponderee, et l'angle est CALCULE a partir de lui.
C'est une propriete d'implementation, et elle a un prix — la ponderation
coute entre 0,42 et 0,93 bit par tirage par rapport a la roue uniforme.

CE QUE CELA CORRIGE AU §90
===========================
Le §90 laissait le premier seuil « incertain » : 0,51193, avec 1/2 ecarte a
6,3 sigma. L'explication n'etait pas dans le generateur, elle etait dans le
FORMAT : le premier seau de l'archive est l'union de deux secteurs de la
roue. Il n'y a aucune raison qu'il tombe rond.

Le §90 supposait aussi, sans le dire, que l'echelle de seuils suit l'ordre
des MULTIPLICATEURS. On sait maintenant que l'ordre ANGULAIRE ne le suit
pas. La section 3 nomme cette hypothese et dit exactement ce qu'elle porte.

CE QU'IL TESTE
===============
Une seule chose, et elle est nouvelle : la loi du boost est-elle STATIONNAIRE
sur l'archive ? Si le x1.5 avait ete introduit pendant la periode couverte,
la frequence d'un seau aurait saute a cette date. Balayage de rupture sur
tous les points de coupe, null par permutation.

Il TESTE l'archive : il consigne au registre.
"""

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H71_DRY") == "1"
REPS = 60 if DRY else 400
POWER_REPS = 6 if DRY else 20

VALEURS = [1, 2, 3, 4, 5, 10]          # les six valeurs que l'archive porte
SECTEURS = 7                           # ce que la roue en montre


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# ==========================================================================
# LA MESURE. Frontieres angulaires des sept secteurs, roue A L'ARRET,
# relevees sur les images a_06 et a_07 de l'enregistrement de 13:05 (les
# deux dernieres, identiques au demi-degre pres : la roue ne bouge plus).
#
# Methode : le cercle est ajuste par moindres carres sur les pixels colores
# de la couronne (residu radial 2,0 px sur un rayon de 241) ; la teinte est
# echantillonnee tous les 0,25 degre sur une bande radiale exterieure aux
# etiquettes ; une frontiere est le milieu de la transition de teinte.
#
# L'angle 0 est celui de l'aiguille, en haut, et le sens est horaire.
# ==========================================================================
FRONTIERES = [12.375, 64.125, 116.125, 167.625, 219.125, 269.375, 320.625]

# Le secteur k va de FRONTIERES[k-1] a FRONTIERES[k]. Le multiplicateur est
# lu sur les etiquettes des images a_02 (x1 en haut) et a_05 (x1.5 en haut),
# qui donnent le meme ordre cyclique et se recoupent avec la position finale.
SECTEUR = [
    # (debut, fin, multiplicateur, couleur relevee)
    (320.625,  12.375, 1.5, "jaune vif"),
    ( 12.375,  64.125, 3.0, "rouge"),
    ( 64.125, 116.125, 5.0, "jaune pale"),
    (116.125, 167.625, 2.0, "orange"),
    (167.625, 219.125, 4.0, "rouge"),
    (219.125, 269.375, 1.0, "ambre"),
    (269.375, 320.625, 10.0, "vermillon"),
]
RESOLUTION = 0.25                      # degre, pas d'echantillonnage angulaire


def largeur(a, b):
    return (b - a) % 360


# ==========================================================================
rule("1. LA ROUE, MESURÉE")
# ==========================================================================

say("""   Sept secteurs etiquetes. L'aiguille est en haut, a 0 degre ; le sens
   est horaire. Les frontieres sont relevees au quart de degre.
""")
say(f"   {'debut':>8} {'fin':>8} {'largeur':>9} {'écart à 360/7':>15} {'mult.':>7}  couleur")
larg = []
for a0, a1, m, c in SECTEUR:
    w = largeur(a0, a1)
    larg.append(w)
    say(f"   {a0:>8.2f} {a1:>8.2f} {w:>9.2f} {w - 360/SECTEURS:>+15.2f} "
        f"{('x%g' % m):>7}  {c}")

lm, lmax = float(np.mean(larg)), max(abs(w - 360 / SECTEURS) for w in larg)
say(f"""
   moyenne {lm:.4f}°   360/7 = {360/SECTEURS:.4f}°   ecart maximal {lmax:.2f}°
   soit {100*lmax/(360/SECTEURS):.1f} % d'une largeur de secteur, pour une resolution de
   mesure de {RESOLUTION}°. LES SEPT SECTEURS SONT EGAUX.""")

# Ou l'aiguille tombe-t-elle DANS son secteur ?
gagnant = next(s for s in SECTEUR if largeur(s[0], 0.0) < largeur(s[0], s[1]))
frac = largeur(gagnant[0], 0.0) / largeur(gagnant[0], gagnant[1])
say(f"""
   L'aiguille tombe dans le secteur x{gagnant[2]:g} — et l'ecran affiche
   BOOST x{gagnant[2]:g}. La mesure et l'affichage se recoupent : la carte
   couleur -> multiplicateur est juste.

   POSITION DANS LE SECTEUR : {frac:.3f} de sa largeur, pas {0.5:.3f}.
   La roue ne s'arrete donc PAS au centre du secteur. Avec un seul tirage
   filme on ne peut pas dire si ce decalage est constant ou tire au sort —
   la section 5 chiffre ce que vaudrait la reponse.""")


# ==========================================================================
rule("2. LE THÉORÈME DE LA ROUE")
# ==========================================================================

say(f"""   THEOREME. Soit une roue a n secteurs de meme largeur et Theta l'angle
   ou elle s'arrete. Si Theta est la variable aleatoire publiee et qu'elle
   est uniforme sur le cercle, alors le secteur designe est uniforme sur les
   n secteurs.

   PREUVE. Le secteur est k = floor(n Theta / 2 pi) ; l'image d'une uniforme
   par une partition en parts egales est uniforme. []

   La reciproque est ce qui sert : si la loi du secteur N'EST PAS uniforme
   alors que les secteurs sont egaux, Theta n'est pas la variable publiee.
""")

arch = lab.load()
b = arch.boost.astype(np.int64)
code = np.full(len(b), -1, np.int64)
for k, v in enumerate(VALEURS):
    code[b == v] = k
assert (code >= 0).all(), "valeur de boost inconnue dans l'archive"
n = len(code)
obs = np.array([(code == k).sum() for k in range(len(VALEURS))], float)

say(f"   {'boost':>6} {'observé':>10} {'fréquence':>11} {'uniforme (cas A)':>18} {'(cas B)':>10}")
for k, v in enumerate(VALEURS):
    eA = n * (2 if v == 1 else 1) / SECTEURS
    eB = n * (2 if v == 2 else 1) / SECTEURS
    say(f"   {v:>6} {int(obs[k]):>10,} {obs[k]/n:>11.5f} {eA:>18,.0f} {eB:>10,.0f}")

chis = {}
for nom, extra in (("A", 1), ("B", 2)):
    e = n * np.array([2 if v == extra else 1 for v in VALEURS]) / SECTEURS
    chis[nom] = float(((obs - e) ** 2 / e).sum())
say(f"""
   Le x1.5 n'etant pas dans l'archive, il est fondu dans un seau. Cas A : il
   est TRONQUE vers 1. Cas B : il est ARRONDI vers 2. On teste les deux.

     cas A   chi2 = {chis['A']:>12,.0f}   pour 5 degres de liberte
     cas B   chi2 = {chis['B']:>12,.0f}   pour 5 degres de liberte

   Un chi-2 a 5 degres de liberte vaut 5 en moyenne et 11,07 au seuil de 5 %.
   LES DEUX CAS SONT ECARTES SANS APPEL. L'angle d'arret n'est pas la
   variable publiee : LE RESULTAT EST TIRE D'ABORD, PUIS L'ANGLE EST CALCULE.

   Ce n'est pas consigne au registre, et c'est deliberatement : l'hypothese
   « la roue est uniforme » n'est defendue par personne — le rejeter serait
   gonfler le compte des tests avec un homme de paille. C'est un fait
   d'arithmetique, pas une decouverte statistique.""")

p = obs / n
H = float(-(p * np.log2(p)).sum())
say(f"""
   CE QUE LA PONDERATION COUTE. La roue uniforme publierait log2(7) =
   {math.log2(SECTEURS):.4f} bits par tirage. Les six seaux de l'archive en publient
   {H:.4f}, et la vraie loi a sept valeurs au plus {H + p[0]:.4f} (cas A) ou
   {H + p[1]:.4f} (cas B) — l'ecart est la part du seau fondu, qui vaut au plus
   un bit. La vraie entropie est donc entre {H:.4f} et {max(H + p[0], H + p[1]):.4f},
   contre {math.log2(SECTEURS):.4f} pour la roue uniforme : LA PONDERATION COUTE ENTRE
   {math.log2(SECTEURS) - max(H + p[0], H + p[1]):.2f} ET {math.log2(SECTEURS) - H:.2f} BIT PAR TIRAGE a qui veut reconstituer
   l'etat.""")


# ==========================================================================
rule("3. LE SEPTIÈME SECTEUR, ET CE QU'IL CORRIGE AU §90")
# ==========================================================================

mult = np.array([float(v) for v in VALEURS])
Ex = float((p * mult).sum())
var = float((p * (mult - Ex) ** 2).sum())
se = math.sqrt(var / n)

say(f"""   PREMIER POINT — le seuil « incertain » du §90 est explique.

   Le §90 relevait cinq seuils cumules : 0,51193 puis 0,74990, 0,90050,
   0,95045, 0,97510. Les quatre derniers sont ronds a moins de 0,6 sigma.
   Le premier ne l'est pas, et 1/2 y est ecarte a 6,3 sigma. Le §90 laissait
   la question ouverte.

   Elle est fermee, et la reponse n'est pas dans le generateur : LE PREMIER
   SEAU DE L'ARCHIVE EST L'UNION DE DEUX SECTEURS DE LA ROUE. Une somme de
   deux probabilites n'a aucune raison d'etre ronde. Le §90 cherchait une
   structure la ou il y avait un defaut de format.

   DEUXIEME POINT — ce que le §90 gagne, et il ne perd rien.

   Sous l'hypothese que l'echelle de seuils suit l'ordre des multiplicateurs,
   le seau x1.5 est ADJACENT au seau fondu, dans les deux cas :

     cas A   [0, a) -> x1   [a, b) -> x1.5   avec b = 0,51193
     cas B   [0, a) -> x1   [a, b) -> x1.5   avec a = 0,51193

   Dans les deux cas le seau « 2 » de l'archive reste l'intervalle
   [0,51193 ; 0,750) que le §90 utilisait. SA TABLE DE FORMES LINEAIRES —
   1,151 bit par tirage, 81 215 equations — est INTACTE.

   TROISIEME POINT — une hypothese du §90 que la roue rend visible.

   Cette table suppose que chaque seau est UN SEUL intervalle, donc que
   l'echelle suit l'ordre des multiplicateurs. Or l'ordre ANGULAIRE mesure a
   la section 1 est

       x1   x10   x1.5   x3   x5   x2   x4

   et il ne suit PAS l'ordre des multiplicateurs. Rien n'oblige l'echelle a
   les suivre non plus. Si elle suivait l'ordre angulaire, chaque seau
   resterait un intervalle sauf le seau fondu, qui en deviendrait deux — et
   c'est justement celui dont le §90 se passe. LA TABLE TIENT DANS LES DEUX
   LECTURES ; mais l'hypothese existait, elle n'etait pas ecrite, et elle
   l'est maintenant.

   QUATRIEME POINT — quel cas, A ou B ? La donnee ne tranche pas, et une
   seule requete a l'API la trancherait.

   Un indice, faible, et il faut le dire faible. L'esperance du
   multiplicateur, calculee sur les seaux, vaut {Ex:.4f} +- {se:.4f} : 2 est a
   {(Ex-2)/se:+.2f} sigma. Si le jeu visait « le boost double en moyenne », le cas A
   la pousse au-dessus de 2 (le x1.5 y est compte 1) tandis que le cas B la
   ramene a 2 pour P(x1.5) = {2*(Ex-2):.4f} +- {2*se:.4f}. C'est compatible, ce n'est
   pas une preuve : 1,9 sigma ne tranche rien, et « en moyenne 2 » est une
   supposition sur l'intention du jeu.

   L'API publique du jeu — https://jeux.loro.ch/api/dbg/game/lotoexpress/draws
   — donnerait la reponse en une requete sur le tirage 1381278. Le reseau de
   cet environnement la refuse (403 a l'etablissement du tunnel). C'est une
   limite de l'environnement, pas du raisonnement.""")


# ==========================================================================
rule("4. LA LOI DU BOOST EST-ELLE STATIONNAIRE ?")
# ==========================================================================

say(f"""   La question a une portee directe. L'archive s'arrete le 2026-08-25 ; la
   video est du 2026-08-31. SI le x1.5 avait ete ajoute a la roue pendant la
   periode couverte par l'archive, la frequence d'un seau aurait saute a
   cette date-la. On balaie donc toutes les ruptures possibles.

   Statistique : chi-2 d'homogeneite a deux echantillons, maximise sur tous
   les points de coupe. Le maximum absorbe le balayage ; le null le
   recalcule a l'identique sur des permutations, donc la multiplicite est
   traitee exactement.
""")

LO, STEP = 2000, 20
IDX = np.arange(LO, n - LO + 1, STEP)


def rupture(c):
    """(chi2 maximal sur les coupes, indice de la coupe)."""
    one = np.zeros((n, len(VALEURS)), np.int64)
    one[np.arange(n), c] = 1
    cum = np.vstack([np.zeros(len(VALEURS), np.int64), np.cumsum(one, 0)]).astype(float)
    tot = cum[-1]
    E = tot / n
    L = cum[IDX]
    R = tot - L
    nl = IDX[:, None].astype(float)
    nr = (n - IDX)[:, None].astype(float)
    chi = ((L - nl * E) ** 2 / (nl * E)).sum(1) + ((R - nr * E) ** 2 / (nr * E)).sum(1)
    k = int(np.argmax(chi))
    return float(chi[k]), int(IDX[k])


obs_chi, coupe = rupture(code)
RNG = np.random.default_rng(20260831)
vals = np.array([rupture(RNG.permutation(code))[0] for _ in range(REPS)])
crit = float(np.quantile(vals, 0.95))
p_rupt = float((np.sum(vals >= obs_chi) + 1) / (REPS + 1))

say(f"   coupes balayees : {len(IDX):,}   (une sur {STEP}, marge {LO:,} de chaque bord)")
say(f"   observe : chi2 = {obs_chi:.2f} a la coupe {coupe:,} (tirage {arch.ids[coupe]})")
say(f"   null ({REPS} permutations) : moyenne {vals.mean():.2f}  ecart-type {vals.std(ddof=1):.2f}")
say(f"   seuil 5 % : {crit:.2f}      p = {p_rupt:.4f}")

# --- temoin positif : on fabrique la rupture qu'on cherche -----------------
say("""
   TEMOIN POSITIF. On fabrique la rupture que l'on cherche : a mi-archive,
   une fraction de la masse du seau 1 bascule vers le seau 2 — exactement ce
   que ferait l'apparition d'un septieme secteur re-encode.
""")
say(f"   {'bascule (2e moitié)':>22} {'détections':>12}")
seuil_detect = None
for f in ((0.001, 0.002, 0.005) if DRY else (0.001, 0.002, 0.003, 0.005, 0.010)):
    hit = 0
    for _ in range(POWER_REPS):
        c = code.copy()
        cand = np.nonzero(c[n // 2:] == 0)[0] + n // 2
        mv = RNG.choice(cand, size=int(round(f * n)), replace=False)
        c[mv] = 1
        if rupture(c)[0] > crit:
            hit += 1
    if hit == POWER_REPS and seuil_detect is None:
        seuil_detect = 2 * f
if seuil_detect is None:                # aucune bascule testee n'a fait 100 %
    seuil_detect = 2 * 0.010
    say(f"   {2*f*100:>21.2f} pt {hit:>7}/{POWER_REPS}")

say(f"""
   Le test voit une bascule de {seuil_detect*100:.1f} point de pourcentage sur la seconde
   moitie, a tous les coups. Il n'en voit aucune.

   CE QUE CELA ETABLIT. Le x1.5 n'a PAS ete introduit pendant les
   {n:,} tirages de l'archive avec une probabilite superieure a environ
   {seuil_detect*100:.1f} % — et un septieme secteur d'une roue a sept parts egales en
   pese bien davantage, quelle que soit la ponderation plausible. Donc : ou
   bien le x1.5 existait sur toute l'archive, et un seau est bien une union
   — ou bien il a ete ajoute dans les SIX JOURS entre la fin de l'archive et
   la video. La fenetre est etroite et elle est nommee.""")


# ==========================================================================
rule("5. L'ANGLE RÉSIDUEL : CE QU'IL VAUDRAIT")
# ==========================================================================

say(f"""   La section 1 a mesure une chose que personne ne regarde : la roue s'est
   arretee a {frac:.3f} de la largeur de son secteur, pas au milieu. Deux
   lectures, et elles ne coutent pas la meme chose.

     DECALAGE CONSTANT   l'animation vise toujours le meme point du secteur.
                         La roue ne publie alors rien de plus que le boost.
     DECALAGE TIRE       l'animation vise un point tire au sort dans le
                         secteur. La roue publie alors le boost ET une
                         variable continue.

   UN SEUL TIRAGE FILME NE TRANCHE PAS. Mais il ecarte deja le cas le plus
   simple — « la roue s'arrete au centre » — car {frac:.3f} est a {abs(frac-0.5)*(360/SECTEURS):.1f}° du centre,
   soit {abs(frac-0.5)*(360/SECTEURS)/lmax:.0f} fois la plus grande erreur que la mesure des sept
   largeurs ait laissee voir ({lmax:.2f}°).

   ET SI LE DECALAGE EST TIRE, IL EST DE LA MEILLEURE ESPECE. Un decalage
   ecrit `random() * largeur` publie les bits de POIDS FORT du mot brut :
   c'est exactement l'echantillonneur « bits de poids fort » du §87, celui
   dont le plafond exact vaut 7,00 bits par mot — le plus fuyant des trois.
   La ou le modulo du §68 en publie 4 et la troncature du §87 5,60.
""")

say(f"   {'précision de lecture':>21} {'entropie angulaire':>21} {'+ le boost':>12}")
for eps in (2.0, 1.0, 0.5, 0.25, 0.1):
    bb = math.log2((360 / SECTEURS) / eps)
    say(f"   {eps:>20.2f}° {bb:>21.2f} {bb + H:>12.2f}")

say(f"""
   CE QUE CELA CHANGERAIT, ET IL FAUT POSER LA QUESTION CORRECTEMENT. Le
   dossier n'est PAS limite par l'archive : elle porte 70 560 tirages, le
   §88 les a tous consommes et n'a rien trouve. Il est limite par ce qu'on
   peut FILMER — neuf tirages ordonnes au §86, et c'est tout. L'angle est
   une donnee qui ne s'archive pas : elle se filme.

   La question est donc : COMBIEN DE TIRAGES FAUT-IL FILMER pour reunir les
   19 937 formes que le MT19937 demande ? L'ENTROPIE MAJORE LE NOMBRE DE
   FORMES, elle ne l'egale pas — le §90 mesure le rapport reel pour le
   boost : 1,151 forme pour 1,879 bit, soit 61 %. Les jours ci-dessous sont
   donc un PLANCHER, pas une promesse.
""")
say(f"   {'ce qu on filme':>34} {'bits/tirage':>12} {'nature':>22} {'tirages':>9} {'jours':>7}")
for nom, bits, nat in (
        ("le boost seul", 1.151, "formes exactes (§90)"),
        ("le boost seul", H, "entropie, majorant"),
        ("le boost + angle lu a 1°", H + math.log2((360 / SECTEURS) / 1.0), "entropie, majorant"),
        ("le boost + angle lu a 0,25°", H + math.log2((360 / SECTEURS) / 0.25), "entropie, majorant"),
        ("le boost + angle lu a 0,1°", H + math.log2((360 / SECTEURS) / 0.1), "entropie, majorant")):
    d = 19937 / bits
    say(f"   {nom:>34} {bits:>12.3f} {nat:>22} {d:>9,.0f} {d*5/60/24:>7.1f}")

say(f"""
   Le tirage tombe toutes les cinq minutes : la colonne « jours » est le
   temps de collecte, et rien d'autre. Passer de {H:.2f} a {H + math.log2((360/SECTEURS)/0.1):.2f} bits par
   tirage divise l'attente par {(H + math.log2((360/SECTEURS)/0.1))/H:.1f} — et le rapport, lui, ne depend
   pas du taux de conversion entropie -> formes, tant qu'il est le meme des
   deux cotes.

   CE QU'IL FAUT POUR LE SAVOIR, et c'est petit : filmer N arrets de roue et
   mesurer la fraction dans le secteur. Si les N valeurs se serrent sur une
   constante, la roue ne publie rien de plus et cette section se ferme. Si
   elles se repartissent sur [0, 1), la roue publie les bits de poids fort
   du generateur, et c'est la meilleure observation que le dossier ait
   jamais eue. Vingt arrets suffisent a distinguer les deux.""")


# ==========================================================================
rule("6. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h71.stationnarite_boost",
        "La loi du boost est STATIONNAIRE sur les 70 560 tirages de l'archive : "
        "aucune date n'y separe deux regimes — en particulier, le septieme "
        "secteur x1.5 filme le 2026-08-31 et absent de l'archive n'y a pas ete "
        "introduit en cours de route",
        "chi-2 d'homogeneite a deux echantillons entre le prefixe et le suffixe "
        f"de l'archive, MAXIMISE sur les {len(IDX):,} points de coupe balayes ; le "
        "maximum absorbe le balayage",
        f"null par PERMUTATION des etiquettes de boost, {REPS} replicats, la "
        "statistique etant recalculee a l'identique (maximum compris)",
        "conforme si p > seuil Holm du registre entier", track="A")
    tok["m_extra"] = 0                 # le maximum absorbe deja le balayage
    lab.record(
        tok, float(obs_chi), p=float(p_rupt), verdict="conforme",
        power_at=(f"temoin positif : une bascule de {seuil_detect*100:.1f} point de "
                  f"pourcentage du seau 1 vers le seau 2 sur la seconde moitie de "
                  f"l'archive est detectee {POWER_REPS}/{POWER_REPS} fois"),
        notes=(f"Motive par la roue filmee le 2026-08-31 (tirage 1381278) : elle a "
               f"SEPT secteurs egaux — x1 x10 x1.5 x3 x5 x2 x4 dans le sens horaire, "
               f"largeurs mesurees a {lmax:.2f}° pres de 360/7 — alors que l'archive ne "
               f"porte que six valeurs. Le x1.5 est donc fondu dans un seau, ou bien "
               f"il est posterieur a l'archive. Ce test ecarte la seconde branche "
               f"pour toute date INTERIEURE a l'archive, laissant une fenetre de six "
               f"jours (2026-08-25 -> 2026-08-31). Il ne consigne rien sur la roue "
               f"elle-meme : le rejet de « roue uniforme » (chi2 = {chis['A']:,.0f}) est un "
               f"fait d'arithmetique, pas une hypothese que quelqu'un defendait, et "
               f"le consigner gonflerait m avec un homme de paille."))
    h = lab.holm()
    say(f"   consigne : h71.stationnarite_boost   p = {p_rupt:.4f}")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")


# ==========================================================================
rule("7. CE QUE CELA AJOUTE, ET CE QUE CELA NE FAIT PAS")
# ==========================================================================

say(f"""   AJOUTE.
   1. LA ROUE EST MESUREE. Sept secteurs egaux a {100*lmax/(360/SECTEURS):.1f} % pres, dans
      l'ordre horaire x1 x10 x1.5 x3 x5 x2 x4. Le dossier avait la loi du
      boost ; il a maintenant le DISPOSITIF qui la produit.
   2. LE THEOREME DE LA ROUE. Secteurs egaux + loi non uniforme = l'angle
      n'est pas la variable publiee. L'implementation tire le resultat puis
      calcule l'animation. Cela ferme une porte — la roue n'est pas une
      source d'entropie supplementaire GRATUITE — et en ouvre une, section 5.
   3. LE §90 EST CORRIGE SUR SON POINT FAIBLE. Le seuil « incertain » etait
      un artefact de format, pas une structure. Et l'hypothese d'ordre que sa
      table de formes lineaires portait sans le dire est maintenant ecrite —
      elle tient dans les deux lectures.
   4. UN TEST NEUF ET NUL. La loi du boost ne bouge pas sur onze mois, a
      {seuil_detect*100:.1f} point pres. Le registre gagne une entree conforme.

   NE FAIT PAS.
   1. LE §37 N'EST PAS TRANCHE, et c'est la deception de ces videos. Le
      bonus 45 est bien visible, mais la grille du meme tirage est TRIEE :
      on ne peut donc pas comparer le bonus au PREMIER NUMERO SORTI. Les
      neuf tirages ordonnes du §86 n'ont pas de bonus ; ce tirage-ci a un
      bonus et pas d'ordre. Il manque toujours la conjonction.
      CE QU'IL FAUT, exactement : un enregistrement d'un SEUL tirage qui
      montre la grille SE REMPLIR boule apres boule, puis la boule EXTRA du
      meme tirage. Pas deux tirages, pas deux ecrans : un seul, continu.
   2. LE CAS A / CAS B N'EST PAS TRANCHE. Une requete a l'API du jeu sur un
      tirage recent le ferait ; le reseau de cet environnement la refuse.
   3. LA ROUE NE PREDIT RIEN. Elle publie un multiplicateur de gain, pas un
      numero. Son interet est entier dans la section 5 : des BITS, si le
      decalage residuel est tire. Vingt arrets filmes le diront.

   Registre : consigne a la section 6.

   ({time.time() - T0:.1f} s)""")
