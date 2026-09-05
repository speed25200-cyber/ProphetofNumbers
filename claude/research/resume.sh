#!/bin/sh
# Relance un balayage la ou son journal s'est arrete. Le conteneur redemarre sans
# prevenir ; un journal vide par generateur est la seule memoire qui survit.
# usage: sh resume.sh rank128 | keysort
cd "$(dirname "$0")"
case "$1" in
  rank128)
    done_g=$(grep -c "^  [a-z0-9_]* *(lo|hi) *lemire : meilleur" rank128_real.log 2>/dev/null)
    [ "$done_g" -ge 7 ] && { echo "rank128 termine"; exit 0; }
    echo "rank128 : reprise au generateur $done_g"
    ./rank128 rank_colex0.bin 4294967296 "$done_g" >> rank128_real.log 2>&1 ;;
  keysort)
    done_g=$(grep -c "reservoir mulhi  : meilleur" keysort_real.log 2>/dev/null)
    [ "$done_g" -ge 7 ] && { echo "keysort termine"; exit 0; }
    echo "keysort : reprise au generateur $done_g"
    ./keysort draws.bin 0 4294967296 "$done_g" >> keysort_real.log 2>&1 ;;
esac
# langhunt : deux moities independantes, C# (2^31, ~1h30) et Ruby (2^32, ~4h)
case "$1" in
  langhunt-cs)
    grep -q "OrderBy(Next())        : " langhunt_cs.log 2>/dev/null && { echo "langhunt C# termine"; exit 0; }
    ./langhunt2 draws.bin 0 4294967296 cs > langhunt_cs.log 2>&1 ;;
  langhunt-rb)
    grep -q "Ruby init_genrand" langhunt_rb.log 2>/dev/null && { echo "langhunt Ruby termine"; exit 0; }
    ./langhunt2 draws.bin 0 4294967296 rb > langhunt_rb.log 2>&1 ;;
esac
