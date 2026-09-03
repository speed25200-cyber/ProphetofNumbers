"""h195 — LES PARITÉS D'ORDRE QUATRE : le seul trou que le §7.37 laisse ouvert
(RAPPORT §215).

CE FICHIER N'EST PAS UNE IDÉE DE PLUS. C'EST LA SEULE QUI RESTE.
================================================================
Le §7.37 découpe ce qu'un dossier de nullités garantit, et ce découpage désigne un unique
survivant :

* la **moyenne** de toute grille est fixée par les marges — conformes (§210 A) ;
* la **variance** de toute grille est fixée par les paires — aucune des `3 160` hors de
  `± 6,3 %` (§213 A) ;
* les **triplets** sont bornés à `± 15,6 %` (§213 B) ;
* les ordres **`≥ 4`** ne sont bornés **par rien de ce qui précède**.

Et ce n'est pas une échappatoire théorique. La construction qui vit exactement là est la
plus banale qui soit en cryptographie : une dépendance de **type parité**, où toute marge
d'ordre inférieur est *exactement* uniforme et où seule la coïncidence complète est biaisée.
C'est la signature d'un générateur **`F₂`-linéaire** — un LFSR, un xorshift, un Mersenne
Twister — dont la sortie est réduite à quatre-vingts classes.

Autrement dit, le trou que le §7.37 nomme est précisément la forme qu'aurait le défaut du
générateur le plus probable de tous.

CE QUI EST MESURÉ
=================
Pour chaque partie `S` de quatre numéros parmi quatre-vingts — il y en a `1 581 580` — la
**parité** du nombre de ses membres sortis :

    W_S = (1/N) · Σ_t (−1)^{|S ∩ D_t|}

Toute relation `F₂`-linéaire entre quatre classes se voit là, et **nulle part ailleurs dans
le dossier** : elle laisse les marges, les paires et les triplets exactement uniformes.

L'IDENTITÉ QUI REND LE CALCUL POSSIBLE
======================================
Naïvement il faudrait `70 560 × 1 581 580 = 1,1 × 10¹¹` évaluations. Mais avec
`y_i = 1 − 2x_i ∈ {±1}`, on a `(−1)^{|S∩D|} = ∏_{i∈S} y_i`, et en développant le produit :

    N · W_S  =  Σ_{T ⊆ S} (−2)^{|T|} · C_T

où `C_T` est le nombre de tirages contenant **tout** `T`. Il suffit donc des comptes
d'inclusion d'ordre `0` à `4` — un `bincount` par ordre — et l'assemblage est vectoriel.
Le contrôle `--autotest` vérifie cette identité par calcul direct.

LA NULLE EST EXACTE, ET CE N'EST PAS `(1/2)⁴`
=============================================
Sous SRS, `|S ∩ D|` est hypergéométrique, donc

    E[(−1)^{|S∩D|}] = Σ_h (−1)^h C(4,h)·C(76,20−h)/C(80,20) = **3799/79079** = 0,04804057

et non `(1/2)⁴ = 0,0625`. L'écart vient de la contrainte « exactement vingt par tirage »,
la même qui rabote les sommes de `z²` du §213. Le produit valant `±1`, sa variance vaut
`1 − E²` exactement, et l'écart-type de `W_S` sur `N` tirages indépendants suit. Aucune
simulation dans la nulle ; les répliques ne servent qu'à la loi du **maximum**, dont la
corrélation entre parties chevauchantes interdit un Bonferroni (§7.32).
"""

import json
import os
import sys
from fractions import Fraction as F
from itertools import combinations
from math import erfc, sqrt

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POOL, DRAWN = 80, 20
EXP_ID = "h195.parites_ordre_quatre"
FJETON = "/tmp/h195_jeton.json"
REPS = 40
ORDRE = 4


def say(*a):
    print(*a, flush=True)


def binom(n, r):
    v = F(1)
    for i in range(r):
        v *= F(n - i, i + 1)
    return v


def parite_exacte(k):
    """E[(-1)^|S inter D|] sous SRS, en fraction EXACTE."""
    return sum((-1) ** h * binom(k, h) * binom(POOL - k, DRAWN - h) / binom(POOL, DRAWN)
               for h in range(k + 1))


def inclusions(NU, k, poids):
    """comptes C_T pour toutes les parties T de taille k, indexes a plat en base 80."""
    idx = np.array(list(combinations(range(DRAWN), k))).T
    acc = np.zeros(POOL ** k, np.int64)
    for d in range(0, len(NU), 1024):
        Q = NU[d:d + 1024]
        p = Q[:, idx[0]] * poids[0]
        for j in range(1, k):
            p += Q[:, idx[j]] * poids[j]
        acc += np.bincount(p.ravel(), minlength=POOL ** k)
    return acc


def parites(NU, N, PL):
    """N * W_S pour toutes les parties de quatre, par l'identite de developpement."""
    C1 = np.bincount(NU.ravel(), minlength=POOL).astype(np.int64)
    C2 = inclusions(NU, 2, (POOL, 1))
    C3 = inclusions(NU, 3, (POOL * POOL, POOL, 1))
    C4 = inclusions(NU, 4, (POOL ** 3, POOL ** 2, POOL, 1))
    s = np.full(len(PL["quad"]), float(N))
    for f in PL["uni"]:
        s -= 2.0 * C1[f]
    for f in PL["pai"]:
        s += 4.0 * C2[f]
    for f in PL["tri"]:
        s -= 8.0 * C3[f]
    s += 16.0 * C4[PL["quad"]]
    return s


def plats():
    """index a plat des 1 581 580 parties de quatre et de toutes leurs sous-parties."""
    S = np.array(list(combinations(range(POOL), ORDRE)), np.int64)
    a, b, c, d = S[:, 0], S[:, 1], S[:, 2], S[:, 3]
    return {
        "uni": [a, b, c, d],
        "pai": [a * POOL + b, a * POOL + c, a * POOL + d,
                b * POOL + c, b * POOL + d, c * POOL + d],
        "tri": [a * 6400 + b * POOL + c, a * 6400 + b * POOL + d,
                a * 6400 + c * POOL + d, b * 6400 + c * POOL + d],
        "quad": a * POOL ** 3 + b * POOL ** 2 + c * POOL + d,
        "S": S,
    }


def selftest():
    """Trois contrôles, et le premier est le seul qui compte vraiment.

    (1) L'IDENTITÉ. `N·W_S = Σ_{T⊆S} (−2)^{|T|} C_T` est ce qui rend le calcul faisable ;
        si elle est fausse, tout le reste est du bruit bien présenté. On la vérifie par
        calcul DIRECT de la parité, sur un jeu synthétique.
    (2) LA NULLE. `E₄ = 3799/79079`, par deux dérivations indépendantes. Attention : sa
        moyenne empirique sur toutes les parties est une **identité algébrique**, vraie de
        n'importe quelle collection de tirages `20/80` — la retrouver ne confirme rien de
        la nulle, c'est un contrôle d'assemblage. Le contenu statistique de la nulle est sa
        **variance**, et c'est elle qu'on vérifie sur répliques.
    (3) LE TÉMOIN. Une parité plantée sur une partie de quatre doit ressortir comme le
        maximum, et à la bonne partie.
    """
    import lab
    say("h195 --autotest : donnees synthetiques uniquement, aucune archive lue")
    PL = plats()

    say("\n   (1) L'IDENTITE N.W_S = somme_(T inclus dans S) (-2)^|T| C_T")
    rng = np.random.default_rng(195)
    M = lab.srs(3000, rng)
    NU = np.nonzero(M)[1].reshape(3000, DRAWN).astype(np.int64)
    s = parites(NU, 3000, PL)
    Y = 1 - 2 * M.astype(np.int64)
    ech = rng.choice(len(PL["quad"]), 40, replace=False)
    direct = np.array([Y[:, PL["S"][j]].prod(axis=1).sum() for j in ech], np.float64)
    ecart = float(np.abs(direct - s[ech]).max())
    say(f"       40 parties tirees au hasard, ecart maximal a la parite directe : {ecart:g}")
    ok = ecart == 0.0
    say(f"       -> {'IDENTITE VERIFIEE' if ok else 'IDENTITE FAUSSE'}")

    say("\n   (2) LA NULLE EXACTE — et ce que la moyenne empirique ne prouve PAS")
    for k in range(1, 6):
        say(f"       E[parite] ordre {k} = {parite_exacte(k)} = "
            f"{float(parite_exacte(k)):.8f}   ((1/2)^{k} = {0.5**k:.8f})")
    E4 = float(parite_exacte(ORDRE))

    # La moyenne de W_S sur TOUTES les parties est une IDENTITE ALGEBRIQUE, vraie de
    # n'importe quelle collection de tirages a vingt numeros sur quatre-vingts : pour un
    # tirage donne, somme_{|S|=4} (-1)^|S inter D| = somme_h (-1)^h C(20,h) C(60,4-h), qui
    # ne depend que de |D| = 20. La retrouver ne confirme donc RIEN de la nulle ; cela
    # verifie mon assemblage, ce qui est utile mais n'est pas la meme chose, et le
    # presenter comme une confirmation serait une tromperie.
    ferme = sum((-1) ** h * binom(DRAWN, h) * binom(POOL - DRAWN, ORDRE - h)
                for h in range(ORDRE + 1)) / binom(POOL, ORDRE)
    say(f"       forme fermee somme_h (-1)^h C(20,h) C(60,4-h) / C(80,4) = {ferme}")
    bon = ferme == parite_exacte(ORDRE)
    say(f"       -> {'les deux derivations coincident' if bon else 'DERIVATIONS EN DESACCORD'}")
    ok &= bon
    M = lab.srs(20000, rng)
    NU = np.nonzero(M)[1].reshape(20000, DRAWN).astype(np.int64)
    W = parites(NU, 20000, PL) / 20000
    say(f"       moyenne empirique : {W.mean():.8f} contre {E4:.8f} — coincidence FORCEE "
        f"par l'identite, c'est un controle d'assemblage et non de nulle")
    bon = abs(W.mean() - E4) < 1e-9
    say(f"       -> {'assemblage correct' if bon else 'ASSEMBLAGE FAUX'}")
    ok &= bon

    # Le contenu statistique de la nulle est sa VARIANCE. Elle, se verifie.
    R, n = 40, 6000
    tem = rng.choice(len(PL["quad"]), 3, replace=False)
    V = np.empty((R, len(tem)))
    for r in range(R):
        Sm = lab.srs(n, rng)
        NUs = np.nonzero(Sm)[1].reshape(n, DRAWN).astype(np.int64)
        V[r] = parites(NUs, n, PL)[tem] / n
    att = sqrt((1 - E4 * E4) / n)
    mes = float(V.std(axis=0).mean())
    say(f"       ecart-type de W_S sur {R} repliques de {n} tirages : {mes:.6f} "
        f"contre racine((1-E4²)/n) = {att:.6f}")
    bon = abs(mes - att) / att < 0.25
    say(f"       -> {'VARIANCE CONFIRMEE' if bon else 'VARIANCE FAUSSE'}")
    ok &= bon

    say("\n   (3) LE TEMOIN : une parite plantee sur une partie de quatre")
    NT, EPS = 40000, 0.05
    CIBLE = np.array([5, 26, 48, 71])
    M = lab.srs(NT, rng)
    frappe = rng.random(NT) < EPS
    for i in np.flatnonzero(frappe):
        if int(M[i, CIBLE].sum()) % 2 == 1:              # rendre la parite PAIRE
            dedans = CIBLE[M[i, CIBLE]]
            if len(dedans):                              # retirer un membre, en rendre un
                x = int(rng.choice(dedans))
                libres = np.flatnonzero(~M[i])
                M[i, x] = False
                M[i, int(rng.choice(libres))] = True
            else:
                x = int(rng.choice(CIBLE))
                pris = np.flatnonzero(M[i] & ~np.isin(np.arange(POOL), CIBLE))
                M[i, int(rng.choice(pris))] = False
                M[i, x] = True
    NU = np.nonzero(M)[1].reshape(NT, DRAWN).astype(np.int64)
    W = parites(NU, NT, PL) / NT
    z = (W - E4) / sqrt((1 - E4 * E4) / NT)
    j = int(np.argmax(np.abs(z)))
    trouve = list(PL["S"][j])
    say(f"       plantee {list(CIBLE)} a {100*EPS:.0f} % ; maximum |z| = {z[j]:+.2f} "
        f"sur {trouve}")
    bon = trouve == list(CIBLE) and abs(z[j]) > 6
    say(f"       -> {'TEMOIN RETROUVE' if bon else 'TEMOIN MANQUE'}")
    ok &= bon
    say(f"\n   -> {'CALIBRE 3/3' if ok else 'DEFAILLANT'}")
    return ok


if __name__ == "__main__":
    if "--autotest" in sys.argv:
        sys.exit(0 if selftest() else 1)

    import lab

    A = lab.load()
    M = np.asarray(A.mask)
    N = len(M)
    NU = np.nonzero(M)[1].reshape(N, DRAWN).astype(np.int64)
    n2 = N // 2
    PL = plats()
    NS = len(PL["quad"])
    E4 = float(parite_exacte(ORDRE))
    SD = sqrt((1 - E4 * E4) / N)

    HYP = ("Aucune relation de parite d'ordre quatre ne lie les numeros d'un tirage. Le "
           "§7.37 decoupe ce que le dossier garantit et designe un unique survivant : la "
           "moyenne d'une grille est fixee par les marges, conformes ; sa variance par les "
           "paires, bornees a +/- 6,3 % ; les triplets a +/- 15,6 % ; et les ordres >= 4 ne "
           "sont bornes PAR RIEN de ce qui precede. Ce n'est pas une echappatoire "
           "theorique : la construction qui vit exactement la est la plus banale de la "
           "cryptographie, une dependance de type PARITE dont toute marge d'ordre inferieur "
           "est exactement uniforme et dont seule la coincidence complete est biaisee — "
           "c'est-a-dire la signature d'un generateur F2-lineaire (LFSR, xorshift, Mersenne "
           "Twister) reduit a quatre-vingts classes. Le trou que le §7.37 nomme est donc "
           "precisement la forme qu'aurait le defaut du generateur le plus probable de "
           f"tous. On mesure la parite W_S = (1/N) somme_t (-1)^|S inter D_t| pour les "
           f"{NS} parties S de quatre numeros parmi quatre-vingts, ce qui n'est fait nulle "
           "part ailleurs dans le dossier")
    STAT = (f"max |z| sur les {NS} parties, ou z = (W_S - E4)/racine((1-E4²)/N), reduit par "
            f"la loi EMPIRIQUE du maximum sur {REPS} repliques SRS chacune laissee hors de "
            f"sa propre normalisation ; plus l'energie somme (W_S - E4)² et la parite hors "
            "echantillon de la partie la plus extreme de la premiere moitie")
    NUL = (f"EXACTE, aucune simulation dans la nulle : sous SRS |S inter D| est "
           f"hypergeometrique, donc E[(-1)^|S inter D|] = {parite_exacte(ORDRE)} = "
           f"{E4:.8f} — et NON (1/2)^4 = 0,0625, l'ecart venant de la contrainte exactement "
           f"vingt par tirage. Le produit valant +/-1, sa variance vaut 1 - E² exactement, "
           f"d'ou un ecart-type de {SD:.8f} sur {N} tirages independants. Les repliques ne "
           "servent qu'a la loi du MAXIMUM, dont la correlation entre parties chevauchantes "
           "interdit un Bonferroni (§7.32)")
    VER = ("conforme si le maximum reduit reste sous le 95e centile de sa loi empirique ; "
           "RELATION DE PARITE sinon, auquel cas la partie designee donne une relation "
           "F2-lineaire entre quatre classes et donc une prise sur le generateur")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h195 : {N} tirages ; {NS} parties de quatre")
    say(f"   nulle exacte E4 = {parite_exacte(ORDRE)} = {E4:.8f} ; ecart-type {SD:.8f}")

    W = parites(NU, N, PL) / N
    z = (W - E4) / SD
    j = int(np.argmax(np.abs(z)))
    obs = np.array([float(np.abs(z).max()), float(((W - E4) ** 2).sum() * N)])
    say(f"\nARCHIVE   max |z| = {z[j]:+.3f} sur la partie {list(PL['S'][j] + 1)}")
    say(f"          energie N.somme (W-E4)² = {obs[1]:.1f}   (attendue ~{NS:d})")
    say(f"          moyenne des z {z.mean():+.4f}, ecart-type {z.std():.4f}")

    V = np.empty((REPS, 2))
    rng = np.random.default_rng(0x195)
    for r in range(REPS):
        S = lab.srs(N, rng)
        NUs = np.nonzero(S)[1].reshape(N, DRAWN).astype(np.int64)
        Ws = parites(NUs, N, PL) / N
        V[r] = (float(np.abs((Ws - E4) / SD).max()), float(((Ws - E4) ** 2).sum() * N))
        if (r + 1) % 10 == 0:
            say(f"   ... {r+1}/{REPS} repliques")

    s1, s2 = V.sum(axis=0), (V * V).sum(axis=0)
    mu, sd = V.mean(axis=0), V.std(axis=0)
    o = float(np.abs((obs - mu) / np.maximum(sd, 1e-12)).max())
    mx = np.empty(REPS)
    for r in range(REPS):
        m_ = (s1 - V[r]) / (REPS - 1)
        v_ = np.maximum((s2 - V[r] * V[r]) / (REPS - 1) - m_ * m_, 1e-12)
        mx[r] = float(np.abs((V[r] - m_) / np.sqrt(v_)).max())
    p = float((1 + int((mx >= o).sum())) / (1 + REPS))

    say(f"\n   {'statistique':>16} | {'archive':>12} | {'repliques':>20} | {'z reduit':>9}")
    for i, nom in enumerate(("max |z|", "energie")):
        say(f"   {nom:>16} | {obs[i]:12.3f} | {mu[i]:12.3f} +/-{sd[i]:7.3f} | "
            f"{(obs[i]-mu[i])/max(sd[i],1e-12):+9.3f}")
    say(f"   maximum reduit {o:.3f} ; median des repliques {np.median(mx):.3f} ; "
        f"95e centile {np.percentile(mx, 95):.3f}")

    # -- hors echantillon : la partie la plus extreme de la premiere moitie, mesuree sur
    #    la seconde. C'est le meme protocole que le §213 D, et il tranche de la meme facon.
    W1 = parites(NU[:n2], n2, PL) / n2
    j1 = int(np.argmax(np.abs((W1 - E4))))
    W2 = parites(NU[n2:], N - n2, PL) / (N - n2)
    sd2 = sqrt((1 - E4 * E4) / (N - n2))
    z1 = (W1[j1] - E4) / sqrt((1 - E4 * E4) / n2)
    z2 = (W2[j1] - E4) / sd2
    say(f"\n   HORS ECHANTILLON : partie {list(PL['S'][j1] + 1)} choisie sur la premiere "
        f"moitie")
    say(f"      en echantillon z = {z1:+.2f}   hors echantillon z = {z2:+.2f}")

    verdict = "RELATION DE PARITE" if p <= 0.05 else "conforme"
    say(f"\n   p (loi empirique du maximum, {REPS} repliques) = {p:.4f}   ->   {verdict}")
    TOK["m_extra"] = NS - 1
    lab.record(
        TOK, o, p=p, verdict=verdict,
        power_at=(f"l'ecart-type de W_S vaut {SD:.6f} sur {N} tirages, donc une relation de "
                  f"parite portee par une fraction eps des tirages sort a z = eps.(1-E4)/"
                  f"{SD:.6f}, soit z = {0.01*(1-E4)/SD:.1f} pour eps = 1 % et "
                  f"{0.002*(1-E4)/SD:.1f} pour eps = 0,2 %. Le test voit donc une relation "
                  f"F2-lineaire portee par deux tirages sur mille. Le temoin plante une "
                  f"parite a 5 % sur 40 000 tirages et la retrouve a la bonne partie"),
        notes=(f"LES PARITES D'ORDRE QUATRE (§215) — le seul trou que le §7.37 laisse "
               f"ouvert, et c'est la forme qu'aurait le defaut d'un generateur F2-lineaire. "
               f"{NS} parties de quatre, nulle EXACTE E4 = {parite_exacte(ORDRE)} (et non "
               f"(1/2)^4, la contrainte des vingt par tirage faisant l'ecart), calcul rendu "
               f"faisable par l'identite N.W_S = somme_(T inclus dans S) (-2)^|T| C_T "
               f"verifiee par calcul direct. Archive : max |z| = {z[j]:+.3f} sur "
               f"{list(PL['S'][j] + 1)}, energie {obs[1]:.1f} pour {NS} attendus ; maximum "
               f"reduit {o:.3f} contre un 95e centile de {np.percentile(mx, 95):.3f}, "
               f"p = {p:.4f}. Hors echantillon, la partie la plus extreme de la premiere "
               f"moitie passe de z = {z1:+.2f} a z = {z2:+.2f}."))
    say("   consigne.")
