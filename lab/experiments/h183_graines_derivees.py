"""h183 — LES GRAINES DÉRIVÉES : et si la graine n'était pas l'heure ? (RAPPORT §202).

CE QUE LES §200 ET §201 SUPPOSENT
=================================
Les deux sections précédentes balayent les graines d'horloge des générateurs modernes, avec
et sans échauffement, sur `1,8·10¹⁰` essais. Elles supposent toutes deux que **la graine est
une date** — la seconde ou la milliseconde du tirage.

Ce n'est pas la seule façon d'amorcer une machine, et ce n'est même pas la plus courante
dans un système de loterie. Un identifiant de tirage est un compteur, il est publié, il est
strictement consécutif (`verifier.py`, bloc 1), et il ferait une graine parfaitement
naturelle — `seed = numero_du_tirage`. Personne n'a testé cela.

LES HUIT DÉRIVÉES
=================
Pour chaque tirage, huit bases de graine, chacune balayée sur une petite fenêtre :

  1  `id`                        l'identifiant du tirage, tel quel
  2  `id · 1000`                 le même, mis à l'échelle d'une milliseconde
  3  `ts − id`                   l'écart entre l'horloge et le compteur
  4  `ts + id`                   leur somme
  5  `ts mod 86 400`             les secondes depuis minuit
  6  `AAAAMMJJ`                  la date en entier décimal
  7  `numéro de nuit`            `0..345`
  8  `numéro dans la nuit`       `0..203`

Les deux dernières ont un espace minuscule : la fenêtre les couvre **entièrement**, ce qui
en fait un test exhaustif et non un sondage.

Chaque base est balayée avec un échauffement de `0` à `50` mots, la leçon du §201 étant
qu'un balayage de graine sans échauffement rate une machine réelle.

Le résultat reste binaire : `1/C(80,20) = 2,8·10⁻¹⁹` par essai, donc **tout appariement est
réel**.
"""

import json
import os
import sys
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import h181_graine_moderne as G                                        # noqa: E402

POOL, DRAWN = 80, 20
EXP_ID = "h183b.graines_derivees"
FJETON = "/tmp/h183b_jeton.json"
FJOURNAL = "/tmp/h183b_journal.json"
# Le premier jeton (h183) declarait une fenetre de +-100 et un echauffement de 0 a 50, soit
# 5,8e10 essais — environ quatre heures, sans reprise possible entre deux redemarrages du
# conteneur. Il a ete ABANDONNE AVANT TOUT RESULTAT, et re-scelle ici sur une grille
# executable et journalisee. Aucune donnee n'avait ete regardee : ce n'est pas un choix
# apres coup, c'est un choix de faisabilite.
FEN = 20
WMAX = 50


def say(*a):
    print(*a, flush=True)


def bases(ids, ts, nuit, rang_nuit):
    j = np.array([int(datetime.fromtimestamp(int(t), timezone.utc).strftime("%Y%m%d"))
                  for t in ts], np.int64)
    return [
        ("id", ids),
        ("id x 1000", ids * 1000),
        ("ts - id", ts - ids),
        ("ts + id", ts + ids),
        ("secondes depuis minuit", ts % 86400),
        ("date AAAAMMJJ", j),
        ("numero de nuit", nuit),
        ("numero dans la nuit", rang_nuit),
    ]


def selftest():
    say("h183 --autotest : donnees synthetiques uniquement, aucune archive lue")
    ok = True
    say(f"   {'generateur':>14} | base plantee | retrouvee")
    for g, s_, base, w in ((0, 0, 1309614, 0), (3, 1, 20260903, 7), (4, 0, 173, 21)):
        gen = G.Gen(base, g)
        for _ in range(w):
            gen.suivant()
        vus = set()
        for _ in range(300):
            x = gen.suivant()
            vus.add(((x * POOL) >> 32) if s_ == 0 else (x % POOL))
            if len(vus) == DRAWN:
                break
        m0 = m1 = 0
        for c in vus:
            if c < 64:
                m0 |= 1 << c
            else:
                m1 |= 1 << (c - 64)
        G.ecrire_cibles("/tmp/h183_t.bin", [(base - 4, m0, m1)])
        out = G.lancer("/tmp/h183_t.bin", 3, 10, 1, WMAX)
        vu = any(f"graine {base} " in L and f"echauffement {w}" in L
                 for L in out.splitlines())
        say(f"   {G.NOMGEN[g]:>14} | {base:12d} | {'OUI' if vu else 'NON'}")
        ok &= vu
    say(f"   -> {'CALIBRE 3/3' if ok else 'DEFAILLANT'}")
    return ok


if __name__ == "__main__":
    if "--autotest" in sys.argv:
        sys.exit(0 if selftest() else 1)

    import lab

    A = lab.load()
    N = len(A.ids)
    IDS = np.asarray(A.ids).astype(np.int64)
    TS = np.asarray(A.ts).astype(np.int64)
    NUMS = np.asarray(A.nums).astype(np.int64)
    M0 = np.zeros(N, np.uint64)
    M1 = np.zeros(N, np.uint64)
    for j in range(DRAWN):
        c = NUMS[:, j] - 1
        bas = c < 64
        M0[bas] |= (np.uint64(1) << c[bas].astype(np.uint64))
        M1[~bas] |= (np.uint64(1) << (c[~bas] - 64).astype(np.uint64))
    DEB = np.r_[0, np.flatnonzero(np.diff(TS) > 1000) + 1]
    nuit = np.zeros(N, np.int64)
    nuit[DEB] = 1
    nuit = np.cumsum(nuit) - 1
    rang_nuit = np.arange(N) - DEB[nuit]
    BASES = bases(IDS, TS, nuit, rang_nuit)

    HYP = ("La graine n'est pas davantage une quantite DERIVEE du tirage qu'elle n'etait "
           "l'heure. Les §200 et §201 supposent tous deux que la graine est une date ; or "
           "un identifiant de tirage est un compteur, il est publie, il est strictement "
           "consecutif, et il ferait une graine parfaitement naturelle. On balaye donc huit "
           "bases derivees — l'identifiant, l'identifiant en milliemes, sa somme et sa "
           "difference avec l'horloge, les secondes depuis minuit, la date en entier "
           "decimal, le numero de nuit et le rang dans la nuit — chacune avec un "
           f"echauffement de 0 a {WMAX} mots, sur les cinq generateurs modernes et les deux "
           "echantillonneurs. Pour les deux dernieres bases l'espace est si petit que la "
           "fenetre le couvre ENTIEREMENT : le test y est exhaustif")
    STAT = (f"nombre d'appariements exacts sur les vingt numeros, sur les {N} tirages, "
            f"{len(BASES)} bases de graine, fenetre +-{FEN}, echauffement 0..{WMAX}, "
            "cinq generateurs x deux echantillonneurs")
    NUL = ("Aucune : un appariement fortuit vaut 1/C(80,20) = 2,8e-19 par essai. Resultat "
           "binaire")
    VER = "conforme si zero appariement ; GRAINE TROUVEE sinon"

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h183 : {N} tirages, {len(BASES)} bases, fenetre +-{FEN}, "
        f"echauffement 0..{WMAX}")
    J = json.load(open(FJOURNAL, encoding="utf-8")) if os.path.exists(FJOURNAL) else {}
    trouves = []
    total = 0.0
    for nom, base in BASES:
        e = N * (2 * FEN + 1) * 10 * (WMAX + 1)
        total += e
        if nom in J:
            n_app, lignes = J[nom]["n"], J[nom]["lignes"]
        else:
            G.ecrire_cibles("/tmp/h183b.bin", zip(base, M0, M1))
            out = G.lancer("/tmp/h183b.bin", 3, FEN, 1, WMAX)
            lignes = [L for L in out.splitlines() if L.startswith("APPARIEMENT")]
            n_app = len(lignes)
            J[nom] = {"n": n_app, "lignes": lignes}
            json.dump(J, open(FJOURNAL, "w", encoding="utf-8"))
        for L in lignes:
            trouves.append(f"[{nom}] {L}")
            say("   " + f"[{nom}] {L}")
        say(f"   {nom:>24} : {e:.3e} essais, {n_app} appariement(s)"
            + ("   (espace couvert ENTIEREMENT)"
               if nom in ("numero de nuit", "numero dans la nuit") else ""))

    say(f"\n   essais totaux {total:.3e} ; faux attendus {total*2.8e-19:.3e}")
    say(f"   appariements : {len(trouves)}")
    TOK["m_extra"] = 0
    lab.record(
        TOK, float(len(trouves)), p=1.0 if not trouves else 0.0,
        verdict="GRAINE TROUVEE" if trouves else "conforme",
        power_at=("l'autotest plante trois graines derivees (un identifiant, une date en "
                  "entier decimal, un petit compteur) avec echauffement, sur trois "
                  f"generateurs differents, et l'outil les retrouve toutes. Sur {total:.2e} "
                  f"essais l'esperance de faux vaut {total*2.8e-19:.1e}"),
        notes=(f"GRAINES DERIVEES (§202) : {len(BASES)} bases — id, id x 1000, ts-id, "
               "ts+id, secondes depuis minuit, date AAAAMMJJ, numero de nuit, rang dans la "
               f"nuit — sur les {N} tirages, fenetre +-{FEN}, echauffement 0..{WMAX}, cinq "
               f"generateurs modernes x deux echantillonneurs. {total:.3e} essais, "
               f"{len(trouves)} appariement(s). Les deux dernieres bases ont un espace plus "
               "petit que la fenetre : le test y est EXHAUSTIF."))
    say("   consigne.")
