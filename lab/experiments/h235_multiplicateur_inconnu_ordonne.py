"""h235 — LE MULTIPLICATEUR INCONNU SUR LES TIRAGES ORDONNÉS : le petit état sous le rejet,
sans modèle de consommation (RAPPORT §261).

LE TROU, ET POURQUOI IL EST LE DERNIER À PETIT ÉTAT
====================================================
Le §229 exclut tout état de moins de `2²⁸` bits par les doublons qui manquent ; le §252 en tire
la seule fenêtre congruentielle restante — `2²⁹` à `2³²` à constantes NON publiées — et le
§253 la ferme sur le flux du bonus : `4 026 531 840` multiplicateurs, zéro survivant. Mais le
flux du bonus est lu sous le modèle du bloc FIXE (§225) : `P` mots par tirage, toujours les
mêmes. Un échantillonneur à REJET consomme un nombre variable de mots par tirage, et la
chaîne du bonus n'est alors plus un LCG de multiplicateur `a^P` : le §253 ne la voit pas.

Les tirages ordonnés, eux, n'ont pas besoin de modèle de consommation : à l'intérieur d'un
tirage, les mots sont consécutifs, et le rejet n'est qu'un mot muet de temps en temps. C'est
la seule combinaison que rien ne couvre — **un LCG de `2²⁹` à `2³²`, constantes inconnues,
troncature, rejet** — et c'est la plus dangereuse : trente-deux bits d'état, UN tirage ordonné
suffit à les relever, et tout tirage suivant serait connu.

CE QUE FAIT CELUI-CI
====================
Le balayeur du §253 (`tools/lcg_mult_sweep.c`), auquel est ajouté un mode `multi` :

  * pour chaque multiplicateur impair `a` : une réduction LLL du réseau des différences
    (`~50 µs` sur `54`), faite UNE fois, puis pour chacune des treize suites son pavé, son
    énumération et sa vérification — treize tirages coûtent `64 µs` au lieu de `13 × 54` ;
  * les `KMOTS = 10` premiers numéros d'un tirage sont lus comme dix mots consécutifs (huit
    différences au réseau, dix classes à l'intersection cyclique), ce qui vaut pour les
    tirages dont le préfixe de dix mots est sans rejet : `Π_{j<10}(1 − j/80) = 0,556` ;
  * un candidat est un membre de la FAMILLE `(x₀ + δ, c + δ(1 − a))` qui reproduit les dix
    classes ; le tirage ENTIER, rejets compris, est alors rejoué sur un `δ` par segment de
    classes constantes — les vingt numéros dans l'ordre, `126` bits contre `96` d'inconnues.

LE RÉSIDU, CHIFFRÉ
==================
Un générateur de cette famille n'échappe au balayage que si les TREIZE tirages ont un rejet
dans leurs dix premiers mots : `(1 − 0,556)¹³ = 2,6·10⁻⁵`. Ce n'est pas un résidu d'états :
un seul tirage à préfixe propre suffit, et il y en a sept attendus sur treize.

TÉMOINS
=======
Trois couples `(a, c, x₀)` plantés à `2³²`, chacun avec un tirage au rejet réel dans la queue,
noyés parmi douze suites au hasard : la part du balayage qui contient `a` doit rendre l'état
— dans la famille, et rejouant les vingt numéros. Douze suites au hasard sur une part
entière : zéro survivant. L'autotest du §253 (quatre modules, témoin négatif à `2 000`
multiplicateurs) est relancé d'abord.
"""

import csv
import json
import os
import random
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RACINE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(RACINE, "tools", "lcg_mult_sweep.c")
BIN = "/tmp/lcg_mult_sweep_multi"
CSV = os.path.join(RACINE, "lab", "draws_ordered.csv")
SUITES = "/tmp/h235_suites.txt"
CACHE = "/tmp/h235_faits.json"
FJETON = "/tmp/h235_jeton.json"
EXP_ID = "h235.multiplicateur_inconnu_ordonne"
POOL, DRAWN = 80, 20
KMOTS = 10
BITS = (32, 31, 30, 29)
NPARTS = {32: 64, 31: 32, 30: 16, 29: 8}
PROCS = int(os.environ.get("H235_PROCS", "4"))


def say(*a):
    print(*a, flush=True)


def classe(w, m):
    return (w * POOL) // m


def engendre(x0, a, c, m):
    vus, w, out, k = set(), x0, [], 0
    while len(out) < DRAWN and k < 300:
        v = classe(w, m)
        if v not in vus:
            vus.add(v)
            out.append(v)
        w = (a * w + c) % m
        k += 1
    return out, k


def temoin(m, rng):
    """un couple au hasard dont les dix premiers mots publient dix numeros distincts."""
    while True:
        a = rng.randrange(m // 4) * 4 + 1
        c = rng.randrange(m // 2) * 2 + 1
        x0 = rng.randrange(m)
        out, k = engendre(x0, a, c, m)
        w, vus, propre = x0, set(), True
        for _ in range(KMOTS):
            v = classe(w, m)
            if v in vus:
                propre = False
                break
            vus.add(v)
            w = (a * w + c) % m
        if propre and len(out) == DRAWN:
            return a, c, x0, out, k - DRAWN


def lance(bits, fichier, part, nparts):
    return subprocess.Popen([BIN, "multi", str(bits), fichier, str(part), str(nparts)],
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)


def survivants_de(sortie):
    out = []
    for l in sortie.splitlines():
        if l.startswith("*** SURVIVANT"):
            f = dict(kv.split("=") for kv in l.split()[2:7])
            out.append({"suite": int(f["suite"]), "a": int(f["a"]), "c": int(f["c"]),
                        "x0": int(f["x0"])})
    return out


if __name__ == "__main__":
    import lab

    lignes = list(csv.DictReader(open(CSV, encoding="utf-8")))
    IDS = [r["id"] for r in lignes]
    ORD = [[int(r["o%d" % i]) - 1 for i in range(1, DRAWN + 1)] for r in lignes]
    with open(SUITES, "w") as fh:
        for o in ORD:
            fh.write(" ".join(map(str, o)) + "\n")

    p_propre = 1.0
    for j in range(KMOTS):
        p_propre *= (POOL - j) / POOL
    residu = (1 - p_propre) ** len(ORD)
    total = sum(1 << (b - 1) for b in BITS)

    HYP = (f"Aucun generateur congruentiel de module 2^29, 2^30, 2^31 ou 2^32, a constantes "
           f"INCONNUES, lu par troncature avec rejet, ne produit l'un des {len(ORD)} tirages "
           f"ordonnes. LE TROU : le §253 ferme ces quatre modules sur le flux du bonus, mais "
           f"sous le modele du bloc FIXE — P mots par tirage — et un echantillonneur a rejet "
           f"consomme un nombre variable de mots, ce qui sort la chaine du bonus de la famille "
           f"a^P ; les tirages ordonnes n'ont pas besoin de ce modele, les mots y sont "
           f"consecutifs. C'est la seule combinaison a petit etat que rien ne couvre, et la "
           f"plus dangereuse : 32 bits d'etat, un tirage ordonne les releve, tout tirage "
           f"suivant serait connu. METHODE : le balayeur du §253 en mode multi — pour chaque "
           f"multiplicateur impair, une reduction LLL du reseau des differences (N = 8), puis "
           f"pour chacune des {len(ORD)} suites son pave, son enumeration, l'intersection "
           f"cyclique des {KMOTS} premieres classes lues comme mots consecutifs, et le REJEU DU "
           f"TIRAGE ENTIER rejets compris sur la famille (x0 + d, c + d(1 - a)), un d par "
           f"segment de classes constantes. {total} multiplicateurs impairs en tout. "
           f"Couverture : un tirage est lisible si ses {KMOTS} premiers mots sont sans rejet, "
           f"probabilite {p_propre:.3f} ; un generateur n'echappe que si les {len(ORD)} tirages "
           f"ont un rejet dans ce prefixe, residu {residu:.1e}. Temoins : trois couples plantes "
           f"a 2^32 avec rejet dans la queue, noyes parmi douze suites au hasard, rendus par la "
           f"part qui contient leur multiplicateur ; douze suites au hasard sur une part "
           f"entiere, zero survivant ; l'autotest du §253 relance")
    STAT = (f"nombre de couples (a, c, x0) reproduisant un tirage reel ENTIER, rejets compris, "
            f"sur {total} multiplicateurs x {len(ORD)} tirages")
    NUL = (f"EXACTE et combinatoire : vingt numeros dans l'ordre valent 126 bits contre 96 "
           f"d'inconnues (a, c, x0) ; par multiplicateur et par tirage la probabilite d'un faux "
           f"passage du rejeu entier est < 2^-30, soit moins de 2^-20 faux survivants attendus "
           f"sur la grille entiere")
    VER = ("ETAT RELEVE si un couple rejoue un tirage reel entier — il donne alors tous les "
           "tirages suivants ; conforme sinon, et l'absence est CERTAINE (a la marge de 1e-9 "
           "du reseau flottant pres, verifiee en entiers) pour tout LCG de 2^29 a 2^32 dont "
           "un des treize tirages a un prefixe de dix mots sans rejet ; NON CALIBRE si un "
           "temoin plante n'est pas rendu")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h235 : {len(ORD)} tirages ordonnes, {KMOTS} premiers mots au reseau, modules "
        f"{', '.join('2^%d' % b for b in BITS)}, {total} multiplicateurs impairs")
    say(f"   couverture par tirage {p_propre:.3f}, residu joint {residu:.1e}")

    say("\n   compilation et autotest du balayeur")
    subprocess.run(["gcc", "-O3", "-march=native", "-std=c11", "-Wall", "-Wextra",
                    "-o", BIN, SRC, "-lm"], check=True)
    r = subprocess.run([BIN, "autotest"], capture_output=True, text=True)
    say("      " + r.stdout.strip().splitlines()[-1])
    if r.returncode != 0:
        raise SystemExit("balayeur NON CALIBRE")

    say("\n   temoins du mode multi (2^32) : trois couples plantes parmi douze suites au hasard")
    rng = random.Random(235)
    m = 1 << 32
    calibre = True
    for k in range(3):
        a, c, x0, out, rej = temoin(m, rng)
        suites = [" ".join(map(str, out))]
        for _ in range(12):
            suites.append(" ".join(map(str, rng.sample(range(POOL), DRAWN))))
        fichier = f"/tmp/h235_temoin{k}.txt"
        open(fichier, "w").write("\n".join(suites) + "\n")
        nparts = 1 << 20
        part = ((a - 1) // 2) % nparts
        p = lance(32, fichier, part, nparts)
        sortie, _ = p.communicate()
        surv = survivants_de(sortie)
        bons = [s for s in surv if s["suite"] == 0 and s["a"] == a
                and engendre(s["x0"], s["a"], s["c"], m)[0] == out]
        say(f"      temoin {k} : a = {a}, {rej} rejet(s) dans la queue -> "
            f"{len(surv)} survivant(s), etat {'RENDU' if bons else 'MANQUE'}")
        calibre &= bool(bons)
    fichier = "/tmp/h235_negatif.txt"
    open(fichier, "w").write("\n".join(" ".join(map(str, rng.sample(range(POOL), DRAWN)))
                                       for _ in range(13)) + "\n")
    p = lance(32, fichier, 5, 4096)
    sortie, _ = p.communicate()
    dernier = sortie.strip().splitlines()[-1]
    nsurv = len(survivants_de(sortie))
    say(f"      negatif (treize suites au hasard, une part de 2^19) : {nsurv} survivant(s) ; "
        f"{dernier.split(':', 1)[1].strip()}")
    calibre &= (nsurv == 0)
    if not calibre:
        raise SystemExit("mode multi NON CALIBRE : on ne balaie rien avec ca")

    deja = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}

    def consigne_cache():
        json.dump(deja, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)

    say(f"\n   l'archive : {len(ORD)} tirages, {PROCS} processus")
    t_all = time.time()
    for bits in BITS:
        nparts = NPARTS[bits]
        restantes = [k for k in range(nparts) if f"{bits}|{k}" not in deja]
        say(f"\n   m = 2^{bits} : {1 << (bits - 1)} multiplicateurs, {nparts} parts, "
            f"{len(restantes)} a faire")
        actifs = {}
        while restantes or actifs:
            while restantes and len(actifs) < PROCS:
                k = restantes.pop(0)
                actifs[k] = (lance(bits, SUITES, k, nparts), time.time())
            finis = [k for k, (p, _) in actifs.items() if p.poll() is not None]
            if not finis:
                time.sleep(20)
                continue
            for k in finis:
                p, t0 = actifs.pop(k)
                sortie = p.stdout.read()
                if p.returncode != 0:
                    raise SystemExit(f"la part {k} de 2^{bits} a echoue")
                surv = survivants_de(sortie)
                dernier = sortie.strip().splitlines()[-1] if sortie.strip() else ""
                deja[f"{bits}|{k}"] = {"survivants": surv, "s": time.time() - t0,
                                       "ligne": dernier}
                consigne_cache()
                say(f"      part {k:>3}/{nparts} : {len(surv)} survivant(s), "
                    f"{time.time()-t0:.0f}s   [{time.time()-t_all:.0f}s]")
                for s in surv:
                    say(f"      *** SURVIVANT tirage {IDS[s['suite']]} : m = 2^{bits}, "
                        f"a = {s['a']}, c = {s['c']}, x0 = {s['x0']}")

    survivants = [(k, s) for k, v in deja.items() for s in v["survivants"]]
    dt = sum(v["s"] for v in deja.values())
    confirmes = []
    for k, s in survivants:
        bits = int(k.split("|")[0])
        m = 1 << bits
        out, _ = engendre(s["x0"], s["a"], s["c"], m)
        if out == ORD[s["suite"]]:
            confirmes.append((bits, s))
    say(f"\n   {total} multiplicateurs balayes, {len(deja)} parts, {dt:.0f}s de calcul, "
        f"{len(survivants)} survivant(s), {len(confirmes)} confirme(s) en Python")
    verdict = "ETAT RELEVE" if confirmes else "conforme"
    say(f"\n   {verdict}")

    TOK["m_extra"] = 0
    lab.record(
        TOK, float(len(confirmes)), p=float(1.0 if not confirmes else 2.0 ** -30),
        verdict=verdict,
        power_at=(f"detection CERTAINE pour tout LCG de 2^29 a 2^32 dont un tirage sur "
                  f"{len(ORD)} a un prefixe de {KMOTS} mots sans rejet (residu joint "
                  f"{residu:.1e}) : trois couples plantes a 2^32 avec rejet dans la queue sont "
                  f"rendus par la part qui contient leur multiplicateur, treize suites au "
                  f"hasard rendent zero, l'autotest du §253 passe. Non couvert : un rejet dans "
                  f"les {KMOTS} premiers mots des treize tirages a la fois, les modules hors "
                  f"de 2^29..2^32 (le §229 ferme en dessous, le §259 au-dessus a constantes "
                  f"publiees), et la regle modulo 80 (§226, §260)"),
        notes=(f"LE MULTIPLICATEUR INCONNU SUR LES TIRAGES ORDONNES (§261) — le §253 fermait "
               f"2^29..2^32 sous le bloc fixe, pas sous le rejet ; ici les tirages ordonnes, "
               f"mots consecutifs, {total} multiplicateurs, {len(ORD)} tirages, {dt:.0f}s, "
               f"{len(survivants)} survivant(s), {len(confirmes)} confirme(s). {verdict}."))
    say("   consigne.")
