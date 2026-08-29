"""g1 — trois thèses jamais posées, qui FERMENT la question de la prédiction.

Tout le dossier — 29 voies, 3 310 tests — a cherché un écart. Ces trois
thèses posent la question inverse et complémentaire : que peut-on PROUVER
sur la meilleure prédiction possible ?

g1-A  LA DISTRIBUTION, PAS LA MOYENNE. f3 a testé l'espérance des hits du
      prédicteur déployé. Mais un prédicteur qui exploiterait une structure
      pourrait avoir la BONNE moyenne et la MAUVAISE loi — des épaules plus
      lourdes, une queue déplacée. Sous H0, conditionnellement au passé, le
      recouvrement du top-k avec le tirage suit une hypergéométrique(80,20,k)
      QUEL QUE SOIT le contenu du top-k : l'histogramme des 70 547
      recouvrements est donc exactement multinomial(T, pmf) — un null EXACT,
      sans simulation d'archives. Jamais testé.

g1-B  LA BORNE D'ÉTAT ET LE BUDGET D'INFORMATION. Aucune analyse ne peut
      distinguer un bon générateur cryptographique du vrai hasard — mais on
      peut CHIFFRER ce que l'archive peut réfuter et ce qu'il faudrait pour
      aller plus loin. (1) Un générateur à petit état finit par cycler, et un
      cycle produit des tirages exactement répétés : zéro doublon sur 70 560
      donne une borne inférieure sur la période, donc sur l'état. (2) Le
      résidu le plus cohérent du dossier (V3, z = −2,58) a besoin d'un nombre
      calculable de tirages pour atteindre le seuil du registre : c'est le
      prix, en jours, de la première découverte possible.

g1-C  LE THÉORÈME DE L'ASSURANCE GRATUITE. Sous H0, par échangeabilité des
      80 numéros, la LOI COMPLÈTE des hits d'une grille de k numéros — pas
      seulement son espérance — est la même hypergéométrique pour TOUT choix
      de k numéros fait sans voir le tirage. Conséquence jamais énoncée :
      suivre l'essaim ne coûte RIEN, en distribution, par rapport à des
      numéros au hasard — mais capterait un biais si un apparaissait. La
      politique { essaim + paquet étalé + seuil de jackpot + surveillance
      relancée } est donc minimax : perte nulle sous H0, gain maximal
      réalisable sous les familles de biais bornées par c0/c1. g1-A est le
      test empirique de sa prémisse.
"""

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import lab
import swarm_py as sp

T0 = time.time()
POOL, DRAWN = sp.POOL, sp.DRAWN


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def hyper_pmf(k: int) -> np.ndarray:
    c = math.comb
    tot = c(POOL, DRAWN)
    return np.array([c(DRAWN, h) * c(POOL - DRAWN, k - h) / tot
                     for h in range(k + 1)], float)


def chi2_classes(pmf: np.ndarray, T: int, min_exp: float = 8.0):
    """Regroupe les classes de queue pour que chaque attendu soit >= min_exp."""
    exp = pmf * T
    lo = 0
    while exp[:lo + 1].sum() < min_exp:
        lo += 1
    hi = len(pmf) - 1
    while exp[hi:].sum() < min_exp:
        hi -= 1
    edges = [(0, lo)] + [(i, i) for i in range(lo + 1, hi)] + [(hi, len(pmf) - 1)]
    probs = np.array([pmf[a:b + 1].sum() for a, b in edges])
    return edges, probs


def chi2_stat(counts_by_val: np.ndarray, edges, probs, T: int) -> float:
    obs = np.array([counts_by_val[a:b + 1].sum() for a, b in edges], float)
    exp = probs * T
    return float(((obs - exp) ** 2 / exp).sum())


DECISION = ("significatif seulement si p franchit le seuil Holm du registre "
            "entier ; sinon consigné comme nul avec sa sensibilité")

TOK_A20 = lab.preregister(
    "g1.A20", "la LOI du recouvrement top-20 du predicteur deploye s'ecarte de "
              "l'hypergeometrique (moyenne correcte mais forme fausse)",
    "chi2 de l'histogramme des 70 547 recouvrements de l'ensemble contre "
    "multinomial(T, hypergeom(80,20,20)), classes regroupees a attendu >= 8",
    "multinomial EXACT simule (le null ne depend pas du contenu des tops : "
    "conditionnellement au passe, chaque recouvrement est hypergeometrique)",
    DECISION, track="C")

TOK_A10 = lab.preregister(
    "g1.A10", "la LOI des hits du top-10 (la grille maximale affichee) "
              "s'ecarte de l'hypergeometrique(80,20,10)",
    "chi2 de l'histogramme des hits du top-10 de l'ensemble contre "
    "multinomial(T, hypergeom(80,20,10))",
    "multinomial exact simule", DECISION, track="C")

TOK_B = lab.preregister(
    "g1.B", "le generateur a un etat assez petit pour cycler dans l'archive",
    "nombre de tirages exactement repetes sur 70 560 (un cycle en produit)",
    "sous H0, esperance C(70560,2)/C(80,20) ~ 7e-10 : zero attendu ; "
    "la borne est deterministe, pas statistique",
    "toute repetition exacte serait un evenement a p ~ 7e-10", track="C")


# --------------------------------------------------------------------------
# g1-A — la distribution complète du prédicteur déployé
# --------------------------------------------------------------------------

rule("g1-A — LA LOI COMPLÈTE DU PRÉDICTEUR, PAS SA MOYENNE")
say("   f3 a testé l'espérance. Un prédicteur exploitant une structure peut")
say("   avoir la bonne moyenne et la mauvaise LOI. Sous H0 l'histogramme des")
say("   recouvrements est exactement multinomial — null exact, zéro rejeu.")

arch = lab.load()
mask = arch.mask
r = sp.run(mask, keep_picks=True)
say(f"   essaim rejoué : {r['steps']} pas ({time.time() - T0:.0f}s)")

T = r["steps"]
ov20 = r["ov_ens"].astype(int)
# hits du top-10 : les 10 premiers indices du top-20 (tri décroissant stable)
top10 = r["picks_ens"][:, :10]
WARM = sp.WARMUP
hits10 = np.array([int(mask[WARM + t][top10[t]].sum()) for t in range(T)])

pmf20, pmf10 = hyper_pmf(20), hyper_pmf(10)
rng = np.random.default_rng(2026)
RESULTS = {}
for nom, tok, vals, pmf in (("top-20", TOK_A20, ov20, pmf20),
                            ("top-10", TOK_A10, hits10, pmf10)):
    edges, probs = chi2_classes(pmf, T)
    cnt = np.bincount(vals, minlength=len(pmf))
    obs_chi2 = chi2_stat(cnt, edges, probs, T)
    sims = np.empty(4000)
    for i in range(4000):
        sims[i] = chi2_stat(rng.multinomial(T, pmf), edges, probs, T)
    null = lab.Null(float(sims.mean()), float(sims.std(ddof=1)), 4000, sims)
    RESULTS[nom] = (tok, obs_chi2, null, edges, probs, cnt)
    say(f"\n   {nom} : χ² = {obs_chi2:.2f} sur {len(edges) - 1} ddl")
    say(f"      null multinomial : {null.mean:.2f} ± {null.sd:.2f}"
        f"   z = {null.z(obs_chi2):+.2f}   p = {null.p_two_sided(obs_chi2):.4f}")

say("\n   histogramme du top-20, classe par classe (attendu >= 8) :")
tok, obs_chi2, null, edges, probs, cnt = RESULTS["top-20"]
for (a, b), pr in zip(edges, probs):
    o = cnt[a:b + 1].sum()
    e = pr * T
    lbl = f"{a}" if a == b else f"{a}-{b}"
    say(f"      {lbl:>6}   observé {o:>7,}   attendu {e:>10,.1f}   "
        f"{(o - e) / math.sqrt(e):+6.2f} σ")

# Puissance : la contamination momentum déforme la loi des recouvrements des
# têtes momentum, donc de l'ensemble qui les reprend.
say("\n   puissance (T = 20 000, contamination momentum, seuil 3σ du null) :")


def contaminate(m, rg, eps):
    m = m.copy()
    for t in range(1, len(m)):
        if rg.random() >= eps:
            continue
        prev = np.flatnonzero(m[t - 1] & ~m[t])
        cur = np.flatnonzero(m[t] & ~m[t - 1])
        if len(prev) and len(cur):
            m[t, rg.choice(prev)] = True
            m[t, rg.choice(cur)] = False
    return m


T_POW = 20_000
edges_p, probs_p = chi2_classes(pmf20, T_POW - sp.WARMUP + 13)
rngp = np.random.default_rng(31)
simp = np.empty(2000)
for i in range(2000):
    simp[i] = chi2_stat(rngp.multinomial(T_POW - sp.WARMUP, pmf20), edges_p, probs_p,
                        T_POW - sp.WARMUP)
seuil = simp.mean() + 3 * simp.std(ddof=1)
for eps in (0.05, 0.10):
    got = []
    for _ in range(2):
        rr = sp.run(contaminate(lab.srs(T_POW, rngp), rngp, eps), keep_picks=False)
        c = np.bincount(rr["ov_ens"].astype(int), minlength=21)
        got.append(chi2_stat(c, edges_p, probs_p, rr["steps"]))
    got = np.array(got)
    say(f"      ε = {eps:.2f}   χ² moyen {got.mean():8.1f}   seuil {seuil:6.1f}"
        f"   détecté {int((got >= seuil).sum())}/2")

lab.record(RESULTS["top-20"][0], RESULTS["top-20"][1], RESULTS["top-20"][2],
           power_at=f"momentum a T={T_POW}, cf. sortie", verdict="",
           notes="histogramme complet des recouvrements de l'ensemble deploye")
lab.record(RESULTS["top-10"][0], RESULTS["top-10"][1], RESULTS["top-10"][2],
           power_at=f"momentum a T={T_POW}, cf. sortie", verdict="",
           notes="hits du top-10 affiche, loi complete contre hypergeom(80,20,10)")


# --------------------------------------------------------------------------
# g1-B — la borne d'état et le budget d'information
# --------------------------------------------------------------------------

rule("g1-B — CE QUE L'ARCHIVE PEUT RÉFUTER, ET LE PRIX D'ALLER PLUS LOIN")

seen = {}
dups = 0
for i, row in enumerate(arch.nums):
    k = row.tobytes()
    if k in seen:
        dups += 1
    else:
        seen[k] = i
say(f"   tirages exactement répétés : {dups} / 70 560")
say(f"   attendu sous H0 : C(70560,2)/C(80,20) = "
    f"{math.comb(70560, 2) / math.comb(80, 20):.2e}")
say("   -> un générateur qui aurait cyclé DANS l'archive aurait répété des")
say("      tirages à l'identique. Zéro répétition = période > 70 559 pas de")
say(f"      tirage, donc état > log2(70 560) = {math.log2(70560):.1f} bits par pas")
say("      consommé. C'est une borne FAIBLE et c'est la thèse : l'archive ne")
say("      peut réfuter que les générateurs à état minuscule — tout état")
say("      modéré (64 bits et plus) est hors de portée de N'IMPORTE QUELLE")
say("      analyse de 70 560 sorties, celle-ci comprise.")

say(f"\n   budget d'information de l'archive : 70 560 × 61,6165 = "
    f"{70560 * 61.6165 / 1e6:.2f} Mbit")

# Le prix de la première découverte possible : V3 au seuil du registre.
rows = lab.holm()
thr = rows[0]["holm_threshold"]
z_now, n_now = 2.58, 70559
from math import erf, sqrt


def z_of_p(p):
    lo, hi = 0.0, 10.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if 2 * (1 - 0.5 * (1 + erf(mid / sqrt(2)))) > p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


z_star = z_of_p(thr)
n_star = n_now * (z_star / z_now) ** 2
say(f"\n   le résidu V3 (z = −2,58) au seuil du registre ({thr:.2e}, z = {z_star:.2f}) :")
say(f"      il faudrait {n_star:,.0f} tirages, soit {n_star - n_now:,.0f} de plus")
say(f"      = {(n_star - n_now) / 204:.0f} jours de nouveaux tirages (204/jour)")
say("   et cela suppose que l'effet est réel et stationnaire — sinon ce temps")
say("   n'achète rien. C'est le prix plancher de toute première découverte.")

lab.record(TOK_B, float(dups), None, p=1.0, power_at="borne deterministe",
           verdict="",
           notes=f"0 repetition -> periode > 70559 pas, etat > {math.log2(70560):.1f} "
                 f"bits ; V3 au seuil du registre : {(n_star - n_now) / 204:.0f} jours")


# --------------------------------------------------------------------------
# g1-C — le théorème de l'assurance gratuite (dérivation + appui empirique)
# --------------------------------------------------------------------------

rule("g1-C — LE THÉORÈME DE L'ASSURANCE GRATUITE")
say("""   Sous H0, les 80 numéros sont échangeables. Pour toute grille de k
   numéros choisie sans voir le tirage — si adaptative soit-elle —, la LOI
   COMPLÈTE de ses hits est hypergéométrique(80, 20, k). Pas seulement
   l'espérance : chaque probabilité de chaque rang de gain, donc la
   distribution des gains sous N'IMPORTE QUEL barème à cotes fixes.

   Conséquence jamais énoncée dans ce dossier : suivre l'essaim ne coûte
   RIEN — en distribution — par rapport à des numéros au hasard. Et si un
   biais des familles bornées par c0/c1 apparaissait, l'essaim est
   précisément l'objet qui le capterait (f3 : détection à +0,043 hit dès
   T = 20 000). La politique de l'app :

      essaim (biais éventuels)  +  paquet étalé (P(pleine) rang par rang)
      +  seuil de jackpot (quand jouer)  +  surveillance relancée (alerte)

   est donc MINIMAX : perte exactement nulle sous H0, gain maximal
   réalisable sous les alternatives bornées. « La meilleure prédiction
   possible » n'est pas un choix de numéros — c'est cette politique, et
   g1-A vient d'en tester la prémisse sur les 70 547 pas du déployé.""")

rule(f"consigné au registre — total {time.time() - T0:.0f}s")
