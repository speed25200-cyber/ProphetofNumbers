/* sweep_time.c — la graine que personne n'a essayee : celle qu'on CONNAIT.
 *
 * Ce que tous les autres balayages du dossier font
 * -------------------------------------------------
 * sweep48, sweep_mt, sweep_order, sweep_modern, sweep_java48 enumerent un
 * espace de graines INCONNUES : 2^48 etats, 20,9 jours par coeur, jamais
 * mene a terme faute de GPU. Ils supposent que la graine est un secret.
 *
 * Ce que celui-ci fait
 * --------------------
 * Il suppose le contraire, et c'est le mode de defaillance le plus courant
 * des vrais systemes : la graine derive de l'HORLOGE ou d'un COMPTEUR.
 * srand(time(NULL)) est l'erreur la plus repandue de tout le logiciel.
 *
 * L'archive donne les deux quantites en clair :
 *   - le numero de tirage, strictement consecutif de 1 309 614 a 1 380 173 ;
 *   - l'horodatage unix, sur une grille exacte de 300 s (70 548 / 70 560).
 *
 * L'espace de recherche passe donc de 2^48 a quelques dizaines de graines
 * PAR TIRAGE. Ce qui demandait 21 jours-coeur tient en une minute.
 *
 * Ce qu'il mesure
 * ---------------
 * Non pas une correspondance binaire, mais le RECOUVREMENT maximal entre le
 * tirage engendre et le tirage reel, sur tout le produit
 * (tirage x convention de graine x decalage x famille x echantillonneur).
 * Un recouvrement de 20/20 serait une reproduction exacte ; mais 16 ou 18
 * signalerait deja une famille correcte avec une convention legerement
 * fausse, et le chercher ne coute rien de plus.
 *
 * Sous H0 le recouvrement suit une hypergeometrique(80, 20, 20) : moyenne 5,
 * ecart-type 1,76. La loi du MAXIMUM sur T essais est calculee a part, en
 * Python, et c'est elle qui fait foi — jamais un seuil tabule.
 *
 * Compilation :  cc -O3 -march=native -o sweep_time sweep_time.c
 * Usage       :  ./sweep_time draws.txt [n] [L] [W] [--sessions]
 *
 *   L  longueur de CHAINE : apres un seul amorcage, on engendre L tirages
 *      consecutifs et on somme les recouvrements. L=1 (defaut) teste le
 *      re-amorcage a chaque tirage ; L>1 teste le re-amorcage suivi d'une
 *      COURSE CONTINUE — le regime d'un systeme qui demarre le matin et
 *      tourne toute la journee, qu'aucun balayage du dossier ne couvre.
 *   W  demi-largeur du decalage sur la graine (defaut 3).
 *   --sessions  ne tente d'amorcer qu'aux DEBUTS DE SESSION (ecart > 1000 s
 *      avec le tirage precedent). L'archive en compte 345, tous a 04:05:00
 *      UTC pile.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#define POOL 80
#define DRAWN 20

/* ------------------------------------------------------------------ */
/* Les familles. Chacune expose un etat et un next32().                */
/* ------------------------------------------------------------------ */

typedef struct { uint64_t s; } java_t;      /* java.util.Random          */
typedef struct { uint32_t r[344]; int k; } glibc_t;  /* random() TYPE_3  */
typedef struct { uint32_t mt[624]; int i; } mt_t;    /* MT19937          */
typedef struct { uint32_t s; } lcg32_t;     /* MSVC, NR, minstd         */
typedef struct { uint64_t s; } sm64_t;      /* splitmix64               */

static void java_init(java_t *g, uint64_t seed) {
    g->s = (seed ^ 0x5DEECE66DULL) & ((1ULL << 48) - 1);
}
static uint32_t java_next(java_t *g, int bits) {
    g->s = (g->s * 0x5DEECE66DULL + 0xBULL) & ((1ULL << 48) - 1);
    return (uint32_t)(g->s >> (48 - bits));
}
static uint32_t java_next32(void *v) { return java_next((java_t *)v, 32); }
/* nextInt(bound) exact de java.util.Random, borne non puissance de deux */
static uint32_t java_below(void *v, uint32_t n) {
    java_t *g = (java_t *)v;
    if ((n & (n - 1)) == 0) return (uint32_t)(((uint64_t)n * java_next(g, 31)) >> 31);
    uint32_t bits, val;
    do { bits = java_next(g, 31); val = bits % n; }
    while ((int32_t)(bits - val + (n - 1)) < 0);
    return val;
}

static void glibc_init(glibc_t *g, uint32_t seed) {
    if (seed == 0) seed = 1;
    g->r[0] = seed;
    for (int i = 1; i < 31; i++) {
        int32_t prev = (int32_t)g->r[i - 1];
        int32_t hi = prev / 127773, lo = prev % 127773;
        int32_t w = 16807 * lo - 2836 * hi;
        if (w < 0) w += 2147483647;
        g->r[i] = (uint32_t)w;
    }
    for (int i = 31; i < 34; i++) g->r[i] = g->r[i - 31];
    for (int i = 34; i < 344; i++) g->r[i] = g->r[i - 31] + g->r[i - 3];
    g->k = 344;
}
static uint32_t glibc_next32(void *v) {
    glibc_t *g = (glibc_t *)v;
    int k = g->k;
    uint32_t x = g->r[(k - 31) % 344] + g->r[(k - 3) % 344];
    g->r[k % 344] = x;
    g->k = k + 1;
    return x >> 1;                      /* random() rend 31 bits */
}

static void mt_init(mt_t *g, uint32_t seed) {
    g->mt[0] = seed;
    for (int i = 1; i < 624; i++)
        g->mt[i] = 1812433253U * (g->mt[i - 1] ^ (g->mt[i - 1] >> 30)) + (uint32_t)i;
    g->i = 624;
}
static uint32_t mt_next32(void *v) {
    mt_t *g = (mt_t *)v;
    if (g->i >= 624) {
        for (int i = 0; i < 624; i++) {
            uint32_t y = (g->mt[i] & 0x80000000U) | (g->mt[(i + 1) % 624] & 0x7fffffffU);
            g->mt[i] = g->mt[(i + 397) % 624] ^ (y >> 1) ^ ((y & 1) ? 0x9908b0dfU : 0);
        }
        g->i = 0;
    }
    uint32_t y = g->mt[g->i++];
    y ^= y >> 11; y ^= (y << 7) & 0x9d2c5680U;
    y ^= (y << 15) & 0xefc60000U; y ^= y >> 18;
    return y;
}

static uint32_t A_MUL, A_ADD, A_SHIFT;   /* parametres du LCG 32 courant */
static uint32_t lcg_next32(void *v) {
    lcg32_t *g = (lcg32_t *)v;
    g->s = g->s * A_MUL + A_ADD;
    return A_SHIFT ? ((g->s >> A_SHIFT) & 0x7fff) : g->s;
}
static uint32_t minstd_next32(void *v) {
    lcg32_t *g = (lcg32_t *)v;
    g->s = (uint32_t)(((uint64_t)g->s * 16807ULL) % 2147483647ULL);
    return g->s;
}
static uint32_t sm64_next32(void *v) {
    sm64_t *g = (sm64_t *)v;
    uint64_t z = (g->s += 0x9E3779B97F4A7C15ULL);
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return (uint32_t)((z ^ (z >> 31)) >> 32);
}

/* ------------------------------------------------------------------ */
/* Les echantillonneurs : 20 numeros sur 80, a partir d'un next32().    */
/* ------------------------------------------------------------------ */

typedef uint32_t (*next_fn)(void *);
typedef uint32_t (*below_fn)(void *, uint32_t);

static uint32_t below_mod(void *g, uint32_t n, next_fn nx) { return nx(g) % n; }

/* Fisher-Yates partiel : a[i..] , on prend les 20 premiers. */
static int samp_fy_partial(void *g, next_fn nx, below_fn bl, uint8_t *out) {
    uint8_t a[POOL];
    for (int i = 0; i < POOL; i++) a[i] = (uint8_t)(i + 1);
    for (int i = 0; i < DRAWN; i++) {
        uint32_t j = bl ? i + bl(g, POOL - i) : i + below_mod(g, POOL - i, nx);
        uint8_t t = a[i]; a[i] = a[j]; a[j] = t;
        out[i] = a[i];
    }
    return 1;
}
/* Fisher-Yates descendant complet, puis les 20 premiers. */
static int samp_fy_full(void *g, next_fn nx, below_fn bl, uint8_t *out) {
    uint8_t a[POOL];
    for (int i = 0; i < POOL; i++) a[i] = (uint8_t)(i + 1);
    for (int i = POOL - 1; i > 0; i--) {
        uint32_t j = bl ? bl(g, i + 1) : below_mod(g, i + 1, nx);
        uint8_t t = a[i]; a[i] = a[j]; a[j] = t;
    }
    for (int i = 0; i < DRAWN; i++) out[i] = a[i];
    return 1;
}
/* Rejet par modulo, doublons ignores. */
static int samp_reject_mod(void *g, next_fn nx, below_fn bl, uint8_t *out) {
    uint8_t seen[POOL + 1]; memset(seen, 0, sizeof seen);
    int n = 0, guard = 0;
    while (n < DRAWN && guard++ < 4000) {
        uint32_t v = (bl ? bl(g, POOL) : below_mod(g, POOL, nx)) + 1;
        if (!seen[v]) { seen[v] = 1; out[n++] = (uint8_t)v; }
    }
    return n == DRAWN;          /* un tirage incomplet est REJETE, pas bourre */
}
/* Rejet par flottant : floor(u * 80) + 1. */
static int samp_reject_float(void *g, next_fn nx, below_fn bl, uint8_t *out) {
    (void)bl;
    uint8_t seen[POOL + 1]; memset(seen, 0, sizeof seen);
    int n = 0, guard = 0;
    while (n < DRAWN && guard++ < 4000) {
        uint32_t v = (uint32_t)((double)nx(g) / 4294967296.0 * POOL) + 1;
        if (v > POOL) v = POOL;
        if (!seen[v]) { seen[v] = 1; out[n++] = (uint8_t)v; }
    }
    return n == DRAWN;
}

typedef int (*samp_fn)(void *, next_fn, below_fn, uint8_t *);
static const char *SAMP_NAME[4] = {"fy_partiel", "fy_complet", "rejet_mod", "rejet_flot"};
static samp_fn SAMP[4] = {samp_fy_partial, samp_fy_full, samp_reject_mod, samp_reject_float};

/* ------------------------------------------------------------------ */

#define NFAM 8
static const char *FAM_NAME[NFAM] = {
    "java.util.Random", "glibc random()", "MT19937", "MSVC rand()",
    "NumRecipes LCG", "minstd 16807", "splitmix64", "glibc LCG 2^31"
};

/* Prepare l'etat de la famille f pour la graine s ; rend le pointeur. */
static void *fam_init(int f, uint64_t s, java_t *j, glibc_t *gl, mt_t *m,
                      lcg32_t *l, sm64_t *sm, next_fn *nx, below_fn *bl) {
    *bl = NULL;
    switch (f) {
    case 0: java_init(j, s);  *nx = java_next32; *bl = java_below; return j;
    case 1: glibc_init(gl, (uint32_t)s); *nx = glibc_next32; return gl;
    case 2: mt_init(m, (uint32_t)s); *nx = mt_next32; return m;
    case 3: l->s = (uint32_t)s; A_MUL = 214013U;    A_ADD = 2531011U;   A_SHIFT = 16; *nx = lcg_next32; return l;
    case 4: l->s = (uint32_t)s; A_MUL = 1664525U;   A_ADD = 1013904223U; A_SHIFT = 0; *nx = lcg_next32; return l;
    case 5: l->s = (uint32_t)(s % 2147483646ULL) + 1; *nx = minstd_next32; return l;
    case 6: sm->s = s; *nx = sm64_next32; return sm;
    default: l->s = (uint32_t)s; A_MUL = 1103515245U; A_ADD = 12345U;  A_SHIFT = 0; *nx = lcg_next32; return l;
    }
}

#define NCONV 6
static const char *CONV_NAME[NCONV] = {
    "ts+d", "id+d", "ts/300+d", "(ts^id)+d", "(ts+id)+d", "ts*1000+d"
};
static uint64_t conv_seed(int c, uint64_t ts, uint64_t id, int64_t d) {
    switch (c) {
    case 0: return ts + d;
    case 1: return id + d;
    case 2: return ts / 300 + d;
    case 3: return (ts ^ id) + d;
    case 4: return (ts + id) + d;
    default: return ts * 1000ULL + d;
    }
}

int main(int argc, char **argv) {
    if (argc < 2) { fprintf(stderr, "usage: %s draws.txt [n]\n", argv[0]); return 1; }
    FILE *fh = fopen(argv[1], "r");
    if (!fh) { perror("fopen"); return 1; }
    int want = (argc > 2) ? atoi(argv[2]) : 1 << 30;
    int L = (argc > 3) ? atoi(argv[3]) : 1;
    int W = (argc > 4) ? atoi(argv[4]) : 3;
    int only_sessions = 0;
    for (int i = 1; i < argc; i++)
        if (!strcmp(argv[i], "--sessions")) only_sessions = 1;
    if (L < 1) L = 1;

    static uint64_t ids[80000], tss[80000];
    static uint8_t seen_t[80000][POOL + 1];
    int n = 0;
    while (n < want && n < 80000) {
        uint64_t id, ts; int v[DRAWN];
        int got = fscanf(fh, "%llu %llu", (unsigned long long *)&id, (unsigned long long *)&ts);
        if (got != 2) break;
        for (int i = 0; i < DRAWN; i++) if (fscanf(fh, "%d", &v[i]) != 1) { got = 0; break; }
        if (!got) break;
        ids[n] = id; tss[n] = ts;
        memset(seen_t[n], 0, POOL + 1);
        for (int i = 0; i < DRAWN; i++) seen_t[n][v[i]] = 1;
        n++;
    }
    fclose(fh);
    fprintf(stderr, "%d tirages lus\n", n);

    /* Points d'amorcage : tous les tirages, ou les seuls debuts de session. */
    static int anchors[80000]; int na = 0;
    for (int t = 0; t + L <= n; t++) {
        if (only_sessions && t > 0 && (int64_t)tss[t] - (int64_t)tss[t - 1] <= 1000) continue;
        anchors[na++] = t;
    }
    fprintf(stderr, "L=%d  W=%d  points d'amorcage : %d\n", L, W, na);

    int best = -1, bf = 0, bs = 0, bc = 0; int64_t bd = 0; int bdraw = 0;
    long long trials = 0, rejected = 0;
    int HMAX = DRAWN * L;
    static long long hist[DRAWN * 16 + 1];
    memset(hist, 0, sizeof hist);

    java_t j; glibc_t gl; mt_t m; lcg32_t l; sm64_t sm;
    next_fn nx; below_fn bl; uint8_t out[DRAWN];

    for (int ai = 0; ai < na; ai++) {
        int t = anchors[ai];
        for (int c = 0; c < NCONV; c++) {
            for (int64_t d = -W; d <= W; d++) {
                uint64_t s = conv_seed(c, tss[t], ids[t], d);
                for (int f = 0; f < NFAM; f++) {
                    for (int sp = 0; sp < 4; sp++) {
                        void *g = fam_init(f, s, &j, &gl, &m, &l, &sm, &nx, &bl);
                        /* UN SEUL amorcage, puis L tirages consecutifs tires
                         * de l'etat qui CONTINUE — c'est ce qui distingue ce
                         * regime du re-amorcage par tirage. */
                        int ov = 0, bad = 0;
                        for (int step = 0; step < L; step++) {
                            if (!SAMP[sp](g, nx, bl, out)) { bad = 1; break; }
                            /* intersection d'ENSEMBLES : un doublon dans `out`
                             * ne doit pas compter deux fois. C'est le defaut
                             * qu'a revele le temoin positif (4 264 succes au
                             * lieu de 400). */
                            uint8_t used[POOL + 1]; memset(used, 0, sizeof used);
                            for (int i = 0; i < DRAWN; i++) {
                                uint8_t v = out[i];
                                if (v >= 1 && v <= POOL && !used[v]) {
                                    used[v] = 1;
                                    if (seen_t[t + step][v]) ov++;
                                }
                            }
                        }
                        if (bad) { rejected++; continue; }
                        hist[ov]++; trials++;
                        if (ov > best) {
                            best = ov; bf = f; bs = sp; bc = c; bd = d; bdraw = t;
                            fprintf(stderr, "  nouveau max %2d  %s / %s / %s d=%+lld  tirage %llu\n",
                                    ov, FAM_NAME[f], SAMP_NAME[sp], CONV_NAME[c],
                                    (long long)d, (unsigned long long)ids[t]);
                        }
                    }
                }
            }
        }
    }

    printf("essais %lld  (rejetes %lld)  L %d  W %d  ancres %d\n",
           trials, rejected, L, W, na);
    printf("max %d  famille %s  echantillonneur %s  convention %s  d %+lld  tirage %llu\n",
           best, FAM_NAME[bf], SAMP_NAME[bs], CONV_NAME[bc], (long long)bd,
           (unsigned long long)ids[bdraw]);
    for (int k = 0; k <= HMAX; k++) if (hist[k]) printf("hist %d %lld\n", k, hist[k]);
    return 0;
}
