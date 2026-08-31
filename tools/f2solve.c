// f2solve — élimination de Gauss sur F2, pour les très grands systèmes.
//
// POURQUOI CE FICHIER EXISTE
// --------------------------
// Le §106 a montré que les rangs du bonus mettent MT19937 à portée : 3,20
// équations F2 exactes par tirage, 70 560 tirages disponibles, et 19 937 bits
// d'état à déterminer — soit 6 230 tirages suffisants. Il concluait :
//
//     « c'est le COÛT DE CALCUL des formes linéaires qui bloque, pas la
//       donnée. La différence avec le §105 est entière : là, il manquait des
//       tirages ; ici, il manque des heures. »
//
// Les formes se calculent en une minute en Python. C'est l'ÉLIMINATION qui ne
// passe pas : réduire 20 000 lignes de 19 937 bits demande environ 2·10⁸
// XOR de lignes, soit plusieurs jours avec les entiers longs de Python et
// moins d'une minute ici.
//
// FORMAT D'ENTRÉE (binaire, petit-boutiste)
// -----------------------------------------
//     int32  nbits        nombre d'inconnues
//     int32  nrows        nombre d'équations
//     puis, pour chaque équation :
//         uint64[ceil(nbits/64)]  la ligne
//         uint8                   le second membre
//
// SORTIE (texte, sur stdout)
// --------------------------
//     rang=<r> incoherent=<0|1> lignes=<n> sec=<t>
//     puis, si cohérent et de rang plein, la solution en hexadécimal.
//
//   cc -O3 -march=native -o f2solve f2solve.c

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>

int main(int argc, char **argv) {
    if (argc < 2) { fprintf(stderr, "usage: %s systeme.bin\n", argv[0]); return 2; }
    FILE *f = fopen(argv[1], "rb");
    if (!f) { perror("fopen"); return 2; }

    int32_t nbits, nrows;
    if (fread(&nbits, 4, 1, f) != 1 || fread(&nrows, 4, 1, f) != 1) return 2;
    size_t W = (size_t)((nbits + 63) / 64);

    // piv[p] : la ligne dont le bit de tête est p, ou NULL. rhs[p] : son second membre.
    uint64_t **piv = calloc((size_t)nbits, sizeof(uint64_t *));
    uint8_t *rhs = calloc((size_t)nbits, 1);
    uint64_t *row = malloc(W * 8);
    if (!piv || !rhs || !row) { fprintf(stderr, "memoire\n"); return 2; }

    clock_t t0 = clock();
    long rang = 0, incoherent = 0, lues = 0;

    for (int32_t r = 0; r < nrows; r++) {
        uint8_t b;
        if (fread(row, 8, W, f) != W) break;
        if (fread(&b, 1, 1, f) != 1) break;
        lues++;

        // réduction contre les pivots déjà installés
        for (;;) {
            // bit de tête
            long tete = -1;
            for (size_t w = W; w-- > 0;) {
                if (row[w]) { tete = (long)(w * 64) + 63 - __builtin_clzll(row[w]); break; }
            }
            if (tete < 0) {                       // ligne nulle
                if (b) incoherent = 1;            // 0 = 1 : système impossible
                break;
            }
            if (!piv[tete]) {                     // nouveau pivot
                piv[tete] = malloc(W * 8);
                memcpy(piv[tete], row, W * 8);
                rhs[tete] = b;
                rang++;
                break;
            }
            uint64_t *p = piv[tete];
            for (size_t w = 0; w < W; w++) row[w] ^= p[w];
            b ^= rhs[tete];
        }
        if (incoherent) break;                    // inutile de continuer
    }

    double sec = (double)(clock() - t0) / CLOCKS_PER_SEC;
    printf("rang=%ld incoherent=%ld lignes=%ld sec=%.2f\n", rang, incoherent, lues, sec);

    if (!incoherent) {
        // Substitution arrière. Les pivots sont en forme échelonnée : la ligne
        // de tête p n'a pas de bit au-dessus de p, donc on résout p croissant.
        //
        // ON ÉMET UNE SOLUTION MÊME À RANG INCOMPLET, en fixant les variables
        // libres à zéro. Ce n'est pas une commodité : plusieurs générateurs
        // logent moins de bits utiles que leur état nominal — taus88 en met 88
        // dans 96, LFSR113 en met 113 dans 128 — et les bits morts ne peuvent
        // être déterminés par AUCUNE observation, puisqu'ils n'influencent
        // aucune sortie. Exiger le rang plein reviendrait à déclarer l'attaque
        // en échec sur des familles qu'elle résout parfaitement.
        uint64_t *sol = calloc(W, 8);
        for (long p = 0; p < nbits; p++) {
            uint64_t *pr = piv[p];
            if (!pr) continue;                // variable libre : on la met à 0
            uint64_t acc = 0;
            for (size_t w = 0; w < W; w++) acc ^= pr[w] & sol[w];
            int par = __builtin_parityll(acc) ^ rhs[p];
            if (par) sol[p / 64] |= 1ULL << (p % 64);
        }
        printf("solution=");
        for (size_t w = 0; w < W; w++) printf("%016llx", (unsigned long long)sol[w]);
        printf("\n");
    }
    return 0;
}
