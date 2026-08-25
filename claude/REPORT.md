# Loto Express — dossier d’analyse PRNG (archive complète)

Tu n’as **pas accès** à l’API LoRo (`jeux.loro.ch`). Ce fichier + `STATS.json` **sont** l’échantillon : 70560 tirages, sans trou d’id, 2025-09-14T06:05:00Z → 2026-08-25T21:00:00Z (UTC). Jeu : 20 boules distinctes parmi 1–80, toutes les ~5 min. Les 20 numéros sont **publiés déjà triés** : l’ordre interne du générateur n’est pas observé. Boost (1/2/3) et bonus (une des 20 boules) sont des champs annexes.

## Schéma des tirages bruts (si fournis)

```
[id, unixUtc, [20 numéros triés], boost|null, bonus|null]
```

Exemple dernier tirage : `[1380173, 1787691600, [8, 12, 21, 23, 27, 30, 33, 42, 43, 46, 50, 52, 59, 60, 62, 65, 70, 71, 73, 78], 1, 59]`

## Modèle nul (RNG équitable)

- Chaque tirage ~ SRS 20/80 (hypergéométrique).
- P(inclusion d’un numéro) = 20/80 = 0.25.
- Hits attendus / numéro = 17640.0.
- Overlap attendu entre deux tirages indépendants = 20×20/80 = **5**.
- Écart inter-apparitions attendu = 4 tirages.
- Somme attendue = 810. Impairs attendus = 10.

Un RNG correct **reste imbattable** au sens strict. Un p-value bas à N=70560 peut venir d’un biais microscopique. Lire **χ²/df** et **z sériel**, pas seulement p.

## Résultats globaux (N = 70560)

| Métrique | Valeur | Attendu / note |
|---|---|---|
| χ² | 53.60 | df = 79 |
| χ² / df | 0.6784 | 1.00 si uniforme |
| p (χ²) | 0.9873 | N grand ⇒ p trop sensible |
| Overlap lag-1 | 5.0019 | 5.000 |
| z sériel lag-1 | 0.262 | ~0 si sans mémoire |
| Entropie freq. | 6.3219 bit | max 6.3219 |
| Impairs / tirage | 9.997 | 10 |
| Somme / tirage | 810.44 ± 90.29 | 810 |
| Sets identiques répétés | 0 | 70560 ensembles uniques / 70560 |

**Verdict mécanique :** `uniforme`  
Règle : uniforme si χ²/df ≤ 1.12 et |z_sériel| ≤ 2 ; écart léger au-delà ; structure si χ²/df > 1.35 ou |z| > 3.

Split half : 1ʳᵉ moitié χ²/df = 0.7519 (n=35280) · 2ᵉ = 0.6173 (n=35280).

## Overlap sériel

| lag | overlap moyen |
|---|---|
| 1 | 5.0019 |
| 2 | 5.0000 |
| 3 | 4.9976 |
| 4 | 4.9952 |
| 5 | 4.9974 |
| 8 | 4.9928 |
| 12 | 4.9984 |
| 20 | 4.9957 |

Histogramme |A∩A₊₁| (0..20) : `[79, 813, 3669, 8693, 14343, 16486, 13351, 7990, 3709, 1135, 238, 42, 10, 1, 0, 0, 0, 0, 0, 0, 0]`

## Numéros les plus / moins tirés

| n | hits | z | gap moyen |
|---|---|---|---|
| 76 | 17953 | +2.72 | 3.93 |
| 42 | 17914 | +2.38 | 3.94 |
| 04 | 17898 | +2.24 | 3.94 |
| 62 | 17896 | +2.23 | 3.94 |
| 26 | 17862 | +1.93 | 3.95 |
| 65 | 17837 | +1.71 | 3.96 |
| 22 | 17833 | +1.68 | 3.96 |
| 28 | 17753 | +0.98 | 3.97 |
| … | | | |
| 50 | 17427 | -1.85 | 4.05 |
| 10 | 17472 | -1.46 | 4.04 |
| 23 | 17473 | -1.45 | 4.04 |
| 59 | 17488 | -1.32 | 4.03 |
| 27 | 17488 | -1.32 | 4.03 |
| 19 | 17491 | -1.30 | 4.03 |
| 68 | 17494 | -1.27 | 4.03 |
| 74 | 17510 | -1.13 | 4.03 |

Table complète des 80 numéros : `STATS.json` → `numbers`.

## Paires |z| ≥ 2.5 (top)

| a | b | count | z |
|---|---|---|---|
| 10 | 38 | 4010 | -3.57 |
| 21 | 59 | 4028 | -3.29 |
| 23 | 47 | 4044 | -3.05 |
| 04 | 26 | 4439 | +3.02 |
| 22 | 41 | 4439 | +3.02 |
| 65 | 71 | 4431 | +2.89 |
| 06 | 40 | 4059 | -2.82 |
| 09 | 62 | 4424 | +2.79 |
| 35 | 65 | 4422 | +2.75 |
| 32 | 60 | 4065 | -2.73 |
| 11 | 44 | 4418 | +2.69 |
| 31 | 74 | 4068 | -2.68 |
| 42 | 76 | 4416 | +2.66 |
| 52 | 62 | 4416 | +2.66 |
| 41 | 73 | 4414 | +2.63 |

## Mois (Zurich)

| mois | tirages | χ²/df | chaud | froid |
|---|---|---|---|---|
| 2025-09 | 3444 | 0.804 | 3 | 27 |
| 2025-10 | 6324 | 0.752 | 2 | 25 |
| 2025-11 | 6120 | 0.666 | 55 | 69 |
| 2025-12 | 6324 | 0.530 | 37 | 74 |
| 2026-01 | 6324 | 0.681 | 37 | 36 |
| 2026-02 | 5712 | 0.620 | 76 | 30 |
| 2026-03 | 6324 | 0.913 | 10 | 56 |
| 2026-04 | 6120 | 0.849 | 62 | 1 |
| 2026-05 | 6324 | 0.937 | 26 | 68 |
| 2026-06 | 6120 | 0.774 | 14 | 50 |
| 2026-07 | 6324 | 0.651 | 21 | 10 |
| 2026-08 | 5100 | 0.791 | 69 | 43 |

## Boost

`{1: 36122, 2: 16791, 3: 10626, 4: 3525, 5: 1739, 10: 1757}`

## Ce que tu dois faire

1. Interpréter ces stats comme un test d’**uniformité** et d’**indépendance** d’un keno 20/80, pas comme une preuve de prédiction.
2. Dire clairement si un écart est **pratique** (exploitable) ou seulement **détectable** à N ≈ 7×10⁴.
3. Si on te demande des grilles (Prophet CRF-9 / Hawkes / Weibull) : rappeler qu’un RNG équitable ne se bat pas ; toute grille reste un pari à espérance négative.
4. Tu peux demander le JSON brut (`lotoexpress-draws.json`) pour des tests supplémentaires (KS sur les sommes, FFT d’une série binaire, runs). Ne pas inventer de tirages.

## Échantillons

Premier : id 1309614 2025-09-14T06:05:00Z → [3, 4, 7, 11, 16, 23, 27, 33, 35, 39, 53, 55, 62, 64, 67, 70, 71, 73, 77, 80]  
Dernier : id 1380173 2026-08-25T21:00:00Z → [8, 12, 21, 23, 27, 30, 33, 42, 43, 46, 50, 52, 59, 60, 62, 65, 70, 71, 73, 78]
