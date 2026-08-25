# Instructions Claude — archive Loto Express

Tu n’as **pas** accès à l’API LoRo. Ce dossier **est** l’échantillon.

## Lire dans cet ordre

1. `REPORT.md` — synthèse de **tous** les 70 560 tirages publics
2. `STATS.json` — fréquences 1–80, χ², overlap sériel, paires, mois
3. `FREQ.tsv` — table compacte n / hits / z / gap
4. `draws/draws-01.csv` … `draws-08.csv` — brut, un tirage par ligne

## Schéma CSV

```
id,unix_utc,n1..n20,boost,bonus
```

20 numéros distincts parmi 1–80, **déjà triés**. Boost et bonus sont annexes.

| Fichier | ids | n |
|---|---|---|
| draws-01.csv | 1309614–1318613 | 9000 |
| draws-02.csv | 1318614–1327613 | 9000 |
| draws-03.csv | 1327614–1336613 | 9000 |
| draws-04.csv | 1336614–1345613 | 9000 |
| draws-05.csv | 1345614–1354613 | 9000 |
| draws-06.csv | 1354614–1363613 | 9000 |
| draws-07.csv | 1363614–1372613 | 9000 |
| draws-08.csv | 1372614–1380173 | 7560 |

Total : **70 560** tirages, 0 trou d’identifiant. 2025-09-14T06:05:00Z → 2026-08-25T21:00:00Z.

Fenêtre iOS Prophet = 399 tirages (`Prophet/Services/Oracle.swift`). Ici l’historique public complet.

## Modèle nul

SRS 20/80. P(inclusion)=0.25. Overlap indépendant attendu = 5. χ²/df ≈ 1 si uniforme.

## Mission

Diagnostiquer uniformité et mémoire. Quantifier l’effet (χ²/df, z), pas seulement p.
Ne pas inventer de tirages. Un RNG équitable reste imbattable ; CRF-9 est un pari à espérance négative.
