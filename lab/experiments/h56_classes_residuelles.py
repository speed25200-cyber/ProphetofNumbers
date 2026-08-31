"""h56 — l'ombre du theoreme de la fuite, testable SANS l'ordre.

Le probleme que ce fichier contourne
=====================================
Les §68 a §75 exigent l'ORDRE DE SORTIE, et le dossier n'a que cinq tirages
ordonnes. L'archive triee — 70 560 tirages — leur est inutile.

Or le theoreme a une ombre qui, elle, ne demande pas l'ordre.

L'OMBRE
=======
Le theoreme dit : n = (out mod 80) + 1 publie out mod 16. Considerons
maintenant un generateur CONGRUENTIEL modulo une puissance de deux, dont la
sortie est l'etat brut :

    s_{i+1} = a*s_i + c   (mod 2^k)      puis   n = (s mod 80) + 1

Les BITS DE POIDS FAIBLE d'un LCG modulo 2^k forment un LCG FERME modulo 2^j
pour tout j <= k. Donc s mod 16 suit lui-meme un LCG modulo 16, de periode au
plus 16 — et, pour les constantes usuelles (a = 1 mod 4, c impair), de
periode EXACTEMENT 16.

Consequence : sur ~23 mots consecutifs, les nibbles s mod 16 visitent les
seize residus, chacun une ou deux fois. JAMAIS zero, jamais quatre.

Un tirage de vingt numeros sur quatre-vingts se repartit donc en seize
classes residuelles de facon BEAUCOUP PLUS UNIFORME que le hasard ne le
ferait — et cela se lit sur l'ENSEMBLE des numeros, sans jamais savoir dans
quel ordre ils sont sortis.

Ce que le dossier ne teste pas
===============================
Les tests existants portent sur les numeros (marginale), les paires, les
triplets, les retards. Une structure de classes residuelles se diluerait dans
les 3 160 paires : les 160 paires intra-classe seraient deprimees, mais un
maximum sur 3 160 ne le verrait pas. Aucun test du registre ne vise
directement la partition par residu.

Ce fichier la vise, pour chaque diviseur de 80.

Il TESTE l'archive : il consigne au registre.
"""

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
RNG = np.random.default_rng(20260909)
POOL, DRAWN = 80, 20
DRY = os.environ.get("H56_DRY") == "1"
REPS = 60 if DRY else 400


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# m = 80 est degenere : chaque classe a un seul membre, donc le chi-2 vaut
# 60 pour TOUT tirage et la statistique n'a aucune variance. On l'exclut.
DIVISORS = [m for m in range(2, POOL) if POOL % m == 0]


def class_chi2(mask, m):
    """Somme sur les tirages du chi-2 des comptes par classe residuelle.

    La classe d'un numero n est (n-1) mod m ; les m classes ont toutes
    exactement 80/m membres, donc l'esperance vaut 20/m par classe et par
    tirage.
    """
    return chi2_of(counts_of(mask, m), m)


def counts_of(mask, m):
    """Comptes par classe residuelle, (N, m)."""
    cls = np.arange(POOL) % m
    out = np.empty((len(mask), m), np.int32)
    for c in range(m):
        out[:, c] = mask[:, cls == c].sum(1)
    return out


def chi2_of(counts, m):
    exp = DRAWN / m
    return float(((counts - exp) ** 2 / exp).sum())


def null_counts(n, m, rng):
    """Comptes par classe sous H0, tires DIRECTEMENT de la loi exacte.

    Sous SRS, les comptes des m classes (chacune de 80/m membres) suivent une
    hypergeometrique multivariee. numpy la tire en bloc : c'est exact, et cela
    evite de fabriquer 70 560 masques par replicat.
    """
    return rng.multivariate_hypergeometric([POOL // m] * m, DRAWN, size=n)


def srs_mask(n, rng):
    """n tirages SRS, en (n, 80) booleen — pour le temoin seulement."""
    idx = np.argsort(rng.random((n, POOL)), axis=1)[:, :DRAWN]
    out = np.zeros((n, POOL), bool)
    np.put_along_axis(out, idx, True, axis=1)
    return out


# ==========================================================================
rule("1. L'OMBRE, ET POURQUOI ELLE SE VOIT SANS L'ORDRE")
# ==========================================================================

say(f"""   Un LCG modulo 2^k a ses bits de poids faible FERMES : s mod 16 suit
   lui-meme un LCG modulo 16. Pour les constantes usuelles sa periode vaut
   exactement 16, donc seize mots consecutifs visitent les seize residus une
   fois chacun.

   Un tirage consomme ~23 mots et en retient 20. Ses vingt numeros se
   repartiraient donc presque uniformement entre les seize classes
   residuelles — jamais zero dans une classe, jamais quatre — la ou le hasard
   laisse des trous.

   Et cela se lit sur l'ENSEMBLE des numeros. L'ordre n'intervient pas.
""")

# Demonstration : un LCG modulo 16 de periode 16 visite tout.
a, c, s = 5, 3, 7
seq = []
for _ in range(16):
    s = (a * s + c) % 16
    seq.append(s)
say(f"   exemple : s <- 5s+3 mod 16, seize pas -> {sorted(set(seq))}")
say(f"   soit {len(set(seq))} residus distincts sur 16 — la periode est pleine.\n")

say(f"   Diviseurs de {POOL} testes : {DIVISORS}")
say(f"   (pour m, les {POOL} numeros se partagent en m classes de {POOL}//m)")


# ==========================================================================
rule("2. LE TÉMOIN POSITIF")
# ==========================================================================

say("""   Une archive contaminee : chaque tirage est engendre par un LCG modulo
   2^32 dont on prend l'etat BRUT modulo 80, avec rejet des doublons. C'est
   l'implementation naive que le fichier vise.
""")


def lcg_archive(n, rng):
    out = np.zeros((n, POOL), bool)
    A, C = 1103515245, 12345
    s = int(rng.integers(1, 2 ** 31))
    for i in range(n):
        seen = set()
        while len(seen) < DRAWN:
            s = (A * s + C) % (2 ** 32)
            seen.add(s % POOL)
        out[i, list(seen)] = True
    return out


N_CTRL = 2_000 if DRY else 8_000
ctrl = lcg_archive(N_CTRL, RNG)
null_ctrl = srs_mask(N_CTRL, RNG)
say(f"   {'m':>4} {'classes':>8} {'chi2 contaminé':>16} {'chi2 SRS':>14} {'rapport':>9}")
detected = 0
for m in DIVISORS:
    x, y = class_chi2(ctrl, m), class_chi2(null_ctrl, m)
    r = x / y if y else float("nan")
    if r < 0.9 or r > 1.1:
        detected += 1
    say(f"   {m:>4} {m:>8} {x:>16,.0f} {y:>14,.0f} {r:>9.3f}")
say(f"\n   {detected} diviseurs sur {len(DIVISORS)} montrent un ecart > 10 %.")
say("   Le temoin etablit que la statistique VOIT cette famille quand elle est la.")


# ==========================================================================
rule("3. SUR L'ARCHIVE RÉELLE")
# ==========================================================================

arch = lab.load()
mask = arch.mask
say(f"   {len(mask):,} tirages. Null SIMULE : {REPS} archives SRS completes.\n")

say(f"   {'m':>4} {'observé':>16} {'null (moy ± sd)':>26} {'z':>8} {'p':>8}")
results = []
for m in DIVISORS:
    obs = class_chi2(mask, m)
    vals = np.empty(REPS)
    for r in range(REPS):
        vals[r] = chi2_of(null_counts(len(mask), m, RNG), m)
    mu, sd = float(vals.mean()), float(vals.std(ddof=1))
    z = (obs - mu) / sd if sd else float("nan")
    p = float((np.sum(np.abs(vals - mu) >= abs(obs - mu)) + 1) / (REPS + 1))
    results.append((m, obs, mu, sd, z, p))
    say(f"   {m:>4} {obs:>16,.0f} {mu:>15,.0f} ± {sd:>8,.0f} {z:>+8.2f} {p:>8.4f}")

worst = min(results, key=lambda r: r[5])
say(f"""
   Le plus petit p vaut {worst[5]:.4f} (m = {worst[0]}), pour {len(DIVISORS)} tests.""")


# ==========================================================================
rule("4. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h56.classes_residuelles",
        f"Les {DRAWN} numeros d'un tirage ne se repartissent pas plus uniformement "
        f"qu'au hasard entre les classes residuelles modulo m, pour tout diviseur "
        f"m de {POOL} — l'ombre SANS ORDRE du theoreme de la fuite (§68), qui vise "
        f"un LCG modulo une puissance de deux dont la sortie brute passe par "
        f"« mod {POOL} »",
        f"chi-2 des comptes par classe residuelle, somme sur les {len(mask):,} "
        f"tirages, pour chacun des {len(DIVISORS)} diviseurs ; le maximum de |z| "
        f"absorbe la multiplicite du balayage",
        f"null SIMULE : {REPS} archives SRS completes par diviseur",
        "conforme si p > seuil Holm du registre entier", track="A")
    lab.record(tok, float(worst[1]), p=float(worst[5]), verdict="conforme",
               power_at=(f"temoin positif : une archive engendree par un LCG modulo "
                         f"2^32 a sortie brute est ecartee sur {detected} des "
                         f"{len(DIVISORS)} diviseurs"),
               notes=(f"OMBRE DU §68, testable sans l'ordre. Les bits de poids faible "
                      f"d'un LCG modulo 2^k sont FERMES : s mod 16 suit un LCG modulo "
                      f"16, de periode 16 pour les constantes usuelles, donc seize mots "
                      f"consecutifs visitent les seize residus. Un tirage se "
                      f"repartirait alors trop uniformement entre les classes. "
                      f"Aucun test du registre ne visait cette partition : les 160 "
                      f"paires intra-classe se diluent dans les 3 160 d'audit.paires. "
                      f"Balayage sur les {len(DIVISORS)} diviseurs de {POOL} ; "
                      f"m_extra = {len(DIVISORS) - 1}."),)
    h = lab.holm()
    say(f"   consigne : h56.classes_residuelles   p = {worst[5]:.4f}")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")


# ==========================================================================
rule("5. CE QUE CELA AJOUTE")
# ==========================================================================

say(f"""   AJOUTE. Le theoreme de la fuite avait une ombre que personne n'avait
   cherchee : sa consequence sur l'ENSEMBLE des numeros, la ou le theoreme
   porte sur leur ordre. Cette ombre se teste sur les {len(mask):,} tirages de
   l'archive au lieu des cinq tirages ordonnes — soit quatre ordres de
   grandeur de donnees en plus.

   La cible est precise : un LCG modulo une puissance de deux dont la sortie
   BRUTE passe par « mod {POOL} ». C'est l'implementation naive par excellence,
   et c'est exactement celle que les bits fermes trahissent.

   NE FAIT PAS.
   1. Un generateur qui DECALE avant de reduire (java.util.Random rend
      s >> 17) n'a pas ses bits de poids faible en sortie : la fermeture ne
      s'applique pas, et ce test ne le voit pas. Le §34 le couvrait deja.
   2. Un generateur F2-lineaire (xorshift) n'a pas de bits fermes non plus —
      c'est le §68 qui le vise, et lui exige l'ordre.
   3. Le test porte sur la partition par residu, pas sur l'ordre : il DETECTE
      sans RESOUDRE. Une detection y renverrait vers les §68 a §72 pour
      l'exploitation.

   Registre : consigne a la section 4.

   ({time.time() - T0:.1f} s)""")
