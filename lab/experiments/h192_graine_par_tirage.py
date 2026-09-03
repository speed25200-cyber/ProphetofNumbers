"""h192 — LA GRAINE REPRISE À CHAQUE TIRAGE (RAPPORT §212).

LE MODÈLE QUE NEUF BALAYAGES ONT MANQUÉ
=======================================
Les §200 à §206 balayent `2,85 × 10¹¹` graines. **Tous** supposent que la machine s'amorce
**une fois** — au début d'une nuit, sur un identifiant, sur une date — puis déroule son
flux. C'est le modèle du programmeur soigneux.

Le modèle du programmeur pressé est autre, et c'est de loin le plus répandu au monde :

    pour chaque tirage :  amorcer sur l'horloge, puis tirer vingt numéros

Le générateur est **repris de l'horloge à chaque tirage**. C'est le bogue de génération
aléatoire le plus commun qui existe, et le dossier ne l'avait jamais testé comme tel.

CE QUI EST DÉJÀ FERMÉ SANS QUE JE L'AIE SU
==========================================
À la **seconde**, c'est fermé — par accident heureux. Le §211 balaie les `2³²` graines et
compare chacune à l'archive **entière** par table de hachage. Tout horodatage unix de
l'archive vaut `1,76 × 10⁹`, donc **inférieur à `2³² = 4,29 × 10⁹`** : toute graine
« seconde du tirage » a déjà été essayée, avec les cinq générateurs et les six
échantillonneurs. Le modèle « `srand(time(NULL))` par tirage » à la seconde est mort.

CE QUI RESTE OUVERT, ET QUE CE FICHIER FERME
============================================
La **sous-seconde par tirage**. Le §205 ne visite les millisecondes et les microsecondes
qu'autour des `346` **débuts de nuit**. Si la machine reprend l'horloge à chaque tirage,
la graine du tirage `t` vaut `ts_t · 1000 + ms` ou `ts_t · 10⁶ + µs`, et ces plages-là —
sauf pour les 346 premiers tirages de nuit — n'ont **jamais** été visitées. Elles valent
d'ailleurs jusqu'à `1,77 × 10¹⁵`, donc très au-delà des `2³²` du §211.

  **A  MILLISECONDE, TOTALE.** Les `70 560` tirages, plage complète de `1000`
     millisecondes chacune. Aucun trou : si la machine s'amorce à la milliseconde de son
     propre tirage, **chacun** des 70 560 doit apparier.

  **B  MICROSECONDE, PROFONDE.** Un sous-échantillon de `2 000` tirages régulièrement
     espacés, plage complète de `10⁶` microsecondes chacune. Deux mille chances
     indépendantes : si la machine s'amorce à la microseconde de son propre tirage,
     **les deux mille** doivent apparier. Une seule suffirait.

La comparaison se fait contre l'archive **entière** et non contre le seul tirage visé.
C'est plus fort et non moins : une graine de la fenêtre du tirage `t` qui produirait le
tirage `u` serait vue aussi.

L'OUTIL EST CELUI DU §211, INCLUS ET NON RECOPIÉ
================================================
`graine_plages.c` fait `#include "graine_exhaustive.c"` avec le pilote débranché. Les cinq
générateurs, les six échantillonneurs et la table de hachage sont donc *le même code
objet* que celui que le témoin `30/30` du §211 a validé. Une seconde copie aurait été une
seconde chose capable de dériver.
"""

import json
import os
import struct
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import h181_graine_moderne as G                                         # noqa: E402
import h187_echantillonneurs as S                                       # noqa: E402

POOL, DRAWN = 80, 20
EXP_ID = "h192.graine_par_tirage"
FJETON = "/tmp/h192_jeton.json"
OUTIL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "tools_bin", "graine_plages")
CIBLES = "/tmp/h192_cibles.bin"
PLAGES = "/tmp/h192_plages.bin"
NBLOC = 4
NSOUS = 2000                       # tirages retenus pour le balayage microseconde


def say(*a):
    print(*a, flush=True)


def selftest():
    """Le témoin : une graine plantée DANS une plage doit être retrouvée par l'outil.

    Synthétique de bout en bout — aucune ligne de l'archive n'est lue. On plante une
    graine de l'ordre de 10¹² (l'ordre de grandeur d'un `ts·1000`, hors d'atteinte des
    2³² du §211), au milieu d'une plage, pour chacun des trente couples.
    """
    say("h192 --autotest : donnees synthetiques uniquement, aucune archive lue")
    say(f"   {'generateur':>14} | {'echantillonneur':>16} | {'graine':>16} | retrouvee")
    ok = True
    for g in range(5):
        for s in range(6):
            graine = 1_757_829_900_000 + 7919 * (6 * g + s)
            t = S.tirage(graine, g, s)
            if t is None:
                say(f"   {G.NOMGEN[g]:>14} | {S.NOMECH[s]:>16} | ENGENDREMENT IMPOSSIBLE")
                ok = False
                continue
            with open("/tmp/h192_t.bin", "wb") as f:
                f.write(struct.pack("<qQQ", 0, t[0], t[1]))
            # trois plages, la graine plantee au milieu de la seconde : le temoin verifie
            # AUSSI que l'outil traite bien plusieurs plages et le decoupage en blocs
            with open("/tmp/h192_p.bin", "wb") as f:
                f.write(struct.pack("<QQ", graine - 500, 100))
                f.write(struct.pack("<QQ", graine - 50, 100))
                f.write(struct.pack("<QQ", graine + 500, 100))
            vu = False
            for b in range(2):
                r = subprocess.run([OUTIL, "/tmp/h192_t.bin", "/tmp/h192_p.bin",
                                    str(b), "2"], capture_output=True, text=True)
                vu |= any(f"graine {graine} generateur {G.NOMGEN[g]} "
                          f"echantillonneur {S.NOMECH[s]}" in L
                          for L in r.stdout.splitlines())
            say(f"   {G.NOMGEN[g]:>14} | {S.NOMECH[s]:>16} | {graine:16d} | "
                f"{'OUI' if vu else 'NON'}")
            ok &= vu
    say(f"   -> {'CALIBRE 30/30' if ok else 'DEFAILLANT'}")
    return ok


if __name__ == "__main__":
    if "--autotest" in sys.argv:
        sys.exit(0 if selftest() else 1)

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

    # ---- les plages : A milliseconde sur TOUS les tirages, B microseconde sur NSOUS
    sous = np.linspace(0, N - 1, NSOUS).astype(np.int64)
    sous = np.unique(sous)
    if not os.path.exists(PLAGES):
        with open(PLAGES, "wb") as f:
            for i in range(N):
                f.write(struct.pack("<QQ", int(TS[i]) * 1000, 1000))
            for i in sous:
                f.write(struct.pack("<QQ", int(TS[i]) * 1000000, 1000000))

    grA = N * 1000
    grB = len(sous) * 1000000
    essais = float(grA + grB) * 5 * 6
    faux = essais * N / 3.5353e18

    HYP = ("La machine ne reprend pas sa graine de l'horloge A CHAQUE TIRAGE. Les §200 a "
           "§206 balayent 2,85e11 graines mais supposent TOUS un amorcage unique — debut "
           "de nuit, identifiant, date — puis un flux deroule ; c'est le modele du "
           "programmeur soigneux. Le modele du programmeur presse, de loin le plus repandu "
           "au monde, amorce sur l'horloge a chaque tirage. A la SECONDE ce modele est "
           "deja mort, et par accident : le §211 balaie les 2^32 graines en comparant "
           "chacune a l'archive entiere, et tout horodatage unix de l'archive (1,76e9) est "
           "inferieur a 2^32, donc toute graine seconde-du-tirage a deja ete essayee avec "
           "les cinq generateurs et les six echantillonneurs. Ce qui reste ouvert est la "
           "SOUS-SECONDE PAR TIRAGE : le §205 ne visite les millisecondes et microsecondes "
           "qu'autour des 346 debuts de nuit, et les plages ts*1000 et ts*1000000 des "
           "tirages eux-memes — qui valent jusqu'a 1,77e15, tres au-dela de 2^32 — n'ont "
           f"jamais ete visitees. Balayage A : les {N} tirages, plage milliseconde "
           f"complete de 1000 chacune, aucun trou. Balayage B : {len(sous)} tirages "
           "regulierement espaces, plage microseconde complete de 10^6 chacune")
    STAT = (f"nombre d'appariements exacts sur les vingt numeros. Balayage A : {N} plages "
            f"de 1000, soit {grA:.4e} graines. Balayage B : {len(sous)} plages de 10^6, "
            f"soit {grB:.4e} graines. Le tout x 5 generateurs x 6 echantillonneurs = "
            f"{essais:.4e} essais, chaque tirage engendre etant cherche dans une table de "
            f"hachage des {N} masques — donc compare a l'archive ENTIERE et non au seul "
            "tirage vise, ce qui est plus fort et non moins")
    NUL = (f"Aucune : une coincidence fausse vaut {N}/C(80,20) = {N/3.5353e18:.2e} par "
           f"essai, soit {faux:.2e} au total. Resultat binaire. Si la machine s'amorce a la "
           f"milliseconde de son propre tirage, LES {N} doivent apparier ; a la "
           f"microseconde, LES {len(sous)} du balayage B doivent apparier. Une seule "
           "suffirait")
    VER = "conforme si zero appariement ; GRAINE TROUVEE sinon"

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h192 : {N} cibles ; A = {N} plages de 1000 ms, B = {len(sous)} plages de 10^6 us")
    say(f"   {grA + grB:.4e} graines x 5 x 6 = {essais:.4e} essais ; "
        f"faux attendus {faux:.3e}")

    if "--lancer" in sys.argv:
        for k in range(NBLOC):
            jour = f"/tmp/h192_bloc{k}.txt"
            if os.path.exists(jour) and "TERMINE" in open(jour, encoding="utf-8").read():
                say(f"   bloc {k} deja termine")
                continue
            subprocess.Popen([OUTIL, CIBLES, PLAGES, str(k), str(NBLOC)],
                             stdout=open(jour, "w"), stderr=subprocess.STDOUT)
            say(f"   bloc {k} lance")
        say("   relancer sans --lancer pour agreger")
        sys.exit(0)

    trouves, faits = [], 0
    for k in range(NBLOC):
        jour = f"/tmp/h192_bloc{k}.txt"
        if not os.path.exists(jour):
            say(f"   bloc {k} : ABSENT")
            continue
        txt = open(jour, encoding="utf-8").read()
        fini = "TERMINE" in txt
        faits += fini
        for L in txt.splitlines():
            if L.startswith("APPARIEMENT"):
                trouves.append(L)
                say("   " + L)
        dern = [L for L in txt.splitlines() if L.startswith("  ...")]
        say(f"   bloc {k} : {'termine' if fini else 'EN COURS'}"
            + (f"   {dern[-1].strip()}" if dern and not fini else ""))

    if faits < NBLOC:
        say(f"\n   {faits}/{NBLOC} blocs termines — rien n'est consigne tant que le "
            "balayage n'est pas complet")
        sys.exit(0)

    say(f"\n   balayage COMPLET : {essais:.4e} essais, {len(trouves)} appariement(s)")
    TOK["m_extra"] = 0
    lab.record(
        TOK, float(len(trouves)), p=1.0 if not trouves else 0.0,
        verdict="GRAINE TROUVEE" if trouves else "conforme",
        power_at=("un appariement exact sur vingt numeros vaut 1/C(80,20) = 2,83e-19 par "
                  "essai : le test n'a aucune zone grise, il trouve la graine ou il "
                  "n'existe pas de graine de cette forme. Le temoin plante trente graines "
                  "de l'ordre de 1,76e12 — hors d'atteinte des 2^32 du §211 — au milieu "
                  "d'une plage et les retrouve 30/30, ce qui verifie du meme coup que "
                  "l'outil traite bien une LISTE de plages et son decoupage en blocs"),
        notes=(f"LA GRAINE REPRISE A CHAQUE TIRAGE (§212) — le modele d'amorcage que les "
               f"§200 a §206 ne pouvaient pas atteindre. A la seconde il etait deja mort "
               f"par accident (les horodatages sont sous 2^32, donc balayes par le §211) ; "
               f"restait la sous-seconde PAR TIRAGE, jamais visitee ailleurs qu'aux 346 "
               f"debuts de nuit du §205. A : {N} plages millisecondes completes. B : "
               f"{len(sous)} plages microsecondes completes. {essais:.4e} essais, "
               f"{len(trouves)} appariement(s). Outil graine_plages, qui INCLUT "
               f"graine_exhaustive.c au lieu de le recopier : meme code que le temoin "
               f"30/30 du §211."))
    say("   consigne.")
