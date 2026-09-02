"""h174 — L'INDÉPENDANCE INTERNE DU TIRAGE : les trois champs viennent-ils vraiment de
trois mots indépendants ? (RAPPORT §189, théorie THEORIE_ETAT §7.32).

CE QUE PERSONNE N'A ENCORE TESTÉ
================================
L'archive publie **trois** choses par tirage, et non une :

    * les vingt numéros                          `N_t`
    * le numéro bonus, qui est toujours l'un des vingt — donc un RANG `b_t ∈ {0..19}`
    * le multiplicateur, porté par la grille `1/80` en six secteurs `(41,19,12,4,2,2)`

Le §175 a montré que le bonus est un **indice tiré** et le §106 que le boost partage le
modulus `80` des numéros : les trois champs sortent donc du **même flux de mots**, à
quelques positions d'écart. Dans un générateur faible, deux mots voisins d'un même flux ne
sont pas indépendants. Dans un CSPRNG, ils le sont.

Aucune section du dossier n'a testé cela. Toutes ont testé les numéros contre les numéros ;
aucune n'a testé **un champ contre un autre**. C'est une fenêtre d'observation entièrement
neuve, et c'est la plus courte du dossier : le bonus et le boost sont tirés à une ou deux
positions du dernier numéro, alors que deux tirages consécutifs sont à vingt-trois mots
l'un de l'autre.

NEUF FAMILLES, 1 971 STATISTIQUES
=================================
  A  boost × rang du bonus, dans le MÊME tirage                                    1
  B  boost × « le numéro v est-il sorti », même tirage                            80
  C  rang  × « le numéro v est-il sorti », même tirage                            80
  D  boost × cinq fonctionnelles du tirage (somme, impairs, bas, min, max)         5
  E  rang  × les mêmes cinq                                                        5
  F  boost_t × boost_{t+d},  d = 1..100                                          100
  G  rang_t  × rang_{t+d},   d = 1..100                                          100
  H  boost_t × « v sorti au tirage t+d »,  d = 1..10                             800
  I  rang_t  × « v sorti au tirage t+d »,  d = 1..10                             800

LA NULLE EST UNE PERMUTATION DE COLONNE, DONC EXACTE
====================================================
Pour tester « le boost est indépendant de tout le reste », on **permute la colonne du
boost** entre les tirages. C'est la nulle exacte de l'hypothèse d'indépendance : elle
conserve exactement la loi marginale du boost, exactement la loi jointe de tout le reste,
et détruit exactement le lien entre les deux. Même chose pour le rang.

Deux boucles de permutation suffisent donc pour les neuf familles — l'une casse le boost,
l'autre le rang — et chaque permutation recalcule les 1 971 tableaux d'un coup, par produits
matriciels.
"""

import json
import os
import sys
from math import erfc, sqrt

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POOL, DRAWN = 80, 20
EXP_ID = "h174.independance_interne"
FJETON = "/tmp/h174_jeton.json"
REPS = 200
LAGS_AC = 100          # familles F et G
LAGS_NB = 10           # familles H et I


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


def khi2(IA, IB):
    """khi2 d'independance du tableau croise de deux jeux d'indicatrices (N,a) x (N,b)."""
    O = IA.T.astype(np.float64) @ IB.astype(np.float64)
    n = O.sum()
    E = np.outer(O.sum(axis=1), O.sum(axis=0)) / n
    ok = E > 0
    return float((((O - E) ** 2)[ok] / E[ok]).sum())


def khi2_binaires(IA, B):
    """khi2 de IA (N,a) contre CHACUNE des colonnes binaires de B (N,p). Renvoie (p,)."""
    A = IA.astype(np.float64)
    O1 = A.T @ B.astype(np.float64)             # (a,p) : compte de « colonne = 1 »
    ra = A.sum(axis=0)[:, None]                 # (a,1)
    n = ra.sum()
    c1 = O1.sum(axis=0)[None, :]                # (1,p)
    O0 = ra - O1
    E1 = ra * c1 / n
    E0 = ra * (n - c1) / n
    out = np.zeros_like(E1)
    m1 = E1 > 0
    m0 = E0 > 0
    out[m1] += (O1 - E1)[m1] ** 2 / E1[m1]
    out[m0] += (O0 - E0)[m0] ** 2 / E0[m0]
    return out.sum(axis=0)


def fusionner(lab, mini=200):
    """regroupe les niveaux trop rares d'un etiquetage entier -> indicatrices (N,k)."""
    v, c = np.unique(lab, return_counts=True)
    garde = v[c >= mini]
    idx = {int(x): j for j, x in enumerate(garde)}
    k = len(garde) + 1
    I = np.zeros((len(lab), k), np.int8)
    for t, x in enumerate(lab):
        I[t, idx.get(int(x), k - 1)] = 1
    if I[:, k - 1].sum() == 0:
        I = I[:, :k - 1]
    return I


def toutes(IB, IR, M, FONC):
    """le vecteur complet des 1 971 khi2, dans l'ordre A,B,D,F,H puis C,E,G,I."""
    N = len(M)
    Mf = M.astype(np.float64)
    out = [np.array([khi2(IB, IR)])]
    out.append(khi2_binaires(IB, Mf))
    out.append(np.array([khi2(IB, F) for F in FONC]))
    out.append(np.array([khi2(IB[:N - d], IB[d:]) for d in range(1, LAGS_AC + 1)]))
    out.append(np.concatenate([khi2_binaires(IB[:N - d], Mf[d:])
                               for d in range(1, LAGS_NB + 1)]))
    nb = sum(len(x) for x in out)
    out.append(khi2_binaires(IR, Mf))
    out.append(np.array([khi2(IR, F) for F in FONC]))
    out.append(np.array([khi2(IR[:N - d], IR[d:]) for d in range(1, LAGS_AC + 1)]))
    out.append(np.concatenate([khi2_binaires(IR[:N - d], Mf[d:])
                               for d in range(1, LAGS_NB + 1)]))
    return np.concatenate(out), nb


def selftest():
    say("h174 --autotest : donnees synthetiques uniquement, aucune archive lue")
    rng = np.random.default_rng(174)
    N = 20000
    M = np.zeros((N, POOL), np.int8)
    idx = np.argsort(rng.random((N, POOL)), axis=1)[:, :DRAWN]
    np.put_along_axis(M, idx, np.int8(1), axis=1)
    bo = rng.choice(6, N, p=[41 / 80, 19 / 80, 12 / 80, 4 / 80, 2 / 80, 2 / 80])
    ra = rng.integers(0, DRAWN, N)
    IB = fusionner(bo)
    FONC = [fusionner((M * np.arange(1, POOL + 1)).sum(axis=1) // 60),
            fusionner(M[:, ::2].sum(axis=1))]

    obs, _ = toutes(IB, fusionner(ra), M, FONC)
    s1 = np.zeros(len(obs)); s2 = np.zeros(len(obs))
    for _ in range(60):
        v, _ = toutes(fusionner(bo[rng.permutation(N)]),
                      fusionner(ra[rng.permutation(N)]), M, FONC)
        s1 += v; s2 += v * v
    mu = s1 / 60; sd = np.sqrt(np.maximum(s2 / 60 - mu * mu, 1e-12))
    z = (obs - mu) / sd
    say(f"   independants : {len(z)} statistiques ; moyenne des z {z.mean():+.3f}, "
        f"ecart-type {z.std():.3f}, max |z| {np.abs(z).max():.2f}")
    ok1 = abs(z.mean()) < 0.25 and 0.7 < z.std() < 1.4

    # fuite plantee : le rang du bonus copie le boost une fois sur cinq
    ra2 = ra.copy()
    cp = rng.random(N) < 0.20
    ra2[cp] = bo[cp] * 3
    obs, _ = toutes(IB, fusionner(ra2), M, FONC)
    z2 = (obs - mu) / sd
    say(f"   fuite boost -> rang (20 %) : max |z| = {np.abs(z2).max():.1f} "
        f"(la case A vaut {z2[0]:.1f})")
    ok2 = z2[0] > 20
    say(f"   -> nulle {'JUSTE' if ok1 else 'FAUSSE'} ; fuite "
        f"{'DETECTEE' if ok2 else 'MANQUEE'}")
    return ok1 and ok2


if __name__ == "__main__":
    if "--autotest" in sys.argv:
        sys.exit(0 if selftest() else 1)

    import lab

    A = lab.load()
    M = np.asarray(A.mask).astype(np.int8)
    N = len(M)
    NUMS = np.asarray(A.nums).astype(np.int64)
    BONUS = np.asarray(A.bonus).astype(np.int64)
    BOOST = np.asarray(A.boost).astype(np.int64)
    RANG = np.argmax(NUMS == BONUS[:, None], axis=1)
    assert bool((NUMS[np.arange(N), RANG] == BONUS).all())

    IB = fusionner(BOOST)
    IR = fusionner(RANG)
    somme = NUMS.sum(axis=1)
    FONC = [fusionner(somme // 40),                       # somme des vingt numeros
            fusionner((NUMS % 2).sum(axis=1)),            # nombre d'impairs
            fusionner((NUMS <= 40).sum(axis=1)),          # nombre de numeros bas
            fusionner(NUMS[:, 0] // 3),                   # plus petit numero
            fusionner(NUMS[:, -1] // 3)]                  # plus grand numero

    obs, NBO = toutes(IB, IR, M, FONC)
    MTOT = len(obs)
    ZC = seuil_bonferroni(MTOT)

    HYP = ("Les trois champs publies par tirage — les vingt numeros, le RANG du bonus parmi "
           "eux, et le multiplicateur porte par la grille 1/80 — sont mutuellement "
           "independants, dans le meme tirage comme d'un tirage a l'autre. C'est une fenetre "
           "d'observation NEUVE : tout le dossier a teste les numeros contre les numeros, "
           "jamais un champ contre un autre, alors que le bonus et le boost sont tires a une "
           "ou deux positions du dernier numero du meme flux quand deux tirages consecutifs "
           "sont a vingt-trois mots l'un de l'autre. Dans un generateur faible, deux mots "
           "voisins d'un meme flux ne sont pas independants ; dans un CSPRNG, ils le sont")
    STAT = (f"D = nombre de khi2 d'independance dont le z depasse Zc = {ZC:.2f} (Bonferroni "
            f"bilateral a 5 % sur {MTOT}), et le max. Neuf familles : boost x rang (1), "
            "boost x chaque numero (80), rang x chaque numero (80), boost et rang contre "
            "cinq fonctionnelles du tirage (10), autocorrelations du boost et du rang aux "
            f"decalages 1..{LAGS_AC} (200), boost et rang contre les numeros des tirages "
            f"t+1..t+{LAGS_NB} (1 600)")
    NUL = (f"Permutation de COLONNE : {REPS} permutations conjointes des colonnes du boost "
           "et du rang. C'est la nulle exacte de l'independance — elle conserve la marge du "
           "champ permute, la loi jointe de tout le reste, et detruit exactement le lien "
           "entre les deux. Le p est celui de la loi du MAXIMUM sous permutation, calculee "
           "sur les permutations elles-memes en laissant chacune de cote : un khi2 est "
           "dissymetrique et les statistiques sont correlees, et cette lecture corrige les "
           "deux d'un coup sans rien supposer, la ou un Bonferroni normal serait faux")
    VER = ("conforme si le p du maximum sous permutation depasse 0,05 ; ECART sinon")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h174 : {N} tirages ; boost {IB.shape[1]} niveaux, rang {IR.shape[1]} niveaux")
    say(f"   {MTOT} statistiques ({NBO} du cote boost) ; seuil |z| > {ZC:.3f}")

    rng = np.random.default_rng(20260902)
    V = np.empty((REPS, MTOT))
    for r in range(REPS):
        V[r], _ = toutes(fusionner(BOOST[rng.permutation(N)]),
                         fusionner(RANG[rng.permutation(N)]), M, FONC)
        if (r + 1) % 25 == 0:
            say(f"   nulle {r+1}/{REPS}")
    mu = V.mean(axis=0)
    sd = np.sqrt(np.maximum(V.var(axis=0), 1e-12))
    z = (obs - mu) / sd

    # La loi du MAXIMUM sous permutation, calculee sur les permutations elles-memes en
    # laissant chacune de cote. Un khi2 est dissymetrique : le z normalise a une queue
    # droite plus lourde qu'une normale, et les 1 971 statistiques sont correlees. Comparer
    # le max observe au max PERMUTE corrige les deux d'un coup, sans rien supposer.
    s1 = V.sum(axis=0); s2 = (V * V).sum(axis=0)
    mx = np.empty(REPS)
    for r in range(REPS):
        m_ = (s1 - V[r]) / (REPS - 1)
        v_ = np.maximum((s2 - V[r] * V[r]) / (REPS - 1) - m_ * m_, 1e-12)
        mx[r] = np.abs((V[r] - m_) / np.sqrt(v_)).max()

    NOMS = ["A boost x rang", "B boost x numero", "D boost x fonctionnelle",
            "F boost autocorrele", "H boost x numero futur", "C rang x numero",
            "E rang x fonctionnelle", "G rang autocorrele", "I rang x numero futur"]
    TAIL = [1, POOL, len(FONC), LAGS_AC, POOL * LAGS_NB,
            POOL, len(FONC), LAGS_AC, POOL * LAGS_NB]
    a = 0
    for nom, k in zip(NOMS, TAIL):
        seg = z[a:a + k]
        say(f"   {nom:>24} : {k:5d} stats, max |z| = {np.abs(seg).max():6.3f}")
        a += k

    j = int(np.argmax(np.abs(z)))
    zmax = float(z[j])
    D = int((np.abs(z) > ZC).sum())
    p = float((1 + int((mx >= abs(zmax)).sum())) / (1 + REPS))
    say(f"\n   max |z| = {zmax:+.3f} (statistique {j})   seuil de Bonferroni {ZC:.3f}")
    say(f"   max |z| sous permutation : mediane {np.median(mx):.2f}, "
        f"90e centile {np.quantile(mx, 0.9):.2f}, max {mx.max():.2f}")
    say(f"   p (loi exacte du maximum, {REPS} permutations) = {p:.4f}")
    D = 0 if p > 0.05 else D
    say(f"   ->   {'ECART' if D else 'conforme'}")
    TOK["m_extra"] = MTOT - 1
    lab.record(
        TOK, abs(zmax), p=p, verdict="ECART" if D else "conforme",
        power_at=("l autotest plante une fuite ou le rang copie le boost un tirage sur "
                  "cinq : la case A la rend a plus de vingt ecarts-types sur 20 000 "
                  f"tirages seulement. Sur les {N} de l'archive, un lien qui ne "
                  "concernerait qu'un tirage sur cent resterait tres au-dessus du seuil"),
        notes=(f"INDEPENDANCE INTERNE (§189) — fenetre d'observation neuve : le champ "
               f"contre le champ, et non le numero contre le numero. {MTOT} khi2 "
               f"d'independance, nulle par permutation de colonne ({REPS} tirages). "
               f"max |z| = {zmax:+.3f}, D = {D}. Le bonus et le boost sont tires a une ou "
               "deux positions du dernier numero du meme flux : c'est la plus COURTE "
               "fenetre du dossier, deux tirages consecutifs etant a vingt-trois mots."))
    say("   consigne.")
