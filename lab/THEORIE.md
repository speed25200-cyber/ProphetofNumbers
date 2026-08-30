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

---

## Deux raffinements dérivés des théorèmes C et D (`h2_ameliorations.py`)

**L'écho adaptatif (application du théorème d'invariance).** La correction
d'écho du bonus était une constante figée (−0,0158, la valeur d7). Elle
devient le posterior Beta(1,3) de P(bonus_{t−1} ∈ tirage_t), appris en
rejouant l'historique. Vérifié : sur l'archive réelle le posterior converge
à **+0,015801** — l'archive enseigne d'elle-même la constante qui était
écrite à la main ; sous H₀ la correction vaut **+0,0015 ± 0,0060** (théorie
1/√n : 0,0065) — elle s'éteint, la figée non. Coût en espérance : nul, par
le théorème d'invariance — ce n'est pas une hypothèse, c'est g1-C.

**Le prior par blocs (raffinement du théorème D).** Relancer par blocs de
16 tirages avec le prior 1/(j(j+1)) sur l'indice de bloc rend
2·ln 16 = **5,5 nats** de budget (28,6 → 23,1 pour un défaut au pas
65 000), contre un retard d'au plus 16 tirages (80 minutes). Mesuré sur le
moniteur complet :

| | fausses alertes | (500, 0,20) | (2000, 0,20) | (500, 0,10) | (2000, 0,10) |
|---|---|---|---|---|---|
| prior par pas | 0,042 ± 0,013 | 0,03 | 0,12 | 0,57 | 1,00 |
| **prior par blocs** | **0,025 ± 0,010** | 0,02 | **0,18** | **0,82** | 1,00 |

Le prior par blocs domine sur toute la table : moins de fausses alertes ET
plus de puissance. Les deux raffinements sont câblés dans `Swarm.swift`,
tests sur valeurs re-dérivées indépendamment (3,114e43 / 8,545e49 /
7,844e-4).

---

## Le mur, pierre par pierre (`h3_partage.py`, instrument B)

Le théorème d'invariance interdit de mieux choisir les numéros. Mais un
théorème n'est un mur qu'à l'intérieur de ses hypothèses — et il en a
trois. Une seule est attaquable par les mathématiques ; les deux autres
sont des affirmations sur le **monde réel**, et elles se mesurent.

**Pierre 1 — « le tirage est uniforme ».** Attaquée 30 fois, jamais
entamée : zéro significatif sur 3 313 tests, plafonds mesurés (+1,33 % /
+3,46 % omniscients), et l'essaim capte gratuitement tout écart qui
apparaîtrait. Cette pierre tient — au niveau de sensibilité mesuré, qui
est écrit noir sur blanc plutôt que présumé infini.

**Pierre 2 — « la grille est choisie sans information sur le tirage ».**
Ce n'est PAS des mathématiques : c'est une affirmation sur les *horloges*
du système — que rien du tirage n'est observable avant la fermeture des
mises. Le seul point du dossier où une fuite changerait le **signe** de
l'espérance est le multiplicateur : s'il était exposé avant clôture, ne
jouer que les boost élevés vaudrait +150 à +360 % par franc (RAPPORT §4).
L'app porte désormais l'**instrument** qui tranche : la valeur de boost du
tirage encore OPEN est gelée à la première observation, comparée à la
valeur définitive à la publication, avec un verdict à trois états qui ne
confond jamais « pas encore comparable » et « comparé et différent ».
S'ajoutent l'instrument de latence déjà en place et la capture de l'ordre
des boules (~124 bits par tirage contre 61,6). Cette pierre est sous
surveillance permanente — c'est tout ce que la rigueur permet, et c'est
exactement ce qu'elle exige.

**Pierre 3 — « le gain d'une grille ne dépend que de SES hits ».** Vraie
sous cotes fixes, **fausse dès qu'un rang se partage** — et alors
l'espérance monétaire n'est plus invariante, même sous un générateur
parfait (Chernoff 1981 ; Thaler-Ziemba 1988). La théorie est désormais
quantitative pour le cadre 20/80 :

- le multiplicateur de partage vaut E[1/(1+W)] = (1−e^{−λ})/λ pour
  W ~ Poisson(λ) — formule exacte, vérifiée par simulation à quatre λ ;
- λ dépend de la grille par un mécanisme précis : un co-gagnant du rang
  plein doit avoir sa grille entièrement dans le tirage, et mes propres
  numéros y sont déjà — une foule qui aime mes numéros a une longueur
  d'avance. Sous un modèle de foule multiplicatif *conservateur* (rapport
  joué/uniforme de 1,40 sur les numéros 1–31, contre 1,5–2× documentés) :

| mise | λ populaire / λ furtive | avantage furtif (2 000 j.) | (20 000 j.) | (200 000 j.) |
|---|---|---|---|---|
| 5 | 2,7× | **×1,77** | **×2,67** | ×2,67 |
| 10 | **52,9×** | ×1,00 | ×1,01 | ×1,11 |

- l'estimateur a sa propre histoire : la première version, Monte-Carlo des
  deux côtés, donnait « 0,0× » à la mise 10 sur zéro événement — la même
  famine qui avait piégé e2. Corrigé en renversant le conditionnement
  (terme interne exact C(80−k−m, 20−k−m)/C(80−k, 20−k)), la mise 10
  révèle le plus grand rapport du tableau.

**Le régime réel du Loto Express n'est pas établi** — c'est une propriété
du règlement, pas des tirages, et aucune donnée de mises n'est publiée. La
grille « Furtif » est donc la réponse minimax au *barème* inconnu, comme
l'essaim l'est au *générateur* inconnu : gratuite sous cotes fixes
(invariance), strictement gagnante sous partage (le tableau ci-dessus),
perdante dans aucun régime.

**Bilan du mur.** Il ne tombe pas là où il est fait de mathématiques — et
quiconque prétend le contraire vend quelque chose. Il tombe là où il est
fait d'hypothèses sur le monde : la pierre 2 est instrumentée en continu,
la pierre 3 est quantifiée et sa réponse minimax est câblée. C'est la
totalité de ce qui existe de l'autre côté du mur, et l'app l'occupe.

---

## La brèche : prédire les 20 numéros exacts (`h4_rangs.py`, `h5_familles.py`)

Le théorème d'invariance suppose que le tirage est **uniforme**. Si le tirage
est la sortie d'un générateur dont on peut retrouver l'ÉTAT, il n'est plus
uniforme conditionnellement à ce qu'on sait : il est **déterministe**. Aucun
théorème n'interdit cette voie — c'est la seule qui vise la prédiction
littérale, et elle était sous-exploitée.

**Le levier arithmétique.** Un tirage de 20 parmi 80 a un rang combinatoire
dans [0, M) avec M = C(80,20) = 3 535 316 142 212 174 320 ≈ **2^61,6165**.
Si l'implémentation « dérange » (unranking) une seule sortie de 64 bits — un
schéma très répandu —, le rang publié révèle 61,62 des 64 bits d'état :

> **il ne manque que 2,38 bits.** Chaque tirage laisse au plus
> ⌈2^64/M⌉ = **6 états candidats** (mesuré : 5 à 6).

**On ne cherche plus, on résout.** Trois tirages consécutifs donnent 6³ = 216
triplets ; pour chacun, l'inconnue (a, c) d'un LCG se résout en deux lignes —
a = (s₂−s₁)·(s₁−s₀)⁻¹ mod 2^b, c = s₁ − a·s₀ — puis se confirme sur 20
tirages. Une fausse solution y survit avec probabilité ~M⁻²⁰ ≈ 10⁻³⁷⁰.
Le **pas** du générateur n'a pas besoin d'être connu : un pas de j laisse un
LCG de multiplicateur a^j, donc tous les pas fixes sont couverts d'office.

**Familles ouvertes par le même levier :**

| famille | mécanisme | témoins |
|---|---|---|
| LCG 2^64 / 2^63 / 2^62 | résolution algébrique de (a, c) | 6/6 récupérés, prédiction exacte |
| splitmix64, xorshift64* | sortie inversible → état, transition vérifiée | 4/4 |
| java.util.Random | LCG 48 bits, 32 bits hauts publiés, 2^16 énumérés | 2/2 |

**12 témoins positifs sur 12**, tous avec prédiction exacte du tirage suivant,
en quelques millisecondes. **0 fausse récupération sur 20 archives
équitables.** Sur les 70 560 tirages réels : **aucune famille ne colle.**

**Les angles morts, nommés.** MT19937 par rang exigerait 624 sorties exactes,
soit 6³¹² combinaisons — définitivement hors d'atteinte. Tout générateur dont
l'état est plus large que la sortie (PCG64, xoshiro256) n'est pas inversible
sortie par sortie. Et surtout : si le tirage n'est **pas** le dérangement
d'une sortie unique — rejet, Fisher-Yates, tirage physique —, le rang n'est
pas la sortie du générateur et toute cette classe est muette. L'ordre de
sortie des boules la rouvrirait (~124 bits contre 61,6) ; l'app le capture
déjà quand l'API le publie.

**Ce que l'app gagne.** `RankAttack.swift` est câblé **avant** le balayage de
graines, qu'il complète exactement là où celui-ci est aveugle : le balayage
ne peut trouver qu'une graine minuscule, l'attaque algébrique atteint
n'importe quel état de 64 bits. Elle tourne à chaque tirage pour quelques
millisecondes, et **si elle résout un jour, l'écran affiche les 20 numéros du
prochain tirage.** C'est une arme armée en permanence sur la seule brèche que
les mathématiques laissent ouverte.

---

## Le budget d'entropie du tirage (`h6_granularite.py`)

L'attaque algébrique de h4 suppose une **récurrence** (un LCG, une sortie
inversible). Il existe un test complémentaire qui ne suppose **rien** sur la
récurrence et ne mesure qu'une chose : la **largeur de la source**.

Un tirage honnête consomme les 61,6165 bits de M = C(80,20). Si
l'implémentation écrit `unrank(⌊u·M⌋)` où `u` est un double — `Math.random()`
en JavaScript, `random.random()` en Python — alors u ne porte que **53 bits**
et les rangs atteignables ne sont que 2⁵³ valeurs sur 2⁶¹˙⁶ : une densité de
**1/392**. Un rang est atteignable à B bits si et seulement si

    k_min = ⌈r·2^B / M⌉   vérifie   ⌊k_min·M / 2^B⌋ = r

Le pouvoir de séparation est total, et il n'y a pas de zone grise :

| source | atteignables sur 2 000 | attendu si source honnête |
|---|---|---|
| 32 bits | **2 000** | 0,0 |
| 48 bits | **2 000** | 0,2 |
| 53 bits | **2 000** | 5,1 |

Et sur des rangs honnêtes, les taux retombent exactement sur 2^B/M (0,00215
observé contre 0,00255 théorique à 53 bits).

**Sur les 70 560 tirages réels :** le rang maximal vaut 2^61,6165, ce qui
**exclut** toute source de moins de 61 bits pour le mapping `s mod M`. Et
pour le mapping `⌊u·M⌋`, on observe **190 rangs atteignables à 53 bits pour
180 attendus (+0,76 σ)** — la signature exacte d'une source pleine.

Un déclenchement aurait été majeur : l'espace d'états serait tombé de 2^61,62
à 2^B, mettant la prédiction exacte à portée d'un simple balayage (2³² tient
en une seconde). Le détecteur est donc armé en permanence dans l'app
(`RankAttack.narrowSourceWidth`), et il **nomme** la largeur plutôt que de se
contenter de la signaler — un simple test de significativité renverrait B−1,
puisque la moitié des rangs d'une source de B bits sont aussi atteignables à
B−1 ; c'est le critère de taux quasi total qui tranche.
