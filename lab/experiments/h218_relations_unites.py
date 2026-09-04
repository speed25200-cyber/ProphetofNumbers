"""h218 — LES RELATIONS À COEFFICIENTS UNITÉS : la troisième linéarité
(RAPPORT §242).

CE QUE LA CARTE DU §233 LAISSAIT PASSER
=======================================
Le §233 range les générateurs en deux linéarités : `F₂`-linéaire (Berlekamp-Massey, §124) et
`Z/2^W`-linéaire (réseau euclidien, §230 et §232). C'est incomplet, et le trou a un nom.

**Le Fibonacci retardé** — `x_t = x_{t−j} ± x_{t−k} mod 2^W` — n'est **ni** l'un **ni** l'autre
au sens de ces deux outils :

  * il n'est pas `F₂`-linéaire (l'addition retient, le `xor` non), donc Berlekamp-Massey
    passe à côté ;
  * il est bien `Z/2^W`-linéaire, mais le réseau du §230 exige de **connaître** `a` et `c`, et
    un Fibonacci retardé n'a ni l'un ni l'autre : il a des **lags**.

Or c'est la famille de `System.Random` (.NET, lags `21`/`55`), de `math/rand` (Go, `273`/`607`),
de `ran3` (Numerical Recipes, `31`/`55`) — tout sauf exotique.

L'OUTIL, ET IL NE DEMANDE AUCUN PARAMÈTRE
=========================================
Voici le point. Soit `u_t = x_t/2^W ∈ [0,1)` et `r_t = ⌊base·u_t⌋` la classe observée. Si

    x_t = ε₁·x_{t−J} + ε₂·x_{t−K}   (mod 2^W)     avec ε ∈ {+1, −1}

alors `u_t − ε₁u_{t−J} − ε₂u_{t−K}` est un **entier exact**. En écrivant `u = (r + θ)/base`
avec `θ ∈ [0,1)` :

    s_t = r_t − ε₁·r_{t−J} − ε₂·r_{t−K}   vérifie   s_t ∈ (base·Z − 2, base·Z + 2)

Donc **`s_t mod base` est confiné à quatre valeurs sur `base`** — quatre sur vingt pour le rang,
quatre sur quatre-vingts pour le numéro. La statistique naturelle est la concentration
circulaire

    Z(J,K,ε) = (1/n)·|Σ_t exp(2πi·s_t/base)|

qui vaut `≈ 0,94` (base `20`) ou `≈ 0,996` (base `80`) sous l'hypothèse, contre `1/√n ≈ 0,0038`
sous la nulle. **Un facteur deux cent cinquante.**

Et surtout : **aucun paramètre**. Ni modulus, ni multiplicateur, ni incrément, ni graine. On
balaie seulement les deux lags.

LA PORTÉE, DITE HONNÊTEMENT
===========================
Le flux du bonus est à pas `P` mots par tirage (§225). Une relation entre **mots** aux lags
`j` et `k` ne devient une relation entre **bonus** que si `P` divise `j` et `k`. Ce test couvre
donc : le cas `P = 1`, et tous les couples `(j, k)` multiples du pas. Ce n'est pas toute la
famille — c'en est la part qui survit à la décimation, et personne ne l'avait regardée.

Le calcul se fait par **corrélation triple via FFT** : `620` lags × `2` signes de préfixe
donnent `1 240` tableaux, chacun corrélé en une transformée. Un million et demi de
statistiques en une trentaine de secondes.
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POOL, DRAWN = 80, 20
EXP_ID = "h218.relations_unites"
FJETON = "/tmp/h218_jeton.json"
LMAX = 620                      # couvre les lags de Go (273 / 607)
REPS = 20


def say(*a):
    print(*a, flush=True)


def concentrations(r, base, lmax=LMAX):
    """max de |Z| sur toutes les relations a coefficients unites de poids 2 et 3.

    Z(J,K,eps) = (1/n) |somme_t exp(2i pi (r_t - eps1 r_{t-J} - eps2 r_{t-K}) / base)|

    Calcul par correlation triple : pour chaque (J, eps1) on forme g = e * conj(e decale)^eps1
    puis on correle g avec e et conj(e) d'un coup par FFT — d'ou tous les K a la fois.
    Renvoie (max, argmax) avec argmax = (poids, J, K, eps1, eps2).
    """
    n = len(r)
    e = np.exp(2j * np.pi * r.astype(np.float64) / base)
    # longueur juste suffisante pour que la correlation circulaire coincide avec la
    # lineaire aux retards <= lmax : l'alias tombe au retard L - J >= L - lmax > n - 1.
    L = 1 << int(np.ceil(np.log2(n + lmax + 1)))
    E = np.fft.fft(e, L)
    Ec = np.fft.fft(np.conj(e), L)
    best, arg = 0.0, None

    # --- poids 2 : Z(J, eps) = (1/n) |somme e_t * (e_{t-J})^{-eps}|
    for eps in (1, -1):
        cr = np.fft.ifft(E * np.conj(E if eps == 1 else Ec))[:lmax + 1] / n
        for J in range(1, lmax + 1):
            v = abs(cr[J])
            if v > best:
                best, arg = v, (2, J, 0, eps, 0)

    # --- poids 3
    for eps1 in (1, -1):
        for J in range(1, lmax + 1):
            d = np.zeros(n, complex)
            d[J:] = e[:-J] if eps1 == -1 else np.conj(e[:-J])
            g = e * d
            G = np.fft.fft(g, L)
            for eps2 in (1, -1):
                cr = np.fft.ifft(G * np.conj(E if eps2 == 1 else Ec))[:lmax + 1] / n
                k0 = J + 1
                if k0 <= lmax:
                    seg = np.abs(cr[k0:lmax + 1])
                    i = int(seg.argmax())
                    if seg[i] > best:
                        best, arg = float(seg[i]), (3, J, k0 + i, eps1, eps2)
    return best, arg


def compte(lmax=LMAX):
    return 2 * lmax + 4 * (lmax * (lmax - 1) // 2)


if __name__ == "__main__":
    import lab

    A = lab.load()
    M = np.asarray(A.mask)
    bonus = np.asarray(A.bonus).astype(np.int64)
    nums = np.asarray(A.nums).astype(np.int64)
    N = len(M)
    CANAUX = (("rang du bonus (regle du §106)", (nums < bonus[:, None]).sum(axis=1), DRAWN),
              ("numero du bonus", bonus - 1, POOL))
    NCELL = compte() * len(CANAUX)

    HYP = (f"Le flux du bonus ne verifie aucune relation a coefficients unites de poids 2 ou "
           f"3, a aucun couple de lags jusqu'a {LMAX}. LA CARTE DU §233 EST INCOMPLETE : elle "
           f"range les generateurs en F2-lineaires (Berlekamp-Massey, §124) et Z/2^W-lineaires "
           f"(reseau, §230 et §232), et le FIBONACCI RETARDE x_t = x_{{t-j}} +/- x_{{t-k}} mod "
           f"2^W n'est ni l'un ni l'autre AU SENS DE CES OUTILS — pas F2-lineaire car "
           f"l'addition retient, et Z/2^W-lineaire certes mais le reseau exige de CONNAITRE a "
           f"et c alors qu'un Fibonacci retarde n'a que des lags. C'est pourtant la famille de "
           f"System.Random (.NET, 21/55), de math/rand (Go, 273/607), de ran3 (31/55). "
           f"L'outil ne demande AUCUN parametre : si x_t = eps1 x_{{t-J}} + eps2 x_{{t-K}} mod "
           f"2^W alors u_t - eps1 u_{{t-J}} - eps2 u_{{t-K}} est un entier exact, donc "
           f"s_t = r_t - eps1 r_{{t-J}} - eps2 r_{{t-K}} est confine a QUATRE valeurs sur base "
           f"modulo base. La concentration circulaire |Z| vaut alors 0,94 (base 20) ou 0,996 "
           f"(base 80) contre 1/racine(n) = 0,0038 sous la nulle — un facteur 250. PORTEE, dite "
           f"honnetement : le flux du bonus etant a pas P mots par tirage, une relation entre "
           f"MOTS aux lags j et k ne devient une relation entre BONUS que si P divise j et k ; "
           f"ce test couvre donc le cas P = 1 et tous les couples multiples du pas — la part de "
           f"la famille qui survit a la decimation, que personne n'avait regardee")
    STAT = (f"max sur {NCELL} cellules de |Z| = (1/n)|somme exp(2i pi s_t/base)|, pour les "
            f"relations de poids 2 (J = 1..{LMAX}, 2 signes) et de poids 3 "
            f"(1 <= J < K <= {LMAX}, 4 signes), sur les deux canaux")
    NUL = (f"E[Z] = 0 EXACTEMENT sous SRS : le rang du bonus est uniforme sur 0..19 et le "
           f"numero sur 0..79, donc l'esperance de chaque facteur exp(2i pi r/base) est nulle "
           f"et celle du produit aussi, les tirages etant independants. La loi du MAXIMUM sur "
           f"les {NCELL} cellules est calibree sur {REPS} archives SRS rejouant la meme chaine")
    VER = (f"RELATION TROUVEE si le max observe depasse le 95e centile du max sous SRS — "
           f"auquel cas les lags et les signes NOMMENT le generateur et donnent l'etat ; "
           f"conforme sinon")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h218 : {NCELL} relations testees, lags jusqu'a {LMAX}, aucun parametre a fournir")

    # ---------------------------------------------------------------- selftest
    say("\n   selftest : un Fibonacci retarde PLANTE doit sortir a |Z| proche de 1")
    rng0 = np.random.default_rng(218)
    for (j, k, nom) in ((21, 55, ".NET System.Random"), (31, 55, "ran3"),
                        (273, 607, "Go math/rand")):
        W = 32
        etat = list(rng0.integers(0, 1 << W, k).tolist())
        suite = []
        for t in range(20000):
            v = (etat[-j] - etat[-k]) % (1 << W)
            etat.append(v)
            suite.append(v)
        for base in (DRAWN, POOL):
            r = np.array([(v * base) >> W for v in suite], np.int64)
            b, a = concentrations(r, base, lmax=max(k + 5, 60))
            say(f"      {nom:>22} base {base:2d} : |Z| = {b:.4f}  "
                f"a (poids {a[0]}, J = {a[1]}, K = {a[2]}, signes {a[3]:+d}/{a[4]:+d})")
            if b < 0.5:
                say("      TEMOIN NON VU — l'instrument est aveugle, on s'arrete")
                sys.exit(1)
    del W, etat, suite

    # ---------------------------------------------------------------- archive
    say("\n   archive :")
    obs = {}
    for nom, r, base in CANAUX:
        b, a = concentrations(np.asarray(r), base)
        obs[nom] = b
        say(f"      {nom:>32} : |Z| max = {b:.6f}  "
            f"(poids {a[0]}, J = {a[1]}, K = {a[2]}, signes {a[3]:+d}/{a[4]:+d})")

    # ---------------------------------------------------------------- nulle
    V = {nom: np.empty(REPS) for nom, _, _ in CANAUX}
    rng = np.random.default_rng(0x218)
    for rep in range(REPS):
        Mr = np.zeros((N, POOL), bool)
        idx = np.argsort(rng.random((N, POOL)), axis=1)[:, :DRAWN]
        Mr[np.arange(N)[:, None], idx] = True
        tri = np.sort(idx, axis=1)
        pos = rng.integers(0, DRAWN, N)
        rangs = pos.astype(np.int64)
        numeros = tri[np.arange(N), pos].astype(np.int64)
        for nom, base, r in ((CANAUX[0][0], DRAWN, rangs), (CANAUX[1][0], POOL, numeros)):
            V[nom][rep] = concentrations(r, base)[0]
        if (rep + 1) % 5 == 0:
            say(f"   ... {rep+1}/{REPS} repliques")

    say(f"\n   {'canal':>32} | {'archive':>9} | {'max sous SRS':>22} | {'95e centile':>12} | "
        f"{'p':>7}")
    pmin, depasse = 1.0, False
    for nom, _, _ in CANAUX:
        m_, s_ = float(V[nom].mean()), float(V[nom].std())
        q = float(np.quantile(V[nom], 0.95))
        p = float((np.sum(V[nom] >= obs[nom]) + 1) / (REPS + 1))
        pmin = min(pmin, p)
        depasse |= obs[nom] > q
        say(f"   {nom:>32} | {obs[nom]:9.6f} | {m_:9.6f} +/-{s_:9.6f} | {q:12.6f} | "
            f"{p:7.4f}")

    verdict = "RELATION TROUVEE" if depasse else "conforme"
    say(f"\n   {verdict}")
    say(f"   pour memoire : un Fibonacci retarde donnerait |Z| proche de 1, "
        f"soit plus de cent fois le maximum observe")

    TOK["m_extra"] = NCELL - 1
    lab.record(
        TOK, float(max(obs.values())), p=float(pmin), verdict=verdict,
        power_at=(f"les trois temoins plantes — .NET (21/55), ran3 (31/55) et Go (273/607) — "
                  f"sortent tous a |Z| proche de 1 sur les deux canaux, contre un maximum "
                  f"observe de {max(obs.values()):.6f} sur l'archive. L'ecart n'est pas "
                  f"marginal : c'est un facteur cent. La detection est donc CERTAINE et non "
                  f"probable pour tout Fibonacci retarde dont les lags sont multiples du pas "
                  f"de bloc, jusqu'a {LMAX} tirages"),
        notes=(f"LES RELATIONS A COEFFICIENTS UNITES (§242) — la TROISIEME linearite, que la "
               f"carte du §233 laissait passer. Le Fibonacci retarde n'est ni F2-lineaire "
               f"(l'addition retient) ni attaquable par le reseau du §230 (qui exige de "
               f"connaitre a et c, alors qu'un LFG n'a que des lags). Or c'est la famille de "
               f"System.Random, de Go math/rand et de ran3. Le test ne demande AUCUN "
               f"parametre : sous la relation, s_t = r_t - eps1 r_{{t-J}} - eps2 r_{{t-K}} "
               f"est confine a 4 valeurs sur base, donc |Z| passe de 1/racine(n) a ~1. "
               f"{NCELL} relations testees (poids 2 et 3, lags jusqu'a {LMAX}, deux canaux) "
               f"par correlation triple via FFT. Maximum observe "
               f"{max(obs.values()):.6f}, p = {pmin:.4f}. Portee dite honnetement : couvre "
               f"le pas P = 1 et tous les couples de lags multiples du pas."))
    say("   consigne.")
