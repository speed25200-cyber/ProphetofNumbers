"""h168c — le triplet `(3,1,1)` est-il un effet de FRONTIÈRE DE NUIT ?
(RAPPORT §183 addendum 2).

CE QU'ON TESTE
==============
Le §183 rend `z = +3,267` au triplet `(3,1,1)` et le §183 addendum montre qu'il se
RÉPLIQUE : `+3,145` sur la première moitié de l'archive, `+2,196` sur la seconde, mêmes
signes, très près des `+2,31` qu'un effet réel donnerait de chaque côté.

Avant d'y voir une trace de générateur, il faut écarter l'explication banale. La
statistique `T3(3,1,1)` fait intervenir quatre tirages : `t-3`, `t-1`, `t-1` et `t`. Quand
`t` est au début d'une nuit, ces quatre tirages ne sont PAS dans la même nuit — ils
enjambent une coupure. L'archive a `370` nuits et deux longueurs de nuit (`180` puis `204`
tirages) ; si les nuits ne sont pas parfaitement échangeables entre elles, les quadruplets
à cheval sur une coupure suffisent à créer un petit excès.

C'est testable en une ligne : recalculer la MÊME statistique en ne gardant que les
quadruplets **entièrement contenus dans une nuit**.

    si l'excès disparaît   -> c'était la frontière, et il n'y a rien
    s'il persiste          -> ce n'est pas la frontière, et il faut chercher ailleurs

Le triplet et le seuil sont fixés par les sections précédentes. Rien n'est choisi ici après
avoir regardé.
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import h164_energie_signee as S                                        # noqa: E402

POOL, DRAWN = 80, 20
EXP_ID = "h168c.triplet_intranuit"
FJETON = "/tmp/h168c_jeton.json"
REPS = 24
CIBLE = (3, 1, 1)
DELTAS = (0, 1, 2)


def say(*a):
    print(*a, flush=True)


def par_tirage(m, g):
    """T3 pour chaque t valide, ET les indices t correspondants."""
    n = len(m)
    lo, hi = min(0, *g), max(0, *g)
    deb, fin = max(0, hi), n + min(0, lo)
    F = [np.fft.rfft(m[deb - x: fin - x].astype(np.float64), axis=1) for x in g]
    conv = np.rint(np.fft.irfft(F[0] * F[1] * F[2], n=POOL, axis=1)).astype(np.int64)
    C = m[deb:fin]
    s = np.zeros(len(C), np.int64)
    for d in DELTAS:
        w = (np.arange(POOL) - d) % POOL
        s += (conv[:, w] * C).sum(axis=1)
    return s, np.arange(deb, fin)


if __name__ == "__main__":
    import lab

    HYP = (f"L'exces du triplet {CIBLE} (§183 : z = +3,267 ; replique a +3,145 et +2,196 sur "
           "les deux moities) vient des quadruplets a cheval sur une FRONTIERE DE NUIT. Si "
           "c'est le cas, il disparait quand on ne garde que les quadruplets entierement "
           "contenus dans une nuit ; sinon il persiste")
    STAT = ("z_intra = ecart normalise du triplet (3,1,1) calcule sur les seuls tirages t "
            "dont les quatre tirages t-3, t-1, t-1, t appartiennent a la meme nuit "
            "(370 nuits, coupures aux discontinuites de 300 s)")
    NUL = (f"Simulation : {REPS} replicats SRS de meme taille que le sous-ensemble intra-nuit, "
           "moyenne et variance PAR TIRAGE ; ecart-type de la moyenne = sd/sqrt(n_intra)")
    VER = ("frontiere si |z_intra| < 2 (l'exces disparait) ; PERSISTE si |z_intra| > 2 avec "
           "le meme signe positif")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    A = lab.load()
    M = np.asarray(A.mask)
    TS = np.asarray(A.ts).astype(np.int64)
    DEB = np.r_[0, np.flatnonzero(np.diff(TS) != 300) + 1]
    nuit = np.zeros(len(M), np.int64)
    nuit[DEB] = 1
    nuit = np.cumsum(nuit) - 1
    t3, idx = par_tirage(M, CIBLE)
    garde = (nuit[idx] == nuit[idx - 3])          # t et t-3 dans la meme nuit
    n_in = int(garde.sum())
    obs = float(t3[garde].mean())
    say(f"h168c : {len(DEB)} nuits ; {n_in} quadruplets intra-nuit sur {len(idx)} "
        f"({100*n_in/len(idx):.1f} %)")
    say(f"   observe intra-nuit : {obs:.4f}   (toute l'archive : {t3.mean():.4f})")

    rng = np.random.default_rng(20260910)
    s1 = s2 = 0.0
    cpt = 0
    for k in range(REPS):
        m = S.srs(n_in + 4, rng)
        t, _ = par_tirage(m, CIBLE)
        t = t.astype(np.float64)
        s1 += t.sum(); s2 += (t * t).sum(); cpt += len(t)
        if (k + 1) % 8 == 0:
            say(f"   nulle {k+1}/{REPS}")
    mu = s1 / cpt
    sd = np.sqrt(max(s2 / cpt - mu * mu, 0) / n_in)
    z = (obs - mu) / sd
    from math import erfc, sqrt
    p = float(erfc(abs(z) / sqrt(2)))
    say(f"\n   nulle {mu:.4f} +- {sd:.4f}   ->   z_intra = {z:+.3f}   p = {p:.4f}")
    persiste = abs(z) > 2 and z > 0
    say(f"   {'PERSISTE' if persiste else 'DISPARAIT'} — "
        f"{'ce n est pas la frontiere de nuit' if persiste else 'c etait la frontiere de nuit'}")
    TOK["m_extra"] = 0
    lab.record(
        TOK, float(abs(z)), p=p,
        verdict="PERSISTE" if persiste else "frontiere de nuit",
        power_at=(f"le sous-ensemble intra-nuit porte {n_in} quadruplets, soit "
                  f"{100*n_in/len(idx):.1f} % du total : un effet reel de z = +3,267 sur "
                  f"l'archive entiere y donnerait z = {3.267*np.sqrt(n_in/len(idx)):.2f}"),
        notes=(f"CHASSE 2 AU TRIPLET {CIBLE} : intra-nuit z = {z:+.3f} sur {n_in} "
               f"quadruplets, contre +3,267 sur les {len(idx)} de l'archive entiere. "
               "Le triplet etait fixe par le §183 et le decoupage par nuit est celui du "
               "§172 — rien n'est choisi apres avoir regarde."))
    say("   consigne.")
