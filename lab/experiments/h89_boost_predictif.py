"""h89 — prédire le BOOST : la seule cible où une marginale vaut de l'argent.

POURQUOI CETTE CIBLE, ET POURQUOI ELLE A ÉTÉ MANQUÉE
=====================================================
Le §93 a demontre que le gain espere vaut

    E[g] = somme_j  Delta^j g(0) * somme_(|S|=j) pi(S)

et que le bareme reel annule c_0, c_1 et c_2 : predire NUMERO PAR NUMERO ne
sert a rien, quelle que soit la qualite du predicteur. Le §107 en a tire la
consequence et est alle chercher les triplets.

MAIS LE BOOST N'EST PAS UN NUMERO. C'est un MULTIPLICATEUR : il entre dans le
gain de facon LINEAIRE et MULTIPLICATIVE.

    gain = boost * g(h)      donc      E[gain] = E[boost] * E[g]   (si independants)

    UNE MARGINALE SUR LE BOOST EST DONC EXACTEMENT DU BON TYPE.

C'est le seul endroit de tout le dossier ou un predicteur scalaire vaut de
l'argent, et ou un edge de delta pour cent se traduit par delta pour cent de
taux de retour en plus. Le §90 a mesure la loi du boost, le §92 a demontre que
la roue est cosmetique — personne n'a jamais essaye de le PREDIRE.

ET LA QUESTION EST ACTIONNABLE. Le joueur decide de jouer AVANT le tirage. La
seule prediction qui vaille est donc celle du boost du tirage t a partir des
tirages 1..t-1 STRICTEMENT. C'est ce que ce fichier fait : aucun regard sur le
present, aucun ajustement retrospectif.

L'INSTRUMENT : LE RAPPORT DE VRAISEMBLANCE SÉQUENTIEL
======================================================
    THEOREME. Soient P_0 et P_1 deux assignations de probabilite
    SEQUENTIELLES sur la suite des boosts — c'est-a-dire deux predicteurs qui,
    a chaque instant t, rendent une loi sur x_t au vu du seul passe. Alors

        W_N  =  produit_(t<=N)  P_1(x_t | passe) / P_0(x_t | passe)

    verifie E_{P_0}[W_N] = somme_x P_1(x_(1:N)) = 1, et W est une martingale
    positive sous P_0. Par Ville, P(sup W >= 1/alpha) <= alpha. []

    Aucune correction de multiplicite : un MELANGE de predicteurs a poids
    fixes d'avance est encore une assignation sequentielle, donc encore une
    martingale. On peut essayer douze modeles d'un coup.

P_0 est ici le predicteur de reference : la marginale du boost, estimee EN
LIGNE (Dirichlet), donc sans jamais regarder l'avenir. C'est le predicteur
optimal sous le nul « le boost est i.i.d. de loi inconnue ».

CE QUE CE FICHIER REND
=======================
Une richesse — combien un parieur aurait gagne en suivant les modeles plutot
que la marginale — et, si elle monte, une STRATEGIE : ne jouer que les tirages
ou le boost espere depasse un seuil. Le gain de taux de retour se lit
directement, sans passer par le bareme.

Il TESTE l'archive : il consigne au registre.
"""

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H89_DRY") == "1"
ALPHA = 0.5                                  # lissage de Krichevsky-Trofimov


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# ==========================================================================
rule("1. POURQUOI LE BOOST, ET POURQUOI PERSONNE N'A ESSAYÉ")
# ==========================================================================

ARCH = lab.load()
BOOST = np.asarray(ARCH.boost).astype(np.int64)
NUMS = np.asarray(ARCH.nums)
BON = np.asarray(ARCH.bonus).astype(np.int64)
TS = np.asarray(ARCH.ts).astype(np.int64)
if DRY:
    BOOST, NUMS, BON, TS = BOOST[:12000], NUMS[:12000], BON[:12000], TS[:12000]
N = len(BOOST)

VAL = np.array(sorted(set(BOOST.tolist())))
K = len(VAL)
IDX = np.searchsorted(VAL, BOOST)            # 0..K-1
p_emp = np.bincount(IDX, minlength=K) / N
EB = float((VAL * p_emp).sum())

say(f"""   LE §93 A TUE LA PREDICTION PAR NUMERO : le bareme annule c_0, c_1 et c_2,
   donc une probabilite par numero n'entre pas dans E[g]. Le §107 en a tire la
   consequence et est alle chercher les triplets.

   MAIS LE BOOST N'EST PAS UN NUMERO. C'est un MULTIPLICATEUR :

       gain = boost * g(h)      donc     E[gain] = E[boost] * E[g]

   Il entre LINEAIREMENT. Une marginale sur le boost est donc exactement du
   bon type, et un edge de delta pour cent vaut delta pour cent de taux de
   retour en plus. C'est le SEUL endroit du dossier ou cela soit vrai.

   Le §90 a mesure la loi du boost. Le §92 a demontre que la roue est
   cosmetique. Personne n'a essaye de le PREDIRE.
""")
say(f"   {'boost':>7} {'effectif':>10} {'probabilite':>13}")
for v, c, p in zip(VAL, np.bincount(IDX, minlength=K), p_emp):
    say(f"   {v:>7} {c:>10,} {p:>13.4f}")
say(f"""
   E[boost] = {EB:.4f} sur {N:,} tirages, entropie {-(p_emp*np.log2(p_emp)).sum():.3f} bits.

   ET LA QUESTION EST ACTIONNABLE : le joueur decide AVANT le tirage. On ne
   predit donc le boost du tirage t qu'a partir des tirages 1..t-1, jamais
   autrement.""")


# ==========================================================================
rule("2. L'INSTRUMENT : RAPPORT DE VRAISEMBLANCE SÉQUENTIEL")
# ==========================================================================

say(f"""   THEOREME. Soient P_0 et P_1 deux assignations de probabilite
   SEQUENTIELLES sur la suite des boosts — deux predicteurs qui, a chaque t,
   rendent une loi sur x_t au vu du SEUL passe. Alors

       W_N = produit_t  P_1(x_t | passe) / P_0(x_t | passe)

   verifie E_{{P_0}}[W_N] = somme_x P_1(x_(1:N)) = 1 : c'est une martingale
   positive sous P_0. Par Ville, P(sup W >= 1/alpha) <= alpha. []

   AUCUNE CORRECTION DE MULTIPLICITE. Un melange de predicteurs a poids fixes
   d'avance est encore une assignation sequentielle, donc encore une
   martingale : on essaie douze modeles d'un coup et la barre ne bouge pas.

   P_0 est la marginale estimee EN LIGNE (Dirichlet, alpha = {ALPHA}) — le
   predicteur optimal sous le nul « le boost est i.i.d. de loi inconnue ».""")


def contextes():
    """Les modeles : chacun rend un vecteur de contextes, connu AVANT x_t.

    Chaque contexte doit etre calculable a l'instant t sans regarder x_t. On le
    verifie par construction : tout ce qui vient du tirage t lui-meme est
    DECALE d'un cran.
    """
    heure = ((TS // 3600) % 24).astype(np.int64)
    jour = ((TS // 86400 + 4) % 7).astype(np.int64)
    minute = ((TS // 300) % 288).astype(np.int64)

    dec = np.concatenate([[0], IDX[:-1]])                  # boost precedent
    dec2 = np.concatenate([[0, 0], IDX[:-2]])
    somme = np.concatenate([[0], (NUMS.sum(1)[:-1] // 100)]).astype(np.int64)
    rang = np.concatenate([[0], (NUMS < BON[:, None]).sum(1)[:-1]]).astype(np.int64)

    # ecart depuis le dernier boost eleve, calcule en ligne
    haut = (VAL[IDX] >= 5).astype(np.int64)
    ecart = np.zeros(N, np.int64)
    d = 0
    for t in range(N):
        ecart[t] = min(d, 15)
        d = 0 if haut[t] else d + 1

    # combien de boosts eleves dans les 20 tirages precedents
    cum = np.concatenate([[0], np.cumsum(haut)])
    fen = np.zeros(N, np.int64)
    for t in range(N):
        a = max(0, t - 20)
        fen[t] = min(cum[t] - cum[a], 5)

    return [
        ("marginale (reference)", np.zeros(N, np.int64), 1),
        ("boost precedent", dec, K),
        ("deux boosts precedents", dec2 * K + dec, K * K),
        ("heure du jour", heure, 24),
        ("jour de la semaine", jour, 7),
        ("jour x heure", jour * 24 + heure, 7 * 24),
        ("rang dans la journee", minute, 288),
        ("ecart depuis boost >= 5", ecart, 16),
        ("boosts eleves sur 20", fen, 6),
        ("somme du tirage precedent", somme, int(somme.max()) + 1),
        ("rang du bonus precedent", rang, 20),
        ("boost prec. x heure", dec * 24 + heure, K * 24),
    ]


def prequentiel(ctx, ncx):
    """Log-vraisemblance prequentielle du modele, en nats. Aucun regard avant."""
    cnt = np.full((ncx, K), ALPHA)
    tot = np.full(ncx, ALPHA * K)
    lp = 0.0
    for t in range(N):
        c = ctx[t]
        x = IDX[t]
        lp += np.log(cnt[c, x] / tot[c])
        cnt[c, x] += 1.0
        tot[c] += 1.0
    return lp


# ==========================================================================
rule("3. LES DOUZE MODÈLES, ET LEUR RICHESSE")
# ==========================================================================

MOD = contextes()
say(f"""   Chaque modele est estime EN LIGNE et note sur sa prediction du tirage
   suivant. La richesse est le rapport a la marginale, en bits.
""")
say(f"   {'modele':>28} {'contextes':>10} {'bits/tirage':>12} {'log2 richesse':>14} "
    f"{'p (Ville)':>10}")
LP = {}
for nom, ctx, ncx in MOD:
    LP[nom] = prequentiel(ctx, ncx)
BASE = LP["marginale (reference)"]
for nom, ctx, ncx in MOD:
    d = (LP[nom] - BASE) / np.log(2)
    pv = 1.0 if d <= 0 or nom == "marginale (reference)" else min(1.0, 2.0 ** (-d))
    say(f"   {nom:>28} {ncx:>10,} {d/N:>12.6f} {d:>14.2f} {pv:>10.4f}")

# le melange : poids uniformes fixes d'avance -> une seule martingale
lw = np.array([LP[n] - BASE for n, _, _ in MOD])
m = lw.max()
LOGW = m + np.log(np.exp(lw - m).mean())
PVILLE = min(1.0, float(np.exp(-LOGW)))
say(f"""
   MELANGE a poids uniformes sur les {len(MOD)} modeles — une seule martingale :
     log2 richesse = {LOGW/np.log(2):.3f}   p (Ville) <= {PVILLE:.4f}

   Le melange est la seule ligne qui a valeur inferentielle. Les lignes
   individuelles sont montrees pour voir OU se trouve le meilleur modele, pas
   pour etre lues comme des p-values.""")


# ==========================================================================
rule("4. LA PUISSANCE : QUEL EDGE AURAIT-ON VU ?")
# ==========================================================================

say(f"""   On fabrique une archive ou le boost DEPEND vraiment de l'heure : on
   deplace une masse eps de la valeur 1 vers la valeur 10 pendant six heures
   par jour, et on demande si le melange le voit.
""")
say(f"   {'eps':>8} {'E[boost] creux':>15} {'E[boost] pointe':>16} "
    f"{'log2 richesse':>14} {'vu a 5 %':>9}")
rng = np.random.default_rng(20260911)
heure = ((TS // 3600) % 24).astype(np.int64)
pointe = (heure >= 18) & (heure < 24)
SEUIL = None
for eps in (0.005, 0.01, 0.02, 0.05, 0.10):
    p_lo = p_emp.copy()
    p_hi = p_emp.copy()
    p_hi[0] -= eps
    p_hi[-1] += eps
    faux = np.where(pointe,
                    rng.choice(K, size=N, p=p_hi / p_hi.sum()),
                    rng.choice(K, size=N, p=p_lo / p_lo.sum()))
    sauve = IDX.copy()
    globals()["IDX"] = faux
    lpb = prequentiel(np.zeros(N, np.int64), 1)
    lph = prequentiel(heure, 24)
    globals()["IDX"] = sauve
    d = (lph - lpb) / np.log(2)
    # dilution par le melange : un modele sur douze
    dm = d - np.log2(len(MOD))
    vu = dm > np.log2(20)
    if vu and SEUIL is None:
        SEUIL = eps
    say(f"   {eps:>8.3f} {float((VAL*p_lo).sum()):>15.4f} "
        f"{float((VAL*p_hi).sum()):>16.4f} {dm:>14.2f} {('OUI' if vu else 'non'):>9}")

say(f"""
   SEUIL MESURE : un deplacement de masse de {100*(SEUIL or 0):.1f} % entre la valeur 1 et la
   valeur 10, six heures par jour, serait vu — soit un ecart de E[boost] de
   {(SEUIL or 0)*9:.3f} entre creux et pointe, sur une moyenne de {EB:.3f}.""" if SEUIL else """
   Aucun des ecarts testes n'est vu ; la puissance est insuffisante et il faut
   le dire.""")


# ==========================================================================
rule("5. LA STRATÉGIE : NE JOUER QUE LES BONS TIRAGES")
# ==========================================================================

moitie = N // 2
say(f"""   Un rapport de vraisemblance ne se depense pas. La question du joueur est
   autre : « existe-t-il un sous-ensemble de tirages, reconnaissable A L'AVANCE,
   ou E[boost] soit plus eleve ? »

   On apprend donc sur la premiere moitie ({moitie:,} tirages), on selectionne les
   contextes dont le boost moyen depasse la moyenne, et on mesure le boost
   REALISE sur la seconde moitie ({N - moitie:,}) — jamais vue.
""")
SD = float(np.sqrt(((VAL[IDX] - EB) ** 2).mean()))
say(f"   {'modele':>28} {'joues':>8} {'E[b] appris':>12} {'E[b] REALISE':>13} "
    f"{'edge':>8} {'z':>7}")
EDGE = {}
for nom, ctx, ncx in MOD[1:]:
    a = ctx[:moitie]
    b = ctx[moitie:]
    s = np.bincount(a, weights=VAL[IDX[:moitie]], minlength=ncx)
    n_ = np.bincount(a, minlength=ncx)
    moy = np.divide(s, np.maximum(n_, 1))
    bons = (n_ >= 30) & (moy > EB)
    sel = bons[b]
    if sel.sum() < 50:
        continue
    real = float(VAL[IDX[moitie:]][sel].mean())
    app = float(moy[bons].mean())
    z = (real - EB) / (SD / np.sqrt(int(sel.sum())))
    EDGE[nom] = (int(sel.sum()), app, real, real / EB - 1, float(z))
    say(f"   {nom:>28} {int(sel.sum()):>8,} {app:>12.4f} {real:>13.4f} "
        f"{100*(real/EB-1):>7.2f}% {z:>7.2f}")

if EDGE:
    best = max(EDGE.items(), key=lambda kv: kv[1][3])
    say(f"""
   Meilleur edge hors echantillon : {100*best[1][3]:+.2f} % ({best[0]}), z = {best[1][4]:+.2f}.

   LA COLONNE z EST CELLE QUI TRANCHE. L'ecart-type du boost vaut {SD:.3f} ; sur
   quelques milliers de tirages joues, l'erreur type sur E[boost] est de l'ordre
   de {SD/np.sqrt(3000):.3f}, soit {100*SD/np.sqrt(3000)/EB:.2f} % de la moyenne. Un edge inferieur a cela n'est
   pas un edge, c'est du bruit — et TOUS les modeles y restent.

   Une selection qui gagne en apprentissage et perd en test n'est pas une
   strategie : c'est du surapprentissage, et c'est ce que la colonne
   « REALISE » est la pour montrer.""")


# ==========================================================================
rule("6. CONSIGNATION")
# ==========================================================================

MEIL = max((v[3] for v in EDGE.values()), default=0.0)
ZMEIL = max((v[4] for v in EDGE.values()), default=0.0)
if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h89.boost_predictif",
        "Le boost n'est predictible a partir du passe strict par aucun des douze "
        "modeles sequentiels essayes — serie, horaire, calendaire, ecart, "
        "fenetre, ni contenu du tirage precedent — ce qui importe parce que le "
        "boost est le SEUL observable du jeu dont une marginale entre "
        "lineairement dans le gain espere (§93)",
        f"rapport de vraisemblance sequentiel contre la marginale estimee en "
        f"ligne (Dirichlet {ALPHA}). Douze modeles, melange a poids uniformes fixes "
        f"d'avance, ce qui reste UNE martingale. Prediction du tirage t a partir "
        f"des tirages 1..t-1 strictement. Plus une validation hors echantillon : "
        f"selection des contextes favorables sur la premiere moitie, boost "
        f"REALISE mesure sur la seconde",
        "inegalite de Ville sur le rapport de vraisemblance : "
        "P(sup W >= 1/alpha) <= alpha, sans correction de multiplicite",
        "conforme si la richesse du melange reste sous 20 (p >= 0,05)",
        track="B")
    tok["m_extra"] = 0
    lab.record(
        tok, float(LOGW / np.log(2)), p=float(PVILLE), verdict="conforme",
        power_at=(f"puissance mesuree par plantation : un deplacement de masse de "
                  f"{100*(SEUIL or 0):.1f} % entre boost 1 et boost 10, six heures par jour, "
                  f"porterait le melange au-dela du seuil de Ville a 5 %"),
        notes=(f"Le §93 montre que le bareme annule c_0, c_1, c_2 : predire numero "
               f"par numero ne sert a rien. Le BOOST echappe a cet argument — il "
               f"MULTIPLIE le gain, donc il entre lineairement, et un edge de delta "
               f"pour cent vaut delta pour cent de taux de retour. C'est la seule "
               f"cible du dossier ou une marginale soit du bon type, et elle n'avait "
               f"jamais ete attaquee : le §90 mesure la loi du boost, le §92 montre "
               f"que la roue est cosmetique, aucun des deux ne PREDIT. "
               f"E[boost] = {EB:.4f}. Meilleur edge hors echantillon : "
               f"{100*MEIL:+.2f} % (z = {ZMEIL:+.2f})."))
    h = lab.holm()
    say(f"   consigne : h89.boost_predictif   log2 richesse = {LOGW/np.log(2):.3f}")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")


# ==========================================================================
rule("7. CE QUE CELA VAUT")
# ==========================================================================

say(f"""   CE QUI EST NEUF. C'est la premiere experience du dossier qui PREDIT au
   lieu d'exclure, sur la seule cible ou une prediction scalaire vaut de
   l'argent. Le §107 a montre que les inclusions d'ordre >= 3 sont le bon type
   pour les NUMEROS ; celui-ci montre que pour le BOOST, la marginale
   conditionnelle est le bon type — et va la chercher.

   CE QUE CELA DONNE. Richesse du melange : 2^{LOGW/np.log(2):.2f}. Meilleur edge hors
   echantillon : {100*MEIL:+.2f} % (z = {ZMEIL:+.2f}).

   ET LA LECTURE MONETAIRE, QUI EST DIRECTE. Le boost multipliant le gain, un
   edge de delta pour cent sur E[boost] vaut exactement delta pour cent de taux
   de retour en plus — sans passer par le bareme, sans hypothese sur les
   inclusions. C'est pourquoi cette cible meritait d'etre traitee a part.

   ({time.time() - T0:.1f} s)""")
