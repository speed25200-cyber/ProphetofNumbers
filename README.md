# Prophet

Oracle iOS pour **Loto Express** (Loterie Romande). Tirage live avec anneau de
compte à rebours, grilles Alpha / Omega / Nexus pour 5/5 → 10/10 avec bilan
réel des grilles jouées, analyse 1–80, backtest walk-forward (« Vérité
terrain »), séance du jour.

Le moteur est un **essaim de 26 têtes** en compétition (Hedge à part fixe +
évolution par mutation) — architecture détaillée dans
[`docs/ESSAIM.md`](docs/ESSAIM.md).

Design : obsidienne + or champagne, fond aurora animé, verre dépoli,
haptiques, transitions spring. L'oracle est calculé hors du main thread.

## Le laboratoire

[`lab/`](lab/) est la moitié du dépôt qu'on ne voit pas à l'écran, et c'est
elle qui décide de ce que l'app a le droit d'afficher. Elle teste
l'hypothèse d'uniformité sur 70 560 tirages publics, sous un protocole en
trois règles — null simulé et jamais tabulé, pré-enregistrement, correction
de multiplicité sur le registre entier — avec puissance mesurée et témoins
positifs obligatoires à chaque expérience.

| | |
|---|---|
| [`lab/RAPPORT.md`](lab/RAPPORT.md) | le dossier complet, une section par voie explorée |
| [`lab/README.md`](lab/README.md) | le protocole et l'API |
| [`lab/THEORIE.md`](lab/THEORIE.md) | les théorèmes, dérivés puis vérifiés |
| `lab/ledger.jsonl` | le registre de tous les tests dépensés |

**Zéro significatif** sur l'ensemble du registre. Ce n'est pas un échec :
c'est la mesure qui autorise l'app à ne rien promettre qu'elle ne puisse
tenir. Les seuls leviers réels que le dossier ait trouvés portent sur le
*moment* de jouer, la *taille* de la mise et la *géométrie* du paquet —
jamais sur le choix des numéros, que l'invariance hypergéométrique ferme par
un théorème.

Bundle ID : `io.ProphetOfNumbers.Prophet`  
Équipe : `BTMRPS8F79`

## Codemagic

Le fichier [`codemagic.yaml`](codemagic.yaml) définit trois flux, calqués sur Limbator :

| Flux | Quand | Résultat |
|---|---|---|
| **validate** | push / PR sur `main` | compile + tests simulateur |
| **testflight** | manuel (ou après validate) | IPA → TestFlight |
| **release** | étiquette `v*` | App Store |

### Première fois

1. [Codemagic → Applications](https://codemagic.io/apps) → **Add application**
2. Choisir le dépôt GitHub `speed25200-cyber/ProphetofNumbers`
3. Codemagic détecte `codemagic.yaml`
4. Team integrations : réutiliser **PetMind ASC API** (même clé que Limbator)
5. Lancer **validate**, puis **testflight**

Un RNG équitable reste imbattable au sens strict. L'essaim (Bayes, EWMA,
Hawkes, écarts, spectre, Markov, graphe de paires, ACP, contra, pression)
mesure honnêtement son propre écart au hasard — il ne le crée pas.
