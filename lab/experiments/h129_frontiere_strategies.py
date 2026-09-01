"""h129 — LA FRONTIÈRE (TAUX DE GAIN, RENDEMENT) : ce qu'une stratégie peut
atteindre, ce qu'aucune ne peut, et le tournoi de l'archive qui le mesure.

LA QUESTION POSÉE
==================
« Existe-t-il des stratégies à haut taux de gain ET à haut rendement ? »

Le dossier a des THÉORÈMES sur le rendement (§29, §30, §57, §62, §107) mais
jamais la carte complète que la question demande : pour CHAQUE stratégie
possible, où tombe le couple (taux de gain, rendement) ? Cette section la
dresse, la démontre, et la confronte à l'archive entière.

LE THÉORÈME DE DÉCOUPLAGE
==========================
Soit une stratégie CAUSALE : une grille G_t de k numéros choisie comme une
fonction quelconque du passé strict (tirages < t, horodatages, bonus, ce qu'on
veut). Sous l'hypothèse que le dossier a testée plus de 60 000 fois sans la
mettre en défaut — le tirage t est uniforme sur C(80,20) et indépendant du
passé —, le nombre de touches H_t = |G_t ∩ D_t| vérifie

    H_t | passé  ~  Hypergéométrique(80, 20, k),        QUELLE QUE SOIT G_t.

Preuve : conditionnellement au passé, G_t est fixée, et D_t est uniforme sur
les 20-parties de [80] ; le nombre de points d'une partie uniforme dans un
ensemble fixé de taille k est hypergéométrique. []

Donc pour toute stratégie causale et tout barème g_k :

    taux de gain  P(g_k(H) > 0)  =  somme_h p_k(h) 1[g_k(h) > 0]
    rendement     E[g_k(H)] / c  =  somme_h p_k(h) g_k(h) / c

NE DÉPENDENT QUE DE k ET DU BARÈME. Le choix des numéros — chauds, froids,
retards, paires, heure du jour, réseau de neurones — n'apparaît dans AUCUNE
des deux formules. Une « stratégie » au sens des vendeurs de méthodes n'est
donc PAS un point différent de la carte : c'est le MÊME point que le hasard.

CE QUI RESTE À CHOISIR, ET C'EST TOUT
======================================
Deux leviers, et deux seulement, déplacent un point de la carte :

(1) LA TAILLE DE GRILLE k, et le NOMBRE DE GRILLES (les « systèmes »). Ils
    déplacent le TAUX DE GAIN — vers 1 si l'on veut, en achetant assez de
    grilles — sans bouger le rendement d'un centime. Le taux de gain est un
    choix de VARIANCE, pas d'espérance.

(2) LA CAGNOTTE BANGO J. Elle est la seule quantité qui déplace le RENDEMENT :
    rendement(J) = rendement(0) + J p_k(k) / c, et franchit 100 % au seuil
    J* = (c − E[g_k]) / p_k(k) — CHF 6 385 à la mise 6 (§57, §62).

Les deux axes sont DÉCOUPLÉS : on peut avoir n'importe quel taux de gain à
rendement fixé, et le rendement ne se choisit pas, il se LIT sur la cagnotte.
« Haut taux de gain ET haut rendement » n'est donc pas une stratégie à trouver,
c'est un point de la carte à ATTENDRE — quand J > J* — puis à jouer avec
autant de grilles qu'on veut de taux de gain.

CE QUE CE FICHIER MESURE, SUR L'ARCHIVE ENTIÈRE
================================================
Un théorème est une chose ; le dossier exige la MESURE. Donc :

  A. la carte exacte, pour les cinq mises, avec et sans cagnotte ;
  B. les systèmes : jusqu'où le taux de gain monte à rendement constant ;
  C. LE TOURNOI : vingt-deux règles de sélection causales — chaudes, froides,
     retards, fenêtres, tendance, compagnes, successeurs, heure du jour, jour
     de semaine, bas, haut, hasard — croisées avec les cinq mises, rejouées
     en marche avant sur les 69 560 tirages qui suivent l'échauffement, avec
     le contrôle de fuite du laboratoire, et comparées à la carte ;
  D. LE PIÈGE DE L'OPTIMISEUR : 10 000 grilles fixes optimisées sur la
     première moitié, évaluées sur la seconde — la taille EXACTE du mirage
     que produit tout « optimiseur de stratégies » ;
  E. LA MESURE HONNÊTE : une seule martingale de mélange sur les 110
     cellules du tournoi (Ville : P(sup W ≥ 20) ≤ 0,05 sans correction), et
     sa puissance mesurée sur des archives plantées avec une persistance
     d'un tirage à l'autre.

Il TESTE l'archive : il consigne au registre.
"""

import csv
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H129_DRY") == "1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POOL, DRAWN = 80, 20
MISES = (5, 6, 7, 8, 10)
PRIX = 2.0                     # CHF par grille, règlement (§62)
ECHAUFF = 1000                 # la plus longue fenêtre des règles
RNG = np.random.default_rng(129)


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# ==========================================================================
# LE BARÈME, LA CAGNOTTE, LA LOI
# ==========================================================================
BASE = {}
with open(os.path.join(ROOT, "bareme_observed.csv")) as fh:
    for row in csv.DictReader(l for l in fh if not l.startswith("#")):
        BASE.setdefault(int(row["mise"]), {})[int(row["hits"])] = float(row["gain_base"])
GAIN = {k: np.array([BASE[k].get(h, 0.0) for h in range(k + 1)]) for k in MISES}

# Cagnottes BANGO relevées le 2026-08-30 à 22:16 (lab/jackpots_observed.csv)
BANGO = {5: 245.0, 6: 3035.0, 7: 3838.0, 8: 13051.0, 10: 498218.0}

PMF = {k: lab.hits_pmf(k) for k in MISES}


def carte(k, J=0.0):
    """Le point (taux de gain, rendement) d'une grille de k, cagnotte J."""
    p, g = PMF[k], GAIN[k].copy()
    g[k] += J
    return dict(
        touche=float(p[g > 0].sum()),           # gagne quelque chose
        sans_perte=float(p[g >= PRIX].sum()),   # ne perd pas sa mise
        net=float(p[g > PRIX].sum()),           # profit net
        rendement=float((p * g).sum() / PRIX),
        sigma=float(math.sqrt((p * g * g).sum() - (p * g).sum() ** 2)),
    )


# ==========================================================================
# A. LA CARTE EXACTE
# ==========================================================================
rule("A. LA CARTE (TAUX DE GAIN, RENDEMENT) — exacte, pour toute stratégie causale")

say("""   Sous le null que le dossier n'a jamais mis en défaut, H | passé est
   hypergéométrique(80,20,k) pour TOUTE grille choisie à partir du passé.
   Les deux colonnes ne dépendent donc que de k et du barème — la sélection
   des numéros n'y entre pas. Cagnotte J = 0 :

   mise   P(gagne qqch)   P(ne perd pas)   P(profit net)   rendement    sigma(gain)""")
CARTE0 = {k: carte(k) for k in MISES}
for k in MISES:
    c = CARTE0[k]
    say(f"   {k:>4}   {c['touche']:>13.4f}   {c['sans_perte']:>14.4f}   "
        f"{c['net']:>13.4f}   {c['rendement']:>9.4f}   {c['sigma']:>11.2f}")

say("""
   Le rendement est le même aux cinq mises à 0,1 % près (le §56 l'avait mesuré :
   l'opérateur égalise). Le taux de gain, lui, varie d'un facteur trois entre
   la mise 10 — dont le 0/10 rend la mise — et la mise 5. C'est le premier
   énoncé de la frontière : à cagnotte nulle, tout point admissible a un
   rendement de 58,8 % et un taux de gain dans une COLONNE, pas dans une ligne.

   Avec la cagnotte BANGO relevée le 30 août 2026 à 22:16 :

   mise   cagnotte J    p(plein)     rendement(J)   seuil J*    J / J*""")
SEUIL = {}
for k in MISES:
    pk = float(PMF[k][k])
    E0 = CARTE0[k]["rendement"] * PRIX
    Js = (PRIX - E0) / pk
    SEUIL[k] = Js
    cJ = carte(k, BANGO[k])
    say(f"   {k:>4}   {BANGO[k]:>10,.0f}   {pk:.3e}   {cJ['rendement']:>12.4f}   "
        f"{Js:>9,.0f}   {BANGO[k]/Js:>6.3f}")

say(f"""
   La cagnotte est le SEUL levier du rendement. Le jour du relevé elle en
   relevait la mise 6 de {100*(carte(6, BANGO[6])['rendement']-CARTE0[6]['rendement']):.1f} points,
   à {100*carte(6, BANGO[6])['rendement']:.1f} % — encore sous 100 %. Le seuil
   J* = {SEUIL[6]:,.0f} CHF à la mise 6 est celui du §57 (CHF 6 385), retrouvé.""")


# ==========================================================================
# B. LES SYSTÈMES : le taux de gain à rendement constant
# ==========================================================================
rule("B. LES SYSTÈMES — le taux de gain se monte, le rendement ne bouge pas")

say("""   Un « système » joue les C(m,k) grilles de k numéros contenues dans m numéros.
   Si H est le nombre de touches parmi les m, le nombre de grilles à h touches
   vaut C(H,h)·C(m−H,k−h) — le gain TOTAL est donc une fonction exacte de H,
   et H est hypergéométrique(80,20,m). Coût C(m,k)·2 CHF.

   mise   m   grilles   coût CHF   P(une grille paie)   P(total ≥ coût)   rendement""")
SYST = []
for k in MISES:
    for m in range(k, 21):
        ng = math.comb(m, k)
        cout = ng * PRIX
        if cout > 500:
            break
        pm = lab.hits_pmf(m)
        p_paie = p_sans = 0.0
        esp = 0.0
        for H in range(m + 1):
            total = 0.0
            paie = False
            for h in range(max(0, H + k - m), min(k, H) + 1):
                n_h = math.comb(H, h) * math.comb(m - H, k - h)
                total += n_h * GAIN[k][h]
                if n_h and GAIN[k][h] > 0:
                    paie = True
            p_paie += pm[H] * paie
            p_sans += pm[H] * (total >= cout)
            esp += pm[H] * total
        SYST.append((k, m, ng, cout, p_paie, p_sans, esp / cout))
        if m == k or m in (k + 2, k + 4) or cout > 250:
            say(f"   {k:>4}  {m:>2}   {ng:>7}   {cout:>8.0f}   {p_paie:>18.4f}   "
                f"{p_sans:>15.4f}   {esp/cout:>9.4f}")

best = max(SYST, key=lambda s: s[4])
say(f"""
   Le taux « une grille paie » monte jusqu'à {100*best[4]:.1f} % (mise {best[0]},
   {best[1]} numéros, {best[2]} grilles, {best[3]:.0f} CHF) ; le rendement reste
   0,588 sur TOUTES les lignes — c'est la linéarité de l'espérance, et c'est le
   théorème : le taux de gain est un choix de variance, jamais d'espérance.
   La colonne « P(total ≥ coût) » — ne rien perdre — reste sous celle d'une
   grille seule : multiplier les grilles multiplie aussi les façons de perdre.""")


# ==========================================================================
# C. LE TOURNOI DE L'ARCHIVE
# ==========================================================================
rule("C. LE TOURNOI — vingt-deux règles causales x cinq mises, en marche avant")

ARCH = lab.load()
ARCH.build_index()
N = len(ARCH)
MASK = ARCH.mask
STOP = 4000 if DRY else N
NB = STOP - ECHAUFF

# Chaque règle rend un SCORE sur les 80 numéros ; la grille de k est le top-k
# (ex aequo : le plus petit numéro d'abord, argsort stable). Les grilles des
# cinq mises sont donc emboîtées : un classement par règle et par tirage.
#
# Deux écritures par règle : l'incrémentale (pour la marche, un état porté
# d'un tirage au suivant) et celle « depuis le passé » (pour le contrôle de
# fuite, qui réécrit l'archive et exige une fonction pure du passé). Leur
# égalité est vérifiée en cours de marche.
SLOTS = 288
slot = ((ARCH.ts // 300) % SLOTS).astype(np.int64)
jour = ((ARCH.ts // 86400 + 4) % 7).astype(np.int64)
PERM_FIXE = RNG.permutation(POOL).astype(np.float64)


class Etat:
    """L'état incrémental : tout ce qui est en O(80^2) à recalculer."""

    def __init__(self, t):
        self.t = t
        # produits en float32 (BLAS, exacts sous 2^24) puis entiers
        M = MASK[:t].astype(np.float32)
        self.paires = (M.T @ M).astype(np.int32)        # co-occurrences
        self.succ = (M[:-1].T @ M[1:]).astype(np.int32)  # i en t-1, j en t
        S = np.zeros((t, SLOTS), np.float32)
        S[np.arange(t), slot[:t]] = 1.0
        self.cslot = (S.T @ M).astype(np.int32)
        J = np.zeros((t, 7), np.float32)
        J[np.arange(t), jour[:t]] = 1.0
        self.cjour = (J.T @ M).astype(np.int32)

    def avance(self):
        """Intègre le tirage t (il devient passé) ; t -> t+1."""
        t = self.t
        m = MASK[t].astype(np.int32)
        self.paires += np.outer(m, m)
        if t >= 1:
            self.succ += np.outer(MASK[t - 1].astype(np.int32), m)
        self.cslot[slot[t]] += m
        self.cjour[jour[t]] += m
        self.t = t + 1


def scores_inc(past, e):
    """Les scores des règles, incrémental. past.t == e.t."""
    t = past.t
    c = past.counts.astype(np.float64)
    g = past.gaps.astype(np.float64)
    w10, w50 = past.counts_window(10), past.counts_window(50)
    w200, w1000 = past.counts_window(200), past.counts_window(1000)
    dern = MASK[t - 1]
    ordre_dern = np.where(dern, 1.0, 0.0)
    rt = np.random.default_rng(t).permutation(POOL).astype(np.float64)
    return {
        "chaud_tout": c, "froid_tout": -c,
        "chaud_10": w10, "froid_10": -w10,
        "chaud_50": w50, "froid_50": -w50,
        "chaud_200": w200, "froid_200": -w200,
        "chaud_1000": w1000, "froid_1000": -w1000,
        "retard_max": g, "retard_min": -g,
        "tendance": w200 - 0.2 * w1000,
        "compagnes": e.paires[:, dern].sum(1) - ordre_dern * 1e9,
        "successeurs": e.succ[dern, :].sum(0),
        "anti_succ": -e.succ[dern, :].sum(0),
        "heure": e.cslot[slot[t]],
        "jour": e.cjour[jour[t]],
        "bas": -np.arange(POOL, dtype=np.float64),
        "haut": np.arange(POOL, dtype=np.float64),
        "hasard_fixe": PERM_FIXE,
        "hasard_t": rt,
    }


def scores_pur(past):
    """Les mêmes scores, fonction pure du passé (pour le contrôle de fuite)."""
    return scores_inc(past, Etat(past.t))


REGLES = list(scores_inc(lab.Past(ARCH, ECHAUFF), Etat(ECHAUFF)).keys())
R = len(REGLES)


def topk(score, k):
    return np.argsort(-score, kind="stable")[:k] + 1


# --- la marche avant --------------------------------------------------------
say(f"   {R} règles : {', '.join(REGLES)}")
say(f"   marche avant sur les tirages {ECHAUFF}..{STOP-1} ({NB:,} tirages)")
HITS = np.zeros((R, 5, NB), np.int8)          # touches par règle, mise, tirage
CONTROLES = set(np.linspace(ECHAUFF, STOP - 1, 5, dtype=int).tolist())
past = lab.Past(ARCH, ECHAUFF)
et = Etat(ECHAUFF)
ta = time.time()
for t in range(ECHAUFF, STOP):
    past.t = t
    sc = scores_inc(past, et)
    if t in CONTROLES:
        sp = scores_pur(past)
        for r in REGLES:
            assert np.array_equal(topk(sc[r], 10), topk(sp[r], 10)), (t, r)
    m = MASK[t]
    for i, r in enumerate(REGLES):
        ordre = np.argsort(-sc[r], kind="stable")[:10]
        cum = np.cumsum(m[ordre])
        for j, k in enumerate(MISES):
            HITS[i, j, t - ECHAUFF] = cum[k - 1]
    et.avance()
    if (t - ECHAUFF + 1) % 10000 == 0:
        say(f"     {t-ECHAUFF+1:>6} tirages   {time.time()-ta:6.0f} s")
say(f"   marche : {time.time()-ta:.0f} s ; l'incrémental et le pur coïncident "
    f"aux {len(CONTROLES)} points de contrôle")

# --- le contrôle de fuite du laboratoire -----------------------------------
say("\n   contrôle de fuite (lab.leak_check, l'archive réécrite à partir de t) :")


def pred_toutes(p, t):
    """Les top-10 des R règles, concaténés et étiquetés par règle : le contrôle
    compare le vecteur entier, donc UNE règle qui bougerait suffit à échouer."""
    sp = scores_pur(p)
    return np.concatenate([topk(sp[r], 10) + 100 * i for i, r in enumerate(REGLES)])


PROPRE, SPOTS = lab.leak_check(ARCH, pred_toutes, k=10, warmup=ECHAUFF,
                               probes=4 if DRY else 8, repeats=3 if DRY else 6)
say(f"     {'les ' + str(R) + ' règles sont propres' if PROPRE else 'FUITE aux positions ' + str(SPOTS)}"
    f" ({4 if DRY else 8} instants x {3 if DRY else 6} futurs réécrits)")
assert PROPRE, "une règle lit le futur : le tournoi est invalide"

# --- la table du tournoi ----------------------------------------------------
say(f"""
   Chaque cellule : taux de gain et rendement EMPIRIQUES sur {NB:,} tirages, contre
   la carte exacte ; z = écart du rendement en erreurs types ; log10 e = e-valeur
   de mélange du laboratoire sur la loi des touches (lab.evalue).

   règle           mise   P(gagne) exact    rendement  exact    z     log10 e""")
TABLE = []
LOG_E = np.zeros((R, 5))
for i, r in enumerate(REGLES):
    for j, k in enumerate(MISES):
        h = HITS[i, j]
        gain = GAIN[k][h]
        pg = float((gain > 0).mean())
        rd = float(gain.mean() / PRIX)
        se = CARTE0[k]["sigma"] / math.sqrt(NB) / PRIX
        z = (rd - CARTE0[k]["rendement"]) / se
        e, le = lab.evalue(h, k)
        LOG_E[i, j] = le
        TABLE.append((r, k, pg, rd, z, le))
        if k in (6, 10) or DRY:
            say(f"   {r:<15} {k:>4}   {pg:>8.4f} {CARTE0[k]['touche']:>6.4f}   "
                f"{rd:>9.4f} {CARTE0[k]['rendement']:>6.4f}  {z:>+5.2f}  {le:>+8.3f}")

Z = np.array([t[4] for t in TABLE])
RD = np.array([t[3] for t in TABLE])
PG = np.array([t[2] for t in TABLE])
best_cell = max(TABLE, key=lambda t: t[3])
say(f"""
   {R*5} cellules. Rendement : min {RD.min():.4f}, max {RD.max():.4f} (règle
   « {best_cell[0]} », mise {best_cell[1]}) ; z de −{-Z.min():.2f} à +{Z.max():.2f}.
   Taux de gain : chaque cellule à moins de {100*np.abs(PG - np.array([CARTE0[t[1]]['touche'] for t in TABLE])).max():.2f}
   point de sa valeur exacte.""")

# La calibration : que vaut le MAX d'un tournoi de 100 cellules SANS signal ?
# Les cellules d'une même règle sont emboîtées (corrélées), on simule donc le
# tournoi entier sur des touches hypergéométriques emboîtées, pas 100 cellules
# libres. Les dix numéros d'une grille sont tirés un à un sans remise dans une
# urne de 80 dont 20 sont marqués : c'est exactement la loi des touches
# emboîtées d'une grille quelconque sous le null.


def touches_emboitees(n, rng):
    out = np.zeros((n, 10), bool)
    marques = np.full(n, DRAWN, np.int64)
    for i in range(10):
        x = rng.random(n) < marques / (POOL - i)
        out[:, i] = x
        marques -= x
    return out


say("\n   calibration : le maximum du z sur un tournoi de même taille, sans signal")
MAXZ = []
for rep in range(20 if DRY else 200):
    zz = []
    for i in range(R):
        cum = np.cumsum(touches_emboitees(NB, RNG), axis=1)
        for j, k in enumerate(MISES):
            g = GAIN[k][cum[:, k - 1]]
            se = CARTE0[k]["sigma"] / math.sqrt(NB) / PRIX
            zz.append((g.mean() / PRIX - CARTE0[k]["rendement"]) / se)
    MAXZ.append(max(zz))
MAXZ = np.array(MAXZ)
say(f"     max z sans signal : médiane {np.median(MAXZ):+.2f}, 95 % {np.quantile(MAXZ, .95):+.2f}, "
    f"99 % {np.quantile(MAXZ, .99):+.2f}")
say(f"     max z observé     : {Z.max():+.2f}   -> fraction des tournois nuls qui font "
    f"mieux : {float((MAXZ >= Z.max()).mean()):.2f}")


# ==========================================================================
# D. LE PIÈGE DE L'OPTIMISEUR
# ==========================================================================
rule("D. LE PIÈGE DE L'OPTIMISEUR — 10 000 grilles fixes, moitié contre moitié")

say("""   Tout « optimiseur de stratégies » fait ceci : il essaie beaucoup de grilles
   sur le passé, garde la meilleure, et annonce SON rendement. Voici la taille
   exacte du mirage, sur l'archive réelle : 10 000 grilles fixes tirées au
   hasard, sélectionnées sur la première moitié, jugées sur la seconde.

   mise    grilles   meilleur rendement    la même grille         rang de la
                     sur la 1re moitié     sur la 2de moitié      2de moitié""")
NG = 500 if DRY else 10000
moitie = ECHAUFF + NB // 2
M1 = MASK[ECHAUFF:moitie].astype(np.float32)
M2 = MASK[moitie:STOP].astype(np.float32)
OPT = {}
for k in MISES:
    G = np.zeros((POOL, NG), np.float32)
    for c in range(NG):
        G[RNG.choice(POOL, k, replace=False), c] = 1.0
    r1 = np.empty(NG)
    r2 = np.empty(NG)
    for a in range(0, NG, 500):                        # par morceaux : mémoire
        h1 = (M1 @ G[:, a:a + 500]).astype(np.int64)   # touches, 1re moitié
        h2 = (M2 @ G[:, a:a + 500]).astype(np.int64)
        r1[a:a + 500] = GAIN[k][h1].mean(0) / PRIX
        r2[a:a + 500] = GAIN[k][h2].mean(0) / PRIX
    b = int(np.argmax(r1))
    rang = int((r2 >= r2[b]).sum())
    OPT[k] = (r1[b], r2[b], r1.mean(), r2.mean())
    say(f"   {k:>4}   {NG:>8}   {r1[b]:>18.4f}   {r2[b]:>20.4f}   {rang:>7}/{NG}")
SE_DEMI = {k: CARTE0[k]["sigma"] / math.sqrt(NB // 2) / PRIX for k in MISES}
say(f"""
   Le « meilleur rendement » est un maximum sur {NG:,} tirages hypergéométriques
   indépendants : il dépasse la carte de plusieurs erreurs types PAR
   CONSTRUCTION (l'erreur type d'UNE grille sur une moitié vaut
   {', '.join(f'{SE_DEMI[k]:.3f} à la mise {k}' for k in MISES)}). La même grille,
   sur la moitié qu'elle n'a pas vue, retombe dans le bruit de 0,588 — et son
   rang y est celui du hasard. C'est le théorème de découplage vu du côté de
   l'optimiseur : ce qu'il « trouve » est le bruit qu'il a sélectionné.""")


# ==========================================================================
# E. LA MESURE HONNÊTE : une martingale, et sa puissance
# ==========================================================================
rule("E. LA MARTINGALE DE MÉLANGE, ET SA PUISSANCE MESURÉE")

# e-valeur de mélange à poids uniformes sur les R x 5 cellules : une seule
# martingale (Ville), donc une seule barre à 20, quel que soit R.
mx = LOG_E.max()
E_MIX = mx + math.log10(np.mean(10.0 ** (LOG_E - mx)))
P_MIX = min(1.0, 10.0 ** (-E_MIX))
say(f"""   Le mélange à poids uniformes des {R*5} e-processus est un e-processus :
   par l'inégalité de Ville, P(sup ≥ 20) ≤ 0,05 SANS correction de multiplicité.

     log10 e du mélange = {E_MIX:+.3f}     (barre : +1,301)
     meilleure cellule  = {mx:+.3f}     ({TABLE[int(np.argmax(LOG_E))][0]}, mise {TABLE[int(np.argmax(LOG_E))][1]})
     p                  = {P_MIX:.3f}""")

# Puissance : une archive PLANTÉE avec persistance — chaque numéro du tirage
# t-1 est repris en t avec un excès eps — et la règle « retard_min » qui la
# vise. À quel eps le mélange (ici sur la seule règle visée x 5 mises, ce qui
# est PLUS FAIBLE que le mélange complet) franchit-il 20 ?


def archive_persistante(n, eps, rng):
    M = np.zeros((n, POOL), bool)
    M[0] = lab.srs(1, rng)[0]
    for t in range(1, n):
        prev = np.flatnonzero(M[t - 1])
        garde = prev[rng.random(DRAWN) < eps]            # numéros repris
        reste = np.setdiff1d(np.arange(POOL), garde)
        autres = rng.choice(reste, DRAWN - len(garde), replace=False)
        M[t, garde] = True
        M[t, autres] = True
    return M


say("\n   puissance : archive plantée, persistance eps d'un tirage au suivant")
say("     eps      log10 e (retard_min, mélange sur les 5 mises)   détecté")
NP = 3000 if DRY else NB
PUIS = {}
for eps in (0.0, 0.01, 0.02, 0.03, 0.05):
    rng = np.random.default_rng(1000 + int(1000 * eps))
    Mp = archive_persistante(NP + 1, eps, rng)
    les = []
    for k in MISES:
        # retard_min : les numéros du tirage précédent (ex aequo : plus petits)
        h = np.array([Mp[t][np.flatnonzero(Mp[t - 1])[:k]].sum() for t in range(1, NP + 1)])
        les.append(lab.evalue(h, k)[1])
    les = np.array(les)
    m_ = les.max()
    lm = m_ + math.log10(np.mean(10.0 ** (les - m_)))
    PUIS[eps] = lm
    say(f"     {eps:.2f}   {lm:>+12.3f}                                    {'oui' if lm >= 1.301 else 'non'}")
EPS_DET = min([e for e, v in PUIS.items() if v >= 1.301], default=None)
say(f"""
   Une persistance de {EPS_DET if EPS_DET is not None else '> 0,05'} — soit
   {20*EPS_DET if EPS_DET else 0:.1f} numéro repris en moyenne par tirage, sur 20 —
   est détectée. Sur l'archive réelle le même instrument lit {LOG_E[REGLES.index('retard_min')].max():+.3f}
   sur sa meilleure mise : rien.""")


# ==========================================================================
# F. CONSIGNATION
# ==========================================================================
rule("F. CONSIGNATION")

if DRY:
    say("   MODE ESSAI : rien n'est consigné.")
else:
    tok = lab.preregister(
        "h129.frontiere_strategies",
        f"Aucune des {R} règles de sélection causales (chaudes, froides, retards, "
        f"fenêtres, tendance, compagnes, successeurs, heure, jour, bas, haut, "
        f"hasard) croisées avec les cinq mises ne quitte la frontière "
        f"(taux de gain, rendement) exacte du barème sur les {NB:,} tirages de "
        f"l'archive en marche avant",
        f"e-valeur de mélange à poids uniformes (lab.evalue, grille signée) sur "
        f"les {R*5} cellules du tournoi ; en regard, rendement et taux de gain "
        f"empiriques par cellule contre la carte exacte, et le max du z calibré "
        f"par 200 tournois simulés de même forme",
        "exact : sous H0 les touches de toute grille causale sont "
        "hypergéométriques(80,20,k) ; le mélange est une martingale, Ville donne "
        "P(sup >= 20) <= 0,05 sans correction de multiplicité",
        "conforme si l'e-valeur du mélange reste sous 20 (log10 e < 1,301)",
        track="B")
    tok["m_extra"] = 0
    lab.record(
        tok, float(E_MIX), p=float(P_MIX),
        verdict="conforme" if E_MIX < 1.301 else "REJET",
        power_at=(f"puissance mesurée par plantation : une persistance de "
                  f"{EPS_DET} d'un tirage au suivant ({20*EPS_DET if EPS_DET else 0:.1f} "
                  f"numéro repris sur 20) porte le mélange au-delà de 20"),
        notes=(f"Théorème de découplage : pour toute grille causale H|passé ~ "
               f"Hyp(80,20,k), donc taux de gain et rendement ne dépendent que de "
               f"k et du barème ; le taux se monte par les systèmes à rendement "
               f"constant (jusqu'à {100*best[4]:.1f} %), le rendement ne bouge que par "
               f"la cagnotte (seuil J* = {SEUIL[6]:,.0f} CHF à la mise 6). Tournoi : "
               f"{R*5} cellules, rendement de {RD.min():.4f} à {RD.max():.4f} contre "
               f"0,588 exact, max z {Z.max():+.2f} (95 % des tournois nuls : "
               f"{np.quantile(MAXZ, .95):+.2f}). Optimiseur : meilleure de {NG:,} grilles "
               f"fixes, rendement {OPT[6][0]:.4f} en échantillon, {OPT[6][1]:.4f} hors "
               f"échantillon (mise 6). Contrôle de fuite : les {R} règles propres "
               f"sur 8 instants x 6 futurs réécrits."))
    h = lab.holm()
    say(f"   consigné : h129.frontiere_strategies   log10 e = {E_MIX:+.3f}   p = {P_MIX:.3f}")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")

say(f"\n   durée totale : {time.time()-T0:.0f} s")
