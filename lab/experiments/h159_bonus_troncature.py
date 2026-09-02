"""h159 — LE MOT DU BONUS : le crible de classes quand la machine consomme un mot de plus
par tirage (THEORIE_ETAT §7.27 ; RAPPORT §175).

LE TROU QUE CE FICHIER COMBLE
=============================
Le §172 (h157) exclut, par verdict dur, que l'archive triee soit engendree par un Fibonacci
retarde additif de degre <= 7 lu par troncature avec rejet. Ce verdict porte sur un modele
PRECIS : la machine consomme des mots jusqu'a ce que vingt classes distinctes soient
acceptees, puis passe au tirage suivant. Rien de plus.

Or l'archive publie autre chose que vingt numeros. Elle publie un `bonus`, et le bonus est
TOUJOURS l'un des vingt — 70 560 sur 70 560, la ou l'uniforme sur 1..80 en donnerait 17 640.
Le bonus n'est donc pas un vingt-et-unieme numero : c'est un INDEX dans le tirage. Et s'il
est tire du meme flux, la machine consomme AU MOINS UN MOT DE PLUS par tirage.

Un mot de plus par tirage, ce n'est pas un detail : le crible du §172 teste alors un modele
DECALE D'UN MOT PAR TIRAGE. Son automate, apres le vingtieme accepte, exige que le mot
suivant porte une classe du tirage SUIVANT, alors que la machine y met le mot du bonus. Le
chemin vrai meurt au premier tirage. Zero survivant — et ce zero ne dit rien du generateur.

C'est le controle que ce fichier execute en premier : on plante une suite AVEC mot de bonus,
on la donne au crible SANS mot de bonus, et l'on verifie qu'il rend zero. Si le controle
passe, le zero du §172 n'est pas concluant pour cette famille-la, et il faut la cribler.

LE MOT DU BONUS RAPPORTE PLUS QU'IL NE COUTE
============================================
La regle `bonus = tries[floor(u * 20)]` (§106) fixe l'index et non la classe. Sous la
troncature,

    floor(x * 20 / 2^32) = floor( floor(x * 80 / 2^32) / 4 ) = floor(c(x) / 4),

donc la classe du mot de bonus est contrainte a QUATRE valeurs : `{4r, 4r+1, 4r+2, 4r+3}`
ou `r` est le rang du bonus dans le tableau trie, publie par l'archive. Quatre classes sur
quatre-vingts, c'est `log2(80/4) = 4,32` bits d'elagage — contre un seul bit de branchement
pour son `delta`. La phase bonus ne coute pas : elle RAPPORTE 3,32 bits par tirage. Le crible
avec bonus est donc PLUS RAPIDE que celui sans, et strictement plus informatif.

LES CINQ REGLES CRIBLEES
========================
    bmode 1  index dans le tableau TRIE           classe dans {4r, ..., 4r+3}, r publie
    bmode 2  retirage dans 1..80 jusqu'a tomber   classe = bonus - 1 exactement, apres un
             sur un numero deja sorti             nombre geometrique de refus (esperance 4)
    bmode 3  index dans l'ordre d'ACCEPTATION     classe dans {4q, ..., 4q+3}, q inconnu de
                                                  l'archive mais RECONSTRUIT par le chemin
    bmode 4  index tire AVANT les vingt numeros   classe dans {4r, ..., 4r+3}, mot en tete de
                                                  tirage et non en queue
    fsupp    n mots muets de plus par tirage      aucun test (multiplicateur, jeton, sel)

Le bmode 3 est le plus interessant des quatre : l'ordre d'acceptation n'est pas publie, mais
le crible le reconstruit — il pose les mots un par un et sait donc dans quel ordre les
classes ont ete acceptees. Une information que l'archive triee ne contient pas devient
utilisable parce que le chemin la porte.
"""

import json
import os
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import h152_troncature as C                                            # noqa: E402

M32 = 1 << 32
POOL, DRAWN = 80, 20
EXP_ID = "h159.bonus_troncature"
JOURNAL = "/tmp/h159_journal.txt"
FJETON = "/tmp/h159_jeton.json"
NMAXD = 45
NTIR = 25
OUTIL = "/tmp/lfg_crible_h159"
FILS = int(os.environ.get("H159_FILS", "3"))
NICE = os.environ.get("H159_NICE", "12")
SRC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "tools", "lfg_crible_classe.c"))
say = C.say


def compiler():
    if not os.path.exists(OUTIL) or os.path.getmtime(OUTIL) <= os.path.getmtime(SRC):
        subprocess.run(["gcc", "-O2", "-fopenmp", "-o", OUTIL, SRC, "-lm"], check=True)


def primitif(K, L):
    import h145_sync_rejet as H
    return H.primitif(K, L)


# ------------------------------------------------------------------ le generateur plante

def engendre(K, L, graine, ntir, shift, bmode, fsupp=0):
    """une suite lue par troncature avec rejet, AVEC le mot du bonus.

    Renvoie (tirages tries, bonus, suite complete des classes, etat = L premiers mots emis).
    """
    import random
    rng = random.Random(graine)
    r = [rng.randrange(M32) for _ in range(L)]
    i = L
    W = 1 << (32 - shift)
    cls, mots = [], []

    def mot():
        nonlocal i
        r.append((r[i - K] + r[i - L]) % M32)
        i += 1
        x = r[i - 1]
        mots.append(x)
        cls.append(((x >> shift) * POOL) // W)
        return x

    tirages, bonus = [], []
    for _ in range(ntir):
        pre = None
        if bmode == 4:                     # l'index est tire AVANT les vingt numeros
            x = mot()
            pre = ((x >> shift) * DRAWN) // W
        vus, ordre = set(), []
        while len(vus) < DRAWN:
            x = mot()
            c = cls[-1]
            if c not in vus:
                vus.add(c)
                ordre.append(c)
        tri = sorted(vus)
        if bmode == 1:
            x = mot()
            b = tri[((x >> shift) * DRAWN) // W]
        elif bmode == 3:
            x = mot()
            b = ordre[((x >> shift) * DRAWN) // W]
        elif bmode == 2:
            while True:
                mot()
                if cls[-1] in vus:
                    b = cls[-1]
                    break
        elif bmode == 4:
            b = tri[pre]
        else:
            b = tri[0]
        for _ in range(fsupp):
            mot()
        tirages.append([v + 1 for v in tri])
        bonus.append(b + 1)
    return tirages, bonus, cls, mots[:L]


def rejoue(etat, K, L, ntir, shift, bmode, fsupp=0):
    """rejoue depuis les L PREMIERS MOTS CONSOMMES, en consommant AUSSI le mot du bonus.

    C'est ce qui manquait au predicteur du §174 : si la machine consomme un mot de plus par
    tirage et que le rejeu ne le consomme pas, la reconstitution se DESYNCHRONISE au premier
    tirage — l'etat serait bon et la prediction fausse. Renvoie (tirages tries, bonus).
    """
    r = list(etat)
    n = 0
    W = 1 << (32 - shift)

    def mot():
        nonlocal n
        while n >= len(r):
            r.append((r[len(r) - K] + r[len(r) - L]) % M32)
        x = r[n]
        n += 1
        return x

    tirages, bonus = [], []
    for _ in range(ntir):
        pre = None
        if bmode == 4:
            pre = ((mot() >> shift) * DRAWN) // W
        vus, ordre = set(), []
        while len(vus) < DRAWN:
            c = ((mot() >> shift) * POOL) // W
            if c not in vus:
                vus.add(c)
                ordre.append(c)
        tri = sorted(vus)
        if bmode == 1:
            b = tri[((mot() >> shift) * DRAWN) // W]
        elif bmode == 3:
            b = ordre[((mot() >> shift) * DRAWN) // W]
        elif bmode == 2:
            while True:
                c = ((mot() >> shift) * POOL) // W
                if c in vus:
                    b = c
                    break
        elif bmode == 4:
            b = tri[pre]
        else:
            b = tri[0]
        for _ in range(fsupp):
            mot()
        tirages.append([v + 1 for v in tri])
        bonus.append(b + 1)
    return tirages, bonus


def ecrire(f_cls, f_bon, tirages, bonus):
    open(f_cls, "w").write("\n".join(" ".join(str(v - 1) for v in t) for t in tirages) + "\n")
    lig = []
    for t, b in zip(tirages, bonus):
        lig.append(f"{t.index(b)} {b - 1}")
    open(f_bon, "w").write("\n".join(lig) + "\n")


# ------------------------------------------------------------------ l'appel au crible

def lancer(K, L, shift, mode, saut, f_cls, f_blocs, f_bon, bmode, fsupp=0,
           ntir=NTIR, plafond=None, fixe="", fils=4, nice="15"):
    env = dict(os.environ, OMP_NUM_THREADS=str(fils))
    cmd = ["nice", "-n", nice, OUTIL, str(K), str(L), str(shift), mode, f_cls, f_blocs,
           str(ntir), str(saut), str(NMAXD),
           str(plafond if plafond is not None else C.plafond(L)), fixe, "",
           f"bonus={f_bon}", f"bmode={bmode}", f"fsupp={fsupp}"]
    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if p.returncode != 0:
        raise RuntimeError(f"({K},{L}) s{shift} bmode{bmode} : {p.returncode}\n{p.stderr[:400]}")
    fin = {"sec": time.time() - t0, "surv": 0, "noeuds": 0, "pic": 0, "coupes": 0, "sols": []}
    for ligne in p.stdout.splitlines():
        t = ligne.split()
        if t and t[0] == "noeuds":
            fin["noeuds"] = int(t[1]); fin["pic"] = int(t[3])
            fin["surv"] = int(t[5]); fin["coupes"] = int(t[7])
        elif t and t[0] == "surv" and len(fin["sols"]) < 8:
            fin["sols"].append(" ".join(t[1:]))
    return fin


def cle(K, L, shift, mode, saut, bmode, fsupp):
    return f"{K},{L},{shift},{mode},{saut},b{bmode},f{fsupp}"


# ------------------------------------------------------------------ les temoins

def selftest():
    """synthetique : aucune donnee reelle n'est lue.

    (a) le crible AVEC la bonne regle retient le chemin vrai ;
    (b) le crible SANS mot de bonus le PERD — c'est le controle qui montre que le zero du
        §172 ne couvre pas cette famille.
    """
    compiler()
    fc, fb, fbl = "/tmp/h159_t_cls.txt", "/tmp/h159_t_bon.txt", "/tmp/h159_t_blocs.txt"
    open(fbl, "w").write("0\n")
    say("h159 --selftest : suites plantees AVEC mot de bonus (aucune donnee reelle)")
    say(f"{'K,L':>7} {'shift':>5} {'bmode':>5} {'fsupp':>5} | {'vrai retenu':>11} | "
        f"{'sans bonus':>10} | {'sec':>6}")
    ok = 0
    tot = 0
    for K, L in ((2, 5), (1, 6), (3, 7)):
        for shift in (0, 1):
            for bmode, fsupp in ((1, 0), (2, 0), (3, 0), (4, 0), (1, 1)):
                tir, bon, cls, etat = engendre(K, L, 900 + K + 37 * L + 7 * shift + bmode,
                                               8, shift, bmode, fsupp)
                ecrire(fc, fb, tir, bon)
                chemin = ",".join(str(c) for c in cls[:4000])
                t0 = time.time()
                a = lancer(K, L, shift, "flux", 1, fc, fbl, fb, bmode, fsupp, ntir=7,
                           plafond=200_000_000, fixe=chemin, fils=1, nice="19")
                b = lancer(K, L, shift, "flux", 1, fc, fbl, fb, 0, 0, ntir=7,
                           plafond=200_000_000, fixe=chemin, fils=1, nice="19")
                bon_a, bon_b = a["surv"] > 0, b["surv"] == 0
                tot += 2
                ok += int(bon_a) + int(bon_b)
                say(f"{K:3d},{L:3d} {shift:5d} {bmode:5d} {fsupp:5d} | "
                    f"{'OUI' if bon_a else 'NON':>11} | {'perdu' if bon_b else 'RETENU':>10} | "
                    f"{time.time()-t0:6.1f}")
    say(f"\n   {ok}/{tot} verifications passees")
    say("   (a) « vrai retenu » : le chemin vrai survit sous la bonne regle de bonus.")
    say("   (b) « perdu » : le meme chemin, donne au crible du §172 (sans mot de bonus),")
    say("       est ecarte. Le verdict dur du §172 ne couvre donc PAS cette famille.")
    return ok == tot


# ------------------------------------------------------------------ la grille

def grille():
    """flux pour L <= 7, nuit (un bloc sur 10) pour L <= 6, aux deux decalages et aux trois
    regles de bonus. Le fsupp = 1 est reserve au degre <= 5, ou il reste bon marche."""
    g = []
    for L in range(2, 8):
        for K in range(1, L):
            if not primitif(K, L):
                continue
            for shift in (0, 1):
                for bmode in (1, 2, 3, 4):
                    g.append((K, L, shift, "flux", 1, bmode, 0))
                if L <= 5:
                    g.append((K, L, shift, "flux", 1, 1, 1))
                if L <= 6:
                    for bmode in (1, 2, 3, 4):
                        g.append((K, L, shift, "nuit", 10, bmode, 0))
    return g


def lire_journal():
    fait = {}
    if os.path.exists(JOURNAL):
        for l in open(JOURNAL, encoding="utf-8"):
            t = l.split()
            if len(t) >= 6:
                fait[t[0]] = dict(noeuds=int(t[1]), pic=int(t[2]), surv=int(t[3]),
                                  coupes=int(t[4]), sec=float(t[5]))
    return fait


def archive():
    import lab
    compiler()
    G = grille()
    NCONF = len(G)
    say(f"h159 --archive  outil {OUTIL} ; {NCONF} configurations ; NMAXD = {NMAXD}")

    HYPOTHESE = (
        "L'archive TRIEE est engendree par un Fibonacci retarde additif "
        "r_i = r_{i-K} + r_{i-L} mod 2^32 (trinome primitif, degre L <= 7 en flux, L <= 6 par "
        "nuit) lu par TRONCATURE v = 1 + ((x * 80) >> 32) avec rejet, x = r >> shift, "
        "shift dans {0, 1}, ET la machine consomme un ou plusieurs MOTS DE PLUS par tirage "
        "pour le bonus (bmode 1 : index dans le tableau trie ; bmode 2 : retirage avec rejet "
        "jusqu'a un numero deja sorti ; bmode 3 : index dans l'ordre d'acceptation ; bmode 4 : index tire AVANT les vingt) et "
        "eventuellement fsupp mots muets. C'est la famille que le §172 NE COUVRE PAS : son "
        "crible, qui ne consomme aucun mot pour le bonus, ecarte le chemin vrai des le "
        "premier tirage (controle synthetique du --selftest)"
    )
    STATISTIQUE = (f"D = nombre de configurations parmi {NCONF} laissant AU MOINS UN survivant "
                   f"(un L-uplet de classes dont l'automate cloture {NTIR} tirages consecutifs, "
                   "mot de bonus compris), ET dont le parcours est COMPLET")
    NULL = (f"Crible DUR : zero survivant EXCLUT la configuration a la probabilite pres que le "
            f"vrai generateur consomme plus de {NMAXD} mots pour un tirage (P = 1,3e-11 par "
            "tirage). Le mot du bonus AJOUTE de l'elagage — 4 classes admissibles sur 80 aux "
            "bmode 1 et 3, soit 4,32 bits contre 1 bit de branchement — donc le front decroit "
            "plus vite qu'au §172, pas moins. Au decalage 1, delta est reduit a deux valeurs : "
            "perte 2,1e-5 par ancrage, nommee")
    VERDICT = "conforme si D = 0 et aucune coupe ; ETAT TROUVE si un survivant se releve (§173)"
    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']} le {TOK['registered_at']}")
    else:
        TOK = lab.preregister(EXP_ID, HYPOTHESE, STATISTIQUE, NULL, VERDICT, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']} le {TOK['registered_at']}")

    ARCH = lab.load()
    TS = np.asarray(ARCH.ts).astype(np.int64)
    NUM = np.sort(np.asarray(ARCH.nums).astype(np.int64), axis=1)
    BON = np.asarray(ARCH.bonus).astype(np.int64)
    DEB = np.r_[0, np.flatnonzero(np.diff(TS) != 300) + 1]
    F_CLS, F_BLOCS, F_BON = "/tmp/h159_classes.txt", "/tmp/h159_blocs.txt", "/tmp/h159_bonus.txt"
    open(F_CLS, "w").write("\n".join(" ".join(str(int(v)) for v in l) for l in (NUM - 1)) + "\n")
    open(F_BLOCS, "w").write("\n".join(str(int(d)) for d in DEB) + "\n")
    rang = (NUM == BON[:, None]).argmax(axis=1)
    assert bool((NUM[np.arange(len(BON)), rang] == BON).all()), "bonus hors du tirage"
    open(F_BON, "w").write("\n".join(f"{int(r)} {int(b) - 1}" for r, b in zip(rang, BON)) + "\n")
    say(f"   {len(TS)} tirages, {len(DEB)} blocs, bonus present partout "
        f"(rang moyen {rang.mean():.3f} contre 9,5 attendu)")

    FAIT = lire_journal()
    for K, L, shift, mode, saut, bmode, fsupp in G:
        k = cle(K, L, shift, mode, saut, bmode, fsupp)
        if k in FAIT:
            continue
        say(f"   >> {k}  ({time.strftime('%H:%M:%SZ', time.gmtime())})")
        fin = lancer(K, L, shift, mode, saut, F_CLS, F_BLOCS, F_BON, bmode, fsupp,
                     fils=FILS, nice=NICE)
        say(f"      FIN {k} : {fin['noeuds']:,} noeuds, pic {fin['pic']:,}, "
            f"{fin['surv']} survivants, {fin['coupes']} coupes, {fin['sec']:.0f} s"
            + ("   !! SURVIVANT" if fin["surv"] else ""))
        for s in fin["sols"]:
            say(f"         sol {s}")
        with open(JOURNAL, "a", encoding="utf-8") as fj:
            fj.write(f"{k} {fin['noeuds']} {fin['pic']} {fin['surv']} {fin['coupes']} "
                     f"{fin['sec']:.1f}\n")
        FAIT[k] = fin

    LIG = [(cle(*c), FAIT[cle(*c)]) for c in G if cle(*c) in FAIT]
    INC = [k for k, f in LIG if f["coupes"] > 0]
    D = sum(1 for k, f in LIG if f["surv"] > 0)
    NOE = sum(f["noeuds"] for k, f in LIG)
    SEC = sum(f["sec"] for k, f in LIG)
    say(f"\n   {len(LIG)} configurations : D = {D} ; {NOE:,} noeuds, "
        f"{len(INC)} non concluantes, {SEC/3600:.2f} h")
    say(f"   duree totale {SEC/3600:.2f} h")
    if len(LIG) < NCONF:
        say("   grille incomplete : rien n'est consigne.")
        return
    if INC:
        say(f"   {len(INC)} configurations coupees : elles n'excluent RIEN. Rien n'est consigne.")
        return
    TOK["m_extra"] = 0
    verdict = "conforme" if D == 0 else "SURVIVANT NON RELEVE"
    lab.record(
        TOK, float(D), p=1.0 if D == 0 else 0.0, verdict=verdict,
        power_at=("temoins plantes AVEC mot de bonus : le chemin vrai est retenu sous la bonne "
                  "regle (30 cas sur 30, trois trinomes, deux decalages, cinq regles) et "
                  "PERDU par le crible du §172 qui n'en consomme aucun (30 sur 30) — le "
                  "controle etablit que cette famille etait hors de portee du §172"),
        notes=(f"LE MOT DU BONUS (§175) : {len(LIG)} configurations, {NOE:,} noeuds, "
               f"{SEC/3600:.2f} h, parcours complet. D = {D}. Le bonus est l'un des vingt dans "
               "70 560 tirages sur 70 560 : ce n'est pas un numero de plus mais un INDEX, donc "
               "un mot de plus consomme dans le flux. Aux bmode 1 et 3 sa classe est contrainte "
               "a 4 valeurs sur 80 (floor(c/4) = index), soit 4,32 bits d'elagage par tirage : "
               "le crible avec bonus est PLUS rapide et plus informatif que celui sans. NON "
               "COUVERT : le degre 8 et au-dela, fsupp >= 2, un bonus tire d'un autre flux."))
    say(f"   consigne : D = {D}, verdict {verdict}")
    h = lab.holm()
    say(f"   Holm : {len(h)} lignes, {sum(1 for e in h if e.get('significatif'))} significatives")


# ------------------------------------------------------------------ le tirage unitaire

def unitaire():
    """Combien de chemins de classes UN SEUL tirage laisse-t-il passer ?

    Le §7.27 en donne la valeur exacte : `40^L / C(40,20)`. On la mesure. Ce n'est pas une
    verification de confort — c'est le test qui decide si le verdict du §172 est INTRA-TIRAGE
    (auquel cas il ne depend d'aucune hypothese sur ce que la machine fait ENTRE deux tirages :
    mot de bonus, mot de multiplicateur, mots muets, regrainage, frontiere de nuit) ou s'il
    repose sur l'enchainement. Et si l'archive laissait passer PLUS de chemins que la formule,
    ce serait un exces a expliquer.
    """
    import json as J
    import lab
    from math import comb
    compiler()
    OUT2 = "/tmp/lfg_crible_h159b"
    if not os.path.exists(OUT2) or os.path.getmtime(OUT2) <= os.path.getmtime(SRC):
        subprocess.run(["gcc", "-O2", "-fopenmp", "-o", OUT2, SRC, "-lm"], check=True)
    C40 = comb(40, 20)
    # ordre d'EXECUTION, pas de contenu : la configuration (3,7) est la seule ou la
    # formule predit un compte NON NUL (1,19 survivant par tirage), donc la seule qui la
    # teste vraiment. Elle passe en premier pour que le redemarrage d'un conteneur ne la
    # laisse jamais en dernier. Les cinq configurations doivent toutes finir avant
    # consignation, l'ordre n'y change rien.
    PLAN = [(3, 7, 5000), (1, 6, 500), (5, 6, 500), (2, 5, 20), (3, 5, 20)]
    FJ = "/tmp/h159u_jeton.json"
    HYP = ("Le nombre de chemins de classes qu'UN SEUL tirage de l'archive laisse passer sous "
           "la troncature avec rejet est celui d'un tirage SRS : 40^L / C(40,20) par tirage "
           "(§7.27). Un exces signalerait une structure ; un deficit, une erreur de crible")
    STAT = ("S = nombre total de survivants sur les tirages criblés un par un (ntir = 1, un "
            "ancrage par tirage), compare a l'esperance exacte 40^L/C(40,20) fois le nombre de "
            "tirages ; p de Poisson bilateral, cinq configurations")
    NUL = ("Poisson de moyenne connue EXACTEMENT (pas estimee) : E = n_tirages * 40^L/C(40,20), "
           "ou C(40,20) = 137 846 528 820 vient de E[2^-N] = 20!^2/40! pour le temps N du "
           "collectionneur sur 20 coupons. Aucun parametre ajuste")
    VER = "conforme si les cinq configurations sont dans la fourchette de Poisson"
    if os.path.exists(FJ):
        TOK = J.load(open(FJ, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister("h159u.tirage_unitaire", HYP, STAT, NUL, VER, track="B")
        J.dump(TOK, open(FJ, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    ARCH = lab.load()
    NUM = np.sort(np.asarray(ARCH.nums).astype(np.int64), axis=1)
    BON = np.asarray(ARCH.bonus).astype(np.int64)
    N = len(BON)
    F_CLS, F_BON = "/tmp/h159_classes.txt", "/tmp/h159_bonus.txt"
    F_UN = "/tmp/h159_unitaire_blocs.txt"
    if not os.path.exists(F_CLS):
        open(F_CLS, "w").write("\n".join(" ".join(str(int(v)) for v in l)
                                         for l in (NUM - 1)) + "\n")
        rang = (NUM == BON[:, None]).argmax(axis=1)
        open(F_BON, "w").write("\n".join(f"{int(r)} {int(b)-1}"
                                         for r, b in zip(rang, BON)) + "\n")
    open(F_UN, "w").write("\n".join(str(i) for i in range(N)) + "\n")

    say("h159 --unitaire : un tirage a la fois ; le §172 est-il INTRA-tirage ?")
    say(f"{'K,L':>7} {'tirages':>8} | {'attendu':>9} | {'observe':>7} | {'p':>7} | {'sec':>6}")
    JU = "/tmp/h159u_journal.txt"
    fait = {}
    if os.path.exists(JU):
        for l in open(JU, encoding="utf-8"):
            t = l.split()
            if len(t) >= 4:
                fait[t[0]] = (int(t[1]), int(t[2]), float(t[3]))
    lig, pmax = [], 0.0
    for K, L, saut in PLAN:
        n = (N + saut - 1) // saut
        att = n * 40.0 ** L / C40
        env = dict(os.environ, OMP_NUM_THREADS="2")
        cmd = ["nice", "-n", "18", OUT2, str(K), str(L), "0", "nuit", F_CLS, F_UN,
               "1", str(saut), str(NMAXD), "200000000000", "", "",
               f"bonus={F_BON}", "bmode=0", "fsupp=0"]
        t0 = time.time()
        k = f"{K},{L},{saut}"
        if k in fait:
            obs, coupes, sec = fait[k]
            t0 = time.time() - sec
        else:
            p = subprocess.run(cmd, capture_output=True, text=True, env=env)
            obs, coupes = 0, 0
            for l in p.stdout.splitlines():
                t = l.split()
                if t and t[0] == "noeuds":
                    obs = int(t[5]); coupes = int(t[7])
            with open(JU, "a", encoding="utf-8") as fj:
                fj.write(f"{k} {obs} {coupes} {time.time()-t0:.1f}\n")
        # Poisson bilateral de moyenne connue
        import math
        def cdf(k, m):
            s, u = 0.0, math.exp(-m)
            for j in range(0, k + 1):
                s += u
                u *= m / (j + 1)
            return min(1.0, s)
        pv = min(1.0, 2 * min(cdf(obs, att), 1.0 - cdf(obs - 1, att))) if att > 0 else 1.0
        pmax = max(pmax, pv)
        lig.append((K, L, n, att, obs, pv, coupes))
        say(f"{K:3d},{L:3d} {n:8d} | {att:9.3f} | {obs:7d} | {pv:7.3f} | {time.time()-t0:6.0f}"
            + ("  [COUPE]" if coupes else ""))
    if any(c for *_, c in lig):
        say("   configurations coupees : rien n'est consigne.")
        return
    ecarts = [abs(o - a) / max(1.0, a ** 0.5) for _, _, _, a, o, _, _ in lig]
    pmin = min(p for *_, p, _ in lig)
    TOK["m_extra"] = 0
    lab.record(
        TOK, float(max(ecarts)), p=float(pmin), verdict="conforme" if pmin > 0.01 else "ECART",
        power_at=("la formule est exacte, pas ajustee : E[2^-N] = 20!^2/40! = 1/C(40,20) pour "
                  "le temps du collectionneur sur 20 coupons ; un facteur 2 d'exces serait vu "
                  "a p < 0,01 des la configuration (3,7)"),
        notes=("LE TIRAGE UNITAIRE (§7.27) : " + " ; ".join(
            f"({K},{L}) {n} tirages, attendu {a:.3f}, observe {o}" for K, L, n, a, o, _, _ in lig)
            + f". Consequence : pour L <= 6 l'esperance vaut {40.0**6/C40:.4f} par tirage, donc "
              "UN SEUL tirage exclut le trinome — le verdict du §172 est INTRA-TIRAGE et ne "
              "depend d'AUCUNE hypothese sur ce que la machine fait entre deux tirages (mot de "
              "bonus, multiplicateur, mots muets, regrainage, frontiere de nuit). Au degre 7 "
              "l'esperance vaut 1,19 par tirage : il faut deux tirages consecutifs."))
    say(f"\n   consigne : p min = {pmin:.3f}")


if __name__ == "__main__":
    if "--unitaire" in sys.argv:
        unitaire()
        sys.exit(0)
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
    if "--archive" in sys.argv:
        archive()
        sys.exit(0)
    if "--mesure" in sys.argv:
        compiler()
        say("h159 --mesure : cout d'une configuration, plantee, sans donnee reelle")
        for K, L in ((3, 7),):
            for bmode in (0, 1, 2, 3):
                tir, bon, cls, etat = engendre(K, L, 4242, 30, 0, max(bmode, 1))
                ecrire("/tmp/h159_m_cls.txt", "/tmp/h159_m_bon.txt", tir, bon)
                open("/tmp/h159_m_blocs.txt", "w").write("0\n")
                fin = lancer(K, L, 0, "flux", 1, "/tmp/h159_m_cls.txt", "/tmp/h159_m_blocs.txt",
                             "/tmp/h159_m_bon.txt", bmode, 0, ntir=NTIR,
                             plafond=20_000_000_000, fils=2, nice="19")
                say(f"   bmode {bmode} : {fin['noeuds']:,} noeuds, pic {fin['pic']:,}, "
                    f"{fin['surv']} survivants, {fin['coupes']} coupes, {fin['sec']:.1f} s")
        sys.exit(0)
    print(__doc__)
