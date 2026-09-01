"""h118 — le bonus est un VINGT ET UNIÈME appel, et vingt et un mots suffisent à
immuniser la plateforme contre tout test d'équidistribution.

LA QUESTION QUE LE §129 A LAISSÉE OUVERTE
==========================================
Le §129 a réfuté le modèle A du §89 — « le bonus est le premier numéro sorti » —
sur la première vidéo. Il a alors écrit ce qu'il ne pouvait pas trancher :

    « L'indice du bonus vaut 2 dans l'ordre d'émission et 10 dans le tableau
      trié. Les deux lectures restent possibles :
          bonus = ordre[j] avec j = 2   ou   bonus = trié[j] avec j = 10
      Un seul tirage ne les sépare pas — il faudrait reconstituer l'état. »

DEUX VIDÉOS DE PLUS, ET LA QUESTION SE RÈGLE SANS RIEN RECONSTITUER
====================================================================
Les deux lectures supposent toutes deux un indice CONSTANT. Trois tirages
suffisent donc, et le test est DÉTERMINISTE :

        tirage      bonus    indice ÉMISSION    indice TRIÉ
       1381278         45                  2             10
       1381481         10                 18              3
       1381483         14                  9              4

    NI L'UN NI L'AUTRE N'EST CONSTANT. Les deux lectures tombent ENSEMBLE.
    L'INDICE EST TIRÉ — donc un appel de générateur le tire, donc

        LE TIRAGE CONSOMME VINGT ET UN MOTS, PAS VINGT.

Le troisième axe du §121 — « mots par numéro » — passe de SUPPOSÉ à MESURÉ, et
le modèle B du §106, qui porte les §103, §122, §124, §126 et la borne
W >= 47 040, cesse d'être une hypothèse : c'est le seul survivant.

CE QUE CELA REND TESTABLE — ET CE QUE LA MESURE DE PUISSANCE EN DIT
====================================================================
Savoir d'où vient le rang du bonus rend enfin possible le test classique du
réseau : l'équidistribution en dimension 2 et 3, à la résolution 20 par axe.
On l'écrit, puis ON MESURE SA PUISSANCE AVANT DE LIRE L'ARCHIVE — et la mesure
renverse la section :

    au pas 1        LCG a=5 : p = 0     RANDU : p = 0     glibc : p = 5e-5
    au pas 21       LCG a=5 : p = 0,003 RANDU : p = 0,022 glibc : p = 0,058

    LES TROIS SONT ANÉANTIS AU PAS 1 ET AUCUN NE TOMBE AU PAS 21.

THÉORÈME DE L'IMMUNITÉ PAR DÉCIMATION ARITHMÉTIQUE
===================================================
La raison est élémentaire et elle vaut pour tout LCG :

    observer un mot sur sigma, c'est observer un LCG de multiplicateur a^sigma.

Le réseau de a^21 est FIN même quand celui de a est grossier — c'est exactement
le phénomène du §134 (b), où la décimation détruit la complexité linéaire, vu
de l'autre côté : ici elle détruit la STRUCTURE DE RÉSEAU.

    LA CONSOMMATION DE VINGT ET UN MOTS PAR TIRAGE EST, À ELLE SEULE, UNE
    DÉFENSE. La plateforme n'est pas protégée parce que son générateur serait
    bon, mais parce qu'elle n'en publie qu'un mot sur vingt et un.

Cela explique rétroactivement pourquoi aucun test spectral du dossier n'a jamais
rien trouvé, et cela DIT QU'IL NE FALLAIT PAS S'Y ATTENDRE.

Il TESTE l'archive — la réfutation, elle, est déterministe — et il consigne au
registre EN DÉCLARANT SA PUISSANCE NULLE sur le volet spectral.
"""

import csv
import os
import sys
import time

import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H118_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
DEC2 = (1, 2, 3, 4, 5, 6, 7, 8)
DEC3 = (1, 2, 3, 4)
K = 20


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def p_dim2(r, k):
    a, b = r[:-k], r[k:]
    o = np.bincount(a * K + b, minlength=K * K).astype(float)
    e = len(a) / (K * K)
    return float(stats.chi2.sf(((o - e) ** 2 / e).sum(), K * K - 1))


def p_dim3(r, k):
    a, b, c = r[:-2 * k], r[k:-k], r[2 * k:]
    o = np.bincount((a * K + b) * K + c, minlength=K ** 3).astype(float)
    e = len(a) / K ** 3
    return float(stats.chi2.sf(((o - e) ** 2 / e).sum(), K ** 3 - 1))


def pmin(r):
    return min(min(p_dim2(r, k) for k in DEC2), min(p_dim3(r, k) for k in DEC3))


def rangs_lcg(a, c, m, n, pas):
    x, out = 12345 % m, np.zeros(n, np.int64)
    for i in range(n):
        for _ in range(pas):
            x = (a * x + c) % m
        out[i] = min(K - 1, int(K * (x / m)))
    return out


# ==========================================================================
rule("1. LES DEUX LECTURES DU §129 TOMBENT ENSEMBLE")
# ==========================================================================

LIG, EM, TR = [], [], []
for r in csv.DictReader(open(os.path.join(os.path.dirname(ICI), "draws_ordered.csv"),
                             encoding="utf-8")):
    if not r.get("bonus"):
        continue
    o = [int(r[f"o{i}"]) for i in range(1, 21)]
    b = int(r["bonus"])
    EM.append(o.index(b))
    TR.append(sorted(o).index(b))
    LIG.append((r["id"], b, EM[-1], TR[-1]))

say(f"""   Le §129 a refute le modele A du §89, puis a ecrit ce qu'il ne pouvait pas
   trancher :

     « L'indice du bonus vaut 2 dans l'ordre d'emission et 10 dans le tableau
       trie. Les deux lectures restent possibles : bonus = ordre[j] avec j = 2,
       ou bonus = trie[j] avec j = 10. Un seul tirage ne les separe pas — il
       faudrait reconstituer l'etat. »

   LES DEUX SUPPOSENT UN INDICE CONSTANT. Trois tirages suffisent donc, et le
   test est DETERMINISTE — nul besoin de reconstituer quoi que ce soit.

   {'tirage':>9} {'bonus':>7} {'indice ÉMISSION':>17} {'indice TRIÉ':>13}""")
for tid, b, ie, it in LIG:
    say(f"   {tid:>9} {b:>7} {ie:>17} {it:>13}")

CONST_EM = len(set(EM)) == 1
CONST_TR = len(set(TR)) == 1
say(f"""
   indices d'emission distincts : {len(set(EM))} sur {len(EM)}   -> constant ? {'oui' if CONST_EM else 'NON'}
   indices tries      distincts : {len(set(TR))} sur {len(TR)}   -> constant ? {'oui' if CONST_TR else 'NON'}

     NI L'UN NI L'AUTRE. Un modele deterministe tombe sur un seul
     contre-exemple ; chacune des deux lectures en recoit DEUX.""")


# ==========================================================================
rule("2. CE QUI SURVIT : VINGT ET UN MOTS PAR TIRAGE")
# ==========================================================================

say("""   Si l'indice du bonus est TIRE, c'est qu'un appel de generateur le tire.

       LE TIRAGE CONSOMME VINGT ET UN MOTS, PAS VINGT.

     modèle                                       statut
     ---------------------------------------------------------------------
     A  (§89)   bonus = 1er numero sorti          refute au §129
     A' (§129)  bonus = ordre[j], j constant      REFUTE ICI
     B' (§129)  bonus = trie[j], j constant       REFUTE ICI
     B  (§106)  rang du bonus = floor(20·u)       SEUL SURVIVANT

   Le troisieme axe du §121 — « mots par numero » — passe de SUPPOSE a MESURE,
   et le modele B, qui porte les §103, §122, §124, §126 et la borne
   W >= 47 040, cesse d'etre une hypothese de travail.

   ET AUCUN RESULTAT NE BOUGE : les balayages du dossier ont toujours enumere
   les pas 20, 21 et 22 ; le bon pas etait dans le lot. Ce qui change n'est pas
   un resultat, c'est son STATUT.""")


# ==========================================================================
rule("3. LA MESURE DE PUISSANCE, AVANT DE LIRE L'ARCHIVE")
# ==========================================================================

say(f"""   Savoir d'ou vient le rang du bonus rend enfin possible le test classique du
   reseau : deux rangs separes de k tirages viennent de deux mots separes de
   21·k, donc on peut tester l'equidistribution en dimension 2 ({K}x{K} = {K*K}
   cases) et 3 ({K**3:,} cases).

   ON MESURE SA PUISSANCE AVANT DE LIRE L'ARCHIVE. Trois LCG dont on SAIT
   qu'ils ont un reseau grossier, observes au pas 1 puis au pas 21 :

       générateur              pas 1        pas 21     conclusion""")

PUISS, OKP = [], 0
for nom, a, c in (("LCG a=5, m=2^31", 5, 1),
                  ("RANDU a=65539", 65539, 0),
                  ("LCG glibc", 1103515245, 12345)):
    p1 = pmin(rangs_lcg(a, c, 1 << 31, 70560, 1))
    p21 = pmin(rangs_lcg(a, c, 1 << 31, 70560, 21))
    tue = p1 < 1e-4
    survit = p21 > 1e-3
    OKP += tue and survit
    PUISS.append((nom, p1, p21))
    say(f"   {nom:>22} {p1:>12.3g} {p21:>13.3g}     "
        f"{'anéanti au pas 1, INTACT au pas 21' if tue and survit else 'autre'}")

p_h = pmin(np.random.default_rng(20260901).integers(0, K, 70560).astype(np.int64))
say(f"""   {'hasard vrai':>22} {'':>12} {p_h:>13.3g}     temoin negatif

   {OKP}/3 : LES TROIS SONT ANEANTIS AU PAS 1 ET AUCUN NE TOMBE AU PAS 21.

     LE TEST N'A AUCUNE PUISSANCE AU PAS DE LA PLATEFORME. Il ne faut donc PAS
     lire son resultat sur l'archive comme une exculpation.""")


# ==========================================================================
rule("4. LE THÉORÈME DE L'IMMUNITÉ PAR DÉCIMATION ARITHMÉTIQUE")
# ==========================================================================

say("""   La raison est elementaire, et elle vaut pour tout LCG :

       observer un mot sur sigma, c'est observer un LCG de multiplicateur
       a^sigma mod m.

   Le reseau de a^21 est FIN meme quand celui de a est grossier. C'est
   exactement le phenomene du §134 (b) — la decimation detruit la complexite
   lineaire — vu de l'autre cote : ici elle detruit la STRUCTURE DE RESEAU.

     LA CONSOMMATION DE VINGT ET UN MOTS PAR TIRAGE EST, A ELLE SEULE, UNE
     DEFENSE. La plateforme n'est pas protegee parce que son generateur serait
     bon, mais parce qu'elle n'en publie qu'un mot sur vingt et un.

   Cela explique retroactivement pourquoi aucun test spectral du dossier n'a
   jamais rien trouve, ET DIT QU'IL NE FALLAIT PAS S'Y ATTENDRE. Ce n'est pas
   une absence de preuve : c'est une preuve d'absence de puissance.

   COROLLAIRE POUR LA SUITE. Un test spectral n'a de sens ici que sur des mots
   CONSECUTIFS — donc uniquement sur les tirages ORDONNES, ou les vingt mots
   d'un meme tirage sont lus a la file. Douze tirages filmes donnent 252 mots
   consecutifs par blocs de 21 : c'est peu, mais c'est le seul endroit ou le
   test a de la puissance.""")


# ==========================================================================
rule("5. L'ARCHIVE, LUE EN SACHANT QUE LE TEST NE PEUT RIEN")
# ==========================================================================

ARCH = lab.load()
NUM = np.sort(np.asarray(ARCH.nums).astype(np.int64), axis=1)
BON = np.asarray(ARCH.bonus).astype(np.int64)
RANG = np.argmax(NUM == BON[:, None], axis=1).astype(np.int64)
NA = len(RANG)

O1 = np.bincount(RANG, minlength=K).astype(float)
X1 = float(((O1 - NA / K) ** 2 / (NA / K)).sum())
P1 = float(stats.chi2.sf(X1, K - 1))
PA2 = [p_dim2(RANG, k) for k in DEC2]
PA3 = [p_dim3(RANG, k) for k in DEC3]
PMINA = min(PA2 + PA3)
NT = len(PA2) + len(PA3) + 1
PHOLM = min(1.0, PMINA * NT)

say(f"""   {NA:,} rangs de bonus.

       dimension 1, {K-1} ddl                 khi2 = {X1:>8.1f}   p = {P1:.3f}
       dimension 2, {K*K-1} ddl, 8 décalages   p min = {min(PA2):.3f}
       dimension 3, {K**3-1:,} ddl, 4 décalages  p min = {min(PA3):.3f}

   p minimal sur les {NT} tests : {PMINA:.3f} ; apres Holm : {PHOLM:.3f}. Aucun ecart.

     ET CE RESULTAT NE VAUT RIEN CONTRE UN LCG, la section 3 l'ayant mesure.
     Il vaut seulement comme controle de coherence du modele B : si le rang du
     bonus n'etait PAS floor(20·u) d'un mot, rien ne garantissait qu'il soit
     uniforme ni independant, et il l'est.""")


# ==========================================================================
rule("6. CONSIGNATION")
# ==========================================================================

STAT = (0 if CONST_EM else 1) + (0 if CONST_TR else 1)

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h118.bonus_vingt_et_unieme",
        "Les deux lectures que le §129 laissait ouvertes — « bonus = ordre[j] "
        "avec j constant » et « bonus = trie[j] avec j constant » — sont toutes "
        "DEUX fausses : sur les trois tirages filmes portant un bonus, l'indice "
        "du bonus n'est constant ni dans l'ordre d'emission ni dans le tableau "
        "trie. Il s'ensuit que l'indice est TIRE, donc qu'un appel de generateur "
        "le tire, donc que le tirage consomme VINGT ET UN mots et non vingt, et "
        "que le modele B du §106 est le seul survivant",
        "nombre de lectures a indice constant refutees, sur les deux que le §129 "
        "laissait ouvertes. La refutation est DETERMINISTE : un seul indice "
        "different suffit, et il y en a deux pour chaque lecture",
        "sous une lecture a indice constant, les trois tirages donneraient trois "
        "fois le meme indice. Aucune statistique n'est requise",
        "conforme si les deux lectures a indice constant sont refutees", track="B")
    tok["m_extra"] = 0
    lab.record(
        tok, float(STAT), p=1.0,
        verdict="conforme" if STAT == 2 else "NON REFUTE",
        power_at=("la refutation est deterministe et le temoin l'est aussi : si "
                  "l'indice etait constant, les trois tirages donneraient trois "
                  "fois la meme valeur, et ils donnent 2/18/9 en emission et "
                  "10/3/4 en tri. Aucune puissance statistique n'est en jeu"),
        notes=(f"LE §129 DISAIT QU'IL FAUDRAIT RECONSTITUER L'ETAT POUR TRANCHER. "
               f"Deux videos de plus le font sans rien reconstituer. Le troisieme "
               f"axe du §121 (« mots par numero ») passe de suppose a MESURE : "
               f"21. Aucun resultat du dossier ne change — les balayages "
               f"enumeraient deja 20 a 22 — mais le modele B, qui porte la borne "
               f"W >= 47 040, cesse d'etre une hypothese. "
               f"VOLET SPECTRAL, DECLARE SANS PUISSANCE ET DONC NON CONSIGNE "
               f"COMME TEST : savoir d'ou vient le rang rend possible "
               f"l'equidistribution en dimensions 2 et 3, mais la mesure de "
               f"puissance la detruit — LCG a=5, RANDU et glibc sont aneantis au "
               f"pas 1 (p = 0, 0, 5e-5) et AUCUN ne tombe au pas 21 (p = 3e-3, "
               f"2e-2, 6e-2), parce qu'observer un mot sur sigma revient a "
               f"observer le multiplicateur a^sigma, de reseau fin. C'est le "
               f"§134 (b) vu de l'autre cote. La consommation de 21 mots par "
               f"tirage est a elle seule une defense, et cela explique "
               f"retroactivement que nul test spectral du dossier n'ait rien "
               f"trouve. Sur l'archive, {NA:,} rangs, 13 tests : p min {PMINA:.3f}, "
               f"Holm {PHOLM:.3f} — controle de coherence du modele B, rien de plus."))
    h = lab.holm()
    say(f"   consigne : h118.bonus_vingt_et_unieme   {STAT}/2 lectures refutees")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")

say(f"\n   ({time.time() - T0:.1f} s)")
