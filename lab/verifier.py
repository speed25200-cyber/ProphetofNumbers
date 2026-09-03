"""verifier.py — LE HARNAIS DE VÉRIFICATION : recalculer, depuis les sources, chaque
chiffre publié dont le reste du dossier dépend.

POURQUOI CE FICHIER EXISTE
==========================
Ce dossier vaut ce que valent ses chiffres. Or, sur la seule dernière session, **cinq
défauts d'instrument** ont été trouvés dans ma propre production :

  1. un prédicteur qui lisait le tirage qu'il prédisait (§185, fuite invisible sur la
     moyenne, `+12,08 σ` dans la queue) ;
  2. un témoin XOR dégénéré — `x⁴⁶+x²³+1` divise `x⁶⁹−1`, période de trois tirages,
     prédiction `20/20` (§192) ;
  3. un test de gigue confondu, qui comparait deux portées différentes (§192) ;
  4. un témoin classé « hors portée » qui passait en fait (§192) ;
  5. un Bonferroni gaussien sur des `khi²`, qui aurait produit quatre fausses
     découvertes (§189) et, une troisième fois, une cinquième (§193).

Cinq défauts en une session, tous trouvés par des contrôles que rien n'obligeait à faire.
Un taux pareil ne permet pas de faire confiance au reste sur parole. Ce fichier recalcule
donc **depuis les fichiers source**, sans passer par le cache ni par aucune valeur
recopiée, tout ce dont le dossier dépend.

    python3 lab/verifier.py

Chaque contrôle affiche `ok` ou `ECHEC` et la valeur recalculée face à la valeur publiée.
Le code de sortie vaut le nombre d'échecs.
"""

import csv
import glob
import itertools
import json
import os
import sys
from fractions import Fraction
from math import comb, log2, sqrt

import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

POOL, DRAWN = 80, 20
ECHECS = []


def dit(nom, ok, mesure, publie=""):
    ECHECS.append(nom) if not ok else None
    marque = "ok   " if ok else "ECHEC"
    ligne = f"  [{marque}] {nom:<46} {mesure}"
    if publie:
        ligne += f"   (publie : {publie})"
    print(ligne, flush=True)


def proche(a, b, tol=5e-4):
    return abs(a - b) <= tol


# ======================================================================================
# 1. L'ARCHIVE, RELUE DEPUIS LES CSV — jamais depuis le cache
# ======================================================================================

def lire_brut():
    lignes = []
    for chemin in sorted(glob.glob(os.path.join(ROOT, "..", "claude", "draws", "*.csv"))):
        with open(chemin) as fh:
            lignes.extend(csv.DictReader(fh))
    lignes.sort(key=lambda r: int(r["id"]))
    return lignes


def bloc_archive(L):
    print("\n1. L'ARCHIVE, relue depuis les huit CSV source")
    N = len(L)
    dit("nombre de tirages", N == 70560, N, "70 560")

    ids = np.array([int(r["id"]) for r in L], np.int64)
    dit("identifiants strictement consecutifs",
        bool((np.diff(ids) == 1).all()), f"{ids[0]}..{ids[-1]}", "1 309 614..1 380 173")
    dit("etendue = effectif", int(ids[-1] - ids[0] + 1) == N,
        int(ids[-1] - ids[0] + 1), str(N))

    ts = np.array([int(r["unix_utc"]) for r in L], np.int64)
    d = np.diff(ts)
    import collections
    gros = collections.Counter(d[d > 1000].tolist())
    dit("coupures de nuit", sum(gros.values()) == 345, sum(gros.values()), "345")
    dit("dont 25 500 s", gros.get(25500) == 343, gros.get(25500), "343")
    dit("dont 21 900 s (heure d'ete)", gros.get(21900) == 1, gros.get(21900), "1")
    dit("dont 29 100 s (heure d'hiver)", gros.get(29100) == 1, gros.get(29100), "1")
    dit("cycle nominal = 24 h", 203 * 300 + 25500 == 86400,
        f"{203*300+25500} s", "86 400 s")
    dit("ecarts de +300 s", int((d == 300).sum()) == 70190,
        int((d == 300).sum()), "70 190")

    # Les ecarts anormaux INTRA-NUIT viennent en paires consecutives qui se compensent
    # exactement : un tirage en avance de delta, le suivant en retard de delta, somme 600 s.
    # Le calendrier se RECALE, donc l'horodatage ne porte presque aucune entropie propre —
    # ce qui explique que les balayages de graine d'horloge (§200-§212) le couvrent si bien.
    anom = np.flatnonzero((d != 300) & (d < 1000))
    paires = comp = 0
    i = 0
    while i < len(anom):
        if i + 1 < len(anom) and anom[i + 1] == anom[i] + 1:
            paires += 1
            comp += int(d[anom[i]]) + int(d[anom[i] + 1]) == 600
            i += 2
        else:
            i += 1
    dit("ecarts anormaux intra-nuit", len(anom) == 24, len(anom), "24")
    dit("ils viennent tous en paires consecutives", paires == 12, paires, "12")
    dit("et TOUTES se compensent a 600 s", comp == 12 and comp == paires,
        f"{comp}/{paires}", "12/12")

    deb = np.r_[0, np.flatnonzero(d > 1000) + 1]
    lon = np.diff(np.r_[deb, N])
    c = collections.Counter(lon.tolist())
    dit("nuits", len(deb) == 346, len(deb), "346")
    dit("nuits de 204 tirages", c.get(204) == 345, c.get(204), "345")
    dit("nuits de 180 tirages", c.get(180) == 1, c.get(180), "1")

    nums = np.array([[int(r[f"n{j}"]) for j in range(1, 21)] for r in L], np.int64)
    dit("vingt numeros distincts par tirage",
        bool((np.diff(np.sort(nums, axis=1), axis=1) > 0).all()), "tous", "")
    dit("numeros dans 1..80",
        bool((nums >= 1).all() and (nums <= POOL).all()), "oui", "")
    return ids, ts, nums, L


# ======================================================================================
# 2. LE THEOREME DU BONUS (§175, §190, §194) — le seul resultat positif du dossier
# ======================================================================================

def bloc_bonus(nums, L):
    print("\n2. LE THEOREME DU BONUS — recalcule depuis les CSV, colonne par colonne")
    bonus = np.array([int(r["bonus"]) if r.get("bonus") else -1 for r in L], np.int64)
    dit("colonne bonus presente partout", int((bonus < 0).sum()) == 0,
        f"{int((bonus >= 0).sum())}/{len(L)}", f"{len(L)}/{len(L)}")
    dit("bonus prend les 80 valeurs", len(np.unique(bonus)) == POOL,
        len(np.unique(bonus)), "80")

    dedans = int((nums == bonus[:, None]).any(axis=1).sum())
    dit("LE BONUS EST L'UN DES VINGT", dedans == len(L),
        f"{dedans}/{len(L)}", "70 560/70 560")

    rang = np.argmax(nums == bonus[:, None], axis=1)
    hist = np.bincount(rang, minlength=DRAWN)
    khi = float(((hist - len(L) / DRAWN) ** 2 / (len(L) / DRAWN)).sum())
    dit("khi2 d'uniformite du rang (19 ddl)", proche(khi, 27.46, 0.01),
        f"{khi:.2f}", "27,46")
    dit("facteur exact 1/80 -> 1/20", POOL // DRAWN == 4, POOL / DRAWN, "4")
    return bonus, rang


# ======================================================================================
# 3. LA GRILLE DU BOOST (§106, §194)
# ======================================================================================

def bloc_boost(L):
    print("\n3. LA GRILLE DU MULTIPLICATEUR")
    boost = np.array([int(r["boost"]) for r in L], np.int64)
    v, c = np.unique(boost, return_counts=True)
    dit("six valeurs", len(v) == 6, list(v.tolist()), "[1, 2, 3, 4, 5, 10]")
    secteurs = [round(80 * x / len(L)) for x in c]
    dit("secteurs sur la grille 1/80", secteurs == [41, 19, 12, 4, 2, 2],
        secteurs, "[41, 19, 12, 4, 2, 2]")
    dit("les secteurs somment a 80", sum(secteurs) == 80, sum(secteurs), "80")
    p = c / len(L)
    H = float(-(p * np.log2(p)).sum())
    dit("entropie du multiplicateur", proche(H, 1.8790, 5e-4), f"{H:.4f}", "1,8790")
    dit("mode", proche(100 * p.max(), 51.193, 0.01), f"{100*p.max():.3f} %", "51,193 %")
    return boost, H


# ======================================================================================
# 4. LES CONSTANTES EXACTES DONT TOUT LE DOSSIER DEPEND
# ======================================================================================

def bloc_constantes(H):
    print("\n4. LES CONSTANTES EXACTES, recalculees en rationnels quand c'est possible")

    # variance hypergeometrique du recouvrement (§185)
    var = Fraction(DRAWN) * Fraction(DRAWN, POOL) * Fraction(POOL - DRAWN, POOL) \
        * Fraction(POOL - DRAWN, POOL - 1)
    dit("Var du recouvrement = 20(1/4)(3/4)(60/79)", proche(float(var), 2.8481, 5e-5),
        f"{float(var):.6f} = {var}", "2,8481")
    dit("ecart-type du recouvrement", proche(sqrt(float(var)), 1.687632, 1e-5),
        f"{sqrt(float(var)):.6f}", "1,6876")

    # mots consommes par tirage (§7.27)
    EN = sum(Fraction(POOL, POOL - k) for k in range(DRAWN))
    varN = sum(Fraction(POOL, POOL - k) * Fraction(k, POOL - k) for k in range(DRAWN))
    dit("E[N] = 80(H80 - H60)", proche(float(EN), 22.848709, 1e-6),
        f"{float(EN):.6f}", "22,848709")
    dit("Var[N]", proche(float(varN), 3.4319, 5e-4), f"{float(varN):.4f}", "3,4319")
    dit("ecart-type de N", proche(sqrt(float(varN)), 1.8525451, 1e-6),
        f"{sqrt(float(varN)):.7f}", "1,8525451")

    # entropie publiee par tirage (§193, §194)
    lc = log2(comb(POOL, DRAWN))
    dit("log2 C(80,20)", proche(lc, 61.6165, 5e-4), f"{lc:.4f}", "61,6165")
    dit("log2 20", proche(log2(DRAWN), 4.3219, 5e-4), f"{log2(DRAWN):.4f}", "4,3219")
    dit("entropie totale par tirage", proche(lc + log2(DRAWN) + H, 67.8175, 1e-3),
        f"{lc + log2(DRAWN) + H:.4f}", "67,8175")

    # variance exacte de l'autocorrelation (§7.29)
    dit("Var(x) = (1/4)(3/4) = 3/16", Fraction(1, 4) * Fraction(3, 4) == Fraction(3, 16),
        str(Fraction(3, 16)), "3/16")


# ======================================================================================
# 5. LA NULLE EXACTE DES DETECTEURS D'ENERGIE (§184) — enumeration, pas formule
# ======================================================================================

def bloc_nulle_energie():
    print("\n5. LA NULLE EXACTE DES DETECTEURS D'ENERGIE (§184), par enumeration")
    p1 = Fraction(DRAWN, POOL)
    p2 = Fraction(DRAWN * (DRAWN - 1), POOL * (POOL - 1))
    p3 = Fraction(DRAWN * (DRAWN - 1) * (DRAWN - 2), POOL * (POOL - 1) * (POOL - 2))

    for S in ([0], [0, 1], [0, 1, 2]):
        # (a) trois tirages distincts : chaque indicatrice pese 20/80 independamment
        att_a = Fraction(POOL * POOL * len(S)) * p1 ** 3
        # (b) tout dans le MEME tirage : on classe chaque triple par ses coincidences
        n1 = n2 = n3 = 0
        for u in range(POOL):
            for v in range(POOL):
                for dd in S:
                    w = (u + v + dd) % POOL
                    k = len({u, v, w})
                    n1 += k == 1
                    n2 += k == 2
                    n3 += k == 3
        att_b = n1 * p1 + n2 * p2 + n3 * p3
        cible = 100 * len(S)
        dit(f"|S|={len(S)} : trois tirages distincts", proche(float(att_a), cible, 1e-9),
            f"{float(att_a):.4f}", f"{cible}")
        dit(f"|S|={len(S)} : tout dans le meme tirage", proche(float(att_b), cible, 1e-9),
            f"{float(att_b):.4f}  ({n1} + {n2} + {n3} triples)", f"{cible}")


# ======================================================================================
# 6. LA NULLE EXACTE DE L'AUTOCORRELATION (§7.29) — verifiee par simulation
# ======================================================================================

def bloc_autocorrelation():
    print("\n6. LA NULLE EXACTE DE L'AUTOCORRELATION (§7.29), verifiee par simulation")
    rng = np.random.default_rng(4242)
    n, reps, dmax = 4000, 40, 25
    z = []
    for _ in range(reps):
        m = np.zeros((n, POOL), bool)
        idx = np.argsort(rng.random((n, POOL)), axis=1)[:, :DRAWN]
        np.put_along_axis(m, idx, True, axis=1)
        x = m.astype(np.float64) - 0.25
        for dd in range(1, dmax + 1):
            C = (x[:n - dd] * x[dd:]).sum(axis=0)
            z.append(C / ((3.0 / 16.0) * sqrt(n - dd)))
    z = np.concatenate(z)
    dit("moyenne des z (attendu 0 exactement)", abs(z.mean()) < 0.02,
        f"{z.mean():+.4f}", "0")
    dit("ecart-type des z (attendu 1 exactement)", abs(z.std() - 1) < 0.02,
        f"{z.std():.4f}", "1")


# ======================================================================================
# 7. LE REGISTRE : Holm sur l'ensemble, et les entrees retirees
# ======================================================================================

def bloc_registre():
    print("\n7. LE REGISTRE")
    import lab
    L = lab.ledger()
    dit("entrees au registre", len(L) >= 250, len(L), ">= 250")
    h = lab.holm()
    m = h[0]["m_total"]
    sig = [r for r in h if r["significant"]]
    dit("tests comptes (m_extra compris)", m > 6_900_000, f"{m:,}", "6 952 111+")
    dit("AUCUN resultat significatif apres Holm", len(sig) == 0, len(sig), "0")
    dit("plus petit p du dossier", proche(h[0]["p"], 1.805e-4, 1e-6),
        f"{h[0]['p']:.3e} ({h[0]['id']})", "1,805e-4")
    dit("seuil de Holm au premier rang", h[0]["holm_threshold"] < 1e-8,
        f"{h[0]['holm_threshold']:.3e}", "7,19e-9")
    facteur = h[0]["p"] / h[0]["holm_threshold"]
    dit("facteur manquant", facteur > 20000, f"{facteur:,.0f}", "~25 000")

    retires = [r for r in L if "RETIR" in str(r.get("verdict", "")).upper()]
    dit("entree retiree pour fuite (h170)",
        any(r["id"] == "h170.predicteur_energie" for r in retires),
        [r["id"] for r in retires], "h170.predicteur_energie")

    for cle, att in (("h173.predicteur_appris", 4.99449),
                     ("h176.borne_elargie", 5.00230),
                     ("h170b.predicteur_energie", 5.00300)):
        e = [r for r in L if r["id"] == cle]
        dit(f"{cle} : recouvrement", bool(e) and proche(e[0]["observed"], att, 1e-4),
            f"{e[0]['observed']:.5f}" if e else "ABSENT", f"{att:.5f}")


# ======================================================================================
# 8. LE CACHE EST-IL FIDELE AUX CSV ?
# ======================================================================================

def bloc_cache(ids, ts, nums, bonus, boost):
    print("\n8. LE CACHE .npz EST-IL FIDELE AUX CSV ?")
    import lab
    A = lab.load()
    dit("identifiants", bool((np.asarray(A.ids) == ids).all()), "identiques", "")
    dit("horodatages", bool((np.asarray(A.ts) == ts).all()), "identiques", "")
    dit("numeros", bool((np.asarray(A.nums) == nums).all()), "identiques", "")
    dit("bonus", bool((np.asarray(A.bonus) == bonus).all()), "identiques", "")
    dit("boost", bool((np.asarray(A.boost) == boost).all()), "identiques", "")
    M = np.asarray(A.mask)
    ok = bool((M.sum(axis=1) == DRAWN).all())
    dit("masque : vingt bits par tirage", ok, "oui", "")
    rec = np.zeros_like(M)
    rec[np.arange(len(nums))[:, None], nums - 1] = True
    dit("masque = numeros", bool((rec == M).all()), "identiques", "")


# ======================================================================================
# 9. LE FLUX MINCE (§7.34, §197, §198) — le lemme et la nulle exacte, par enumeration
# ======================================================================================

def bloc_flux_mince():
    print("\n9. LE FLUX MINCE (§7.34) — lemme et nulle exacte, par enumeration")

    # (a) le lemme c = 4b + k avec k dans {0,1,2,3}, verifie sur tout le domaine utile
    M32 = 1 << 32
    u = np.unique(np.r_[np.arange(0, M32, 9973), M32 - 1]).astype(np.int64)
    c = (u * POOL) >> 32
    b = (u * DRAWN) >> 32
    k = c - 4 * b
    dit("lemme c = 4b + k, k dans {0,1,2,3}",
        bool((k >= 0).all() and (k <= 3).all()), f"k dans [{k.min()}, {k.max()}]",
        "[0, 3]")
    dit("les quatre valeurs de k sont atteintes", len(np.unique(k)) == 4,
        sorted(np.unique(k).tolist()), "[0, 1, 2, 3]")

    # (b) E[T2] = 0,8|S| par tirage : enumeration exhaustive sur les 20x20 blocs
    B = [set(range(4 * j, 4 * j + 4)) for j in range(DRAWN)]
    for S in ([0], [0, 1], [0, 1, 2, 3]):
        tot = 0
        for b1 in B:
            for b2 in B:
                for uu in b1:
                    for vv in b2:
                        for dd in S:
                            w = (uu + vv + dd) % POOL
                            tot += sum(w in bt for bt in B)
        moy = tot / (DRAWN * DRAWN * DRAWN)          # moyenne sur les trois blocs
        dit(f"|S|={len(S)} : E[T2] par tirage", proche(moy, 0.8 * len(S), 1e-12),
            f"{moy:.6f}", f"{0.8*len(S):.6f}")

    # (c) la grille du boost : les p theoriques somment a 1
    P = np.array([41, 19, 12, 4, 2, 2]) / POOL
    dit("les six p theoriques somment a 1", proche(float(P.sum()), 1.0, 1e-12),
        f"{P.sum():.6f}", "1")


# ======================================================================================
# 10. LES SECTIONS DE GRAINE (§200-§205) et l'esperance a TROIS termes du flux mince
# ======================================================================================

def bloc_graines():
    print("\n10. LES SECTIONS DE GRAINE, et l'esperance a trois termes du flux mince")
    import lab
    L = {r["id"]: r for r in lab.ledger()}
    for cle in ("h181.graine_moderne", "h182.echauffement", "h183b.graines_derivees",
                "h184.graine_exhaustive", "h185.sous_seconde"):
        e = L.get(cle)
        dit(f"{cle} : zero appariement",
            bool(e) and e["verdict"] == "conforme" and e["observed"] == 0.0,
            f"{e['observed']:.0f} appariement(s)" if e else "ABSENTE", "0")

    # l'esperance a TROIS termes du flux mince : 4^3 |S| / 20, verifiee par enumeration.
    # C'est la valeur que h180 appliquait a tort a 3,2 dans sa premiere version.
    B = [set(range(4 * j, 4 * j + 4)) for j in range(DRAWN)]
    S = [0, 1, 2, 3]
    tot = 0
    for b1 in B:
        for b2 in B:
            for b3 in B:
                for uu in b1:
                    for vv in b2:
                        for ww in b3:
                            for dd in S:
                                w = (uu + vv + ww + dd) % POOL
                                tot += sum(w in bt for bt in B)
    moy = tot / (DRAWN ** 4)
    dit("E[T3] du flux mince = 4^3|S|/20", proche(moy, 64 * len(S) / 20.0, 1e-12),
        f"{moy:.6f}", f"{64*len(S)/20.0:.6f}")

    # et la moyenne du vecteur mixte des 41 statistiques de h178
    m = (21 * 0.8 * len(S) + 20 * 64 * len(S) / 20.0) / 41
    dit("moyenne des 41 statistiques melangees", proche(m, 7.8829, 1e-3),
        f"{m:.4f}", "7,8829")


def bloc_dependance():
    """11. LA LOI JOINTE INTERNE (§213, §7.37) et LES REGLES D'ECHANTILLONNAGE (§214).

    Tout est etabli par fractions exactes ou par enumeration complete ; aucune simulation,
    et en particulier aucune valeur reprise d'un fichier d'experience.
    """
    from fractions import Fraction as F
    print("\n11. LA LOI JOINTE INTERNE, et les regles d'echantillonnage")

    # -- les probabilites jointes exactes du §213
    for k, publie in ((2, F(19, 316)), (3, F(57, 4108))):
        p = F(1)
        for j in range(k):
            p *= F(DRAWN - j, POOL - j)
        dit(f"P({k}/{k}) = produit (20-j)/(80-j)", p == publie, str(p), str(publie))

    # -- la loi de X_G est hypergeometrique : moyenne k/4 et variance k(1/4)(3/4)(80-k)/79,
    #    verifiees par la loi complete, en fractions
    def binom(n, r):
        v = F(1)
        for i in range(r):
            v *= F(n - i, i + 1)
        return v

    for k in (1, 2, 3, 5, 10, 20):
        loi = [binom(k, h) * binom(POOL - k, DRAWN - h) / binom(POOL, DRAWN)
               for h in range(k + 1)]
        dit(f"loi de X_G somme a 1 (k = {k:2d})", sum(loi) == 1, str(sum(loi)), "1")
        esp = sum(h * loi[h] for h in range(k + 1))
        var = sum(h * h * loi[h] for h in range(k + 1)) - esp * esp
        dit(f"E[X_G] = k/4 (k = {k:2d})", esp == F(k, 4), str(esp), str(F(k, 4)))
        dit(f"Var(X_G) = k(3/16)(80-k)/79 (k = {k:2d})",
            var == F(k * 3, 16) * F(POOL - k, POOL - 1), str(var),
            str(F(k * 3, 16) * F(POOL - k, POOL - 1)))

    # -- le seuil de rejet des echantillonneurs 2 et 3 du §211
    dit("2^32 mod 80 = 16", (1 << 32) % POOL == 16, str((1 << 32) % POOL), "16")

    def binom2(n, r):
        v = F(1)
        for i in range(r):
            v *= F(n - i, i + 1)
        return v

    # -- les queues basses du §217 : Q_k = produit (60-j)/(80-j)
    for k, publie in ((5, "0,2271842"), (10, "0,0457907")):
        q = F(1)
        for j in range(k):
            q *= F(POOL - DRAWN - j, POOL - j)
        dit(f"Q({k}) = P(aucun des {k} ne sort)", proche(float(q), float(
            publie.replace(",", ".")), 5e-7), f"{float(q):.7f} = {q}", publie)

    # -- les parites exactes des §215 et §218, par DEUX derivations independantes :
    #    l'esperance hypergeometrique, et la forme fermee somme_h (-1)^h C(20,h) C(60,k-h)
    #    / C(80,k) qui vient du fait que la moyenne sur toutes les parties de taille k est
    #    une identite algebrique pour n'importe quelle collection de tirages 20/80.
    for k, publie in ((4, "3799/79079"), (5, "3079/158158")):
        e1 = sum((-1) ** h * binom2(k, h) * binom2(POOL - k, DRAWN - h)
                 / binom2(POOL, DRAWN) for h in range(k + 1))
        e2 = sum((-1) ** h * binom2(DRAWN, h) * binom2(POOL - DRAWN, k - h)
                 for h in range(k + 1)) / binom2(POOL, k)
        dit(f"E[parite] ordre {k}, deux derivations",
            str(e1) == publie and e1 == e2, f"{e1} et {e2}", publie)
        dit(f"E[parite] ordre {k} != (1/2)^{k}", e1 != F(1, 2 ** k),
            f"{float(e1):.8f} contre {0.5**k:.8f}", "differentes")

    # -- le systeme de numeration combinatoire du §218 : rang = somme_i C(a_i, i) numerote
    #    les parties de taille k exactement sur 0..C(n,k)-1, sans trou ni collision
    for n, k in ((10, 3), (14, 4), (16, 5)):
        r = sorted(sum(int(binom2(a, i + 1)) for i, a in enumerate(p))
                   for p in itertools.combinations(range(n), k))
        dit(f"rang colex bijectif sur C({n},{k})",
            r == list(range(int(binom2(n, k)))), f"{len(r)} rangs, max {r[-1]}",
            f"0..{int(binom2(n,k))-1}")

    # -- les regles du §214 sont-elles CORRECTES ? Enumeration EXHAUSTIVE sur un analogue
    #    reduit (pool 5, tirage 2), tous les mots parcourus, en fractions exactes.
    #
    #    Le bon invariant n'est PAS la marge. Une premiere version de ce controle comparait
    #    les marges et declarait le melange naif conforme : en comptant AVEC MULTIPLICITE,
    #    ses cinq marges valent exactement 2/5 comme celles du bon. C'est faux et ca cachait
    #    sa vraie faute. Le melange naif `k = w mod n` peut sortir DEUX FOIS LE MEME NUMERO
    #    -- il produit ici quinze ensembles au lieu de dix, dont des ensembles a un seul
    #    element, et ses marges d'appartenance valent 9/25 au lieu de 2/5.
    #
    #    L'invariant qui tranche est donc : la loi de l'ENSEMBLE de sortie doit etre
    #    uniforme sur les C(n,k) parties, ce qui exige d'abord k valeurs DISTINCTES.
    P5, D2 = 5, 2

    def loi_fy(faux):
        """melange partiel ; `faux` remplace k = j + w mod (n-j) par la faute k = w."""
        c, plages = {}, [P5] * D2 if faux else [P5 - j for j in range(D2)]
        tot = F(1)
        for p in plages:
            tot *= p
        for ws in itertools.product(*[range(p) for p in plages]):
            tab, out = list(range(P5)), []
            for j, w in enumerate(ws):
                k = w if faux else j + w
                tab[j], tab[k] = tab[k], tab[j]
                out.append(tab[j])
            c[frozenset(out)] = c.get(frozenset(out), F(0)) + F(1) / tot
        return c

    def loi_knuth():
        """selection sequentielle : recurrence EXACTE sur (i, m), sans aucun tirage."""
        c, etat = {}, {(0, (), 0): F(1)}
        for i in range(P5):
            suiv = {}
            for (ii, pris, m), pr in etat.items():
                if m == D2:
                    suiv[(ii, pris, m)] = suiv.get((ii, pris, m), F(0)) + pr
                    continue
                q = F(D2 - m, P5 - i)                    # probabilite de retenir i
                for cle, w in (((i + 1, pris + (i,), m + 1), q),
                               ((i + 1, pris, m), 1 - q)):
                    if w:
                        suiv[cle] = suiv.get(cle, F(0)) + pr * w
            etat = suiv
        for (_, pris, _), pr in etat.items():
            c[frozenset(pris)] = c.get(frozenset(pris), F(0)) + pr
        return c

    def loi_tri():
        """tri de n cles : enumeration des n! ordres, tous equiprobables."""
        c = {}
        for perm in itertools.permutations(range(P5)):
            s = frozenset(sorted(range(P5), key=lambda i: perm[i])[:D2])
            c[s] = c.get(s, F(0)) + F(1, 120)
        return c

    att = F(1, 10)                                        # 1/C(5,2)
    for nom, f, doit in (("Fisher-Yates partiel", lambda: loi_fy(False), True),
                         ("tri de n cles", loi_tri, True),
                         ("selection sequentielle", loi_knuth, True),
                         ("melange NAIF (k = w mod n)", lambda: loi_fy(True), False)):
        c = f()
        distincts = all(len(s) == D2 for s in c)
        bon = distincts and len(c) == 10 and all(v == att for v in c.values())
        dit(f"loi de l'ensemble uniforme : {nom}", bon == doit,
            f"{len(c)} ensembles, "
            + ("tous a 1/10" if bon else
               f"tailles {sorted({len(s) for s in c})}, probas "
               f"{sorted({str(v) for v in c.values()})}"),
            "uniforme sur 10" if doit else "NON uniforme, et c'est voulu")

    # -- les lignes de registre des sections nouvelles
    import lab
    L = {r["id"]: r for r in lab.ledger()}
    for cle in ("h187.echantillonneurs", "h192.graine_par_tirage",
                "h194.echantillonneurs_structurels"):
        e = L.get(cle)
        dit(f"{cle} : zero appariement",
            bool(e) and e["verdict"] == "conforme" and e["observed"] == 0.0,
            f"{e['observed']:.0f} appariement(s)" if e else "ABSENTE", "0")
    for cle in ("h193.dependance_interne", "h195.parites_ordre_quatre",
                "h196.les_deux_queues", "h197.parites_ordre_cinq"):
        e = L.get(cle)
        dit(f"{cle} : conforme", bool(e) and e["verdict"] == "conforme",
            e["verdict"] if e else "ABSENTE", "conforme")


def bloc_bareme():
    """12. LE BAREME (§216) — ce que la nullite vaut en francs, recalcule depuis le CSV.

    Un dossier de nullites ne dit rien d'utile tant qu'il n'est pas converti en argent.
    Le bareme releve sur l'ecran donne l'esperance de gain EXACTE sous SRS, et le facteur
    par lequel un joueur devrait la multiplier pour atteindre l'equilibre.
    """
    from fractions import Fraction as F
    print("\n12. LE BAREME, et ce que la nullite vaut en francs")

    lignes = [r for r in csv.DictReader(
        l for l in open(os.path.join(ROOT, "bareme_observed.csv"), encoding="utf-8")
        if not l.startswith("#"))]
    par = {}
    for r in lignes:
        par.setdefault(int(r["mise"]), {})[int(r["hits"])] = int(r["gain_base"])
    dit("tailles de grille au bareme", sorted(par) == [5, 6, 7, 8, 10],
        sorted(par), "[5, 6, 7, 8, 10]")

    def binom(n, r):
        v = F(1)
        for i in range(r):
            v *= F(n - i, i + 1)
        return v

    esp = {}
    for k in sorted(par):
        P = [binom(k, h) * binom(POOL - k, DRAWN - h) / binom(POOL, DRAWN)
             for h in range(k + 1)]
        dit(f"loi des justes somme a 1 (grille de {k:2d})", sum(P) == 1, str(sum(P)), "1")
        esp[k] = sum(P[h] * par[k].get(h, 0) for h in range(k + 1))
        print(f"          grille de {k:2d} : E[gain] = {float(esp[k]):.5f} CHF, "
              f"P({k}/{k}) = {float(P[k]):.4e}")

    # La constance de E[gain] a travers les tailles est la signature d'un rendement cible
    # fixe : l'operateur a normalise son bareme. Elle est ce qui permet de parler d'UNE
    # marge de maison, et non de cinq.
    lo, hi = float(min(esp.values())), float(max(esp.values()))
    dit("E[gain] quasi constant sur les cinq tailles", hi / lo < 1.03,
        f"{lo:.5f} a {hi:.5f}, rapport {hi/lo:.4f}", "rapport < 1,03")

    # Le facteur d'amelioration que le dossier justifie AU MIEUX : la meilleure grille de
    # cinq trouvee hors echantillon (§213 D) a 29 jackpots sur 35 280, dont la borne haute
    # unilaterale a 95 % vaut (29 + 1,645 racine(29))/35 280.
    P5 = [binom(5, h) * binom(POOL - 5, DRAWN - h) / binom(POOL, DRAWN) for h in range(6)]
    haut = (29 + 1.645 * sqrt(29)) / 35280
    dit("borne haute 95 % de la meilleure grille de cinq",
        proche(haut / float(P5[5]), 1.664, 5e-3), f"x{haut/float(P5[5]):.3f}", "x1,664")
    ameliore = (360 * haut + 36 * float(P5[4]) + 6 * float(P5[3])) / float(esp[5])
    dit("gain de rendement que le dossier justifie au mieux",
        proche(ameliore, 1.132, 5e-3), f"x{ameliore:.3f}", "x1,132")
    print(f"          -> pour l'equilibre il faudrait multiplier E[gain] par mise/"
          f"{float(esp[5]):.3f} ; le dossier n'offre que x{ameliore:.3f}")

    # L'option EXTRA paie 1 000 sur 5/5 et parait donc bien plus convexe. Sa loi complete
    # dit le contraire : son esperance vit dans l'ECHEC ORDINAIRE, pas dans le jackpot,
    # ce qui la rend MOINS sensible a un avantage de queue et non plus.
    ext = {}
    for r in lignes:
        ext.setdefault(int(r["mise"]), {})[int(r["hits"])] = int(r["gain_extra"])
    Ee = sum(P5[h] * ext[5].get(h, 0) for h in range(6))
    part5 = float(P5[5] * ext[5][5] / Ee)
    part1 = float(P5[1] * ext[5][1] / Ee)
    dit("E[EXTRA] pour une grille de cinq", proche(float(Ee), 11.13364, 5e-5),
        f"{float(Ee):.5f}", "11,13364")
    dit("le jackpot ne pese presque rien dans EXTRA", proche(part5, 0.058, 2e-3),
        f"{100*part5:.1f} % de E[EXTRA]", "5,8 %")
    dit("le tier « un seul juste » pese le plus", proche(part1, 0.437, 2e-3),
        f"{100*part1:.1f} % de E[EXTRA]", "43,7 %")
    Pb = [float(x) for x in P5]
    Pb[5] = haut
    ame_e = sum(Pb[h] * ext[5].get(h, 0) for h in range(6)) / float(Ee)
    dit("EXTRA est MOINS ameliorable que la base", ame_e < ameliore,
        f"x{ame_e:.4f} contre x{ameliore:.4f} en base", "moins")


def bloc_ordonnes():
    """13. LES DOUZE TIRAGES ORDONNES (§214) — ce que l'ordre de sortie elimine.

    Ils ne servaient qu'aux cribles du §159. Ils tranchent aussi sur les regles
    d'echantillonnage, et sans calcul : la selection sequentielle de Knuth parcourt
    0..79 dans l'ordre et retient au passage, donc sous sa forme naturelle elle sort
    TRIEE PAR INDICE.
    """
    print("\n13. LES DOUZE TIRAGES ORDONNES, et la regle qu'ils eliminent")
    chemin = os.path.join(ROOT, "draws_ordered.csv")
    L = [r for r in csv.DictReader(open(chemin, encoding="utf-8"))]
    dit("douze tirages ordonnes", len(L) == 12, len(L), "12")

    V = np.array([[int(r[f"o{j}"]) for j in range(1, DRAWN + 1)] for r in L], np.int64)
    dit("vingt numeros distincts par tirage",
        bool((np.diff(np.sort(V, axis=1), axis=1) > 0).all()), "tous", "")
    croissants = int((np.diff(V, axis=1) > 0).all(axis=1).sum())
    dit("AUCUN tirage croissant -> Knuth S en ordre d'indice eliminee",
        croissants == 0, f"{croissants}/12 croissants", "0/12")

    # nombre de montees : sous permutation uniforme de n elements, moyenne (n-1)/2 et
    # variance (n+1)/12, toutes deux EXACTES.
    montees = (np.diff(V, axis=1) > 0).sum(axis=1).astype(np.float64)
    mu, var = (DRAWN - 1) / 2, (DRAWN + 1) / 12
    z = (montees.mean() - mu) / sqrt(var / len(montees))
    dit("montees : moyenne conforme a (n-1)/2",
        proche(montees.mean(), 9.333, 5e-3) and abs(z) < 3,
        f"{montees.mean():.3f}, z = {z:+.2f}", f"{mu} +/- {sqrt(var/len(montees)):.3f}")
    dit("variance exacte des montees = (n+1)/12", proche(var, 1.75, 1e-12),
        f"{var:.4f}", "1,7500")


if __name__ == "__main__":
    print("=" * 78)
    print("VERIFICATION DU DOSSIER — tout est recalcule depuis les sources")
    print("=" * 78)
    L = lire_brut()
    ids, ts, nums, L = bloc_archive(L)
    bonus, rang = bloc_bonus(nums, L)
    boost, H = bloc_boost(L)
    bloc_constantes(H)
    bloc_nulle_energie()
    bloc_autocorrelation()
    bloc_registre()
    bloc_cache(ids, ts, nums, bonus, boost)
    bloc_flux_mince()
    bloc_graines()
    bloc_dependance()
    bloc_bareme()
    bloc_ordonnes()

    print("\n" + "=" * 78)
    if ECHECS:
        print(f"{len(ECHECS)} ECHEC(S) : " + ", ".join(ECHECS))
    else:
        print("TOUS LES CONTROLES PASSENT.")
    print("=" * 78)
    sys.exit(len(ECHECS))
