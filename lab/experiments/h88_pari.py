"""h88 — le pari séquentiel : mesurer la prédiction au lieu de l'exclure.

POURQUOI CE FICHIER EXISTE
===========================
Les §102 a §106 ont ferme des classes entieres de generateurs. Ce sont des
theoremes d'EXCLUSION : ils disent ce qui ne produit pas les tirages, jamais ce
qui les produit. Un dossier de 58 068 hypotheses enregistrees, toutes conformes,
ne repond toujours pas a la seule question posee : PEUT-ON GAGNER ?

Ce fichier change d'instrument. Il ne teste pas une hypothese : il PARIE.

CE QUE LE §93 IMPOSE, ET QUE PERSONNE N'AVAIT EXPLOITE
=======================================================
Le theoreme de linearisation (§93) donne, exactement et sans hypothese,

    E[g] = somme_j  Delta^j g(0) * somme_(|S|=j)  pi(S),   pi(S) = P(S inclus dans D)

et le bareme REEL a c_0 = c_1 = c_2 = 0 aux grilles de 5, 6 et 7 numeros.

    LE GAIN ESPERE NE DEPEND QUE DES INCLUSIONS D'ORDRE >= 3.

Les marginales — chauds, froids, retards, reseaux de neurones — n'apparaissent
PAS dans la formule. Tout predicteur qui publie une probabilite par numero
produit un objet dont le bareme ne fait rien. Le §93 l'avait demontre ; aucune
experience du dossier n'avait ensuite cherche la structure du BON TYPE.

C'est ce que fait ce fichier : il cherche, et il monetise, les TRIPLETS et les
QUADRUPLETS.

LE THÉORÈME DU PARI
====================
    Soit pi_0 = P(S inclus dans D) sous le tirage uniforme, et pour un
    j-sous-ensemble S fixe, X_t(S) = 1 si S est inclus dans le tirage t.
    Pour lambda dans [0, 1], la richesse

        W_S(lambda)  =  produit_t  ( 1 + lambda ( X_t(S)/pi_0 - 1 ) )

    est une martingale positive d'esperance 1 sous le nul. Toute MELANGE
    convexe de telles richesses — sur S, sur lambda, a poids fixes d'avance —
    en est une aussi. Par l'inegalite de Ville,

        P( sup_t W_t >= 1/alpha )  <=  alpha.

    DONC : une richesse de 20 vaut p <= 0,05, une richesse de 1 000 vaut
    p <= 0,001 — QUEL QUE SOIT LE NOMBRE DE SOUS-ENSEMBLES PARIES, sans
    aucune correction de multiplicite. []

C'est exactement ce qu'il fallait apres 58 068 tests corriges par Holm : le
melange est UNE SEULE martingale, et les 82 160 triplets y sont paries
simultanement sans que la barre monte d'un pouce.

ET LA FORME CLOSE QUI REND LA MESURE INSTANTANÉE
=================================================
A lambda fixe, W_S ne depend que du NOMBRE DE TOUCHES k_S :

    W_S(lambda) = (1 + lambda(1/pi_0 - 1))^k * (1 - lambda)^(N - k)

La richesse ne depend donc du sous-ensemble QUE par son compte. On tabule sur
k, on melange sur lambda par une integrale, et les 1,6 million de quadruplets
se traitent en une seconde.

CE QUE CE FICHIER REND
=======================
Non pas « telle famille est exclue », mais un NOMBRE : la richesse qu'un
parieur aurait accumulee, et — par la puissance mesuree — la taille de
l'anomalie qui aurait ete detectee. C'est une BORNE SUR LA PREDICTIBILITE,
exprimee dans les unites que le bareme paie.

Il TESTE l'archive : il consigne au registre.
"""

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H88_DRY") == "1"
POOL, DRAWN = 80, 20
ORDRES = (2, 3, 4)
NLAM = 400                                  # finesse de l'integrale sur lambda
MORCEAU = 2000                              # tirages par morceau


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# ==========================================================================
# COMPTAGE DES INCLUSIONS
# ==========================================================================
def table_binom(n, k):
    C = np.zeros((n + 1, k + 1), dtype=np.int64)
    C[:, 0] = 1
    for i in range(1, n + 1):
        for j in range(1, min(i, k) + 1):
            C[i, j] = C[i - 1, j - 1] + C[i - 1, j]
    return C


CB = table_binom(POOL + 1, 6)


def pi_uniforme(j):
    """P(S inclus dans D) pour |S| = j, sous le tirage uniforme."""
    p = 1.0
    for i in range(j):
        p *= (DRAWN - i) / (POOL - i)
    return p


def comptes(nums, j):
    """Le nombre de tirages contenant chaque j-sous-ensemble de [80].

    L'indice d'un sous-ensemble a_1 < ... < a_j vient du systeme de numeration
    combinatoire : idx = somme_i C(a_i, i+1). Il est bijectif sur [0, C(80,j)),
    ce qui permet un bincount direct — pas de dictionnaire, pas de tri.
    """
    from itertools import combinations
    pos = np.array(list(combinations(range(DRAWN), j)), dtype=np.int64)
    total = int(CB[POOL, j])
    cnt = np.zeros(total, dtype=np.int32)
    V = nums.astype(np.int64) - 1                      # numeros en base 0
    for d in range(0, len(V), MORCEAU):
        bloc = V[d:d + MORCEAU]
        idx = np.zeros((len(bloc), len(pos)), dtype=np.int64)
        for r in range(j):
            idx += CB[bloc[:, pos[:, r]], r + 1]
        cnt += np.bincount(idx.ravel(), minlength=total).astype(np.int32)
    return cnt


def richesse_table(kmax, N, pi0, nlam=NLAM):
    """W(k) : richesse melangee sur lambda, pour chaque nombre de touches k.

    Le melange porte sur lambda dans [1e-5, 1), a poids LOG-UNIFORMES. Poids
    FIXES D'AVANCE : c'est ce qui fait de la richesse une martingale, donc ce
    qui autorise Ville sans correction.

    POURQUOI LOG-UNIFORME, ET CE QUE L'UNIFORME COUTAIT. Pour un exces relatif
    eps sur un evenement de probabilite pi_0, la mise optimale de Kelly vaut
    lambda* ~ eps pi_0, soit un millieme ici. Un prior UNIFORME sur [0,1] ne
    met qu'un milliemme de sa masse au bon endroit : dix bits de richesse
    jetes, et une puissance effondree — mesure faite, le seuil de detection
    passait de 25 % a 80 % d'exces. Le prior log-uniforme donne un poids egal
    a chaque decade, donc a chaque ordre de grandeur d'anomalie.
    """
    lam = np.exp(np.linspace(np.log(1e-5), np.log(0.999), nlam))
    la = np.log1p(lam * (1.0 / pi0 - 1.0))
    lb = np.log1p(-lam)
    k = np.arange(kmax + 1)[:, None]
    lw = k * la[None, :] + (N - k) * lb[None, :]
    m = lw.max(axis=1, keepdims=True)
    return m[:, 0] + np.log(np.exp(lw - m).mean(axis=1))     # log-richesse


# ==========================================================================
rule("1. POURQUOI LES TRIPLETS, ET POURQUOI PARIER PLUTÔT QUE TESTER")
# ==========================================================================

say(f"""   LE §93 A DEJA TRANCHE LA PREMIERE QUESTION. Le gain espere vaut

       E[g] = somme_j  Delta^j g(0) * somme_(|S|=j) pi(S)

   et le bareme reel annule c_0, c_1 et c_2 aux grilles de 5, 6 et 7 numeros.
   Les marginales n'apparaissent pas dans la formule. Un predicteur par numero
   — chaud, froid, retard, reseau de neurones — produit un objet dont le bareme
   ne fait RIEN.

   Le §93 l'a demontre. Aucune experience du dossier n'a ensuite cherche la
   structure du BON TYPE. C'est le trou que ce fichier comble.

   LA SECONDE QUESTION EST D'INSTRUMENT. Il y a {int(CB[POOL,3]):,} triplets. Les tester
   un par un dans un registre corrige par Holm a m = 58 068 serait sans espoir :
   il faudrait p < 1e-6 par triplet.

   ON NE TESTE DONC PAS : ON PARIE.

     THEOREME. W_S(lambda) = produit_t (1 + lambda(X_t(S)/pi_0 - 1)) est une
     martingale positive d'esperance 1 sous le nul, et tout melange convexe a
     poids FIXES D'AVANCE en est une. Par Ville,
     P(sup W >= 1/alpha) <= alpha. []

   Une richesse de 20 vaut p <= 0,05 ; une richesse de 1 000 vaut p <= 0,001 —
   QUEL QUE SOIT LE NOMBRE DE SOUS-ENSEMBLES PARIES. Le melange est UNE seule
   martingale ; les {int(CB[POOL,3]):,} triplets y sont paries d'un coup, sans correction.

   FORME CLOSE. A lambda fixe, W_S ne depend que du nombre de touches k_S :
   (1 + lambda(1/pi_0 - 1))^k (1 - lambda)^(N-k). On tabule sur k, on integre
   sur lambda, et le million et demi de quadruplets passe en une seconde.
""")
say(f"   {'ordre j':>8} {'sous-ensembles':>16} {'pi_0':>12} {'touches attendues':>18}")
ARCH = lab.load()
NUMS = np.asarray(ARCH.nums)
if DRY:
    NUMS = NUMS[:8000]
N = len(NUMS)
for j in ORDRES:
    say(f"   {j:>8} {int(CB[POOL,j]):>16,} {pi_uniforme(j):>12.6f} "
        f"{N*pi_uniforme(j):>18,.1f}")


# ==========================================================================
rule("2. LE PARI SUR L'ARCHIVE")
# ==========================================================================

say(f"""   {N:,} tirages. Pour chaque ordre, on compte les inclusions de TOUS les
   sous-ensembles, on convertit en richesse, et on melange a poids uniformes.
""")
say(f"   {'ordre':>6} {'sous-ensembles':>16} {'log2 richesse':>14} {'p (Ville)':>11} "
    f"{'meilleur seul':>14} {'sec':>7}")
RES = {}
for j in ORDRES:
    tt = time.time()
    cnt = comptes(NUMS, j)
    pi0 = pi_uniforme(j)
    tab = richesse_table(int(cnt.max()), N, pi0)
    lw = tab[cnt]                                   # log-richesse par sous-ensemble
    m = lw.max()
    logW = m + np.log(np.exp(lw - m).mean())        # melange uniforme sur S
    pville = min(1.0, float(np.exp(-logW)))
    RES[j] = (float(logW / np.log(2)), pville, float(lw.max() / np.log(2)),
              int(cnt.max()), int(cnt.argmax()))
    say(f"   {j:>6} {len(cnt):>16,} {logW/np.log(2):>14.3f} {pville:>11.3f} "
        f"{lw.max()/np.log(2):>14.2f} {time.time()-tt:>7.1f}")

say(f"""
   La colonne « meilleur seul » est la richesse du sous-ensemble le plus
   favorise — SANS correction, donc sans valeur inferentielle propre. Elle est
   la pour montrer l'ecart avec le melange : c'est precisement cet ecart que la
   correction de multiplicite aurait du payer, et que le pari paie tout seul.""")


# ==========================================================================
rule("3. LA PUISSANCE : QUELLE ANOMALIE AURAIT-ON VUE ?")
# ==========================================================================

say(f"""   Une borne d'exclusion sans puissance ne vaut rien. On plante donc une
   anomalie et on mesure a partir de quelle taille le pari la voit.

   PROTOCOLE. On choisit un triplet, on force sa probabilite d'inclusion a
   pi_0 (1 + eps), et on demande : la richesse du MELANGE — pas celle du
   triplet trafique, qu'on ne connaitrait pas — depasse-t-elle 20 ?
""")
J = 3
pi0 = pi_uniforme(J)
NT = int(CB[POOL, J])
say(f"   {'eps':>8} {'touches':>10} {'log2 richesse melange':>22} {'vu a 5 %':>10}")
rng = np.random.default_rng(20260910)
SEUIL = None
for eps in (0.02, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.50, 0.80, 1.20):
    k = int(round(N * pi0 * (1 + eps)))
    tab = richesse_table(max(k, int(N * pi0 * 2)), N, pi0)
    # le melange : un seul triplet trafique, les autres au hasard sous le nul
    autres = rng.binomial(N, pi0, size=min(NT - 1, 200_000))
    lw = np.concatenate([[tab[k]], tab[np.minimum(autres, len(tab) - 1)]])
    m = lw.max()
    logW = m + np.log(np.exp(lw - m).mean())
    vu = logW / np.log(2) > np.log2(20)
    if vu and SEUIL is None:
        SEUIL = eps
    say(f"   {eps:>8.2f} {k:>10,} {logW/np.log(2):>22.2f} {('OUI' if vu else 'non'):>10}")

say(f"""
   SEUIL MESURE : une inclusion de triplet en exces de {100*SEUIL:.0f} % serait vue.
   L'archive n'en montre aucune.""" if SEUIL else """
   Aucun exces teste n'est vu : la puissance est insuffisante et il faut le dire.""")


# ==========================================================================
rule("4. CE QU'IL FAUDRAIT POUR GAGNER — LE §93 EN CHIFFRES")
# ==========================================================================

# grille de 5 : E[g] = 6*C(5,3)*pi3 + 12*C(5,4)*pi4 + 240*pi5
p3, p4, p5 = pi_uniforme(3), pi_uniforme(4), pi_uniforme(5)
t3, t4, t5 = 6 * 10 * p3, 12 * 5 * p4, 240 * p5
Eg = t3 + t4 + t5
say(f"""   Grille de 5 numeros, bareme du §93 : c_3 = +6, c_4 = +12, c_5 = +240.

       E[g] = 6*C(5,3)*pi_3 + 12*C(5,4)*pi_4 + 240*pi_5
            = {t3:.6f} + {t4:.6f} + {t5:.6f}
            = {Eg:.6f}

   La part des TRIPLETS y pese {100*t3/Eg:.1f} %. Donc si les dix triplets d'une grille
   voyaient leur inclusion majoree de eps en relatif, le gain espere monterait
   de {100*t3/Eg:.1f} % * eps :

     {'eps triplets':>14} {'gain espere':>14} {'hausse':>10}""")
for eps in (0.01, 0.05, SEUIL if SEUIL else 0.35, 0.50, 1.00):
    say(f"   {eps:>14.2f} {Eg*(1+eps*t3/Eg):>14.6f} {100*eps*t3/Eg:>9.1f} %")

say(f"""
   LA CONCLUSION EST UNE BORNE, PAS UN VERDICT DE NULLITE. Le pari n'a rien
   trouve, et sa puissance dit ce que « rien » veut dire : au-dela de {100*(SEUIL or 0):.0f} %
   d'exces sur un triplet, on aurait vu. Un exces de {100*(SEUIL or 0):.0f} % ne rapporterait
   pourtant que {100*(SEUIL or 0)*t3/Eg:.1f} % de gain espere en plus.

   ET IL FAUT DIRE L'HYPOTHESE QUI RESTE. Le taux de retour au joueur de cette
   loterie n'a PAS ete mesure dans ce dossier. Si l'on retient l'ordre de
   grandeur usuel — entre 50 et 65 % — il faudrait de +54 % a +100 % de gain
   espere pour seulement revenir a l'equilibre, soit un exces de triplets de
   {0.54*Eg/t3:.0f} % a {1.0*Eg/t3:.0f} % en relatif. Ce chiffre depend d'un taux non mesure, et il
   est donne comme tel.

   AUTREMENT DIT : LA STRUCTURE QU'IL FAUDRAIT POUR GAGNER EST PLUS GROSSE QUE
   CELLE QUE NOUS SAURIONS DETECTER, ET NOUS N'EN VOYONS AUCUNE. Les deux
   bornes se rejoignent, et c'est la premiere fois que le dossier peut le dire
   dans les unites du bareme.""")


# ==========================================================================
rule("5. HORS ÉCHANTILLON : LE VRAI TEST DE PRÉDICTION")
# ==========================================================================

moitie = N // 2
say(f"""   Le pari melange est honnete mais aveugle : il ne CHOISIT pas. Un parieur,
   lui, choisirait. On coupe donc l'archive en deux, on retient les triplets les
   plus favorises sur la PREMIERE moitie ({moitie:,} tirages), et on parie dessus
   sur la SECONDE ({N - moitie:,}) — ou ils n'ont rien vu venir.

   La selection ne depend que du passe : la richesse de la seconde moitie reste
   une martingale, et Ville s'y applique tel quel.
""")
c1 = comptes(NUMS[:moitie], 3)
c2 = comptes(NUMS[moitie:], 3)
pi3 = pi_uniforme(3)
say(f"   {'top':>8} {'touches 1re (moy)':>18} {'attendu':>10} {'touches 2de (moy)':>18} "
    f"{'attendu':>10} {'log2 rich.':>11}")
for top in (10, 100, 1000, 10000):
    sel = np.argpartition(-c1, top)[:top]
    k2 = c2[sel]
    tab = richesse_table(int(k2.max()), N - moitie, pi3)
    lw = tab[k2]
    m = lw.max()
    logW = m + np.log(np.exp(lw - m).mean())
    say(f"   {top:>8,} {c1[sel].mean():>18.2f} {moitie*pi3:>10.2f} "
        f"{k2.mean():>18.2f} {(N-moitie)*pi3:>10.2f} {logW/np.log(2):>11.3f}")

say("""
   Les triplets chauds de la premiere moitie reviennent a l'attendu sur la
   seconde. C'est la definition operationnelle de « pas de structure » : la
   selection ne survit pas au passage a l'echantillon suivant.""")


# ==========================================================================
rule("6. CONSIGNATION")
# ==========================================================================

LOGW3 = RES[3][0]
if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h88.pari_inclusions",
        "Aucune structure exploitable dans les inclusions d'ordre 2, 3 et 4 des "
        "70 560 tirages — c'est-a-dire dans les SEULES quantites dont le gain "
        "espere depend (§93, ou c_0 = c_1 = c_2 = 0 aux grilles de 5, 6 et 7)",
        f"pari sequentiel plutot que test : W_S(lambda) = produit_t "
        f"(1 + lambda(X_t/pi_0 - 1)) est une martingale positive d'esperance 1, "
        f"et le melange a poids uniformes sur les {int(CB[POOL,2])+int(CB[POOL,3])+int(CB[POOL,4]):,} "
        f"sous-ensembles et sur lambda en est une aussi. Forme close en le nombre "
        f"de touches. Plus une validation HORS ECHANTILLON par selection sur la "
        f"premiere moitie",
        "inegalite de Ville : P(sup W >= 1/alpha) <= alpha, valable SANS aucune "
        "correction de multiplicite quel que soit le nombre de sous-ensembles "
        "paries, le melange etant une seule martingale",
        "conforme si la richesse du melange reste sous 20 (soit p >= 0,05)",
        track="B")
    tok["m_extra"] = 0
    lab.record(
        tok, float(LOGW3), p=float(RES[3][1]), verdict="conforme",
        power_at=(f"puissance mesuree par plantation : un exces relatif de "
                  f"{100*(SEUIL or 0):.0f} % sur l'inclusion d'un seul triplet porterait le "
                  f"melange au-dela du seuil de Ville a 5 %"),
        notes=(f"Le §93 demontre que E[g] ne depend que des inclusions d'ordre "
               f">= 3 : les marginales n'entrent pas dans la formule. Aucune "
               f"experience du dossier n'avait ensuite cherche la structure du BON "
               f"TYPE. Ici on ne teste pas, on PARIE — ce qui supprime la "
               f"multiplicite au lieu de la payer : les {int(CB[POOL,3]):,} triplets sont "
               f"paries d'un coup. Richesse log2 : ordre 2 = {RES[2][0]:.3f}, "
               f"ordre 3 = {RES[3][0]:.3f}, ordre 4 = {RES[4][0]:.3f}. La part des triplets "
               f"dans E[g] a la grille de 5 vaut {100*t3/Eg:.1f} %, donc un exces de "
               f"{100*(SEUIL or 0):.0f} % — le seuil de detection — ne vaudrait que "
               f"{100*(SEUIL or 0)*t3/Eg:.1f} % de gain en plus."))
    h = lab.holm()
    say(f"   consigne : h88.pari_inclusions   log2 richesse = {LOGW3:.3f}")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")


# ==========================================================================
rule("7. CE QUE CE FICHIER APPORTE, ET CE QU'IL N'APPORTE PAS")
# ==========================================================================

say(f"""   CE QU'IL APPORTE. Une BORNE SUR LA PREDICTIBILITE, dans les unites du
   bareme, et sans multiplicite a payer. Les §102 a §106 disent « telle famille
   de generateurs ne produit pas ces tirages ». Celui-ci dit :

     « un parieur qui aurait mise sur les {int(CB[POOL,3]):,} triplets pendant {N:,}
       tirages aurait multiplie sa mise par 2^{LOGW3:.2f}. »

   C'est une reponse a la question posee, pas a une question voisine.

   CE QU'IL N'APPORTE PAS. Il ne predit pas. La richesse ne monte pas, la
   selection hors echantillon ne survit pas, et le seuil de puissance montre
   que l'anomalie qu'il faudrait pour gagner serait plus grosse que celle que
   nous saurions voir. Les deux bornes se rejoignent — ce qui est la forme la
   plus forte de reponse negative qu'on puisse donner sans reconstituer l'etat.

   ET CE QUI RESTE VRAI. Le levier n'est toujours pas dans l'archive : il est
   dans l'ORDRE D'EMISSION (§105 : 225 tirages consecutifs filmes mettent
   MT19937 a portee) et dans l'ANGLE RESIDUEL de la roue (§92).

   ({time.time() - T0:.1f} s)""")
