"""f3 — le PRÉDICTEUR comme statistique de test.

Ce qui n'avait jamais été fait
------------------------------
Les 23 voies du dossier testent une propriété des TIRAGES : une fréquence,
un écart, un recouvrement, un lag. Chacune choisit une statistique, la
calibre, et conclut. Aucune n'a jamais testé la seule chose qui décide du
produit : **l'essaim déployé bat-il le hasard ?**

Ce n'est pas « un test de plus ». C'est un renversement :

  * une voie classique demande « telle régularité existe-t-elle ? » et doit
    la nommer d'avance ;
  * ici on demande « l'une QUELCONQUE des 26 hypothèses du banc, plus leur
    combinaison adaptative, rapporte-t-elle un hit de plus que le hasard ? »
    — la multiplicité du choix de tête est absorbée dans la LOI DU MAXIMUM,
    calibrée en rejouant l'essaim entier sur des archives synthétiques.

Le test est exact sans rien supposer du contenu des prédictions, grâce au
théorème qui borne déjà tout le dossier : pour TOUT ensemble de 20 numéros
choisi sans voir le tirage, le recouvrement suit une hypergéométrique(80,20,20),
d'espérance 5 et d'écart-type 1,68764. Donc sous H0, pour chaque tête,

    S_h = Σ_t (recouvrement_{h,t} − 5)

est une martingale de loi connue. Le seul inconnu est la DÉPENDANCE entre
têtes — et elle est obtenue par simulation, pas par formule.

Quatre statistiques, pré-enregistrées avant lecture
---------------------------------------------------
  F3-A  max_h z_h            — la meilleure des 26 têtes bat-elle le hasard ?
  F3-B  z_ens                — l'ensemble AdaHedge (ce que l'app affiche) ?
  F3-C  transfert            — la tête gagnante d'une moitié gagne-t-elle sur
                               l'autre ? (malédiction du vainqueur corrigée
                               par validation croisée : c'est la seule version
                               EXPLOITABLE de la question)
  F3-D  têtes effectives     — les poids se concentrent-ils plus que le
                               hasard ne l'autorise ?

Et une mesure de sensibilité, sans laquelle un nul ne veut rien dire :
quelle avance faudrait-il pour que F3-A se déclenche ?
"""

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import lab
import swarm_py as sp

T0 = time.time()


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# --------------------------------------------------------------------------
# Pré-enregistrement — AVANT de regarder quoi que ce soit
# --------------------------------------------------------------------------

DECISION = ("significatif seulement si p franchit le seuil Holm du registre "
            "entier ; sinon consigné comme nul avec sa sensibilité")

TOK_A = lab.preregister(
    "f3.A", "l'une des 26 têtes de l'essaim bat le hasard sur l'archive entière",
    "max_h (S_h / (1.68764*sqrt(T))), S_h = somme des recouvrements top-20 moins 5T",
    "essaim entier rejoué sur archives SRS complètes (loi du maximum) + null "
    "conditionnel martingale sur les prédictions observées",
    DECISION, track="C")

TOK_B = lab.preregister(
    "f3.B", "l'ensemble AdaHedge de l'app bat le hasard",
    "z du recouvrement top-20 de l'ensemble pondéré",
    "essaim entier rejoué sur archives SRS complètes", DECISION, track="C")

TOK_C = lab.preregister(
    "f3.C", "la tête gagnante sur une moitié de l'archive garde son avance sur l'autre",
    "moyenne sur 8 plis du z hors-echantillon de la tête gagnante en echantillon",
    "meme procedure sur archives SRS complètes", DECISION, track="C")

TOK_D = lab.preregister(
    "f3.D", "les poids AdaHedge se concentrent plus que sous H0",
    "moyenne des tetes effectives exp(H(w)) sur la seconde moitie",
    "essaim entier rejoué sur archives SRS complètes", DECISION, track="C")


# --------------------------------------------------------------------------
# 1. L'essaim sur l'archive réelle
# --------------------------------------------------------------------------

rule("1. L'ESSAIM SUR L'ARCHIVE RÉELLE — 70 560 tirages, marche avant")

arch = lab.load()
mask = arch.mask
T_all = len(mask)
say(f"   {T_all} tirages, {sp.N_HEADS} têtes, échauffement {sp.WARMUP}")

t0 = time.time()
obs = sp.run(mask, keep_picks=True)
say(f"   rejoué en {time.time() - t0:.0f}s — {obs['steps']} évaluations par tête")

OV = obs["ov"].astype(np.int64)          # (steps, 26)
STEPS = obs["steps"]


def z_heads(ov):
    T = len(ov)
    return (ov.sum(axis=0) - T * sp.OV_MEAN) / (sp.OV_SD * np.sqrt(T))


z_obs = z_heads(OV)
zA_obs = float(z_obs.max())
zB_obs = sp.z_of(obs["ov_ens"].astype(np.int64))
zD_obs = float(obs["eff"][STEPS // 2:].mean())

order = np.argsort(-z_obs)
say("\n   les 5 meilleures têtes (avant toute correction) :")
for i in order[:5]:
    say(f"     {sp.HEAD_IDS[i]:<16} hits/tirage {OV[:, i].mean():.5f}   z = {z_obs[i]:+.2f}")
say("   les 3 pires :")
for i in order[-3:]:
    say(f"     {sp.HEAD_IDS[i]:<16} hits/tirage {OV[:, i].mean():.5f}   z = {z_obs[i]:+.2f}")
say(f"\n   ensemble AdaHedge   hits/tirage {obs['ov_ens'].mean():.5f}   z = {zB_obs:+.2f}")
say(f"   têtes effectives (2ᵉ moitié) : {zD_obs:.2f} sur {sp.N_HEADS}")


# --------------------------------------------------------------------------
# 2. Transfert hors échantillon — la seule version exploitable
# --------------------------------------------------------------------------

def transfer(ov, folds=8):
    """Choisir la meilleure tête sur un pli, la payer sur le suivant.

    C'est la correction de la malédiction du vainqueur : `max_h z_h` est
    biaisé vers le haut par construction, un z hors échantillon ne l'est pas.
    """
    n = len(ov)
    edges = np.linspace(0, n, folds + 1).astype(int)
    out = []
    for f in range(folds - 1):
        a = ov[edges[f]:edges[f + 1]]
        b = ov[edges[f + 1]:edges[f + 2]]
        win = int(np.argmax(a.sum(axis=0)))
        out.append((b[:, win].sum() - len(b) * sp.OV_MEAN)
                   / (sp.OV_SD * np.sqrt(len(b))))
    return float(np.mean(out))


zC_obs = transfer(OV)
say(f"   transfert (8 plis, gagnante d'un pli payée sur le suivant) : z = {zC_obs:+.2f}")


# --------------------------------------------------------------------------
# 3. Null conditionnel (martingale) — exact sur les marges, immédiat
# --------------------------------------------------------------------------

rule("2. NULL CONDITIONNEL — prédictions observées, tirages rebattus")
say("   Sous H0, recouvrement | prédiction ~ hypergéométrique(80,20,20), quelle")
say("   que soit la prédiction. On garde donc les 26 prédictions OBSERVÉES à")
say("   chaque pas et on retire le tirage : les marges sont exactes et la")
say("   corrélation entre têtes est celle réellement observée.")

PICKS = obs["picks"]                      # (steps, 26, 20) int8
PICKS_ENS = obs["picks_ens"]
rng = np.random.default_rng(7)
REPS_C = 600
maxes = np.empty(REPS_C)
enss = np.empty(REPS_C)
CHUNK = 8000
t0 = time.time()
for r in range(REPS_C):
    tot = np.zeros(sp.N_HEADS, np.int64)
    tot_e = 0
    for s in range(0, STEPS, CHUNK):
        e = min(STEPS, s + CHUNK)
        m = lab.srs(e - s, rng)
        idx = np.arange(e - s)[:, None, None]
        tot += m[idx, PICKS[s:e]].sum(axis=(0, 2))
        tot_e += int(m[np.arange(e - s)[:, None], PICKS_ENS[s:e]].sum())
    zs = (tot - STEPS * sp.OV_MEAN) / (sp.OV_SD * np.sqrt(STEPS))
    maxes[r] = zs.max()
    enss[r] = (tot_e - STEPS * sp.OV_MEAN) / (sp.OV_SD * np.sqrt(STEPS))
    if (r + 1) % 100 == 0:
        say(f"   {r + 1}/{REPS_C}  ({time.time() - t0:.0f}s)")

null_A_cond = lab.Null(float(maxes.mean()), float(maxes.std(ddof=1)), REPS_C, maxes)
null_B_cond = lab.Null(float(enss.mean()), float(enss.std(ddof=1)), REPS_C, enss)
say(f"\n   max_h z_h : observé {zA_obs:+.3f}   null {null_A_cond.mean:+.3f} ± {null_A_cond.sd:.3f}"
    f"   z = {null_A_cond.z(zA_obs):+.2f}   p = {null_A_cond.p_two_sided(zA_obs):.4f}")
say(f"   ensemble  : observé {zB_obs:+.3f}   null {null_B_cond.mean:+.3f} ± {null_B_cond.sd:.3f}"
    f"   z = {null_B_cond.z(zB_obs):+.2f}   p = {null_B_cond.p_two_sided(zB_obs):.4f}")


# --------------------------------------------------------------------------
# 4. Null complet — l'essaim entier rejoué sur des archives synthétiques
# --------------------------------------------------------------------------

rule("3. NULL COMPLET — l'essaim entier rejoué sur archives SRS")
say("   Le null conditionnel fige les prédictions ; le null complet ne fige")
say("   rien : têtes, poids, prédictions, tout est re-généré. C'est le seul")
say("   qui capture la boucle état→prédiction→état. Coûteux, donc peu de")
say("   réplicats — on retient le PLUS CONSERVATEUR des deux écarts-types.")

REPS_F = 12
rngf = np.random.default_rng(101)
fa, fb, fc, fd = [], [], [], []
for r in range(REPS_F):
    t0 = time.time()
    syn = lab.srs(T_all, rngf)
    rr = sp.run(syn, keep_picks=False)
    ovr = rr["ov"].astype(np.int64)
    fa.append(float(z_heads(ovr).max()))
    fb.append(sp.z_of(rr["ov_ens"].astype(np.int64)))
    fc.append(transfer(ovr))
    fd.append(float(rr["eff"][rr["steps"] // 2:].mean()))
    say(f"   rep {r + 1}/{REPS_F}  max {fa[-1]:+.2f}  ens {fb[-1]:+.2f}"
        f"  transf {fc[-1]:+.2f}  eff {fd[-1]:.2f}   ({time.time() - t0:.0f}s)")

fa, fb, fc, fd = map(np.array, (fa, fb, fc, fd))
null_A = lab.Null(float(fa.mean()), float(fa.std(ddof=1)), REPS_F, fa)
null_B = lab.Null(float(fb.mean()), float(fb.std(ddof=1)), REPS_F, fb)
null_C = lab.Null(float(fc.mean()), float(fc.std(ddof=1)), REPS_F, fc)
null_D = lab.Null(float(fd.mean()), float(fd.std(ddof=1)), REPS_F, fd)

# On garde, pour A et B, le null dont l'écart-type est le plus grand.
if null_A.sd > null_A_cond.sd:
    say("\n   -> A : le null complet est plus large que le conditionnel, on le garde")
    useA = null_A
else:
    say("\n   -> A : le null conditionnel est plus large, on le garde (conservateur)")
    useA = lab.Null(null_A.mean, null_A_cond.sd, null_A_cond.reps, null_A_cond.samples
                    + (null_A.mean - null_A_cond.mean))
useB = null_B if null_B.sd > null_B_cond.sd else lab.Null(
    null_B.mean, null_B_cond.sd, null_B_cond.reps,
    null_B_cond.samples + (null_B.mean - null_B_cond.mean))

rule("4. VERDICTS")
for nom, tok, obsv, nul in (("F3-A  meilleure des 26 têtes", TOK_A, zA_obs, useA),
                            ("F3-B  ensemble AdaHedge", TOK_B, zB_obs, useB),
                            ("F3-C  transfert hors échantillon", TOK_C, zC_obs, null_C),
                            ("F3-D  têtes effectives", TOK_D, zD_obs, null_D)):
    say(f"   {nom:<34} observé {obsv:+8.3f}   null {nul.mean:+7.3f} ± {nul.sd:.3f}"
        f"   z = {nul.z(obsv):+6.2f}   p = {nul.p_two_sided(obsv):.4f}")


# --------------------------------------------------------------------------
# 5. Sensibilité — quelle avance l'essaim verrait-il ?
# --------------------------------------------------------------------------

rule("5. SENSIBILITÉ — quelle avance l'essaim détecterait-il ?")
say("   Contamination : avec probabilité ε, un numéro du tirage précédent est")
say("   réinjecté dans le tirage courant. C'est du momentum pur — exactement")
say("   ce que les têtes EWMA/Hawkes/Markov sont faites pour voir.")
say("   Mesuré sur T = 20 000 (le coût interdit l'archive entière), puis")
say("   converti en avance de hits par tirage.")

T_POW = 20_000


def contaminate(m, rng, eps):
    m = m.copy()
    for t in range(1, len(m)):
        if rng.random() >= eps:
            continue
        prev = np.flatnonzero(m[t - 1] & ~m[t])
        cur = np.flatnonzero(m[t] & ~m[t - 1])
        if len(prev) == 0 or len(cur) == 0:
            continue
        m[t, rng.choice(prev)] = True
        m[t, rng.choice(cur)] = False
    return m


rngp = np.random.default_rng(303)
say(f"\n   null de max_h z_h à T = {T_POW} (6 réplicats) :")
base = []
for r in range(6):
    rr = sp.run(lab.srs(T_POW, rngp), keep_picks=False)
    base.append(float(z_heads(rr["ov"].astype(np.int64)).max()))
    say(f"     rep {r + 1}/6  {base[-1]:+.2f}")
base = np.array(base)
seuil = base.mean() + 3 * base.std(ddof=1)
say(f"   null {base.mean():+.2f} ± {base.std(ddof=1):.2f}  ->  seuil à 3σ : {seuil:+.2f}")

say("\n   ε      avance réelle    max_h z_h      détecté (3σ)")
for eps in (0.02, 0.05, 0.10, 0.20):
    vals, gains = [], []
    for r in range(4):
        m = contaminate(lab.srs(T_POW, rngp), rngp, eps)
        lag1 = float((m[1:] & m[:-1]).sum(axis=1).mean())
        gains.append(lag1 - 5.0)
        rr = sp.run(m, keep_picks=False)
        vals.append(float(z_heads(rr["ov"].astype(np.int64)).max()))
    vals = np.array(vals)
    say(f"   {eps:<6.2f} +{np.mean(gains):.4f} hits    {vals.mean():+7.2f}"
        f"        {int((vals >= seuil).sum())}/4")


# --------------------------------------------------------------------------
# 6. Registre
# --------------------------------------------------------------------------

pw = f"contamination momentum, cf. section 5 (T={T_POW})"
lab.record(TOK_A, zA_obs, useA, power_at=pw,
           verdict="", notes=f"meilleure tête = {sp.HEAD_IDS[int(np.argmax(z_obs))]}")
lab.record(TOK_B, zB_obs, useB, power_at=pw, verdict="", notes="ensemble AdaHedge de l'app")
lab.record(TOK_C, zC_obs, null_C, power_at=pw, verdict="",
           notes="8 plis, gagnante en échantillon payée hors échantillon")
lab.record(TOK_D, zD_obs, null_D, power_at=pw, verdict="",
           notes=f"exp(H(w)) moyenne, seconde moitié, sur {sp.N_HEADS} têtes")

rule(f"consigné au registre — total {time.time() - T0:.0f}s")
