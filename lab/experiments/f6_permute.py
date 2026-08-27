"""f6 — réel, permuté, simulé : le triangle qui isole la cause.

D'où vient cette expérience
---------------------------
f3 a mesuré une chose que personne n'avait regardée : les « têtes effectives »
exp(H(w)) de l'essaim, ce chiffre que l'app affiche sur la carte L'ESSAIM.
Sur l'archive réelle il vaut ~6,8 sur 26. Le premier réplicat sous H0 en a
donné ~10,0. Si l'écart tient sur les 12 réplicats, c'est un écart RÉEL entre
l'archive et un générateur parfait — et il faut savoir d'où il vient avant
d'en dire quoi que ce soit.

Le triangle
-----------
Trois façons de produire une séquence de 70 560 tirages :

  RÉEL      l'archive telle quelle
  PERMUTÉ   les MÊMES tirages, dans un ordre rebattu au hasard
  SIMULÉ    des tirages SRS uniformes, indépendants

La permutation détruit toute structure TEMPORELLE tout en préservant
EXACTEMENT le multi-ensemble des tirages : mêmes fréquences marginales,
mêmes co-occurrences, même tout ce qui ne dépend pas de l'ordre. Le triangle
sépare donc les deux causes possibles, ce qu'aucun null seul ne peut faire :

  réel ≠ permuté  ->  il y a de la structure TEMPORELLE
  permuté ≠ simulé ->  la LOI des tirages s'écarte de l'uniforme
  les trois égaux  ->  il n'y a rien, et l'écart de f3 était du bruit

Ce que l'on mesure sur les trois
--------------------------------
  * têtes effectives exp(H(w)) — la statistique en cause ;
  * max_h z_h — la meilleure des 26 têtes ;
  * la dispersion des hits totaux entre têtes, en hits — la cause mécanique
    de la concentration : AdaHedge concentre quand les pertes cumulées
    s'écartent, et elles s'écartent quand les têtes se ressemblent moins ;
  * le recouvrement moyen entre deux top-20 de têtes différentes — la mesure
    directe de « les têtes se ressemblent-elles ? ».
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


TOK = lab.preregister(
    "f6.eff",
    "la concentration des poids AdaHedge sur l'archive reelle s'ecarte de H0, "
    "et l'ordre temporel en est la cause",
    "tetes effectives exp(H(w)) moyennes sur la seconde moitie",
    "triangle reel / permute (memes tirages, ordre rebattu) / SRS simule",
    "significatif seulement si p franchit le seuil Holm du registre entier",
    track="C")

TOK_D = lab.preregister(
    "f6.disp",
    "la dispersion des performances entre tetes s'ecarte de H0",
    "ecart-type entre les 26 totaux de hits, en hits",
    "triangle reel / permute / SRS simule",
    "significatif seulement si p franchit le seuil Holm du registre entier",
    track="C")


def measure(mask, want_picks=False):
    r = sp.run(mask, keep_picks=want_picks)
    ov = r["ov"].astype(np.int64)
    tot = ov.sum(axis=0)
    T = len(ov)
    out = {
        "eff": float(r["eff"][T // 2:].mean()),
        "maxz": float(((tot - T * sp.OV_MEAN) / (sp.OV_SD * np.sqrt(T))).max()),
        "disp": float(tot.std(ddof=1)),
        "ens": sp.z_of(r["ov_ens"].astype(np.int64)),
    }
    if want_picks:
        # recouvrement moyen entre deux top-20 de tetes differentes, sur un
        # echantillon de pas — mesure directe de la ressemblance des tetes.
        p = r["picks"]
        step = max(1, len(p) // 400)
        acc, cnt = 0.0, 0
        for t in range(0, len(p), step):
            m = np.zeros((sp.N_HEADS, sp.POOL), bool)
            m[np.arange(sp.N_HEADS)[:, None], p[t]] = True
            o = m.astype(np.float32) @ m.astype(np.float32).T
            iu = np.triu_indices(sp.N_HEADS, 1)
            acc += float(o[iu].mean())
            cnt += 1
        out["sim"] = acc / cnt
    return out


rule("1. LES TROIS SÉQUENCES")

arch = lab.load()
mask = arch.mask
T = len(mask)
say(f"   {T} tirages")

t0 = time.time()
reel = measure(mask, want_picks=True)
say(f"\n   RÉEL      têtes eff {reel['eff']:6.2f}   max_h z {reel['maxz']:+6.2f}"
    f"   dispersion {reel['disp']:7.1f} hits   ressemblance {reel['sim']:.3f}/20"
    f"   ({time.time() - t0:.0f}s)")

REPS = 8
rng = np.random.default_rng(77)
perm, simu = [], []
for r in range(REPS):
    t0 = time.time()
    p = measure(mask[rng.permutation(T)], want_picks=(r == 0))
    perm.append(p)
    extra = f"   ressemblance {p['sim']:.3f}/20" if "sim" in p else ""
    say(f"   PERMUTÉ {r + 1} têtes eff {p['eff']:6.2f}   max_h z {p['maxz']:+6.2f}"
        f"   dispersion {p['disp']:7.1f} hits{extra}   ({time.time() - t0:.0f}s)")
for r in range(REPS):
    t0 = time.time()
    s = measure(lab.srs(T, rng), want_picks=(r == 0))
    simu.append(s)
    extra = f"   ressemblance {s['sim']:.3f}/20" if "sim" in s else ""
    say(f"   SIMULÉ  {r + 1} têtes eff {s['eff']:6.2f}   max_h z {s['maxz']:+6.2f}"
        f"   dispersion {s['disp']:7.1f} hits{extra}   ({time.time() - t0:.0f}s)")


def arr(rows, key):
    return np.array([x[key] for x in rows])


rule("2. LE TRIANGLE")
say("   statistique              RÉEL      PERMUTÉ (8)         SIMULÉ (8)")
for key, lbl, fmt in (("eff", "têtes effectives", "{:6.2f}"),
                      ("maxz", "max_h z_h", "{:+6.2f}"),
                      ("disp", "dispersion (hits)", "{:6.1f}"),
                      ("ens", "z de l'ensemble", "{:+6.2f}")):
    a, b = arr(perm, key), arr(simu, key)
    say(f"   {lbl:<22} " + fmt.format(reel[key]) +
        f"   " + fmt.format(a.mean()) + f" ± {a.std(ddof=1):.2f}" +
        f"   " + fmt.format(b.mean()) + f" ± {b.std(ddof=1):.2f}")

for key, tok, lbl in (("eff", TOK, "têtes effectives"), ("disp", TOK_D, "dispersion")):
    a, b = arr(perm, key), arr(simu, key)
    nP = lab.Null(float(a.mean()), float(a.std(ddof=1)), REPS, a)
    nS = lab.Null(float(b.mean()), float(b.std(ddof=1)), REPS, b)
    say(f"\n   {lbl} :")
    say(f"     réel contre PERMUTÉ  z = {nP.z(reel[key]):+6.2f}   p = {nP.p_two_sided(reel[key]):.4f}"
        f"   -> structure temporelle ?")
    say(f"     réel contre SIMULÉ   z = {nS.z(reel[key]):+6.2f}   p = {nS.p_two_sided(reel[key]):.4f}")
    dz = (a.mean() - b.mean()) / np.sqrt(a.var(ddof=1) / REPS + b.var(ddof=1) / REPS)
    say(f"     PERMUTÉ contre SIMULÉ  t = {dz:+6.2f}   -> la loi des tirages"
        f" s'écarte-t-elle de l'uniforme ?")
    lab.record(tok, reel[key], nP, power_at="triangle, cf. section 2", verdict="",
               notes=f"null = permutations de l'archive ; contre SRS : "
                     f"z = {nS.z(reel[key]):+.2f} ; permute vs SRS : t = {dz:+.2f}")

rule(f"consigné au registre — total {time.time() - T0:.0f}s")
