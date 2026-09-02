/* lfg_beam_mod4 — h149 : la synchronisation sous le rejet par le canal MOD 4 (deux bits par
 * mot au lieu d'un), avec ou sans JUMEAU entrelace.  THEORIE_ETAT §7.21.
 *
 * Le numero publie donne v - 1 = x mod 80, donc x mod 4 : DEUX bits du mot (80 = 4 . 20, chaque
 * classe mod 4 contient exactement 20 des quatre-vingts numeros).  Le §7.17 n'en lisait qu'un
 * (la parite) parce que l'etat cache du plan 0 seul est une m-suite de 2^L - 1 positions ; lire
 * x mod 4 demande le couple (plan 0, plan 1) — les orbites du Fibonacci mod 4, N = (2^L-1) 2^L —
 * et, pour la sortie decalee de la glibc (x = r >> 1), le triplet (plans 0, 1, 2) mod 8.
 *
 *   P(A, n | fenetre) = [prod_{c != c*} F20(w_c, a_c)] . G20(w_{c*}, a_{c*})
 *   F20(w, a) = a! S(w, a) / 20^w,   G20(w, a) = a! S(w-1, a-1) / 20^w
 * (w_c = nombre de mots de classe c dans la fenetre, c* = classe du dernier mot, a_c = nombre de
 * numeros tires de classe c).  Normalisation verifiee a 1e-9.  Debit mesure : 5,37 bits par
 * tirage contre 1,31 pour la parite.
 *
 * JUMEAU (option) : le meme generateur sert, entre deux de nos tirages, un AUTRE tirage du meme
 * jeu — n' mots de loi P0(n') (loi exacte du §7.17, entropie 2,85 bits).  La transition devient
 * une convolution :  alpha_t(p) = sum_{n'} P0(n') beta_t(p - n'),  beta_t(p) = sum_n W(p-n, n)
 * alpha_{t-1}(p-n).  Le canal de parite y perdrait 1,54 bit par tirage ; celui-ci gagne 2,53.
 *
 * usage : lfg_beam_mod4 K L shift(0|1) jumeau(0|1) f_ac f_blocs mode(flux|nuit) m B1 m2 B2
 *                       [pas_journal] [saut]
 *   f_ac : quatre entiers par ligne (a_0 a_1 a_2 a_3, somme 20), un tirage par ligne.
 * sortie : "T t log2bf max tmax", "BLOC b t0 n log2bf max", "PIC seq q masse",
 *          "FIN nseq Pi N nt log2bf max tmax bmax nblocs maxcum nmort nred sec".
 */
#include <immintrin.h>
#include <math.h>
#include <omp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define POOL 80
#define DRAWN 20
#define PAR 20                 /* numeros par classe mod 4 */
#define NMIN 20
#define NMAX 40
#define NW (NMAX + 1)
#define NN (NMAX - NMIN + 1)
#define MMAX 64
#define CL 4

static float F20[NW][DRAWN + 1];        /* C(80,20)^(1/1) . a! S(w,a) / 20^w  (echelle a part) */
static float R20[NW][DRAWN + 1];        /* G20 / F20 */
static double LOG2_C8020;

static void tables(void)
{
    static long double S[NW][DRAWN + 1];
    memset(S, 0, sizeof S);
    S[0][0] = 1;
    for (int w = 1; w < NW; w++)
        for (int a = 1; a <= DRAWN; a++)
            S[w][a] = a * S[w - 1][a] + S[w - 1][a - 1];
    long double fact[DRAWN + 1];
    fact[0] = 1;
    for (int a = 1; a <= DRAWN; a++) fact[a] = fact[a - 1] * a;
    long double pw[NW];
    pw[0] = 1;
    for (int w = 1; w < NW; w++) pw[w] = pw[w - 1] * PAR;
    long double c = 1;
    for (int i = 0; i < DRAWN; i++) c = c * (POOL - i) / (i + 1);
    LOG2_C8020 = (double)log2l(c);
    /* l'echelle C(80,20) est portee par la table F de la classe 0 (une fois par tirage) */
    for (int w = 0; w < NW; w++)
        for (int a = 0; a <= DRAWN; a++) {
            long double f = (w < a || (a == 0 && w > 0)) ? 0.0L : fact[a] * S[w][a] / pw[w];
            long double g = (a == 0 || w < a) ? 0.0L : fact[a] * S[w - 1][a - 1] / pw[w];
            F20[w][a] = (float)f;
            R20[w][a] = (float)(g > 0 ? g / f : 0.0L);
        }
}

/* ---- les sequences : deux bits (classe mod 4) par position ------------------- */

static uint64_t *CLS;          /* NSEQ segments de STRIDE mots ; 32 classes par mot */
static size_t STRIDE;
static uint32_t Pi, NSEQ;
static double LOG2_N;

static inline int getcl(const uint64_t *b, uint32_t q)
{
    return (int)((b[q >> 5] >> (2 * (q & 31))) & 3);
}

static inline void metcl(uint64_t *seg, uint32_t i, int v)
{
    seg[i >> 5] |= (uint64_t)v << (2 * (i & 31));
}

/* les 40 classes qui precedent q, deux bits chacune (bit 2j = classe de q-1-j) */
static inline __uint128_t win40(const uint64_t *b, uint32_t q)
{
    __uint128_t v = 0;
    for (int j = 0; j < NMAX; j++)
        v |= (__uint128_t)getcl(b, (uint32_t)(((uint64_t)q + Pi - 1 - j) % Pi)) << (2 * j);
    return v;
}

static void alloue(uint32_t pi, uint32_t nseq)
{
    Pi = pi;
    NSEQ = nseq;
    STRIDE = (size_t)(pi + 256) / 32 + 4;
    CLS = calloc((size_t)nseq * STRIDE, 8);
    if (!CLS) { fprintf(stderr, "memoire (%.2f Go)\n", (double)nseq * STRIDE * 8 / 1e9); exit(2); }
    LOG2_N = log2((double)nseq * pi);
}

static void replie(uint64_t *seg)
{
    for (uint32_t i = 0; i < 256; i++) metcl(seg, Pi + i, getcl(seg, i % Pi));
}

/* shift 0 : classes (plan 1, plan 0) du Fibonacci mod 4, plan 0 non nul :
 * 2^(L-1) orbites de periode 2P.  Representants : plan 0 canonique, plan 1 apparie. */
static void orbites_mod4(int K, int L)
{
    uint32_t P = (1U << L) - 1;
    alloue(2 * P, 1U << (L - 1));
    uint64_t msk = (1ULL << L) - 1;
    unsigned char *vu = calloc(1ULL << L, 1);
    uint32_t no = 0;
    for (uint32_t c0 = 0; c0 < (1U << L); c0++) {
        if (vu[c0]) continue;
        vu[c0] = 1;
        if (no >= NSEQ) { fprintf(stderr, "trop d'orbites\n"); exit(2); }
        uint64_t R0 = 1, R1 = c0;
        uint64_t *seg = CLS + (size_t)no * STRIDE;
        for (uint32_t i = 0; i < 2 * P; i++) {
            uint64_t x0 = (R0 >> (K - 1)) & 1, y0 = (R0 >> (L - 1)) & 1;
            uint64_t x1 = (R1 >> (K - 1)) & 1, y1 = (R1 >> (L - 1)) & 1;
            uint64_t b = x0 ^ y0, cc = x1 ^ y1 ^ (x0 & y0);
            metcl(seg, i, (int)(b | (cc << 1)));            /* classe = plan0 + 2 plan1 */
            R0 = (R0 << 1) | b;
            R1 = (R1 << 1) | cc;
            if (i + 1 == P) {
                uint32_t part = (uint32_t)(R1 & msk);
                if ((R0 & msk) != 1 || part == c0) { fprintf(stderr, "periode\n"); exit(2); }
                vu[part] = 1;
            }
        }
        if ((R1 & msk) != c0 || (R0 & msk) != 1) { fprintf(stderr, "periode 2P fausse\n"); exit(2); }
        replie(seg);
        no++;
    }
    if (no != NSEQ) { fprintf(stderr, "%u orbites, %u attendues\n", no, NSEQ); exit(2); }
    free(vu);
}

/* shift 1 : x = r >> 1, classes (plan 2, plan 1) du Fibonacci mod 8, plan 0 non nul :
 * periode 4P, 2^(2L-2) orbites.  Representants : plan 0 canonique, les 2^(2L) couples
 * (plan 1, plan 2) se groupant par quatre. */
static void orbites_mod8(int K, int L)
{
    uint32_t P = (1U << L) - 1;
    alloue(4 * P, 1U << (2 * L - 2));
    uint64_t msk = (1ULL << L) - 1;
    size_t nvu = (size_t)1 << (2 * L);
    unsigned char *vu = calloc(nvu, 1);
    if (!vu) { fprintf(stderr, "memoire (vu)\n"); exit(2); }
    uint32_t no = 0;
    for (size_t cc0 = 0; cc0 < nvu; cc0++) {
        if (vu[cc0]) continue;
        vu[cc0] = 1;
        if (no >= NSEQ) { fprintf(stderr, "trop d'orbites\n"); exit(2); }
        uint64_t R0 = 1, R1 = cc0 & msk, R2 = (cc0 >> L) & msk;
        uint64_t *seg = CLS + (size_t)no * STRIDE;
        for (uint32_t i = 0; i < 4 * P; i++) {
            uint64_t x0 = (R0 >> (K - 1)) & 1, y0 = (R0 >> (L - 1)) & 1;
            uint64_t x1 = (R1 >> (K - 1)) & 1, y1 = (R1 >> (L - 1)) & 1;
            uint64_t x2 = (R2 >> (K - 1)) & 1, y2 = (R2 >> (L - 1)) & 1;
            uint64_t b = x0 ^ y0;
            uint64_t r1 = x0 & y0;                       /* retenue vers le plan 1 */
            uint64_t c1 = x1 ^ y1 ^ r1;
            uint64_t r2 = (x1 & y1) | (r1 & (x1 ^ y1));  /* retenue vers le plan 2 */
            uint64_t c2 = x2 ^ y2 ^ r2;
            metcl(seg, i, (int)(c1 | (c2 << 1)));        /* x = r >> 1 : bits 1 et 2 de r */
            R0 = (R0 << 1) | b;
            R1 = (R1 << 1) | c1;
            R2 = (R2 << 1) | c2;
            if ((i + 1) % P == 0 && i + 1 < 4 * P) {
                size_t part = (size_t)(R1 & msk) | ((size_t)(R2 & msk) << L);
                if ((R0 & msk) != 1) { fprintf(stderr, "plan 0 : periode != P\n"); exit(2); }
                vu[part] = 1;
            }
        }
        if (((R1 & msk) | ((R2 & msk) << L)) != cc0 || (R0 & msk) != 1) {
            fprintf(stderr, "periode 4P fausse\n");
            exit(2);
        }
        replie(seg);
        no++;
    }
    if (no != NSEQ) { fprintf(stderr, "%u orbites, %u attendues\n", no, NSEQ); exit(2); }
    free(vu);
}

/* ---- selection des B meilleures ---------------------------------------------- */

typedef struct { float v; uint32_t s, q; } Cand;
typedef struct { Cand *c; long n, cap, B; float seuil; } Sel;

static int cmp_cand(const void *a, const void *b)
{
    float x = ((const Cand *)a)->v, y = ((const Cand *)b)->v;
    return x < y ? 1 : (x > y ? -1 : 0);
}

static void sel_reduit(Sel *s)
{
    qsort(s->c, (size_t)s->n, sizeof(Cand), cmp_cand);
    if (s->n > s->B) s->n = s->B;
    if (s->n == s->B) s->seuil = s->c[s->n - 1].v;
}

static inline void sel_push(Sel *s, float v, uint32_t sq, uint32_t q)
{
    if (!(v > s->seuil)) return;
    s->c[s->n].v = v;
    s->c[s->n].s = sq;
    s->c[s->n].q = q;
    if (++s->n == s->cap) sel_reduit(s);
}

/* ---- phase A : m tirages pleins, un passage en flot -------------------------- */

/* MTF[c][w][j] = F20(w, a_c^{(t+j)}) (la classe 0 porte l'echelle C(80,20)) ;
 * MTR[c][w][j] = R20(w, a_c^{(t+j)}) ; PJ[n'][j] = P0(n') (jumeau) ou 0. */
__attribute__((always_inline))
static inline void flot_nv(uint32_t sq, uint32_t q0, uint32_t q1, int m, const float *__restrict MTF,
                           const float *__restrict MTR, const float *__restrict PJ, int jumeau,
                           double *S, Sel *sel, const int NV)
{
    const int mp = 8 * NV, rs = mp + 8;
    const uint64_t *seg = CLS + (size_t)sq * STRIDE;
    uint32_t PRO = (uint32_t)(jumeau ? 2 * NMAX : NMAX) * (uint32_t)m;
    _MM_SET_FLUSH_ZERO_MODE(_MM_FLUSH_ZERO_ON);
    _MM_SET_DENORMALS_ZERO_MODE(_MM_DENORMALS_ZERO_ON);
    float *bufa = aligned_alloc(64, (size_t)256 * rs * sizeof(float));   /* alpha_0..alpha_{m-1} */
    float *bufb = aligned_alloc(64, (size_t)256 * rs * sizeof(float));   /* beta_1..beta_m */
    float *sv = aligned_alloc(64, (size_t)mp * sizeof(float));
    float *acc = aligned_alloc(64, (size_t)mp * sizeof(float));
    double *loc = calloc((size_t)mp, sizeof(double));
    memset(bufa, 0, (size_t)256 * rs * sizeof(float));
    memset(bufb, 0, (size_t)256 * rs * sizeof(float));
    memset(sv, 0, (size_t)mp * sizeof(float));
    for (int i = 0; i < 256; i++) bufa[(size_t)i * rs] = 1.0f;           /* alpha_0 = 1 */
    uint32_t p = (uint32_t)(((uint64_t)q0 + (uint64_t)Pi * 2 - PRO % Pi) % Pi);
    __uint128_t V = win40(seg, p);
    uint64_t total = (uint64_t)PRO + (q1 - q0);
    int nflush = 0;
    for (uint64_t k = 0; k < total; k++) {
        int cs = (int)(V & 3);                     /* classe du dernier mot de la fenetre */
        int w[CL] = {0, 0, 0, 0};
        for (int j = 0; j < NMIN; j++) w[(int)((V >> (2 * j)) & 3)]++;
        __m256 A[8];
        for (int u = 0; u < NV; u++) A[u] = _mm256_setzero_ps();
        for (int n = NMIN; n <= NMAX; n++) {
            if (n > NMIN) w[(int)((V >> (2 * (n - 1))) & 3)]++;
            const float *f0 = MTF + ((size_t)0 * NW + w[0]) * mp;
            const float *f1 = MTF + ((size_t)1 * NW + w[1]) * mp;
            const float *f2 = MTF + ((size_t)2 * NW + w[2]) * mp;
            const float *f3 = MTF + ((size_t)3 * NW + w[3]) * mp;
            const float *r = MTR + ((size_t)cs * NW + w[cs]) * mp;
            const float *a = bufa + (size_t)((k - (uint64_t)n) & 255) * rs;
            for (int u = 0; u < NV; u++) {
                __m256 g = _mm256_mul_ps(_mm256_load_ps(f0 + 8 * u), _mm256_load_ps(f1 + 8 * u));
                g = _mm256_mul_ps(g, _mm256_load_ps(f2 + 8 * u));
                g = _mm256_mul_ps(g, _mm256_load_ps(f3 + 8 * u));
                g = _mm256_mul_ps(g, _mm256_load_ps(r + 8 * u));
                A[u] = _mm256_fmadd_ps(_mm256_load_ps(a + 8 * u), g, A[u]);
            }
        }
        float *curb = bufb + (size_t)(k & 255) * rs;
        for (int u = 0; u < NV; u++) _mm256_store_ps(curb + 8 * u, A[u]);      /* beta_1..beta_m */
        if (jumeau) {                                    /* alpha_t(p) = sum_n' P0(n') beta_t(p-n') */
            for (int u = 0; u < NV; u++) A[u] = _mm256_setzero_ps();
            for (int n2 = NMIN; n2 <= NMAX; n2++) {
                const float *pj = PJ + (size_t)(n2 - NMIN) * mp;
                const float *b = bufb + (size_t)((k - (uint64_t)n2) & 255) * rs;
                for (int u = 0; u < NV; u++)
                    A[u] = _mm256_fmadd_ps(_mm256_load_ps(b + 8 * u), _mm256_load_ps(pj + 8 * u), A[u]);
            }
        }
        float *cura = bufa + (size_t)(k & 255) * rs;
        for (int u = 0; u < NV; u++) _mm256_storeu_ps(cura + 1 + 8 * u, A[u]);
        cura[0] = 1.0f;
        if (k >= PRO) {
            for (int u = 0; u < NV; u++)
                _mm256_store_ps(sv + 8 * u, _mm256_add_ps(_mm256_load_ps(sv + 8 * u), A[u]));
            if (++nflush == 1024) {
                for (int j = 0; j < mp; j++) { loc[j] += (double)sv[j]; sv[j] = 0.0f; }
                nflush = 0;
            }
            if (sel) {
                for (int u = 0; u < NV; u++) _mm256_store_ps(acc + 8 * u, A[u]);
                sel_push(sel, acc[m - 1], sq, p);
            }
        }
        p = (p + 1 == Pi) ? 0 : p + 1;
        V = ((__uint128_t)getcl(seg, p ? p - 1 : Pi - 1))
            | ((V << 2) & ((((__uint128_t)1 << (2 * NMAX)) - 1)));
    }
    for (int j = 0; j < m; j++) loc[j] += (double)sv[j];
#pragma omp critical
    for (int j = 0; j < m; j++) S[j] += loc[j];
    free(bufa);
    free(bufb);
    free(sv);
    free(acc);
    free(loc);
}

static void flot(uint32_t sq, uint32_t q0, uint32_t q1, int m, int mp, const float *MTF,
                 const float *MTR, const float *PJ, int jumeau, double *S, Sel *sel)
{
    switch (mp / 8) {
    case 1: flot_nv(sq, q0, q1, m, MTF, MTR, PJ, jumeau, S, sel, 1); break;
    case 2: flot_nv(sq, q0, q1, m, MTF, MTR, PJ, jumeau, S, sel, 2); break;
    case 3: flot_nv(sq, q0, q1, m, MTF, MTR, PJ, jumeau, S, sel, 3); break;
    case 4: flot_nv(sq, q0, q1, m, MTF, MTR, PJ, jumeau, S, sel, 4); break;
    case 5: flot_nv(sq, q0, q1, m, MTF, MTR, PJ, jumeau, S, sel, 5); break;
    case 6: flot_nv(sq, q0, q1, m, MTF, MTR, PJ, jumeau, S, sel, 6); break;
    case 7: flot_nv(sq, q0, q1, m, MTF, MTR, PJ, jumeau, S, sel, 7); break;
    case 8: flot_nv(sq, q0, q1, m, MTF, MTR, PJ, jumeau, S, sel, 8); break;
    default: fprintf(stderr, "m hors [1, 64]\n"); exit(2);
    }
}

/* ---- faisceau ---------------------------------------------------------------- */

typedef struct { uint64_t k; double v; } KV;
static KV *RAD;
static size_t RADCAP;

static void radix(KV *a, size_t n)
{
    if (n > RADCAP) { RADCAP = n; RAD = realloc(RAD, RADCAP * sizeof(KV)); }
    for (int pass = 0; pass < 3; pass++) {
        size_t cnt[4096], s = 0;
        memset(cnt, 0, sizeof cnt);
        int sh = 12 * pass;
        for (size_t i = 0; i < n; i++) cnt[(a[i].k >> sh) & 4095]++;
        for (int i = 0; i < 4096; i++) { size_t c = cnt[i]; cnt[i] = s; s += c; }
        for (size_t i = 0; i < n; i++) RAD[cnt[(a[i].k >> sh) & 4095]++] = a[i];
        memcpy(a, RAD, n * sizeof(KV));
    }
}

static void top_b(KV *a, long n, long B)
{
    if (B >= n) return;
    long lo = 0, hi = n - 1;
    while (lo < hi) {
        double piv = a[(lo + hi) / 2].v;
        long i = lo, j = hi;
        while (i <= j) {
            while (a[i].v > piv) i++;
            while (a[j].v < piv) j--;
            if (i <= j) { KV t = a[i]; a[i] = a[j]; a[j] = t; i++; j--; }
        }
        if (B - 1 <= j) hi = j;
        else if (B - 1 >= i) lo = i;
        else break;
    }
}

int main(int argc, char **argv)
{
    if (argc < 12) {
        fprintf(stderr, "usage : %s K L shift(0|1) jumeau(0|1) f_ac f_blocs mode(flux|nuit) m B1 "
                        "m2 B2 [pas_journal] [saut]\n", argv[0]);
        return 1;
    }
    int K = atoi(argv[1]), L = atoi(argv[2]), shift = atoi(argv[3]), jumeau = atoi(argv[4]);
    const char *f_ac = argv[5], *f_blocs = argv[6];
    int nuit = !strcmp(argv[7], "nuit");
    int m = atoi(argv[8]);
    long B1 = atol(argv[9]);
    int m2 = atoi(argv[10]);
    long B2 = atol(argv[11]);
    int pasj = argc > 12 ? atoi(argv[12]) : 5000;
    int saut = argc > 13 ? atoi(argv[13]) : 1;
    int DBG = getenv("DBG") != NULL;
    const int RMAX = 64;
    if (saut < 1) saut = 1;
    if (m < 1 || m > MMAX) { fprintf(stderr, "m in [1, %d]\n", MMAX); return 1; }
    if (B2 > B1) B1 = B2;
    double t00 = omp_get_wtime();
    tables();
    if (shift == 0) orbites_mod4(K, L);
    else orbites_mod8(K, L);
    double NPOS = (double)NSEQ * Pi;
    fprintf(stderr, "sequences pretes : %u x %u = %.6g positions, canal mod 4%s (%.1f s)\n",
            NSEQ, Pi, NPOS, jumeau ? ", JUMEAU entrelace" : "", omp_get_wtime() - t00);

    /* les tirages : a_0 a_1 a_2 a_3 par ligne */
    FILE *f = fopen(f_ac, "r");
    if (!f) { perror(f_ac); return 1; }
    int cap = 1 << 16, nt = 0;
    int *ac = malloc(sizeof(int) * 4 * cap);
    int v[4];
    while (fscanf(f, "%d %d %d %d", &v[0], &v[1], &v[2], &v[3]) == 4) {
        if (v[0] + v[1] + v[2] + v[3] != DRAWN) { fprintf(stderr, "somme != 20\n"); return 1; }
        if (nt == cap) { cap *= 2; ac = realloc(ac, sizeof(int) * 4 * cap); }
        for (int c = 0; c < 4; c++) ac[4 * nt + c] = v[c];
        nt++;
    }
    fclose(f);
    unsigned char *deb = calloc((size_t)nt + 1, 1);
    f = fopen(f_blocs, "r");
    if (!f) { perror(f_blocs); return 1; }
    int u;
    while (fscanf(f, "%d", &u) == 1)
        if (u >= 0 && u < nt) deb[u] = 1;
    fclose(f);
    deb[0] = 1;

    /* la loi P0(n') du jumeau : 20! S(n-1,19) / 80^n . C(80,20) */
    double PJ0[NN];
    {
        static long double S2[NMAX + 1][DRAWN + 1];
        memset(S2, 0, sizeof S2);
        S2[0][0] = 1;
        for (int w = 1; w <= NMAX; w++)
            for (int a = 1; a <= DRAWN; a++)
                S2[w][a] = a * S2[w - 1][a] + S2[w - 1][a - 1];
        long double fa = 1;
        for (int a = 1; a <= DRAWN; a++) fa *= a;
        long double c8 = 1;
        for (int i = 0; i < DRAWN; i++) c8 = c8 * (POOL - i) / (i + 1);
        double s = 0;
        for (int n = NMIN; n <= NMAX; n++) {
            PJ0[n - NMIN] = (double)(fa * S2[n - 1][DRAWN - 1] / powl(POOL, n) * c8);
            s += PJ0[n - NMIN];
        }
        if (jumeau) fprintf(stderr, "loi du jumeau : somme %.9f sur [%d, %d]\n", s, NMIN, NMAX);
    }

    int mpad = ((m + 7) / 8) * 8;
    float *MTF = aligned_alloc(64, (size_t)CL * NW * mpad * sizeof(float));
    float *MTR = aligned_alloc(64, (size_t)CL * NW * mpad * sizeof(float));
    float *PJ = aligned_alloc(64, (size_t)NN * mpad * sizeof(float));
    KV *beam = malloc((size_t)B1 * sizeof(KV));
    KV *cnd = malloc((size_t)B1 * NN * sizeof(KV));
    KV *RAD2 = jumeau ? malloc((size_t)B1 * NN * sizeof(KV)) : NULL;
    int nfils = omp_get_max_threads();
    Sel *sels = calloc((size_t)nfils, sizeof(Sel));
    for (int i = 0; i < nfils; i++) {
        sels[i].cap = 2 * B1;
        sels[i].c = malloc((size_t)sels[i].cap * sizeof(Cand));
    }
    double *S = calloc((size_t)m, sizeof(double));

    double lb = 0, lscale = 0, lbmax = 0, gmax = 0, gcum = 0, gcummax = 0;
    int tmax = 0, bmax = -1, bloc = -1, t0bloc = 0, nmort = 0, ncum = 0, nred = 0;
    long nb = 0;
    int apres = 0, t = 0, mort = 0, actif = 1;
    uint32_t pic_s = 0, pic_q = 0;
    double pic_v = 0;

    while (t < nt) {
        if (mort && !nuit) break;
        if (nuit && deb[t]) {
            if (bloc >= 0 && actif && t > t0bloc) {
                printf("BLOC %d %d %d %.6f %.6f\n", bloc, t0bloc, t - t0bloc, lb, lbmax);
                if (lbmax > gmax) { gmax = lbmax; bmax = bloc; }
                gcum += lb;
                ncum++;
                if (gcum > gcummax) gcummax = gcum;
            }
            bloc++;
            actif = (bloc % saut == 0);
            t0bloc = t;
            lb = lbmax = lscale = 0;
            nb = 0;
            if (!actif) { t++; while (t < nt && !deb[t]) t++; continue; }
        }
        if (nb == 0) {
            int fin = nt;
            if (nuit) for (int y = t + 1; y < nt; y++) if (deb[y]) { fin = y; break; }
            int mm = m < fin - t ? m : fin - t;
            int mp = ((mm + 7) / 8) * 8;
            memset(MTF, 0, (size_t)CL * NW * mp * sizeof(float));
            memset(MTR, 0, (size_t)CL * NW * mp * sizeof(float));
            memset(PJ, 0, (size_t)NN * mp * sizeof(float));
            for (int c = 0; c < CL; c++)
                for (int w = 0; w < NW; w++)
                    for (int j = 0; j < mm; j++) {
                        int a = ac[4 * (t + j) + c];
                        MTF[((size_t)c * NW + w) * mp + j] =
                            F20[w][a] * (c == 0 ? (float)exp2(LOG2_C8020) : 1.0f);
                        MTR[((size_t)c * NW + w) * mp + j] = R20[w][a];
                    }
            for (int n2 = 0; n2 < NN; n2++)
                for (int j = 0; j < mm; j++) PJ[(size_t)n2 * mp + j] = (float)PJ0[n2];
            memset(S, 0, (size_t)mm * sizeof(double));
            for (int i = 0; i < nfils; i++) { sels[i].n = 0; sels[i].B = B1; sels[i].seuil = 0.0f; }
            uint32_t chunk = Pi;
            long parseq = 1;
            if (NSEQ < (uint32_t)(4 * nfils)) {          /* peu de sequences : on decoupe */
                parseq = (4L * nfils + NSEQ - 1) / NSEQ;
                chunk = (uint32_t)((Pi + parseq - 1) / parseq);
                if (chunk < (1u << 15)) { chunk = 1u << 15; parseq = (Pi + chunk - 1) / chunk; }
            }
            long ntache = (long)NSEQ * parseq;
#pragma omp parallel for schedule(dynamic)
            for (long ta = 0; ta < ntache; ta++) {
                uint32_t sq = (uint32_t)(ta / parseq);
                uint32_t q0 = (uint32_t)((ta % parseq) * chunk);
                uint32_t q1 = q0 + chunk > Pi ? Pi : q0 + chunk;
                if (q0 < q1)
                    flot(sq, q0, q1, mm, mp, MTF, MTR, PJ, jumeau, S, &sels[omp_get_thread_num()]);
            }
            int j;
            for (j = 0; j < mm; j++) {
                if (!(S[j] > 0)) break;
                lb = log2(S[j]) - LOG2_N;
                if (lb > lbmax) { lbmax = lb; tmax = t + j + 1; }
                if (pasj > 0 && !nuit && (t + j + 1) % pasj == 0)
                    printf("T %d %.4f %.4f %d\n", t + j + 1, lb, lbmax, tmax);
            }
            if (j < mm) {
                if (DBG) fprintf(stderr, "mort phaseA t=%d j=%d\n", t, j);
                nmort++;
                lb = -INFINITY;
                t += j + 1;
                nb = 0;
                if (nuit) { while (t < nt && !deb[t]) t++; }
                else if (++nred > RMAX) mort = 1;
                else { if (lbmax > gmax) gmax = lbmax; lbmax = lb = lscale = 0; }
                continue;
            }
            nb = 0;
            for (int i = 0; i < nfils; i++) {
                sel_reduit(&sels[i]);
                for (long y = 0; y < sels[i].n; y++)
                    cnd[nb++] = (KV){ (uint64_t)sels[i].c[y].s * Pi + sels[i].c[y].q, sels[i].c[y].v };
            }
            top_b(cnd, nb, B1);
            if (nb > B1) nb = B1;
            double mx = 0;
            for (long i = 0; i < nb; i++) if (cnd[i].v > mx) mx = cnd[i].v;
            if (!(mx > 0)) {
                nmort++;
                lb = -INFINITY;
                nb = 0;
                t += mm;
                if (!nuit && ++nred > RMAX) mort = 1;
                else if (!nuit) { if (lbmax > gmax) gmax = lbmax; lbmax = lb = lscale = 0; }
                continue;
            }
            double sfa = 0;
            for (long i = 0; i < nb; i++) { beam[i] = (KV){ cnd[i].k, cnd[i].v / mx }; sfa += beam[i].v; }
            lscale = log2(mx);
            lb = log2(sfa) + lscale - LOG2_N;
            if (lb > lbmax) { lbmax = lb; tmax = t + mm; }
            t += mm;
            apres = 0;
            continue;
        }
        /* ---- un tirage sur le faisceau ---- */
        long B = apres < m2 ? B1 : B2;
        const int *a = ac + 4 * t;
        long nc = 0;
        for (long i = 0; i < nb; i++) {
            uint64_t g = beam[i].k;
            uint32_t sq = (uint32_t)(g / Pi);
            uint32_t q = (uint32_t)(g - (uint64_t)sq * Pi);
            const uint64_t *seg = CLS + (size_t)sq * STRIDE;
            int w[CL] = {0, 0, 0, 0};
            for (int y = 0; y < NMIN; y++) w[getcl(seg, (q + y) % Pi)]++;
            double val = beam[i].v;
            for (int n = NMIN; n <= NMAX; n++) {
                int cs = getcl(seg, (q + n - 1) % Pi);
                if (n > NMIN) w[cs]++;
                double wt = (double)F20[w[0]][a[0]] * F20[w[1]][a[1]] * F20[w[2]][a[2]]
                            * F20[w[3]][a[3]] * R20[w[cs]][a[cs]];
                if (!(wt > 0)) continue;
                uint32_t q2 = q + (uint32_t)n;
                while (q2 >= Pi) q2 -= Pi;
                cnd[nc].k = (uint64_t)sq * Pi + q2;
                cnd[nc].v = val * wt * exp2(LOG2_C8020);
                nc++;
            }
        }
        radix(cnd, (size_t)nc);
        long nu = 0;
        for (long i = 0; i < nc; ) {
            long y = i + 1;
            double s = cnd[i].v;
            while (y < nc && cnd[y].k == cnd[i].k) s += cnd[y++].v;
            cnd[nu].k = cnd[i].k;
            cnd[nu].v = s;
            nu++;
            i = y;
        }
        if (nu > B) { top_b(cnd, nu, B); nu = B; }
        if (jumeau) {                       /* convolution par la loi du jumeau, seconde passe */
            long nc2 = 0;
            for (long i = 0; i < nu; i++) {
                uint64_t g = cnd[i].k;
                uint32_t sq = (uint32_t)(g / Pi);
                uint32_t q = (uint32_t)(g - (uint64_t)sq * Pi);
                for (int n2 = NMIN; n2 <= NMAX; n2++) {
                    uint32_t q2 = q + (uint32_t)n2;
                    while (q2 >= Pi) q2 -= Pi;
                    RAD2[nc2].k = (uint64_t)sq * Pi + q2;
                    RAD2[nc2].v = cnd[i].v * PJ0[n2 - NMIN];
                    nc2++;
                }
            }
            memcpy(cnd, RAD2, (size_t)nc2 * sizeof(KV));
            radix(cnd, (size_t)nc2);
            long nu2 = 0;
            for (long i = 0; i < nc2; ) {
                long y = i + 1;
                double s = cnd[i].v;
                while (y < nc2 && cnd[y].k == cnd[i].k) s += cnd[y++].v;
                cnd[nu2].k = cnd[i].k;
                cnd[nu2].v = s;
                nu2++;
                i = y;
            }
            nu = nu2;
            if (nu > B) { top_b(cnd, nu, B); nu = B; }
        }
        double mx = 0;
        for (long i = 0; i < nu; i++) if (cnd[i].v > mx) mx = cnd[i].v;
        double sfa = 0;
        for (long i = 0; i < nu; i++) { beam[i] = (KV){ cnd[i].k, cnd[i].v / mx }; sfa += beam[i].v; }
        nb = nu;
        lscale += log2(mx);
        lb = log2(sfa) + lscale - LOG2_N;
        t++;
        apres++;
        if (lb > lbmax) { lbmax = lb; tmax = t; }
        if (pasj > 0 && !nuit && t % pasj == 0) printf("T %d %.4f %.4f %d\n", t, lb, lbmax, tmax);
    }
    if (nuit && bloc >= 0 && actif) {
        printf("BLOC %d %d %d %.6f %.6f\n", bloc, t0bloc, nt - t0bloc, lb, lbmax);
        if (lbmax > gmax) { gmax = lbmax; bmax = bloc; }
        gcum += lb;
        ncum++;
        if (gcum > gcummax) gcummax = gcum;
    }
    if (!nuit && lbmax > gmax) gmax = lbmax;
    if (nb) {
        long ib = 0;
        double s = 0;
        for (long i = 0; i < nb; i++) { s += beam[i].v; if (beam[i].v > beam[ib].v) ib = i; }
        pic_s = (uint32_t)(beam[ib].k / Pi);
        pic_q = (uint32_t)(beam[ib].k - (uint64_t)pic_s * Pi);
        pic_v = beam[ib].v / s;
    }
    printf("PIC %u %u %.6f\n", pic_s, pic_q, pic_v);
    printf("FIN %u %u %.0f %d %.4f %.4f %d %d %d %.4f %d %d %.1f\n", NSEQ, Pi, NPOS, nt, lb, gmax,
           tmax, bmax, ncum, gcummax, nmort, nred, omp_get_wtime() - t00);
    return 0;
}
