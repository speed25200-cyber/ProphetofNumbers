/* multibm — plusieurs suites, une seule récurrence : la borne de Berlekamp-Massey levée.
 *
 * bm.c écarte les générateurs F2-linéaires d'état < 35 280 bits, et la borne est
 * intrinsèque : une suite de N bits ne détermine une complexité linéaire que jusqu'à N/2.
 * WELL44497 (44 497 bits) passe juste au-dessus. La lever en le nommant reviendrait à
 * l'énumération que ce test existait pour éviter.
 *
 * Mais il n'y a pas qu'une suite. Pour un générateur F2-linéaire, TOUTE fonctionnelle
 * linéaire de l'état satisfait la MÊME récurrence minimale. Les 4 plans de bits k-libres
 * du rang (32 sous mulhi) sont donc m suites différentes obéissant à une seule et même
 * loi inconnue d'ordre L. Avec m suites de longueur N, il faut m(N−L) ≥ L équations, soit
 *
 *     L <= m·N/(m+1)   ->   56 448 pour m=4, 68 422 pour m=32
 *
 * au lieu de N/2 = 35 280. WELL44497 rentre.
 *
 * Le test n'est pas de TROUVER la récurrence mais de savoir si elle peut exister :
 * le système M·c = b sur GF(2) est-il consistant ? Une seule ligne se réduisant à
 * « 0 = 1 » prouve qu'aucune récurrence de cet ordre n'existe, quelle qu'elle soit.
 *
 *   ./multibm selftest
 *   ./multibm <L> <fichier de bits> [fichier ...]
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

typedef uint64_t u64;
static int W;                      /* words per row, covering L coefficients + 1 rhs */
static int L;
static u64 **PIV;                  /* PIV[c] = row whose leading coefficient column is c */
static long NPIV;

static inline int getbit(const u64 *r, int i){ return (r[i>>6] >> (i&63)) & 1; }
static inline void setbit(u64 *r, int i){ r[i>>6] |= 1ULL << (i&63); }

/* returns 1 if the row is consistent with the system (and installs it), 0 if it proves
   inconsistency — a row reducing to all-zero coefficients with a nonzero right-hand side */
static int absorb(u64 *r){
  for(int c = 0; c < L; c++){
    if(!getbit(r, c)) continue;
    if(PIV[c]){ for(int w = 0; w < W; w++) r[w] ^= PIV[c][w]; continue; }
    u64 *keep = malloc(W * 8); memcpy(keep, r, W * 8);
    PIV[c] = keep; NPIV++;
    return 1;
  }
  return getbit(r, L) ? 0 : 1;     /* all coefficients cancelled: 0 = rhs */
}

/* feed the rows of one sequence: row i has coefficients s[i-1..i-L], rhs s[i] */
static long feed(const unsigned char *s, long n, long *rows, int *bad){
  u64 *r = calloc(W, 8);
  for(long i = L; i < n; i++){
    memset(r, 0, W * 8);
    for(int k = 1; k <= L; k++) if(s[i-k]) setbit(r, k-1);
    if(s[i]) setbit(r, L);
    (*rows)++;
    if(!absorb(r)){ *bad = 1; free(r); return i; }
  }
  free(r);
  return -1;
}

static unsigned char *readbits(const char *fn, long *n){
  FILE *f = fopen(fn, "rb"); if(!f){ perror(fn); exit(1); }
  fseek(f, 0, SEEK_END); long sz = ftell(f); fseek(f, 0, SEEK_SET);
  unsigned char *b = malloc(sz);
  if((long)fread(b, 1, sz, f) != sz){ fprintf(stderr, "short read\n"); exit(1); }
  fclose(f); *n = sz; return b;
}

static void setup(int order){
  L = order; W = (L + 1 + 63) / 64;
  PIV = calloc(L, sizeof(u64*)); NPIV = 0;
}
static void teardown(void){
  for(int c = 0; c < L; c++) free(PIV[c]);
  free(PIV);
}

/* ---- controls: a planted LFSR of known order, and random bits ---- */
static void lfsr_planes(int order, long n, int m, unsigned char **out){
  /* an order-`order` F2-linear generator; every output bit is a linear functional of the
     state, so all m planes obey the same recurrence — exactly the premise under test */
  int words = (order + 63) / 64;
  u64 *st = calloc(words, 8), *tap = calloc(words, 8);
  u64 z = 0x9E3779B97F4A7C15ULL;
  for(int i = 0; i < words; i++){ z = z*6364136223846793005ULL + 1; st[i] = z; }
  for(int i = 0; i < words; i++){ z = z*6364136223846793005ULL + 1; tap[i] = z; }
  tap[0] |= 1;
  for(long i = 0; i < n; i++){
    for(int j = 0; j < m; j++){
      int bitpos = (j * 7 + 3) % order;             /* m different linear functionals */
      out[j][i] = (st[bitpos>>6] >> (bitpos&63)) & 1;
    }
    u64 fb = 0;
    for(int w = 0; w < words; w++) fb ^= st[w] & tap[w];
    int b = __builtin_parityll(fb);
    for(int w = words-1; w > 0; w--) st[w] = (st[w]<<1) | (st[w-1]>>63);
    st[0] = (st[0]<<1) | (u64)b;
  }
  free(st); free(tap);
}

int main(int argc, char **argv){
  if(argc > 1 && !strcmp(argv[1], "selftest")){
    printf("selftest: with m sequences obeying ONE recurrence of order R, the system must\n");
    printf("  be consistent for L >= R and inconsistent for L < R. That two-sided cut is\n");
    printf("  the whole test: an inconsistency PROVES no recurrence of that order exists.\n\n");
    /* a multiple of 64: the state is held in whole words, so the true recurrence order
       is the ROUNDED size. Using 3000 made the cut land at 3008 and looked like an
       off-by-one in the test when it was an off-by-one in my expectation. */
    int R = 3008, m = 4; long n = 6000;
    unsigned char **pl = malloc(m * sizeof(void*));
    for(int j = 0; j < m; j++) pl[j] = malloc(n);
    lfsr_planes(R, n, m, pl);
    for(int order = R - 64; order <= R + 64; order += 64){
      setup(order);
      long rows = 0; int bad = 0;
      for(int j = 0; j < m && !bad; j++) feed(pl[j], n, &rows, &bad);
      printf("  planted order %d, tested at L=%4d : %-34s (rank %ld, %ld rows)  %s\n",
             R, order, bad ? "INCONSISTENT — no such recurrence" : "consistent",
             NPIV, rows, (order < R) == (bad != 0) ? "as it must" : "UNEXPECTED");
      teardown();
    }
    /* the same lengths, but random bits: must be inconsistent at every order */
    u64 z = 0xABCDEF12345ULL;
    for(int j = 0; j < m; j++)
      for(long i = 0; i < n; i++){ z = z*6364136223846793005ULL + 1; pl[j][i] = (z>>33)&1; }
    for(int order = R - 64; order <= R + 64; order += 64){
      setup(order);
      long rows = 0; int bad = 0;
      for(int j = 0; j < m && !bad; j++) feed(pl[j], n, &rows, &bad);
      printf("  random bits,     tested at L=%4d : %-34s (rank %ld, %ld rows)  %s\n",
             order, bad ? "INCONSISTENT — no such recurrence" : "consistent", NPIV, rows,
             bad ? "as it must" : "UNEXPECTED");
      teardown();
    }
    for(int j = 0; j < m; j++) free(pl[j]);
    free(pl);
    return 0;
  }
  if(argc < 3){ fprintf(stderr, "usage: multibm <L> <bitfile> [bitfile ...]\n"); return 1; }
  int order = atoi(argv[1]);
  int m = argc - 2;
  setup(order);
  printf("order L = %d, %d sequences; a recurrence of this order needs %d equations,\n",
         order, m, order);
  long rows = 0; int bad = 0; long where = -1;
  for(int j = 0; j < m && !bad; j++){
    long n; unsigned char *s = readbits(argv[2+j], &n);
    if(j == 0) printf("  each of length %ld, so %d sequences give %ld  ->  %s\n",
                      n, m, (long)m*(n-order), (long)m*(n-order) >= order ? "enough" : "NOT ENOUGH");
    where = feed(s, n, &rows, &bad);
    free(s);
  }
  printf("  rows fed %ld, rank %ld%s\n", rows, NPIV,
         bad ? "" : "   (system still consistent)");
  if(bad) printf("  *** INCONSISTENT at row %ld — NO F2-linear recurrence of order <= %d ***\n",
                 where, order);
  else printf("  consistent: a recurrence of order <= %d is not excluded by these rows\n", order);
  teardown();
  return 0;
}
