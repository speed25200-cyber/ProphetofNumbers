"""f4 — coder le tirage. Combien de BITS l'essaim sait-il vraiment ?

L'idée, jamais tentée ici
--------------------------
Toutes les voies du dossier réduisent un tirage à UN nombre : un
recouvrement, un écart, une fréquence. C'est jeter 61 bits pour n'en garder
que trois. f3 lui-même ne regarde que le top-20 de chaque tête.

Ici on ne réduit rien. On demande à chaque modèle de PARIER SUR LE TIRAGE
ENTIER, et on le paie exactement à ce que son pari valait.

Sous H0, le tirage est uniforme sur les C(80,20) = 3,54·10^18 sous-ensembles
de taille 20 : il coûte log2 C(80,20) = 61,6165 bits, et pas un de moins.
Un modèle qui, avant de voir le tirage, propose une loi Q sur ces mêmes
sous-ensembles reçoit

    e_t = Q(D_t) · C(80,20)

et sous H0, E[e_t | passé] = Σ_S (1/C)·Q(S)·C = 1 EXACTEMENT. C'est une
e-valeur, sans approximation, sans calibration, sans simulation.

Trois conséquences que le dossier n'avait pas :

  1. **Pas de correction de multiplicité.** La moyenne d'e-valeurs est une
     e-valeur. On peut donc lancer 174 modèles à la fois et lire le résultat
     du mélange tel quel — là où le registre impose un seuil de Holm à
     1,5·10⁻⁵ à toute statistique classique.
  2. **Valide à tout instant** (Ville) : P(sup_t E_t ≥ 1/α) ≤ α. On peut
     regarder la courbe en continu sans dépenser d'alpha.
  3. **La réponse est en BITS**, donc en argent : (1/T)·log2 E est le taux de
     croissance de Kelly. Zéro bit = aucune information exploitable, quelle
     que soit la mise.

La loi Q : Bernoulli conditionnelle
-----------------------------------
Chaque modèle produit 80 poids w_i > 0 (fonction du passé strict). La loi

    Q(S) = Π_{i∈S} w_i / e_20(w)

où e_20 est le polynôme symétrique élémentaire de degré 20, est une vraie
loi sur les sous-ensembles de taille 20 — c'est la Bernoulli conditionnelle.
e_20(w) se calcule par récurrence en 80 × 21 produits, vectorisée ici sur
tous les modèles et tous les tirages d'un bloc.

Les modèles : les 26 têtes de l'app, leur mélange AdaHedge, plus deux signaux
bruts que le dossier a déjà interrogés — l'appartenance au tirage précédent
et l'écho du bonus (23ᵉ voie) — chacun incliné par θ ∈ {±0,02 ; ±0,05 ;
±0,10 ; ±0,20}. 29 × 6 = 174 paris simultanés, et un seul chiffre à lire.
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
LOG_C = float(sum(math.log(POOL - i) - math.log(i + 1) for i in range(DRAWN)))
THETAS = np.array([0.02, 0.05, 0.10, -0.02, -0.05, -0.10])


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def shiryaev_roberts(loge: np.ndarray) -> np.ndarray:
    """R_t = (1 + R_{t-1})·f_t, en log, vectorisé sur les modèles.

    f2 a mesuré ce qu'un e-processus cumulé depuis le premier tirage coûte :
    le même défaut est détecté 1,00 fois sur 1 quand il tombe tôt, 0,00 quand
    il tombe tard. La cause est arithmétique — exp(Σ log f) ne dépend pas de
    l'ORDRE, donc sa valeur finale ignore quand le défaut s'est produit, et
    son maximum courant ne bouge plus une fois la richesse effondrée.

    R_t = Σ_{k≤t} Π_{s=k..t} f_s est la somme des paris démarrés à chaque
    instant : R_t/t est la moyenne de t e-processus, donc une e-valeur. Un
    biais apparu au tirage 70 000 est vu par le pari relancé au tirage 70 000.
    """
    T, M = loge.shape
    out = np.empty((T, M))
    r = np.full(M, -np.inf)
    for t in range(T):
        r = np.minimum(np.logaddexp(0.0, r) + loge[t], 700.0)
        out[t] = r
    return out


def e20_log(W: np.ndarray) -> np.ndarray:
    """log e_20(w) pour un bloc de poids (B, M, 80), poids déjà centrés à 1."""
    B, M, _ = W.shape
    E = np.zeros((B, M, DRAWN + 1))
    E[:, :, 0] = 1.0
    for i in range(POOL):
        E[:, :, 1:] += W[:, :, i:i + 1] * E[:, :, :-1]
    return np.log(E[:, :, DRAWN])


# --------------------------------------------------------------------------
# Pré-enregistrement
# --------------------------------------------------------------------------

TOK = lab.preregister(
    "f4.mix",
    "un portefeuille de 174 modèles, pariant sur le TIRAGE ENTIER, accumule "
    "de la richesse contre le hasard",
    "log10 de la moyenne des e-processus (Bernoulli conditionnelle, e_t = "
    "Q(D_t)·C(80,20))",
    "aucune calibration : E[e_t|passé] = 1 par construction ; seuil de Ville "
    "1/alpha, verifie par simulation",
    "significatif si E >= 20 (alpha = 0,05, valide a tout instant) ; le seuil "
    "de Ville ne se corrige pas de la multiplicite car la moyenne d'e-valeurs "
    "est une e-valeur",
    track="C")

TOK_SR = lab.preregister(
    "f4.restart",
    "un portefeuille qui inclut les paris RELANCES a chaque tirage accumule "
    "de la richesse contre le hasard, y compris pour un biais apparu tard",
    "max_t log10 de la moyenne des 348 e-processus (174 depuis le debut, 174 "
    "en melange de Shiryaev-Roberts)",
    "aucune calibration : moyenne d'e-valeurs = e-valeur ; seuil de Ville",
    "significatif si le sup depasse 20 ; f2 a montre qu'un portefeuille sans "
    "relance est structurellement aveugle a un defaut tardif, ce jeton couvre "
    "ce cas",
    track="C")

TOK_MAX = lab.preregister(
    "f4.sup",
    "le portefeuille franchit le seuil de Ville a un instant quelconque",
    "max_t log10 E_t (supremum courant du melange)",
    "inegalite de Ville, P(sup E >= 1/alpha) <= alpha",
    "significatif si le sup depasse 20 ; sans correction, Ville couvrant "
    "deja l'inspection continue",
    track="C")


# --------------------------------------------------------------------------
# 1. Vérification de la construction — E[e_t] doit valoir 1, pas « environ »
# --------------------------------------------------------------------------

rule("1. LA CONSTRUCTION EST-ELLE UNE VRAIE e-VALEUR ?")
say("   Un e-processus faux monte tout seul et invente un signal. Avant de")
say("   l'appliquer, on vérifie E[e_t] = 1 sur des tirages purement uniformes,")
say("   avec des poids arbitraires mais fixés à l'avance.")

rng = np.random.default_rng(11)
for theta in (0.05, 0.20, -0.20):
    n = 200_000
    z = rng.standard_normal((n, POOL))
    W = np.exp(theta * z)
    W /= W.mean(axis=1, keepdims=True)
    m = lab.srs(n, rng)
    logZ = e20_log(W[:, None, :])[:, 0]
    lognum = np.where(m, np.log(W), 0.0).sum(axis=1)
    e = np.exp(LOG_C + lognum - logZ)
    se = e.std(ddof=1) / np.sqrt(n)
    say(f"   θ = {theta:+.2f}   moyenne de e_t = {e.mean():.5f} ± {se:.5f}"
        f"   (écart à 1 : {(e.mean() - 1) / se:+.2f} σ)")


# --------------------------------------------------------------------------
# 2. Le portefeuille sur l'archive réelle
# --------------------------------------------------------------------------

rule("2. LE PORTEFEUILLE SUR L'ARCHIVE — 174 paris simultanés")

arch = lab.load()
mask = arch.mask
bonus = arch.bonus
T_all = len(mask)
say(f"   {T_all} tirages ; 29 signaux × {len(THETAS)} inclinaisons")

SIG_NAMES = sp.HEAD_IDS + ["ensemble", "lag1", "bonus"]
N_SIG = len(SIG_NAMES)
M = N_SIG * len(THETAS)
MODEL_NAMES = [f"{s}@{t:+.2f}" for s in SIG_NAMES for t in THETAS]

CHUNK = 512


def portfolio(mask, bonus, progress=0):
    """Renvoie (log e_t) pour chaque modèle, (steps, M)."""
    T = len(mask)
    heads = sp.make_heads()
    n = len(heads)
    w = np.full(n, 1 / n)
    cum_loss = np.zeros(n)
    ada_gap = 1e-3
    steps = max(0, T - sp.WARMUP)
    out = np.empty((steps, M))

    buf_W = np.empty((CHUNK, M, POOL))
    buf_hit = np.empty((CHUNK, POOL), bool)
    fill = 0
    base = 0
    prev = None
    last_bonus = -1

    def flush(k, at):
        Wc = buf_W[:k]
        logZ = e20_log(Wc)
        logn = np.where(buf_hit[:k][:, None, :], np.log(Wc), 0.0).sum(axis=2)
        out[at:at + k] = LOG_C + logn - logZ

    j = 0
    for t in range(T):
        hit = mask[t].astype(float)
        if t >= sp.WARMUP:
            fields = np.stack([sp._z(h.field()) for h in heads])
            ens = w @ fields
            lag1 = prev.astype(float) if prev is not None else np.zeros(POOL)
            bsig = np.zeros(POOL)
            if 1 <= last_bonus <= POOL:
                bsig[last_bonus - 1] = 1.0
            sig = np.vstack([fields, sp._z(ens)[None, :],
                             sp._z(lag1)[None, :], sp._z(bsig)[None, :]])
            Wj = np.exp(THETAS[None, :, None] * sig[:, None, :]).reshape(M, POOL)
            Wj /= Wj.mean(axis=1, keepdims=True)
            buf_W[fill] = Wj
            buf_hit[fill] = mask[t]
            fill += 1
            if fill == CHUNK:
                flush(CHUNK, base)
                base += CHUNK
                fill = 0

            # AdaHedge, identique à f3 et à Swift
            tops = np.stack([sp._top(fields[i]) for i in range(n)])
            o = mask[t][tops].sum(axis=1)
            losses = 1 - o / DRAWN
            eta = np.log(n) / ada_gap
            h_loss = float(w @ losses)
            lmin = float(losses.min())
            accum = float(w @ np.exp(-eta * (losses - lmin)))
            ada_gap += max(0.0, h_loss - (lmin - np.log(max(accum, 1e-300)) / eta))
            cum_loss += losses
            eta = np.log(n) / ada_gap
            raw = np.exp(-eta * (cum_loss - cum_loss.min()))
            s = raw.sum()
            w = np.full(n, 1 / n) if (s <= 0 or not np.isfinite(s)) else raw / s
            w = 0.98 * w + 0.02 / n
            j += 1
        for h in heads:
            h.absorb(hit)
        prev = mask[t]
        if bonus is not None and 1 <= bonus[t] <= POOL:
            last_bonus = int(bonus[t])
        if progress and t % progress == 0:
            say(f"     {t}/{T}  ({time.time() - T0:.0f}s)")
    if fill:
        flush(fill, base)
    return out


t0 = time.time()
LOGE = portfolio(mask, bonus, progress=20_000)
say(f"   parcouru en {time.time() - t0:.0f}s")

cum = np.cumsum(LOGE, axis=0)                     # (steps, M) log E_t par modèle
# Mélange à poids égaux : la moyenne d'e-valeurs est une e-valeur.
mx = cum.max(axis=1, keepdims=True)
log_mix = (mx[:, 0] + np.log(np.exp(cum - mx).mean(axis=1)))
log10_mix = log_mix / np.log(10)

say(f"\n   E final du mélange        : 10^{log10_mix[-1]:+.3f}")
say(f"   sup_t E du mélange        : 10^{log10_mix.max():+.3f}"
    f"  (au pas {int(np.argmax(log10_mix))} / {len(log10_mix)})")
say(f"   seuil de Ville à α = 0,05 : 10^{math.log10(20):+.3f}")
say(f"   taux de Kelly             : {log_mix[-1] / np.log(2) / len(cum):+.3e} bit/tirage")
say(f"   (un tirage coûte {LOG_C / math.log(2):.4f} bits sous H0)")

# --------------------------------------------------------------------------
# 2 bis. Les mêmes paris, mais relancés à chaque tirage
# --------------------------------------------------------------------------

rule("2 bis. LE MÊME PORTEFEUILLE, RELANCÉ À CHAQUE TIRAGE")
say("   Le mélange ci-dessus est cumulé depuis le premier tirage. f2 a montré")
say("   qu'une telle martingale est structurellement aveugle à un défaut")
say("   tardif : sa richesse est déjà effondrée quand le défaut arrive. On")
say("   ajoute donc les mêmes 174 paris relancés à CHAQUE tirage.")

SR = shiryaev_roberts(LOGE)
logt = np.log(np.arange(1, len(SR) + 1))[:, None]
ALL = np.concatenate([cum, SR - logt], axis=1)          # 348 e-processus
mx2 = ALL.max(axis=1, keepdims=True)
log_all = mx2[:, 0] + np.log(np.exp(ALL - mx2).mean(axis=1))
log10_all = log_all / np.log(10)

mxs = (SR - logt).max(axis=1, keepdims=True)
log_sr = mxs[:, 0] + np.log(np.exp((SR - logt) - mxs).mean(axis=1))
say(f"\n   sup_t E, relancés seuls   : 10^{(log_sr / np.log(10)).max():+.3f}")
say(f"   sup_t E, les 348 ensemble : 10^{log10_all.max():+.3f}"
    f"  (au pas {int(np.argmax(log10_all))} / {len(log10_all)})")
say(f"   E final, les 348 ensemble : 10^{log10_all[-1]:+.3f}")
say(f"   seuil de Ville à α = 0,05 : 10^{math.log10(20):+.3f}")

best = int(np.argmax(cum[-1]))
say(f"\n   meilleur modèle isolé     : {MODEL_NAMES[best]}  ->  10^{cum[-1, best] / np.log(10):+.3f}")
say(f"   pire modèle isolé         : {MODEL_NAMES[int(np.argmin(cum[-1]))]}"
    f"  ->  10^{cum[-1].min() / np.log(10):+.3f}")
say("   (le mélange est la seule lecture valide ; un modèle choisi APRÈS coup")
say("    est soumis à la malédiction du vainqueur, le mélange non)")

sig_last = cum[-1].reshape(N_SIG, len(THETAS))
say("\n   par signal, log10 E au meilleur θ :")
ordre = np.argsort(-sig_last.max(axis=1))
for i in ordre[:6]:
    k = int(np.argmax(sig_last[i]))
    say(f"     {SIG_NAMES[i]:<14} θ = {THETAS[k]:+.2f}   10^{sig_last[i, k] / np.log(10):+.3f}")


# --------------------------------------------------------------------------
# 3. Sensibilité — combien de bits faudrait-il pour que ça se voie ?
# --------------------------------------------------------------------------

rule("3. SENSIBILITÉ — quelle avance le portefeuille verrait-il ?")
say("   Contamination momentum (un numéro du tirage précédent réinjecté avec")
say("   probabilité ε), sur T = 20 000. On lit E, pas un z : le seuil est 20.")

T_POW = 20_000
rngp = np.random.default_rng(909)


def contaminate(m, rng, eps):
    m = m.copy()
    for t in range(1, len(m)):
        if rng.random() >= eps:
            continue
        prev = np.flatnonzero(m[t - 1] & ~m[t])
        cur = np.flatnonzero(m[t] & ~m[t - 1])
        if len(prev) and len(cur):
            m[t, rng.choice(prev)] = True
            m[t, rng.choice(cur)] = False
    return m


say("\n   ε        avance réelle     sup_t log10 E (348)   E >= 20 ?")
for eps in (0.0, 0.02, 0.05, 0.10):
    m = lab.srs(T_POW, rngp)
    if eps:
        m = contaminate(m, rngp, eps)
    lag1 = float((m[1:] & m[:-1]).sum(axis=1).mean())
    lg = portfolio(m, None)
    c = np.cumsum(lg, axis=0)
    sr = shiryaev_roberts(lg) - np.log(np.arange(1, len(lg) + 1))[:, None]
    a = np.concatenate([c, sr], axis=1)
    mm = a.max(axis=1, keepdims=True)
    l10 = (mm[:, 0] + np.log(np.exp(a - mm).mean(axis=1))) / np.log(10)
    say(f"   {eps:<8.2f} +{lag1 - 5:.4f} hits     {l10.max():+10.3f}"
        f"            {'oui' if l10.max() >= math.log10(20) else 'non'}")


# --------------------------------------------------------------------------
# 4. Registre
# --------------------------------------------------------------------------

lab.record(TOK, float(log10_mix[-1]), None, p=float(min(1.0, 10 ** (-log10_mix[-1]))),
           power_at=f"contamination momentum, cf. section 3 (T={T_POW})",
           verdict="",
           notes=f"{M} modeles, melange a poids egaux ; Kelly "
                 f"{log_mix[-1] / np.log(2) / len(cum):+.3e} bit/tirage")
lab.record(TOK_SR, float(log10_all.max()), None,
           p=float(min(1.0, 10 ** (-log10_all.max()))),
           power_at=f"contamination momentum, cf. section 3 (T={T_POW})",
           verdict="", notes="348 e-processus : 174 depuis le debut + 174 relances "
                             "a chaque tirage (Shiryaev-Roberts)")
lab.record(TOK_MAX, float(log10_mix.max()), None,
           p=float(min(1.0, 10 ** (-log10_mix.max()))),
           power_at=f"contamination momentum, cf. section 3 (T={T_POW})",
           verdict="", notes="supremum courant, valide a tout instant (Ville)")

np.save(os.path.join(os.path.dirname(os.path.abspath(__file__)), "f4_log10_mix.npy"),
        log10_mix.astype(np.float32))
rule(f"consigné au registre — total {time.time() - T0:.0f}s")
