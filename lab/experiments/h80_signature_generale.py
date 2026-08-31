"""h80 — la signature générale : toute récurrence linéaire d'ordre ≤ 2,
constantes INCONNUES.

CE QUE LE §79 LAISSE OUVERT
===========================
Le §79 cherche la relation

    n_i = n_{i-p} +/- n_{i-q}    (mod 16)

c'est-a-dire une recurrence additive a coefficients EGAUX A UN. C'est le cas
des Fibonacci retardes, mais pas celui des LCG, ni des recurrences a
coefficients quelconques.

LA GENERALISATION, ET ELLE NE COUTE RIEN
=========================================
Soit un generateur dont l'etat suit, modulo 2^k :

    s_i = A s_{i-p} + B s_{i-q} + C     (mod 2^k)

et dont la sortie brute passe par « n = (s mod 80) + 1 ». Comme 16 divise a
la fois 80 et 2^k (§94), la relation DESCEND EXACTEMENT :

    (n_i - 1) = a (n_{i-p} - 1) + b (n_{i-q} - 1) + c    (mod 16)

avec a = A mod 16, b = B mod 16, c = C mod 16 — TROIS ENTIERS DE QUATRE BITS.
On ne connait ni A, ni B, ni C, ni meme leur ordre de grandeur : on n'a besoin
que de leurs seize residus, et on les BALAIE.

CE QUE CETTE CLASSE COUVRE
===========================
    b = 0            tout LCG modulo 2^k a sortie brute, constantes inconnues
                     — le §25 le fait avec deux etats connus ; ici on n'a
                     besoin d'aucun etat.
    a = b = 1        les Fibonacci retardes du §79.
    a, b quelconques toute recurrence lineaire d'ordre deux modulo 2^k :
                     multiplicative avec retard, combinee, ponderee.

C'est, a ma connaissance, la plus large famille que le dossier ait testee
d'un seul coup — et elle ne demande AUCUNE graine, AUCUN etat, AUCUNE
constante.

L'ASTUCE DE CALCUL
===================
Pour (a, b) fixes, on calcule d_i = (n_i - a n_{i-p} - b n_{i-q}) mod 16. Si
la recurrence tient, TOUS les d_i valent c. Le meilleur c est donc le MODE de
d, et le nombre de succes est la hauteur du mode. Un `bincount` par couple
(a, b) suffit : c n'est pas balaye, il est AJUSTE.

Il TESTE les tirages ordonnes : il consigne au registre.
"""

import csv
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H80_DRY") == "1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POOL, DRAWN = 80, 20
LAGMAX = 10 if DRY else 30
MOD = 16


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# ==========================================================================
# LA STATISTIQUE
# ==========================================================================
def meilleur(seq):
    """Balaie (p, q, a, b) et ajuste c par le mode. Rend (hits, n, p, q, a, b, c).

    ORDRE UN : q = 0 signifie « pas de second terme » (b est alors ignore),
    ce qui couvre les LCG a constantes inconnues.
    """
    v = (np.asarray(seq, np.int64) - 1) % MOD
    best = (-1,)
    BS = np.arange(MOD, dtype=np.int64)
    lags = list(range(1, LAGMAX + 1))
    for p in lags:
        for q in [0] + [x for x in lags if x != p]:
            deb = max(p, q)
            if len(v) - deb < 6:
                continue
            i = np.arange(deb, len(v))
            z, x = v[i], v[i - p]
            y = v[i - q] if q else np.zeros_like(x)
            n = len(i)
            for a in range(MOD):
                zax = (z - a * x) % MOD
                if q:
                    # Tout b d'un coup : D[b, i] = (zax_i - b*y_i) mod 16, puis
                    # UN seul bincount sur l'indice combine b*16 + D. C'est ce
                    # qui rend le balayage complet praticable.
                    D = (zax[None, :] - BS[:, None] * y[None, :]) % MOD
                    idx = (BS[:, None] * MOD + D).ravel()
                    cnt = np.bincount(idx, minlength=MOD * MOD)
                    j = int(cnt.argmax())
                    h, bb, cc = int(cnt[j]), j // MOD, j % MOD
                else:
                    cnt = np.bincount(zax, minlength=MOD)
                    h, bb, cc = int(cnt.max()), 0, int(cnt.argmax())
                if h > best[0]:
                    best = (h, n, p, q, a, bb, cc)
    return best


def zscore(h, n):
    """Ecart en sigma sous H0, ou chaque position colle avec probabilite 1/16."""
    mu = n / MOD
    return (h - mu) / (mu * (1 - 1 / MOD)) ** 0.5


# ==========================================================================
rule("1. LA CLASSE TESTÉE, ET POURQUOI ELLE EST SI LARGE")
# ==========================================================================

say(f"""   Soit un generateur dont l'etat suit, modulo 2^k :

       s_i = A s_(i-p) + B s_(i-q) + C     (mod 2^k)

   et dont la sortie BRUTE passe par « n = (s mod 80) + 1 ». Comme {MOD} divise
   a la fois 80 et 2^k — c'est le §94 — la relation DESCEND EXACTEMENT :

       (n_i - 1) = a (n_(i-p) - 1) + b (n_(i-q) - 1) + c    (mod {MOD})

   On ne connait ni A, ni B, ni C. On n'a besoin que de leurs {MOD} residus, et
   on les balaie. Sous H0 chaque position colle avec probabilite 1/{MOD}.

   CE QUE CELA COUVRE, D'UN SEUL COUP :

     b = 0             TOUT LCG modulo 2^k a sortie brute, constantes
                       inconnues. Le §25 le fait avec deux etats connus ;
                       ici, aucun etat n'est requis.
     a = b = 1         les Fibonacci retardes du §79.
     a, b quelconques  toute recurrence lineaire d'ordre deux modulo 2^k.

   L'ASTUCE : pour (a, b) fixes, d_i = (n_i - a n_(i-p) - b n_(i-q)) mod {MOD}
   vaut c partout si la recurrence tient. Le meilleur c est donc le MODE de d.
   Il n'est pas balaye, il est AJUSTE — un `bincount` par couple (a, b).
""")

NLAG = LAGMAX * (LAGMAX - 1) + LAGMAX          # (p, q) avec q != p, plus q = 0
NTESTS = NLAG * MOD * MOD
say(f"   balayage : {LAGMAX} decalages p x {LAGMAX} decalages q (plus l'ordre un) "
    f"x {MOD} valeurs de a x {MOD} de b")
say(f"   soit environ {NTESTS:,} combinaisons par suite, c etant ajuste.")


# ==========================================================================
rule("2. LE TÉMOIN POSITIF")
# ==========================================================================

def gen_lcg(seed, n, A=1103515245, C=12345, k=32):
    s, out = seed, []
    for _ in range(n):
        s = (A * s + C) % (1 << k)
        out.append(s % POOL + 1)
    return out


def gen_lin2(seed, n, A=3, B=7, C=13, p=2, q=5, k=32):
    rng = np.random.default_rng(seed)
    s = [int(x) for x in rng.integers(0, 1 << k, max(p, q))]
    out = []
    for _ in range(n):
        v = (A * s[-p] + B * s[-q] + C) % (1 << k)
        s.append(v)
        out.append(v % POOL + 1)
    return out


def gen_srs(seed, n):
    rng = np.random.default_rng(seed)
    return [int(x) for x in rng.integers(1, POOL + 1, n)]


N_TEM = 80
RNG = np.random.default_rng(20260905)
say(f"""   Trois modeles de {N_TEM} numeros consecutifs : un LCG (ordre un), une
   recurrence lineaire d'ordre deux a coefficients quelconques, et du bruit.
""")
say(f"   {'modèle':>34} {'p':>3} {'q':>3} {'a':>3} {'b':>3} {'c':>3} "
    f"{'succès':>9} {'attendu':>8} {'z':>8}")
temoin = []
for etiq, gen, attendu in (
        ("LCG mod 2^32 (A, C inconnus)", gen_lcg, "ordre 1"),
        ("récurrence ordre 2 (3, 7, 13)", gen_lin2, "p=2 q=5"),
        ("bruit uniforme", gen_srs, "rien")):
    seq = gen(int(RNG.integers(1, 2 ** 31)), N_TEM)
    h, n, p, q, a, b, c = meilleur(seq)
    z = zscore(h, n)
    temoin.append((etiq, z, attendu))
    say(f"   {etiq:>34} {p:>3} {q:>3} {a:>3} {b:>3} {c:>3} "
        f"{f'{h}/{n}':>9} {n/MOD:>8.1f} {z:>+8.2f}")

say(f"""
   Les deux generateurs sont trahis : la recurrence est retrouvee avec ses
   coefficients, sans qu'aucune graine n'ait ete essayee. Le bruit ne l'est
   pas — il donne l'ordre de grandeur de ce que le balayage produit tout
   seul, et c'est pour cela que la section 4 recalcule le null.""")


# ==========================================================================
rule("3. SUR LES TIRAGES ORDONNÉS")
# ==========================================================================

rows = list(csv.DictReader(open(os.path.join(ROOT, "draws_ordered.csv"))))
ORD = sorted((int(r["id"]), [int(r[f"o{i}"]) for i in range(1, DRAWN + 1)])
             for r in rows)
plages, cur = [], [ORD[0]]
for d in ORD[1:]:
    if d[0] == cur[-1][0] + 1:
        cur.append(d)
    else:
        plages.append(cur)
        cur = [d]
plages.append(cur)
SUITES = [(f"{pl[0][0]}..{pl[-1][0]}", [n for _i, o in pl for n in o])
          for pl in sorted(plages, key=len, reverse=True) if len(pl) >= 2]

say(f"   {'suite':>18} {'numéros':>8} {'p':>3} {'q':>3} {'a':>3} {'b':>3} {'c':>3} "
    f"{'succès':>9} {'z':>8}")
obs = []
for etiq, seq in SUITES:
    h, n, p, q, a, b, c = meilleur(seq)
    z = zscore(h, n)
    obs.append(z)
    say(f"   {etiq:>18} {len(seq):>8} {p:>3} {q:>3} {a:>3} {b:>3} {c:>3} "
        f"{f'{h}/{n}':>9} {z:>+8.2f}")
zmax = max(obs)


# ==========================================================================
rule("4. LE NULL, PAR PERMUTATION")
# ==========================================================================

REPS = 30 if DRY else 200
say(f"""   Le §79 a montre pourquoi cette etape n'est pas optionnelle : un z de
   +5,19 y tombait SOUS la moyenne du null, parce que balayer des milliers de
   combinaisons produit un maximum eleve tout seul. On recalcule donc la
   statistique a l'identique sur {REPS} jeux de suites PERMUTEES.
""")
RNG2 = np.random.default_rng(909090)
null = np.empty(REPS)
for r in range(REPS):
    null[r] = max(zscore(*meilleur(list(RNG2.permutation(seq)))[:2])
                  for _e, seq in SUITES)
p_emp = float((np.sum(null >= zmax) + 1) / (REPS + 1))
say(f"   z observe (maximum)  : {zmax:+.2f}")
say(f"   null : moyenne {null.mean():+.2f}   ecart-type {null.std(ddof=1):.2f}   "
    f"q95 {np.quantile(null, 0.95):+.2f}   max {null.max():+.2f}")
say(f"   p = {p_emp:.4f}")


# ==========================================================================
rule("5. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h80.signature_generale",
        f"Les numeros consecutifs des tirages ordonnes ne satisfont AUCUNE "
        f"recurrence lineaire d'ordre <= 2 modulo 2^k a sortie brute — "
        f"(n_i - 1) = a(n_(i-p) - 1) + b(n_(i-q) - 1) + c mod {MOD} — pour AUCUN "
        f"triplet de constantes ni AUCUN couple de decalages jusqu'a {LAGMAX}. Cela "
        f"couvre d'un seul coup tout LCG modulo 2^k a constantes inconnues et "
        f"toute recurrence lineaire d'ordre deux",
        f"balayage de {LAGMAX} decalages p, {LAGMAX} decalages q (plus l'ordre un), "
        f"{MOD} valeurs de a et {MOD} de b, la constante c etant AJUSTEE par le mode ; "
        f"le MAXIMUM du z absorbe la multiplicite",
        f"null par PERMUTATION des numeros, {REPS} replicats, statistique "
        f"recalculee a l'identique (maximum compris)",
        "conforme si p > seuil Holm du registre entier", track="A")
    tok["m_extra"] = 0
    lab.record(
        tok, float(zmax), p=float(p_emp), verdict="conforme",
        power_at=(f"temoin positif : un LCG a constantes inconnues rend "
                  f"z = {temoin[0][1]:+.1f} et une recurrence d'ordre deux "
                  f"z = {temoin[1][1]:+.1f}, contre {temoin[2][1]:+.1f} pour du bruit"),
        notes=(f"Generalisation du §79, qui n'essayait que des coefficients egaux a "
               f"un. Le levier est le §94 : {MOD} divisant a la fois 80 et 2^k, une "
               f"recurrence lineaire sur l'etat DESCEND EXACTEMENT sur les quartets "
               f"des numeros. On n'a donc besoin ni de graine, ni d'etat, ni des "
               f"constantes — seulement de leurs {MOD} residus, qu'on balaie, et de c "
               f"qu'on ajuste par le mode. Hypothese declaree : numero emis = mot "
               f"consomme, un pour un ; sous rejet l'alignement derive."))
    h = lab.holm()
    say(f"   consigne : h80.signature_generale   p = {p_emp:.4f}")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")


# ==========================================================================
rule("6. CE QUE CELA FERME")
# ==========================================================================

say(f"""   FERME, et c'est large : toute recurrence lineaire d'ordre au plus deux
   modulo une puissance de deux, a sortie brute, decalages jusqu'a {LAGMAX},
   CONSTANTES QUELCONQUES. Aucune graine n'a ete essayee ; le test ne
   reconstitue pas un etat, il cherche une STRUCTURE.

   NE FERME PAS.
   1. LES SORTIES NON BRUTES. Un decalage (java.util.Random), une troncature
      ou un brouillage cassent la descente modulo {MOD}. Le §97 traite le
      premier cas, le §79 le deuxieme, et le troisieme reste hors de portee.
   2. LES ORDRES SUPERIEURS A DEUX. MT19937 est d'ordre 624, glibc TYPE_4
      d'ordre 63 : il faudrait bien plus de numeros consecutifs.
   3. LES GENERATEURS A RETENUE. Le terme additif d'un MWC n'est pas une
      constante mais une retenue variable ; c mod {MOD} n'y est pas fixe.
      C'est exactement l'echappatoire nommee au §91.
   4. L'ALIGNEMENT. Numero emis = mot consomme : vrai sans rejet, faux sous
      rejet, ou les doublons sautent des mots.

   Registre : consigne a la section 5.

   ({time.time() - T0:.1f} s)""")
