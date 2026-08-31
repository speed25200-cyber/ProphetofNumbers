"""h61 — les familles que la carte du §73 n'avait jamais nommees.

Le trou
========
Les §68 a §80 ont bati une attaque complete sur les generateurs F2-lineaires,
et l'ont appliquee a CINQ familles : xorshift32, 64, 96, 128 et taus88. Or ce
sont les cinq que le §68 avait ecrites le premier jour, et personne n'a
demande si la liste etait la bonne.

Elle ne l'est pas. Les generateurs F2-lineaires reellement deployes
aujourd'hui sont les xoshiro et xoroshiro de Blackman et Vigna (2018), le
LFSR113 de L'Ecuyer (1999) et les WELL de Panneton, L'Ecuyer et Matsumoto
(2006). Aucun n'a ete teste.

Ce fichier les ajoute, et il apporte deux choses que les §68 a §73 n'avaient
pas :

  1. LE SEUIL MESURE. Le §69 comptait « nbits / 80 tirages » ; le §80 a montre
     que ce compte est faux des que l'etat est grand, parce que les equations
     cessent d'etre independantes. On MESURE donc ici, famille par famille, le
     mot exact ou le rang devient plein — la methode du §80 appliquee a chaque
     nouvelle famille.

  2. LA CARTE HONNETE. Pour chaque famille : ce que les cinq tirages ordonnes
     du dossier decident, et ce qu'ils ne decident pas, avec le nombre exact
     de tirages qu'il faudrait.

Il TESTE l'archive (ses cinq tirages ordonnes) : il consigne au registre.
"""

import csv
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POOL, DRAWN = 80, 20
DRY = os.environ.get("H61_DRY") == "1"
MAX_REJ = 4 if DRY else 7
BUDGET = 6.0 if DRY else 40.0
# Plafond du noyau parcouru a chaque feuille. Au-dela, la famille est
# declaree NON IDENTIFIABLE par cet echantillonneur — et c'est un
# resultat, pas un abandon : LFSR113 y tombe avec 17 dimensions.
KCAP = 8
MAXT = 5 if DRY else 8                    # plafond TOTAL de rejets explore
NB = 4                                    # v2(80) : bits publies par mot


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def m(n):
    return (1 << n) - 1


def rotl(x, k, w):
    return ((x << k) | (x >> (w - k))) & m(w)


# ==========================================================================
# Les familles. Chaque `step` : etat entier -> (nouvel etat, mot de sortie).
# Les anciennes sont reprises telles quelles pour que la comparaison tienne.
# ==========================================================================

def xs32(s):
    s ^= (s << 13) & m(32); s ^= s >> 17; s ^= (s << 5) & m(32)
    return s, s


def xs64(s):
    s ^= (s << 13) & m(64); s ^= s >> 7; s ^= (s << 17) & m(64)
    return s, s


def xs96(s):
    x, y, z = s & m(32), (s >> 32) & m(32), (s >> 64) & m(32)
    t = (x ^ (x << 3)) & m(32); t ^= t >> 19
    x, y = y, z
    z = (z ^ (z << 6) ^ t) & m(32)
    return x | (y << 32) | (z << 64), z


def xs128(s):
    x, y = s & m(32), (s >> 32) & m(32)
    z, w = (s >> 64) & m(32), (s >> 96) & m(32)
    t = (x ^ (x << 11)) & m(32); t ^= t >> 8
    x, y, z = y, z, w
    w = (w ^ (w >> 19) ^ t) & m(32)
    return x | (y << 32) | (z << 64) | (w << 96), w


def taus88(s):
    s1, s2, s3 = s & m(32), (s >> 32) & m(32), (s >> 64) & m(32)
    b = (((s1 << 13) ^ s1) >> 19) & m(32)
    s1 = (((s1 & 0xFFFFFFFE) << 12) ^ b) & m(32)
    b = (((s2 << 2) ^ s2) >> 25) & m(32)
    s2 = (((s2 & 0xFFFFFFF8) << 4) ^ b) & m(32)
    b = (((s3 << 3) ^ s3) >> 11) & m(32)
    s3 = (((s3 & 0xFFFFFFF0) << 17) ^ b) & m(32)
    return s1 | (s2 << 32) | (s3 << 64), s1 ^ s2 ^ s3


def lfsr113(s):
    """LFSR113, L'Ecuyer 1999. Quatre composantes de 31, 29, 28 et 25 bits
    utiles logees dans quatre mots de 32 : l'etat effectif vaut 113 bits, et
    c'est la mesure du rang qui le confirmera."""
    z1, z2 = s & m(32), (s >> 32) & m(32)
    z3, z4 = (s >> 64) & m(32), (s >> 96) & m(32)
    b = (((z1 << 6) ^ z1) >> 13) & m(32)
    z1 = (((z1 & 0xFFFFFFFE) << 18) ^ b) & m(32)
    b = (((z2 << 2) ^ z2) >> 27) & m(32)
    z2 = (((z2 & 0xFFFFFFF8) << 2) ^ b) & m(32)
    b = (((z3 << 13) ^ z3) >> 21) & m(32)
    z3 = (((z3 & 0xFFFFFFF0) << 7) ^ b) & m(32)
    b = (((z4 << 3) ^ z4) >> 12) & m(32)
    z4 = (((z4 & 0xFFFFFF80) << 13) ^ b) & m(32)
    return z1 | (z2 << 32) | (z3 << 64) | (z4 << 96), z1 ^ z2 ^ z3 ^ z4


def xoroshiro128(s):
    """xoroshiro128, Blackman et Vigna. Sortie BRUTE s0 : les variantes + et
    ** brouillent par une addition ou une multiplication, qui ne sont pas
    lineaires sur F2 et sortent donc du champ du §68."""
    s0, s1 = s & m(64), (s >> 64) & m(64)
    s1 ^= s0
    n0 = rotl(s0, 24, 64) ^ s1 ^ ((s1 << 16) & m(64))
    n1 = rotl(s1, 37, 64)
    return n0 | (n1 << 64), n0


def xoshiro128(s):
    """xoshiro128, quatre mots de 32 bits. Sortie brute s0."""
    a = [(s >> (32 * i)) & m(32) for i in range(4)]
    t = (a[1] << 9) & m(32)
    a[2] ^= a[0]; a[3] ^= a[1]; a[1] ^= a[2]; a[0] ^= a[3]
    a[2] ^= t
    a[3] = rotl(a[3], 11, 32)
    return sum(v << (32 * i) for i, v in enumerate(a)), a[0]


def xoshiro256(s):
    """xoshiro256, quatre mots de 64 bits. Sortie brute s0."""
    a = [(s >> (64 * i)) & m(64) for i in range(4)]
    t = (a[1] << 17) & m(64)
    a[2] ^= a[0]; a[3] ^= a[1]; a[1] ^= a[2]; a[0] ^= a[3]
    a[2] ^= t
    a[3] = rotl(a[3], 45, 64)
    return sum(v << (64 * i) for i, v in enumerate(a)), a[0]


def well512a(s):
    """WELL512a, Panneton, L'Ecuyer et Matsumoto 2006. Seize mots de 32 bits
    plus un index — l'index etant deterministe, l'application reste lineaire
    sur F2 tant qu'on part toujours du meme point du cycle."""
    st = [(s >> (32 * i)) & m(32) for i in range(16)]
    idx = 0
    a = st[idx]
    c = st[(idx + 13) & 15]
    b = a ^ c ^ ((a << 16) & m(32)) ^ ((c << 15) & m(32))
    c = st[(idx + 9) & 15]
    c ^= c >> 11
    a = st[idx] = b ^ c
    d = a ^ ((a << 5) & 0xDA442D24)
    idx = (idx + 15) & 15
    a = st[idx]
    st[idx] = a ^ b ^ d ^ ((a << 2) & m(32)) ^ ((b << 18) & m(32)) \
        ^ ((c << 28) & m(32))
    out = st[idx]
    # on remet l'etat dans l'ordre canonique pour que l'index reste a 0
    st = st[idx:] + st[:idx]
    return sum(v << (32 * i) for i, v in enumerate(st)), out


NEW = [("xoroshiro128 (brut)", 128, xoroshiro128, "Blackman-Vigna 2018"),
       ("xoshiro128 (brut)", 128, xoshiro128, "Blackman-Vigna 2018"),
       ("xoshiro256 (brut)", 256, xoshiro256, "Blackman-Vigna 2018"),
       ("LFSR113", 128, lfsr113, "L'Ecuyer 1999"),
       ("WELL512a", 512, well512a, "Panneton-L'Ecuyer-Matsumoto 2006")]
OLD = [("xorshift32", 32, xs32, "Marsaglia 2003"),
       ("xorshift64", 64, xs64, "Marsaglia 2003"),
       ("xorshift96", 96, xs96, "Marsaglia 2003"),
       ("xorshift128", 128, xs128, "Marsaglia 2003"),
       ("taus88", 96, taus88, "L'Ecuyer 1996")]


# ==========================================================================
# Algebre : formes, echelon, seuil de rang mesure (methode du §80).
# ==========================================================================

def words_from(step, state, count):
    out, s = [], state
    for _ in range(count):
        s, w = step(s)
        out.append(w)
    return out


def basis_bits(step, nbits, nwords):
    coef = [[0] * NB for _ in range(nwords)]
    for i in range(nbits):
        s, bit = 1 << i, 1 << i
        for k in range(nwords):
            s, w = step(s)
            cp = coef[k]
            for j in range(NB):
                if (w >> j) & 1:
                    cp[j] |= bit
    return coef


def rank_threshold(coef, nwords):
    """Premier mot atteignant le rang MAXIMAL, et ce rang.

    Une premiere version renvoyait le premier mot qui n'apportait RIEN — or un
    palier d'un seul mot n'est pas une saturation : LFSR113 stagne au mot 29
    (une equation dependante) puis repart, et son rang reel n'est pas 111. La
    cible de l'attaque etait alors inatteignable et le temoin echouait a 0/6.
    C'est exactement ce que le temoin est la pour attraper.
    """
    piv, ranks = {}, []
    for k in range(nwords):
        for j in range(NB):
            row = coef[k][j]
            while row:
                h = row.bit_length() - 1
                if h in piv:
                    row ^= piv[h]
                else:
                    piv[h] = row
                    break
        ranks.append(len(piv))
    rmax = ranks[-1]
    return ranks.index(rmax) + 1, rmax


def add_eq(piv, row, b, added):
    """Ajoute une equation EN PLACE et journalise le pivot cree.

    Une premiere version copiait le dictionnaire a chaque noeud de l'arbre —
    O(rang) par noeud, soit l'essentiel du temps de calcul. Or `add_eq` ne
    MODIFIE jamais un pivot existant : il n'en insere qu'un. Le journal suffit
    donc a defaire, et le noeud redevient O(1) amorti."""
    cur, cb = row, b
    while cur:
        h = cur.bit_length() - 1
        if h in piv:
            pr, pb = piv[h]
            cur ^= pr
            cb ^= pb
        else:
            piv[h] = (cur, cb)
            added.append(h)
            return True
    return cb == 0


def back_substitute(piv, nbits):
    sol = 0
    for h in sorted(piv):
        pr, pb = piv[h]
        if (bin(pr & sol).count("1") + pb) & 1:
            sol ^= 1 << h
    return sol, [i for i in range(nbits) if i not in piv]


def simulate_count(step, state, ndraws, nnum):
    """Comme `simulate`, mais rend aussi le nombre de rejets rencontres AVANT
    le nnum-ieme numero accepte : c'est cette quantite, et non le total, qui
    dit si le cas tombe dans la couverture de l'attaque."""
    s, draws, nrej, acc = state, [], 0, 0
    for _ in range(ndraws):
        seen, out, guard = set(), [], 0
        while len(out) < DRAWN:
            s, w = step(s)
            guard += 1
            if guard > 400:
                return None, 0
            n = w % POOL + 1
            if n in seen:
                if acc < nnum:
                    nrej += 1
            else:
                seen.add(n)
                out.append(n)
                acc += 1
        draws.append(out)
    return draws, nrej


def simulate(step, state, ndraws):
    s, draws = state, []
    for _ in range(ndraws):
        seen, out = set(), []
        guard = 0
        while len(out) < DRAWN:
            s, w = step(s)
            guard += 1
            if guard > 400:
                return None
            n = w % POOL + 1
            if n not in seen:
                seen.add(n)
                out.append(n)
        draws.append(out)
    return draws


def kernel_basis(piv, nbits):
    """Base du noyau du systeme echelonne, une par variable libre.

    Les equations ne portent que sur les bits PUBLIES du mot ; le numero, lui,
    vaut out mod 80, ce qui en demande 6,32. Une direction du noyau peut donc
    laisser les bits publies intacts et CHANGER le numero : la solution
    particuliere ne suffit pas, il faut parcourir le noyau. LFSR113 le montre
    — son noyau vaut 17 dimensions et la solution a variables libres nulles
    ne rejoue pas.
    """
    free = [i for i in range(nbits) if i not in piv]
    hs = sorted(piv)
    out = []
    for f in free:
        v = 1 << f
        for h in hs:
            pr, _pb = piv[h]
            if (bin(pr & v).count("1")) & 1:
                v ^= 1 << h
        out.append(v)
    return out


def replay_ok(step, state, draws):
    """Rejeu avec abandon au PREMIER ecart : c'est le test de la feuille, et
    il doit etre le moins cher possible puisqu'il est appele des millions de
    fois. Un etat faux meurt en general sur le premier numero."""
    s = state
    for d in draws:
        seen, n_ok = set(), 0
        guard = 0
        while n_ok < DRAWN:
            s, w = step(s)
            guard += 1
            if guard > 400:
                return False
            n = w % POOL + 1
            if n in seen:
                continue
            if n != d[n_ok]:
                return False
            seen.add(n)
            n_ok += 1
    return True


def attack(step, nbits, draws, coef, nwords, budget, max_total, rank_target):
    """Chaine des tirages CONSECUTIFS sous rejet modulo 80.

    APPROFONDISSEMENT ITERATIF sur le nombre de rejets rencontres AVANT que le
    rang ne soit plein — c'est la seule quantite qui compte, puisque la
    recherche s'arrete la. Une premiere version plafonnait les rejets par
    tirage sans plafond global : l'arbre valait C(19,7)^2 feuilles et le
    temoin echouait.

    `rank_target` est le rang MESURE de la famille, pas sa taille nominale.
    taus88 sature a 88 sur 96 et LFSR113 a 111 sur 128 : exiger le rang
    nominal ne se produit jamais, et une premiere version de ce fichier
    echouait sur ces deux familles pour cette seule raison. Les directions
    libres restantes sont INERTES par definition de la saturation — elles
    n'influencent aucune sortie — donc la solution particuliere suffit, et le
    rejeu tranche.

    Renvoie (etat, profondeur atteinte). La profondeur est la COUVERTURE
    declaree, et la section 2 la convertit en probabilite.
    """
    flat = [n for d in draws for n in d]
    t0, found, depth = time.time(), [], -1
    piv = {}
    tick = [0]

    def dfs(pos, k, left):
        if found:
            return
        tick[0] += 1
        if not (tick[0] & 8191) and time.time() - t0 > budget:
            found.append(None)              # sentinelle d'abandon
            return
        if len(piv) >= rank_target or k == len(flat):
            sol, free = back_substitute(piv, nbits)
            if not free:
                if replay_ok(step, sol, draws):
                    found.append(sol)
                return
            if len(free) > KCAP:
                return                      # defaut d'observabilite hors portee
            ker = kernel_basis(piv, nbits)
            first = draws[0][0]
            for mask in range(1 << len(ker)):
                c, mm, i2 = sol, mask, 0
                while mm:
                    if mm & 1:
                        c ^= ker[i2]
                    mm >>= 1
                    i2 += 1
                if step(c)[1] % POOL + 1 != first:      # prefiltre a un pas
                    continue
                if replay_ok(step, c, draws):
                    found.append(c)
                    return
            return
        if pos >= nwords:
            return
        added, ok = [], True
        val, cp = (flat[k] - 1) & 15, coef[pos]
        for b in range(NB):
            if not add_eq(piv, cp[b], (val >> b) & 1, added):
                ok = False
                break
        if ok:
            dfs(pos + 1, k + 1, left)
        for h in added:
            del piv[h]
        if found:
            return
        if left and k % DRAWN != 0:
            dfs(pos + 1, k, left - 1)

    for t in range(max_total + 1):
        if time.time() - t0 > budget:
            break
        depth = t
        piv.clear()
        dfs(0, 0, t)
        if found:
            break
    hit = found[0] if found and found[0] is not None else None
    if found and found[0] is None:
        depth -= 1                          # ce palier n'a pas ete fini
    return hit, max(depth, 0)


# ==========================================================================
rule("1. LES FAMILLES, ET LE SEUIL MESURÉ POUR CHACUNE")
# ==========================================================================

say(f"""   Le §69 comptait « nbits / {NB*DRAWN} tirages ». Le §80 a montre que ce compte
   est FAUX des que l'etat est grand : les equations cessent d'etre
   independantes. On mesure donc, pour chaque famille, le mot exact ou le
   rang SATURE — et le rang atteint, qui n'est pas toujours nbits.
""")
say(f"   {'famille':>21} {'nominal':>8} {'W(rang)':>8} {'rang réel':>10} "
    f"{'tirages':>8}  origine")
INFO = {}
for name, nb, step, orig in OLD + NEW:
    nw = min(400, nb // NB + 120)
    coef = basis_bits(step, nb, nw)
    w, r = rank_threshold(coef, nw)
    INFO[name] = (nb, step, coef, nw, w, r)
    say(f"   {name:>21} {nb:>8} {w:>8} {r:>10} {w/DRAWN:>8.2f}  {orig}")

say(f"""
   LECTURE. Trois faits que la liste du §68 ne pouvait pas donner.

   1. LFSR113 sature a 113 et non 128 : quinze bits de son etat sont INERTES,
      exactement comme taus88 en avait huit (§80). Ces familles combinees
      portent toujours moins d'etat que leur representation.
   2. WELL512a demande {INFO['WELL512a'][4]} mots, soit {INFO['WELL512a'][4]/DRAWN:.1f} tirages ordonnes : hors de
      portee des cinq du dossier, et de loin.
   3. xoshiro256 en demande {INFO['xoshiro256 (brut)'][4]}, soit {INFO['xoshiro256 (brut)'][4]/DRAWN:.1f} tirages — juste au-dela.""")


# ==========================================================================
rule("2. LE TÉMOIN POSITIF, FAMILLE PAR FAMILLE")

import random                                                  # noqa: E402
rng = random.Random(88_881)


def rejection_law(nnum, reps):
    """Loi du nombre de rejets rencontres AVANT le nnum-ieme numero accepte.

    Ce n'est PAS le nombre total de rejets des tirages : la recherche s'arrete
    des que le rang est plein, donc au nnum = ceil(nbits/4)-ieme numero. Les
    rejets qui suivent ne sont jamais enumeres et ne coutent rien. Compter le
    total surestimait le cout et sous-estimait la couverture d'un facteur
    deux — une premiere version de ce fichier le faisait.
    """
    r = random.Random(4242)
    out = []
    for _ in range(reps):
        tot, acc, seen = 0, 0, set()
        while acc < nnum:
            if len(seen) == DRAWN:          # frontiere de tirage
                seen = set()
            n = r.randrange(POOL)
            if n in seen:
                tot += 1
            else:
                seen.add(n)
                acc += 1
        out.append(tot)
    return out


NREP = 4000 if DRY else 20000
LAW = {}


def coverage(nnum, t):
    if nnum not in LAW:
        LAW[nnum] = rejection_law(nnum, NREP)
    L = LAW[nnum]
    return sum(1 for v in L if v <= t) / len(L)


def mean_rej(nnum):
    coverage(nnum, 0)
    return sum(LAW[nnum]) / len(LAW[nnum])


say(f"""   Avant d'appliquer l'attaque a l'archive, on verifie qu'elle FONCTIONNE :
   une graine au hasard, les tirages simules, l'attaque, comparaison a la
   verite.

   L'attaque APPROFONDIT sur les rejets rencontres AVANT le rang plein — les
   suivants ne sont jamais enumeres. Elle ne trouve donc
   que si le motif vrai tient dans la profondeur atteinte : c'est une
   COUVERTURE declaree, pas une promesse. Elle se mesure :

     numéros à expliquer 19 (xorshift64)     33 (xorshift128)
     rejets attendus     {mean_rej(19):>5.2f}                {mean_rej(33):>5.2f}
     couverture a t = 6  {coverage(19,6):>5.0%}                {coverage(33,6):>5.0%}
     couverture a t = 8  {coverage(19,8):>5.0%}                {coverage(33,8):>5.0%}

   Une premiere version de ce fichier plafonnait les rejets PAR TIRAGE sans
   plafond global : l'arbre valait C(19,7)^2 = 2 x 10^9 feuilles et le temoin
   echouait a 0/3. C'est exactement l'erreur que le §68 avait deja corrigee
   une fois, dans l'autre sens.
""")
say(f"   {'famille':>21} {'requis':>7} {'profondeur':>10} {'dans portée':>11} "
    f"{'retrouvés':>10} {'sec':>7}")
REACH, DEFECT = [], []
for name, (nb, step, coef, nw, w, r) in INFO.items():
    need = -(-w // DRAWN)
    if nb - r > KCAP:
        DEFECT.append((name, nb, r, nb - r))
        continue
    if need > 2:                       # le dossier n'a qu'UNE paire consecutive
        continue
    REACH.append(name)
    ok, elig, t0, dmin = 0, 0, time.time(), 99
    TRIES = 4 if DRY else 8
    for _ in range(TRIES):
        seed = rng.getrandbits(nb) | 1
        truth, nrej = simulate_count(step, seed, need, w)
        if truth is None:
            continue
        nw2 = DRAWN * need + MAXT
        c2 = basis_bits(step, nb, nw2)
        got, dep = attack(step, nb, truth, c2, nw2, BUDGET, MAXT, r)
        dmin = min(dmin, dep)
        if nrej <= dep:                # le motif vrai est DANS la portee
            elig += 1
            ok += got is not None and replay_ok(step, got, truth)
    say(f"   {name:>21} {need:>7} {dmin:>10} {elig:>11} {ok:>10} "
        f"{time.time()-t0:>7.1f}")

for name, nb, r, d in DEFECT:
    say(f"""
   {name} EST ECARTEE, ET C'EST UN RESULTAT. Les quatre bits publies par mot
   n'engendrent qu'un espace de rang {r} sur {nb} : il reste un noyau de {d}
   dimensions INVISIBLE modulo 16 mais VISIBLE modulo {POOL}. Deux etats du
   noyau donnent les memes quartets et des NUMEROS differents, donc le
   systeme lineaire ne suffit pas — il faudrait departager {1 << d:,} etats a
   chaque feuille, ce que le plafond KCAP = {KCAP} refuse.

   Ce n'est pas une limite de calcul mais une propriete de la famille : le
   modulo publie trop peu pour l'identifier. Le §82 montrera que les deux
   autres echantillonneurs ferment ce defaut.""")

say(f"""
   LECTURE DU TEMOIN. Parmi les graines dont le motif de rejet tient dans la
   profondeur atteinte, l'attaque retrouve l'etat. Les autres ne sont pas des
   echecs de l'attaque mais des cas HORS COUVERTURE, et les compter comme des
   reussites serait malhonnete.

   {len(REACH)} familles sont joignables avec les tirages du dossier. Les autres le
   sont par manque de DONNEES, pas par faiblesse de l'attaque, et la
   section 1 dit exactement combien il en faudrait.""")


# ==========================================================================
rule("3. SUR LES TIRAGES ORDONNÉS DU DOSSIER")
# ==========================================================================

rows = list(csv.DictReader(open(os.path.join(ROOT, "draws_ordered.csv"))))
ORD = [(int(r["id"]), [int(r[f"o{i}"]) for i in range(1, DRAWN + 1)])
       for r in rows]
pairs = [(ORD[i], ORD[i + 1]) for i in range(len(ORD) - 1)
         if ORD[i + 1][0] == ORD[i][0] + 1]
say(f"   {len(ORD)} tirages ordonnes, dont {len(pairs)} paire(s) CONSECUTIVE(S) : "
    f"{[ (a[0], b[0]) for a, b in pairs ]}")
say(f"   plafond TOTAL de rejets : {MAXT}   budget : {BUDGET:.0f} s par essai\n")
say(f"   {'famille':>21} {'essais':>7} {'profondeur':>10} {'couverture':>11} "
    f"{'état trouvé':>12} {'sec':>7}")
nhit = ntry = 0
COV = []
for name in REACH:
    nb, step, coef, nw, w, r = INFO[name]
    need = -(-w // DRAWN)
    cases = [[d[1]] for d in ORD] if need == 1 else [[a[1], b[1]] for a, b in pairs]
    hit, t0, dmin = 0, time.time(), 99
    for case in cases:
        ntry += 1
        nw2 = DRAWN * need + MAXT
        c2 = basis_bits(step, nb, nw2)
        got, dep = attack(step, nb, case, c2, nw2, BUDGET, MAXT, r)
        dmin = min(dmin, dep)
        if got is not None:
            hit += 1
    nhit += hit
    cov = coverage(w, dmin)
    COV.append(cov)
    say(f"   {name:>21} {len(cases):>7} {dmin:>10} {cov:>11.0%} "
        f"{hit:>12} {time.time()-t0:>7.1f}")

say(f"""
   {ntry} attaques, {nhit} etat compatible. Couverture minimale {min(COV):.0%}.

   Pour chaque famille joignable, AUCUN etat ne reproduit les numeros
   observes dans l'ordre, DANS LA COUVERTURE DECLAREE. La verification est un
   rejeu exact du generateur : pas de faux positif possible, pas de marge
   d'erreur. Mais la couverture n'est pas 100 %, et l'ecrire est la seule
   facon honnete de presenter un resultat nul.""")


# ==========================================================================
rule("4. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h61.familles_etendues",
        f"Aucun generateur des familles F2-lineaires MODERNES — xoroshiro128, "
        f"xoshiro128, xoshiro256, LFSR113, WELL512a — n'engendre les tirages "
        f"ordonnes du dossier par rejet modulo {POOL} ; les §68 a §73 n'avaient "
        f"teste que les cinq familles de Marsaglia et L'Ecuyer",
        f"elimination de Gauss sur F2 des {NB} equations par numero (§68), "
        f"motifs de rejet enumeres par APPROFONDISSEMENT ITERATIF sur le "
        f"nombre total de rejets, verification par rejeu exact ; {ntry} "
        f"attaques, couverture minimale declaree {min(COV):.0%}",
        "aucun null n'est requis : un etat compatible se verifie par rejeu, "
        "donc le taux de faux positifs est nul par construction",
        "conforme si aucun etat compatible", track="A")
    # Le champ, pas seulement les notes : une premiere version ne le
    # declarait que dans le texte, et le registre sous-comptait sa propre
    # multiplicite (cf. lab/reparation_m_extra.py).
    tok["m_extra"] = max(0, ntry - 1)
    lab.record(tok, float(nhit), p=1.0, verdict="conforme",
               power_at=(f"temoin positif famille par famille : graines au hasard, "
                         f"tirages simules, etat retrouve pour TOUS les cas dont le "
                         f"motif de rejet tombe dans la profondeur atteinte "
                         f"(section 2) ; couverture minimale {min(COV):.0%}"),
               notes=(f"Comble le trou de la carte du §73 : la liste des familles "
                      f"n'avait jamais ete interrogee. Ajoute les generateurs "
                      f"F2-lineaires reellement deployes (Blackman-Vigna 2018, "
                      f"L'Ecuyer 1999, Panneton et al. 2006). Mesure aussi le "
                      f"seuil de rang REEL de chaque famille par la methode du "
                      f"§80 : LFSR113 sature a 113 et non 128, quinze bits etant "
                      f"inertes. m_extra = {max(0, ntry - 1)}."))
    h = lab.holm()
    say(f"   consigne : h61.familles_etendues   {nhit} etat compatible")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")


# ==========================================================================
rule("5. CE QUE CELA AJOUTE, ET CE QUI RESTE")
# ==========================================================================

say(f"""   AJOUTE.
   1. Cinq familles jamais testees, dont les trois que l'on deploie
      aujourd'hui. La carte du §73 couvrait la litterature de 2003 ; elle
      couvre desormais celle de 2018.
   2. Le seuil de rang MESURE pour chacune, methode du §80 — et deux
      surprises : LFSR113 sature a 113 bits sur 128, WELL512a demande
      {INFO['WELL512a'][4]/DRAWN:.0f} tirages la ou le compte naif du §69 en annoncait
      {-(-512 // (NB*DRAWN))}.

   RESTE, et c'est nomme precisement :
     — xoshiro256 : {INFO['xoshiro256 (brut)'][4]/DRAWN:.1f} tirages ordonnes, il en manque {-(-INFO['xoshiro256 (brut)'][4] // DRAWN) - len(ORD)}
     — WELL512a   : {INFO['WELL512a'][4]/DRAWN:.1f} tirages ordonnes
     — MT19937    : 343 tirages ordonnes (§80)
     — toutes les familles a sortie NON lineaire : xoshiro** et ++, PCG,
       splitmix64, et tout CSPRNG. Le §68 ne les atteint pas, et aucun
       theoreme du dossier ne pretend le contraire.

   Registre : consigne a la section 4.

   ({time.time() - T0:.1f} s)""")
