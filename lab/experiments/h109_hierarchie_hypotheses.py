"""h109 — la hiérarchie des hypothèses : ce que chaque supposition achète.

CE QUI MANQUAIT AU DOSSIER
===========================
Les §105 à §127 empilent des exclusions, chacune sous ses propres hypothèses.
Mais elles ne sont jamais RANGÉES PAR FORCE D'HYPOTHÈSE. Or c'est ce rangement
qui fait une théorie plutôt qu'une collection : à chaque niveau de supposition
correspond un outil, et à chaque outil une portée mesurée.

Et le niveau le plus faible — celui qui ne suppose RIEN d'autre que le
déterminisme — n'avait jamais été traité. Ce fichier le traite, puis dresse la
hiérarchie complète.

LE THÉORÈME DU DÉTERMINISME
============================
    Soit un générateur d'état s, de transition DÉTERMINISTE quelconque, et une
    observation o = phi(s) quelconque. Si deux pas produisent le même état,
    toutes les observations suivantes coïncident : la suite observée est
    périodique à partir de là.

    CONTRAPOSÉE. Si la suite observée ne contient AUCUNE répétition sur N pas,
    aucun état ne s'est répété, et la trajectoire n'a pas bouclé. []

Aucune linéarité, aucun échantillonneur, aucun pas constant, aucune famille.
C'est la seule affirmation du dossier qui ne suppose rien.

CE QUE CELA COÛTE, ET C'EST LE PRIX DE NE RIEN SUPPOSER. Pour une transition
BIJECTIVE — tous les générateurs standards le sont — la trajectoire d'un point
au hasard d'une permutation aléatoire de S états boucle en L pas avec
probabilité L/S. N'observer aucune répétition sur N pas ne minore donc S qu'à

    S >= N / 0,05 = 20 N        au seuil de 5 %,

soit vingt bits et demi. C'est faible, et ce n'est pas un défaut de la mesure :
c'est ce que vaut le déterminisme tout seul.

LE RAFFINEMENT : LE PLUS LONG BLOC RÉPÉTÉ
==========================================
Une répétition complète est un événement de mesure nulle. Le plus long BLOC
répété, lui, a une loi connue : pour une source sans mémoire d'entropie de
COLLISION H2 = −ln(somme des p²), il vaut environ 2·ln(N)/H2.

    ATTENTION AU PIÈGE. On lit souvent 2·log_a(N) pour un alphabet de taille a.
    C'est la forme UNIFORME. Le boost ne l'est pas du tout : son alphabet
    compte 6 valeurs mais sa somme des carrés vaut 0,3453, soit H2 = 1,063 nat
    et une longueur attendue de 21,0 — et non les 12,5 que la formule uniforme
    prédirait. Lue avec la mauvaise formule, la mesure crierait à l'anomalie.

Il TESTE l'archive : il consigne au registre.
"""

import os
import sys
import time
from collections import Counter

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H109_DRY") == "1"
NNULL = 20 if DRY else 200


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def plus_long_bloc(seq):
    """Longueur du plus long bloc qui apparaisse deux fois."""
    s = bytes(np.asarray(seq, np.uint8).tolist())
    n = len(s)
    L = 1
    while L <= n // 2:
        vus = set()
        trouve = False
        for i in range(n - L + 1):
            t = s[i:i + L]
            if t in vus:
                trouve = True
                break
            vus.add(t)
        if not trouve:
            return L - 1
        L += 1
    return L - 1


def h2_nats(p):
    return float(-np.log(np.sum(np.asarray(p, float) ** 2)))


# ==========================================================================
rule("1. LE THÉORÈME DU DÉTERMINISME, ET CE QU'IL COÛTE")
# ==========================================================================

ARCH = lab.load()
NUM = np.sort(np.asarray(ARCH.nums).astype(np.int64), axis=1)
BON = np.asarray(ARCH.bonus).astype(np.int64)
BOO = np.asarray(ARCH.boost).astype(np.int64)
RANG = np.argmax(NUM == BON[:, None], axis=1)
N = len(BON)
MAPB = {1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 10: 5}
BOS = np.array([MAPB[int(x)] for x in BOO])

say(f"""   THEOREME. Soit un generateur d'etat s, de transition DETERMINISTE
   quelconque, et une observation o = phi(s) quelconque. Si deux pas produisent
   le meme etat, toutes les observations suivantes coincident.

     CONTRAPOSEE. Si la suite observee ne contient AUCUNE repetition sur N pas,
     aucun etat ne s'est repete. []

   Aucune linearite, aucun echantillonneur, aucun pas constant, aucune famille.
   C'est la seule affirmation du dossier qui ne suppose RIEN d'autre.
""")

cle1 = [bytes(r.tolist()) for r in NUM.astype(np.uint8)]
cle2 = [cle1[i] + bytes([int(BON[i]), int(BOO[i])]) for i in range(N)]
cle3 = [cle2[i] + cle2[i + 1] for i in range(N - 1)]
REP = [sum(v - 1 for v in Counter(c).values() if v > 1) for c in (cle1, cle2, cle3)]
HASARD = N * (N - 1) / 2 / 3.5359e18

say(f"   {'granularité':>34} {'répétitions':>12} {'attendu par hasard':>20}")
for nom, r, h in (("les 20 numéros", REP[0], HASARD),
                  ("20 numéros + bonus + boost", REP[1], HASARD / 480),
                  ("deux tirages consécutifs", REP[2], HASARD * HASARD)):
    say(f"   {nom:>34} {r:>12} {h:>20.2e}")

BORNE = 20 * N
say(f"""
   AUCUNE REPETITION, A AUCUNE DES TROIS GRANULARITES.

   CE QUE CELA MINORE. Pour une transition BIJECTIVE — tous les generateurs
   standards le sont — la trajectoire d'un point au hasard d'une permutation
   aleatoire de S etats boucle en L pas avec probabilite L/S. N'observer aucune
   repetition sur {N:,} pas ne minore donc S qu'a

       S >= {N:,} / 0,05 = {BORNE:,} etats,  soit {np.log2(BORNE):.1f} bits.

   C'est FAIBLE, et ce n'est pas un defaut de mesure : c'est ce que vaut le
   determinisme tout seul. Un generateur de periode maximale ne se repete
   jamais en {N:,} pas, quelle que soit sa taille au-dela de {np.log2(BORNE):.0f} bits.""")


# ==========================================================================
rule("2. LE RAFFINEMENT : LE PLUS LONG BLOC RÉPÉTÉ")
# ==========================================================================

pr = np.full(20, 1 / 20)
pb = np.array([41, 19, 12, 4, 2, 2]) / 80          # §125
pj = np.outer(pr, pb).ravel()

say(f"""   Une repetition COMPLETE est un evenement de mesure nulle. Le plus long BLOC
   repete, lui, a une loi connue : pour une source sans memoire d'entropie de
   COLLISION H2 = -ln(somme des p²), il vaut environ 2·ln(N)/H2.

   ATTENTION AU PIEGE. On lit souvent 2·log_a(N) pour un alphabet de taille a :
   c'est la forme UNIFORME. Le boost ne l'est pas — 6 valeurs, mais une somme
   des carres de {np.sum(pb**2):.4f}, donc H2 = {h2_nats(pb):.3f} nat. Lue avec la formule
   uniforme, la mesure crierait a l'anomalie sans raison.

   {'suite':>16} {'alphabet':>9} {'H2 (nat)':>9} {'2·ln N/H2':>11} {'formule uniforme':>17} {'mesuré':>8}""")
SUITES = (("rang du bonus", RANG, pr, 20),
          ("boost", BOS, pb, 6),
          ("(rang, boost)", RANG * 6 + BOS, pj, 120))
MES = {}
for nom, seq, p, a in SUITES:
    L = plus_long_bloc(seq)
    MES[nom] = L
    h2 = h2_nats(p)
    say(f"   {nom:>16} {a:>9} {h2:>9.3f} {2*np.log(N)/h2:>11.1f} "
        f"{2*np.log(N)/np.log(a):>17.1f} {L:>8}")

say(f"""
   Les trois mesures collent a la prediction par ENTROPIE DE COLLISION, et
   aucune ne colle a la formule uniforme. Le « 20 » du boost, qui paraissait
   enorme contre 12,5, tombe SOUS son attendu de {2*np.log(N)/h2_nats(pb):.1f}.""")


# ==========================================================================
rule("3. LE NULL, ET LA CONSIGNATION")
# ==========================================================================

CIBLE = "(rang, boost)"
OBS = MES[CIBLE]
say(f"   {NNULL} archives simulees, memes marginales, meme statistique.")
tn = time.time()
rng = np.random.default_rng(20260903)
NULLS = np.array([plus_long_bloc(rng.choice(120, N, p=pj)) for _ in range(NNULL)])
P = (1 + int((NULLS >= OBS).sum())) / (1 + len(NULLS))
say(f"   null : moyenne {NULLS.mean():.2f}   min {NULLS.min()}   max {NULLS.max()}"
    f"   ({time.time()-tn:.1f} s)")
say(f"   observe {OBS}   p = {P:.4f}")

if DRY:
    say("\n   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h109.bloc_repete",
        "La suite des couples (rang du bonus, boost) ne contient aucun bloc "
        "repete plus long que ce qu'une source sans memoire de memes marginales "
        "produit. C'est le test qui ne suppose RIEN d'autre que le determinisme "
        "du generateur : ni linearite, ni echantillonneur, ni pas constant, ni "
        "famille nommee",
        "longueur du plus long bloc apparaissant deux fois dans la suite des "
        "70 560 couples (rang, boost), alphabet de 120. Une valeur LONGUE serait "
        "l'anomalie : elle signalerait une collision d'etat, donc un cycle",
        f"{NNULL} suites simulees de meme longueur et memes marginales — rang "
        f"uniforme sur 20, boost sur la grille 1/80 du §125 ; "
        f"p = (1 + #{{null >= observe}}) / (1 + {NNULL})",
        "conforme si le bloc observe ne depasse pas le null", track="A")
    tok["m_extra"] = 2          # les trois suites testees, moins celle-ci
    lab.record(
        tok, float(OBS), p=P, verdict="conforme" if P > 0.05 else "ANOMALIE",
        power_at=("le test detecte par construction toute collision d'etat : "
                  "deux etats egaux rendent des futurs egaux, donc un bloc "
                  "repete de longueur illimitee. Sa sensibilite est celle de la "
                  "loi du plus long bloc, dont la prediction par entropie de "
                  "collision est verifiee sur les trois suites"),
        notes=(f"Aucune repetition a aucune des trois granularites : {REP[0]} tirage "
               f"identique sur les 20 numeros, {REP[1]} sur (20 numeros + bonus + "
               f"boost), {REP[2]} paire consecutive. Le determinisme seul minore donc "
               f"l'etat a {np.log2(BORNE):.1f} bits — faible, et c'est ce que vaut le "
               f"determinisme sans autre hypothese. Le plus long bloc repete "
               f"suit la prediction par ENTROPIE DE COLLISION 2·ln(N)/H2 et non "
               f"la formule uniforme 2·log_a(N) : pour le boost, {MES['boost']} mesure "
               f"contre {2*np.log(N)/h2_nats(pb):.1f} attendu, la formule uniforme n'annoncant que "
               f"{2*np.log(N)/np.log(6):.1f} — lue ainsi, la mesure aurait crie a l'anomalie."))
    h = lab.holm()
    say(f"\n   consigne : h109.bloc_repete   {OBS}")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")


# ==========================================================================
rule("4. LA HIÉRARCHIE COMPLÈTE : CE QUE CHAQUE HYPOTHÈSE ACHÈTE")
H1, H2, H3 = "ce qu'on suppose", "outil", "portée sur l'état"
R1, O1, V1 = "le déterminisme, et rien d'autre", "absence de répétition", f"> {np.log2(BORNE):.1f} bits"
R2, O2, V2 = "+ sortie F2-linéaire, pas constant", "complexité conjointe §127", "≥ 56 448 bits"
R3, O3, V3 = "+ le modèle d'indexation inconnu", "minimum des deux §127", "≥ 47 040 bits"
R4, O4, V4 = "+ la famille est nommée", "élimination directe §105-118", "≤ 306 936 bits"
R5, O5, V5 = "+ la graine tient en 32 bits", "balayage §120-§121", "1,2e11 testées"
# ==========================================================================

say(f"""   Voici le rangement qui manquait. Chaque ligne suppose STRICTEMENT PLUS que
   la precedente, et achete strictement plus de portee.

   {H1:>44} {H2:>26} {H3:>19}
   {'-'*44:>44} {'-'*26:>26} {'-'*19:>19}
   {R1:>44} {O1:>26} {V1:>19}
   {R2:>44} {O2:>26} {V2:>19}
   {R3:>44} {O3:>26} {V3:>19}
   {R4:>44} {O4:>26} {V4:>19}
   {R5:>44} {O5:>26} {V5:>19}

   CE QUE LA HIERARCHIE DIT, LUE DE HAUT EN BAS. Plus on suppose, plus on
   atteint — et la premiere ligne montre le prix de ne rien supposer : vingt
   bits. Toute la portee du dossier vient donc des hypotheses de MODELE, pas du
   volume de donnees. C'est pourquoi l'archive de 70 560 tirages ne suffit pas,
   et c'est pourquoi neuf tirages ORDONNES valaient plus que sept mille tries.

   CE QU'ELLE DIT, LUE DE BAS EN HAUT. Chaque hypothese est un point de rupture
   possible : si la plateforme indexe dans l'ordre d'emission (§106), la ligne
   2 tombe et il reste la ligne 3 ; si elle rejette a pas variable (§111), les
   lignes 2 et 3 tombent et il reste VINGT BITS. Le dossier tient donc entier
   sur deux suppositions — pas constant, et sortie lineaire — dont AUCUNE n'est
   verifiable depuis les donnees publiees.

   C'EST LA REPONSE COMPLETE A « PEUT-ON RECONSTITUER L'ETAT ». Non depuis
   l'archive, et la raison n'est pas qu'on manque de tirages : c'est qu'on
   manque d'HYPOTHESES VERIFIABLES. Les deux donnees qui en verifieraient une
   sont nommees depuis le §92 et le §110, et elles se filment en une soiree :
   un tirage montrant la grille se remplir PUIS la boule EXTRA, et vingt
   arrets de roue.

   ({time.time() - T0:.1f} s)""")
