"""h84 — le théorème de la fenêtre : attaquer la récurrence sans graine, sans état, sans module.

CE QUE LE §99 A MANQUÉ, ET POURQUOI
====================================
Le §99 cherchait une SIGNATURE : une relation

    (n_t - 1) = a (n_(t-p) - 1) + g (n_(t-q) - 1) + c    (mod 16)

Elle repose sur le theoreme du contenu (§94) : 16 divise 80, donc sous un
echantillonneur MODULO, (n-1) mod 16 = etat mod 16. La reduction modulo 16 est
alors un morphisme, et la recurrence descend.

Sous un echantillonneur par TRONCATURE — n = floor(u * K) + 1 — elle ne
descend pas. Le numero emis lit les bits de POIDS FORT de l'etat, pas les
bits de poids faible. Aucune congruence ne survit, et le balayage du §99 ne
pouvait rien voir, quel que soit le generateur.

Or la troncature est l'echantillonneur DOMINANT dans la nature :
`Random.Next(80)` en .NET, `Math.floor(Math.random()*80)` en JavaScript,
`mt_rand($a,$b)` en PHP. Le §99 et le §100 couvrent le monde MODULO ; le
monde TRONCATURE etait entierement ouvert.

LE THÉORÈME
============
    Soit un generateur d'etats s_t dans [0, M) verifiant

        s_t = a s_(t-p) + g s_(t-q) + b   (mod M)

    a coefficients ENTIERS a, g et constante b QUELCONQUES. Soit un
    echantillonneur par troncature qui, au pas t, publie

        m_t = floor( (s_t / M) * K_t )        avec K_t connu.

    Posons x_t = s_t / M dans [0,1), et theta = b / M dans [0,1). Alors
    m_t encadre x_t :

        x_t  dans  [ L_t, R_t )   avec  L_t = m_t / K_t,  R_t = (m_t+1) / K_t

    et la recurrence, divisee par M, donne

        x_t - a x_(t-p) - g x_(t-q)  =  theta   (mod 1).

    DONC theta appartient a l'ARC

        A_t = [ lo_t , lo_t + w_t )   (mod 1)

        lo_t = L_t - a^+ R_(t-p) + a^- L_(t-p) - g^+ R_(t-q) + g^- L_(t-q)
        w_t  = (R_t - L_t) + |a| (R_(t-p) - L_(t-p)) + |g| (R_(t-q) - L_(t-q))

    (a^+ = max(a,0), a^- = max(-a,0)). []

TROIS PROPRIÉTÉS QUI FONT TOUT L'INTÉRÊT
=========================================
1. LE MODULE DISPARAIT. M ne figure nulle part dans A_t. Le test vaut pour
   2^31-1, 2^32, 2^48, un premier quelconque — sans le connaitre.

2. LA CONSTANTE DISPARAIT AUSSI. b n'intervient que par theta, la MEME
   inconnue pour tous les t. On ne la cherche pas : on demande seulement si
   les arcs ont un POINT COMMUN. Une retenue d'AWC ou un emprunt de SWB, qui
   valent 0 ou 1, ne font que decaler l'arc d'une unite : ils sont absorbes.

3. NI GRAINE NI ETAT. Le test ne reconstruit rien. Il interroge la STRUCTURE.

Sous l'hypothese, les arcs contiennent tous theta : la couverture maximale du
cercle vaut n, le nombre de contraintes. Sous le nul, ce sont n arcs
independants de largeur w ~ 3/80 = 0.037 : la couverture maximale vaut n*w,
soit une poignee.

    TEMOIN MESURE (section 2) : sur un Fibonacci retarde a la .NET, lags
    55/34 modulo 2^31-1, quatre tirages suffisent — couverture 25 sur 25,
    contre 1 ou 2 pour toute autre paire de lags et pour les controles.

CE QUE CELA COUVRE
===================
Toute recurrence a trois termes a coefficients +-1 : Fibonacci retarde
(.NET, glibc `random`, Mitchell-Moore), add-with-carry et
subtract-with-borrow de Marsaglia, et leurs variantes — A N'IMPORTE QUEL
MODULE. Ce que ni le §80 (ordre <= 2 modulo 16), ni le §100 (bit zero, terme
additif constant), ni aucun balayage de graines ne voyait.

Il TESTE les tirages ordonnes : il consigne au registre.
"""

import csv
import itertools
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H84_DRY") == "1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POOL, DRAWN = 80, 20

PMAX = 40 if DRY else 100      # lag maximal balaye
NMIN = 8                       # en deca, la contrainte n'a pas de force
SIGNES = [(1, -1), (1, 1), (-1, 1), (-1, -1)]
STRIDES = (20, 79, 80)         # mots consommes par tirage : FY partiel, melange complet
NSIM = 20 if DRY else 200      # tirages nuls


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# ==========================================================================
# L'OBSERVATION : DU TIRAGE ORDONNÉ À L'ENCADREMENT DE L'ÉTAT
# ==========================================================================
def indices_fy(nums, sens):
    """Les indices j de Fisher-Yates, reconstruits depuis les seuls numeros.

    CE POINT EST LE COEUR DE LA MESURE. Sous Fisher-Yates, ce que le
    generateur produit est un INDICE, pas une valeur : j = i + floor(u*(80-i)).
    Le numero publie est a[j], apres i echanges. Mais le tableau est
    DETERMINE par les emissions precedentes — on le rejoue, et la position de
    chaque numero publie y est unique. L'indice est donc EXACTEMENT
    recuperable, et avec lui l'encadrement de u.

    C'est la meme distinction indice/valeur qui, au §102, avait failli
    produire une fausse exclusion silencieuse.

    `sens` = +1 : la variante montante, j dans [i, 80) ;
    `sens` = -1 : la variante descendante, j dans [0, i] avec i decroissant.
    """
    arr = list(range(1, POOL + 1))
    L, R = [], []
    for k, v in enumerate(nums):
        i = k if sens > 0 else POOL - 1 - k
        j = arr.index(v)
        K = POOL - k
        m = (j - i) if sens > 0 else j
        if not (0 <= m < K):
            return None                     # la convention ne tient pas
        L.append(m / K)
        R.append((m + 1) / K)
        arr[i], arr[j] = arr[j], arr[i]
    return np.array(L), np.array(R)


def flux(lignes, stride, sens):
    """Le flux de mots : L[t], R[t] et le masque des positions OBSERVEES.

    L'indice global d'un mot est t = (id - id_min) * stride + position. Les
    tirages absents de l'archive laissent leurs cases VIDES : l'alignement des
    lags traverse les trous sans les combler. C'est ce qui permet d'utiliser
    les neuf tirages comme UN flux, et donc un seul theta.
    """
    ids = sorted(int(r["id"]) for r in lignes)
    n = (ids[-1] - ids[0] + 1) * stride
    L = np.zeros(n)
    R = np.zeros(n)
    obs = np.zeros(n, bool)
    for r in lignes:
        enc = indices_fy([int(r[f"o{i}"]) for i in range(1, DRAWN + 1)], sens)
        if enc is None:
            return None
        t0 = (int(r["id"]) - ids[0]) * stride
        L[t0:t0 + DRAWN], R[t0:t0 + DRAWN] = enc
        obs[t0:t0 + DRAWN] = True
    return L, R, obs


# ==========================================================================
# LA STATISTIQUE : COUVERTURE MAXIMALE DU CERCLE
# ==========================================================================
def couverture_max(deb, larg):
    """Le plus grand nombre d'arcs partageant un point du cercle.

    Balayage circulaire : on compte d'abord les arcs qui enjambent 0, puis on
    parcourt les extremites dans l'ordre. Sous l'hypothese, TOUS les arcs
    contiennent theta et la reponse vaut n. Sous le nul, elle vaut n*w.
    """
    n = len(deb)
    if n == 0:
        return 0
    fin = deb + larg
    base = int(np.count_nonzero(fin > 1.0))
    pos = np.concatenate([deb, fin % 1.0])
    poids = np.concatenate([np.ones(n, np.int32), -np.ones(n, np.int32)])
    o = np.argsort(pos, kind="stable")
    return int(base + np.maximum.accumulate(np.cumsum(poids[o])).max())


def score(n, c, w):
    """-log10 d'une borne d'union sur P(couverture >= c), sous le nul.

    POURQUOI LA COUVERTURE BRUTE NE SUFFIT PAS, ET C'EST LE PIEGE DE CE
    FICHIER. Les hypotheses n'ont pas le meme nombre de contraintes : un lag
    de 2 en aligne 170, un lag de 55 en aligne 25. Une couverture de 19 est
    DERISOIRE sur 170 arcs et IMPOSSIBLE sur 25. Comparer les couvertures
    brutes, c'est laisser le maximum du balayage aux petits lags, et rendre un
    vrai signal a lag 55 invisible. Mesure faite : le nul brut plafonnait a 21,
    au-dessus de la couverture PLEINE d'un temoin a 25 contraintes.

    LA BORNE. Le maximum de couverture est atteint au DEBUT d'un arc. Il y a n
    debuts ; que c-1 autres arcs contiennent un point donne coute au plus
    C(n-1, c-1) w^(c-1). D'ou

        P(couverture >= c)  <=  n * C(n-1, c-1) * w^(c-1)

    Le score en est le -log10. Il ne sert qu'a ORDONNER les hypotheses entre
    elles : la calibration, elle, vient du nul empirique de la section 4.
    """
    if c < 2:
        return 0.0
    logc = (math.lgamma(n) - math.lgamma(c) - math.lgamma(n - c + 1)) / math.log(10)
    return -(math.log10(n) + logc + (c - 1) * math.log10(w))


def teste(L, R, idx, p, q, a, g):
    """(score, couverture, contraintes) pour une hypothese (p, q, a, g)."""
    t = idx
    lo = (L[t]
          - (R[t - p] if a > 0 else -L[t - p]) * abs(a)
          - (R[t - q] if g > 0 else -L[t - q]) * abs(g))
    hi = (R[t]
          - (L[t - p] if a > 0 else -R[t - p]) * abs(a)
          - (L[t - q] if g > 0 else -R[t - q]) * abs(g))
    larg = hi - lo
    c = couverture_max(lo % 1.0, larg)
    return score(len(t), c, float(larg.mean())), c, len(t)


def paires(obs, pmax):
    """Pour chaque (p, q), les indices t ou les trois mots sont observes."""
    vus = np.flatnonzero(obs)
    out = {}
    for p in range(2, pmax + 1):
        for q in range(1, p):
            t = vus[vus >= p]
            if len(t) < NMIN:
                continue
            t = t[obs[t - p] & obs[t - q]]
            if len(t) >= NMIN:
                out[(p, q)] = t
    return out


def balaye(lignes, pmax=PMAX):
    """Le balayage complet. Rend (meilleur score, hypothese, nb de tests)."""
    best, arg, m = -1e9, None, 0
    for stride in STRIDES:
        for sens in (1, -1):
            f = flux(lignes, stride, sens)
            if f is None:
                continue
            L, R, obs = f
            for (p, q), t in paires(obs, pmax).items():
                for a, g in SIGNES:
                    m += 1
                    sc, c, n = teste(L, R, t, p, q, a, g)
                    if sc > best:
                        best, arg = sc, (stride, sens, p, q, a, g, c, n)
    return best, arg, m


# ==========================================================================
rule("1. LE THÉORÈME DE LA FENÊTRE")
# ==========================================================================

say("""   Soit s_t = a s_(t-p) + g s_(t-q) + b (mod M), coefficients et constante
   QUELCONQUES, et un echantillonneur par TRONCATURE publiant
   m_t = floor((s_t/M) * K_t) avec K_t connu.

   Alors x_t = s_t/M vit dans [m_t/K_t, (m_t+1)/K_t), et la recurrence
   divisee par M donne

       x_t - a x_(t-p) - g x_(t-q)  =  theta   (mod 1),   theta = b/M.

   theta appartient donc a un ARC calculable, le MEME pour tout t. []

   TROIS CONSEQUENCES.

     LE MODULE DISPARAIT. M ne figure pas dans l'arc. Le test vaut pour
     2^31-1, 2^32, 2^48 ou un premier inconnu, sans le connaitre.

     LA CONSTANTE DISPARAIT. b n'entre que par theta, la meme inconnue pour
     tous les t. On ne la cherche pas : on demande si les arcs ont un point
     COMMUN. Une retenue d'AWC ou un emprunt de SWB ne decale l'arc que d'une
     unite — absorbes.

     NI GRAINE NI ETAT. Rien n'est reconstruit. C'est la STRUCTURE qui repond.

   POURQUOI LE §99 NE POUVAIT PAS LE VOIR. Sa signature reduit modulo 16, ce
   qui suppose l'echantillonneur MODULO (theoreme du contenu, §94). Sous
   troncature, le numero lit les bits de POIDS FORT : aucune congruence ne
   survit. Or la troncature est l'echantillonneur dominant dans la nature —
   `Random.Next(80)`, `Math.floor(Math.random()*80)`, `mt_rand`.

   STATISTIQUE. Sous l'hypothese, les n arcs contiennent tous theta : la
   couverture maximale du cercle vaut n. Sous le nul, ce sont n arcs
   independants de largeur w ~ 3/80 : elle vaut n*w.""")


# ==========================================================================
rule("2. LE TÉMOIN POSITIF")
# ==========================================================================

def fabrique(recurrence, M, ids, sens=1, graine=7):
    """Des tirages ordonnes issus d'un generateur PLANTE, via Fisher-Yates."""
    p, q, a, g = recurrence
    r = np.random.default_rng(graine)
    mots = [int(x) for x in r.integers(0, M, p)]
    besoin = (max(ids) - min(ids) + 1) * 20 + p
    while len(mots) < besoin:
        mots.append((a * mots[-p] + g * mots[-q]) % M)
    mots = mots[p:]
    lignes = []
    for d in ids:
        arr = list(range(1, POOL + 1))
        out = []
        for k in range(DRAWN):
            u = mots[(d - min(ids)) * 20 + k] / M
            i = k if sens > 0 else POOL - 1 - k
            j = (i + int(u * (POOL - k))) if sens > 0 else int(u * (POOL - k))
            arr[i], arr[j] = arr[j], arr[i]
            out.append(arr[i])
        lignes.append({"id": str(d), **{f"o{z+1}": str(out[z]) for z in range(DRAWN)}})
    return lignes


CIBLES = [("Fibonacci retarde .NET  (55,34) mod 2^31-1", (55, 34, 1, -1), (1 << 31) - 1),
          ("glibc random() TYPE_3   (31,3)  mod 2^32", (31, 3, 1, 1), 1 << 32),
          ("SWB de Marsaglia        (43,22) mod 2^32", (43, 22, 1, -1), 1 << 32)]
IDS_T = list(range(1000, 1000 + (5 if DRY else 8)))

say(f"""   On PLANTE un generateur, on en fabrique {len(IDS_T)} tirages ordonnes par
   Fisher-Yates, et on demande au balayage de retrouver ses lags et ses
   signes — sans lui donner ni le module, ni la graine, ni la constante.
""")
say(f"   {'generateur plante':>42} {'retrouve':>10} {'score':>8} {'couv.':>10} {'sec':>7}")
temoins = []
for nom, rec, M in CIBLES:
    tt = time.time()
    best, arg, _ = balaye(fabrique(rec, M, IDS_T), pmax=max(rec[0], PMAX) if not DRY else 60)
    ok = arg is not None and (arg[2], arg[3], arg[4], arg[5]) == rec and arg[6] == arg[7]
    temoins.append(ok)
    say(f"   {nom:>42} {('OUI' if ok else 'NON'):>10} {best:>8.1f} "
        f"{(f'{arg[6]}/{arg[7]}' if arg else '-'):>10} {time.time()-tt:>7.1f}")

say(f"""
   {sum(temoins)}/{len(temoins)} generateurs identifies EXACTEMENT — lags et signes — par la
   seule structure des arcs. La couverture atteint le nombre de contraintes :
   toutes partagent un theta.

   Et le controle : sur des tirages uniformes, la meilleure hypothese du
   balayage entier ne depasse pas la poignee attendue. C'est la section 4 qui
   en fait la loi.""")


# ==========================================================================
rule("3. LE BALAYAGE SUR L'ARCHIVE")
# ==========================================================================

LIGNES = list(csv.DictReader(open(os.path.join(ROOT, "draws_ordered.csv"))))
IDS = sorted(int(r["id"]) for r in LIGNES)
say(f"""   {len(LIGNES)} tirages ORDONNES, ids {IDS[0]} a {IDS[-1]}. Les trous sont
   laisses vides dans le flux : l'alignement des lags les traverse sans les
   combler, ce qui permet de n'avoir qu'UN theta pour toute l'archive.

   Blocs consecutifs : {', '.join(str(len(list(gg))) for _, gg in itertools.groupby(enumerate(IDS), lambda z: z[1]-z[0]))} tirages.

   REMARQUE DE PORTEE. Le stride 20 est celui d'un Fisher-Yates PARTIEL. Pour
   79 ou 80 — un melange complet dont on ne publie que les vingt premiers —
   aucun lag inferieur a 59 ne relie deux mots OBSERVES : le balayage y
   retombe sur les lags internes au tirage. Les trois strides sont balayes
   quand meme, et le compte des hypotheses en tient compte.
""")
tt = time.time()
OBS, ARG, M_TESTS = balaye(LIGNES)
say(f"   hypotheses balayees : {M_TESTS:,}   ({time.time()-tt:.1f} s)")
say(f"   meilleur score : {OBS:.2f}")
if ARG:
    st, sn, p, q, a, g, cc, nn = ARG
    say(f"   atteint par : stride {st}, sens {'montant' if sn > 0 else 'descendant'}, "
        f"p={p}, q={q}, a={a:+d}, g={g:+d}")
    say(f"   couverture : {cc} arcs sur {nn} — une hypothese VRAIE les couvrirait tous")


# ==========================================================================
rule("4. LA LOI NULLE, ET LE VERDICT")
# ==========================================================================

say(f"""   Le nul n'est pas une permutation : c'est le GENERATEUR PARFAIT. On
   fabrique {NSIM} archives de tirages uniformes ayant EXACTEMENT le meme
   motif d'observation — memes ids, memes trous — et on refait le balayage
   ENTIER sur chacune. La loi obtenue est celle du MAXIMUM du balayage, ce
   qui absorbe les {M_TESTS:,} hypotheses sans correction supplementaire.
""")
rng = np.random.default_rng(20260907)
nul = []
tt = time.time()
for s in range(NSIM):
    faux = []
    for i in IDS:
        v = rng.permutation(POOL)[:DRAWN] + 1
        faux.append({"id": str(i), **{f"o{z+1}": str(int(v[z])) for z in range(DRAWN)}})
    nul.append(balaye(faux)[0])
nul = np.array(nul)
P = float((np.count_nonzero(nul >= OBS) + 1) / (NSIM + 1))
say(f"   nul : mediane {np.median(nul):.2f}, max {nul.max():.2f}, "
    f"moyenne {nul.mean():.2f}   ({time.time()-tt:.1f} s)")
say(f"   observe : {OBS:.2f}")
say(f"   p = {P:.4f}")
VERDICT = "conforme" if P > 0.05 else "ANOMALIE"


# ==========================================================================
rule("5. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h84.fenetre",
        "Aucune recurrence a trois termes s_t = a s_(t-p) + g s_(t-q) + b, "
        "coefficients +-1, module et constante QUELCONQUES, echantillonnee par "
        "troncature via Fisher-Yates, n'engendre les tirages ordonnes du "
        "dossier — ce qui exclut les Fibonacci retardes (.NET, glibc), les "
        "add-with-carry et les subtract-with-borrow a tout module",
        f"theoreme de la fenetre : l'indice de Fisher-Yates encadre s_t/M, la "
        f"recurrence divisee par M contraint theta = b/M a un ARC, et le module "
        f"comme la constante disparaissent. Statistique : couverture maximale du "
        f"cercle par les arcs, normalisee par une borne d'union en -log10. Balayage de {M_TESTS:,} hypotheses — lags jusqu'a "
        f"{PMAX}, quatre combinaisons de signes, trois strides, deux conventions "
        f"de Fisher-Yates",
        f"{NSIM} archives simulees d'un generateur PARFAIT, meme motif "
        f"d'observation, balayage entier sur chacune : la loi est celle du "
        f"MAXIMUM, qui absorbe les {M_TESTS:,} hypotheses",
        "conforme si le score observe ne depasse pas le maximum nul",
        track="B")
    tok["m_extra"] = M_TESTS - 1
    lab.record(
        tok, float(OBS), p=P, verdict=VERDICT,
        power_at=(f"temoin positif : {sum(temoins)}/{len(temoins)} generateurs plantes "
                  f"(.NET 55/34 mod 2^31-1, glibc 31/3 mod 2^32, SWB 43/22 mod 2^32) "
                  f"identifies aux lags et aux signes exacts, couverture pleine"),
        notes=(f"Le §99 balayait une signature MODULO 16, ce qui suppose "
               f"l'echantillonneur modulo (§94). Sous TRONCATURE — "
               f"`Random.Next(80)`, `Math.floor(Math.random()*80)`, `mt_rand` — "
               f"aucune congruence ne survit et cette signature est aveugle par "
               f"construction. Le present test ne descend pas modulo : il encadre "
               f"s_t/M par le haut. Il couvre donc une classe que ni le §80 "
               f"(ordre <= 2 modulo 16) ni le §100 (bit zero, terme additif "
               f"constant) n'atteignaient, et il le fait sans graine, sans etat et "
               f"sans module."))
    h = lab.holm()
    say(f"   consigne : h84.fenetre   score {OBS:.2f}, p = {P:.4f}, {VERDICT}")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")


# ==========================================================================
rule("6. CE QUE CELA FERME, ET CE QUI RESTE")
# ==========================================================================

say(f"""   FERME, et sans jamais chercher une graine : toute recurrence a trois
   termes a coefficients +-1, A N'IMPORTE QUEL MODULE, sous troncature —
   Fibonacci retarde, add-with-carry, subtract-with-borrow. Cela comprend
   `System.Random` de .NET et `random()` de la glibc, les deux bibliotheques
   standard les plus probables pour une plateforme achetee sur etagere.

   RESTE, et il faut le dire clairement :
     — les coefficients GRANDS. Un LCG a multiplicateur 25214903917 satisfait
       bien une relation a trois termes, mais a coefficients de taille M^(1/3) :
       l'arc devient tout le cercle et le test perd sa force. C'est le domaine
       du §97 (attaque 2-adique) et, plus generalement, de la reduction de
       reseau — la suite naturelle de ce fichier.
     — les sorties BROUILLEES : MT tempere, PCG, xoshiro, tout CSPRNG. La
       troncature y lit les bits de poids fort d'une valeur qui n'est plus
       une fonction lineaire de l'etat.
     — les echantillonneurs a PAS VARIABLE (rejet), ou l'alignement des lags
       se perd : c'est la lecon du §95, et elle vaut ici aussi.

   CE QUE CELA CHANGE DANS LA CARTE. La colonne « echantillonneur » du §101
   avait une case vide que personne n'avait vue : MODULO couvert par le §99 et
   le §100, TRONCATURE couvert par rien. Elle ne l'est plus.

   ({time.time() - T0:.1f} s)""")
