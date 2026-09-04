#!/bin/sh
# Le balayage 2^32 pour l'architecture par derangement, SANS les deux Mersenne Twister.
#
# Raison : gen64() reamorce le generateur a chaque graine, et un MT reamorce 624 mots puis
# fait un twist — environ 5000 operations par graine contre ~10 pour un LCG. Les deux MT
# representaient a eux seuls plus de 99 % du cout, et le balayage complet n'aurait pas fini
# en plusieurs jours (7 h 57 de CPU consommees sans atteindre la premiere sortie).
#
# Les retirer ne laisse aucun trou : MT est precisement la famille exclue le plus fortement
# par ailleurs — complexite lineaire 35 280, systeme multi-suites 48 000 (qui couvre aussi
# WELL44497), mtbreak, et daily_reseed sur les 358 blocs. C'est du calcul redondant qu'on
# retire, pas une hypothese.
#
# Indices : 0..11 et 13..18  (12 = mt19937, 19 = mt19937_64)
set -e
echo "=== 2^32 exhaustif, tirage 0, generateurs 0..11 (MT exclu, couvert ailleurs) ==="
./rankseed rank_colex0.bin 0 0 4294967296 4 0 12
echo "=== 2^32 exhaustif, tirage 0, generateurs 13..18 ==="
./rankseed rank_colex0.bin 0 0 4294967296 4 13 19
