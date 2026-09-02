/* lfg_trois_plans — les trois plans muets (THEORIE_ETAT §7.10).
 *
 * Fibonacci retardé additif r_i = r_{i-K} + r_{i-L} mod 2^32, sortie r >> 1,
 * tirages TRIÉS à pas constant S (Fisher-Yates partiel par modulo). Les deux
 * mots sûrs de chaque tirage (positions 0 et 16, lemme du §7.6) publient :
 *   mot 0  : (r >> 1) mod 16 = bits 1..4 de r, dans le masque mod 16 du tirage
 *            (canal 4 : les classes (v-1) mod 16 des vingt numéros) ;
 *   mot 16 : (r >> 1) mod 64 = bits 1..6 de r, dans le masque mod 64 du tirage
 *            (canal 6 : les v - 17 des numéros v >= 17 ; lemme du mot 16 à six bits).
 *
 * Le crible du §155 énumère les 2^{5L} états bas. Ici on n'énumère que les
 * PLANS 0..2 des L mots initiaux (2^{3L}) : les plans 0..2 fixés, les retenues
 * vers le bit 3 sont connues et le plan 3 de tout mot est une forme AFFINE sur
 * F_2 du plan 3 initial x3 ∈ F_2^L :
 *     b3_i = <α_i, x3> ⊕ γ_i,   α_i = α_{i-K} ⊕ α_{i-L},  γ_i = γ_{i-K} ⊕ γ_{i-L} ⊕ c3_i,
 *     c3_i = [(r_{i-K} mod 8) + (r_{i-L} mod 8) ≥ 8].
 * Un mot sûr dont les bits 1..2 sont connus n'admet, d'après son masque, que
 * certains bits 3 ; s'il n'en admet qu'un, c'est une ÉQUATION linéaire sur x3 ;
 * s'il n'en admet aucun, l'état des plans 0..2 est mort. Gauss incrémental :
 * un faux état est rejeté dès qu'une équation contredit. Le plan 3 résolu, le
 * plan 4 est affine à son tour (retenues connues) et se résout de même ; au
 * canal 6, les plans 5 et 6 aussi (mot 16 seul) — état bas de 7L bits.
 *
 * usage : lfg_trois_plans K L S N masques.bin nlibre canal [r8 des L-nlibre derniers mots initiaux]
 *   masques.bin : N uint16 (masque mod 16) puis N uint64 (masque mod 64)
 *   nlibre      : les nlibre PREMIERS mots initiaux parcourent (Z/8)^nlibre ; les
 *                 autres sont fixés (sous-cube contenant un état planté, pour
 *                 mesurer à grand L sans parcourir 2^{3L})
 *   canal       : 4 (mot 16 lu mod 16 comme le mot 0) ou 6 (mot 16 lu mod 64)
 * sortie : lignes "BAS r0 ... r_{L-1}" (mod 32 au canal 4, mod 128 au canal 6), puis
 *          "FIN etats=.. vides=.. gauss=.. survivants=.. mots_moyens=.. sec=.."
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define MAXL 63
#define NSURS 2
static const int SURS[NSURS] = {0, 16};
#define PMAX 7                     /* plans 0..6 */

static int K, L, S, N, CANAL, PFIN;
static uint16_t *m16;               /* N masques mod 16 */
static uint64_t *m64;               /* N masques mod 64 */
/* tab[(t*NSURS+q)*4 + (p-3)][low] : bit p de r permis, sachant low = bits 1..p-1 ;
   0 mort, 1 force 0, 2 force 1, 3 libre */
static uint8_t *tab;
static uint64_t *alpha;             /* forme F2 de chaque mot (L bits) */
static int nmots;
static uint64_t n_vides, n_gauss[PMAX], n_surv;

static double now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + 1e-9 * ts.tv_nsec;
}

/* ---- Gauss incrémental sur F_2^L (+1 bit de second membre en position L) ---- */
typedef struct { uint64_t piv[MAXL]; int rang; } gauss_t;

static inline void g_init(gauss_t *g) { g->rang = 0; memset(g->piv, 0, sizeof(g->piv)); }

/* ajoute l'équation row (bits 0..L-1 : coefficients, bit L : second membre) ;
   rend 0 si contradiction, 1 sinon */
static inline int g_add(gauss_t *g, uint64_t row) {
    for (int j = 0; j < L; j++) {
        if (!((row >> j) & 1)) continue;
        if (g->piv[j]) { row ^= g->piv[j]; continue; }
        g->piv[j] = row;
        g->rang++;
        return 1;
    }
    return (row >> L) == 0;       /* 0 = c avec c != 0 : contradiction */
}

/* énumère les solutions (au plus max, au plus 2^20) dans sols ; rend leur nombre */
static int g_solutions(gauss_t *g, uint64_t *sols, int max) {
    for (int j = L - 1; j >= 0; j--) {
        if (!g->piv[j]) continue;
        for (int i = 0; i < L; i++)
            if (i != j && g->piv[i] && ((g->piv[i] >> j) & 1)) g->piv[i] ^= g->piv[j];
    }
    int libres[MAXL], nl = 0;
    for (int j = 0; j < L; j++) if (!g->piv[j]) libres[nl++] = j;
    if (nl > 20) nl = 20;
    int n = 0;
    for (uint64_t m = 0; m < (1ULL << nl) && n < max; m++) {
        uint64_t x = 0;
        for (int q = 0; q < nl; q++) if ((m >> q) & 1) x |= 1ULL << libres[q];
        for (int j = 0; j < L; j++) {
            if (!g->piv[j]) continue;
            uint64_t row = g->piv[j];
            uint64_t v = (row >> L) & 1;
            for (int q = 0; q < nl; q++)
                if ((row >> libres[q]) & 1) v ^= (x >> libres[q]) & 1;
            x |= v << j;
        }
        sols[n++] = x;
    }
    return n;
}

/* ---- vérification d'un état bas mod 2^PFIN sur tous les mots sûrs ---- */
static int verifie(const uint8_t *init) {
    uint8_t *r = malloc(nmots);
    unsigned M = (1u << PFIN) - 1;
    for (int i = 0; i < L; i++) r[i] = init[i] & M;
    for (int i = L; i < nmots; i++) r[i] = (r[i - K] + r[i - L]) & M;
    int ok = 1;
    for (int t = 0; t < N && ok; t++)
        for (int q = 0; q < NSURS; q++) {
            int i = t * S + SURS[q];
            unsigned u = r[i] >> 1;
            int permis = (q == 1 && CANAL == 6) ? (int)((m64[t] >> (u & 63)) & 1)
                                                : (int)((m16[t] >> (u & 15)) & 1);
            if (!permis) { ok = 0; break; }
        }
    free(r);
    return ok;
}

/* ---- étage p (3..PFIN-1) : r contient les mots mod 2^p ; résout le plan p, récurse ---- */
static void etage(int p, const uint8_t *r_in) {
    if (p < 3 || p >= PMAX || L < 1 || L > MAXL) return;   /* borne la récursion */
    uint8_t *r = malloc(nmots), *g = malloc(nmots);
    memcpy(r, r_in, L);
    for (int j = 0; j < L; j++) g[j] = 0;
    unsigned M = (1u << p) - 1;
    for (int i = L; i < nmots; i++) {
        unsigned s = (unsigned)(r[i - K] & M) + (r[i - L] & M);
        r[i] = s & M;
        g[i] = g[i - K] ^ g[i - L] ^ (uint8_t)(s >> p);
    }
    gauss_t G; g_init(&G);
    int ok = 1;
    for (int t = 0; t < N && ok; t++)
        for (int q = 0; q < NSURS; q++) {
            int i = t * S + SURS[q];
            unsigned low = (r[i] >> 1) & ((1u << (p - 1)) - 1);
            uint8_t c = tab[((t * NSURS + q) * 4 + (p - 3)) * 32 + low];
            if (c == 3) continue;
            if (c == 0) { ok = 0; break; }
            uint64_t row = alpha[i] | ((uint64_t)((c >> 1) ^ g[i]) << L);
            if (!g_add(&G, row)) { ok = 0; break; }
        }
    if (!ok) { n_gauss[p]++; free(r); free(g); return; }
    static uint64_t sols[PMAX][1 << 12];
    int ns = g_solutions(&G, sols[p], 1 << 12);
    uint8_t init[MAXL];
    for (int a = 0; a < ns; a++) {
        for (int j = 0; j < L; j++) init[j] = (uint8_t)(r[j] | (((sols[p][a] >> j) & 1) << p));
        if (p + 1 < PFIN) { etage(p + 1, init); continue; }
        if (!verifie(init)) { fprintf(stderr, "INCOHERENT : solution non verifiee\n"); continue; }
        n_surv++;
        printf("BAS");
        for (int j = 0; j < L; j++) printf(" %u", init[j]);
        printf("\n");
    }
    free(r); free(g);
}

int main(int argc, char **argv) {
    if (argc < 8) { fprintf(stderr, "usage: %s K L S N masques.bin nlibre canal [r8 fixes...]\n", argv[0]); return 2; }
    K = atoi(argv[1]); L = atoi(argv[2]); S = atoi(argv[3]); N = atoi(argv[4]);
    int nlibre = atoi(argv[6]);
    CANAL = atoi(argv[7]);
    if (L > MAXL || K >= L || nlibre > L || (CANAL != 4 && CANAL != 6) || argc != 8 + (L - nlibre)) {
        fprintf(stderr, "arguments\n"); return 2;
    }
    PFIN = (CANAL == 6) ? 7 : 5;    /* plans 0..PFIN-1 dans l'état bas */
    m16 = malloc(sizeof(uint16_t) * N); m64 = malloc(sizeof(uint64_t) * N);
    FILE *f = fopen(argv[5], "rb");
    if (!f || fread(m16, sizeof(uint16_t), N, f) != (size_t)N || fread(m64, sizeof(uint64_t), N, f) != (size_t)N) {
        fprintf(stderr, "masques\n"); return 2;
    }
    fclose(f);
    nmots = (N - 1) * S + SURS[NSURS - 1] + 1;
    if (nmots < L) nmots = L;

    /* tables d'admissibilité : bit p de r sachant les bits 1..p-1 */
    tab = malloc((size_t)N * NSURS * 4 * 32);
    for (int t = 0; t < N; t++)
        for (int q = 0; q < NSURS; q++) {
            int six = (q == 1 && CANAL == 6);
            int nb = six ? 6 : 4;              /* bits publiés : 1..nb de r */
            uint64_t m = six ? m64[t] : (uint64_t)m16[t];
            for (int p = 3; p < 3 + 4; p++)
                for (unsigned low = 0; low < 32; low++) {
                    uint8_t c = 0;
                    if (p <= nb && low < (1u << (p - 1))) {
                        for (unsigned u = 0; u < (1u << nb); u++) {
                            if ((u & ((1u << (p - 1)) - 1)) != low) continue;
                            if ((m >> u) & 1) c |= 1 << ((u >> (p - 1)) & 1);
                        }
                    } else c = 3;              /* bit non publié par ce mot : libre */
                    tab[((t * NSURS + q) * 4 + (p - 3)) * 32 + low] = c;
                }
        }
    /* formes F2 */
    alpha = malloc(sizeof(uint64_t) * nmots);
    for (int i = 0; i < L; i++) alpha[i] = 1ULL << i;
    for (int i = L; i < nmots; i++) alpha[i] = alpha[i - K] ^ alpha[i - L];

    uint8_t *r8 = malloc(nmots), *g3 = malloc(nmots);
    uint8_t fixe[MAXL];
    for (int j = nlibre; j < L; j++) fixe[j] = (uint8_t)(atoi(argv[8 + j - nlibre]) & 7);

    uint64_t total = 1ULL << (3 * nlibre);
    double mots_cum = 0;
    double t0 = now();
    static uint64_t sols3[1 << 12];

    for (uint64_t c = 0; c < total; c++) {
        for (int j = 0; j < nlibre; j++) r8[j] = (c >> (3 * j)) & 7;
        for (int j = nlibre; j < L; j++) r8[j] = fixe[j];
        for (int j = 0; j < L; j++) g3[j] = 0;
        gauss_t G; g_init(&G);
        int calcule = L;              /* mots r8/g3 calculés jusqu'ici */
        int vivant = 1, mots_vus = 0;
        for (int t = 0; t < N && vivant; t++) {
            int fin = t * S + SURS[NSURS - 1] + 1;
            for (int i = calcule; i < fin; i++) {
                unsigned s = (unsigned)r8[i - K] + r8[i - L];
                r8[i] = s & 7;
                g3[i] = g3[i - K] ^ g3[i - L] ^ (uint8_t)(s >> 3);
            }
            if (fin > calcule) calcule = fin;
            for (int q = 0; q < NSURS; q++) {
                int i = t * S + SURS[q];
                mots_vus++;
                uint8_t cc = tab[((t * NSURS + q) * 4 + 0) * 32 + ((r8[i] >> 1) & 3)];
                if (cc == 3) continue;
                if (cc == 0) { vivant = 0; n_vides++; break; }
                uint64_t row = alpha[i] | ((uint64_t)((cc >> 1) ^ g3[i]) << L);
                if (!g_add(&G, row)) { vivant = 0; n_gauss[3]++; break; }
            }
        }
        mots_cum += mots_vus;
        if (!vivant) continue;
        int n3 = g_solutions(&G, sols3, 1 << 12);
        uint8_t init[MAXL];
        for (int a = 0; a < n3; a++) {
            for (int j = 0; j < L; j++) init[j] = (uint8_t)(r8[j] | (((sols3[a] >> j) & 1) << 3));
            etage(4, init);
        }
    }
    printf("FIN etats=%llu vides=%llu gauss3=%llu gauss4=%llu gauss5=%llu gauss6=%llu survivants=%llu mots_moyens=%.1f sec=%.3f\n",
           (unsigned long long)total, (unsigned long long)n_vides, (unsigned long long)n_gauss[3],
           (unsigned long long)n_gauss[4], (unsigned long long)n_gauss[5], (unsigned long long)n_gauss[6],
           (unsigned long long)n_surv, mots_cum / (double)total, now() - t0);
    return 0;
}
