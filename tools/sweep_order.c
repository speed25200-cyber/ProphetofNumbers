// sweep_order — balayage de graines contre un tirage ORDONNÉ.
//
// La région que ce programme couvre, et que rien d'autre ne couvrait
// ---------------------------------------------------------------------
// Toutes les attaques du labo (h4 à h20) supposent un générateur qui TOURNE
// EN CONTINU : l'état à la fin d'un tirage est celui du début du suivant.
// C'est ce qui rend possible de résoudre (a, c) sur plusieurs tirages.
//
// Une implémentation qui RÉ-AMORCE le générateur à chaque tirage les défait
// toutes d'un coup — et c'est le cas le plus courant en pratique, celui
// qu'on écrit quand on tape `new Random(seed)` au début de la fonction de
// tirage. Contre lui, la seule attaque est le balayage de l'espace des
// graines.
//
// `sweep48.c` faisait cela pour UNE famille (java.util.Random), UN
// échantillonneur (modulo avec rejet), et contre l'ENSEMBLE des vingt
// numéros. Ce programme-ci change les trois points :
//
//   * il teste huit familles de générateurs et quatre échantillonneurs,
//     soit trente-deux combinaisons ;
//   * il travaille sur l'ORDRE de sortie, pas sur l'ensemble. Le filtre
//     passe de 1/4 à 1/80 par pas : le balayage est plus rapide ET la
//     probabilité de faux positif tombe de C(80,20)⁻¹ ≈ 3·10⁻¹⁹ à
//     (80!/60!)⁻¹ ≈ 1·10⁻³⁷ ;
//   * il vérifie chaque touche sur un second tirage ordonné avant de la
//     déclarer.
//
// Autotest
// --------
// `--selftest` fabrique, pour chacune des trente-deux combinaisons, un
// tirage à partir d'une graine connue, puis balaie et exige de la retrouver.
// Une attaque qui ne retrouve pas son propre témoin ne prouve rien quand
// elle ne trouve rien.
//
//   cc -O3 -march=native -pthread -o sweep_order sweep_order.c
//   ./sweep_order --selftest
//   ./sweep_order <lo> <hi> <o1..o20> [-- <c1..c20>]
//
// Les vingt numéros sont donnés DANS L'ORDRE DE SORTIE. Après `--`, un
// second tirage ordonné sert de confirmation.

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <pthread.h>

#define POOL 80
#define DRAWN 20
#define NGEN 8
#define NSAMP 4

// ---------------------------------------------------------------------------
// Les huit familles de générateurs. Chacune expose un état opaque de 64 bits
// et rend une sortie de 32 bits par appel — c'est la forme sous laquelle
// toutes les bibliothèques standard livrent leur flux, et elle uniformise
// les échantillonneurs.
// ---------------------------------------------------------------------------

#define JAVA_A 0x5DEECE66DULL
#define JAVA_C 0xBULL
#define M48    0xFFFFFFFFFFFFULL

typedef struct { uint64_t a, b; } gstate;

static inline void gen_init(int g, uint64_t seed, gstate *st) {
    st->b = 0;
    switch (g) {
    case 0: st->a = (seed ^ JAVA_A) & M48; break;          // java.util.Random
    case 1: st->a = seed & 0xFFFFFFFFULL; break;            // LCG 32 « MSVC »
    case 2: st->a = seed & 0x7FFFFFFFULL; break;            // LCG 32 « glibc »
    case 3: st->a = (seed & 0xFFFFFFFFULL) ? (seed & 0xFFFFFFFFULL) : 1; break; // xorshift32
    case 4: st->a = seed ? seed : 1; break;                 // xorshift64*
    case 5: st->a = seed; break;                            // splitmix64
    case 6: st->a = seed; st->b = 1442695040888963407ULL; break; // pcg32
    default: st->a = seed; break;                           // LCG 64 MMIX
    }
}

static inline uint32_t gen_next(int g, gstate *st) {
    uint64_t x;
    switch (g) {
    case 0:
        st->a = (st->a * JAVA_A + JAVA_C) & M48;
        return (uint32_t)(st->a >> 16);                     // next(32)
    case 1:
        st->a = (st->a * 214013ULL + 2531011ULL) & 0xFFFFFFFFULL;
        return (uint32_t)(st->a >> 16) & 0x7FFFu;           // 15 bits utiles
    case 2:
        st->a = (st->a * 1103515245ULL + 12345ULL) & 0x7FFFFFFFULL;
        return (uint32_t)st->a;
    case 3:
        x = st->a;
        x ^= (x << 13) & 0xFFFFFFFFULL;
        x ^= x >> 17;
        x ^= (x << 5) & 0xFFFFFFFFULL;
        st->a = x & 0xFFFFFFFFULL;
        return (uint32_t)st->a;
    case 4:
        x = st->a;
        x ^= x >> 12; x ^= x << 25; x ^= x >> 27;
        st->a = x;
        return (uint32_t)((x * 2685821657736338717ULL) >> 32);
    case 5:
        st->a += 0x9E3779B97F4A7C15ULL;
        x = st->a;
        x = (x ^ (x >> 30)) * 0xBF58476D1CE4E5B9ULL;
        x = (x ^ (x >> 27)) * 0x94D049BB133111EBULL;
        return (uint32_t)((x ^ (x >> 31)) >> 32);
    case 6: {
        uint64_t old = st->a;
        st->a = old * 6364136223846793005ULL + (st->b | 1ULL);
        uint32_t xs = (uint32_t)(((old >> 18) ^ old) >> 27);
        uint32_t rot = (uint32_t)(old >> 59);
        return (xs >> rot) | (xs << ((-rot) & 31));
    }
    default:
        st->a = st->a * 6364136223846793005ULL + 1442695040888963407ULL;
        return (uint32_t)(st->a >> 32);
    }
}

// Combien de bits utiles la sortie porte-t-elle ? Le LCG « MSVC » n'en rend
// que quinze, ce qui change l'échelle du multiply-shift.
static inline uint32_t gen_bound(int g) { return (g == 1) ? 15u : 32u; }

// ---------------------------------------------------------------------------
// Les quatre échantillonneurs. Chacun produit l'ordre de sortie et s'arrête
// dès qu'un numéro s'écarte de la cible.
// ---------------------------------------------------------------------------

static inline int match_order(int g, int s, uint64_t seed, const uint8_t *target) {
    gstate st;
    gen_init(g, seed, &st);
    uint32_t bits = gen_bound(g);
    if (s == 0 || s == 1) {                                 // rejet des doublons
        uint64_t lo = 0, hi = 0;
        int got = 0, steps = 0;
        while (got < DRAWN && steps < 400) {
            steps++;
            uint32_t u = gen_next(g, &st);
            uint32_t n = (s == 0) ? (u % POOL)
                                  : (uint32_t)(((uint64_t)u * POOL) >> bits);
            int b = (int)n;
            uint64_t bit = (b < 64) ? (1ULL << b) : (1ULL << (b - 64));
            uint64_t *w = (b < 64) ? &lo : &hi;
            if (*w & bit) continue;
            *w |= bit;
            if (n + 1 != target[got]) return 0;
            got++;
        }
        return got == DRAWN;
    }
    // Fisher-Yates partiel : arr[i] <-> arr[j], j = i + p.
    uint8_t arr[POOL];
    for (int i = 0; i < POOL; i++) arr[i] = (uint8_t)(i + 1);
    for (int i = 0; i < DRAWN; i++) {
        uint32_t m = (uint32_t)(POOL - i);
        uint32_t u = gen_next(g, &st);
        uint32_t p = (s == 2) ? (u % m) : (uint32_t)(((uint64_t)u * m) >> bits);
        int j = i + (int)p;
        uint8_t t = arr[i]; arr[i] = arr[j]; arr[j] = t;
        if (arr[i] != target[i]) return 0;
    }
    return 1;
}

// ---------------------------------------------------------------------------
// Le balayage, réparti sur les cœurs
// ---------------------------------------------------------------------------

typedef struct {
    uint64_t lo, hi;
    const uint8_t *target;
    const uint8_t *confirm;      // NULL si aucun second tirage
    int gen, samp;
    uint64_t hits;
    uint64_t hit_seed;
} job;

static void *worker(void *arg) {
    job *j = (job *)arg;
    j->hits = 0;
    for (uint64_t seed = j->lo; seed < j->hi; seed++) {
        if (match_order(j->gen, j->samp, seed, j->target)) {
            if (j->confirm && !match_order(j->gen, j->samp, seed, j->confirm)) continue;
            if (j->hits == 0) j->hit_seed = seed;
            j->hits++;
        }
    }
    return NULL;
}

static const char *GEN_NAME[NGEN] = {
    "java.util.Random", "LCG32 MSVC", "LCG32 glibc", "xorshift32",
    "xorshift64*", "splitmix64", "pcg32", "LCG64 MMIX"
};
static const char *SAMP_NAME[NSAMP] = {
    "modulo + rejet", "multiply-shift + rejet", "Fisher-Yates modulo",
    "Fisher-Yates multiply-shift"
};

static uint64_t sweep(int g, int s, uint64_t lo, uint64_t hi,
                      const uint8_t *target, const uint8_t *confirm,
                      int nthreads, uint64_t *first) {
    pthread_t th[64];
    job jobs[64];
    if (nthreads > 64) nthreads = 64;
    uint64_t span = (hi - lo) / (uint64_t)nthreads + 1;
    for (int i = 0; i < nthreads; i++) {
        jobs[i].lo = lo + span * (uint64_t)i;
        jobs[i].hi = jobs[i].lo + span; if (jobs[i].hi > hi) jobs[i].hi = hi;
        if (jobs[i].lo > hi) jobs[i].lo = jobs[i].hi = hi;
        jobs[i].target = target; jobs[i].confirm = confirm;
        jobs[i].gen = g; jobs[i].samp = s; jobs[i].hits = 0; jobs[i].hit_seed = 0;
        pthread_create(&th[i], NULL, worker, &jobs[i]);
    }
    uint64_t total = 0;
    for (int i = 0; i < nthreads; i++) {
        pthread_join(th[i], NULL);
        if (jobs[i].hits && total == 0 && first) *first = jobs[i].hit_seed;
        total += jobs[i].hits;
    }
    return total;
}

// Fabrique l'ordre produit par (g, s) depuis une graine — pour l'autotest.
static void produce(int g, int s, uint64_t seed, uint8_t *out) {
    gstate st;
    gen_init(g, seed, &st);
    uint32_t bits = gen_bound(g);
    if (s == 0 || s == 1) {
        uint64_t lo = 0, hi = 0; int got = 0, steps = 0;
        while (got < DRAWN && steps < 4000) {
            steps++;
            uint32_t u = gen_next(g, &st);
            uint32_t n = (s == 0) ? (u % POOL)
                                  : (uint32_t)(((uint64_t)u * POOL) >> bits);
            int b = (int)n;
            uint64_t bit = (b < 64) ? (1ULL << b) : (1ULL << (b - 64));
            uint64_t *w = (b < 64) ? &lo : &hi;
            if (*w & bit) continue;
            *w |= bit;
            out[got++] = (uint8_t)(n + 1);
        }
        return;
    }
    uint8_t arr[POOL];
    for (int i = 0; i < POOL; i++) arr[i] = (uint8_t)(i + 1);
    for (int i = 0; i < DRAWN; i++) {
        uint32_t m = (uint32_t)(POOL - i);
        uint32_t u = gen_next(g, &st);
        uint32_t p = (s == 2) ? (u % m) : (uint32_t)(((uint64_t)u * m) >> bits);
        int j = i + (int)p;
        uint8_t t = arr[i]; arr[i] = arr[j]; arr[j] = t;
        out[i] = arr[i];
    }
}

int main(int argc, char **argv) {
    int nthreads = 4;
    const char *env = getenv("SWEEP_THREADS");
    if (env) nthreads = atoi(env);
    if (nthreads < 1) nthreads = 1;

    if (argc >= 2 && strcmp(argv[1], "--selftest") == 0) {
        // Graine témoin volontairement placée en fin de plage : une attaque
        // qui ne balaierait que le début la manquerait.
        const uint64_t WITNESS = 1234567;
        const uint64_t LO = 0, HI = 2000000;
        int ok = 0, tot = 0;
        printf("AUTOTEST — graine témoin %llu dans [%llu, %llu)\n\n",
               (unsigned long long)WITNESS, (unsigned long long)LO,
               (unsigned long long)HI);
        printf("%-20s %-30s %-10s %s\n", "générateur", "échantillonneur",
               "retrouvée", "graines compatibles");
        for (int g = 0; g < NGEN; g++) {
            for (int s = 0; s < NSAMP; s++) {
                uint8_t tgt[DRAWN];
                memset(tgt, 0, sizeof tgt);
                produce(g, s, WITNESS, tgt);
                int complete = 1;
                for (int i = 0; i < DRAWN; i++) if (!tgt[i]) complete = 0;
                if (!complete) {
                    printf("%-20s %-30s %-10s %s\n", GEN_NAME[g], SAMP_NAME[s],
                           "—", "tirage incomplet (sortie trop étroite)");
                    continue;
                }
                uint64_t first = 0;
                uint64_t n = sweep(g, s, LO, HI, tgt, NULL, nthreads, &first);
                tot++;
                int found = (n >= 1);
                if (found) ok++;
                printf("%-20s %-30s %-10s %llu\n", GEN_NAME[g], SAMP_NAME[s],
                       found ? "OUI" : "NON", (unsigned long long)n);
            }
        }
        printf("\n%d/%d combinaisons retrouvent leur témoin.\n", ok, tot);
        return ok == tot ? 0 : 1;
    }

    if (argc < 23) {
        fprintf(stderr, "usage: %s <lo> <hi> <o1..o20> [-- <c1..c20>]\n", argv[0]);
        fprintf(stderr, "       %s --selftest\n", argv[0]);
        return 1;
    }
    uint64_t lo = strtoull(argv[1], 0, 10), hi = strtoull(argv[2], 0, 10);
    uint8_t target[DRAWN], confirm[DRAWN];
    for (int i = 0; i < DRAWN; i++) target[i] = (uint8_t)atoi(argv[3 + i]);
    int has_confirm = 0;
    if (argc >= 23 + 1 + DRAWN && strcmp(argv[23], "--") == 0) {
        for (int i = 0; i < DRAWN; i++) confirm[i] = (uint8_t)atoi(argv[24 + i]);
        has_confirm = 1;
    }

    fprintf(stderr, "plage [%llu, %llu) — %d fils — confirmation : %s\n",
            (unsigned long long)lo, (unsigned long long)hi, nthreads,
            has_confirm ? "oui" : "non");
    printf("%-20s %-30s %s\n", "générateur", "échantillonneur", "graines compatibles");
    uint64_t grand = 0;
    for (int g = 0; g < NGEN; g++) {
        for (int s = 0; s < NSAMP; s++) {
            uint64_t first = 0;
            uint64_t n = sweep(g, s, lo, hi, target,
                               has_confirm ? confirm : NULL, nthreads, &first);
            grand += n;
            if (n)
                printf("%-20s %-30s %llu   PREMIÈRE = %llu\n", GEN_NAME[g],
                       SAMP_NAME[s], (unsigned long long)n,
                       (unsigned long long)first);
            else
                printf("%-20s %-30s 0\n", GEN_NAME[g], SAMP_NAME[s]);
            fflush(stdout);
        }
    }
    printf("\ntotal : %llu graine(s) compatible(s)\n", (unsigned long long)grand);
    return 0;
}
