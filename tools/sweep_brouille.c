// sweep_brouille — balayage de graines pour les familles que dim L = 0 protège.
//
// POURQUOI CE FICHIER EXISTE
// --------------------------
// Le §119 mesure la frontière : xoshiro**, xoshiro++, PCG32 et splitmix64 ont
// un sous-espace de linéarité de dimension EXACTEMENT ZÉRO. Aucune élimination
// de Gauss ne mordra jamais sur eux — c'est une dimension calculée, pas une
// conjecture.
//
// Mais cela ne dit rien de leur GRAINE. Un état de 256 bits est hors de portée ;
// une graine de 32 bits ne l'est pas. Et une plateforme qui doit pouvoir
// REJOUER ses tirages pour l'audit amorce naturellement sur le numéro de
// tirage ou sur l'horodatage.
//
//   L'ÉTAT EST INATTEIGNABLE, LA GRAINE NE L'EST PAS. C'est la dernière voie
//   par laquelle un résultat POSITIF peut encore sortir de ce dossier.
//
// CE QU'IL FAIT
// -------------
// Pour une famille, un échantillonneur, une forme de graine et une plage
// [lo, hi), il engendre le tirage et le compare à la cible TRIÉE. Le filtre est
// une appartenance à l'ensemble : un numéro sur quatre survit, donc le coût
// réel est d'environ 1,33 pas de générateur par graine.
//
//   probabilité de faux positif : 1/C(80,20) = 2,8e-19 par graine.
//
// AUTOTEST
// --------
// `--selftest` plante une graine connue pour chaque combinaison et exige de la
// retrouver. Une attaque qui ne retrouve pas son propre témoin ne prouve rien
// quand elle ne trouve rien.
//
//   cc -O3 -march=native -o sweep_brouille tools/sweep_brouille.c

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>

#define POOL 80
#define DRAWN 20

typedef struct { uint64_t a, b, c, d; } st_t;

static inline uint64_t rotl64(uint64_t x, int k) { return (x << k) | (x >> (64 - k)); }
static inline uint32_t rotr32(uint32_t x, int k) { return k ? ((x >> k) | (x << (32 - k))) : x; }

// ---- les familles, et leur mot de sortie ramené sur 64 bits utiles ----
enum { F_XOSHIRO_SS, F_XOSHIRO_PP, F_XOROSHIRO_SS, F_PCG32, F_SPLITMIX,
       F_XS128P, F_XOSHIRO_BRUT, NFAM };
static const char *FAM_NOM[NFAM] = {
    "xoshiro256**", "xoshiro256++", "xoroshiro128**", "PCG32",
    "splitmix64", "xorshift128+", "xoshiro256 (brut)" };
// largeur utile de la sortie, en bits
static const int FAM_W[NFAM] = { 64, 64, 64, 32, 64, 64, 64 };

static void gen_init(int f, uint64_t seed, st_t *s) {
    // amorçage par splitmix64, la convention universelle pour ces familles
    uint64_t z = seed;
    uint64_t o[4];
    for (int i = 0; i < 4; i++) {
        z += 0x9E3779B97F4A7C15ULL;
        uint64_t y = z;
        y = (y ^ (y >> 30)) * 0xBF58476D1CE4E5B9ULL;
        y = (y ^ (y >> 27)) * 0x94D049BB133111EBULL;
        o[i] = y ^ (y >> 31);
    }
    s->a = o[0]; s->b = o[1]; s->c = o[2]; s->d = o[3];
    if (f == F_PCG32 || f == F_SPLITMIX) { s->a = seed; }
    if ((f == F_XOSHIRO_SS || f == F_XOSHIRO_PP || f == F_XOSHIRO_BRUT ||
         f == F_XOROSHIRO_SS || f == F_XS128P) &&
        !(s->a | s->b | s->c | s->d)) s->a = 1;
}

static inline uint64_t gen_next(int f, st_t *s) {
    switch (f) {
    case F_XOSHIRO_SS: case F_XOSHIRO_PP: case F_XOSHIRO_BRUT: {
        uint64_t res;
        if (f == F_XOSHIRO_SS)      res = rotl64(s->b * 5, 7) * 9;
        else if (f == F_XOSHIRO_PP) res = rotl64(s->a + s->d, 23) + s->a;
        else                        res = s->a;
        uint64_t t = s->b << 17;
        s->c ^= s->a; s->d ^= s->b; s->b ^= s->c; s->a ^= s->d; s->c ^= t;
        s->d = rotl64(s->d, 45);
        return res;
    }
    case F_XOROSHIRO_SS: {
        uint64_t s0 = s->a, s1 = s->b;
        uint64_t res = rotl64(s0 * 5, 7) * 9;
        s1 ^= s0;
        s->a = rotl64(s0, 24) ^ s1 ^ (s1 << 16);
        s->b = rotl64(s1, 37);
        return res;
    }
    case F_XS128P: {
        uint64_t x = s->a, y = s->b;
        uint64_t res = x + y;
        s->a = y;
        x ^= x << 23;
        s->b = x ^ y ^ (x >> 18) ^ (y >> 5);
        return res;
    }
    case F_PCG32: {
        uint64_t old = s->a;
        s->a = old * 6364136223846793005ULL + 1442695040888963407ULL;
        uint32_t x = (uint32_t)(((old >> 18) ^ old) >> 27);
        int r = (int)(old >> 59);
        return (uint64_t)rotr32(x, r);
    }
    default: {                                   // splitmix64
        s->a += 0x9E3779B97F4A7C15ULL;
        uint64_t z = s->a;
        z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
        z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
        return z ^ (z >> 31);
    }
    }
}

// ---- les échantillonneurs ----
enum { S_FY_TRONC, S_FY_MODULO, S_REJ_TRONC, S_REJ_MODULO, NSAMP };
static const char *SAMP_NOM[NSAMP] = {
    "Fisher-Yates tronqué", "Fisher-Yates modulo",
    "rejet tronqué", "rejet modulo" };

// vu[n] : le numéro n appartient-il à la cible ? Filtre d'appartenance.
static inline int tire(int f, int samp, st_t *s, const uint8_t *vu,
                       uint8_t *sortie) {
    int W = FAM_W[f];
    uint8_t arr[POOL];
    if (samp == S_FY_TRONC || samp == S_FY_MODULO) {
        for (int i = 0; i < POOL; i++) arr[i] = (uint8_t)(i + 1);
        for (int k = 0; k < DRAWN; k++) {
            uint64_t w = gen_next(f, s);
            int j;
            if (samp == S_FY_TRONC) {
                if (W == 64) j = k + (int)(((__uint128_t)w * (POOL - k)) >> 64);
                else         j = k + (int)(((uint64_t)(uint32_t)w * (POOL - k)) >> 32);
            } else {
                j = k + (int)(w % (uint64_t)(POOL - k));
            }
            uint8_t t = arr[k]; arr[k] = arr[j]; arr[j] = t;
            if (!vu[arr[k]]) return 0;           // abandon au premier écart
            sortie[k] = arr[k];
        }
        return 1;
    }
    uint8_t pris[POOL + 1];
    memset(pris, 0, sizeof pris);
    int n = 0, mots = 0;
    while (n < DRAWN) {
        if (++mots > 400) return 0;              // état dégénéré
        uint64_t w = gen_next(f, s);
        int v;
        if (samp == S_REJ_TRONC) {
            if (W == 64) v = 1 + (int)(((__uint128_t)w * POOL) >> 64);
            else         v = 1 + (int)(((uint64_t)(uint32_t)w * POOL) >> 32);
        } else {
            v = 1 + (int)(w % POOL);
        }
        if (pris[v]) continue;
        if (!vu[v]) return 0;
        pris[v] = 1;
        sortie[n++] = (uint8_t)v;
    }
    return 1;
}

// formes de graine : 0 = id+B, 1 = ts+B, 2 = B seul
static inline uint64_t graine_de(int forme, uint64_t base, uint64_t B) {
    switch (forme) {
    case 0: return base + B;
    case 1: return base + B;
    default: return B;
    }
}

int main(int argc, char **argv) {
    if (argc >= 2 && !strcmp(argv[1], "--selftest")) {
        int ok = 0, tot = 0;
        for (int f = 0; f < NFAM; f++)
            for (int sa = 0; sa < NSAMP; sa++) {
                uint64_t vraie = 123456789ULL + f * 7919 + sa * 104729;
                st_t s; gen_init(f, vraie, &s);
                uint8_t tousvus[POOL + 1]; memset(tousvus, 1, sizeof tousvus);
                uint8_t cible[DRAWN];
                if (!tire(f, sa, &s, tousvus, cible)) { tot++; continue; }
                uint8_t vu[POOL + 1]; memset(vu, 0, sizeof vu);
                for (int i = 0; i < DRAWN; i++) vu[cible[i]] = 1;
                int trouve = 0;
                for (uint64_t g = vraie - 500; g <= vraie + 500; g++) {
                    st_t s2; gen_init(f, g, &s2);
                    uint8_t out[DRAWN];
                    if (tire(f, sa, &s2, vu, out)) { trouve = 1; break; }
                }
                tot++; ok += trouve;
                printf("  %-18s %-22s %s\n", FAM_NOM[f], SAMP_NOM[sa],
                       trouve ? "OUI" : "NON");
            }
        printf("autotest : %d/%d\n", ok, tot);
        return ok == tot ? 0 : 1;
    }
    if (argc < 7) {
        fprintf(stderr, "usage: %s <fam> <samp> <forme> <base> <lo> <hi> <n1..n20>\n",
                argv[0]);
        fprintf(stderr, "       %s --selftest\n", argv[0]);
        return 2;
    }
    int f = atoi(argv[1]), sa = atoi(argv[2]), forme = atoi(argv[3]);
    uint64_t base = strtoull(argv[4], 0, 10);
    uint64_t lo = strtoull(argv[5], 0, 10), hi = strtoull(argv[6], 0, 10);
    uint8_t vu[POOL + 1]; memset(vu, 0, sizeof vu);
    for (int i = 0; i < DRAWN; i++) vu[atoi(argv[7 + i])] = 1;

    clock_t t0 = clock();
    long trouves = 0;
    uint8_t out[DRAWN];
    for (uint64_t B = lo; B < hi; B++) {
        st_t s; gen_init(f, graine_de(forme, base, B), &s);
        if (tire(f, sa, &s, vu, out)) {
            printf("TROUVE graine=%llu B=%llu\n",
                   (unsigned long long)graine_de(forme, base, B),
                   (unsigned long long)B);
            trouves++;
        }
    }
    printf("fam=%s samp=%s forme=%d testees=%llu trouves=%ld sec=%.1f\n",
           FAM_NOM[f], SAMP_NOM[sa], forme, (unsigned long long)(hi - lo),
           trouves, (double)(clock() - t0) / CLOCKS_PER_SEC);
    return 0;
}
