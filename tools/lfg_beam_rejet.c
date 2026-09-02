/* lfg_beam_rejet — h146 : la synchronisation sous le REJET pour les GRANDS etats,
 * par programmation dynamique ELAGUEE (faisceau).  THEORIE_ETAT §7.18 (suite du §7.17).
 *
 * Le §7.17 lit le pas variable de l'echantillonneur a rejet par une chaine cachee sur la
 * POSITION ABSOLUE q dans une sequence de bits periodique :
 *     alpha_t[(q + n) mod Pi] += alpha_{t-1}[q] . C(80,20) . P(A_t, n | bits q..q+n-1)
 * avec n in [20, 40] et alpha_0 = 1 partout (unites de rapport de vraisemblance) ; alors
 *     BF_t = (1/N) Sum_q alpha_t[q],   N = NSEQ . Pi,
 * est une martingale de moyenne 1 sous H0 (Ville : P0(sup_t BF_t >= 1e7) <= 1e-7).  Elle coute
 * 21 N par tirage : hors de portee pour N = 2^31 - 1 (plan 0 de TYPE_3, x^31 + x^3 + 1) ou
 * N = 2^14 . 65534 (plan 1 de TYPE_2, x^15 + x + 1) sur 70 560 tirages.
 *
 * L'ELAGAGE.  Mettre a zero une partie des alpha, par n'importe quelle regle (meme dependante
 * des donnees), ne peut que DIMINUER tous les alpha ulterieurs (les poids sont positifs), et
 * l'esperance conditionnelle d'un pas reste <= 1 (melange propre, tronque a n <= 40) : BF' est
 * une SURMARTINGALE positive de moyenne <= 1 et l'inegalite de Ville s'applique telle quelle.
 * L'elagage ne coute pas de validite ; il coute de la PUISSANCE : il faut que la VRAIE position
 * survive.  Borne de Markov : sous H0, E[#{q : LR_q >= 2^x}] <= N 2^-x, donc un faisceau de
 * largeur B garde tout ce qui depasse la COUPE x = log2(N/B) ; la vraie position gagne ~1,1 bit
 * par tirage (mesure sur generateurs plantes), soit 43 +- 8 bits en m = 40 tirages, tres
 * au-dessus des 15 bits de coupe d'un faisceau de 2^16.
 *
 * TROIS PHASES.
 *   A. m tirages PLEINS (toutes les positions), en UN SEUL passage en flot : alpha_t(p) ne
 *      depend que de alpha_{t-1}(p-20..p-40), donc un anneau de 64 positions x m etages suffit
 *      — memoire O(m), aucun tableau de taille N.  Un prologue de 40 m positions avant le debut
 *      d'un morceau rend le calcul EXACT (alpha_0 = 1 partout) : le passage se decoupe en
 *      morceaux paralleles sans aucune approximation.
 *   B. les B1 meilleures positions, m2 tirages de plus.
 *   C. les B2 meilleures, tous les tirages restants.
 *
 * usage : lfg_beam_rejet K L shift(0|1) f_a0 f_blocs mode(flux|nuit) m B1 m2 B2 [pas_journal] [saut]
 *   saut : mode nuit, ne traiter qu'un bloc sur "saut" (echantillon systematique preenregistre)
 * sortie : "T t log2bf max tmax" tous les pas_journal tirages (mode flux),
 *          "BLOC b t0 n log2bf max_dans_le_bloc" par bloc (mode nuit),
 *          "PIC seq q masse", "FIN nseq Pi N nt log2bf max tmax bmax nblocs maxcum nmort nred sec".
 * Mode flux : quand le faisceau meurt (aucune position survivante — l'elagage, pas le modele),
 * la chaine redemarre a l'uniforme au tirage suivant, au plus RMAX = 64 fois ; le melange de
 * poids 1/RMAX sur les chaines reste une surmartingale, d'ou le seuil log2(1e7) + log2(64).
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
#define HALF 40
#define NMIN 20
#define NMAX 40
#define NW (NMAX + 1)          /* w1 in [0, 40] */
#define NIDX (2 * NW)          /* (dernier bit, w1) */
#define NN (NMAX - NMIN + 1)   /* 21 valeurs de n */
#define MMAX 64
#define MASK20 ((1ULL << NMIN) - 1)

static float TABF[DRAWN + 1][NMAX + 1][NIDX];   /* C(80,20) . P(A, n | w1, b) */

static void tables(void)
{
    static long double S[NMAX + 1][DRAWN + 1];
    memset(S, 0, sizeof S);
    S[0][0] = 1;
    for (int w = 1; w <= NMAX; w++)
        for (int a = 1; a <= DRAWN; a++)
            S[w][a] = a * S[w - 1][a] + S[w - 1][a - 1];
    long double fact[DRAWN + 1];
    fact[0] = 1;
    for (int a = 1; a <= DRAWN; a++) fact[a] = fact[a - 1] * a;
    long double pw[NMAX + 1];
    pw[0] = 1;
    for (int w = 1; w <= NMAX; w++) pw[w] = pw[w - 1] * HALF;
    long double c = 1;
    for (int i = 0; i < DRAWN; i++) c = c * (POOL - i) / (i + 1);
#define FF(w, a) (((w) < (a) || ((a) == 0 && (w) > 0)) ? 0.0L : fact[a] * S[w][a] / pw[w])
#define GG(w, a) (((a) == 0 || (w) < (a)) ? 0.0L : fact[a] * S[(w) - 1][(a) - 1] / pw[w])
    for (int a0 = 0; a0 <= DRAWN; a0++) {
        int a1 = DRAWN - a0;
        for (int n = NMIN; n <= NMAX; n++)
            for (int w1 = 0; w1 <= n; w1++) {
                int w0 = n - w1;
                TABF[a0][n][w1] = (float)(c * FF(w1, a1) * GG(w0, a0));        /* dernier bit 0 */
                TABF[a0][n][NW + w1] = (float)(c * FF(w0, a0) * GG(w1, a1));   /* dernier bit 1 */
            }
    }
}

/* ---- les sequences, en bits tasses ------------------------------------------ */

static uint64_t *BITS;         /* NSEQ segments de STRIDE mots de 64 bits */
static size_t STRIDE;
static uint32_t Pi, NSEQ;
static double LOG2_N;

static inline int getbit(const uint64_t *b, uint32_t q) { return (int)((b[q >> 6] >> (q & 63)) & 1); }

static inline uint64_t win64(const uint64_t *b, uint32_t q)
{
    size_t w = q >> 6;
    int r = (int)(q & 63);
    uint64_t lo = b[w];
    return r ? (lo >> r) | (b[w + 1] << (64 - r)) : lo;
}

static inline void metbit(uint64_t *seg, uint32_t i, int v)
{
    if (v) seg[i >> 6] |= 1ULL << (i & 63);
}

static void alloue(uint32_t pi, uint32_t nseq)
{
    Pi = pi;
    NSEQ = nseq;
    STRIDE = (pi + 192) / 64 + 2;
    BITS = calloc((size_t)nseq * STRIDE, 8);
    if (!BITS) { fprintf(stderr, "memoire (%.2f Go)\n", (double)nseq * STRIDE * 8 / 1e9); exit(2); }
    LOG2_N = log2((double)nseq * pi);
}

static void replie(uint64_t *seg)      /* recopie les 128 premiers bits apres la fin */
{
    for (uint32_t i = 0; i < 128; i++) metbit(seg, Pi + i, getbit(seg, i));
}

/* plan 0 : la m-sequence b_i = b_{i-K} xor b_{i-L}, periode 2^L - 1 */
static void m_sequence(int K, int L)
{
    alloue((uint32_t)((1U << L) - 1), 1);
    uint64_t msk = (1ULL << L) - 1, R = 1;      /* R bit j = b_{i-1-j} ; etat initial 0...01 */
    for (uint32_t i = 0; i < Pi; i++) {
        uint64_t b = ((R >> (K - 1)) ^ (R >> (L - 1))) & 1;
        metbit(BITS, i, (int)b);
        R = (R << 1) | b;
    }
    if ((R & msk) != 1) { fprintf(stderr, "periode fausse (etat non revenu)\n"); exit(2); }
    replie(BITS);
}

/* plan 1 du Fibonacci mod 4 : b_i = b_{i-K} ^ b_{i-L},  c_i = c_{i-K} ^ c_{i-L} ^ (b_{i-K} & b_{i-L}).
 * Plan 0 non nul : 2^(L-1) orbites de periode 2P (Brent).  Representants : plan 0 fixe a l'etat
 * canonique 0...01, les 2^L etats du plan 1 s'appariant (c, c apres P pas). */
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
        uint64_t *seg = BITS + (size_t)no * STRIDE;
        for (uint32_t i = 0; i < 2 * P; i++) {
            uint64_t x0 = (R0 >> (K - 1)) & 1, y0 = (R0 >> (L - 1)) & 1;
            uint64_t x1 = (R1 >> (K - 1)) & 1, y1 = (R1 >> (L - 1)) & 1;
            uint64_t b = x0 ^ y0, cc = x1 ^ y1 ^ (x0 & y0);
            metbit(seg, i, (int)cc);
            R0 = (R0 << 1) | b;
            R1 = (R1 << 1) | cc;
            if (i + 1 == P) {                                  /* plan 0 revenu : c partenaire */
                uint32_t part = (uint32_t)(R1 & msk);
                if ((R0 & msk) != 1) { fprintf(stderr, "plan 0 : periode != P\n"); exit(2); }
                if (part == c0) { fprintf(stderr, "orbite de periode P\n"); exit(2); }
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

/* ---- selection des B meilleures positions ------------------------------------- */

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

/* ---- phase A : m tirages pleins, un seul passage en flot ---------------------- */

/* passage sur [q0, q1) du segment sq, prologue de 40 m positions compris ;
 * MT[(n - NMIN) * NIDX + idx][j] = C(80,20) P(A_{t+j}, n | idx) ; S[j] += Sum_p alpha_{j+1}(p). */
__attribute__((always_inline))
static inline void flot_nv(uint32_t sq, uint32_t q0, uint32_t q1, int m, const float *__restrict MT,
                           double *S, Sel *sel, const int NV)
{
    const int mp = 8 * NV, rs = mp + 8;                 /* rs : la rangee deborde d'un vecteur */
    /* les alpha des positions mortes descendent sous 2^-126 : sans mise a zero materielle des
     * denormaux, l'assistance microcode coute 10 fois le passage (mesure) ; la mise a zero est
     * un elagage de plus, donc licite (BF' <= BF). */
    _MM_SET_FLUSH_ZERO_MODE(_MM_FLUSH_ZERO_ON);
    _MM_SET_DENORMALS_ZERO_MODE(_MM_DENORMALS_ZERO_ON);
    const uint64_t *seg = BITS + (size_t)sq * STRIDE;
    uint32_t PRO = (uint32_t)NMAX * (uint32_t)m;
    float *buf = aligned_alloc(64, (size_t)64 * rs * sizeof(float));
    double *loc = calloc((size_t)mp, sizeof(double));
    float *sv = aligned_alloc(64, (size_t)mp * sizeof(float));
    float *acc = aligned_alloc(64, (size_t)mp * sizeof(float));
    memset(buf, 0, (size_t)64 * rs * sizeof(float));
    memset(sv, 0, (size_t)mp * sizeof(float));
    for (int i = 0; i < 64; i++) buf[(size_t)i * rs] = 1.0f;          /* alpha_0 = 1 */
    uint32_t p = (uint32_t)(((uint64_t)q0 + Pi - PRO % Pi) % Pi);
    uint64_t V = 0;
    for (int i = 0; i < 64; i++)
        V = (V << 1) | (uint64_t)getbit(seg, (uint32_t)(((uint64_t)p + Pi - 64 + i) % Pi));
    uint64_t total = (uint64_t)PRO + (q1 - q0);
    int nflush = 0;
    for (uint64_t k = 0; k < total; k++) {
        int b = (int)(V & 1);
        int w1 = __builtin_popcountll(V & MASK20);
        __m256 A[8];
        for (int u = 0; u < NV; u++) A[u] = _mm256_setzero_ps();
        for (int n = NMIN; n <= NMAX; n++) {
            if (n > NMIN) w1 += (int)((V >> (n - 1)) & 1);
            const float *w = MT + ((size_t)(n - NMIN) * NIDX + (size_t)(w1 + NW * b)) * mp;
            const float *a = buf + (size_t)((k - (uint64_t)n) & 63) * rs;
            for (int u = 0; u < NV; u++)
                A[u] = _mm256_fmadd_ps(_mm256_load_ps(a + 8 * u), _mm256_load_ps(w + 8 * u), A[u]);
        }
        float *cur = buf + (size_t)(k & 63) * rs;
        for (int u = 0; u < NV; u++) _mm256_storeu_ps(cur + 1 + 8 * u, A[u]);   /* alpha_1..alpha_m */
        cur[0] = 1.0f;
        if (k >= PRO) {
            for (int u = 0; u < NV; u++)
                _mm256_store_ps(sv + 8 * u, _mm256_add_ps(_mm256_load_ps(sv + 8 * u), A[u]));
            if (++nflush == 1024) {
                for (int j = 0; j < m; j++) { loc[j] += (double)sv[j]; sv[j] = 0.0f; }
                for (int j = m; j < mp; j++) sv[j] = 0.0f;
                nflush = 0;
            }
            if (sel) {
                for (int u = 0; u < NV; u++) _mm256_store_ps(acc + 8 * u, A[u]);
                sel_push(sel, acc[m - 1], sq, p);
            }
        }
        p = (p + 1 == Pi) ? 0 : p + 1;
        V = (V << 1) | (uint64_t)getbit(seg, p ? p - 1 : Pi - 1);
    }
    for (int j = 0; j < m; j++) loc[j] += (double)sv[j];
#pragma omp critical
    for (int j = 0; j < m; j++) S[j] += loc[j];
    free(buf);
    free(sv);
    free(acc);
    free(loc);
}

static void flot(uint32_t sq, uint32_t q0, uint32_t q1, int m, int mp, const float *MT, double *S,
                 Sel *sel)
{
    switch (mp / 8) {
    case 1: flot_nv(sq, q0, q1, m, MT, S, sel, 1); break;
    case 2: flot_nv(sq, q0, q1, m, MT, S, sel, 2); break;
    case 3: flot_nv(sq, q0, q1, m, MT, S, sel, 3); break;
    case 4: flot_nv(sq, q0, q1, m, MT, S, sel, 4); break;
    case 5: flot_nv(sq, q0, q1, m, MT, S, sel, 5); break;
    case 6: flot_nv(sq, q0, q1, m, MT, S, sel, 6); break;
    case 7: flot_nv(sq, q0, q1, m, MT, S, sel, 7); break;
    case 8: flot_nv(sq, q0, q1, m, MT, S, sel, 8); break;
    default: fprintf(stderr, "m hors [1, 64]\n"); exit(2);
    }
}

/* ---- phases B et C : le faisceau ----------------------------------------------- */

typedef struct { uint64_t k; double v; } KV;

static KV *RAD;
static size_t RADCAP;

static void radix(KV *a, size_t n)                      /* tri par cle (36 bits) */
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

/* place les B plus grandes valeurs en tete (selection rapide de Hoare, O(n) en moyenne) */
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
    if (argc < 11) {
        fprintf(stderr, "usage : %s K L shift(0|1) f_a0 f_blocs mode(flux|nuit) m B1 m2 B2 [pas_journal]\n",
                argv[0]);
        return 1;
    }
    int K = atoi(argv[1]), L = atoi(argv[2]), shift = atoi(argv[3]);
    const char *f_a0 = argv[4], *f_blocs = argv[5];
    int nuit = !strcmp(argv[6], "nuit");
    int m = atoi(argv[7]);
    long B1 = atol(argv[8]);
    int m2 = atoi(argv[9]);
    long B2 = atol(argv[10]);
    int pasj = argc > 11 ? atoi(argv[11]) : 5000;
    int saut = argc > 12 ? atoi(argv[12]) : 1;      /* mode nuit : un bloc sur saut */
    if (saut < 1) saut = 1;
    int DBG = getenv("DBG") != NULL;
    const int RMAX = 64;                       /* budget de redemarrages du flux (melange 1/RMAX) */
    if (m < 1 || m > MMAX) { fprintf(stderr, "m in [1, %d]\n", MMAX); return 1; }
    if (B2 > B1) B1 = B2;
    double t00 = omp_get_wtime();
    tables();
    if (shift == 0) m_sequence(K, L);
    else orbites_mod4(K, L);
    double NPOS = (double)NSEQ * Pi;
    fprintf(stderr, "sequences pretes : %u x %u = %.6g positions (%.1f s)\n", NSEQ, Pi, NPOS,
            omp_get_wtime() - t00);

    FILE *f = fopen(f_a0, "r");
    if (!f) { perror(f_a0); return 1; }
    int cap = 1 << 16, nt = 0, v;
    int *a0 = malloc(sizeof(int) * cap);
    while (fscanf(f, "%d", &v) == 1) {
        if (v < 0 || v > DRAWN) { fprintf(stderr, "a0 hors [0,20]\n"); return 1; }
        if (nt == cap) { cap *= 2; a0 = realloc(a0, sizeof(int) * cap); }
        a0[nt++] = v;
    }
    fclose(f);
    unsigned char *deb = calloc((size_t)nt + 1, 1);
    f = fopen(f_blocs, "r");
    if (!f) { perror(f_blocs); return 1; }
    while (fscanf(f, "%d", &v) == 1)
        if (v >= 0 && v < nt) deb[v] = 1;
    fclose(f);
    deb[0] = 1;

    int mpad = ((m + 7) / 8) * 8;
    float *MT = aligned_alloc(64, (size_t)NN * NIDX * mpad * sizeof(float));
    KV *beam = malloc((size_t)B1 * sizeof(KV));
    KV *cnd = malloc((size_t)B1 * NN * sizeof(KV));
    int nfils = omp_get_max_threads();
    Sel *sels = calloc((size_t)nfils, sizeof(Sel));
    for (int i = 0; i < nfils; i++) {
        sels[i].cap = 2 * B1;
        sels[i].c = malloc((size_t)sels[i].cap * sizeof(Cand));
    }
    double *S = calloc((size_t)m, sizeof(double));

    double lb = 0, lscale = 0, lbmax = 0;         /* chaine courante */
    double gmax = 0, gcum = 0, gcummax = 0;       /* max global (flux) ; cumul des blocs (nuit) */
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
            lb = 0;
            lbmax = 0;
            lscale = 0;
            nb = 0;
            if (!actif) { t++; while (t < nt && !deb[t]) t++; continue; }
        }
        if (nb == 0) {
            /* ---- phase A ---- */
            int fin = nt;
            if (nuit) for (int u = t + 1; u < nt; u++) if (deb[u]) { fin = u; break; }
            int mm = m < fin - t ? m : fin - t;
            int mp = ((mm + 7) / 8) * 8;
            memset(MT, 0, (size_t)NN * NIDX * mp * sizeof(float));
            for (int n = NMIN; n <= NMAX; n++)
                for (int ix = 0; ix < NIDX; ix++)
                    for (int j = 0; j < mm; j++)
                        MT[((size_t)(n - NMIN) * NIDX + ix) * mp + j] = TABF[a0[t + j]][n][ix];
            memset(S, 0, (size_t)mm * sizeof(double));
            for (int i = 0; i < nfils; i++) { sels[i].n = 0; sels[i].B = B1; sels[i].seuil = 0.0f; }
            uint32_t chunk = Pi;
            long ntache = NSEQ;
            if (NSEQ == 1) {
                chunk = Pi / (uint32_t)(4 * nfils) + 1;
                if (chunk < (1u << 16)) chunk = 1u << 16;
                ntache = (Pi + chunk - 1) / chunk;
            }
#pragma omp parallel for schedule(dynamic)
            for (long ta = 0; ta < ntache; ta++) {
                uint32_t sq = NSEQ == 1 ? 0 : (uint32_t)ta;
                uint32_t q0 = NSEQ == 1 ? (uint32_t)ta * chunk : 0;
                uint32_t q1 = NSEQ == 1 ? (q0 + chunk > Pi ? Pi : q0 + chunk) : Pi;
                flot(sq, q0, q1, mm, mp, MT, S, &sels[omp_get_thread_num()]);
            }
            int j;
            for (j = 0; j < mm; j++) {
                if (!(S[j] > 0)) break;
                lb = log2(S[j]) - LOG2_N;
                if (lb > lbmax) { lbmax = lb; tmax = t + j + 1; }
                if (pasj > 0 && !nuit && (t + j + 1) % pasj == 0)
                    printf("T %d %.4f %.4f %d\n", t + j + 1, lb, lbmax, tmax);
            }
            if (j < mm) {                          /* tirage impossible : la chaine meurt */
                if (DBG) fprintf(stderr, "mort phaseA t=%d j=%d a0=%d\n", t, j, a0[t + j]);
                nmort++;
                lb = -INFINITY;
                t += j + 1;
                nb = 0;
                if (nuit) { while (t < nt && !deb[t]) t++; }
                else if (++nred > RMAX) mort = 1;
                else { if (lbmax > gmax) gmax = lbmax; lbmax = 0; lb = 0; lscale = 0; }
                continue;
            }
            nb = 0;
            for (int i = 0; i < nfils; i++) {
                sel_reduit(&sels[i]);
                for (long u = 0; u < sels[i].n; u++)
                    cnd[nb++] = (KV){ (uint64_t)sels[i].c[u].s * Pi + sels[i].c[u].q, sels[i].c[u].v };
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
                else if (!nuit) { if (lbmax > gmax) gmax = lbmax; lbmax = 0; lb = 0; lscale = 0; }
                continue;
            }
            double sfa = 0;
            for (long i = 0; i < nb; i++) { beam[i] = (KV){ cnd[i].k, cnd[i].v / mx }; sfa += beam[i].v; }
            lscale = log2(mx);
            lb = log2(sfa) + lscale - LOG2_N;      /* la somme ELAGUEE, celle de la surmartingale */
            if (lb > lbmax) { lbmax = lb; tmax = t + mm; }
            t += mm;
            apres = 0;
            continue;
        }
        /* ---- un tirage sur le faisceau ---- */
        long B = apres < m2 ? B1 : B2;
        const float (*T)[NIDX] = TABF[a0[t]];
        long nc = 0;
        for (long i = 0; i < nb; i++) {
            uint64_t g = beam[i].k;
            uint32_t sq = NSEQ == 1 ? 0 : (uint32_t)(g / Pi);
            uint32_t q = NSEQ == 1 ? (uint32_t)g : (uint32_t)(g - (uint64_t)sq * Pi);
            uint64_t U = win64(BITS + (size_t)sq * STRIDE, q);
            int w1 = __builtin_popcountll(U & MASK20);
            double val = beam[i].v;
            for (int n = NMIN; n <= NMAX; n++) {
                int b = (int)((U >> (n - 1)) & 1);
                if (n > NMIN) w1 += b;
                float w = T[n][w1 + NW * b];
                if (!(w > 0.0f)) continue;
                uint32_t q2 = q + (uint32_t)n;
                if (q2 >= Pi) q2 -= Pi;
                cnd[nc].k = (uint64_t)sq * Pi + q2;
                cnd[nc].v = val * (double)w;
                nc++;
            }
        }
        if (nc == 0) {
            if (DBG) fprintf(stderr, "mort faisceau t=%d a0=%d nb=%ld\n", t, a0[t], nb);
            nmort++;
            lb = -INFINITY;
            nb = 0;
            t++;
            if (nuit) { while (t < nt && !deb[t]) t++; }
            else if (++nred > RMAX) mort = 1;
            else { if (lbmax > gmax) gmax = lbmax; lbmax = 0; lb = 0; lscale = 0; }
            continue;
        }
        radix(cnd, (size_t)nc);
        long nu = 0;
        for (long i = 0; i < nc; ) {
            long j = i + 1;
            double s = cnd[i].v;
            while (j < nc && cnd[j].k == cnd[i].k) s += cnd[j++].v;
            cnd[nu].k = cnd[i].k;
            cnd[nu].v = s;
            nu++;
            i = j;
        }
        if (nu > B) { top_b(cnd, nu, B); nu = B; }
        double mx = 0;
        for (long i = 0; i < nu; i++) if (cnd[i].v > mx) mx = cnd[i].v;
        double sfa = 0;
        for (long i = 0; i < nu; i++) { beam[i] = (KV){ cnd[i].k, cnd[i].v / mx }; sfa += beam[i].v; }
        nb = nu;
        if (DBG && t % 500 == 0)
            fprintf(stderr, "t=%d a0=%d nc=%ld nu=%ld mx=%.3g lb=%.2f\n", t, a0[t], nc, nu, mx, lb);
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
        pic_s = NSEQ == 1 ? 0 : (uint32_t)(beam[ib].k / Pi);
        pic_q = (uint32_t)(beam[ib].k - (uint64_t)pic_s * Pi);
        pic_v = beam[ib].v / s;
    }
    printf("PIC %u %u %.6f\n", pic_s, pic_q, pic_v);
    printf("FIN %u %u %.0f %d %.4f %.4f %d %d %d %.4f %d %d %.1f\n", NSEQ, Pi, NPOS, nt, lb, gmax,
           tmax, bmax, ncum, gcummax, nmort, nred, omp_get_wtime() - t00);
    return 0;
}
