// Balayage exhaustif de l'espace d'états 48 bits (java.util.Random / LCG
// mod 2^48) contre un tirage Loto Express publié.
//
// L'observable est n = ((s >> 17) mod 80) + 1 : il dépend des bits de
// POIDS FORT de l'état, ce qui place ce cas hors du théorème de la
// récurrence basse close (cf. claude/AUDIT-CLAUDE.md §2). C'est donc la
// dernière classe atteignable par calcul.
//
//   cc -O3 -march=native -o sweep48 sweep48.c -lpthread
//   ./sweep48 <lo> <hi> <n1..n20>          (bornes = indices d'état)
//
// Parallélisable trivialement : découper [0, 2^48) en tranches.
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>

#define A 0x5DEECE66DULL
#define C 0xBULL
#define M48 0xFFFFFFFFFFFFULL

int main(int argc, char **argv) {
    if (argc < 23) { fprintf(stderr, "usage: %s lo hi n1..n20\n", argv[0]); return 1; }
    uint64_t lo = strtoull(argv[1], 0, 10), hi = strtoull(argv[2], 0, 10);
    uint8_t in_target[81]; memset(in_target, 0, sizeof in_target);
    for (int i = 0; i < 20; i++) in_target[atoi(argv[3 + i])] = 1;

    uint64_t tested = 0, found = 0;
    int deepest = 0;
    for (uint64_t seed = lo; seed < hi; seed++) {
        uint64_t s = seed;
        uint64_t seen_lo = 0, seen_hi = 0;
        int matched = 0;
        for (int step = 0; step < 64; step++) {
            s = (s * A + C) & M48;
            uint32_t n = (uint32_t)((s >> 17) % 80u) + 1u;
            int b = n - 1;
            uint64_t bit = 1ULL << (b & 63);
            uint64_t *w = (b < 64) ? &seen_lo : &seen_hi;
            if (b >= 64) bit = 1ULL << (b - 64);
            if (*w & bit) continue;          // doublon : rejeté par le tireur
            *w |= bit;
            if (!in_target[n]) break;        // arrêt anticipé
            if (++matched == 20) { found++; printf("HIT %llu\n", (unsigned long long)seed); break; }
        }
        if (matched > deepest) deepest = matched;
        tested++;
    }
    fprintf(stderr, "testes=%llu profondeur_max=%d trouves=%llu\n",
            (unsigned long long)tested, deepest, (unsigned long long)found);
    return 0;
}
