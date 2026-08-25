# tools — balayage d'espace d'états

Ferment la dernière classe de générateurs atteignable par le calcul :
les états de 48 bits (`java.util.Random`, LCG modulo 2⁴⁸). Contexte et
justification dans [`../claude/AUDIT-CLAUDE.md`](../claude/AUDIT-CLAUDE.md).

Un état n'est retenu que s'il reproduit **les 20 numéros** du tirage
cible. Confirmer ensuite sur le tirage suivant élimine tout faux positif
résiduel (probabilité d'un faux positif sur 2⁴⁸ : ≈ 8 × 10⁻⁷).

## CPU — `sweep48.c`

```sh
cc -O3 -march=native -o sweep48 sweep48.c
./sweep48 0 1099511627776  5 6 10 11 13 22 26 28 32 35 37 38 39 41 50 55 66 68 78 79
```

Mesuré : **156 M états/s par cœur**. Tranche `[lo, hi)` en argument —
parallélisation triviale, aucune communication entre workers.

| Configuration | 2⁴⁸ intégral |
|---|---|
| 1 cœur | 20,9 jours |
| 64 cœurs | ~8 heures |

## GPU — `sweep48.cu`

```sh
nvcc -O3 -arch=sm_80 -o sweep48cu sweep48.cu     # sm_80 = A100, sm_89 = L40S/4090
./sweep48cu 0 281474976710656  5 6 10 11 13 22 26 28 32 35 37 38 39 41 50 55 66 68 78 79
```

Logique identique à la version CPU (validée à 156 M états/s/cœur), portée
en noyau à boucle à pas de grille. Le programme affiche son débit réel et
extrapole la durée d'une couverture complète.

Estimation A100 80 Go : **1 h 30 à 3 h** pour les 2⁴⁸ complets. La VRAM
est sans objet — le noyau tient en registres, aucun accès mémoire globale
dans la boucle interne ; il tournerait à l'identique sur une carte 8 Go.
Le facteur limitant est le débit entier et la divergence de warp.

> Le noyau CUDA n'a pas pu être compilé ni mesuré dans l'environnement de
> développement (aucun GPU disponible). Sa logique est celle de la version
> CPU, testée. Vérifier le débit affiché sur une petite tranche avant de
> lancer une couverture complète.

## Découper le travail

```sh
# 8 tranches de 2^45 sur 8 GPU
for i in $(seq 0 7); do
  LO=$(( i * 35184372088832 )); HI=$(( (i+1) * 35184372088832 ))
  CUDA_VISIBLE_DEVICES=$i ./sweep48cu $LO $HI <20 numéros> &
done
```

Toute sortie `HIT <état>` est à vérifier immédiatement sur le tirage
suivant — et, si elle se confirme, à signaler à l'exploitant avant toute
autre chose.
