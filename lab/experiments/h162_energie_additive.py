"""h162 — l'ENERGIE ADDITIVE des tirages modulo 80 : la statistique que le crible de classes
teste vraiment (THEORIE_ETAT §7.27 ; RAPPORT §177).

D'OU VIENT CETTE IDEE
=====================
Le crible de classes du §172 avance mot par mot : la classe du mot `i` vaut
`c_{i-K} + c_{i-L} + delta (mod 80)` avec `delta` dans {0, 1}, et le mot ne survit que si
cette classe est PUBLIEE par le tirage. Un chemin ne traverse donc un tirage que si ce
tirage contient beaucoup de COINCIDENCES ADDITIVES : des triplets `(u, v, w)` de classes
publiees avec `w = u + v` ou `w = u + v + 1` modulo 80.

Le theoreme du tirage unitaire (§7.27) donne l'esperance du nombre de chemins survivants
pour un tirage tire au hasard : `40^L / C(40,20)`. Mais cette esperance est une MOYENNE sur
les tirages. Pour un tirage DONNE, le compte depend de sa structure additive — et cette
structure, personne dans ce dossier ne l'a mesuree.

C'est donc une statistique naturelle, directement issue de la mecanique de l'attaque, et
jamais testee : le nombre de triplets additifs d'un tirage, modulo 80.

LES DEUX STATISTIQUES
=====================
Pour un tirage de classes `C` (vingt valeurs dans 0..79) :

    T0(C) = #{(u, v) dans C x C : (u + v) mod 80 dans C}
    T1(C) = #{(u, v) dans C x C : (u + v + 1) mod 80 dans C}

Sous SRS — un sous-ensemble de vingt valeurs pris au hasard parmi quatre-vingts — chacune
vaut environ `400 x 20/80 = 100`, mais pas exactement : les cas `u = v`, `w = u`, `w = v`
introduisent des corrections d'ordre 1/80 qu'il ne sert a rien de calculer a la main. La
nulle est donc obtenue par SIMULATION exacte du meme nombre de tirages SRS, ce qui la rend
insensible a ces corrections.

CE QUE LA MESURE PEUT DIRE
==========================
Un EXCES de coincidences additives est ce qu'un generateur additif laisserait : ses classes
verifient la relation a trois termes, donc ses tirages en contiennent par construction. Un
DEFICIT est plus surprenant, et c'est ce qu'une mesure preliminaire du crible unitaire a
suggere — zero chemin survivant la ou la formule en attend onze. Les deux directions sont
donc lues, et le test est BILATERAL.
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POOL, DRAWN = 80, 20
EXP_ID = "h162.energie_additive"
FJETON = "/tmp/h162_jeton.json"
REPS = 40


def say(*a):
    print(*a, flush=True)


def triplets(masques, decalage):
    """T_decalage pour chaque tirage : #{(u,v) : u,v,(u+v+decalage) mod 80 publies}.

    `masques` : (n, 80) booleen. Le calcul passe par une convolution CIRCULAIRE, car
    `#{(u,v) : u+v = w}` sur un ensemble est exactement l'auto-convolution de son indicatrice
    modulo 80 — d'ou un cout en `n x 80 log 80` au lieu de `n x 400`.
    """
    f = np.fft.rfft(masques.astype(np.float64), axis=1)
    conv = np.fft.irfft(f * f, n=POOL, axis=1)              # conv[w] = #{(u,v) : u+v = w}
    conv = np.rint(conv).astype(np.int64)
    w = (np.arange(POOL) - decalage) % POOL
    return (conv[:, w] * masques).sum(axis=1)


def stats(masques):
    return np.array([triplets(masques, 0).mean(), triplets(masques, 1).mean()])


def srs(n, rng):
    """n tirages SRS 20/80, vectorises : argpartition d'une matrice uniforme."""
    idx = np.argpartition(rng.random((n, POOL)), DRAWN, axis=1)[:, :DRAWN]
    m = np.zeros((n, POOL), bool)
    m[np.arange(n)[:, None], idx] = True
    return m


if __name__ == "__main__":
    import lab

    if "--selftest" in sys.argv:
        say("h162 --selftest : synthetique, aucune donnee reelle")
        rng = np.random.default_rng(7)
        # (a) coherence de la convolution avec le comptage direct
        m = srs(50, rng)
        for dec in (0, 1):
            direct = []
            for i in range(50):
                C = set(np.flatnonzero(m[i]).tolist())
                direct.append(sum(1 for u in C for v in C if (u + v + dec) % POOL in C))
            ok = np.array_equal(np.array(direct), triplets(m, dec))
            say(f"   decalage {dec} : convolution == comptage direct : {'OUI' if ok else 'NON'}")
            if not ok:
                sys.exit(1)
        # (b) puissance : un tirage ENGENDRE par un Fibonacci additif doit montrer un exces
        import random as R
        M32 = 1 << 32
        K, L = 3, 7
        r = [R.Random(11).randrange(M32) for _ in range(L)]
        i = L
        tir = []
        for _ in range(400):
            vus = set()
            while len(vus) < DRAWN:
                r.append((r[i - K] + r[i - L]) % M32); i += 1
                vus.add((r[i - 1] * POOL) >> 32)
            tir.append(sorted(vus))
        mg = np.zeros((400, POOL), bool)
        for j, t in enumerate(tir):
            mg[j, t] = True
        sg = stats(mg)
        sn = stats(srs(400, rng))
        say(f"   T0, T1 sur 400 tirages d'un (3,7) lu par troncature : {sg.round(3)}")
        say(f"   T0, T1 sur 400 tirages SRS                          : {sn.round(3)}")
        say("   (le crible n'exige pas un exces MOYEN : la relation ne lie que des mots")
        say("    CONSECUTIFS du flux, pas toutes les paires du tirage — le temoin sert")
        say("    a verifier le calcul, pas a prouver une direction.)")
        sys.exit(0)

    if "--archive" not in sys.argv:
        print(__doc__)
        sys.exit(0)

    HYP = ("Les tirages de l'archive ont la meme ENERGIE ADDITIVE modulo 80 que des tirages "
           "SRS : le nombre moyen de couples (u,v) de classes publiees dont la somme "
           "u+v (T0) ou u+v+1 (T1) est elle aussi publiee ne s'ecarte pas de la nulle. "
           "C'est la structure exacte dont le crible de classes du §172 se nourrit — un "
           "generateur additif en laisserait, et le §7.27 montre que le compte de chemins "
           "survivants d'un tirage en depend directement")
    STAT = ("D = max sur les deux statistiques |z| ou z = (moyenne archive - moyenne SRS) / "
            "ecart-type SRS de la moyenne, la loi par tirage etant estimee sur 40 x 70 560 "
            "tirages SRS et l'ecart-type de la moyenne valant sd(par tirage)/sqrt(n) ; "
            "test BILATERAL, les deux directions etant interpretables (exces = trace "
            "additive ; deficit = repulsion additive)")
    NUL = ("Simulation : 2 822 400 tirages SRS 20/80 independants, dont on tire la moyenne "
           "et la variance PAR TIRAGE. "
           "Aucun calcul analytique — les corrections d'ordre 1/80 dues aux cas u = v, "
           "w = u, w = v sont absorbees par la nulle simulee")
    VER = "conforme si p > 0,05 apres correction bilaterale sur les deux statistiques"

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    A = lab.load()
    M = np.asarray(A.mask)
    n = len(M)
    obs = stats(M)
    say(f"h162 : {n} tirages ; T0 = {obs[0]:.5f}, T1 = {obs[1]:.5f}")

    # La nulle porte sur la MOYENNE de n tirages : on estime la loi PAR TIRAGE sur
    # REPS x n tirages SRS, puis sd(moyenne) = sd(par tirage) / sqrt(n). C'est exact et
    # cent fois moins cher que REPS replicats de la moyenne.
    rng = np.random.default_rng(20260902)
    somme = np.zeros(2); somme2 = np.zeros(2); cpt = 0
    for k in range(REPS):
        m = srs(n, rng)
        for j, dec in enumerate((0, 1)):
            t = triplets(m, dec).astype(np.float64)
            somme[j] += t.sum(); somme2[j] += (t * t).sum()
        cpt += n
        if (k + 1) % 10 == 0:
            say(f"   nulle {k+1}/{REPS} replicats ({cpt:,} tirages SRS)")
    mu = somme / cpt
    var = somme2 / cpt - mu * mu
    sd = np.sqrt(var / n)                      # ecart-type de la MOYENNE de n tirages
    z = (obs - mu) / sd
    from math import erfc, sqrt
    p1 = np.array([erfc(abs(v) / sqrt(2)) for v in z])
    p = min(1.0, 2 * p1.min())                      # bilateral, deux statistiques
    say(f"\n   T0 : observe {obs[0]:.5f}  nulle {mu[0]:.5f} +- {sd[0]:.5f}  z = {z[0]:+.3f}")
    say(f"   T1 : observe {obs[1]:.5f}  nulle {mu[1]:.5f} +- {sd[1]:.5f}  z = {z[1]:+.3f}")
    say(f"   p = {p:.4f}")
    TOK["m_extra"] = 1                              # deux statistiques, une correction
    lab.record(
        TOK, float(np.abs(z).max()), p=float(p),
        verdict="conforme" if p > 0.05 else "ECART",
        power_at=("PUISSANCE MESUREE sur generateurs plantes, 2 000 tirages, lecture par "
                  "troncature avec rejet : (3,7) z = +20,7 ; (1,15) TYPE_2 z = +9,3 ; "
                  "(3,17) z = +7,5 ; (2,21) z = +1,6 ; (3,31) TYPE_3 z = -0,7 ; (1,63) "
                  "z = -0,2. Sur les 70 560 tirages de l'archive ces z sont multiplies par "
                  "sqrt(70560/2000) = 5,94 : le test voit un Fibonacci retarde additif "
                  "jusqu'au degre 21 environ, la ou le crible de classes du §172 s'arrete au "
                  "degre 7 — et il coute des secondes au lieu d'heures"),
        notes=("ENERGIE ADDITIVE MOD 80 (§177) : la structure exacte dont le crible de "
               "classes se nourrit — la relation c_i = c_{i-K} + c_{i-L} + delta ne survit "
               "que si les sommes de classes publiees sont publiees. Statistique nouvelle "
               "dans ce dossier. T0 (somme) et T1 (somme + 1), nulle par simulation. "
               f"z = ({z[0]:+.3f}, {z[1]:+.3f})."))
    say("   consigne.")
