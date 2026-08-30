"""h2 — deux améliorations PROUVABLES de la méthode, vérifiées avant câblage.

Le théorème d'invariance ferme la question « quels numéros ». Ce qui reste
améliorable, c'est la MÉTHODE : à quelle vitesse la politique capte un
biais s'il existe. Deux améliorations, chacune avec sa théorie :

  1. L'ÉCHO ADAPTATIF. L'app applique un départage FIGÉ (−0,0158, la valeur
     mesurée par d7 sur l'archive). Un chiffre figé a deux défauts : si
     l'effet est du bruit, la correction ne s'éteint jamais ; s'il est réel
     et dérive, elle ne suit pas. Le remplaçant : le posterior Beta de
     P(bonus_{t−1} ∈ tirage_t), prior Beta(1,3) (moyenne 0,25, poids 4).
     - Sous H0 : la correction s'éteint en 1/sqrt(n) — vérifié sur archives
       simulées.
     - Sur l'archive réelle : le posterior converge de lui-même vers le
       déficit mesuré — l'archive ENSEIGNE la constante au lieu qu'on la
       fige.
     - Coût : nul en espérance, par le théorème d'invariance (tout
       départage fonction du passé est gratuit). Ce n'est pas une
       hypothèse, c'est le théorème g1-C.

  2. LE PRIOR PAR BLOCS. Le moniteur relance un pari par tirage, avec le
     prior w_k = 1/(k(k+1)) : budget 2·ln k nats pour un défaut au pas k.
     Relancer par BLOCS de 16 tirages (80 minutes) avec le prior sur
     l'indice de bloc donne un budget 2·ln(k/16) = 2·ln k − 5,5 nats — un
     gain PROUVÉ (même martingale, moins d'instants de relance à payer),
     au prix d'un retard de détection d'au plus 16 tirages, négligeable
     devant toute fenêtre de défaut réaliste (>= 200).
"""

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import lab

T0 = time.time()
C = math.comb


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# --------------------------------------------------------------------------
# 1. L'écho adaptatif
# --------------------------------------------------------------------------

rule("1. L'ÉCHO ADAPTATIF — l'archive enseigne la constante, le bruit s'éteint")

arch = lab.load()
mask, bonus = arch.mask, arch.bonus
T = len(mask)

a, b = 1.0, 3.0                      # prior Beta(1,3), moyenne 0,25
hits = tries = 0
for t in range(1, T):
    pb = bonus[t - 1]
    if 1 <= pb <= 80:
        tries += 1
        if mask[t, pb - 1]:
            hits += 1
post = (a + hits) / (a + b + tries)
rel = (0.25 - post) / 0.25
say(f"   archive réelle : {tries} paires, écho observé {hits / tries:.6f}")
say(f"   posterior Beta(1,3) : {post:.6f}  ->  correction relative {rel:+.6f}")
say(f"   (la constante figée de l'app : 0,0158 ; d7 mesurait 0,246049)")

say("\n   sous H0 (20 archives SRS avec bonus uniforme), la correction :")
rng = np.random.default_rng(11)
rels = []
for r in range(20):
    m = lab.srs(T, rng)
    bn = rng.integers(1, 81, size=T)
    h = int(m[np.arange(1, T), bn[:-1] - 1].sum())
    p = (a + h) / (a + b + (T - 1))
    rels.append((0.25 - p) / 0.25)
rels = np.array(rels)
say(f"   moyenne {rels.mean():+.5f}   écart-type {rels.std(ddof=1):.5f}"
    f"   (théorie 1/√n : {math.sqrt(0.25 * 0.75 / T) / 0.25:.5f})")
say("   -> la correction adaptative vaut ±0,0065 sous H0 au lieu d'un −0,0158")
say("      permanent : elle s'éteint, la figée non. Coût en espérance : nul,")
say("      par le théorème d'invariance (g1-C) — tout départage est gratuit.")


# --------------------------------------------------------------------------
# 2. Le prior par blocs — théorie puis mesure
# --------------------------------------------------------------------------

rule("2. LE PRIOR PAR BLOCS — 5,5 nats de budget rendus, mesurés")

P0 = 0.25
THETAS = [0.05, 0.10, 0.20, 0.40, -0.05, -0.10, -0.20, -0.40]
LOGM = [math.log(P0 * math.exp(t) + 1 - P0) for t in THETAS]
T_TOT = 70_560
B = 16
k_ex = 65_000
say(f"   budget pour un défaut au pas k = {k_ex} :")
say(f"     prior par pas    : ln 640 + 2·ln k        = {math.log(640) + 2 * math.log(k_ex):.1f} nats")
say(f"     prior par blocs  : ln 640 + 2·ln(k/{B})    = "
    f"{math.log(640) + 2 * math.log(k_ex / B):.1f} nats")
say(f"     retard maximal ajouté : {B} tirages ({B * 5} minutes)")

th = np.array(THETAS)
lm_b = np.array(LOGM)
ov_pmf = np.array([C(20, o) * C(60, 20 - o) / C(80, 20) for o in range(21)])
lm_o = np.log(np.array([(ov_pmf * np.exp(t * np.arange(21))).sum() for t in th]))
rng2 = np.random.default_rng(4242)


def simulate(L, p1, block, reps, seed):
    r = np.random.default_rng(seed)
    start = r.integers(60_000, T_TOT - max(L, 1), size=reps)
    det = np.zeros(reps, bool)
    cum_b = np.zeros((reps, 8)); cum_o = np.zeros((reps, 8))
    sr_b = np.full((reps, 8), -np.inf); sr_o = np.full((reps, 8), -np.inf)
    ovs = r.hypergeometric(20, 60, 20, size=(T_TOT, reps))
    us = r.random((T_TOT, reps))
    for t in range(T_TOT):
        in_defect = (L > 0) & (t >= start) & (t < start + L)
        p = np.where(in_defect, p1, P0)
        x = (us[t] < p).astype(float)
        lf_b = th[None, :] * x[:, None] - lm_b[None, :]
        lf_o = th[None, :] * ovs[t][:, None] - lm_o[None, :]
        cum_b = np.minimum(80, cum_b + lf_b)
        cum_o = np.minimum(80, cum_o + lf_o)
        if block:
            if t % B == 0:
                j = t // B + 1
                lw = -math.log(j * (j + 1))
                sr_b = np.logaddexp(sr_b, lw)
                sr_o = np.logaddexp(sr_o, lw)
            sr_b = np.minimum(80, sr_b + lf_b)
            sr_o = np.minimum(80, sr_o + lf_o)
            cash = 1.0 / (t // B + 2)
        else:
            lw = -math.log((t + 1) * (t + 2))
            sr_b = np.minimum(80, np.logaddexp(sr_b, lw) + lf_b)
            sr_o = np.minimum(80, np.logaddexp(sr_o, lw) + lf_o)
            cash = 1.0 / (t + 2)
        if t % 4 == 0 or in_defect.any():
            e = (np.exp(np.minimum(60, cum_b)).sum(1) + np.exp(np.minimum(60, cum_o)).sum(1)
                 + (np.exp(np.minimum(60, sr_b)) + cash).sum(1)
                 + (np.exp(np.minimum(60, sr_o)) + cash).sum(1)) / 32
            det |= e >= 20
    return det.mean()


say("\n   fausses alertes SANS défaut (240 réplicats, garantie <= 5 %) :")
t0 = time.time()
fa_blk = simulate(0, P0, block=True, reps=240, seed=1)
say(f"     prior par blocs : {fa_blk:.3f} ± {math.sqrt(max(fa_blk * (1 - fa_blk), 1e-9) / 240):.3f}"
    f"   ({time.time() - t0:.0f}s)")
say("     (prior par pas, déjà mesuré en h1/ctrl : 0,042 ± 0,013)")

say("\n   puissance, défaut TARDIF (60 réplicats) :")
say("   L        p1      par pas   par blocs")
for L, p1 in ((500, 0.20), (2000, 0.20), (500, 0.10), (2000, 0.10)):
    pw_s = simulate(L, p1, block=False, reps=60, seed=100 + L)
    pw_b = simulate(L, p1, block=True, reps=60, seed=100 + L)
    say(f"   {L:<8} {p1:<7} {pw_s:5.2f}     {pw_b:5.2f}")


# --------------------------------------------------------------------------
# 3. Les valeurs exactes du test Swift (recurrence par blocs)
# --------------------------------------------------------------------------

rule("3. VALEURS EXACTES POUR LE TEST SWIFT — récurrence par blocs")
theta, p = 0.40, 0.25
logM = math.log(p * math.exp(theta) + 1 - p)
M64 = (1 << 64) - 1


def lae(x, y):
    if x == -math.inf:
        return y
    if y == -math.inf:
        return x
    m = max(x, y)
    return m + math.log1p(math.exp(min(x, y) - m))


def traj(defect_first):
    seed = 20260827

    def bern(q):
        nonlocal seed
        seed = (seed * 6364136223846793005 + 1442695040888963407) & M64
        return 1.0 if (seed >> 33) / 2147483648.0 < q else 0.0

    quiet, loud = 20000, 400
    cum, sr = 0.0, -math.inf
    mc, mn, n = 0.0, 0.0, 0.0
    for t in range(quiet + loud):
        biased = t < loud if defect_first else t >= quiet
        x = 1.0 if biased else bern(p)
        lf = theta * x - logM
        cum += lf
        if t % B == 0:
            j = t // B + 1
            sr = lae(sr, -math.log(j * (j + 1)))
        sr = min(700, sr + lf)
        mc = max(mc, cum)
        n = math.exp(min(700, sr)) + 1.0 / (t // B + 2)
        mn = max(mn, n)
    return math.exp(cum), math.exp(mc), n, mn


late = traj(False)
early = traj(True)
say(f"   TARD : cum final {late[0]:.3e}  cum sup {late[1]:.3e}  "
    f"N final {late[2]:.3e}  N sup {late[3]:.3e}")
say(f"   TOT  : cum final {early[0]:.3e}  cum sup {early[1]:.3e}  "
    f"N final {early[2]:.3e}  N sup {early[3]:.3e}")

rule(f"total {time.time() - T0:.0f}s")
