# Quatre théorèmes pour mieux prédire — dérivés, puis vérifiés

Le dossier empirique (RAPPORT.md, 30 voies, 3 313 tests, zéro significatif)
a établi qu'aucun choix de numéros ne bat le hasard. Ce document développe
la mathématique des quatre leviers qui décident *réellement* des gains — et
chaque énoncé est vérifié par calcul exact ou simulation fidèle dans
`experiments/h1_theoremes.py` avant d'être écrit ici.

---

## Théorème A — la loi jointe de deux grilles, et la monotonie qui fonde l'étalement

**Cadre.** Deux grilles de k numéros partagent s numéros. Sous H₀ le tirage
est un 20-sous-ensemble uniforme de {1..80}. Les hits (X_A, X_B) suivent la
loi jointe multivariée hypergéométrique sur quatre groupes — partagés (s),
propres à A (k−s), propres à B (k−s), reste (80−2k+s) :

    P(X_A ≥ t, X_B ≥ t) = Σ_{c,a,b} C(s,c)·C(k−s,a)·C(k−s,b)·C(80−2k+s, 20−c−a−b) / C(80,20)
                            (c+a ≥ t, c+b ≥ t)

**Théorème (monotonie, par épuisement du domaine).** À (k, t) fixés,
s ↦ P(X_A ≥ t, X_B ≥ t) est croissante, pour tout k ∈ {5, 6, 7, 8, 10} et
tout t ≤ k. Vérifié sur *l'intégralité* du domaine utilisé par l'app :
**0 violation**, pire accroissement +1,7·10⁻¹⁷ (positif, au bruit machine).
La formule elle-même est contre-vérifiée par Monte-Carlo brut en quatre
points non rares (écarts −1,04 σ à +1,01 σ).

**Corollaire (le fondement de l'étalement).** Chaque marge étant invariante
(hypergéométrique quelle que soit la grille), P(au moins une ≥ t) =
2q − P(les deux ≥ t) est *décroissante* en s : à tout rang t, moins deux
grilles partagent, plus l'une d'elles a de chances d'atteindre t. Le
mécanisme, en un chiffre : à k = 10, P(les deux pleines) va de 2,8·10⁻¹⁹
(disjointes) à 1,1·10⁻⁷ (identiques) — neuf ordres de grandeur d'écart
pour la même paire de marges.

## Théorème B — la dominance rang par rang, e2 tranché sans Monte-Carlo

e2 concluait que l'étalement ne domine PAS aux rangs 9-10 de la mise 10 —
sur ~85 et ~5 événements Monte-Carlo. Le sandwich de Bonferroni, avec S2
exact (66 paires, théorème A) et S3 majoré par Σ min(joints par paire),
donne :

    S1 − S2  ≤  P(∃ grille ≥ t)  ≤  S1 − S2 + S3⁺

et au rang plein, l'inclusion-exclusion **complète** (4 095 sous-ensembles)
est exacte, car P(toutes pleines d'un sous-ensemble) ne dépend que de
l'union. Sur 12 jeux de champs, mêmes champs pour les deux géométries :

| rang | étalée | ancienne | dominance prouvée |
|---|---|---|---|
| t = 8 | [1,699e-3, 1,700e-3] | [1,584e-3, 1,585e-3] | **12/12** |
| t = 9 | [7,479e-5, 7,479e-5] | [7,139e-5, 7,140e-5] | **12/12** |
| t = 10 (exact) | 1,3465e-6 | 1,3112e-6 | **12/12**, rapport 1,0269 |

Le « NON » de e2 était un artefact de comptage. **La géométrie étalée
domine à tous les rangs, à toutes les mises — prouvé, plus mesuré.** Et par
le théorème A, la dominance vaut sous *n'importe quel* barème positif :
l'ignorance du barème est sans conséquence pour cette décision.

## Théorème C — le regret de l'essaim borne la distance au minimax

Sous H₀, la politique perd exactement 0 (invariance de la loi complète,
g1-C). Sous une alternative où une tête du banc porte une avance de
ε hit/tirage, AdaHedge garantit

    hits(essaim) ≥ hits(meilleure tête) − 2·√(T·ln N)·(20/T)   hit/tirage

soit une franchise de 0,272 hit/tirage à T = 70 547 — et la franchise
*réelle* mesurée par f3 est de **0,016**, six pour cent de la borne. La
politique est donc minimax à un terme évanescent près, sans savoir si
l'alternative est vraie. C'est l'« assurance gratuite » avec sa franchise
écrite : gratuite en espérance sous H₀, à franchise O(√(ln N / T)) → 0
sous les alternatives.

## Théorème D — la frontière de détection, et la faille qu'elle a révélée

Pour un défaut de divergence d(θ\*) nats/tirage sur une fenêtre L finissant
au temps t, le critère de dérive moyenne du moniteur est

    détectable  ⇔  L·d(θ*) ≳ ln(seuil · nb_paris) + ln(poids de la relance)

d(θ) = θ·p₁ − ln(p₀·e^θ + 1 − p₀), θ* le meilleur de la grille. La
simulation fidèle du moniteur (32 paris, 70 560 pas) a confirmé trois
prédictions sur quatre — et la quatrième a mis au jour une **faille du
moniteur que ce même labo avait fait câbler** :

R_t = (1 + R_{t−1})·f_t est une *sous*-martingale (E[R_{t+1}|F_t] = 1 + R_t).
R_t/t est donc une e-valeur à chaque instant *fixé*, mais son supremum au
fil du temps n'est **pas** couvert par l'inégalité de Ville. Mesuré :
**12 % de fausses alertes** sur 70 560 pas, pour 5 % promis à l'écran.

**Le correctif (mixture à trésorerie).** Poids a priori w_k = 1/(k(k+1))
par instant de relance (Σ w_k = 1), et les paris pas encore lancés comptent
leur trésorerie :

    S_t = f_t·(S_{t−1} + w_t)          (récurrence O(1))
    N_t = S_t + Σ_{k>t} w_k = S_t + 1/(t+1)

N_t est une **vraie martingale positive de moyenne 1** : Ville s'applique au
supremum. Mesuré : fausses alertes **0,042 ± 0,013** (240 archives
simulées) — la garantie de 5 % redevient vraie, à tout instant. Le prix :
un défaut commençant au pas k coûte ln(k(k+1)) ≈ 2·ln k nats de plus, et la
puissance mesurée passe p. ex. de 1,00 à 0,62 sur (L = 500, p₁ = 0,10) —
c'est le prix exact de l'honnêteté uniforme dans le temps, payé en
connaissance de cause. Câblé dans `Swarm.swift`, test à l'appui (valeurs
re-dérivées indépendamment : 1,666e42 / 1,224e50 / 4,908e-5).

**Limite assumée.** La frontière de dérive moyenne est un squelette à
quelques nats près : les fluctuations √(L·v) et les relances internes au
défaut la floutent (un cas prédit « invisible » à 12,8 nats sort à 0,77 de
puissance sous le moniteur non corrigé). C'est la simulation qui fait foi —
comme partout dans ce labo.

## Théorème E — l'anti-foule, conditionnel et honnête

Si un rang de gain est *partagé* entre gagnants (pari mutuel), l'espérance
monétaire d'une grille dépend de sa popularité : E[gain] =
prix·P(rang)/E[1 + autres gagnants], et les numéros impopulaires deviennent
strictement meilleurs — c'est le résultat classique de Chernoff (1981) sur
le Numbers Game du Massachusetts. Sous cotes fixes, l'effet est nul
(théorème d'invariance). Le dossier n'établit pas quel régime s'applique au
Loto Express : la grille « Furtif » reste donc au conditionnel dans l'app —
gratuite sous cotes fixes (invariance), gagnante sous partage. C'est le même
argument minimax que le théorème C, appliqué au barème au lieu du
générateur.

---

## Ce que ces théorèmes changent

1. **L'étalement est un théorème** (A + B), plus une mesure : dominance à
   tous les rangs, sous tout barème, prouvée par bornes exactes.
2. **La politique de l'app est minimax quantifié** (C) : franchise réelle
   0,016 hit/tirage, bornée par 0,272.
3. **Le moniteur est redevenu honnête** (D) : 12 % → 4,2 % de fausses
   alertes, garantie α = 5 % vraie à tout instant, au prix documenté de
   2·ln k nats sur les défauts tardifs.
4. **« Furtif » a sa théorie** (E) : gratuite ou gagnante selon le régime de
   barème, jamais perdante en espérance.
