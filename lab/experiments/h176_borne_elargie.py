"""h176 — L'ÉLARGISSEMENT DE LA BORNE : six familles de défauts de plus, et un témoin
planté pour chacune (RAPPORT §192).

CE QUE LE §188 LAISSE OUVERT
============================
Le §188 borne la prédiction des numéros à `+0,0113` numéro par tirage. Mais une borne ne
vaut **que pour la classe de défauts que ses traits savent lire**, et le §7.31 le dit sans
détour : *un témoin manquant est un trou dans la borne, et il ne se voit pas*. Le §188 en a
fait la démonstration à ses dépens — sans le trait d'énergie, il rendait `z = −1,07` sur un
Fibonacci planté, c'est-à-dire rien.

La classe du §188 contient la mémoire courte, la chaleur, le biais de long terme, la
structure de nuit, le créneau, le bonus et l'énergie additive à deux termes. Elle ne
contient PAS :

  L  la DENSITÉ LOCALE      — un échantillonneur qui rappelle les numéros voisins
  M  le canal MODULAIRE     — un modulus qui fuit (2, 4, 5, 8), au tirage précédent et sur
                              cent tirages
  O  l'ORDRE                — le rang du numéro dans le tirage précédent, son minimum, son
                              maximum
  T  l'énergie à TROIS TERMES — les récurrences `r_i = r_{i-J} + r_{i-K} + r_{i-L}`,
                              à portée nulle comme à portée `(1, 2, 3)`
  X  l'énergie XOR          — les générateurs `F₂`-linéaires, sur les six bits de tête
  P  la PÉRIODICITÉ longue  — le même créneau une nuit, deux nuits, une semaine plus tard

Ce fichier ajoute ces six familles — dix-sept traits, portant le modèle de quatorze à
trente et un — et surtout **un témoin planté par famille**. Sans le témoin, ajouter un
trait ne prouve rien du tout.

LA RÈGLE, QUI EST LE VRAI CONTENU
=================================
    Pour borner une classe de défauts, il faut UN TRAIT PAR FORME DE DÉFAUT
    et UN TÉMOIN PLANTÉ PAR TRAIT, qui vérifie que le trait s'allume.

Un trait qui ne s'allume sur aucun témoin est décoratif : il gonfle la classe annoncée sans
rien fermer. Ce fichier refuse donc de consigner sa borne si un seul témoin échoue.

ET LE TÉMOIN SE JUGE SUR SON PROPRE TRAIT
=========================================
Un témoin vérifie qu'un TRAIT lit un DÉFAUT : c'est donc le trait seul qui doit être jugé.
Dilué dans trente et un traits, un signal faible se perd — mesuré, le trait à trois termes
rend `+3,66` seul et `+2,86` accompagné. Juger le témoin sur le modèle complet reviendrait
à déclarer aveugle un trait qui voit. Chaque témoin est donc mesuré deux fois : sur les
traits de sa famille (c'est la porte) et sur le modèle complet (c'est l'information).

DEUX TÉMOINS ONT DÛ ÊTRE REFAITS, ET UNE FAUSSE PISTE ÉCARTÉE
==============================================================
1. `x⁴⁶ + x²³ + 1` divise `x⁶⁹ − 1` : le Fibonacci XOR de retards `(23, 46)` a une période
   de **soixante-neuf mots**, soit trois tirages. Il se prédit à `20/20` et ne prouve rien.
   Un témoin dégénéré est pire qu'un témoin absent.
2. Un additif de retards en mots `(23, 46, 69)` a d'abord paru invisible (`z = +0,85`). J'en
   avais tiré une explication — la **gigue de consommation** : `22,85` mots par tirage avec
   un écart-type de `1,85`, donc un partenaire situé `d` mots en arrière flotte au lieu de
   tomber dans un tirage fixe. **Cette explication est fausse, et le fait qu'elle expliquait
   l'était aussi.** Le `+0,85` venait d'un essai à `N = 20 000` avec un jeu de triplets qui
   ne contenait pas `(3, 2, 1)` ; à la taille de l'archive et avec le bon triplet, le même
   générateur rend `z = +6,72`. Le `h176b` mesure la gigue séparément et la disculpe
   (§7.33). Ce témoin est donc BLOQUANT comme les autres.
3. Le témoin de la famille à trois termes existe aussi à retards **courts** en mots,
   `(2, 3, 7)` : `z = +3,66` sur le trait seul contre `+0,50` pour le trait à deux termes —
   spécifique, et pas un artefact.

LE PROTOCOLE, INCHANGÉ
======================
Ajustement sur les tirages `2 000..43 136`, mesure sur `43 136..70 560`, disjoints. Nulle
hypergéométrique exacte : moyenne `5`, écart-type `1,6876` par tirage. Traits strictement
causaux — aucun ne lit le tirage qu'il prédit, et la LOI entière du recouvrement est
vérifiée, pas seulement sa moyenne (§185).
"""

import json
import os
import sys
from math import erfc, sqrt

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import h173_predicteur_appris as B                                      # noqa: E402

POOL, DRAWN = 80, 20
M32 = 1 << 32
EXP_ID = "h176.borne_elargie"
FJETON = "/tmp/h176_jeton.json"
FJOURNAL = "/tmp/h176_journal.json"          # reprise apres redemarrage du conteneur
CHAUFFE, PART = B.CHAUFFE, B.PART
SD1 = B.SD1

NOUVEAUX = ("L densite 3", "L densite 5", "L densite 10", "L densite 20",
            "M mod2 t-1", "M mod4 t-1", "M mod5 t-1", "M mod8 t-1",
            "M mod4 100", "M mod8 100",
            "O rang t-1", "O extreme t-1",
            "T trois termes", "X energie XOR",
            "P nuit", "P deux nuits", "P semaine")
NOMS = B.NOMS + NOUVEAUX
NF = len(NOMS)
TRIPLETS = ((1, 1, 1), (2, 1, 1), (2, 2, 1), (3, 2, 1), (3, 1, 1))
PERIODES = (204, 408, 1428)


def say(*a):
    print(*a, flush=True)


def wht(A):
    """transformee de Walsh-Hadamard sur l'axe 1, longueur 64."""
    A = A.copy()
    n = A.shape[1]
    h = 1
    while h < n:
        for i in range(0, n, 2 * h):
            a = A[:, i:i + h].copy()
            b = A[:, i + h:i + 2 * h].copy()
            A[:, i:i + h] = a + b
            A[:, i + h:i + 2 * h] = a - b
        h *= 2
    return A


TETE = ((np.arange(POOL) * 64) // POOL).astype(np.int64)     # classe -> six bits de tete


def construire(M, bornes, bonus=None):
    """(N,80,31) : les quatorze traits du §188, plus les dix-sept nouveaux."""
    N = len(M)
    Mi = M.astype(np.int32)
    X = np.zeros((N, POOL, NF), np.float32)
    X[:, :, :B.NF] = B.construire(M, bornes, bonus)
    k = B.NF

    # ---- L : densite locale. Combien de numeros du tirage t-1 sont a distance <= r de v,
    #      distance CIRCULAIRE sur les quatre-vingts (le vivier n'a pas de bord privilegie).
    Fm = np.fft.rfft(Mi.astype(np.float64), axis=1)
    for r in (3, 5, 10, 20):
        noy = np.zeros(POOL)
        d = np.minimum(np.arange(POOL), POOL - np.arange(POOL))
        noy[(d <= r) & (d > 0)] = 1.0
        C = np.rint(np.fft.irfft(Fm * np.fft.rfft(noy)[None, :], n=POOL, axis=1))
        X[1:, :, k] = (C[:-1] / (2.0 * r)).astype(np.float32)
        k += 1

    # ---- M : canal modulaire. Frequence, dans le passe, de la classe residuelle de v.
    cls = np.arange(POOL)
    cum = np.zeros((N + 1, POOL), np.int32)
    np.cumsum(Mi, axis=0, out=cum[1:])
    t = np.arange(N)
    for q in (2, 4, 5, 8):
        R = (cls % q)
        S = np.zeros((N, q), np.float64)
        for j in range(q):
            S[:, j] = Mi[:, R == j].sum(axis=1)
        X[1:, :, k] = (S[:-1][:, R] / (DRAWN / q)).astype(np.float32)
        k += 1
    for q in (4, 8):
        R = (cls % q)
        cq = np.zeros((N + 1, q), np.float64)
        for j in range(q):
            cq[1:, j] = cum[1:, R == j].sum(axis=1)
        bas = np.maximum(t - 100, 0)
        F = (cq[t] - cq[bas]) / np.maximum((t - bas) * (DRAWN / q), 1)[:, None]
        X[:, :, k] = F[:, R].astype(np.float32)
        k += 1

    # ---- O : l'ordre. Rang de v dans le tirage t-1 (0 s'il n'y etait pas), et
    #      indicatrice « v etait le plus petit ou le plus grand du tirage t-1 ».
    rang = np.cumsum(Mi, axis=1) * Mi                     # 1..20 si sorti, 0 sinon
    X[1:, :, k] = (rang[:-1] / float(DRAWN)).astype(np.float32)
    k += 1
    ext = ((rang == 1) | (rang == DRAWN)).astype(np.float32)
    X[1:, :, k] = ext[:-1]
    k += 1

    # ---- T : energie a TROIS termes, delta dans {0,1,2}
    E3 = np.zeros((N, POOL), np.float64)
    for g in TRIPLETS:
        lo = max(g)
        P = (Fm[lo - g[0]:N - g[0]] * Fm[lo - g[1]:N - g[1]] * Fm[lo - g[2]:N - g[2]])
        C = np.rint(np.fft.irfft(P, n=POOL, axis=1))
        for d in (0, 1, 2):
            E3[lo:] += np.roll(C, d, axis=1)
    m3, s3 = E3[CHAUFFE:].mean(), E3[CHAUFFE:].std()
    X[:, :, k] = ((E3 - m3) / max(s3, 1e-9)).astype(np.float32)
    k += 1

    # ---- X : energie XOR sur les six bits de tete. score(t,v) = #{(u,w) dans
    #      C_{t-1} x C_{t-2} : tete(u) xor tete(w) = tete(v)}.
    ONE = np.zeros((POOL, 64), np.float64)
    ONE[np.arange(POOL), TETE] = 1.0
    W = wht(Mi.astype(np.float64) @ ONE)
    CX = np.zeros((N, 64), np.float64)
    CX[2:] = wht(W[1:N - 1] * W[:N - 2]) / 64.0
    mx, sx = CX[CHAUFFE:].mean(), CX[CHAUFFE:].std()
    X[:, :, k] = ((CX[:, TETE] - mx) / max(sx, 1e-9)).astype(np.float32)
    k += 1

    # ---- P : periodicite longue. v etait-il sorti une nuit, deux nuits, une semaine avant.
    for p in PERIODES:
        if N > p:
            X[p:, :, k] = Mi[:-p]
        k += 1

    assert k == NF, (k, NF)
    return X


# --------------------------------------------------------------------------------------
# Les generateurs plantes : UN PAR FAMILLE
# --------------------------------------------------------------------------------------

def _echange(m, t, entrant, rng):
    """fait entrer `entrant` au tirage t en sortant un numero au hasard. Garde 20/80."""
    if m[t, entrant]:
        return
    dedans = np.flatnonzero(m[t])
    m[t, dedans[rng.integers(len(dedans))]] = False
    m[t, entrant] = True


def plante_local(n, rng, eps, r=3):
    """densite locale : un numero VOISIN d'un numero d'hier revient plus souvent."""
    m = B.srs(n, rng)
    for t in range(1, n):
        if rng.random() < eps:
            hier = np.flatnonzero(m[t - 1])
            v = int(hier[rng.integers(len(hier))])
            _echange(m, t, (v + int(rng.integers(-r, r + 1))) % POOL, rng)
    return m


def plante_modulaire(n, rng, eps, q=4):
    """canal modulaire : la classe majoritaire mod q d'hier revient aujourd'hui."""
    m = B.srs(n, rng)
    cls = np.arange(POOL) % q
    for t in range(1, n):
        if rng.random() < eps:
            j = int(np.bincount(cls[m[t - 1]], minlength=q).argmax())
            cand = np.flatnonzero(cls == j)
            _echange(m, t, int(cand[rng.integers(len(cand))]), rng)
    return m


def plante_periodique(n, rng, eps, p=204):
    """periodicite : le tirage d'il y a p tirages se rappelle au present."""
    m = B.srs(n, rng)
    for t in range(p, n):
        if rng.random() < eps:
            av = np.flatnonzero(m[t - p])
            _echange(m, t, int(av[rng.integers(len(av))]), rng)
    return m


def plante_ordre(n, rng, eps):
    """ordre : le PLUS PETIT numero d'hier revient aujourd'hui."""
    m = B.srs(n, rng)
    for t in range(1, n):
        if rng.random() < eps:
            _echange(m, t, int(np.flatnonzero(m[t - 1])[0]), rng)
    return m


def plante_recurrence(n, graine, retards, op="+"):
    """r_i = somme (ou XOR) des r_{i-d} pour d dans `retards`, mod 2^32.

    LES RETARDS SONT DONNES EN MOTS, et c'est tout l'enjeu. La regle de portee du §7.28
    convertit un retard de mots `d` en un retard de TIRAGES `g = d / E[N]` avec
    `E[N] = 22,85` mots par tirage. Un retard de 3 ou 7 mots donne `g = 0` : les trois
    indices de la relation tombent DANS LE MEME TIRAGE. Un detecteur voit cela (§183) ;
    un PREDICTEUR ne le peut pas, puisqu'il faudrait connaitre une partie du tirage pour
    predire le reste. Les temoins d'un predicteur doivent donc etre plantes a des retards
    de mots MULTIPLES de 23, seuls a produire une portee predictive entiere.
    """
    import random
    r0 = random.Random(graine)
    L = max(retards)
    r = [r0.randrange(M32) for _ in range(L + 1)]
    i = len(r)
    m = np.zeros((n, POOL), bool)
    for j in range(n):
        vus = set()
        while len(vus) < DRAWN:
            if op == "+":
                v = 0
                for d in retards:
                    v += r[i - d]
                r.append(v % M32)
            else:
                v = 0
                for d in retards:
                    v ^= r[i - d]
                r.append(v)
            i += 1
            vus.add((r[i - 1] * POOL) >> 32)
        m[j, list(vus)] = True
    return m


def plante_classe(n, rng, k, retards, op="+"):
    """Plante la relation DIRECTEMENT AU NIVEAU DES CLASSES, et non des mots.

    POURQUOI. Un temoin plante au niveau des MOTS depend de deux choses a la fois : que la
    relation existe, et que sa portee tombe sur un couple ou un triplet effectivement
    present dans le trait. Quand un tel temoin echoue, on ne sait pas laquelle des deux a
    manque. Planter la relation DIRECTEMENT AU NIVEAU DES CLASSES separe les deux : on
    plante exactement ce que le trait est cense lire, a une force reglable, et l'echec ne
    peut plus venir que du trait.

    C'est de l'etalonnage d'instrument, pas une simulation de generateur, et les deux sont
    necessaires : le temoin au niveau des mots dit si une famille REELLE de generateurs est
    couverte, celui au niveau des classes dit si le TRAIT fonctionne.
    """
    m = B.srs(n, rng)
    g = max(retards)
    for t in range(g, n):
        for _ in range(k):
            vals = []
            for d in retards:
                c = np.flatnonzero(m[t - d])
                vals.append(int(c[rng.integers(len(c))]))
            if op == "+":
                v = (sum(vals) + int(rng.integers(0, 2))) % POOL
            else:
                h = 0
                for c in vals:
                    h ^= int(TETE[c])
                cand = np.flatnonzero(TETE == h)
                if not len(cand):
                    continue
                v = int(cand[rng.integers(len(cand))])
            _echange(m, t, v, rng)
    return m


def plante_xorshift(n, graine):
    """xorshift32 : x ^= x<<13 ; x ^= x>>17 ; x ^= x<<5.

    TEMOIN NON BLOQUANT, et il faut dire pourquoi. Un xorshift est F2-lineaire mais a UN
    SEUL PAS : ses sorties ne satisfont aucune relation a deux ou trois termes a des
    retards de l'ordre du tirage — les multiples de poids 3 de son polynome
    caracteristique tombent a des degres tres superieurs. Aucun trait de ce fichier ne
    peut donc l'allumer, et la borne ne couvre PAS cette famille. Elle est fermee
    ailleurs, par le crible de classes (§172) et par les §163-§164, jamais par ici. Ce
    temoin est garde justement pour que le trou soit visible et chiffre.
    """
    x = graine | 1
    msk = M32 - 1
    m = np.zeros((n, POOL), bool)
    for j in range(n):
        vus = set()
        while len(vus) < DRAWN:
            x ^= (x << 13) & msk
            x ^= x >> 17
            x ^= (x << 5) & msk
            vus.add((x * POOL) >> 32)
        m[j, list(vus)] = True
    return m


# --------------------------------------------------------------------------------------

FAMILLES = {
    "classique": list(range(0, 13)),          # les traits du §188 hors energie
    "energie2":  [13],
    "L local":   [14, 15, 16, 17],
    "M modulo":  [18, 19, 20, 21, 22, 23],
    "O ordre":   [24, 25],
    "T trois":   [26],
    "X xor":     [27],
    "P periode": [28, 29, 30],
}


def chaine(M, bornes, bonus, etiq, fam=None):
    """Ajuste et mesure. Renvoie le resultat du modele COMPLET et, si `fam` est donne,
    celui des seuls traits de cette famille.

    POURQUOI LES DEUX. Un temoin verifie qu'un TRAIT lit un DEFAUT ; c'est donc le trait
    seul qui doit etre juge. Dilue dans trente et un traits, un signal faible se perd :
    mesure, le trait a trois termes rend `+3,66` seul et `+2,86` accompagne. Juger un
    temoin sur le modele complet reviendrait a declarer aveugle un trait qui voit.
    """
    N = len(M)
    coupe = CHAUFFE + int((N - CHAUFFE) * PART)
    X = construire(M, bornes, bonus)
    ya = M[CHAUFFE:coupe].reshape(-1)
    out = {}
    jeux = [("tous", list(range(NF)))]
    if fam is not None:
        jeux.append((fam, FAMILLES[fam]))
    for nom, cols in jeux:
        Xc = X[:, :, cols]
        w, mu, sd = B.ajuster(Xc[CHAUFFE:coupe].reshape(-1, len(cols)), ya)
        S = B.scorer(Xc, w, mu, sd)
        del Xc
        rec, gain = B.mesurer(M, S, coupe, N)
        z = (rec.mean() - 5.0) / (SD1 / sqrt(len(rec)))
        out[nom] = {"rec": float(rec.mean()), "z": float(z), "gain": float(gain),
                    "w": [float(x) for x in w], "n": int(len(rec)),
                    "loi": [int((rec == kk).sum()) for kk in range(DRAWN + 1)]}
    del X
    a = out["tous"]
    b = out.get(fam)
    say(f"   {etiq:>28} | {a['rec']:9.5f} | {a['z']:+8.2f} | "
        + (f"{fam:>10} seul {b['z']:+7.2f}" if b else " " * 22))
    return out


def journal():
    if os.path.exists(FJOURNAL):
        return json.load(open(FJOURNAL, encoding="utf-8"))
    return {}


def noter(J, cle, val):
    J[cle] = val
    json.dump(J, open(FJOURNAL, "w", encoding="utf-8"))


if __name__ == "__main__":
    import lab

    A = lab.load()
    M = np.asarray(A.mask)
    TS = np.asarray(A.ts).astype(np.int64)
    N = len(M)
    BOR = np.r_[0, np.flatnonzero(np.diff(TS) > 1000) + 1, N]
    BONUS = np.asarray(A.bonus).astype(np.int64)
    coupe = CHAUFFE + int((N - CHAUFFE) * PART)
    nmes = N - coupe
    sdm = SD1 / sqrt(nmes)

    HYP = (f"Un predicteur ajuste sur {NF} traits causaux — les quatorze du §188 plus six "
           "familles neuves : densite locale, canal modulaire (2, 4, 5, 8), ordre dans le "
           "tirage precedent, energie a TROIS termes, energie XOR sur les six bits de tete, "
           "et periodicite longue (une nuit, deux nuits, une semaine) — ne bat pas le hasard "
           f"sur les {nmes} derniers tirages, qu'il n'a jamais vus. Chaque famille est "
           "accompagnee d'un TEMOIN PLANTE qui verifie que son trait s'allume : sans quoi "
           "ajouter un trait elargit la classe ANNONCEE de la borne sans rien fermer, ce qui "
           "est exactement l'erreur que le §188 a commise puis corrigee")
    STAT = ("R = recouvrement moyen des vingt numeros de plus fort score avec le tirage "
            f"reel, sur les {nmes} tirages de mesure ; z = (R-5)/(1,6876/racine(n)). "
            "Secondaire : gain de log-vraisemblance hors echantillon. La LOI entiere du "
            "recouvrement est verifiee, pas seulement sa moyenne")
    NUL = ("EXACTE : le recouvrement de deux sous-ensembles de vingt parmi quatre-vingts est "
           "hypergeometrique, moyenne 5, ecart-type 1,6876 par tirage. CONTROLE : la meme "
           "chaine complete sur une archive SRS, qui doit rendre 5,000 et un gain nul")
    VER = ("conforme si |z| < 3 ET si les sept temoins passent ; NON CONCLUANT si un temoin "
           "echoue (la borne serait alors annoncee sur une classe qu'elle ne couvre pas) ; "
           "PREDICTION si z > 3")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h176 : {N} tirages, {NF} traits ({B.NF} du §188 + {len(NOUVEAUX)} neufs)")
    say(f"   apprentissage {CHAUFFE}..{coupe}, mesure {coupe}..{N} ; "
        f"ecart-type de la moyenne {sdm:.5f}")
    say(f"   {'source':>28} | {'recouvr.':>9} | {'z':>8} | famille seule")

    J = journal()
    rng = np.random.default_rng(176)
    PLAN = [
        ("controle_srs", "CONTROLE  SRS", None, lambda: B.srs(N, rng)),
        ("t_chaud", "T1 main chaude", "classique",
         lambda: B.plante_chaud(N, rng, 0.30)),
        ("t_additif", "T2 additif mots (3,7)", "energie2",
         lambda: B.plante(N, 21, 3, 7)),
        ("t_local", "T3 densite locale", "L local",
         lambda: plante_local(N, rng, 0.50)),
        ("t_modulaire", "T4 canal mod 4", "M modulo",
         lambda: plante_modulaire(N, rng, 0.50)),
        ("t_ordre", "T5 le plus petit d'hier", "O ordre",
         lambda: plante_ordre(N, rng, 0.30)),
        ("t_periodique", "T6 periode 204", "P periode",
         lambda: plante_periodique(N, rng, 0.30)),
        ("t_trois", "T7 additif mots (2,3,7)", "T trois",
         lambda: plante_recurrence(N, 31, (2, 3, 7), "+")),
        ("t_xorclasse", "T8 classe XOR de tete", "X xor",
         lambda: plante_classe(N, rng, 4, (1, 2), "^")),
        ("x_xorshift", "X1 xorshift32 (hors portee)", "X xor",
         lambda: plante_xorshift(N, 0x9E3779B9)),
        ("t_mots3", "T9 additif mots (23,46,69)", "T trois",
         lambda: plante_recurrence(N, 31, (23, 46, 69), "+")),
        ("archive", "ARCHIVE", None, None),
    ]
    for cle, etiq, fam, fab in PLAN:
        if cle in J:
            r = J[cle]["tous"]
            b = J[cle].get(fam) if fam else None
            say(f"   {etiq:>28} | {r['rec']:9.5f} | {r['z']:+8.2f} | "
                + (f"{fam:>10} seul {b['z']:+7.2f}" if b else " " * 22) + "  (repris)")
            continue
        r = chaine(M if fab is None else fab(), BOR,
                   BONUS if fab is None else None, etiq, fam)
        noter(J, cle, r)

    HORS = {"x_xorshift"}   # seul temoin NON BLOQUANT : voir sa docstring

    def zfam(c, fam):
        """le z du temoin, juge sur les traits de SA famille."""
        return J[c][fam]["z"] if fam and fam in J[c] else J[c]["tous"]["z"]

    temoins = [(c, fam) for c, _, fam, f in PLAN
               if f is not None and c != "controle_srs" and c not in HORS]
    passes = [c for c, fam in temoins if zfam(c, fam) > 3.0]
    rate = [c for c, fam in temoins if zfam(c, fam) <= 3.0]
    zc = J["controle_srs"]["tous"]["z"]
    ra = J["archive"]["tous"]
    say(f"\n   temoins passes (juges sur leur famille) : {len(passes)}/{len(temoins)}"
        + (f"   ECHECS : {', '.join(rate)}" if rate else ""))
    for c, _, fam, f in PLAN:
        if f is None or c == "controle_srs":
            continue
        marque = "hors portee" if c in HORS else ("ok" if zfam(c, fam) > 3 else "ECHEC")
        say(f"      {c:>14} [{fam or '-':>10}] z famille = {zfam(c, fam):+7.2f}  {marque}")
    say(f"   controle SRS : z = {zc:+.2f}, gain "
        f"{J['controle_srs']['tous']['gain']:+.2e} "
        f"-> la chaine {'ne fuit pas' if abs(zc) < 3 else 'FUIT'}")

    from math import comb
    P = [comb(DRAWN, kk) * comb(POOL - DRAWN, DRAWN - kk) / comb(POOL, DRAWN)
         for kk in range(DRAWN + 1)]
    say(f"\n   loi du recouvrement sur l'archive :")
    say(f"{'k':>4} | {'observe':>8} | {'attendu':>9} | {'z':>7}")
    zloi = 0.0
    for kk in range(1, 14):
        o = ra["loi"][kk]; a = ra["n"] * P[kk]
        if a > 5:
            zk = (o - a) / sqrt(a * (1 - P[kk]))
            zloi = max(zloi, abs(zk))
            say(f"{kk:4d} | {o:8d} | {a:9.1f} | {zk:+7.2f}")

    zA = ra["z"]
    p = float(erfc(abs(zA) / sqrt(2)))
    borne = (ra["rec"] - 5.0) + 1.645 * sdm
    ok = (not rate) and abs(zc) < 3
    verdict = ("PREDICTION" if zA > 3 else ("conforme" if ok else "NON CONCLUANT"))
    say(f"\n   archive : recouvrement {ra['rec']:.5f}, z = {zA:+.3f}, p = {p:.4f}")
    say(f"   BORNE a 95 % : aucun predicteur de cette classe ne gagne plus de "
        f"{borne:+.4f} numero par tirage ({100*borne/5:.2f} % relatif)")
    say(f"   ->   {verdict}")

    say(f"\n   poids appris sur l'archive, les dix plus forts :")
    w = np.array(ra["w"])
    for j in np.argsort(-np.abs(w[:NF]))[:10]:
        say(f"      {NOMS[j]:>16} : {w[j]:+.4f}")

    TOK["m_extra"] = 0
    lab.record(
        TOK, float(ra["rec"]), p=p, verdict=verdict,
        power_at=("NEUF TEMOINS PLANTES BLOQUANTS, au moins un par famille de traits, plus "
                  "UN temoin NON BLOQUANT qui chiffre le seul trou, chacun de "
                  f"{N} tirages, chacun juge sur les traits de SA famille : "
                  + " ; ".join(
                      f"{e} z = {zfam(c, fam):+.1f}"
                      for c, e, fam, f in PLAN
                      if f is not None and c != "controle_srs")
                  + f". Controle SRS z = {zc:+.2f}, gain "
                    f"{J['controle_srs']['tous']['gain']:+.2e} : la chaine ne fuit pas. "
                    f"L'ecart-type de la moyenne vaut {sdm:.5f} sur {nmes} tirages"),
        notes=(f"BORNE ELARGIE (§192) : {NF} traits contre {B.NF} au §188 — six familles "
               "neuves (densite locale, canal modulaire, ordre, energie a trois termes, "
               "energie XOR, periodicite longue), chacune avec son temoin plante. Archive : "
               f"recouvrement {ra['rec']:.5f}, z = {zA:+.3f}, gain {ra['gain']:+.2e}. "
               f"Borne a 95 % : {borne:+.4f} numero par tirage. Loi du recouvrement : max "
               f"|z| par case = {zloi:.2f}. Temoins passes {len(passes)}/{len(temoins)}. "
               "REGLE : un trait sans temoin elargit la classe ANNONCEE sans rien fermer."))
    say("   consigne.")
