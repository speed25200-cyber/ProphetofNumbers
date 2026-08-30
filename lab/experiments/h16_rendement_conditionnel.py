"""h16 — le rendement conditionnel, et l'identité qui le rend calculable.

Ce que h15 laissait passer
---------------------------
h15 a calculé à quelle FRÉQUENCE la cagnotte dépasse le seuil de bascule.
C'est la bonne question pour savoir combien d'occasions se présentent. Ce
n'est pas la question qui décide s'il faut jouer.

Celle-là est : quand une occasion se présente, elle vaut COMBIEN ? Et la
réponse a une forme fermée d'une simplicité qui n'était pas prévisible.

L'identité
----------
Soit un ticket de prix c à la mise k, p = P(k/k), et S = c/p le seuil de
bascule (h9) : au-delà, la cagnotte seule rembourse la mise. Sous les
hypothèses de h15, la cagnotte suit une loi sans mémoire de moyenne μ, donc

    E[J | J ≥ S] = S + μ                    (absence de mémoire)

et le rendement d'un franc misé, CONDITIONNELLEMENT au fait de ne jouer
qu'au-dessus du seuil, vaut

    p·E[J | J ≥ S] / c = p(S + μ)/c = 1 + p·μ/c = 1 + μ/S

Le gain conditionnel est donc **exactement μ/S** — c'est-à-dire le nombre
que h9 affichait comme « fraction du seuil » en croyant ne mesurer qu'une
distance. Le même rapport, lu dans l'autre sens, est le taux de profit
disponible le jour où le seuil est franchi.

Et ce rapport est une constante du jeu
---------------------------------------
Mieux : μ/S ne dépend ni du nombre de joueurs, ni du prix du ticket, ni de
la mise. Si N grilles sont jouées par tirage, que la cagnotte reçoit une
fraction α de la mise collectée et qu'elle tombe avec probabilité
q ≈ N·p par tirage, alors

    μ = r/q = (α·N·c)/(N·p) = α·c/p = α·S     donc   μ/S = α

**Le gain conditionnel est la part de la mise que l'opérateur verse dans la
cagnotte.** N disparaît : plus de joueurs font monter la cagnotte plus vite
ET la font tomber plus souvent, exactement dans la même proportion.

L'optimum est le seuil lui-même
--------------------------------
On pourrait vouloir attendre plus que le seuil. Le profit espéré PAR TIRAGE
(et non par franc misé) vaut e^(−x)·(α(x+1) − 1) où x = seuil visé / μ ; sa
dérivée s'annule en x = 1/α, c'est-à-dire précisément au seuil de bascule.
Attendre davantage augmente le gain par occasion mais raréfie les occasions
plus vite encore.
"""

import csv
import math
import os
import sys
import time

import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

T0 = time.time()
POOL, DRAWN = 80, 20
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAKES = (5, 6, 7, 8, 10)


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def threshold(k: int) -> float:
    return math.comb(POOL, k) / math.comb(DRAWN, k)


# --------------------------------------------------------------------------
# 1. L'identité, vérifiée sur le processus lui-même
# --------------------------------------------------------------------------

rule("1. VÉRIFICATION — jouer au-dessus du seuil rapporte-t-il bien μ/S ?")

say("""   Ce qui est incertain ici, c'est la loi de la cagnotte ; le reste est
   de l'arithmétique exacte. On simule donc le processus — N joueurs, une
   cagnotte qui reçoit une fraction α de la mise collectée et tombe quand
   quelqu'un gagne — et on y mesure la seule chose qui porte l'identité :

       E[J | J ≥ x] − x  doit valoir μ, pour TOUT x

   C'est l'absence de mémoire, et c'est elle qui donne le gain conditionnel.
   Simuler en plus le tirage gagnant serait une faute de méthode : avec
   p ≈ 10⁻⁴, il faudrait un milliard de tirages joués pour que la moyenne
   empirique du gain veuille dire quelque chose, et à trois millions elle ne
   mesure que du bruit.""")

rng = np.random.default_rng(20260830)
say("""
   L'identité μ/S = α est ASYMPTOTIQUE en λ = N·p, et le tableau le montre
   plutôt que de le taire. Exactement, l'âge moyen d'une cagnotte tombant
   avec probabilité q par tirage vaut (1−q)/q, donc

       μ/S = α · κ    avec  κ = N·p·(1−q)/q  et  q = 1 − (1−p)^N

   κ tend vers 1 quand λ tend vers 0 — c'est-à-dire dans le régime d'une
   cagnotte qui s'accumule visiblement, le seul où cette stratégie a un
   sens. La colonne κ dit à partir d'où l'approximation coûte quelque
   chose.""")
say("\n   α       N        λ=N·p    κ exact   μ/S mesuré   α·κ prédit   E[J|J≥x]−x, x=μ,2μ,3μ")
for alpha in (0.05, 0.15, 0.295):
    for N in (50, 500, 5000):
        c, k = 1.0, 6
        p = 1 / threshold(k)
        S = c / p
        r = alpha * N * c
        q = 1 - (1 - p) ** N
        lam = N * p
        kappa = lam * (1 - q) / q
        steps = 3_000_000
        hits = rng.random(steps) < q
        idx = np.arange(steps)
        last = np.maximum.accumulate(np.where(hits, idx, -1))
        J = r * (idx - last)[last >= 0]
        mu = float(J.mean())
        excess = []
        for x in (mu, 2 * mu, 3 * mu):
            tail = J[J >= x]
            excess.append(float(tail.mean() - x) / mu if tail.size > 30 else float("nan"))
        say(f"   {alpha:<7.3f} {N:<8,} {lam:<8.4f} {kappa:<9.4f} {mu / S:<12.4f} "
            f"{alpha * kappa:<12.4f} "
            + "  ".join(f"{e:.3f}" for e in excess))
        assert abs(mu / S / (alpha * kappa) - 1) < 0.05

say("""
   Trois faits se lisent dans ce tableau, et ce sont les trois qui comptent.

   μ/S mesuré colle à α·κ à moins de 1 % partout : la relation est exacte,
   pas approchée. Et κ reste au-dessus de 0,96 jusqu'à λ = 0,065 ; il ne
   s'effondre qu'à λ = 0,65, où la cagnotte tombe deux tirages sur trois et
   n'accumule plus rien — un régime où personne ne parlerait de cagnotte
   progressive.

   Le nombre de joueurs a disparu du résultat. Plus de joueurs font monter
   la cagnotte plus vite ET la font tomber plus souvent, exactement dans la
   même proportion — d'où μ/S = α, la part de la mise versée dans la
   cagnotte, et rien d'autre.

   Enfin l'excédent au-dessus d'un seuil vaut μ quel que soit ce seuil
   (colonnes de droite, proches de 1) : c'est l'absence de mémoire, mesurée
   plutôt que supposée. D'où le gain conditionnel
   p·E[J | J ≥ S]/c = p·(S + μ)/c = 1 + μ/S = 1 + α.

   Les deux écarts apparaissent ENSEMBLE, à λ = 0,65 : l'excédent y monte à
   1,8 μ parce que la cagnotte n'y prend plus qu'une poignée de valeurs
   distinctes, et κ y chute pour la même raison. Ce n'est pas deux fragilités
   mais une seule — la discrétisation d'une cagnotte qui ne s'accumule
   plus — et elle disparaît dès que λ descend sous 0,1.""")

say("""
   Reste le partage entre gagnants, que h13 a montré non négligeable. Il
   s'inclut exactement, sans simulation : avec W ~ Poisson(λ) autres
   gagnants, le gain devient (1+α)·E[1/(1+W)] − 1. Mêmes N qu'au tableau
   précédent, pour que les deux se lisent ensemble.""")
say("\n   α       N        λ = N·p   E[1/(1+W)]   gain avec partage   sans partage")
for alpha in (0.05, 0.15, 0.295):
    for N in (50, 500, 5000):
        p = 1 / threshold(6)
        lam = N * p
        share = (1 - math.exp(-lam)) / lam if lam > 0 else 1.0
        say(f"   {alpha:<7.3f} {N:<8,} {lam:<9.4f} {share:<12.5f} "
            f"{(1 + alpha) * share - 1:>+17.4f}   {alpha:>+12.4f}")
say("""
   Le partage ne coûte presque rien tant que λ reste petit — 0,3 % de gain
   perdu à λ = 0,006, 3 % à λ = 0,065 — et il retourne le signe à λ = 0,65,
   c'est-à-dire dans le même régime dégénéré que κ. Les deux limites de
   cette stratégie sont donc la MÊME limite, et elle a un nom : une cagnotte
   qui tombe trop souvent pour s'accumuler.""")


# --------------------------------------------------------------------------
# 2. Le seuil de bascule est l'optimum, pas un pis-aller
# --------------------------------------------------------------------------

rule("2. LE SEUIL EST L'OPTIMUM — attendre plus est une erreur")

say("""   Profit espéré PAR TIRAGE en ne jouant qu'au-dessus d'un seuil visé
   S' = x·μ : f(x) = e^(−x)·(α(x+1) − 1). Le maximum est en x = 1/α, soit
   S' = μ/α = S. Vérification numérique, α = 0,295 :""")

alpha = 0.295
say("\n   seuil visé / μ   fraction jouée   gain par occasion   profit par tirage")
best = (None, -1)
for x in (1.0, 2.0, 3.0, 1 / alpha, 4.0, 6.0, 10.0):
    f = math.exp(-x) * (alpha * (x + 1) - 1)
    tag = "  <- le seuil de bascule" if abs(x - 1 / alpha) < 1e-9 else ""
    say(f"   {x:<16.3f} {math.exp(-x):<16.4%} {alpha * (x + 1) - 1:>+17.4f} "
        f"{f:>+18.5f}{tag}")
    if f > best[1]:
        best = (x, f)
say(f"\n   maximum numérique en x = {best[0]:.3f} ; prédit 1/α = {1 / alpha:.3f}")
assert abs(best[0] - 1 / alpha) < 1e-9

say("""
   Attendre une cagnotte plus grosse augmente le gain par occasion, mais
   raréfie les occasions plus vite encore. Le point d'équilibre est
   exactement le seuil de h9 — celui-là même qui définit la bascule.""")


# --------------------------------------------------------------------------
# 3. Ce que valent les occasions, sur les relevés réels
# --------------------------------------------------------------------------

rule("3. LES CHIFFRES, SUR LE SEUL RELEVÉ DISPONIBLE")

rows = []
with open(os.path.join(ROOT, "jackpots_observed.csv")) as fh:
    for r in csv.DictReader(fh):
        rows.append(r)
obs = {k: [float(r[f"j{k}"]) for r in rows if r.get(f"j{k}")] for k in STAKES}

say("   « part cagnotte » est l'estimation de α = μ/S, donc à la fois le gain")
say("   conditionnel et la fraction de la mise que l'opérateur y verse.\n")
say("   mise   cagnotte μ̂     seuil S        part cagnotte α̂   gain conditionnel")
for k in STAKES:
    if not obs[k]:
        continue
    mu = float(np.mean(obs[k]))
    S = threshold(k)
    say(f"   {k:<6} CHF {mu:>10,.0f}   CHF {S:>10,.0f}   {mu / S:>14.1%}   "
        f"{mu / S:>+16.1%}")

k = 6
mu = float(np.mean(obs[k]))
S = threshold(k)
n = len(obs[k])
lo = 2 * n * mu / stats.chi2.ppf(0.975, 2 * n)
hi = 2 * n * mu / stats.chi2.ppf(0.025, 2 * n)
say(f"""
   Et l'incertitude, cette fois, est BEAUCOUP mieux conditionnée qu'au §3 de
   h15 : le gain conditionnel est LINÉAIRE en μ, là où la fréquence en
   dépendait exponentiellement. Avec {n} relevé, à 95 % :

     gain conditionnel à la mise {k} : de {lo / S:+.1%} à {hi / S:+.1%}

   La borne basse est POSITIVE. Sous les hypothèses de h15, et sous elles
   seules, jouer la mise {k} uniquement quand sa cagnotte dépasse
   CHF {S:,.0f} est favorable — pas « moins défavorable », favorable — et ce
   avant même de compter les rangs intermédiaires, qui ne peuvent qu'ajouter.""")


# --------------------------------------------------------------------------
# 4. L'objection du partage, et pourquoi elle se dissout
# --------------------------------------------------------------------------

rule("4. L'OBJECTION DU PARTAGE")

say("""   h13 a montré qu'un rang partagé change l'espérance. Si W autres
   gagnants se présentent, le gain conditionnel devient
   (1 + α)·E[1/(1+W)] − 1, et la stratégie meurt dès que

        E[1/(1+W)] < 1/(1+α)

   Avec W ~ Poisson(λ), cela donne un λ maximal admissible.""")


def e_inv(lam: float, kmax: int = 400) -> float:
    if lam <= 0:
        return 1.0
    tot, logp = 0.0, -lam
    for w in range(kmax):
        tot += math.exp(logp) / (1 + w)
        logp += math.log(lam) - math.log(w + 1)
    return tot


say("\n   α       E[1/(1+W)] requis   λ maximal   soit un gain de cagnotte")
say("                                             tous les … tirages")
for a_ in (0.05, 0.15, 0.295):
    need = 1 / (1 + a_)
    lo_l, hi_l = 0.0, 50.0
    for _ in range(200):
        mid = (lo_l + hi_l) / 2
        if e_inv(mid) > need:
            lo_l = mid
        else:
            hi_l = mid
    lam_max = (lo_l + hi_l) / 2
    say(f"   {a_:<7.3f} {need:<19.4f} {lam_max:<11.3f} {1 / lam_max:>10.1f}")

say("""
   Voilà pourquoi l'objection se dissout. λ n'est pas un paramètre libre :
   c'est le nombre attendu de gagnants par tirage, donc AUSSI le taux auquel
   la cagnotte tombe. Or une cagnotte qui atteint visiblement des milliers
   de francs en s'incrémentant de quelques dizaines par tirage est, par
   construction, une cagnotte qui ne tombe qu'une fois toutes les dizaines
   ou centaines de tirages — soit λ de l'ordre de 0,01.

   Le tableau demande λ < 0,3 environ. Une cagnotte progressive VISIBLE
   satisfait donc la condition avec un ou deux ordres de grandeur de marge.
   Le partage ne devient un problème que pour un rang qui tombe presque à
   chaque tirage — et un tel rang n'accumule pas, donc n'entre jamais dans
   cette stratégie.""")


# --------------------------------------------------------------------------
# 5. Ce qui peut faire mentir tout ceci
# --------------------------------------------------------------------------

rule("5. LES RÉSERVES, ET UNE QUI DEVRAIT INQUIÉTER")

alpha_hat = float(np.mean(obs[6])) / threshold(6)
say(f"""   1. UN α DE {alpha_hat:.1%} EST ANORMALEMENT GÉNÉREUX, et c'est la réserve
      la plus sérieuse. Une cagnotte progressive reçoit typiquement 1 à 5 %
      de la mise collectée, pas trente. Trois explications possibles, et le
      dossier ne peut pas trancher entre elles :
        — l'estimation de μ sur UN relevé est très bruitée (le §3 donne
          l'intervalle, qui est large) ;
        — la cagnotte affichée n'est peut-être pas purement progressive :
          une part fixe abondée par l'opérateur gonflerait μ sans
          correspondre à un α de turnover ;
        — le prix du ticket n'est pas 1 franc. Le seuil S est PAR FRANC : si
          le ticket coûte 2 francs, le vrai seuil double et α̂ est divisé
          par deux.
      Les trois se lèvent avec les mêmes données : une série de relevés, et
      le prix du ticket.

   2. L'ABSENCE DE MÉMOIRE est l'hypothèse qui porte l'identité. Si la
      cagnotte est plafonnée, ou versée à date fixe, E[J | J ≥ S] n'est plus
      S + μ et le gain conditionnel change. Une série de relevés le teste
      directement : sous absence de mémoire, l'excédent au-dessus du seuil a
      la même loi quelle que soit la hauteur du seuil.

   3. LA STRATÉGIE SUPPOSE QU'ON PEUT VOIR LA CAGNOTTE AVANT DE MISER. C'est
      le cas : elle est affichée. Mais elle suppose aussi qu'on peut
      s'abstenir — ce qui, dans un jeu à un tirage toutes les cinq minutes,
      est une contrainte de discipline plus que de mathématiques.

   4. RIEN ICI NE PRÉDIT UN NUMÉRO. Le gain vient du MOMENT choisi, pas du
      choix des numéros — l'invariance reste intacte. Et à ce moment-là,
      c'est la géométrie de h13 qui dit COMMENT répartir les grilles :
      disjointes, pour multiplier par n les chances de toucher le rang
      plein sans rien coûter en espérance.""")

rule(f"total {time.time() - T0:.0f}s")
