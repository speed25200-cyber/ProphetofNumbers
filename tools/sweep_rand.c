// sweep_rand.c — les trois cases que sweep_order laissait ouvertes.
//
// -------------------------------------------------------------------------
// Ce que ce programme ferme, et que rien d'autre ne fermait
// -------------------------------------------------------------------------
//
// sweep_order balaie douze familles de générateurs contre quatre
// échantillonneurs. En relisant sa liste, trois absences sautent aux yeux —
// et ce sont trois des chemins les plus fréquentés du logiciel ordinaire.
//
// 1. LE VRAI rand() DE LA GLIBC.
//    sweep_order nomme une de ses familles « LCG32 glibc » : s → 1103515245·s
//    + 12345 mod 2³¹. C'est le TYPE_0 de la glibc, celui qu'on n'obtient qu'en
//    réduisant explicitement l'état à huit octets. Le rand() qu'on obtient en
//    tapant srand(); rand(); sur Linux N'EST PAS un LCG : c'est un générateur
//    à récurrence additive décalée, r[i] = r[i-3] + r[i-31], dont le LCG ne
//    sert qu'à remplir la table initiale. Les deux n'ont ni le même état
//    (992 bits contre 31), ni la même sortie, ni la même trace. Balayer l'un
//    ne dit rigoureusement RIEN de l'autre.
//
//    C'est probablement l'omission la plus grave du dossier : « le rand() du
//    C » est la première chose qu'écrit quiconque n'a pas réfléchi au sujet,
//    et c'est exactement le profil qu'on cherche.
//
// 2. LES LCG À MODULE PREMIER.
//    Toutes les attaques algébriques du labo (h7, h8, h10, h11, h12) vivent
//    dans Z/2^k : elles reposent sur la valuation 2-adique, sur des inverses
//    modulo une puissance de deux, sur des racines carrées de Hensel. Un
//    générateur de Lehmer — s → a·s mod (2³¹−1) — n'a aucune de ces prises,
//    et aucun balayage ne l'a couvert. Or MINSTD est `minstd_rand` du C++11,
//    le rand() de plusieurs unix historiques, et le générateur de référence
//    de tous les manuels.
//
// 3. L'ÉCHANTILLONNEUR PAR FLOTTANT — deux mots par numéro.
//    Les quatre échantillonneurs existants consomment UNE sortie par numéro.
//    Or `(int)(Math.random() * 80)` est, de très loin, la façon la plus
//    répandue d'écrire « un numéro au hasard » en Java — et nextDouble()
//    consomme DEUX appels à next() :
//
//        d = ((next(26) << 27) + next(27)) / 2⁵³
//
//    Un balayage qui consomme un mot par numéro se désynchronise donc dès le
//    premier, et meurt en croyant avoir éliminé la graine. Les sorties sont
//    les mêmes, la graine est la bonne, et le test répond non : c'est le pire
//    type d'angle mort, celui qui rend un résultat négatif faux sans jamais
//    rien signaler.
//
// -------------------------------------------------------------------------
// Économie du balayage
// -------------------------------------------------------------------------
//
// L'amorçage de la glibc coûte 341 pas là où un LCG en coûte un. Pour ne pas
// le payer six fois, chaque graine est amorcée UNE fois et ses sorties sont
// mises en tampon PARESSEUX : les six échantillonneurs lisent le même flux,
// et le tampon ne se remplit qu'à la demande. Une graine fausse meurt au
// premier numéro, donc le tampon ne dépasse presque jamais deux entrées.
//
// Le filtre reste celui de l'ORDRE : les vingt numéros doivent sortir dans
// l'ordre publié. Probabilité qu'une graine fausse survive : (80!/60!)⁻¹ ≈
// 1·10⁻³⁷. Aucune confirmation sur un second tirage n'est nécessaire — et
// en exiger une serait une faute, puisque l'hypothèse testée est justement
// celle du ré-amorçage à chaque tirage (voir tools/README.md).
//
// Les couples (famille 0-11, échantillonneur 0-3) sont déjà couverts par
// sweep_order ; ils sont affichés « déjà couvert » et non rebalayés.
//
//   cc -O3 -march=native -pthread -o sweep_rand sweep_rand.c
//   ./sweep_rand --selftest
//   ./sweep_rand 0 4294967296  33 35 45 44 27 70 34 77 7 64 73 22 63 61 8 14 2 26 72 43

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <pthread.h>

#define POOL  80
#define DRAWN 20
#define NGEN  20
#define NSAMP 6
#define BUFMAX 400

#define JAVA_A 0x5DEECE66DULL
#define JAVA_C 0xBULL
#define M48    0xFFFFFFFFFFFFULL
#define MINSTD_M 2147483647L

// Table de la glibc : 63 entrées au plus (TYPE_4), plus les deux pointeurs.
typedef struct {
    uint64_t a, b, c, d;
    int32_t  tab[64];
    int      f, r, deg;
} gstate;

static inline uint64_t sm64(uint64_t *x) {
    *x += 0x9E3779B97F4A7C15ULL;
    uint64_t z = *x;
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31);
}
static inline uint64_t rotl64(uint64_t x, int k) { return (x << k) | (x >> (64 - k)); }
static inline uint32_t rotl32(uint32_t x, int k) { return (x << k) | (x >> (32 - k)); }

// ---------------------------------------------------------------------------
// La glibc, à la ligne près
// ---------------------------------------------------------------------------
// random_r() : *fptr += *rptr (sur int32, avec débordement silencieux), puis
// la sortie vaut le mot obtenu décalé d'un bit — trente et un bits utiles.
// Le bit de poids faible est jeté parce qu'il est de période 2 : c'est la
// seule raison pour laquelle la sortie n'est pas l'état.

static inline uint32_t glibc_next(gstate *st) {
    uint32_t v = (uint32_t)st->tab[st->f] + (uint32_t)st->tab[st->r];
    st->tab[st->f] = (int32_t)v;
    if (++st->f >= st->deg) st->f = 0;
    if (++st->r >= st->deg) st->r = 0;
    return v >> 1;
}

static void glibc_init(gstate *st, uint32_t seed, int deg, int sep) {
    if (seed == 0) seed = 1;
    st->deg = deg;
    int32_t word = (int32_t)seed;
    st->tab[0] = word;
    for (int i = 1; i < deg; i++) {
        // Schrage : 16807·word mod (2³¹−1) sans jamais dépasser 32 bits.
        long hi = (long)word / 127773L;
        long lo = (long)word % 127773L;
        long w = 16807L * lo - 2836L * hi;
        if (w < 0) w += MINSTD_M;
        word = (int32_t)w;
        st->tab[i] = word;
    }
    st->f = sep;
    st->r = 0;
    for (int k = deg * 10; k > 0; k--) glibc_next(st);
}

// ---------------------------------------------------------------------------
// Les vingt familles
// ---------------------------------------------------------------------------

static inline void gen_init(int g, uint64_t seed, gstate *st) {
    st->b = 0;
    switch (g) {
    case 0: st->a = (seed ^ JAVA_A) & M48; break;
    case 1: st->a = seed & 0xFFFFFFFFULL; break;
    case 2: st->a = seed & 0x7FFFFFFFULL; break;
    case 3: st->a = (seed & 0xFFFFFFFFULL) ? (seed & 0xFFFFFFFFULL) : 1; break;
    case 4: st->a = seed ? seed : 1; break;
    case 5: st->a = seed; break;
    case 6: st->a = seed; st->b = 1442695040888963407ULL; break;
    case 7: st->a = seed; break;
    case 8: { uint64_t x = seed;
        st->a = sm64(&x); st->b = sm64(&x); st->c = sm64(&x); st->d = sm64(&x); break; }
    case 9: { uint64_t x = seed; uint64_t u = sm64(&x), v = sm64(&x);
        st->a = u & 0xFFFFFFFFULL; st->b = u >> 32;
        st->c = v & 0xFFFFFFFFULL; st->d = v >> 32; break; }
    case 10: { uint64_t x = seed; st->a = sm64(&x); st->b = sm64(&x); break; }
    case 11: { uint64_t x = seed;
        st->a = sm64(&x); st->b = sm64(&x); st->c = 1ULL; st->d = 0; break; }
    case 12: glibc_init(st, (uint32_t)seed, 31, 3); break;   // rand() par défaut
    case 13: glibc_init(st, (uint32_t)seed,  7, 3); break;   // initstate 32 o
    case 14: glibc_init(st, (uint32_t)seed, 15, 1); break;   // initstate 64 o
    case 15: glibc_init(st, (uint32_t)seed, 63, 1); break;   // initstate 256 o
    case 16:                                                 // MINSTD 16807
    case 17: {                                               // MINSTD 48271
        // Convention de std::linear_congruential_engine : l'état vaut
        // graine mod m, ramené à 1 s'il est nul. Reproduire ce détail n'est
        // pas cosmétique — une touche doit rendre la graine que le programme
        // visé aurait réellement passée, pas une graine décalée qui mène au
        // même état.
        uint64_t v = seed % (uint64_t)MINSTD_M;
        st->a = v ? v : 1ULL; break;
    }
    // RANDU : l'état vaut la graine modulo 2³¹, sans la forcer impaire. Une
    // graine paire donne une suite dégénérée — mais réelle, donc à couvrir —
    // et forcer le bit de poids faible ferait rendre à une touche une graine
    // qui n'est pas celle du programme visé.
    case 18: st->a = seed & 0x7FFFFFFFULL; break;
    default: st->a = seed & 0xFFFFFFFFULL; break;            // Borland / Delphi
    }
}

static inline uint32_t gen_next(int g, gstate *st) {
    uint64_t x;
    switch (g) {
    case 0:
        st->a = (st->a * JAVA_A + JAVA_C) & M48;
        return (uint32_t)(st->a >> 16);
    case 1:
        st->a = (st->a * 214013ULL + 2531011ULL) & 0xFFFFFFFFULL;
        return (uint32_t)(st->a >> 16) & 0x7FFFu;
    case 2:
        st->a = (st->a * 1103515245ULL + 12345ULL) & 0x7FFFFFFFULL;
        return (uint32_t)st->a;
    case 3:
        x = st->a;
        x ^= (x << 13) & 0xFFFFFFFFULL; x ^= x >> 17; x ^= (x << 5) & 0xFFFFFFFFULL;
        st->a = x & 0xFFFFFFFFULL;
        return (uint32_t)st->a;
    case 4:
        x = st->a; x ^= x >> 12; x ^= x << 25; x ^= x >> 27; st->a = x;
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
    case 7:
        st->a = st->a * 6364136223846793005ULL + 1442695040888963407ULL;
        return (uint32_t)(st->a >> 32);
    case 8: {
        uint64_t r = rotl64(st->b * 5ULL, 7) * 9ULL;
        uint64_t t = st->b << 17;
        st->c ^= st->a; st->d ^= st->b; st->b ^= st->c; st->a ^= st->d;
        st->c ^= t; st->d = rotl64(st->d, 45);
        return (uint32_t)(r >> 32);
    }
    case 9: {
        uint32_t s0 = (uint32_t)st->a, s1 = (uint32_t)st->b;
        uint32_t s2 = (uint32_t)st->c, s3 = (uint32_t)st->d;
        uint32_t r = rotl32(s1 * 5u, 7) * 9u;
        uint32_t t = s1 << 9;
        s2 ^= s0; s3 ^= s1; s1 ^= s2; s0 ^= s3; s2 ^= t; s3 = rotl32(s3, 11);
        st->a = s0; st->b = s1; st->c = s2; st->d = s3;
        return r;
    }
    case 10: {
        uint64_t s0 = st->a, s1 = st->b;
        uint64_t r = s0 + s1;
        s1 ^= s0;
        st->a = rotl64(s0, 24) ^ s1 ^ (s1 << 16);
        st->b = rotl64(s1, 37);
        return (uint32_t)(r >> 32);
    }
    case 11: {
        uint64_t lo = st->a, hi = st->b;
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
        uint64_t xorshifted = nhi ^ nlo;
        unsigned rot = (unsigned)(nhi >> 58);
        uint64_t out = (xorshifted >> rot) | (xorshifted << ((-rot) & 63));
        return (uint32_t)(out >> 32);
    }
    case 12: case 13: case 14: case 15:
        return glibc_next(st);
    case 16:
        st->a = (st->a * 16807ULL) % (uint64_t)MINSTD_M;
        return (uint32_t)st->a;
    case 17:
        st->a = (st->a * 48271ULL) % (uint64_t)MINSTD_M;
        return (uint32_t)st->a;
    case 18:
        st->a = (st->a * 65539ULL) & 0x7FFFFFFFULL;
        return (uint32_t)st->a;
    default:
        st->a = (st->a * 134775813ULL + 1ULL) & 0xFFFFFFFFULL;
        return (uint32_t)st->a;
    }
}

// Bits utiles de la sortie. Le « MSVC » n'en rend que quinze ; la glibc,
// MINSTD et RANDU en rendent trente et un ; le reste, trente-deux.
static inline uint32_t gen_bits(int g) {
    if (g == 1) return 15u;
    if (g == 2) return 31u;
    if (g >= 12 && g <= 18) return 31u;
    return 32u;
}

// ---------------------------------------------------------------------------
// Le flux, en tampon paresseux : un amorçage, six lectures
// ---------------------------------------------------------------------------

typedef struct { gstate st; int g, n; uint32_t buf[BUFMAX]; } stream;

static inline void sreset(stream *S, int g, uint64_t seed) {
    S->g = g; S->n = 0; gen_init(g, seed, &S->st);
}
static inline uint32_t sget(stream *S, int i) {
    while (S->n <= i) { S->buf[S->n] = gen_next(S->g, &S->st); S->n++; }
    return S->buf[i];
}

// nextDouble() de Java, reconstitué depuis deux mots quelconques :
// les 26 bits de poids fort du premier, les 27 du second.
static inline uint64_t dword(stream *S, int i, uint32_t bits) {
    uint64_t hi = (uint64_t)(sget(S, i)     >> (bits - 26));
    uint64_t lo = (uint64_t)(sget(S, i + 1) >> (bits - 27));
    return (hi << 27) | lo;
}

// -1 : l'échantillonneur ne s'applique pas à cette famille.
static int match_s(stream *S, int s, const uint8_t *t, uint32_t bits) {
    if ((s == 4 || s == 5) && bits < 27) return -1;

    if (s == 0 || s == 1 || s == 4) {                 // tirage avec rejet
        uint64_t lo = 0, hi = 0;
        int got = 0, i = 0;
        while (got < DRAWN && i < BUFMAX - 4) {
            uint32_t n;
            if (s == 4) {
                n = (uint32_t)((dword(S, i, bits) * POOL) >> 53); i += 2;
            } else {
                uint32_t u = sget(S, i); i++;
                n = (s == 0) ? (u % POOL)
                             : (uint32_t)(((uint64_t)u * POOL) >> bits);
            }
            uint64_t bit = (n < 64) ? (1ULL << n) : (1ULL << (n - 64));
            uint64_t *w = (n < 64) ? &lo : &hi;
            if (*w & bit) continue;
            *w |= bit;
            if (n + 1 != t[got]) return 0;
            got++;
        }
        return got == DRAWN;
    }

    uint8_t arr[POOL];                                 // Fisher-Yates partiel
    for (int i = 0; i < POOL; i++) arr[i] = (uint8_t)(i + 1);
    int idx = 0;
    for (int i = 0; i < DRAWN; i++) {
        uint32_t m = (uint32_t)(POOL - i), p;
        if (s == 5) {
            p = (uint32_t)((dword(S, idx, bits) * m) >> 53); idx += 2;
        } else {
            uint32_t u = sget(S, idx); idx++;
            p = (s == 2) ? (u % m) : (uint32_t)(((uint64_t)u * m) >> bits);
        }
        int j = i + (int)p;
        uint8_t tmp = arr[i]; arr[i] = arr[j]; arr[j] = tmp;
        if (arr[i] != t[i]) return 0;
    }
    return 1;
}

// Les couples déjà balayés par sweep_order : douze familles x quatre
// échantillonneurs. Les rebalayer ne coûterait que du temps.
static inline int deja_couvert(int g, int s) { return g < 12 && s < 4; }

// ---------------------------------------------------------------------------
// Balayage
// ---------------------------------------------------------------------------

typedef struct {
    uint64_t lo, hi;
    const uint8_t *target;
    int gen;
    uint64_t hits[NSAMP], first[NSAMP];
    int na[NSAMP];
} job;

static void *worker(void *arg) {
    job *j = (job *)arg;
    stream S;
    uint32_t bits = gen_bits(j->gen);
    for (int s = 0; s < NSAMP; s++) { j->hits[s] = 0; j->first[s] = 0; j->na[s] = 0; }
    for (uint64_t seed = j->lo; seed < j->hi; seed++) {
        sreset(&S, j->gen, seed);
        for (int s = 0; s < NSAMP; s++) {
            if (deja_couvert(j->gen, s)) continue;
            int r = match_s(&S, s, j->target, bits);
            if (r < 0) { j->na[s] = 1; continue; }
            if (r) {
                if (j->hits[s] == 0) j->first[s] = seed;
                j->hits[s]++;
            }
        }
    }
    return NULL;
}

static const char *GEN_NAME[NGEN] = {
    "java.util.Random", "LCG32 MSVC", "LCG32 glibc T0", "xorshift32",
    "xorshift64*", "splitmix64", "pcg32", "LCG64 MMIX",
    "xoshiro256**", "xoshiro128**", "xoroshiro128+", "pcg64",
    "glibc rand() T3 31,3", "glibc T1 7,3", "glibc T2 15,1", "glibc T4 63,1",
    "MINSTD 16807", "MINSTD 48271", "RANDU 65539", "Borland/Delphi"
};
static const char *SAMP_NAME[NSAMP] = {
    "modulo + rejet", "multiply-shift + rejet", "Fisher-Yates modulo",
    "Fisher-Yates multiply-shift", "nextDouble + rejet", "Fisher-Yates nextDouble"
};

static void sweep(int g, uint64_t lo, uint64_t hi, const uint8_t *target,
                  int nthreads, uint64_t *hits, uint64_t *first, int *na) {
    pthread_t th[64];
    job jobs[64];
    if (nthreads > 64) nthreads = 64;
    uint64_t span = (hi - lo) / (uint64_t)nthreads + 1;
    for (int i = 0; i < nthreads; i++) {
        jobs[i].lo = lo + span * (uint64_t)i;
        jobs[i].hi = jobs[i].lo + span; if (jobs[i].hi > hi) jobs[i].hi = hi;
        if (jobs[i].lo > hi) jobs[i].lo = jobs[i].hi = hi;
        jobs[i].target = target; jobs[i].gen = g;
        pthread_create(&th[i], NULL, worker, &jobs[i]);
    }
    for (int s = 0; s < NSAMP; s++) { hits[s] = 0; first[s] = 0; na[s] = 0; }
    for (int i = 0; i < nthreads; i++) {
        pthread_join(th[i], NULL);
        for (int s = 0; s < NSAMP; s++) {
            if (jobs[i].na[s]) na[s] = 1;
            if (jobs[i].hits[s] && hits[s] == 0) first[s] = jobs[i].first[s];
            hits[s] += jobs[i].hits[s];
        }
    }
}

// Fabrique le tirage ordonné qu'une graine donnée produirait.
static int produce(int g, int s, uint64_t seed, uint8_t *out) {
    stream S; sreset(&S, g, seed);
    uint32_t bits = gen_bits(g);
    if ((s == 4 || s == 5) && bits < 27) return 0;
    if (s == 0 || s == 1 || s == 4) {
        uint64_t lo = 0, hi = 0; int got = 0, i = 0;
        while (got < DRAWN && i < BUFMAX - 4) {
            uint32_t n;
            if (s == 4) { n = (uint32_t)((dword(&S, i, bits) * POOL) >> 53); i += 2; }
            else {
                uint32_t u = sget(&S, i); i++;
                n = (s == 0) ? (u % POOL) : (uint32_t)(((uint64_t)u * POOL) >> bits);
            }
            uint64_t bit = (n < 64) ? (1ULL << n) : (1ULL << (n - 64));
            uint64_t *w = (n < 64) ? &lo : &hi;
            if (*w & bit) continue;
            *w |= bit; out[got++] = (uint8_t)(n + 1);
        }
        return got == DRAWN;
    }
    uint8_t arr[POOL];
    for (int i = 0; i < POOL; i++) arr[i] = (uint8_t)(i + 1);
    int idx = 0;
    for (int i = 0; i < DRAWN; i++) {
        uint32_t m = (uint32_t)(POOL - i), p;
        if (s == 5) { p = (uint32_t)((dword(&S, idx, bits) * m) >> 53); idx += 2; }
        else {
            uint32_t u = sget(&S, idx); idx++;
            p = (s == 2) ? (u % m) : (uint32_t)(((uint64_t)u * m) >> bits);
        }
        int j = i + (int)p;
        uint8_t t = arr[i]; arr[i] = arr[j]; arr[j] = t;
        out[i] = arr[i];
    }
    return 1;
}

int main(int argc, char **argv) {
    int nthreads = 4;
    const char *env = getenv("SWEEP_THREADS");
    if (env) { nthreads = atoi(env); if (nthreads < 1) nthreads = 1; }

    if (argc == 2 && !strcmp(argv[1], "--selftest")) {
        const uint64_t WIT = 1234567ULL, HI = 3000000ULL;
        printf("AUTOTEST — graine témoin %llu dans [0, %llu)\n\n",
               (unsigned long long)WIT, (unsigned long long)HI);
        printf("%-22s %-28s %-10s %s\n",
               "générateur", "échantillonneur", "retrouvée", "graines compatibles");
        int ok = 0, tot = 0;
        for (int g = 0; g < NGEN; g++) {
            for (int s = 0; s < NSAMP; s++) {
                if (deja_couvert(g, s)) continue;
                uint8_t tgt[DRAWN];
                if (!produce(g, s, WIT, tgt)) {
                    printf("%-22s %-28s %-10s —\n",
                           GEN_NAME[g], SAMP_NAME[s], "n/a");
                    continue;
                }
                uint64_t hits[NSAMP], first[NSAMP]; int na[NSAMP];
                sweep(g, 0, HI, tgt, nthreads, hits, first, na);
                // Le critère n'est pas « la première touche est le témoin » :
                // plusieurs familles ont un espace d'états plus PETIT que la
                // plage de graines (RANDU et glibc T0 vivent modulo 2³¹,
                // MINSTD modulo 2³¹−1), si bien que deux graines distinctes
                // mènent au même état et sont toutes deux compatibles. Exiger
                // la première ferait échouer un balayage pourtant exact. La
                // seule question qui compte est : le témoin SURVIT-IL ?
                uint64_t hw[NSAMP], fw[NSAMP]; int naw[NSAMP];
                sweep(g, WIT, WIT + 1, tgt, 1, hw, fw, naw);
                tot++;
                int found = hw[s] == 1;
                ok += found;
                const char *note = !found ? ""
                                 : (hits[s] == 1 ? "   = témoin seul"
                                                 : "   dont le témoin (états alias)");
                printf("%-22s %-28s %-10s %llu%s\n", GEN_NAME[g], SAMP_NAME[s],
                       found ? "OUI" : "NON", (unsigned long long)hits[s], note);
            }
        }
        printf("\n%d/%d combinaisons retrouvent leur témoin.\n", ok, tot);
        return ok == tot ? 0 : 1;
    }

    if (argc != 3 + DRAWN) {
        fprintf(stderr,
            "usage: %s <lo> <hi> <o1> ... <o20>   (ordre de sortie)\n"
            "       %s --selftest\n", argv[0], argv[0]);
        return 2;
    }
    uint64_t lo = strtoull(argv[1], NULL, 10);
    uint64_t hi = strtoull(argv[2], NULL, 10);
    uint8_t target[DRAWN];
    for (int i = 0; i < DRAWN; i++) target[i] = (uint8_t)atoi(argv[3 + i]);

    printf("plage [%llu, %llu) — %d fils — filtre : ORDRE des vingt numéros\n",
           (unsigned long long)lo, (unsigned long long)hi, nthreads);
    printf("%-22s %-28s %s\n", "générateur", "échantillonneur", "graines compatibles");
    uint64_t total = 0;
    for (int g = 0; g < NGEN; g++) {
        uint64_t hits[NSAMP], first[NSAMP]; int na[NSAMP];
        sweep(g, lo, hi, target, nthreads, hits, first, na);
        for (int s = 0; s < NSAMP; s++) {
            if (deja_couvert(g, s)) {
                printf("%-22s %-28s déjà couvert (sweep_order)\n",
                       GEN_NAME[g], SAMP_NAME[s]);
                continue;
            }
            if (na[s]) {
                printf("%-22s %-28s sans objet (< 27 bits)\n",
                       GEN_NAME[g], SAMP_NAME[s]);
                continue;
            }
            total += hits[s];
            if (hits[s])
                printf("%-22s %-28s %llu   PREMIÈRE = %llu\n", GEN_NAME[g],
                       SAMP_NAME[s], (unsigned long long)hits[s],
                       (unsigned long long)first[s]);
            else
                printf("%-22s %-28s 0\n", GEN_NAME[g], SAMP_NAME[s]);
        }
        fflush(stdout);
    }
    printf("\ntotal : %llu graine(s) compatible(s)\n", (unsigned long long)total);
    return 0;
}
