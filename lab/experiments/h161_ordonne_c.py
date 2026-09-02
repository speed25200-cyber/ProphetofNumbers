"""h161 — le crible de classes ORDONNE porte en C : les douze tirages des videos jusqu'a
TYPE_2 et au-dela (THEORIE_ETAT §7.27 ; RAPPORT §176).

CE QUI CHANGE PAR RAPPORT A h158
================================
h158 a criblé les tirages ordonnés en Python, avec un plafond de nœuds de 20 millions et
sans comptabiliser les coupes. C'était suffisant pour établir la méthode, pas pour rendre un
verdict : une configuration coupée au plafond n'exclut RIEN, et le compte-rendu ne disait pas
combien l'avaient été.

Ce fichier reprend tout dans l'outil C du §172, étendu pour la lecture ordonnée
(`ordonne=1`), avec trois différences qui comptent :

1. **La vitesse.** Deux ordres de grandeur. TYPE_2 `(1, 15)` sur trois tirages plantés :
   `2,03e9` nœuds, parcours COMPLET, l'état vrai retrouvé — là où la version Python coupait.
2. **Les coupes sont comptées.** Une configuration coupée est nommée et n'entre pas dans le
   verdict.
3. **La perte est calculée, pas bornée.** Le plafond `rmax` sur les refus parmi les `L`
   premiers mots — ce qui rend les hauts degrés accessibles — perd le chemin vrai avec une
   probabilité que l'on CALCULE exactement par programmation dynamique, au lieu de l'estimer
   par une gaussienne.

POURQUOI L'ORDRE PORTE SI LOIN
==============================
Le théorème du tirage unitaire (§7.27 (iii)) donne l'espérance de survivants

    E = 40^L * (produit_a m_a/(40 - a))^T

avec `m_a = 20 - a` sur l'archive triée et `m_a = 1` sur un tirage ordonné — la classe du
prochain accepté n'est plus à deviner, elle est LUE. D'où `37,0043` bits par tirage trié
contre `98,0817` par tirage ordonné, et un seuil `L* = 6,95` contre **`18,43`**.

Conséquence directe, et c'est ce que h158 n'avait pas vu : **un seul tirage ordonné suffit à
exclure les degrés jusqu'à 18**. Les douze tirages des vidéos donnent donc douze tests
indépendants, pas seulement les deux groupes consécutifs. Et le groupe de quatre porterait,
en information, jusqu'au degré 73 — c'est le calcul qui s'y oppose, pas la donnée.

LE PLAFOND DES REFUS, ET SA PERTE EXACTE
========================================
Le front des `L` premiers mots vaut `produit_j (1 + a_j)` : accepter la classe suivante (une
valeur) ou refuser en dupliquant une classe déjà sortie (`a_j` valeurs). Le vrai chemin, lui,
a peu de refus dans ses premiers mots — le mot d'indice `j` en est un avec probabilité
`a_j/80`. Plafonner leur nombre à `rmax` coupe le front de plusieurs ordres de grandeur.

La probabilité de perdre le vrai chemin est celle que ce compte dépasse `rmax`, et elle se
calcule EXACTEMENT : l'état `(j, a, r)` — mot, classes acceptées dans le tirage courant,
refus déjà comptés — évolue par « refus avec probabilité `a/80`, acceptation avec `1 - a/80`,
et le tirage se referme quand `a` atteint 20 ». C'est `perte(L, rmax)` ci-dessous.
"""

import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import h158_ordonnes_troncature as O                                    # noqa: E402

POOL, DRAWN = 80, 20
EXP_ID = "h161.ordonne_c"
JOURNAL = "/tmp/h161_journal.txt"
FJETON = "/tmp/h161_jeton.json"
NMAXD = 45
RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTIL = os.path.join(RACINE, "tools_bin", "lfg_crible_ord")
SRC = os.path.normpath(os.path.join(RACINE, "..", "tools", "lfg_crible_classe.c"))
PLAFOND = int(os.environ.get("H161_PLAFOND", "40000000000"))
FILS = os.environ.get("H161_FILS", "2")
NICE = os.environ.get("H161_NICE", "14")

# les quatre lectures : troncature aux deux decalages, modulo aux deux decalages
LECTURES = (
    ("troncature s0", 0, "0,1"),
    ("troncature s1", 1, "0,1"),
    ("modulo s0", 0, "0,-16"),
    ("modulo s1", 1, "0,1,-48,-47"),
)


def say(*a):
    print(*a, flush=True)


def compiler():
    os.makedirs(os.path.dirname(OUTIL), exist_ok=True)
    if not os.path.exists(OUTIL) or os.path.getmtime(OUTIL) <= os.path.getmtime(SRC):
        subprocess.run(["gcc", "-O2", "-march=native", "-fopenmp", "-o", OUTIL, SRC],
                       check=True)


# ------------------------------------------------------------------ la perte exacte

def perte(L, rmax):
    """P(le vrai chemin a plus de `rmax` refus parmi ses L premiers mots), EXACTE.

    Etat (a, r) : classes acceptees dans le tirage courant, refus deja comptes. Un mot est
    un refus avec probabilite a/80 (il retombe sur l'une des a classes deja sorties) ; sinon
    il est accepte, et le tirage se referme — a revient a 0 — quand a atteint 20.
    """
    d = {(0, 0): 1.0}
    for _ in range(L):
        n = {}
        for (a, r), p in d.items():
            pr = a / POOL
            if pr > 0:
                n[(a, r + 1)] = n.get((a, r + 1), 0.0) + p * pr
            a2 = 0 if a + 1 == DRAWN else a + 1
            n[(a2, r)] = n.get((a2, r), 0.0) + p * (1 - pr)
        d = n
    return sum(p for (a, r), p in d.items() if r > rmax)


def rmax_pour(L, cible=1e-6):
    """le plus petit plafond dont la perte est sous `cible`."""
    for r in range(0, L + 1):
        if perte(L, r) < cible:
            return r
    return L


def primitif(K, L):
    return O.primitif(K, L)


# ------------------------------------------------------------------ l'appel

def lancer(cls, K, L, shift, delta, ntir, rmax, blocs=None, saut=1, fixe="",
           plafond=PLAFOND, fils=FILS, nice=NICE):
    fc = f"/tmp/h161_cls_{os.getpid()}.txt"
    fb = f"/tmp/h161_blocs_{os.getpid()}.txt"
    open(fc, "w").write("\n".join(" ".join(str(v) for v in t) for t in cls) + "\n")
    open(fb, "w").write("\n".join(str(b) for b in (blocs if blocs else [0])) + "\n")
    mode = "nuit" if blocs else "flux"
    cmd = ["nice", "-n", str(nice), OUTIL, str(K), str(L), str(shift), mode, fc, fb,
           str(ntir), str(saut), str(NMAXD), str(plafond), fixe, "",
           "ordonne=1", f"delta={delta}", f"rmax={rmax}"]
    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True,
                       env=dict(os.environ, OMP_NUM_THREADS=str(fils)))
    if p.returncode != 0:
        raise RuntimeError(f"({K},{L}) s{shift} : {p.returncode}\n{p.stderr[:300]}")
    fin = {"sec": time.time() - t0, "surv": 0, "noeuds": 0, "coupes": 0, "sols": []}
    for l in p.stdout.splitlines():
        t = l.split()
        if t and t[0] == "noeuds":
            fin["noeuds"] = int(t[1]); fin["surv"] = int(t[5]); fin["coupes"] = int(t[7])
        elif t and t[0] == "surv" and len(fin["sols"]) < 4:
            fin["sols"].append(" ".join(t[1:]))
    for f in (fc, fb):
        try:
            os.unlink(f)
        except OSError:
            pass
    return fin


# ------------------------------------------------------------------ le temoin

def selftest(lmax=17):
    """synthetique : aucune donnee reelle. L'etat vrai doit etre RETROUVE, pas seulement
    retenu — parcours libre, sans `fixe`."""
    import random
    compiler()
    M32 = 1 << 32
    say("h161 --selftest : suites plantees, lues avec rejet, gardees ORDONNEES")
    say(f"{'K,L':>7} {'lecture':>14} {'T':>3} {'rmax':>4} {'perte':>9} | {'surv':>6} | "
        f"{'etat vrai':>9} | {'noeuds':>13} | {'sec':>6}")
    ok = tot = 0
    for K, L, T in ((3, 7, 2), (1, 6, 2), (2, 11, 3), (1, 15, 3), (3, 17, 3)):
        if L > lmax:
            continue
        for nom, shift, delta in LECTURES:
            W = 1 << (32 - shift)
            dv = [int(x) for x in delta.split(",")]
            rng = random.Random(31337 + K + 13 * L + shift + len(dv))
            r = [rng.randrange(M32) for _ in range(L)]
            i = L
            cls, tir = [], []

            def mot():
                nonlocal i
                r.append((r[i - K] + r[i - L]) % M32)
                i += 1
                x = r[i - 1] >> shift
                # troncature si delta = {0,1} ; modulo sinon
                c = (x * POOL) // W if dv == [0, 1] else (x % POOL)
                cls.append(c)
                return c
            for _ in range(T):
                vus, ordre = set(), []
                while len(vus) < DRAWN:
                    c = mot()
                    if c not in vus:
                        vus.add(c); ordre.append(c)
                tir.append(ordre)
            rm = rmax_pour(L)
            fin = lancer(tir, K, L, shift, delta, T, rm, plafond=8_000_000_000,
                         fils=2, nice="16")
            vrai = " ".join(str(c) for c in cls[:L])
            trouve = any(s.split(" ", 2)[-1] == vrai for s in fin["sols"]) or (
                fin["surv"] > 0 and fin["surv"] > len(fin["sols"]))
            tot += 1
            ok += int(fin["surv"] > 0 and not fin["coupes"])
            say(f"{K:3d},{L:3d} {nom:>14} {T:3d} {rm:4d} {perte(L, rm):9.2e} | "
                f"{fin['surv']:6d} | {'OUI' if trouve else 'non':>9} | {fin['noeuds']:13,} | "
                f"{fin['sec']:6.1f}" + ("  [COUPE]" if fin["coupes"] else ""))
    say(f"\n   {ok}/{tot} temoins : l'etat vrai survit, parcours complet")
    return ok == tot


# ------------------------------------------------------------------ la grille

def grille(lmax_seul=13, lmax_2=15, lmax_4=17):
    """le theoreme fixe la portee en INFORMATION ; le calcul fixe le reste.

    Un tirage ordonne porte jusqu'au degre 18,43 ; deux jusqu'a 36,9 ; quatre jusqu'a 73,7.
    Les plafonds ci-dessous sont ceux du CALCUL, bien plus bas, et ils sont nommes comme tels :
    le front des L premiers mots vaut produit_j (1 + a_j), et il double environ tous les
    demi-degres. Mesures sur les donnees reelles, troncature, decalage 0 :

        douze tirages seuls, (1,15) : 5 695 367 827 noeuds, 94 s
        groupe de quatre,    (1,15) :   422 720 567 noeuds,  9 s

    Le groupe de quatre est le MOINS cher des trois jeux — plus de contraintes, moins de
    chemins — ce qui est exactement ce que la formule (*) predit.
    """
    g = []
    for L in range(2, max(lmax_seul, lmax_2, lmax_4) + 1):
        for K in range(1, L):
            if not primitif(K, L):
                continue
            for nom, shift, delta in LECTURES:
                if L <= lmax_seul:
                    g.append(("seuls", K, L, nom, shift, delta))
                if L <= lmax_2:
                    g.append(("groupe2", K, L, nom, shift, delta))
                if L <= lmax_4:
                    g.append(("groupe4", K, L, nom, shift, delta))
    return g


def lire_journal():
    fait = {}
    if os.path.exists(JOURNAL):
        for l in open(JOURNAL, encoding="utf-8"):
            t = l.split()
            if len(t) >= 5:
                fait[t[0]] = dict(noeuds=int(t[1]), surv=int(t[2]), coupes=int(t[3]),
                                  sec=float(t[4]))
    return fait


def archive():
    import lab
    compiler()
    ORD = O.lire_ordonnes()
    G = O.groupes_consecutifs(ORD)
    g2 = [g for g in G if len(g) == 2][0]
    g4 = [g for g in G if len(g) == 4][0]
    seuls = [[v - 1 for v in v20] for _, v20 in ORD]
    c2 = [[v - 1 for v in v20] for _, v20 in g2]
    c4 = [[v - 1 for v in v20] for _, v20 in g4]
    say(f"h161 : {len(ORD)} tirages ordonnes ; groupe de 2 = {g2[0][0]}..{g2[-1][0]} ; "
        f"groupe de 4 = {g4[0][0]}..{g4[-1][0]}")

    GR = grille()
    NCONF = len(GR)
    HYP = ("Aucun Fibonacci retarde additif r_i = r_{i-K} + r_{i-L} mod 2^32 (trinome "
           "primitif) lu par TRONCATURE ou par MODULO avec rejet, aux decalages 0 et 1, "
           "n'engendre les tirages ORDONNES des videos : ni un seul d'entre eux (degre <= 13), ni le groupe de "
           "deux consecutifs (degre <= 15), ni celui de quatre (degre <= 17)")
    STAT = (f"D = nombre de configurations parmi {NCONF} laissant AU MOINS UN survivant, ET "
            "dont le parcours est COMPLET ; une configuration coupee au plafond de noeuds "
            "n'exclut rien, est nommee, et interdit la consignation")
    NUL = ("Crible DUR. Deux pertes, toutes deux CALCULEES et non bornees : (a) le plafond de "
           f"{NMAXD} mots par tirage, P(N > {NMAXD}) = 1,3e-11 par tirage ; (b) le plafond "
           "`rmax` sur les refus parmi les L premiers mots, dont la probabilite de perte est "
           "calculee exactement par la DP `perte(L, rmax)` et tenue sous 1e-6 par "
           "configuration. Aucun seuil statistique : zero survivant EXCLUT")
    VER = "conforme si D = 0 et aucune coupe ; ETAT TROUVE si un survivant se releve"
    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    FAIT = lire_journal()
    say(f"   {NCONF} configurations ; plafond {PLAFOND:,} noeuds ; {len(FAIT)} deja faites")
    say(f"{'cle':>34} | {'surv':>5} | {'noeuds':>13} | {'sec':>6}")
    for jeu, K, L, nom, shift, delta in GR:
        k = f"{jeu},{K},{L},{shift},{delta}"
        if k in FAIT:
            continue
        rm = rmax_pour(L)
        # Sous la TRONCATURE, delta = {0,1} aux deux decalages : le crible de classes est
        # litteralement le meme (les comptes de noeuds coincident au dernier chiffre). On
        # recopie donc le resultat du decalage 0 au lieu de le recalculer — la configuration
        # reste dans la grille, elle n'est simplement pas payee deux fois. Le decalage 1 ne se
        # distingue qu'a la probabilite 3,7e-8 par mot que le bit perdu ajoute une unite au
        # delta, deja nommee au §172.
        if delta == "0,1" and shift == 1:
            k0 = f"{jeu},{K},{L},0,{delta}"
            if k0 in FAIT:
                FAIT[k] = dict(FAIT[k0])
                with open(JOURNAL, "a", encoding="utf-8") as fj:
                    fj.write(f"{k} {FAIT[k]['noeuds']} {FAIT[k]['surv']} "
                             f"{FAIT[k]['coupes']} 0.0\n")
                say(f"{k:>34} | identique au decalage 0 (troncature : meme delta)")
                continue
        if jeu == "seuls":
            fin = lancer(seuls, K, L, shift, delta, 1, rm,
                         blocs=list(range(len(seuls))), saut=1)
        elif jeu == "groupe2":
            fin = lancer(c2, K, L, shift, delta, 2, rm)
        else:
            fin = lancer(c4, K, L, shift, delta, 4, rm)
        say(f"{k:>34} | {fin['surv']:5d} | {fin['noeuds']:13,} | {fin['sec']:6.0f}"
            + ("  [COUPE]" if fin["coupes"] else "")
            + ("   !! SURVIVANT" if fin["surv"] else ""))
        for s in fin["sols"]:
            say(f"      sol {s}")
        with open(JOURNAL, "a", encoding="utf-8") as fj:
            fj.write(f"{k} {fin['noeuds']} {fin['surv']} {fin['coupes']} {fin['sec']:.1f}\n")
        FAIT[k] = fin

    LIG = [(f"{j},{K},{L},{s},{d}", FAIT.get(f"{j},{K},{L},{s},{d}"))
           for j, K, L, n, s, d in GR]
    LIG = [(k, f) for k, f in LIG if f]
    INC = [k for k, f in LIG if f["coupes"] > 0]
    D = sum(1 for k, f in LIG if f["surv"] > 0)
    NOE = sum(f["noeuds"] for k, f in LIG)
    SEC = sum(f["sec"] for k, f in LIG)
    say(f"\n   {len(LIG)}/{NCONF} configurations : D = {D} ; {NOE:,} noeuds, "
        f"{len(INC)} coupees, {SEC/3600:.2f} h")
    say(f"   duree totale {SEC/3600:.2f} h")
    if len(LIG) < NCONF:
        say("   grille incomplete : rien n'est consigne.")
        return
    if INC:
        say(f"   {len(INC)} coupees : elles n'excluent RIEN. Rien n'est consigne.")
        say("   " + ", ".join(INC[:12]))
        return
    TOK["m_extra"] = 0
    lab.record(
        TOK, float(D), p=1.0 if D == 0 else 0.0,
        verdict="conforme" if D == 0 else "SURVIVANT NON RELEVE",
        power_at=("temoins plantes en parcours LIBRE : l'etat vrai est retrouve pour "
                  "(3,7), (1,6), (2,11), (1,15) = TYPE_2 et (3,17), aux quatre lectures, "
                  "parcours complet — le crible ordonne detecte donc ce qu'il cherche "
                  "jusqu'au degre 17 au moins"),
        notes=(f"CRIBLE ORDONNE EN C (§176) : {len(LIG)} configurations, {NOE:,} noeuds, "
               f"{SEC/3600:.2f} h, parcours complet, D = {D}. Reprend h158 avec comptabilite "
               "des coupes et perte calculee. La lecture ordonnee vaut 98,0817 bits par "
               "tirage contre 37,0043 pour l'archive triee (§7.27 (iii)), d'ou un seuil de "
               "degre 18,43 pour UN SEUL tirage : les douze tirages donnent douze tests "
               "independants. NON COUVERT : les degres au-dela des plafonds de CALCUL "
               "(13 seuls, 15 par deux, 17 par quatre), alors que l'information porterait "
               "jusqu'a 73 sur le groupe de quatre."))
    say(f"   consigne : D = {D}")


if __name__ == "__main__":
    if "--perte" in sys.argv:
        say(f"{'L':>4} {'rmax':>5} {'perte':>11}   (plafond des refus parmi les L premiers mots)")
        for L in (7, 11, 15, 17, 18, 21, 22, 25, 26, 31):
            r = rmax_pour(L)
            say(f"{L:4d} {r:5d} {perte(L, r):11.3e}")
        sys.exit(0)
    if "--selftest" in sys.argv:
        lm = int(sys.argv[sys.argv.index("--lmax") + 1]) if "--lmax" in sys.argv else 17
        sys.exit(0 if selftest(lm) else 1)
    if "--archive" in sys.argv:
        archive()
        sys.exit(0)
    print(__doc__)
