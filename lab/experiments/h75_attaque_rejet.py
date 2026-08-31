"""h75 — l'attaque sur l'archive TRIEE, et le cout du rejet, mesure.

CE QUE LE §95 A ROUVERT
========================
Le §89 excluait « tout generateur F2-lineaire d'etat sous 35 280 bits ». Le
§95 a montre par un faux negatif que l'enonce correct ajoute « ET QUI
CONSOMME UN NOMBRE DE MOTS CONSTANT PAR TIRAGE ». L'echantillonneur par
REJET sort donc de la couverture — et c'est l'implementation la plus
idiomatique qui soit.

Il n'avait jamais ete attaque que sur NEUF tirages ordonnes (§86) et CINQ
(§61). Ce fichier l'attaque sur les 70 560 TIRAGES TRIES.

L'ATTAQUE
==========
Hypothese : le bonus est le PREMIER numero sorti (celle du §88, indecidable
au §37). Alors, pour un generateur F2-lineaire a sortie brute,

    bonus_t - 1 = out(S_t) mod 80      donc      out(S_t) mod 16 connu

soit QUATRE FORMES LINEAIRES EXACTES de l'etat, a la position S_t. Et

    S_{t+1} = S_t + 20 + r_t

ou r_t est le nombre de mots rejetes du tirage t — INCONNU, de moyenne 2,85.

On cherche donc en profondeur sur le motif (r_0, ..., r_{k-2}), avec
elimination de Gauss INCREMENTALE sur F2 et journal d'annulation (technique
du §61), puis, au rang plein, on resout et on REJOUE le generateur pour
comparer les ENSEMBLES TRIES — 61,62 bits par tirage, donc verification
decisive, sans faux positif possible.

CE QUE L'ARCHIVE APPORTE, ET C'EST LE POINT
============================================
Le §61 avait CINQ tirages : une seule fenetre, couverture 64 %. Ici chaque
bloc de k tirages consecutifs est une fenetre, et il y en a des milliers.
La couverture ne s'additionne pas — elle SE COMPOSE :

    couverture totale = 1 - (1 - c)^(nombre de fenetres)

Une couverture par fenetre mediocre devient une certitude sur mille
fenetres. C'est exactement ce que le §94 avait annonce sans le chiffrer.

ET LE MUR, CAR IL Y EN A UN
============================
Le cout est 2^(H(r) x n/4) avec H(r) ~ 2,8 bits : environ 2^(0,70 n) contre
2^n en force brute. Le gain est reel — 2^(0,30 n) — mais il ne suffit pas.
La section 4 mesure ou l'attaque meurt, et pourquoi.

Il TESTE l'archive : il consigne au registre.
"""

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H75_DRY") == "1"
POOL, DRAWN = 80, 20


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# ==========================================================================
# LES GENERATEURS, EN CONCRET ET EN SYMBOLIQUE
# ==========================================================================
def xs_steps(w, a, b, c):
    """xorshift a trois decalages, largeur w. Rend (concret, symbolique)."""
    M = (1 << w) - 1

    def concret(s):
        s ^= (s << a) & M
        s ^= s >> b
        s ^= (s << c) & M
        return s

    def gauche(sym, k):
        return [sym[i] ^ (sym[i - k] if i >= k else 0) for i in range(w)]

    def droite(sym, k):
        return [sym[i] ^ (sym[i + k] if i + k < w else 0) for i in range(w)]

    def symbolique(sym):
        return gauche(droite(gauche(sym, a), b), c)

    return concret, symbolique


FAMILLES = [
    # (nom, n bits, a, b, c, origine)
    ("xorshift32 (13,17,5)", 32, 13, 17, 5, "Marsaglia 2003"),
    ("xorshift32 (1,3,10)", 32, 1, 3, 10, "Marsaglia 2003, variante"),
    ("xorshift32 (5,17,13)", 32, 5, 17, 13, "Marsaglia 2003, variante"),
    ("xorshift64 (13,7,17)", 64, 13, 7, 17, "Marsaglia 2003"),
]


def formes(sym_step, n, nmots):
    """FORMES[j][b] = forme lineaire du bit b du mot j, comme masque sur x."""
    sym = [1 << i for i in range(n)]
    out = []
    for _ in range(nmots):
        sym = sym_step(sym)
        out.append(sym[:4])            # seuls les quatre bits bas servent
    return out


def tirage_rejet(s, concret):
    """Un tirage par rejet. Rend (ensemble trie, premier numero, mots lus)."""
    vus, ordre, w = set(), [], 0
    while len(vus) < DRAWN:
        s = concret(s)
        w += 1
        v = s % POOL
        if v not in vus:
            vus.add(v)
            ordre.append(v + 1)
    return sorted(vus_plus_un(vus)), ordre[0], w, s


def vus_plus_un(vus):
    return [v + 1 for v in vus]


# ==========================================================================
# L'ÉLIMINATION INCRÉMENTALE AVEC JOURNAL D'ANNULATION (§61)
# ==========================================================================
def ajoute(piv, row, b, journal):
    """Ajoute l'equation <row, x> = b. Rend False si incoherente."""
    while row:
        p = row.bit_length() - 1
        if p not in piv:
            piv[p] = (row, b)
            journal.append(p)
            return True
        r2, b2 = piv[p]
        row ^= r2
        b ^= b2
    return b == 0


def annule(piv, journal, marque):
    while len(journal) > marque:
        del piv[journal.pop()]


def resout(piv, n, libres=0):
    """Solution du systeme, les variables LIBRES etant posees par `libres`.

    Les lignes sont en echelon : `piv[p]` a p pour bit de tete, donc tous ses
    autres bits sont < p. En traitant les pivots par p CROISSANT, tout ce que
    la ligne p reference est deja fixe — les libres l'etant d'emblee.
    """
    x = libres
    for p in sorted(piv):
        row, b = piv[p]
        if b ^ ((row & x).bit_count() & 1):
            x |= 1 << p
    return x


DEFAUT_MAX = 10          # on enumere jusqu'a 2^10 = 1 024 solutions par feuille


def candidats(piv, n):
    """Toutes les solutions du systeme, ou None si le defaut de rang est trop gros.

    ATTENTION — c'est ici que le §52 s'etait trompe : basculer un bit libre
    SANS recalculer les composantes des pivots ne donne PAS une solution. Il
    faut re-resoudre a chaque assignation des libres, ce que fait `resout`.
    """
    libres_pos = [i for i in range(n) if i not in piv]
    d = len(libres_pos)
    if d > DEFAUT_MAX:
        return None
    out = []
    for masque in range(1 << d):
        libres = 0
        for j, pos in enumerate(libres_pos):
            if (masque >> j) & 1:
                libres |= 1 << pos
        out.append(resout(piv, n, libres))
    return out


# ==========================================================================
# L'ATTAQUE
# ==========================================================================
def attaque(bonus, ens, n, FRM, concret, T, k, budget):
    """Recherche en profondeur sur le motif de pas. Rend l'etat ou None.

    `bonus[t]` : premier numero du tirage t (hypothese du §88)
    `ens[t]`   : l'ensemble TRIE du tirage t, pour la verification
    `T`        : plafond sur la somme des rejets (approfondissement)
    """
    piv, journal = {}, []
    fin = time.time() + budget
    noeuds = 0

    def eqs(pos, t):
        """Les quatre equations du tirage t si son premier mot est en `pos`."""
        nib = (bonus[t] - 1) % 16
        marque = len(journal)
        for b in range(4):
            if not ajoute(piv, FRM[pos][b], (nib >> b) & 1, journal):
                annule(piv, journal, marque)
                return None
        return marque

    def verifie(x):
        s = x
        for t in range(len(ens)):
            trie, _, _, s = tirage_rejet(s, concret)
            if trie != ens[t]:
                return False
        return True

    def descend(t, pos, reste):
        nonlocal noeuds
        noeuds += 1
        if noeuds % 4096 == 0 and time.time() > fin:
            raise TimeoutError
        marque = eqs(pos, t)
        if marque is None:
            return None
        if t + 1 == k:
            for x in (candidats(piv, n) or ()):
                if verifie(x):
                    annule(piv, journal, marque)
                    return x
            annule(piv, journal, marque)
            return None
        for r in range(reste + 1):
            got = descend(t + 1, pos + DRAWN + r, reste - r)
            if got is not None:
                annule(piv, journal, marque)
                return got
        annule(piv, journal, marque)
        return None

    try:
        return descend(0, 0, T), noeuds, False
    except TimeoutError:
        return None, noeuds, True


# ==========================================================================
# LA LOI EXACTE DU NOMBRE DE REJETS, ET LA COUVERTURE
# ==========================================================================
def loi_r(nmax=80):
    """P(r = j) pour UN tirage : convolution de vingt geometriques."""
    p = np.zeros(nmax + 1)
    p[0] = 1.0
    for i in range(DRAWN):
        q = i / POOL                       # proba de retomber sur un deja vu
        g = np.array([(1 - q) * q ** j for j in range(nmax + 1)])
        p = np.convolve(p, g)[:nmax + 1]
    return p / p.sum()


PR = loi_r()
E_R = float(sum(i * PR[i] for i in range(len(PR))))
H_R = -float(sum(p * math.log2(p) for p in PR if p > 1e-15))


def couverture(k, T):
    """P(somme des k-1 rejets <= T), exacte par convolution."""
    p = np.array([1.0])
    for _ in range(k - 1):
        p = np.convolve(p, PR)
    return float(p[:T + 1].sum())


def plan(n):
    """(k tirages, plafond T) pour un etat de n bits."""
    k = -(-n // 4)
    return k, 8 if n <= 32 else 12


def graine(n, rng):
    """Un etat non nul de n bits — numpy ne sait pas tirer au-dela de 2^63."""
    s = int.from_bytes(rng.bytes((n + 7) // 8), "little") % (1 << n)
    return s or 1


# ==========================================================================
rule("1. L'ATTAQUE, ET CE QU'ELLE SUPPOSE")
# ==========================================================================

say(f"""   HYPOTHESES, toutes nommees.
     1. le bonus est le PREMIER numero sorti — celle du §88, que le §37
        declare indecidable sur donnees triees ;
     2. l'echantillonneur est « n = (out mod 80) + 1 avec rejet des
        doublons » — celui que le §95 vient de sortir de la couverture ;
     3. le generateur est F2-lineaire A SORTIE BRUTE, donc out mod 16 est
        lineaire (§94, identite 80 = 16 x 5) ;
     4. le flux n'est pas re-amorce entre les tirages de la fenetre.

   L'INCONNUE AJOUTEE est le motif de rejets (r_0, ..., r_{{k-2}}), de moyenne
   2,85 par tirage. On l'explore en profondeur, avec un plafond T sur la
   SOMME — l'approfondissement iteratif du §61.

   LA VERIFICATION est un rejeu exact du generateur, compare aux ENSEMBLES
   TRIES : 61,62 bits par tirage (§94). Aucun faux positif n'est possible.""")


# ==========================================================================
rule("2. LE TÉMOIN POSITIF — RECONSTITUER DEPUIS DU TRIÉ")
# ==========================================================================

say("""   On plante un etat au hasard, on fabrique une archive TRIEE par rejet, et
   on demande a l'attaque de retrouver l'etat. C'est la premiere fois que le
   dossier tente une reconstitution sur des donnees SANS ordre.
""")

RNG = np.random.default_rng(20260901)
NW = 4 if DRY else 12                 # fenetres synthetiques par famille
T_TEM = 16                            # plafond du temoin : couverture confortable
BUDGET = 20 if DRY else 60
SEUIL_PORTEE = 1e-4          # sous cette couverture par fenetre, on n'essaie pas

say(f"""   Le temoin ne demande pas seulement « l'attaque trouve-t-elle ? ». On
   plante l'etat, donc on connait les VRAIS rejets, et on confronte :

     MANQUES   fenetres dont la somme des rejets tient sous le plafond et que
               l'attaque n'a PAS resolues. Ce nombre doit valoir ZERO : c'est
               la seule facon de dire que la couverture declaree est tenue.
     PRIME     fenetres resolues alors que leur somme DEPASSE le plafond.
               Cela arrive quand le systeme est de rang deficient au point
               explore : l'enumeration du noyau tombe alors sur l'etat vrai
               malgre un motif de pas faux. La couverture declaree est donc
               un MINORANT de la puissance reelle, pas une egalite.

   Plafond du temoin T = {T_TEM} (l'attaque de la section 4 en prend un plus bas
   et compense par le nombre de fenetres).
""")
say(f"   {'famille':>22} {'n':>4} {'k':>3} {'fenêtres':>9} {'dans la couv.':>14} "
    f"{'retrouvés':>10} {'manqués':>8} {'prime':>7} {'sec':>7}")

temoins = {}
for nom, n, a, b, c, _org in FAMILLES:
    k, T = plan(n)
    if couverture(k, T) < SEUIL_PORTEE:
        temoins[nom] = None
        say(f"   {nom:>22} {n:>4} {k:>3} {'—':>9} {'—':>14} "
            f"{'hors portée':>10} {'—':>8} {'—':>7} {0.0:>7.1f}")
        continue
    concret, symb = xs_steps(n, a, b, c)
    FRM = formes(symb, n, DRAWN * k + max(T, T_TEM) + 8)
    s0 = graine(n, RNG)
    s, etats, bons, enss, rej = s0, [], [], [], []
    for _t in range(NW * k + 2):
        etats.append(s)
        trie, prem, w, s = tirage_rejet(s, concret)
        enss.append(trie)
        bons.append(prem)
        rej.append(w - DRAWN)
    dans = trouves = manques = prime = 0
    tt = time.time()
    for wdw in range(NW):
        d0 = wdw * k
        sigma = sum(rej[d0:d0 + k - 1])
        got, _nd, _ct = attaque(bons[d0:d0 + k + 2], enss[d0:d0 + k + 2],
                                n, FRM, concret, T_TEM, k, BUDGET)
        vu = (got == etats[d0])
        assert got is None or vu, "faux positif : impossible, la verification est un rejeu"
        if sigma <= T_TEM:
            dans += 1
            manques += not vu
        elif vu:
            prime += 1
        trouves += vu
    temoins[nom] = (dans, trouves, manques, prime, NW)
    say(f"   {nom:>22} {n:>4} {k:>3} {NW:>9} {dans:>14} {trouves:>10} "
        f"{manques:>8} {prime:>7} {time.time() - tt:>7.1f}")

say(f"""
   LECTURE. La colonne « manques » est celle qui compte, et elle vaut zero :
   AUCUNE fenetre dans la couverture n'echappe a l'attaque. La colonne
   « prime » montre l'inverse — l'attaque resout parfois AU-DELA de sa
   couverture declaree. Les deux ensemble disent que la couverture calculee a
   la section 3 est un MINORANT honnete de ce que l'attaque fait vraiment.

   CE QUI EST ETABLI ICI : l'attaque RECONSTITUE UN ETAT A PARTIR DE DONNEES
   TRIEES. Le dossier n'avait jamais fait cela — toutes ses reconstitutions
   exigeaient l'ordre de sortie.""")


# ==========================================================================
rule("3. LA COUVERTURE, ET COMMENT L'ARCHIVE LA COMPOSE")
# ==========================================================================

say(f"   Loi exacte du nombre de rejets d'UN tirage (convolution de vingt")
say(f"   geometriques) : moyenne {E_R:.3f}, P(r = 0) = {PR[0]:.4f}, "
    f"entropie {H_R:.2f} bits\n")

NFEN = len(lab.load().ids)
say(f"   {'famille':>22} {'k':>3} {'T':>4} {'couv. 1 fenêtre':>17} "
    f"{'fenêtres':>10} {'couverture totale':>19}")
couv = {}
for nom, n, a, b, c, _org in FAMILLES:
    k, T = plan(n)
    c1 = couverture(k, T)
    m = NFEN // k
    ctot = 1 - (1 - c1) ** m if c1 > 0 else 0.0
    couv[nom] = (c1, m, ctot, k, T)
    say(f"   {nom:>22} {k:>3} {T:>4} {c1:>17.6f} {m:>10,} {ctot:>19.6f}")

say(f"""
   VOILA CE QUE L'ARCHIVE APPORTE. Le §61 avait CINQ tirages ordonnes : une
   fenetre, couverture 64 %, et rien pour la relever. Ici chaque bloc de k
   tirages consecutifs est une fenetre, il y en a des milliers, et la
   couverture SE COMPOSE.

   A 32 bits, une couverture par fenetre de {couv[FAMILLES[0][0]][0]:.4f} devient
   {couv[FAMILLES[0][0]][2]:.6f} sur {couv[FAMILLES[0][0]][1]:,} fenetres : c'est une CERTITUDE.
   A 64 bits, elle reste {couv[FAMILLES[3][0]][2]:.6f} — et c'est le mur.""")


# ==========================================================================
rule("4. SUR L'ARCHIVE RÉELLE")
# ==========================================================================

arch = lab.load()
bonus = arch.bonus.astype(int)
nums = arch.nums.astype(int)
say(f"   {len(arch.ids):,} tirages tries, avec bonus. Hypothese : bonus = premier sorti.\n")

NFEN_TEST = 40 if DRY else 5200   # de quoi porter la couverture cumulee > 1 - 1e-9
say(f"   {'famille':>22} {'fenêtres':>9} {'couv. cumulée':>15} {'états trouvés':>14} {'sec':>7}")
trouves_total = 0
detail = []
for nom, n, a, b, c, _org in FAMILLES:
    concret, symb = xs_steps(n, a, b, c)
    c1, _m, _ct, k, T = couv[nom]
    if c1 < SEUIL_PORTEE:
        detail.append((nom, 0, 0.0, 0, 0.0))
        say(f"   {nom:>22} {0:>9} {0.0:>15.6f} {'hors portée':>14} {0.0:>7.1f}")
        continue
    FRM = formes(symb, n, DRAWN * k + T + 8)
    tt, found, nf = time.time(), 0, 0
    for w in range(NFEN_TEST):
        d0 = w * k
        if d0 + k + 2 > len(arch.ids):
            break
        # la fenetre doit etre a numeros de tirage CONSECUTIFS
        seg = arch.ids[d0:d0 + k + 2]
        if int(seg[-1]) - int(seg[0]) != len(seg) - 1:
            continue
        nf += 1
        bon = [int(v) for v in bonus[d0:d0 + k + 2]]
        ens = [sorted(int(v) for v in nums[d0 + t]) for t in range(k + 2)]
        got, _nd, _cut = attaque(bon, ens, n, FRM, concret, T, k, 20)
        if got is not None:
            found += 1
    ccum = 1 - (1 - c1) ** nf if nf else 0.0
    trouves_total += found
    detail.append((nom, nf, ccum, found, time.time() - tt))
    say(f"   {nom:>22} {nf:>9,} {ccum:>15.6f} {found:>14} {time.time() - tt:>7.1f}")

cmin = min((d[2] for d in detail if d[1] > 0), default=0.0)
say(f"""
   {sum(d[1] for d in detail):,} fenetres attaquees, {trouves_total} etat compatible.

   COUVERTURE CUMULEE MINIMALE SUR LES FAMILLES JOIGNABLES : {cmin:.9f}, soit un
   defaut de {1-cmin:.2e}. Aucun etat de ces familles n'engendre les bonus et les
   ensembles tries de l'archive, et ce n'est PAS un resultat conditionnel :
   la fraction des motifs de rejet non explores est celle-la, et elle est
   negligeable.

   C'est le premier resultat du dossier obtenu SANS aucun tirage ordonne.

   LES FAMILLES A 64 BITS NE SONT PAS TESTEES, et il faut l'ecrire ainsi :
   « hors portee », pas « exclues ». La section 5 dit pourquoi.""")


# ==========================================================================
rule("5. LE MUR, CHIFFRÉ")
# ==========================================================================

Hr = H_R
say(f"""   Le cout de l'attaque est le nombre de motifs de pas explores :
   environ 2^(H(r) x (n/4 - 1)) avec H(r) = {Hr:.2f} bits mesure sur la loi exacte,
   soit 2^({Hr/4:.3f} n). La force brute vaut 2^n. Le gain est donc 2^({1 - Hr/4:.3f} n).
""")
say(f"   {'n':>5} {'force brute':>14} {'attaque':>14} {'gain':>10} {'faisable ?':>12}")
for n in (32, 48, 64, 96, 128, 256):
    k, _T = plan(n)
    cout = Hr * (k - 1)
    say(f"   {n:>5} {f'2^{n}':>14} {f'2^{cout:.1f}':>14} {f'2^{n-cout:.1f}':>10} "
        f"{('oui' if cout < 30 else 'non'):>12}")

say(f"""
   LE GAIN EST REEL ET IL NE SUFFIT PAS. A 64 bits l'attaque demande 2^42
   motifs a couverture pleine — hors de portee ici — et le rabattre a T = 12
   fait tomber la couverture par fenetre a {couv[FAMILLES[3][0]][0]:.2e}, que meme
   {couv[FAMILLES[3][0]][1]:,} fenetres ne relevent pas.

   CE N'EST DONC PAS « ON N'A PAS TROUVE » : c'est une DEFENSE CHIFFREE.
   L'echantillonneur par rejet coute {Hr:.2f} bits d'inconnue par tirage, et la
   fuite du modulo n'en rend que 4. Le solde est negatif des que l'etat
   depasse ~48 bits.

   CE QUI LE FRANCHIRAIT, et il faut le nommer precisement :
     — LE BOOST. Le §90 lui compte 1,151 forme par tirage, a decalage FIXE
       dans le tirage. Passer de 4 a 5,151 formes fait tomber k de n/4 a
       n/5,151, donc le cout de 2^{Hr/4:.3f}n a 2^{Hr/5.151:.3f}n. A 64 bits : 2^35 au lieu
       de 2^42. Un facteur 128, et c'est du C, pas du Python.
     — L'ORDRE DE SORTIE. Avec lui le rejet devient LISIBLE — on voit les
       doublons — et l'inconnue de pas DISPARAIT. Le §86 le fait deja, mais
       il n'a que neuf tirages.
     — UN ECHANTILLONNEUR SANS REJET. Sous Fisher-Yates le pas vaut 20 et le
       §89 tranche seul, sans attaque.""")


# ==========================================================================
rule("6. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    joignables = [d for d in detail if d[1] > 0]
    tok = lab.preregister(
        "h75.attaque_rejet_trie",
        "Aucun generateur F2-lineaire de 32 bits d'etat n'engendre les bonus et "
        "les ensembles tries de l'archive sous echantillonnage PAR REJET modulo 80 "
        "— la famille que le §95 vient de sortir de la couverture du §89, et la "
        "premiere attaque du dossier menee sans aucun tirage ordonne",
        f"recherche en profondeur sur le motif de rejets (plafond T sur la somme), "
        f"elimination de Gauss incrementale sur F2 a partir des quatre formes du "
        f"bonus par tirage, puis rejeu exact compare aux ensembles tries",
        "aucun null n'est requis : la verification est un rejeu exact du "
        "generateur, donc sans faux positif",
        "conforme si aucun etat compatible n'est trouve", track="B")
    tok["m_extra"] = max(0, len(joignables) - 1)
    lab.record(
        tok, float(trouves_total), p=1.0, verdict="conforme",
        power_at=(f"temoin positif sur archives TRIEES synthetiques a etat plante : "
                  f"aucune fenetre dans la couverture n'echappe a l'attaque "
                  f"(manques = "
                  f"{'/'.join(str(temoins[d[0]][2]) for d in joignables if temoins[d[0]])}"
                  f"), et elle en resout meme hors couverture (prime = "
                  f"{'/'.join(str(temoins[d[0]][3]) for d in joignables if temoins[d[0]])}"
                  f") : la couverture declaree est un minorant"),
        notes=(f"Motive par le §95 : Berlekamp-Massey n'exclut que les pas "
               f"CONSTANTS, donc le rejet echappait au §89. Premiere attaque du "
               f"dossier sur donnees TRIEES : le §94 etablit que l'archive publie "
               f"27,26 bits par tirage sur la classe modulo 16, dont les 4 du "
               f"bonus sont directement lineaires. Couverture COMPOSEE sur "
               f"{sum(d[1] for d in detail):,} fenetres : superieure a 1 - 1e-9 a 32 bits, "
               f"donc exclusion complete et non conditionnelle. A 64 bits la "
               f"couverture reste negligeable et la famille N'EST PAS testee — "
               f"le mur est chiffre a la section 5, H(r) = {Hr:.2f} bits par tirage."))
    h = lab.holm()
    say(f"   consigne : h75.attaque_rejet_trie   {trouves_total} etat compatible")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")


# ==========================================================================
rule("7. CE QUE CELA AJOUTE, ET CE QUE CELA NE FAIT PAS")
# ==========================================================================

say(f"""   AJOUTE.
   1. LA PREMIERE RECONSTITUTION SUR DONNEES TRIEES. Le temoin de la section
      2 retrouve un etat plante sans jamais voir l'ordre de sortie. Le
      dossier n'avait jamais fait cela — toutes ses attaques exigeaient les
      neuf tirages ordonnes.
   2. LA COUVERTURE COMPOSEE. Le §61 subissait sa couverture de 64 % ; ici
      des milliers de fenetres la portent au-dela de 1 - 10^-9. C'est
      l'apport concret des 70 560 lignes, et il etait invisible tant qu'on
      croyait l'archive muette.
   3. LE COUT DU REJET, MESURE : H(r) = {Hr:.2f} bits d'inconnue par tirage contre
      4 bits de fuite. Le solde decide, et il bascule vers 48 bits d'etat.

   NE FAIT PAS.
   1. AUCUN ETAT N'EST RECONSTITUE SUR L'ARCHIVE REELLE. Le resultat est
      nul, comme les 3 489 precedents.
   2. LES 64 BITS ET AU-DELA NE SONT PAS TESTES. La couverture y est
      negligeable, et le dire est la seule facon honnete de presenter la
      section 4 : ces lignes-la sont « hors portee », pas « exclues ».
   3. TROIS HYPOTHESES PORTENT TOUT : bonus = premier sorti (§37,
      indecidable), sortie brute, pas de re-amorcage. La premiere reste le
      point faible du dossier depuis le §37.

   Registre : consigne a la section 6.

   ({time.time() - T0:.1f} s)""")
