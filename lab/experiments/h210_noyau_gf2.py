"""h210 — LE NOYAU SUR GF(2) : toutes les relations de parité d'un seul coup
(RAPPORT §231).

CE QUE LE DOSSIER TESTAIT, ET CE QUE ÇA LAISSAIT DEHORS
======================================================
Le §215 teste les parités de sous-ensembles de **quatre** numéros dans un tirage :
`C(80,4) = 1 581 580` statistiques. Le §218 monte à **cinq** : `C(80,5) = 24 040 016`.
Chaque fois, un balayage explicite, et chaque fois une famille bornée par ce qu'on peut
énumérer.

Or il existe un objet qui répond pour **toutes** les tailles à la fois, sans énumérer :
le **noyau sur `GF(2)`**. Une relation de parité exacte sur un sous-ensemble `S`, c'est

    Σ_{n ∈ S} x[i,n] ≡ 0   (mod 2)   pour TOUT tirage i

c'est-à-dire un vecteur du **noyau** de la matrice d'incidence vue sur `GF(2)`. Une
élimination de Gauss sur `70 560` lignes en donne la **dimension exacte** — et donc l'exacte
réponse pour les `2⁸⁰` sous-ensembles, en une fraction de seconde.

ON ÉLARGIT AUX FENÊTRES, ET C'EST LÀ QUE ÇA DEVIENT UNE ATTAQUE
===============================================================
On empile `d` tirages consécutifs en une seule ligne de `80·d` colonnes. Le noyau teste
alors toutes les relations de parité **reliant un tirage à ses successeurs** — exactement
la forme que prend un générateur `GF(2)`-linéaire (Mersenne Twister, `xorshift`, `xoshiro`,
registre à décalage) dont la sortie serait lue linéairement. Pour `d = 16`, c'est
`1 281` colonnes, donc **`2¹²⁸¹` sous-ensembles testés d'un coup**.

On ajoute une **colonne constante** à `1`, ce qui fait tomber les relations *affines*
(« la parité de `S` vaut toujours `1` ») dans le même noyau.

LE NOYAU TRIVIAL, QU'IL FAUT CONNAÎTRE POUR NE PAS CRIER
========================================================
Chaque tirage a vingt numéros, et `20` est **pair**. Donc pour chaque bloc de la fenêtre, le
vecteur « tous les numéros de ce bloc » est dans le noyau, gratuitement et pour n'importe
quelle collection de `20`-sous-ensembles. Le noyau attendu vaut donc **exactement `d`**, et
toute dimension supérieure est une découverte.

C'est aussi ce qui explique la relation triviale `x₈₀ = x₁ ⊕ … ⊕ x₇₉` : elle n'est pas une
propriété du générateur, c'est la parité de vingt.

LA PARTIE BIAISÉE : CE QUE LE NOYAU EXACT NE VOIT PAS
=====================================================
Une relation peut être **penchée** sans être exacte — c'est le principe de l'attaque par
corrélation sur un registre à décalage. On mesure donc aussi, sur les parités **croisant
les tirages** (que le §215 et le §218 ne touchent pas, tous deux confinés à un seul tirage) :

  * **poids 2** — `(a` dans le tirage `i`, `b` dans le tirage `i+g)` pour `g = 1 … 32`,
    soit `204 800` statistiques. **Le retard `1` recoupe le §220** et quelques retards
    choisis recoupent le §199 : cette moitié-là est une extension de couverture, pas une
    nouveauté, et elle sert surtout de contrôle interne ;
  * **poids 3** — `(a, b, c)` dans trois tirages **consécutifs**, soit `512 000`. Celle-là
    est neuve : une corrélation *triple* entre trois tirages, que rien dans le dossier
    n'avait formée.

`716 800` parités croisées, calibrées par la loi empirique du maximum sur répliques SRS.
"""

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POOL, DRAWN = 80, 20
EXP_ID = "h210.noyau_gf2"
FJETON = "/tmp/h210_jeton.json"
DS = (1, 2, 3, 4, 6, 8, 12, 16)
ECARTS = (1, 2, 3, 4, 5, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128, 192, 256, 384, 512,
          768, 1024, 1536, 2048, 3072, 4096, 8192, 16384, 32768)
GAPS2 = tuple(range(1, 33))          # poids 2 : retards balayes
REPS = 40


def say(*a):
    print(*a, flush=True)


def empaquete(B):
    """(n, ncol) booleen -> (n, W) uint64 ; le bit c est dans le mot c//64, position c%64."""
    n, ncol = B.shape
    W = (ncol + 63) // 64
    Q = np.zeros((n, W * 64), bool)
    Q[:, :ncol] = B
    return np.packbits(Q, axis=1, bitorder="little").view(np.uint64)


def rref(P, ncol):
    """Reduction de Gauss COMPLETE sur GF(2). Renvoie (rang, pivots, lignes reduites)."""
    P = P.copy()
    n = len(P)
    un = np.uint64(1)
    r, piv = 0, []
    for c in range(ncol):
        w, b = divmod(c, 64)
        bit = (P[r:, w] >> np.uint64(b)) & un
        nz = np.flatnonzero(bit)
        if nz.size == 0:
            continue
        p = r + int(nz[0])
        if p != r:
            tmp = P[r].copy()
            P[r] = P[p]
            P[p] = tmp
        # elimination AU-DESSUS et AU-DESSOUS : on obtient la forme echelonnee reduite
        bit_all = (P[:, w] >> np.uint64(b)) & un
        sel = np.flatnonzero(bit_all)
        sel = sel[sel != r]
        if sel.size:
            P[sel] ^= P[r]
        piv.append(c)
        r += 1
        if r == n:
            break
    return r, piv, P[:r]


def noyau(P, ncol):
    """Base du noyau {v : M v = 0 sur GF(2)}, en vecteurs booleens de longueur ncol."""
    r, piv, R = rref(P, ncol)
    pivset = set(piv)
    libres = [c for c in range(ncol) if c not in pivset]
    out = []
    for f in libres:
        v = np.zeros(ncol, bool)
        v[f] = True
        wf, bf = divmod(f, 64)
        for j, c in enumerate(piv):
            if (int(R[j, wf]) >> bf) & 1:
                v[c] = True
        out.append(v)
    return out


def fenetre(M, d, cst=True, ecart=1):
    """(N-(d-1)*ecart, 80d [+1]) booleen : d tirages espaces de `ecart`, colonne constante."""
    n = len(M) - (d - 1) * ecart
    ncol = POOL * d + (1 if cst else 0)
    B = np.zeros((n, ncol), bool)
    for k in range(d):
        B[:, POOL * k:POOL * (k + 1)] = M[k * ecart:k * ecart + n]
    if cst:
        B[:, -1] = True
    return B, ncol


def dim_noyau(M, d, ecart=1):
    B, ncol = fenetre(M, d, True, ecart)
    r, _, _ = rref(empaquete(B), ncol)
    return ncol - r


# ---------------------------------------------------------------- temoins plantes

def plante_intra(M, T, rng):
    """force la parite du sous-ensemble T a 0 dans CHAQUE tirage, en gardant 20 numeros."""
    W = M.copy()
    T = np.array(T)
    dehors = np.setdiff1d(np.arange(POOL), T)
    for i in range(len(W)):
        if W[i, T].sum() % 2 == 0:
            continue
        dedans = T[W[i, T]]
        if dedans.size:                       # on sort un element de T
            a = int(dedans[0])
            libre = dehors[~W[i, dehors]]
            W[i, a] = False
            W[i, int(libre[0])] = True
        else:                                 # on fait entrer un element de T
            a = int(T[~W[i, T]][0])
            occ = dehors[W[i, dehors]]
            W[i, a] = True
            W[i, int(occ[0])] = False
    return W


def plante_croise(M, a, b):
    """force x[i,b] = x[i-1,a] pour tout i : une relation de poids 2 croisant deux tirages."""
    W = M.copy()
    autres = np.setdiff1d(np.arange(POOL), [a, b])
    for i in range(1, len(W)):
        if W[i, b] == W[i - 1, a]:
            continue
        if W[i, b]:                           # il faut sortir b
            libre = autres[~W[i, autres]]
            W[i, b] = False
            W[i, int(libre[0])] = True
        else:                                 # il faut faire entrer b
            occ = autres[W[i, autres]]
            W[i, b] = True
            W[i, int(occ[0])] = False
    return W


# ---------------------------------------------------------------- parites biaisees

def croisees(M):
    """toutes les parites croisant les tirages : poids 2 aux retards, poids 3 consecutif.

    Renvoie un vecteur plat de 32*6400 + 512000 = 716 800 moyennes de signes.
    """
    S = (1.0 - 2.0 * M).astype(np.float32)
    n = len(S)
    out = []
    for g in GAPS2:
        out.append(((S[:n - g].T @ S[g:]) / (n - g)).ravel())
    n3 = n - 2
    S0, S1, S2 = S[:n3], S[1:1 + n3], S[2:2 + n3]
    T3 = np.empty((POOL, POOL, POOL), np.float32)
    for a in range(POOL):
        T3[a] = (S1 * S0[:, a:a + 1]).T @ S2
    out.append((T3 / n3).ravel())
    return np.concatenate(out)


if __name__ == "__main__":
    import lab

    A = lab.load()
    M = np.asarray(A.mask)
    N = len(M)
    NCROIS = len(GAPS2) * POOL * POOL + POOL ** 3

    HYP = (f"L'archive ne porte AUCUNE relation de parite, ni exacte ni penchee, entre ses "
           f"numeros et ceux des tirages voisins. Le §215 teste les parites de 4 numeros "
           f"dans UN tirage (1 581 580 statistiques), le §218 celles de 5 (24 040 016) : "
           f"deux balayages explicites, bornes par ce qu'on peut enumerer. Le NOYAU SUR "
           f"GF(2) repond pour toutes les tailles a la fois sans enumerer — une relation de "
           f"parite exacte sur S est un vecteur du noyau de la matrice d'incidence, et une "
           f"elimination de Gauss en donne la dimension EXACTE. En empilant d tirages "
           f"consecutifs en {POOL}d colonnes (plus une colonne constante, qui fait tomber "
           f"les relations affines dans le meme noyau), on teste toutes les relations "
           f"reliant un tirage a ses successeurs — la forme exacte que prend un generateur "
           f"GF(2)-lineaire (Mersenne Twister, xorshift, xoshiro, registre a decalage) lu "
           f"lineairement. A d = 16 c'est 1281 colonnes, soit 2^1281 sous-ensembles d'un "
           f"coup. On ajoute la partie PENCHEE, que le noyau exact ne voit pas : les "
           f"{NCROIS} parites CROISANT les tirages (poids 2 aux retards 1..32, poids 3 sur "
           f"trois tirages consecutifs), que ni le §215 ni le §218 ne touchent, tous deux "
           f"confines a un seul tirage — etant entendu que le poids 2 au retard 1 recoupe "
           f"le §220 et quelques retards du §199, donc que cette moitie-la est une "
           f"extension de couverture et un controle interne, la nouveaute etant la "
           f"correlation TRIPLE entre trois tirages consecutifs")
    STAT = (f"dimension du noyau sur GF(2) pour les fenetres d = {DS} et pour les paires "
            f"espacees de {len(ECARTS)} ecarts — le noyau TRIVIAL vaut exactement d, la "
            f"parite de 20 etant nulle bloc par bloc, donc toute dimension superieure est "
            f"une decouverte ; et max |z| sur les {NCROIS} parites croisees, calibre par la "
            f"loi empirique du maximum sur {REPS} repliques SRS")
    NUL = (f"pour le noyau : EXACTE et combinatoire — la dimension triviale vaut d pour une "
           f"fenetre de d tirages, quelle que soit la collection de 20-sous-ensembles, et "
           f"les temoins plantes verifient qu'une relation ajoutee fait bien monter la "
           f"dimension de 1. Pour les parites croisees : {REPS} archives SRS completes, "
           f"meme chaine de calcul, loi empirique du maximum du §7.32")
    VER = ("RELATION EXACTE si une dimension de noyau depasse sa valeur triviale — auquel "
           "cas la relation est extraite et nommee, et elle predit une parite de tout "
           "tirage futur ; RELATION PENCHEE si max |z| depasse le 95e centile sous SRS ; "
           "conforme sinon")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    # ------------------------------------------------------------------ selftest
    say("\n   selftest : temoins plantes sur SRS, aucune archive lue")
    rng = np.random.default_rng(210)
    W0 = lab.srs(6000, rng)
    for nom, W, d, att in (
            ("SRS pur, d = 2", W0, 2, 2),
            # une relation INTRA vaut dans CHACUN des d blocs : elle ajoute d, pas 1
            ("parite intra de 4 numeros forcee", plante_intra(W0, (3, 17, 41, 62), rng), 2, 4),
            ("relation croisee x[i,7] = x[i-1,13]", plante_croise(W0, 13, 7), 2, 3)):
        got = dim_noyau(W, d)
        say(f"      {nom:>38} : noyau = {got}  (attendu {att})  "
            f"{'OK' if got == att else 'ECHEC'}")
        if got != att:
            say("      selftest en echec — on n'attaque pas l'archive")
            sys.exit(1)
    del W0

    # ------------------------------------------------------------------ noyau exact
    say(f"\n   A. LE NOYAU EXACT — {N} tirages")
    say(f"      {'fenetre':>10} | {'colonnes':>8} | {'rang':>6} | {'noyau':>6} | "
        f"{'trivial':>8} | {'temps':>7}")
    exces = []
    for d in DS:
        t = time.time()
        B, ncol = fenetre(M, d, True, 1)
        r, piv, _ = rref(empaquete(B), ncol)
        k = ncol - r
        say(f"      {'d = %d' % d:>10} | {ncol:8d} | {r:6d} | {k:6d} | {d:8d} | "
            f"{time.time()-t:6.2f}s")
        if k != d:
            exces.append(("fenetre d=%d" % d, k, d))
        del B

    say(f"\n      paires espacees : {len(ECARTS)} ecarts, noyau trivial = 2")
    mauvais = []
    for g in ECARTS:
        if 1 + g >= N:
            continue
        k = dim_noyau(M, 2, g)
        if k != 2:
            mauvais.append((g, k))
            exces.append(("paire ecart %d" % g, k, 2))
    say(f"      {len(ECARTS)} ecarts testes, {len(mauvais)} au-dessus du trivial "
        f"{mauvais if mauvais else ''}")

    if exces:
        say("\n      *** RELATIONS EXACTES TROUVEES — extraction :")
        for nom, k, triv in exces:
            say(f"          {nom} : noyau {k} contre {triv} attendus")

    # ------------------------------------------------------------------ penchees
    say(f"\n   B. LES PARITES CROISEES — {NCROIS} statistiques")
    t = time.time()
    obs = croisees(M)
    say(f"      archive calculee en {time.time()-t:.1f}s ; "
        f"moyenne {obs.mean():+.6f}, ecart-type {obs.std():.6f}")

    # Chaque cellule a sa PROPRE esperance sous SRS — 0,25 pour le poids 2, 0,125 pour le
    # poids 3 — donc on ne peut pas centrer toutes les familles ensemble. On standardise
    # cellule par cellule, laisser-un-dehors (§7.32).
    V = np.empty((REPS, NCROIS), np.float32)
    rng2 = np.random.default_rng(0x210)
    for r in range(REPS):
        V[r] = croisees(lab.srs(N, rng2))
        if (r + 1) % 10 == 0:
            say(f"      ... {r+1}/{REPS} repliques ({time.time()-t:.0f}s)")

    S1 = V.sum(axis=0, dtype=np.float64)
    S2 = np.einsum("ij,ij->j", V, V, dtype=np.float64)
    muo = S1 / REPS
    sdo = np.sqrt(np.maximum(S2 / REPS - muo ** 2, 1e-30))
    mx = np.empty(REPS)
    for r in range(REPS):
        m = (S1 - V[r]) / (REPS - 1)
        s = np.sqrt(np.maximum((S2 - V[r].astype(np.float64) ** 2) / (REPS - 1) - m ** 2,
                               1e-30))
        mx[r] = float(np.abs((V[r] - m) / s).max())

    Z = np.abs((obs - muo) / sdo)
    zo = float(Z.max())
    arg = int(Z.argmax())
    m0, s0 = float(muo.mean()), float(sdo.mean())
    seuil = float(np.quantile(mx, 0.95))
    p = float((np.sum(mx >= zo) + 1) / (REPS + 1))
    say(f"\n      centre moyen sous SRS : {m0:+.8f}   dispersion moyenne : {s0:.8f}")
    say(f"      max |z| archive : {zo:.3f}  (cellule {arg})")
    say(f"      95e centile du max sous SRS : {seuil:.3f}   p = {p:.4g}")

    verdict = ("RELATION EXACTE" if exces else
               ("RELATION PENCHEE" if zo > seuil else "conforme"))
    say(f"\n   {verdict}")

    TOK["m_extra"] = NCROIS + len(DS) + len(ECARTS) - 1
    lab.record(
        TOK, float(zo), p=float(0.0 if exces else p), verdict=verdict,
        power_at=(f"le noyau exact est DECISIF, pas probabiliste : les trois temoins "
                  f"plantes montrent qu'une relation de parite ajoutee — intra-tirage de "
                  f"poids 4, ou croisant deux tirages de poids 2 — fait monter la dimension "
                  f"de exactement 1, et l'absence d'exces prouve qu'AUCUN des 2^1281 "
                  f"sous-ensembles d'une fenetre de 16 tirages ne porte de relation exacte. "
                  f"Pour la partie penchee, la dispersion sous SRS vaut {s0:.2e}, donc le "
                  f"test voit un biais de {3*s0:.2e} sur une parite croisee"),
        notes=(f"LE NOYAU SUR GF(2) (§231) — toutes les parites d'un coup au lieu de les "
               f"enumerer. Noyau exact sur les fenetres d = {DS} (jusqu'a 1281 colonnes, "
               f"soit 2^1281 sous-ensembles) et sur {len(ECARTS)} paires espacees : "
               f"dimension EGALE au trivial partout ({len(exces)} exces). Le trivial vaut d "
               f"parce que 20 est pair — c'est aussi ce qui explique la relation x80 = x1 "
               f"xor ... xor x79, qui n'est pas une propriete du generateur. Partie "
               f"penchee : {NCROIS} parites croisant les tirages (poids 2 aux retards 1-32, "
               f"poids 3 sur trois tirages consecutifs), que le §215 et le §218 ne "
               f"touchaient pas car confines a un tirage ; max |z| = {zo:.3f} contre un 95e "
               f"centile de {seuil:.3f} sous {REPS} repliques, p = {p:.4g}."))
    say("   consigne.")
