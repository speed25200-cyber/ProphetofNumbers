"""h198 — LA COURBE VARIANCE-TEMPS : le défaut diffus que le maximum ne peut pas voir
(RAPPORT §219).

LE TROU, ET IL EST DANS LA STATISTIQUE ELLE-MÊME
================================================
Le §194 calcule l'autocorrélation **exacte** de chaque numéro à chaque retard, jusqu'à
`35 280`, et retient le **maximum** de `|z|`. Il agrège aussi sur les quatre-vingts numéros
**à retard fixé**. Ce qu'il ne fait **jamais**, c'est agréger **sur les retards**.

Or c'est là que se cache toute une classe de défauts. Soit une corrélation diffuse
`ρ(d) = δ` pour tout `d ≤ D`. Chaque retard pris seul donne `z = δ√n`, invisible si `δ` est
petit. Mais la variance d'une somme sur une fenêtre de `L` tirages vaut

    Var(S_L) = L·γ(0) + 2·Σ_{d=1}^{L−1} (L−d)·γ(d)

de sorte que le **facteur de Fano** `F(L) = Var(S_L)/(L·3/16)` vaut

    F(L) = 1 + δ·(L−1)      pour L ≤ D.

**Il croît linéairement avec l'échelle.** À `L = 2048`, une corrélation diffuse de
`δ = 10⁻³` — parfaitement invisible retard par retard — donne `F = 3`. La courbe
variance-temps est donc, contre ce type de défaut, plusieurs ordres de grandeur plus
puissante que le maximum sur les retards.

CE QUE ÇA VISE, ET CE N'EST PAS UNE ABSTRACTION
===============================================
C'est le mode de défaillance **classique** des vraies machines de loterie, et le dossier ne
l'avait jamais agrégé :

  * un **quota** — « chaque numéro doit sortir à peu près `n/4` fois par période » — donne
    `F < 1`, une variance **sous-poissonienne**, à l'échelle de la période et pas ailleurs ;
  * une **dérive** lente des marges donne `F > 1` croissant aux grandes échelles ;
  * un **mélange par paquets** (un réservoir rebattu tous les `k` tirages) donne un creux
    de `F` exactement à `L = k`.

Aucun de ces trois ne déplace la marge globale, aucun ne produit un pic d'autocorrélation à
un retard particulier, et **les trois seraient économiquement exploitables** : sous quota,
un numéro en retard est réellement plus probable.

TROIS FAMILLES
==============
  **A  PAR NUMÉRO ET PAR ÉCHELLE.** `F̂_i(L)` pour les `80` numéros et `21` échelles de `2`
     à `2 048`, sur fenêtres disjointes. `1 680` statistiques.

  **B  AGRÉGÉE.** `S(L) = Σ_i (F̂_i(L) − 1)/√80` à chaque échelle. `21` statistiques, et
     c'est la famille puissante : un quota commun à tous les numéros s'y somme au lieu de
     se diluer.

  **C  ALIGNÉE SUR LA NUIT.** Fenêtre = une nuit entière (`204` tirages), sur les `345`
     nuits complètes. C'est l'échelle à laquelle un quota serait implémenté si quelqu'un en
     avait implémenté un.

LA NULLE
========
Sous SRS le compte d'un numéro sur `L` tirages est binomial de paramètre `1/4` **exactement**,
donc `F = 1` exactement. Mais la famille B porte une contrainte : chaque tirage ayant
exactement vingt numéros, `Σ_i S_L,i = 20L` est **constante**, ce qui corrèle négativement
les quatre-vingts comptes et rabote la loi de `S(L)`. On calibre donc sur répliques SRS —
qui respectent la contrainte par construction — avec la loi du maximum laissée hors de sa
propre normalisation (§7.32).
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POOL, DRAWN = 80, 20
EXP_ID = "h198.courbe_variance_temps"
FJETON = "/tmp/h198_jeton.json"
REPS = 200
ECHELLES = (2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128, 192, 256, 384, 512,
            768, 1024, 1536, 2048)


def say(*a):
    print(*a, flush=True)


def fano(M, L):
    """facteur de Fano de chaque numero a l'echelle L, sur fenetres DISJOINTES."""
    nw = len(M) // L
    if nw < 8:
        return None
    C = M[:nw * L].reshape(nw, L, POOL).sum(axis=1).astype(np.float64)
    return C.var(axis=0, ddof=1) / (L * 3.0 / 16.0)


def fano_nuits(M, BOR):
    """facteur de Fano a l'echelle de la nuit, sur les nuits de longueur majoritaire."""
    lon = np.diff(BOR)
    L = int(np.bincount(lon).argmax())
    C = np.array([M[BOR[k]:BOR[k] + L].sum(axis=0) for k in range(len(lon))
                  if lon[k] >= L], np.float64)
    return C.var(axis=0, ddof=1) / (L * 3.0 / 16.0), L, len(C)


def profil(M, BOR):
    """vecteur de toutes les statistiques : A aplatie, B, puis C (par numero et agregee)."""
    A, B = [], []
    for L in ECHELLES:
        f = fano(M, L)
        A.append(f)
        B.append(float((f - 1.0).sum() / np.sqrt(POOL)))
    fn, _, _ = fano_nuits(M, BOR)
    return (np.concatenate(A), np.array(B), fn,
            float((fn - 1.0).sum() / np.sqrt(POOL)))


def vecteur(M, BOR):
    a, b, c, d = profil(M, BOR)
    return np.concatenate([a, b, c, [d]])


def nuit_a_quota(rng, L=204):
    """une nuit ou chaque numero sort EXACTEMENT L*20/80 fois : le quota parfait."""
    besoin = np.full(POOL, L * DRAWN // POOL, np.int64)
    out = np.zeros((L, POOL), bool)
    for t in range(L):
        cle = besoin * 1000 + rng.integers(0, 1000, POOL)
        pris = np.argsort(-cle)[:DRAWN]
        out[t, pris] = True
        besoin[pris] -= 1
    return out, besoin


def tirage_pondere(n, W, rng):
    """n tirages 20/80 aux poids w_i(t), par l'astuce de Gumbel (Plackett-Luce exact)."""
    G = rng.gumbel(size=(n, POOL)) + np.log(W)
    ordre = np.argpartition(-G, DRAWN, axis=1)[:, :DRAWN]
    M = np.zeros((n, POOL), bool)
    M[np.arange(n)[:, None], ordre] = True
    return M


def selftest():
    """Les seuils sont pris sur des REPLIQUES, jamais fixes a la main.

    La premiere version de ce controle exigeait de l'agregee du quota qu'elle descende
    sous `−20`. C'est impossible : `S = Σ(F−1)/√80` vaut au mieux `−√80 = −8,944` quand
    tous les `F` valent zero, c'est-a-dire quand le quota est PARFAIT. Le seuil condamnait
    donc un instrument qui marchait. Et le second temoin, cense produire une correlation
    DIFFUSE, ne produisait qu'un effet de retard 1 — il ne pouvait pas montrer la
    croissance qu'on lui demandait de montrer. Les deux fautes etaient dans les temoins.
    """
    import lab
    say("h198 --autotest : donnees synthetiques uniquement, aucune archive lue")
    rng = np.random.default_rng(198)
    NN, L, RS = 200, 204, 20
    BOR = np.arange(NN + 1) * L
    n = NN * L
    ok = True

    say(f"\n   (0) LA NULLE, calibree sur {RS} repliques SRS de {n} tirages")
    V = np.array([vecteur(lab.srs(n, rng), BOR) for _ in range(RS)])
    mu, sd = V.mean(axis=0), np.maximum(V.std(axis=0), 1e-12)
    nA, nB = POOL * len(ECHELLES), len(ECHELLES)
    a, b, c, d = profil(lab.srs(n, rng), BOR)
    say(f"       A par numero : moyenne {a.mean():.4f} (attendue 1)")
    say(f"       B agregee : moyenne des repliques {V[:, nA:nA+nB].mean():+.3f}, "
        f"ecart-type {V[:, nA:nA+nB].std():.3f}")
    say(f"       C nuit agregee : {V[:, -1].mean():+.3f} +/- {V[:, -1].std():.3f}")
    bon = abs(a.mean() - 1) < 0.02
    say(f"       -> {'NULLE CONFIRMEE' if bon else 'NULLE FAUSSE'}")
    ok &= bon

    def juge(nom, X, indices, attendu):
        z = (vecteur(X, BOR) - mu) / sd
        zz = z[indices]
        j = int(np.argmax(np.abs(zz)))
        say(f"       max |z| sur la famille visee : {zz[j]:+.1f}")
        vu = abs(zz[j]) > 6 and (zz[j] < 0) == (attendu < 0)
        say(f"       -> {nom} {'VU' if vu else 'MANQUE'}")
        return vu, z

    say("\n   (1) LE QUOTA : chaque nuit equilibree exactement -> F(204) doit s'effondrer")
    nuits, reste = [], None
    for _ in range(NN):
        nu, reste = nuit_a_quota(rng, L)
        nuits.append(nu)
    Q = np.concatenate(nuits)
    say(f"       quota atteint exactement : {'OUI' if not reste.any() else 'NON'}")
    aq, bq, cq, dq = profil(Q, BOR)
    say(f"       C nuit : F moyen {cq.mean():.4f} au lieu de 1 ; agregee {dq:+.3f} "
        f"(le plancher absolu vaut -racine(80) = {-np.sqrt(POOL):.3f})")
    vu, _ = juge("QUOTA", Q, np.arange(nA + nB, nA + nB + POOL + 1), -1)
    ok &= vu and not reste.any()

    say("\n   (2) LA CORRELATION DIFFUSE : un etat cache LENT, pas un effet de retard 1")
    #   poids sinusoidaux de longue periode : rho(d) reste non nul sur des milliers de
    #   retards, ce qui est la seule facon de faire croitre F(L) avec l'echelle.
    P, ALPHA = 12000.0, 0.06
    t = np.arange(n)[:, None]
    phi = rng.uniform(0, 2 * np.pi, POOL)[None, :]
    W = 1.0 + ALPHA * np.sin(2 * np.pi * t / P + phi)
    D = tirage_pondere(n, W, rng)
    aD, bD, cD, dD = profil(D, BOR)
    say(f"       B : echelle 2 {bD[0]:+.2f} ; 32 {bD[8]:+.2f} ; 512 {bD[16]:+.2f} ; "
        f"2048 {bD[-1]:+.2f}")
    croit = bD[-1] > 5 * max(abs(bD[0]), 0.05)
    say(f"       croissance avec l'echelle : {'OUI' if croit else 'NON'}")
    vu, _ = juge("CORRELATION DIFFUSE", D, np.arange(nA, nA + nB), +1)
    ok &= vu and croit

    say(f"\n   -> {'CALIBRE 3/3' if ok else 'DEFAILLANT'}")
    return ok


if __name__ == "__main__":
    if "--autotest" in sys.argv:
        sys.exit(0 if selftest() else 1)

    import lab

    A = lab.load()
    M = np.asarray(A.mask)
    TS = np.asarray(A.ts).astype(np.int64)
    N = len(M)
    BOR = np.r_[0, np.flatnonzero(np.diff(TS) > 1000) + 1, N]
    _, LN, NNUIT = fano_nuits(M, BOR)
    MTOT = POOL * len(ECHELLES) + len(ECHELLES) + POOL + 1

    HYP = ("La variance des comptes ne s'ecarte de la valeur poissonienne a AUCUNE echelle "
           "de temps. Le §194 calcule l'autocorrelation exacte a chaque retard et retient "
           "le MAXIMUM ; il agrege sur les quatre-vingts numeros a retard fixe, mais JAMAIS "
           "sur les retards. Or une correlation diffuse rho(d) = delta sur tous les retards "
           "courts est invisible retard par retard et donne un facteur de Fano F(L) = 1 + "
           "delta (L-1), donc CROISSANT LINEAIREMENT avec l'echelle : a L = 2048 une "
           "correlation de 1e-3 donne F = 3. C'est le mode de defaillance classique des "
           "vraies machines de loterie et le dossier ne l'avait jamais agrege — un QUOTA "
           "(« chaque numero doit sortir n/4 fois par periode ») donne F < 1 a l'echelle de "
           "la periode ; une DERIVE lente donne F > 1 croissant ; un reservoir rebattu tous "
           "les k tirages donne un creux exactement a L = k. Aucun des trois ne deplace la "
           "marge globale, aucun ne fait de pic a un retard particulier, et les trois "
           "seraient exploitables — sous quota, un numero en retard est reellement plus "
           f"probable. Trois familles : A les {POOL} numeros x {len(ECHELLES)} echelles de 2 "
           f"a 2048 sur fenetres disjointes ; B l'agregee S(L) = somme_i (F_i(L)-1)/racine(80) "
           f"a chaque echelle, ou un quota commun se somme au lieu de se diluer ; C alignee "
           f"sur la NUIT ({LN} tirages, {NNUIT} nuits), l'echelle a laquelle un quota serait "
           "implemente si quelqu'un en avait implemente un")
    STAT = (f"max |z| reduit par la loi EMPIRIQUE du maximum sur {REPS} repliques SRS, "
            f"chacune laissee hors de sa propre normalisation, sur les {MTOT} statistiques "
            f"des trois familles")
    NUL = ("Sous SRS le compte d'un numero sur L tirages est binomial de parametre 1/4 "
           "EXACTEMENT, donc F = 1 exactement. Mais la famille B porte une contrainte — "
           "chaque tirage ayant exactement vingt numeros, la somme des comptes vaut 20L et "
           "est CONSTANTE, ce qui correle negativement les quatre-vingts et rabote la loi "
           "de S(L). On calibre donc sur repliques SRS, qui respectent la contrainte par "
           "construction, plutot que sur une formule")
    VER = ("conforme si le maximum reduit reste sous le 95e centile de sa loi empirique ; "
           "STRUCTURE TEMPORELLE sinon, en precisant l'echelle et le signe — F < 1 pour un "
           "quota, F > 1 pour une derive ou une correlation diffuse")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h198 : {N} tirages ; nuits de {LN} tirages ({NNUIT} completes) ; "
        f"{MTOT} statistiques")

    obs = vecteur(M, BOR)
    a, b, c, d = profil(M, BOR)
    say(f"\nARCHIVE")
    say(f"   {'echelle':>8} | {'fenetres':>9} | {'F moyen':>9} | "
        f"{'F min':>8} | {'F max':>8} | {'B agregee':>10}")
    for j, L in enumerate(ECHELLES):
        f = a[j * POOL:(j + 1) * POOL]
        say(f"   {L:8d} | {N//L:9d} | {f.mean():9.5f} | {f.min():8.4f} | "
            f"{f.max():8.4f} | {b[j]:+10.3f}")
    say(f"   {'nuit ' + str(LN):>8} | {NNUIT:9d} | {c.mean():9.5f} | {c.min():8.4f} | "
        f"{c.max():8.4f} | {d:+10.3f}")

    V = np.empty((REPS, len(obs)))
    rng = np.random.default_rng(0x198)
    for r in range(REPS):
        V[r] = vecteur(lab.srs(N, rng), BOR)
        if (r + 1) % 50 == 0:
            say(f"   ... {r+1}/{REPS} repliques")

    s1, s2 = V.sum(axis=0), (V * V).sum(axis=0)
    mu, sd = V.mean(axis=0), V.std(axis=0)
    zobs = (obs - mu) / np.maximum(sd, 1e-12)
    o = float(np.abs(zobs).max())
    j = int(np.argmax(np.abs(zobs)))
    mx = np.empty(REPS)
    for r in range(REPS):
        m_ = (s1 - V[r]) / (REPS - 1)
        v_ = np.maximum((s2 - V[r] * V[r]) / (REPS - 1) - m_ * m_, 1e-12)
        mx[r] = float(np.abs((V[r] - m_) / np.sqrt(v_)).max())
    p = float((1 + int((mx >= o).sum())) / (1 + REPS))

    nA, nB = POOL * len(ECHELLES), len(ECHELLES)
    if j < nA:
        ou = f"A numero {j % POOL + 1} echelle {ECHELLES[j // POOL]}"
    elif j < nA + nB:
        ou = f"B agregee echelle {ECHELLES[j - nA]}"
    elif j < nA + nB + POOL:
        ou = f"C nuit, numero {j - nA - nB + 1}"
    else:
        ou = "C nuit, agregee"
    say(f"\n   max |z| = {zobs[j]:+.3f} ({ou})")
    say(f"   B agregee, z reduits : " + " ".join(
        f"{L}:{zobs[nA+i]:+.2f}" for i, L in enumerate(ECHELLES)))
    say(f"   maximum reduit {o:.3f} ; median des repliques {np.median(mx):.3f} ; "
        f"95e centile {np.percentile(mx, 95):.3f}")
    verdict = "STRUCTURE TEMPORELLE" if p <= 0.05 else "conforme"
    say(f"   p (loi empirique du maximum, {REPS} repliques) = {p:.4f}   ->   {verdict}")

    TOK["m_extra"] = MTOT - 1
    lab.record(
        TOK, o, p=p, verdict=verdict,
        power_at=("le temoin plante un QUOTA parfait — chaque nuit equilibree a 51 sorties "
                  "par numero — et la famille C s'effondre a F proche de 0, tandis qu'une "
                  "CORRELATION DIFFUSE de 5 % fait croitre la famille B avec l'echelle, "
                  "signature qu'aucun maximum sur les retards ne peut produire. C'est "
                  "precisement le gain de puissance vise : a l'echelle 2048, F(L) = 1 + "
                  "delta (L-1) transforme une correlation de 1e-3, invisible retard par "
                  "retard, en un facteur de Fano de 3"),
        notes=(f"LA COURBE VARIANCE-TEMPS (§219) — le §194 agrege sur les numeros a retard "
               f"fixe mais JAMAIS sur les retards, et manque donc toute correlation diffuse. "
               f"Le facteur de Fano F(L) = 1 + delta (L-1) l'amplifie lineairement avec "
               f"l'echelle. {MTOT} statistiques : A {POOL}x{len(ECHELLES)} echelles de 2 a "
               f"2048, B l'agregee a chaque echelle, C alignee sur la nuit ({LN} tirages, "
               f"{NNUIT} nuits). Archive : max |z| = {zobs[j]:+.3f} ({ou}) ; maximum reduit "
               f"{o:.3f} contre un 95e centile de {np.percentile(mx, 95):.3f}, p = {p:.4f}. "
               f"F moyen a l'echelle de la nuit : {c.mean():.5f}."))
    say("   consigne.")
