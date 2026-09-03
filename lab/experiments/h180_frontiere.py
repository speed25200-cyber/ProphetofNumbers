"""h180 — LA FRONTIÈRE DU DOSSIER : quelles familles de générateurs mes instruments
attrapent, et lesquelles leur sont invisibles (RAPPORT §199).

DONNÉES SYNTHÉTIQUES UNIQUEMENT. Ce fichier ne teste aucune hypothèse sur l'archive : il
mesure la PORTÉE des instruments. Rien à pré-enregistrer, rien à consigner au registre.

LA QUESTION QUE PERSONNE NE POSE APRÈS UN RÉSULTAT NÉGATIF
==========================================================
Ce dossier a mesuré, testé, borné — et n'a rien trouvé. Un lecteur a le droit de demander :

    « L'archive est-elle propre, ou tes instruments sont-ils aveugles ? »

La réponse honnête n'est pas un serment, c'est une **carte**. On plante un panel de
générateurs couvrant les grandes familles, du plus faible au cryptographique, on passe
chacun dans les instruments du dossier, et on regarde qui est pris et qui passe.

Le §192 a déjà nommé un trou — le `xorshift32`, `F₂`-linéaire à un seul pas, que les
détecteurs d'énergie ne peuvent pas voir. Ce fichier le généralise : **où exactement
s'arrête ce dossier ?**

LE PANEL
========
  1  SRS                — le hasard parfait, contrôle
  2  Fibonacci (3,7)    — additif à deux termes, retards courts        [famille classique]
  3  Fibonacci (2,3,7)  — additif à trois termes
  4  LCG 32 bits        — congruentiel linéaire, `glibc` historique
  5  xorshift32         — `F₂`-linéaire, UN SEUL PAS                   [trou connu]
  6  splitmix64         — compteur + mélange fort (Java SplittableRandom)
  7  PCG32              — LCG 64 bits + permutation de sortie
  8  xoshiro128**       — `F₂`-linéaire 128 bits + multiplication de sortie
  9  os.urandom         — cryptographique

LES INSTRUMENTS
===============
  A  énergie additive à deux termes, tous couples `g₁ ≥ g₂ ≥ 1` jusqu'à 4   (§177-§179)
  B  autocorrélation exacte, numéro par numéro, tous décalages ≤ 2 000      (§186)
  C  prédicteur appris à 31 traits, marche avant, tranches disjointes       (§192)
  D  flux mince du bonus, énergie sur les blocs de quatre                   (§197)

CE QU'IL FAUT LIRE DANS LE RÉSULTAT
===================================
Si les familles classiques sont prises et les modernes invisibles, alors le dossier prouve
exactement ceci : **l'archive n'est engendrée par aucun générateur de la première classe**,
et elle est indiscernable de tout générateur de la seconde. Ce n'est pas un échec, c'est
une frontière — et une frontière nommée vaut mieux qu'une conclusion vague.
"""

import json
import os
import sys
from math import sqrt

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import h173_predicteur_appris as P                                      # noqa: E402
import h176_borne_elargie as E                                          # noqa: E402
import h178_flux_mince as F                                             # noqa: E402

POOL, DRAWN = 80, 20
M64 = (1 << 64) - 1
M32 = (1 << 32) - 1
N = 30000
FJOURNAL = "/tmp/h180_journal.json"


def say(*a):
    print(*a, flush=True)


# --------------------------------------------------------------------------------------
# Le panel. Chaque generateur rend une suite de mots de 32 bits.
# --------------------------------------------------------------------------------------

def g_fib(graine, retards):
    import random
    r0 = random.Random(graine)
    L = max(retards)
    r = [r0.randrange(1 << 32) for _ in range(L + 1)]
    i = len(r)
    while True:
        v = 0
        for d in retards:
            v += r[i - d]
        r.append(v & M32)
        i += 1
        if i > 4096:                              # fenetre glissante : la memoire
            del r[:2048]                          # ne doit pas croitre sans fin
            i -= 2048
        yield r[i - 1]


def g_lcg32(graine):
    x = graine & M32
    while True:
        x = (1103515245 * x + 12345) & M32
        yield x


def g_xorshift32(graine):
    x = graine | 1
    while True:
        x ^= (x << 13) & M32
        x ^= x >> 17
        x ^= (x << 5) & M32
        yield x


def g_splitmix64(graine):
    s = graine & M64
    while True:
        s = (s + 0x9E3779B97F4A7C15) & M64
        z = s
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & M64
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & M64
        z = z ^ (z >> 31)
        yield (z >> 32) & M32


def g_pcg32(graine, inc=1442695040888963407):
    s = (graine + inc) & M64
    s = (s * 6364136223846793005 + inc) & M64
    while True:
        old = s
        s = (s * 6364136223846793005 + inc) & M64
        xs = (((old >> 18) ^ old) >> 27) & M32
        rot = (old >> 59) & 31
        yield ((xs >> rot) | (xs << ((-rot) & 31))) & M32


def g_xoshiro128ss(graine):
    import random
    r0 = random.Random(graine)
    s = [r0.randrange(1, 1 << 32) for _ in range(4)]

    def rotl(x, k):
        return ((x << k) | (x >> (32 - k))) & M32

    while True:
        out = (rotl((s[1] * 5) & M32, 7) * 9) & M32
        t = (s[1] << 9) & M32
        s[2] ^= s[0]
        s[3] ^= s[1]
        s[1] ^= s[2]
        s[0] ^= s[3]
        s[2] ^= t
        s[3] = rotl(s[3], 11)
        yield out


def g_urandom(_graine):
    while True:
        b = os.urandom(4096)
        for k in range(0, 4096, 4):
            yield int.from_bytes(b[k:k + 4], "little")


def echantillonne(gen, n):
    """rejet jusqu'a vingt classes distinctes, PUIS un mot pour le rang du bonus."""
    m = np.zeros((n, POOL), bool)
    rang = np.empty(n, np.int64)
    for j in range(n):
        vus = set()
        while len(vus) < DRAWN:
            vus.add((next(gen) * POOL) >> 32)
        m[j, list(vus)] = True
        rang[j] = ((next(gen) * POOL) >> 32) >> 2
    return m, rang


PANEL = [
    ("1 SRS (controle)", None),
    ("2 Fibonacci (3,7)", lambda g: g_fib(g, (3, 7))),
    ("3 Fibonacci (2,3,7)", lambda g: g_fib(g, (2, 3, 7))),
    ("4 LCG 32 bits", g_lcg32),
    ("5 xorshift32", g_xorshift32),
    ("6 splitmix64", g_splitmix64),
    ("7 PCG32", g_pcg32),
    ("8 xoshiro128**", g_xoshiro128ss),
    ("9 os.urandom (crypto)", g_urandom),
]


# --------------------------------------------------------------------------------------
# Les instruments
# --------------------------------------------------------------------------------------

COUPLES_A = [(a, b) for a in range(1, 5) for b in range(1, a + 1)]
MU_A = 200.0      # §184 : E[T2] = 100|S| par tirage, exactement, ici |S| = 2
# §197 : E[T] = |B|^k |S| / 20 par tirage, exactement — |B| = 4, |S| = 4, k le nombre de
# termes. Donc 0,8|S| = 3,2 pour les couples et 4^3|S|/20 = 12,8 pour les TRIPLETS. La
# premiere version de ce fichier appliquait 3,2 aux quarante et une statistiques : la
# moyenne mesuree valait 7,8874, soit exactement (21*3,2 + 20*12,8)/41 = 7,8829, et tous
# les generateurs — SRS compris — sortaient a z = 70. Une nulle fausse ne se voit pas sur
# le classement, elle se voit sur le CONTROLE.
MU_D = np.r_[np.full(len(F.COUPLES), 0.8 * len(F.SLACK)),
             np.full(len(F.TRIPLETS), 4.0 ** 3 * len(F.SLACK) / 20.0)]


def stats_A(m):
    """energie additive a deux termes PAR TIRAGE, dix couples g1 >= g2 >= 1."""
    return np.array([_e2(m, a, b) for a, b in COUPLES_A]) / len(m)


def _e2(m, g1, g2):
    n = len(m)
    lo = max(g1, g2)
    B = m.astype(np.float64)
    Fr = np.fft.rfft(B, axis=1)
    Cc = np.fft.irfft(Fr[lo - g1:n - g1] * Fr[lo - g2:n - g2], n=POOL, axis=1)
    s = 0.0
    for d in (0, 1):
        s += float((np.roll(Cc, d, axis=1) * B[lo:]).sum())
    return s


def instrument_B(m, dmax=2000):
    """autocorrelation exacte, numero par numero (§7.29)."""
    n = len(m)
    nfft = 1 << int(np.ceil(np.log2(2 * n)))
    cnt = np.arange(n - 1, n - dmax - 1, -1).astype(np.float64)
    zmax = 0.0
    for v in range(POOL):
        x = m[:, v].astype(np.float64) - 0.25
        Fr = np.fft.rfft(x, n=nfft)
        Cc = np.fft.irfft(Fr * np.conjugate(Fr), n=nfft)[1:dmax + 1]
        zmax = max(zmax, float(np.abs(Cc / ((3.0 / 16.0) * np.sqrt(cnt))).max()))
    return zmax


def instrument_C(m):
    """predicteur appris a 31 traits, marche avant, tranches disjointes."""
    n = len(m)
    BOR = np.array([0, n])
    coupe = P.CHAUFFE + int((n - P.CHAUFFE) * P.PART)
    X = E.construire(m, BOR, None)
    w, mu, sd = P.ajuster(X[P.CHAUFFE:coupe].reshape(-1, E.NF),
                          m[P.CHAUFFE:coupe].reshape(-1))
    S = P.scorer(X, w, mu, sd)
    del X
    rec, _ = P.mesurer(m, S, coupe, n)
    return (rec.mean() - 5.0) / (P.SD1 / sqrt(len(rec)))


def stats_D(rang):
    """flux mince du bonus : energie sur les blocs de quatre, PAR TIRAGE (§197)."""
    return F.toutes_energies(rang) / len(rang)


REPS_NUL = 30
SEUIL_B = 5.11       # exact : Bonferroni sur les 80 x 2000 cases a nulle EXACTE du §7.29
SEUIL_C = 3.00       # une seule statistique


def _max_loo(V, mu):
    """loi du max de |z| sous la nulle, chaque replicat laisse de cote dans sa propre
    estimation d'ecart-type. Un Bonferroni gaussien sur un maximum de statistiques
    CORRELEES est faux — la premiere version de ce fichier classait ainsi un CSPRNG
    comme detecte (D = 4,26 pour un seuil de 3,24). C'est la quatrieme fois dans ce
    dossier ; la parade est toujours la meme (§7.32)."""
    R = len(V)
    s1 = V.sum(axis=0)
    s2 = (V * V).sum(axis=0)
    mx = np.empty(R)
    for r in range(R):
        m_ = (s1 - V[r]) / (R - 1)
        v_ = np.maximum((s2 - V[r] * V[r]) / (R - 1) - m_ * m_, 1e-18)
        mx[r] = np.abs((V[r] - mu) / np.sqrt(v_)).max()
    return mx


def nulle(rng):
    """ecarts-types PAR STATISTIQUE et loi du MAXIMUM, sous SRS. Les moyennes, elles,
    sont EXACTES (§184, §197) : les estimer ajouterait un bruit inutile."""
    A, D = [], []
    for k in range(REPS_NUL):
        m = P.srs(N, rng)
        A.append(stats_A(m))
        D.append(stats_D(rng.integers(0, DRAWN, N)))
        if (k + 1) % 10 == 0:
            say(f"      nulle {k+1}/{REPS_NUL}")
    A = np.array(A)
    D = np.array(D)
    say(f"      moyenne A mesuree {A.mean():.4f} (exacte {MU_A})  ;  "
        f"moyenne D mesuree {D.mean():.4f} (exacte {MU_D.mean():.4f})")
    sA = _max_loo(A, MU_A)
    sD = _max_loo(D, MU_D)
    say(f"      loi du max sous la nulle : A mediane {np.median(sA):.2f}, "
        f"95e centile {np.quantile(sA, 0.95):.2f}  ;  D mediane {np.median(sD):.2f}, "
        f"95e centile {np.quantile(sD, 0.95):.2f}")
    return (A.std(axis=0), D.std(axis=0),
            float(np.quantile(sA, 0.95)), float(np.quantile(sD, 0.95)))


if __name__ == "__main__":
    J = json.load(open(FJOURNAL, encoding="utf-8")) if os.path.exists(FJOURNAL) else {}
    say("h180 : LA FRONTIERE — donnees synthetiques uniquement, aucune archive lue")
    say(f"   {N} tirages par generateur ; les instruments sont ceux du dossier")

    rng = np.random.default_rng(180)
    if "_sd" in J:
        sdA, sdD = np.array(J["_sd"][0]), np.array(J["_sd"][1])
        seuilA, seuilD = J["_sd"][2], J["_sd"][3]
    else:
        say(f"   nulle : {REPS_NUL} replicats SRS, moyennes EXACTES, ecarts-types et loi "
            "du maximum simules")
        sdA, sdD, seuilA, seuilD = nulle(rng)
        J["_sd"] = [sdA.tolist(), sdD.tolist(), seuilA, seuilD]
        json.dump(J, open(FJOURNAL, "w", encoding="utf-8"))

    say(f"\n   {'generateur':>22} | {'A energie':>9} | {'B autoc.':>8} | {'C appris':>8} "
        f"| {'D flux mince':>12}")
    for nom, fab in PANEL:
        if nom in J:
            r = J[nom]
        else:
            if fab is None:
                m = P.srs(N, rng)
                rang = rng.integers(0, DRAWN, N)
            else:
                m, rang = echantillonne(fab(20260903), N)
            r = {"A": float(np.abs((stats_A(m) - MU_A) / sdA).max()),
                 "B": instrument_B(m),
                 "C": float(instrument_C(m)),
                 "D": float(np.abs((stats_D(rang) - MU_D) / sdD).max())}
            J[nom] = r
            json.dump(J, open(FJOURNAL, "w", encoding="utf-8"))
            del m, rang
        say(f"   {nom:>22} | {r['A']:9.2f} | {r['B']:8.2f} | {r['C']:+8.2f} "
            f"| {r['D']:12.2f}")

    say("\n   Les quatre colonnes sont des |z|. A et D : ecart a la moyenne EXACTE, "
        "divise par")
    say("   l'ecart-type simule. B : z exact du §7.29. C : z du recouvrement hors "
        "echantillon.")
    say(f"\n   seuils, un par instrument, chacun a son propre 95e centile sous la nulle :")
    say(f"      A > {seuilA:.2f} (loi du max simulee)  |  B > {SEUIL_B:.2f} (Bonferroni "
        f"sur une nulle EXACTE)")
    say(f"      C > {SEUIL_C:.2f} (une seule statistique)  |  D > {seuilD:.2f} (loi du "
        f"max simulee)")
    pris, invisibles = [], []
    for nom, fab in PANEL:
        if nom not in J:
            continue
        r = J[nom]
        vu = (r["A"] > seuilA or r["B"] > SEUIL_B
              or abs(r["C"]) > SEUIL_C or r["D"] > seuilD)
        if fab is None:
            say(f"\n   CONTROLE SRS : {'DETECTE — LA CALIBRATION EST FAUSSE' if vu else 'invisible, comme il se doit'}")
            continue
        (pris if vu else invisibles).append(nom)
    say(f"\n   PRIS        : {', '.join(pris) if pris else '(aucun)'}")
    say(f"   INVISIBLES  : {', '.join(invisibles) if invisibles else '(aucun)'}")
    say("\n   C'est la frontiere du dossier. Ce qu'il prouve : l'archive n'est engendree "
        "par")
    say("   aucun generateur de la premiere liste. Ce qu'il ne prouve pas : elle est "
        "indiscernable")
    say("   de tout generateur de la seconde — y compris d'un vrai hasard.")
