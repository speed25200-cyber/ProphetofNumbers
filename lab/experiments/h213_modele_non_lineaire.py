"""h213 — LE MODÈLE NON LINÉAIRE : la question du joueur, posée au plus gros modèle
que le dossier ait porté (RAPPORT §236).

CE QUE TOUS LES PRÉDICTEURS DU DOSSIER ONT EN COMMUN
====================================================
Le §192 apprend `31` traits — **linéairement**. Le §227 mesure la perte logarithmique de ce
même modèle — **linéaire**. Le §235 y ajoute le contexte intra-tirage — **linéairement**.
Le §193 cherche des grilles convexes, le §220 des règles conditionnelles : tout cela reste
dans la famille des **fonctions linéaires des traits**.

C'est une critique juste, et elle a une réponse chiffrable : **un modèle non linéaire sur la
même information trouverait-il ce qu'un modèle linéaire manque ?**

LE MODÈLE
=========
Douze traits causaux au niveau du tirage — donc **jouables** : rien du tirage courant n'y
entre, contrairement au §235 dont les traits intra-tirage mesuraient une structure sans être
misables. Puis l'expansion :

    12 traits  +  66 produits croisés  +  12 carrés  =  90 colonnes

Une régression logistique sur ces `90` colonnes **est** un modèle non linéaire des douze
traits d'origine : elle porte toutes les interactions d'ordre deux et toutes les courbures.
Ajustée par Newton exact (pas de descente à régler), sur `3,3` millions de couples
(tirage, numéro).

LE TRAIT QUI MANQUAIT : LA STRUCTURE DE PAIRES
===============================================
Le §193 a mesuré la dépendance interne — quels numéros sortent ensemble. **Personne ne l'a
jamais donnée à un prédicteur.** On calcule donc, sur la seule tranche d'ajustement, le
levier de co-occurrence

    Ĉ(n,m) = P(n et m ensemble) / (P(n)·P(m)) − 1

et l'on donne au modèle, pour chaque tirage `t` et chaque numéro `n`, la somme des `Ĉ(n,m)`
sur les vingt numéros du tirage `t−1`. C'est causal, c'est nouveau, et c'est exactement le
canal que le §7.37 désigne comme celui qui paie.

LA MESURE EST CELLE DU JOUEUR, PAS CELLE DU STATISTICIEN
=========================================================
On ne mesure pas un `z` sur une statistique abstraite. On joue les `k` meilleurs numéros du
modèle, tirage après tirage, hors échantillon, et l'on compte **les justes**.

La nulle est un **théorème**, pas une simulation : sous SRS, `E[justes] = k/4` pour une
grille de `k` numéros, **quel que soit le choix des numéros**. Une grille de dix rapporte
`2,5` justes en moyenne, et aucune sélection ne déplace cela d'un iota tant qu'il n'y a pas de
biais réel.

Reste à savoir de combien le hasard fait fluctuer un taux mesuré sur `27 424` tirages, et si
la chaîne complète — traits, expansion, ajustement, sélection des `k` meilleurs — fabrique un
excès par elle-même. D'où les répliques SRS, qui rejouent **toute** la chaîne.
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POOL, DRAWN = 80, 20
EXP_ID = "h213.modele_non_lineaire"
FJETON = "/tmp/h213_jeton.json"
REPS = 16
PART = 0.6
CHAUFFE = 2000
KS = (1, 5, 10, 20)
BLOC = 400_000            # lignes traitees d'un coup dans Newton


def say(*a):
    print(*a, flush=True)


def base(M, bonus, boost, veille, deb_aj, fin_aj):
    """(N,80,12) float32, TOUS causaux au niveau du tirage : rien du tirage courant.

    Le levier de co-occurrence est calcule sur la seule tranche [deb_aj, fin_aj).
    """
    N = len(M)
    Mf = M.astype(np.float32)
    C = np.cumsum(Mf, axis=0, dtype=np.float32)
    Cp = np.zeros_like(C)
    Cp[1:] = C[:-1]
    t = np.arange(N, dtype=np.float32)[:, None]

    F = []
    prev = np.zeros_like(Mf)
    prev[1:] = Mf[:-1]
    F.append(prev)
    for w in (10, 50, 200, 1000, 5000):
        A = np.full_like(Mf, 0.25)
        A[w:] = (Cp[w:] - Cp[:-w]) / w
        F.append(A)
    F.append(Cp / np.maximum(t, 1.0))
    idx = np.where(Mf > 0, np.arange(N, dtype=np.float32)[:, None], -1.0)
    der = np.maximum.accumulate(idx, axis=0)
    derp = np.zeros_like(der)
    derp[1:] = der[:-1]
    derp[0] = -1.0
    F.append(np.log1p(np.maximum(t - derp, 0.0)) / 10.0)

    bp = np.zeros(N, np.int64)
    bp[1:] = bonus[:-1]
    eb = np.zeros_like(Mf)
    eb[np.arange(N), np.maximum(bp - 1, 0)] = 1.0
    eb[0] = 0.0
    F.append(eb)
    bo = np.zeros(N, np.float32)
    bo[1:] = boost[:-1].astype(np.float32)
    F.append(np.repeat((bo / 10.0)[:, None], POOL, axis=1))
    F.append(np.repeat(veille[:, None].astype(np.float32), POOL, axis=1))

    # --- le levier de co-occurrence, appris sur la tranche d'ajustement SEULE
    T = Mf[deb_aj:fin_aj]
    n_aj = len(T)
    co = (T.T @ T) / n_aj
    marg = T.mean(axis=0)
    lift = co / np.maximum(marg[:, None] * marg[None, :], 1e-9) - 1.0
    np.fill_diagonal(lift, 0.0)
    F.append(prev @ lift.astype(np.float32))

    return np.stack(F, axis=2)


def etendre(Xb):
    """(m,12) -> (m,90) : les traits, leurs produits croises et leurs carres."""
    m, f = Xb.shape
    cols = [Xb]
    for i in range(f):
        cols.append(Xb[:, i:i + 1] * Xb[:, i:])
    return np.concatenate(cols, axis=1)


def ajuster(Xb, y, iters=8, ridge=1e-2):
    """Newton exact sur la logistique etendue, par blocs pour tenir en memoire."""
    m = len(Xb)
    ech = etendre(Xb[:min(m, 200_000)])
    nf = ech.shape[1]
    mu = ech.mean(axis=0)
    sd = ech.std(axis=0) + 1e-6
    del ech
    w = np.zeros(nf)
    b = 0.0
    for _ in range(iters):
        H = np.zeros((nf + 1, nf + 1))
        g = np.zeros(nf + 1)
        for a in range(0, m, BLOC):
            Z = (etendre(Xb[a:a + BLOC]) - mu) / sd
            Z = np.concatenate([Z, np.ones((len(Z), 1), np.float32)], axis=1).astype(np.float64)
            pr = 1.0 / (1.0 + np.exp(-(Z @ np.r_[w, b])))
            pds = np.maximum(pr * (1 - pr), 1e-9)
            H += (Z * pds[:, None]).T @ Z
            g += Z.T @ (y[a:a + BLOC] - pr)
            del Z
        H += ridge * m * np.eye(nf + 1)
        pas = np.linalg.solve(H, g)
        w += pas[:nf]
        b += pas[nf]
        if float(np.abs(pas).max()) < 1e-10:
            break
    return w, b, mu, sd


def scorer(Xb, w, b, mu, sd):
    out = np.empty(len(Xb))
    for a in range(0, len(Xb), BLOC):
        Z = (etendre(Xb[a:a + BLOC]) - mu) / sd
        out[a:a + BLOC] = Z @ w + b
    return out


def justes(S, Mx, deb, fin, k):
    """taux de justes moyen d'une grille des k meilleurs, tirage par tirage."""
    s = S.reshape(-1, POOL)
    top = np.argpartition(-s, k - 1, axis=1)[:, :k]
    y = Mx[deb:fin]
    return float(y[np.arange(len(y))[:, None], top].sum(axis=1).mean())


if __name__ == "__main__":
    import lab

    A = lab.load()
    M = np.asarray(A.mask)
    TS = np.asarray(A.ts).astype(np.int64)
    BONUS = np.asarray(A.bonus).astype(np.int64)
    BOOST = np.asarray(A.boost).astype(np.int64)
    N = len(M)
    veille = np.zeros(N, np.int8)
    veille[np.r_[0, np.flatnonzero(np.diff(TS) > 1000) + 1]] = 1
    coupe = CHAUFFE + int((N - CHAUFFE) * PART)
    nmes = N - coupe

    HYP = (f"Aucun modele non lineaire des traits disponibles ne bat k/4 justes sur une "
           f"grille de k numeros. Tous les predicteurs du dossier sont LINEAIRES en leurs "
           f"traits : le §192 apprend 31 traits lineairement, le §227 mesure ce meme modele, "
           f"le §235 y ajoute le contexte intra-tirage lineairement, le §193 cherche des "
           f"grilles convexes, le §220 des regles conditionnelles. On sort de cette famille : "
           f"12 traits causaux au niveau du tirage — donc JOUABLES, rien du tirage courant "
           f"n'y entre — puis 66 produits croises et 12 carres, soit 90 colonnes. Une "
           f"logistique sur ces 90 colonnes EST un modele non lineaire des 12 traits : elle "
           f"porte toutes les interactions d'ordre deux et toutes les courbures. Ajustee par "
           f"Newton exact sur 3,3 millions de couples. Elle recoit aussi un trait que "
           f"personne n'avait jamais donne a un predicteur : le LEVIER DE CO-OCCURRENCE "
           f"C(n,m) = P(n et m ensemble)/(P(n)P(m)) - 1 appris sur la seule tranche "
           f"d'ajustement, somme sur les vingt numeros du tirage precedent — le §193 a mesure "
           f"cette dependance, aucun modele ne s'en etait servi, et c'est le canal que le "
           f"§7.37 designe comme celui qui paie. La mesure est celle du joueur : on joue les "
           f"k meilleurs numeros, tirage apres tirage, hors echantillon, et on compte les "
           f"justes")
    STAT = (f"taux de justes moyen d'une grille des k meilleurs numeros du modele, pour "
            f"k = {KS}, sur les {nmes} tirages hors echantillon")
    NUL = (f"THEOREME pour l'esperance : sous SRS, E[justes] = k/4 pour une grille de k "
           f"numeros QUEL QUE SOIT le choix des numeros — l'esperance d'une hypergeometrique "
           f"ne depend pas de quels numeros on coche. La dispersion et le sur-apprentissage "
           f"de la chaine complete (traits, levier de co-occurrence, expansion, Newton, "
           f"selection des k meilleurs) viennent de {REPS} archives SRS rejouant toute la "
           f"chaine")
    VER = ("conforme si aucun k ne depasse le 95e centile de son taux sous SRS ; BIAIS "
           "EXPLOITABLE sinon, auquel cas l'exces de justes se convertit directement en "
           "esperance de gain")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="A")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    def chaine(Mx, bx, box, vx):
        Xb = base(Mx, bx, box, vx, CHAUFFE, coupe)
        nf = Xb.shape[2]
        Xa = Xb[CHAUFFE:coupe].reshape(-1, nf)
        ya = Mx[CHAUFFE:coupe].reshape(-1).astype(np.float64)
        w, b, mu, sd = ajuster(Xa, ya)
        del Xa, ya
        S = scorer(Xb[coupe:].reshape(-1, nf), w, b, mu, sd)
        del Xb
        return {k: justes(S, Mx, coupe, len(Mx), k) for k in KS}, w

    # ------------------------------------------------------------------ selftest
    say("\n   selftest : temoin plante — dix numeros surponderes (tirage de Gumbel)")
    say("      la surponderation est convertie en ECART DE MARGE MESURE, pas annoncee")
    rng0 = np.random.default_rng(213)
    CHAUDS = np.arange(10) * 8

    def tirage_pondere(n, delta, rng):
        """top-20 d'un tirage de Gumbel pondere : marges deplacees, sans boucle."""
        poids = np.ones(POOL)
        poids[CHAUDS] = 1.0 + delta
        g = rng.gumbel(size=(n, POOL)) + np.log(poids)[None, :]
        idx = np.argpartition(-g, DRAWN - 1, axis=1)[:, :DRAWN]
        W = np.zeros((n, POOL), bool)
        W[np.arange(n)[:, None], idx] = True
        return W

    for delta in (0.0, 0.02, 0.05):
        W = tirage_pondere(N, delta, rng0)
        marge = float(W[:, CHAUDS].mean())
        r, _ = chaine(W, BONUS, BOOST, veille)
        say(f"      delta = {delta:.2f} -> marge des chauds {marge:.5f} "
            f"(soit +{marge-0.25:.5f}) : " + "  ".join(
                f"k={k} -> {r[k]:.4f}" for k in KS))
    del W

    # ------------------------------------------------------------------ archive
    say(f"\n   archive : ajustement {CHAUFFE}..{coupe}, mesure {coupe}..{N} "
        f"({nmes} tirages, 90 colonnes)")
    obs, wobs = chaine(M, BONUS, BOOST, veille)
    for k in KS:
        say(f"      k = {k:2d} : {obs[k]:.5f} justes en moyenne   (nulle exacte {k/4:.2f})")

    # ------------------------------------------------------------------ nulle
    V = {k: np.empty(REPS) for k in KS}
    rng = np.random.default_rng(0x213)
    for r in range(REPS):
        o, _ = chaine(lab.srs(N, rng), BONUS, BOOST, veille)
        for k in KS:
            V[k][r] = o[k]
        if (r + 1) % 5 == 0:
            say(f"   ... {r+1}/{REPS} repliques")

    say(f"\n   {'k':>3} | {'archive':>10} | {'nulle exacte':>13} | "
        f"{'sous SRS':>22} | {'z':>7} | {'95e centile':>12}")
    zmax, kmax, pmin = 0.0, None, 1.0
    for k in KS:
        m_, s_ = float(V[k].mean()), float(V[k].std())
        z = (obs[k] - m_) / max(s_, 1e-12)
        q = float(np.quantile(V[k], 0.95))
        p = float((np.sum(V[k] >= obs[k]) + 1) / (REPS + 1))
        say(f"   {k:3d} | {obs[k]:10.5f} | {k/4:13.2f} | {m_:10.5f} +/-{s_:9.5f} | "
            f"{z:+7.2f} | {q:12.5f}")
        if z > zmax:
            zmax, kmax = z, k
        pmin = min(pmin, p)

    verdict = "BIAIS EXPLOITABLE" if any(
        obs[k] > float(np.quantile(V[k], 0.95)) for k in KS) else "conforme"
    say(f"\n   z maximal {zmax:+.2f} (k = {kmax})   p = {pmin:.4g}   ->   {verdict}")

    TOK["m_extra"] = len(KS) - 1
    lab.record(
        TOK, float(zmax), p=float(pmin), verdict=verdict,
        power_at=(f"le temoin plante donne l'echelle : dix numeros portes a p = 1/4 + eps "
                  f"font monter le taux de justes a k = 10 selon la table de la sortie. "
                  f"L'ecart-type du taux a k = 10 sous SRS vaut "
                  f"{float(V[10].std()):.5f} juste, donc la chaine voit un exces de "
                  f"{3*float(V[10].std()):.5f} juste sur une grille de dix, soit un "
                  f"deplacement de probabilite de {3*float(V[10].std())/10:.5f} par numero"),
        notes=(f"LE MODELE NON LINEAIRE (§236) — premier modele du dossier hors de la famille "
               f"lineaire : 12 traits causaux, 66 produits croises, 12 carres, 90 colonnes, "
               f"Newton exact sur 3,3 M de couples, plus un trait jamais donne a un "
               f"predicteur (le levier de co-occurrence du §193). Mesure du JOUEUR : justes "
               f"sur une grille des k meilleurs, hors echantillon sur {nmes} tirages, nulle "
               f"exacte k/4 par theoreme. "
               + " ; ".join(f"k={k} : {obs[k]:.5f} contre {k/4:.2f}" for k in KS)
               + f". z maximal {zmax:+.2f} a k = {kmax}, p = {pmin:.4g}."))
    say("   consigne.")
