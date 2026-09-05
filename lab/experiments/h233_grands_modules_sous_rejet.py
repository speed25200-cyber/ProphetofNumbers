"""h233 — LES GRANDS MODULES SUR LES TREIZE TIRAGES ORDONNÉS, EXACTS SOUS LE REJET
(RAPPORT §259).

LE TROU QUE LE §248 NOMMAIT
===========================
Le crible exhaustif du §248 ferme la moitié `m ≤ 2³²` de la famille congruentielle sur les
tirages ordonnés, rejet simulé dès le filtre, sans heuristique. Au-dessus de `2³²`, il écrit :
*« seul le réseau reste — avec son hypothèse de préfixe sans rejet, donc avec le trou du
tableau »* : le §246 lit les `n` premiers numéros comme `n` mots CONSÉCUTIFS, ce qui n'est
vrai qu'avec probabilité `Π(1 − j/80)` — `0,42` pour `n = 12` —, et il tranche par Babai, qui
peut manquer une solution qui existe. Le §251 a retiré Babai pour le flux du bonus ; il ne l'a
pas retiré pour les tirages ordonnés, et personne n'a retiré l'hypothèse du préfixe.

CE QUE FAIT CELUI-CI
====================
Deux choses, et les deux sont exactes.

  1. **Le rejet est ÉNUMÉRÉ, pas supposé absent.** Avant le `n`-ième numéro publié, `r` mots
     ont pu être consommés sans rien publier — un mot dont le numéro est déjà sorti. Un MOTIF
     de rejet, c'est l'ensemble des positions de ces `r` mots muets parmi les `n + r` premiers
     mots ; le premier mot ne peut pas être muet, le dernier est le `n`-ième publié. Pour
     chaque motif, les numéros publiés sont à des positions CONNUES, et les mots muets ne
     contraignent rien : ils sont simplement retirés du réseau. Tout motif à `r ≤ R = 4` mots
     muets est passé ; la part des tirages réels dont le préfixe a plus de `R` rejets est
     calculée EXACTEMENT (loi du nombre de mots muets, `k/80` au `k`-ième numéro) et
     rapportée — c'est le seul résidu, et il est chiffré :

         n =  9 (m = 2^48)    : P(r > 4) = 0,00042      495 motifs
         n = 11 (m = 2^61-1)  : P(r > 4) = 0,00232    1 001 motifs
         n = 12 (m = 2^64)    : P(r > 4) = 0,00474    1 365 motifs

  2. **Babai est remplacé par l'énumération exacte du pavé** (`lab/cvp_exact.py`, §251) : tous
     les points du réseau des positions publiées dans le pavé des contraintes, en entiers et
     en `Fraction`. La base est d'abord réduite par le LLL flottant de `lab/lll.py` — une
     transformation unimodulaire, donc le MÊME réseau — puis passée à l'arithmétique exacte,
     qui ne dépend de la réduction que pour le nombre de nœuds visités, jamais pour la réponse.

Chaque point rendu donne le premier mot `w₀` ; il est REJOUÉ en entiers sur le tirage entier,
rejet simulé, et doit reproduire les vingt numéros dans l'ordre. `126` bits de contrainte
contre `64` d'état : une fausse alerte est impossible, et un survivant serait réel.

LA GRILLE
=========
Les `15` générateurs congruentiels à constantes publiées de module `> 2³²` du dossier : les
trois de la famille élargie (§232 : `java.util.Random`/`drand48` avec et sans incrément sur
`2⁴⁸`, le LCG sur `2⁶¹−1`) et les douze `mod 2⁶⁴` du §223 (Knuth MMIX, PCG, L'Ecuyer 1999,
Vigna 2019, Steele-Vigna…). Deux règles de sortie — troncature pleine, troncature des 32 bits
hauts — comme aux §223 et §246 ; la règle « modulo 80 » n'est PAS couverte ici : sur un module
puissance de deux, `x mod 80` n'est pas un intervalle de `x`, et le réseau ne la lit pas.
Treize tirages ordonnés (§258), et la même grille sur les témoins.

TÉMOINS, DANS LA MÊME PASSE
===========================
Pour chaque module et chaque règle, un tirage est PLANTÉ depuis un état tiré au sort, avec au
moins un rejet dans son préfixe (et au plus `R`) — la voie que le §246 n'exerçait pas — et
il traverse exactement la même grille que les tirages réels : l'état planté doit être rendu.
Un témoin NÉGATIF (vingt numéros dans un ordre au hasard) traverse la grille du plus grand
module et doit rendre zéro. Les témoins sont dans la même passe que l'archive parce que la
base réduite d'un motif sert à tous les tirages ; leur verdict est lu en premier, et un
témoin manqué invalide la passe entière.
"""

import csv
import itertools
import json
import math
import os
import random
import sys
import time
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cvp_exact as CV                                                   # noqa: E402
from lll import lll as lll_flottant                                      # noqa: E402
import h211_familles_elargies as H11                                     # noqa: E402
import h202_attaque_par_reseau as H2                                     # noqa: E402

RACINE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CSV = os.path.join(RACINE, "lab", "draws_ordered.csv")
POOL, DRAWN = 80, 20
EXP_ID = "h233.grands_modules_sous_rejet"
FJETON = "/tmp/h233_jeton.json"
CACHE = os.environ.get("H233_CACHE", "/tmp/h233_faits.json")
R_MAX = 4
CAP = 300
NOEUDS_MAX = 2_000_000
REGLES = (0, 1)
NOMS_REGLES = ("troncature pleine", "troncature des 32 bits hauts")

GRANDS = ([k for k in H11.CONFS if k[1] > (1 << 32)]
          + [(n, 1 << 64, a, c) for n, a, c in H2.LCGS])


def say(*a):
    print(*a, flush=True)


def n_pour(m: int) -> int:
    """numeros publies mis au reseau : assez pour que m / 80^n < 2^-6."""
    return math.ceil((math.log2(m) + 6) / math.log2(POOL))


def module(m: int) -> str:
    """le nom du module, pour les etiquettes : 2^48, 2^61-1, 2^64."""
    if m & (m - 1) == 0:
        return f"2^{m.bit_length() - 1}"
    return f"2^{m.bit_length()}-1" if m == (1 << m.bit_length()) - 1 else str(m)


def residu(n: int, R: int) -> float:
    """P(plus de R mots muets avant le n-ieme numero publie), EXACTE."""
    d = {0: Fraction(1)}
    for k in range(1, n):
        p, q = Fraction(k, POOL), Fraction(POOL - k, POOL)
        nd = {}
        for r, pr in d.items():
            s, w = 0, q
            while r + s <= 60:
                nd[r + s] = nd.get(r + s, 0) + pr * w
                s, w = s + 1, w * p
        d = nd
    return float(sum(v for r, v in d.items() if r > R))


def motifs(n: int, r: int):
    """positions des n numeros publies parmi n + r mots, pour chaque choix des r muets."""
    for muets in itertools.combinations(range(1, n + r - 1), r):
        yield tuple(p for p in range(n + r) if p not in muets)


def nb_motifs(n: int, R: int) -> int:
    return sum(math.comb(n + r - 2, r) for r in range(R + 1))


def increments(a, c, m, L):
    out, cc = [0], 0
    for _ in range(L - 1):
        cc = (a * cc + c) % m
        out.append(cc)
    return out


def base_positions(a, m, pos):
    row = [pow(a, p, m) for p in pos]
    return [row] + [[m if j == i else 0 for j in range(len(pos))] for i in range(len(pos))]


def preparer(a, m, pos):
    red = [v for v in lll_flottant(base_positions(a, m, pos)) if any(v)]
    return red, CV.prepare(red)


def numero(w, m, regle):
    return 1 + H11.classe(w, m, POOL, regle)


def rejoue(w0, a, c, m, ordre, regle, cap=CAP):
    """w0 est le PREMIER mot ; on deroule en simulant le rejet, il faut les 20 numeros."""
    vus, w, pos, k = set(), w0, 0, 0
    while pos < DRAWN and k < cap:
        v = numero(w, m, regle)
        if v not in vus:
            if v != ordre[pos]:
                return False
            vus.add(v)
            pos += 1
        w = (a * w + c) % m
        k += 1
    return pos == DRAWN


def engendre(w0, a, c, m, regle):
    """le tirage ordonne que produit l'etat w0, et les positions de ses numeros publies."""
    vus, w, ordre, posp, k = set(), w0, [], [], 0
    while len(ordre) < DRAWN and k < CAP:
        v = numero(w, m, regle)
        if v not in vus:
            vus.add(v)
            ordre.append(v)
            posp.append(k)
        w = (a * w + c) % m
        k += 1
    return ordre, posp


def temoin(nom, m, a, c, regle, n, graine):
    """un etat au sort dont le prefixe de n numeros contient 1 a R_MAX rejets."""
    rng = random.Random(graine)
    while True:
        w0 = rng.getrandbits(m.bit_length()) % m
        if w0 == 0:
            continue
        ordre, posp = engendre(w0, a, c, m, regle)
        if len(ordre) < DRAWN:
            continue
        r = posp[n - 1] - (n - 1)
        if 1 <= r <= R_MAX:
            return w0, ordre, r


def _travail(arg):
    """une tache = un generateur x un nombre de muets r : tous les motifs a r muets, chaque
    base reduite UNE fois et servie a tous les tirages (reels et temoins) x deux regles."""
    (nom, m, a, c), r, tirages = arg
    n = n_pour(m)
    cinc = increments(a, c, m, n + R_MAX + 1)
    t0 = time.time()
    enums = incomplets = noeuds = 0
    trouves = []
    for pos in motifs(n, r):
        red, prep = preparer(a, m, pos)
        for etiquette, ordre in tirages:
            for regle in REGLES:
                los, his = [], []
                for i, p in enumerate(pos):
                    lo, hi = H11.intervalle(ordre[i] - 1, m, POOL, regle)
                    los.append(lo - cinc[p])
                    his.append(hi - cinc[p])
                pts, nd, cp = CV.points_dans_pave(red, los, his, NOEUDS_MAX, prep)
                enums += 1
                noeuds += nd
                incomplets += (not cp)
                for v in pts:
                    w0 = int(v[0]) % m
                    if rejoue(w0, a, c, m, ordre, regle):
                        trouves.append((etiquette, regle, w0, pos))
    return nom, r, enums, incomplets, noeuds, trouves, time.time() - t0


if __name__ == "__main__":
    import multiprocessing as mp
    import lab

    lignes = list(csv.DictReader(open(CSV, encoding="utf-8")))
    REELS = [(f"tirage {r['id']}", [int(r["o%d" % i]) for i in range(1, DRAWN + 1)])
             for r in lignes]

    # --- les temoins, un par (module, regle), plantes AVEC rejet dans le prefixe
    TEMOINS, ATTENDUS = [], {}
    graine = 233
    for nom, m, a, c in GRANDS:
        if any(t[0].endswith(f"m={module(m)}") for t in TEMOINS):
            continue
        n = n_pour(m)
        for regle in REGLES:
            w0, ordre, r = temoin(nom, m, a, c, regle, n, graine)
            graine += 1
            et = f"temoin {nom} regle {regle} m={module(m)}"
            TEMOINS.append((et, ordre))
            ATTENDUS[(et, regle)] = (nom, w0, r)
    rng = random.Random(233_233)
    NEGATIF = ("temoin NEGATIF (ordre au hasard)", rng.sample(range(1, POOL + 1), DRAWN))

    par_module = {}
    for nom, m, a, c in GRANDS:
        par_module.setdefault(m, []).append(nom)
    nb_enum = sum(nb_motifs(n_pour(m), R_MAX) * len(REGLES)
                  * (len(REELS) + sum(1 for t in TEMOINS if t[0].endswith(f"m={module(m)}"))
                     + (1 if m == max(par_module) else 0))
                  for nom, m, a, c in GRANDS)
    residus = {m: residu(n_pour(m), R_MAX) for m in par_module}

    HYP = (f"Aucun des {len(GRANDS)} generateurs congruentiels a constantes publiees de module "
           f"> 2^32 du dossier ({len(H2.LCGS)} mod 2^64 du §223, trois de la famille elargie du "
           f"§232 : 2^48 avec et sans increment, 2^61-1) ne produit l'un des {len(REELS)} "
           f"tirages ordonnes, sous la troncature pleine ni sous la troncature des 32 bits "
           f"hauts, depuis AUCUN etat, sous AUCUN motif de rejet a R <= {R_MAX} mots muets "
           f"avant le n-ieme numero publie. LE TROU : le §246 lisait les n premiers numeros "
           f"comme n mots consecutifs (vrai avec probabilite 0,42 pour n = 12) et tranchait par "
           f"Babai, qui peut manquer une solution ; le §251 a retire Babai pour le bonus, pas "
           f"pour les tirages ordonnes, et personne n'a retire l'hypothese du prefixe. ICI : "
           f"les motifs de rejet sont ENUMERES (positions des r mots muets parmi n + r, premier "
           f"mot jamais muet, dernier publie), les mots muets retires du reseau, et TOUS les "
           f"points du reseau des positions publiees dans le pave des contraintes sont "
           f"enumeres exactement (lab/cvp_exact.py), apres une reduction LLL flottante "
           f"unimodulaire qui ne change pas le reseau. n = {n_pour(1 << 48)} pour 2^48, "
           f"{n_pour((1 << 61) - 1)} pour 2^61-1, {n_pour(1 << 64)} pour 2^64 ; motifs : "
           f"{nb_motifs(n_pour(1 << 48), R_MAX)}, {nb_motifs(n_pour((1 << 61) - 1), R_MAX)}, "
           f"{nb_motifs(n_pour(1 << 64), R_MAX)}. Le residu — part des tirages reels dont le "
           f"prefixe a plus de {R_MAX} rejets — est exact : "
           + ", ".join(f"{residus[m]:.5f} pour {m.bit_length()} bits" for m in sorted(par_module))
           + f". Chaque point est rejoue en entiers sur le tirage entier, rejet simule. Temoins "
           f"dans la meme passe : un tirage plante par module et par regle, avec 1 a {R_MAX} "
           f"rejets dans son prefixe, doit etre rendu ; un ordre au hasard doit rendre zero. "
           f"La regle modulo 80 n'est PAS couverte au-dessus de 2^32, et c'est dit")
    STAT = (f"nombre d'etats reproduisant les vingt numeros ordonnes d'un tirage reel, sur "
            f"{nb_enum} enumerations exactes (generateur x motif x tirage x regle), les "
            f"temoins comptes a part")
    NUL = (f"EXACTE et combinatoire : 126 bits de contrainte contre au plus 64 d'etat, moins "
           f"de 2^-62 par enumeration qu'un faux etat passe le rejeu ; et l'enumeration ne "
           f"peut MANQUER aucun point du pave (drapeau 'complet' exige)")
    VER = (f"ETAT RELEVE si un etat reproduit un tirage reel entier ; conforme sinon, et "
           f"l'absence est alors CERTAINE pour ces {len(GRANDS)} generateurs, ces deux regles, "
           f"tout motif a <= {R_MAX} rejets ; NON CALIBRE si un temoin plante n'est pas rendu ou "
           f"si le temoin negatif rend un etat ; INCOMPLET pour toute enumeration qui atteint "
           f"le plafond de noeuds")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h233 : {len(GRANDS)} generateurs > 2^32, {len(REELS)} tirages ordonnes, "
        f"{len(TEMOINS)} temoins plantes + 1 negatif, R <= {R_MAX}")
    for m in sorted(par_module):
        n = n_pour(m)
        say(f"   m = {module(m):>7} : n = {n:>2}, {nb_motifs(n, R_MAX):>5} motifs, "
            f"residu P(r > {R_MAX}) = {residus[m]:.5f}   [{', '.join(par_module[m])}]")
    for (et, regle), (nom, w0, r) in ATTENDUS.items():
        say(f"   {et} : {r} rejet(s) dans le prefixe")
    say(f"   {nb_enum} enumerations exactes annoncees")

    deja = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    taches = []
    for conf in GRANDS:
        nom, m, a, c = conf
        tirs = list(REELS) + [t for t in TEMOINS if t[0].endswith(f"m={module(m)}")]
        if m == max(par_module):
            tirs.append(NEGATIF)
        for r in range(R_MAX + 1):
            if f"{nom}|{r}" not in deja:
                taches.append((conf, r, tirs))
    # les grosses taches d'abord, pour equilibrer les coeurs
    taches.sort(key=lambda t: -nb_motifs(n_pour(t[0][1]), R_MAX) * math.comb(
        n_pour(t[0][1]) + t[1] - 2, t[1]))
    say(f"\n   {len(taches)} taches a faire, {len(deja)} reprises du cache")

    procs = max(1, min(len(taches), int(os.environ.get("H233_PROCS", os.cpu_count() or 1))))
    t0 = time.time()
    if taches:
        with mp.Pool(procs) as pool:
            for nom, r, enums, inc, nd, trouves, dt in pool.imap_unordered(_travail, taches):
                deja[f"{nom}|{r}"] = {"enum": enums, "incomplets": inc, "noeuds": nd,
                                      "trouves": [list(t[:3]) + [list(t[3])] for t in trouves],
                                      "dt": dt}
                json.dump(deja, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
                say(f"      {nom:>28} r={r} : {enums:>6} enumerations, {inc} incompletes, "
                    f"{len(trouves)} etat(s), {dt:6.0f}s   [{time.time()-t0:6.0f}s]")

    # --- lecture : temoins d'abord
    say("\n   temoins :")
    calibre = True
    for (et, regle), (nom, w0, r) in ATTENDUS.items():
        rendus = {t[2] for k, v in deja.items() if k.split("|")[0] == nom
                  for t in v["trouves"] if t[0] == et and t[1] == regle}
        ok = w0 in rendus
        calibre &= ok
        say(f"      {et:<60} {r} rejet(s) : etat plante {'RENDU' if ok else 'MANQUE'}"
            f"{'' if len(rendus) <= 1 else f' ({len(rendus)} etats)'}")
    negatifs = [t for v in deja.values() for t in v["trouves"] if t[0] == NEGATIF[0]]
    say(f"      temoin negatif : {len(negatifs)} etat(s), attendu 0")
    calibre &= not negatifs

    enums = sum(v["enum"] for v in deja.values())
    incomplets = sum(v["incomplets"] for v in deja.values())
    noeuds = sum(v["noeuds"] for v in deja.values())
    dt_tot = sum(v["dt"] for v in deja.values())
    reels = [(k.split("|")[0], t) for k, v in deja.items() for t in v["trouves"]
             if t[0].startswith("tirage ")]
    say(f"\n   l'archive : {enums} enumerations exactes, {incomplets} incompletes, "
        f"{noeuds} noeuds, {dt_tot:.0f}s de calcul")
    for nom, t in reels:
        say(f"   *** {nom}, {NOMS_REGLES[t[1]]}, {t[0]}, etat {t[2]}, positions {t[3]}")

    if not calibre:
        verdict = "NON CALIBRE"
    elif reels:
        verdict = "ETAT RELEVE"
    elif incomplets:
        verdict = "INCOMPLET"
    else:
        verdict = "conforme"
    say(f"\n   {verdict}")

    TOK["m_extra"] = 0
    lab.record(
        TOK, float(len(reels)), p=float(1.0 if not reels else 2.0 ** -62),
        verdict=verdict,
        power_at=(f"detection CERTAINE : {len(ATTENDUS)} temoins plantes avec 1 a {R_MAX} "
                  f"rejets dans le prefixe traversent la meme grille et sont "
                  f"{'tous rendus' if calibre else 'PAS TOUS RENDUS'} ; le temoin negatif rend "
                  f"{len(negatifs)}. L'enumeration est exacte et complete "
                  f"({incomplets} incompletes sur {enums}). Non couvert : la regle modulo 80 "
                  f"au-dessus de 2^32, les motifs a plus de {R_MAX} rejets (residu exact "
                  + ", ".join(f"{residus[m]:.5f} pour {module(m)}" for m in sorted(par_module))
                  + "), et les constantes non publiees"),
        notes=(f"LES GRANDS MODULES SOUS LE REJET (§259) — le §246 supposait le prefixe sans "
               f"rejet et tranchait par Babai ; ici les motifs de rejet sont enumeres (R <= "
               f"{R_MAX}) et le pave est enumere exactement. {len(GRANDS)} generateurs, "
               f"{len(REELS)} tirages, 2 regles, {enums} enumerations en {dt_tot:.0f}s, "
               f"{len(reels)} etat(s) sur les tirages reels. {verdict}."))
    say("   consigne.")
