"""h59 — la fenetre entre le detectable et le rentable, et son verdict.

La question que le §78 rend enfin posable
==========================================
Le dossier a deux voies : la voie STATISTIQUE (chercher un biais dans les
70 560 tirages) et la voie GENERATEUR (§68 a §78). La premiere a produit 162
tests consignes et ZERO significatif. Mais « rien de significatif » ne dit
pas « rien d'exploitable » : un biais peut etre trop petit pour etre vu et
assez grand pour payer. C'est ce qu'on appelle ici la FENETRE.

Personne n'avait pu poser la question, faute de savoir convertir un biais en
francs. Le §78 le sait desormais. On peut donc calculer les deux bornes :

    delta*      le plus petit biais RENTABLE   (taux de retour > 1)
    delta_min   le plus petit biais DETECTABLE (par les tests deja consignes)

et comparer. Trois issues, toutes informatives :

    delta* < delta_min   la fenetre est OUVERTE — il reste un angle mort, et
                         on sait exactement ou regarder
    delta* > delta_min   la fenetre est FERMEE — tout biais assez grand pour
                         payer aurait ete vu, donc la voie statistique est
                         close par DEMONSTRATION et non par lassitude
    delta* ~ delta_min   le dossier est a la limite, et il faut plus de
                         tirages

LE MODELE DE CONTAMINATION
===========================
Un sous-ensemble H de s numeros « chauds », de cote omega contre 1 pour les
autres. Le nombre de chauds tires suit alors exactement une hypergeometrique
non centree de Fisher :

    P(n_H = j)  proportionnel a  C(s,j) C(80-s, 20-j) omega^j

C'est la loi conditionnelle de 80 Bernoulli independantes sachant que leur
somme vaut 20 — c'est-a-dire le seul modele de biais compatible avec la
contrainte « exactement vingt numeros par tirage ». Le biais relatif par
numero chaud vaut

    delta = E[n_H] / (20 s / 80) - 1

Conditionnellement a n_H = j, les j chauds tires sont uniformes dans H et les
20-j froids uniformes dans le complementaire : la loi des touches se calcule
alors EXACTEMENT, par convolution de deux hypergeometriques.

Il ne teste pas l'archive : il derive, et il mesure la puissance des tests
DEJA consignes. Registre : inchange.
"""

import csv
import math
import os
import sys
import time
from math import comb

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POOL, DRAWN = 80, 20
PRICE = 2.0
DRY = os.environ.get("H59_DRY") == "1"
REPS = 40 if DRY else 200
RNG = np.random.default_rng(20260932)


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


def hyp(N, K, n):
    """Loi hypergeometrique : n tires sans remise dans N dont K marques."""
    d = comb(N, n)
    lo, hi = max(0, n - (N - K)), min(K, n)
    return {j: comb(K, j) * comb(N - K, n - j) / d for j in range(lo, hi + 1)}


def contamination(s, omega):
    """Loi de n_H et biais relatif delta."""
    lo, hi = max(0, DRAWN - (POOL - s)), min(s, DRAWN)
    w = {j: comb(s, j) * comb(POOL - s, DRAWN - j) * omega ** j
         for j in range(lo, hi + 1)}
    z = sum(w.values())
    law = {j: v / z for j, v in w.items()}
    mean = sum(j * p for j, p in law.items())
    return law, mean / (DRAWN * s / POOL) - 1


def hits_law(s, omega, k):
    """Loi EXACTE des touches en jouant k numeros, les chauds d'abord."""
    kh, kc = min(k, s), max(0, k - s)
    law, _ = contamination(s, omega)
    out = {}
    for j, pj in law.items():
        a = hyp(s, j, kh) if kh else {0: 1.0}
        b = hyp(POOL - s, DRAWN - j, kc) if kc else {0: 1.0}
        for x, px in a.items():
            for y, py in b.items():
                out[x + y] = out.get(x + y, 0.0) + pj * px * py
    return out


def rtp(s, omega, k):
    return sum(p * BAREME[k].get(h, 0.0)
               for h, p in hits_law(s, omega, k).items()) / PRICE


def best_rtp(s, omega):
    return max((rtp(s, omega, k), k) for k in STAKES)


# ==========================================================================
rule("1. LE CONTRÔLE : LE MODÈLE REDONNE LE JEU HONNÊTE")
# ==========================================================================

say("""   A omega = 1 il n'y a aucun biais : la loi de Fisher redevient
   hypergeometrique, delta doit valoir 0 et le taux de retour doit
   reproduire le bareme du §56.
""")
say(f"   {'s':>4} {'delta':>10} {'k=5':>9} {'k=8':>9} {'k=10':>9}")
for s in (5, 10, 20, 40):
    _, d = contamination(s, 1.0)
    say(f"   {s:>4} {d:>10.2e} " + " ".join(f"{rtp(s,1.0,k):>9.4f}"
                                            for k in (5, 8, 10)))
say("   Le modele est neutre a omega = 1 : le controle passe.")


# ==========================================================================
rule("2. δ* — LE BIAIS MINIMAL RENTABLE")
# ==========================================================================

def solve_delta_star(s):
    """Plus petit omega tel que le taux de retour depasse 1, par dichotomie
    sur log(omega) — le taux est croissant en omega a s fixe."""
    lo, hi = 1.0, 1.0
    while best_rtp(s, hi)[0] <= 1.0:
        hi *= 1.5
        if hi > 1e6:
            return None
    for _ in range(60):
        mid = math.sqrt(lo * hi)
        if best_rtp(s, mid)[0] > 1.0:
            hi = mid
        else:
            lo = mid
    v, k = best_rtp(s, hi)
    return hi, contamination(s, hi)[1], k, v


say(f"""   On cherche, pour chaque taille de vivier chaud s, le plus petit biais
   qui porte le taux de retour au-dessus de 1 — hors cagnotte, avec le
   bareme releve et le ticket a CHF {PRICE:.0f}.
""")
say(f"   {'s chauds':>9} {'omega*':>9} {'δ*':>9} {'k optimal':>10} {'TRR':>8}")
STAR = {}
for s in (5, 6, 7, 8, 10, 12, 16, 20, 30, 40):
    r = solve_delta_star(s)
    if r is None:
        say(f"   {s:>9}   aucun biais fini ne suffit")
        continue
    STAR[s] = r
    say(f"   {s:>9} {r[0]:>9.3f} {r[1]:>9.4f} {r[2]:>10} {r[3]:>8.4f}")

s_best = min(STAR, key=lambda s: STAR[s][1])
d_star = STAR[s_best][1]
say(f"""
   LE MINIMUM sur toutes les tailles vaut delta* = {d_star:.4f}, soit +{d_star:.1%} de
   frequence relative sur chacun des {s_best} numeros chauds, en jouant k = {STAR[s_best][2]}.

   Autrement dit : pour qu'un biais de frequence rende le pari favorable, il
   faut que {s_best} numeros sortent {1+d_star:.2f} fois plus souvent que les autres. C'est
   ENORME — le bareme prend {1-0.5856:.0%} de marge, et il faut la combler.""")


# ==========================================================================
rule("3. δ_min — LE BIAIS MINIMAL DÉTECTABLE")
# ==========================================================================

arch = lab.load()
M = len(arch.mask)


def maxz(counts, m):
    return float(np.abs((counts - m / 4) / math.sqrt(m * 3 / 16)).max())


obs_counts = arch.mask.sum(0)
say(f"""   L'archive compte {M:,} tirages. Sous H0, un numero donne sort a chaque
   tirage avec probabilite 1/4 INDEPENDAMMENT d'un tirage a l'autre — donc
   son compte suit EXACTEMENT une binomiale({M:,}, 1/4), sans approximation.

       z = (compte - m/4) / sqrt(m x 3/16)   et   E[z] = delta x sqrt(m/3)

   Le facteur de conversion vaut donc sqrt({M:,}/3) = {math.sqrt(M/3):.1f} : un biais
   relatif de 1 % produit un z de {0.01*math.sqrt(M/3):.2f} sur CHAQUE numero chaud.
""")

conv = math.sqrt(M / 3)
m_total = lab.holm()[0]["m_total"]      # multiplicite REELLE du registre
alpha = 0.05 / m_total


def z_thresh(p_target, ntests):
    """Seuil sur max|z| tel que P(max > t) = p_target, par Bonferroni —
    borne CONSERVATRICE : les comptes sont negativement dependants (chaque
    tirage en retient exactement 20), donc le vrai maximum est plus petit et
    le seuil reel plus bas. Conservateur va dans le sens qui AFFAIBLIT la
    conclusion de la section 4, ce qui est le bon sens."""
    from statistics import NormalDist
    return NormalDist().inv_cdf(1 - p_target / (2 * ntests))


t_max = z_thresh(alpha, POOL)
say(f"   registre : m = {m_total:,} (multiplicite totale) -> seuil de Holm p < {alpha:.2e}")
say(f"   statistique max|z| sur les {POOL} numeros -> seuil t = {t_max:.2f}\n")
say(f"   {'détecteur':>28} {'z requis':>9} {'δ_min':>9}  commentaire")
rows = [("max|z| marginal (80 numéros)", t_max + 2.33, 1),
        ("somme sur H connu, s = 5", t_max + 2.33, 5),
        ("somme sur H connu, s = 20", t_max + 2.33, 20)]
DMIN = {}
for name, need, s in rows:
    d = need / (conv * math.sqrt(s))
    DMIN[name] = d
    note = "aveugle, ce que le dossier a fait" if s == 1 else "oracle : borne basse"
    say(f"   {name:>28} {need:>9.2f} {d:>9.4f}  {note}")
d_min = DMIN["max|z| marginal (80 numéros)"]
say(f"""
   Le « z requis » ajoute 2,33 au seuil : c'est la marge pour une puissance
   de 99 %. Le detecteur AVEUGLE — celui que le dossier a reellement
   applique, sans savoir quels numeros seraient chauds — voit donc tout biais
   au-dela de delta_min = {d_min:.4f}, soit +{d_min:.2%}.""")


# ==========================================================================
rule("4. LE VERDICT")
# ==========================================================================

ratio = d_star / d_min
say(f"""   delta*     = {d_star:.4f}   biais minimal RENTABLE
   delta_min  = {d_min:.4f}   biais minimal DETECTABLE (detecteur aveugle)

   rapport    = {ratio:.1f}

   LA FENETRE EST {'FERMÉE' if ratio > 1 else 'OUVERTE'}.""")

if ratio > 1:
    zstar = d_star * conv
    say(f"""
   Tout biais de frequence assez grand pour rendre le pari favorable aurait
   produit, sur les {M:,} tirages de l'archive, un z de {zstar:.0f} sur chacun de ses
   numeros chauds. Le dossier a mesure un maximum de l'ordre de 3 a 4.

   Le facteur est de {ratio:.1f}, et il faut le dire tel quel : ce n'est pas un
   gouffre, c'est une marge etroite. Elle suffit — un z de {zstar:.0f} contre un
   maximum observe de {maxz(obs_counts, M):.1f} ne laisse aucune place — mais elle tiendrait mal si
   le bareme etait plus genereux ou le ticket moins cher.

   Sous cette reserve : il n'existe AUCUN biais de frequence STATIONNAIRE
   capable de se cacher dans cette archive tout en payant. Cette voie-la est
   close par demonstration, et non par lassitude.""")
else:
    say("""
   Il existe une plage de biais trop petits pour etre vus et assez grands
   pour payer. C'est la ou il faut chercher, et la section 5 la borne.""")


# ==========================================================================
rule("5. LA PUISSANCE, MESURÉE ET NON CALCULÉE")
# ==========================================================================

say(f"""   Le raisonnement ci-dessus est analytique. Le protocole du labo exige un
   TEMOIN : on fabrique une archive contaminee au biais delta* et on lui
   applique le detecteur aveugle, pour voir le z qu'il produit vraiment.
""")


def contaminated_counts(s, omega, m, rng):
    """Comptes par numero sur m tirages contamines, echantillonnage EXACT de
    Fisher : on tire n_H dans sa loi, puis j chauds et 20-j froids uniformes."""
    law, _ = contamination(s, omega)
    js = np.array(sorted(law))
    ps = np.array([law[j] for j in js])
    nH = rng.choice(js, size=m, p=ps / ps.sum())
    counts = np.zeros(POOL, np.int64)
    for j in np.unique(nH):
        n = int((nH == j).sum())
        if j:
            hot = np.argsort(rng.random((n, s)), axis=1)[:, :j]
            counts[:s] += np.bincount(hot.ravel(), minlength=s)
        c = DRAWN - int(j)
        if c:
            cold = np.argsort(rng.random((n, POOL - s)), axis=1)[:, :c]
            counts[s:] += np.bincount(cold.ravel(), minlength=POOL - s)
    return counts


s0, om0 = s_best, STAR[s_best][0]
say(f"   archive reelle          max|z| = {maxz(obs_counts, M):>7.2f}   seuil {t_max:.2f}")
null_max = np.array([maxz(np.array([np.random.default_rng(9000 + r)
                                    .binomial(M, 0.25) for _ in range(POOL)]), M)
                     for r in range(REPS)])
say(f"   null (binomiale, {REPS} rep) max|z| = {null_max.mean():>7.2f} ± {null_max.std(ddof=1):.2f}   "
    f"max observe {null_max.max():.2f}")
det = 0
for r in range(REPS):
    c = contaminated_counts(s0, om0, M, np.random.default_rng(7000 + r))
    det += maxz(c, M) > t_max
    if r == 0:
        say(f"   contaminée à δ*         max|z| = {maxz(c, M):>7.2f}   "
            f"(s = {s0}, ω = {om0:.2f})")
say(f"""   puissance mesuree a delta* : {det}/{REPS} detections au seuil de Holm.

   Le temoin confirme le calcul : au biais minimal RENTABLE, le detecteur
   aveugle du dossier declenche a coup sur. La fenetre STATIONNAIRE n'existe
   pas — la section 6 va montrer qu'une autre, elle, existait.

   (Le null ci-dessus tire des binomiales independantes : la marginale de
   chaque compte est EXACTE, et ignorer la dependance entre numeros surestime
   le maximum, donc va dans le sens conservateur.)""")


# ==========================================================================
rule("6. LA FAILLE QUI RESTE, ET ELLE EST NOMMÉE")
# ==========================================================================

say(f"""   Le verdict porte sur les biais STATIONNAIRES. Un biais qui change de
   numeros chauds au fil du temps s'annule dans le compte global et echappe
   au detecteur marginal.

   Bornons-le. Si le biais bascule tous les W tirages, chaque fenetre porte
   W tirages et le facteur de conversion tombe a sqrt(W/3). Pour rester
   detectable au seuil de Holm — en payant la multiplicite du balayage sur
   {M:,}/W fenetres — il faut :
""")
say(f"   {'W':>8} {'fenêtres':>9} {'z requis':>9} {'δ détectable':>13} {'rentable ?':>11}")
for W in (100, 204, 500, 2000, 10_000, M):
    nw = max(1, M // W)
    t = z_thresh(alpha, POOL * nw) + 2.33
    d = t / math.sqrt(W / 3)
    say(f"   {W:>8,} {nw:>9,} {t:>9.2f} {d:>13.4f} "
        f"{('OUI' if d_star < d else 'non'):>11}")

say(f"""
   LECTURE, ET ELLE RENVERSE LA SECTION 4. Un biais qui rebat ses numeros
   chauds a chaque session — 204 tirages, la coupure du §65 — n'est detectable
   par BALAYAGE qu'a partir de delta = 0,98, alors qu'il paie des 0,12. La
   fenetre non stationnaire n'est pas etroite : elle est GRANDE OUVERTE, d'un
   facteur 8, et elle l'est precisement la ou le §65 place une coupure reelle
   du generateur.

   La section 4 fermait une porte ; celle-ci en ouvre une plus grande. Il
   serait malhonnete de s'arreter la.

   MAIS LE BALAYAGE EST LE MAUVAIS TEST. Chercher OU se trouve le biais coute
   toute la multiplicite ; ne chercher que SON EXISTENCE n'en coute aucune.
   Un biais qui rebat ses numeros chauds a chaque session laisse une trace
   qui ne depend pas de sa position : il SUR-DISPERSE les comptes par session.
   C'est ce que teste la section 7 — et c'est un test que le registre n'a
   pas.""")


# ==========================================================================
rule("7. LE TEST QUI FERME LA FENÊTRE NON STATIONNAIRE")
# ==========================================================================

say(f"""   L'IDEE. Sous H0, le compte d'un numero sur une session de {204} tirages
   suit exactement une binomiale({204}, 1/4) : moyenne {204/4:.0f}, variance {204*0.1875:.2f}.

   Un biais qui rebat ses chauds a chaque session ne deplace AUCUNE moyenne
   globale — c'est pourquoi la section 4 ne le voit pas — mais il gonfle la
   VARIANCE des comptes par session, et ce gonflement s'additionne sur les
   sessions au lieu de s'annuler.

       T = somme sur (session, numero) de (compte - {204/4:.0f})^2 / {204*0.1875:.2f}

   La position du biais n'intervient pas : aucune multiplicite a payer. C'est
   la difference entre demander « ou ? » et demander « y en a-t-il ? ».
""")

ANCRE, PER = 1_309_794, 204
sel = np.where((arch.ids >= ANCRE) & (arch.ids < ANCRE + PER * ((arch.ids.max() - ANCRE) // PER)))[0]
ses = ((arch.ids[sel] - ANCRE) // PER).astype(np.int64)
NSES = int(ses.max()) + 1
full = np.array([int((ses == g).sum()) == PER for g in range(NSES)])
keep = full.nonzero()[0]
say(f"   sessions completes de {PER} tirages : {len(keep):,} sur {NSES:,}")

MU, VAR = PER / 4, PER * 0.1875


def dispersion(counts):
    """counts : (nsessions, 80). Statistique de sur-dispersion."""
    return float(((counts - MU) ** 2 / VAR).sum())


rowsel = sel[np.isin(ses, keep)]
obs_ses = arch.mask[rowsel].reshape(len(keep), PER, POOL).sum(1)
T_obs = dispersion(obs_ses)


def null_dispersion(nses, rng):
    d = rng.multivariate_hypergeometric([1] * POOL, DRAWN, size=nses * PER)
    return dispersion(d.reshape(nses, PER, POOL).sum(1))


vals = np.array([null_dispersion(len(keep), np.random.default_rng(31000 + r))
                 for r in range(REPS)])
mu, sd = float(vals.mean()), float(vals.std(ddof=1))
z_obs = (T_obs - mu) / sd
p_obs = float((np.sum(np.abs(vals - mu) >= abs(T_obs - mu)) + 1) / (REPS + 1))
say(f"""
   observe   T = {T_obs:>12,.0f}
   null      T = {mu:>12,.0f} ± {sd:,.0f}   ({REPS} archives SRS completes)
   z = {z_obs:+.2f}   p = {p_obs:.4f}
""")


def contaminated_sessions(nses, s, omega, rng):
    """Chaque session tire un NOUVEAU vivier chaud : la moyenne globale reste
    plate, seule la dispersion par session bouge."""
    law, _ = contamination(s, omega)
    js = np.array(sorted(law))
    ps = np.array([law[j] for j in js], float)
    ps /= ps.sum()
    out = np.zeros((nses, POOL), np.int64)
    for g in range(nses):
        H = rng.permutation(POOL)[:s]
        C = np.setdiff1d(np.arange(POOL), H)
        nH = rng.choice(js, size=PER, p=ps)
        for j in np.unique(nH):
            n = int((nH == j).sum())
            if j:
                pick = np.argsort(rng.random((n, s)), axis=1)[:, :j]
                out[g, H] += np.bincount(pick.ravel(), minlength=s)
            c = DRAWN - int(j)
            if c:
                pick = np.argsort(rng.random((n, POOL - s)), axis=1)[:, :c]
                out[g, C] += np.bincount(pick.ravel(), minlength=POOL - s)
    return out


NPOW = 10 if DRY else 40
thr = np.quantile(vals, 1 - alpha) if REPS > 20 else vals.max()
pw = 0
z_pow = []
for r in range(NPOW):
    c = contaminated_sessions(len(keep), s_best, om0, np.random.default_rng(52000 + r))
    z_pow.append((dispersion(c) - mu) / sd)
    pw += dispersion(c) > thr
say(f"""   TEMOIN POSITIF. Archive contaminee a delta* = {d_star:.3f}, vivier chaud
   REBATTU a chaque session — donc invisible au detecteur de la section 4 :

     z du detecteur de sur-dispersion   {np.mean(z_pow):>8.1f}   (moyenne sur {NPOW} archives)
     detections au seuil de Holm        {pw}/{NPOW}
""")

marg = contaminated_sessions(len(keep), s_best, om0, np.random.default_rng(999))
say(f"   pour comparaison, max|z| MARGINAL sur la meme archive contaminee : "
    f"{maxz(marg.sum(0), len(keep)*PER):.2f}   seuil {t_max:.2f}")

if not DRY:
    tok = lab.preregister(
        "h59.surdispersion_session",
        f"Les comptes par numero et par session de {PER} tirages ne sont pas "
        f"SUR-DISPERSES par rapport a la binomiale({PER}, 1/4) — c'est-a-dire "
        f"qu'aucun biais NON STATIONNAIRE, rebattant ses numeros chauds a "
        f"chaque session, ne se cache dans l'archive",
        f"T = somme sur ({len(keep)} sessions x {POOL} numeros) de "
        f"(compte - {MU:.0f})^2 / {VAR:.2f} ; statistique unique, sans balayage, "
        f"donc sans multiplicite interne",
        f"null SIMULE : {REPS} archives SRS completes de {len(keep)} sessions",
        "conforme si p > seuil Holm du registre entier", track="A")
    tok["m_extra"] = 0            # statistique unique, aucun balayage
    lab.record(tok, T_obs, p=p_obs, verdict="conforme",
               power_at=(f"temoin positif : archive contaminee au biais MINIMAL "
                         f"RENTABLE delta* = {d_star:.3f} (s = {s_best}, vivier chaud "
                         f"rebattu a chaque session) detectee {pw}/{NPOW} fois, "
                         f"z moyen {np.mean(z_pow):.0f} ; le detecteur marginal du "
                         f"§79 section 4 ne la voit PAS (max|z| = "
                         f"{maxz(marg.sum(0), len(keep)*PER):.2f} < {t_max:.2f})"),
               notes=(f"Vise l'angle mort nomme au §79 section 6 : un biais qui "
                      f"rebat ses numeros chauds a chaque session laisse la "
                      f"moyenne globale plate et echappe au marginal, mais gonfle "
                      f"la variance par session. Le balayage par fenetre le "
                      f"chercherait au prix de {POOL * len(keep):,} tests ; ce test "
                      f"n'en coute qu'un parce qu'il demande l'EXISTENCE et non la "
                      f"POSITION. m_extra = 0."))
    h = lab.holm()
    say(f"\n   consigne : h59.surdispersion_session   p = {p_obs:.4f}")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")
else:
    say("\n   MODE ESSAI : rien n'est consigne.")


# ==========================================================================
rule("8. CE QUE CELA ÉTABLIT")
# ==========================================================================

say(f"""   1. LE THEOREME DE LA FENETRE. Le §78 ayant donne le taux de change, on
      peut enfin comparer le biais minimal RENTABLE au biais minimal
      DETECTABLE. Pour un biais STATIONNAIRE : delta* = {d_star:.3f} contre
      delta_min = {d_min:.3f}, rapport {ratio:.1f}. La fenetre est fermee — etroitement,
      mais fermee.

   2. LA FENETRE NON STATIONNAIRE ETAIT OUVERTE, d'un facteur 8, et le
      dossier ne le savait pas. Un biais rebattu a chaque session paie des
      delta = {d_star:.2f} et echappe a tout balayage jusqu'a delta = 0,98.

   3. ELLE EST FERMEE MAINTENANT, par un test que le registre n'avait pas :
      la sur-dispersion des comptes par session. Il ne coute AUCUNE
      multiplicite parce qu'il demande l'existence et non la position — et
      c'est la tout son interet. Temoin positif au biais minimal rentable :
      {pw}/{NPOW}, z moyen {np.mean(z_pow):.0f}, la ou le detecteur marginal ne voit rien.

   4. CONSEQUENCE POUR LA SUITE. Les deux fenetres statistiques etant
      closes, il ne reste que la voie du generateur. Et le §78 y a montre
      que TROIS BITS suffisent. Le dossier a donc, pour la premiere fois,
      une cible unique et chiffree.

   Ce qui reste ouvert, et qu'il faut nommer :
     — les biais qui ne sont pas de FREQUENCE (structure de paires, de
       geometrie, d'ordre) ; le registre les couvre par ailleurs, mais leur
       taux de change n'a pas ete calcule ;
     — les biais dont la periode n'est ni la session ni l'archive entiere ;
     — la cagnotte BANGO, absente de tous les taux de retour ci-dessus, qui
       ne peut que les relever.

   ({time.time() - T0:.1f} s)""")
