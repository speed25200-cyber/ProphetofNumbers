"""h205 — LE CANAL DE POIDS FAIBLE : une faille testable sans supposer ni graine ni
constantes (RAPPORT §226).

CE QUE CE FICHIER FAIT DE DIFFÉRENT
===================================
Les §223 à §225 attaquent l'**état** : ils supposent une famille de générateurs, des
constantes, un pas, et cherchent `x₀`. Quand ils rendent zéro, ils ne ferment que la
conjonction qu'ils ont supposée.

Celui-ci ne suppose **rien**. Il teste une conséquence structurelle qui se lit directement
sur les numéros triés de l'archive.

LE RAISONNEMENT, EN TROIS LIGNES
================================
1. Deux des dix échantillonneurs du dossier — le **modulo** `c = w mod 80` (§211, règle 1
   et 2) et les **sept bits bas** `c = w ∧ 127` (règle 5) — donnent une classe qui ne dépend
   que des **bits de poids faible** de `w`.
2. Pour **tout** LCG `mod 2^W`, les bits de poids faible forment un **sous-système clos** :
   `w mod 16` suit un LCG `mod 16`, de période au plus `16`. C'est le §7.36 lu à l'envers —
   ce qui protège le générateur quand la sortie lit le haut le trahit quand elle lit le bas.
3. Donc les `~23` mots consommés par tirage ont des résidus `mod 16` qui parcourent un
   **cycle de période 16** : chaque résidu sort une ou deux fois, jamais zéro, jamais trois.

CE QUE ÇA PRÉDIT, ET C'EST ÉNORME
=================================
Chaque classe de résidus `mod 16` contient `5` numéros sur `80`. Sous SRS, le nombre de
numéros tirés dans une classe suit une hypergéométrique :

| compte | `0` | `1` | `2` | `3` | `4` | `5` |
|---|---|---|---|---|---|---|
| SRS | `0,227184` | `0,405686` | `0,270457` | `0,083935` | `0,012092` | `0,000645` |
| LCG + modulo | **`≈ 0`** | grand | grand | **`≈ 0`** | `≈ 0` | `≈ 0` |

`P(compte = 0)` passe de `0,227` à zéro, et `P(compte ≥ 3)` de `0,096` à zéro. Sur
`70 560 × 16 = 1 128 960` observations, l'écart serait colossal — et **aucune hypothèse sur
la graine, le multiplicateur ou l'incrément n'est nécessaire pour le voir**.

L'EXCLUSION IMMÉDIATE DES SEPT BITS BAS
=======================================
Pour l'échantillonneur `c = w ∧ 127` avec rejet de `c ≥ 80`, la classe **est** les sept bits
bas. Sous un LCG `mod 2^W` ceux-ci suivent un cycle de période au plus `128`, donc l'état du
canal ne prend que `128` valeurs, donc **il n'existe au plus que `128` tirages distincts
possibles**. L'archive en contient `70 560` dont aucun ne se répète. La conjonction est
morte sans le moindre calcul, et ce fichier le vérifie.

TROIS FAMILLES
==============
  **A  LA LOI DES COMPTES.** Pour `k = 1 … 4`, la distribution du nombre de numéros tirés
     par classe de résidus `mod 2^k`, contre l'hypergéométrique **exacte**.
  **B  LES DEUX CELLULES QU'UN LCG VIDERAIT.** `P(compte = 0)` et `P(compte ≥ 3)` à
     `mod 16`, mesurées séparément parce que ce sont elles qui portent la signature.
  **C  LE COMPTE DE TIRAGES DISTINCTS**, qui exclut les sept bits bas sans calcul.

Les comptes d'une même classe étant liés — leur somme vaut `20` — la loi du maximum est
calibrée sur répliques SRS (§7.32).
"""

import json
import os
import sys
from fractions import Fraction as F

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POOL, DRAWN = 80, 20
EXP_ID = "h205.canal_poids_faible"
FJETON = "/tmp/h205_jeton.json"
REPS = 200
KS = (1, 2, 3, 4)                      # mod 2, 4, 8, 16 — tous diviseurs de 80


def say(*a):
    print(*a, flush=True)


def binom(n, r):
    v = F(1)
    for i in range(r):
        v *= F(n - i, i + 1)
    return v


def loi_exacte(taille):
    """P(h numeros tires parmi les `taille` d'une classe), hypergeometrique EXACTE."""
    return [float(binom(taille, h) * binom(POOL - taille, DRAWN - h) / binom(POOL, DRAWN))
            for h in range(min(taille, DRAWN) + 1)]


def comptes(M, k):
    """pour chaque tirage et chaque classe mod 2^k, le nombre de numeros tires."""
    m = 1 << k
    cls = np.arange(POOL) % m
    out = np.zeros((len(M), m), np.int64)
    for r in range(m):
        out[:, r] = M[:, cls == r].sum(axis=1)
    return out


def profil(M):
    """vecteur de statistiques : khi2 par k, plus les deux cellules de mod 16."""
    v = []
    for k in KS:
        m = 1 << k
        taille = POOL // m
        p = loi_exacte(taille)
        c = comptes(M, k)
        hist = np.bincount(c.ravel(), minlength=len(p)).astype(np.float64)
        att = np.array(p) * c.size
        v.append(float((((hist - att) ** 2) / np.maximum(att, 1e-9)).sum()))
    c16 = comptes(M, 4)
    v.append(float((c16 == 0).mean()))
    v.append(float((c16 >= 3).mean()))
    return np.array(v)


if __name__ == "__main__":
    import lab

    A = lab.load()
    M = np.asarray(A.mask)
    N = len(M)
    NOMS = tuple(f"khi2 mod {1<<k}" for k in KS) + ("P(compte=0) mod 16",
                                                   "P(compte>=3) mod 16")
    p16 = loi_exacte(5)
    MTOT = len(NOMS) + 1

    HYP = ("Les numeros de l'archive ne portent aucune signature de canal de poids faible. "
           "Les §223 a §225 attaquent l'ETAT et supposent donc une famille, des constantes "
           "et un pas ; celui-ci ne suppose RIEN et teste une consequence structurelle qui "
           "se lit sur les numeros tries. Deux des dix echantillonneurs du dossier — le "
           "modulo c = w mod 80 et les sept bits bas c = w et 127 — donnent une classe qui "
           "ne depend que des bits de POIDS FAIBLE de w. Or pour TOUT LCG mod 2^W ces bits "
           "forment un sous-systeme CLOS : w mod 16 suit un LCG mod 16, de periode au plus "
           "16. C'est le §7.36 lu a l'envers — ce qui protege le generateur quand la sortie "
           "lit le haut le trahit quand elle lit le bas. Les ~23 mots consommes par tirage "
           "ont donc des residus mod 16 parcourant un cycle de periode 16 : chaque residu "
           "sort une ou deux fois, jamais zero, jamais trois. Chaque classe mod 16 contenant "
           "5 numeros sur 80, la loi SRS du compte est hypergeometrique de P(0) = 0,227184 "
           "et P(>=3) = 0,096139, tandis qu'un LCG les ecraserait toutes deux a zero — sur "
           f"{N} x 16 = {N*16} observations l'ecart serait colossal, et AUCUNE hypothese sur "
           "la graine, le multiplicateur ou l'increment n'est necessaire pour le voir. "
           "Enfin, pour les sept bits bas la classe EST le canal clos, donc l'etat ne prend "
           "que 128 valeurs et il n'existe au plus que 128 tirages distincts possibles : "
           f"l'archive en contient {N} sans repetition, ce qui tue la conjonction sans le "
           "moindre calcul")
    STAT = (f"khi2 de la loi des comptes par classe de residus mod 2^k pour k = 1 a 4, plus "
            f"P(compte = 0) et P(compte >= 3) a mod 16, reduits par la loi EMPIRIQUE du "
            f"maximum sur {REPS} repliques SRS chacune laissee hors de sa propre "
            f"normalisation ; plus le nombre de tirages distincts")
    NUL = ("EXACTE : sous SRS le nombre de numeros tires dans une classe de taille `taille` "
           "suit une hypergeometrique C(taille,h) C(80-taille,20-h) / C(80,20). A mod 16 "
           "(classes de 5) : P(0) = 0,227184, P(1) = 0,405686, P(2) = 0,270457, "
           "P(3) = 0,083935, P(4) = 0,012092, P(5) = 0,000645. Les comptes d'un meme tirage "
           "etant lies par leur somme egale a 20, la loi du MAXIMUM est calibree sur "
           "repliques (§7.32)")
    VER = ("conforme si le maximum reduit reste sous le 95e centile de sa loi empirique ; "
           "CANAL DE POIDS FAIBLE sinon, auquel cas l'echantillonneur lit le bas de l'etat "
           "et le generateur est un congruentiel, ce qui donne prise sans enumeration")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h205 : {N} tirages ; canaux mod 2, 4, 8, 16")
    say(f"   loi exacte a mod 16 (classes de 5 numeros) :")
    say("      " + "  ".join(f"P({h})={p16[h]:.6f}" for h in range(6)))

    # ---- C : l'exclusion immediate des sept bits bas
    vus = {(int(a), int(b)) for a, b in
           zip((M[:, :64] * (1 << np.arange(64, dtype=np.uint64))).sum(axis=1),
               (M[:, 64:] * (1 << np.arange(16, dtype=np.uint64))).sum(axis=1))}
    say(f"\nC  L'EXCLUSION SANS CALCUL")
    say(f"   tirages distincts dans l'archive : {len(vus)} sur {N}")
    say(f"   un LCG mod 2^W lu par ses sept bits bas n'en produirait qu'au plus 128")
    say(f"   -> conjonction {'EXCLUE' if len(vus) > 128 else 'NON exclue'} "
        f"(facteur {len(vus)/128:.0f})")

    obs = profil(M)
    c16 = comptes(M, 4)
    say(f"\nA/B  LA LOI DES COMPTES")
    hist = np.bincount(c16.ravel(), minlength=6) / c16.size
    say(f"   {'compte':>7} | {'observe':>10} | {'SRS exact':>10} | {'LCG+modulo':>11}")
    for h in range(6):
        say(f"   {h:7d} | {hist[h]:10.6f} | {p16[h]:10.6f} | "
            f"{'~0' if h in (0,3,4,5) else 'grand':>11}")

    V = np.empty((REPS, len(obs)))
    rng = np.random.default_rng(0x205)
    for r in range(REPS):
        V[r] = profil(lab.srs(N, rng))
        if (r + 1) % 50 == 0:
            say(f"   ... {r+1}/{REPS} repliques")

    s1, s2 = V.sum(axis=0), (V * V).sum(axis=0)
    mu, sd = V.mean(axis=0), V.std(axis=0)
    zr = (obs - mu) / np.maximum(sd, 1e-12)
    o = float(np.abs(zr).max())
    mx = np.empty(REPS)
    for r in range(REPS):
        m_ = (s1 - V[r]) / (REPS - 1)
        v_ = np.maximum((s2 - V[r] * V[r]) / (REPS - 1) - m_ * m_, 1e-12)
        mx[r] = float(np.abs((V[r] - m_) / np.sqrt(v_)).max())
    p = float((1 + int((mx >= o).sum())) / (1 + REPS))

    say(f"\n   {'statistique':>20} | {'archive':>13} | {'repliques':>22} | {'z reduit':>9}")
    for i, nom in enumerate(NOMS):
        say(f"   {nom:>20} | {obs[i]:13.5f} | {mu[i]:13.5f} +/-{sd[i]:8.5f} | {zr[i]:+9.3f}")
    say(f"   maximum reduit {o:.3f} ; 95e centile {np.percentile(mx, 95):.3f} ; "
        f"p = {p:.4f}")
    verdict = "CANAL DE POIDS FAIBLE" if p <= 0.05 else "conforme"
    say(f"   ->   {verdict}")

    TOK["m_extra"] = MTOT - 1
    lab.record(
        TOK, o, p=p, verdict=verdict,
        power_at=(f"la puissance est ecrasante contre le modele vise : un LCG lu par le bas "
                  f"ecrase P(compte=0) de 0,227184 a zero et P(compte>=3) de 0,096139 a "
                  f"zero, sur {N*16} observations dont l'ecart-type de la proportion vaut "
                  f"{np.sqrt(0.227184*0.772816/(N*16)):.6f} — soit un z de l'ordre de "
                  f"{0.227184/np.sqrt(0.227184*0.772816/(N*16)):.0f}. Le test ne peut pas "
                  f"manquer ce defaut s'il existe ; en revanche il ne dit rien d'un "
                  f"echantillonneur qui lit le HAUT de l'etat, ou d'un generateur non "
                  f"congruentiel"),
        notes=(f"LE CANAL DE POIDS FAIBLE (§226) — une faille testable SANS supposer ni "
               f"graine ni constantes, contrairement aux §223-§225 qui attaquent l'etat. "
               f"Deux des dix echantillonneurs donnent une classe ne dependant que des bits "
               f"bas de w, or pour tout LCG mod 2^W ces bits forment un sous-systeme CLOS de "
               f"periode <= 16 : le §7.36 lu a l'envers. Loi exacte des comptes par classe "
               f"mod 2^k, k = 1 a 4, plus les deux cellules qu'un LCG viderait. Archive : "
               f"P(compte=0) = {obs[4]:.6f} contre {p16[0]:.6f} attendu, P(compte>=3) = "
               f"{obs[5]:.6f} contre {sum(p16[3:]):.6f}. Maximum reduit {o:.3f} contre un "
               f"95e centile de {np.percentile(mx,95):.3f}, p = {p:.4f}. Et l'exclusion sans "
               f"calcul des sept bits bas : {len(vus)} tirages distincts dans l'archive "
               f"contre au plus 128 possibles sous ce modele."))
    say("   consigne.")
