"""h178 — LE FLUX MINCE DU BONUS : l'observable le plus net de l'archive, jamais traité
comme un flux (RAPPORT §197, théorie THEORIE_ETAT §7.34).

L'IDÉE, ET POURQUOI ELLE EST NEUVE
==================================
Tout le dossier lit les **vingt numéros**. Or vingt numéros parmi quatre-vingts, c'est
`61,62` bits répartis sur **environ vingt-trois mots** — moins de `2,7` bits par mot, et
répartis sur un ENSEMBLE dont on ignore quel mot a produit quel élément.

Le bonus est d'une tout autre nature. Le §175 établit que `bonus = triés[⌊20u⌋]`, donc le
rang `b` du bonus parmi les vingt vaut `b = ⌊20u/2³²⌋`. Et sous la même troncature, la
classe de ce mot vaut `c = ⌊80u/2³²⌋`. Les deux lectures sont liées **exactement** :

        b = ⌊c/4⌋        c'est-à-dire        c ∈ {4b, 4b+1, 4b+2, 4b+3} .

> **Le rang du bonus contraint la classe d'UN MOT PRÉCIS à quatre valeurs sur
> quatre-vingts.** C'est `4,32` bits sur un mot identifié, contre `2,7` bits dilués par mot
> pour les numéros — et surtout, on sait DE QUEL MOT il s'agit.

L'archive contient donc une suite de `70 560` mots **fortement contraints**, espacés
d'environ `24,85` mots dans le flux. C'est un flux mince, régulier, et bien plus net que
celui des numéros. Aucune section ne l'a détecté comme tel : le §175 l'a utilisé dans le
crible de classes, le §187 a vérifié que son rang est uniforme, le §189 l'a croisé avec les
autres champs. Personne ne lui a appliqué les détecteurs exacts.

TROIS FAMILLES
==============
  A  AUTOCORRÉLATION EXACTE du rang, rang par rang et décalage par décalage. Nulle exacte
     par le théorème du §7.29 transposé : avec `p = 1/20`, `Var(x) = 19/400` et

         Var(C_j(d)) = n_d · (19/400)²        exactement.

     Vingt rangs × `35 279` décalages = `705 580` cases.

  B  ÉNERGIE ADDITIVE sur les blocs de quatre. Si un mot vaut `r_i = r_{i-K} + r_{i-L}`,
     sa classe vaut `c_i = c_{i-K} + c_{i-L} + δ` avec `δ` petit. Sur le flux mince, les
     trois classes sont connues **à quatre valeurs près chacune**, donc

         T2(g1,g2) = Σ_t Σ_{δ∈S} #{ (u,v) ∈ B_{t-g1} × B_{t-g2} : u+v+δ ∈ B_t }

     avec `S = {0,1,2,3}` pour absorber la retenue de troncature. Vingt et un couples
     `1 ≤ g2 ≤ g1 ≤ 6`.

  C  ÉNERGIE À TROIS TERMES sur les mêmes blocs, vingt triplets `1 ≤ g3 ≤ g2 ≤ g1 ≤ 4`.

L'espérance de `T2` sous SRS se calcule **exactement** : à `u`, `v` et `δ` fixés la cible
`w = u+v+δ` est une classe déterminée, et les vingt blocs partitionnent `Z/80`, donc
`P(w ∈ B_t) = 1/20` quel que soit `w`. D'où

        E[T2] = 4 · 4 · |S| · (1/20) = 0,8 · |S|        par tirage, exactement.

La variance vient d'une **permutation** de la suite des rangs, qui est la nulle exacte de
l'échangeabilité et conserve la loi marginale du rang.

LE TÉMOIN
=========
Un générateur planté doit produire un vrai bonus : vingt classes par rejet, PUIS un mot de
plus dont le rang est `⌊c/4⌋`. Si le détecteur ne le voit pas là, il ne prouve rien ici.

Trois témoins, et l'un d'eux m'a contredit. J'avais prévu qu'un additif de retards courts
`(3, 7)` serait **hors portée** du flux mince — portée `0,12` et `0,28`, aucun couple
entier pour le lire. Il rend `+0,53` par tirage. La récurrence se **chaîne** : sur les
vingt-cinq pas qui séparent deux mots du bonus, un mot est une combinaison linéaire de
nombreux mots du bonus précédent, et la trace survit. La famille couvre donc plus large que
sa dérivation ne le laissait croire — mesuré, pas supposé.
"""

import json
import os
import sys
from math import erfc, sqrt

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POOL, DRAWN = 80, 20
M32 = 1 << 32
EXP_ID = "h178.flux_mince"
FJETON = "/tmp/h178_jeton.json"
REPS = 200
SLACK = (0, 1, 2, 3)                     # retenue de troncature absorbee
COUPLES = tuple((g1, g2) for g1 in range(1, 7) for g2 in range(1, g1 + 1))
TRIPLETS = tuple((g1, g2, g3) for g1 in range(1, 5)
                 for g2 in range(1, g1 + 1) for g3 in range(1, g2 + 1))
SDX = 19.0 / 400.0                       # Var(1(b=j)) = (1/20)(19/20), exact


def say(*a):
    print(*a, flush=True)


def blocs(rang):
    """(N,80) : indicatrice des quatre classes compatibles avec le rang."""
    N = len(rang)
    B = np.zeros((N, POOL), np.float64)
    for k in range(4):
        B[np.arange(N), 4 * rang + k] = 1.0
    return B


def _energie(B, F, g):
    """T pour un couple ou un triplet de decalages. `F` est la rfft de `B`, calculee UNE
    fois : la recalculer par statistique coutait quarante et une transformees par
    permutation, soit l'essentiel du temps de la nulle."""
    N = len(B)
    lo = max(g)
    P = F[lo - g[0]:N - g[0]]
    for x in g[1:]:
        P = P * F[lo - x:N - x]
    C = np.fft.irfft(P, n=POOL, axis=1)
    # somme_d (C roule de d) . B  =  C . (somme_d B roule de -d), une seule contraction
    Bd = np.zeros_like(C)
    for d in SLACK:
        Bd += np.roll(B[lo:], -d, axis=1)
    return float((C * Bd).sum())


def toutes_energies(rang):
    B = blocs(rang)
    F = np.fft.rfft(B, axis=1)
    return np.array([_energie(B, F, c) for c in COUPLES]
                    + [_energie(B, F, t) for t in TRIPLETS])


def autocorr_exacte(rang, dmax):
    """z_j(d) pour les vingt rangs et tous les decalages, nulle EXACTE."""
    N = len(rang)
    nfft = 1 << int(np.ceil(np.log2(2 * N)))
    zmax, arg = -1.0, None
    cnt = np.arange(N - 1, N - dmax - 1, -1).astype(np.float64)
    for j in range(DRAWN):
        x = (rang == j).astype(np.float64) - 1.0 / DRAWN
        F = np.fft.rfft(x, n=nfft)
        C = np.fft.irfft(F * np.conjugate(F), n=nfft)[1:dmax + 1]
        z = C / (SDX * np.sqrt(cnt))
        k = int(np.argmax(np.abs(z)))
        if abs(z[k]) > zmax:
            zmax, arg = abs(z[k]), (j, k + 1, float(z[k]))
    return zmax, arg


def seuil(m, alpha=0.05):
    lo, hi = 0.0, 40.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if erfc(mid / sqrt(2)) > alpha / m:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# --------------------------------------------------------------------------------------
# Le temoin : un generateur qui produit VRAIMENT un bonus
# --------------------------------------------------------------------------------------

def plante(n, graine, K, L, signe=1):
    """vingt classes par rejet, PUIS un mot de plus dont le rang vaut floor(c/4)."""
    import random
    r0 = random.Random(graine)
    r = [r0.randrange(M32) for _ in range(max(80, L + 1))]
    i = len(r)
    rang = np.empty(n, np.int64)

    def suivant():
        nonlocal i
        r.append((r[i - K] + signe * r[i - L]) % M32)
        i += 1
        return (r[i - 1] * POOL) >> 32

    for j in range(n):
        vus = set()
        while len(vus) < DRAWN:
            vus.add(suivant())
        rang[j] = suivant() >> 2               # floor(c/4), le mot du bonus
    return rang


def selftest():
    say("h178 --autotest : donnees synthetiques uniquement, aucune archive lue")
    rng = np.random.default_rng(178)
    n = 40000
    lib = rng.integers(0, DRAWN, n)
    zA, argA = autocorr_exacte(lib, 400)
    say(f"   rang libre : autocorrelation max |z| = {zA:.2f} sur {DRAWN*400} cases "
        f"(max attendu du bruit pur {seuil(DRAWN*400, 0.5):.2f})")
    ok1 = zA < 5.5

    # copie plantee : le rang copie celui d'il y a trois tirages une fois sur dix
    cop = lib.copy()
    for t in range(3, n):
        if rng.random() < 0.10:
            cop[t] = cop[t - 3]
    zB, argB = autocorr_exacte(cop, 400)
    say(f"   rang copie a 10 % au decalage 3 : max |z| = {zB:.1f} au rang {argB[0]}, "
        f"decalage {argB[1]}")
    ok2 = zB > 20 and argB[1] == 3

    # energie : la nulle exacte, puis un temoin A LA BONNE PORTEE
    e0 = toutes_energies(lib) / n
    att = 0.8 * len(SLACK)
    say(f"   energie par tirage, rang libre : {e0[:len(COUPLES)].mean():.4f}   "
        f"(attendu EXACT {att:.4f})")
    ok3 = abs(e0[:len(COUPLES)].mean() - att) < 0.02

    # J'AVAIS PREVU QUE LES RETARDS COURTS SERAIENT HORS PORTEE, ET LA MESURE ME CONTREDIT.
    # Les mots du bonus sont espaces de E[N]+2 = 24,85 mots, donc un additif de retards
    # (3, 7) a une portee de 0,12 et 0,28 sur ce flux : aucun couple entier ne devrait le
    # lire. Il rend pourtant +0,53. La raison est que la recurrence se CHAINE — sur
    # vingt-cinq pas, un mot du bonus est une combinaison lineaire de nombreux mots du
    # bonus precedent, et la trace survit. La famille est donc plus large que sa
    # derivation ne le laissait croire, et le temoin le prouve au lieu de le supposer.
    say(f"   {'temoin':>26} | {'portee flux mince':>18} | {'ecart max/tirage':>17}")
    ok4 = True
    for nom, K, L in (("additif mots (3,7)", 3, 7),
                      ("additif mots (49,25)", 49, 25),
                      ("additif mots (25,50)", 25, 50)):
        d = toutes_energies(plante(n, 71, K, L)) / n - e0
        j = int(np.argmax(np.abs(d)))
        vu = abs(d[j]) > 0.30
        say(f"   {nom:>26} | {K/24.85:6.2f}, {L/24.85:6.2f}  | {d[j]:+8.4f} en "
            f"{(COUPLES + TRIPLETS)[j]}" + ("   VU" if vu else "   MANQUE"))
        ok4 &= vu
    say(f"   -> nulle exacte {'VERIFIEE' if ok3 else 'FAUSSE'} ; "
        f"autocorrelation {'JUSTE' if ok1 else 'FAUSSE'} ; "
        f"copie {'DETECTEE' if ok2 else 'MANQUEE'} ; "
        f"energie {'CALIBREE' if ok4 else 'NON CALIBREE'}")
    return ok1 and ok2 and ok3 and ok4


if __name__ == "__main__":
    if "--autotest" in sys.argv:
        sys.exit(0 if selftest() else 1)

    import lab

    A = lab.load()
    N = len(A.ids)
    NUMS = np.asarray(A.nums).astype(np.int64)
    BONUS = np.asarray(A.bonus).astype(np.int64)
    RANG = np.argmax(NUMS == BONUS[:, None], axis=1)
    assert bool((NUMS[np.arange(N), RANG] == BONUS).all())
    DMAX = N // 2
    NA = DRAWN * DMAX
    NE = len(COUPLES) + len(TRIPLETS)
    MTOT = NA + NE
    ZC = seuil(MTOT)

    HYP = ("Le FLUX MINCE du bonus ne porte aucune trace. Sous la lecture "
           "bonus = tries[floor(20u)] du §175, le rang du bonus vaut floor(c/4) ou c est la "
           "classe d'un mot PRECIS du flux : chaque tirage contraint donc un mot identifie "
           "a quatre valeurs sur quatre-vingts, soit 4,32 bits sur un mot connu, contre 2,7 "
           "bits dilues par mot pour les numeros. L'archive porte 70 560 tels mots, espaces "
           "d'environ 24,85 mots. Aucune section ne l'avait detecte comme un flux. On y "
           "cherche : (A) une autocorrelation du rang, rang par rang et a tous les "
           "decalages, contre une nulle EXACTE ; (B) une energie additive a deux termes sur "
           "les blocs de quatre classes ; (C) la meme a trois termes")
    STAT = (f"D = nombre de cases depassant Zc = {ZC:.2f} (Bonferroni bilateral a 5 % sur "
            f"{MTOT}). Famille A : z_j(d) = C_j(d)/((19/400) racine(n_d)) avec "
            "C_j(d) = somme_t (1(b_t=j) - 1/20)(1(b_(t+d)=j) - 1/20), pour les vingt rangs "
            f"et les {DMAX} decalages. Familles B et C : z = (T - moyenne)/ecart-type sous "
            f"permutation, sur {len(COUPLES)} couples et {len(TRIPLETS)} triplets")
    NUL = ("Famille A : EXACTE, par le theoreme du §7.29 transpose a p = 1/20 — la "
           "covariance des termes partageant un tirage s'annule identiquement, donc "
           "Var(C_j(d)) = n_d (19/400)^2 sans une simulation. Familles B et C : esperance "
           "EXACTE de 0,8|S| par tirage (les vingt blocs partitionnent Z/80, donc la cible "
           f"tombe dans le bloc avec probabilite 1/20 quelle qu'elle soit) et variance par "
           f"{REPS} permutations de la suite des rangs")
    VER = f"conforme si D = 0 ; ECART sinon"

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h178 : {N} tirages ; {MTOT} statistiques ; seuil |z| > {ZC:.3f}")
    say(f"   flux mince : {N} mots contraints a 4 classes sur 80, espaces de ~24,85 mots")

    zA, argA = autocorr_exacte(RANG, DMAX)
    say(f"\n   A autocorrelation : {NA} cases, max |z| = {argA[2]:+.3f} "
        f"(rang {argA[0]}, decalage {argA[1]})")

    obs = toutes_energies(RANG)
    att = 0.8 * len(SLACK)
    say(f"   B/C energie : {NE} statistiques ; observe/tirage "
        f"{obs[:len(COUPLES)].mean()/N:.5f}, attendu exact {att:.5f}")
    # nulle par permutation, JOURNALISEE : le conteneur redemarre toutes les quinze a
    # vingt minutes et la nulle en demande quatorze. Sans reprise, elle ne finirait jamais.
    FNUL = "/tmp/h178_nulle.npy"
    V = np.load(FNUL) if os.path.exists(FNUL) else np.zeros((0, NE))
    if len(V):
        say(f"      nulle reprise a {len(V)}/{REPS}")
    rng = np.random.default_rng(20260903 + len(V))
    while len(V) < REPS:
        lot = [toutes_energies(RANG[rng.permutation(N)]) for _ in range(5)]
        V = np.vstack([V, np.array(lot)])
        np.save(FNUL, V)
        say(f"      nulle {len(V)}/{REPS}")
    V = V[:REPS]
    mu = V.mean(axis=0)
    sd = np.sqrt(np.maximum(V.var(axis=0), 1e-12))
    zE = (obs - mu) / sd
    jE = int(np.argmax(np.abs(zE)))
    nomE = (COUPLES + TRIPLETS)[jE]
    say(f"      max |z| = {zE[jE]:+.3f} en {nomE}")

    zmax = max(zA, abs(zE[jE]))
    D = int(zA > ZC) + int((np.abs(zE) > ZC).sum())
    p = float(min(1.0, erfc(zmax / sqrt(2)) * MTOT))
    say(f"\n   max |z| toutes familles = {zmax:.3f}   seuil {ZC:.3f}")
    say(f"   p (Bonferroni sur {MTOT}) = {p:.4f}   ->   {'ECART' if D else 'conforme'}")
    TOK["m_extra"] = MTOT - 1
    lab.record(
        TOK, float(zmax), p=p, verdict="ECART" if D else "conforme",
        power_at=("l'autotest plante une copie du rang d'il y a trois tirages un tirage sur "
                  "dix : la famille A la rend a plus de vingt ecarts-types et DESIGNE le bon "
                  "decalage. Sur les 70 560 mots du flux mince, un exces de repetition de "
                  f"1 % en valeur relative donnerait z = {0.01*0.05*np.sqrt(N)/SDX:.0f} au "
                  "decalage le plus peuple"),
        notes=(f"FLUX MINCE DU BONUS (§197) — l'observable le plus net de l'archive, jamais "
               f"traite comme un flux. Le rang vaut floor(c/4) : {N} mots identifies, "
               f"contraints a 4 classes sur 80 (4,32 bits), espaces de ~24,85 mots. "
               f"{MTOT} statistiques. A : max |z| = {argA[2]:+.3f} (rang {argA[0]}, "
               f"decalage {argA[1]}), nulle EXACTE par le §7.29 transpose a p = 1/20. "
               f"B/C : max |z| = {zE[jE]:+.3f} en {nomE}, esperance exacte 0,8|S| par "
               f"tirage verifiee ({obs[:len(COUPLES)].mean()/N:.5f} contre {att:.5f}). "
               f"D = {D}."))
    say("   consigne.")
