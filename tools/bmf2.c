// bmf2 — Berlekamp-Massey sur F2, et le ppcm des polynômes minimaux.
//
// POURQUOI CE FICHIER EXISTE
// --------------------------
// Tout le dossier, du §105 au §121, procède par ÉNUMÉRATION : on nomme une
// famille, on écrit ses formes linéaires, on résout, on exclut. Onze mille
// systèmes, cinq axes de modèle, et trois de ces axes n'ont été trouvés
// qu'APRÈS COUP — chacun faisait échouer les attaques EN SILENCE.
//
//   Une exclusion par énumération ne vaut que pour ce qui a été énuméré.
//
// Ce fichier calcule à la place un INVARIANT. Si l'état évolue par s -> A·s
// sur F2^W et que le mot rendu est une fonction F2-linéaire de s, alors tout
// bit observé aux positions d'une PROGRESSION ARITHMÉTIQUE c + σi vérifie une
// récurrence linéaire de degré <= W — quels que soient A, W, σ, c, la
// fonction de sortie et l'échantillonneur. Berlekamp-Massey rend EXACTEMENT
// ce degré minimal pour la suite observée.
//
//   Un seul nombre teste alors toutes les familles F2-linéaires à la fois,
//   y compris celles que personne n'a publiées.
//
// LE PPCM
// -------
// Deux bits observés du même mot donnent deux suites b et b'. Leurs polynômes
// minimaux f et f' DIVISENT tous deux le polynôme caractéristique de A^σ,
// donc ppcm(f, f') le divise aussi :
//
//   W >= deg ppcm(f, f') = deg f + deg f' - deg pgcd(f, f').
//
// Sur un vrai générateur à polynôme irréductible (MT19937) f = f' et la borne
// vaut exactement W. Sur du hasard f et f' sont premiers entre eux et la
// borne vaut ~N : la portée du test DOUBLE sans coûter un bit de plus.
//
// FORMAT D'ENTRÉE
// ---------------
//   int32 nseq, int32 N, puis nseq blocs de ceil(N/64) uint64.
//   Le bit t de la suite j est le bit (t%64) du mot (t/64) du bloc j.
//
//   cc -O3 -march=native -o bmf2 tools/bmf2.c

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>

#define WPB(n) (((n) + 63) / 64)

static void *xcalloc(size_t n, size_t s) {
    void *p = calloc(n, s);
    if (!p) { fprintf(stderr, "memoire\n"); exit(3); }
    return p;
}

static inline int bit_de(const uint64_t *a, long i) { return (a[i >> 6] >> (i & 63)) & 1; }
static inline void met_bit(uint64_t *a, long i) { a[i >> 6] |= 1ULL << (i & 63); }

// degré du polynôme empaqueté (-1 si nul)
static long degre(const uint64_t *a, long nw) {
    for (long i = nw - 1; i >= 0; i--)
        if (a[i]) return i * 64 + 63 - __builtin_clzll(a[i]);
    return -1;
}

// C ^= B << m,  B de bw mots, C de cw mots
static void xor_decale(uint64_t *C, long cw, const uint64_t *B, long bw, long m) {
    long ws = m >> 6, bs = m & 63;
    for (long i = bw - 1; i >= 0; i--) {
        uint64_t v = B[i];
        if (!v) continue;
        long j = i + ws;
        if (j < cw) C[j] ^= v << bs;
        if (bs && j + 1 < cw) C[j + 1] ^= v >> (64 - bs);
    }
}

// parité de sum_{i=0..L} C_i & R_{start+i}   (R doit avoir 2 mots de marge)
static inline int produit_parite(const uint64_t *C, const uint64_t *R, long start, long L) {
    long ws = start >> 6, bs = start & 63;
    long nw = (L >> 6) + 1;
    uint64_t acc = 0;
    if (bs == 0) {
        for (long i = 0; i < nw; i++) acc ^= C[i] & R[ws + i];
    } else {
        for (long i = 0; i < nw; i++) {
            uint64_t w = (R[ws + i] >> bs) | (R[ws + i + 1] << (64 - bs));
            acc ^= C[i] & w;
        }
    }
    return __builtin_parityll(acc);
}

// Berlekamp-Massey sur F2. S : suite empaquetée de N bits.
// Rend la complexité linéaire L ; écrit le polynôme de connexion dans C
// (bit i = coefficient de x^i, C_0 = 1), qui doit tenir N/2+2 bits au moins.
static long bm_f2(const uint64_t *S, long N, uint64_t *C, long cw) {
    long nw = WPB(N);
    // R : la suite RENVERSÉE, pour que la fenêtre de convolution soit contiguë.
    uint64_t *R = xcalloc(nw + 2, 8);
    for (long t = 0; t < N; t++)
        if (bit_de(S, t)) met_bit(R, N - 1 - t);

    uint64_t *B = xcalloc(cw, 8), *T = xcalloc(cw, 8);
    memset(C, 0, cw * 8);
    C[0] = 1; B[0] = 1;
    long L = 0, m = 1;

    for (long n = 0; n < N; n++) {
        int d = produit_parite(C, R, N - 1 - n, L);
        if (!d) { m++; continue; }
        if (2 * L <= n) {
            memcpy(T, C, cw * 8);
            xor_decale(C, cw, B, cw, m);
            memcpy(B, T, cw * 8);
            L = n + 1 - L;
            m = 1;
        } else {
            xor_decale(C, cw, B, cw, m);
            m++;
        }
    }
    free(R); free(B); free(T);
    return L;
}

// a mod b sur F2, en place dans a
static void reste(uint64_t *a, long aw, const uint64_t *b, long bw) {
    long db = degre(b, bw);
    if (db < 0) return;
    for (;;) {
        long da = degre(a, aw);
        if (da < db) return;
        xor_decale(a, aw, b, bw, da - db);
    }
}

static long degre_pgcd(const uint64_t *f, long fw, const uint64_t *g, long gw) {
    long nw = fw > gw ? fw : gw;
    uint64_t *a = xcalloc(nw, 8), *b = xcalloc(nw, 8), *t = xcalloc(nw, 8);
    memcpy(a, f, fw * 8);
    memcpy(b, g, gw * 8);
    while (degre(b, nw) >= 0) {
        memcpy(t, a, nw * 8);
        reste(t, nw, b, nw);
        memcpy(a, b, nw * 8);
        memcpy(b, t, nw * 8);
    }
    long d = degre(a, nw);
    free(a); free(b); free(t);
    return d;
}

// --------------------------------------------------------------------------
// AUTOTEST : un LFSR de degré connu doit rendre EXACTEMENT ce degré.
// Une attaque qui ne retrouve pas son propre témoin ne prouve rien quand elle
// ne trouve rien.
// --------------------------------------------------------------------------
// splitmix64 : sortie BROUILLÉE, dim L = 0 au §119 — c'est notre « hasard ».
static uint64_t rng_s = 88172645463325252ULL;
static uint64_t rnd(void) {
    rng_s += 0x9E3779B97F4A7C15ULL;
    uint64_t z = rng_s;
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31);
}

// xorshift64, F2-linéaire : son bit bas doit rendre L = 64 EXACTEMENT.
static uint64_t xs_s = 88172645463325252ULL;
static uint64_t xs64(void) {
    xs_s ^= xs_s << 13; xs_s ^= xs_s >> 7; xs_s ^= xs_s << 17;
    return xs_s;
}

static int autotest(void) {
    int ok = 0, tot = 0;
    long degres[] = { 17, 88, 113, 128, 512, 1279, 4253 };
    for (unsigned k = 0; k < sizeof degres / sizeof *degres; k++) {
        long D = degres[k], N = 4 * D + 64;
        long L = -1;
        // Un P tire au hasard peut se factoriser et l'etat tomber dans un
        // sous-espace propre : alors L < D, et c'est BM qui a raison. On
        // retire jusqu'a obtenir un couple de complexite pleine.
        for (int essai = 0; essai < 12 && L != D; essai++) {
            long pw = WPB(D + 1);
            uint64_t *P = xcalloc(pw + 2, 8);
            for (long i = 1; i < D; i++) if (rnd() & 1) met_bit(P, i);
            met_bit(P, 0); met_bit(P, D);
            uint64_t *S = xcalloc(WPB(N) + 2, 8);
            uint8_t *etat = xcalloc(D, 1);
            for (long i = 0; i < D; i++) etat[i] = rnd() & 1;
            etat[0] |= 1;
            for (long t = 0; t < N; t++) {
                if (etat[0]) met_bit(S, t);
                int nb = 0;                       // s_{t+D} = sum P_i s_{t+D-i}
                for (long i = 1; i <= D; i++) if (bit_de(P, i) && etat[D - i]) nb ^= 1;
                memmove(etat, etat + 1, D - 1);
                etat[D - 1] = (uint8_t)nb;
            }
            long cw = WPB(N + 2) + 2;
            uint64_t *C = xcalloc(cw, 8);
            L = bm_f2(S, N, C, cw);
            free(P); free(S); free(etat); free(C);
            if (L > D) break;                     // violation de la borne
        }
        printf("  LFSR degre %5ld  -> L = %5ld  %s\n", D, L,
               L == D ? "EXACT" : (L < D ? "borne ok" : "ECHEC"));
        tot++; ok += (L == D);
    }
    // suite aléatoire : L doit valoir ~N/2
    {
        long N = 20000;
        uint64_t *S = xcalloc(WPB(N) + 2, 8);
        for (long t = 0; t < N; t++) if (rnd() & 1) met_bit(S, t);
        long cw = WPB(N + 2) + 2;
        uint64_t *C = xcalloc(cw, 8);
        long L = bm_f2(S, N, C, cw);
        int bon = (L > N / 2 - 60 && L < N / 2 + 60);
        printf("  hasard   N = %5ld  -> L = %5ld  (attendu ~%ld)  %s\n",
               N, L, N / 2, bon ? "OK" : "ECHEC");
        tot++; ok += bon;
        free(S); free(C);
    }
    // LE THÉORÈME EN VIVO : le bit BAS de xorshift64, pris un mot sur SEPT,
    // doit rendre L = 64 — la largeur de l'état, sans qu'on ait dit à BM ni
    // les décalages, ni le pas, ni même qu'il s'agissait d'un xorshift.
    {
        long N = 4000;
        uint64_t *S = xcalloc(WPB(N) + 2, 8);
        for (long t = 0; t < N; t++) {
            uint64_t w = 0;
            for (int k = 0; k < 7; k++) w = xs64();
            if (w & 1) met_bit(S, t);
        }
        long cw = WPB(N + 2) + 2;
        uint64_t *C = xcalloc(cw, 8);
        long L = bm_f2(S, N, C, cw);
        printf("  xorshift64 bit bas, pas 7 -> L = %ld  (etat = 64)  %s\n",
               L, L <= 64 ? "OK" : "ECHEC");
        tot++; ok += (L <= 64);
        free(S); free(C);
    }
    // pgcd : deux polynômes de facteur commun connu
    {
        long nw = 8;
        uint64_t *f = xcalloc(nw, 8), *g = xcalloc(nw, 8);
        // f = x^10 + x^3 + 1 ; g = f * (x^5 + x^2 + 1) -> pgcd de degre 10
        met_bit(f, 10); met_bit(f, 3); met_bit(f, 0);
        long h[] = { 5, 2, 0 };
        for (unsigned i = 0; i < 3; i++) xor_decale(g, nw, f, nw, h[i]);
        long d = degre_pgcd(f, nw, g, nw);
        printf("  pgcd(f, f*h) = degre %ld  (attendu 10)  %s\n",
               d, d == 10 ? "OK" : "ECHEC");
        tot++; ok += (d == 10);
        free(f); free(g);
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
    int32_t nseq, N;
    if (fread(&nseq, 4, 1, fh) != 1 || fread(&N, 4, 1, fh) != 1) return 2;
    long nw = WPB(N), cw = WPB(N / 2 + 2) + 2;

    uint64_t **C = xcalloc(nseq, sizeof *C);
    long *L = xcalloc(nseq, sizeof *L);
    uint64_t *S = xcalloc(nw + 2, 8);
    clock_t t0 = clock();
    for (int j = 0; j < nseq; j++) {
        memset(S, 0, (nw + 2) * 8);
        if ((long)fread(S, 8, nw, fh) != nw) return 2;
        C[j] = xcalloc(cw, 8);
        L[j] = bm_f2(S, N, C[j], cw);
        printf("L %d %ld\n", j, L[j]);
    }
    fclose(fh);

    for (int i = 0; i < nseq; i++)
        for (int j = i + 1; j < nseq; j++) {
            long dg = degre_pgcd(C[i], cw, C[j], cw);
            printf("PPCM %d %d pgcd=%ld ppcm=%ld\n", i, j, dg, L[i] + L[j] - dg);
        }
    printf("N=%d nseq=%d sec=%.2f\n", N, nseq, (double)(clock() - t0) / CLOCKS_PER_SEC);
    return 0;
}
