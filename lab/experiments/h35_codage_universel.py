"""h35 — codage universel : chercher un écart SANS nommer la famille.

Le mur que ce fichier contourne
--------------------------------
Chaque voie du dossier doit déclarer d'avance QUELLE régularité elle cherche,
puis payer sa place au registre (126 tests dépensés, Holm à ~1,5e-05). Les
§41-43 montrent que le plafond d'un biais indétectable croît en m^(1/4) avec
la taille de la famille : plus la famille est grande, mieux un biais s'y
cache — et il y a une infinité de familles jamais nommées.

Le codage universel échappe à cette structure. Un compresseur universel
converge vers l'entropie de la source SANS qu'on lui dise quoi chercher,
dans toute la classe qu'il mélange. Et le lien avec l'argent est exact :
sous H0 un tirage coûte log2 C(80,20) = 61,6165 bits ; tout bit économisé
est un taux de croissance de Kelly.

f4 a fait un pas : des e-processus sur des Bernoulli conditionnelles — mais
ses modèles sont NOMMÉS d'avance (26 têtes, écho du bonus, lag-1). Ici la
classe est STRUCTURELLE et fixée avant toute lecture des données.

La représentation, et pourquoi
------------------------------
Deux représentations d'un tirage : le rang combinatoire (un entier de 61,6
bits) ou les 80 indicatrices d'appartenance. Le rang est écarté : il détruit
la localité (changer UN numéro déplace le rang de quantités énormes), et
aucun modèle de contexte sur ses chiffres ne correspond à un biais physique
plausible. Les indicatrices, elles, rendent de faible complexité exactement
les biais que le monde sait produire : marginale (un numéro trop fréquent),
rémanence (mémoire de sa propre histoire), périodicité courte, canal du
bonus. L'universalité n'a de sens que RELATIVE à une classe ; celle-ci
contient les alternatives physiquement plausibles à faible profondeur.

La classe (fixée ici, dans ce fichier, avant toute exécution sur l'archive)
---------------------------------------------------------------------------
Mélange bayésien à poids égaux de 22 codeurs KT (Krichevsky-Trofimov,
prior Beta(1/2, 3/2), de moyenne 1/4 = la valeur H0) sur des contextes
STRUCTURELS de l'indicatrice x[t,i] :

  - partagés (un paramètre par contexte, mis en commun sur les 80 numéros) :
    profondeur d de l'histoire propre (x[t-1,i]..x[t-d,i]),
    d in {0,1,2,4,8,12} — la hiérarchie des arbres complets, le cousin à
    régret quasi identique de CTW (CTW n'ajoute que l'élagage des arbres
    déséquilibrés ; le mélange sur d couvre tous les ordres de Markov <= 12) ;
  - un seul bit retardé (lag j in {2,3,4,6,8,12}) : couvre les couplages
    purs à un lag, que les arbres contigus diluent sur 2^d cases ;
  - fenêtrés (comptes glissants, W in {512, 4096}) : couvrent les défauts
    transitoires, que des comptes convergés à 5,6 millions d'événements ne
    peuvent plus apprendre ;
  - par numéro (80 paramètres et plus) : d in {0,1,2} et d=0 fenêtré
    (W = 4096 et 512, le second étant le spécialiste des transitoires) —
    couvrent la marginale et la rémanence propres à chaque numéro ;
  - canal du bonus (contexte à 3 états : absent en t-1 / présent / était le
    bonus) : le seul membre hérité d'une famille déjà nommée (d7, V3),
    déclaré comme tel.

La profondeur maximale 12 vient du budget de données, pas des données :
5,6 M d'événements / 4096 contextes ~= 1 378 événements par feuille.

Le couplage : de 80 probabilités théta_i à une loi sur les 20-parmi-80 par la
Bernoulli conditionnelle Q(S) = prod_{i in S} w_i / e20(w), w_i = odds(théta_i)
— la loi de maximum d'entropie à champ donné, celle de f4. Alors

    e_t = Q(D_t) · C(80,20)   et   E[e_t | passé] = 1  EXACTEMENT,

quel que soit l'état d'apprentissage du codeur : la validité ne dépend PAS
de la qualité du modèle, seulement du fait que théta est une fonction du
passé strict. Le mélange est une vraie martingale sous H0 : lisible sans
correction de multiplicité, valide à tout instant d'arrêt (Ville).

La leçon de f2/§14-D est câblée : au mélange cumulé depuis le pas 1
(structurellement aveugle à un défaut tardif) s'ajoute, PAR MODÈLE, le
mélange de redémarrages par blocs de 16 tirages à prior w_j = 1/(j(j+1)) +
trésorerie des paris à venir — la construction corrigée du §14-D, une vraie
martingale uniformément dans le temps (pas le R_t/t dont le sup n'est pas
couvert par Ville).

Ce que ce fichier livre : le chiffre EN BITS (taux de Kelly du codeur
universel sur les 70 560 tirages), sa puissance mesurée sur quatre témoins
positifs (marginale, rémanence, lag-8, transitoire tardif — plus un témoin
d'ANGLE MORT assumé, la modulation périodique pure en temps), le prix de
l'universalité sous H0, et la comparaison au mélange nommé de f4.

Usage : python3 h35_codage_universel.py [--fast] [--no-record]
"""

import itertools
import math
import os
import sys
import time

import numpy as np

EXPDIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(EXPDIR))
import lab

POOL, DRAWN = lab.POOL, lab.DRAWN
LOG_C = float(sum(math.log(POOL - i) - math.log(i + 1) for i in range(DRAWN)))
BITS_H0 = LOG_C / math.log(2)                     # 61,6165 bits par tirage
LN10 = math.log(10)
LOG10_VILLE = math.log10(20.0)                    # seuil de Ville, alpha = 0,05

FAST = "--fast" in sys.argv
NO_RECORD = "--no-record" in sys.argv or FAST

T0 = time.time()


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# --------------------------------------------------------------------------
# La classe de modèles — fixée ICI, avant toute exécution sur l'archive.
# --------------------------------------------------------------------------

A_PRIOR, S_PRIOR = 0.5, 2.0        # Beta(1/2, 3/2) : moyenne 1/4 = H0
DMAX = 12
MASKD = (1 << DMAX) - 1
BLOCK = 16                          # blocs de redémarrage (§15 : prior par blocs)
CHUNK = 1024
LOGW_MIN = math.log(1e-8)           # plancher numérique sur les odds normalisés

# (nom, genre, paramètre, fenêtre) — genre : sh=partagé profondeur d,
# lag=un bit au lag j, pn=par numéro profondeur d, bo=canal du bonus.
MODELS = [
    ("sh-d0",        "sh", 0,  None),
    ("sh-d1",        "sh", 1,  None),
    ("sh-d2",        "sh", 2,  None),
    ("sh-d4",        "sh", 4,  None),
    ("sh-d8",        "sh", 8,  None),
    ("sh-d12",       "sh", 12, None),
    ("lag2",         "lag", 2,  None),
    ("lag3",         "lag", 3,  None),
    ("lag4",         "lag", 4,  None),
    ("lag6",         "lag", 6,  None),
    ("lag8",         "lag", 8,  None),
    ("lag12",        "lag", 12, None),
    ("sh-d1-w512",   "sh", 1,  512),
    ("sh-d1-w4096",  "sh", 1,  4096),
    ("sh-d4-w4096",  "sh", 4,  4096),
    ("pn-d0",        "pn", 0,  None),
    ("pn-d1",        "pn", 1,  None),
    ("pn-d2",        "pn", 2,  None),
    ("pn-d0-w4096",  "pn", 0,  4096),
    # pn-d0-w512 : le spécialiste des transitoires marginaux. Il SAIGNE en
    # permanence (~80/(2·514·ln2) = 0,11 bit/tirage de bruit d'estimation,
    # 80 paramètres ré-estimés sur 512 tirages glissants) — c'est le prix
    # déclaré d'avance pour qu'un défaut bref ait un spécialiste dans la
    # classe ; les redémarrages par blocs le paient localement, pas sur
    # toute l'archive.
    #
    # ENTORSE DISCLOSÉE (règle n°2, même statut que celle de h29) : ce
    # membre a été ajouté APRÈS que le témoin transitoire simulé eut montré
    # la classe initiale aveugle (delta=0,60 manqué), et une passe de mise
    # au point --fast avait alors déjà vu les 8 000 premiers tirages réels
    # (mélange 10^-1,17, sups nuls — rien). L'ajout est motivé par une
    # SIMULATION, pas par l'archive, et le résultat réel final est nul de
    # toute façon ; mais le jeton définitif a été scellé après ce regard,
    # et cela se dit.
    ("pn-d0-w512",   "pn", 0,  512),
    ("bonus",        "bo", None, None),
    ("bonus-w4096",  "bo", None, 4096),
]
M = len(MODELS)


def _size(kind, par):
    if kind == "sh":
        return 1 << par
    if kind == "lag":
        return 2
    if kind == "pn":
        return POOL << par
    return 3                                       # bo


SIZES = [_size(k, p) for _, k, p, _ in MODELS]
OFFS = np.concatenate([[0], np.cumsum(SIZES)])[:-1].astype(np.int64)
TOTAL = int(sum(SIZES))
I80 = np.arange(POOL, dtype=np.int64)


# --------------------------------------------------------------------------
# Le codeur
# --------------------------------------------------------------------------

def _log_factors(TH, HIT):
    """(B, M', 80) probas théta et (B, 80) tirages -> (B, M') log e-facteurs.

    w_i = théta_i/(1-théta_i), normalisés au max (invariance d'échelle de la
    Bernoulli conditionnelle : multiplier w par c multiplie numérateur et
    e20 par c^20), plancher 1e-8 pour que e20 reste dans le flottant. Le
    plancher modifie Q mais Q reste une vraie loi : la martingale tient.
    """
    logw = np.log(TH) - np.log1p(-TH)
    logw -= logw.max(axis=2, keepdims=True)
    np.maximum(logw, LOGW_MIN, out=logw)
    W = np.exp(logw)
    B, Mm, _ = W.shape
    E = np.zeros((B, Mm, DRAWN + 1))
    E[:, :, 0] = 1.0
    for i in range(POOL):
        E[:, :, 1:] += W[:, :, i:i + 1] * E[:, :, :-1]
    logZ = np.log(E[:, :, DRAWN])
    lognum = np.where(HIT[:, None, :], logw, 0.0).sum(axis=2)
    return LOG_C + lognum - logZ


def run_coder(mask, bonus, progress=0):
    """Une passe de codage. Renvoie (T, M) log e-facteurs naturels.

    Sémantique par lot : les 80 prédictions du tirage t sont émises depuis
    l'état de fin du tirage t-1 (aucune mise à jour intra-tirage), puis les
    comptes absorbent le tirage t. théta ne dépend donc que du passé strict.
    """
    T = len(mask)
    N1 = np.zeros(TOTAL)
    NT = np.zeros(TOTAL)
    IDX = np.empty((M, POOL), np.int64)
    rings = {m: np.empty((w, POOL), np.int64)
             for m, (_, _, _, w) in enumerate(MODELS) if w}
    h = np.zeros(POOL, np.int64)
    bkey = np.zeros(POOL, np.int64)
    TH = np.empty((CHUNK, M, POOL))
    HIT = np.empty((CHUNK, POOL), bool)
    LOGF = np.empty((T, M))
    fill, base = 0, 0

    def flush(k, at):
        LOGF[at:at + k] = _log_factors(TH[:k], HIT[:k])

    for t in range(T):
        for m, (_, kind, par, _) in enumerate(MODELS):
            if kind == "sh":
                IDX[m] = OFFS[m] + (h & ((1 << par) - 1))
            elif kind == "lag":
                IDX[m] = OFFS[m] + ((h >> (par - 1)) & 1)
            elif kind == "pn":
                IDX[m] = OFFS[m] + (I80 << par) + (h & ((1 << par) - 1))
            else:
                IDX[m] = OFFS[m] + bkey

        TH[fill] = (N1[IDX] + A_PRIOR) / (NT[IDX] + S_PRIOR)
        HIT[fill] = mask[t]
        fill += 1
        if fill == CHUNK:
            flush(CHUNK, base)
            base += CHUNK
            fill = 0

        x = mask[t]
        np.add.at(NT, IDX.ravel(), 1.0)
        np.add.at(N1, IDX[:, x].ravel(), 1.0)
        for m, ring in rings.items():
            W = len(ring)
            if t >= W:
                old = ring[t % W]
                np.add.at(NT, old, -1.0)
                np.add.at(N1, old[mask[t - W]], -1.0)
            ring[t % W] = IDX[m]

        h = ((h << 1) & MASKD) | x
        bkey = x.astype(np.int64).copy()
        b = int(bonus[t])
        if 1 <= b <= POOL:
            bkey[b - 1] = 2
        if progress and t and t % progress == 0:
            say(f"     {t}/{T}  ({time.time() - T0:.0f}s)")
    if fill:
        flush(fill, base)
    return LOGF


def mixture_log(LOGF):
    """log du mélange à poids égaux des M e-processus cumulés depuis le pas 1."""
    cum = np.cumsum(LOGF, axis=0)
    mx = cum.max(axis=1, keepdims=True)
    return mx[:, 0] + np.log(np.exp(cum - mx).mean(axis=1)), cum


def restart_mean_log10(LOGF, block=BLOCK):
    """sup-lisible : moyenne sur les modèles des martingales à redémarrages.

    Par modèle : N_t = somme_{j<=J(t)} w_j * prod_{s>=début bloc j} f_s
                       + somme_{j>J(t)} w_j            (trésorerie, §14-D)
    avec w_j = 1/(j(j+1)) sur l'index de bloc (blocs de 16 tirages, §15).
    Chaque N est une VRAIE martingale (pas le R_t/t dont le sup échappe à
    Ville) ; leur moyenne aussi. Le pari j=1 (poids 1/2) contient le pari
    « depuis le début » : tôt et tard sont couverts par le même chiffre.
    """
    T = LOGF.shape[0]
    logA = np.full(M, -np.inf)
    logtail = 0.0
    out = np.empty(T)
    logMinv = math.log(1.0 / M)
    for t in range(T):
        if t % block == 0:
            j = t // block + 1
            logA = np.logaddexp(logA, math.log(1.0 / (j * (j + 1))))
            logtail = math.log(1.0 / (j + 1))
        logA = np.minimum(logA + LOGF[t], 700.0)
        logN = np.logaddexp(logA, logtail)
        mx = logN.max()
        out[t] = (mx + math.log(np.exp(logN - mx).mean()) ) / LN10
    return out


# --------------------------------------------------------------------------
# Pré-enregistrement — avant toute vérification et toute donnée réelle
# --------------------------------------------------------------------------

TOK_UNIV = lab.preregister(
    "h35.univ",
    f"un codeur universel (melange bayesien de {M} codeurs KT sur contextes "
    "structurels des indicatrices : profondeurs 0-12 partagees, lags isoles, "
    "fenetres 512/4096, par-numero, canal bonus) economise des bits sur les "
    "70 560 tirages par rapport aux 61,6165 bits/tirage de H0",
    f"log10 de la valeur FINALE du melange a poids egaux des {M} e-processus "
    "(e_t = Q(D_t)*C(80,20), Q Bernoulli conditionnelle a champ KT) ; "
    "taux de Kelly = log2(E_final)/T bits/tirage",
    "aucune calibration : E[e_t|passe] = 1 par construction, quelle que soit "
    "la classe ; verifie AVANT application par (i) e20 exact sur petit cas "
    "enumere, (ii) 200 000 tirages uniformes a champs fixes, (iii) le codeur "
    "complet sur 4 archives SRS de 70 560",
    "significatif si E >= 20 (Ville, alpha = 0,05, valide a tout instant) ; "
    "pas de correction de multiplicite (moyenne d'e-valeurs = e-valeur) ; "
    "le livrable principal est le taux en bits, signe compris",
    track="C")

TOK_SUP = lab.preregister(
    "h35.sup",
    "le melange universel cumule franchit le seuil de Ville a un instant "
    "quelconque de l'archive",
    f"max_t log10 E_t du melange des {M} e-processus cumules",
    "inegalite de Ville : P(sup E >= 1/alpha) <= alpha, sans correction",
    "significatif si sup >= 20",
    track="C")

TOK_RST = lab.preregister(
    "h35.restart",
    "avec les redemarrages par blocs (prior 1/(j(j+1)) + tresorerie, la "
    "construction corrigee du 14-D), le codeur universel detecte aussi un "
    "defaut apparu tard dans l'archive",
    f"max_t log10 de la moyenne sur les {M} modeles des martingales a "
    "redemarrages par blocs de 16 tirages",
    "vraie martingale uniformement dans le temps (pas R_t/t) ; Ville "
    "s'applique au sup ; verifie sur les memes 4 archives SRS",
    "significatif si sup >= 20 ; ce jeton couvre le cas ou f2 a montre "
    "qu'un pari cumule est structurellement aveugle",
    track="C")


# --------------------------------------------------------------------------
# 1. Vérifications AVANT toute donnée réelle
# --------------------------------------------------------------------------

def verify_e20_exact():
    """Le polynôme symétrique par récurrence contre l'énumération brute.

    Leçon du §13.4 : la vérification d'avant-lancement doit couvrir AUSSI
    les petits cas, pas seulement la taille nominale. Ici pool=6, k=3,
    énumérés exhaustivement (20 sous-ensembles), 5 champs aléatoires.
    """
    rng = np.random.default_rng(7)
    for rep in range(5):
        w = np.exp(rng.standard_normal(6))
        e3_brute = sum(w[a] * w[b] * w[c]
                       for a, b, c in itertools.combinations(range(6), 3))
        E = np.zeros(4)
        E[0] = 1.0
        for i in range(6):
            E[1:] += w[i] * E[:-1]
        assert abs(E[3] - e3_brute) / e3_brute < 1e-12, (E[3], e3_brute)
    # Et le chemin de production : théta = 1/4 partout doit coder à 0 bit près.
    TH = np.full((4, 1, POOL), 0.25)
    HIT = np.zeros((4, POOL), bool)
    HIT[:, :DRAWN] = True
    lf = _log_factors(TH, HIT)
    assert np.abs(lf).max() < 1e-9, lf
    say("   e20 : récurrence == énumération brute (pool 6, k 3, 5 champs) ;")
    say("   théta uniforme 1/4 -> facteur EXACTEMENT 1 sur le chemin de production.")


def verify_fixed_fields():
    """E[e_t] = 1 sur 200 000 tirages uniformes, champs FIXES arbitraires.

    La même vérification que f4 (sa moyenne était à 1 sous 1,5 sigma). Un
    e-processus faux monte tout seul ; celui-ci ne doit pas bouger.
    """
    rng = np.random.default_rng(11)
    n = 20_000 if FAST else 200_000
    worst = 0.0
    for theta in (0.05, 0.20, -0.20):
        z = rng.standard_normal((1, POOL))
        w = np.exp(theta * z)[0]
        th_field = w / (1.0 + w)                  # le chemin théta -> odds -> Q
        acc, acc2, cnt = 0.0, 0.0, 0
        for a in range(0, n, 4096):
            b = min(a + 4096, n)
            m = lab.srs(b - a, rng)
            TH = np.broadcast_to(th_field, (b - a, 1, POOL)).copy()
            e = np.exp(_log_factors(TH, m)[:, 0])
            acc += e.sum(); acc2 += (e * e).sum(); cnt += len(e)
        mean = acc / cnt
        se = math.sqrt(max(acc2 / cnt - mean * mean, 1e-30) / cnt)
        zz = (mean - 1.0) / se
        worst = max(worst, abs(zz))
        say(f"   champ fixe theta = {theta:+.2f}   moyenne e_t = {mean:.5f} "
            f"± {se:.5f}   (écart à 1 : {zz:+.2f} sigma)")
    assert worst < 4.0, "E[e_t] s'écarte de 1 : la construction est fausse, ARRÊT"


def verify_no_leak():
    """Le codeur lit-il le futur ? Tranché par l'expérience (esprit leak_check).

    Deux archives identiques jusqu'à t0, différentes après : les log-facteurs
    des t < t0 doivent être BIT À BIT identiques. Un décalage d'indice — la
    fuite accidentelle la plus probable — casse l'égalité immédiatement.
    """
    rng = np.random.default_rng(23)
    T, t0 = 6000, 3000
    mA = lab.srs(T, rng)
    bA = gen_bonus(mA, rng)
    mB = mA.copy(); bB = bA.copy()
    mB[t0:] = lab.srs(T - t0, rng)
    bB[t0:] = gen_bonus(mB[t0:], rng)
    lfA = run_coder(mA, bA)
    lfB = run_coder(mB, bB)
    assert np.array_equal(lfA[:t0], lfB[:t0]), "FUITE : le passé dépend du futur"
    assert not np.array_equal(lfA[t0:], lfB[t0:]), "témoin cassé : rien ne diffère"
    say(f"   futur réécrit à partir de t0={t0} : les {t0} log-facteurs du passé")
    say("   sont bit à bit identiques ; ceux du futur diffèrent (témoin).")


def gen_bonus(mask, rng):
    """Bonus uniforme parmi les 20 du même tirage (null exact de d7/f2).

    Leçon du plancher de f4 : JAMAIS de bonus constant dans une simulation —
    un champ constant fige les modèles bonus à 1 et fabrique un plancher
    qu'on prend pour une mesure.
    """
    nums = np.argsort(~mask, axis=1, kind="stable")[:, :DRAWN] + 1
    pick = rng.integers(0, DRAWN, size=len(mask))
    return nums[np.arange(len(mask)), pick].astype(np.int64)


def verify_full_coder_h0(R):
    """Le codeur COMPLET (apprentissage inclus) sur R archives SRS entières.

    Trois lectures par archive : la moyenne des e-facteurs (E=1 exactement
    par la tour des espérances ; les différences f_t - 1 sont non corrélées,
    donc l'erreur-type vaut std/racine(T)) ; la valeur finale du mélange (la
    REDONDANCE : le prix de l'universalité sous H0, en bits/tirage) ; les
    sups (Ville : franchissement de 20 avec proba <= 5 %).
    """
    rng = np.random.default_rng(31)
    Tsim = 8000 if FAST else 70560
    reds, sups_mix, sups_rst = [], [], []
    for r in range(R):
        m = lab.srs(Tsim, rng)
        bo = gen_bonus(m, rng)
        lf = run_coder(m, bo)
        f = np.exp(lf)                                   # e-facteurs par modèle
        fm = f.mean(axis=1)                              # facteur du mélange ~ moyenne ponctuelle
        # contrôle martingale sur le MEILLEUR test dispo : la moyenne temporelle
        # du facteur d'un modèle (mart. differences non corrélées). sh-d0 est
        # exclu : théta y est CONSTANT sur les 80 numéros, et le couplage est
        # invariant d'échelle — son facteur vaut 1 EXACTEMENT à chaque pas
        # (c'est le membre « cash » de la classe, voir la note du mélange).
        zs = []
        for j in range(M):
            sd = f[:, j].std(ddof=1)
            if sd > 0:
                zs.append((f[:, j].mean() - 1.0) / (sd / math.sqrt(Tsim)))
        worst = max(abs(z) for z in zs)
        log_mix, _ = mixture_log(lf)
        l10r = restart_mean_log10(lf)
        red_bits = log_mix[-1] / math.log(2) / Tsim
        reds.append(red_bits)
        sups_mix.append(log_mix.max() / LN10)
        sups_rst.append(float(l10r.max()))
        say(f"   archive H0 n°{r + 1} (T={Tsim}) : pire |z| des moyennes de "
            f"facteurs = {worst:.2f} sigma ({len(zs)} modèles non dégénérés) ;")
        say(f"      redondance du mélange = {red_bits:+.3e} bit/tirage ; "
            f"sup mélange 10^{sups_mix[-1]:+.3f} ; sup redémarrages "
            f"10^{sups_rst[-1]:+.3f}  (Ville : 10^{LOG10_VILLE:+.3f})")
        assert worst < 4.5, "une moyenne de facteurs dérive : ARRÊT"
    return reds, sups_mix, sups_rst


# --------------------------------------------------------------------------
# 2. Témoins positifs — sources délibérément biaisées, courbe d'amplitude
# --------------------------------------------------------------------------

def srs_weighted(T, w, rng):
    """Tirage sans remise à probabilités proportionnelles (Gumbel top-k =
    Plackett-Luce). w uniforme -> SRS exact."""
    g = np.log(w)[None, :] + rng.gumbel(size=(T, POOL))
    idx = np.argsort(-g, axis=1)[:, :DRAWN]
    m = np.zeros((T, POOL), bool)
    m[np.arange(T)[:, None], idx] = True
    return m


def contaminate_echo(m, rng, eps, lag):
    """Réinjection : avec proba eps, un numéro du tirage t-lag remplace un
    numéro frais du tirage t (la contamination momentum de f4 pour lag=1)."""
    m = m.copy()
    for t in range(lag, len(m)):
        if rng.random() >= eps:
            continue
        prev = np.flatnonzero(m[t - lag] & ~m[t])
        cur = np.flatnonzero(m[t] & ~m[t - lag])
        if len(prev) and len(cur):
            m[t, rng.choice(prev)] = True
            m[t, rng.choice(cur)] = False
    return m


def one_control_run(make_mask, rng):
    m = make_mask(rng)
    bo = gen_bonus(m, rng)
    lf = run_coder(m, bo)
    log_mix, _ = mixture_log(lf)
    l10r = restart_mean_log10(lf)
    kelly = log_mix[-1] / math.log(2) / len(m)
    return float(l10r.max()), kelly, m


def power_tables(T_pow, reps):
    """Quatre familles injectées + un angle mort assumé. Détection =
    sup des redémarrages >= 20 (le critère pré-enregistré de h35.restart)."""
    results = {}

    say("\n   -- null (aucun biais), la référence des cinq tableaux --")
    rngN = np.random.default_rng(101)
    for r in range(reps):
        s, k, _ = one_control_run(lambda rg: lab.srs(T_pow, rg), rngN)
        say(f"      H0 : sup redémarrages 10^{s:+.3f}   Kelly {k:+.3e} bit/t")

    say("\n   -- 1. MARGINALE : 8 numéros à poids (1+delta) --")
    fav = np.arange(8)
    for delta in (0.05, 0.10, 0.20, 0.40):
        w = np.ones(POOL); w[fav] = 1.0 + delta
        rng = np.random.default_rng(2000 + int(delta * 100))
        det, sups, effs = 0, [], []
        for r in range(reps):
            s, k, m = one_control_run(lambda rg: srs_weighted(T_pow, w, rg), rng)
            det += s >= LOG10_VILLE
            sups.append(s)
            effs.append(m[:, fav].mean() - 0.25)
        say(f"      delta={delta:.2f}  Dp={np.mean(effs):+.4f}  "
            f"sup 10^{np.mean(sups):+.2f}  détecté {det}/{reps}")
        results[("marginale", delta)] = (det, reps, float(np.mean(sups)))

    say("\n   -- 2. RÉMANENCE lag-1 (la contamination momentum de f3/f4) --")
    for eps in (0.02, 0.05, 0.10, 0.20):
        rng = np.random.default_rng(3000 + int(eps * 100))
        det, sups, effs = 0, [], []
        for r in range(reps):
            s, k, m = one_control_run(
                lambda rg: contaminate_echo(lab.srs(T_pow, rg), rg, eps, 1), rng)
            det += s >= LOG10_VILLE
            sups.append(s)
            effs.append((m[1:] & m[:-1]).sum(axis=1).mean() - 5.0)
        say(f"      eps={eps:.2f}  avance +{np.mean(effs):.4f} hits  "
            f"sup 10^{np.mean(sups):+.2f}  détecté {det}/{reps}")
        results[("momentum", eps)] = (det, reps, float(np.mean(sups)))

    say("\n   -- 3. PÉRIODIQUE structurel : écho au lag 8 --")
    for eps in (0.05, 0.10, 0.20):
        rng = np.random.default_rng(4000 + int(eps * 100))
        det, sups, effs = 0, [], []
        for r in range(reps):
            s, k, m = one_control_run(
                lambda rg: contaminate_echo(lab.srs(T_pow, rg), rg, eps, 8), rng)
            det += s >= LOG10_VILLE
            sups.append(s)
            effs.append((m[8:] & m[:-8]).sum(axis=1).mean() - 5.0)
        say(f"      eps={eps:.2f}  recouv-8 +{np.mean(effs):.4f}  "
            f"sup 10^{np.mean(sups):+.2f}  détecté {det}/{reps}")
        results[("lag8", eps)] = (det, reps, float(np.mean(sups)))

    say("\n   -- 4. TRANSITOIRE : marginale (1+delta) sur une fenêtre de 500 --")
    say("      Le régime que le §43 nomme le trou du dossier : même le")
    say("      balayage nommé de a3 n'a que 0,28 de puissance à L=500/+20 %.")
    L = 500
    for delta, t_on, tag in ((0.30, 3 * T_pow // 4, "tard"),
                             (0.60, 3 * T_pow // 4, "tard"),
                             (1.20, 3 * T_pow // 4, "tard"),
                             (0.60, T_pow // 10, "tôt ")):
        w = np.ones(POOL); w[fav] = 1.0 + delta

        def mk(rg, w=w, t_on=t_on):
            m = lab.srs(T_pow, rg)
            m[t_on:t_on + L] = srs_weighted(L, w, rg)
            return m
        rng = np.random.default_rng(5000 + int(delta * 100) + t_on)
        det, sups, effs = 0, [], []
        for r in range(reps):
            s, k, m = one_control_run(mk, rng)
            det += s >= LOG10_VILLE
            sups.append(s)
            effs.append(m[t_on:t_on + L][:, fav].mean() - 0.25)
        say(f"      delta={delta:.2f} ({tag}, t0={t_on})  "
            f"Dp fenêtre={np.mean(effs):+.4f}  "
            f"sup 10^{np.mean(sups):+.2f}  détecté {det}/{reps}")
        results[(f"transitoire-{tag.strip()}", delta)] = (det, reps, float(np.mean(sups)))

    say("\n   -- 5. ANGLE MORT ASSUMÉ : modulation périodique PURE EN TEMPS")
    say("      (période 2 : poids (1+delta) aux tirages pairs, 1/(1+delta)")
    say("      aux impairs). La classe ne contient AUCUN contexte exogène en")
    say("      t : elle ne doit voir ce biais qu'au second ordre, voire pas.")
    for delta in (0.30,):
        wA = np.ones(POOL); wA[fav] = 1.0 + delta
        wB = np.ones(POOL); wB[fav] = 1.0 / (1.0 + delta)

        def mk2(rg, wA=wA, wB=wB):
            mA = srs_weighted(T_pow, wA, rg)
            mB = srs_weighted(T_pow, wB, rg)
            m = mA.copy()
            m[1::2] = mB[1::2]
            return m
        rng = np.random.default_rng(6000)
        det, sups = 0, []
        for r in range(reps):
            s, k, m = one_control_run(mk2, rng)
            det += s >= LOG10_VILLE
            sups.append(s)
        say(f"      delta={delta:.2f}  sup 10^{np.mean(sups):+.2f}  "
            f"détecté {det}/{reps}  (attendu : faible/nul — limite de classe)")
        results[("periode2", delta)] = (det, reps, float(np.mean(sups)))

    return results


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------

def main():
    rule("h35 — CODAGE UNIVERSEL " + ("(mode FAST, rien au registre)" if FAST else ""))
    say(f"   classe : {M} codeurs KT, {TOTAL} paramètres Beta au total ; "
        f"coût du mélange log2({M}) = {math.log2(M):.2f} bits")
    say(f"   un tirage coûte {BITS_H0:.4f} bits sous H0")
    say("   NOTE STRUCTURELLE (leçon du plancher de f4, assumée d'avance) :")
    say("   sh-d0 a un théta CONSTANT sur les 80 numéros ; le couplage étant")
    say("   invariant d'échelle, son facteur vaut 1 exactement à chaque pas —")
    say("   c'est le codeur H0 lui-même, membre « cash » de la classe. Le")
    say(f"   mélange est donc PLANCHONNÉ à 1/{M} (log10 = {-math.log10(M):.3f}) :")
    say(f"   le taux de Kelly ne peut descendre sous {-math.log2(M):.2f}/T")
    say("   bit/tirage. C'est un choix, pas un accident : un compresseur")
    say("   universel contient le codeur de référence dans sa classe. Toute")
    say("   valeur finale collée à ce plancher se lit « les 20 autres modèles")
    say("   ont tout perdu », pas comme une mesure fine de leur perte.")

    rule("1. VÉRIFIER AVANT D'APPLIQUER — la leçon la plus chère du dossier")
    verify_e20_exact()
    verify_fixed_fields()
    verify_no_leak()
    say("\n   Le codeur complet, apprentissage compris, sur des archives SRS :")
    R_H0 = 2 if FAST else 4
    reds, sups_mix_h0, sups_rst_h0 = verify_full_coder_h0(R_H0)
    say(f"\n   PRIX DE L'UNIVERSALITÉ sous H0 : {np.mean(reds):+.3e} "
        f"bit/tirage (moyenne sur {R_H0} archives, min {min(reds):+.3e}, "
        f"max {max(reds):+.3e})")

    rule("2. LES 70 560 TIRAGES RÉELS")
    a = lab.load()
    mask, bonus = (a.mask[:8000], a.bonus[:8000]) if FAST else (a.mask, a.bonus)
    Treal = len(mask)
    t0 = time.time()
    LOGF = run_coder(mask, bonus, progress=20_000)
    say(f"   passe de codage : {time.time() - t0:.0f}s")
    log_mix, cum = mixture_log(LOGF)
    log10_mix = log_mix / LN10
    l10_rst = restart_mean_log10(LOGF)

    kelly = log_mix[-1] / math.log(2) / Treal
    say(f"\n   E final du mélange           : 10^{log10_mix[-1]:+.3f}")
    say(f"   taux de Kelly                : {kelly:+.3e} bit/tirage")
    say(f"   bits économisés sur l'archive: {log_mix[-1] / math.log(2):+.1f} bits "
        f"(sur {Treal * BITS_H0 / 1e6:.2f} Mbit)")
    say(f"   sup_t E du mélange           : 10^{log10_mix.max():+.3f}  "
        f"(au pas {int(np.argmax(log10_mix))}/{Treal})")
    say(f"   sup_t redémarrages (14-D)    : 10^{l10_rst.max():+.3f}  "
        f"(au pas {int(np.argmax(l10_rst))}/{Treal})")
    say(f"   seuil de Ville alpha = 0,05  : 10^{LOG10_VILLE:+.3f}")

    say("\n   par modèle, log10 E final (diagnostic — la décision est le mélange) :")
    finals = cum[-1] / LN10
    for j in np.argsort(-finals):
        say(f"     {MODELS[j][0]:<14} 10^{finals[j]:+9.3f}")

    rule("3. PUISSANCE — quatre témoins positifs et un angle mort assumé")
    T_pow = 4000 if FAST else 20_000
    reps = 1 if FAST else 2
    say(f"   T = {T_pow}, {reps} réplicat(s)/point ; détection = sup "
        f"redémarrages >= 20 (le critère pré-enregistré)")
    pw = power_tables(T_pow, reps)

    rule("4. LE PRIX DE L'UNIVERSALITÉ — comparaison à f4 (modèles nommés)")
    say("   f4 (RAPPORT 12.2, registre) : Kelly -3,33e-03 bit/tirage sur 70 547")
    say("   pas ; sup du mélange 10^+0,066 ; sup des 348 relancés 10^+0,962.")
    say(f"   h35 (universel)             : Kelly {kelly:+.3e} bit/tirage sur "
        f"{Treal} pas ;")
    say(f"   sup du mélange 10^{log10_mix.max():+.3f} ; sup des redémarrages "
        f"10^{l10_rst.max():+.3f}.")
    say(f"   Redondance structurelle mesurée sous H0 : {np.mean(reds):+.3e} "
        f"bit/tirage — c'est ce que coûte le droit de NE PAS nommer la famille.")

    rule("5. REGISTRE")
    if NO_RECORD:
        say("   --fast/--no-record : rien n'est écrit au registre")
        return
    existing = {r.get("id") for r in lab.ledger()}
    if {"h35.univ", "h35.sup", "h35.restart"} & existing:
        say("   entrées h35.* déjà présentes — AUCUN doublon écrit")
        return
    pw_str = "; ".join(f"{k[0]}@{k[1]}:{v[0]}/{v[1]}" for k, v in pw.items())
    h0_str = (f"redondance H0 {np.mean(reds):+.3e} bit/t sur {R_H0} archives "
              f"completes; sups H0 melange {['%+.2f' % s for s in sups_mix_h0]}, "
              f"redemarrages {['%+.2f' % s for s in sups_rst_h0]}")
    lab.record(TOK_UNIV, float(log10_mix[-1]), None,
               p=float(min(1.0, 10 ** (-log10_mix[-1]))),
               power_at=pw_str,
               verdict="",
               notes=f"Kelly {kelly:+.3e} bit/tirage ({Treal} pas) ; {M} modeles, "
                     f"{TOTAL} parametres ; {h0_str} ; f4 (nomme) : -3.326e-03")
    lab.record(TOK_SUP, float(log10_mix.max()), None,
               p=float(min(1.0, 10 ** (-log10_mix.max()))),
               power_at=pw_str,
               verdict="",
               notes=f"sup au pas {int(np.argmax(log10_mix))}/{Treal} ; "
                     f"Ville 10^{LOG10_VILLE:.3f}")
    lab.record(TOK_RST, float(l10_rst.max()), None,
               p=float(min(1.0, 10 ** (-l10_rst.max()))),
               power_at=pw_str,
               verdict="",
               notes=f"sup au pas {int(np.argmax(l10_rst))}/{Treal} ; blocs de "
                     f"{BLOCK}, prior 1/(j(j+1)) + tresorerie (14-D corrige)")
    say("   consigné : h35.univ, h35.sup, h35.restart")


if __name__ == "__main__":
    main()
    rule(f"terminé — {time.time() - T0:.0f}s")
