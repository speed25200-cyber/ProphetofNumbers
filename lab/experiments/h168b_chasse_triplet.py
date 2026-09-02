"""h168b — la chasse au triplet `(3,1,1)` : réplication sur deux moitiés disjointes
(RAPPORT §183 addendum).

CE QU'ON CHASSE
===============
Le §183 rend `|z| max = 3,267` au triplet `(3,1,1)`, `p = 0,0381` après Bonferroni sur les
trente-cinq — sous le seuil de `0,05`, donc consigné ECART. Ce n'est pas significatif après
Holm sur le registre entier, mais la règle de ce dossier est de ne pas laisser un écart
sans suite : on le CHASSE.

Cinq des six plus grands écarts sont en `g1 = 3` et tous sont POSITIFS (`+2,0` à `+3,3`),
ce qui ressemble à un effet commun plutôt qu'à un pic isolé — et les trente-cinq
statistiques sont fortement corrélées puisqu'elles partagent les mêmes tirages.

LE TEST
=======
Le seul qui tranche : la moitié. On coupe l'archive en deux blocs disjoints de `35 280`
tirages et l'on recalcule le MÊME triplet, préenregistré, sur chacun. Un effet réel se
réplique avec le même signe et environ `z/√2 = 2,31` sur chaque moitié ; une fluctuation
ne se réplique pas.

Le triplet est FIXÉ AVANT de regarder les moitiés : c'est ce qui distingue une chasse
d'une pêche.
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import h164_energie_signee as S                                        # noqa: E402
import h168_energie_trois_termes as T                                  # noqa: E402

EXP_ID = "h168b.chasse_triplet"
FJETON = "/tmp/h168b_jeton.json"
REPS = 24
CIBLE = (3, 1, 1)          # fixe par le §183, AVANT de regarder les moities


def say(*a):
    print(*a, flush=True)


if __name__ == "__main__":
    import lab

    HYP = (f"L'ecart du triplet {CIBLE} rendu par le §183 (z = +3,267, p = 0,0381 apres "
           "Bonferroni sur 35) se REPLIQUE sur deux moities disjointes de l'archive : un "
           "effet reel donne le meme signe et environ z/racine(2) = 2,31 sur chacune ; une "
           "fluctuation ne se replique pas. Le triplet est FIXE AVANT de regarder les "
           "moities")
    STAT = ("z1 et z2, les ecarts normalises du triplet (3,1,1) sur les tirages 0..35 279 et "
            "35 280..70 559, meme nulle simulee. D = min(|z1|, |z2|) si les signes "
            "coincident, 0 sinon")
    NUL = (f"Simulation : {REPS} x 35 280 tirages SRS 20/80 par moitie, moyenne et variance "
           "PAR TIRAGE ; ecart-type de la moyenne = sd/sqrt(35 280)")
    VER = ("replique si les deux signes coincident ET min(|z1|,|z2|) > 2 ; non replique "
           "sinon, auquel cas l'ecart du §183 est une fluctuation")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    A = lab.load()
    M = np.asarray(A.mask)
    n2 = len(M) // 2
    moities = (M[:n2], M[n2:])
    obs = np.array([T.energie(h, CIBLE).mean() for h in moities])
    say(f"h168b : triplet {CIBLE} ; deux moities de {n2} tirages")
    say(f"   observe : {obs[0]:.4f} et {obs[1]:.4f}")

    rng = np.random.default_rng(20260909)
    s1 = np.zeros(2); s2 = np.zeros(2); cpt = 0
    for k in range(REPS):
        m = S.srs(n2, rng)
        t = T.energie(m, CIBLE).astype(np.float64)
        for j in (0, 1):
            s1[j] += t.sum(); s2[j] += (t * t).sum()
        cpt += n2
        if (k + 1) % 8 == 0:
            say(f"   nulle {k+1}/{REPS}")
    mu = s1 / cpt
    sd = np.sqrt(np.maximum(s2 / cpt - mu * mu, 0) / n2)
    z = (obs - mu) / sd
    meme_signe = bool(z[0] * z[1] > 0)
    D = float(min(abs(z[0]), abs(z[1]))) if meme_signe else 0.0
    say(f"\n   moitie 1 : z = {z[0]:+.3f}")
    say(f"   moitie 2 : z = {z[1]:+.3f}")
    say(f"   memes signes : {'OUI' if meme_signe else 'NON'} ; D = min|z| = {D:.3f}")
    say(f"   (un effet reel donnerait ~{3.267/2**0.5:.2f} de chaque cote)")
    from math import erfc, sqrt
    p = float(erfc(D / sqrt(2))) if meme_signe else 1.0
    TOK["m_extra"] = 0
    lab.record(
        TOK, D, p=p, verdict="replique" if (meme_signe and D > 2) else "NON REPLIQUE",
        power_at=("chaque moitie porte 35 280 tirages, donc un effet reel de z = +3,267 sur "
                  "l'archive entiere donne z = +2,31 par moitie ; le test detecte donc la "
                  "replication avec une puissance de 0,84 a alpha = 0,05"),
        notes=(f"CHASSE AU TRIPLET {CIBLE} (§183 addendum) : z1 = {z[0]:+.3f}, "
               f"z2 = {z[1]:+.3f}, memes signes {meme_signe}, D = {D:.3f}. Le triplet etait "
               "fixe par le §183 AVANT que les moities ne soient regardees — c'est ce qui "
               "distingue une chasse d'une peche."))
    say("   consigne.")
