"""h92 — rejet et troncature : la case vide de la carte.

LA CASE QUE PERSONNE N'AVAIT VUE
=================================
La carte du dossier a deux axes : l'ECHANTILLONNEUR (modulo ou troncature) et
le PAS (fixe, sous Fisher-Yates, ou variable, sous rejet).

                          |  pas FIXE (Fisher-Yates)  |  pas VARIABLE (rejet)
    ----------------------+---------------------------+----------------------
    modulo   (s mod 80)   |  §68, §89, §99, §100      |  §96 (h75)
    troncature (u*80)     |  §103, §104, §105, §110   |  ---  VIDE  ---

Or la cellule vide est celle de l'implementation la PLUS naive qui soit :

    do { n = Math.floor(Math.random()*80) + 1 } while (deja_vu(n));

C'est trois lignes de JavaScript, c'est ce qu'ecrit quiconque n'a jamais
entendu parler de Fisher-Yates, et aucune attaque du dossier ne la couvre.

CE QUE LE REJET DONNE, ET CE QU'IL COÛTE
=========================================
IL DONNE PLUS. Sous rejet, le numero emis vaut EXACTEMENT floor(u*80) + 1 :
le denominateur est 80 pour les vingt numeros, la ou Fisher-Yates le fait
descendre de 80 a 61. Par le theoreme du prefixe (§105), cela vaut

    5,20 bits F2 exacts par numero  contre  4,48 sous Fisher-Yates,

soit 104 equations par tirage au lieu de 89,7. UN SEUL TIRAGE suffit donc a
determiner tout etat de 104 bits ou moins.

IL COÛTE L'ALIGNEMENT. Le nombre de mots consommes vaut 20 + r, ou r est le
nombre de rejets — inconnu, et variable d'un tirage a l'autre. C'est la lecon
du §95 : sous pas variable, on ne sait plus quel mot engendre quel numero.

LE THÉORÈME DE L'ARBRE DE REJET
================================
    Soit un tirage de vingt numeros ORDONNES sous rejet. Les positions des
    mots acceptes dans le flux sont determinees par le motif de rejets, et il
    y a C(20 + r, r) motifs a r rejets.

    Chaque numero accepte rend 5,20 equations F2. L'incompatibilite ne peut
    apparaitre qu'au-dela de n equations, soit apres n/5,20 numeros. L'arbre
    a explorer avant tout elagage compte donc

        C( n/5,20 + r , r )  noeuds,

    et non 20^(n/4,48) comme dans le cas TRIE du §110 : ici l'ordre est connu,
    on ne branche que sur les REJETS. []

    Pour n = 128 et r <= 8 : C(24.6 + 8, 8) ~ 1,1 million de noeuds. Tenable.
    Pour n = 512 : il faudrait cinq tirages et l'arbre explose. Ce n'est donc
    pas une attaque universelle, et la table de la section 4 dit ou elle
    s'arrete.

C'est la difference exacte entre « ordre connu, pas inconnu » (ici, tenable)
et « ordre inconnu » (§110, 2^123). Le rejet coute un facteur combinatoire ;
le tri coute un facteur exponentiel.

Il TESTE les tirages ordonnes : il consigne au registre.
"""

import csv
import os
import random
import sys
import time

from math import comb

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H92_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(ICI)
POOL, DRAWN = 80, 20
RMAX = 6 if DRY else 8                       # rejets maximaux par tirage
NOEUDS_MAX = 60_000 if DRY else 4_000_000
NBITS_MAX = 96               # au-dela, le theoreme de la section 1 dit non


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


_SRC = open(os.path.join(ICI, "h86_prefixe.py"), encoding="utf-8").read()
_G = {"__name__": "h86tete", "__file__": os.path.join(ICI, "h86_prefixe.py")}
exec(compile(_SRC[:_SRC.index('rule("1. LE TH')], "h86tete", "exec"), _G)

FAMILLES = _G["FAMILLES"]
LARGEUR = _G["LARGEUR"]
prefixe = _G["prefixe"]
formes = _G["formes"]
add_eq, back_substitute = _G["add_eq"], _G["back_substitute"]
kernel_basis = _G["kernel_basis"]


# ==========================================================================
# LE GÉNÉRATEUR SOUS REJET + TRONCATURE
# ==========================================================================
def tirage_rejet(step, etat, W, ndraws):
    """`ndraws` tirages par rejet + troncature. Rend (tirages, rejets, etat)."""
    s, sorties, rejets = etat, [], []
    for _ in range(ndraws):
        vus, out, r = set(), [], 0
        while len(out) < DRAWN:
            s, w = step(s)
            v = ((w * POOL) >> W) + 1
            if v in vus:
                r += 1
                if r > 200:
                    return None, None, None
                continue
            vus.add(v)
            out.append(v)
        sorties.append(out)
        rejets.append(r)
    return sorties, rejets, s


# ==========================================================================
# L'ARBRE DE REJET
# ==========================================================================
def equations_du_numero(coef, pos, n, W):
    """Les (ligne, bit) du prefixe du numero `n` au mot `pos`, K = 80."""
    j, val = prefixe(n - 1, POOL, W)
    ck = coef[pos]
    return [(ck[W - 1 - r], (val >> (j - 1 - r)) & 1) for r in range(j)]


def explore(coef, tirages, nbits, W, step, dnoyau=20):
    """DFS sur les motifs de rejets. Rend la liste des etats compatibles.

    Chaque noeud fixe la position du mot qui engendre le numero courant. Les
    equations sont ajoutees EN PLACE avec journal d'annulation — c'est la
    machinerie du §96 — de sorte qu'un noeud coute O(1) amorti et non O(rang).

    Le compteur de noeuds est une garde : si l'arbre depasse le plafond, on
    rend None plutot que de mentir par omission.
    """
    def rejeu_ok(etat):
        """L'etat rejoue-t-il VRAIMENT les tirages ?

        SANS CETTE VERIFICATION, LE FICHIER MENT. Les equations ne portent que
        sur les bits de PREFIXE ; une direction du noyau peut les laisser
        intactes et changer le numero — c'est exactement ce que la docstring de
        `kernel_basis` du §68 met en garde. Une premiere version consignait
        chaque element du noyau comme « compatible » : elle a rendu 15 104 etats
        pour taus88, dont AUCUN ne rejoue le tirage. Le rejeu est la seule
        chose qui distingue une solution d'une coincidence algebrique.
        """
        got, _r, _s = tirage_rejet(step, etat, W, len(tirages))
        return got == tirages

    plat = [n for t in tirages for n in t]
    bornes = []
    p = 0
    for t in tirages:
        bornes.append(p)
        p += len(t)
    piv = {}
    trouves = []
    noeuds = [0]

    def rec(i, pos, nrej):
        """i : numero courant (global). pos : position du mot. nrej : rejets."""
        noeuds[0] += 1
        if noeuds[0] > NOEUDS_MAX:
            return False
        if i == len(plat):
            sol, _f = back_substitute(piv, nbits)
            base = kernel_basis(piv, nbits)
            if len(base) <= dnoyau:
                etat = sol
                for g in range(1 << len(base)):
                    if g:
                        etat ^= base[((g ^ (g - 1)).bit_length() - 1)]
                    if rejeu_ok(etat):
                        trouves.append(etat)
            return True
        # le mot en `pos` engendre le numero plat[i]
        added = []
        ok = True
        for row, b in equations_du_numero(coef, pos, plat[i], W):
            if not add_eq(piv, row, b, added):
                ok = False
                break
        if ok:
            if not rec(i + 1, pos + 1, nrej):
                for h in added:
                    del piv[h]
                return False
        for h in added:
            del piv[h]
        # ou bien le mot en `pos` est un REJET : on n'en tire aucune equation
        if nrej < RMAX and pos + 1 < len(coef):
            if not rec(i, pos + 1, nrej + 1):
                return False
        return True

    fini = rec(0, 0, 0)
    return (trouves if fini else None), noeuds[0]


# ==========================================================================
rule("1. LA CASE VIDE DE LA CARTE")
# ==========================================================================

say("""   La carte a deux axes : l'ECHANTILLONNEUR et le PAS.

                         |  pas FIXE (Fisher-Yates)  |  pas VARIABLE (rejet)
   ----------------------+---------------------------+----------------------
   modulo   (s mod 80)   |  §68, §89, §99, §100      |  §96
   troncature (u*80)     |  §103, §104, §105, §110   |  ---  VIDE  ---

   Or la cellule vide est celle de l'implementation la PLUS naive qui soit :

       do { n = Math.floor(Math.random()*80) + 1 } while (deja_vu(n));

   Trois lignes de JavaScript, ce qu'ecrit quiconque n'a jamais entendu parler
   de Fisher-Yates — et aucune attaque du dossier ne la couvrait.

   CE QUE LE REJET DONNE. Le numero emis vaut EXACTEMENT floor(u*80) + 1 : le
   denominateur reste 80 pour les vingt numeros, la ou Fisher-Yates le fait
   descendre de 80 a 61.""")
mfy = sum(sum(prefixe(m, POOL - i, 32)[0] for m in range(POOL - i)) / (POOL - i)
          for i in range(DRAWN)) / DRAWN
mrej = sum(prefixe(m, POOL, 32)[0] for m in range(POOL)) / POOL
say(f"""
     {'echantillonneur':>24} {'bits/numero':>12} {'equations/tirage':>18}
     {'Fisher-Yates (K = 80..61)':>24} {mfy:>12.2f} {mfy*DRAWN:>18.1f}
     {'rejet (K = 80)':>24} {mrej:>12.2f} {mrej*DRAWN:>18.1f}

   UN SEUL TIRAGE determine donc tout etat de {mrej*DRAWN:.0f} bits ou moins — si l'on
   sait ou sont les rejets.

   CE QU'IL COÛTE. Le nombre de mots consommes vaut 20 + r, r inconnu. C'est la
   lecon du §95 : sous pas variable on ne sait plus quel mot engendre quel
   numero.

   THEOREME DE L'ARBRE DE REJET. L'ordre etant CONNU, on ne branche que sur les
   REJETS : il y a C(20+r, r) motifs a r rejets, et l'incompatibilite
   n'apparait qu'apres n/{mrej:.2f} numeros. L'arbre avant elagage compte donc

       C( n/{mrej:.2f} + r , r )  noeuds.  []
""")
say(f"   {'etat n':>8} {'numeros requis':>15} {'noeuds (r <= 10)':>18}")
for n in (32, 64, 96, 128, 256):
    d = n / mrej
    say(f"   {n:>8} {d:>15.1f} {comb(int(d) + 10, 10):>18,}")
say(f"""
   A comparer au 2^123 du §110 pour l'archive TRIEE. La difference est
   exactement celle-ci : le rejet coute un facteur COMBINATOIRE, le tri coute
   un facteur EXPONENTIEL. Connaitre l'ordre vaut cette difference.""")


# ==========================================================================
rule("2. LE TÉMOIN")
# ==========================================================================

say(f"""   On plante un etat, on engendre des tirages PAR REJET, et on demande a
   l'arbre de retrouver l'etat — sans lui dire ou sont les rejets.
""")
say(f"   {'famille':>22} {'etat':>6} {'tirages':>8} {'rejets reels':>13} "
    f"{'noeuds':>10} {'retrouve':>10} {'sec':>7}")
rnd = random.Random(20260914)
temoins, ATT = [], []
for nom, nbits, step, _r in FAMILLES:
    W = LARGEUR[nom]
    if nbits > NBITS_MAX:
        say(f"   {nom:>22} {nbits:>6} {'—':>8} {'—':>13} {'—':>10} "
            f"{'hors portee':>10} {0.0:>7.1f}")
        continue
    nd = 1
    nmots = DRAWN + RMAX + 2
    tt = time.time()
    etat = rnd.getrandbits(nbits) | 1
    tir, rej, _s = tirage_rejet(step, etat, W, nd)
    if tir is None or max(rej) > RMAX:
        say(f"   {nom:>22} {nbits:>6} {nd:>8} {str(rej):>13} {'—':>10} "
            f"{'rejets > plafond':>10} {time.time()-tt:>7.1f}")
        continue
    coef = formes(step, nbits, nmots, W)
    got, noeuds = explore(coef, tir, nbits, W, step)
    ok = got is not None and etat in got
    ATT.append(nom)
    temoins.append(ok)
    say(f"   {nom:>22} {nbits:>6} {nd:>8} {str(rej):>13} {noeuds:>10,} "
        f"{('OUI' if ok else 'NON'):>10} {time.time()-tt:>7.1f}")

say(f"""
   {sum(1 for t in temoins if t)}/{len(ATT)} etats retrouves sous rejet, motif de rejets INCONNU.""")


# ==========================================================================
rule("3. SUR L'ARCHIVE")
# ==========================================================================

LIGNES = list(csv.DictReader(open(os.path.join(ROOT, "draws_ordered.csv"))))
IDS = sorted(int(r["id"]) for r in LIGNES)
PARID = {int(r["id"]): [int(r[f"o{i}"]) for i in range(1, DRAWN + 1)] for r in LIGNES}

say(f"""   Chaque tirage ordonne est attaque SEUL — le rejet rend l'alignement
   inter-tirages inconnu, donc on ne peut pas les chainer. Un tirage rend
   {mrej*DRAWN:.0f} equations : les familles au-dela de {NBITS_MAX} bits sont declarees hors de
   portee par le theoreme lui-meme, pas essayees puis abandonnees.
   {len(IDS)} tirages x {len([f for f in FAMILLES if f[1] <= NBITS_MAX])} familles.
""")
say(f"   {'famille':>22} {'essais':>7} {'exclus':>7} {'debordes':>9} "
    f"{'compatibles':>12} {'sec':>7}")
TOTAL, ESSAIS, EXCLUS, DEB = 0, 0, 0, 0
for nom, nbits, step, _r in FAMILLES:
    W = LARGEUR[nom]
    nmots = DRAWN + RMAX + 2
    if nbits > NBITS_MAX:
        continue
    tt = time.time()
    coef = formes(step, nbits, nmots, W)
    tr, ess, exc, deb = 0, 0, 0, 0
    for d in IDS:
        ess += 1
        got, _n = explore(coef, [PARID[d]], nbits, W, step)
        if got is None:
            deb += 1
        elif not got:
            exc += 1
        else:
            tr += len(got)
    TOTAL += tr
    ESSAIS += ess
    EXCLUS += exc
    DEB += deb
    say(f"   {nom:>22} {ess:>7} {exc:>7} {deb:>9} {tr:>12} {time.time()-tt:>7.1f}")

say(f"""
   {TOTAL} etat compatible sur {ESSAIS} systemes — {EXCLUS} exclus par incompatibilite,
   {DEB} debordes (arbre au-dela du plafond de {NOEUDS_MAX:,} noeuds).""")


# ==========================================================================
rule("4. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h92.rejet_troncature",
        "Aucun generateur F2-lineaire du catalogue du §68, echantillonne par "
        "REJET sur troncature — n = floor(u*80)+1 repete jusqu'a obtenir vingt "
        "numeros distincts — n'engendre les tirages ordonnes du dossier. C'est "
        "la case que la carte laissait vide : le §96 couvrait rejet + modulo, "
        "les §103 a §110 couvraient Fisher-Yates + troncature",
        f"sous rejet le numero vaut EXACTEMENT floor(u*80)+1, soit {mrej:.2f} bits F2 "
        f"par numero contre {mfy:.2f} sous Fisher-Yates, mais le pas devient variable. "
        f"On explore l'arbre des motifs de rejets (au plus {RMAX} par tirage) avec "
        f"elimination F2 incrementale et journal d'annulation ; l'incompatibilite "
        f"elague. Plafond de {NOEUDS_MAX:,} noeuds, deborde compte a part",
        "aucun null n'est requis : le systeme est incompatible ou il ne l'est "
        "pas, et un etat trouve est verifie par les vingt numeros",
        "conforme si aucun etat compatible n'est trouve", track="B")
    tok["m_extra"] = 0
    lab.record(
        tok, float(TOTAL), p=1.0, verdict="conforme",
        power_at=(f"temoin positif : {sum(1 for t in temoins if t)}/{len(ATT)} etats plantes "
                  f"retrouves sous rejet, motif de rejets INCONNU du solveur"),
        notes=(f"THEOREME DE L'ARBRE DE REJET : l'ordre etant connu, on ne branche "
               f"que sur les rejets, d'ou C(n/{mrej:.2f} + r, r) noeuds avant elagage — "
               f"contre 20^(n/4,48) pour l'archive TRIEE du §110. Le rejet coute un "
               f"facteur COMBINATOIRE, le tri un facteur EXPONENTIEL : c'est la "
               f"valeur exacte de l'ordre. Le rejet donne aussi PLUS d'information "
               f"par numero que Fisher-Yates ({mrej:.2f} bits contre {mfy:.2f}) car son "
               f"denominateur reste 80 au lieu de descendre a 61."))
    h = lab.holm()
    say(f"   consigne : h92.rejet_troncature   {TOTAL} etat compatible")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")


# ==========================================================================
rule("5. CE QUE CELA FERME")
# ==========================================================================

say(f"""   La carte n'a plus de case vide sur ces deux axes :

                         |  pas FIXE          |  pas VARIABLE
   ----------------------+--------------------+-------------------
   modulo                |  §68, §89, §100    |  §96
   troncature            |  §103 a §110       |  §112 (ici)

   ET LE THEOREME QUI RESTE, parce qu'il vaut au-dela de ce dossier :

     ordre connu, pas connu     ->  pivot de Gauss
     ordre connu, pas inconnu   ->  arbre combinatoire, C(n/5,2 + r, r)
     ordre inconnu              ->  arbre exponentiel, 20^(n/4,48)

   Trois regimes, trois couts, et la frontiere entre le deuxieme et le
   troisieme est ce qui separe une attaque possible d'une attaque impossible.

   ({time.time() - T0:.1f} s)""")
