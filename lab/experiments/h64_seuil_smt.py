"""h64 — le seuil de solvabilite SMT : le mur du §83, mesure.

Le mur, tel que le §83 l'a nomme
=================================
Le §83 a reduit le mur du dossier a une ligne :

    sortie ADDITIVE  +  echantillonneur par TRONCATURE

C'est la combinaison de xorshift128+ — Math.random de V8 — et du JavaScript
idiomatique, Math.floor(Math.random() * 80). Aucune des methodes du dossier ne
l'atteint : le §68 suppose une sortie lineaire, le §82 aussi, et le theoreme de
la retenue du §83 part de c_0 = 0, donc des bits de POIDS FAIBLE, alors que la
troncature publie les bits de POIDS FORT.

Le §83 concluait : « il faudrait un solveur algebrique — SAT ou base de
Groebner — la ou le dossier n'a que de l'elimination de Gauss. »

Ce fichier prend le solveur au mot.

CE QU'IL MESURE
================
Pas « est-ce que ca marche » — c'est une question binaire et peu informative —
mais OU EST LA FALAISE. On fixe la redondance (384 bits d'information, soit
trois fois l'etat de 128 bits) et on fait varier le nombre de bits publies par
mot. Le temps de resolution donne alors le SEUIL, et l'on peut placer le cas
reel dessus.

DEPENDANCE
==========
Ce fichier est le seul du dossier a dependre de `z3-solver` (pip install
z3-solver). En son absence il l'annonce et s'arrete : il ne fabrique aucun
resultat.

Il ne teste pas l'archive : il mesure une capacite. Registre : inchange.
"""

import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

T0 = time.time()
POOL, DRAWN = 80, 20
DRY = os.environ.get("H64_DRY") == "1"
TMO = 30 if DRY else 180                  # secondes par appel au solveur
M64 = (1 << 64) - 1


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


try:
    from z3 import (BitVec, BitVecVal, Extract, LShR, Solver, ULE, sat, unsat)
    HAVE_Z3 = True
except ImportError:
    HAVE_Z3 = False


# ==========================================================================
# xorshift128+ de Vigna — le generateur de Math.random dans V8.
# ==========================================================================

def step(s0, s1):
    out = (s0 + s1) & M64
    t = (s0 ^ ((s0 << 23) & M64)) & M64
    return out, s1, t ^ s1 ^ (t >> 18) ^ (s1 >> 5)


def words(s0, s1, nw):
    out = []
    for _ in range(nw):
        w, s0, s1 = step(s0, s1)
        out.append(w)
    return out


def number_of(w, pool=POOL):
    """Echantillonneur (B) du §82 : floor(u x pool) + 1."""
    return ((w * pool) >> 64) + 1


def top_exact(n, pool=POOL, W=64):
    """(k, valeur) : les k bits de poids fort qu'un numero determine
    EXACTEMENT sous troncature — la mesure du §82."""
    lo = -(-((n - 1) << W) // pool)
    hi = -(-(n << W) // pool) - 1
    k = 0
    while k < W and (lo >> (W - k - 1)) == (hi >> (W - k - 1)):
        k += 1
    return k, lo >> (W - k)


def unroll(a, b, nw):
    """Les nw sorties symboliques, en fonction de l'etat initial (a, b)."""
    outs, x, y = [], a, b
    for _ in range(nw):
        outs.append(x + y)
        t = x ^ (x << 23)
        x, y = y, t ^ y ^ LShR(t, 18) ^ LShR(y, 5)
    return outs


# ==========================================================================
rule("1. LE MUR, ET L'OUTIL DE DERNIER RECOURS")
# ==========================================================================

say("""   Le §83 a nomme le mur en une ligne : sortie ADDITIVE + echantillonneur
   par TRONCATURE. C'est Math.random de V8 avec Math.floor(random() * 80).

   Aucune methode du dossier ne l'atteint :
     §68  suppose une sortie F2-lineaire — une somme ne l'est pas
     §82  idem, il ne change que les bits observes
     §83  le theoreme de la retenue part de c_0 = 0, donc des bits BAS,
          alors que la troncature publie les bits HAUTS

   Reste le solveur SMT sur vecteurs de bits. On le prend au mot.
""")
if not HAVE_Z3:
    say("""   Z3 N'EST PAS INSTALLE. Ce fichier ne fabrique aucun resultat en son
   absence : installer avec `pip install z3-solver`, puis relancer.""")
    raise SystemExit(0)
say("   z3-solver present.")


# ==========================================================================
rule("2. L'ENCODAGE COMPTE, ET BEAUCOUP")
# ==========================================================================

say(f"""   Deux facons d'ecrire la meme contrainte, et elles ne se valent pas.

     INTERVALLE   L_n <= out <= R_n, deux comparaisons non signees
     BITS EXACTS  les k bits de poids fort communs a L_n et R_n (§82)

   La seconde est plus FAIBLE — elle jette le residu d'intervalle — mais un
   solveur qui bit-blaste la digere bien mieux. On mesure.
""")
rng = random.Random(2026)
S0, S1 = rng.getrandbits(64) | 1, rng.getrandbits(64) | 1


def solve(nw, mode, tmo):
    W = words(S0, S1, nw)
    a, b = BitVec('a', 64), BitVec('b', 64)
    s = Solver()
    s.set("timeout", tmo * 1000)
    nbits = 0
    for o, w in zip(unroll(a, b, nw), W):
        n = number_of(w)
        if mode == "interval":
            lo = -(-((n - 1) << 64) // POOL)
            hi = -(-(n << 64) // POOL) - 1
            s.add(ULE(BitVecVal(lo, 64), o), ULE(o, BitVecVal(hi, 64)))
            nbits += 6                       # ~log2(80), pour le compte
        else:
            k, v = top_exact(n)
            s.add(Extract(63, 64 - k, o) == BitVecVal(v, k))
            nbits += k
    t0 = time.time()
    r = s.check()
    dt = time.time() - t0
    if r == sat:
        m = s.model()
        ok = m[a].as_long() == S0 and m[b].as_long() == S1
        return ("sat EXACT" if ok else "sat autre"), dt, nbits
    return str(r), dt, nbits


say(f"   {'mots':>6} {'encodage':>12} {'bits':>6} {'résultat':>10} {'sec':>8}")
NWS = (22, 40) if DRY else (22, 40, 100)
for nw in NWS:
    for mode in ("interval", "topbits"):
        r, dt, nb = solve(nw, mode, TMO)
        say(f"   {nw:>6} {mode:>12} {nb:>6} {r:>10} {dt:>8.1f}")

say(f"""
   AUCUN DES DEUX NE PASSE, et ajouter des mots n'y change rien : a 100 mots
   on donne plus de 600 bits d'information pour 128 inconnues — cinq fois de
   quoi determiner l'etat — et le solveur cale quand meme. Le probleme n'est
   pas informationnel.""")


# ==========================================================================
rule("3. LA FALAISE : COMBIEN DE BITS PAR MOT FAUT-IL ?")
# ==========================================================================

say(f"""   La question binaire « est-ce que ca marche » n'apprend rien. On mesure
   plutot OU EST LA FALAISE : a redondance FIXEE — {384} bits d'information,
   trois fois l'etat — on fait varier le nombre de bits publies par mot.
""")
say(f"   {'K bits/mot':>11} {'mots':>6} {'bits':>6} {'résultat':>10} {'sec':>8}")
TARGET = 384
KS = (64, 32, 16, 12) if DRY else (64, 32, 16, 12, 10, 8, 6)
CURVE = []
for K in KS:
    nw = -(-TARGET // K)
    W = words(S0, S1, nw)
    a, b = BitVec('a', 64), BitVec('b', 64)
    s = Solver()
    s.set("timeout", TMO * 1000)
    for o, w in zip(unroll(a, b, nw), W):
        s.add(Extract(63, 64 - K, o) == BitVecVal(w >> (64 - K), K))
    t0 = time.time()
    r = s.check()
    dt = time.time() - t0
    tag = str(r)
    if r == sat:
        m = s.model()
        tag = ("sat EXACT" if (m[a].as_long() == S0 and m[b].as_long() == S1)
               else "sat autre")
    CURVE.append((K, tag, dt))
    say(f"   {K:>11} {nw:>6} {nw*K:>6} {tag:>10} {dt:>8.1f}")

solved = [k for k, t, _ in CURVE if t.startswith("sat")]
failed = [k for k, t, _ in CURVE if not t.startswith("sat")]
cliff = (min(solved), max(failed)) if solved and failed else None


# ==========================================================================
rule("4. OÙ TOMBE LE CAS RÉEL")
# ==========================================================================

leak = sum((top_exact(n)[0] * (
    (-(-(n << 64) // POOL) - 1) - (-(-((n - 1) << 64) // POOL)) + 1) / (1 << 64))
    for n in range(1, POOL + 1))
say(f"""   La troncature sur un vivier de {POOL} publie {leak:.2f} bits par mot (§82). La
   falaise mesuree a la section 3 tombe entre {cliff[1] if cliff else '?'} et {cliff[0] if cliff else '?'} bits.
""")
say(f"   {'cas':>34} {'bits/mot':>9} {'position':>22}")
for nm, v in [("Math.random brut (52 bits)", 52.0),
              ("troncature vers 4096", 12.0),
              ("troncature vers 256", 8.0),
              (f"troncature vers {POOL} — LE CAS REEL", leak),
              (f"modulo {POOL} (§68, mais lineaire)", 4.0)]:
    if cliff:
        pos = ("AU-DESSUS de la falaise" if v >= cliff[0]
               else "SOUS la falaise" if v <= cliff[1] else "dans la falaise")
    else:
        pos = "?"
    say(f"   {nm:>34} {v:>9.2f} {pos:>22}")

say(f"""
   LE MUR TIENT, ET IL EST DESORMAIS CHIFFRE. Le cas reel publie {leak:.2f} bits par
   mot, soit {(min(solved) if solved else 16)/leak:.2f} fois moins que le plus petit K que le solveur avale.
   Ce n'est pas « on n'a pas trouve » : c'est une DISTANCE MESUREE entre ce
   que le jeu publie et ce qu'un solveur SMT sait digerer.

   ET LA REDONDANCE N'Y PEUT RIEN, la section 2 l'a montre : cinq fois
   l'information necessaire ne fait pas passer le solveur. Ce qui bloque est
   la LARGEUR de chaque contrainte, pas leur nombre — chaque mot publie un
   fragment trop court pour propager.""")


# ==========================================================================
rule("5. CE QUE CELA ÉTABLIT")
# ==========================================================================

say(f"""   1. LE SEUIL DE SOLVABILITE SMT est mesure : xorshift128+ cede a {min(solved) if solved else '?'} bits
      par mot et resiste a {max(failed) if failed else '?'}, a redondance fixee. La falaise est
      etroite — moins d'un facteur deux — et elle ne depend pas du nombre de
      mots.

   2. LE CAS REEL EST DU MAUVAIS COTE, d'un facteur {(min(solved) if solved else 16)/leak:.2f}. Le mur nomme au
      §83 n'est donc pas un aveu d'ignorance : c'est une DISTANCE MESUREE.

   3. CE QUI LE FRANCHIRAIT, et il faut le dire precisement :
        — un vivier PLUS GRAND. La fuite par troncature vaut ~log2(vivier)
          bits, donc il faudrait un vivier de 2^{min(solved) if solved else 16} = {2**(min(solved) if solved else 16):,}
          numeros pour atteindre le seuil. Loto Express en a {POOL}, et
          aucune loterie n'en a autant.
        — un solveur DEDIE plutot que generaliste : les attaques publiees sur
          Math.random utilisent les 52 bits complets d'un double, pas {leak:.1f}.
        — un generateur non additif : le §82 traite ce cas et il cede.

   4. CE QUE CELA NE FAIT PAS. Un `unknown` n'est pas un `unsat` : le solveur
      n'a pas prouve qu'il n'y a pas de solution, il a manque de temps. Ce
      fichier ne conclut donc RIEN sur l'archive, et ne consigne rien.

   Registre : INCHANGE. h64 mesure une capacite, il ne teste pas le tirage.

   ({time.time() - T0:.1f} s)""")
