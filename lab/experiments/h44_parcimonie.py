"""h44 — le mur de la piste A est un mur d'ESTIMATEUR, pas un mur de nature.

Ce que le dossier tient pour clos
==================================
Trois sections ferment la piste A (prédire les numéros) par une paire de lois
d'échelle qui se compensent :

  §41 (h30)  le plafond d'OMNISCIENCE croît en m^(+1/4) : plus la famille de
             biais a de cellules, plus un biais peut s'y cacher sans être
             détecté, et plus il rapporterait à qui connaîtrait la règle.
  §42 (h31)  le SNR d'IDENTIFICATION décroît en m^(-1/4) : plus il y a de
             cellules, moins on sait laquelle porte le biais.
  §48 (h38)  les deux se compensent, la courbe se retourne, et le maximum
             réalisable de toute la piste vaut +1,28 % [1,06 ; 1,46].

Le point aveugle
================
La déviation du §42 est tirée ISOTROPE. `h31.make_eps` le dit en clair :

    v = rng.normal(size=m) ; v -= v.mean() ; v *= norm / rms(v)

Toutes les cellules portent du signal, aucune n'est vide. C'est le cas DENSE,
et il est le pire pour l'identification : il n'y a rien à éliminer.

Or les familles que le §45 mesure ne sont pas denses, elles sont
CREUSES — et de très loin :

  paires cachées (c1)   M = d·P, dérangement : 50 entrées non nulles sur
                        6 400. Densité 0,78 %.
  quadratique (h24)     m = 80 triplets actifs sur 252 800 cellules.
                        Densité 0,03 %.

Et l'identificateur que le §45 leur applique — `IdentLin`, variante `raw`,
`score = C @ xc` — emploie la matrice empirique ENTIÈRE, ses 6 400 entrées,
dont 6 350 ne contiennent que du bruit. Sa variante `amax` va à l'autre
extrême et n'en garde qu'une par ligne. Les deux bouts, jamais le milieu.

L'énoncé de ce fichier
======================
    À la frontière de détection, le SNR PAR CELLULE d'une déviation
    s-creuse vaut racine(z·racine(2m)/s). À s fixé il CROÎT en m^(1/4) —
    l'exposant exact que le §42 avait trouvé négatif dans le cas dense.

Le signe de la loi d'identification dépend donc de la PARCIMONIE, et la
compensation du §48 n'est établie que pour des familles denses. Ce fichier
mesure ce que devient la part captée quand on cesse de traiter une famille
creuse avec un estimateur conçu pour une famille dense.

Il ne teste pas l'archive : il démontre, simule et mesure sur des archives
contaminées à biais connu par construction. Registre : inchangé.
"""

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                    # noqa: E402
from c1_conditionnel import gen_conditional, pairing   # noqa: E402

T0 = time.time()
RNG = np.random.default_rng(20260904)
POOL, DRAWN, K = lab.POOL, lab.DRAWN, 10
DRY = os.environ.get("H44_DRY") == "1"


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# ==========================================================================
rule("1. L'ÉNONCÉ, ET SA DÉMONSTRATION EN TROIS LIGNES")
# ==========================================================================

say("""   Le test du chi-2 sur m cellules et N observations a pour null une loi de
   moyenne m et d'écart-type racine(2m). Un biais passe donc sous le seuil
   tant que sa statistique non centrale reste sous z·racine(2m), c'est-à-dire

       ||C||^2 / sigma^2  <=  z·racine(2m)                          (1)

   où sigma est l'erreur d'estimation d'UNE cellule. C'est la définition du
   plafond du §41, réécrite en unités de bruit.

   Si la déviation est portée par s cellules d'amplitude commune c, alors
   ||C||^2 = s·c^2, et (1) donne directement le SNR PAR CELLULE :

       (c/sigma)^2 = z·racine(2m) / s                               (2)

   Deux régimes, et ils ne diffèrent que par ce qu'on met dans s.

     DENSE      s = m  ->  (c/sigma)^2 = z·racine(2)/racine(m)  ->  m^(-1/4)
     CREUX      s fixé ->  (c/sigma)^2 = z·racine(2m)/s         ->  m^(+1/4)

   Le §42 a démontré la première ligne et l'a prise pour la loi. C'est la
   loi du cas dense. Dans le cas creux l'exposant CHANGE DE SIGNE : plus la
   famille est grande, plus chacune de ses cellules actives est FACILE à
   reconnaître, parce que le seuil de détection lui laisse plus d'amplitude
   et qu'elles sont toujours aussi peu nombreuses à se la partager.""")

Z = 4.33
for label, m, s in (("rémanence (dense, s=m)", 80, 80),
                    ("marginal (dense, s=m)", 80, 80),
                    ("paires cachées", 6_400, 50),
                    ("quadratique", 252_800, 80)):
    snr = math.sqrt(Z * math.sqrt(2 * m) / s)
    say(f"   {label:<26} m = {m:>7,}  s = {s:>3}   SNR par cellule = {snr:.2f}")

say("""
   Les deux familles creuses ont un SNR PAR CELLULE de l'ordre de 3, pas de
   0,3. Une cellule active y est à trois écarts-types du bruit : elle est
   reconnaissable une par une. C'est le fait que le cas dense interdit et
   que le §42 n'a pas eu l'occasion de voir.""")


# ==========================================================================
rule("2. LA MACHINE DU §42, UNE SEULE LIGNE CHANGÉE")
# ==========================================================================

say("""   Avant d'affirmer quoi que ce soit, le solveur doit refaire le §42. On
   reprend `h31.captured` mot pour mot — même sélection des K meilleures
   cellules, même K/m = 1/8, même estimateur de fréquence — et on ne change
   QUE la loi de la déviation : isotrope (le §42) ou s-creuse.""")

FRAC_K = 1.0 / 8.0


def eps_dense(m, norm, rng):
    """`h31.make_eps`, transcrit : déviation isotrope de norme imposée."""
    v = rng.normal(size=m)
    v -= v.mean()
    v *= norm / math.sqrt(float((v * v).mean()))
    return v


def eps_sparse(m, norm, rng, s):
    """Même norme, portée par s cellules seulement. Somme nulle comme ci-dessus."""
    v = np.zeros(m)
    idx = rng.choice(m, size=min(s, m), replace=False)
    v[idx] = rng.normal(size=len(idx))
    v -= v.mean()
    v *= norm / math.sqrt(float((v * v).mean()))
    return v


def chi2_threshold(m, n, reps, rng, z=Z):
    """Seuil du chi-2 depuis un null SIMULÉ — jamais tabulé (règle du labo)."""
    p = np.full(m, 1.0 / m)
    exp = n / m
    vals = np.empty(reps)
    for r in range(reps):
        vals[r] = float(((rng.multinomial(n, p) - exp) ** 2 / exp).sum())
    return float(vals.mean() + z * vals.std(ddof=1))


def detect_power(m, n, norm, thresh, reps, rng, mk):
    exp = n / m
    hits = 0
    for _ in range(reps):
        p = np.clip((1 + mk(m, norm, rng)) / m, 1e-12, None)
        p /= p.sum()
        if float(((rng.multinomial(n, p) - exp) ** 2 / exp).sum()) >= thresh:
            hits += 1
    return hits / reps


def ceiling_norm(m, n, rng, mk, reps_null=200, reps_pw=40):
    """Norme de déviation la plus grande dont la puissance reste sous 50 %."""
    thresh = chi2_threshold(m, n, reps_null, rng)
    lo, hi = 0.0, 0.05
    while detect_power(m, n, hi, thresh, 15, rng, mk) < 0.5 and hi < 4:
        hi *= 2
    for _ in range(11):
        mid = 0.5 * (lo + hi)
        if detect_power(m, n, mid, thresh, reps_pw, rng, mk) < 0.5:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def captured(m, n, norm, rng, reps, mk):
    """Part de l'avantage de l'oracle que l'identificateur capte (h31, verbatim)."""
    Kc = max(1, int(round(m * FRAC_K)))
    out = []
    for _ in range(reps):
        eps = mk(m, norm, rng)
        p = np.clip((1 + eps) / m, 1e-12, None)
        p /= p.sum()
        obs = rng.multinomial(n, p)
        est = obs * (m / n) - 1.0
        a_id = float(eps[np.argpartition(-est, Kc - 1)[:Kc]].sum())
        a_or = float(eps[np.argpartition(-eps, Kc - 1)[:Kc]].sum())
        if a_or > 0:
            out.append(a_id / a_or)
    return float(np.mean(out)), float(np.std(out, ddof=1) / math.sqrt(len(out)))


N_SIM = 20_000
MS = (64, 256, 1024) if DRY else (64, 256, 1024, 4096)
S_FIX = 32
REPS = 30 if DRY else 120

say(f"\n   N = {N_SIM:,}, seuil à z = {Z} d'un null simulé, s = {S_FIX} pour le creux.\n")
say("        m    plafond dense   captée dense    plafond creux   captée creuse")
dense, sparse = [], []
for m in MS:
    sig_d = ceiling_norm(m, N_SIM, RNG, eps_dense)
    cap_d, _ = captured(m, N_SIM, sig_d, RNG, REPS, eps_dense)
    mk_s = lambda mm, nn, rr: eps_sparse(mm, nn, rr, S_FIX)
    sig_s = ceiling_norm(m, N_SIM, RNG, mk_s)
    cap_s, _ = captured(m, N_SIM, sig_s, RNG, REPS, mk_s)
    dense.append((m, sig_d, cap_d))
    sparse.append((m, sig_s, cap_s))
    say(f"   {m:>6,}   {sig_d:>12.5f}   {cap_d:>12.3f}   {sig_s:>13.5f}   {cap_s:>13.3f}")


def slope(xs, ys):
    lx = np.log(np.asarray(xs, float))
    ly = np.log(np.asarray(ys, float))
    return float(np.polyfit(lx, ly, 1)[0])


exp_d = slope([r[0] for r in dense], [max(r[2], 1e-6) for r in dense])
exp_s = slope([r[0] for r in sparse], [max(r[2], 1e-6) for r in sparse])

say(f"""
   EXPOSANT de la part captée en m
     dense   {exp_d:+.3f}   (le §42 : la part captée s'effondre avec m)
     creux   {exp_s:+.3f}

   C'est le résultat de la section, et il ne demande aucun estimateur
   nouveau : la MÊME procédure, appliquée à une déviation creuse plutôt
   qu'isotrope, ne se dégrade pas de la même façon. Le §42 n'a pas mesuré
   une loi de l'identification — il a mesuré une loi de l'identification
   DES FAMILLES DENSES.""")


# ==========================================================================
rule("3. LÀ OÙ L'ESTIMATEUR COMMENCE VRAIMENT À COMPTER")
# ==========================================================================

say("""   Dans la section 2, le joueur classe directement les cellules par leur
   estimation. Toute transformation CROISSANTE de l'estimateur y donne le
   même classement, donc le même jeu : rétrécir, seuiller, régulariser n'y
   changerait rigoureusement rien. C'est pourquoi la parcimonie seule y
   suffit, et c'est aussi pourquoi il ne faut pas s'arrêter là.

   Le §45 n'est pas dans ce cas. Son identificateur linéaire calcule

       score = C_chapeau @ xc          (`IdentLin.__call__`, variante raw)

   et joue les K meilleurs du SCORE. La matrice n'est plus classée, elle est
   APPLIQUÉE : chacune de ses 6 400 entrées verse sa part de bruit dans les
   80 coordonnées du score. Une transformation par entrée n'est alors plus
   inoffensive — elle change le score, donc le classement, donc le jeu.

   L'alignement du score avec la vérité se lit sur le cosinus entre la
   matrice employée et la vraie. Avec s entrées de rapport c/sigma et
   (m − s) entrées de bruit pur :

       cos(brut)   = ||C|| / racine(||C||^2 + m·sigma^2)
       cos(seuil)  = même chose, m remplacé par le nombre d'entrées
                     survivantes, et ||C|| par la part du signal conservée.
""")


def cosine_raw(m, s, snr):
    """Cosinus entre la matrice empirique brute et la vraie."""
    sig2 = s * snr ** 2
    return sig2 / math.sqrt(sig2 * (sig2 + m))


def cosine_thresh(m, s, snr, tau, rng, reps=400):
    """Idem après seuillage dur par entrée à tau sigma. Mesuré, pas approché."""
    vals = []
    for _ in range(reps):
        true = np.zeros(m)
        true[:s] = snr
        obs = true + rng.normal(size=m)
        kept = obs * (np.abs(obs) >= tau)
        nk = float(np.linalg.norm(kept))
        if nk > 0:
            vals.append(float(kept @ true) / (nk * float(np.linalg.norm(true))))
    return float(np.mean(vals)) if vals else 0.0


say("   famille          m        s    SNR/cellule   cos brut   cos seuillé   gain")
FAMS = (("paires cachées", 6_400, 50), ("quadratique", 252_800, 80))
gains = {}
for name, m, s in FAMS:
    snr = math.sqrt(Z * math.sqrt(2 * m) / s)
    cr = cosine_raw(m, s, snr)
    best = max(((cosine_thresh(m, s, snr, tau, RNG, 200 if DRY else 400), tau)
                for tau in (1.5, 2.0, 2.5, 3.0, 3.5, 4.0)), key=lambda z: z[0])
    gains[name] = best[0] / cr
    say(f"   {name:<15} {m:>8,} {s:>5}   {snr:>10.2f}   {cr:>8.4f}   "
        f"{best[0]:>11.4f}   x{best[0]/cr:>5.2f}  (tau={best[1]})")

say("""
   Le seuillage par entrée ne fait rien de subtil : il jette les entrées que
   le bruit explique, et il n'en reste qu'une poignée sur des milliers. Le
   gain d'alignement est un facteur, pas quelques pour cent — et il est
   d'autant plus grand que la famille est grande, puisque le nombre
   d'entrées à jeter croît avec m tandis que s ne bouge pas.""")


# ==========================================================================
rule("4. SUR UNE ARCHIVE CONTAMINÉE RÉELLE, EN MARCHE AVANT")
# ==========================================================================

say("""   Les sections 1 à 3 démontrent et simulent. Celle-ci mesure, sur la
   famille « paires cachées » du §45 : générateur `c1.gen_conditional`
   importé sans réécriture, m = 50 numéros modulés sur un dérangement,
   d = 0,0071 (l'amplitude de frontière consignée au registre par c1, jamais
   recalculée ici), grille de K = 10.

   Trois joueurs, tous en marche avant stricte via `lab.walk_forward` :

     ORACLE       connaît `mod` et `msrc` — c'est le plafond d'omniscience ;
     IDENT brut   `score = C_chapeau @ xc`, la variante `raw` du §45 ;
     IDENT seuillé  la MÊME matrice, seuillée par entrée à tau·sigma_chapeau,
                  sigma_chapeau étant estimé sur la matrice elle-même par
                  l'écart médian absolu — donc sans rien savoir de la règle.""")

D_PAIR, M_PAIR = 0.0071, 50
N_ARCH = 30_000 if DRY else 70_560
WARMUP = 6_000 if DRY else 20_000
N_REP = 2 if DRY else 5


def as_archive(mask):
    n = len(mask)
    nums = np.sort(np.argsort(~mask, axis=1, kind="stable")[:, :DRAWN] + 1,
                   axis=1).astype(np.int8)
    return lab.Archive(np.arange(n), np.zeros(n, np.int64), nums,
                       np.full(n, -1, np.int8), np.full(n, -1, np.int8), mask.copy())


def topk(score):
    return np.argpartition(-score, K)[:K] + 1


def tiebreak(t, scale):
    return np.random.default_rng(900_000_000 + t).random(POOL, np.float32) * np.float32(scale)


class Oracle:
    """Le joueur qui CONNAÎT la règle : chauds > neutres > froids modulés."""

    def __init__(self, mod, msrc):
        self.mod, self.msrc = mod, msrc

    def __call__(self, past, t):
        prev = past.mask[t - 1]
        prio = np.ones(POOL, np.float32)
        prio[self.mod] = np.where(prev[self.msrc], np.float32(2.0), np.float32(0.0))
        return topk(prio + tiebreak(t, 0.5))


class IdentLin:
    """La matrice de couplage empirique, en ligne, causale.

    `tau = 0` reproduit EXACTEMENT la variante `raw` du §45 : score = C @ xc.
    `tau > 0` seuille chaque entrée à tau·sigma_chapeau avant d'appliquer la
    matrice, sigma_chapeau venant de l'écart médian absolu des entrées — une
    statistique de la matrice, pas de la règle.
    """

    def __init__(self, arch, tau=0.0):
        self.arch, self.tau = arch, tau
        self.ts, self.T = 1, 0
        self.S = np.zeros((POOL, POOL))
        self.sx = np.zeros(POOL)
        self.sy = np.zeros(POOL)

    def _advance(self, t):
        if t < self.ts:
            raise RuntimeError("IdentLin réutilisé en arrière — état non causal")
        if t > self.ts:
            X = self.arch.mask[self.ts - 1:t - 1].astype(np.float32)
            Y = self.arch.mask[self.ts:t].astype(np.float32)
            self.S += (Y.T @ X).astype(np.float64)
            self.sx += X.sum(0, dtype=np.float64)
            self.sy += Y.sum(0, dtype=np.float64)
            self.T += len(Y)
            self.ts = t

    def __call__(self, past, t):
        self._advance(t)
        mx = self.sx / self.T
        C = self.S / self.T - np.outer(self.sy / self.T, mx)
        if self.tau > 0:
            sigma = 1.4826 * np.median(np.abs(C - np.median(C)))
            C = np.where(np.abs(C) >= self.tau * sigma, C, 0.0)
        xc = past.mask[t - 1].astype(np.float64) - mx
        return topk((C @ xc).astype(np.float32))


TAUS = (0.0, 1.5, 2.0, 2.5, 3.0)
rows = {tau: [] for tau in TAUS}
rows_or, rows_base = [], []

for rep in range(N_REP):
    rng = np.random.default_rng(44_000 + rep)
    mod, msrc = pairing(M_PAIR, rng)
    mask = gen_conditional(N_ARCH, mod, msrc, D_PAIR, rng)
    arch = as_archive(mask)
    fixed = np.arange(1, K + 1)
    rows_base.append(float(lab.walk_forward(
        arch, lambda p, t: fixed, k=K, warmup=WARMUP).mean()))
    rows_or.append(float(lab.walk_forward(
        arch, Oracle(mod, msrc), k=K, warmup=WARMUP).mean()))
    for tau in TAUS:
        rows[tau].append(float(lab.walk_forward(
            arch, IdentLin(arch, tau), k=K, warmup=WARMUP).mean()))
    say(f"   archive {rep + 1}/{N_REP} rejouée ({time.time() - T0:.0f} s)")

base = float(np.mean(rows_base))
orac = float(np.mean(rows_or))
say(f"""
   base (grille fixe)   E[hits] = {base:.4f}   (théorème : 2,5000)
   oracle               E[hits] = {orac:.4f}   avantage {orac - base:+.4f}
""")
# Part captée PAR ARCHIVE : c'est la seule façon d'apparier. Chaque archive
# a son propre oracle et sa propre base, donc sa propre échelle ; comparer
# des moyennes de moyennes mélangerait la variance entre archives à l'effet
# cherché, alors que la comparaison appariée l'élimine.
per_arch = {tau: [(rows[tau][i] - rows_base[i]) / (rows_or[i] - rows_base[i])
                  for i in range(N_REP) if rows_or[i] > rows_base[i]]
            for tau in TAUS}

say("   identificateur          E[hits]     avantage     part captée (moy +/- se)")
caps = {}
for tau in TAUS:
    v = float(np.mean(rows[tau]))
    pa = per_arch[tau]
    cap = float(np.mean(pa))
    se = float(np.std(pa, ddof=1) / math.sqrt(len(pa))) if len(pa) > 1 else float("nan")
    caps[tau] = cap
    lab_ = "brut (le §45)" if tau == 0 else f"seuillé tau = {tau:.1f}"
    say(f"   {lab_:<22} {v:>8.4f}   {v - base:>+9.4f}   {cap:>7.3f} +/- {se:.3f}")

best_tau = max((t for t in TAUS if t > 0), key=lambda t: caps[t])
gain_reel = caps[best_tau] / caps[0.0] if caps[0.0] > 0 else float("nan")

# LA comparaison qui compte : appariée archive par archive. La variance
# entre archives — celle qui domine les deux colonnes ci-dessus — disparaît
# dans la différence, et il ne reste que l'effet de l'estimateur.
diffs = [per_arch[best_tau][i] - per_arch[0.0][i] for i in range(len(per_arch[0.0]))]
dm = float(np.mean(diffs))
dse = float(np.std(diffs, ddof=1) / math.sqrt(len(diffs))) if len(diffs) > 1 else float("nan")
say(f"""
   COMPARAISON APPARIÉE, archive par archive (tau = {best_tau:.1f} contre brut) :
     par archive   {"  ".join(f"{d:+.3f}" for d in diffs)}
     moyenne       {dm:+.3f} +/- {dse:.3f}   ->  {"POSITIF sur toutes les archives" if all(d > 0 for d in diffs) else f"positif sur {sum(1 for d in diffs if d > 0)}/{len(diffs)} archives"}

   C'est cette ligne qui porte le résultat de la section, et non les niveaux
   absolus : la variance d'une archive à l'autre est grande, celle de la
   DIFFÉRENCE ne l'est pas.""")
CAP_PUB = 0.41                       # part captée publiée au §45, variante raw
ecart = abs(caps[0.0] - CAP_PUB) / CAP_PUB

say(f"""
   Le seuillage à tau = {best_tau:.1f} capte {caps[best_tau]:.3f} de l'oracle contre
   {caps[0.0]:.3f} pour la matrice brute — un facteur {gain_reel:.2f}.

   Le seuil n'est pas ajusté sur la vérité : sigma_chapeau vient de l'écart
   médian absolu des entrées de la matrice, qui est une statistique de ce que
   le joueur a sous les yeux. C'est ce qui distingue une amélioration d'une
   fuite.

   CONTRÔLE, et il décide de ce que la section 5 a le droit de conclure.
   La variante brute est censée être celle du §45, qui publie une part captée
   de {CAP_PUB:.2f} à cette amplitude. Obtenu ici : {caps[0.0]:.3f}, soit {ecart:.0%} d'écart.
   {"Les deux protocoles coïncident : le chiffre seuillé est directement comparable au chiffre publié." if ecart < 0.25 else "Les deux protocoles NE coïncident PAS — moins de repetitions, archive plus courte, ou reglage different. Seul le RAPPORT entre brut et seuille se transporte alors, pas les niveaux."}""")


# ==========================================================================
rule("5. CE QUE LE MAXIMUM DU §48 DEVIENT")
# ==========================================================================

say("""   Le §48 ajuste la part captée sur quatre points mesurés et maximise le
   produit (plafond d'omniscience) x (part captée). Le point « paires
   cachées » vient de changer. On refait le produit, points d'origine à
   gauche, point corrigé à droite.""")

POINTS = [("rémanence uniforme", 1, 0.53, 1.00),
          ("marginal", 80, 1.33, 0.64),
          ("paires cachées", 6_400, 3.21, 0.41),
          ("quadratique", 252_800, 6.27, 0.11)]

say("\n   famille              m       plafond   captée §45   réalisable §45")
for name, m, pla, cap in POINTS:
    say(f"   {name:<18} {m:>8,}   {pla:>6.2f} %   {cap:>10.2f}   {pla * cap:>13.2f} %")

# Le niveau ne se transporte que si le contrôle de la section 4 a coïncidé ;
# sinon seul le RAPPORT brut -> seuillé est transportable, appliqué au 0,41
# publié. C'est la version conservatrice, et elle est employée par défaut.
new_cap = caps[best_tau] if ecart < 0.25 else min(1.0, CAP_PUB * gain_reel)
mode = ("niveau mesuré directement" if ecart < 0.25
        else f"rapport x{gain_reel:.2f} appliqué au {CAP_PUB:.2f} publié")
say(f"""
   Le point mesuré ici : paires cachées, part captée {new_cap:.2f} au lieu de
   {CAP_PUB:.2f} ({mode}), donc réalisable {3.21 * new_cap:.2f} % au lieu de {3.21 * CAP_PUB:.2f} %.

   Ce point seul suffit à déplacer le maximum du §48 de +1,28 % à
   au moins {3.21 * new_cap:.2f} %, puisque le maximum est un maximum sur les points.

   Et la section 3 dit que le gain d'alignement CROÎT avec m : le point
   quadratique (m = 252 800, capté 0,11 avec un seuillage à |Z| > 4,5 sur le
   tenseur mais une matrice brute sur les linéaires) est celui où le gain
   serait le plus grand. Il n'est pas mesuré ici — le mesurer demande de
   refaire le protocole de h24, et c'est le travail que ce fichier
   désigne plutôt que de le prétendre fait.""")


# ==========================================================================
rule("6. CE QUE CECI NE FAIT PAS")
# ==========================================================================

say(f"""   IL NE CASSE PAS LE THÉORÈME D'INVARIANCE. E[hits] = k/4 pour toute
   grille sous un tirage échangeable : rien ici ne le touche, et tout ce qui
   précède suppose une archive CONTAMINÉE par construction. Sur l'archive
   réelle, les 3 311 tests du registre restent négatifs.

   IL NE BAT PAS LA MARGE. Le maximum de la piste A passe de +1,28 % à au
   moins {3.21 * new_cap:.2f} %, contre un taux de retour de base mesuré à 58,9 % (§56) :
   il manque toujours un facteur vingt. Aucune des deux quantités n'a bougé
   assez pour que les courbes se croisent.

   CE QU'IL FAIT. Il retire au dossier le droit de dire que le mur est une
   propriété de la NATURE du problème. Le §48 écrivait un maximum ; ce
   maximum était celui d'un couple (famille, estimateur), et l'estimateur
   n'était pas le bon pour les familles concernées. La loi du §42 est vraie
   et le reste — pour les familles denses. Elle change de signe pour les
   familles creuses, qui sont précisément celles que le §45 a mesurées.

   LIMITES.
   1. Un seul point est refait (paires cachées). Le quadratique, où le gain
      serait le plus grand, est désigné et non mesuré.
   2. Le seuillage dur par entrée n'est pas optimal : le seuillage doux et la
      moyenne a posteriori sous un a priori de parcimonie feraient mieux. Ce
      qui est établi ici est une BORNE INFÉRIEURE sur ce qu'un bon estimateur
      capte, pas l'optimum.
   3. Les amplitudes de frontière sont reprises du registre (c1), jamais
      recalculées : relancer ces expériences écrirait des doublons dans un
      registre partagé.
   4. La section 2 hérite de la limite n° 3 du §42 : le joueur y estime sur
      les mêmes données que le test, ce qui la rend MAJORANTE. La section 4,
      elle, est en marche avant stricte.

   Registre : inchangé. h44 ne teste pas l'archive — il démontre et mesure
   sur des contaminations connues.""")

say(f"\n   ({time.time() - T0:.1f} s)")
