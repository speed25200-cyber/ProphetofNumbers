// sweep_mt — balayage de graines Mersenne Twister contre un tirage ORDONNÉ.
//
// Pourquoi un programme séparé
// -----------------------------
// `sweep_order.c` couvre huit familles dont l'amorçage coûte une poignée
// d'opérations. Le Mersenne Twister, lui, initialise 624 mots avant sa
// première sortie : deux mille opérations par graine au lieu d'une. Il ne
// peut pas partager la même boucle sans la ralentir d'un facteur mille.
//
// Il mérite pourtant son propre balayage, pour une raison simple : c'est le
// générateur le plus répandu du logiciel ordinaire. `random` de Python,
// `mt_rand` de PHP, `RandomState` de numpy, la bibliothèque standard de
// Ruby — tous MT19937, tous amorçables par un entier de 32 bits, donc tous
// entièrement balayables.
//
// Ce que ce programme reproduit EXACTEMENT
// -----------------------------------------
// Deux amorçages :
//   init_genrand(s)          la forme canonique de Matsumoto-Nishimura
//   init_by_array([s])       ce que fait `random.seed(n)` de CPython
//
// Cinq façons de tirer vingt numéros sur quatre-vingts, dont trois sont des
// algorithmes publiés que l'on peut transcrire à la ligne près :
//   S0  random.sample de CPython — méthode « pool », avec _randbelow par
//       getrandbits et rejet ; c'est l'algorithme exact, pas une imitation
//   S1  Fisher-Yates partiel à indice modulaire
//   S2  Fisher-Yates partiel à indice multiply-shift
//   S3  modulo 80 avec rejet des doublons
//   S4  random.shuffle de CPython puis les vingt premiers
//
// L'autotest fabrique un tirage depuis une graine connue pour chacune des
// dix combinaisons et exige de la retrouver.
//
//   cc -O3 -march=native -pthread -o sweep_mt sweep_mt.c
//   ./sweep_mt --selftest
//   ./sweep_mt <lo> <hi> <o1..o20> [-- <c1..c20>]

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <pthread.h>

#define POOL 80
#define DRAWN 20
#define N 624
#define M 397
#define MATRIX_A 0x9908b0dfUL
#define UPPER 0x80000000UL
#define LOWER 0x7fffffffUL

typedef struct { uint32_t mt[N]; int mti; } mt_t;

static void init_genrand(mt_t *g, uint32_t s) {
    g->mt[0] = s;
    for (int i = 1; i < N; i++)
        g->mt[i] = (uint32_t)(1812433253UL * (g->mt[i - 1] ^ (g->mt[i - 1] >> 30)) + (uint32_t)i);
    g->mti = N;
}

// `random.seed(n)` de CPython pour un entier n tenant sur 32 bits.
static void init_by_array(mt_t *g, const uint32_t *key, int klen) {
    init_genrand(g, 19650218UL);
    int i = 1, j = 0;
    int k = (N > klen ? N : klen);
    for (; k; k--) {
        g->mt[i] = (uint32_t)((g->mt[i] ^ ((g->mt[i - 1] ^ (g->mt[i - 1] >> 30)) * 1664525UL))
                              + key[j] + (uint32_t)j);
        i++; j++;
        if (i >= N) { g->mt[0] = g->mt[N - 1]; i = 1; }
        if (j >= klen) j = 0;
    }
    for (k = N - 1; k; k--) {
        g->mt[i] = (uint32_t)((g->mt[i] ^ ((g->mt[i - 1] ^ (g->mt[i - 1] >> 30)) * 1566083941UL))
                              - (uint32_t)i);
        i++;
        if (i >= N) { g->mt[0] = g->mt[N - 1]; i = 1; }
    }
    g->mt[0] = 0x80000000UL;
    g->mti = N;
}

static inline uint32_t genrand(mt_t *g) {
    uint32_t y;
    if (g->mti >= N) {
        int kk;
        for (kk = 0; kk < N - M; kk++) {
            y = (g->mt[kk] & UPPER) | (g->mt[kk + 1] & LOWER);
            g->mt[kk] = g->mt[kk + M] ^ (y >> 1) ^ ((y & 1) ? MATRIX_A : 0);
        }
        for (; kk < N - 1; kk++) {
            y = (g->mt[kk] & UPPER) | (g->mt[kk + 1] & LOWER);
            g->mt[kk] = g->mt[kk + (M - N)] ^ (y >> 1) ^ ((y & 1) ? MATRIX_A : 0);
        }
        y = (g->mt[N - 1] & UPPER) | (g->mt[0] & LOWER);
        g->mt[N - 1] = g->mt[M - 1] ^ (y >> 1) ^ ((y & 1) ? MATRIX_A : 0);
        g->mti = 0;
    }
    y = g->mt[g->mti++];
    y ^= (y >> 11);
    y ^= (y << 7) & 0x9d2c5680UL;
    y ^= (y << 15) & 0xefc60000UL;
    y ^= (y >> 18);
    return y;
}

static inline int bit_length(uint32_t n) {
    int b = 0;
    while (n) { b++; n >>= 1; }
    return b;
}

// `_randbelow_with_getrandbits` de CPython : getrandbits(k) puis rejet.
//
// Le nombre de bits demandés est `n.bit_length()` et NON `(n-1).bit_length()`
// — CPython le commente explicitement (« don't use (n-1) here because n can
// be 1 »). Les deux coïncident partout SAUF quand n est une puissance de
// deux, et n parcourt ici 80, 79, …, 61 : la divergence tombe donc pile sur
// n = 64, au dix-septième numéro. Une transcription fautive produit les
// seize premiers numéros justes puis diverge, ce qu'aucun autotest interne
// ne peut voir. Seule la confrontation à CPython lui-même l'attrape.
static inline uint32_t randbelow(mt_t *g, uint32_t n) {
    if (n <= 1) return 0;
    int k = bit_length(n);
    if (k == 0) return 0;
    for (int guard = 0; guard < 200; guard++) {
        uint32_t r = genrand(g) >> (32 - k);
        if (r < n) return r;
    }
    return 0;
}

// ---------------------------------------------------------------------------
// Les cinq échantillonneurs. `out` reçoit l'ordre de sortie ; `target`, s'il
// est non nul, permet l'arrêt anticipé dès le premier écart.
// ---------------------------------------------------------------------------

static int emit(int samp, mt_t *g, const uint8_t *target, uint8_t *out) {
    uint8_t pool[POOL];
    switch (samp) {
    case 0: {                                   // random.sample, méthode pool
        for (int i = 0; i < POOL; i++) pool[i] = (uint8_t)(i + 1);
        for (int i = 0; i < DRAWN; i++) {
            uint32_t j = randbelow(g, (uint32_t)(POOL - i));
            uint8_t v = pool[j];
            pool[j] = pool[POOL - i - 1];
            if (out) out[i] = v;
            if (target && v != target[i]) return 0;
        }
        return 1;
    }
    case 1:                                     // Fisher-Yates modulaire
    case 2: {                                   // Fisher-Yates multiply-shift
        for (int i = 0; i < POOL; i++) pool[i] = (uint8_t)(i + 1);
        for (int i = 0; i < DRAWN; i++) {
            uint32_t m = (uint32_t)(POOL - i);
            uint32_t u = genrand(g);
            uint32_t p = (samp == 1) ? (u % m) : (uint32_t)(((uint64_t)u * m) >> 32);
            int j = i + (int)p;
            uint8_t t = pool[i]; pool[i] = pool[j]; pool[j] = t;
            if (out) out[i] = pool[i];
            if (target && pool[i] != target[i]) return 0;
        }
        return 1;
    }
    case 3: {                                   // modulo 80 avec rejet
        uint64_t lo = 0, hi = 0;
        int got = 0, steps = 0;
        while (got < DRAWN && steps < 400) {
            steps++;
            uint32_t n = genrand(g) % POOL;
            uint64_t bit = (n < 64) ? (1ULL << n) : (1ULL << (n - 64));
            uint64_t *w = (n < 64) ? &lo : &hi;
            if (*w & bit) continue;
            *w |= bit;
            if (out) out[got] = (uint8_t)(n + 1);
            if (target && (uint8_t)(n + 1) != target[got]) return 0;
            got++;
        }
        return got == DRAWN;
    }
    default: {                                  // random.shuffle puis 20 premiers
        for (int i = 0; i < POOL; i++) pool[i] = (uint8_t)(i + 1);
        for (int i = POOL - 1; i >= 1; i--) {
            uint32_t j = randbelow(g, (uint32_t)(i + 1));
            uint8_t t = pool[i]; pool[i] = pool[j]; pool[j] = t;
        }
        for (int i = 0; i < DRAWN; i++) {
            if (out) out[i] = pool[i];
            if (target && pool[i] != target[i]) return 0;
        }
        return 1;
    }
    }
}

#define NINIT 2
#define NSAMP 5

static const char *INIT_NAME[NINIT] = { "init_genrand(s)", "random.seed(s) CPython" };
static const char *SAMP_NAME[NSAMP] = {
    "random.sample (pool)", "Fisher-Yates modulo", "Fisher-Yates multiply-shift",
    "modulo 80 + rejet", "random.shuffle + 20 premiers"
};

static void seed_mt(mt_t *g, int init, uint64_t seed) {
    uint32_t s = (uint32_t)seed;
    if (init == 0) init_genrand(g, s);
    else { uint32_t key[1] = { s }; init_by_array(g, key, 1); }
}

typedef struct {
    uint64_t lo, hi;
    const uint8_t *target, *confirm;
    int init;
    uint64_t hits[NSAMP];
    uint64_t first[NSAMP];
} job;

static void *worker(void *arg) {
    job *j = (job *)arg;
    memset(j->hits, 0, sizeof j->hits);
    mt_t g, saved;
    for (uint64_t seed = j->lo; seed < j->hi; seed++) {
        seed_mt(&saved, j->init, seed);          // l'amorçage domine le coût
        for (int s = 0; s < NSAMP; s++) {
            g = saved;
            if (!emit(s, &g, j->target, NULL)) continue;
            if (j->confirm) {
                seed_mt(&g, j->init, seed);
                if (!emit(s, &g, j->confirm, NULL)) continue;
            }
            if (j->hits[s] == 0) j->first[s] = seed;
            j->hits[s]++;
        }
    }
    return NULL;
}

static void sweep(int init, uint64_t lo, uint64_t hi, const uint8_t *target,
                  const uint8_t *confirm, int nthreads,
                  uint64_t *tot, uint64_t *first) {
    pthread_t th[64];
    job jobs[64];
    if (nthreads > 64) nthreads = 64;
    uint64_t span = (hi - lo) / (uint64_t)nthreads + 1;
    for (int i = 0; i < nthreads; i++) {
        jobs[i].lo = lo + span * (uint64_t)i;
        jobs[i].hi = jobs[i].lo + span; if (jobs[i].hi > hi) jobs[i].hi = hi;
        if (jobs[i].lo > hi) jobs[i].lo = jobs[i].hi = hi;
        jobs[i].target = target; jobs[i].confirm = confirm; jobs[i].init = init;
        memset(jobs[i].first, 0, sizeof jobs[i].first);
        pthread_create(&th[i], NULL, worker, &jobs[i]);
    }
    memset(tot, 0, sizeof(uint64_t) * NSAMP);
    memset(first, 0, sizeof(uint64_t) * NSAMP);
    for (int i = 0; i < nthreads; i++) {
        pthread_join(th[i], NULL);
        for (int s = 0; s < NSAMP; s++) {
            if (jobs[i].hits[s] && tot[s] == 0) first[s] = jobs[i].first[s];
            tot[s] += jobs[i].hits[s];
        }
    }
}

int main(int argc, char **argv) {
    int nthreads = 4;
    const char *env = getenv("SWEEP_THREADS");
    if (env) nthreads = atoi(env);
    if (nthreads < 1) nthreads = 1;

    if (argc >= 2 && strcmp(argv[1], "--selftest") == 0) {
        const uint64_t WITNESS = 987654;
        const uint64_t LO = 0, HI = 1500000;
        int ok = 0, tot_c = 0;
        printf("AUTOTEST — graine témoin %llu dans [%llu, %llu)\n\n",
               (unsigned long long)WITNESS, (unsigned long long)LO,
               (unsigned long long)HI);
        printf("%-24s %-30s %-10s %s\n", "amorçage", "échantillonneur",
               "retrouvée", "graines compatibles");
        for (int init = 0; init < NINIT; init++) {
            uint8_t tgt[NSAMP][DRAWN];
            for (int s = 0; s < NSAMP; s++) {
                mt_t g; seed_mt(&g, init, WITNESS);
                emit(s, &g, NULL, tgt[s]);
            }
            for (int s = 0; s < NSAMP; s++) {
                uint64_t t[NSAMP], f[NSAMP];
                sweep(init, LO, HI, tgt[s], NULL, nthreads, t, f);
                tot_c++;
                int found = t[s] >= 1;
                if (found) ok++;
                printf("%-24s %-30s %-10s %llu\n", INIT_NAME[init], SAMP_NAME[s],
                       found ? "OUI" : "NON", (unsigned long long)t[s]);
            }
        }
        printf("\n%d/%d combinaisons retrouvent leur témoin.\n", ok, tot_c);
        return ok == tot_c ? 0 : 1;
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
    printf("%-24s %-30s %s\n", "amorçage", "échantillonneur", "graines compatibles");
    uint64_t grand = 0;
    for (int init = 0; init < NINIT; init++) {
        uint64_t t[NSAMP], f[NSAMP];
        sweep(init, lo, hi, target, has_confirm ? confirm : NULL, nthreads, t, f);
        for (int s = 0; s < NSAMP; s++) {
            grand += t[s];
            if (t[s])
                printf("%-24s %-30s %llu   PREMIÈRE = %llu\n", INIT_NAME[init],
                       SAMP_NAME[s], (unsigned long long)t[s],
                       (unsigned long long)f[s]);
            else
                printf("%-24s %-30s 0\n", INIT_NAME[init], SAMP_NAME[s]);
        }
        fflush(stdout);
    }
    printf("\ntotal : %llu graine(s) compatible(s)\n", (unsigned long long)grand);
    return 0;
}
