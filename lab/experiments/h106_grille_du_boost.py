"""h106 — la loi du boost vit sur une grille de 1/80, et 80 est la taille du vivier.

CE QUE LE §92 A ÉTABLI, ET CE QU'IL A LAISSÉ OUVERT
====================================================
Le §92 a filmé la roue : sept secteurs ÉGAUX à 360/7 près, et une loi publiée
qui n'est pas uniforme (khi2 = 35 173 contre un seuil de 11,07). Sa conclusion
tient et elle est forte :

    « L'angle d'arrêt n'est pas la variable publiée. Le résultat est tiré
      d'abord, d'une loi PONDÉRÉE, et l'angle est calculé à partir de lui. »

Il a aussi noté que quatre des cinq seuils cumulés sont « ronds à moins de
0,6 σ ». Mais RONDS SUR QUELLE GRILLE ? Il ne le dit pas, et c'est là qu'est la
structure.

LA MESURE
==========
    boost      1      2      3     4     5    10
    secteurs  41     19     12     4     2     2      (somme = 80)

    khi2 = 0,66 pour 5 degrés de liberté, loi ENTIÈREMENT SPÉCIFIÉE, aucun
    paramètre ajusté.

CE QUE LE BALAYAGE PROUVE, ET CE QU'IL NE PROUVE PAS
=====================================================
Il faut être précis ici, parce que la tentation de sur-lire est forte.

    CE QU'IL PROUVE. Parmi les 95 dénominateurs de 6 à 100, DEUX SEULEMENT
    portent la loi sans être rejetés : 79 et 80. Les 93 autres tombent, et
    la grille deux fois plus grossière — 1/40 — tombe à khi2 = 61,5. Cela,
    c'est un résultat : la loi n'est PAS sur une grille grossière.

    CE QU'IL NE PROUVE PAS. Le minimum du khi2 sur D n'est PAS une preuve.
    Témoin : en plantant une vraie loi 1/80 et en tirant 70 560 boosts, le
    minimum ne retombe sur 80 que dans 4 % des cas — médiane 274. Une grille
    assez fine suit le bruit d'échantillonnage mieux que la vraie. Le minimum
    observé en D = 80 sur l'archive est donc une COÏNCIDENCE AGRÉABLE, pas un
    argument, et il n'est pas compté comme tel.

CE QUI DÉPARTAGE 79 DE 80, ET CE N'EST PAS UNE FRÉQUENCE
=========================================================
Deux faits, tous deux extérieurs au khi2 :

1. 80 EST LA TAILLE DU VIVIER. Le jeu tire vingt numéros sur quatre-vingts.
   Une table de 80 entrées réutilise le modulus déjà présent dans le code.
   79 est premier et ne désigne rien.

2. LA CLÔTURE À SEPT SECTEURS. Le §92 a filmé SEPT valeurs (le ×1,5 est fondu
   dans le seau « 1 » de l'archive). Sur la grille de 1/80, le seau de 41 se
   scinde en 39 + 2, et les sept comptes deviennent

       ×1  39     ×1,5  2     ×2  19     ×3  12     ×4  4     ×5  2     ×10  2

   — somme 80, et LES TROIS VALEURS LES PLUS RARES ONT EXACTEMENT DEUX
   SECTEURS CHACUNE. Cette lecture PRÉDIT l'espérance du multiplicateur :

       E = 162/80 = 2,025      mesurée (corrigée du seau fondu) : 2,0242 ± 0,0062

   soit 0,13 σ. Le §92 estimait P(×1,5) = 0,0234 ± 0,0123 par un tout autre
   chemin ; 2/80 = 0,025 y tombe à 0,13 σ également.

CE QUE CELA RAPPORTE
=====================
Les bornes deviennent des rationnels EXACTS, ce qui supprime l'élargissement de
4 σ du §118 : le rendement du canal boost passe de 0,762 à 1,150 bit exact par
tirage.

ET CE QUE CELA NE DONNE PAS. Les fréquences donnent les LONGUEURS des plages,
jamais leurs POSITIONS dans la table. La disposition reste invisible.

Il TESTE l'archive : il consigne au registre.
"""

import os
import sys
import time

import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H106_DRY") == "1"
DMAX = 300                                # au-dela, toute grille ajuste
NREP = 40 if DRY else 200
POOL = 80


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def loi_sur_grille(D, p):
    """La loi de grille 1/D la plus proche de p, somme forcée à D."""
    k = np.round(np.asarray(p) * D).astype(int)
    k[k < 1] = 1
    while k.sum() != D:
        d = 1 if k.sum() < D else -1
        cand = [(abs(p[i] - (k[i] + d) / D) - abs(p[i] - k[i] / D), i)
                for i in range(len(k)) if k[i] + d > 0]
        k[min(cand)[1]] += d
    return k


def khi2(obs, k, D):
    att = obs.sum() * np.asarray(k) / D
    return float(((obs - att) ** 2 / att).sum())


def profil(obs, dmax=DMAX):
    p = obs / obs.sum()
    return [(khi2(obs, loi_sur_grille(D, p), D), D)
            for D in range(len(obs), dmax + 1)]


def prefixe_exact(a, b, K, jmax=24):
    """Bits de poids fort determines par u dans [a/K, b/K) — entiers exacts."""
    j = 0
    while j < jmax and (a * (1 << (j + 1))) // K == (b * (1 << (j + 1)) - 1) // K:
        j += 1
    return j


def prefixe_flottant(lo, hi, jmax=24):
    """La meme chose sur un intervalle REEL elargi — le regime du §118."""
    j = 0
    while j < jmax:
        m = 1 << (j + 1)
        if int(np.floor(lo * m)) != int(np.ceil(hi * m)) - 1:
            break
        j += 1
    return j


# ==========================================================================
rule("1. CE QUE LE §92 A LAISSÉ OUVERT")
# ==========================================================================

ARCH = lab.load()
BO = np.asarray(ARCH.boost).astype(np.int64)
VAL, OBS = np.unique(BO, return_counts=True)
N = int(OBS.sum())
P = OBS / N
FCUM = np.cumsum(P)
SEUIL = float(stats.chi2.ppf(0.95, len(VAL) - 1))

say(f"""   Le §92 a filme la roue : SEPT SECTEURS EGAUX a 360/7 pres, et une loi
   publiee qui n'est pas uniforme. Sa conclusion tient : l'angle d'arret n'est
   pas la variable publiee, le resultat est tire d'abord d'une loi PONDEREE.

   Il note aussi que quatre des cinq seuils cumules sont « ronds a moins de
   0,6 sigma ». MAIS RONDS SUR QUELLE GRILLE ? Il ne le dit pas.

   {'boost':>7} {'observé':>9} {'fréquence':>11} {'F cumulé':>11}""")
for v, o, pi, fi in zip(VAL, OBS, P, FCUM):
    say(f"   {v:>7} {o:>9,} {pi:>11.6f} {fi:>11.6f}")


# ==========================================================================
rule("2. CE QUE LE BALAYAGE PROUVE — ET CE QU'IL NE PROUVE PAS")
# ==========================================================================

K80 = loi_sur_grille(80, P)
K40 = loi_sur_grille(40, P)
C80, C40 = khi2(OBS, K80, 80), khi2(OBS, K40, 40)
SURV = [D for D in range(len(VAL), 101) if khi2(OBS, loi_sur_grille(D, P), D) < SEUIL]
LARGE = sum(1 for c, _ in profil(OBS, 1000) if c < SEUIL)

say(f"""   CE QUE LE BALAYAGE PROUVE. On teste, pour chaque D, la loi de grille 1/D la
   plus proche — ENTIEREMENT SPECIFIEE, aucun parametre libre. Parmi les
   {101-len(VAL)} denominateurs de {len(VAL)} a 100, DEUX SEULEMENT ne sont pas rejetes :

       {SURV}

   Les {101-len(VAL)-len(SURV)} autres tombent, et la grille deux fois plus grossiere avec eux :

     grille 1/40  {list(int(x) for x in K40)}   khi2 = {C40:.1f}   REJETEE (seuil {SEUIL:.2f})
     grille 1/80  {list(int(x) for x in K80)}   khi2 = {C80:.2f}   p = {1-stats.chi2.cdf(C80,5):.4f}

   Ce qui tranche est le seul seuil que le §92 trouvait NON rond : F(1) = 41/80,
   et 41 est IMPAIR — aucune grille 1/40 ne le porte.

   {'seuil cumulé':>14} {'observé':>10} {'exact':>10} {'écart σ':>9}""")
for i in range(len(VAL) - 1):
    ex = K80[:i + 1].sum() / 80
    sg = np.sqrt(FCUM[i] * (1 - FCUM[i]) / N)
    say(f"   {str(int(K80[:i+1].sum())) + '/80':>14} {FCUM[i]:>10.6f} {ex:>10.6f} "
        f"{abs(FCUM[i]-ex)/sg:>9.2f}")

# --- ce que le balayage NE prouve pas, et on le mesure ---
rng = np.random.default_rng(20260902)
ARG, CH = [], []
for _ in range(NREP):
    ech = rng.multinomial(N, K80 / 80)
    ARG.append(min(profil(ech))[1])
    CH.append(khi2(ech, K80, 80))
ARG = np.array(ARG)
TAUX = float((ARG % 80 == 0).mean())
ARGV = min(profil(OBS))[1]

say(f"""
   CE QUE LE BALAYAGE NE PROUVE PAS, ET IL FAUT LE DIRE AVANT DE S'EN SERVIR.
   Sur D <= 1000, {LARGE} denominateurs passent le seuil : une grille assez FINE
   ajuste toujours. On pourrait croire que le MINIMUM tranche — il tombe en
   D = {ARGV} sur l'archive. IL NE TRANCHE PAS :

     on plante une VRAIE loi 1/80, on tire {N:,} boosts, on redemande le minimum
     -> il retombe sur un multiple de 80 dans {100*TAUX:.0f} % des cas seulement, mediane {np.median(ARG):.0f}

   Une grille fine suit le BRUIT d'echantillonnage mieux que la vraie grille.
   Le minimum observe en D = {ARGV} est donc une coincidence agreable, pas un
   argument, et il n'est pas compte comme tel.

   Le khi2 en D = 80, lui, est bien calibre : moyenne {np.mean(CH):.2f} sur les replicats
   plantes, pour une esperance theorique de {len(VAL)-1}.""")


# ==========================================================================
rule("3. CE QUI DÉPARTAGE 79 DE 80, ET CE N'EST PAS UNE FRÉQUENCE")
# ==========================================================================

SEPT = [("×1", 39), ("×1,5", 2), ("×2", 19), ("×3", 12),
        ("×4", 4), ("×5", 2), ("×10", 2)]
MULTI = {"×1": 1.0, "×1,5": 1.5, "×2": 2.0, "×3": 3.0,
         "×4": 4.0, "×5": 5.0, "×10": 10.0}
EPRED = sum(MULTI[n] * k for n, k in SEPT) / 80
EBUC = float((VAL * OBS).sum()) / N
SDE = float(np.sqrt(((VAL - EBUC) ** 2 * OBS).sum() / N / N))
EVRAI = EBUC + 0.5 * 2 / 80

say(f"""   Le khi2 ne separe pas 79 de 80 : les deux ajustent. Ce qui les separe est
   exterieur aux frequences, et il y a deux faits.

   1. 80 EST LA TAILLE DU VIVIER. Le jeu tire vingt numeros sur QUATRE-VINGTS.
      Une table de 80 entrees reutilise un modulus deja present dans le code.
      79 est premier et ne designe rien.

   2. LA CLOTURE A SEPT SECTEURS. Le §92 a FILME sept valeurs — le ×1,5 est
      fondu dans le seau « 1 » de l'archive. Sur la grille de 1/80 le seau de
      41 se scinde en 39 + 2, et les sept comptes se ferment :

     {'valeur':>8} {'secteurs':>10} {'probabilité':>13}""")
for n, k in SEPT:
    say(f"     {n:>8} {k:>10} {k/80:>13.4f}")
say(f"""     {'somme':>8} {sum(k for _, k in SEPT):>10}

      LES TROIS VALEURS LES PLUS RARES ONT EXACTEMENT DEUX SECTEURS CHACUNE.

   ET CETTE LECTURE PREDIT UNE QUANTITE QU'ELLE N'A PAS AJUSTEE :

     E[multiplicateur] predit    = 162/80 = {EPRED}
     mesure sur les seaux        = {EBUC:.4f} ± {SDE:.4f}
     corrigee du seau fondu      = {EVRAI:.4f}          ecart : {abs(EVRAI-EPRED)/SDE:.2f} sigma

   Le §92 estimait P(×1,5) = 0,0234 ± 0,0123 par un tout autre chemin ;
   2/80 = 0,025 y tombe a {abs(0.025-0.0234)/0.0123:.2f} sigma. Deux estimations independantes, une
   seule grille.""")


# ==========================================================================
rule("4. CE QUE CELA RAPPORTE EN BITS")
# ==========================================================================

bornes, acc = [], 0
for k in K80:
    bornes.append((acc, acc + int(k)))
    acc += int(k)
sig = np.sqrt(FCUM * (1 - FCUM) / N)

say(f"""   Le §118 estimait les bornes du boost puis les elargissait de 4 sigma — ce
   qui coute des bits et ne peut pas en inventer. Avec des bornes k/80 EXACTES,
   l'elargissement disparait.

   {'boost':>6} {'secteurs':>9} {'intervalle exact':>20} {'bits exacts':>12} {'§118 (4σ)':>11}""")
GEX, G118 = 0.0, 0.0
for i, (v, (a, b)) in enumerate(zip(VAL, bornes)):
    je = prefixe_exact(a, b, POOL)
    lo = 0.0 if i == 0 else FCUM[i - 1] - 4 * sig[i - 1]
    hi = 1.0 if i == len(VAL) - 1 else FCUM[i] + 4 * sig[i]
    jf = prefixe_flottant(max(0.0, lo), min(1.0, hi))
    GEX += P[i] * je
    G118 += P[i] * jf
    say(f"   {v:>6} {int(K80[i]):>9} {f'[{a}/80, {b}/80)':>20} {je:>12} {jf:>11}")

say(f"""
   rendement exact  : {GEX:.3f} bit par tirage
   rendement §118   : {G118:.3f} bit par tirage       soit {100*(GEX/G118-1):+.0f} %

   ET LE THEOREME DU CONTENU (§94) S'APPLIQUE AU MOT DU BOOST : comme 16 divise
   80, sous echantillonneur modulo le secteur donne les quatre bits BAS du mot
   — pourvu qu'on sache QUEL secteur.

   LA LIMITE. Les frequences donnent les LONGUEURS des six plages, jamais leurs
   POSITIONS. Le tableau ci-dessus suppose la disposition CUMULEE, celle qu'un
   `cumsum` + `searchsorted` produit ; c'est l'hypothese que le §92 avait deja
   signalee sans pouvoir la lever, et elle n'est pas levee ici non plus.""")


# ==========================================================================
rule("5. CE QUE CELA REND TESTABLE SUR LA VIDÉO")
# ==========================================================================

say(f"""   Le §92 laissait une question ouverte : filmer vingt arrets de roue et
   mesurer la fraction dans le secteur — constante, ou repartie sur [0, 1) ?

   LA GRILLE DE 1/80 REND CETTE QUESTION QUANTITATIVE. Si le boost est tire
   comme un secteur sur 80 et que l'animation calcule l'angle a partir du
   SECTEUR, la fraction residuelle ne prend pas une valeur continue : elle
   prend AU PLUS k_v valeurs distinctes pour la valeur v.

     ×5 et ×10  :  2 angles residuels distincts, pas plus
     ×1,5       :  2
     ×4         :  4
     ×3         :  12

   C'est FALSIFIABLE a peu de frais : trois arrets sur ×10 donnant trois
   fractions differentes la refutent. Et si elle tient, filmer un ×10 identifie
   le secteur parmi 80 — {np.log2(80):.2f} bits EXACTS par tirage filme.

   Trois lectures, et une seule video les separe :
     angle CONSTANT par valeur    -> la roue ne publie que le boost
     angle a k_v valeurs          -> la roue publie le SECTEUR ({np.log2(80):.2f} bits)
     angle CONTINU sur le secteur -> la roue publie les bits de poids fort du
                                     mot brut (§87, plafond 7,00 bits)""")


# ==========================================================================
rule("6. CONSIGNATION")
# ==========================================================================

CONFORME = C80 < SEUIL and all(
    khi2(OBS, loi_sur_grille(D, P), D) > SEUIL for D in range(len(VAL), 79))

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h106.grille_du_boost",
        "La loi du boost est portee par la grille 1/80 — (41, 19, 12, 4, 2, 2) "
        "secteurs — et par aucune grille strictement plus grossiere. 80 est la "
        "TAILLE DU VIVIER : l'echantillonnage du boost partage donc le modulus "
        "K = 80 de celui des numeros. Le §92 avait note quatre seuils « ronds » "
        "sans dire sur quelle grille",
        "khi2 d'ajustement d'une multinomiale a six cases ENTIEREMENT SPECIFIEE "
        "(aucun parametre ajuste), 5 ddl, en D = 80 ; et rejet exige de tous les "
        "D de 6 a 78. Le denominateur a ete trouve par balayage de D = 6 a 300, "
        "dont la multiplicite est declaree en m_extra. Le MINIMUM du khi2 sur D "
        "n'est PAS retenu comme statistique : un temoin plante montre qu'il ne "
        "retrouve la vraie grille que dans 4 % des cas",
        "loi du khi2 a 5 ddl, exacte pour une multinomiale entierement "
        "specifiee ; seuil de 5 % a 11,07",
        "conforme si la grille 1/80 n'est pas rejetee ET si toutes les grilles "
        "de 6 a 78 le sont", track="A")
    tok["m_extra"] = DMAX - len(VAL)
    lab.record(
        tok, C80, p=float(1 - stats.chi2.cdf(C80, len(VAL) - 1)),
        verdict="conforme" if CONFORME else "ANOMALIE",
        power_at=(f"le khi2 en D = 80 est calibre : moyenne {np.mean(CH):.2f} sur {NREP} "
                  f"replicats d'une loi 1/80 plantee, pour une esperance de 5. "
                  f"Et le test a de la puissance contre les grilles grossieres : "
                  f"{101-len(VAL)-len(SURV)} des {101-len(VAL)} denominateurs de 6 a 100 sont rejetes, dont "
                  f"1/40 a khi2 = {C40:.1f}"),
        notes=(f"Parmi D = 6..100, seuls {SURV} ne sont pas rejetes. Le khi2 ne "
               f"separe donc pas 79 de 80 ; ce qui les separe est exterieur aux "
               f"frequences. (1) 80 est la taille du vivier, 79 est premier et "
               f"ne designe rien. (2) La CLOTURE A SEPT SECTEURS : le §92 a "
               f"filme sept valeurs, le seau de 41 se scinde en 39 + 2, et les "
               f"sept comptes 39/2/19/12/4/2/2 somment a 80 avec les trois "
               f"valeurs les plus rares a deux secteurs chacune. Cette lecture "
               f"PREDIT E[multiplicateur] = 162/80 = {EPRED} ; la mesure corrigee du "
               f"seau fondu vaut {EVRAI:.4f} ± {SDE:.4f}, soit {abs(EVRAI-EPRED)/SDE:.2f} sigma. "
               f"ATTENTION : le MINIMUM du khi2 sur D tombe en {ARGV} sur l'archive, "
               f"mais ce n'est PAS un argument — sur une loi 1/80 plantee il ne "
               f"retrouve un multiple de 80 que dans {100*TAUX:.0f} % des cas. Consequence "
               f"utile : les bornes deviennent des rationnels exacts, ce qui "
               f"supprime l'elargissement de 4 sigma du §118 et porte le "
               f"rendement du canal boost de {G118:.3f} a {GEX:.3f} bit exact par tirage. "
               f"Limite : les frequences donnent les LONGUEURS des plages, "
               f"jamais leurs POSITIONS."))
    h = lab.holm()
    say(f"   consigne : h106.grille_du_boost   khi2 = {C80:.2f}   "
        f"verdict {'conforme' if CONFORME else 'ANOMALIE'}")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")

say(f"\n   ({time.time() - T0:.1f} s)")
