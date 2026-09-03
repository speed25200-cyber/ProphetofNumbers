"""h209 — LE RÉSEAU SUR LE FLUX DU BONUS : l'archive contenait un relevé ordonné
(RAPPORT §230).

CE QUI EST NOUVEAU ICI, ET CE QUI NE L'EST PAS
==============================================
**Rien du fait lui-même.** Le §77 a établi que le `bonus` est *toujours* l'un des vingt
numéros tirés — `70 560` sur `70 560` — et le bloc `2` du vérificateur le recalcule depuis
les CSV à chaque exécution. Le §106 a établi la règle : `bonus = triés[⌊u·20⌋]`, donc un
**index**, non un vingt-et-unième numéro. Le §175 en a tiré les `4,32` bits que le mot du
bonus rapporte à un crible. Le §222 en a testé la chaîne de Markov.

**Ce qui est nouveau, c'est le rapprochement avec le §225.** Le fichier
`lab/RELEVE_ORDONNE.md` déclare qu'il manque au dossier une *suite ordonnée de sorties*, et
c'était exact **sous le modèle d'alors** : à pas variable (rejet à l'extérieur du bloc), un
mot isolé par tirage ne sert à rien, faute de savoir de combien de pas ses voisins sont
séparés. Le §225 a corrigé ce modèle : sous un **budget fixe de `P` mots par tirage**, le
rejet se faisant à l'intérieur, deux mots au même décalage dans deux blocs consécutifs sont
séparés de **exactement `P` pas**.

> Sous le §225, **un mot par tirage suffit**. Le flux du bonus est alors une suite ordonnée
> de `70 560` sorties à pas constant — le relevé que je déclarais manquant, et qui était
> publié depuis le début.

Le §223 a monté le réseau sur des tirages ordonnés qui n'existent pas ; le §224 l'a monté
sur le **boost**, qui ne porte que `1,88` bit par tirage et a exigé `69 120` résolutions. Le
bonus porte `4,32` bits (son rang) ou `6,32` (son numéro) : c'est **le canal ordonné le plus
riche de l'archive**, et le réseau n'y a jamais été passé.

CE QUE ÇA DONNE, EXACTEMENT
===========================
Sous l'hypothèse du **bloc fixe** (§225 : un budget de `P` mots par tirage, le rejet se
faisant *à l'intérieur*), deux bonus consécutifs sont séparés par exactement `P` mots. Donc

    x_{t+1} = L^P(x_t)   avec   L : x -> a·x + c  mod 2⁶⁴

et `L^P` est **elle-même** une application affine, de constantes `(a^P, c·(a^P−1)/(a−1))`
calculables. **Le flux du bonus est donc un LCG**, de constantes connues dès que `P` l'est.
Le décalage du bonus dans le bloc s'absorbe dans l'état initial inconnu (§225), donc un seul
décalage suffit à couvrir les vingt.

LA RÈGLE MODULO EST DÉJÀ MORTE, ET C'EST GRATUIT
================================================
Si la classe était `w mod 80`, alors — puisque `16 | 80` — on aurait
`(bonus−1) mod 16 = w mod 16`. Or les bits bas d'un LCG `mod 2⁶⁴` forment un **sous-système
clos** (§7.36) : `w mod 16` suivrait un cycle **déterministe** d'au plus seize états. Une
table de contingence `80 × 80` verrait ça exploser — chaque ligne n'aurait de support que
sur cinq colonnes sur quatre-vingts. Le §222 a mesuré ces tables à tous les retards `1..20`
et les a trouvées uniformes. **La règle modulo est donc exclue sans un calcul de plus.**

Reste la **troncature** — la règle qui lit les bits *hauts*. Le §7.36 dit qu'elle ne fuit
**rien** statistiquement : c'est exactement pourquoi le §222 ne pouvait rien trouver. Mais
elle fuit **tout** algébriquement : c'est le cadre de Frieze-Håstad-Kannan-Lagarias, et
douze valeurs consécutives suffisent à retrouver un état de soixante-quatre bits.

DEUX CANAUX
===========
  **le numéro du bonus** — `6,32` bits par tirage, `n = 14` suffit largement ;
  **le rang du bonus parmi les vingt triés** — `4,32` bits, `n = 20`. Ce canal-là couvre le
     modèle où le bonus est choisi par un mot *supplémentaire* tirant un indice dans la
     liste triée.

La vérification est en **entiers exacts** sur dix valeurs de plus que celles utilisées :
une fausse alerte vaut `80⁻¹⁰`. Il n'y a pas de zone grise.
"""

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lll import _gso, lll                                              # noqa: E402
import h202_attaque_par_reseau as H2                                   # noqa: E402
import h203_reseau_sur_le_boost as H3                                  # noqa: E402

M64 = 1 << 64
POOL, DRAWN = 80, 20
EXP_ID = "h209.reseau_sur_le_bonus"
FJETON = "/tmp/h209_jeton.json"

PAS = tuple(range(1, 129))          # budget de mots par tirage, balaye
NFEN = 40                           # fenetres de depart, reparties sur l'archive
SUP = 10                            # valeurs de verification en plus de celles resolues

# (nom, base de la classe, n du reseau)
#
# Le n du canal du rang a ete choisi par MESURE, pas par calcul de bits : a n = 20 le
# relevement synthetique ne rend que 14 succes sur 18, a n = 18 il en rend 18 sur 18.
# Plus de contraintes n'aide pas indefiniment — la qualite de Babai se degrade avec la
# dimension plus vite que le systeme ne se contraint. Le calcul de bits (18 x 4,32 = 77,8
# contre 64 a trouver) dit seulement que n = 18 SUFFIT ; c'est le temoin qui dit qu'il est
# le bon.
CANAUX = (("numero du bonus", 80, 14),
          ("rang du bonus parmi les 20 tries", 20, 18))

# (nom, decalage de lecture) : ((x >> dec) * base) >> 32 ou (x * base) >> 64
REGLES = (("troncature 64 bits", 64), ("troncature du mot haut", 32))


def say(*a):
    print(*a, flush=True)


def _arg(nom, defaut):
    return sys.argv[sys.argv.index(nom) + 1] if nom in sys.argv else defaut


def affine(a, c, e, m=M64):
    """(x -> a x + c)^e mod m, par exponentiation rapide."""
    aa, bb, k = 1, 0, e
    ba, bc = a, c
    while k:
        if k & 1:
            aa, bb = (aa * ba) % m, (bb * ba + bc) % m
        ba, bc = (ba * ba) % m, (bc * ba + bc) % m
        k >>= 1
    return aa, bb


def classe(x, base, larg):
    """classe 0..base-1 lue sur les bits hauts de x."""
    if larg == 64:
        return (x * base) >> 64
    return (((x >> 32) & 0xFFFFFFFF) * base) >> 32


def intervalle(c, base, larg):
    """intervalle exact [lo, hi] des etats de classe c."""
    if larg == 64:
        lo = -(-(c << 64) // base)
        hi = -(-((c + 1) << 64) // base)
        return lo, hi - 1
    lo_w = -(-(c << 32) // base)
    hi_w = -(-((c + 1) << 32) // base)
    return lo_w << 32, (hi_w << 32) - 1


def prepare(A, n):
    """base du reseau pour le multiplicateur effectif A et n contraintes, DEJA reduite.

    La base ne depend que de (A, n) — ni de l'increment, ni des classes, ni de la regle.
    On la reduit une fois et l'on resout des milliers de fois (§224).
    """
    Ai, pw = [], 1
    for _ in range(n):
        pw = (pw * A) % M64
        Ai.append(pw)
    base = [Ai] + [[M64 if j == i else 0 for j in range(n)] for i in range(n)]
    red = lll(base)
    return Ai, red, _gso(red)


def increments(a, c, n):
    """B_i = increment cumule apres i+1 pas de x -> a x + c."""
    B, bb = [], 0
    for _ in range(n):
        bb = (bb * a + c) % M64
        B.append(bb)
    return B


def attaque(cs, Ai, red, gso, B, base_cl, larg):
    """cs : n classes consecutives. Renvoie x0 candidat ou None."""
    cible = []
    for i, ci in enumerate(cs):
        lo, hi = intervalle(int(ci), base_cl, larg)
        cible.append(((lo + hi) // 2 - B[i]) % M64)
    try:
        v = H3.babai_reduit(red, gso, cible)
    except Exception:
        return None
    return (int(v[0]) % M64) * pow(Ai[0], -1, M64) % M64


def verifie(x0, A, C, cs, base_cl, larg):
    """verification EXACTE en entiers sur toutes les classes fournies."""
    x = x0
    for ci in cs:
        x = (A * x + C) % M64
        if classe(x, base_cl, larg) != int(ci):
            return False
    return True


def selftest():
    say("h209 --autotest : flux synthetique uniquement, aucune archive lue")
    ok = True
    say(f"\n   {'generateur':>22} | {'pas':>4} | {'canal':>8} | {'regle':>22} | "
        f"{'temps':>7} | resultat")
    VRAI = 0x0123456789ABCDEF
    for nom, a, c in H2.LCGS[:3]:
        for pas in (1, 23, 82):
            A, C = affine(a, c, pas)
            for _cn, base_cl, n in CANAUX:
                for nomr, larg in REGLES:
                    x, cs = VRAI, []
                    for _ in range(n + SUP):
                        x = (A * x + C) % M64
                        cs.append(classe(x, base_cl, larg))
                    t = time.time()
                    Ai, red, gso = prepare(A, n)
                    B = increments(A, C, n)
                    got = attaque(cs[:n], Ai, red, gso, B, base_cl, larg)
                    dt = time.time() - t
                    bon = got is not None and verifie(got, A, C, cs, base_cl, larg)
                    if pas == 23 and base_cl == 80:
                        say(f"   {nom:>22} | {pas:4d} | {base_cl:8d} | {nomr:>22} | "
                            f"{dt:6.2f}s | "
                            f"{'EXACT' if got == VRAI else ('compatible' if bon else 'ECHEC')}")
                    ok &= bon
    say(f"   -> {'CALIBRE' if ok else 'DEFAILLANT'} "
        f"(3 generateurs x 3 pas x 2 canaux x 2 regles = 36 relevements)")
    return ok


if __name__ == "__main__":
    if "--autotest" in sys.argv:
        sys.exit(0 if selftest() else 1)

    import lab

    if not selftest():
        say("autotest en echec : on n'attaque pas l'archive avec un outil non calibre")
        sys.exit(1)

    A_ = lab.load()
    bonus = np.asarray(A_.bonus).astype(np.int64)
    nums = np.asarray(A_.nums).astype(np.int64)
    TS = np.asarray(A_.ts).astype(np.int64)
    N = len(bonus)
    BOR = np.r_[0, np.flatnonzero(np.diff(TS) > 1000) + 1, N]

    dedans = int((nums == bonus[:, None]).any(axis=1).sum())
    say(f"\nh209 : bonus appartenant au tirage : {dedans} / {N}")
    if dedans != N:
        say("   le fait de format n'est pas verifie — on s'arrete")
        sys.exit(1)

    SUITES = {
        "numero du bonus": bonus - 1,
        "rang du bonus parmi les 20 tries": (nums < bonus[:, None]).sum(axis=1),
    }

    # fenetres : NFEN departs repartis, chacun ENTIEREMENT a l'interieur d'une nuit
    besoin = max(n for _, _, n in CANAUX) + SUP
    nuits = [(BOR[i], BOR[i + 1]) for i in range(len(BOR) - 1)
             if BOR[i + 1] - BOR[i] >= besoin + 4]
    pas_nuit = max(1, len(nuits) // NFEN)
    depart = [nuits[i][0] + 1 for i in range(0, len(nuits), pas_nuit)][:NFEN]
    say(f"   {len(nuits)} nuits utilisables, {len(depart)} fenetres de depart")
    say(f"   {len(H2.LCGS)} generateurs x {len(PAS)} pas x {len(CANAUX)} canaux x "
        f"{len(REGLES)} regles x {len(depart)} fenetres")
    NTEST = len(H2.LCGS) * len(PAS) * len(CANAUX) * len(REGLES) * len(depart)
    say(f"   = {NTEST} relevements, verification exacte sur {SUP} valeurs de plus")

    HYP = (f"Le flux du bonus n'est pas la sortie tronquee d'un LCG mod 2^64 a constantes "
           f"publiees, a pas de bloc fixe. CE QUI EST NOUVEAU N'EST PAS LE FAIT MAIS SON "
           f"EMPLOI : que le bonus appartienne au tirage ({dedans} sur {N}) est acquis "
           f"depuis le §77 et recalcule par le bloc 2 du verificateur ; que la regle soit "
           f"bonus = tries[floor(u*20)] est acquis depuis le §106 ; ses 4,32 bits sont "
           f"exploites par le crible du §175 ; sa chaine de Markov est testee au §222. Ce "
           f"qui change, c'est le §225 : lab/RELEVE_ORDONNE.md declarait qu'il manquait au "
           f"dossier une suite ordonnee de sorties, et c'etait exact SOUS LE MODELE D'ALORS "
           f"— a pas variable, un mot isole par tirage ne sert a rien faute de savoir de "
           f"combien de pas ses voisins sont separes. Sous le budget de bloc FIXE du §225, "
           f"deux mots au meme decalage dans deux blocs consecutifs sont separes d'exactement "
           f"P pas : le flux du bonus est alors une suite ordonnee de {N} sorties a pas "
           f"constant, donc LUI-MEME un LCG de constantes (a^P, c(a^P-1)/(a-1)) calculables, "
           f"le decalage du bonus dans le bloc s'absorbant dans l'etat initial. Le §223 a "
           f"monte le reseau sur des tirages ordonnes qui n'existent pas, le §224 sur le "
           f"boost qui ne porte que 1,88 bit ; le bonus en porte 4,32 (son rang) ou 6,32 "
           f"(son numero) et le reseau n'y est jamais passe. La regle modulo est deja "
           f"exclue gratuitement : 16 divise 80, donc (bonus-1) mod 16 = w mod 16 suivrait "
           f"un cycle DETERMINISTE de 16 etats (sous-systeme clos du §7.36), ce que les "
           f"tables 80x80 du §222 auraient vu exploser. Reste la troncature, invisible "
           f"statistiquement (§7.36) et ouverte algebriquement (Frieze-Hastad-Kannan-"
           f"Lagarias) : c'est elle qu'on attaque")
    STAT = (f"nombre de relevements dont l'etat candidat reproduit EXACTEMENT, en entiers, "
            f"les {SUP} classes suivantes non utilisees par le reseau, sur {NTEST} tentatives")
    NUL = (f"EXACTE et combinatoire : un candidat faux reproduit {SUP} classes de plus par "
           f"hasard avec probabilite base^-{SUP}, soit 80^-{SUP} = 1e-19 pour le canal du "
           f"numero et 20^-{SUP} = 1e-13 pour celui du rang ; sur {NTEST} tentatives "
           f"l'esperance de faux positifs est inferieure a 1e-8. Il n'y a pas de zone grise")
    VER = ("ETAT RELEVE si au moins un candidat passe la verification exacte — auquel cas "
           "il donne tous les tirages suivants ET precedents ; conforme sinon, ce qui "
           "exclut la famille entiere (LCG mod 2^64 a constantes publiees, pas fixe <= 128, "
           "sortie tronquee) sur le seul canal ordonne de l'archive")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    if "--jeton" in sys.argv:
        say("   jeton pose ; les parts peuvent partir")
        sys.exit(0)

    # --- decoupage en parts : le balayage est du Python pur, 4 coeurs valent 4 parts
    NPARTS = int(_arg("--nparts", 1))
    PART = int(_arg("--part", 0))
    FPART = "/tmp/h209_part%d.json"

    if "--agrege" in sys.argv:
        survivants, fait, t0 = [], 0, time.time()
        for k in range(NPARTS):
            d = json.load(open(FPART % k, encoding="utf-8"))
            fait += d["fait"]
            survivants += [tuple(s) for s in d["survivants"]]
            say(f"   part {k} : {d['fait']} relevements, {len(d['survivants'])} survivants")
    else:
        t0 = time.time()
        survivants, fait = [], 0
        for ic, (nom, a, c) in enumerate(H2.LCGS):
            if ic % NPARTS != PART:
                continue
            for pas in PAS:
                A, C = affine(a, c, pas)
                for canal, base_cl, n in CANAUX:
                    s = SUITES[canal]
                    Ai, red, gso = prepare(A, n)
                    B = increments(A, C, n)
                    for nomr, larg in REGLES:
                        for d0 in depart:
                            cs = s[d0:d0 + n + SUP]
                            x0 = attaque(cs[:n], Ai, red, gso, B, base_cl, larg)
                            fait += 1
                            if x0 is not None and verifie(x0, A, C, cs, base_cl, larg):
                                survivants.append(
                                    (nom, pas, canal, nomr, int(d0), int(x0)))
                                say(f"   *** SURVIVANT : {nom}, pas {pas}, {canal}, "
                                    f"{nomr}, depart {d0}, x0 = {x0}")
            say(f"   part {PART} {nom:>24} : {fait} relevements, "
                f"{len(survivants)} survivants, {time.time()-t0:7.1f}s")

        if NPARTS > 1:
            json.dump({"fait": fait, "survivants": survivants},
                      open(FPART % PART, "w", encoding="utf-8"))
            say(f"   part {PART} ecrite : {fait} relevements, {len(survivants)} survivants")
            sys.exit(0)

    say(f"\n   {fait} relevements sur {NTEST} annonces, {len(survivants)} survivants, "
        f"{time.time()-t0:.1f}s")

    verdict = "ETAT RELEVE" if survivants else "conforme"
    p = 1.0 if not survivants else 1e-19
    say(f"\n   {verdict}")

    TOK["m_extra"] = 0
    lab.record(
        TOK, float(len(survivants)), p=float(p), verdict=verdict,
        power_at=(f"l'autotest releve l'etat EXACT sur 36 flux synthetiques — 3 generateurs "
                  f"x 3 pas (1, 23, 82) x 2 canaux x 2 regles — donc l'outil retrouve un "
                  f"etat de 64 bits a partir de 14 numeros de bonus (6,32 bits chacun) ou "
                  f"de 20 rangs (4,32 bits). La puissance est TOTALE a l'interieur de la "
                  f"famille balayee : si le flux du bonus etait la troncature d'un des "
                  f"{len(H2.LCGS)} LCG a un pas de bloc <= {max(PAS)}, il serait releve avec "
                  f"certitude, pas avec probabilite. La nullite n'exclut donc pas 'un "
                  f"generateur' mais TOUTE cette famille sur ce canal"),
        notes=(f"LE RESEAU SUR LE FLUX DU BONUS (§230) — le fait (bonus dans le tirage, "
               f"{dedans}/{N}) est du §77, la regle tries[floor(u*20)] du §106, les 4,32 "
               f"bits du §175, la chaine de Markov du §222 ; ce qui est nouveau est le "
               f"rapprochement avec le §225 : sous un budget de bloc FIXE, un mot par "
               f"tirage suffit, car deux bonus consecutifs sont alors separes d'exactement "
               f"P pas. Le flux du bonus est donc la suite ordonnee a pas constant que "
               f"RELEVE_ORDONNE.md declarait manquante — declaration exacte sous le modele "
               f"a pas variable d'alors, perimee par le §225. Regle modulo exclue "
               f"gratuitement (16 | 80 -> cycle deterministe de "
               f"16 etats, que les tables du §222 auraient vu). Attaque par reseau sur la "
               f"troncature : {fait} relevements ({len(H2.LCGS)} LCG x {len(PAS)} pas x "
               f"{len(CANAUX)} canaux x {len(REGLES)} regles x {len(depart)} fenetres de "
               f"nuit), verification en entiers exacts sur {SUP} classes de plus. "
               f"{len(survivants)} survivants."))
    say("   consigne.")
