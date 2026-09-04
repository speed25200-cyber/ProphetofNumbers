/* lowlcg3 — the low-bit collapse with the increment unknown too.
 *
 * lowlcg fixes each family's increment to its standard constant. That leaves a real
 * caveat: an operator who kept a well-known multiplier but chose their own increment
 * escapes it. This lifts that.
 *
 * Enumerating (state, increment) naively is 2^2L, which is 2^40 for java — too much.
 * But the first two draws already pin four bits of x0 and four bits of x1, so only
 * 2^(L-4) x 2^(L-4) = 2^32 pairs are worth visiting, and each pair *determines* the
 * increment: C = x1 - A*x0 (mod 2^L). The remaining draws then check it. So the
 * unknown increment costs a squaring of the narrow search, not of the whole state.
 *
 * ---------------------------------------------------------------------------------
 * What the observable can and cannot determine, and why the control is written the
 * way it is.
 *
 * With the increment free the pair (x0, C) is NOT identifiable, and the reason is
 * exact rather than statistical. Write u = A - 1. From
 *
 *     x_k = A^k x0 + C (A^k - 1) / u
 *
 * substitute x0 -> x0 + d and C -> C - u d:
 *
 *     A^k (x0 + d) + (C - u d)(A^k - 1)/u = A^k x0 + C(A^k - 1)/u + A^k d - d(A^k - 1)
 *                                         = x_k + d.
 *
 * So that substitution translates the WHOLE orbit by exactly d, at every step, forever.
 * The observable is one nibble of each x_k, so every d small enough that no observed
 * x_k is pushed across a nibble boundary is perfectly indistinguishable from d = 0.
 * There are thousands of such d — for java at L=20 the measured family is 9515 members,
 * and 9515 is also the total survivor count, i.e. the search finds the translation
 * family and nothing else.
 *
 * That is not a failure. A translated orbit emits the same nibbles going forward too,
 * which is precisely what a prediction attack wants. Demanding exact recovery of
 * (state, increment) asks the observable for something it does not carry. So the
 * control asks for what does matter:
 *
 *   1. the planted pair must be among the survivors           (nothing is lost)
 *   2. every survivor must lie in the translation family      (nothing spurious is found)
 *   3. the survivors must PREDICT held-out future nibbles     (the result is usable)
 *
 * and the negative controls must still come back empty (a wrong W, and random nibbles).
 *
 *   ./lowlcg3 selftest      plant a state AND a non-standard increment, recover both
 *   ./lowlcg3 real [maxW]
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

typedef struct { const char *name; uint64_t a; int M, shift; } LCGA;
static const LCGA FAM[] = {
  {"java multiplier",     25214903917ULL, 48, 16},
  {"MSVC multiplier",     214013ULL,      32, 16},
  {"glibc LCG multiplier",1103515245ULL,  31, 12},
  {"Borland multiplier",  22695477ULL,    32, 16},
};
#define NFAM ((int)(sizeof FAM / sizeof FAM[0]))

static uint32_t N, *IDS, *TS; static uint8_t *NUMS, *BOOST, *BONUS;
static void loadbin(void){
  FILE *f = fopen("draws.bin", "rb"); if(!f || fread(&N,4,1,f)!=1){ perror("draws.bin"); exit(1); }
  IDS=malloc(4*N); TS=malloc(4*N);
  uint64_t *LO=malloc(8*N), *HI=malloc(8*N);
  NUMS=malloc(20*N); BOOST=malloc(N); BONUS=malloc(N);
  if(fread(IDS,4,N,f)!=N||fread(TS,4,N,f)!=N||fread(LO,8,N,f)!=N||fread(HI,8,N,f)!=N||
     fread(NUMS,20,N,f)!=N||fread(BOOST,1,N,f)!=N||fread(BONUS,1,N,f)!=N){
    fprintf(stderr,"short read\n"); exit(1); }
  fclose(f); free(LO); free(HI);
}
static inline int nib(int d, int first){ return (BONUS[first+d]-1) & 15; }

/* survivors are kept so the control can check what they are, not just how many */
#define SVMAX 400000
static uint64_t SV_S[SVMAX], SV_C[SVMAX];
static long long NSV;

/* A = a^W mod 2^L; the per-draw increment C is derived per candidate pair, not assumed */
static long long search(const LCGA *g, int W, int ndraws, const int *obs, int keep){
  int L = g->shift + 4;
  uint64_t mask = (1ULL << L) - 1;
  uint64_t A = 1; for(int i=0;i<W;i++) A = (A * g->a) & mask;
  int sh = g->shift;
  uint64_t lowmask = (sh == 0) ? 0 : ((1ULL << sh) - 1);
  uint64_t himask  = mask >> (sh + 4);
  uint64_t n0 = (uint64_t)obs[0] << sh, n1 = (uint64_t)obs[1] << sh;
  long long hits = 0;
  if(keep) NSV = 0;
  for(uint64_t h0 = 0; ; h0++){
    for(uint64_t l0 = 0; ; l0++){
      uint64_t x0 = ((h0 << (sh+4)) | n0 | l0) & mask;
      uint64_t Ax0 = (A * x0) & mask;
      for(uint64_t h1 = 0; ; h1++){
        for(uint64_t l1 = 0; ; l1++){
          uint64_t x1 = ((h1 << (sh+4)) | n1 | l1) & mask;
          uint64_t C = (x1 - Ax0) & mask;          /* the increment the pair implies */
          uint64_t t = x1; int d = 2;
          for(; d < ndraws; d++){
            t = (A*t + C) & mask;
            if((int)((t >> sh) & 15) != obs[d]) break;
          }
          if(d == ndraws){
            hits++;
            if(keep && NSV < SVMAX){ SV_S[NSV] = x0; SV_C[NSV] = C; NSV++; }
          }
          if(l1 >= lowmask) break;
        }
        if(h1 >= himask) break;
      }
      if(l0 >= lowmask) break;
    }
    if(h0 >= himask) break;
  }
  return hits;
}

/* majority vote of the survivor set on one future step */
static int vote(const LCGA *g, uint64_t A, int sh, uint64_t mask, int step){
  int cnt[16]; memset(cnt, 0, sizeof cnt);
  for(long long i = 0; i < NSV; i++){
    uint64_t t = SV_S[i];
    for(int k = 0; k < step; k++) t = (A*t + SV_C[i]) & mask;
    cnt[(t >> sh) & 15]++;
  }
  int best = 0; for(int v = 1; v < 16; v++) if(cnt[v] > cnt[best]) best = v;
  return best;
}

int main(int argc, char **argv){
  const char *mode = argc > 1 ? argv[1] : "selftest";
  int ndraws = 48;   /* the translation family shrinks as nibbles accumulate: 11477 at 20,
                        9515 at 30, 1026 at 40 — by 40 the majority vote is already exact.
                        Extra nibbles are nearly free: a wrong pair dies at the third. */
  int nfut   = 20;   /* held out; never shown to the search */
  if(!strcmp(mode, "selftest")){
    printf("selftest: plant a state AND a non-standard increment\n");
    printf("  the increment is derived per candidate pair, never assumed\n");
    printf("  (x0,C) is not identifiable — (x0+d, C-(A-1)d) shifts the whole orbit by d —\n");
    printf("  so the control asks that nothing be lost, nothing spurious be found,\n");
    printf("  and that the survivors predict %d held-out future nibbles.\n\n", nfut);
    for(int i = 0; i < NFAM; i++){
      const LCGA *g = &FAM[i];
      int L = g->shift + 4; if(L > 20){ printf("  %-22s L=%d out of range\n", g->name, L); continue; }
      uint64_t mask = (1ULL << L) - 1;
      int W = 21; uint64_t A = 1; for(int k=0;k<W;k++) A = (A*g->a) & mask;
      uint64_t u = (A - 1) & mask;
      uint64_t s0 = 0xBEEF1234ULL & mask, C = 0xDEAD57ULL & mask;   /* not a standard c */
      int obs[128]; uint64_t s = s0;
      for(int d = 0; d < ndraws + nfut; d++){ obs[d] = (int)((s >> g->shift) & 15); s = (A*s + C) & mask; }

      long long h = search(g, W, ndraws, obs, 1);

      /* 1. is the planted pair among the survivors? */
      int planted = 0;
      for(long long k = 0; k < NSV; k++) if(SV_S[k] == s0 && SV_C[k] == C){ planted = 1; break; }
      /* 2. is every survivor a translate of it? */
      long long stray = 0;
      for(long long k = 0; k < NSV; k++){
        uint64_t d = (SV_S[k] - s0) & mask;
        if(((SV_C[k] - C) & mask) != ((0 - u*d) & mask)) stray++;
      }
      /* 3. does the survivor set predict the held-out nibbles? */
      int good = 0;
      for(int f = 0; f < nfut; f++)
        if(vote(g, A, g->shift, mask, ndraws - 1 + f + 1) == obs[ndraws + f]) good++;

      /* negative controls: a wrong W, and nibbles that came from no LCG at all */
      long long nW = search(g, W - 1, ndraws, obs, 0);
      int rnd[128]; uint64_t z = 0x9E3779B97F4A7C15ULL ^ (uint64_t)i;
      for(int d = 0; d < ndraws; d++){ z = z*6364136223846793005ULL + 1442695040888963407ULL;
                                       rnd[d] = (int)((z >> 33) & 15); }
      long long nR = search(g, W, ndraws, rnd, 0);

      printf("  %-22s L=%2d  survivors=%-6lld planted kept=%s  strays=%lld  "
             "future %2d/%2d  wrongW=%lld random=%lld  %s\n",
             g->name, L, h, planted?"yes":"NO", stray, good, nfut, nW, nR,
             (planted && stray==0 && good==nfut && nW==0 && nR==0) ? "PASS" : "FAIL");
      fflush(stdout);
    }
    return 0;
  }
  loadbin();
  int maxW = argc > 2 ? atoi(argv[2]) : 24;
  int starts[] = {0, 20000, 55000};
  printf("real archive, increment UNKNOWN: %d nibbles per candidate pair, W 1..%d\n", ndraws, maxW);
  printf("  a wrong pair survives with probability 16^-%d; a right one comes with its\n", ndraws-2);
  printf("  whole translation family, so a hit shows up as thousands of survivors at once\n\n");
  fflush(stdout);
  long long total = 0;
  for(int i = 0; i < NFAM; i++){
    const LCGA *g = &FAM[i];
    int L = g->shift + 4; if(L > 20){ printf("  %-22s skipped (L=%d)\n", g->name, L); continue; }
    long long best = 0; int bw = 0;
    for(int W = 1; W <= maxW; W++)
      for(int si = 0; si < 3; si++){
        int obs[128]; for(int d = 0; d < ndraws; d++) obs[d] = nib(d, starts[si]);
        long long h = search(g, W, ndraws, obs, 0);
        if(h > best){ best = h; bw = W; }
        total += h;
      }
    printf("  %-22s L=%2d  best survivors %lld%s\n", g->name, L, best,
           best ? "" : "   (no state/increment pair fits at any W)");
    if(best) printf("        at W=%d — INVESTIGATE\n", bw);
    fflush(stdout);
  }
  printf("\n  total survivors: %lld  ->  %s\n", total,
         total ? "INVESTIGATE" : "no custom-increment LCG of this shape fits the archive");
  return 0;
}
