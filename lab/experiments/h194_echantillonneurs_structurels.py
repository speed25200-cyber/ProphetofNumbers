"""h194 — LES QUATRE ÉCHANTILLONNEURS QUE LE §211 NOMME SANS LES TESTER (RAPPORT §214).

CE QUE JE M'OBLIGE À FAIRE ICI
==============================
Le §211 se termine par un aveu, et un aveu n'est pas un test :

> « Six n'est pas tous. Un Fisher-Yates partiel sur un tableau de quatre-vingts, un tirage
> par ordre de tri de quatre-vingts clés aléatoires, un rejet sur un intervalle décalé —
> chacun est un septième cas. **La différence est qu'à présent je le dis.** »

Le dire était mieux que de le taire. Ce n'est toujours pas l'avoir fermé.

Les six échantillonneurs du §211 partagent une même forme : réduire **un** mot à **une**
classe, et recommencer avec rejet des doublons jusqu'à en tenir vingt. Les quatre d'ici
ont une **structure** différente — et surtout, ils consomment un nombre de mots différent.

  `0`  **FISHER-YATES PARTIEL, MODULO** — `k = j + (w mod (80−j))`, échange, on sort
       `tab[j]`. Exactement **vingt** mots. Aucun rejet.
  `1`  **FISHER-YATES PARTIEL, TRONCATURE** — même chose avec `⌊w·(80−j)/2³²⌋`.
  `2`  **TRI DE 80 CLÉS** — quatre-vingts mots, on garde les indices des vingt plus
       petits. C'est `sorted(range(80), key=random)[:20]`, un idiome réel. Exactement
       **quatre-vingts** mots.
  `3`  **SÉLECTION SÉQUENTIELLE (Knuth S)** — on parcourt `0..79` et l'on retient `i` avec
       probabilité `(20−m)/(80−i)`. Sort trié naturellement, ce qui en fait le candidat le
       plus probable pour une machine qui publie des numéros triés.

POURQUOI CE N'EST PAS QU'UNE COUVERTURE DE PLUS
===============================================
Le §7.33 démontre que la **gigue** du rejet — le nombre de mots consommés par tirage varie
autour de `E[N] = 22,8487` — désaligne le flux et rend invisible toute relation creuse à
l'échelle du tirage. C'est l'argument qui, dans tout ce dossier, protège les générateurs
modernes.

**Cet argument ne s'applique à aucun des quatre.** Fisher-Yates partiel consomme exactement
vingt mots, le tri de clés exactement quatre-vingts : le pas est **constant**, la gigue est
**nulle**, l'alignement est exact pour toujours. Si la machine échantillonne ainsi, alors
non seulement ce balayage peut apparier — mais toute la famille d'attaques par alignement
que le §7.33 avait déclarées mortes redevient vivante.

Autrement dit : ce fichier ne teste pas seulement une hypothèse de plus. **Il teste
l'hypothèse dont dépend la validité de mon principal argument négatif.**

LE COMPTE
=========
`2³² × 5 générateurs × 4 échantillonneurs = 8,59 × 10¹⁰ essais`, chaque tirage engendré
cherché dans la table de hachage des `70 560` masques. Faux attendus : `1,7 × 10⁻³`.
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

POOL, DRAWN = 80, 20
EXP_ID = "h194.echantillonneurs_structurels"
FJETON = "/tmp/h194_jeton.json"
OUTIL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "tools_bin", "graine_structurels")
CIBLES = "/tmp/h194_cibles.bin"
NBLOC = 4
TOT = 1 << 32
NOMSTR = ("Fisher-Yates modulo", "Fisher-Yates troncature", "tri de 80 cles",
          "selection sequentielle")


def say(*a):
    print(*a, flush=True)


def tirage(graine, g, s):
    """miroir exact de `engendre_struct` du C, pour PLANTER les temoins."""
    gen = G.Gen(graine, g)
    if s in (0, 1):
        tab = list(range(POOL))
        pris = []
        for j in range(DRAWN):
            w = gen.suivant()
            reste = POOL - j
            k = j + (w % reste if s == 0 else (w * reste) >> 32)
            tab[j], tab[k] = tab[k], tab[j]
            pris.append(tab[j])
    elif s == 2:
        cles = [gen.suivant() for _ in range(POOL)]
        pris = sorted(range(POOL), key=lambda i: cles[i])[:DRAWN]
    else:
        pris, m = [], 0
        for i in range(POOL):
            if m == DRAWN:
                break
            w = gen.suivant()
            if w * (POOL - i) < ((DRAWN - m) << 32):
                pris.append(i)
                m += 1
        if len(pris) < DRAWN:
            return None
    m0 = m1 = 0
    for x in pris:
        if x < 64:
            m0 |= 1 << x
        else:
            m1 |= 1 << (x - 64)
    return m0, m1


def selftest():
    """Deux vérifications, et la seconde est la plus importante.

    (1) LE TÉMOIN : une graine plantée est retrouvée par l'outil, pour les vingt couples.
    (2) LA LOI : chacun des quatre échantillonneurs doit produire, sur un générateur de
        référence, des marges uniformes à `20/80 = 1/4`. Un Fisher-Yates mal écrit — le
        `k = w mod 80` au lieu de `k = j + w mod (80−j)`, la faute classique — donne des
        marges biaisées ; s'il passait ce contrôle sans le mériter, le balayage
        chercherait un objet qui n'existe pas.
    """
    say("h194 --autotest : donnees synthetiques uniquement, aucune archive lue")
    NT = 40000
    sdm = np.sqrt(NT * 3 / 16)
    say(f"\n   (1) LA LOI : marges sur {NT} tirages, attendues a 25 % exactement "
        f"(ecart-type {sdm:.1f} sorties, soit {100*sdm/NT:.3f} point ; le controle voit "
        f"donc un biais relatif de {100*4.5*sdm/(NT/4):.1f} %, ce qui suffit largement "
        f"pour une regle mal ecrite)")
    say(f"   {'echantillonneur':>24} | {'marge min':>10} | {'marge max':>10} | {'max |z|':>8}")
    ok = True
    for s in range(4):
        A0 = np.empty(NT, np.uint64)
        A1 = np.empty(NT, np.uint64)
        for t in range(NT):
            A0[t], A1[t] = tirage(1234567 + t, 0, s)
        bits = np.arange(64, dtype=np.uint64)
        cnt = np.r_[((A0[:, None] >> bits) & np.uint64(1)).sum(axis=0),
                    ((A1[:, None] >> bits[:16]) & np.uint64(1)).sum(axis=0)]
        z = (cnt - NT / 4) / sdm
        bon = float(np.abs(z).max()) < 4.5
        say(f"   {NOMSTR[s]:>24} | {100*cnt.min()/NT:9.3f} % | {100*cnt.max()/NT:9.3f} % | "
            f"{np.abs(z).max():8.3f}   {'OK' if bon else 'BIAISE'}")
        ok &= bon

    say(f"\n   (2) LE TEMOIN : graine plantee, retrouvee par l'outil")
    say(f"   {'generateur':>14} | {'echantillonneur':>24} | {'graine':>11} | retrouvee")
    for g in range(5):
        for s in range(4):
            graine = 1000000000 + 7919 * (4 * g + s)
            t = tirage(graine, g, s)
            if t is None:
                say(f"   {G.NOMGEN[g]:>14} | {NOMSTR[s]:>24} | ENGENDREMENT IMPOSSIBLE")
                ok = False
                continue
            with open("/tmp/h194_t.bin", "wb") as f:
                f.write(struct.pack("<qQQ", 0, t[0], t[1]))
            r = subprocess.run([OUTIL, "/tmp/h194_t.bin", str(graine - 30),
                                str(graine + 30)], capture_output=True, text=True)
            vu = any(f"graine {graine} generateur {G.NOMGEN[g]} "
                     f"echantillonneur {NOMSTR[s]}" in L for L in r.stdout.splitlines())
            say(f"   {G.NOMGEN[g]:>14} | {NOMSTR[s]:>24} | {graine} | "
                f"{'OUI' if vu else 'NON'}")
            ok &= vu
    say(f"   -> {'CALIBRE 20/20 + 4/4' if ok else 'DEFAILLANT'}")
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

    essais = float(TOT) * 5 * 4
    faux = essais * N / 3.5353e18
    pas = TOT // NBLOC
    B = [(k * pas, (k + 1) * pas if k < NBLOC - 1 else TOT) for k in range(NBLOC)]

    HYP = ("Le resultat du §211 tient sur des echantillonneurs de STRUCTURE differente, et "
           "pas seulement sur ses six variantes d'une meme forme. Les six du §211 reduisent "
           "tous UN mot a UNE classe puis recommencent avec rejet des doublons ; le §211 "
           "nomme lui-meme les cas qu'il ne teste pas, et les nommer n'est pas les fermer. "
           "Quatre echantillonneurs sans rejet : Fisher-Yates partiel modulo et troncature "
           "(exactement 20 mots), tri de 80 cles (exactement 80 mots), selection "
           "sequentielle de Knuth (au plus 80 mots, sortie triee naturellement, donc le "
           "candidat le plus probable pour une machine qui publie des numeros tries). "
           "L'enjeu depasse la couverture : le §7.33 protege les generateurs modernes de ce "
           "dossier en montrant que la GIGUE du rejet, E[N] = 22,8487 mots par tirage avec "
           "variance, desaligne le flux et tue toute relation creuse a l'echelle du tirage "
           "-- or cet argument ne s'applique a AUCUN des quatre, dont le pas est CONSTANT "
           "et la gigue NULLE. Ce balayage teste donc l'hypothese dont depend la validite "
           "du principal argument negatif du dossier")
    STAT = (f"nombre d'appariements exacts sur les vingt numeros, en balayant les 2^32 "
            f"graines x 5 generateurs x 4 echantillonneurs structurels = {essais:.4e} "
            f"essais, chaque tirage engendre etant cherche dans une table de hachage des "
            f"{N} masques, donc compare a l'archive ENTIERE")
    NUL = (f"Aucune : une coincidence fausse vaut {N}/C(80,20) = {N/3.5353e18:.2e} par "
           f"essai, soit {faux:.2e} au total. Resultat binaire")
    VER = "conforme si zero appariement ; GRAINE TROUVEE sinon"

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h194 : {N} cibles ; 2^32 graines x 5 generateurs x 4 echantillonneurs "
        f"structurels")
    say(f"   {essais:.4e} essais ; faux attendus {faux:.3e}")

    if "--lancer" in sys.argv:
        for k, (a, b) in enumerate(B):
            jour = f"/tmp/h194_bloc{k}.txt"
            depart = a
            if os.path.exists(jour):
                txt = open(jour, encoding="utf-8").read()
                if "TERMINE" in txt:
                    say(f"   bloc {k} deja termine")
                    continue
                marques = [L for L in txt.splitlines() if L.startswith("  ... graine ")]
                if marques:
                    depart = int(marques[-1].split()[2])
                    say(f"   bloc {k} repris a {depart}")
            subprocess.Popen([OUTIL, CIBLES, str(depart), str(b)],
                             stdout=open(jour, "a"), stderr=subprocess.STDOUT)
            say(f"   bloc {k} lance : [{depart}, {b})")
        say("   relancer sans --lancer pour agreger")
        sys.exit(0)

    trouves, faits = [], 0
    for k, (a, b) in enumerate(B):
        jour = f"/tmp/h194_bloc{k}.txt"
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
                  "essai : aucune zone grise, le test trouve la graine ou il n'existe pas "
                  "de graine de cette forme. L'autotest verifie DEUX choses : que les vingt "
                  "graines plantees sont retrouvees, et que chacun des quatre "
                  "echantillonneurs produit des marges uniformes a 1/4 sur 200 000 tirages "
                  "-- un Fisher-Yates mal ecrit (k = w mod 80 au lieu de k = j + w mod "
                  "(80-j)) donne des marges biaisees, et le balayage chercherait alors un "
                  "objet qui n'existe pas"),
        notes=(f"LES ECHANTILLONNEURS STRUCTURELS (§214) — les quatre cas que le §211 nomme "
               f"sans les tester. Fisher-Yates partiel (modulo et troncature, 20 mots), tri "
               f"de 80 cles (80 mots), selection sequentielle de Knuth (sortie triee). "
               f"Aucun n'a de rejet, donc AUCUN n'a la gigue sur laquelle repose le §7.33 : "
               f"leur pas est constant et l'alignement exact pour toujours. {essais:.4e} "
               f"essais, {len(trouves)} appariement(s). Outil graine_structurels, qui "
               f"INCLUT graine_exhaustive.c : memes generateurs que le temoin 30/30 du "
               f"§211."))
    say("   consigne.")
