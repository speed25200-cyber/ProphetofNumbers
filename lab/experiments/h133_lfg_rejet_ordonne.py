"""h133 — l'ÉTAT BAS du Fibonacci retardé additif (glibc random(), TYPE_1/2/3),
retrouvé ou exclu à partir des tirages ORDONNÉS CONSÉCUTIFS des vidéos, sous
REJET des doublons, l'état étant LIBRE (amorcé n'importe comment).

CE QUI RESTAIT OUVERT
=====================
Le §103 teste la récurrence à trois termes de glibc à PAS CONSTANT (troncature),
et note que sous le rejet « l'alignement des lags se perd ». Le §152 crible les
LCG sous le rejet grâce à leur autonomie modulo 2^m. Le Fibonacci retardé
r_i = r_{i-k} + r_{i-L} mod 2^32 est lui aussi AUTONOME modulo 32 : ses cinq
bits bas forment un flux de 5L bits qui ne dépend de rien d'autre. Écrivons
r = 2q + b. Le bit b (plan 0) n'est JAMAIS publié (random() rend r >> 1) et
suit un LFSR ; le nibble q mod 16 = (v − 1) mod 16 est publié par chaque mot
accepté, car 80 = 16 · 5 ; et

    b_i = b_{i-k} ⊕ b_{i-L},     q_i = q_{i-k} + q_{i-L} + c_i (mod 16),
    c_i = b_{i-k} ∧ b_{i-L}.

LA RECONSTRUCTION (tools/lfg_low_reject.c, THEORIE_ETAT.md §7.7)
=================================================================
1. ALIGNEMENT. Les mots perdus (doublons) sont invisibles ; on cherche leurs
   positions. Un mot accepté dont les deux antécédents sont connus doit
   vérifier (q_i − q_{i-k} − q_{i-L}) mod 16 ∈ {0, 1} — élague 7/8 — et la
   valeur trouvée EST la retenue c_i. Un mot perdu doit être un doublon : son
   nibble, {s, s+1}, doit être une classe déjà sortie dans le tirage, et il
   reçoit ce nibble, si bien que les cohérences suivantes s'appliquent aussi
   à lui. La recherche est paresseuse : le premier tirage n'est décidé qu'au
   fil des besoins des suivants, chaque décision élaguée aussitôt.
2. PLAN 0. c_i = 1 dit b_{i-k} = b_{i-L} = 1 : deux équations linéaires sur les
   L bits initiaux du LFSR ; c_i = 0 dit NON(b_{i-k} ∧ b_{i-L}). Gauss sur
   GF(2), énumération du noyau, filtre par les NON-ET.
3. NIBBLES. Le plan 0 fixé, les retenues sont des constantes et q_i est AFFINE
   mod 16 dans les L nibbles initiaux : relèvement de Hensel plan par plan
   avec la même matrice sur GF(2).
4. VÉRIFICATION. Le flux bas régénéré rend tous les nibbles, les doublons sont
   des doublons, et, les bits bas connus, 2^32 ≡ 1 (mod 5) livre le BIT DE
   DÉBORDEMENT w_i = [r_{i-k} + r_{i-L} ≥ 2^32] = (r_{i-k} + r_{i-L} − r_i)
   mod 5 avec r ≡ 2·(v−1) + b (mod 5) : il doit valoir 0 ou 1 (élague 3/5).
   Les SATELLITES — tirages ordonnés du même jour à un écart d'identifiants
   connu — sont rejoués depuis l'état trouvé, la récurrence étant inversible.

Un état est identifié à son ORBITE : quand le premier mot du noyau est suivi
de son propre doublon, l'état « un pas plus tard » explique aussi tout — même
flux, même prédiction. Ce fantôme de décalage n'est pas un faux positif ; le
témoin le compte à part (défaut découvert et corrigé en mode essai, AVANT la
consignation).

CE QUE LES VIDÉOS DONNENT
=========================
Trois jours, trois structures (lab/draws_ordered.csv) :
    jour A : noyau 1381030–1381031 (2 consécutifs), satellites −7, −4, −2 ;
    jour B : noyau 1381256–1381259 (4 consécutifs), satellite +22 ;
    jour C : noyau 1381481 (seul), satellite +2.
Un jour n'est DÉCISIF pour un type que si l'information dépasse les inconnues
(§1) ET que l'outil retrouve un état planté dans la même structure (§2).
TYPE_4 (63, 1) est hors de portée : 315 bits bas, il faudrait ~11 tirages
consécutifs. TYPE_3 à deux tirages consécutifs (jour A) l'est aussi, par le
calcul : trop peu de retenues, le noyau du plan 0 a ~2^20 éléments par
alignement.

Il TESTE les vidéos : il consigne au registre. Aucune validation sur
l'archive n'est possible, elle s'arrête (1380173) avant les vidéos.
"""

import csv
import os
import random
import subprocess
import sys
import time
from math import comb, log2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H133_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.dirname(os.path.dirname(ICI))
TMP = os.environ.get("H133_TMP", "/tmp")
THREADS = os.environ.get("SWEEP_THREADS", "4")
CAP = 10                         # mots perdus au plus par tirage
NTEM = 4 if DRY else 10          # témoins plantés par cellule
GRAINE = 20260901
M32 = 1 << 32

TYPES = [("TYPE_1", 3, 7), ("TYPE_2", 1, 15), ("TYPE_3", 3, 31)]
# (nom, identifiants du noyau, [(g, identifiant satellite)])
JOURS = [
    ("A", [1381030, 1381031], [(-7, 1381023), (-4, 1381026), (-2, 1381028)]),
    ("B", [1381256, 1381257, 1381258, 1381259], [(22, 1381278)]),
    ("C", [1381481], [(2, 1381483)]),
]


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


BIN = os.path.join(TMP, "lfg_low_reject_h133")
subprocess.run(["cc", "-O3", "-march=native", "-pthread", "-o", BIN,
                os.path.join(DEPOT, "tools", "lfg_low_reject.c")],
               check=True, capture_output=True)


# --------------------------------------------------------------- l'outil
def outil(k, L, core, sats, cap=CAP, verbose=False):
    inp = f"{len(core)}\n" + "\n".join(" ".join(map(str, d)) for d in core) + "\n"
    inp += f"{len(sats)}\n" + "".join(f"{g} " + " ".join(map(str, d)) + "\n" for g, d in sats)
    t0 = time.time()
    p = subprocess.run([BIN, str(k), str(L), str(cap), THREADS] + (["-v"] if verbose else []),
                       input=inp, capture_output=True, text=True)
    res = {"sec": time.time() - t0, "etats": {}, "fin": {}, "debord": []}
    cur = None
    for line in p.stdout.split("\n"):
        if line.startswith("ETAT"):
            nok = int(line.split("satellites=")[1].split("/")[0])
            mots = tuple(int(x) for x in line.split("mots=")[1].split(","))
            cur = mots
            e = res["etats"].setdefault(mots, {"sat": 0, "n": 0, "debord": None})
            e["n"] += 1
            e["sat"] = max(e["sat"], nok)
        elif line.startswith("DEBORD") and cur is not None:
            items = [(int(x.split(":")[0]), int(x.split(":")[1])) for x in line.split()[2:]]
            if res["etats"][cur]["debord"] is None:
                res["etats"][cur]["debord"] = items
        elif line.startswith("FIN"):
            for kv in line.split()[1:]:
                a, b = kv.split("=")
                res["fin"][a] = int(b)
    res["nsat"] = len(sats)
    return res


# ------------------------------------------------------- le modèle planté
def flux(state, k, L, n):
    r = list(state)
    for _ in range(n):
        r.append((r[-k] + r[-L]) & 0xFFFFFFFF)
    return r[L:]


def tirages_rejet(words, nb, start=0):
    """nb tirages sous rejet à partir de words[start] : (numéros, positions)"""
    p, res = start, []
    for _ in range(nb):
        seen, order, pos = set(), [], []
        while len(order) < 20:
            v = (words[p] >> 1) % 80 + 1
            if v not in seen:
                seen.add(v)
                order.append(v)
                pos.append(p)
            p += 1
        res.append((order, pos))
    return res, p


def temoin(k, L, nd, gaps, rng):
    """plante un état, produit un jour de structure (nd, gaps) ; rend le noyau,
    les satellites, l'état bas vrai (les L mots avant le premier mot du noyau),
    les mots perdus par tirage, et les débordements vrais."""
    pre = max(0, -min(gaps + [0]))
    post = max(gaps + [nd - 1]) - nd + 1
    state = [rng.getrandbits(32) for _ in range(L)]
    n = (pre + nd + post) * (20 + 60) + 4 * L
    words = flux(state, k, L, n)
    allD, _ = tirages_rejet(words, pre + nd + post)
    p0 = allD[pre][1][0]                              # position du premier mot du noyau
    # l'état bas vrai : les L mots qui précèdent p0 (état initial si p0 < L)
    full = state + words
    truth = tuple(full[p0 + j] & 31 for j in range(L))   # full[p0 + L] est words[p0]
    core = [allD[pre + i][0] for i in range(nd)]
    sats = [(g, allD[pre + g][0]) for g in gaps]
    lost = [allD[pre + i][1][-1] - allD[pre + i][1][0] + 1 - 20 for i in range(nd)]
    lost += [allD[pre + g][1][-1] - allD[pre + g][1][0] + 1 - 20 for g in gaps]
    # débordements vrais aux positions relatives au noyau
    deb = {}
    for i in range(p0, p0 + 4 * (20 + CAP) * nd + L):
        s = full[i + L - k] + full[i + L - L]
        deb[i - p0] = 1 if s >= M32 else 0
    return core, sats, truth, lost, deb


def orbite(m, k, L, cap):
    """les états à au plus cap pas de m sur la même orbite (même flux bas).
    L'outil pose le premier numéro du noyau en position 0 ; si ce mot est suivi
    de son propre doublon (perdu), l'état « un pas plus tard » explique aussi
    tout — même flux, même prédiction : un FANTÔME DE DÉCALAGE, pas un faux."""
    out = {tuple(m)}
    r = list(m)
    for _ in range(cap):                               # en avant
        r.append((r[-k] + r[-L]) & 31)
        out.add(tuple(r[-L:]))
    r = list(m)
    for _ in range(cap):                               # en arrière : r_{p-L} = r_p - r_{p-k}
        r = [(r[L - 1] - r[L - 1 - k]) & 31] + r[:-1]
        out.add(tuple(r))
    return out


# --------------------------------------------------- la loi des mots perdus
def loi_perdus():
    """P(mots perdus dans un tirage = l) sous le rejet : somme de géométriques"""
    dist = {0: 1.0}
    for j in range(1, 20):                 # j numéros déjà sortis avant le (j+1)-ième
        pd = j / 80
        geo = [(1 - pd) * pd ** t for t in range(60)]
        new = {}
        for l, pl in dist.items():
            for t, pt in enumerate(geo):
                new[l + t] = new.get(l + t, 0.0) + pl * pt
        dist = new
    return dist


LOI = loi_perdus()
P_CAP = sum(p for l, p in LOI.items() if l <= CAP)
MOY = sum(l * p for l, p in LOI.items())
PLACEMENTS = sum(comb(19 + l, l) for l in range(CAP + 1))


# ==========================================================================
rule("1. L'INFORMATION CONTRE LES INCONNUES, CELLULE PAR CELLULE")
# ==========================================================================
say(f"""   Sous le rejet un tirage perd en moyenne {MOY:.2f} mots ; P(perdus <= {CAP}) = {P_CAP:.4f}
   par tirage. Les placements des perdus dans un tirage : {PLACEMENTS:,} ({CAP} au plus).

   INCONNUES : 5L bits d'état bas, plus log2(placements) par tirage.
   INFORMATION : chaque mot accepté publie son nibble, 4 bits — 80 bits par
   tirage ; un satellite à l'écart g en donne 80 moins l'entropie de son
   décalage (log2 des {CAP}|g|+1 positions de départ).
   FAUX POSITIFS : E[nombre d'hypothèses fausses compatibles]
                   = 2^(5L) x placements^ND x 16^(-20 ND)      (noyau seul)
                   x [ (cap|g|+1) x placements x 16^(-20) ]     par satellite
   Une cellule est DÉCISIVE si E < 1e-6 : au noyau seul, ou avec les
   satellites. Le calcul ne regarde pas les données.""")

CELLULES = []      # (type, k, L, jour, nd, gaps, décisif_noyau, décisif_sat, FP_noyau, FP_sat)
say(f"\n   {'type':7s} {'jour':4s} {'ND':>2s} {'NS':>2s} {'inconnues':>10s} {'info noyau':>10s} "
    f"{'info sat.':>9s} {'FP noyau':>10s} {'FP + sat.':>10s}  décisif")
for tn, k, L in TYPES:
    for jn, ids, sat in JOURS:
        nd, gaps = len(ids), [g for g, _ in sat]
        unk = 5 * L + nd * log2(PLACEMENTS)
        info = 80 * nd
        info_s = sum(80 - log2(CAP * abs(g) + 1) - log2(PLACEMENTS) for g in gaps)
        fp_core = 2 ** (5 * L) * PLACEMENTS ** nd * 16.0 ** (-20 * nd)
        fp_sat = fp_core
        for g in gaps:
            fp_sat *= (CAP * abs(g) + 1) * PLACEMENTS * 16.0 ** (-20)
        dc, ds = fp_core < 1e-6, fp_sat < 1e-6
        # TYPE_3 à deux tirages : hors calcul (noyau du plan 0 ~2^20 par alignement)
        calc = not (tn == "TYPE_3" and nd < 3)
        lab_ = ("noyau seul" if dc else "avec satellites" if ds else "NON") if calc else "NON (calcul)"
        CELLULES.append((tn, k, L, jn, nd, gaps, dc and calc, ds and calc, fp_core, fp_sat))
        say(f"   {tn:7s} {jn:4s} {nd:2d} {len(gaps):2d} {unk:10.1f} {info:10d} {info_s:9.1f} "
            f"{fp_core:10.1e} {fp_sat:10.1e}  {lab_}")
DECISIVES = [c for c in CELLULES if c[7]]
say(f"\n   cellules décisives : {len(DECISIVES)} sur {len(CELLULES)}")
say("   TYPE_4 (k=1, L=63 : r_i = r_{i-1} + r_{i-63}) : 315 bits bas, "
    "~11 tirages consécutifs nécessaires — aucun jour ne les a.")


# ==========================================================================
rule(f"2. LES TÉMOINS PLANTÉS — {NTEM} par cellule décisive, dans la structure du jour")
# ==========================================================================
say(f"""   Pour chaque cellule décisive, {NTEM} états aléatoires de L mots de 32 bits
   engendrent le jour (noyau + satellites aux mêmes écarts) sous le rejet ;
   l'outil, aveugle à l'état, doit le retrouver. COUVERT : tous les tirages
   du jour ont <= {CAP} perdus (sinon l'outil ne peut pas, par construction).
   FAUX : un état passant noyau ET satellites HORS de l'orbite du vrai.
   FANTÔMES : états passant tout, sur l'orbite du vrai à |j| <= {CAP} pas — même
   flux, même prédiction ; ils naissent quand le premier mot du noyau est
   suivi de son propre doublon (l'outil ne peut pas savoir lequel des deux
   est « la position 0 »).
   DÉBORDEMENTS : bits de débordement lus contre les vrais (§7.7).""")
rng = random.Random(GRAINE)
TEMOINS = {}
say(f"\n   {'type':7s} {'jour':4s} {'couverts':>8s} {'retrouvés':>9s} {'faux':>5s} {'fantômes':>8s} "
    f"{'noyau seul':>12s} {'débord.':>9s} {'sec/max':>9s}")
for tn, k, L, jn, nd, gaps, dc, ds, _, _ in CELLULES:
    if not ds:
        continue
    cov = ret = faux = fant = 0
    core_only = []
    deb_ok = deb_n = 0
    tmax = 0.0
    for t in range(NTEM):
        core, sats, truth, lost, deb = temoin(k, L, nd, gaps, rng)
        covered = max(lost) <= CAP
        res = outil(k, L, core, sats)
        tmax = max(tmax, res["sec"])
        good = [m for m, e in res["etats"].items() if e["sat"] == res["nsat"]]
        core_only.append(len(res["etats"]))
        orb = orbite(truth, k, L, CAP)
        vrais = [m for m in good if m in orb]
        if covered:
            cov += 1
            if vrais:
                ret += 1
                fant += len(vrais) - 1
                if truth in res["etats"]:
                    d = res["etats"][truth]["debord"] or []
                    deb_n += len(d)
                    deb_ok += sum(1 for p, w in d if deb.get(p) == w)
            faux += sum(1 for m in good if m not in orb)
        elif vrais:
            ret += 1          # retrouvé malgré un tirage hors cap (perdus > cap sur un satellite)
    TEMOINS[(tn, jn)] = (cov, ret, faux, core_only, deb_ok, deb_n, tmax, fant)
    co = f"{min(core_only)}..{max(core_only)}"
    say(f"   {tn:7s} {jn:4s} {cov:8d} {ret:9d} {faux:5d} {fant:8d} {co:>12s} {deb_ok:4d}/{deb_n:<4d} {tmax:8.1f}")
say("""
   « noyau seul » : états compatibles avec le noyau avant les satellites —
   pour TYPE_3 à quatre tirages ils sont plusieurs, le satellite tranche.""")
TEM_OK = all(v[1] >= v[0] and v[2] == 0 for v in TEMOINS.values())
say(f"   témoins : {'tous retrouvés, aucun faux' if TEM_OK else 'DÉFAUT'}")


# ==========================================================================
rule("3. LES VIDÉOS")
# ==========================================================================
ORD = {}
with open(os.path.join(DEPOT, "lab", "draws_ordered.csv")) as f:
    for row in csv.DictReader(f):
        ORD[int(row["id"])] = [int(row[f"o{i}"]) for i in range(1, 21)]
RESULT = {}
TOTAL = 0          # la statistique : états compatibles (noyau + satellites) sur les cellules décisives
TOTAL_NOYAU = 0
for tn, k, L, jn, nd, gaps, dc, ds, fpc, fps in CELLULES:
    if not ds:
        continue
    ids, sat = next((i, s) for j, i, s in JOURS if j == jn)
    core = [ORD[i] for i in ids]
    sats = [(g, ORD[i]) for g, i in sat]
    res = outil(k, L, core, sats)
    fin = res["fin"]
    good = [m for m, e in res["etats"].items() if e["sat"] == res["nsat"]]
    RESULT[(tn, jn)] = (len(res["etats"]), len(good), res["sec"], fin)
    TOTAL += len(good)
    TOTAL_NOYAU += len(res["etats"]) if dc else 0
    say(f"   {tn} jour {jn} : alignements {fin.get('alignements', 0):,}, plan 0 {fin.get('plan0', 0):,}, "
        f"états noyau {len(res['etats'])}, noyau + satellites {len(good)}, "
        f"noyaux abandonnés {fin.get('noyaux_abandonnes', 0)}, {res['sec']:.1f} s")
    for m in good:
        say(f"      ÉTAT TROUVÉ : {','.join(map(str, m))}")
        # prédiction falsifiable : les classes (v-1) mod 16 des 24 mots qui suivent le noyau
        r = list(m)                        # le flux bas est autonome : on le prolonge
        for _ in range(4 * (20 + CAP) + 24):
            r.append((r[-k] + r[-L]) & 31)
        say(f"      flux bas après l'état (nibbles des {4 * (20 + CAP) + 24} mots suivants) : "
            + " ".join(str((x >> 1) & 15) for x in r[L:]))
say(f"\n   STATISTIQUE : {TOTAL} état(s) compatible(s) noyau + satellites sur {len(DECISIVES)} cellules "
    f"décisives ; {TOTAL_NOYAU} au noyau seul sur les cellules décisives au noyau seul.")


# ==========================================================================
rule("4. CONSIGNATION")
# ==========================================================================
if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    cells = "; ".join(f"{t} jour {j}" for t, _, _, j, *_ in DECISIVES)
    tok = lab.preregister(
        "h133.lfg_rejet_ordonne",
        "Aucun etat bas (les 5L bits bas des L mots, quotient autonome mod 32) "
        "d'un Fibonacci retarde additif r_i = r_{i-k} + r_{i-L} mod 2^32 aux "
        "retards de glibc random() — TYPE_1 (3, 7), TYPE_2 (1, 15), TYPE_3 (3, 31) "
        "— echantillonne par v = (r >> 1) mod 80 + 1 avec rejet des doublons "
        f"(au plus {CAP} mots perdus par tirage), l'etat etant LIBRE, ne reproduit "
        "les tirages ordonnes consecutifs des videos et les satellites du meme "
        f"jour, sur les cellules decisives ({cells}). Decisif : E[faux positifs] "
        "< 1e-6 par le compte information/inconnues, calcule sans regarder les "
        "donnees, et temoin plante retrouve dans la meme structure. TYPE_4 (315 "
        "bits) et TYPE_3 a deux tirages (noyau du plan 0 ~2^20 par alignement) "
        "sont hors de portee et exclus AVANT cette consignation. L'attaque : "
        "alignement des perdus par les coherences (q_i - q_{i-k} - q_{i-L}) mod "
        "16 in {0,1}, plan 0 par les retenues (Gauss sur GF(2) + NON-ET), "
        "nibbles par relevement de Hensel, verification par le bit de "
        "debordement mod 5 et rejeu des satellites",
        "nombre d'etats bas compatibles avec le noyau ET tous les satellites, "
        "somme sur les cellules decisives",
        "aucun null n'est requis : E[faux positifs] par cellule = 2^(5L) x "
        "placements^ND x 16^(-20 ND) x prod_satellites((cap|g|+1) x placements "
        f"x 16^(-20)), au plus {max(c[9] for c in DECISIVES):.1e} sur les cellules retenues",
        "conforme si aucun etat n'est compatible", track="B")
    tok["m_extra"] = 0
    tem = "; ".join(f"{t} jour {j}: {v[1]}/{v[0]} retrouves, {v[2]} faux, {v[7]} fantomes de decalage "
                    f"(meme orbite), debordements {v[4]}/{v[5]}"
                    for (t, j), v in TEMOINS.items())
    lab.record(
        tok, float(TOTAL), p=1.0,
        verdict="conforme" if TOTAL == 0 else "ETAT TROUVE",
        power_at=(f"temoins plantes ({NTEM} par cellule, graine {GRAINE}) : {tem} — "
                  + (f"un etat couvert (perdus <= {CAP} partout) est toujours retrouve (a un fantome "
                     f"de decalage pres : meme orbite, meme flux), aucun etat hors orbite"
                     if TEM_OK else "DEFAUT DE PUISSANCE : un temoin couvert manque ou un faux etat passe")
                  + f" ; bits de debordement exacts {sum(v[4] for v in TEMOINS.values())}"
                  f"/{sum(v[5] for v in TEMOINS.values())}"),
        notes=(f"LE FIBONACCI RETARDE SOUS LE REJET, ETAT LIBRE — le cas que le §103 "
               f"laissait (« l'alignement des lags se perd »). Cellules decisives : "
               f"{cells}. Resultats : " + "; ".join(
                   f"{t} {j}: {v[0]} etats noyau, {v[1]} noyau+satellites, {v[2]:.1f} s"
                   for (t, j), v in RESULT.items())
               + f". P(perdus <= {CAP}) = {P_CAP:.4f} par tirage. Aucune validation sur "
               f"l'archive (elle s'arrete avant les videos)."))
    say(f"   Enregistré : h133.lfg_rejet_ordonne, statistique {TOTAL}, verdict "
        f"{'conforme' if TOTAL == 0 else 'ETAT TROUVE'}")

say(f"\n   durée totale : {time.time() - T0:.0f} s")
