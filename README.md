# Prophet

Oracle iOS pour **Loto Express** (Loterie Romande). Tirage live, grilles CRF-9
(Alpha / Omega / Nexus) pour 5/5 → 10/10, analyse 1–80, séance du jour.

Bundle ID : `com.prophetofnumbers.app`  
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

Un RNG équitable reste imbattable au sens strict. CRF-9 est un ensemble
statistique (Bayes, Hawkes, Weibull, résidu spectral, ACP en ligne).
