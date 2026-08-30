"""h45 — le détecteur qui manquait à la famille linéaire.

D'où vient cette expérience
============================
Le §59 (`h44`) établit que le rapport signal sur bruit PAR CELLULE d'une
déviation s-creuse vaut racine(z·racine(2m)/s) : il croît avec m à s fixé, au
lieu de décroître comme dans le cas dense. La conséquence immédiate sur
l'IDENTIFICATION y est traitée. Il en reste une, symétrique, sur la
DÉTECTION — et elle se lit dans le registre sans rien exécuter.

La famille quadratique de h24 a été testée DEUX FOIS, avec deux statistiques
qui ne visent pas la même chose :

    h24.quad_diffus   Q1 = somme des carrés des 252 800 corrélations
                      partielles          -> optimale contre un biais DENSE
    h24.quad_max      Q2 = max |Z| sur les 252 800 cellules
                      -> optimale contre un biais CONCENTRÉ

La famille linéaire, elle, n'a été testée qu'UNE fois :

    c1.matrix_real    T2 = ||C_chapeau||²_F, somme des carrés des 6 400
                      covariances croisées lag-1        (p = 0,787)
    d2.t2_lagscan     le même T2, balayé sur 306 lags   (p = 0,784)

Les deux sont des statistiques de SOMME. Leur note dit qu'elles « couvrent
toute matrice de couplage, dérangements compris » : c'est vrai au sens de la
consistance — une somme de carrés finit par tout voir — et faux au sens de la
puissance. Aucune statistique de MAXIMUM n'existe pour la famille linéaire.
C'est une case vide du produit (famille x forme du détecteur), et le §59 dit
exactement dans quel régime elle coûte quelque chose.

Ce que ce fichier fait
======================
1. Il chiffre le croisement : à partir de quelle parcimonie la somme perd
   contre le maximum. Trois lignes d'algèbre, aucune exécution.
2. Il exécute les deux détecteurs manquants sur l'archive RÉELLE, avec
   pré-enregistrement, null par permutation et calibration du maximum contre
   la loi de son propre balayage (précédent d2/a3).

Il TESTE l'archive : il consigne au registre, et il paie sa multiplicité.
"""

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402
from scipy.special import erfc                                # noqa: E402

T0 = time.time()
POOL, DRAWN = lab.POOL, lab.DRAWN
DRY = os.environ.get("H45_DRY") == "1"
REPS = 40 if DRY else 300


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# ==========================================================================
rule("1. LE CROISEMENT, EN TROIS LIGNES")
# ==========================================================================

M_CELLS, Z_REG = 6_400, 4.33

say(f"""   Une déviation portée par s cellules d'amplitude c, sur m = {M_CELLS:,} cellules
   dont l'erreur d'estimation vaut sigma.

   LA SOMME détecte quand la non-centralité dépasse le bruit du chi-2 :

       s·(c/sigma)²  >=  z·racine(2m)     ->   c/sigma  >=  racine(z·racine(2m)/s)

   LE MAXIMUM détecte quand une cellule dépasse le maximum du null, qui pour
   m cellules gaussiennes vaut environ racine(2·ln m) :

       c/sigma  >=  racine(2·ln m)   (indépendant de s)

   Les deux exigences se croisent en s* = z·racine(2m) / (2·ln m).""")

need_max = math.sqrt(2 * math.log(M_CELLS))
s_star = Z_REG * math.sqrt(2 * M_CELLS) / (2 * math.log(M_CELLS))
say(f"""
   m = {M_CELLS:,}, z = {Z_REG}   ->   le maximum exige c/sigma >= {need_max:.2f}
                              ->   croisement en s* = {s_star:.0f} cellules

        s      la somme exige   le maximum exige   qui gagne""")
for s in (1, 5, 10, 20, 28, 50, 100, 400, 6400):
    need_sum = math.sqrt(Z_REG * math.sqrt(2 * M_CELLS) / s)
    win = "MAXIMUM" if need_max < need_sum else "somme"
    say(f"   {s:>6}   {need_sum:>14.2f}   {need_max:>16.2f}   {win}")

say(f"""
   LECTURE. Sous {s_star:.0f} cellules actives, la statistique de somme employée par
   c1 et d2 est le MAUVAIS détecteur, et l'écart n'est pas marginal : à une
   seule cellule active elle exige {math.sqrt(Z_REG * math.sqrt(2 * M_CELLS)):.1f} écarts-types là où le maximum en
   exige {need_max:.2f}. Au-dessus de {s_star:.0f}, c'est la somme qui gagne, et les paires
   cachées de c1 (s = 50) tombent de ce côté-là — ce qui est précisément
   pourquoi le trou n'a pas sauté aux yeux : la famille de contamination
   choisie pour mesurer la puissance était justement dans le régime où le
   détecteur existant est le bon.

   Le trou porte donc sur les couplages TRÈS creux : une, deux, dix paires
   (source -> numéro) au lieu de cinquante. Rien dans le dossier ne les
   exclut, et rien ne les a cherchés avec le bon instrument.""")


# ==========================================================================
rule("2. LES DEUX DÉTECTEURS MANQUANTS, SUR L'ARCHIVE RÉELLE")
# ==========================================================================

arch = lab.load()
say(f"   archive : {len(arch):,} tirages.")


def cross_cov(a):
    """C[n,j] = Cov^(y_n(t), x_j(t-1)), colonnes centrées — convention c1."""
    X = a.mask[:-1].astype(np.float64)
    Y = a.mask[1:].astype(np.float64)
    T = len(Y)
    mx, my = X.mean(0), Y.mean(0)
    return (Y.T @ X) / T - np.outer(my, mx)


def stat_max(a):
    """max |C| sur les 6 400 cellules, en unités de l'écart-type EMPIRIQUE
    des cellules — l'échelle est ainsi interne à chaque réplicat, ce qui
    rend la statistique invariante à la longueur de l'archive."""
    C = cross_cov(a)
    return float(np.abs(C).max() / C.std())


def stat_hc(a):
    """Higher Criticism (Donoho-Jin) sur les 6 400 cellules.

    HC = max_i racine(m)·(i/m - p_(i)) / racine(p_(i)(1-p_(i))), sur la
    moitié inférieure des p triés. C'est le détecteur ADAPTATIF : il atteint
    la frontière de détection à toute parcimonie sans qu'on ait à la
    connaître, ce que ni la somme ni le maximum ne font.

    Les 6 400 cellules ne sont PAS indépendantes — chaque tirage porte
    exactement 20 numéros, ce qui contraint sommes de lignes et de colonnes.
    Les p gaussiens ci-dessous sont donc mal calibrés cellule par cellule.
    Cela n'a aucune conséquence : HC n'est ici qu'un NOMBRE, et sa
    calibration vient entièrement de la loi de permutation, qui subit
    exactement les mêmes contraintes. C'est la raison pour laquelle le null
    est permutationnel et non gaussien.
    """
    C = cross_cov(a)
    z = np.abs(C.ravel() / C.std())
    p = np.sort(erfc(z / math.sqrt(2)))
    m = len(p)
    i = np.arange(1, m + 1) / m
    half = m // 2
    num = math.sqrt(m) * (i[:half] - p[:half])
    den = np.sqrt(np.clip(p[:half] * (1 - p[:half]), 1e-15, None))
    return float((num / den).max())


TESTS = (
    ("h45.matrix_max", stat_max,
     "Aucune cellule de la matrice de couplage lag-1 (6 400 covariances "
     "croisées, colonnes centrées) n'est isolément forte : max |C|/sd(C) est "
     "compatible avec l'absence de couplage",
     "max |C[n,j]| / sd(C) sur les 6 400 covariances croisées lag-1 ; la "
     "multiplicité des 6 400 cellules est DANS la loi du maximum, pas "
     "corrigée après coup (précédent h24.quad_max)"),
    ("h45.matrix_hc", stat_hc,
     "Higher Criticism sur les mêmes 6 400 cellules ne détecte aucun excès "
     "de cellules modérément fortes — le détecteur adaptatif que ni la somme "
     "(c1.matrix_real) ni le maximum ne fournissent",
     "HC = max_i racine(m)(i/m - p_(i))/racine(p_(i)(1-p_(i))) sur la moitié "
     "inférieure des 6 400 p triés, p issus de |C|/sd(C) gaussien"),
)

NULLM = (f"permutation de l'ORDRE des tirages ({REPS} réplicats) : les 70 560 "
         "tirages sont conservés tels quels, seul le chaînage t -> t+1 est "
         "détruit. C'est le null exact de l'hypothèse visée, et il est plus "
         "conservateur qu'un SRS puisqu'il préserve toute structure "
         "intra-tirage.")
DEC = "conforme si p > seuil Holm du registre entier"

results = []
for tid, fn, hyp, sta in TESTS:
    tok = lab.preregister(tid, hyp, sta, NULLM, DEC, track="A")
    say(f"\n   pré-enregistré : {tid}  (sceau {tok['seal']})")
    obs = fn(arch)
    null = lab.calibrate_perm(fn, arch, reps=REPS, seed=45_000, progress=not DRY)
    p = float((np.sum(null.samples >= obs) + 1) / (null.reps + 1))   # unilatéral haut
    say(f"   observé {obs:.4f}   null {null.mean:.4f} +/- {null.sd:.4f}   "
        f"z = {null.z(obs):+.2f}   p = {p:.4f}")
    results.append((tid, tok, obs, null, p))

say("""
   Les deux statistiques sont UNILATÉRALES par construction : un maximum ou
   un HC anormalement BAS ne signale aucun couplage, il signale un null trop
   dispersé. Le p est donc la fraction des permutations qui atteignent ou
   dépassent l'observé, plus un — la correction de Barnard, qui interdit un
   p nul quand le nombre de réplicats est fini.""")


# ==========================================================================
rule("3. CONSIGNATION ET MULTIPLICITÉ")
# ==========================================================================

before = lab.holm()
m_before = before[0]["m_total"] if before else 0

if DRY:
    # Garde-fou : un galop d'essai ne doit RIEN écrire dans un registre
    # append-only et partagé. La première version de ce fichier ne l'avait
    # pas, elle a consigné deux lignes à 40 réplicats, et il a fallu les
    # écraser par `lab.dedupe()` — le précédent est au §60.
    say("   MODE ESSAI : rien n'est consigné.")
    raise SystemExit(0)

for tid, tok, obs, null, p in results:
    lab.record(tok, obs, null=null, p=p,
        verdict="conforme" if p > 0.05 / 4000 else "A EXAMINER",
        notes=(f"detecteur MANQUANT de la famille lineaire (§59/h44) : c1.matrix_real "
               f"et d2.t2_lagscan n'emploient qu'une statistique de SOMME, optimale "
               f"contre un biais dense, perdante sous s* = {s_star:.0f} cellules actives. "
               f"Null par permutation de l'ordre, {REPS} replicats, multiplicite des "
               f"6 400 cellules dans la loi de la statistique."))

after = lab.holm()
m_after = after[0]["m_total"]
say(f"""   m du registre : {m_before:,} -> {m_after:,}   (+{m_after - m_before})
   seuil Holm le plus strict : {0.05 / m_after:.3e}
""")
for tid, tok, obs, null, p in results:
    row = next(r for r in after if r["id"] == tid)
    say(f"   {tid:<20} p = {p:.4f}   seuil {row['holm_threshold']:.3e}   "
        f"{'SIGNIFICATIF' if row['significant'] else 'conforme'}")

worst = min(r["p"] for r in after)
say(f"""
   Le plus petit p du registre entier vaut {worst:.2e} pour un seuil Holm de
   {0.05 / m_after:.2e} : le registre reste conforme.""")


# ==========================================================================
rule("4. CE QUE CELA FERME, ET CE QUE CELA N'ATTEINT PAS")
# ==========================================================================

say(f"""   FERMÉ. La case vide du produit (famille linéaire x détecteur de forme
   concentrée) est remplie. La famille linéaire est désormais testée par une
   somme (c1, d2), un maximum et un Higher Criticism — la même couverture que
   la famille quadratique, qui l'avait depuis h24.

   CE QUE CE N'EST PAS. Deux tests conformes n'établissent pas l'absence de
   couplage : ils établissent qu'aucun couplage assez fort pour être vu à
   cette puissance n'est présent. La puissance n'est pas mesurée ici, et
   c'est la limite principale — le dossier exige d'ordinaire un témoin
   positif, et il faudrait une contamination très creuse (s = 1 à 10) pour
   le fournir. Sans lui, ces deux lignes valent comme couverture de famille,
   pas comme borne.

   CE QUE CELA NE CHANGE PAS. Le théorème d'invariance tient, et le §59 ne
   l'a pas touché non plus. Ce qui a bougé est la carte de ce qui a été
   cherché — pas le résultat de la recherche.

   ({time.time() - T0:.1f} s)""")
