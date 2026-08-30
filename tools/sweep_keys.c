// sweep_keys — l'échantillonneur PAR CLÉS, que rien ne couvrait.
//
// La case béante
// ---------------
// Tous les échantillonneurs testés jusqu'ici — modulo avec rejet,
// multiply-shift, Fisher-Yates partiel, dérangement d'une valeur large,
// `random.sample`, `random.shuffle` — consomment VINGT sorties du générateur
// pour produire vingt numéros. Aucun n'en consomme quatre-vingts.
//
// Or l'idiome le plus répandu de toute la programmation ordinaire pour
// « tirer k éléments parmi n » n'est aucun de ceux-là. C'est
//
//     ORDER BY RANDOM() LIMIT 20          (SQL, toutes bases)
//     argsort(rand(80))[:20]              (numpy, R, MATLAB)
//     sorted(items, key=lambda _: rnd())  (Python, JavaScript, Java streams)
//
// c'est-à-dire : donner une CLÉ aléatoire à chacun des quatre-vingts
// numéros, trier, garder les vingt premiers. Le générateur y consomme
// quatre-vingts sorties par tirage, et l'ordre publié est l'ordre des clés.
//
// Aucune attaque du dossier ne pouvait le voir. Les attaques algébriques
// supposent vingt sorties consécutives reliées par une récurrence ; les
// balayages précédents rejettent une graine dès le premier numéro, ce qui
// n'a aucun sens ici puisque le premier numéro dépend des quatre-vingts
// clés à la fois.
//
// Le test
// -------
// Pour une graine candidate : produire les 80 clés, puis vérifier que les
// vingt numéros du tirage sont EXACTEMENT ceux de plus petite clé, et que
// leur ordre de clés croissantes est l'ordre publié. C'est une condition
// d'une force écrasante — elle fixe l'ordre relatif de 80 valeurs — donc la
// probabilité qu'une graine fausse la satisfasse vaut 1/(80!/60!) ≈ 10⁻³⁷.
//
// Il n'y a pas d'arrêt anticipé possible : il faut les quatre-vingts sorties
// avant de pouvoir juger. Le balayage coûte donc quatre-vingts fois plus
// cher par graine que les précédents — ce qui reste faisable, à dix-sept
// minutes pour 2³² graines et douze familles.
//
//   cc -O3 -march=native -pthread -o sweep_keys sweep_keys.c
//   ./sweep_keys --selftest
//   ./sweep_keys <lo> <hi> <o1..o20>

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <pthread.h>

#define POOL 80
#define DRAWN 20
#define NGEN 12

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

static const char *GEN_NAME[NGEN] = {
    "java.util.Random", "LCG32 MSVC", "LCG32 glibc", "xorshift32",
    "xorshift64*", "splitmix64", "pcg32", "LCG64 MMIX",
    "xoshiro256**", "xoshiro128**", "xoroshiro128+", "pcg64"
};

// `desc` = 0 : on garde les vingt PLUS PETITES clés ; 1 : les plus grandes.
// Les deux conventions existent selon qu'on écrit ORDER BY x ou ORDER BY x DESC.
//
// Le tirage est reproduit si et seulement si :
//   * les clés des vingt numéros publiés sont croissantes dans l'ordre publié ;
//   * toute clé d'un numéro NON publié est plus grande que la vingtième.
// C'est une condition sur l'ordre relatif de quatre-vingts valeurs, donc de
// probabilité 1/(80!/60!) ≈ 10^-37 pour une graine fausse.
static inline int match_keys(int g, uint64_t seed, const uint8_t *target,
                             const uint8_t *inset, int desc) {
    gstate st;
    gen_init(g, seed, &st);
    uint32_t key[POOL];
    for (int i = 0; i < POOL; i++) {
        uint32_t u = gen_next(g, &st);
        key[i] = desc ? ~u : u;
    }
    uint32_t prev = key[target[0] - 1];
    for (int i = 1; i < DRAWN; i++) {
        uint32_t k = key[target[i] - 1];
        if (k < prev) return 0;                 // ordre des clés non croissant
        prev = k;
    }
    for (int n = 1; n <= POOL; n++)
        if (!inset[n] && key[n - 1] < prev) return 0;   // un exclu passe devant
    return 1;
}

typedef struct {
    uint64_t lo, hi;
    const uint8_t *target, *inset;
    int gen, desc;
    uint64_t hits, first;
} job;

static void *worker(void *arg) {
    job *J = (job *)arg;
    J->hits = 0;
    for (uint64_t s = J->lo; s < J->hi; s++)
        if (match_keys(J->gen, s, J->target, J->inset, J->desc)) {
            if (J->hits == 0) J->first = s;
            J->hits++;
        }
    return NULL;
}

static uint64_t sweep(int g, int desc, uint64_t lo, uint64_t hi,
                      const uint8_t *target, const uint8_t *inset,
                      int nthreads, uint64_t *first) {
    pthread_t th[64]; job jobs[64];
    if (nthreads > 64) nthreads = 64;
    uint64_t span = (hi - lo) / (uint64_t)nthreads + 1, total = 0;
    for (int i = 0; i < nthreads; i++) {
        jobs[i].lo = lo + span * (uint64_t)i;
        jobs[i].hi = jobs[i].lo + span; if (jobs[i].hi > hi) jobs[i].hi = hi;
        if (jobs[i].lo > hi) jobs[i].lo = jobs[i].hi = hi;
        jobs[i].target = target; jobs[i].inset = inset;
        jobs[i].gen = g; jobs[i].desc = desc; jobs[i].hits = 0; jobs[i].first = 0;
        pthread_create(&th[i], NULL, worker, &jobs[i]);
    }
    for (int i = 0; i < nthreads; i++) {
        pthread_join(th[i], NULL);
        if (jobs[i].hits && total == 0 && first) *first = jobs[i].first;
        total += jobs[i].hits;
    }
    return total;
}

// Fabrique l'ordre que (g, desc) produit depuis une graine — pour l'autotest.
static void produce(int g, uint64_t seed, int desc, uint8_t *out) {
    gstate st;
    gen_init(g, seed, &st);
    uint32_t key[POOL];
    for (int i = 0; i < POOL; i++) {
        uint32_t u = gen_next(g, &st);
        key[i] = desc ? ~u : u;
    }
    int idx[POOL];
    for (int i = 0; i < POOL; i++) idx[i] = i;
    for (int i = 1; i < POOL; i++) {            // tri par insertion, n petit
        int v = idx[i], j = i - 1;
        while (j >= 0 && key[idx[j]] > key[v]) { idx[j + 1] = idx[j]; j--; }
        idx[j + 1] = v;
    }
    for (int i = 0; i < DRAWN; i++) out[i] = (uint8_t)(idx[i] + 1);
}

int main(int argc, char **argv) {
    int nthreads = 4;
    const char *env = getenv("SWEEP_THREADS");
    if (env) nthreads = atoi(env);
    if (nthreads < 1) nthreads = 1;

    if (argc >= 2 && strcmp(argv[1], "--selftest") == 0) {
        const uint64_t W = 1234567, LO = 0, HI = 3000000;
        int ok = 0, tot = 0;
        printf("AUTOTEST — graine témoin %llu dans [%llu, %llu)\n\n",
               (unsigned long long)W, (unsigned long long)LO,
               (unsigned long long)HI);
        printf("%-20s %-14s %-10s %s\n", "générateur", "convention",
               "retrouvée", "graines compatibles");
        for (int g = 0; g < NGEN; g++) {
            for (int d = 0; d < 2; d++) {
                uint8_t tgt[DRAWN], inset[POOL + 1];
                produce(g, W, d, tgt);
                memset(inset, 0, sizeof inset);
                for (int i = 0; i < DRAWN; i++) inset[tgt[i]] = 1;
                uint64_t first = 0;
                uint64_t n = sweep(g, d, LO, HI, tgt, inset, nthreads, &first);
                tot++;
                if (n >= 1) ok++;
                printf("%-20s %-14s %-10s %llu%s\n", GEN_NAME[g],
                       d ? "décroissante" : "croissante",
                       n ? "OUI" : "NON", (unsigned long long)n,
                       (n && first == W) ? "   = témoin" : "");
            }
        }
        printf("\n%d/%d combinaisons retrouvent leur témoin.\n", ok, tot);
        return ok == tot ? 0 : 1;
    }

    if (argc < 23) {
        fprintf(stderr, "usage: %s <lo> <hi> <o1..o20>\n       %s --selftest\n",
                argv[0], argv[0]);
        return 1;
    }
    uint64_t lo = strtoull(argv[1], 0, 10), hi = strtoull(argv[2], 0, 10);
    uint8_t target[DRAWN], inset[POOL + 1];
    memset(inset, 0, sizeof inset);
    for (int i = 0; i < DRAWN; i++) {
        target[i] = (uint8_t)atoi(argv[3 + i]);
        inset[target[i]] = 1;
    }
    fprintf(stderr, "plage [%llu, %llu) — %d fils — 80 clés par graine\n",
            (unsigned long long)lo, (unsigned long long)hi, nthreads);
    printf("%-20s %-14s %s\n", "générateur", "convention", "graines compatibles");
    uint64_t grand = 0;
    for (int g = 0; g < NGEN; g++)
        for (int d = 0; d < 2; d++) {
            uint64_t first = 0;
            uint64_t n = sweep(g, d, lo, hi, target, inset, nthreads, &first);
            grand += n;
            if (n) printf("%-20s %-14s %llu   PREMIÈRE = %llu\n", GEN_NAME[g],
                          d ? "décroissante" : "croissante",
                          (unsigned long long)n, (unsigned long long)first);
            else printf("%-20s %-14s 0\n", GEN_NAME[g],
                        d ? "décroissante" : "croissante");
            fflush(stdout);
        }
    printf("\ntotal : %llu graine(s) compatible(s)\n", (unsigned long long)grand);
    return 0;
}
