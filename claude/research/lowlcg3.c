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
 * Only families with L <= 20 are in range; the wide ones stay with lowlcg, where the
 * standard increment is the sensible assumption anyway (a 64-bit LCG with both a custom
 * multiplier and a custom increment is not something a sweep can reach).
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

/* A = a^W mod 2^L; the per-draw increment C is derived per candidate pair, not assumed */
static long long search(const LCGA *g, int W, int ndraws, const int *obs,
                        uint64_t *fs, uint64_t *fc){
  int L = g->shift + 4;
  uint64_t mask = (1ULL << L) - 1;
  uint64_t A = 1; for(int i=0;i<W;i++) A = (A * g->a) & mask;
  int sh = g->shift;
  uint64_t lowmask = (sh == 0) ? 0 : ((1ULL << sh) - 1);
  uint64_t himask  = mask >> (sh + 4);
  uint64_t n0 = (uint64_t)obs[0] << sh, n1 = (uint64_t)obs[1] << sh;
  long long hits = 0;
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
          if(d == ndraws){ hits++; if(fs){ *fs = x0; *fc = C; } }
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

int main(int argc, char **argv){
  const char *mode = argc > 1 ? argv[1] : "selftest";
  int ndraws = 18;
  if(!strcmp(mode, "selftest")){
    printf("selftest: plant a state AND a non-standard increment; both must be recovered\n");
    printf("  the increment is derived per candidate pair, never assumed\n\n");
    for(int i = 0; i < NFAM; i++){
      const LCGA *g = &FAM[i];
      int L = g->shift + 4; if(L > 20){ printf("  %-22s L=%d out of range\n", g->name, L); continue; }
      uint64_t mask = (1ULL << L) - 1;
      int W = 21; uint64_t A = 1; for(int k=0;k<W;k++) A = (A*g->a) & mask;
      uint64_t s0 = 0xBEEF1234ULL & mask, C = 0xDEAD57ULL & mask;   /* not a standard c */
      int obs[64]; uint64_t s = s0;
      for(int d = 0; d < ndraws; d++){ obs[d] = (int)((s >> g->shift) & 15); s = (A*s + C) & mask; }
      uint64_t gs = 0, gc = 0;
      long long h = search(g, W, ndraws, obs, &gs, &gc);
      printf("  %-22s L=%2d  survivors=%-4lld %s\n", g->name, L, h,
             (h >= 1 && gs == s0 && gc == C) ? "RECOVERED (state and increment)" :
             (h >= 1 ? "survivor found, different pair" : "MISSED"));
    }
    return 0;
  }
  loadbin();
  int maxW = argc > 2 ? atoi(argv[2]) : 24;
  int starts[] = {0, 20000, 55000};
  printf("real archive, increment UNKNOWN: %d nibbles per candidate pair, W 1..%d\n", ndraws, maxW);
  printf("  a wrong pair survives with probability 16^-%d\n\n", ndraws-2);
  fflush(stdout);
  long long total = 0;
  for(int i = 0; i < NFAM; i++){
    const LCGA *g = &FAM[i];
    int L = g->shift + 4; if(L > 20){ printf("  %-22s skipped (L=%d)\n", g->name, L); continue; }
    long long best = 0; int bw = 0;
    for(int W = 1; W <= maxW; W++)
      for(int si = 0; si < 3; si++){
        int obs[64]; for(int d = 0; d < ndraws; d++) obs[d] = nib(d, starts[si]);
        long long h = search(g, W, ndraws, obs, NULL, NULL);
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
