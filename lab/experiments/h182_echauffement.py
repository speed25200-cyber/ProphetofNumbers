"""h182 — L'ÉCHAUFFEMENT : le cas qu'un balayage de graine simple manque (RAPPORT §201).

CE QUE LE §200 NE COUVRE PAS
============================
Le §200 balaye les graines d'horloge des cinq générateurs modernes et ne trouve rien sur
`9,83·10⁹` essais. Mais il suppose, sans le dire, que **le premier mot tiré après
l'amorçage est le premier mot du tirage**.

Une machine réelle ne se comporte presque jamais ainsi. Elle s'amorce, puis consomme
quelques mots pour autre chose — une initialisation, un identifiant, un mélange préalable,
un test — avant de tirer les numéros. Le décalage est petit et inconnu, et il suffit à
faire échouer tout le balayage du §200.

C'est un angle mort que je me suis créé moi-même en écrivant l'outil, et il faut le fermer.

CE QUI EST BALAYÉ ICI
=====================
Le même panel — cinq générateurs à un seul pas × deux échantillonneurs — mais avec un
troisième axe : le nombre de mots **jetés après l'amorçage**, de `0` à `300`.

  A  les 346 débuts de nuit, graine `ts + δ` avec `|δ| ≤ 3 600 s`, échauffement `0..300`
  B  2 000 tirages répartis dans toute l'archive, `|δ| ≤ 60 s`, échauffement `0..300`

`8,2·10⁹` essais de plus, et la même règle : un appariement fortuit a une probabilité de
`1/C(80,20) = 2,8·10⁻¹⁹`, donc **tout appariement est réel** et le résultat est binaire.

LE TÉMOIN
=========
Une graine plantée **avec** un échauffement de `37` mots est retrouvée par l'outil, à
l'échauffement `37` exactement (et à `38` et `39`, parce que les mots jetés y donnaient
des classes déjà vues — c'est le comportement correct, pas un défaut).
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import h181_graine_moderne as G                                        # noqa: E402

POOL, DRAWN = 80, 20
EXP_ID = "h182.echauffement"
FJETON = "/tmp/h182_jeton.json"
WMAX = 300
FEN_A = 3600
FEN_B = 60
NB_B = 2000


def say(*a):
    print(*a, flush=True)


def selftest():
    say("h182 --autotest : donnees synthetiques uniquement, aucune archive lue")
    ok = True
    say(f"   {'generateur':>14} | {'ech.':>10} | echauffement plante | retrouve")
    for g, s_, w in ((3, 0, 37), (0, 1, 5), (4, 0, 128), (1, 1, 200), (2, 0, 0)):
        graine = 1757829900 + 13 * g
        gen = G.Gen(graine, g)
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
        G.ecrire_cibles("/tmp/h182_t.bin", [(graine - 3, m0, m1)])
        out = G.lancer("/tmp/h182_t.bin", 3, 10, 1, WMAX)
        vu = any(f"generateur {G.NOMGEN[g]} echantillonneur {G.NOMECH[s_]}" in L
                 and f"graine {graine} " in L and f"echauffement {w}" in L
                 for L in out.splitlines())
        say(f"   {G.NOMGEN[g]:>14} | {G.NOMECH[s_]:>10} | {w:19d} | "
            f"{'OUI' if vu else 'NON'}")
        ok &= vu
    say(f"   -> balayage d'echauffement {'CALIBRE 5/5' if ok else 'DEFAILLANT'}")
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
    DEB = np.r_[0, np.flatnonzero(np.diff(TS) > 1000) + 1]
    ECH = np.linspace(0, N - 1, NB_B).astype(np.int64)

    HYP = ("Aucun generateur moderne a un seul pas — splitmix64, xoshiro256++, "
           "xoshiro128**, pcg32, pcg64 — amorce sur l'horloge PUIS ECHAUFFE de 0 a 300 "
           "mots n'engendre le tirage observe. Le §200 balayait les memes graines mais "
           "supposait, sans le dire, que le premier mot tire apres l'amorcage est le "
           "premier mot du tirage. Une machine reelle consomme presque toujours quelques "
           "mots avant — initialisation, identifiant, melange prealable — et ce decalage "
           "suffit a faire echouer tout le balayage precedent. C'est un angle mort que "
           "j'ai cree moi-meme en ecrivant l'outil")
    STAT = (f"nombre d'appariements exacts sur les vingt numeros. Balayage A : les "
            f"{len(DEB)} debuts de nuit, graines ts+delta pour |delta| <= {FEN_A} s, "
            f"echauffement de 0 a {WMAX} mots. Balayage B : {NB_B} tirages repartis "
            f"regulierement dans l'archive, |delta| <= {FEN_B} s, meme echauffement. Cinq "
            "generateurs x deux echantillonneurs")
    NUL = ("Aucune : un appariement fortuit sur les vingt numeros a une probabilite de "
           "1/C(80,20) = 2,8e-19 par essai. Le resultat est BINAIRE")
    VER = ("conforme si zero appariement ; GRAINE TROUVEE sinon, auquel cas l'etat et "
           "l'echauffement sont connus et tout ce qui suit est predit")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    trouves = []
    total = 0.0
    for nom, idx, fen in (("A debuts de nuit", DEB, FEN_A),
                          ("B echantillon reparti", ECH, FEN_B)):
        say(f"\n{nom} : {len(idx)} cibles, fenetre +-{fen} s, echauffement 0..{WMAX}")
        G.ecrire_cibles("/tmp/h182.bin", [(TS[i], M0[i], M1[i]) for i in idx])
        out = G.lancer("/tmp/h182.bin", 3, fen, 1, WMAX)
        for L in out.splitlines():
            if L.startswith("APPARIEMENT"):
                trouves.append(L)
                say("   " + L)
            elif L.startswith(("cibles", "graines", "TERMINE")):
                say("   " + L)
        total += len(idx) * (2 * fen + 1) * 10 * (WMAX + 1)

    say(f"\n   essais totaux {total:.3e} ; faux attendus {total*2.8e-19:.3e}")
    say(f"   appariements : {len(trouves)}")
    TOK["m_extra"] = 0
    lab.record(
        TOK, float(len(trouves)), p=1.0 if not trouves else 0.0,
        verdict="GRAINE TROUVEE" if trouves else "conforme",
        power_at=("l'autotest plante cinq graines AVEC echauffement (37, 5, 128, 200 et "
                  "0 mots, sur cinq couples generateur x echantillonneur differents) et "
                  f"l'outil les retrouve toutes les cinq, a l'echauffement exact. Sur "
                  f"{total:.2e} essais l'esperance de faux vaut {total*2.8e-19:.1e}"),
        notes=(f"ECHAUFFEMENT (§201) — l'angle mort du §200. Cinq generateurs modernes x "
               f"deux echantillonneurs x graines d'horloge x {WMAX+1} echauffements. "
               f"Balayage A : {len(DEB)} debuts de nuit, fenetre +-{FEN_A} s. Balayage B : "
               f"{NB_B} tirages repartis, fenetre +-{FEN_B} s. {total:.3e} essais, "
               f"{len(trouves)} appariement(s). Avec le §200, le total des deux sections "
               f"atteint {(total + 9.831e9):.3e} essais de graine."))
    say("   consigne.")
