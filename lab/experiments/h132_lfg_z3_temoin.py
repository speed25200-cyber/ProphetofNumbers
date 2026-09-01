"""
h132 — LA FRONTIÈRE DU 7.6 : LE LFG DE glibc, ATTAQUÉ AU SOLVEUR (TÉMOIN SEUL)

Le §152 laisse un generateur hors du crible des quotients : random() de la
glibc, r_i = r_{i-3} + r_{i-31} mod 2^32, sortie r_i >> 1. Son quotient bas
utile est (Z/32)^31 = 2^155 etats : on ne les enumere pas. Ce fichier NE
TRANCHE RIEN SUR L'ARCHIVE. Il mesure, sur des temoins plantes, si un solveur
peut REMONTER l'etat bas depuis des tirages tries — et COMMENT LE TEMPS CROIT
avec la taille de l'etat, en faisant varier le retard L du generateur
r_i = r_{i-k} + r_{i-L} : 5L bits inconnus, L = 7 ... 31.

CE QUI EST OBSERVE. Sous le tirage a rejet (n = (r_i >> 1) mod 80 + 1, on
rejette les doublons), tout mot de la fenetre du tirage t verifie
    q_i := bits 1..4 de r_i  =  n - 1 mod 16   avec n dans D_t,
donc q_i est dans A_t, les classes mod 16 touchees par les 20 numeros. Mieux :
la fenetre contient EXACTEMENT les 20 numeros une fois chacun, plus des
doublons ; si n_c compte les numeros tires dans la classe c, le nombre m_c de
mots de la fenetre dans la classe c verifie m_c >= n_c (et m_c = 0 si n_c = 0).
C'est la CONTRAINTE DE MULTI-ENSEMBLE, bien plus forte que l'appartenance.

LA REFORMULATION PAR LES RETENUES. Ecrivons r_i = 2 q_i + b_i mod 32 (b_i le
bit 0, jamais observe). Alors
    b_i = b_{i-k} XOR b_{i-L}                                    (plan 0, LFSR)
    q_i = q_{i-k} + q_{i-L} + c_i  mod 16,  c_i = b_{i-k} AND b_{i-L}.
Le plan 0 est un LFSR de polynome x^L + x^k + 1 ; les nibbles suivent une
recurrence AFFINE mod 16 dont le terme constant est le AND de deux bits du
LFSR. Contrainte de coherence : (q_i - q_{i-k} - q_{i-L}) mod 16 est dans
{0, 1}, et vaut la retenue.

TROIS DIFFICULTES CROISSANTES, chacune sur un temoin plante :
    A. alignement connu (sigma_t donne), appartenance + multi-ensemble
    B. alignement INCONNU (sigma_t dans [20, SIGMAX], fenetres contigues)
    C. B avec 0..P mots perdus entre les tirages
Pour chaque L : temps du solveur, et l'etat retrouve est-il l'etat plante ?

    H132_K       tirages donnes au solveur (defaut 16)
    H132_TIMEOUT secondes par instance (defaut 300)
    H132_LAGS    liste de L, ex. '7,11,15,20,25,31' (defaut)
    H132_CAS     'A', 'AB' ou 'ABC' (defaut 'AB')
"""
import os
import random
import sys
import time
from math import log2, factorial

import z3

K = int(os.environ.get("H132_K", "16"))
TIMEOUT = int(os.environ.get("H132_TIMEOUT", "300"))
CAS = os.environ.get("H132_CAS", "AB")
LAGS = [int(x) for x in os.environ.get("H132_LAGS", "7,11,15,20,25,31").split(",")]
SIGMAX = 32
PERDUS = 2
GRAINE = int(os.environ.get("H132_GRAINE", "20260901"))
# trinomes x^L + x^k + 1 de la table de Zierler-Brillhart (non reverifies ici :
# la difficulte du solveur ne depend pas de la primitivite)
PETIT_RETARD = {7: 3, 9: 4, 10: 3, 11: 2, 15: 4, 17: 3, 20: 3, 23: 5,
                25: 3, 28: 3, 31: 3}

M32 = (1 << 32) - 1


def lfg_mots(etat, n, k, L):
    """r_i = r_{i-k} + r_{i-L} mod 2^32 a partir des L mots d'etat."""
    r = list(etat)
    for i in range(L, n + L):
        r.append((r[i - k] + r[i - L]) & M32)
    return r[L:]  # les mots produits APRES l'etat initial


def tirages_rejet(mots, nb, perdus_max, rng):
    """nb tirages a rejet, 0..perdus_max mots perdus entre deux tirages.
    Renvoie (ensembles tries, sigma_t, perdus_t)."""
    tir, sig, perd = [], [], []
    pos = 0
    for _ in range(nb):
        vus = set()
        s = 0
        while len(vus) < 20:
            n = ((mots[pos] >> 1) % 80) + 1
            pos += 1
            s += 1
            vus.add(n)
        tir.append(sorted(vus))
        sig.append(s)
        p = rng.randint(0, perdus_max)
        perd.append(p)
        pos += p
    return tir, sig, perd


def classes(ens):
    n = [0] * 16
    for v in ens:
        n[(v - 1) % 16] += 1
    return n


def bits_appartenance(n):
    """-log2 P(un nibble uniforme tombe dans une classe touchee)."""
    a = sum(1 for c in n if c)
    return -log2(a / 16)


def proba_multiensemble(n, sigma):
    """P(sigma nibbles uniformes couvrent le multi-ensemble n : m_c >= n_c,
    m_c = 0 si n_c = 0). Coefficient de x^sigma dans le produit des series
    tronquees, fois sigma! / 16^sigma."""
    poly = [1.0]  # serie en x, coefficient de x^m
    for c in range(16):
        if n[c] == 0:
            continue
        f = [0.0] * (sigma + 1)
        for m in range(n[c], sigma + 1):
            f[m] = 1.0 / factorial(m)
        nouv = [0.0] * (sigma + 1)
        for a, pa in enumerate(poly):
            if pa == 0:
                continue
            for b in range(sigma + 1 - a):
                nouv[a + b] += pa * f[b]
        poly = nouv
    return poly[sigma] * factorial(sigma) / 16 ** sigma


def modele(tirages, k, L, sigma_connu, perdus_max, solveur):
    """Construit le modele z3 ; renvoie les L mots d'etat (BV 5 bits)."""
    nb = len(tirages)
    NW = SIGMAX * nb + perdus_max * nb + 1
    R = [z3.BitVec(f"r{i}", 5) for i in range(L)]
    seq = list(R)
    for i in range(L, NW + L):
        seq.append(seq[i - k] + seq[i - L])
    q = [z3.Extract(4, 1, s) for s in seq[L:]]  # nibble des mots produits
    if sigma_connu is not None:
        pos = 0
        for t in range(nb):
            n = classes(tirages[t])
            fen = list(range(pos, pos + sigma_connu[t][0]))
            for i in fen:
                solveur.add(z3.Or([q[i] == c for c in range(16) if n[c]]))
            for c in range(16):
                if n[c] >= 2:
                    solveur.add(z3.PbGe([(q[i] == c, 1) for i in fen], n[c]))
                elif n[c] == 1:
                    solveur.add(z3.Or([q[i] == c for i in fen]))
            pos += sigma_connu[t][0] + sigma_connu[t][1]
        return R
    B = 16
    starts = [z3.BitVec(f"s{t}", B) for t in range(nb + 1)]
    sigmas = [z3.BitVec(f"g{t}", B) for t in range(nb)]
    solveur.add(starts[0] == 0)
    for t in range(nb):
        solveur.add(z3.UGE(sigmas[t], 20), z3.ULE(sigmas[t], SIGMAX))
        solveur.add(z3.UGE(starts[t + 1], starts[t] + sigmas[t]))
        solveur.add(z3.ULE(starts[t + 1], starts[t] + sigmas[t] + perdus_max))
    for t in range(nb):
        n = classes(tirages[t])
        lo, hi = 20 * t, min(NW, (SIGMAX + perdus_max) * t + SIGMAX)
        dedans = {}
        for i in range(lo, hi):
            iv = z3.BitVecVal(i, B)
            d = z3.Bool(f"w{t}_{i}")
            solveur.add(d == z3.And(z3.ULE(starts[t], iv),
                                    z3.ULT(iv, starts[t] + sigmas[t])))
            dedans[i] = d
            solveur.add(z3.Implies(d, z3.Or([q[i] == c for c in range(16) if n[c]])))
        for c in range(16):
            if n[c] >= 1:
                solveur.add(z3.PbGe([(z3.And(dedans[i], q[i] == c), 1)
                                     for i in range(lo, hi)], n[c]))
    return R


def instance(cas, k, L, tirages, sig, perd, etat):
    s = z3.Solver()
    s.set("timeout", TIMEOUT * 1000)
    if cas == "A":
        R = modele(tirages, k, L, list(zip(sig, perd)), 0, s)
    elif cas == "B":
        R = modele(tirages, k, L, None, 0, s)
    else:
        R = modele(tirages, k, L, None, PERDUS, s)
    t0 = time.time()
    res = s.check()
    dt = time.time() - t0
    trouve = None
    if res == z3.sat:
        m = s.model()
        trouve = [m.eval(r, model_completion=True).as_long() for r in R]
    return res, dt, trouve, [e & 31 for e in etat]


def main():
    rng = random.Random(GRAINE)
    print("=" * 78)
    print("1. L'INFORMATION PAR TIRAGE, APPARTENANCE CONTRE MULTI-ENSEMBLE")
    print("=" * 78)
    print("   Mot par mot, l'appartenance q_i dans A_t vaut -log2(|A_t|/16) ;")
    print("   la fenetre entiere, prise comme multi-ensemble, vaut bien plus.")
    etat31 = [rng.getrandbits(32) for _ in range(31)]
    mots31 = lfg_mots(etat31, 40 * K + 64, 3, 31)
    tir, sig, _ = tirages_rejet(mots31, K, 0, rng)
    b_app = sum(bits_appartenance(classes(e)) for e in tir) / K
    b_m20 = sum(-log2(proba_multiensemble(classes(e), 20)) for e in tir) / K
    b_mS = sum(-log2(proba_multiensemble(classes(tir[t]), sig[t])) for t in range(K)) / K
    print(f"       appartenance seule, par mot              {b_app:6.3f} bits")
    print(f"       appartenance, fenetre de 20 mots         {20*b_app:6.3f} bits")
    print(f"       multi-ensemble, sigma = 20               {b_m20:6.3f} bits")
    print(f"       multi-ensemble, sigma reel (moy {sum(sig)/K:4.1f})   {b_mS:6.3f} bits")
    print(f"       tirages pour 155 bits : {155/b_mS:.1f} (multi-ensemble)"
          f"  contre {155/(20*b_app):.1f} (appartenance)")
    print()
    print("=" * 78)
    print("2. LES TÉMOINS PLANTÉS, DU PETIT RETARD AU GRAND")
    print("=" * 78)
    print(f"   K = {K} tirages par instance, timeout {TIMEOUT} s, graine {GRAINE}")
    print(f"   information disponible ~ {K*b_mS:.0f} bits (multi-ensemble)")
    print()
    print("      cas    L    k   bits   resultat        sec   etat bas retrouve")
    bilan = {}
    for cas in CAS:
        for L in LAGS:
            k = PETIT_RETARD[L]
            etat = [rng.getrandbits(32) for _ in range(L)]
            mots = lfg_mots(etat, 40 * K + 64, k, L)
            pl = PERDUS if cas == "C" else 0
            tirs, sigs, perds = tirages_rejet(mots, K, pl, rng)
            res, dt, trouve, plante = instance(cas, k, L, tirs, sigs, perds, etat)
            ok = "-"
            if trouve is not None:
                ok = "OUI" if trouve == plante else "NON (autre solution)"
            print(f"      {cas}    {L:3d}  {k:3d}   {5*L:4d}   {str(res):8s}  {dt:8.1f}   {ok}")
            bilan[(cas, L)] = (str(res), dt, ok)
            sys.stdout.flush()
            if res != z3.sat:
                print(f"           -> on arrete la montee en L pour le cas {cas}")
                break
    print()
    print("=" * 78)
    print("3. CE QUE CELA VEUT DIRE")
    print("=" * 78)
    for cas in CAS:
        faits = [(L, bilan[(cas, L)]) for L in LAGS if (cas, L) in bilan]
        ok = [L for L, b in faits if b[0] == "sat" and b[2] == "OUI"]
        lib = {"A": "alignement connu", "B": "alignement inconnu, contigu",
               "C": f"alignement inconnu, 0..{PERDUS} mots perdus"}[cas]
        if ok:
            print(f"   {cas} ({lib}) : etat retrouve jusqu'a L = {max(ok)}, "
                  f"soit {5*max(ok)} bits, en {bilan[(cas, max(ok))][1]:.0f} s.")
        else:
            print(f"   {cas} ({lib}) : aucun etat retrouve.")
        if 31 in ok:
            print("       LA FRONTIERE DU 7.6 TOMBE sur temoin : les 155 bits de glibc")
            print("       se remontent depuis des ensembles tries.")
    print("   AUCUN verdict sur l'archive ici : c'est un temoin de faisabilite.")


if __name__ == "__main__":
    main()
