"""h170 — le détecteur d'énergie **converti en prédicteur**, et mesuré en marche avant sur
l'archive (RAPPORT §185).

CE QUI CHANGE PAR RAPPORT AUX §177-§184
=======================================
Les six détecteurs répondent à « y a-t-il une trace ? ». Ils ne répondent pas à « quels
numéros sortiront ? ». Ce fichier fait la conversion, et c'est une conversion naturelle :
si un mot vaut `r_i = r_{i-K} + r_{i-L}`, alors sa classe vaut `c_{i-K} + c_{i-L} + δ`, donc
**les classes du tirage à venir sont des sommes de classes déjà publiées**.

D'où un score, pour chaque numéro `v` candidat au tirage `t` :

    S_t(v) = # { (u,w) dans C_{t-g1} x C_{t-g2} : u + w + δ = v - 1 (mod 80) }
             sommé sur les couples (g1,g2) retenus et sur δ dans {0,1}

On ordonne les quatre-vingts numéros par `S_t` décroissant, on prend les vingt premiers,
et l'on compte le recouvrement avec le tirage réel. C'est une PRÉDICTION, faite en marche
avant — le score du tirage `t` n'utilise que des tirages d'indice strictement inférieur.

LA NULLE EST EXACTE
===================
Sous SRS, vingt numéros choisis sans regarder recouvrent le tirage suivant de
`20 x 20 / 80 = 5` numéros en moyenne, avec une variance hypergéométrique

    Var = 20 * (20/80) * (60/80) * (60/79) = 2,8481 ,   ecart-type 1,6876

et sur `n` tirages l'écart-type de la moyenne vaut `1,6876/racine(n)`. Aucune simulation :
la loi du recouvrement de deux sous-ensembles de vingt parmi quatre-vingts est
hypergéométrique, point.

CE QUE LE TÉMOIN DOIT MONTRER
=============================
Sur un générateur additif planté, le score doit MARCHER — sinon la mesure sur l'archive ne
voudrait rien dire. C'est le rôle de `--temoin`.
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import h164_energie_signee as S                                        # noqa: E402

POOL, DRAWN = 80, 20
M32 = 1 << 32
EXP_ID = "h170b.predicteur_energie"
FJETON = "/tmp/h170b_jeton.json"
# Couples de décalages STRICTEMENT dans le passé. Le `0` est INTERDIT : un couple
# (g, 0) fait entrer `m[t]` — le tirage que l'on prédit — dans son propre score. C'est
# ce que faisait la première version, et cela ne se voyait PAS sur la moyenne (5,00164,
# z = +0,26) mais sur la QUEUE : 555 tirages à dix numéros ou plus contre 334,6 attendus,
# soit +12,1 écarts-types. Une fuite ne déplace pas toujours la moyenne ; elle épaissit
# la loi. C'est pourquoi on vérifie la LOI entière et pas seulement son centre.
COUPLES = [(1, 1), (2, 1), (2, 2), (3, 1), (3, 2), (3, 3),
           (4, 1), (4, 2), (4, 3), (4, 4)]
SD1 = float(np.sqrt(DRAWN * (DRAWN / POOL) * ((POOL - DRAWN) / POOL)
                    * ((POOL - DRAWN) / (POOL - 1))))


def say(*a):
    print(*a, flush=True)


def scores(m, t, couples):
    """S_t(v) pour les quatre-vingts numéros, à partir des tirages < t seulement."""
    s = np.zeros(POOL, np.float64)
    for g1, g2 in couples:
        if t - g1 < 0 or t - g2 < 0:
            continue
        A = m[t - g1].astype(np.float64)
        B = m[t - g2].astype(np.float64)
        conv = np.rint(np.fft.irfft(np.fft.rfft(A) * np.fft.rfft(B), n=POOL)).astype(np.int64)
        for d in (0, 1):
            s += np.roll(conv, d)
    return s


def marche_avant(m, couples, debut=5, pas=1):
    """recouvrement du top-20 avec le tirage reel, tirage par tirage."""
    rec = []
    for t in range(debut, len(m), pas):
        sc = scores(m, t, couples)
        # departage stable : on prend les vingt plus grands scores
        top = np.argpartition(-sc, DRAWN)[:DRAWN]
        rec.append(int(m[t][top].sum()))
    return np.array(rec)


def plante(n, graine, K, L, signe=1):
    import random
    rng = random.Random(graine)
    r = [rng.randrange(M32) for _ in range(max(80, L + 1))]
    i = len(r)
    m = np.zeros((n, POOL), bool)
    for j in range(n):
        vus = set()
        while len(vus) < DRAWN:
            r.append((r[i - K] + signe * r[i - L]) % M32)
            i += 1
            vus.add((r[i - 1] * POOL) >> 32)
        m[j, list(vus)] = True
    return m


if __name__ == "__main__":
    import lab

    if "--temoin" in sys.argv:
        n = int(sys.argv[sys.argv.index("--nb") + 1]) if "--nb" in sys.argv else 3000
        say(f"h170 --temoin : {n} tirages plantes, aucune donnee reelle")
        say(f"   nulle exacte : recouvrement moyen 5, ecart-type par tirage {SD1:.4f}")
        say(f"{'generateur':>26} | {'recouvrement':>12} | {'z':>8}")
        rng = np.random.default_rng(61)
        for nom, m in (("SRS (controle)", S.srs(n, rng)),
                       ("additif (3,7)", plante(n, 11, 3, 7)),
                       ("additif (1,15) TYPE_2", plante(n, 12, 1, 15)),
                       ("additif (3,31) TYPE_3", plante(n, 13, 3, 31)),
                       ("soustractif (24,55)", plante(n, 14, 24, 55, -1))):
            rec = marche_avant(m, COUPLES)
            z = (rec.mean() - 5.0) / (SD1 / np.sqrt(len(rec)))
            say(f"{nom:>26} | {rec.mean():12.4f} | {z:+8.2f}")
        sys.exit(0)

    if "--archive" not in sys.argv:
        print(__doc__)
        sys.exit(0)

    HYP = ("Le predicteur d'energie — vingt numeros choisis en marche avant par le score "
           "S_t(v) = #{(u,w) dans C_{t-g1} x C_{t-g2} : u+w+delta = v-1}, somme sur les dix "
           "couples de decalages g1 >= g2 >= 1 (STRICTEMENT passes) et delta dans {0,1} — ne "
           "bat pas le hasard sur "
           "l'archive : son recouvrement moyen avec le tirage reel vaut 5, la valeur "
           "hypergeometrique, et non davantage. C'est la conversion en PREDICTEUR des "
           "detecteurs des §177 a §184, et la premiere fois que la theorie de l'energie est "
           "mise a produire des numeros plutot qu'a repondre oui ou non")
    STAT = ("R = recouvrement moyen entre les vingt numeros predits et le tirage reel, sur "
            "les 70 555 tirages d'indice >= 5 ; z = (R - 5) / (1,6876/racine(n)). Marche "
            "avant STRICTE : le score du tirage t n'utilise que des tirages d'indice < t, "
            "aucun couple n'ayant de decalage nul. La LOI entiere du recouvrement est "
            "verifiee en plus de sa moyenne")
    NUL = ("Exacte, aucune simulation : le recouvrement de deux sous-ensembles de vingt "
           "parmi quatre-vingts est hypergeometrique, de moyenne 5 et de variance "
           "20*(20/80)*(60/80)*(60/79) = 2,8481, soit un ecart-type de 1,6876 par tirage")
    VER = "conforme si |z| < 3 ; PREDICTION si z > 3 (le predicteur bat le hasard)"

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    A = lab.load()
    M = np.asarray(A.mask)
    say(f"h170 : marche avant sur {len(M)} tirages, {len(COUPLES)} couples")
    rec = marche_avant(M, COUPLES)
    n = len(rec)
    z = (rec.mean() - 5.0) / (SD1 / np.sqrt(n))
    from math import erfc, sqrt
    p = float(erfc(abs(z) / sqrt(2)))
    say(f"\n   {n} tirages predits")
    say(f"   recouvrement moyen : {rec.mean():.5f}   (nulle exacte : 5, ecart-type de la "
        f"moyenne {SD1/np.sqrt(n):.5f})")
    say(f"   z = {z:+.3f}   p = {p:.4f}")
    # la LOI entiere, pas seulement la moyenne : c'est ce qui a revele la fuite
    from math import comb
    P = [comb(DRAWN, k) * comb(POOL - DRAWN, DRAWN - k) / comb(POOL, DRAWN)
         for k in range(DRAWN + 1)]
    say(f"   distribution : min {rec.min()}, max {rec.max()}")
    say(f"{'k':>4} | {'observe':>8} | {'attendu':>9} | {'z':>7}")
    khi = 0.0
    for k in range(0, 14):
        o = int((rec == k).sum()); a = n * P[k]
        if a > 5:
            zk = (o - a) / np.sqrt(a * (1 - P[k])); khi += zk * zk
            say(f"{k:4d} | {o:8d} | {a:9.1f} | {zk:+7.2f}")
    o = int((rec >= 10).sum()); a = n * sum(P[10:])
    say(f"  >=10 | {o:8d} | {a:9.1f} | {(o-a)/np.sqrt(a*(1-sum(P[10:]))):+7.2f}")
    TOK["m_extra"] = 0
    lab.record(
        TOK, float(rec.mean()), p=p,
        verdict="PREDICTION" if z > 3 else "conforme",
        power_at=("temoins plantes, 3 000 tirages : le meme predicteur, sur un additif (3,7), "
                  "monte a un recouvrement bien au-dessus de 5 — voir --temoin. Sur "
                  "70 555 tirages l'ecart-type de la moyenne vaut 0,00635, donc un avantage "
                  "de 0,02 numero par tirage serait vu a plus de trois ecarts-types"),
        notes=("PREDICTEUR D'ENERGIE (§185) : la conversion des detecteurs en producteur de "
               "numeros. Marche avant stricte, nulle hypergeometrique EXACTE (moyenne 5, "
               f"ecart-type 1,6876 par tirage). Recouvrement mesure {rec.mean():.5f} sur "
               f"{n} tirages, z = {z:+.3f}."))
    say("   consigne.")
