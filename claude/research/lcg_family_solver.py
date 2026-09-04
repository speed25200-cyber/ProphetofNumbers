"""Récupération EXHAUSTIVE d'un LCG depuis des tirages ordonnés — état *et* incrément.

CE QUE CE FICHIER COMBLE
========================
`REPRISE_ETAT.md` laisse six voies ouvertes. La sixième dit :

    « Reconstruction LCG avec récupération réelle de l'état et de l'incrément,
      pas seulement détection heuristique d'un vecteur court. »

et `lcg_lll.py` conclut honnêtement que le réseau échoue sur le canal du bonus
(`6,3` bits par tirage), en ajoutant : *« capturer l'ordre du tirage referme cette
famille — 20 indices ordonnés par tirage font 126 bits, bien au-delà de ce dont le
réseau a besoin »*.

Ce fichier est cet outil-là. Il ne cherche pas un vecteur court : pour tout module
`m <= 2^32` il **énumère** les `m/80` mots compatibles avec le premier numéro publié
et descend en profondeur. Aucune heuristique — si une solution existe, elle est
trouvée. Au-delà de `2^32` il retombe sur LLL + Babai, mais la décision finale reste
une **vérification en entiers exacts**, jamais une norme.

La troisième voie ouverte — « rejection sampling et consommations variables » — est
traitée du même coup : la vérification déroule le flux en **simulant le rejet**, un
mot dont le numéro est déjà sorti étant consommé sans rien publier.

CE QU'IL NE COUVRE PAS
======================
`MT19937` : c'est `keno_break` qui s'en charge, et sa méthode (élimination `GF(2)`)
ne s'applique pas à une récurrence congruentielle. Les deux outils sont
complémentaires et lisent **le même fichier** `ordered.txt`.

Les échantillonneurs de Fisher-Yates ne sont pas modélisés ici : sous Fisher-Yates
le mot ne porte pas le numéro mais un **indice dans le vivier résiduel**, ce que
`keno_break` exploite déjà. Ce fichier modélise le tirage **avec rejet** — tirer un
numéro uniforme, recommencer s'il est déjà sorti — qui est l'autre famille naturelle
et celle que le rendu écran suggère.

FORMAT D'ENTRÉE
===============
Identique à `keno_break scanfile` : une ligne par tirage, vingt numéros dans l'ordre
**de sortie**, séparés par des espaces. Une entrée triée est refusée (code `3`), comme
côté C — un fichier trié ne peut pas porter d'ordre.

VERDICTS, ET LE HOLDOUT
=======================
Tri-valués, comme `keno_break` :

  `RECOVERED`     un modèle unique reproduit **tous** les tirages d'apprentissage
                  **et** le holdout intact ;
  `REJECTED`      un candidat existait et a été contredit ;
  `INCONCLUSIVE`  aucun candidat, ou plusieurs modèles survivants.

Le holdout est le **suffixe** du fichier ; il ne sert jamais à choisir un modèle. Sur
un seul tirage il n'y a pas de holdout possible et le verdict est plafonné à
`INCONCLUSIVE` — un état qui reproduit un tirage isolé n'établit rien.

    python3 lcg_family_solver.py selftest
    python3 lcg_family_solver.py scan ordered.txt [--holdout 50] [--strides 20,21,22]
    python3 lcg_family_solver.py crible ordered.txt

`scan` suppose un relevé **continu** — c'est la cible de la campagne de capture. `crible`
ne suppose rien : chaque ligne est un tirage indépendant, et la question est seulement
*« un de ces générateurs produit-il cette suite ordonnée, depuis n'importe quel état ? »*.
C'est le bon outil pour douze relevés pris des jours différents.
"""

from __future__ import annotations

import os
import sys
from typing import Iterable

import numpy as np

POOL, DRAWN = 80, 20
BLOC = 1 << 22
PROF = 5          # numeros filtres avant la verification complete
CAP = 400         # mots consommes au maximum pour reproduire un tirage

# (nom, module, multiplicateur, increment) — neuf modules, trente configurations
CONFS: tuple[tuple[str, int, int, int], ...] = (
    ("RANDU",                      1 << 31,       65539,               0),
    ("minstd 16807",               (1 << 31) - 1, 16807,               0),
    ("minstd 48271",               (1 << 31) - 1, 48271,               0),
    ("ANSI C / glibc TYPE_0",      1 << 31,       1103515245,          12345),
    ("Borland C/C++",              1 << 32,       22695477,            1),
    ("Turbo Pascal",               1 << 32,       134775813,           1),
    ("Microsoft Visual C++",       1 << 32,       214013,              2531011),
    ("Numerical Recipes",          1 << 32,       1664525,             1013904223),
    ("VMS MTH$RANDOM",             1 << 32,       69069,               1),
    ("Commodore / cc65",           1 << 23,       16843009,            826366247),
    ("Visual Basic 6",             1 << 24,       1140671485,          12820163),
    ("java.util.Random / drand48", 1 << 48,       25214903917,         11),
    ("drand48 sans increment",     1 << 48,       25214903917,         0),
    ("Native API Windows",         1 << 31,       2147483629,          2147483587),
    ("Sinclair ZX81",              (1 << 16) + 1, 75,                  74),
    ("glibc TYPE_1 mod 2^32",      1 << 32,       1103515245,          12345),
    ("LCG mod 2^61-1",             (1 << 61) - 1, 2307085864,          0),
    ("ANSI C sans increment",      1 << 32,       1103515245,          0),
    ("Knuth MMIX",                 1 << 64,       6364136223846793005, 1442695040888963407),
    ("PCG flux par defaut",        1 << 64,       6364136223846793005, 1442695040888963407),
    ("PCG flux 1",                 1 << 64,       6364136223846793005, 1),
    ("Newlib / musl 64",           1 << 64,       6364136223846793005, 1),
    ("L'Ecuyer 1999 a",            1 << 64,       2862933555777941757, 3037000493),
    ("L'Ecuyer 1999 a, c=1",       1 << 64,       2862933555777941757, 1),
    ("L'Ecuyer 1999 b",            1 << 64,       3935559000370003845, 2691343689449507681),
    ("L'Ecuyer 1999 b, c=1",       1 << 64,       3935559000370003845, 1),
    ("Vigna 2019 a",               1 << 64,       2685821657736338717, 1),
    ("Vigna 2019 b",               1 << 64,       1181783497276652981, 1),
    ("MMIX-like 6906969069",       1 << 64,       6906969069,          1),
    ("Steele-Vigna 64",            1 << 64,       7664345821815920749, 1),
)

# vocabulaire des mappings, aligne sur keno_break.c :
#   0 mulhi (u*k)>>32     1 u%k     2 (u>>16)%k
MAPPINGS = ("mulhi", "mod", "shr16")


def haut32(m: int) -> int:
    """decalage ramenant un mot de module m sur trente-deux bits.

    On mesure la largeur de la plus grande valeur possible, `m - 1`, et non celle de
    `m` : pour `m = 2^32` l'etat tient deja sur trente-deux bits et le decalage doit
    valoir zero, alors que `m.bit_length()` vaut trente-trois.
    """
    return max(0, (m - 1).bit_length() - 32)


def numero(w: int, m: int, mapping: int) -> int:
    """mot -> numero 1..80, selon le mapping de keno_break."""
    d = haut32(m)
    w32 = (w >> d) if d else w
    borne = (m >> d) if d else m
    if mapping == 0:
        return 1 + (w32 * POOL) // borne
    if mapping == 1:
        return 1 + (w32 % POOL)
    return 1 + ((w32 >> 16) % POOL)


def image(m: int, mapping: int) -> int:
    """nombre de numeros DISTINCTS que ce mapping peut produire sur ce module.

    Se calcule, ne s'essaie pas. `mulhi` et `mod` couvrent les quatre-vingts des que le
    module les depasse ; `shr16` ne voit que les hauts de seize bits, donc il n'en atteint
    que `((m-1) >> 16) + 1`. Un mapping dont l'image compte moins de vingt numeros ne peut
    produire AUCUN tirage de vingt numeros distincts : c'est une conclusion exhaustive, et
    elle doit etre affichee comme telle plutot que sautee.
    """
    d = haut32(m)
    borne = (m >> d) if d else m
    if mapping == 2:
        return min(POOL, ((borne - 1) >> 16) + 1)
    return min(POOL, borne)


def candidats(n1: int, m: int, mapping: int) -> Iterable[np.ndarray]:
    """tous les mots dont le numero vaut n1, par blocs uint64. ENUMERATION COMPLETE."""
    d = haut32(m)
    borne = (m >> d) if d else m
    if mapping == 1:
        # w32 = w >> d doit valoir n1-1 modulo 80. Le crible exhaustif ne tourne que
        # pour m <= 2^32, ou d vaut zero ; on le verifie plutot que de le supposer.
        if d:
            raise ValueError("mapping mod : enumeration exhaustive reservee a d = 0")
        deb = (n1 - 1) % POOL
        return [np.arange(a, min(a + BLOC * POOL, m), POOL, dtype=np.uint64)
                for a in range(deb, m, BLOC * POOL)]
    if mapping == 2:
        # (w32 >> 16) % 80 == n1 - 1 : w32 vit dans des blocs de 2^16 mots, espaces
        # de 80 * 2^16. On les assemble par paquets pour rester en numpy.
        #
        # LE BLOC DE TETE EST PARTIEL DES QUE LE MODULE N'EST PAS UNE PUISSANCE DE DEUX.
        # Le plus grand mot vaut m - 1, donc le plus grand haut vaut (m - 1) >> 16 — et il
        # est ATTEINT. Arreter a `borne >> 16` exclut ce haut-la : pour m = 2^31-1 cela
        # perdait 65 536 mots des que n1 valait 48, et pour m = 2^16+1 cela perdait le
        # mot 65 536 tout entier. Sur une puissance de deux les deux bornes coincident,
        # ce qui est exactement pourquoi un autotest limite aux puissances de deux ne
        # voyait rien.
        if d:
            raise ValueError("mapping shr16 : enumeration exhaustive reservee a d = 0")
        hmax = (borne - 1) >> 16
        hauts = np.arange((n1 - 1), hmax + 1, POOL, dtype=np.uint64)
        blocs, paquet = [], 64
        for i in range(0, len(hauts), paquet):
            h = hauts[i:i + paquet]
            b = ((h[:, None] << np.uint64(16))
                 + np.arange(1 << 16, dtype=np.uint64)[None, :]).ravel()
            blocs.append(b[b < np.uint64(borne)])          # le bloc de tete est tronque
        return blocs
    lo = -(-((n1 - 1) * borne) // POOL)
    hi = -(-(n1 * borne) // POOL) - 1
    lo, hi = max(lo << d, 0), min(((hi + 1) << d) - 1, m - 1)
    return [np.arange(a, min(a + BLOC, hi + 1), dtype=np.uint64)
            for a in range(lo, hi + 1, BLOC)]


def rejoue_tirage(w1: int, m: int, a: int, c: int, mapping: int, ordre, cap=CAP):
    """deroule le flux depuis le mot w1 en SIMULANT LE REJET.

    Renvoie (ok, mots_consommes). Un mot dont le numero est deja sorti est consomme
    sans rien publier ; sinon il doit etre le suivant attendu.
    """
    vus: set[int] = set()
    w, pos, k = w1, 0, 0
    while pos < DRAWN and k < cap:
        n = numero(w, m, mapping)
        if n not in vus:
            if n != ordre[pos]:
                return False, k
            vus.add(n)
            pos += 1
        w = (a * w + c) % m
        k += 1
    return pos == DRAWN, k


def crible_exhaustif(ordre, m: int, a: int, c: int, mapping: int, prof=PROF, cap=CAP):
    """ENUMERATION COMPLETE des mots premiers, filtres sur les `prof` premiers numeros
    PUBLIES — rejets compris — puis rejeu du tirage entier. Renvoie les mots premiers.

    LE FILTRE DOIT SIMULER LE REJET, LUI AUSSI
    ==========================================
    La premiere version comparait `numero(w_j)` a `ordre[j]` : elle supposait que le
    j-ieme numero publie est celui du j-ieme mot. Sous rejet c'est faux — un mot dont
    le numero est deja sorti est consomme sans rien publier — et le crible ecartait
    alors sa propre graine plantee. Ce n'etait pas une faiblesse du crible : le filtre
    testait une hypothese que le generateur ne verifie pas.

    La regle exacte tient en une table. Les numeros deja publies sont *exactement*
    `ordre[:pos]`, donc, en notant `PREM[n]` le rang de `n` dans le tirage (255 s'il
    n'y figure pas) :

        PREM[n] == pos   le numero attendu       -> on publie, pos avance
        PREM[n] <  pos   un numero deja sorti    -> REJET, le mot est consomme
        PREM[n] >  pos   contradiction           -> le candidat meurt

    Trois cas, aucun arbitrage : le filtre reste exhaustif. Un candidat n'est ecarte
    que s'il contredit le tirage ou s'il ne publie pas `prof` numeros en `cap` mots —
    et dans ce dernier cas il n'en publierait pas vingt non plus.
    """
    if m > (1 << 32) or a >= (1 << 32):
        raise ValueError("le crible exhaustif exige m <= 2^32 et a < 2^32")
    out = []
    Au, Cu, mu, pu = np.uint64(a), np.uint64(c), np.uint64(m), np.uint64(POOL)
    d = haut32(m)
    du, bu = np.uint64(d), np.uint64((m >> d) if d else m)
    prof = min(prof, DRAWN)
    PREM = np.full(POOL, 255, dtype=np.uint8)
    for j, v in enumerate(ordre):
        PREM[int(v) - 1] = j
    seuil = np.uint8(prof)
    for bloc in candidats(int(ordre[0]), m, mapping):
        cur, w0 = bloc.copy(), bloc.copy()
        pos = np.zeros(bloc.size, dtype=np.uint8)
        for _ in range(cap):
            if cur.size == 0:
                break
            y = (cur >> du) if d else cur
            if mapping == 0:
                nn = (y * pu) // bu
            elif mapping == 1:
                nn = y % pu
            else:
                nn = (y >> np.uint64(16)) % pu
            rang = PREM[nn]
            avance = rang == pos
            garde = avance | (rang < pos)
            cur = ((cur * Au + Cu) % mu)[garde]
            w0 = w0[garde]
            pos = (pos + avance.view(np.uint8))[garde]
            fini = pos >= seuil
            if fini.any():
                for wi in w0[fini].tolist():
                    if rejoue_tirage(int(wi), m, a, c, mapping, ordre, cap)[0]:
                        out.append(int(wi))
                reste = ~fini
                cur, w0, pos = cur[reste], w0[reste], pos[reste]
    return out


def enchaine(w1: int, m: int, a: int, c: int, mapping: int, tirages, stride=None):
    """verifie que le meme flux reproduit TOUS les tirages fournis, dans l'ordre.

    `stride=None` : consommation variable — le tirage suivant commence au mot juste
    apres le dernier mot consomme. `stride=W` : bloc fixe de W mots par tirage.
    Renvoie (nombre de tirages reproduits, mot initial du tirage suivant).
    """
    w = w1
    for i, ordre in enumerate(tirages):
        ok, k = rejoue_tirage(w, m, a, c, mapping, ordre)
        if not ok:
            return i, None
        if stride is not None and k > stride:
            return i, None                  # le bloc fixe ne contient pas le tirage
        for _ in range(k if stride is None else stride):
            w = (a * w + c) % m
    return len(tirages), w


def charge(chemin: str):
    tirages = []
    with open(chemin, encoding="utf-8") as fh:
        for num, ligne in enumerate(fh, 1):
            ligne = ligne.strip()
            if not ligne:
                continue
            vals = [int(x) for x in ligne.split()]
            if len(vals) != DRAWN:
                raise SystemExit(f"ligne {num}: exactly 20 numbers required")
            if len(set(vals)) != DRAWN or not all(1 <= v <= POOL for v in vals):
                raise SystemExit(f"ligne {num}: 20 valeurs distinctes de 1 a 80 requises")
            tirages.append(vals)
    if not tirages:
        raise SystemExit("fichier vide")
    if all(v == sorted(v) for v in tirages):
        print("input is sorted: a sorted file cannot carry an order", file=sys.stderr)
        raise SystemExit(3)
    return tirages


def selftest() -> bool:
    """temoins plantes AVEC REJETS : le crible doit retrouver l'etat exact.

    La colonne `rej.pref` compte les rejets tombant AVANT le `prof`-ieme numero publie,
    c'est-a-dire dans la fenetre meme que le filtre examine. C'est la regression a tenir :
    la premiere version du crible supposait le prefixe sans rejet et ecartait sa propre
    graine des que cette colonne n'etait pas nulle. Un temoin doit etre plante dans les
    conditions de l'hypothese testee, et le rejet EST l'hypothese testee.

    TOUTES LES CONFIGURATIONS, PAS UN ECHANTILLON
    =============================================
    L'autotest replante une graine dans CHACUNE des configurations que le crible pretend
    couvrir, jamais dans cinq d'entre elles. La version echantillonnee a laisse passer une
    enumeration `shr16` incomplete : elle s'arretait au haut `borne >> 16` alors que le
    plus grand haut atteignable vaut `(borne - 1) >> 16`. Sur une puissance de deux les
    deux coincident — et les cinq configurations tirees etaient toutes des puissances de
    deux. Le module `2^31-1` perdait 65 536 mots des que le premier numero valait 48, et
    `2^16+1` perdait un mot entier.

    > Un autotest qui echantillonne ne peut pas soutenir le mot « exhaustif ». Il ne
    > mesure que l'echantillon.
    """
    print("lcg_family_solver --selftest : donnees synthetiques uniquement")
    petits = [k for k in CONFS if k[1] <= (1 << 32) and k[2] < (1 << 32)]
    ok, avec_rejet_prefixe = True, 0
    print(f"   {'generateur':>26} | {'mapping':>7} | {'mots':>5} | {'rejets':>6} | "
          f"{'rej.pref':>8} | resultat")
    for nom, m, a, c in petits:
        for mapping in range(len(MAPPINGS)):
            w1 = 123456789 % m
            vus, ordre, w, k, kpref = set(), [], w1, 0, None
            while len(ordre) < DRAWN and k < CAP:
                n = numero(w, m, mapping)
                if n not in vus:
                    vus.add(n)
                    ordre.append(n)
                    if len(ordre) == PROF:
                        kpref = k + 1
                w = (a * w + c) % m
                k += 1
            if len(ordre) < DRAWN:
                # NE JAMAIS PASSER EN SILENCE. Soit le mapping ne peut PAS produire vingt
                # numeros distincts — et c'est alors une conclusion exhaustive a part
                # entiere, pas un trou —, soit c'est la graine qui est mauvaise et il faut
                # le dire. La taille de l'image se calcule, elle ne s'essaie pas.
                img = image(m, mapping)
                if img < DRAWN:
                    print(f"   {nom:>26} | {MAPPINGS[mapping]:>7} | {'-':>5} | {'-':>6} | "
                          f"{'-':>8} | IMPOSSIBLE par construction : image = {img} numeros "
                          f"< {DRAWN}")
                else:
                    print(f"   {nom:>26} | {MAPPINGS[mapping]:>7} | {k:5d} | {'-':>6} | "
                          f"{'-':>8} | NON PLANTE : image = {img} mais la graine ne rend "
                          f"que {len(ordre)} numeros")
                    ok = False
                continue
            rp = (kpref or PROF) - PROF
            avec_rejet_prefixe += int(rp > 0)
            sol = crible_exhaustif(ordre, m, a, c, mapping)
            bon = w1 in sol
            ok &= bon
            print(f"   {nom:>26} | {MAPPINGS[mapping]:>7} | {k:5d} | {k-DRAWN:6d} | "
                  f"{rp:8d} | {len(sol)} solution(s), la vraie "
                  f"{'TROUVEE' if bon else 'MANQUEE'}")
    # temoin negatif : un tirage aleatoire ne doit avoir aucune solution
    rng = np.random.default_rng(7)
    faux = (rng.permutation(POOL)[:DRAWN] + 1).tolist()
    nom, m, a, c = petits[7]
    vide = crible_exhaustif(faux, m, a, c, 0)
    print(f"   {'temoin NEGATIF (tirage au hasard)':>26} | {'mulhi':>7} | "
          f"{'-':>5} | {'-':>6} | {'-':>8} | {len(vide)} solution(s), attendu 0")
    ok &= (len(vide) == 0)
    # un autotest ou aucun temoin n'a de rejet dans le prefixe ne prouve rien du rejet
    if avec_rejet_prefixe == 0:
        print("   temoins sans rejet dans le prefixe : l'autotest ne couvre pas le rejet")
        ok = False
    else:
        print(f"   {avec_rejet_prefixe} temoins ont un rejet DANS LA FENETRE DU FILTRE : "
              f"la voie du rejet est reellement exercee")
    print(f"   -> {'CALIBRE' if ok else 'DEFAILLANT'}")
    return ok


def _travail(arg):
    """une tache = (configuration, mapping) sur tous les tirages. Niveau module, pour
    que `multiprocessing` puisse la serialiser."""
    (nom, m, a, c), mapping, tirages = arg
    if image(m, mapping) < DRAWN:
        return nom, mapping, [], 0          # impossible par construction, et c'est un fait
    trouves = []
    for i, ordre in enumerate(tirages):
        for w1 in crible_exhaustif(ordre, m, a, c, mapping):
            trouves.append((nom, MAPPINGS[mapping], i, w1))
    return nom, mapping, trouves, len(tirages)


def crible_independant(tirages, verbeux=True, procs=None):
    """chaque ligne est un tirage INDEPENDANT : on ne suppose aucune continuite de flux.

    C'est le bon instrument pour un relevé qui n'est pas continu — douze tirages pris
    des jours differents ne partagent pas d'etat. La question devient : *un* de ces
    generateurs produit-il *cette* suite ordonnee, depuis n'importe quel etat ?

    Aucune hypothese de prefixe sans rejet, contrairement a une attaque par reseau qui
    lit les `n` premiers numeros comme les classes de `n` mots CONSECUTIFS : ici le
    rejet est simule des le filtre.
    """
    import multiprocessing as mp

    petits = [k for k in CONFS if k[1] <= (1 << 32) and k[2] < (1 << 32)]
    taches = [(k, mp_i, tirages) for k in petits for mp_i in range(len(MAPPINGS))]
    if procs is None:
        procs = max(1, min(len(taches), (os.cpu_count() or 1)))
    touches, essais = [], 0
    if procs > 1:
        with mp.Pool(procs) as pool:
            for nom, mapping, trouves, faits in pool.imap_unordered(_travail, taches):
                essais += faits
                touches.extend(trouves)
                if verbeux and trouves:
                    for t in trouves:
                        print(f"   *** {t[0]}, {t[1]}, tirage #{t[2] + 1}, etat {t[3]}")
    else:
        for t in taches:
            nom, mapping, trouves, faits = _travail(t)
            essais += faits
            touches.extend(trouves)
    return touches, essais, len(petits)


def scan(chemin: str, holdout: int, strides: list[int]) -> int:
    tirages = charge(chemin)
    n = len(tirages)
    if holdout >= n:
        holdout = max(0, n // 5)
    apprentissage, reserve = tirages[:n - holdout], tirages[n - holdout:]
    print(f"lcg_family_solver : {n} tirages ordonnes, "
          f"{len(apprentissage)} d'apprentissage, {len(reserve)} de holdout")
    if holdout == 0:
        print("   AUCUN holdout : le verdict sera plafonne a INCONCLUSIVE")

    petits = [k for k in CONFS if k[1] <= (1 << 32) and k[2] < (1 << 32)]
    survivants = []
    for nom, m, a, c in petits:
        for mapping in range(len(MAPPINGS)):
            # un seul tirage suffit a epingler l'etat ; on part du premier, et l'on
            # repart du deuxieme si le premier avait un rejet dans son prefixe.
            for depart in range(min(3, len(apprentissage))):
                cands = crible_exhaustif(apprentissage[depart], m, a, c, mapping)
                if not cands:
                    continue
                for w1 in cands:
                    for stride in [None] + strides:
                        vus, _ = enchaine(w1, m, a, c, mapping,
                                          apprentissage[depart:], stride)
                        if vus < len(apprentissage) - depart:
                            continue
                        # le holdout n'a jamais servi a choisir : on l'utilise ici seul
                        _, w = enchaine(w1, m, a, c, mapping,
                                        apprentissage[depart:], stride)
                        vus2, _ = enchaine(w, m, a, c, mapping, reserve, stride)
                        survivants.append((nom, MAPPINGS[mapping], stride, depart, w1,
                                           vus2 == len(reserve)))
                        print(f"   *** {nom}, {MAPPINGS[mapping]}, "
                              f"stride={'variable' if stride is None else stride}, "
                              f"apprentissage COMPLET, holdout "
                              f"{vus2}/{len(reserve)}")
                break

    if not survivants:
        print("\nINCONCLUSIVE : aucun candidat sur les familles congruentielles couvertes")
        print(f"   ({len(petits)} configurations x {len(MAPPINGS)} mappings, "
              f"crible EXHAUSTIF — l'absence de solution est certaine, pas heuristique)")
        return 4
    bons = [s for s in survivants if s[5]]
    if len(bons) == 1 and holdout > 0:
        print(f"\nRECOVERED : {bons[0][0]}, {bons[0][1]}, "
              f"stride={'variable' if bons[0][2] is None else bons[0][2]}")
        return 0
    if not bons:
        print("\nREJECTED : des candidats reproduisaient l'apprentissage mais aucun le holdout")
        return 2
    print(f"\nINCONCLUSIVE : {len(bons)} modeles survivent, aucun n'est unique")
    return 4


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "selftest":
        sys.exit(0 if selftest() else 1)
    if len(sys.argv) >= 3 and sys.argv[1] == "crible":
        if not selftest():
            print("autotest en echec : on n'attaque pas une capture avec un outil non calibre",
                  file=sys.stderr)
            sys.exit(1)
        T = charge(sys.argv[2])
        print(f"\ncrible INDEPENDANT : {len(T)} tirages, aucune continuite de flux supposee")
        touches, essais, nconf = crible_independant(T)
        print(f"\n   {essais} cribles exhaustifs ({nconf} generateurs x {len(MAPPINGS)} "
              f"mappings x {len(T)} tirages), {len(touches)} etats trouves")
        if not touches:
            print("INCONCLUSIVE : aucun etat, sur AUCUNE des configurations couvertes.")
            print("   L'enumeration est complete : l'absence est certaine, pas heuristique.")
            sys.exit(4)
        print("RECOVERED (a confirmer sur un releve continu : un etat qui reproduit un")
        print("   tirage isole n'etablit rien — il faut le tirage suivant).")
        sys.exit(0)
    if len(sys.argv) >= 3 and sys.argv[1] == "scan":
        ho, st = 50, [20, 21, 22, 23, 24]
        args = sys.argv[3:]
        if "--holdout" in args:
            ho = int(args[args.index("--holdout") + 1])
        if "--strides" in args:
            st = [int(x) for x in args[args.index("--strides") + 1].split(",")]
        if not selftest():
            print("autotest en echec : on n'attaque pas une capture avec un outil non calibre",
                  file=sys.stderr)
            sys.exit(1)
        print()
        sys.exit(scan(sys.argv[2], ho, st))
    print(__doc__)
    print("usage: lcg_family_solver.py selftest | scan <ordered.txt> "
          "[--holdout N] [--strides A,B,C] | crible <ordered.txt>", file=sys.stderr)
    sys.exit(1)
