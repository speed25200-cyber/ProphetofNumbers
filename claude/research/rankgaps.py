"""Combien de bits l'opérateur émet-il réellement par tirage ?  (test sans modèle de RNG)

C(80,20) = 3.535e18 = 2^61.617.  Un tirage honnête consomme 61.6 bits.  Si le générateur
de l'opérateur en émet moins — b bits mis à l'échelle dans [0, C) — alors le flux des rangs
ne prend au plus que 2^b valeurs distinctes, quelle que soit la façon dont il les met à
l'échelle.  Deux tests, de portée différente, et je dis pour chacun ce qu'il suppose :

  (A) SANS MODÈLE.  L'image du générateur a au plus 2^b points ; n = 70560 tirages y
      entrent en collision au rythme des anniversaires, n(n-1)/2 / 2^b, quelle que soit
      l'application.  Compter les rangs répétés borne donc b par le bas sans rien supposer
      sur la mise à l'échelle.  Portée limitée : n^2/2 = 2.49e9 = 2^31.2, donc ce test seul
      ne voit rien au-delà de ~2^41.

  (B) AVEC LE MODÈLE DE MISE À L'ÉCHELLE STANDARD r = floor(u * C / 2^b), u dans [0,2^b).
      Ce modèle s'inverse exactement : r = floor(u*C/2^b) équivaut à u = ceil(r*2^b/C)
      (ATTENTION : plancher à l'aller, PLAFOND au retour — un plancher au retour rend
      u-1 et casse le test ; le contrôle positif ci-dessous ne passait pas avant ce
      correctif).  Un seul tirage qui échoue tue le b correspondant : réfutation dure,
      pas statistique.  Sous l'uniformité un tirage passe avec probabilité 2^b/C, donc le
      test meurt au premier ou deuxième tirage tant que b < 61.

Un flux à b bits passe (B) pour tout b' >= b (le pas C/2^b est un multiple entier du pas
C/2^b'), donc la statistique lue est LE PLUS PETIT b qui passe.  Sous l'uniformité ce plus
petit b doit être 62, là où 2^b > C rend le test vide.
"""
import math
import numpy as np

C80 = math.comb(80, 20)
C81 = math.comb(81, 20)
N_EXPECTED = 70560

# le module propre à chaque convention : colex1 indexe des sous-ensembles de {1..80} vus
# comme 0-based, donc son image vit dans [0, C(81,20)) et n'en couvre que C(80,20) points.
MODULUS = {"colex0": C80, "lex0": C80, "colex1": C81, "comp0": C80, "revcolex0": C80}
FULL_IMAGE = {"colex0": True, "lex0": True, "colex1": False, "comp0": True, "revcolex0": True}


def smallest_passing_b(r, M, bmax=62):
    """Le plus petit b tel que TOUS les rangs soient des points du réseau à b bits."""
    for b in range(8, bmax + 1):
        shift = 1 << b
        for x in r:
            u = -((-x * shift) // M)          # ceil(x * 2^b / M)
            if (u * M) // shift != x:
                break
        else:
            return b
    return None


def report(name, r, M, full_image=True, show_gaps=False):
    n = len(r)
    d = n - len(set(r))
    pairs = n * (n - 1) / 2.0
    print("  %-24s n = %d" % (name, n))
    if d == 0:
        b_hard = max((b for b in range(8, 62) if math.exp(-pairs / (1 << b)) < 1e-3),
                     default=None)
        print("    (A) 0 rang repete  -> tout reseau de <= %d bits rejete a p < 1e-3" % b_hard)
    else:
        print("    (A) %d rangs repetes -> image de taille ~2^%.1f" % (d, math.log2(pairs / d)))

    b = smallest_passing_b(r, M)
    if b is None or b >= 62:
        print("    (B) plus petit reseau compatible : AUCUN b <= 61")
    else:
        print("    (B) plus petit reseau compatible : b = %d   *** RESEAU DETECTE ***" % b)

    if show_gaps:
        s = sorted(r)
        g = np.array([float(s[i + 1] - s[i]) for i in range(n - 1)])
        mean_exp = M / n
        print("    espacements : moyenne %.4e (theorie %.4e, rapport %.4f), sd/moy %.4f"
              % (g.mean(), mean_exp, g.mean() / mean_exp, g.std() / g.mean()))
        if full_image:
            u = np.sort(1.0 - np.exp(-g / mean_exp))
            ks = np.abs(u - (np.arange(1, n) / (n - 1))).max()
            crit = 1.36 / math.sqrt(n - 1)
            print("                  KS vs exponentielle D = %.5f (critique 5%% %.5f)  %s"
                  % (ks, crit, "OK" if ks < crit else "DEVIE"))
        else:
            print("                  KS non applicable : l'image n'est pas l'intervalle entier")
        print("    ecart minimal %.4e -> tout reseau de <= %d bits refute par ce seul ecart"
              % (g.min(), int(math.floor(math.log2(M / g.min())))))
    return b


fails = 0
print("=" * 74)
print("CONTROLES POSITIFS -- le test doit retrouver un reseau plante")
print("=" * 74)
rng = np.random.default_rng(20260904)
for b_true in (24, 32, 38, 44, 52, 58):
    u = [int(x) for x in rng.integers(0, 1 << b_true, size=N_EXPECTED, dtype=np.uint64)]
    r = [(x * C80) >> b_true for x in u]
    b = report("reseau plante b=%d" % b_true, r, C80)
    ok = (b == b_true)
    fails += (not ok)
    print("    -> %s (attendu b = %d)\n" % ("RECOVERED" if ok else "FAIL b=%s" % b, b_true))

print("=" * 74)
print("CONTROLE NEGATIF -- un flux vraiment uniforme ne doit montrer aucun reseau")
print("=" * 74)
r = [int(x) for x in rng.integers(0, C80, size=N_EXPECTED, dtype=np.uint64)]
b = report("uniforme sur [0,C)", r, C80, show_gaps=True)
ok = (b is None or b >= 62)
fails += (not ok)
print("    -> %s\n" % ("PASS (aucun reseau, comme attendu)" if ok else "FAIL faux positif b=%d" % b))

if fails:
    raise SystemExit("CONTROLES ECHOUES (%d) -- resultat sur l'archive NON ecrit" % fails)
print("controles: tous passes -- l'outil retrouve un reseau plante de 24 a 58 bits")
print("           et n'en invente pas sur un flux uniforme.\n")

print("=" * 74)
print("ARCHIVE REELLE")
print("=" * 74)
for conv in ("colex0", "lex0", "colex1", "comp0", "revcolex0"):
    try:
        a = np.fromfile("rank_%s.bin" % conv, dtype=np.uint64)
    except FileNotFoundError:
        continue
    r = [int(x) for x in a]
    if len(r) != N_EXPECTED:
        print("  %s : %d rangs (attendu %d) -- ignore" % (conv, len(r), N_EXPECTED))
        continue
    report("rang %s" % conv, r, MODULUS[conv], FULL_IMAGE[conv], show_gaps=True)
    print()
