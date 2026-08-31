"""h74 — l'angle mort du §89, demontre par un FAUX NEGATIF.

CE QUE LE §89 CONCLUT
======================
    « La suite des bonus de l'archive n'est engendree par AUCUN generateur
      F2-lineaire dont l'etat tienne sous 35 280 bits — MT19937 compris, et
      sans enumerer aucune famille. »

C'est la conclusion la plus large du dossier : elle ne nomme pas de famille,
donc elle les couvre toutes. Le §90 a verifie qu'elle ne depend pas de la
longueur W du tirage, et en a conclu qu'elle etait PLUS FORTE qu'annonce.

LA CONDITION QUE NI L'UN NI L'AUTRE N'A NOMMEE
===============================================
Berlekamp-Massey mesure la complexite lineaire d'une SUITE. La suite des
bonus vaut b_t = phi(L^{S_t} x), ou S_t est la position du premier mot du
tirage t dans le flux.

    SI S_t = W t avec W CONSTANT,  alors b_t = phi((L^W)^t x) : la suite est
    lineaire recurrente, de complexite au plus n. BM la voit.

    SI S_t est un PAS VARIABLE, b_t est une decimation a positions
    irregulieres. Rien ne dit qu'elle soit lineaire recurrente — et si elle
    ne l'est pas, BM rend N/2, c'est-a-dire « aleatoire ».

Or le pas EST variable des que l'echantillonneur procede par REJET : il
consomme 20 + r_t mots, ou r_t est le nombre de doublons rencontres (2,85 en
moyenne, §94). C'est l'implementation que le §76 appelle lui-meme « la naive
par excellence ».

CE FICHIER NE DISCUTE PAS : IL FABRIQUE LE CONTRE-EXEMPLE
==========================================================
On prend UN generateur — MT19937, exactement celui que le §89 nomme — et on
en tire deux archives synthetiques avec LE MEME etat initial et LA MEME
formule de bonus. Une seule chose change :

    (a) FISHER-YATES   pas exactement 20
    (b) REJET          pas 20 + r_t

Si BM rend 19 937 en (a) et N/2 en (b), alors le §89 aurait declare
« exclu » un generateur QUI EST LA. C'est un faux negatif, et il se
constate ; il ne se discute pas.

La section 3 mesure ensuite DE COMBIEN le pas doit varier pour aveugler BM.

Il ne teste rien sur l'archive : il ne consigne RIEN. Il corrige la PORTEE
d'un resultat deja consigne, ce qui ne se fait pas en reecrivant le registre.
"""

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

T0 = time.time()
DRY = os.environ.get("H74_DRY") == "1"
POOL, DRAWN = 80, 20

N_, M_, MAG = 624, 397, 0x9908B0DF
MT_BITS = 19937


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def berlekamp_massey(bits):
    """Complexite lineaire. Transcrit du §89 (h68), a la ligne pres."""
    C, B, L, mm, R = 1, 1, 0, 1, 0
    for n, b in enumerate(bits):
        R = (R << 1) | int(b)
        if (C & R).bit_count() & 1:
            T = C
            C ^= B << mm
            if 2 * L <= n:
                L, B, mm = n + 1 - L, T, 1
            else:
                mm += 1
        else:
            mm += 1
    return L


# ==========================================================================
# LES DEUX GENERATEURS, EN FLUX PARESSEUX
# ==========================================================================
def mt_words(state, count):
    """MT19937 : `count` mots temperes. Le temperage est F2-lineaire."""
    x, out = list(state), []
    for k in range(count):
        if k >= N_:
            y = (x[k - N_] & 0x80000000) | (x[k - N_ + 1] & 0x7FFFFFFF)
            x.append(x[k - N_ + M_] ^ (y >> 1) ^ (MAG if y & 1 else 0))
        v = x[k]
        v ^= v >> 11
        v ^= (v << 7) & 0x9D2C5680
        v ^= (v << 15) & 0xEFC60000
        v ^= v >> 18
        out.append(v & 0xFFFFFFFF)
    return out


def xs64_words(seed, count):
    """xorshift64 de Marsaglia : F2-lineaire, sortie brute."""
    s = seed & 0xFFFFFFFFFFFFFFFF
    out = []
    for _ in range(count):
        s ^= (s << 13) & 0xFFFFFFFFFFFFFFFF
        s ^= s >> 7
        s ^= (s << 17) & 0xFFFFFFFFFFFFFFFF
        out.append(s)
    return out


# ==========================================================================
# LES ECHANTILLONNEURS — ILS NE DIFFERENT QUE PAR LE PAS
# ==========================================================================
def decoupe(words, mode, ndraws, rng=None, p=0.0):
    """Rend (quartets du premier mot de chaque tirage, pas consommes).

    Dans TOUS les modes le bonus est le premier numero sorti, donc
    bonus - 1 = words[S_t] mod 80, donc son quartet vaut words[S_t] mod 16.
    SEUL LE PAS CHANGE.
    """
    nib, pas, s = [], [], 0
    for _ in range(ndraws):
        if s >= len(words):
            break
        nib.append(words[s] % 16)
        if mode == "fy":
            w = DRAWN
        elif mode == "rejet":
            vus, w = set(), 0
            while len(vus) < DRAWN and s + w < len(words):
                vus.add(words[s + w] % POOL)
                w += 1
        elif mode == "bernoulli":
            w = DRAWN + (1 if rng.random() < p else 0)
        else:
            raise ValueError(mode)
        pas.append(w)
        s += w
    return nib, pas


def complexites(nib, nbits=4):
    """Complexite lineaire de chacun des `nbits` flux de bits."""
    return [berlekamp_massey([(v >> b) & 1 for v in nib]) for b in range(nbits)]


# ==========================================================================
rule("1. LA CONDITION QUE LE §89 N'AVAIT PAS NOMMÉE")
# ==========================================================================

say(f"""   Le §89 mesure la complexite lineaire de la suite des bonus. Cette suite
   vaut b_t = phi(L^{{S_t}} x), ou S_t est la position, DANS LE FLUX DE MOTS,
   du premier mot du tirage t.

     pas CONSTANT   S_t = W t   -->   b_t = phi((L^W)^t x), lineaire
                    recurrente de complexite au plus n. BM la VOIT.

     pas VARIABLE   S_t marche aleatoire  -->  decimation a positions
                    irregulieres. Rien ne garantit la recurrence lineaire,
                    et si elle tombe, BM rend N/2 : « aleatoire ».

   Sous FISHER-YATES le pas vaut exactement {DRAWN}. Sous REJET il vaut {DRAWN} + r_t,
   avec r_t = 2,85 en moyenne (§94). Le §90 a verifie que le §89 tenait pour
   tout W FIXE — il n'a pas teste W VARIABLE, et ce n'est pas la meme chose.
""")


# ==========================================================================
rule("2. LE FAUX NÉGATIF, SUR MT19937 LUI-MÊME")
# ==========================================================================

NSYN = 3_000 if DRY else 45_000
CIBLE = MT_BITS
say(f"""   Meme generateur, meme etat initial, meme formule de bonus. UNE SEULE
   chose change : l'echantillonneur, donc le pas.

   {NSYN:,} tirages synthetiques. BM a besoin de 2L echantillons pour rendre L :
   avec {NSYN:,} tirages il peut donc constater jusqu'a {NSYN // 2:,}, et la cible
   MT19937 vaut {CIBLE:,}.
""")

rng = np.random.default_rng(20260831)
etat = [int(v) for v in rng.integers(0, 2 ** 32, N_, dtype=np.uint64)]
etat[0] = 0x80000000                       # etat non degenere

besoin = NSYN * 24 + 4000
say(f"   engendrement de {besoin:,} mots MT19937 ...")
mots = mt_words(etat, besoin)
say(f"   fait ({time.time() - T0:.1f} s)\n")

resultats = {}
say(f"   {'échantillonneur':>18} {'pas moyen':>10} {'pas min/max':>12} "
    f"{'complexité (4 bits)':>34}")
for mode in ("fy", "rejet"):
    nib, pas = decoupe(mots, mode, NSYN)
    L = complexites(nib)
    resultats[mode] = (L, float(np.mean(pas)), min(pas), max(pas), len(nib))
    say(f"   {mode:>18} {np.mean(pas):>10.2f} {f'{min(pas)}/{max(pas)}':>12} "
        f"{str(L):>34}")

Lfy, Lrj = resultats["fy"][0], resultats["rejet"][0]
PLAFOND = NSYN // 2 - 500          # critere du §89 : L doit etre loin de N/2
vu_fy = all(x <= CIBLE and x < PLAFOND for x in Lfy)
vu_rj = all(x <= CIBLE and x < PLAFOND for x in Lrj)

say(f"""
   LECTURE.

     FISHER-YATES : complexite {min(Lfy):,}–{max(Lfy):,}, contre la cible {CIBLE:,}.
     BM VOIT le generateur. C'est le regime que le §89 a valide sur temoin.

     REJET        : complexite {min(Lrj):,}–{max(Lrj):,}, contre N/2 = {NSYN // 2:,}.
     BM NE VOIT RIEN. La suite est indiscernable d'une suite aleatoire.

   ET C'EST LE MEME GENERATEUR, LE MEME ETAT, LA MEME FORMULE DE BONUS.
   Seul le pas differe : {resultats['fy'][1]:.2f} mots contre {resultats['rejet'][1]:.2f}.

   VERDICT : {'FAUX NEGATIF CONFIRME' if (vu_fy and not vu_rj) else 'NON CONCLUANT'}.""")

if PLAFOND < CIBLE:
    say(f"""
   ATTENTION — ESSAI SOUS-DIMENSIONNE. Avec {NSYN:,} tirages, BM ne peut
   constater au mieux que {PLAFOND:,}, ce qui est SOUS la cible {CIBLE:,}. Les deux
   colonnes rendent donc N/2 par construction et la comparaison ne prouve
   rien. Il faut au moins 2 x {CIBLE:,} = {2*CIBLE:,} tirages : c'est le mode complet.""")

if vu_fy and not vu_rj:
    say(f"""
   Le §89, applique a cette archive synthetique, aurait ecrit exactement sa
   phrase : « aucun generateur F2-lineaire d'etat sous 35 280 bits ». Et le
   generateur est MT19937, il est la, on connait son etat.

   SA CONCLUSION SUR L'ARCHIVE REELLE N'EST DONC PAS FAUSSE — elle est PLUS
   ETROITE QUE SON ENONCE. Elle exclut les generateurs F2-lineaires A PAS
   CONSTANT. Elle ne dit RIEN de ceux qui echantillonnent PAR REJET.""")


# ==========================================================================
rule("3. DE COMBIEN LE PAS DOIT-IL VARIER POUR AVEUGLER BM ?")
# ==========================================================================

say(f"""   Le rejet fait varier le pas de 2,85 mots en moyenne. C'est beaucoup.
   La question utile est : a partir de QUELLE variation BM decroche ?

   On prend xorshift64 — {64} bits d'etat, donc BM le voit avec 128
   echantillons — et un pas de {DRAWN} + Bernoulli(p) : une fraction p des
   tirages consomme UN mot de plus, les autres exactement {DRAWN}. p = 0 est le
   pas constant ; p = 1 l'est aussi (pas {DRAWN + 1}). Entre les deux, l'irregularite.
""")

NB = 200 if DRY else 900
REP = 3 if DRY else 12
CIBLE64 = 64
rng2 = np.random.default_rng(7)
say(f"   {NB:,} tirages par essai, {REP} graines par valeur de p, cible {CIBLE64} bits.\n")
say(f"   {'p':>7} {'complexité moyenne':>20} {'min':>7} {'max':>7} {'BM voit ?':>12}")
courbe = []
for p in (0.0, 0.002, 0.005, 0.01, 0.02, 0.05, 0.20, 0.50, 1.0):
    vals = []
    for r in range(REP):
        seed = int(rng2.integers(1, 2 ** 63))
        w = xs64_words(seed, NB * (DRAWN + 2) + 50)
        nib, _ = decoupe(w, "bernoulli", NB, rng=np.random.default_rng(1000 + r), p=p)
        vals.append(berlekamp_massey([v & 1 for v in nib]))
    m = float(np.mean(vals))
    voit = sum(1 for v in vals if v <= CIBLE64)
    courbe.append((p, m, min(vals), max(vals), voit))
    say(f"   {p:>7.3f} {m:>20.1f} {min(vals):>7} {max(vals):>7} {f'{voit}/{REP}':>12}")

decroche = next((p for p, m, lo, hi, v in courbe if v == 0 and p > 0), None)
if decroche:
    say(f"""
   LA FALAISE EST BRUTALE. A p = 0 la complexite vaut {courbe[0][1]:.0f} : BM voit le
   generateur sur les {REP} graines. Des que p atteint {decroche:g}, il ne le voit
   sur AUCUNE.

   Autrement dit : il suffit qu'environ UN TIRAGE SUR {round(1/decroche):,} consomme un mot de
   plus pour que Berlekamp-Massey devienne aveugle. Le rejet, lui, en fait
   varier PRESQUE TOUS — {100*(1 - 0.0746):.0f} % des tirages ont au moins un doublon (§94).

   LE §89 N'EST DONC PAS « PRESQUE » VALIDE SOUS REJET. Il l'est zero fois.""")
else:
    say(f"""
   AUCUNE VALEUR DE p TESTEE N'AVEUGLE BM SUR TOUTES LES GRAINES. Le
   decrochage est donc plus lent qu'annonce, et la section 2 doit etre
   relue a cette lumiere : c'est l'AMPLEUR de la variation du rejet, pas sa
   simple existence, qui aveugle BM.""")


# ==========================================================================
rule("4. CE QUE LE §89 EXCLUT VRAIMENT")
# ==========================================================================

say(f"""   L'enonce consigne au registre disait :

     « aucun generateur F2-lineaire dont l'etat tienne sous 35 280 bits »

   L'enonce correct est :

     « aucun generateur F2-lineaire dont l'etat tienne sous 35 280 bits ET
       QUI CONSOMME UN NOMBRE DE MOTS CONSTANT PAR TIRAGE »

   Ce qui reste couvert :
     — Fisher-Yates partiel (exactement {DRAWN} mots), et c'est l'echantillonneur
       le plus courant en bibliotheque ;
     — tout schema a budget fixe de mots.

   Ce qui SORT de la couverture, et qu'il faut desormais attaquer autrement :
     — l'echantillonneur par REJET, sous toutes ses variantes ;
     — tout schema dont la consommation depend des valeurs tirees.

   LE RESULTAT NUMERIQUE DU §89 NE BOUGE PAS. Les complexites mesurees sur
   l'archive reelle — 35 279, 35 281, 35 281, 35 281 pour N/2 = 35 280 —
   restent exactes. C'est leur INTERPRETATION qui retrecit.""")


# ==========================================================================
rule("5. CONSIGNATION, ET POURQUOI IL N'Y EN A PAS")
# ==========================================================================

say(f"""   RIEN N'EST CONSIGNE, et c'est un point de protocole, pas de paresse.

   1. Ce fichier ne teste pas l'archive. Il fabrique deux archives
      SYNTHETIQUES a generateur connu et constate ce que BM en dit. Il n'y a
      pas d'hypothese sur le tirage reel, donc pas de p a consigner.

   2. Il serait TENTANT de re-consigner h68 avec l'hypothese corrigee, ce
      que `lab.dedupe()` permettrait techniquement — la derniere ecriture
      d'un id ecrase les precedentes. CE SERAIT UNE FAUTE : reecrire une
      hypothese PRE-ENREGISTREE apres avoir vu le resultat est exactement ce
      que le pre-enregistrement interdit. L'entree de h68 reste telle
      qu'elle a ete scellee ; la correction de portee vit dans le rapport,
      datee et attribuee.

   Registre : INCHANGE, a dessein.""")


# ==========================================================================
rule("6. CE QUE CELA OUVRE POUR LA RECONSTITUTION")
# ==========================================================================

say(f"""   Une famille que le dossier croyait fermee ne l'est pas : les
   generateurs F2-lineaires a echantillonneur par REJET. Ils n'ont jamais
   ete testes que sur NEUF tirages ordonnes (§86) et CINQ (§61).

   ET LE §94 DIT OU CHERCHER. L'archive triee publie 27,26 bits par tirage
   sur la classe modulo 16 — dont 12,04 verifiables SANS affectation, par
   les quatre comptes de Hamming. Contre 3 bits d'inconnue de pas par
   tirage. Le budget est largement positif ; c'est l'algorithme qui manque,
   et le §94 dit precisement pourquoi : la contrainte est un multiensemble,
   pas une equation.

   CE QUI SERAIT LE PROCHAIN PAS, et il est nomme : une attaque qui prend le
   pas comme inconnue explicite et le multiensemble comme contrainte, sur
   les familles de petit etat ou l'enumeration reste possible. C'est le
   §61 avec 70 560 tirages au lieu de cinq.

   ({time.time() - T0:.1f} s)""")
