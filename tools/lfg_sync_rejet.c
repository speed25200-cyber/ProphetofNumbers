/* lfg_sync_rejet — h145 : la SYNCHRONISATION sous le REJET (pas variable), THEORIE_ETAT §7.17.
 *
 * Chaine cachee sur les positions d'une (ou de plusieurs) sequence(s) de bits periodique(s) :
 *   shift 0 : la m-sequence du plan 0 du Fibonacci retarde additif r_i = r_{i-K} + r_{i-L}
 *             (trinome primitif), une sequence de periode P = 2^L - 1 ;
 *   shift 1 : le plan 1 (bit 1 de r, sortie glibc r >> 1) : les 2^(L-1) orbites de periode 2P
 *             du Fibonacci mod 4 dont le plan 0 n'est pas nul ;
 *   alt     : la sequence alternee 0101... (tout LCG mod 2^k a increment impair, sortie = etat).
 * Le tirage t consomme n in [20, 40] mots ; sa vraisemblance exacte est T_{a0}[n][b, w1]
 * (a0 = nombre de numeros impairs tires, w1 = nombre de bits 1 de la fenetre, b = dernier bit) :
 *   P(A, n | fenetre) = F(w_{1-b}, a_{1-b}) G(w_b, a_b), F(w,a) = a! S(w,a)/40^w,
 *   G(w,a) = a! S(w-1,a-1)/40^w (Stirling de seconde espece).
 *   alpha_t[(q+n) mod Pi] += alpha_{t-1}[q] T[n][idx(q, n)] ; BF_t = prod_t (sum alpha_t) C(80,20)^t
 * Deux chaines en parallele : FLUX (jamais remise a l'uniforme) et BLOC (remise a l'uniforme au
 * debut de chaque bloc de nuit). Evasion eps par tirage : alpha <- (1-eps) alpha + eps/N.
 * Sous H0 chaque BF_t est une martingale de moyenne 1 : Ville, P0(sup BF >= 1/a) <= a.
 *
 * usage : lfg_sync_rejet K L shift(0|1|alt) fichier_a0 fichier_blocs [eps] [pas_journal]
 *   fichier_a0    : un entier a0 in [0,20] par ligne (un tirage par ligne, dans l'ordre)
 *   fichier_blocs : indices (0-based) des tirages qui ouvrent un bloc, un par ligne
 * sortie : lignes "T t log2bf_flux max_flux tmax_flux log2bf_bloc max_bloc tmax_bloc" tous les
 *          pas_journal tirages, "BLOC b t0 n log2bf" par bloc, puis
 *          "FIN nseq Pi ntirages log2bf_flux max_flux tmax_flux log2bf_bloc max_bloc tmax_bloc
 *               maxbloc_log2bf bloc_maxbloc pic_seq pic_q pic_masse sec nimp_flux nimp_bloc".
 * Un tirage IMPOSSIBLE sous H1 (aucune fenetre de la sequence ne peut le produire : F(w, a) = 0
 * des que w < a) tue la chaine : log2 BF = -inf a jamais (compte dans nimp_*), le maximum courant
 * est fige ; alpha repart de l'uniforme pour que le calcul continue (cette reprise n'est PAS une
 * martingale : seul le maximum atteint AVANT la mort compte pour Ville, et il est fige).
 */
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define POOL 80
#define DRAWN 20
#define HALF 40
#define NMIN 20
#define NMAX 40
#define NW (NMAX + 1)

static double TAB[DRAWN + 1][NMAX + 1][2 * NW];   /* [a0][n][b*NW + w1] */
static double LOG2_C8020;

static void tables(void)
{
    /* Stirling S(w, a) exacts en long double (w <= 40, a <= 20 : < 1e45, exact a 1e-19 pres) */
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
#define FF(w, a) (((w) < (a) || ((a) == 0 && (w) > 0)) ? 0.0L : fact[a] * S[w][a] / pw[w])
#define GG(w, a) (((a) == 0 || (w) < (a)) ? 0.0L : fact[a] * S[(w) - 1][(a) - 1] / pw[w])
    for (int a0 = 0; a0 <= DRAWN; a0++) {
        int a1 = DRAWN - a0;
        for (int n = NMIN; n <= NMAX; n++)
            for (int w1 = 0; w1 <= n; w1++) {
                int w0 = n - w1;
                TAB[a0][n][w1] = (double)(FF(w1, a1) * GG(w0, a0));           /* dernier bit 0 */
                TAB[a0][n][NW + w1] = (double)(FF(w0, a0) * GG(w1, a1));      /* dernier bit 1 */
            }
    }
    long double c = 1;
    for (int i = 0; i < DRAWN; i++) c = c * (POOL - i) / (i + 1);
    LOG2_C8020 = (double)log2l(c);
}

/* ---- sequences ---------------------------------------------------------- */

static int nseq, Pi;
static uint8_t *seqs;       /* nseq x Pi */

static void m_sequence(int K, int L)
{
    Pi = (1 << L) - 1;
    nseq = 1;
    seqs = calloc((size_t)Pi + L, 1);
    seqs[0] = 1;
    for (int i = L; i < Pi + L; i++) seqs[i] = seqs[i - K] ^ seqs[i - L];
    for (int i = 0; i < L; i++)
        if (seqs[Pi + i] != seqs[i]) { fprintf(stderr, "periode fausse\n"); exit(2); }
}

static void orbites_mod4(int K, int L)
{
    int P = (1 << L) - 1;
    Pi = 2 * P;
    nseq = 1 << (L - 1);
    size_t netats = (size_t)1 << (2 * L);
    uint8_t *vu = calloc(netats, 1);
    seqs = malloc((size_t)nseq * Pi);
    int *r = malloc(sizeof(int) * (Pi + L));
    int no = 0;
    for (size_t rep = 0; rep < netats; rep++) {
        if (vu[rep]) continue;
        int impair = 0;
        for (int i = 0; i < L; i++) { r[i] = (int)((rep >> (2 * i)) & 3); impair |= r[i] & 1; }
        if (!impair) { vu[rep] = 1; continue; }              /* plan 0 nul : m-sequence pure (shift 0) */
        for (int i = L; i < Pi + L; i++) r[i] = (r[i - K] + r[i - L]) & 3;
        for (int i = 0; i < L; i++)
            if (r[Pi + i] != r[i]) { fprintf(stderr, "periode 2P fausse\n"); exit(2); }
        if (no >= nseq) { fprintf(stderr, "trop d'orbites\n"); exit(2); }
        for (int j = 0; j < Pi; j++) {
            size_t code = 0;
            for (int i = 0; i < L; i++) code |= (size_t)r[j + i] << (2 * i);
            if (vu[code]) { fprintf(stderr, "orbite non disjointe / periode < 2P\n"); exit(2); }
            vu[code] = 1;
            seqs[(size_t)no * Pi + j] = (uint8_t)((r[j] >> 1) & 1);
        }
        no++;
    }
    if (no != nseq) { fprintf(stderr, "%d orbites, %d attendues\n", no, nseq); exit(2); }
    free(vu);
    free(r);
}

static void alternee(void)
{
    Pi = 2;
    nseq = 1;
    seqs = malloc(2);
    seqs[0] = 0;
    seqs[1] = 1;
}

/* ---- la DP --------------------------------------------------------------- */

int main(int argc, char **argv)
{
    if (argc < 6) { fprintf(stderr, "usage : %s K L shift(0|1|alt) fichier_a0 fichier_blocs [eps] [pas_journal]\n", argv[0]); return 1; }
    int K = atoi(argv[1]), L = atoi(argv[2]);
    const char *sh = argv[3];
    double eps = argc > 6 ? atof(argv[6]) : 1e-3;
    int pasj = argc > 7 ? atoi(argv[7]) : 2000;
    clock_t c0 = clock();
    tables();
    if (!strcmp(sh, "alt")) alternee();
    else if (!strcmp(sh, "0")) m_sequence(K, L);
    else if (!strcmp(sh, "1")) orbites_mod4(K, L);
    else { fprintf(stderr, "shift ?\n"); return 1; }
    size_t N = (size_t)nseq * Pi;

    /* tirages */
    FILE *f = fopen(argv[4], "r");
    if (!f) { perror(argv[4]); return 1; }
    int cap = 1 << 16, nt = 0;
    int *a0 = malloc(sizeof(int) * cap);
    int v;
    while (fscanf(f, "%d", &v) == 1) {
        if (v < 0 || v > DRAWN) { fprintf(stderr, "a0 hors [0,20]\n"); return 1; }
        if (nt == cap) { cap *= 2; a0 = realloc(a0, sizeof(int) * cap); }
        a0[nt++] = v;
    }
    fclose(f);
    uint8_t *debut = calloc(nt + 1, 1);
    f = fopen(argv[5], "r");
    if (!f) { perror(argv[5]); return 1; }
    int nblocs = 0;
    while (fscanf(f, "%d", &v) == 1)
        if (v >= 0 && v < nt && !debut[v]) { debut[v] = 1; nblocs++; }
    fclose(f);
    if (!debut[0]) { debut[0] = 1; nblocs++; }

    /* index (b, w1) par n : idx[n - NMIN][s][q] */
    int NN = NMAX - NMIN + 1;
    uint8_t *idx = malloc((size_t)NN * N);
    int32_t *C = malloc(sizeof(int32_t) * (Pi + NMAX + 1));
    for (int s = 0; s < nseq; s++) {
        const uint8_t *sq = seqs + (size_t)s * Pi;
        C[0] = 0;
        for (int i = 0; i < Pi + NMAX; i++) C[i + 1] = C[i] + sq[i % Pi];
        for (int n = NMIN; n <= NMAX; n++) {
            uint8_t *ix = idx + ((size_t)(n - NMIN) * nseq + s) * Pi;
            for (int q = 0; q < Pi; q++)
                ix[q] = (uint8_t)(C[q + n] - C[q] + NW * sq[(q + n - 1) % Pi]);
        }
    }
    free(C);

    double *af = malloc(sizeof(double) * N), *ab = malloc(sizeof(double) * N);
    double *gf = malloc(sizeof(double) * N), *gb = malloc(sizeof(double) * N);
    for (size_t i = 0; i < N; i++) af[i] = ab[i] = 1.0 / N;
    double lf = 0, lb = 0, mf = 0, mb = 0, lbloc = 0, maxbloc = -INFINITY;
    int tmf = 0, tmb = 0, bloc = -1, t0bloc = 0, bmax = -1, nimpf = 0, nimpb = 0;
    double unif = eps / N, keep = 1.0 - eps;

    for (int t = 0; t < nt; t++) {
        if (debut[t]) {
            if (bloc >= 0) {
                printf("BLOC %d %d %d %.6f\n", bloc, t0bloc, t - t0bloc, lbloc);
                if (lbloc > maxbloc) { maxbloc = lbloc; bmax = bloc; }
            }
            bloc++;
            t0bloc = t;
            lbloc = 0;
            for (size_t i = 0; i < N; i++) ab[i] = 1.0 / N;
        }
        const double *T = TAB[a0[t]][0];
        memset(gf, 0, sizeof(double) * N);
        memset(gb, 0, sizeof(double) * N);
        for (int n = NMIN; n <= NMAX; n++) {
            const double *Tn = TAB[a0[t]][n];
            for (int s = 0; s < nseq; s++) {
                const uint8_t *ix = idx + ((size_t)(n - NMIN) * nseq + s) * Pi;
                const double *xf = af + (size_t)s * Pi, *xb = ab + (size_t)s * Pi;
                double *yf = gf + (size_t)s * Pi, *yb = gb + (size_t)s * Pi;
                if (n < Pi) {
                    int q = 0;
                    for (; q < Pi - n; q++) {
                        double w = Tn[ix[q]];
                        yf[q + n] += xf[q] * w;
                        yb[q + n] += xb[q] * w;
                    }
                    for (; q < Pi; q++) {
                        double w = Tn[ix[q]];
                        yf[q + n - Pi] += xf[q] * w;
                        yb[q + n - Pi] += xb[q] * w;
                    }
                } else {
                    for (int q = 0; q < Pi; q++) {
                        double w = Tn[ix[q]];
                        yf[(q + n) % Pi] += xf[q] * w;
                        yb[(q + n) % Pi] += xb[q] * w;
                    }
                }
            }
        }
        (void)T;
        double sf = 0, sb = 0;
        for (size_t i = 0; i < N; i++) { sf += gf[i]; sb += gb[i]; }
        if (sf > 0) {
            lf += log2(sf) + LOG2_C8020;
            double r = keep / sf;
            for (size_t i = 0; i < N; i++) af[i] = gf[i] * r + unif;
        } else {          /* aucun chemin : le tirage est IMPOSSIBLE sous H1, BF = 0 a jamais
                             (la chaine est morte ; on repart de l'uniforme pour la suite du calcul) */
            lf = -INFINITY;
            nimpf++;
            for (size_t i = 0; i < N; i++) af[i] = 1.0 / N;
        }
        if (sb > 0) {
            double d = log2(sb) + LOG2_C8020;
            lb += d;
            lbloc += d;
            double r = keep / sb;
            for (size_t i = 0; i < N; i++) ab[i] = gb[i] * r + unif;
        } else {
            lb = -INFINITY;
            lbloc = -INFINITY;
            nimpb++;
            for (size_t i = 0; i < N; i++) ab[i] = 1.0 / N;
        }
        if (lf > mf) { mf = lf; tmf = t + 1; }
        if (lb > mb) { mb = lb; tmb = t + 1; }
        if (pasj > 0 && (t + 1) % pasj == 0)
            printf("T %d %.4f %.4f %d %.4f %.4f %d\n", t + 1, lf, mf, tmf, lb, mb, tmb);
    }
    if (bloc >= 0) {
        printf("BLOC %d %d %d %.6f\n", bloc, t0bloc, nt - t0bloc, lbloc);
        if (lbloc > maxbloc) { maxbloc = lbloc; bmax = bloc; }
    }
    /* pic a posteriori (flux) : l'evasion melangee est retiree (af = gf r + unif) */
    size_t ip = 0;
    for (size_t i = 1; i < N; i++) if (af[i] > af[ip]) ip = i;
    double sec = (double)(clock() - c0) / CLOCKS_PER_SEC;
    printf("FIN %d %d %d %.4f %.4f %d %.4f %.4f %d %.4f %d %d %d %.6f %.2f %d %d\n", nseq, Pi, nt, lf, mf, tmf,
           lb, mb, tmb, maxbloc, bmax, (int)(ip / Pi), (int)(ip % Pi), af[ip], sec, nimpf, nimpb);
    return 0;
}
