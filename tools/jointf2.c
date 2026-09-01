// jointf2 — la complexité linéaire CONJOINTE de plusieurs suites sur F2,
//           par réduction de base sur F2[x] (forme faiblement de Popov).
//
// POURQUOI CE FICHIER EXISTE : IL RÉPARE UNE FAUTE DU §122
// --------------------------------------------------------
// Le §122 a mesuré, sur les deux bits exacts du rang du bonus, deux complexités
// linéaires L et L', puis a écrit
//
//     W  >=  deg ppcm(f, f')  =  L + L' - deg pgcd(f, f')          <-- FAUX
//
// C'est faux, et le contre-exemple est élémentaire. Sur une suite FINIE de N
// termes, Berlekamp-Massey rend le degré minimal d'un annulateur du PRÉFIXE ;
// ce polynôme ne divise le caractéristique du générateur que si N >= 2W. Pour
// W > N/2, un vrai générateur rend exactement L = N/2 — indiscernable du
// hasard. Vérifié : un LFSR de degré 400 observé sur 560 termes rend 280.
//
//     Le ppcm de deux annulateurs du préfixe MAJORE la borne conjointe ;
//     il ne la MINORE pas. Le §122 lisait l'inégalité à l'envers.
//
// CE QUI EST VRAI, ET CE QUE CE FICHIER CALCULE
// ---------------------------------------------
// Si un générateur de largeur W a produit les M suites, son polynôme
// caractéristique khi (degré <= W) annule les M préfixes A LA FOIS. Donc
//
//     W  >=  L_conjointe  =  min { deg g : g annule les M préfixes }.
//
// C'est une borne RIGOUREUSE pour tout W, et elle vaut ~2N/3 pour M = 2 sur du
// hasard (contre N/2 pour une seule suite) : le comptage donne dim > 0 dès que
// d + 1 > M(N - d), soit d > MN/(M+1).
//
// COMMENT ON LA CALCULE
// ---------------------
// g de degré <= d annule le préfixe de b ssi, en notant R le RENVERSÉ de b,
//
//     (g^ · R  mod x^N)  a un degré < d,        g^ = renversé de g.
//
// L'ensemble des (g^, rho_0, .., rho_{M-1}) tels que g^·R_j = rho_j mod x^N est
// un module LIBRE de rang M+1 sur F2[x], engendré par
//
//     (1, R_0, .., R_{M-1}),   (0, x^N, 0, ..),   ...,  (0, .., 0, x^N).
//
// On cherche l'élément minimisant le degré DÉCALÉ max(deg g^, deg rho_j + 1) —
// exactement L_conjointe. L'algorithme de Mulders-Storjohann réduit la base en
// forme faiblement de Popov (pivots distincts) ; la propriété de degré
// prévisible garantit alors que le minimum sur les LIGNES est le minimum sur
// tout le module. Chaque étape fait strictement décroître la somme des degrés
// décalés, donc l'algorithme termine en au plus ~(M+1)N étapes.
//
// AUTOTEST
// --------
// `--selftest` vérifie trois choses : pour M = 1 le résultat coïncide avec
// Berlekamp-Massey (c'est la formulation euclidienne classique) ; sur un LFSR
// planté de degré D observé assez longtemps, il rend D ; et sur M = 2 suites
// indépendantes il rend ~2N/3 et non ~N/2.
//
//   cc -O3 -march=native -o jointf2 tools/jointf2.c

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>

#define MAXM 32

static long CAP;                       // mots par polynôme

static uint64_t *xalloc(void) {
    uint64_t *p = calloc(CAP, 8);
    if (!p) { fprintf(stderr, "memoire\n"); exit(3); }
    return p;
}

static inline int bit_de(const uint64_t *a, long i) { return (a[i >> 6] >> (i & 63)) & 1; }
static inline void met_bit(uint64_t *a, long i) { a[i >> 6] |= 1ULL << (i & 63); }

static long degre(const uint64_t *a) {
    for (long i = CAP - 1; i >= 0; i--)
        if (a[i]) return i * 64 + 63 - __builtin_clzll(a[i]);
    return -1;                          // polynôme nul
}

// u ^= v << k
static void xor_decale(uint64_t *u, const uint64_t *v, long k) {
    long ws = k >> 6, bs = k & 63;
    for (long i = CAP - 1 - ws; i >= 0; i--) {
        uint64_t x = v[i];
        if (!x) continue;
        u[i + ws] ^= x << bs;
        if (bs && i + ws + 1 < CAP) u[i + ws + 1] ^= x >> (64 - bs);
    }
}

// ---------------------------------------------------------------------------
// La base : M+1 lignes, M+1 colonnes de polynômes. Décalage s = (0, 1, .., 1).
// ---------------------------------------------------------------------------
typedef struct {
    uint64_t **a;                       // a[ligne][colonne] -> polynôme
    long *dg;                           // degré de chaque entrée
    int M;
} base_t;

static inline long dec(int col) { return col == 0 ? 0 : 1; }

static long rowdeg(base_t *b, int i, int *pivot) {
    long best = -1;
    int piv = 0;
    for (int c = 0; c <= b->M; c++) {
        long d = b->dg[i * (b->M + 1) + c];
        if (d < 0) continue;
        long sd = d + dec(c);
        if (sd >= best) { best = sd; piv = c; }   // égalité -> plus grand indice
    }
    if (pivot) *pivot = piv;
    return best;
}

// Renvoie le degré décalé minimal du module = la complexité conjointe.
static long complexite_conjointe(const uint64_t **R, int M, long N, long *nsteps) {
    base_t b;
    b.M = M;
    b.a = malloc((M + 1) * sizeof *b.a);
    b.dg = malloc((M + 1) * (M + 1) * sizeof *b.dg);
    for (int i = 0; i <= M; i++) {
        b.a[i] = malloc((M + 1) * sizeof(uint64_t *));
        for (int c = 0; c <= M; c++) ((uint64_t **)b.a[i])[c] = xalloc();
    }
#define ENT(i, c) (((uint64_t **)b.a[i])[c])
    // ligne 0 : (1, R_0, .., R_{M-1})
    ENT(0, 0)[0] = 1;
    for (int j = 0; j < M; j++) memcpy(ENT(0, j + 1), R[j], CAP * 8);
    // lignes 1..M : (0, .., x^N, .., 0)
    for (int j = 0; j < M; j++) met_bit(ENT(j + 1, j + 1), N);
    for (int i = 0; i <= M; i++)
        for (int c = 0; c <= M; c++) b.dg[i * (M + 1) + c] = degre(ENT(i, c));

    long pas = 0;
    for (;;) {
        int piv[MAXM + 1];
        long rd[MAXM + 1];
        for (int i = 0; i <= M; i++) rd[i] = rowdeg(&b, i, &piv[i]);
        int u = -1, v = -1;
        for (int i = 0; i <= M && u < 0; i++)
            for (int j = i + 1; j <= M; j++)
                if (piv[i] == piv[j]) {
                    if (rd[i] >= rd[j]) { u = i; v = j; } else { u = j; v = i; }
                    break;
                }
        if (u < 0) break;                          // pivots distincts : terminé
        long k = b.dg[u * (M + 1) + piv[u]] - b.dg[v * (M + 1) + piv[v]];
        for (int c = 0; c <= M; c++) {
            if (b.dg[v * (M + 1) + c] < 0) continue;
            xor_decale(ENT(u, c), ENT(v, c), k);
        }
        for (int c = 0; c <= M; c++) b.dg[u * (M + 1) + c] = degre(ENT(u, c));
        pas++;
        if (pas > 8L * (M + 1) * (N + 8)) { fprintf(stderr, "non convergent\n"); exit(4); }
    }
    long best = -1;
    for (int i = 0; i <= M; i++) {
        long d = rowdeg(&b, i, NULL);
        if (best < 0 || d < best) best = d;
    }
    if (nsteps) *nsteps = pas;
    for (int i = 0; i <= M; i++) {
        for (int c = 0; c <= M; c++) free(ENT(i, c));
        free(b.a[i]);
    }
    free(b.a); free(b.dg);
#undef ENT
    return best;
}

// ---------------------------------------------------------------------------
// Berlekamp-Massey scalaire, pour confronter le cas M = 1.
// ---------------------------------------------------------------------------
static long bm_simple(const uint8_t *s, long N) {
    uint8_t *C = calloc(N + 2, 1), *B = calloc(N + 2, 1), *T = calloc(N + 2, 1);
    C[0] = B[0] = 1;
    long L = 0, m = 1;
    for (long n = 0; n < N; n++) {
        int d = s[n];
        for (long i = 1; i <= L; i++) d ^= C[i] & s[n - i];
        if (d) {
            memcpy(T, C, N + 2);
            for (long i = 0; i + m <= N + 1; i++) C[i + m] ^= B[i];
            if (2 * L <= n) { L = n + 1 - L; memcpy(B, T, N + 2); m = 1; }
            else m++;
        } else m++;
    }
    free(C); free(B); free(T);
    return L;
}

static uint64_t rs = 0x243F6A8885A308D3ULL;
static uint64_t rnd(void) {
    rs += 0x9E3779B97F4A7C15ULL;
    uint64_t z = rs;
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31);
}

static void empile(uint64_t *dst, const uint8_t *s, long N) {
    memset(dst, 0, CAP * 8);
    for (long t = 0; t < N; t++) if (s[N - 1 - t]) met_bit(dst, t);   // RENVERSÉ
}

static int autotest(void) {
    int ok = 0, tot = 0;

    // 1. M = 1 doit rendre exactement Berlekamp-Massey.
    for (int e = 0; e < 4; e++) {
        long N = 400 + 137 * e;
        CAP = (N + 128) / 64 + 4;
        uint8_t *s = malloc(N);
        for (long t = 0; t < N; t++) s[t] = rnd() & 1;
        uint64_t *R = xalloc(); empile(R, s, N);
        const uint64_t *tab[1] = { R };
        long j = complexite_conjointe(tab, 1, N, NULL), bmv = bm_simple(s, N);
        printf("  M=1  N=%4ld   conjointe=%4ld   Berlekamp-Massey=%4ld   %s\n",
               N, j, bmv, j == bmv ? "OK" : "ECHEC");
        tot++; ok += (j == bmv);
        free(s); free(R);
    }

    // 2. Deux bits d'un MÊME LFSR planté : la borne doit valoir D.
    for (int e = 0; e < 3; e++) {
        long D = 60 + 70 * e, N = 3 * D;
        CAP = (N + 128) / 64 + 4;
        uint8_t *P = calloc(D + 1, 1), *st = calloc(D, 1);
        for (long i = 1; i < D; i++) P[i] = rnd() & 1;
        P[0] = P[D] = 1;
        for (long i = 0; i < D; i++) st[i] = rnd() & 1;
        st[0] |= 1;
        uint8_t *b0 = malloc(N), *b1 = malloc(N);
        // deux fonctionnelles distinctes du même registre
        for (long t = 0; t < N; t++) {
            b0[t] = st[0];
            b1[t] = st[0] ^ st[D / 2] ^ st[D - 1];
            int nb = 0;
            for (long i = 1; i <= D; i++) if (P[i] && st[D - i]) nb ^= 1;
            memmove(st, st + 1, D - 1);
            st[D - 1] = (uint8_t)nb;
        }
        uint64_t *R0 = xalloc(), *R1 = xalloc();
        empile(R0, b0, N); empile(R1, b1, N);
        const uint64_t *tab[2] = { R0, R1 };
        long j = complexite_conjointe(tab, 2, N, NULL);
        printf("  M=2  LFSR degre %3ld, N=%4ld  ->  conjointe=%4ld  (attendu <= %ld)  %s\n",
               D, N, j, D, j <= D ? "OK" : "ECHEC");
        tot++; ok += (j <= D);
        free(P); free(st); free(b0); free(b1); free(R0); free(R1);
    }

    // 3. Deux suites INDÉPENDANTES : ~2N/3, et non ~N/2.
    for (int e = 0; e < 3; e++) {
        long N = 600 + 300 * e;
        CAP = (N + 128) / 64 + 4;
        uint8_t *b0 = malloc(N), *b1 = malloc(N);
        for (long t = 0; t < N; t++) { b0[t] = rnd() & 1; b1[t] = rnd() & 1; }
        uint64_t *R0 = xalloc(), *R1 = xalloc();
        empile(R0, b0, N); empile(R1, b1, N);
        const uint64_t *tab[2] = { R0, R1 };
        long j = complexite_conjointe(tab, 2, N, NULL);
        long att = (2 * N) / 3;
        int bon = (j > att - 40 && j < att + 40);
        printf("  M=2  hasard N=%4ld  ->  conjointe=%4ld  (attendu ~%ld, N/2=%ld)  %s\n",
               N, j, att, N / 2, bon ? "OK" : "ECHEC");
        tot++; ok += bon;
        free(b0); free(b1); free(R0); free(R1);
    }

    printf("autotest : %d/%d\n", ok, tot);
    return ok == tot ? 0 : 1;
}

int main(int argc, char **argv) {
    if (argc >= 2 && !strcmp(argv[1], "--selftest")) return autotest();
    if (argc < 2) {
        fprintf(stderr, "usage: %s <fichier>   |   %s --selftest\n", argv[0], argv[0]);
        return 2;
    }
    FILE *fh = fopen(argv[1], "rb");
    if (!fh) { perror("open"); return 2; }
    int32_t M, N;
    if (fread(&M, 4, 1, fh) != 1 || fread(&N, 4, 1, fh) != 1) return 2;
    if (M < 1 || M > MAXM) { fprintf(stderr, "M hors bornes\n"); return 2; }
    CAP = (N + 128) / 64 + 4;
    long nw = (N + 63) / 64;
    uint64_t *R[MAXM];
    uint64_t *tmp = calloc(nw + 2, 8);
    for (int j = 0; j < M; j++) {
        memset(tmp, 0, (nw + 2) * 8);
        if ((long)fread(tmp, 8, nw, fh) != nw) return 2;
        R[j] = xalloc();
        for (long t = 0; t < N; t++)              // on RENVERSE
            if (bit_de(tmp, N - 1 - t)) met_bit(R[j], t);
    }
    fclose(fh);
    clock_t t0 = clock();
    long pas = 0;
    long L = complexite_conjointe((const uint64_t **)R, M, N, &pas);
    printf("CONJOINTE %ld\nM=%d N=%d etapes=%ld sec=%.2f\n",
           L, M, N, pas, (double)(clock() - t0) / CLOCKS_PER_SEC);
    return 0;
}
