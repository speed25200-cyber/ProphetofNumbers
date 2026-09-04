"""h228 — LE MULTIPLICATEUR INCONNU : la fenêtre du §252, refermée par le calcul
(RAPPORT §253).

CE QUE LE §252 A NOMMÉ, ET CHIFFRÉ
==================================
Les §250 et §251 ferment la famille congruentielle **à constantes publiées**, des deux côtés
de `2³²`. Le §252 localise ce qui reste et en donne le prix :

> Les modules `2²⁹`–`2³²` à constantes **inconnues** : ni « impossible », ni « déjà fait ».

Deux arguments cernent cette fenêtre sans la fermer. Par le bas, l'argument des doublons
(§229) tue tout espace d'états `S ≲ 2²⁸` — mais il ne vaut plus que `0,31` à `2³¹` et `0,44`
à `2³²`. Par le haut, le balayage des constantes coûte `2⁶⁴` couples `(a, c)`… sauf qu'il n'a
pas à les balayer par couples.

L'INCRÉMENT S'ÉLIMINE, ET LE PAS DE BLOC AUSSI
==============================================
Deux réductions, et ce sont elles qui rendent le calcul possible.

  **L'incrément.** Les différences `y_i = x_{i+1} − x_i` vérifient `y_{i+1} = a·y_i` sans
     aucune trace de `c`. Il ne reste qu'un inconnu : `2³¹` multiplicateurs impairs au lieu de
     `2⁶⁴` couples.
  **Le pas de bloc.** Le bonus donne un mot par tirage, espacés de `P` mots sous le §225 : la
     chaîne qu'il suit est un LCG de multiplicateur `A = a^P`. Or `a^P` parcourt les impairs
     quand `a` le fait. **Balayer tous les `A` impairs couvre donc tous les `(a, c, P)` à la
     fois** — le pas n'est plus un paramètre, il est absorbé.

Là où le §250 balayait `109` pas de bloc pour `15` jeux de constantes, celui-ci balaie
**toutes** les constantes et **tous** les pas d'un coup.

L'OUTIL, ET CE QUI LE LICENCIE
==============================
`tools/lcg_mult_sweep.c`. Pour chaque `A` impair : réseau `(1, A, …, A⁷)` + `m·I`, réduction
`LLL`, énumération de **tous** les points du pavé des différences, puis reconstruction exacte
de `x₀` et `c` par intersection d'intervalles et rejeu des `204` classes en entiers.

Trois choses le licencient, et aucune n'est une opinion :

    autotest      12 generateurs plantes (2^29..2^32) -> 12 etats releves, dans la
                  famille exacte du couple plante ; temoin negatif : 2 000 multiplicateurs
                  sur des classes au hasard, 0 survivant
    bout en bout  un LCG plante mod 2^20, balayage des 524 288 impairs -> 1 seul
                  survivant, le bon
    croisement    700 instances tirees au hasard (2^30 et 2^32) : le compte de points du
                  C en `double` et celui de `lab/cvp_exact.py` en `Fraction` coincident
                  700 fois sur 700

Le troisième compte le plus. Le `C` travaille en flottants pour tenir le budget ; dire que
c'est « exact à une marge bornée près » ne vaut que si on le **mesure** contre un oracle exact.

LA FAMILLE, PAS LE POINT
========================
Décaler `x₀` de `δ` et `c` de `δ(1−a)` décale toute la suite de `δ` : les classes ne changent
pas. La solution est donc un **intervalle** d'environ `2(m/80)/204` valeurs, toutes légitimes.
Ce n'est pas un défaut de l'outil mais une propriété du problème, et l'autotest exige
l'appartenance à la bonne famille, non l'égalité des constantes.
"""

import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RACINE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(RACINE, "tools", "lcg_mult_sweep.c")
BIN = "/tmp/lcg_mult_sweep"
CLASSES = "/tmp/h228_classes.txt"
POOL, PAS = 80, 300
EXP_ID = "h228.multiplicateur_inconnu"
FJETON = "/tmp/h228_jeton.json"
CACHE = "/tmp/h228_faits.json"


def say(*a):
    print(*a, flush=True)


def plages(T):
    out, deb = [], 0
    for i in range(len(T) - 1):
        if not (T[i + 1][1] - T[i][1] == PAS and T[i + 1][0] - T[i][0] == 1):
            out.append((deb, i + 1))
            deb = i + 1
    out.append((deb, len(T)))
    return out


if __name__ == "__main__":
    import csv
    import glob

    import lab

    bits_demandes = [int(x) for x in sys.argv[1:] if x.isdigit()] or [31]

    T = []
    for f in sorted(glob.glob(os.path.join(RACINE, "claude", "draws", "draws-*.csv"))):
        for r in csv.DictReader(open(f)):
            T.append((int(r["id"]), int(r["unix_utc"]), int(r["bonus"])))
    T.sort()
    a1, b1 = max(plages(T), key=lambda r: r[1] - r[0])
    cls = [T[j][2] - 1 for j in range(a1, b1)]
    open(CLASSES, "w").write(" ".join(map(str, cls)))
    n = len(cls)

    HYP = (f"AUCUN generateur congruentiel de module 2^29 a 2^32 ne produit le flux du bonus "
           f"— quel que soit son multiplicateur, quel que soit son increment, quel que soit "
           f"son pas de bloc. C'est la fenetre que le §252 a nommee et chiffree sans la "
           f"fermer : les §250 et §251 ferment la famille a constantes PUBLIEES des deux "
           f"cotes de 2^32, l'argument des doublons du §229 tue tout espace d'etats S <~ 2^28, "
           f"mais il ne vaut plus que 0,31 a 2^31 et 0,44 a 2^32. Deux reductions rendent le "
           f"balayage possible. D'abord l'INCREMENT s'elimine : les differences "
           f"y_i = x_{{i+1}} - x_i verifient y_{{i+1}} = a y_i sans aucune trace de c, donc il "
           f"reste 2^31 multiplicateurs impairs au lieu de 2^64 couples. Ensuite le PAS DE "
           f"BLOC s'absorbe : le bonus donne un mot par tirage espaces de P mots sous le §225, "
           f"donc la chaine suit un LCG de multiplicateur A = a^P, et a^P parcourt les impairs "
           f"quand a le fait — balayer tous les A impairs couvre TOUS les (a, c, P) a la fois. "
           f"La ou le §250 balayait 109 pas pour 15 jeux de constantes, celui-ci balaie toutes "
           f"les constantes et tous les pas d'un coup. Pour chaque A impair : reseau "
           f"(1, A, ..., A^7) + m.I, reduction LLL, enumeration de TOUS les points du pave des "
           f"differences, puis reconstruction exacte de x0 et c par intersection d'intervalles "
           f"et rejeu des {n} classes en entiers. La solution est une FAMILLE et non un point — "
           f"decaler x0 de d et c de d(1-a) decale toute la suite de d, donc les classes ne "
           f"changent pas — ce qui est une propriete du probleme et non un defaut de l'outil")
    STAT = (f"nombre de multiplicateurs impairs survivants, sur le balayage complet de "
            f"m/2 valeurs par module, verification exacte sur les {n} classes de la plage "
            f"maximale du §249")
    NUL = (f"EXACTE et combinatoire : reproduire {n} classes consecutives demande "
           f"{n*6.32:.0f} bits a un couple (x0, c) qui en compte au plus 64, et le "
           f"multiplicateur est enumere, non estime. L'esperance de points parasites dans le "
           f"pave vaut m/40^8, soit 6,5e-4 pour m = 2^32 ; celle de survivants apres "
           f"verification des {n} classes est nulle a toute precision utile. Ce n'est pas une "
           f"loi, c'est un COMPTE")
    VER = ("ETAT RELEVE si un seul multiplicateur survit ; conforme sinon, et la fenetre du "
           "§252 est alors refermee pour les modules effectivement balayes — la liste des "
           "modules balayes est donnee, et ceux qui ne le sont pas sont nommes")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h228 : plage de {n} classes (ids {T[a1][0]}..{T[b1-1][0]}), "
        f"modules demandes : {', '.join('2^%d' % b for b in bits_demandes)}")

    say("\n   compilation et autotest de l'outil")
    subprocess.run(["gcc", "-O3", "-march=native", "-std=c11", "-Wall", "-Wextra",
                    "-o", BIN, SRC, "-lm"], check=True)
    r = subprocess.run([BIN, "autotest"], capture_output=True, text=True)
    for ligne in r.stdout.rstrip().splitlines():
        say("   " + ligne)
    if r.returncode != 0:
        raise SystemExit("outil NON CALIBRE : on ne balaie rien avec ca")

    # --- temoin de bout en bout : un LCG plante mod 2^20, balaye en entier
    say("\n   temoin de bout en bout : un LCG plante mod 2^20, balayage des 524 288 impairs")
    m0 = 1 << 20
    a0, c0, x0 = (0xBEEF * 4 + 1) % m0, (0xCAFE * 2 + 1) % m0, 123457 % m0
    w, cl0 = x0, []
    for _ in range(n):
        cl0.append((w * POOL) // m0)
        w = (a0 * w + c0) % m0
    open("/tmp/h228_plante.txt", "w").write(" ".join(map(str, cl0)))
    rp = subprocess.run([BIN, "sweep", "20", "/tmp/h228_plante.txt", "0", "1"],
                        capture_output=True, text=True)
    trouve = [l for l in rp.stdout.splitlines() if "SURVIVANT" in l]
    say(f"      plante a = {a0} ; {len(trouve)} survivant(s) : "
        + ("; ".join(trouve) if trouve else "AUCUN"))
    if len(trouve) != 1 or f"a={a0} " not in trouve[0]:
        raise SystemExit("le temoin de bout en bout echoue : on ne balaie rien avec ca")

    # --- le balayage reel
    #
    # UN CACHE, PARCE QU'UN MODULE COUTE DES HEURES. Chaque module termine est ecrit
    # dans CACHE ; relancer le script avec la liste complete ne rebalaie que ce qui
    # manque, et la ligne de registre couvre alors les QUATRE modules et non le seul
    # dernier. Sans cela, finir 2^32 effacerait du registre le travail sur 2^29..2^31.
    procs = max(1, os.cpu_count() or 1)
    deja = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    fait, survivants = [], []
    for bits in bits_demandes:
        if str(bits) in deja:
            d = deja[str(bits)]
            fait.append(bits)
            survivants.extend(d["survivants"])
            say(f"\n   m = 2^{bits} : deja balaye ({d['n']} multiplicateurs, "
                f"{len(d['survivants'])} survivant(s), {d['s']:.0f}s) — repris du cache")
            continue
        say(f"\n   balayage m = 2^{bits} : {1 << (bits-1)} multiplicateurs impairs, "
            f"{procs} parts")
        t0 = time.time()
        ps = [subprocess.Popen([BIN, "sweep", str(bits), CLASSES, str(k), str(procs)],
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               text=True) for k in range(procs)]
        sorties = [p.communicate()[0] for p in ps]
        if any(p.returncode != 0 for p in ps):
            raise SystemExit(f"le balayage 2^{bits} a echoue")
        surv = [l for s in sorties for l in s.splitlines() if "SURVIVANT" in l]
        survivants.extend(surv)
        fait.append(bits)
        for l in surv:
            say("   *** " + l)
        dt = time.time() - t0
        say(f"      {1 << (bits-1)} multiplicateurs balayes en {dt:.0f}s, "
            f"{len(surv)} survivant(s)")
        deja[str(bits)] = {"n": 1 << (bits - 1), "survivants": surv, "s": dt}
        json.dump(deja, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)

    total = sum(1 << (b - 1) for b in fait)
    manque = [b for b in (29, 30, 31, 32) if b not in fait]
    verdict = "ETAT RELEVE" if survivants else "conforme"
    say(f"\n   {total} multiplicateurs balayes au total, {len(survivants)} survivants")
    if manque:
        say(f"   NON BALAYES, et il faut le dire : "
            + ", ".join("2^%d" % b for b in manque))
    say(f"\n   {verdict}")

    TOK["m_extra"] = 0
    lab.record(
        TOK, float(len(survivants)), p=float(1.0 if not survivants else 2.0 ** -1200),
        verdict=verdict,
        power_at=(f"la detection est CERTAINE et non probable, et trois temoins le "
                  f"licencient : l'autotest releve l'etat exact de 12 generateurs plantes de "
                  f"2^29 a 2^32 et rend zero sur 2 000 multiplicateurs appliques a des classes "
                  f"au hasard ; le temoin de BOUT EN BOUT plante un LCG mod 2^20 et le "
                  f"balayage de ses 524 288 multiplicateurs impairs rend UN survivant, le bon ; "
                  f"et le croisement compare le compte de points du C en double a celui de "
                  f"lab/cvp_exact.py en Fraction sur 700 instances tirees au hasard, avec zero "
                  f"desaccord — sans quoi « exact a une marge bornee pres » ne serait qu'une "
                  f"opinion. Modules effectivement balayes : "
                  + ", ".join("2^%d" % b for b in fait)
                  + (f" ; NON balayes : " + ", ".join("2^%d" % b for b in manque)
                     if manque else " ; aucun module de la fenetre n'est laisse de cote")),
        notes=(f"LE MULTIPLICATEUR INCONNU (§253) — la fenetre du §252 refermee par le calcul. "
               f"Deux reductions la rendent possible : l'increment s'elimine par les "
               f"differences (y_{{i+1}} = a y_i), et le pas de bloc s'absorbe puisque A = a^P "
               f"parcourt les impairs quand a le fait, de sorte que balayer tous les A impairs "
               f"couvre tous les (a, c, P) a la fois. {total} multiplicateurs balayes sur les "
               f"modules " + ", ".join("2^%d" % b for b in fait)
               + f", verification exacte sur les {n} classes de la plage maximale du §249, "
               f"{len(survivants)} survivants. {verdict}."))
    say("   consigne.")
