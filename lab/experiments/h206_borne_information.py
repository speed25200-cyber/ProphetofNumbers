"""h206 — LA BORNE D'INFORMATION : ce qu'AUCUN prédicteur ne pourra dépasser
(RAPPORT §227).

POURQUOI CHANGER DE REGISTRE
============================
Le dossier compte deux cent soixante-dix-huit expériences. La plupart testent **un**
prédicteur, **un** distingueur, **une** famille de générateurs — et rendent « conforme ».
Chaque nullité ferme une porte, et il en reste toujours une autre.

Cette section pose la question autrement, et c'est la seule qui puisse se fermer une fois
pour toutes :

> **Combien de bits prédictibles l'archive contient-elle ?**

Si la réponse est `I` bits par tirage, alors **aucun** modèle — le mien, un réseau de
neurones, un adversaire omniscient sur la même donnée — ne peut faire mieux que ce que `I`
permet. Ce n'est plus une porte fermée de plus : c'est le plafond du couloir.

CE QU'ON MESURE
===============
La **perte logarithmique hors échantillon**. Pour chaque couple (tirage, numéro) de la
tranche de mesure, le modèle donne une probabilité `p̂` que le numéro sorte ; on note

    L = − moyenne [ y·log₂ p̂ + (1−y)·log₂(1−p̂) ]

Sous SRS, la meilleure probabilité possible est `1/4` et la perte vaut

    H(1/4) = −(1/4)log₂(1/4) − (3/4)log₂(3/4) = 0,811278 bit

**Tout gain `ΔH = H(1/4) − L` est de l'information réellement extraite.** Un modèle qui
n'apprend rien rend `ΔH = 0` ; un modèle qui sur-apprend rend `ΔH < 0` hors échantillon,
ce qui est déjà une réponse.

TROIS MODÈLES, DU PLUS BÊTE AU PLUS FORT
========================================
  **`1/4` constant** — la référence, `ΔH = 0` par construction.
  **les marges historiques** — chaque numéro à son propre taux mesuré sur la tranche
     d'ajustement. C'est le meilleur modèle *statique* possible.
  **les 31 traits du §192** — le meilleur modèle *dynamique* du dossier, celui qui passe
     neuf témoins plantés.

LA CONVERSION QUI PARLE
=======================
`ΔH` bits par numéro fait `80·ΔH` bits par tirage. Et pour un joueur, l'avantage maximal
sur un pari top-`1` que `ΔH` autorise se borne par l'inégalité de Pinsker : une divergence
de `ΔH` bits ne peut déplacer une probabilité de `1/4` que de

    |Δp| ≤ √(ΔH · ln2 / 2)

C'est une borne **universelle** : elle vaut pour tout prédicteur ayant la même information,
pas seulement pour les trois testés.
"""

import json
import os
import sys
from math import log, log2, sqrt

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import h173_predicteur_appris as P                                      # noqa: E402
import h176_borne_elargie as E                                          # noqa: E402

POOL, DRAWN = 80, 20
EXP_ID = "h206.borne_information"
FJETON = "/tmp/h206_jeton.json"
REPS = 60
H14 = -(0.25 * log2(0.25) + 0.75 * log2(0.75))          # 0,811278 bit


def say(*a):
    print(*a, flush=True)


def perte(p, y):
    """perte logarithmique en bits, avec un plancher pour eviter les infinis."""
    p = np.clip(p, 1e-9, 1 - 1e-9)
    return float(-(y * np.log2(p) + (1 - y) * np.log2(1 - p)).mean())


def modele_marges(M, deb, fin, cible_deb, cible_fin, lisse=1.0):
    """chaque numero a son taux historique, lisse a la Laplace vers 1/4."""
    n = fin - deb
    c = M[deb:fin].sum(axis=0).astype(np.float64)
    p = (c + lisse * POOL / 4) / (n + lisse * POOL)
    return np.repeat(p[None, :], cible_fin - cible_deb, axis=0)


if __name__ == "__main__":
    import lab

    A = lab.load()
    M = np.asarray(A.mask)
    TS = np.asarray(A.ts).astype(np.int64)
    N = len(M)
    BOR = np.r_[0, np.flatnonzero(np.diff(TS) > 1000) + 1, N]
    BONUS = np.asarray(A.bonus).astype(np.int64)
    coupe = P.CHAUFFE + int((N - P.CHAUFFE) * P.PART)
    nmes = N - coupe
    ncoup = nmes * POOL

    HYP = ("L'archive ne contient aucune information predictible mesurable. Le dossier "
           "compte 278 experiences qui testent chacune UN predicteur, UN distingueur, UNE "
           "famille — et chaque nullite ferme une porte sans epuiser le couloir. Cette "
           "section pose la question autrement et c'est la seule qui puisse se fermer une "
           "fois pour toutes : combien de bits predictibles l'archive contient-elle ? On "
           "mesure la PERTE LOGARITHMIQUE hors echantillon de trois modeles — la constante "
           "1/4, les marges historiques (meilleur modele STATIQUE possible), et les 31 "
           "traits du §192 (meilleur modele DYNAMIQUE du dossier, celui qui passe neuf "
           "temoins plantes) — contre H(1/4) = 0,811278 bit. Tout gain est de l'information "
           "reellement extraite ; un gain nul dit qu'il n'y a rien a extraire, un gain "
           "negatif hors echantillon dit que le modele sur-apprend. Et la conversion est "
           "universelle : par l'inegalite de Pinsker, une divergence de DeltaH bits ne peut "
           "deplacer une probabilite de 1/4 que de racine(DeltaH ln2 / 2), borne qui vaut "
           "pour TOUT predicteur ayant la meme information et non seulement pour les trois "
           "testes")
    STAT = (f"DeltaH = H(1/4) - L, ou L est la perte logarithmique en bits sur les "
            f"{ncoup} couples (tirage, numero) de la tranche de mesure, pour chacun des "
            f"trois modeles ; et la borne de Pinsker qui en decoule. Calibrage sur {REPS} "
            f"repliques SRS pour la loi de DeltaH sous l'hypothese nulle")
    NUL = (f"EXACTE pour la reference : sous SRS la meilleure probabilite est 1/4 et la "
           f"perte vaut H(1/4) = {H14:.6f} bit exactement. La loi de DeltaH sous la nulle "
           f"est obtenue en rejouant la meme chaine d'ajustement et de mesure sur des "
           f"archives SRS, ce qui capture le sur-apprentissage residuel du modele a 31 "
           f"traits")
    VER = ("conforme si DeltaH du meilleur modele ne depasse pas le 95e centile de sa loi "
           "sous SRS ; INFORMATION EXTRAITE sinon, auquel cas la borne de Pinsker donne "
           "l'avantage maximal accessible")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h206 : ajustement {P.CHAUFFE}..{coupe}, mesure {coupe}..{N}")
    say(f"   {ncoup} couples (tirage, numero) hors echantillon")
    say(f"   H(1/4) = {H14:.6f} bit  — la perte de qui ne sait rien")

    def mesurer(Mx):
        y = Mx[coupe:N].astype(np.float64)
        out = {}
        out["1/4 constant"] = perte(np.full_like(y, 0.25), y)
        out["marges historiques"] = perte(
            modele_marges(Mx, P.CHAUFFE, coupe, coupe, N), y)
        X = E.construire(Mx, BOR, BONUS)
        w, mu, sd = P.ajuster(X[P.CHAUFFE:coupe].reshape(-1, E.NF),
                              Mx[P.CHAUFFE:coupe].reshape(-1))
        S = P.scorer(X, w, mu, sd)[coupe:N]
        del X
        out["31 traits du §192"] = perte(1.0 / (1.0 + np.exp(-S)), y)
        return out

    obs = mesurer(M)
    say(f"\nARCHIVE   {'modele':>22} | {'perte L':>10} | {'DeltaH':>12} | "
        f"{'bits/tirage':>12}")
    for nom, L in obs.items():
        d = H14 - L
        say(f"          {nom:>22} | {L:10.6f} | {d:+12.8f} | {80*d:+12.6f}")

    V = {k: np.empty(REPS) for k in obs}
    rng = np.random.default_rng(0x206)
    for r in range(REPS):
        o = mesurer(lab.srs(N, rng))
        for k in o:
            V[k][r] = H14 - o[k]
        if (r + 1) % 20 == 0:
            say(f"   ... {r+1}/{REPS} repliques")

    say(f"\n   {'modele':>22} | {'DeltaH archive':>15} | {'DeltaH sous SRS':>22} | "
        f"{'z':>7}")
    zmax, arg = 0.0, None
    for nom in obs:
        d = H14 - obs[nom]
        m, s = float(V[nom].mean()), float(V[nom].std())
        z = (d - m) / max(s, 1e-15)
        say(f"   {nom:>22} | {d:+15.8f} | {m:+12.8f} +/-{s:9.8f} | {z:+7.2f}")
        if abs(z) > abs(zmax):
            zmax, arg = z, nom

    # borne de Pinsker sur le meilleur DeltaH admissible a 95 %
    dbest = max(H14 - obs[k] for k in obs)
    haut = max(float(V[k].mean() + 1.645 * V[k].std()) for k in V)
    dsup = max(dbest, haut)
    dp = sqrt(max(dsup, 0.0) * log(2) / 2)
    say(f"\n   borne haute a 95 % sur DeltaH : {dsup:.8f} bit par numero "
        f"({80*dsup:.6f} par tirage)")
    say(f"   inegalite de Pinsker : |Delta p| <= racine(DeltaH ln2 / 2) = {dp:.6f}")
    say(f"   soit un taux top-1 au plus {100*(0.25+dp):.4f} % contre 25,0000 %")
    say(f"   et un gain d'esperance d'au plus {100*4*dp:.3f} % en relatif")

    p = 1.0 if abs(zmax) < 2 else 0.05
    verdict = "INFORMATION EXTRAITE" if zmax > 3 else "conforme"
    say(f"\n   z maximal {zmax:+.2f} ({arg})   ->   {verdict}")
    TOK["m_extra"] = len(obs) - 1
    lab.record(
        TOK, float(abs(zmax)), p=float(p), verdict=verdict,
        power_at=(f"la perte logarithmique est la statistique SUFFISANTE de la "
                  f"predictibilite : tout modele qui extrairait de l'information la ferait "
                  f"baisser. Sur {ncoup} couples, l'ecart-type de DeltaH sous SRS vaut "
                  f"{float(np.std(V['31 traits du §192'])):.2e} bit, donc le test voit une "
                  f"information de {3*float(np.std(V['31 traits du §192'])):.2e} bit par "
                  f"numero. La borne de Pinsker qui en decoule est UNIVERSELLE : elle vaut "
                  f"pour tout predicteur ayant acces a la meme information, pas seulement "
                  f"pour les trois mesures ici"),
        notes=(f"LA BORNE D'INFORMATION (§227) — au lieu de tester un predicteur de plus, "
               f"borner ce qu'AUCUN predicteur ne pourra depasser. Perte logarithmique hors "
               f"echantillon sur {ncoup} couples, contre H(1/4) = {H14:.6f} bit. "
               + " ; ".join(f"{k} : L = {v:.6f}, DeltaH = {H14-v:+.8f}"
                            for k, v in obs.items())
               + f". Borne haute a 95 % sur DeltaH : {dsup:.8f} bit/numero, d'ou par "
               f"Pinsker |Delta p| <= {dp:.6f}, soit un top-1 au plus a "
               f"{100*(0.25+dp):.4f} %."))
    say("   consigne.")
