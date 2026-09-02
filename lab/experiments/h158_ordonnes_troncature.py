"""h158 — les tirages ORDONNES sous TRONCATURE avec rejet : le crible de classes quand
l'ordre est connu (THEORIE_ETAT §7.24 ; RAPPORT §175).

CE QUI RESTAIT OUVERT
=====================
Le §154 lit les douze tirages ordonnes des videos sous le rejet, mais par leurs BITS BAS
(echantillonneur a modulo). Le §159 les lit a pas fixe (fy, shuffle). Personne ne les a lus
sous la TRONCATURE `v = 1 + ((x * 80) >> 32)` avec rejet — le quatrieme echantillonneur, celui
que le §172 lit sur l'archive TRIEE.

CE QUE L'ORDRE CHANGE
=====================
Sur l'archive triee, le crible doit deviner la classe de chaque mot parmi les vingt publiees :
`log2 20 = 4,32` bits par mot libre, d'ou un front de `20^L` et un mur au degre 7.

Sur un tirage ORDONNE, la classe de chaque mot ACCEPTE est LUE : c'est `v - 1`, dans l'ordre.
Il ne reste a deviner que le placement des refus — environ `2,85` par tirage — et la classe
que chacun duplique. Le front ne depend plus de `L` mais du nombre de refus, et le mur du
degre disparait.

L'EQUATION EST LA MEME
======================
    c_i = c_{i-K} + c_{i-L} + delta   (mod 80),   delta dans {0, 1}

mais elle sert ici de TEST et non de generateur : a chaque position `i >= L`, les deux
candidats doivent etre soit la prochaine classe acceptee, soit une classe deja acceptee dans
le tirage courant (un refus). Sinon le chemin meurt. Elagage : `2 x (1 + a) / 80` par mot,
soit environ `1,9` bit.

LES DONNEES
===========
`lab/draws_ordered.csv` donne douze tirages, dont un seul groupe de QUATRE consecutifs
(`1381256` a `1381259`). Les autres sont espaces, et un tirage manquant coute un nombre de
mots inconnu : on ne peut donc pas les enchainer. Aucun des douze n'est dans l'archive
(verifie), donc ce crible ne prolonge pas l'archive — il teste la meme machine sur une autre
fenetre.
"""

import csv
import os
import sys
import time

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
sys.path.insert(0, os.path.join(RACINE, "experiments"))

POOL, DRAWN = 80, 20
NMAXD = 45


def say(*a):
    print(*a, flush=True)


def primitif(K, L):
    import h145_sync_rejet as H
    return H.primitif(K, L)


def lire_ordonnes(f=None):
    f = f or os.path.join(RACINE, "draws_ordered.csv")
    rows = list(csv.DictReader(open(f, encoding="utf-8")))
    out = []
    for r in rows:
        out.append((int(r["id"]), [int(r[f"o{k}"]) for k in range(1, 21)]))
    return out


def groupes_consecutifs(ordonnes):
    """suites d'identifiants CONSECUTIFS : un tirage manquant coupe la chaine."""
    g, cour = [], []
    for i, (idt, v) in enumerate(ordonnes):
        if cour and idt != cour[-1][0] + 1:
            if len(cour) > 1:
                g.append(cour)
            cour = []
        cour.append((idt, v))
    if len(cour) > 1:
        g.append(cour)
    return g


def rmax_libre(L, z=6.0):
    """borne sur le nombre de REFUS parmi les L premiers mots.

    Le mot d'indice `i` est un refus avec probabilite `a_i/80` ou `a_i` est le nombre de
    classes deja acceptees dans son tirage, donc `a_i <= i`. L'esperance vaut au plus
    `mu = L(L-1)/160` et la variance au plus `mu`. On coupe a `mu + z sqrt(mu)` : au-dela,
    le chemin vrai est perdu avec une probabilite que `z = 6` rend negligeable.
    """
    import math
    mu = L * (L - 1) / 160.0
    return int(mu + z * math.sqrt(max(mu, 1.0))) + 1


def rmax_serre(L, z=3.0):
    """meme borne, resserree : `z = 3` suffit et divise le front par plusieurs ordres."""
    import math
    mu = L * (L - 1) / 160.0
    return int(mu + z * math.sqrt(max(mu, 1.0))) + 1


def crible(tirages, K, L, delta, nmaxd=NMAXD, plafond=40_000_000, rmax=None,
           arret_premier=False):
    """DFS sur les mots. `tirages` : listes ORDONNEES de 20 valeurs 1..80.

    L'etat porte les L DERNIERES classes (et rien de plus : la relation ne regarde que les
    retards K et L). Le porter dans l'etat plutot que dans un tableau partage est ce qui
    rend la pile explicite correcte — une premiere version ecrivait dans un `hist` commun,
    et les branches s'ecrasaient les unes les autres.

    Renvoie (survivants, noeuds, coupe) ; un survivant est le L-uplet des L PREMIERES
    classes, avec sa suite complete.
    """
    cls = [[v - 1 for v in t] for t in tirages]
    nt = len(cls)
    rmax = rmax if rmax is not None else rmax_libre(L)
    surv, noeuds = [], 0
    # (i, d, j, A, wd, refus_libres, h) ou h = tuple des min(i, L) dernieres classes,
    # et chem = le debut du chemin (les L premieres classes) + la suite complete
    pile = [(0, 0, 0, frozenset(), 0, 0, (), ())]
    while pile:
        i, d, j, A, wd, rl, h, chem = pile.pop()
        noeuds += 1
        if noeuds > plafond:
            return surv, noeuds, True
        if d >= nt:
            surv.append(chem)
            if arret_premier:
                return surv, noeuds, False
            continue
        if wd + (DRAWN - j) > nmaxd:
            continue
        if i < L:
            # pile LIFO : on empile les refus d'abord pour que l'ACCEPTATION soit depilee
            # en premier — le vrai chemin est fait d'acceptations a 87 %
            cand = (sorted(A, reverse=True) if rl < rmax else []) + [cls[d][j]]
        else:
            base = h[-K] + h[0]          # c_{i-K} et c_{i-L} : h = (c_{i-L}, ..., c_{i-1})
            cand = sorted({(base + e) % POOL for e in delta})
        for c in cand:
            if c == cls[d][j]:
                nd, nj, nA, nw, nrl = d, j + 1, A | {c}, wd + 1, rl
                if nj == DRAWN:
                    nd, nj, nA, nw = d + 1, 0, frozenset(), 0
            elif c in A:
                nd, nj, nA, nw = d, j, A, wd + 1
                nrl = rl + (1 if i < L else 0)
            else:
                continue
            nh = (h + (c,))[-L:]
            pile.append((i + 1, nd, nj, nA, nw, nrl, nh, chem + (c,)))
    return surv, noeuds, False


def temoin(K, L, shift=0, ntir=6, graine=31415):
    """une suite plantee, lue par troncature avec rejet, gardee ORDONNEE."""
    import random
    M32 = 1 << 32
    rng = random.Random(graine)
    r = [rng.randrange(M32) for _ in range(L)]
    i = L
    W = 1 << (32 - shift)
    tir = []
    for _ in range(ntir):
        vus, ordre = set(), []
        while len(vus) < DRAWN:
            r.append((r[i - K] + r[i - L]) % M32); i += 1
            c = ((r[i - 1] >> shift) * POOL) // W
            if c not in vus:
                vus.add(c); ordre.append(c + 1)
        tir.append(ordre)
    return tir


if __name__ == "__main__":
    DELTA = (0, 1)
    if "--temoin" in sys.argv:
        say("h158 --temoin : suites plantees, lues par troncature avec rejet, gardees ORDONNEES")
        say(f"{'K,L':>7} | {'survivants':>10} | {'noeuds':>10} | {'sec':>6}")
        for K, L in ((3, 7), (1, 15), (3, 17), (3, 31)):
            tir = temoin(K, L, 0, ntir=6)
            t0 = time.time()
            s, n, coupe = crible(tir, K, L, DELTA)
            say(f"{K:3d},{L:3d} | {len(s):10d} | {n:10,} | {time.time()-t0:6.1f}"
                + ("  [COUPE]" if coupe else ""))
        sys.exit(0)

    ORD = lire_ordonnes()
    G = groupes_consecutifs(ORD)
    say(f"h158 : {len(ORD)} tirages ordonnes, {len(G)} groupe(s) consecutif(s) "
        f"({[len(g) for g in G]} tirages)")
    for g in G:
        say(f"\n=== groupe {g[0][0]}..{g[-1][0]} ({len(g)} tirages consecutifs)")
        tir = [v for _, v in g]
        say(f"{'K,L':>7} | {'survivants':>10} | {'noeuds':>12} | {'sec':>6}")
        lmax = int(sys.argv[sys.argv.index("--lmax") + 1]) if "--lmax" in sys.argv else 20
        tot = 0
        for L in range(2, lmax + 1):
            for K in range(1, L):
                if not primitif(K, L):
                    continue
                t0 = time.time()
                s, n, coupe = crible(tir, K, L, DELTA)
                tot += 1
                if s or coupe or n > 5_000_000:
                    say(f"{K:3d},{L:3d} | {len(s):10d} | {n:12,} | {time.time()-t0:6.1f}"
                        + ("  [COUPE]" if coupe else "")
                        + ("   !! SURVIVANT" if s else ""))
        say(f"   {tot} trinomes primitifs de degre <= {lmax} : "
            "aucun survivant sauf mention ci-dessus")
