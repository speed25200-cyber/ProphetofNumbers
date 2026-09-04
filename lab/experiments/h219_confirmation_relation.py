"""h219 — LA CONFIRMATION DU §242 : une règle déclenchée, et la taille de l'effet qui tranche
(RAPPORT §243).

CE QUI S'EST PASSÉ
==================
Le §242 a pré-enregistré : *« RELATION TROUVÉE si le max observé dépasse le `95ᵉ` centile du
max sous SRS »*. Sur le canal du rang, le max vaut `0,015757` contre un `95ᵉ` centile de
`0,014808`. **La règle s'est déclenchée**, `p = 0,048`, et c'est consigné.

Comme au §237, on ne l'explique pas : on la vérifie. Mais ici il y a plus rapide qu'une
nouvelle nulle — **la taille de l'effet**.

L'ARGUMENT QUI NE DEMANDE AUCUNE STATISTIQUE
============================================
Une relation à coefficients unités n'est pas une tendance : c'est une **contrainte
arithmétique exacte**. Si `x_t = ε₁x_{t−J} + ε₂x_{t−K} mod 2^W`, alors
`s_t = r_t − ε₁r_{t−J} − ε₂r_{t−K}` est confiné à **quatre valeurs sur `base`** — pas
« légèrement plus fréquent » : *confiné*. Les témoins plantés du §242 le montrent en clair :

    .NET (21/55)  ->  |Z| = 0,985      ran3 (31/55)  ->  |Z| = 0,985
    Go (273/607)  ->  |Z| = 0,958      l'archive     ->  |Z| = 0,0158

**Un facteur soixante-deux.** Une relation ne peut pas être « un peu vraie ».

CE QUE CETTE SECTION MESURE
===========================
  **La masse.** Pour la cellule gagnante, on affiche l'histogramme complet de `s mod base`
     et la masse de la meilleure fenêtre de quatre valeurs consécutives. Sous la nulle :
     `4/base`. Sous une relation : `1`. C'est le test décisif, et il n'a pas de `p`.
  **La reproduction.** La même cellule, mesurée séparément sur les deux moitiés de l'archive.
     Une contrainte arithmétique ne s'arrête pas au milieu.
  **La stabilité.** On refait le balayage complet sur chaque moitié : la cellule gagnante
     est-elle la même ?
  **Et la nulle d'une cellule, exacte.** Pour une cellule *fixée d'avance*, `Z` est la
     moyenne de `n` vecteurs unitaires d'espérance nulle, donc `P(|Z| ≥ z) = exp(−n·z²)`
     exactement à la limite. On le vérifie par simulation, puis on l'applique — ce qui donne
     une seconde lecture, indépendante des vingt répliques du §242.

CE QUE CET ÉPISODE APPREND SUR MA PROPRE RÈGLE
==============================================
Le seuil du §242 est un `95ᵉ` centile appliqué à **deux** canaux sans correction interne : il
se déclenche donc à tort une fois sur dix, par construction. Ce n'est pas la donnée qui a mal
tourné, c'est **le seuil que j'ai écrit**. Une règle de décision doit porter sa propre
multiplicité, et celle-là ne la portait pas.
"""

import json
import os
import sys
from math import exp, log, sqrt

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import h218_relations_unites as H18                                    # noqa: E402

POOL, DRAWN = 80, 20
EXP_ID = "h219.confirmation_relation"
FJETON = "/tmp/h219_jeton.json"


def say(*a):
    print(*a, flush=True)


def serie(r, J, K, e1, e2, base, deb=0, fin=None):
    """s_t = r_t - e1 r_{t-J} - e2 r_{t-K} mod base, sur [deb, fin)."""
    n = len(r) if fin is None else fin
    d = max(J, K)
    t = np.arange(max(deb, d), n)
    return (r[t] - e1 * r[t - J] - e2 * r[t - K]) % base


def zed(s, base):
    return float(abs(np.exp(2j * np.pi * s / base).mean()))


def masse4(s, base):
    """masse de la meilleure fenetre de 4 valeurs consecutives modulo base."""
    h = np.bincount(s, minlength=base).astype(np.float64) / len(s)
    dbl = np.r_[h, h]
    return float(max(dbl[i:i + 4].sum() for i in range(base)))


if __name__ == "__main__":
    import lab

    A = lab.load()
    bonus = np.asarray(A.bonus).astype(np.int64)
    nums = np.asarray(A.nums).astype(np.int64)
    N = len(bonus)
    RANG = (nums < bonus[:, None]).sum(axis=1)
    NUM = bonus - 1
    CANAUX = (("rang du bonus", RANG, DRAWN), ("numero du bonus", NUM, POOL))
    MIL = N // 2

    HYP = (f"La cellule gagnante du §242 n'est pas une relation. Le §242 a pre-enregistre "
           f"« RELATION TROUVEE si le max depasse le 95e centile du max sous SRS » et sur le "
           f"canal du rang le max vaut 0,015757 contre un 95e centile de 0,014808 : la regle "
           f"s'est declenchee, p = 0,048. On ne l'explique pas, on la verifie — et ici il y a "
           f"plus rapide qu'une nouvelle nulle, la TAILLE DE L'EFFET. Une relation a "
           f"coefficients unites n'est pas une tendance mais une contrainte arithmetique "
           f"EXACTE : s_t est CONFINE a quatre valeurs sur base, pas « legerement plus "
           f"frequent ». Les temoins plantes du §242 rendent |Z| = 0,985 (.NET et ran3) et "
           f"0,958 (Go) quand l'archive rend 0,0158 — un facteur 62. On mesure donc (1) la "
           f"MASSE de la meilleure fenetre de quatre valeurs pour la cellule gagnante, qui "
           f"vaut 4/base sous la nulle et 1 sous une relation, test decisif et sans p ; (2) "
           f"la REPRODUCTION de cette cellule sur chacune des deux moities, une contrainte "
           f"arithmetique ne s'arretant pas au milieu ; (3) la STABILITE de l'argmax quand on "
           f"refait le balayage complet sur chaque moitie ; (4) la nulle EXACTE d'une cellule "
           f"fixee d'avance, P(|Z| >= z) = exp(-n z^2), verifiee par simulation puis "
           f"appliquee, ce qui donne une seconde lecture independante des vingt repliques du "
           f"§242. Et le constat de methode : le seuil du §242 est un 95e centile applique a "
           f"DEUX canaux sans correction interne, donc il se declenche a tort une fois sur "
           f"dix par construction — ce n'est pas la donnee qui a mal tourne, c'est le seuil "
           f"que j'ai ecrit")
    STAT = ("masse de la meilleure fenetre de quatre valeurs consecutives de s mod base pour "
            "la cellule gagnante de chaque canal, sur l'archive entiere et sur chaque moitie ; "
            "plus la stabilite de l'argmax entre les deux moities")
    NUL = ("EXACTE : sous SRS, s mod base est uniforme, donc la masse d'une fenetre de quatre "
           "vaut 4/base (0,20 pour le rang, 0,05 pour le numero). Sous une relation a "
           "coefficients unites elle vaut 1. Et pour une cellule fixee, "
           "P(|Z| >= z) = exp(-n z^2)")
    VER = ("RELATION CONFIRMEE si la masse depasse 0,5 ET que la cellule gagnante est la meme "
           "sur les deux moities ; ARTEFACT DE SEUIL sinon")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    # -------------------------------------------------- (4) la nulle d'une cellule
    say("\n   la nulle EXACTE d'une cellule fixee : P(|Z| >= z) = exp(-n z^2)")
    rng = np.random.default_rng(219)
    n0, m0 = 4000, 4000
    zz = np.array([zed(rng.integers(0, DRAWN, n0), DRAWN) for _ in range(m0)])
    for q in (0.5, 0.9, 0.99):
        obs_q = float(np.quantile(zz, q))
        theo = sqrt(-log(1 - q) / n0)
        say(f"      centile {q:4.2f} : simule {obs_q:.5f}   theorique {theo:.5f}   "
            f"rapport {obs_q/theo:.3f}")

    # -------------------------------------------------- (1)(2)(3)
    say("")
    resume = []
    for nom, r, base in CANAUX:
        best, arg = H18.concentrations(np.asarray(r), base)
        _, J, K, e1, e2 = arg
        n_eff = N - max(J, K)
        p1 = exp(-n_eff * best * best)
        say(f"   {nom} : cellule gagnante (J = {J}, K = {K}, signes {e1:+d}/{e2:+d})")
        say(f"      |Z| = {best:.6f}   p d'une cellule FIXEE = {p1:.3e}   "
            f"x {H18.compte()*2} cellules -> {min(1.0, p1*H18.compte()*2):.4f}")

        s = serie(np.asarray(r), J, K, e1, e2, base)
        h = np.bincount(s, minlength=base) / len(s)
        m4 = masse4(s, base)
        say(f"      masse de la meilleure fenetre de 4 : {m4:.5f}   "
            f"(nulle {4/base:.5f}, relation 1,00000)")
        say(f"      histogramme (max {h.max():.5f}, min {h.min():.5f}, "
            f"plat = {1/base:.5f})")

        s1 = serie(np.asarray(r), J, K, e1, e2, base, 0, MIL)
        s2 = serie(np.asarray(r), J, K, e1, e2, base, MIL, N)
        say(f"      |Z| moitie 1 = {zed(s1, base):.6f}   moitie 2 = {zed(s2, base):.6f}")

        b1, a1 = H18.concentrations(np.asarray(r)[:MIL], base)
        b2, a2 = H18.concentrations(np.asarray(r)[MIL:], base)
        say(f"      argmax moitie 1 : J = {a1[1]}, K = {a1[2]}, |Z| = {b1:.6f}")
        say(f"      argmax moitie 2 : J = {a2[1]}, K = {a2[2]}, |Z| = {b2:.6f}")
        stable = (a1[1], a1[2], a1[3], a1[4]) == (a2[1], a2[2], a2[3], a2[4])
        say(f"      cellule gagnante identique sur les deux moities : "
            f"{'OUI' if stable else 'NON'}")
        resume.append((nom, J, K, best, m4, stable))
        say("")

    confirme = any(m4 > 0.5 and st for _, _, _, _, m4, st in resume)
    verdict = "RELATION CONFIRMEE" if confirme else "ARTEFACT DE SEUIL"
    say(f"   {verdict}")
    if not confirme:
        say("   -> la cellule gagnante du §242 n'est pas une relation : sa masse est celle du "
            "hasard,")
        say("      et le seuil qui s'est declenche etait un 95e centile sur deux canaux, "
            "donc faux")
        say("      une fois sur dix par construction.")

    TOK["m_extra"] = 5
    lab.record(
        TOK, float(max(x[4] for x in resume)), p=1.0, verdict=verdict,
        power_at=(f"le test de masse est DECISIF et non probabiliste : les temoins plantes du "
                  f"§242 (.NET 21/55, ran3 31/55, Go 273/607) donnent une masse de 1 et un "
                  f"|Z| de 0,96 a 0,99 ; l'archive donne "
                  f"{max(x[4] for x in resume):.5f} de masse. Il n'y a pas de zone grise "
                  f"entre « relation » et « pas de relation » — une contrainte arithmetique "
                  f"est exacte ou n'existe pas"),
        notes=(f"CONFIRMATION DU §242 (§243) — la regle du §242 s'est declenchee sur le canal "
               f"du rang (max 0,015757 contre un 95e centile de 0,014808, p = 0,048). La "
               f"taille de l'effet tranche sans statistique : une relation a coefficients "
               f"unites CONFINE s a quatre valeurs sur base, donc masse 1 et |Z| ~ 0,98 ; "
               f"l'archive donne une masse de {max(x[4] for x in resume):.5f} et un |Z| de "
               f"0,0158, soit un facteur 62. "
               + " ; ".join(f"{x[0]} : J={x[1]}, K={x[2]}, |Z|={x[3]:.6f}, masse={x[4]:.5f}, "
                            f"stable={'oui' if x[5] else 'non'}" for x in resume)
               + f". {verdict}. CONSTAT DE METHODE : le seuil du §242 etait un 95e centile "
               f"applique a deux canaux sans correction interne, donc faux positif une fois "
               f"sur dix par construction — ce n'est pas la donnee qui a mal tourne, c'est le "
               f"seuil que j'ai ecrit."))
    say("   consigne.")
