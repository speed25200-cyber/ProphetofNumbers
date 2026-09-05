"""h234 — LA RÈGLE MODULO 80 SUR LES TIRAGES ORDONNÉS : le réseau des QUOTIENTS, et le
canal mod 16 par motif (RAPPORT §260).

CE QUE LE §259 DISAIT DE TROP
=============================
Le §259 écrivait que le réseau « ne lit pas » `x mod 80`, parce que `x mod 80 = r` n'est pas
un intervalle de `x`. C'est vrai et c'est sans conséquence : `x = r + 80·t` avec `t` dans
l'intervalle `[0, (m − 1 − r)/80]`, et la récurrence de `x` devient une récurrence de `t` :

    module premier p       80·t_j ≡ a^{p_j}·(r_0 + 80·t_0) + c_{p_j} − r_j      (mod p)
                           t_j ≡ a^{p_j}·t_0 + b_j  (mod p),  b_j = (a^{p_j}·r_0 + c_{p_j} − r_j)·80^{-1}
                           -> le MEME reseau qu'au §259, sur les quotients, 6,32 bits par numero

    module 2^k             la meme congruence n'a de solution que si
                           D_j = a^{p_j}·r_0 + c_{p_j} − r_j ≡ 0  (mod 16)   <- le canal mod 16
                           puis, en divisant par 16 :  t_j ≡ a^{p_j}·t_0 + (D_j/16)·5^{-1}  (mod 2^{k−4})
                           -> un reseau de module 2^{k−4}, pave de cote 2^{k−4}/5 : 2,32 bits par numero

Le canal `mod 16` est le §226 lu par tirage et par motif : sous `mod 80`, `x mod 16` se LIT
(`x mod 16 = (v − 1) mod 16`), et pour un `(a, c)` connu la suite des résidus aux positions
publiées est entièrement déterminée — pas une hypothèse à faire, pas un état à chercher. Il
exclut ou non, exactement, à `4` bits par numéro.

CE QUI SE RELÈVE ET CE QUI NE SE RELÈVE PAS
============================================
    2^61-1  sous mod 80   n = 11 numeros, 1 001 motifs : le pave est presque vide, l'etat se releve
    2^48    sous mod 80   canal mod 16 (20 numeros), puis reseau des quotients mod 2^44 sur les 20
                          numeros : 2^44 / 5^20 = 0,19 candidat par motif — l'etat se releve
    2^64    sous mod 80   canal mod 16 seul : 58 bits de quotient contre 46 observes, un tirage
                          seul ne releve PAS l'etat ; il EXCLUT ou non, a 2^-80 pres par motif

TÉMOINS
=======
Un tirage planté par module, sous `mod 80`, avec un à quatre rejets dans le préfixe : pour
`2^61−1` et `2^48` l'état doit être rendu ; pour `2^64` le canal doit passer sur le motif
vrai. Un ordre au hasard doit tout faire échouer. Comme au §259, tout est dans la même passe.
"""

import csv
import json
import math
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ICI = os.path.dirname(os.path.abspath(__file__))
_H233 = open(os.path.join(ICI, "h233_grands_modules_sous_rejet.py"), encoding="utf-8").read()
exec(compile(_H233[:_H233.index('if __name__ == "__main__":')], "h233defs", "exec"), globals())

EXP_ID = "h234.modulo_80_par_les_quotients"
FJETON = "/tmp/h234_jeton.json"
CACHE = os.environ.get("H234_CACHE", "/tmp/h234_faits.json")


def puissance_de_deux(m: int) -> bool:
    return m & (m - 1) == 0


def numero2(w):
    return 1 + w % POOL


def rejoue2(w0, a, c, m, ordre, cap=CAP):
    vus, w, pos, k = set(), w0, 0, 0
    while pos < DRAWN and k < cap:
        v = numero2(w)
        if v not in vus:
            if v != ordre[pos]:
                return False
            vus.add(v)
            pos += 1
        w = (a * w + c) % m
        k += 1
    return pos == DRAWN


def engendre2(w0, a, c, m):
    vus, w, ordre, posp, k = set(), w0, [], [], 0
    while len(ordre) < DRAWN and k < CAP:
        v = numero2(w)
        if v not in vus:
            vus.add(v)
            ordre.append(v)
            posp.append(k)
        w = (a * w + c) % m
        k += 1
    return ordre, posp


def temoin2(m, a, c, n, graine):
    rng = random.Random(graine)
    while True:
        w0 = rng.getrandbits(m.bit_length()) % m
        if w0 == 0:
            continue
        ordre, posp = engendre2(w0, a, c, m)
        if len(ordre) < DRAWN:
            continue
        r = posp[n - 1] - (n - 1)
        if 1 <= r <= R_MAX:
            return w0, ordre, r


def n_mod(m: int) -> int:
    """numeros publies au reseau des quotients : 6,32 bits chacun sur un module premier,
    2,32 bits sur 2^k (les 4 bits bas sont deja depenses par le canal mod 16)."""
    if puissance_de_deux(m):
        return DRAWN
    return n_pour(m)


def canal_mod16(a, c, m, cinc, pos, ordre):
    """module 2^k : D_j = a^{p_j} r_0 + c_{p_j} − r_j doit etre nul mod 16 a chaque position."""
    r0 = ordre[0] - 1
    for i, p in enumerate(pos):
        if (pow(a, p, 16) * r0 + cinc[p] - (ordre[i] - 1)) % 16:
            return False
    return True


def reseau_quotients(a, c, m, cinc, pos, ordre, prep_cache):
    """les points (t_j − b_j) du reseau des quotients dans le pave ; rend les x_0 candidats."""
    n = len(pos)
    if puissance_de_deux(m):
        M = m >> 4
        inv = pow(5, -1, M)
        b = []
        for i, p in enumerate(pos):
            D = pow(a, p, m) * (ordre[0] - 1) + cinc[p] - (ordre[i] - 1)
            assert D % 16 == 0
            b.append(((D // 16) * inv) % M)
    else:
        M = m
        inv = pow(POOL, -1, M)
        b = [((pow(a, p, m) * (ordre[0] - 1) + cinc[p] - (ordre[i] - 1)) * inv) % M
             for i, p in enumerate(pos)]
    cle = (M, pos)
    if cle not in prep_cache:
        prep_cache[cle] = preparer(a % M, M, pos)
    red, prep = prep_cache[cle]
    los = [0 - b[i] for i in range(n)]
    his = [(m - 1 - (ordre[i] - 1)) // POOL - b[i] for i in range(n)]
    pts, nd, cp = CV.points_dans_pave(red, los, his, NOEUDS_MAX, prep)
    xs = []
    for v in pts:
        t0 = int(v[0]) % M                      # position 0 : a^0 = 1, b_0 = 0
        xs.append((ordre[0] - 1) + POOL * t0)
    return xs, nd, cp


def _travail2(arg):
    (nom, m, a, c), r, tirages = arg
    n = n_mod(m)
    cinc = increments(a, c, m, n + R_MAX + 1)
    t0 = time.time()
    verifs = passes = enums = incomplets = noeuds = 0
    trouves, prep_cache = [], {}
    p2 = puissance_de_deux(m)
    for pos in motifs(n, r):
        for etiquette, ordre in tirages:
            if p2:
                verifs += 1
                if not canal_mod16(a, c, m, cinc, pos, ordre):
                    continue
                passes += 1
                if m.bit_length() - 1 >= 64:
                    trouves.append((etiquette, "canal", None, pos))
                    continue
            xs, nd, cp = reseau_quotients(a, c, m, cinc, pos, ordre, prep_cache)
            enums += 1
            noeuds += nd
            incomplets += (not cp)
            for x0 in xs:
                if rejoue2(x0, a, c, m, ordre):
                    trouves.append((etiquette, "etat", x0, pos))
    return nom, r, verifs, passes, enums, incomplets, noeuds, trouves, time.time() - t0


if __name__ == "__main__":
    import multiprocessing as mp
    import lab

    lignes = list(csv.DictReader(open(CSV, encoding="utf-8")))
    REELS = [(f"tirage {r['id']}", [int(r["o%d" % i]) for i in range(1, DRAWN + 1)])
             for r in lignes]

    TEMOINS, ATTENDUS = [], {}
    graine = 234
    for nom, m, a, c in GRANDS:
        if any(t[0].endswith(f"m={module(m)}") for t in TEMOINS):
            continue
        w0, ordre, r = temoin2(m, a, c, n_mod(m), graine)
        graine += 1
        et = f"temoin {nom} mod 80 m={module(m)}"
        TEMOINS.append((et, ordre))
        ATTENDUS[et] = (nom, m, w0, r)
    rng = random.Random(234_234)
    NEGATIF = ("temoin NEGATIF (ordre au hasard)", rng.sample(range(1, POOL + 1), DRAWN))

    par_module = {}
    for nom, m, a, c in GRANDS:
        par_module.setdefault(m, []).append(nom)
    residus = {m: residu(n_mod(m), R_MAX) for m in par_module}
    nb_verifs = sum(nb_motifs(n_mod(m), R_MAX)
                    * (len(REELS) + 1 + (1 if m == max(par_module) else 0))
                    for nom, m, a, c in GRANDS)

    HYP = (f"Aucun des {len(GRANDS)} generateurs congruentiels a constantes publiees de module "
           f"> 2^32 ne produit l'un des {len(REELS)} tirages ordonnes sous la regle MODULO 80, "
           f"depuis aucun etat, sous aucun motif de rejet a R <= {R_MAX} mots muets. CE QUE LE "
           f"§259 DISAIT DE TROP : x mod 80 = r n'est pas un intervalle de x, mais x = r + 80 t "
           f"avec t dans [0, (m-1-r)/80], et la recurrence de x est une recurrence de t : sur un "
           f"module premier, t_j = a^p_j t_0 + b_j mod p avec b_j = (a^p_j r_0 + c_p_j - r_j) "
           f"80^-1 — le meme reseau qu'au §259 sur les QUOTIENTS, 6,32 bits par numero, n = "
           f"{n_mod((1 << 61) - 1)} numeros, {nb_motifs(n_mod((1 << 61) - 1), R_MAX)} motifs ; "
           f"sur 2^k, la congruence n'a de solution que si D_j = a^p_j r_0 + c_p_j - r_j est nul "
           f"mod 16 a chaque position publiee — le CANAL MOD 16 du §226 lu par tirage et par "
           f"motif, sans hypothese ni etat, 4 bits par numero —, puis t_j = a^p_j t_0 + (D_j/16) "
           f"5^-1 mod 2^(k-4), un reseau de module 2^(k-4) et un pave de cote 2^(k-4)/5, soit "
           f"2,32 bits par numero : les {DRAWN} numeros y passent, "
           f"{nb_motifs(DRAWN, R_MAX)} motifs. Sur 2^48 l'etat se releve (2^44/5^20 = 0,19 "
           f"candidat par motif, tue par le rejeu) ; sur 2^64 il ne se releve PAS depuis un "
           f"tirage seul (58 bits de quotient contre 46 observes) et seul le canal mod 16 "
           f"tranche, a 16^-20 pres par motif. Residus exacts P(r > {R_MAX}) : "
           + ", ".join(f"{residus[m]:.5f} pour {module(m)}" for m in sorted(par_module))
           + f". Temoins dans la meme passe : un tirage plante par module sous mod 80 avec 1 a "
           f"{R_MAX} rejets — etat rendu pour 2^61-1 et 2^48, canal passe pour 2^64 — et un "
           f"ordre au hasard qui doit tout faire echouer")
    STAT = (f"nombre de tirages reels qu'un generateur reproduit (etat rendu, ou canal mod 16 "
            f"passe pour 2^64), sur {nb_verifs} verifications de motif (generateur x motif x "
            f"tirage), les temoins comptes a part")
    NUL = ("EXACTE : sur 2^k le canal mod 16 est une egalite deterministe a 4 bits par numero "
           "(16^-20 par motif pour un faux passage) ; sur 2^61-1 l'enumeration du pave est "
           "complete et le rejeu des vingt numeros vaut 126 bits contre 61 d'etat")
    VER = (f"ETAT RELEVE (ou CANAL PASSE pour 2^64) si un tirage reel est reproduit ; conforme "
           f"sinon, et l'absence est CERTAINE pour ces {len(GRANDS)} generateurs sous modulo 80 "
           f"et tout motif a <= {R_MAX} rejets ; NON CALIBRE si un temoin plante n'est pas "
           f"rendu ou si l'ordre au hasard passe ; INCOMPLET si une enumeration atteint le "
           f"plafond de noeuds")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h234 : {len(GRANDS)} generateurs > 2^32 sous modulo 80, {len(REELS)} tirages, "
        f"{len(TEMOINS)} temoins + 1 negatif, R <= {R_MAX}")
    for m in sorted(par_module):
        say(f"   m = {module(m):>7} : n = {n_mod(m):>2}, {nb_motifs(n_mod(m), R_MAX):>5} motifs, "
            f"residu {residus[m]:.5f}   [{', '.join(par_module[m])}]")
    for et, (nom, m, w0, r) in ATTENDUS.items():
        say(f"   {et} : {r} rejet(s) dans le prefixe")
    say(f"   {nb_verifs} verifications de motif annoncees")

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
    taches.sort(key=lambda t: -math.comb(n_mod(t[0][1]) + t[1] - 2, t[1]))
    say(f"\n   {len(taches)} taches a faire, {len(deja)} reprises du cache")

    procs = max(1, min(len(taches), int(os.environ.get("H234_PROCS", os.cpu_count() or 1))))
    t0 = time.time()
    if taches:
        with mp.Pool(procs) as pool:
            for nom, r, verifs, passes, enums, inc, nd, trouves, dt in \
                    pool.imap_unordered(_travail2, taches):
                deja[f"{nom}|{r}"] = {"verifs": verifs, "passes": passes, "enum": enums,
                                      "incomplets": inc, "noeuds": nd,
                                      "trouves": [[t[0], t[1], t[2], list(t[3])] for t in trouves],
                                      "dt": dt}
                json.dump(deja, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
                say(f"      {nom:>28} r={r} : {verifs:>6} canaux, {passes} passes, {enums:>5} "
                    f"enumerations, {inc} incompletes, {len(trouves)} rendu(s), {dt:6.0f}s   "
                    f"[{time.time()-t0:6.0f}s]")

    say("\n   temoins :")
    calibre = True
    for et, (nom, m, w0, r) in ATTENDUS.items():
        rendus = [t for k, v in deja.items() if k.split("|")[0] == nom
                  for t in v["trouves"] if t[0] == et]
        if m.bit_length() - 1 >= 64:
            ok = any(t[1] == "canal" for t in rendus)
            say(f"      {et:<50} {r} rejet(s) : canal mod 16 {'PASSE' if ok else 'FERME'} "
                f"sur {sum(1 for t in rendus if t[1] == 'canal')} motif(s)")
        else:
            ok = any(t[1] == "etat" and t[2] == w0 for t in rendus)
            say(f"      {et:<50} {r} rejet(s) : etat plante {'RENDU' if ok else 'MANQUE'}")
        calibre &= ok
    negatifs = [t for v in deja.values() for t in v["trouves"] if t[0] == NEGATIF[0]]
    say(f"      temoin negatif : {len(negatifs)} passage(s), attendu 0")
    calibre &= not negatifs

    verifs = sum(v["verifs"] for v in deja.values())
    passes = sum(v["passes"] for v in deja.values())
    enums = sum(v["enum"] for v in deja.values())
    incomplets = sum(v["incomplets"] for v in deja.values())
    dt_tot = sum(v["dt"] for v in deja.values())
    reels = [(k.split("|")[0], t) for k, v in deja.items() for t in v["trouves"]
             if t[0].startswith("tirage ")]
    say(f"\n   l'archive : {verifs} canaux mod 16 verifies, {passes} passes, {enums} "
        f"enumerations exactes, {incomplets} incompletes, {dt_tot:.0f}s de calcul")
    for nom, t in reels:
        say(f"   *** {nom}, {t[1]}, {t[0]}, etat {t[2]}, positions {t[3]}")

    if not calibre:
        verdict = "NON CALIBRE"
    elif reels:
        verdict = "ETAT RELEVE" if any(t[1] == "etat" for _, t in reels) else "CANAL PASSE"
    elif incomplets:
        verdict = "INCOMPLET"
    else:
        verdict = "conforme"
    say(f"\n   {verdict}")

    TOK["m_extra"] = 0
    lab.record(
        TOK, float(len(reels)), p=float(1.0 if not reels else 2.0 ** -60),
        verdict=verdict,
        power_at=(f"detection CERTAINE : {len(ATTENDUS)} temoins plantes sous modulo 80 avec 1 a "
                  f"{R_MAX} rejets traversent la meme grille — "
                  f"{'tous rendus ou passes' if calibre else 'PAS TOUS'} ; l'ordre au hasard "
                  f"rend {len(negatifs)}. Le canal mod 16 est exact a 4 bits par numero, "
                  f"l'enumeration est complete ({incomplets} incompletes sur {enums}). Non "
                  f"couvert : les motifs a plus de {R_MAX} rejets (residu "
                  + ", ".join(f"{residus[m]:.5f} pour {module(m)}" for m in sorted(par_module))
                  + "), et les constantes non publiees — sauf sur 2^k, ou le §226 les couvre "
                  f"toutes"),
        notes=(f"LA REGLE MODULO 80 PAR LES QUOTIENTS (§260) — le §259 disait que le reseau ne "
               f"lit pas x mod 80 ; il lit t = (x - r)/80. {len(GRANDS)} generateurs, "
               f"{len(REELS)} tirages, {verifs} canaux, {passes} passes, {enums} enumerations "
               f"en {dt_tot:.0f}s, {len(reels)} tirage(s) reel(s) reproduit(s). {verdict}."))
    say("   consigne.")
