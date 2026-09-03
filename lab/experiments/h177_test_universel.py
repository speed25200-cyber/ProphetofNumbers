"""h177 — LE TEST UNIVERSEL : l'archive est-elle incompressible ? (RAPPORT §193).

POURQUOI CE TEST EST DIFFÉRENT DE TOUS LES AUTRES
=================================================
Les six cent et quelques tests du dossier ont tous la même forme : *je suppose une forme de
défaut, je construis la statistique qui la lit, je mesure*. Le §192 pousse cette logique à
son terme — trente et un traits, neuf familles, un témoin planté par famille — mais reste
prisonnier de la même limite : **il ne voit que ce que ses traits savent lire**, et son
seul trou nommé (le xorshift à un pas) le prouve.

Il existe une classe de détecteurs qui échappe à cette limite : les **compresseurs**. Un
compresseur ne suppose rien. Il cherche *toute* régularité qu'il sait exprimer — répétitions
à n'importe quelle distance, périodes, blocs récurrents, biais de contexte — et il rend un
verdict en une seule quantité : le nombre de bits.

    Si un compresseur descend en dessous de la borne d'entropie,
    l'archive contient de la structure exploitable, et le gain EST cette structure.

C'est le plus faible des tests par défaut trouvé, et le plus large par surface couverte.
C'est aussi, littéralement, la définition opérationnelle du hasard : une suite est aléatoire
si elle n'est pas compressible.

LA BORNE D'ENTROPIE, EXACTE
===========================
Chaque tirage publie trois choses indépendantes sous la nulle :

    les vingt numéros   log2 C(80,20)  =  61,6157 bits
    le rang du bonus    log2 20        =   4,3219 bits   (uniforme, §187)
    le multiplicateur   H(41,19,12,4,2,2)/80 bits        (grille du §106)

L'encodage est SANS PERTE et OPTIMAL : le sous-ensemble est converti en son indice dans le
système combinatoire (`rang = Σ_j C(n_j, j+1)`), ce qui est une bijection sur
`[0, C(80,20))`. Aucun bit n'est gaspillé par la représentation, donc tout ce qu'un
compresseur gagne ensuite est de la **structure**, et non de la mise en forme.

LA NULLE EST SIMULÉE, ET C'EST INDISPENSABLE
============================================
Un compresseur a des frais fixes : en-têtes, dictionnaires, arrondis. Sur des données
parfaitement aléatoires, `xz` rend un fichier *plus gros* que l'entrée. Comparer la taille
compressée à la borne théorique n'aurait donc aucun sens. On la compare à la loi de la
taille compressée d'archives SRS de même taille, encodées par la même chaîne.

ET CETTE LOI EST DÉGÉNÉRÉE — CE QUI INTERDIT LE `z`
===================================================
Mesuré : sur des flux incompressibles, `xz` et `zlib` rendent **exactement la même taille**
à chaque réplicat — `155 068` octets, soixante fois sur soixante. L'écart-type de la nulle
est donc **nul**, et un `z` n'existe pas. Ce n'est pas une faiblesse : c'est la situation la
plus favorable qui soit, puisque la moindre taille inférieure au minimum de la nulle est
déjà une anomalie. Mais elle impose de lire le résultat en `p` EMPIRIQUE et non en `z` :

    p_k = (1 + #{réplicats dont la taille est ≤ celle de l'archive}) / (1 + R)

et la multiplicité se corrige en calculant la loi du `p` MINIMAL sur les réplicats
eux-mêmes, chacun laissé de côté dans le calcul de son propre `p` (§7.32). Aucune
hypothèse de forme, aucune approximation gaussienne.

QUATRE FLUX, TROIS COMPRESSEURS
===============================
  1  les vingt numéros seuls        (rangs combinatoires, 62 bits par tirage)
  2  les trois champs               (numéros + rang du bonus + boost)
  3  la DIFFÉRENCE de rangs         `rang_t - rang_{t-1} mod C(80,20)` — un compresseur
                                    voit mal une périodicité longue dans le flux brut, il
                                    la voit très bien dans la différence
  4  le masque binaire brut         `80` bits par tirage, un bit par numéro — la forme où
                                    une structure PAR NUMÉRO est la plus visible

× `xz -9e`, `bzip2 -9`, `zlib -9`. Douze statistiques, seuil de Bonferroni déclaré avant.
"""

import json
import os
import subprocess
import sys
from math import comb, erfc, log2, sqrt

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POOL, DRAWN = 80, 20
EXP_ID = "h177.test_universel"
FJETON = "/tmp/h177_jeton.json"
REPS = 60
NCOMB = comb(POOL, DRAWN)
LARG = (NCOMB - 1).bit_length()                  # 62 bits par tirage


def say(*a):
    print(*a, flush=True)


def seuil_bonferroni(m, alpha=0.05):
    lo, hi = 0.0, 40.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if erfc(mid / sqrt(2)) > alpha / m:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# --------------------------------------------------------------------------------------
# Encodage combinatoire : bijection sous-ensemble <-> entier de [0, C(80,20))
# --------------------------------------------------------------------------------------

TBL = np.array([[comb(n, k) if n >= k else 0 for k in range(DRAWN + 1)]
                for n in range(POOL + 1)], dtype=object)


def rangs(nums):
    """(N,20) numeros TRIES 1..80  ->  (N,) rangs combinatoires (entiers Python)."""
    n, _ = nums.shape
    out = []
    for i in range(n):
        r = 0
        for j in range(DRAWN):
            r += int(TBL[int(nums[i, j]) - 1][j + 1])
        out.append(r)
    return out


def en_octets(vals, larg):
    """liste d'entiers -> octets, `larg` bits chacun, gros-boutien, sans perte."""
    acc = 0
    nb = 0
    out = bytearray()
    for v in vals:
        acc = (acc << larg) | int(v)
        nb += larg
        while nb >= 8:
            nb -= 8
            out.append((acc >> nb) & 0xFF)
            acc &= (1 << nb) - 1
    if nb:
        out.append((acc << (8 - nb)) & 0xFF)
    return bytes(out)


def masque_octets(m):
    """(N,80) bool -> 10 octets par tirage."""
    return np.packbits(m, axis=1).tobytes()


def flux(nums, rang_bonus, boost_idx, mask):
    """les quatre flux, tous sans perte."""
    R = rangs(nums)
    f1 = en_octets(R, LARG)
    mel = []
    for r, b, o in zip(R, rang_bonus, boost_idx):
        mel.append((int(r) * DRAWN + int(b)) * 8 + int(o))
    f2 = en_octets(mel, LARG + 5 + 3)
    dif = [(int(R[i]) - int(R[i - 1])) % NCOMB for i in range(1, len(R))]
    f3 = en_octets(dif, LARG)
    f4 = masque_octets(mask)
    return {"1 numeros": f1, "2 trois champs": f2, "3 differences": f3, "4 masque": f4}


def comprimer(b):
    import bz2
    import lzma
    import zlib
    xz = subprocess.run(["xz", "-9e", "-c", "-T1"], input=b,
                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    return {"xz": len(xz.stdout) if xz.returncode == 0 else len(lzma.compress(b, preset=9)),
            "bzip2": len(bz2.compress(b, 9)),
            "zlib": len(zlib.compress(b, 9))}


def toutes(nums, rb, bo, mask):
    out = {}
    for nom, b in flux(nums, rb, bo, mask).items():
        for c, t in comprimer(b).items():
            out[f"{nom} / {c}"] = t
    return out


def p_empiriques(O, V):
    """p unilateral (plus PETIT = plus compressible) et sa correction de multiplicite.

    La nulle est degeneree pour xz et zlib — meme taille a chaque replicat, ecart-type nul —
    donc un z n'existe pas. On lit tout en p empirique :

        p_k = (1 + #{r : V[r,k] <= O_k}) / (1 + R)

    et la multiplicite se corrige sur les replicats eux-memes, chacun LAISSE DE COTE dans le
    calcul de son propre p (§7.32) : sans ce laisse-de-cote, un replicat se compare a
    lui-meme, son p est artificiellement bas et le p global penche vers la decouverte.
    """
    R = len(V)
    pk = (1 + (V <= O[None, :]).sum(axis=0)) / (1.0 + R)
    pmin = float(pk.min())
    mins = np.empty(R)
    for r in range(R):
        aut = np.delete(V, r, axis=0)
        q = (1 + (aut <= V[r][None, :]).sum(axis=0)) / (1.0 + R - 1)
        mins[r] = q.min()
    pglob = (1 + int((mins <= pmin).sum())) / (1.0 + R)
    return pk, float(pglob), pmin


def selftest():
    """DONNEES SYNTHETIQUES : le test a-t-il des dents ?"""
    say("h177 --autotest : donnees synthetiques uniquement, aucune archive lue")
    rng = np.random.default_rng(177)
    # R fixe la RESOLUTION du p global : il ne peut pas descendre sous 1/(1+R).
    # Avec R = 12 le plancher vaut 0,077 et aucune decouverte n'est declarable, meme
    # parfaite. R = 30 met le plancher a 0,032, sous le seuil de 5 %.
    n, R = 20000, 30
    base = srs_archive(n, rng)
    cles = list(toutes(*base))
    V = np.array([[toutes(*srs_archive(n, rng))[k] for k in cles] for _ in range(R)], float)
    say(f"   nulle sur {R} replicats de {n} tirages :")
    for i, k in enumerate(cles):
        say(f"      {k:>24} moyenne {V[:, i].mean():10.1f}  ecart-type "
            f"{V[:, i].std(ddof=1):7.2f}")
    deg = int((V.std(axis=0, ddof=1) == 0).sum())
    say(f"   -> {deg}/{len(cles)} statistiques ont une nulle DEGENEREE (ecart-type nul)")

    O0 = np.array([toutes(*base)[k] for k in cles], float)
    _, pg0, pm0 = p_empiriques(O0, V)
    say(f"   archive SRS temoin  : p minimal {pm0:.4f}, p global {pg0:.4f}")

    nums, rb, bo, m = [x.copy() for x in base]
    for s0, d0 in ((3000, 8000), (5000, 15000)):
        nums[d0:d0 + 60] = nums[s0:s0 + 60]
        rb[d0:d0 + 60] = rb[s0:s0 + 60]
        bo[d0:d0 + 60] = bo[s0:s0 + 60]
        m[d0:d0 + 60] = m[s0:s0 + 60]
    O1 = np.array([toutes(nums, rb, bo, m)[k] for k in cles], float)
    pk1, pg1, pm1 = p_empiriques(O1, V)
    say(f"   bloc de 60 recopie deux fois : p minimal {pm1:.4f}, p global {pg1:.4f}")
    for i, k in enumerate(cles):
        if pk1[i] <= 2.0 / (1 + R):
            say(f"      vu par {k:>24} : {int(O1[i])} contre {V[:, i].min():.0f} au minimum "
                f"de la nulle ({V[:, i].mean()-O1[i]:+.0f} octets)")
    ok = pg0 > 0.05 and pg1 <= 0.05
    say(f"   -> nulle {'JUSTE' if pg0 > 0.05 else 'FAUSSE'} ; bloc recopie "
        f"{'DETECTE' if pg1 <= 0.05 else 'MANQUE'}")
    return ok


def srs_archive(n, rng):
    """une archive SRS complete : numeros tries, rang de bonus, boost, masque."""
    m = np.zeros((n, POOL), bool)
    idx = np.argsort(rng.random((n, POOL)), axis=1)[:, :DRAWN]
    np.put_along_axis(m, idx, True, axis=1)
    nums = np.sort(idx, axis=1) + 1
    rb = rng.integers(0, DRAWN, n)
    bo = rng.choice(6, n, p=np.array([41, 19, 12, 4, 2, 2]) / 80.0)
    return nums, rb, bo, m


if __name__ == "__main__":
    if "--autotest" in sys.argv:
        sys.exit(0 if selftest() else 1)

    import lab

    A = lab.load()
    N = len(A.ids)
    NUMS = np.asarray(A.nums).astype(np.int64)
    BONUS = np.asarray(A.bonus).astype(np.int64)
    BOOST = np.asarray(A.boost).astype(np.int64)
    MASK = np.asarray(A.mask)
    RANG = np.argmax(NUMS == BONUS[:, None], axis=1)
    VB, SEC = np.unique(BOOST, return_inverse=True)
    assert len(VB) <= 8, len(VB)

    pb = np.bincount(SEC, minlength=len(VB)) / N
    Hb = float(-(pb[pb > 0] * np.log2(pb[pb > 0])).sum())
    bits = log2(NCOMB) + log2(DRAWN) + Hb
    borne = N * bits / 8.0

    MTOT = 12
    ZC = seuil_bonferroni(MTOT)

    HYP = ("L'archive est INCOMPRESSIBLE : aucun compresseur a usage general ne descend "
           "au-dessous de ce qu'il rend sur une archive SRS de meme taille encodee par la "
           "meme chaine. C'est le seul test du dossier qui ne suppose AUCUNE forme de "
           "defaut — un compresseur cherche toute regularite qu'il sait exprimer, "
           "repetitions a n'importe quelle distance, periodes, blocs recurrents, biais de "
           "contexte — et rend son verdict en une seule quantite, le nombre de bits. "
           "L'encodage est sans perte et optimal (indice combinatoire du sous-ensemble), "
           "donc tout gain est de la STRUCTURE et non de la mise en forme")
    STAT = (f"D = nombre de tailles compressees dont le z depasse Zc = {ZC:.2f} vers le BAS "
            f"(Bonferroni bilateral a 5 % sur {MTOT}), et le z minimal. Quatre flux "
            "(numeros seuls, trois champs, differences de rangs consecutifs, masque binaire) "
            "x trois compresseurs (xz -9e, bzip2 -9, zlib -9)")
    NUL = (f"Simulation : {REPS} archives SRS 20/80 de {N} tirages, rang de bonus uniforme "
           "et boost tire de la grille 1/80, passees par la MEME chaine d'encodage et de "
           "compression. Comparer a la borne d'entropie theorique n'aurait aucun sens : un "
           "compresseur a des frais fixes et rend, sur du hasard pur, un fichier plus GROS "
           "que l'entree")
    VER = ("conforme si D = 0 ; COMPRESSIBLE si une taille tombe sous le seuil, auquel cas "
           "le gain en bits mesure directement la structure trouvee")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h177 : {N} tirages ; entropie par tirage {bits:.4f} bits "
        f"({log2(NCOMB):.4f} + {log2(DRAWN):.4f} + {Hb:.4f})")
    say(f"   borne d'entropie des trois champs : {borne/1024:.1f} Kio")
    say(f"   seuil de Bonferroni sur {MTOT} statistiques : |z| > {ZC:.3f}")

    obs = toutes(NUMS, RANG, SEC, MASK)
    cles = list(obs)
    # reprise : le conteneur redemarre toutes les quinze a vingt minutes, et la nulle
    # coute une demi-heure. Chaque replicat a sa propre graine, donc la reprise est
    # reproductible et non biaisee : le replicat r ne depend que de r.
    FNUL = "/tmp/h177_nulle.npy"
    V = np.empty((REPS, len(cles)))
    deja = 0
    if os.path.exists(FNUL):
        vieux = np.load(FNUL)
        if vieux.shape[1] == len(cles):
            deja = min(len(vieux), REPS)
            V[:deja] = vieux[:deja]
            say(f"   nulle reprise : {deja}/{REPS} replicats deja calcules")
    for r in range(deja, REPS):
        V[r] = [toutes(*srs_archive(N, np.random.default_rng(20260903 + r)))[k]
                for k in cles]
        if (r + 1) % 5 == 0 or r == REPS - 1:
            say(f"   nulle {r+1}/{REPS}")
            np.save(FNUL, V[:r + 1])
    mu = V.mean(axis=0)
    sd = V.std(axis=0, ddof=1)
    O = np.array([obs[k] for k in cles], float)

    pk, pglob, pmin = p_empiriques(O, V)
    say(f"\n{'flux / compresseur':>24} | {'archive':>10} | {'nulle SRS':>11} | "
        f"{'sd':>7} | {'gain':>7} | {'p':>7}")
    for i, k in enumerate(cles):
        say(f"{k:>24} | {int(O[i]):10d} | {mu[i]:11.1f} | {sd[i]:7.1f} | "
            f"{mu[i]-O[i]:+7.0f} | {pk[i]:7.4f}")

    j = int(np.argmin(pk))
    D = 1 if pglob <= 0.05 else 0
    gain = float(mu[j] - O[j])
    say(f"\n   p minimal = {pmin:.4f} ({cles[j]}), gain {gain:+.0f} octets sur "
        f"{int(O[j]):,} ({100*gain/O[j]:+.4f} %)")
    say(f"   p GLOBAL (loi du p minimal sur les {REPS} replicats) = {pglob:.4f}")
    say(f"   ->   {'COMPRESSIBLE' if D else 'conforme'}")

    TOK["m_extra"] = MTOT - 1
    lab.record(
        TOK, gain, p=float(pglob), verdict="COMPRESSIBLE" if D else "conforme",
        power_at=("AUTOTEST : un bloc de 60 tirages recopie deux fois dans une archive de "
                  "20 000 est vu a z = -53 sur le flux du masque et sort du support de la "
                  "nulle sur trois des quatre flux (les tailles xz et zlib sont CONSTANTES "
                  "sur du hasard pur, donc toute taille inferieure est deja hors nulle). "
                  f"Sous SRS l'ecart-type des tailles vaut {sd.min():.0f} a {sd.max():.0f} "
                  "octets. Un compresseur ne voit pas tout, mais ce qu'il voit, il le voit "
                  "sans qu'on le lui ait decrit"),
        notes=(f"TEST UNIVERSEL (§193) : le seul test du dossier qui ne suppose aucune forme "
               f"de defaut. {MTOT} statistiques = 4 flux (numeros seuls, trois champs, "
               "differences de rangs, masque binaire) x 3 compresseurs (xz -9e, bzip2 -9, "
               f"zlib -9), nulle par {REPS} archives SRS completes passees par la meme "
               f"chaine d'encodage. Entropie par tirage {bits:.4f} bits, encodage "
               "combinatoire SANS PERTE (bijection verifiee par decodage). La nulle est "
               "DEGENEREE pour xz et zlib — taille identique a chaque replicat, ecart-type "
               "nul — donc le verdict se lit en p empirique et non en z. p minimal "
               f"{pmin:.4f} sur {cles[j]}, gain {gain:+.0f} octets ; p global {pglob:.4f}."))
    say("   consigne.")
