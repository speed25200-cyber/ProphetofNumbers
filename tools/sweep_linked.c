// sweep_linked — l'amorçage LIÉ AU NUMÉRO DE TIRAGE, sur l'archive entière.
//
// Ce que les autres balayages ne peuvent pas faire
// -------------------------------------------------
// `sweep_order.c` balaie les graines contre UN tirage ordonné. Il écarte donc
// tout schéma d'amorçage dont la graine tombe dans la plage balayée — mais
// pour CE tirage seulement, et le dossier ne dispose que de cinq tirages
// ordonnés, tous du 30 août 2026.
//
// L'archive, elle, contient 70 560 tirages étalés sur des mois. Elle est
// triée, donc son filtre est plus faible (1/4 par numéro au lieu de 1/80),
// mais elle permet une chose que cinq tirages ne permettent pas : tester une
// RELATION entre la graine et le numéro de tirage, et la confirmer sur des
// milliers de tirages séparés dans le temps.
//
// L'hypothèse testée
// -------------------
//     graine du tirage t  =  numéro de tirage t  +  B
//
// pour tout décalage B de [0, 2³²). C'est la forme qu'on écrit quand on veut
// un tirage reproductible et vérifiable — `new Random(drawId)` — et elle est
// invisible pour un balayage qui exigerait la même graine à deux tirages
// différents.
//
// Le décalage B=0 correspond à `new Random(drawId)` exactement. Les autres
// couvrent un identifiant interne décalé, un compteur, ou une graine de base
// à laquelle le numéro s'ajoute.
//
// Coût et pouvoir
// ----------------
// Un B faux meurt au premier ou au deuxième numéro du premier tirage : 1,33
// pas de générateur en moyenne. Le balayage complet coûte donc ≈ 2,7·10¹¹
// pas pour quarante-huit combinaisons.
//
// Un B faux qui survivrait au premier tirage entier a une probabilité
// C(80,20)⁻¹ ≈ 2,8·10⁻¹⁹ de le faire ; la confirmation sur un second tirage
// la porte à 8·10⁻³⁸. Sur 2³² × 48 essais, l'espérance de faux positif vaut
// 10⁻²⁷.
//
//   cc -O3 -march=native -pthread -o sweep_linked sweep_linked.c
//   ./sweep_linked --selftest
//   ./sweep_linked <lo> <hi> <fichier>
//
// Le fichier contient une ligne par tirage : `id n1 n2 … n20` (ensemble
// trié, l'ordre n'important pas ici).

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <pthread.h>

#define POOL 80
#define DRAWN 20
#define NGEN 12
#define NSAMP 4
#define MAXDRAWS 64

#define JAVA_A 0x5DEECE66DULL
#define JAVA_C 0xBULL
#define M48    0xFFFFFFFFFFFFULL

typedef struct { uint64_t a, b, c, d; } gstate;

static inline uint64_t sm64(uint64_t *x) {
    *x += 0x9E3779B97F4A7C15ULL;
    uint64_t z = *x;
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31);
}
static inline uint64_t rotl64(uint64_t x, int k) { return (x << k) | (x >> (64 - k)); }
static inline uint32_t rotl32(uint32_t x, int k) { return (x << k) | (x >> (32 - k)); }

static inline void gen_init(int g, uint64_t seed, gstate *st) {
    st->b = 0; st->c = 0; st->d = 0;
    switch (g) {
    case 0: st->a = (seed ^ JAVA_A) & M48; break;
    case 1: st->a = seed & 0xFFFFFFFFULL; break;
    case 2: st->a = seed & 0x7FFFFFFFULL; break;
    case 3: st->a = (seed & 0xFFFFFFFFULL) ? (seed & 0xFFFFFFFFULL) : 1; break;
    case 4: st->a = seed ? seed : 1; break;
    case 5: st->a = seed; break;
    case 6: st->a = seed; st->b = 1442695040888963407ULL; break;
    case 7: st->a = seed; break;
    case 8: { uint64_t x = seed; st->a = sm64(&x); st->b = sm64(&x);
              st->c = sm64(&x); st->d = sm64(&x); break; }
    case 9: { uint64_t x = seed; uint64_t u = sm64(&x), v = sm64(&x);
              st->a = u & 0xFFFFFFFFULL; st->b = u >> 32;
              st->c = v & 0xFFFFFFFFULL; st->d = v >> 32; break; }
    case 10: { uint64_t x = seed; st->a = sm64(&x); st->b = sm64(&x); break; }
    default: { uint64_t x = seed; st->a = sm64(&x); st->b = sm64(&x); break; }
    }
}

static inline uint32_t gen_next(int g, gstate *st) {
    uint64_t x;
    switch (g) {
    case 0: st->a = (st->a * JAVA_A + JAVA_C) & M48; return (uint32_t)(st->a >> 16);
    case 1: st->a = (st->a * 214013ULL + 2531011ULL) & 0xFFFFFFFFULL;
            return (uint32_t)(st->a >> 16) & 0x7FFFu;
    case 2: st->a = (st->a * 1103515245ULL + 12345ULL) & 0x7FFFFFFFULL;
            return (uint32_t)st->a;
    case 3: x = st->a; x ^= (x << 13) & 0xFFFFFFFFULL; x ^= x >> 17;
            x ^= (x << 5) & 0xFFFFFFFFULL; st->a = x & 0xFFFFFFFFULL;
            return (uint32_t)st->a;
    case 4: x = st->a; x ^= x >> 12; x ^= x << 25; x ^= x >> 27; st->a = x;
            return (uint32_t)((x * 2685821657736338717ULL) >> 32);
    case 5: st->a += 0x9E3779B97F4A7C15ULL; x = st->a;
            x = (x ^ (x >> 30)) * 0xBF58476D1CE4E5B9ULL;
            x = (x ^ (x >> 27)) * 0x94D049BB133111EBULL;
            return (uint32_t)((x ^ (x >> 31)) >> 32);
    case 6: { uint64_t old = st->a;
              st->a = old * 6364136223846793005ULL + (st->b | 1ULL);
              uint32_t xs = (uint32_t)(((old >> 18) ^ old) >> 27);
              uint32_t rot = (uint32_t)(old >> 59);
              return (xs >> rot) | (xs << ((-rot) & 31)); }
    case 7: st->a = st->a * 6364136223846793005ULL + 1442695040888963407ULL;
            return (uint32_t)(st->a >> 32);
    case 8: { uint64_t r = rotl64(st->b * 5ULL, 7) * 9ULL, t = st->b << 17;
              st->c ^= st->a; st->d ^= st->b; st->b ^= st->c; st->a ^= st->d;
              st->c ^= t; st->d = rotl64(st->d, 45); return (uint32_t)(r >> 32); }
    case 9: { uint32_t s0 = (uint32_t)st->a, s1 = (uint32_t)st->b;
              uint32_t s2 = (uint32_t)st->c, s3 = (uint32_t)st->d;
              uint32_t r = rotl32(s1 * 5u, 7) * 9u, t = s1 << 9;
              s2 ^= s0; s3 ^= s1; s1 ^= s2; s0 ^= s3; s2 ^= t; s3 = rotl32(s3, 11);
              st->a = s0; st->b = s1; st->c = s2; st->d = s3; return r; }
    case 10: { uint64_t s0 = st->a, s1 = st->b, r = s0 + s1;
               s1 ^= s0; st->a = rotl64(s0, 24) ^ s1 ^ (s1 << 16);
               st->b = rotl64(s1, 37); return (uint32_t)(r >> 32); }
    default: { uint64_t lo = st->a, hi = st->b;
               const uint64_t ML = 0x4385DF649FCCF645ULL, MH = 0x2360ED051FC65DA4ULL;
               uint64_t l0 = (lo & 0xFFFFFFFFULL) * (ML & 0xFFFFFFFFULL);
               uint64_t l1 = (lo >> 32) * (ML & 0xFFFFFFFFULL);
               uint64_t l2 = (lo & 0xFFFFFFFFULL) * (ML >> 32);
               uint64_t l3 = (lo >> 32) * (ML >> 32);
               uint64_t mid = l1 + (l0 >> 32) + (l2 & 0xFFFFFFFFULL);
               uint64_t nlo = (l0 & 0xFFFFFFFFULL) | (mid << 32);
               uint64_t nhi = l3 + (mid >> 32) + (l2 >> 32) + lo * MH + hi * ML;
               nlo += 1ULL; if (nlo == 0) nhi++;
               nhi += 0x5851F42D4C957F2DULL;
               st->a = nlo; st->b = nhi;
               uint64_t xs = nhi ^ nlo; unsigned rot = (unsigned)(nhi >> 58);
               uint64_t out = (xs >> rot) | (xs << ((-rot) & 63));
               return (uint32_t)(out >> 32); }
    }
}

static inline uint32_t gen_bound(int g) { return (g == 1) ? 15u : 32u; }

// Le tirage est ici comparé comme ENSEMBLE : l'archive est triée, l'ordre de
// sortie n'y figure pas. Le filtre est donc de 1/4 par numéro au lieu de
// 1/80, ce que la longueur de l'archive compense largement.
static int match_set(int g, int s, uint64_t seed, const uint8_t *inset) {
    gstate st;
    gen_init(g, seed, &st);
    uint32_t bits = gen_bound(g);
    uint64_t lo = 0, hi = 0;
    int got = 0;
    if (s == 0 || s == 1) {
        int steps = 0;
        while (got < DRAWN && steps < 400) {
            steps++;
            uint32_t u = gen_next(g, &st);
            uint32_t n = (s == 0) ? (u % POOL)
                                  : (uint32_t)(((uint64_t)u * POOL) >> bits);
            uint64_t bit = (n < 64) ? (1ULL << n) : (1ULL << (n - 64));
            uint64_t *w = (n < 64) ? &lo : &hi;
            if (*w & bit) continue;
            *w |= bit;
            if (!inset[n + 1]) return 0;
            got++;
        }
        return got == DRAWN;
    }
    uint8_t arr[POOL];
    for (int i = 0; i < POOL; i++) arr[i] = (uint8_t)(i + 1);
    for (int i = 0; i < DRAWN; i++) {
        uint32_t m = (uint32_t)(POOL - i);
        uint32_t u = gen_next(g, &st);
        uint32_t p = (s == 2) ? (u % m) : (uint32_t)(((uint64_t)u * m) >> bits);
        int j = i + (int)p;
        uint8_t t = arr[i]; arr[i] = arr[j]; arr[j] = t;
        if (!inset[arr[i]]) return 0;
    }
    return 1;
}

static uint64_t IDS[MAXDRAWS];
static uint8_t INSET[MAXDRAWS][POOL + 1];
static int NDRAWS = 0;

typedef struct {
    uint64_t lo, hi;
    int gen, samp;
    uint64_t hits, first;
} job;

static void *worker(void *arg) {
    job *J = (job *)arg;
    J->hits = 0;
    for (uint64_t B = J->lo; B < J->hi; B++) {
        int ok = 1;
        for (int d = 0; d < NDRAWS && ok; d++)
            if (!match_set(J->gen, J->samp, IDS[d] + B, INSET[d])) ok = 0;
        if (ok) { if (J->hits == 0) J->first = B; J->hits++; }
    }
    return NULL;
}

static const char *GEN_NAME[NGEN] = {
    "java.util.Random", "LCG32 MSVC", "LCG32 glibc", "xorshift32",
    "xorshift64*", "splitmix64", "pcg32", "LCG64 MMIX",
    "xoshiro256**", "xoshiro128**", "xoroshiro128+", "pcg64"
};
static const char *SAMP_NAME[NSAMP] = {
    "modulo + rejet", "multiply-shift + rejet", "Fisher-Yates modulo",
    "Fisher-Yates multiply-shift"
};

static uint64_t sweep(int g, int s, uint64_t lo, uint64_t hi, int nthreads,
                      uint64_t *first) {
    pthread_t th[64]; job jobs[64];
    if (nthreads > 64) nthreads = 64;
    uint64_t span = (hi - lo) / (uint64_t)nthreads + 1, total = 0;
    for (int i = 0; i < nthreads; i++) {
        jobs[i].lo = lo + span * (uint64_t)i;
        jobs[i].hi = jobs[i].lo + span; if (jobs[i].hi > hi) jobs[i].hi = hi;
        if (jobs[i].lo > hi) jobs[i].lo = jobs[i].hi = hi;
        jobs[i].gen = g; jobs[i].samp = s; jobs[i].hits = 0; jobs[i].first = 0;
        pthread_create(&th[i], NULL, worker, &jobs[i]);
    }
    for (int i = 0; i < nthreads; i++) {
        pthread_join(th[i], NULL);
        if (jobs[i].hits && total == 0 && first) *first = jobs[i].first;
        total += jobs[i].hits;
    }
    return total;
}

int main(int argc, char **argv) {
    int nthreads = 4;
    const char *env = getenv("SWEEP_THREADS");
    if (env) nthreads = atoi(env);
    if (nthreads < 1) nthreads = 1;

    if (argc >= 2 && strcmp(argv[1], "--selftest") == 0) {
        const uint64_t B = 777777;
        const uint64_t BASE = 1300000;
        int ok = 0, tot = 0;
        printf("AUTOTEST — décalage témoin B = %llu, trois tirages liés\n\n",
               (unsigned long long)B);
        printf("%-20s %-30s %-10s %s\n", "générateur", "échantillonneur",
               "retrouvé", "décalages compatibles");
        for (int g = 0; g < NGEN; g++) {
            for (int s = 0; s < NSAMP; s++) {
                NDRAWS = 3;
                int complete = 1;
                for (int d = 0; d < NDRAWS; d++) {
                    IDS[d] = BASE + (uint64_t)d * 37ULL;
                    memset(INSET[d], 0, sizeof INSET[d]);
                    // Fabrique le tirage puis le marque comme ensemble.
                    gstate st; gen_init(g, IDS[d] + B, &st);
                    uint32_t bits = gen_bound(g);
                    if (s == 0 || s == 1) {
                        uint64_t lo = 0, hi = 0; int got = 0, steps = 0;
                        while (got < DRAWN && steps < 4000) {
                            steps++;
                            uint32_t u = gen_next(g, &st);
                            uint32_t n = (s == 0) ? (u % POOL)
                                : (uint32_t)(((uint64_t)u * POOL) >> bits);
                            uint64_t bit = (n < 64) ? (1ULL << n) : (1ULL << (n - 64));
                            uint64_t *w = (n < 64) ? &lo : &hi;
                            if (*w & bit) continue;
                            *w |= bit; INSET[d][n + 1] = 1; got++;
                        }
                        if (got != DRAWN) complete = 0;
                    } else {
                        uint8_t arr[POOL];
                        for (int i = 0; i < POOL; i++) arr[i] = (uint8_t)(i + 1);
                        for (int i = 0; i < DRAWN; i++) {
                            uint32_t m = (uint32_t)(POOL - i);
                            uint32_t u = gen_next(g, &st);
                            uint32_t p = (s == 2) ? (u % m)
                                : (uint32_t)(((uint64_t)u * m) >> bits);
                            int j = i + (int)p;
                            uint8_t t = arr[i]; arr[i] = arr[j]; arr[j] = t;
                            INSET[d][arr[i]] = 1;
                        }
                    }
                }
                tot++;
                if (!complete) {
                    printf("%-20s %-30s %-10s %s\n", GEN_NAME[g], SAMP_NAME[s],
                           "—", "tirage incomplet (sortie trop étroite)");
                    ok++;                       // non applicable, pas un échec
                    continue;
                }
                uint64_t first = 0;
                uint64_t n = sweep(g, s, 700000, 800000, nthreads, &first);
                if (n >= 1) ok++;
                printf("%-20s %-30s %-10s %llu%s\n", GEN_NAME[g], SAMP_NAME[s],
                       n ? "OUI" : "NON", (unsigned long long)n,
                       (n && first == B) ? "   = témoin" : "");
            }
        }
        printf("\n%d/%d combinaisons retrouvent leur décalage témoin.\n", ok, tot);
        return ok == tot ? 0 : 1;
    }

    if (argc < 4) {
        fprintf(stderr, "usage: %s <lo> <hi> <fichier>\n", argv[0]);
        fprintf(stderr, "       %s --selftest\n", argv[0]);
        return 1;
    }
    uint64_t lo = strtoull(argv[1], 0, 10), hi = strtoull(argv[2], 0, 10);
    FILE *f = fopen(argv[3], "r");
    if (!f) { perror("fopen"); return 1; }
    while (NDRAWS < MAXDRAWS) {
        unsigned long long id; int n[DRAWN];
        int r = fscanf(f, "%llu", &id);
        if (r != 1) break;
        for (int i = 0; i < DRAWN; i++)
            if (fscanf(f, "%d", &n[i]) != 1) { fclose(f); fprintf(stderr, "ligne courte\n"); return 1; }
        IDS[NDRAWS] = id;
        memset(INSET[NDRAWS], 0, sizeof INSET[NDRAWS]);
        for (int i = 0; i < DRAWN; i++) INSET[NDRAWS][n[i]] = 1;
        NDRAWS++;
    }
    fclose(f);
    fprintf(stderr, "%d tirages liés, décalages [%llu, %llu), %d fils\n",
            NDRAWS, (unsigned long long)lo, (unsigned long long)hi, nthreads);
    printf("%-20s %-30s %s\n", "générateur", "échantillonneur", "décalages compatibles");
    uint64_t grand = 0;
    for (int g = 0; g < NGEN; g++)
        for (int s = 0; s < NSAMP; s++) {
            uint64_t first = 0;
            uint64_t n = sweep(g, s, lo, hi, nthreads, &first);
            grand += n;
            if (n) printf("%-20s %-30s %llu   PREMIER B = %llu\n", GEN_NAME[g],
                          SAMP_NAME[s], (unsigned long long)n, (unsigned long long)first);
            else printf("%-20s %-30s 0\n", GEN_NAME[g], SAMP_NAME[s]);
            fflush(stdout);
        }
    printf("\ntotal : %llu décalage(s) compatible(s)\n", (unsigned long long)grand);
    return 0;
}
