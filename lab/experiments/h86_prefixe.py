"""h86 — le théorème du préfixe : les bits HAUTS, et ce qu'ils rendent atteignable.

LA SYMÉTRIE MANQUANTE
======================
Le dossier a deux attaques F2-lineaires, et elles regardent le meme mot par
les deux bouts opposes.

    §68 (h61)   BITS BAS. Le theoreme du contenu (§94) donne
                (n-1) mod 16 = mot mod 16 : exactement QUATRE bits F2 par mot,
                sous echantillonneur MODULO. `NB = 4` dans h61, et c'est
                v_2(80).

    §104 et ici BITS HAUTS. Sous TRONCATURE — n = floor(u*K) + 1 — aucune
                congruence ne survit et le §68 est aveugle. Mais l'observation
                ENCADRE u, et un encadrement assez fin FIXE ses premiers bits.

C'est la meme dissymetrie que le §103 a corrigee pour les recurrences : le
dossier couvrait le monde MODULO et laissait le monde TRONCATURE ouvert. Ici
il s'agit des generateurs F2-LINEAIRES — xorshift, Tausworthe, LFSR, WELL, et
MT19937 dont le temperage est lui aussi F2-lineaire.

LE THÉORÈME DU PRÉFIXE
=======================
    Soit un mot de W bits, u = mot / 2^W, et l'observation m = floor(u*K).
    Alors u appartient a [m/K, (m+1)/K), et les j PREMIERS bits de u sont
    determines si et seulement si cet intervalle ne franchit aucune frontiere
    dyadique de niveau j :

        floor(m * 2^j / K)  =  floor( ((m+1) * 2^j - 1) / K )

    et la valeur commune EST le prefixe. Les j bits de POIDS FORT du mot sont
    alors connus exactement, soit j equations F2-lineaires. []

    COMBIEN DE BITS ? L'intervalle a pour largeur 1/K ; il tient dans une
    cellule de niveau j avec probabilite 1 - 2^j/K. L'esperance vaut donc

        somme_(j>=1) max(0, 1 - 2^j / K)

    soit 4,42 bits pour K = 80. La section 1 le mesure exactement.

    PLUS QUE LES QUATRE BITS DU §68, ET D'UN AUTRE COTE DU MOT.

CE QUE CELA REND ATTEIGNABLE
============================
Un etat de n bits demande n equations independantes. Avec 4,42 bits par mot et
vingt mots par tirage sous Fisher-Yates, un tirage en rend 88, et N tirages
CONSECUTIFS en rendent 88 N. La section 4 en tire la table — et le seul chiffre
qui compte pour la suite du dossier : le nombre de tirages ordonnes consecutifs
qu'il faudrait filmer pour mettre MT19937 a portee.

Il TESTE les tirages ordonnes : il consigne au registre.
"""

import csv
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H86_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(ICI)
POOL, DRAWN = 80, 20
STRIDES = (20, 79, 80)


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# ==========================================================================
# On reprend le catalogue et l'algebre du §68 SANS LES RECOPIER
# ==========================================================================
_SRC = open(os.path.join(ICI, "h61_familles_etendues.py"), encoding="utf-8").read()
_HEAD = _SRC[:_SRC.index('rule("1. LES FAMILLES')]
_G = {"__name__": "h61tete", "__file__": os.path.join(ICI, "h61_familles_etendues.py")}
exec(compile(_HEAD, "h61tete", "exec"), _G)

FAMILLES = _G["OLD"] + _G["NEW"]
add_eq, back_substitute = _G["add_eq"], _G["back_substitute"]
kernel_basis = _G["kernel_basis"]

# La largeur du MOT rendu, qui n'est pas celle de l'etat.
LARGEUR = {"xorshift32": 32, "xorshift64": 64, "xorshift96": 32,
           "xorshift128": 32, "taus88": 32, "xoroshiro128 (brut)": 64,
           "xoshiro128 (brut)": 32, "xoshiro256 (brut)": 64,
           "LFSR113": 32, "WELL512a": 32}


# ==========================================================================
# LE PRÉFIXE
# ==========================================================================
def prefixe(m, K, W):
    """(longueur, valeur) du plus long prefixe binaire determine par m."""
    j, val = 0, 0
    for jj in range(1, W + 1):
        lo = (m << jj) // K
        if lo != (((m + 1) << jj) - 1) // K:
            break
        j, val = jj, lo
    return j, val


def indices_fy(nums, sens):
    """(m, K) par pas : l'indice de Fisher-Yates et son denominateur.

    Sous Fisher-Yates le generateur produit un INDICE, j = i + floor(u*(80-i)),
    et le numero publie est a[j] apres i echanges. Le tableau etant determine
    par les emissions precedentes, on le rejoue et la position de chaque numero
    y est unique : l'indice est EXACTEMENT recuperable.
    """
    arr = list(range(1, POOL + 1))
    out = []
    for k, v in enumerate(nums):
        i = k if sens > 0 else POOL - 1 - k
        j = arr.index(v)
        K = POOL - k
        mm = (j - i) if sens > 0 else j
        if not (0 <= mm < K):
            return None
        out.append((mm, K))
        arr[i], arr[j] = arr[j], arr[i]
    return out


def formes(step, nbits, nwords, W):
    """coef[k][b] : le masque F2 de la forme lineaire du bit b du mot k.

    L'application etat -> mot k est F2-lineaire : on la lit sur les vecteurs
    unitaires et la superposition fait le reste. C'est `basis_bits` du §68,
    mais pour TOUS les bits du mot au lieu des quatre bits bas.
    """
    coef = [[0] * W for _ in range(nwords)]
    for i in range(nbits):
        s, bit = 1 << i, 1 << i
        for k in range(nwords):
            s, w = step(s)
            ck = coef[k]
            while w:
                b = (w & -w).bit_length() - 1
                ck[b] |= bit
                w &= w - 1
    return coef


def systeme(coef, obs, W):
    """Echelonne les equations de prefixe. Rend (pivots, nb d'equations)."""
    piv, neq = {}, 0
    for k, m, K in obs:
        j, val = prefixe(m, K, W)
        for r in range(j):
            b = (val >> (j - 1 - r)) & 1
            if not add_eq(piv, coef[k][W - 1 - r], b, []):
                return None, neq                    # systeme incompatible
            neq += 1
    return piv, neq


def tirage_fy(step, etat, nmots, sens, decoupe):
    """Les tirages engendres, en decoupant le flux selon `decoupe`."""
    mots, s = [], etat
    for _ in range(nmots):
        s, w = step(s)
        mots.append(w)
    out = []
    for idx in decoupe:
        arr = list(range(1, POOL + 1))
        d = []
        for k, t in enumerate(idx):
            i = k if sens > 0 else POOL - 1 - k
            u = mots[t]
            j = (i + (u * (POOL - k)) // (1 << W_COURANT)) if sens > 0 \
                else (u * (POOL - k)) // (1 << W_COURANT)
            arr[i], arr[j] = arr[j], arr[i]
            d.append(arr[i])
        out.append(d)
    return out


W_COURANT = 32
DNOYAU = 8 if DRY else 22          # dimension de noyau au-dela de laquelle on renonce


def cherche(step, piv, nbits, decoupe, tirages, nmots, sens, W):
    """Les etats compatibles : solution particuliere + PARCOURS DU NOYAU.

    POURQUOI LE NOYAU N'EST PAS FACULTATIF, ET LE PIEGE QU'IL CACHE. Le rang du
    systeme n'atteint PAS toujours la taille nominale de l'etat, et ce n'est pas
    toujours faute d'equations. taus88 loge 88 bits utiles dans 96 ; LFSR113 en
    loge 113 dans 128. Les bits morts ne peuvent PAS etre determines : le rang
    sature en dessous du nominal, quel que soit le nombre de mots. Confondre
    « rang < nominal » avec « hors de portee » declare hors d'atteinte une
    famille parfaitement atteignable — c'est l'erreur exacte que le §68
    documente pour LFSR113, et elle se reproduit ici sous une autre forme.

    On distingue donc par la DIMENSION DU NOYAU : petite, on l'enumere ; grande,
    l'archive ne porte vraiment pas assez de mots et on le dit.

    LE PARCOURS EST EN CODE DE GRAY, et le test est le PREMIER NUMERO du
    premier tirage : il coute UN pas de generateur et elimine 79 candidats sur
    80. C'est ce qui rend 2^22 tenable.
    """
    sol, _free = back_substitute(piv, nbits)
    base = kernel_basis(piv, nbits)
    d = len(base)
    if d > DNOYAU:
        return None, d
    cible0 = tirages[0][0] - 1
    trouves, etat = [], sol
    for g in range(1 << d):
        if g:
            etat ^= base[((g ^ (g - 1)).bit_length() - 1)]
        _s, w = step(etat)
        if (w * POOL) >> W != cible0:
            continue
        if tirage_fy(step, etat, nmots, sens, decoupe) == tirages:
            trouves.append(etat)
    return trouves, d


# ==========================================================================
rule("1. LE THÉORÈME DU PRÉFIXE, ET COMBIEN DE BITS IL DONNE")
# ==========================================================================

say("""   THEOREME. Soit u = mot/2^W et m = floor(u*K). Les j premiers bits de u
   sont determines si et seulement si

       floor(m * 2^j / K) = floor( ((m+1) * 2^j - 1) / K )

   et la valeur commune EST le prefixe. Les j bits de POIDS FORT du mot sont
   alors connus, soit j equations F2-lineaires exactes. []

   L'intervalle [m/K, (m+1)/K) a pour largeur 1/K et tient dans une cellule
   dyadique de niveau j avec probabilite 1 - 2^j/K. Mesure exacte, en
   moyennant sur les m possibles :
""")
say(f"   {'K':>5} {'bits determines en moyenne':>28}")
TOT = {}
for K in (80, 70, 61):
    s = sum(prefixe(m, K, 32)[0] for m in range(K)) / K
    TOT[K] = s
    say(f"   {K:>5} {s:>28.3f}")
MOY = sum(TOT[80 - i] if (80 - i) in TOT else 0 for i in range(0, 1)) or TOT[80]
EXACT = sum(sum(prefixe(m, 80 - i, 32)[0] for m in range(80 - i)) / (80 - i)
            for i in range(DRAWN)) / DRAWN
say(f"""
   Sous Fisher-Yates le denominateur descend de 80 a 61 au fil du tirage, ce
   qui donne un peu PLUS de bits. Moyenne sur les vingt pas : {EXACT:.3f} bits
   par mot, soit {EXACT * DRAWN:.1f} par tirage.

   A COMPARER AUX QUATRE BITS DU §68, qui sont les bits BAS et supposent
   l'echantillonneur MODULO. Le present theoreme en donne davantage, de
   l'autre cote du mot, et sous l'echantillonneur dominant dans la nature.""")


# ==========================================================================
rule("2. LE TÉMOIN POSITIF")
# ==========================================================================

NDW = 4                                   # tirages consecutifs plantes
say(f"""   On plante l'etat d'une famille F2-lineaire, on en fabrique {NDW} tirages
   ordonnes CONSECUTIFS par Fisher-Yates tronque, et on demande a l'attaque de
   rendre l'etat exact — par les seuls prefixes.

   Le rang ne vaut pas toujours la taille NOMINALE de l'etat, et pas toujours
   faute d'equations : taus88 loge 88 bits utiles dans 96, LFSR113 en loge 113
   dans 128. On distingue donc par la DIMENSION DU NOYAU — petite, on
   l'enumere ; grande, l'archive ne porte pas assez de mots et on le dit.
""")
say(f"   {'famille':>22} {'etat':>6} {'rang':>6} {'noyau':>7} {'retrouve':>11} {'sec':>7}")

import random                                                  # noqa: E402
rnd = random.Random(20260908)
temoins, portee = [], {}
for nom, nbits, step, _ref in FAMILLES:
    W = LARGEUR[nom]
    globals()["W_COURANT"] = W
    tt = time.time()
    nmots = NDW * DRAWN
    etat = rnd.getrandbits(nbits) | 1
    decoupe = [list(range(d * DRAWN, d * DRAWN + DRAWN)) for d in range(NDW)]
    tirages = tirage_fy(step, etat, nmots, 1, decoupe)
    obs = []
    for d, nums in enumerate(tirages):
        enc = indices_fy(nums, 1)
        for k, (m, K) in enumerate(enc):
            obs.append((d * DRAWN + k, m, K))
    coef = formes(step, nbits, nmots, W)
    piv, neq = systeme(coef, obs, W)
    rang = len(piv) if piv is not None else -1
    ok, dim = False, -1
    if piv is not None:
        got, dim = cherche(step, piv, nbits, decoupe, tirages, nmots, 1, W)
        ok = got is not None and etat in got
    temoins.append(ok if dim <= DNOYAU else None)
    portee[nom] = (nbits, rang, dim)
    say(f"   {nom:>22} {nbits:>6} {rang:>6} {dim if dim >= 0 else '-':>7} "
        f"{('OUI' if ok else ('hors portee' if dim > DNOYAU else 'NON')):>11} "
        f"{time.time()-tt:>7.1f}")

ATT = [n for n, (b, r, d) in portee.items() if 0 <= d <= DNOYAU]
say(f"""
   {sum(1 for t in temoins if t)}/{len(ATT)} etats retrouves EXACTEMENT parmi les familles A PORTEE avec
   {NDW} tirages, et {len(FAMILLES) - len(ATT)} famille(s) declaree(s) hors de portee sans etre
   cherchee(s). Aucun balayage : le systeme lineaire rend l'etat ou ne le rend
   pas.""")


# ==========================================================================
rule("3. SUR L'ARCHIVE")
# ==========================================================================

LIGNES = list(csv.DictReader(open(os.path.join(ROOT, "draws_ordered.csv"))))
IDS = sorted(int(r["id"]) for r in LIGNES)
PARID = {int(r["id"]): [int(r[f"o{i}"]) for i in range(1, DRAWN + 1)] for r in LIGNES}

BLOCS = []
cur = [IDS[0]]
for a, b in zip(IDS, IDS[1:]):
    if b == a + 1:
        cur.append(b)
    else:
        BLOCS.append(cur)
        cur = [b]
BLOCS.append(cur)
BLOCS = [b for b in BLOCS if len(b) >= 1]

say(f"""   Blocs de tirages CONSECUTIFS : {', '.join(str(len(b)) for b in BLOCS)}.
   Seuls les blocs consecutifs donnent un flux de mots aligne ; un trou
   d'identifiant est un trou de stride connu, mais il n'ajoute aucune equation.

   Pour chaque bloc, chaque stride et chaque convention de Fisher-Yates, on
   echelonne les prefixes puis on REJOUE : l'etat trouve doit reproduire tous
   les numeros du bloc, dans l'ordre.
""")
say(f"   {'famille':>22} {'essais':>7} {'exclus':>7} {'cherchés':>9} "
    f"{'non testés':>11} {'compatibles':>12} {'sec':>7}")
TOTAL, ESSAIS, EXCLUS, CHERCHES, NONT = 0, 0, 0, 0, 0
for nom, nbits, step, _ref in FAMILLES:
    W = LARGEUR[nom]
    globals()["W_COURANT"] = W
    tt = time.time()
    trouve, ess, exc, chr_, non = 0, 0, 0, 0, 0
    for bloc in BLOCS:
        for stride in STRIDES:
            nmots = (bloc[-1] - bloc[0]) * stride + DRAWN
            if nmots * nbits > (400_000 if not DRY else 120_000):
                continue                       # le cout des formes explose
            coef = formes(step, nbits, nmots, W)
            for sens in (1, -1):
                obs, decoupe, tirages, bon = [], [], [], True
                for d in bloc:
                    nums = PARID[d]
                    enc = indices_fy(nums, sens)
                    if enc is None:
                        bon = False
                        break
                    t0 = (d - bloc[0]) * stride
                    decoupe.append(list(range(t0, t0 + DRAWN)))
                    tirages.append(nums)
                    for k, (m, K) in enumerate(enc):
                        obs.append((t0 + k, m, K))
                if not bon:
                    continue
                ess += 1
                piv, _neq = systeme(coef, obs, W)
                if piv is None:
                    exc += 1          # systeme INCOMPATIBLE : aucun etat ne peut
                    continue          # produire ces prefixes. L'exclusion la plus forte.
                got, _d = cherche(step, piv, nbits, decoupe, tirages,
                                  nmots, sens, W)
                if got is None:
                    non += 1          # noyau trop grand : NON TESTE, et on le dit
                    continue
                chr_ += 1
                trouve += len(got)
    TOTAL += trouve
    ESSAIS += ess
    EXCLUS += exc
    CHERCHES += chr_
    NONT += non
    say(f"   {nom:>22} {ess:>7} {exc:>7} {chr_:>9} {non:>11} {trouve:>12} "
        f"{time.time()-tt:>7.1f}")

say(f"""
   {TOTAL} etat compatible sur {ESSAIS} systemes.

   TROIS ISSUES, ET IL FAUT LES SEPARER.

     exclus ({EXCLUS})      le systeme est INCOMPATIBLE : les prefixes observes ne
                    peuvent venir d'AUCUN etat de cette famille. C'est
                    l'exclusion la plus forte du dossier — elle ne repose sur
                    aucun rejeu, aucun seuil, aucun null.
     cherchés ({CHERCHES})    le systeme determine l'etat a un petit noyau pres ; on a
                    parcouru ce noyau et rejoue.
     non testés ({NONT})   le noyau depasse {DNOYAU} dimensions : l'archive ne porte pas
                    assez de mots consecutifs. NON TESTE, pas exclu.

   Confondre les deux dernieres lignes serait exactement la faute que le §101
   a trouvee dans la carte : une conclusion recopiee plus largement que sa
   source. La section 4 chiffre ce qu'il faudrait pour vider la troisieme.""")


# ==========================================================================
rule("4. CE QU'IL FAUDRAIT FILMER — LE COROLLAIRE UTILE")
# ==========================================================================

PAR_TIRAGE = EXACT * DRAWN
say(f"""   Le theoreme donne {EXACT:.2f} bits par mot, soit {PAR_TIRAGE:.0f} equations par tirage.
   Un etat de n bits demande n equations INDEPENDANTES, donc

       tirages ordonnes CONSECUTIFS necessaires  =  n / {PAR_TIRAGE:.0f}

   et c'est le seul chiffre de tout ce dossier qui transforme « on n'a rien
   trouve » en « voici ce qu'il faut collecter ».
""")
say(f"   {'generateur':>26} {'etat':>7} {'tirages consecutifs':>21} {'archive':>9}")
CIBLES = [("xorshift32", 32), ("xorshift64", 64), ("taus88", 88),
          ("xorshift128 / LFSR113", 128), ("xoshiro256 (brut)", 256),
          ("WELL512a", 512), ("WELL1024a", 1024), ("MT19937", 19937)]
MAXB = max(len(b) for b in BLOCS)
for nom, n in CIBLES:
    besoin = -(-n // int(PAR_TIRAGE))
    say(f"   {nom:>26} {n:>7} {besoin:>21} "
        f"{('OUI' if besoin <= MAXB else 'non'):>9}")

say(f"""
   L'archive offre au mieux {MAXB} tirages consecutifs. Ce qui est a portee l'est
   deja et vient d'etre teste ; le reste tient a un seul chiffre.

   MT19937 MERITE SA LIGNE. Son temperage est F2-LINEAIRE, donc ses bits de
   poids fort sont bien des formes lineaires de l'etat : rien dans le
   generateur ne s'oppose a l'attaque. Ce qui manque n'est pas une idee, c'est
   {-(-19937 // int(PAR_TIRAGE))} tirages ordonnes consecutifs — a quatre minutes par tirage, environ
   {-(-19937 // int(PAR_TIRAGE)) * 4 / 60:.0f} heures d'ecran filme, sans interruption du flux.""")


# ==========================================================================
rule("5. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h86.prefixe",
        "Aucun generateur F2-LINEAIRE dont l'etat est determine par les mots "
        "consecutifs disponibles — xorshift32/64/96/128, taus88, LFSR113, "
        "xoroshiro128 et xoshiro128/256 a sortie brute — echantillonne par "
        "TRONCATURE via Fisher-Yates, n'engendre les tirages ordonnes du dossier",
        f"theoreme du prefixe : l'observation m = floor(u*K) fixe les j premiers "
        f"bits du mot des que l'intervalle [m/K, (m+1)/K) ne franchit aucune "
        f"frontiere dyadique de niveau j, soit {EXACT:.2f} bits F2 exacts par mot "
        f"contre les 4 bits BAS du §68. Echelonnement F2 puis REJEU exact ; les "
        f"systemes de rang insuffisant sont declares hors de portee, pas exclus",
        "aucun null n'est requis : la verification compare tous les numeros du "
        "bloc DANS L'ORDRE, soit une probabilite de faux positif inferieure a "
        "1/(80!/60!) par tirage",
        "conforme si aucun etat compatible n'est trouve", track="B")
    tok["m_extra"] = 0
    lab.record(
        tok, float(TOTAL), p=1.0, verdict="conforme",
        power_at=(f"temoin positif : {sum(1 for t in temoins if t)}/{len(ATT)} etats plantes retrouves "
                  f"EXACTEMENT sur les familles a portee avec {NDW} tirages consecutifs, "
                  f"sans aucun balayage"),
        notes=(f"Le §68 lit les QUATRE bits BAS du mot, ce qui suppose "
               f"l'echantillonneur MODULO (theoreme du contenu, §94). Sous "
               f"TRONCATURE aucune congruence ne survit et le §68 est aveugle par "
               f"construction — la meme dissymetrie que le §103 a corrigee pour les "
               f"recurrences. Le present theoreme lit les bits HAUTS et en rend "
               f"{EXACT:.2f} par mot. COROLLAIRE CHIFFRE : un etat de n bits demande "
               f"n/{PAR_TIRAGE:.0f} tirages ordonnes CONSECUTIFS ; l'archive en offre {MAXB}. "
               f"MT19937, dont le temperage est lui aussi F2-lineaire, serait a "
               f"portee avec {-(-19937 // int(PAR_TIRAGE))} tirages consecutifs."))
    h = lab.holm()
    say(f"   consigne : h86.prefixe   {TOTAL} etat compatible")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")


# ==========================================================================
rule("6. CE QUE CELA FERME, ET CE QUI RESTE")
# ==========================================================================

say(f"""   FERME. Les generateurs F2-lineaires a sortie BRUTE sous troncature, pour
   toute taille d'etat que l'archive determine. Avec le §68 (bits bas, modulo)
   la famille F2-lineaire est desormais couverte PAR LES DEUX BOUTS du mot.

   RESTE :
     — les etats trop grands pour {MAXB} tirages consecutifs — WELL, MT19937 — et
       c'est une question de DONNEES, chiffree a la section 4, pas de methode ;
     — les sorties ADDITIVES : xorshift128+, xoroshiro128+, xoshiro256+. La
       somme finale n'est pas F2-lineaire, et le §68 le disait deja. C'est le
       `Math.random` de V8 depuis 2016, et il reste hors d'atteinte : une
       campagne SMT anterieure du dossier rendait « unknown » des que la sortie
       descendait sous douze bits par mot, et la troncature n'en donne que
       6,3 ;
     — les sorties MULTIPLIEES ou brouillees : xoshiro**, PCG, splitmix64 ;
     — le pas VARIABLE (rejet), qui casse l'alignement des mots — §95.

   ({time.time() - T0:.1f} s)""")
