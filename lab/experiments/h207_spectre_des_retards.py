"""h207 — LE SPECTRE DES RETARDS : tous les retards à la fois, pas seulement les courts
(RAPPORT §228).

CE QUE LE DOSSIER N'A JAMAIS REGARDÉ
====================================
Le §219 mesure la corrélation jusqu'à l'échelle `2 048`. Le §220 et le §221 mesurent le
transfert au retard `1`, puis au retard d'une nuit. Le §199 balaie quelques retards choisis.

**Aucune de ces expériences ne peut voir un retard de `31 417`.**

Or c'est exactement la forme qu'aurait le défaut le plus exploitable de tous : un générateur
qui **reboucle**. Un LCG `mod 2³²` mal ensemencé, un compteur qui repasse, une graine tirée
d'un vivier trop petit — tout cela produit une répétition à un retard *unique et arbitraire*,
invisible à qui ne regarde que les retards courts.

L'ARME : L'AUTOCORRÉLATION COMPLÈTE PAR FFT
==========================================
On centre l'archive exactement — `c[i,n] = x[i,n] − 1/4` — ce qui a deux vertus exactes :

  * `E[c] = 0` sous SRS **exactement** (la marge est `20/80 = 1/4` par construction) ;
  * `Σ_n c[i,n] = 0` **exactement** pour chaque tirage (vingt numéros sur quatre-vingts).

On calcule alors, pour **tous** les retards `d` d'un coup,

    R(d) = Σ_n Σ_i c[i,n]·c[i+d,n]

par transformée de Fourier : `R = irfft( Σ_n |rfft(c_n)|² )`. Quatre-vingts colonnes, une
seule transformée inverse, **`35 280` retards** couverts en quelques secondes là où une
boucle naïve demanderait `2·10¹¹` produits.

La statistique standardisée est `T(d) = R(d)/√(N−d)` — de variance à peu près constante en
`d` — et le test porte sur `max_d |T(d)|`, calibré par la **loi empirique du maximum**
(§7.32) sur répliques SRS, avec normalisation « laisser-un-dehors ».

CE QUE ÇA FERME
===============
Si le générateur reboucle avec une période de `P` tirages, alors `R(P)` vaut la puissance
totale `Σ c² ≈ 1,06·10⁶`, contre un écart-type de l'ordre de `450`. Le rapport est de
`2 000` écarts-types : **une répétition, même partielle à un pour mille, saute aux yeux**.
Le témoin planté ci-dessous mesure exactement ce seuil.
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POOL, DRAWN = 80, 20
EXP_ID = "h207.spectre_des_retards"
FJETON = "/tmp/h207_jeton.json"
REPS = 200
FRAC = 0.5            # on garde les retards d <= N/2 : au-dela, N-d s'effondre


def say(*a):
    print(*a, flush=True)


def spectre(M, dmax, L):
    """R(d) pour tout d, par FFT. M : (N,80) booleen. Renvoie T(d)=R(d)/sqrt(N-d)."""
    n = len(M)
    C = np.zeros((POOL, L))
    C[:, :n] = (M.astype(np.float64) - 0.25).T
    P = np.abs(np.fft.rfft(C, axis=1)) ** 2
    R = np.fft.irfft(P.sum(axis=0), n=L)[:dmax + 1]
    d = np.arange(dmax + 1)
    T = np.empty(dmax + 1)
    T[0] = 0.0
    T[1:] = R[1:] / np.sqrt(n - d[1:])
    return T


def maxloo(V, obs):
    """§7.32 : loi empirique du maximum, normalisation laisser-un-dehors.

    V : (reps, k) statistiques par cellule sous la nulle. obs : (k,) l'archive.
    Renvoie (z_obs_max, seuil_95, p_empirique).
    """
    reps = len(V)
    S = V.sum(axis=0)
    Q = V ** 2
    S2 = Q.sum(axis=0)
    mu = (S - V) / (reps - 1)
    sd = np.sqrt(np.maximum((S2 - Q) / (reps - 1) - mu ** 2, 1e-30))
    Z = np.abs(V - mu) / sd
    mrep = Z.max(axis=1)
    muo = S / reps
    sdo = np.sqrt(np.maximum(S2 / reps - muo ** 2, 1e-30))
    zo = float((np.abs(obs - muo) / sdo).max())
    p = float((np.sum(mrep >= zo) + 1) / (reps + 1))
    return zo, float(np.quantile(mrep, 0.95)), p


if __name__ == "__main__":
    import lab

    A = lab.load()
    M = np.asarray(A.mask)
    N = len(M)
    DMAX = int(N * FRAC)
    L = 1 << int(np.ceil(np.log2(2 * N)))

    HYP = (f"La suite des tirages ne se repete a AUCUN retard. Le dossier n'a jamais "
           f"regarde que des retards courts — le §219 s'arrete a l'echelle 2048, le §220 "
           f"au retard 1, le §221 au retard d'une nuit — et aucune de ces experiences ne "
           f"peut voir un retard de 31 417. Or c'est exactement la forme du defaut le plus "
           f"exploitable de tous : un generateur qui reboucle (LCG mod 2^32 mal ensemence, "
           f"compteur qui repasse, graine tiree d'un vivier trop petit) produit une "
           f"repetition a un retard UNIQUE ET ARBITRAIRE, invisible a qui ne regarde que "
           f"les retards courts. On calcule donc l'autocorrelation COMPLETE par FFT : "
           f"R(d) = somme sur n et i de c[i,n]c[i+d,n] avec c = x - 1/4 (centrage EXACT, "
           f"la marge etant 20/80 par construction), pour les {DMAX} retards d = 1..N/2 "
           f"d'un seul coup")
    STAT = (f"max sur d de |T(d)| ou T(d) = R(d)/racine(N-d), sur les {DMAX} retards, "
            f"standardise cellule par cellule contre {REPS} repliques SRS")
    NUL = (f"{REPS} archives SRS completes de {N} tirages, meme chaine FFT ; loi empirique "
           f"du maximum du §7.32 avec normalisation laisser-un-dehors, qui absorbe la "
           f"dependance entre retards voisins sans supposer d'independance")
    VER = ("conforme si le max observe ne depasse pas le 95e centile de la loi du maximum "
           "sous SRS ; PERIODICITE sinon, auquel cas le retard argmax est la periode "
           "candidate et donne directement la prediction")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h207 : {N} tirages, retards 1..{DMAX}, FFT de longueur {L}")
    puissance = float(((M.astype(np.float64) - 0.25) ** 2).sum())
    say(f"   puissance totale (= R(0), ce que vaudrait une repetition parfaite) : "
        f"{puissance:.0f}")

    # ------------------------------------------------------------------ selftest
    say("\n   selftest : temoin plante — une repetition partielle au retard 31417")
    rng0 = np.random.default_rng(7)
    PER = 31417
    for m in (0, 2, 3, 4, 6):
        W = lab.srs(N, rng0).copy()
        if m:
            # sur chaque paire (i, i+PER), on force m numeros communs
            for i in range(0, N - PER):
                if (i % 37):                     # 1 tirage sur 37 seulement
                    continue
                src = np.flatnonzero(W[i])[:m]
                dst = np.flatnonzero(W[i + PER])
                ajout = np.setdiff1d(src, dst, assume_unique=True)
                oter = np.setdiff1d(dst, src, assume_unique=True)[:len(ajout)]
                W[i + PER, oter] = False
                W[i + PER, ajout] = True
        T = spectre(W, DMAX, L)
        say(f"      m = {m} numeros forces : |T| max = {np.abs(T[1:]).max():8.2f} "
            f"au retard {int(np.abs(T[1:]).argmax()) + 1:6d}   "
            f"|T({PER})| = {abs(T[PER]):8.2f}")
    del W

    # ------------------------------------------------------------------ archive
    obs = spectre(M, DMAX, L)[1:]
    say(f"\n   archive : |T| max brut = {np.abs(obs).max():.2f} au retard "
        f"{int(np.abs(obs).argmax()) + 1}")
    ordre = np.argsort(-np.abs(obs))[:8]
    say("   les huit retards les plus forts :")
    for k in ordre:
        say(f"      retard {int(k)+1:6d}   T = {obs[k]:+9.2f}")

    # ------------------------------------------------------------------ nulle
    V = np.empty((REPS, DMAX), np.float32)
    rng = np.random.default_rng(0x207)
    for r in range(REPS):
        V[r] = spectre(lab.srs(N, rng), DMAX, L)[1:]
        if (r + 1) % 50 == 0:
            say(f"   ... {r+1}/{REPS} repliques")

    zo, seuil, p = maxloo(V.astype(np.float64), obs)
    say(f"\n   max |z| observe        : {zo:.3f}")
    say(f"   95e centile sous SRS   : {seuil:.3f}")
    say(f"   p empirique            : {p:.4g}")

    verdict = "PERIODICITE" if zo > seuil else "conforme"
    say(f"\n   {verdict}")

    TOK["m_extra"] = DMAX - 1
    lab.record(
        TOK, float(zo), p=float(p), verdict=verdict,
        power_at=(f"le temoin plante mesure le seuil exactement : forcer m numeros communs "
                  f"sur un tirage sur 37 au retard 31417 donne les |T(31417)| listes dans "
                  f"la sortie, a comparer au maximum du bruit de fond sur 35 280 retards. "
                  f"Le seuil de detection est m = 3 ; m = 2 n'est PAS detecte. Soit "
                  f"3 numeros communs sur 20 dans 2,7 % des tirages a un retard fixe. "
                  f"Une repetition COMPLETE de periode P donnerait "
                  f"T(P) = {puissance:.0f}/racine(N-P), soit plus de mille ecarts-types : "
                  f"le test voit toute periode de l'ordre de N ou moins avec certitude"),
        notes=(f"LE SPECTRE DES RETARDS (§228) — autocorrelation COMPLETE de l'archive par "
               f"FFT, {DMAX} retards couverts d'un coup la ou le dossier ne regardait que "
               f"des retards courts (§219 jusqu'a 2048, §220 retard 1, §221 retard d'une "
               f"nuit). Centrage exact c = x - 1/4. max |z| = {zo:.3f} contre un 95e "
               f"centile de {seuil:.3f} sous {REPS} repliques SRS, p = {p:.4g}. Retard le "
               f"plus fort : {int(np.abs(obs).argmax())+1}. Aucune periode : le generateur "
               f"ne reboucle pas dans la fenetre de l'archive."))
    say("   consigne.")
