"""h140 — le DECODAGE MOU de l'archive TRIEE (70 560 tirages, 346 blocs de nuit) :
les plans bas de tout Fibonacci retarde additif reconstitues PAR JOURNEE — et
sous le flux continu — par transformee de Walsh-Hadamard sur des BITS MOUS
(THEORIE_ETAT §7.13).

CE QUE LES §7.10-7.11 LAISSAIENT
================================
Les cribles EXACTS ne lisent un bit qu'aux EVENEMENTS des masques de residus
(~0,06 par tirage : une classe absente). Sur une journee de 204 tirages, cela
fait ~12 equations : les trois plans bas de TYPE_1 (21 bits) sont MUETS (§7.10),
et le flux continu (§7.11) n'est attaquable que si le generateur n'est JAMAIS
reensemence. Un generateur reamorce chaque jour echappait a tout.

L'IDEE : UNE OBSERVATION PAR TIRAGE
===================================
Chaque mot pair k = 0, 2, ..., 18 (e = v2(80 - k) >= 1 : dix mots par tirage)
livre un BIT MOU sur le bit 0 de x_k = r_k >> shift : parmi les n numeros de
l'ensemble admissibles au mot k, n0 ont un residu pair, n1 un residu impair,
et le vrai residu est l'un d'eux : poids w = 256 ln((n0 + 1/2)/(n1 + 1/2)).
Mais les dix poids d'un tirage sont CORRELES a 0,88-0,99 (ils lisent tous le
meme desequilibre pair/impair de l'ensemble) : un score qui les traite comme
dix mesures independantes a une variance nulle qui depend de l'ETAT (x 9,5
pour un etat dont les dix bits d'un tirage sont egaux) — faux positifs et
fausses identifications sur les temoins. Le modele sain : le tirage t livre
UNE mesure y_t = moyenne des dix poids, et
    y_t | B_t ~ (mu B_t, sigma1^2),   B_t(etat) = somme_k (-1)^(bit_tk) in [-10, 10].
Pour un etat p : Lambda(p) = somme_t y_t B_t(p), Q(p) = somme_t B_t(p)^2,
    z(p) = Lambda / sqrt(sigma0^2 Q)         (variance EXACTEMENT 1 sous H0, tout etat)
    R(p) = Lambda - (mu/2) Q  proportionnel a la log-vraisemblance (le CLASSEMENT).
Le plan 0 est lineaire dans les L bits de l'etat bas, le plan 1 affine :
Lambda et Q s'obtiennent POUR TOUS LES ETATS par deux WHT de 2^L points (shift 0),
ou 2^L fois deux WHT (shift 1, plans 0 et 1 ensemble, 2^(2L) etats). L > 24 :
WHT A POSITIONS FIXEES (les L - b observations les plus fiables fixent L - b
bits, motifs d'erreur par vraisemblance decroissante jusqu'a la masse 0,95).
Detection : z de l'etat de R maximal >= Z1 = Q^-1(10^-7 / 2^nbits) ; z attendu
du vrai etat mu sqrt(10 n)/sigma0 ~ 9,2 par bloc de 204 tirages (sigma 0,77),
~170 sur le flux. Le plan shift + 1 (bit 1 des cinq mots k = 0 mod 4, poids
conditionnels des residus mod 4) CONFIRME : z2 ~ 6,1 attendu.
mu, sigma0, sigma1 sont CALIBRES par Monte-Carlo au lancement de l'outil.

TEMOINS
=======
`tools/lfg_soft_wht.c --selftest` : NB etats plantes (blocs de 204 tirages
dans le regime de l'archive) + NB blocs aleatoires ; la PUISSANCE est mesuree
(fraction des plantes detectes, identifies, confirmes) et les blocs nuls
calibrent la queue (z1 des nuls contre sqrt(2 ln N)). Faux positif = ECHEC.

Il TESTE l'archive : il consigne au registre, pre-enregistrement AVANT le
decodage (jeton scelle, conserve dans le journal pour la reprise).
"""

import json
import math
import os
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H140_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.dirname(os.path.dirname(ICI))
TMP = os.environ.get("H140_TMP", "/tmp")
EXP_ID = "h140.decodage_mou"
POOL, DRAWN = 80, 20
MOTS10 = [(0, 4), (2, 1), (4, 2), (6, 1), (8, 3), (10, 1), (12, 2), (14, 1), (16, 6), (18, 1)]
NBT = 12                                                      # temoins : plantes = nuls = NBT blocs


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def Qinv(cible):
    """Q^-1 : z tel que P(N(0,1) >= z) = cible (bissection, comme l'outil)."""
    lo, hi = 0.0, 20.0
    for _ in range(200):
        z = 0.5 * (lo + hi)
        if 0.5 * math.erfc(z / math.sqrt(2)) > cible:
            lo = z
        else:
            hi = z
    return 0.5 * (lo + hi)


def Phi(x):
    return 0.5 * math.erfc(-x / math.sqrt(2))


def seuil(nbits, alpha=1e-7):
    return Qinv(alpha / 2.0 ** nbits)


# --------------------------------------------------------------------------
# trinomes primitifs x^L + x^K + 1 sur GF(2), L <= 17 (comme h137)
# --------------------------------------------------------------------------

def _mulmod(a, b, p, L):
    r = 0
    while b:
        if b & 1:
            r ^= a
        b >>= 1
        a <<= 1
        if (a >> L) & 1:
            a ^= p
    return r


def _powmod(a, e, p, L):
    r = 1
    while e:
        if e & 1:
            r = _mulmod(r, a, p, L)
        a = _mulmod(a, a, p, L)
        e >>= 1
    return r


def _facteurs(n):
    f, d = set(), 2
    while d * d <= n:
        while n % d == 0:
            f.add(d)
            n //= d
        d += 1
    if n > 1:
        f.add(n)
    return f


def primitif(K, L):
    p = (1 << L) | (1 << K) | 1
    n = (1 << L) - 1
    if _powmod(2, n, p, L) != 1:
        return False
    return all(_powmod(2, n // q, p, L) != 1 for q in _facteurs(n))


LMAX = 17
NOMS = {(3, 7): "TYPE_1", (1, 15): "TYPE_2", (3, 31): "TYPE_3"}
TRINOMES = [(K, L) for L in range(2, LMAX + 1) for K in range(1, L) if primitif(K, L)]
assert len(TRINOMES) == 31 and (3, 7) in TRINOMES and (1, 15) in TRINOMES
VARIANTES = [("fy", s) for s in (20, 21, 22, 23, 24, 79, 80)] + [("shuffle", s) for s in (79, 80)]
SCHEMAS = ("Fisher-Yates partiel par modulo aux pas 20 a 24, 79 et 80 ; "
           "Collections.shuffle vingt dernieres cases aux pas 79 et 80")
# la grille : (cible, shift, trinomes). Par bloc a shift 1, 2^(2L) etats par bloc :
# L <= 11 et TYPE_2 (1, 15) seulement (les cinq autres trinomes de degre 15 et les six
# de degre 17 : 2 a 20 h de calcul chacun, exclus sous le flux continu par h137).
GRILLE = [
    ("bloc", 0, TRINOMES + [(3, 31)]),
    ("flux", 0, TRINOMES + [(3, 31)]),
    ("bloc", 1, [t for t in TRINOMES if t[1] <= 11] + [(1, 15)]),
    ("flux", 1, [t for t in TRINOMES if t[1] <= 15]),
]
if DRY:
    GRILLE = [(c, s, [t for t in tr if t[1] <= 7 or t == (3, 31)][:3]) for c, s, tr in GRILLE]
    VARIANTES = [("fy", 20), ("shuffle", 79)]

NBFILS = os.environ.get("SWEEP_THREADS", "2")
ENV = dict(os.environ, SWEEP_THREADS=NBFILS)
BIN = os.path.join(TMP, "lfg_soft_wht_h140")
subprocess.run(["cc", "-O3", "-march=native", "-pthread", "-o", BIN,
                os.path.join(DEPOT, "tools", "lfg_soft_wht.c"), "-lm"],
               check=True, capture_output=True)


def env_de(K, L, shift):
    """TYPE_3 : WHT a positions fixees, arret anticipe au seuil de detection."""
    e = dict(ENV)
    if L > 24:
        e["WHT_B"] = "18"
        e["WHT_ZSTOP"] = "%.3f" % seuil(L if shift == 0 else 2 * L)
    return e


def lit_calib(lignes):
    for l in lignes:
        if l.startswith("CALIB "):
            t = l.split()
            d = dict(mode=t[1])
            for tok in t[2:]:                      # jetons nom=valeur
                nom, val = tok.split("=")
                d[nom] = float(val)
            return d
    raise RuntimeError("pas de ligne CALIB")


def lit_blocs(lignes):
    """Lignes BLOC -> liste de dicts."""
    out = []
    for l in lignes:
        if not l.startswith("BLOC "):
            continue
        t = l.split()
        out.append(dict(b=int(t[1]), t0=int(t[2]), n=int(t[3]), nobs=int(t[4]), z1=float(t[5]),
                        z1b=float(t[6]), meth=t[7], couv=float(t[8]), plans=t[9:12],
                        z2=float(t[12]), z2b=float(t[13]), meth2=t[14], couv2=float(t[15]),
                        delta=int(t[16])))
    return out


def lit_fin(lignes):
    for l in reversed(lignes):
        if l.startswith("FIN "):
            t = l.split()
            return dict(nblocs=int(t[6]), zmax=float(t[7]), bloc_zmax=int(t[8]), sec=float(t[11]))
    raise RuntimeError("pas de ligne FIN")


def lance(args, K, L, shift):
    p = subprocess.run([BIN] + [str(a) for a in args], capture_output=True, text=True,
                       timeout=12 * 3600, env=env_de(K, L, shift))
    assert p.returncode == 0, (args, p.stderr[-2000:])
    return p.stdout.strip().split("\n")


def decode(K, L, S, mode, shift, fichier, blocs):
    return lance([K, L, S, mode, shift, fichier, blocs], K, L, shift)


def temoin(K, L, S, mode, shift, nb, graine, n=None, flux=False):
    """NB plantes + NB nuls ; rend (calib, dict des comptes, z1 des plantes, z1 des nuls,
    z2 des plantes)."""
    args = ["--selftest-flux" if flux else "--selftest", K, L, S, mode, shift, nb, graine]
    if not flux and n:
        args.append(n)
    lignes = lance(args, K, L, shift)
    cal = lit_calib(lignes)
    d = {}
    for l in lignes:
        if l.startswith("AUTOTEST "):
            for t in l.split():
                if "=" in t:
                    a, b = t.split("=")
                    d[a] = float(b) if a == "Z1" else int(b)
    zv = [float(l.split()[7].split("=")[1]) for l in lignes if l.startswith("VERITE ")]
    bl = lit_blocs(lignes)
    npl = 1 if flux else nb
    z_nuls = [x["z1"] for x in bl if x["b"] >= npl]
    z2_pl = [x["z2"] for x in bl if x["b"] < npl]
    return cal, d, zv, z_nuls, z2_pl


# --------------------------------------------------------------------------
# le flux bas et les masques, cote Python (verification exacte d'un etat rendu)
# --------------------------------------------------------------------------

def masque(ens, k, e, mode):
    m = 0
    for v in ens:
        if mode == "fy":
            if v >= k + 1:
                m |= 1 << ((v - 1 - k) % (1 << e))
        else:                                   # shuffle : mot k <-> case i = 79 - k
            if v <= POOL - k:
                m |= 1 << ((v - 1) % (1 << e))
    return m


def coherent_bloc(plans, K, L, S, mode, shift, ens):
    """Les plans bas rendus (liste d'entiers : plan j = bits j des L mots initiaux) lus
    a partir du premier tirage du bloc sont-ils coherents avec les masques de ses
    ensembles ? Rend (ok, tirage fautif, nombre d'evenements = masques incomplets)."""
    npl = len(plans)
    nb = npl - shift                            # bits de x connus
    if nb <= 0:
        return None, None, 0
    MOD = 1 << npl
    n = S * (len(ens) - 1) + POOL + L
    r = [sum(((plans[j] >> i) & 1) << j for j in range(npl)) for i in range(L)] + [0] * (n - L)
    for i in range(L, n):
        r[i] = (r[i - K] + r[i - L]) % MOD
    nev = 0
    for t, e_t in enumerate(ens):
        for k, e in MOTS10:
            ee = min(e, nb)
            x = (r[S * t + k] >> shift) % (1 << ee)
            m = masque(e_t, k, ee, mode)
            if m != (1 << (1 << ee)) - 1:
                nev += 1
            if not (m >> x) & 1:
                return False, t, nev
    return True, None, nev


# ==========================================================================
rule("1. LA THEORIE : UNE OBSERVATION PAR TIRAGE, DEUX WHT PAR BLOC")
# ==========================================================================

say(f"""   Dix mots pairs par tirage (k, e) = {MOTS10} ; poids w_k = 256 ln((n0 + 1/2)/(n1 + 1/2)) ;
   y_t = moyenne des dix poids (une observation), B_t = somme des dix bits (-1)^b du plan
   shift de l'etat ; Lambda = somme y_t B_t, Q = somme B_t^2 ; z = Lambda/sqrt(sigma0^2 Q) ;
   R = Lambda - (mu/2) Q classe, z de l'etat de R maximal detecte.

   Seuils Z1 = Q^-1(10^-7 / 2^nbits) (nbits = L a shift 0, 2L a shift 1) et puissance du
   modele P(z_vrai >= Z1) = Phi((mu sqrt(10 n)/sigma0 - Z1) / (sigma1/sigma0)) pour n = 204
   (les constantes calibrees sont relues sur le premier temoin, ci-dessous).

       {'K':>2} {'L':>2} {'shift':>5} {'etats':>6} {'Z1':>5}  trinome""")
for cible, shift, trin in GRILLE:
    if cible != "bloc":
        continue
    for K, L in trin:
        nb = L if shift == 0 else 2 * L
        say(f"       {K:>2} {L:>2} {shift:>5} {'2^%d' % nb:>6} {seuil(nb):>5.2f}  x^{L}+x^{L-K}+1 {NOMS.get((K, L), '')}")
NRUNS = sum(len(trin) * len(VARIANTES) for _, _, trin in GRILLE)
say(f"""
   {NRUNS} decodages : par BLOC (346 nuits, un etat par bloc) et sous le FLUX (un etat pour
   les 70 560 tirages), {len(VARIANTES)} variantes ({SCHEMAS}), shift 0 (sortie brute) et
   shift 1 (glibc random()).""")


# ==========================================================================
rule("2. L'ARCHIVE : 346 BLOCS DE NUIT, UN FLUX")
# ==========================================================================

ARCH = lab.load()
TS = np.asarray(ARCH.ts).astype(np.int64)
IDS = np.asarray(ARCH.ids).astype(np.int64)
NUM = np.sort(np.asarray(ARCH.nums).astype(np.int64), axis=1)
NTOT = len(NUM)
ENS = [NUM[t].tolist() for t in range(NTOT)]
coupe = np.flatnonzero(np.diff(TS) != 300)
DEB = np.r_[0, coupe + 1]
FIN_ = np.r_[coupe + 1, NTOT]
TAILLES = FIN_ - DEB
if DRY:
    DEB = DEB[:6]
    FIN_ = FIN_[:6]
    TAILLES = FIN_ - DEB
    NTOT_FLUX = 3000
else:
    NTOT_FLUX = NTOT
FARCH = os.path.join(TMP, "h140_archive.txt")
with open(FARCH, "w") as fh:
    for t in range(NTOT):
        fh.write(" ".join(str(v) for v in ENS[t]) + "\n")
FBLOCS = os.path.join(TMP, "h140_blocs.txt")
with open(FBLOCS, "w") as fh:
    for d in DEB:
        fh.write(f"{int(d)}\n")
FFLUX = os.path.join(TMP, "h140_flux.txt")
with open(FFLUX, "w") as fh:
    fh.write("0\n")
FARCH_FLUX = FARCH
if DRY:
    FARCH_FLUX = os.path.join(TMP, "h140_archive_dry.txt")
    with open(FARCH_FLUX, "w") as fh:
        for t in range(NTOT_FLUX):
            fh.write(" ".join(str(v) for v in ENS[t]) + "\n")
NBLOCS = len(DEB)
tailles = sorted(set(int(x) for x in TAILLES))
say(f"""   {NTOT} tirages, identifiants {int(IDS[0])} a {int(IDS[-1])} ; {NBLOCS} blocs de nuit
   (ruptures de la cadence de 300 s), tailles {tailles} ({int(np.sum(TAILLES == 204))} blocs de
   204 tirages). Par bloc : {NBLOCS} etats independants ; flux : un etat, {NTOT_FLUX} tirages.""")


# ==========================================================================
rule("3. PRE-ENREGISTREMENT (avant tout decodage de l'archive)")
# ==========================================================================

JOURNAL = os.path.join(TMP, "h140_journal.txt")
FJETON = os.path.join(TMP, "h140_jeton.json")
HYPOTHESE = (
    "Aucun bloc de nuit de l'archive triee (346 blocs, un etat par bloc : generateur "
    "reamorce chaque jour) et pas le flux continu (un etat, 70 560 tirages) n'est engendre "
    "par un Fibonacci retarde additif r_i = r_(i-K) + r_(i-L) mod 2^32 lu a pas constant : "
    f"les {len(TRINOMES)} trinomes primitifs de degre L <= {LMAX} (TYPE_1 et TYPE_2 compris) et "
    "TYPE_3 (3, 31), sortie x = r >> 1 (glibc, plans 0 et 1 decodes ensemble, 2^(2L), "
    "L <= 11 et TYPE_2 par bloc, L <= 15 sous le flux) ou x = r (shift 0, plan 0, tous les "
    f"trinomes et TYPE_3), sous les schemas : {SCHEMAS}. Decodage MOU (§7.13) : une observation "
    "par tirage y_t (moyenne des dix poids ln((n0+1/2)/(n1+1/2)) des mots pairs), Lambda et Q "
    "pour tous les etats par deux transformees de Walsh-Hadamard, classement par "
    "R = Lambda - (mu/2) Q, detection par z = Lambda/sqrt(sigma0^2 Q) de l'etat de R maximal. "
    "Design et seuils fixes AVANT cette consignation sur des temoins plantes, jamais sur l'archive"
)
STATISTIQUE = (
    "nombre D de (decodage, bloc) DETECTES : z1 >= Z1 = Q^-1(10^-7 / 2^nbits), nbits = L a "
    "shift 0 et 2L a shift 1 (z1 = z de l'etat de R maximal, variance 1 sous H0 pour tout "
    "etat) ; parmi eux, nombre CONFIRMES : plan shift + 1 (cinq mots k = 0 mod 4, poids "
    "conditionnels mod 4) de z2 >= Z2 = Q^-1(10^-3 / 2^L), et coherence exacte des plans "
    "rendus avec les masques de residus du bloc"
)
NULL = (
    "borne d'union exacte : sous H0, z(p) est de variance 1 pour chacun des 2^nbits etats, "
    f"P(detection d'un bloc) <= 10^-7, soit E[D] <= {NRUNS} decodages x 346 blocs x 10^-7 "
    "~ 0,02 sur toute la grille (queue gaussienne de z, calibree sur les blocs nuls des temoins "
    "contre sqrt(2 ln N))"
)
VERDICT = (
    "conforme si D = 0 ; ETAT TROUVE si un bloc detecte est confirme (z2 >= Z2 ET coherence "
    "exacte) — un generateur reamorce chaque jour en donnerait ~puissance x 346 par schema, "
    "le flux un z ~ 170 ; DETECTION NON CONFIRMEE sinon (anomalie a examiner, non conforme)"
)
if not DRY:
    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']} le {TOK['registered_at']}")
    else:
        TOK = lab.preregister(EXP_ID, HYPOTHESE, STATISTIQUE, NULL, VERDICT, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']} le {TOK['registered_at']}")
else:
    say("   MODE ESSAI : pas de jeton.")


# ==========================================================================
rule("4. TEMOINS : PUISSANCE MESUREE, QUEUE DES BLOCS NULS")
# ==========================================================================

TEMOINS_SPEC = [(3, 7, 20, "fy", 0, 1), (3, 7, 20, "fy", 1, 2), (3, 7, 80, "shuffle", 1, 3),
                (1, 15, 22, "fy", 0, 4), (1, 15, 79, "shuffle", 1, 5), (2, 11, 24, "fy", 1, 6),
                (3, 17, 20, "fy", 0, 7), (3, 17, 80, "shuffle", 0, 8),
                (3, 31, 20, "fy", 0, 9), (3, 31, 80, "shuffle", 0, 10)]
TEMOINS_FLUX = [(3, 7, 20, "fy", 1, 11), (1, 15, 80, "shuffle", 1, 12), (3, 31, 20, "fy", 0, 13)]
if DRY:
    TEMOINS_SPEC = TEMOINS_SPEC[:3] + TEMOINS_SPEC[8:9]
    TEMOINS_FLUX = TEMOINS_FLUX[:1]
say(f"""   {NBT} etats 32 bits plantes (blocs de 204 tirages) + {NBT} blocs aleatoires par classe ;
   detecte = z1 >= Z1, identifie = plan shift exact (etape 1), confirme = plan shift + 1
   exact (etape 2). Puissance du modele entre parentheses. Faux positif = ECHEC.

       {'K':>2} {'L':>2} {'S':>3} {'mode':>7} {'shift':>5} {'Z1':>5} {'detect':>7} {'ident':>6} {'conf':>5} {'z1 vrai':>9} {'z1 nuls max':>11} {'fp':>3} {'sec':>6}""")
TEMOINS = []
CALIB = {}
FP_TOTAL = 0
Z_NULS = []
for K, L, S, mode, shift, gr in TEMOINS_SPEC:
    t0 = time.time()
    cal, d, zv, zn, z2 = temoin(K, L, S, mode, shift, NBT, gr, n=204)
    CALIB.setdefault(mode, cal)
    nb_ = L if shift == 0 else 2 * L
    Z1 = seuil(nb_)
    zmod = cal["mu1"] * math.sqrt(10 * 204) / math.sqrt(cal["s01"])
    pmod = Phi((zmod - Z1) / math.sqrt(cal["s11"] / cal["s01"]))
    if L > 24:
        pmod *= 0.95
    FP_TOTAL += d["faux_positifs"]
    Z_NULS += [(z, nb_) for z in zn]
    TEMOINS.append((K, L, S, mode, shift, d, zv, zn, pmod))
    say(f"       {K:>2} {L:>2} {S:>3} {mode:>7} {shift:>5} {Z1:>5.2f} {d['detectes']:>2}/{NBT:<2} ({pmod:.2f}) "
        f"{d['etape1_ok']:>2}/{NBT:<2} {d['etape2_ok']:>2}/{NBT:<2} {np.mean(zv):>5.2f}±{np.std(zv):<3.2f} "
        f"{max(zn):>5.2f}/{math.sqrt(2 * nb_ * math.log(2)):<5.2f} {d['faux_positifs']:>3} {time.time()-t0:>6.1f}")
say(f"\n   flux : un etat plante sur {NTOT_FLUX} tirages + {NTOT_FLUX} aleatoires")
for K, L, S, mode, shift, gr in TEMOINS_FLUX:
    t0 = time.time()
    cal, d, zv, zn, z2 = temoin(K, L, S, mode, shift, NTOT_FLUX, gr, flux=True)
    nb_ = L if shift == 0 else 2 * L
    FP_TOTAL += d["faux_positifs"]
    Z_NULS += [(z, nb_) for z in zn]
    TEMOINS.append((K, L, S, mode, shift, d, zv, zn, None))
    say(f"       {K:>2} {L:>2} {S:>3} {mode:>7} {shift:>5} {seuil(nb_):>5.2f} {d['detectes']:>2}/1         "
        f"{d['etape1_ok']:>2}/1  {d['etape2_ok']:>2}/1  {zv[0]:>7.1f}     {max(zn):>5.2f}/{math.sqrt(2 * nb_ * math.log(2)):<5.2f} "
        f"{d['faux_positifs']:>3} {time.time()-t0:>6.1f}")
for mode, cal in CALIB.items():
    say(f"   calibration {mode:>7} : mu = {cal['mu1']:.3f}  sigma0 = {math.sqrt(cal['s01']):.1f}  sigma1 = {math.sqrt(cal['s11']):.1f}  "
        f"(z attendu {cal['mu1'] * math.sqrt(2040) / math.sqrt(cal['s01']):.2f} ± {math.sqrt(cal['s11'] / cal['s01']):.2f} par bloc de 204) ; "
        f"etape 2 : mu = {cal['mu2']:.3f}  sigma0 = {math.sqrt(cal['s02']):.1f}  (z2 attendu {cal['mu2'] * math.sqrt(1020) / math.sqrt(cal['s02']):.2f})")
exces = [(z, nb_) for z, nb_ in Z_NULS if z > math.sqrt(2 * nb_ * math.log(2)) + 1.0]
say(f"   blocs nuls : {len(Z_NULS)} valeurs de z1 (etat de R maximal), {len(exces)} au-dela de sqrt(2 ln N) + 1 ; "
    f"faux positifs : {FP_TOTAL}")
say(f"   temoins : {'CONFORMES' if FP_TOTAL == 0 else 'ECHEC'}")
assert FP_TOTAL == 0


# ==========================================================================
rule("5. LE DECODAGE DE L'ARCHIVE")
# ==========================================================================

DEJA = {}
if os.path.exists(JOURNAL):
    for l in open(JOURNAL, encoding="utf-8"):
        t = l.split()
        if len(t) >= 6:
            DEJA[t[0]] = (int(t[1]), int(t[2]), float(t[3]), int(t[4]), float(t[5]), t[6:])
    say(f"   reprise : {len(DEJA)} decodages deja faits, ecrits dans {JOURNAL}")
jr = open(JOURNAL, "a", encoding="utf-8")

say(f"""
       {'cible':>5} {'K':>2} {'L':>2} {'S':>3} {'mode':>7} {'shift':>5} {'etats':>6} {'Z1':>5} {'blocs':>5} {'detec':>5} {'conf':>4} {'z1 max':>7} {'sec':>8}""")
LIG, DETEC = [], []
for cible, shift, trin in GRILLE:
    for K, L in trin:
        for mode, S in VARIANTES:
            cle = f"{cible},{K},{L},{S},{mode},{shift}"
            nb_ = L if shift == 0 else 2 * L
            Z1, Z2 = seuil(nb_), seuil(L, 1e-3)
            t0 = time.time()
            if cle in DEJA:
                ndet, nconf, zmax, bmax, sec, det = DEJA[cle]
                det = [x for x in det if x != "-"]
                nblocs = NBLOCS if cible == "bloc" else 1
            else:
                lignes = decode(K, L, S, mode, shift, FARCH if cible == "bloc" else FARCH_FLUX,
                                FBLOCS if cible == "bloc" else FFLUX)
                bl, fin = lit_blocs(lignes), lit_fin(lignes)
                nblocs, zmax, bmax, sec = fin["nblocs"], fin["zmax"], fin["bloc_zmax"], fin["sec"]
                det = []
                nconf = 0
                for x in bl:
                    if x["z1"] < Z1:
                        continue
                    plans = [int(p, 16) for p in x["plans"] if p != "-"]
                    ens = ENS[x["t0"]:x["t0"] + x["n"]]
                    ok, tf, nev = coherent_bloc(plans, K, L, S, mode, shift, ens)
                    conf = x["z2"] >= Z2 and ok is True
                    nconf += conf
                    det.append(f"{x['b']}:{x['z1']:.2f}:{x['z2']:.2f}:{'+'.join(x['plans'])}:{x['delta']}:"
                               f"{'coherent' if ok else 'incoherent_t%d' % tf if ok is False else 'sans_plan'}:{nev}:"
                               f"{'CONFIRME' if conf else 'non_confirme'}")
                ndet = len(det)
                jr.write(f"{cle} {ndet} {nconf} {zmax} {bmax} {sec} {' '.join(det) if det else '-'}\n")
                jr.flush()
            LIG.append((cible, K, L, S, mode, shift, nblocs, ndet, nconf, zmax, bmax, sec))
            for e in det:
                DETEC.append((cible, K, L, S, mode, shift, e))
            say(f"       {cible:>5} {K:>2} {L:>2} {S:>3} {mode:>7} {shift:>5} {'2^%d' % nb_:>6} {Z1:>5.2f} {nblocs:>5} "
                f"{ndet:>5} {nconf:>4} {zmax:>7.2f} {sec:>8.1f}" + ("" if ndet == 0 else "   !!"))

D_TOT = sum(l[7] for l in LIG)
C_TOT = sum(l[8] for l in LIG)
SEC = sum(l[11] for l in LIG)
NBLOC_TOT = sum(l[6] for l in LIG)
ZMAX = max(l[9] for l in LIG)
lmax = max(LIG, key=lambda l: l[9])
say(f"""
   {len(LIG)} decodages, {NBLOC_TOT} (decodage, bloc) ; D = {D_TOT} detecte, {C_TOT} confirme ;
   z1 max = {ZMAX:.2f} ({lmax[0]} x^{lmax[2]}+x^{lmax[2]-lmax[1]}+1 {lmax[4]} pas {lmax[3]} shift {lmax[5]}, bloc {lmax[10]}) ;
   {SEC/3600:.2f} h de decodage cumulees.""")
for cible, K, L, S, mode, shift, e in DETEC:
    say(f"     !! {cible} x^{L}+x^{L-K}+1 {mode} pas {S} shift {shift} : {e}")
if D_TOT == 0:
    say(f"""     AUCUNE DETECTION. Sur chaque nuit prise a part comme sous le flux continu, les
     plans bas des {len(TRINOMES)} trinomes de degre <= {LMAX} et de TYPE_3 (shift 0) ne sont pas
     dans l'archive triee : un generateur reamorce chaque jour aurait allume
     ~{0.88 * NBLOCS:.0f} blocs sur {NBLOCS} par schema, le flux un z ~ 170.

   CE QUI RESTE HORS DU DECODAGE : TYPE_3 a shift 1 (2^62 etats par bloc : les plans 0
   et 1 ensemble, hors de portee de la WHT), TYPE_4 (1, 63) ; par bloc a shift 1 les
   trinomes de degre 15 (sauf TYPE_2) et 17 ; le rejet des doublons (pas variable) ;
   la troncature (x * 80) >> 32 ; les vingt premieres cases d'un shuffle ; le
   Fibonacci SOUSTRACTIF.""")


# ==========================================================================
rule("6. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    TOK["m_extra"] = 0
    verdict = ("conforme" if D_TOT == 0 else "ETAT TROUVE" if C_TOT else "DETECTION NON CONFIRMEE")
    puiss = "; ".join(
        f"x^{L}+x^{L-K}+1 {mode} pas {S} shift {shift} : detectes {d['detectes']}/{d['plantes']}"
        f"{'' if pm is None else ' (modele %.2f)' % pm}, identifies {d['etape1_ok']}/{d['plantes']}, "
        f"confirmes {d['etape2_ok']}/{d['plantes']}, z1 vrai {np.mean(zv):.2f}±{np.std(zv):.2f}, "
        f"z1 nuls max {max(zn):.2f}"
        for K, L, S, mode, shift, d, zv, zn, pm in TEMOINS)
    lab.record(
        TOK, float(D_TOT), p=1.0 if D_TOT == 0 else min(1.0, NBLOC_TOT * 1e-7), verdict=verdict,
        power_at=(f"temoins plantes dans le regime de l'archive ({NBT} blocs de 204 tirages + "
                  f"{NBT} nuls par classe ; flux : {NTOT_FLUX} tirages) : " + puiss
                  + f" — {FP_TOTAL} faux positif sur les blocs nuls"),
        notes=(f"LE DECODAGE MOU : {len(LIG)} decodages ({NBLOC_TOT} (decodage, bloc)), "
               f"{NBLOCS} blocs de nuit + le flux, {len(VARIANTES)} variantes, shifts 0 et 1. "
               f"D = {D_TOT} detecte, {C_TOT} confirme, z1 max {ZMAX:.2f}. Calibration "
               + "; ".join(f"{m} : mu {c['mu1']:.3f} sigma0 {math.sqrt(c['s01']):.1f} sigma1 {math.sqrt(c['s11']):.1f}"
                           for m, c in CALIB.items())
               + f" (unites 256 ln). {SEC/3600:.2f} h de decodage. NON COUVERT : TYPE_3 shift 1 "
               f"(2^62 par bloc), TYPE_4, degres 15 (hors TYPE_2) et 17 a shift 1 par bloc, rejet, "
               f"troncature, vingt premieres cases d'un shuffle, Fibonacci soustractif."))
    h = lab.holm()
    say(f"   consigne : {EXP_ID}   verdict {verdict}")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")
say(f"\n   duree totale {(time.time() - T0)/60:.1f} min")
