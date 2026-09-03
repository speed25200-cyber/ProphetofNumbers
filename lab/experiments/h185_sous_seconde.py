"""h185 — LES GRAINES SOUS-SECONDE : microseconde et nanoseconde (RAPPORT §204).

LA RÉSOLUTION QUE LE §200 N'A PAS ATTEINTE
==========================================
Le §200 balaye les graines d'horloge à la **seconde** et à la **milliseconde**. Or les deux
sources d'amorçage les plus répandues dans un programme réel ne sont ni l'une ni l'autre :

    clock_gettime(CLOCK_REALTIME)   ->  nanoseconde
    System.nanoTime()               ->  nanoseconde
    gettimeofday()                  ->  microseconde

Une graine prise à la microseconde vaut `ts·10⁶ + µs`, et à la nanoseconde `ts·10⁹ + ns`.
Le §200, qui ne descend qu'au millième, les manque **toutes les deux**.

CE QUI REND CE BALAYAGE POSSIBLE
================================
L'outil du §203 balaye une plage **contiguë** de graines et compare chacune à l'archive
**entière** par table de hachage. Or les graines sous-seconde d'un tirage forment
exactement une plage contiguë :

    microseconde    [ ts·10⁶ , (ts+1)·10⁶ )      soit 10⁶ graines
    nanoseconde     [ ts·10⁹ , (ts+1)·10⁹ )      soit 10⁹ graines

Il suffit donc de lancer l'outil sur ces plages. Et comme il compare à toute l'archive, un
balayage sur la plage d'un tirage attrape aussi n'importe quel autre tirage qui serait né
d'une graine de cette plage.

LES DEUX BALAYAGES
==================
  A  MICROSECONDE, LARGE — les 346 débuts de nuit, plage complète de 10⁶ chacune,
     soit 3,46·10⁹ essais. La couverture est **exhaustive** sur la microseconde pour ces
     346 secondes.
  B  NANOSECONDE, PROFOND — huit débuts de nuit, plage complète de 10⁹ chacune, soit
     8·10¹⁰ essais. Exhaustive sur la nanoseconde pour ces huit secondes.

Le balayage B suffit à trancher l'hypothèse : si la machine s'amorce à la nanoseconde en
début de nuit, **les huit** doivent apparier. Un seul suffirait.

Résultat binaire, comme aux §200 à §203 : coïncidence fausse à `2,0·10⁻¹⁴` par essai.
"""

import json
import os
import struct
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POOL, DRAWN = 80, 20
EXP_ID = "h185.sous_seconde"
FJETON = "/tmp/h185_jeton.json"
FJOURNAL = "/tmp/h185_journal.json"
OUTIL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "tools_bin", "graine_exhaustive")
CIBLES = "/tmp/h185_cibles.bin"
NB_NUIT_NS = 8


def say(*a):
    print(*a, flush=True)


def plages(ts_list, res):
    return [(int(t) * res, (int(t) + 1) * res) for t in ts_list]


if __name__ == "__main__":
    import lab

    A = lab.load()
    N = len(A.ids)
    TS = np.asarray(A.ts).astype(np.int64)
    NUMS = np.asarray(A.nums).astype(np.int64)
    M0 = np.zeros(N, np.uint64)
    M1 = np.zeros(N, np.uint64)
    for j in range(DRAWN):
        c = NUMS[:, j] - 1
        bas = c < 64
        M0[bas] |= (np.uint64(1) << c[bas].astype(np.uint64))
        M1[~bas] |= (np.uint64(1) << (c[~bas] - 64).astype(np.uint64))
    if not os.path.exists(CIBLES):
        with open(CIBLES, "wb") as f:
            for i in range(N):
                f.write(struct.pack("<qQQ", int(TS[i]), int(M0[i]), int(M1[i])))

    DEB = np.r_[0, np.flatnonzero(np.diff(TS) > 1000) + 1]
    TS_NUIT = TS[DEB]
    TS_NS = TS_NUIT[np.linspace(0, len(TS_NUIT) - 1, NB_NUIT_NS).astype(int)]
    PA = plages(TS_NUIT, 10 ** 6)
    PB = plages(TS_NS, 10 ** 9)
    eA = sum(b - a for a, b in PA) * 10
    eB = sum(b - a for a, b in PB) * 10

    HYP = ("La graine n'est pas davantage une horloge SOUS-SECONDE. Le §200 balaye la "
           "seconde et la milliseconde ; or les deux sources d'amorcage les plus repandues "
           "dans un programme reel sont clock_gettime et System.nanoTime, a la "
           "NANOSECONDE, et gettimeofday, a la MICROSECONDE — que le §200 manque toutes "
           "les deux. Les graines sous-seconde d'un tirage formant une plage contigue, "
           "l'outil exhaustif du §203 les balaye directement, et comme il compare a "
           "l'archive entiere par table de hachage, chaque plage attrape aussi tout autre "
           "tirage qui en serait ne")
    STAT = (f"nombre d'appariements exacts sur les vingt numeros. Balayage A : les "
            f"{len(PA)} debuts de nuit, plage microseconde complete de 10^6 chacune, "
            f"{eA:.3e} essais. Balayage B : {len(PB)} debuts de nuit, plage nanoseconde "
            f"complete de 10^9 chacune, {eB:.3e} essais. Cinq generateurs x deux "
            "echantillonneurs, comparaison a la totalite des 70 560 tirages")
    NUL = (f"Aucune : une coincidence fausse a une probabilite de {N}/C(80,20) = "
           f"{N/3.5353e18:.2e} par essai. Resultat binaire. Les deux balayages sont "
           "EXHAUSTIFS sur leur resolution pour les secondes retenues — il n'y a pas de "
           "puissance a estimer, il y a une couverture")
    VER = "conforme si zero appariement ; GRAINE TROUVEE sinon"

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h185 : A microseconde {len(PA)} plages ({eA:.3e} essais) ; "
        f"B nanoseconde {len(PB)} plages ({eB:.3e} essais)")

    J = json.load(open(FJOURNAL, encoding="utf-8")) if os.path.exists(FJOURNAL) else {}
    trouves = []

    if "--lancer" in sys.argv:
        # le balayage B est le long : quatre processus, deux plages chacun
        for k in range(4):
            jour = f"/tmp/h185_ns{k}.txt"
            if os.path.exists(jour) and open(jour, encoding="utf-8").read().count(
                    "TERMINE") >= 2:
                say(f"   B bloc {k} deja termine")
                continue
            cmd = " ; ".join(f"{OUTIL} {CIBLES} {a} {b}" for a, b in PB[2 * k:2 * k + 2])
            subprocess.Popen(["sh", "-c", cmd],
                             stdout=open(jour, "w"), stderr=subprocess.STDOUT)
            say(f"   B bloc {k} lance : plages {PB[2*k:2*k+2]}")
        say("   relancer sans --lancer pour faire A puis agreger")
        sys.exit(0)

    if "A" not in J:
        say(f"\nA MICROSECONDE : {len(PA)} plages de 10^6")
        napp = 0
        for i, (a, b) in enumerate(PA):
            r = subprocess.run([OUTIL, CIBLES, str(a), str(b)],
                               capture_output=True, text=True)
            for L in r.stdout.splitlines():
                if L.startswith("APPARIEMENT"):
                    trouves.append(L)
                    say("   " + L)
                    napp += 1
            if (i + 1) % 100 == 0:
                say(f"   ... {i+1}/{len(PA)} plages")
        J["A"] = {"n": napp}
        json.dump(J, open(FJOURNAL, "w", encoding="utf-8"))
    say(f"   A : {eA:.3e} essais, {J['A']['n']} appariement(s)")

    say(f"\nB NANOSECONDE : {len(PB)} plages de 10^9")
    finis = 0
    for k in range(4):
        jour = f"/tmp/h185_ns{k}.txt"
        if not os.path.exists(jour):
            say(f"   B bloc {k} : ABSENT (lancer avec --lancer)")
            continue
        txt = open(jour, encoding="utf-8").read()
        n_fin = txt.count("TERMINE")
        finis += n_fin
        for L in txt.splitlines():
            if L.startswith("APPARIEMENT"):
                trouves.append(L)
                say("   " + L)
        dern = [L for L in txt.splitlines() if L.startswith("  ...")]
        say(f"   B bloc {k} : {n_fin}/2 plages terminees"
            + (f"   {dern[-1].strip()}" if dern and n_fin < 2 else ""))

    if finis < len(PB):
        say(f"\n   {finis}/{len(PB)} plages nanoseconde terminees — rien n'est consigne "
            "tant que le balayage n'est pas complet")
        sys.exit(0)

    total = eA + eB
    say(f"\n   balayage COMPLET : {total:.3e} essais, {len(trouves)} appariement(s)")
    TOK["m_extra"] = 0
    lab.record(
        TOK, float(len(trouves)), p=1.0 if not trouves else 0.0,
        verdict="GRAINE TROUVEE" if trouves else "conforme",
        power_at=("les deux balayages sont EXHAUSTIFS sur leur resolution : toute "
                  "microseconde des 346 secondes de debut de nuit, et toute nanoseconde "
                  "des huit secondes retenues. Le balayage B suffit a trancher — si la "
                  "machine s'amorce a la nanoseconde en debut de nuit, LES HUIT doivent "
                  "apparier, et un seul suffirait. L'outil est celui du §203, dont le "
                  "temoin retrouve trois graines de 32 bits plantees sur trois"),
        notes=(f"GRAINES SOUS-SECONDE (§204) : la resolution que le §200 n'atteignait pas. "
               f"A microseconde, {len(PA)} debuts de nuit, plages completes de 10^6, "
               f"{eA:.3e} essais. B nanoseconde, {len(PB)} debuts de nuit, plages "
               f"completes de 10^9, {eB:.3e} essais. Total {total:.3e}, "
               f"{len(trouves)} appariement(s). Avec les §200 a §203, le total des "
               f"balayages de graine atteint {(total + 7.28e10):.3e} essais."))
    say("   consigne.")
