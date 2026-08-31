"""h77 — l'audit de la carte : deux lignes surestimees, et ce que les quatre
tirages consecutifs debloquent.

CE QUI A DECLENCHE CET AUDIT
=============================
Le §97 a trouve que la carte de couverture du §73 portait une ligne FAUSSE :

    | LCG mod 2^48 (java.util.Random) | rejet / FY modulaire | §34 | 2^48 |

Verification dans `tools/sweep_java48.c` : ce fichier ne contient qu'UNE
fonction d'echantillonnage, `java_fy`, un Fisher-Yates partiel. Aucun rejet.
La carte avait elargi la conclusion en la recopiant. Si une ligne est fausse,
il faut lire les autres.

LA DEUXIEME LIGNE, ET ELLE EST PLUS LOURDE
===========================================
    | F2-lineaires <= 128 bits | rejet modulo 80 | §68 | resolu, TOUTE GRAINE,
      couverture 46-99 % |

« Resolu pour toute graine » et « couverture 46 % » ne peuvent pas etre vrais
ensemble. La table du §68 elle-meme donne xorshift128 a 46,1 % : plus de la
MOITIE des motifs de rejet n'a jamais ete exploree pour la plus grosse
famille.

LA CAUSE EST DANS LE CODE, ET C'EST UN COMMENTAIRE PERIME
==========================================================
`h61_familles_etendues.py`, ligne 559 :

    if need > 2:            # le dossier n'a qu'UNE paire consecutive
        continue

Le dossier a desormais QUATRE tirages consecutifs (1381256-1381259, releves
cette session). Les familles qui demandent trois ou quatre tirages chaines
etaient ecartees faute de donnees — les donnees existent.

ET LA COUVERTURE NE SE LIT PAS PAR CHAINE
==========================================
Le §68 et le §81 rapportent la couverture d'UNE chaine. Or chaque chaine est
un essai INDEPENDANT : si le generateur est de la famille testee, il suffit
qu'UNE chaine ait son motif de rejet dans la portee pour que l'attaque
aboutisse. La couverture se COMPOSE, exactement comme au §96 :

    couverture totale = 1 - (1 - c)^(nombre de chaines)

Avec quatre chaines de deux tirages, 46,1 % par chaine devient 91,6 %.

Il TESTE les tirages ordonnes du dossier : il consigne au registre.
"""

import csv
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H77_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(ICI)
POOL, DRAWN = 80, 20


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# ==========================================================================
# ON REPREND LA MACHINERIE DU §81 TELLE QUELLE
# ==========================================================================
# Toutes les fonctions de h61 sont definies AVANT sa premiere section : on
# execute cet en-tete et rien d'autre. Aucune reimplementation, donc aucune
# divergence possible entre l'attaque auditee et l'attaque d'origine.
_SRC = open(os.path.join(ICI, "h61_familles_etendues.py")).read()
_HEAD = _SRC[:_SRC.index('rule("1. LES FAMILLES')]
_HEAD = _HEAD.replace("os.path.abspath(__file__)",
                      "os.path.abspath(%r)" % os.path.join(ICI, "h61_familles_etendues.py"))
H61 = {}
exec(compile(_HEAD, "h61(header)", "exec"), H61)               # noqa: S102

basis_bits = H61["basis_bits"]
rank_threshold = H61["rank_threshold"]
attack = H61["attack"]
coverage = H61["coverage"] if "coverage" in H61 else None
OLD, NEW = H61["OLD"], H61["NEW"]
KCAP = H61["KCAP"]
MAXT = 5 if DRY else H61["MAXT"]
BUDGET = 8.0 if DRY else 45.0


# `coverage` et `rejection_law` vivent dans la section 2 de h61 : on les
# retranscrit ici a l'identique plutot que d'executer une section qui
# consigne.
def _loi_partielle(m, nmax=80):
    """Loi du nombre de rejets pour les m PREMIERS numeros d'un tirage.

    Le i-eme numero accepte est precede d'un nombre de rejets geometrique de
    parametre i/80 : c'est la probabilite de retomber sur l'un des i deja vus.
    """
    import numpy as np
    p = np.zeros(nmax + 1)
    p[0] = 1.0
    for i in range(m):
        q = i / POOL
        g = np.array([(1 - q) * q ** j for j in range(nmax + 1)])
        p = np.convolve(p, g)[:nmax + 1]
    return p


def loi_chaine(w, nmax=80):
    """Loi du nombre TOTAL de rejets sur les w premiers mots d'une CHAINE.

    ET C'EST ICI QUE LE §81 SE TROMPE. Il applique la loi d'un tirage de w
    numeros distincts. Or une chaine de deux tirages n'est pas un tirage de
    trente-trois numeros distincts : au vingt-et-unieme, L'ENSEMBLE DES DEJA
    VUS EST REMIS A ZERO, et la probabilite de rejet retombe a zero. Compter
    w d'affilee revient a supposer des rejets qui n'ont pas lieu — pour
    xorshift128 (w = 33), 6,60 rejets attendus au lieu de 3,82.

    L'erreur va dans le sens INCONFORTABLE : elle SOUS-estime la couverture,
    donc elle fait paraitre le dossier moins avance qu'il ne l'est.
    """
    import numpy as np
    pleins, reste = divmod(w, DRAWN)
    p = np.zeros(nmax + 1)
    p[0] = 1.0
    for _ in range(pleins):
        p = np.convolve(p, _loi_partielle(DRAWN, nmax))[:nmax + 1]
    if reste:
        p = np.convolve(p, _loi_partielle(reste, nmax))[:nmax + 1]
    return p / p.sum()


def couverture(w, t):
    """P(le nombre total de rejets sur les w premiers mots tient sous t)."""
    return float(loi_chaine(w)[:max(0, t) + 1].sum())


def couverture_81(w, t):
    """La couverture TELLE QUE LE §81 la calcule — pour montrer l'ecart."""
    return float((_loi_partielle(w) / _loi_partielle(w).sum())[:max(0, t) + 1].sum())


# ==========================================================================
rule("1. LES CHAÎNES DISPONIBLES, ET CE QU'ELLES DÉBLOQUENT")
# ==========================================================================

rows = list(csv.DictReader(open(os.path.join(ROOT, "draws_ordered.csv"))))
ORD = sorted((int(r["id"]), [int(r[f"o{i}"]) for i in range(1, DRAWN + 1)])
             for r in rows)
plages, cur = [], [ORD[0]]
for d in ORD[1:]:
    if d[0] == cur[-1][0] + 1:
        cur.append(d)
    else:
        plages.append(cur)
        cur = [d]
plages.append(cur)

say(f"   {len(ORD)} tirages ordonnes, en {len(plages)} plages consecutives :")
for pl in plages:
    say(f"     {pl[0][0]} .. {pl[-1][0]}   ({len(pl)} tirage{'s' if len(pl) > 1 else ''})")

LMAX = max(len(pl) for pl in plages)


def chaines(L):
    """Toutes les fenetres de L tirages CONSECUTIFS."""
    out = []
    for pl in plages:
        for i in range(len(pl) - L + 1):
            out.append([d[1] for d in pl[i:i + L]])
    return out


say(f"\n   {'longueur':>9} {'chaînes':>8}   {'ce que cela permet':<40}")
for L in range(1, LMAX + 1):
    n = len(chaines(L))
    say(f"   {L:>9} {n:>8}   {'familles demandant ' + str(L) + ' tirage(s)':<40}")
say(f"""
   LA PLAGE DE QUATRE — 1381256 a 1381259 — EST NOUVELLE. Le §81 portait en
   dur « le dossier n'a qu'UNE paire consecutive » et ecartait donc toute
   famille demandant plus de deux tirages chaines. Ce n'est plus vrai.""")


# ==========================================================================
rule("2. LES FAMILLES, ET CELLES QUE LE §81 ÉCARTAIT")
# ==========================================================================

NB = 4                                    # bits publies par mot sous modulo
INFO = {}
say(f"   {'famille':>21} {'bits':>6} {'W(rang)':>8} {'rang':>6} "
    f"{'tirages requis':>15} {'§81':>9} {'ici':>9}")
for name, nb, step, orig in OLD + NEW:
    nw = min(400, nb // NB + 120)
    coef = basis_bits(step, nb, nw)
    w, r = rank_threshold(coef, nw)
    need = -(-w // DRAWN)
    trop = nb - r > KCAP
    av81 = "écartée" if (trop or need > 2) else "testée"
    ici = "écartée" if (trop or need > LMAX or not chaines(need)) else "TESTÉE"
    INFO[name] = (nb, step, coef, nw, w, r, need, trop)
    say(f"   {name:>21} {nb:>6} {w:>8} {r:>6} {need:>15} {av81:>9} {ici:>9}")

nouvelles = [n for n, v in INFO.items()
             if not v[7] and 2 < v[6] <= LMAX and chaines(v[6])]
say(f"""
   {len(nouvelles)} famille(s) que le §81 ne pouvait pas atteindre le sont ici : {nouvelles}.
   Elles ne demandaient pas une meilleure attaque — seulement la plage de
   quatre tirages consecutifs relevee cette session.""")


# ==========================================================================
rule("3. L'ATTAQUE, SUR TOUTES LES CHAÎNES")
# ==========================================================================

say(f"   plafond TOTAL de rejets : {MAXT}   budget : {BUDGET:.0f} s par chaine\n")
say(f"   {'famille':>21} {'chaînes':>8} {'profond.':>9} {'§81':>7} "
    f"{'corrigée':>9} {'COMPOSÉE':>10} {'trouvés':>8} {'sec':>7}")
total_hits = ntry = 0
lignes = []
for name, (nb, step, coef, nw, w, r, need, trop) in INFO.items():
    if trop or need > LMAX:
        continue
    cas = chaines(need)
    if not cas:
        continue
    hit, dmin, t0 = 0, 99, time.time()
    for case in cas:
        ntry += 1
        nw2 = DRAWN * need + MAXT
        c2 = basis_bits(step, nb, nw2)
        got, dep = attack(step, nb, case, c2, nw2, BUDGET, MAXT, r)
        dmin = min(dmin, dep)
        if got is not None:
            hit += 1
    c1 = couverture(w, dmin)
    c81 = couverture_81(w, dmin)
    ctot = 1 - (1 - c1) ** len(cas)
    total_hits += hit
    lignes.append((name, len(cas), dmin, c1, ctot, hit, c81))
    say(f"   {name:>21} {len(cas):>8} {dmin:>9} {c81:>7.1%} {c1:>9.1%} "
        f"{ctot:>10.1%} {hit:>8} {time.time() - t0:>7.1f}")

cmin1 = min(l[3] for l in lignes)
cmintot = min(l[4] for l in lignes)
say(f"""
   {ntry} attaques, {total_hits} etat compatible.

   COUVERTURE MINIMALE : {cmin1:.1%} par chaine, {cmintot:.1%} UNE FOIS COMPOSEE.

   DEUX CORRECTIONS SE CUMULENT ICI, et elles vont dans le meme sens.

     1. LA LOI DE REJETS. Le §81 compte les rejets d'un tirage de w numeros
        distincts. Une chaine de deux tirages remet l'ensemble a zero au
        vingt-et-unieme : la colonne « §81 » et la colonne « corrigee »
        montrent l'ecart, et il est large.
     2. LA COMPOSITION. Chaque chaine est un essai independant ; il suffit
        qu'UNE ait son motif dans la portee. Le §68 et le §81 rapportaient la
        couverture d'une seule.

   Le §68 annoncait 46 % pour xorshift128 et concluait « ferme pour TOUTE
   GRAINE » — les deux ne pouvaient pas tenir ensemble. Le chiffre honnete,
   ici, est {cmintot:.1%}.""")


# ==========================================================================
rule("4. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h77.chaines_longues",
        "Aucun generateur F2-lineaire des familles joignables n'engendre les "
        "tirages ordonnes du dossier sous rejet modulo 80, en exploitant TOUTES "
        "les chaines consecutives disponibles — y compris la plage de quatre "
        "tirages relevee cette session, que le §81 ne pouvait pas utiliser",
        "attaque du §81 reprise a l'identique (son en-tete est execute, rien "
        "n'est reimplemente), appliquee a chaque chaine de longueur requise ; "
        "la couverture est COMPOSEE sur les chaines au lieu d'etre rapportee "
        "par chaine",
        "aucun null n'est requis : la verification est un rejeu exact dans "
        "l'ordre, donc sans faux positif",
        "conforme si aucun etat compatible n'est trouve", track="B")
    tok["m_extra"] = max(0, len(lignes) - 1)
    lab.record(
        tok, float(total_hits), p=1.0, verdict="conforme",
        power_at=(f"le temoin du §81 vaut pour l'attaque elle-meme, qui n'est pas "
                  f"modifiee ; ce qui change ici est le NOMBRE de chaines et la "
                  f"composition — couverture minimale portee de {cmin1:.0%} par "
                  f"chaine a {cmintot:.0%}"),
        notes=(f"AUDIT DE LA CARTE. Le §97 avait trouve une ligne fausse (le §34 "
               f"ne couvre le rejet que sous 2^32, pas 2^48). Celle-ci en corrige "
               f"une seconde : « F2-lineaires <= 128 bits, rejet, resolu TOUTE "
               f"GRAINE, couverture 46-99 % » etait contradictoire. Cause : "
               f"h61 ligne 559 portait en dur « le dossier n'a qu'UNE paire "
               f"consecutive », ce qui est faux depuis la plage 1381256-1381259. "
               f"{len(nouvelles)} famille(s) debloquee(s) : {nouvelles}. "
               f"Couverture composee minimale {cmintot:.3f} sur {ntry} chaines."))
    h = lab.holm()
    say(f"   consigne : h77.chaines_longues   {total_hits} etat compatible")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")


# ==========================================================================
rule("5. CE QUE L'AUDIT ÉTABLIT")
# ==========================================================================

say(f"""   DEUX LIGNES DE LA CARTE ETAIENT SUSTIMEES, et les deux pour la meme
   raison : une conclusion recopiee plus largement que sa source.

     §34   « rejet / FY modulaire, 2^48 »   -> la source ne fait que FY.
            Corrigee au §97, qui ferme le rejet pour de bon.
     §68   « resolu TOUTE GRAINE, 46-99 % » -> 46 % et « toute graine » sont
            contradictoires. Corrigee ici : {cmintot:.1%} compose.

   ET UNE HYPOTHESE PERIMEE DORMAIT DANS LE CODE. « Le dossier n'a qu'UNE
   paire consecutive » etait vrai quand il avait cinq tirages ordonnes ; il en
   a neuf, dont quatre a la suite. Personne n'avait relu la garde.

   CE QUE CELA NE CHANGE PAS. Aucun etat compatible, ici comme partout. Les
   resultats NULS du dossier tiennent tous — un audit de couverture ne
   fabrique pas de decouverte, il dit seulement de combien on s'etait cru
   plus avance qu'on ne l'etait.

   CE QUI RESTE HORS DE PORTEE, et c'est desormais dit avec le bon chiffre :
     — les familles demandant plus de {LMAX} tirages chaines (WELL512a en
       demande {INFO['WELL512a'][6]}) ;
     — les familles dont le noyau depasse KCAP = {KCAP} (LFSR113) ;
     — tout ce que le §91 nomme : sorties brouillees, retenue, CSPRNG.

   Registre : consigne a la section 4.

   ({time.time() - T0:.1f} s)""")
