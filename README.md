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
