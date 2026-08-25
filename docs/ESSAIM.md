# L'Essaim — architecture de prédiction de Prophet

Prophet ne repose plus sur un ensemble figé de 6 têtes : le moteur
(`Prophet/Services/Swarm.swift`) est un **essaim de 26 prédicteurs en
compétition**, pondérés en ligne et capables d'évoluer. Ce document décrit
l'architecture, les algorithmes et — surtout — ce que l'essaim peut et ne
peut pas faire.

## 1. Les 26 têtes, en 11 familles

| Famille | Têtes | Signal capté |
|---|---|---|
| **Bayes** | Beta escompté, mémoires ≈ 10 / 33 / 200 | Fréquence de sortie, avec oubli exponentiel (power prior) |
| **EWMA** | Lissages 8 / 25 / 64 | Momentum de fréquence à trois horizons |
| **Hawkes** | Demi-vies 2,3 / 3,9 / 8,7 | Grappes auto-excitatrices (processus de Hawkes discret) |
| **Écarts** | Weibull k=1,25 / k=1,55, hazard empirique, écart-z | Numéros « dus » : survie paramétrique, hazard non paramétrique P(sortie \| écart), absence normalisée |
| **Spectre** | Résidu 16/64, Momentum 8/32 | Croisements de moyennes mobiles sur la série binaire |
| **Markov** | Markov-1, Markov-3, Séries | P(sortie \| présences récentes) estimée en ligne, longueur de série |
| **Graphe** | PMI de paires | Activation des partenaires fréquents du dernier tirage |
| **ACP** | Axes 1 et 2 (règle d'Oja) | Structure résiduelle de covariance, extraite en ligne |
| **Contra** | Anti-EWMA-25, Anti-Hawkes | Sondes contrariennes : si le momentum trompe systématiquement, l'essaim l'apprend |
| **Pression** | Zones | Déficit récent des décades et de la parité |
| **Géo** | Voisinage, Rangs | Géométrie du tableau officiel 8×10 : P(sortie \| k voisins sortis) auto-calibrée, déficit des rangées. La disposition étant fixe, la géométrie n'ajoute aucune information aux numéros — ces têtes testent l'hypothèse et convergent vers le neutre si elle est fausse. L'app affiche aussi le comptage des paires adjacentes vs le hasard exact (≈ 8,54 attendues) |

Chaque tête est un automate incrémental : `absorb(tirage)` met à jour son
état, `field()` rend un score par numéro (1–80). Les champs sont
normalisés en z-score avant combinaison, donc comparables entre familles.

## 2. Le méta-apprentissage : Hedge à part fixe

Les poids de l'essaim ne sont pas fixés à la main. À chaque tirage
historique `t` :

1. les champs et les poids sont **figés avant d'observer le tirage** ;
2. le top-20 de chaque tête est comparé au tirage réel → récompense
   `r = (hits − 5) / 20` ;
3. mise à jour multiplicative `w ← w · exp(η·r)` (Hedge, Freund &
   Schapire 1997), puis normalisation ;
4. **part fixe** de 2 % redistribuée uniformément (Fixed-Share, Herbster &
   Warmuth 1998) : aucune tête ne meurt jamais, et l'essaim se réadapte
   vite si le « régime » change.

C'est la version en ligne, avec garanties de regret, de ce que faisait
l'ancien softmax sur recouvrement moyen — en plus réactif et plus robuste.

## 3. L'évolution : mutation du plus faible vers le plus fort

Toutes les 24 absorptions, dans chaque famille paramétrique (Bayes, EWMA,
Hawkes) : si l'écart de performance récente entre la meilleure et la pire
tête dépasse 0,35 hit, la pire **adopte la mémoire de la meilleure**, avec
un jitter déterministe de ±30 % (générateur congruentiel semé de façon
fixe — le moteur reste reproductible : mêmes tirages ⇒ même résultat).
Son historique de performance et son poids sont réinitialisés. Le compteur
de génération, visible dans l'app, trace ces mutations.

L'essaim explore ainsi l'espace des hyperparamètres en continu, sans
optimisation hors ligne ni fuite d'information.

## 4. Sous-essaims et grilles

- **Alpha** = blend des têtes momentum (Hawkes, EWMA, Markov, Momentum
  spectral), pondérées par leurs poids Hedge renormalisés.
- **Omega** = blend des têtes de retour (écarts, résidu spectral,
  pression).
- **Nexus** = essaim complet + bonus d'information mutuelle (PMI) dans la
  sélection gloutonne, avec caps par décade et équilibre pair/impair.

Chaque stratégie décline trois variantes : **I** (sélection principale),
**II** (disjointe de la I — double la couverture du champ) et **Anti**
(le pari inverse : les numéros classés derniers). L'Anti est la
contre-épreuve vivante du modèle — sur un RNG équitable elle fait jeu
égal avec la principale, et le bilan de l'app le mesure en continu.

## 5. La mesure honnête : backtest en marche avant

Tout est jugé par le **backtest walk-forward** : à chaque tirage
historique, les hits du top-20 de l'essemble figé sont enregistrés. La
moyenne, l'écart-type et le z-score contre l'espérance uniforme (5,00
hits) sont affichés dans l'app (« Vérité terrain »), ainsi que la
meilleure tête *a posteriori* — étiquetée comme telle, parce que choisir
le vainqueur après coup surestime toujours.

Le « signal » affiché (50 = hasard pur) est dérivé de ce z-score et de
rien d'autre.

## 5 bis. Le test séquentiel par pari (e-process)

Au-delà du z-score, Prophet embarque l'état de l'art de l'inférence
séquentielle : un **test par pari** (*testing by betting* — Shafer 2021,
Ramdas et al. 2023). Sous H0 (tirage uniforme), le recouvrement du top-20
figé suit une hypergéométrique connue ; à chaque tirage, une martingale
« parie » via l'inclinaison exponentielle q(o) ∝ p0(o)·e^{±θo}. Sa
richesse cumulée a une espérance de 1 sous H0, donc par l'inégalité de
Ville : **P(richesse ≥ 20) ≤ 5 % à tout instant** — le test est valide en
continu, sans correction de tests multiples ni p-hacking. Le mélange
bilatéral (θ > 0 et θ < 0) détecte aussi bien une sur- qu'une
sous-performance. Si le générateur de Loro était biaisé, c'est cet
indicateur qui monterait — aussi vite que la théorie le permet.

## 6. La couche décision : valeur du jackpot

Les numéros ne sont pas prédictibles, mais la **mise** est un choix
rationnel : l'app calcule le retour espéré du seul jackpot par franc misé
(jackpot courant × probabilité hypergéométrique exacte du k/k) pour
chaque mise, et marque la plus « rentable » du moment. L'espérance totale
reste négative — l'app le dit — mais c'est le seul levier où les
mathématiques ont réellement quelque chose à optimiser.

## 7. Ce que l'essaim ne peut pas faire

Le Loto Express est un générateur aléatoire certifié : les tirages sont
indépendants et uniformes. **L'espérance de n'importe quel top-20 — y
compris celui de l'essaim — est exactement 5 hits sur 20.** Hedge,
évolution et diversité maximisent la capacité à *détecter* une structure
si elle existait (biais matériel, défaut de générateur) et garantissent
un regret faible contre la meilleure tête ; ils ne créent aucun avantage
contre un RNG équitable. L'essaim est un instrument de mesure au maximum
de ce que la statistique permet — pas une machine à gagner. Le backtest
de l'app le rappelle en continu, sur données réelles.

## Références

- Freund, Schapire — *A decision-theoretic generalization of on-line
  learning* (Hedge), JCSS 1997.
- Herbster, Warmuth — *Tracking the best expert* (Fixed-Share), Machine
  Learning 1998.
- Cesa-Bianchi, Lugosi — *Prediction, Learning, and Games*, 2006.
- Oja — *Simplified neuron model as a principal component analyzer*, 1982.
- Shafer — *Testing by betting*, JRSS-A 2021.
- Ramdas, Grünwald, Vovk, Shafer — *Game-theoretic statistics and
  safe anytime-valid inference*, Statistical Science 2023.
- Hawkes — *Spectra of some self-exciting and mutually exciting point
  processes*, Biometrika 1971.
