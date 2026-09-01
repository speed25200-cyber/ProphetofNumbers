"""Relèvement de l'état HAUT d'un Fibonacci retardé additif (r_i = r_{i-K} + r_{i-L} mod 2^32,
sortie r >> 1, numéro (sortie mod 80) + 1, tirage de 20 numéros sous rejet, publié TRIÉ)
à partir de son état BAS (r mod 32, 5L bits, énumérable par crible) et des tirages triés.
Théorie : THEORIE_ETAT §7.8. Témoin : ce fichier lancé seul (état planté).

Les trois résultats que ce module met en oeuvre
-----------------------------------------------
1. La chaîne mod 5. Avec H_i = r_i >> 5 : H_i = H_{i-K} + H_{i-L} + κ_i - 2^27 w_i où κ_i
   (retenue des bits bas) est connu et w_i (débordement) inconnu ; le numéro donne
   H_i mod 5 = (v-1) div 16, qui doit être un résidu de la classe q_i = (v-1) mod 16 du
   tirage. Sous rejet, un mot est ACCEPTÉ si son (classe, résidu) n'a pas encore été tiré,
   PERDU sinon ; le tirage finit au vingtième accepté. La chaîne branche sur w_i seulement.
2. Les paquets. Deux chemins qui atteignent le même état (tirage, acceptés, perdus, numéros
   tirés, L derniers résidus) diffèrent par ε = w - w' ; leur différence entière vaut
   H' - H = 2^26 δ_Z avec δ_Z = -2 P^{-1} ε (P = 1 - x^K - x^L), qui est à support FINI
   (sinon les résidus ne coïncideraient pas). On les FUSIONNE en notant le support ; le
   nombre d'états vivants reste ≈ 10²-10³ là où le nombre de chemins explose (6 768 chemins
   pour 2 états à 12 tirages, mesuré). Sur les mots du support, H' = H + multiple de 2^27 :
   on retrouve H = H' mod 2^27.
3. Le réseau et la mesure de Mahler. w connu, chaque H_i est une forme entière des L
   inconnues G_j = (H_j - ρ_j)/5 ; la boîte 0 <= H_i < 2^27 sur n mots contient
   ≈ (2^27/5)^L / M(f)^n points du réseau, M(f) la mesure de Mahler de x^L - x^{L-K} - 1
   (≈ 1,38 pour tous les trinômes, la constante de Smyth 1,3814 en limite). Il faut donc
   n* ≈ (27L - L log2 5)/log2 M(f) mots : 360 pour la glibc TYPE_1 (mesuré : 380 réussit
   10/10, 360 échoue 8/10). Le CVP se résout par Babai sur une base LLL EXACTE
   (`lll_exact.py`) : en flottants il échoue toujours.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lll_exact import babai as babai_exact

M32 = 1 << 32
PERDUS_MAX = 48


def suite_basse(etat_bas, K, L, n):
    """r_i mod 32 pour i < n à partir des L mots bas initiaux."""
    s = [x & 31 for x in etat_bas]
    for i in range(L, n):
        s.append((s[i - K] + s[i - L]) & 31)
    return s


def classes(S):
    """Q(c) = {(v-1) div 16 : v dans S, (v-1) mod 16 = c}."""
    d = {}
    for v in S:
        d.setdefault((v - 1) % 16, set()).add((v - 1) // 16)
    return d


def tirages_de(seq, nb, debut=0):
    """Tirages triés sous rejet à partir du mot `debut` : liste de (deb, fin, ensemble trié)."""
    out = []
    p = debut
    for _ in range(nb):
        seen = set()
        deb = p
        while len(seen) < 20:
            seen.add((seq[p] >> 1) % 80 + 1)
            p += 1
        out.append((deb, p, sorted(seen)))
    return out


def _delta_Z(info_a, info_b, i, K, L):
    """Paquet entier entre deux chemins (unités de 2^26) sur les mots < i :
    (support en masque de bits, queue nulle ?)."""
    d = []
    for j in range(min(L, i)):
        m = (2 * (info_a[1][j] - info_b[1][j])) % 5   # H' diffère de m·2^27, m dans [-2, 2]
        if m > 2:
            m -= 5
        d.append(2 * m)
    for j in range(L, i):
        e = ((info_a[0] >> j) & 1) - ((info_b[0] >> j) & 1)
        d.append(d[j - K] + d[j - L] - 2 * e)
    supp = 0
    for j, x in enumerate(d):
        if x:
            supp |= 1 << j
    return supp, all(x == 0 for x in d[max(0, i - L):i])


def chaine_dp(low, Qs, K, L, perdus_max=PERDUS_MAX, etats_max=200000, perdus_inter=0):
    """Programmation dynamique sur les états de la chaîne mod 5.
    low : r_i mod 32 pour tous les mots ; Qs : classes de chaque tirage, dans l'ordre.
    perdus_inter : 0..perdus_inter mots perdus SANS contrainte entre deux tirages (la clé
    porte le compteur `gap`, remis à zéro au premier mot du tirage suivant).
    Rend (finals, stats) ; finals = liste de (mot de fin, clé, info) avec
    info = [w en masque de bits, résidus initiaux, masque des mots à paquet, nb de chemins].
    Chaque clé porte une LISTE d'infos : un représentant par classe de paquet — les
    « faux jumeaux » (même clé, paquet non fini) restent des états à part mais gardent
    la clé, si bien qu'ils peuvent fusionner plus tard ; sans cela ils prolifèrent aux
    petits L, où la coïncidence δ ≡ 0 (mod 10) sur L résidus a probabilité 5^-L."""
    ND = len(Qs)
    NW = len(low)
    q = [(x >> 1) & 15 for x in low]
    kappa = [0] * L + [int(low[i - K] + low[i - L] >= 32) for i in range(L, NW)]
    states = {(0, 0, 0, frozenset(), (), 0): [[0, (), 0, 1]]}
    finals = []
    stats = {"fusions": 0, "faux_jumeaux": 0, "etats_max": 0, "surv": [0] * (ND + 1)}

    def fusionne(new, nk, ninfo, i):
        lst = new.get(nk)
        if lst is None:
            new[nk] = [ninfo]
            return
        for old in lst:
            supp, fini = _delta_Z(old, ninfo, i + 1, K, L)
            if fini:
                old[2] |= ninfo[2] | supp
                old[3] += ninfo[3]
                stats["fusions"] += 1
                return
        stats["faux_jumeaux"] += 1
        lst.append(ninfo)

    for i in range(NW):
        if not states:
            break
        new = {}
        for key, lst in states.items():
            t, acc, perdus, used, tail, gap = key
            if t == ND:
                for info in lst:
                    finals.append((i, key, info))
                continue
            c = q[i]
            Qt = Qs[t]
            if i < L:
                cands = [(None, x) for x in range(5)]
            else:
                base = (tail[L - K] + tail[0] + kappa[i]) % 5
                cands = [(wi, (base - 3 * wi) % 5) for wi in (0, 1)]   # 2^27 = 3 mod 5
            # (b) mot perdu entre deux tirages : classe et résidu libres, gap < perdus_inter
            libre = t >= 1 and acc == 0 and perdus == 0 and gap < perdus_inter
            for info in lst:
                if libre:
                    for wi, x in cands:
                        ntail = (tail + (x,))[-L:]
                        w2 = info[0] | ((wi or 0) << i)
                        rho2 = info[1] + (x,) if i < L else info[1]
                        fusionne(new, (t, 0, 0, used, ntail, gap + 1),
                                 [w2, rho2, info[2], info[3]], i)
                # (a) mot du tirage t : classe permise, résidu dans la classe
                if c not in Qt:
                    continue
                for wi, x in cands:
                    if x not in Qt[c]:
                        continue
                    ntail = (tail + (x,))[-L:]
                    w2 = info[0] | ((wi or 0) << i)
                    rho2 = info[1] + (x,) if i < L else info[1]
                    if (c, x) not in used:
                        if acc + 1 == 20:
                            nk = (t + 1, 0, 0, frozenset(), ntail, 0)
                        else:
                            nk = (t, acc + 1, perdus, used | {(c, x)}, ntail, 0)
                    elif perdus < perdus_max:
                        nk = (t, acc, perdus + 1, used, ntail, 0)
                    else:
                        continue
                    fusionne(new, nk, [w2, rho2, info[2], info[3]], i)
        states = new
        nb = sum(len(v) for v in states.values())
        stats["etats_max"] = max(stats["etats_max"], nb)
        if nb > etats_max:
            stats["abandon"] = i
            return [], stats
        for key, lst in states.items():
            if key[1] == 0 and key[2] == 0 and key[5] == 0 and 1 <= key[0] <= ND:
                stats["surv"][key[0]] += len(lst)
    return finals, stats


def mahler(K, L):
    """Mesure de Mahler de x^L - x^{L-K} - 1 (racines de module > 1), ou None sans numpy."""
    try:
        import numpy as np
    except ImportError:
        return None
    coef = [0] * (L + 1)
    coef[0] = 1
    coef[K] = -1
    coef[L] = -1
    return float(np.prod([abs(z) for z in np.roots(coef) if abs(z) > 1]))


def mots_necessaires(K, L):
    """n* = (27L - L log2 5)/log2 M(f), le seuil théorique du relèvement."""
    m = mahler(K, L) or 1.3814
    return (27 * L - L * math.log2(5)) / math.log2(m)


def releve(low, info, K, L, NU):
    """CVP sur NU mots hors masque pour un état final de la chaîne ; rend l'état 32 bits
    (H = H' mod 2^27) et le plus court vecteur réduit."""
    w, rho, mask = info[0], info[1], info[2]
    kappa = [0] * L + [int(low[i - K] + low[i - L] >= 32) for i in range(L, NU)]
    alpha = [[int(j == i) for j in range(L)] for i in range(L)]
    beta = [0] * L
    for i in range(L, NU):
        alpha.append([alpha[i - K][j] + alpha[i - L][j] for j in range(L)])
        beta.append(beta[i - K] + beta[i - L] + kappa[i] - (1 << 27) * ((w >> i) & 1))
    c = [beta[i] + sum(alpha[i][j] * rho[j] for j in range(L)) for i in range(NU)]
    U = [i for i in range(NU) if not (mask >> i) & 1]
    basis = [[5 * alpha[i][j] for i in U] + [int(k == j) for k in range(L)] for j in range(L)]
    target = [(1 << 26) - c[i] for i in U] + [0] * L
    v, B, _ = babai_exact(basis, target)
    G = v[len(U):]
    H0 = [(5 * G[j] + rho[j]) % (1 << 27) for j in range(L)]
    lam1 = min(math.sqrt(sum(x * x for x in b[:len(U)])) for b in B)
    return [32 * H0[j] + low[j] for j in range(L)], lam1, len(U)


def regenere(etat, K, L, n):
    r = list(etat)
    for i in range(L, n):
        r.append((r[i - K] + r[i - L]) & M32 - 1)
    return r


def regenere_tirages(seq, tirages, perdus_inter=0):
    """Vrai si la suite `seq` (mot 0 = premier mot du tirage 0) régénère les tirages triés,
    avec 0..perdus_inter mots perdus entre deux tirages. Sous le rejet un tirage est
    déterminé par son départ (on lit jusqu'à 20 numéros distincts, tous permis) ; les
    départs vivants d'un tirage forment un petit ensemble, d'où la mémoïsation sur (t, s)."""
    from functools import lru_cache
    ND = len(tirages)
    ens = [set(S) for S in tirages]
    n = len(seq)

    @lru_cache(maxsize=None)
    def ok(t, s):
        if t == ND:
            return True
        vus = set()
        p = s
        St = ens[t]
        while len(vus) < 20:
            if p >= n:
                return False
            v = (seq[p] >> 1) % 80 + 1
            if v not in St:
                return False
            vus.add(v)
            p += 1
        return any(ok(t + 1, p + g) for g in range(perdus_inter + 1))

    return ok(0, 0)


def releve_etat(etat_bas, tirages, K, L, mots_max=None, perdus_max=PERDUS_MAX, perdus_inter=0):
    """Pipeline complet : état bas (L mots mod 32) + tirages triés consécutifs -> états 32 bits
    qui régénèrent exactement ces tirages (liste, vide si aucun). `tirages` : listes de 20 ;
    perdus_inter : mots perdus admis entre deux tirages (0 = tirages jointifs)."""
    ND = len(tirages)
    NW = mots_max or (60 * ND + L + 100)
    low = suite_basse(etat_bas, K, L, NW)
    Qs = [classes(S) for S in tirages]
    finals, stats = chaine_dp(low, Qs, K, L, perdus_max, perdus_inter=perdus_inter)
    trouves = []
    for (iend, key, info) in finals:
        st, lam1, nu = releve(low, info, K, L, iend)
        seq = regenere(st, K, L, NW)
        if regenere_tirages(seq, tirages, perdus_inter) and st not in trouves:
            trouves.append(st)
    return trouves, stats


def _temoin():
    import random
    import time
    K = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    L = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    ND = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    seed = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    NUS = [int(x) for x in os.environ.get("NUS", "100 200 300 400 500 600 800").split()]
    rng = random.Random(seed)
    state = [rng.getrandbits(32) for _ in range(L)]
    NW = 60 * ND + L + 100
    r = regenere(state, K, L, NW)
    draws = tirages_de(r, ND)
    n_true = draws[-1][1]
    low = [x & 31 for x in r]
    Qs = [classes(S) for (_, _, S) in draws]
    print(f"K={K} L={L} ND={ND} graine={seed} : {n_true} mots vrais, {n_true - 20 * ND} perdus")
    t0 = time.time()
    finals, stats = chaine_dp(low, Qs, K, L)
    print(f"chaîne DP : {len(finals)} état(s) final(aux), {stats['etats_max']} états vivants au plus, "
          f"{stats['fusions']} fusions, {stats['faux_jumeaux']} faux jumeaux, {time.time() - t0:.2f} s")
    print("  états à la fin du tirage t :",
          " ".join(f"{t}:{stats['surv'][t]}" for t in range(1, ND + 1)))
    rho_true = tuple((x >> 5) % 5 for x in r[:L])
    for (iend, key, info) in finals:
        print(f"  final : fin={iend} (vraie {n_true}) chemins fusionnés={info[3]} "
              f"mots masqués={bin(info[2]).count('1')} rho0 == vrai {info[1] == rho_true}")
    m = mahler(K, L)
    if m:
        print(f"x^{L}-x^{L-K}-1 : M(f) = {m:.4f}, log2 M(f) = {math.log2(m):.4f} bit/mot, "
              f"n* = {mots_necessaires(K, L):.0f} mots")
    for (iend, key, info) in finals[:1]:
        for NU in sorted(set(NUS + [iend])):
            if NU > iend:
                continue
            t1 = time.time()
            st, lam1, nu = releve(low, info, K, L, NU)
            seq = regenere(st, K, L, NW)
            try:
                okd = all(tirages_de(seq, ND)[t][2] == draws[t][2] for t in range(ND))
            except IndexError:
                okd = False
            print(f"  CVP {NU:4d} mots ({nu} hors masque) : état == vrai {str(st == state):5s} "
                  f"régénère les {ND} tirages {str(okd):5s}  "
                  f"lambda1/(2^27 sqrt nu) = {lam1 / ((1 << 27) * math.sqrt(nu)):8.3g}  "
                  f"({time.time() - t1:.2f} s)")
    t2 = time.time()
    trouves, _ = releve_etat([x & 31 for x in state], [S for (_, _, S) in draws], K, L)
    print(f"releve_etat : {trouves} == [vrai] {trouves == [state]}  ({time.time() - t2:.2f} s)")
    # même état, tirages séparés par t mod 3 mots perdus (0, 1, 2) : relèvement avec perdus_inter=4
    p = 0
    draws_g = []
    for t in range(ND):
        d = tirages_de(r, 1, p)[0]
        draws_g.append(d[2])
        p = d[1] + t % 3
    t3 = time.time()
    trouves_g, stats_g = releve_etat([x & 31 for x in state], draws_g, K, L, perdus_inter=4)
    print(f"releve_etat (perdus entre tirages t mod 3, perdus_inter=4) : {trouves_g} == [vrai] "
          f"{trouves_g == [state]}  états vivants au plus {stats_g['etats_max']}  "
          f"({time.time() - t3:.2f} s)")
    print(f"regenere_tirages sans perdus admis sur ces tirages : "
          f"{regenere_tirages(r, draws_g, 0)} (attendu False)")


if __name__ == "__main__":
    _temoin()
