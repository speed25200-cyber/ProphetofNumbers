"""f5 — les 2,49 milliards de paires, et les 35 280 fréquences.

Ce qui n'avait jamais été fait
------------------------------
Le dossier a testé les lags 1 à 30 (`d2`), le recouvrement conditionnel
(`c1`), les triplets (`d1`). Chaque fois : QUELQUES décalages, choisis à la
main, sur une statistique nommée d'avance.

Or l'archive contient C(70560, 2) = 2 489 344 020 paires de tirages, et le
processus a 35 280 fréquences. Les regarder TOUTES n'est pas une question de
volonté : c'est une question d'algorithme. Fait naïvement, le recouvrement à
tous les décalages coûte 2,5·10⁹ comparaisons de 20 numéros.

Il y a mieux. Le recouvrement au décalage d s'écrit

    Σ_t |D_t ∩ D_{t+d}| = Σ_{n=1}^{80} Σ_t x_n[t]·x_n[t+d]

c'est-à-dire la somme des AUTOCORRÉLATIONS des 80 séries binaires
d'appartenance. Une FFT par numéro donne les 70 559 décalages d'un coup,
en quelques millisecondes. Le null aussi. Ce qui était hors de portée
devient gratuit — et le test passe de « 30 décalages choisis » à « tous les
décalages, avec la loi du maximum calibrée ».

Trois questions, toutes nouvelles :

  f5-A  Le recouvrement moyen s'écarte-t-il de 5 à un décalage QUELCONQUE ?
        (70 559 décalages, loi du maximum simulée)
  f5-B  Le processus a-t-il une périodicité — signature d'un générateur à
        état fini, d'un cycle machine, d'une session ? (périodogramme sommé
        sur les 80 numéros, 35 280 fréquences, loi du maximum simulée)
  f5-C  Deux tirages de l'archive se ressemblent-ils anormalement ?
        (histogramme EXACT des 2 489 344 020 recouvrements par paire,
        contre l'hypergéométrique ; c'est le test de réutilisation de graine
        — le bug Corriveau du Keno de Pennsylvanie, 1994 — mené à l'échelle
        de l'archive entière au lieu des 480 derniers tirages que l'app
        surveille)
"""

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import lab

T0 = time.time()
POOL, DRAWN = lab.POOL, lab.DRAWN
OV_MEAN = DRAWN * DRAWN / POOL
OV_SD = float(np.sqrt(DRAWN * (DRAWN / POOL) * (1 - DRAWN / POOL)
                      * (POOL - DRAWN) / (POOL - 1)))


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# --------------------------------------------------------------------------
# Outils — tout passe par une seule FFT par expérience
# --------------------------------------------------------------------------

def acf_all_lags(mask: np.ndarray) -> np.ndarray:
    """Σ_t |D_t ∩ D_{t+d}| pour d = 0..T-1, par FFT. O(T log T), pas O(T²)."""
    T = len(mask)
    n = 1 << int(np.ceil(np.log2(2 * T)))
    x = np.zeros((n, POOL))
    x[:T] = mask
    X = np.fft.rfft(x, axis=0)
    r = np.fft.irfft(X * np.conj(X), n=n, axis=0)
    return r[:T].sum(axis=1)


def z_by_lag(mask: np.ndarray, lag_max: int) -> np.ndarray:
    """Écart standardisé du recouvrement moyen, décalage par décalage.

    Sous H0 les paires (t, t+d) et (t+d, t+2d) sont NON CORRÉLÉES : le
    tirage du milieu est intégré des deux côtés à la même espérance 5. La
    variance de la moyenne est donc exactement 2,8481/(T−d), sans terme
    croisé — vérifié par la simulation qui suit.
    """
    T = len(mask)
    a = acf_all_lags(mask)[1:lag_max + 1]
    d = np.arange(1, lag_max + 1)
    npairs = T - d
    return (a / npairs - OV_MEAN) * np.sqrt(npairs) / OV_SD


def spectrum(mask: np.ndarray) -> np.ndarray:
    """Périodogramme sommé sur les 80 numéros, séries centrées."""
    x = mask.astype(float) - DRAWN / POOL
    X = np.fft.rfft(x, axis=0)
    p = (X.real ** 2 + X.imag ** 2).sum(axis=1)
    return p[1:]                       # la fréquence nulle est contrainte à 0


DECISION = ("significatif seulement si p franchit le seuil Holm du registre "
            "entier ; sinon consigné comme nul avec sa sensibilité")

TOK_A = lab.preregister(
    "f5.A", "le recouvrement moyen s'ecarte de 5 a un decalage quelconque",
    "max_d |z_d| sur d = 1..69560, z_d = (moyenne_d - 5)*sqrt(T-d)/1.68764",
    "loi du maximum simulee sur archives SRS completes (meme FFT)",
    DECISION, track="C")

TOK_B = lab.preregister(
    "f5.B", "le processus a une periodicite a une frequence quelconque",
    "max_f du periodogramme somme sur les 80 numeros, normalise par sa moyenne",
    "loi du maximum simulee sur archives SRS completes",
    DECISION, track="C")

TOK_C = lab.preregister(
    "f5.C", "deux tirages de l'archive se ressemblent anormalement "
            "(reutilisation de graine)",
    "recouvrement maximal sur les C(70560,2) paires, et effectifs de la queue >= 14",
    "hypergeometrique(80,20,20) exacte pour l'esperance ; loi de Poisson pour "
    "la queue rare, validee par simulation d'archives SRS completes",
    DECISION, track="C")


# --------------------------------------------------------------------------
# 0. Le null est-il celui qu'on croit ? (la variance sans terme croisé)
# --------------------------------------------------------------------------

rule("0. VÉRIFICATION DU NULL — la variance annoncée est-elle la bonne ?")
rng = np.random.default_rng(3)
m = lab.srs(20_000, rng)
zz = z_by_lag(m, 200)
say(f"   200 décalages sur une archive SRS de 20 000 :")
say(f"     moyenne des z : {zz.mean():+.4f}   (attendu 0)")
say(f"     écart-type    : {zz.std(ddof=1):.4f}   (attendu 1 si la variance"
    f" 2,8481/(T−d) est exacte)")
say("   -> si cet écart-type n'était pas 1, tous les z par décalage seraient faux.")


# --------------------------------------------------------------------------
# 1. Tous les décalages
# --------------------------------------------------------------------------

rule("1. f5-A — LES 69 560 DÉCALAGES D'UN COUP")

arch = lab.load()
mask = arch.mask
T = len(mask)
LAGMAX = T - 1000
say(f"   {T} tirages -> {LAGMAX} décalages, {T * LAGMAX - LAGMAX * (LAGMAX + 1) // 2:,}"
    f" paires couvertes")

t0 = time.time()
z_obs = z_by_lag(mask, LAGMAX)
say(f"   FFT : {time.time() - t0:.2f}s pour tous les décalages")
mA_obs = float(np.abs(z_obs).max())
dstar = int(np.argmax(np.abs(z_obs))) + 1
say(f"   max_d |z_d| = {mA_obs:.3f} au décalage {dstar}")
say(f"   décalage 1 : z = {z_obs[0]:+.3f}   (c'est la voie c1, ici sans la"
    f" moindre selection)")
say(f"   |z| > 3 : {int((np.abs(z_obs) > 3).sum())} décalages sur {LAGMAX}"
    f"   (attendu sous H0 : {LAGMAX * 0.0027:.0f})")
say(f"   |z| > 4 : {int((np.abs(z_obs) > 4).sum())}"
    f"   (attendu sous H0 : {LAGMAX * 6.3e-5:.1f})")

REPS = 300
say(f"\n   loi du maximum, {REPS} archives SRS complètes...")
rngA = np.random.default_rng(41)
vals = np.empty(REPS)
t0 = time.time()
for r in range(REPS):
    vals[r] = np.abs(z_by_lag(lab.srs(T, rngA), LAGMAX)).max()
    if (r + 1) % 50 == 0:
        say(f"     {r + 1}/{REPS}  ({time.time() - t0:.0f}s)")
nullA = lab.Null(float(vals.mean()), float(vals.std(ddof=1)), REPS, vals)
say(f"   null : {nullA.mean:.3f} ± {nullA.sd:.3f}")
say(f"   observé {mA_obs:.3f}  ->  z = {nullA.z(mA_obs):+.2f}   "
    f"p = {nullA.p_two_sided(mA_obs):.4f}")


# --------------------------------------------------------------------------
# 2. Toutes les fréquences
# --------------------------------------------------------------------------

rule("2. f5-B — LES 35 280 FRÉQUENCES")
say("   Un générateur à état fini, un cycle de machine, une frontière de")
say("   session : tout cela laisse une raie. Le périodogramme les cherche")
say("   toutes à la fois, sans en nommer une seule d'avance.")

p_obs = spectrum(mask)
mB_obs = float(p_obs.max() / p_obs.mean())
fstar = int(np.argmax(p_obs)) + 1
say(f"   max normalisé = {mB_obs:.3f} à la fréquence {fstar}/{len(p_obs) + 1}"
    f"  (période ≈ {T / fstar:.1f} tirages, soit {T / fstar * 5 / 60:.2f} h)")

REPS_B = 300
rngB = np.random.default_rng(42)
valsB = np.empty(REPS_B)
t0 = time.time()
for r in range(REPS_B):
    p = spectrum(lab.srs(T, rngB))
    valsB[r] = p.max() / p.mean()
    if (r + 1) % 50 == 0:
        say(f"     {r + 1}/{REPS_B}  ({time.time() - t0:.0f}s)")
nullB = lab.Null(float(valsB.mean()), float(valsB.std(ddof=1)), REPS_B, valsB)
say(f"   null : {nullB.mean:.3f} ± {nullB.sd:.3f}")
say(f"   observé {mB_obs:.3f}  ->  z = {nullB.z(mB_obs):+.2f}   "
    f"p = {nullB.p_two_sided(mB_obs):.4f}")


# --------------------------------------------------------------------------
# 3. Les 2,49 milliards de paires, une par une
# --------------------------------------------------------------------------

rule("3. f5-C — L'HISTOGRAMME EXACT DES 2 489 344 020 PAIRES")
say("   L'app surveille le recouvrement maximal sur ses 480 derniers tirages.")
say("   Ici on le fait sur l'archive entière — et pas seulement le maximum :")
say("   l'histogramme complet, comparé à l'hypergéométrique exacte.")


def pair_hist(m: np.ndarray, chunk: int = 256) -> np.ndarray:
    f = m.astype(np.float32)
    n = len(f)
    h = np.zeros(DRAWN + 1, np.int64)
    for a in range(0, n, chunk):
        b = min(n, a + chunk)
        o = (f[a:b] @ f.T).astype(np.int64)
        # ne compter que les paires (i, j) avec j > i
        for i in range(a, b):
            h += np.bincount(o[i - a, i + 1:], minlength=DRAWN + 1)
    return h


t0 = time.time()
h_obs = pair_hist(mask)
say(f"   {h_obs.sum():,} paires comptées en {time.time() - t0:.0f}s")

pmf = lab.overlap_pmf()
npairs = int(h_obs.sum())
exp_h = npairs * pmf
say("\n   recouvrement   observé            attendu (exact)      écart")
for k in range(DRAWN + 1):
    if exp_h[k] < 0.001 and h_obs[k] == 0:
        continue
    if exp_h[k] >= 30:
        z = (h_obs[k] - exp_h[k]) / np.sqrt(exp_h[k])
        say(f"       {k:>2}      {h_obs[k]:>16,}  {exp_h[k]:>18,.1f}   {z:+7.2f} σ")
    else:
        say(f"       {k:>2}      {h_obs[k]:>16,}  {exp_h[k]:>18,.3f}   "
            f"(Poisson λ = {exp_h[k]:.3f})")

mC_obs = int(np.max(np.flatnonzero(h_obs)))
say(f"\n   recouvrement maximal observé sur l'archive : {mC_obs}/20")
lam_ge = float(exp_h[mC_obs:].sum())
say(f"   sous H0, nombre attendu de paires à >= {mC_obs} : {lam_ge:.3f}")
p_C = 1 - np.exp(-lam_ge) if lam_ge < 30 else 1.0
say(f"   P(au moins une paire >= {mC_obs}) sous H0 : {p_C:.4f}")

say("\n   validation de l'approximation de Poisson sur 3 archives SRS :")
rngC = np.random.default_rng(43)
for r in range(3):
    hs = pair_hist(lab.srs(T, rngC))
    mx = int(np.max(np.flatnonzero(hs)))
    say(f"     archive simulée {r + 1} : max = {mx}/20,"
        f" effectif à {mC_obs} = {hs[mC_obs]:,} (attendu {exp_h[mC_obs]:,.1f})")

# Le chi2 global sur l'histogramme entier, pour ne rien laisser passer.
keep = exp_h >= 30
chi2 = float(((h_obs[keep] - exp_h[keep]) ** 2 / exp_h[keep]).sum())
df = int(keep.sum()) - 1
say(f"\n   χ² sur les {df + 1} classes non rares : {chi2:.1f} pour {df} degrés")
say("   (indicatif seulement : les 2,49 milliards de paires ne sont pas")
say("    indépendantes — chaque tirage entre dans 70 559 paires ; c'est")
say("    l'histogramme lui-même, et la queue, qui font foi)")


# --------------------------------------------------------------------------
# 4. Sensibilité
# --------------------------------------------------------------------------

rule("4. SENSIBILITÉ")
say("   f5-A : quelle avance de recouvrement à un décalage donné serait vue ?")
seuil = nullA.mean + 3 * nullA.sd


def contaminate_lag(m, rng, d, eps):
    m = m.copy()
    for t in range(d, len(m)):
        if rng.random() >= eps:
            continue
        prev = np.flatnonzero(m[t - d] & ~m[t])
        cur = np.flatnonzero(m[t] & ~m[t - d])
        if len(prev) and len(cur):
            m[t, rng.choice(prev)] = True
            m[t, rng.choice(cur)] = False
    return m


rngP = np.random.default_rng(44)
say(f"\n   seuil à 3σ du null : {seuil:.3f}")
say("   ε        avance réelle au décalage 137     max_d |z_d|     détecté")
for eps in (0.005, 0.01, 0.02, 0.04):
    got, gains = [], []
    for r in range(2):
        mm = contaminate_lag(lab.srs(T, rngP), rngP, 137, eps)
        a = acf_all_lags(mm)
        gains.append(a[137] / (T - 137) - OV_MEAN)
        got.append(float(np.abs(z_by_lag(mm, LAGMAX)).max()))
    got = np.array(got)
    say(f"   {eps:<8.3f} +{np.mean(gains):.4f} hits"
        f"                    {got.mean():8.3f}       {int((got >= seuil).sum())}/2")

say("\n   f5-B : quelle amplitude de raie serait vue ?")
seuilB = nullB.mean + 3 * nullB.sd
say(f"   seuil à 3σ du null : {seuilB:.3f}")
say("   amplitude   période      max normalisé    détecté")
for amp in (0.002, 0.005, 0.010):
    got = []
    for r in range(2):
        mm = lab.srs(T, rngP)
        # une raie : on force une modulation de la présence du numéro 1..40
        ph = 2 * np.pi * np.arange(T) / 512.0
        push = amp * np.sin(ph)
        for t in range(T):
            if push[t] > 0 and rngP.random() < push[t] * 20:
                off = np.flatnonzero(mm[t, :40] == False)
                on = np.flatnonzero(mm[t, 40:])
                if len(off) and len(on):
                    mm[t, rngP.choice(off)] = True
                    mm[t, 40 + rngP.choice(on)] = False
        p = spectrum(mm)
        got.append(float(p.max() / p.mean()))
    got = np.array(got)
    # Le dénominateur est LU sur le tableau et non écrit à la main : la
    # première version imprimait « /3 » sur une boucle de 2 réplicats, et
    # le rapport a publié un 0/3 qui était un 0/2. Une puissance de 0 sur 2
    # est une information nettement plus faible qu'un 0 sur 3.
    say(f"   {amp:<11.3f} 512 tirages  {got.mean():13.3f}    "
        f"{int((got >= seuilB).sum())}/{len(got)}")


# --------------------------------------------------------------------------
# 5. Registre
# --------------------------------------------------------------------------

lab.record(TOK_A, mA_obs, nullA, power_at="cf. section 4",
           verdict="", notes=f"maximum au decalage {dstar} ; lag 1 : z = {z_obs[0]:+.3f}")
lab.record(TOK_B, mB_obs, nullB, power_at="cf. section 4",
           verdict="", notes=f"maximum a la frequence {fstar}, periode {T / fstar:.1f} tirages")
lab.record(TOK_C, float(mC_obs), None, p=float(p_C), power_at="Poisson validee par 3 archives SRS",
           verdict="", notes=f"recouvrement maximal sur {npairs:,} paires ; "
                             f"lambda(>= {mC_obs}) = {lam_ge:.3f}")

rule(f"consigné au registre — total {time.time() - T0:.0f}s")
