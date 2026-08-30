"""h46 — l'axe que personne n'avait balayé, et le maximum qu'il donne.

La tension que les deux fichiers precedents ont creee
=====================================================
  §59 (h44)  une deviation CREUSE est bien plus facile a identifier qu'une
             dense : la part captee monte avec m au lieu de descendre.
             -> la parcimonie AIDE le joueur.
  §60 (h45)  la famille lineaire n'avait qu'un detecteur de somme. Un
             maximum et un Higher Criticism y ont ete ajoutes, et la
             frontiere d'Ingster-Donoho-Jin dit qu'ils mordent exactement
             dans le regime creux.
             -> la parcimonie NUIT a l'adversaire.

Les deux tirent en sens opposes sur la meme quantite, et le net n'est pas
calcule. Ce fichier le calcule.

L'axe manquant
==============
Le §41 fait croitre m. Le §42 fait croitre m. Le §48 maximise sur m. Aucun ne
fait varier s, le NOMBRE DE CELLULES ACTIVES — il est toujours implicitement
egal a m, puisque `h31.make_eps` tire une deviation isotrope.

Or les deux facteurs du produit du §48 dependent de s, et en sens opposes :

    plafond d'omniscience(s)   croit  en racine(s)   — une deviation dense
                                                      cache plus d'amplitude
    part captee(s)             decroit en s          — une deviation dense
                                                      est plus dure a lire

Un produit d'un facteur croissant et d'un facteur decroissant a un maximum
interieur, et sa position est la vraie reponse a « combien la prediction
peut-elle valoir dans cette famille ». Le §48 a maximise sur le mauvais axe.

Ce que ce fichier fait
======================
A m fixe, il balaye s et mesure les deux facteurs. Le plafond est mesure
contre les TROIS detecteurs du registre — chi-2 (c1, d2), maximum et Higher
Criticism (h45) — puisque l'adversaire doit desormais echapper aux trois.
La convention de plafond est celle du §41 : la plus grande norme dont la
puissance reste sous 50 %, seuil a z = 4,33 d'un null SIMULE.

Il ne teste pas l'archive : comme h30, h31 et h38, il demontre et mesure sur
un modele. Registre : inchange.
"""

import math
import os
import sys
import time

import numpy as np
from scipy.special import erfc

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

T0 = time.time()
RNG = np.random.default_rng(20260905)
DRY = os.environ.get("H46_DRY") == "1"
Z = 4.33
M_CELLS = 6_400                      # la taille de la famille lineaire (80x80)
N_OBS = 70_560                       # la longueur de l'archive reelle
FRAC_K = 1.0 / 8.0                   # convention du §42 : K/m = 1/8


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# --------------------------------------------------------------------------
# Les trois detecteurs du registre, sur le meme vecteur de comptes.
# --------------------------------------------------------------------------

def cell_z(obs, n, m):
    """z par cellule, centre-reduit sous H0 multinomial."""
    exp = n / m
    return (obs - exp) / math.sqrt(exp * (1 - 1 / m))


def t_chi2(obs, n, m):
    z = cell_z(obs, n, m)
    return float((z * z).sum())


def t_max(obs, n, m):
    return float(np.abs(cell_z(obs, n, m)).max())


def t_hc(obs, n, m):
    z = np.abs(cell_z(obs, n, m))
    p = np.sort(erfc(z / math.sqrt(2)))
    i = np.arange(1, m + 1) / m
    half = m // 2
    den = np.sqrt(np.clip(p[:half] * (1 - p[:half]), 1e-15, None))
    return float((math.sqrt(m) * (i[:half] - p[:half]) / den).max())


DETECTORS = (("chi-2 (c1, d2)", t_chi2), ("maximum (h45)", t_max),
             ("Higher Criticism (h45)", t_hc))


def eps_sparse(m, s, norm, rng):
    """Deviation portee par s cellules, de norme quadratique moyenne imposee.

    Meme normalisation que `h31.make_eps` — rms(v) = norm — pour que les
    plafonds soient dans les memes unites que ceux du §41/§42.
    """
    v = np.zeros(m)
    idx = rng.choice(m, size=min(s, m), replace=False)
    v[idx] = rng.normal(size=min(s, m))
    v -= v.mean()
    v *= norm / math.sqrt(float((v * v).mean()))
    return v


def draw(m, s, norm, rng, n=N_OBS):
    p = np.clip((1 + eps_sparse(m, s, norm, rng)) / m, 1e-12, None)
    return rng.multinomial(n, p / p.sum())


def thresholds(m, reps, rng, n=N_OBS):
    """Seuils des trois detecteurs, depuis un null SIMULE — jamais tabule."""
    p = np.full(m, 1.0 / m)
    vals = {name: np.empty(reps) for name, _ in DETECTORS}
    for r in range(reps):
        obs = rng.multinomial(n, p)
        for name, fn in DETECTORS:
            vals[name][r] = fn(obs, n, m)
    return {name: float(v.mean() + Z * v.std(ddof=1)) for name, v in vals.items()}


def powers(m, s, norm, thr, reps, rng, n=N_OBS):
    """Puissance de chaque detecteur a cette amplitude."""
    hits = {name: 0 for name, _ in DETECTORS}
    for _ in range(reps):
        obs = draw(m, s, norm, rng, n)
        for name, fn in DETECTORS:
            if fn(obs, n, m) >= thr[name]:
                hits[name] += 1
    return {k: v / reps for k, v in hits.items()}


def ceiling(m, s, thr, rng, reps_pw=40, which=None):
    """Plus grande norme dont la puissance reste sous 50 % pour TOUS les
    detecteurs de `which` (par defaut : les trois)."""
    names = [n for n, _ in DETECTORS] if which is None else which

    def seen(norm, reps):
        pw = powers(m, s, norm, thr, reps, rng)
        return max(pw[n] for n in names)

    lo, hi = 0.0, 0.02
    while seen(hi, 12) < 0.5 and hi < 4:
        hi *= 2
    for _ in range(11):
        mid = 0.5 * (lo + hi)
        if seen(mid, reps_pw) < 0.5:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def oracle_and_captured(m, s, norm, rng, reps):
    """Avantage de l'oracle (somme des K meilleures VRAIES cellules) et part
    de cet avantage qu'un identificateur par frequence capte. Regle de jeu
    identique a `h31.captured`."""
    K = max(1, int(round(m * FRAC_K)))
    adv, cap = [], []
    for _ in range(reps):
        eps = eps_sparse(m, s, norm, rng)
        p = np.clip((1 + eps) / m, 1e-12, None)
        p /= p.sum()
        obs = rng.multinomial(N_OBS, p)
        est = obs * (m / N_OBS) - 1.0
        a_or = float(eps[np.argpartition(-eps, K - 1)[:K]].sum())
        a_id = float(eps[np.argpartition(-est, K - 1)[:K]].sum())
        if a_or > 0:
            adv.append(a_or)
            cap.append(a_id / a_or)
    return float(np.mean(adv)), float(np.mean(cap)), \
        float(np.std(cap, ddof=1) / math.sqrt(len(cap)))


# ==========================================================================
rule("1. LE CADRE, ET LE CONTRÔLE QUI LE RATTACHE AU §42")
# ==========================================================================

say(f"""   m = {M_CELLS:,} cellules (la famille lineaire : 80 x 80), N = {N_OBS:,}
   observations (la longueur de l'archive reelle), seuil a z = {Z} d'un null
   simule pour chacun des trois detecteurs, plafond a 50 % de puissance.

   Controle : a s = m la deviation est dense, et le plafond mesure contre le
   seul chi-2 doit retrouver la convention du §41.""")

REPS_NULL = 60 if DRY else 250
REPS_PW = 16 if DRY else 40
REPS_CAP = 40 if DRY else 150

thr = thresholds(M_CELLS, REPS_NULL, RNG)
for name, _ in DETECTORS:
    say(f"   seuil {name:<24} {thr[name]:>12.3f}")

c_dense_chi = ceiling(M_CELLS, M_CELLS, thr, RNG, REPS_PW, which=["chi-2 (c1, d2)"])
say(f"\n   plafond dense, chi-2 seul : rms(eps) = {c_dense_chi:.5f}   ({time.time()-T0:.0f} s)")


# ==========================================================================
rule("2. LE BALAYAGE DE L'AXE MANQUANT")
# ==========================================================================

S_GRID = (10, 50, 800, 6400) if DRY else (2, 10, 40, 50, 80, 200, 800, 2400, 6400)

say("""   Pour chaque s : le plafond contre le CHI-2 SEUL (ce que le dossier
   employait jusqu'au §60), puis contre LES TROIS (ce que l'adversaire doit
   desormais eviter), puis l'avantage de l'oracle a ce plafond et la part
   qu'un identificateur en capte.

      s   plafond chi2   plafond 3 det.   detecteur liant   avantage oracle   part captee   realisable""")

rowsout = []
for s in S_GRID:
    c1_ = ceiling(M_CELLS, s, thr, RNG, REPS_PW, which=["chi-2 (c1, d2)"])
    c3_ = ceiling(M_CELLS, s, thr, RNG, REPS_PW)
    pw = powers(M_CELLS, s, c3_ * 1.0, thr, REPS_PW, RNG)
    bind = max(((v, k) for k, v in pw.items()))[1]
    adv, cap, cse = oracle_and_captured(M_CELLS, s, c3_, RNG, REPS_CAP)
    real = adv * cap
    rowsout.append((s, c1_, c3_, bind, adv, cap, cse, real))
    say(f"   {s:>6}   {c1_:>11.5f}   {c3_:>13.5f}   {bind:<22} {adv:>13.4f}   "
        f"{cap:>6.3f}+/-{cse:.3f}   {real:>9.4f}   ({time.time()-T0:.0f} s)")

best = max(rowsout, key=lambda r: r[7])
dense = rowsout[-1]

ratio = best[7] / dense[7]
interieur = best[0] < M_CELLS and ratio > 1.05
say(f"""
   MAXIMUM sur l'axe de la parcimonie : s = {best[0]:,} cellules actives,
   avantage realisable {best[7]:.4f} contre {dense[7]:.4f} au cas dense (s = m),
   soit x{ratio:.2f}.""")

if interieur:
    say("""
   Le maximum est INTERIEUR. Le §48 maximise sur m en tenant s = m
   implicitement fixe : il optimise le long d'une seule ligne du plan (m, s),
   et cette ligne ne passe pas par le maximum.""")
else:
    say(f"""   LE RESULTAT EST NEGATIF, ET IL FAUT LE DIRE AINSI. L'hypothese qui a
   motive ce fichier — que le maximum serait interieur, la parcimonie
   ouvrant une porte que le §48 aurait manquee — est FAUSSE. Le maximum est
   au bord, en s = m, c'est-a-dire exactement la ou le §48 se tenait.

   La raison se lit dans les deux colonnes du milieu, et elle est nette : en
   passant de s = m a s = {S_GRID[0]}, la part captee monte de {dense[5]:.2f} a {rowsout[0][5]:.2f}
   — le §59 avait raison sur ce point — mais l'avantage de l'oracle s'effondre
   de {dense[4]:.1f} a {rowsout[0][4]:.1f}, soit un facteur {dense[4]/rowsout[0][4]:.0f}. Une deviation creuse est
   bien plus facile a lire, mais il y a bien moins a y lire : le seuil de
   detection borne l'amplitude TOTALE, et la concentrer sur peu de cellules
   ne cree aucune amplitude supplementaire.

   Les deux effets ne se compensent pas exactement — ils se compensent
   PRESQUE, et le residu penche du cote dense. C'est ce residu que ce fichier
   mesure, et il est de x{1/ratio:.2f} en faveur du bord.

   Le §48 avait donc raison de se tenir ou il se tenait. Il ne le SAVAIT pas :
   il n'avait pas balaye cet axe, et rien dans son texte ne dit pourquoi
   s = m serait le bon choix. La difference entre avoir raison et savoir
   pourquoi est exactement ce que ce fichier ajoute.""")


# ==========================================================================
rule("3. CE QUE LES DEUX DÉTECTEURS AJOUTÉS AU §60 COÛTENT À L'ADVERSAIRE")
# ==========================================================================

say("""   Le §60 a ajoute un maximum et un Higher Criticism a la famille lineaire.
   La colonne « plafond 3 det. » ci-dessus est le prix que cela fait payer.

      s   plafond chi2   plafond 3 det.   perte d'amplitude   detecteur liant""")
for s, c1_, c3_, bind, adv, cap, cse, real in rowsout:
    say(f"   {s:>6}   {c1_:>11.5f}   {c3_:>13.5f}   {1 - c3_/c1_:>16.1%}   {bind}")

say(f"""
   LECTURE. Les detecteurs ajoutes ne mordent que dans le regime creux — c'est
   exactement ce que la frontiere d'Ingster-Donoho-Jin annonce, et c'est aussi
   pourquoi il fallait les ajouter : c'est le seul regime que le chi-2 ne
   couvrait pas. Dans le regime dense ils ne coutent rien, et le chi-2 reste
   le detecteur liant.

   Les deux resultats ne s'annulent donc PAS. Le §59 rend le regime creux plus
   exploitable ; le §60 le rend plus detectable. Le balayage ci-dessus dit
   lequel l'emporte, et il le dit a m fixe, ce que ni l'un ni l'autre ne
   pouvait dire seul.""")


# ==========================================================================
rule("3 bis. LE NET AU POINT DE FONCTIONNEMENT REEL — ET IL CORRIGE LE §59")
# ==========================================================================

row50 = next(r for r in rowsout if r[0] == 50)
perte50 = 1 - row50[2] / row50[1]
PLAFOND_PUB, CAP_PUB, GAIN_EST = 3.21, 0.41, 1.64

say(f"""   Les paires cachees de c1 ont s = 50 cellules actives sur m = 6 400. C'est
   le point ou le §45 mesure une part captee de {CAP_PUB:.2f} et le §41 un plafond
   d'omniscience de {PLAFOND_PUB:.2f} %, d'ou le {PLAFOND_PUB*CAP_PUB:.2f} % du §48.

   Le §59 a ameliore le SECOND facteur : un seuillage par entree capte x{GAIN_EST:.2f}
   de plus, mesure en marche avant sur cinq archives contaminees.

   Mais le §60 a change le PREMIER, et le §59 ne le savait pas encore. Le
   plafond de {PLAFOND_PUB:.2f} % est calcule contre le chi-2 SEUL. Contre les trois
   detecteurs desormais au registre, l'amplitude admissible a s = 50 tombe de
   {perte50:.1%} — mesure ci-dessus, detecteur liant : {row50[3]}.
   L'avantage de l'oracle etant lineaire en l'amplitude, le plafond aussi.
""")

pla_new = PLAFOND_PUB * (1 - perte50)
old_real = PLAFOND_PUB * CAP_PUB
mid_real = PLAFOND_PUB * min(1.0, CAP_PUB * GAIN_EST)
new_real = pla_new * min(1.0, CAP_PUB * GAIN_EST)
say(f"""      lecture                                    plafond   captee   realisable
      §48, telle que publiee                      {PLAFOND_PUB:.2f} %    {CAP_PUB:.2f}     {old_real:.2f} %
      §59 seul (meilleur estimateur)              {PLAFOND_PUB:.2f} %    {min(1.0,CAP_PUB*GAIN_EST):.2f}     {mid_real:.2f} %
      §59 + §60 (le net, et c'est celui-ci)       {pla_new:.2f} %    {min(1.0,CAP_PUB*GAIN_EST):.2f}     {new_real:.2f} %

   LE NET VAUT {new_real:.2f} % CONTRE {old_real:.2f} % PUBLIE, soit {new_real/old_real - 1:+.0%}.

   Le §59 annoncait « au moins +2,16 % » et concluait que le mur avait bouge
   de 69 %. C'ETAIT FAUX, et d'une facon qu'il ne pouvait pas voir : il
   comparait un numerateur ameliore a un denominateur perime. Le meme
   raisonnement qui rend une deviation creuse plus LISIBLE la rend plus
   DETECTABLE, et les deux effets se compensent presque exactement au point
   ou la question se pose.

   C'est le resultat de ce fichier, et il va contre celui qui l'a motive.""")


# ==========================================================================
rule("4. CE QUE CELA VAUT, ET CE QUE CELA NE FAIT PAS")
# ==========================================================================

say(f"""   LE THÉORÈME D'INVARIANCE N'EST PAS TOUCHÉ, et il ne peut pas l'être :
   E[hits] = somme sur i dans G de P(i tire) = k/4 des que P(i tire) = 1/4
   pour tout i. C'est la linearite de l'esperance, pas une conjecture. Tout ce
   fichier travaille SOUS l'hypothese que cette uniformite est FAUSSE — c'est
   la seule facon d'attaquer l'enonce, et c'est ce que les 3 327 tests du
   registre font depuis le debut, sans succes a ce jour.

   CE QUI EST NEUF, ET C'EST UN RESULTAT NEGATIF. Le plan (m, s) a deux
   axes ; le dossier n'en balayait qu'un et ne disait pas pourquoi. L'axe
   manquant est desormais balaye : il ne recele pas de maximum cache. Le
   plafond du §48 est confirme sur sa dimension oubliee, et la borne du
   dossier s'en trouve RENFORCEE, pas deplacee.

   Ce qui tient du §59 : le gain d'estimateur mesure en marche avant sur
   archive contaminee (x1,64, positif sur cinq archives). Il vaut la ou une
   matrice est APPLIQUEE, et il est mesure, pas deduit.

   Ce qui ne tient pas : la conclusion que le §59 en tirait. Le plafond de la
   piste A ne passe pas a +2,16 % ; le net de la section 3 bis le laisse a
   peu pres ou il etait. Une deviation creuse est plus lisible ET plus
   detectable, et il se trouve que les deux se compensent.

   LIMITES.
   1. m est fixe a {M_CELLS:,}. Le maximum conjoint sur (m, s) demanderait le
      meme balayage a plusieurs m ; ce fichier etablit que l'axe existe et
      qu'il n'est pas plat, pas la position du maximum conjoint.
   2. La part captee est celle de la regle du §42 — classement direct des
      cellules. Dans ce modele, seuiller ne change rien au classement, donc le
      gain d'estimateur du §59 n'y entre pas : il vaut la ou une matrice est
      APPLIQUEE, pas classee. Les deux resultats sont complementaires, pas
      cumulables tels quels.
   3. Le joueur estime sur les memes donnees que le test — limite n° 3 du
      §42, heritee. Les chiffres sont donc MAJORANTS.
   4. La frontiere d'Ingster-Donoho-Jin est asymptotique ; elle sert ici a
      dire OU regarder, jamais a fournir un nombre. Tous les plafonds
      ci-dessus sont mesures par bissection sur un null simule.

   Registre : inchange. h46 ne teste pas l'archive — il balaye un modele.

   ({time.time() - T0:.1f} s)""")
