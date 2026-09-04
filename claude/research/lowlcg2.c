/* lowlcg — collapse a congruential search by working only in the low bits.
 *
 * The gap this fills: modlcg.py sees a congruential generator whose OUTPUT carries the
 * low bits of the state, and lcg_lll sees one whose output is a plain high truncation
 * feeding a mulhi index. Neither reaches the common shape in between — output
 * u = s >> shift, index j = u %% 80 — because there the bonus pins low bits of u, which
 * is neither an interval (no lattice) nor linear over F2 (no Gaussian elimination).
 *
 * The algebra that cracks it: for an LCG modulo 2^M, the low L bits of the state are
 * themselves a self-contained LCG modulo 2^L, whatever the higher bits do. Since
 * 80 = 16*5, u %% 80 fixes u mod 16, i.e. bits shift..shift+3 of s. Those live inside
 * s mod 2^(shift+4). So the unknown collapses from M bits to shift+4:
 *
 *     java.util.Random  M=48, shift=16  ->  2^20 candidates      (a millisecond)
 *     64-bit LCG        M=64, shift=32  ->  2^36 candidates      (about a minute)
 *
 * Each draw checks 4 bits, so a wrong candidate survives with probability 1/16 and ten
 * draws leave nothing. The increment is taken from the generator's standard constant;
 * W, the words consumed per draw, is swept.
 *
 *   ./lowlcg selftest      plant a known state, it must be recovered
 *   ./lowlcg real [maxW]   sweep the real archive
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

typedef struct { const char *name; uint64_t a, c; int M, shift; } LCG;
/* NB = low bits each draw reveals: 4 from u %% 80 (80 = 16*5), 2 from a rank via
   u %% 20 (20 = 4*5). CHANNEL picks which observable is used. */
static int NB = 4;
static int CHANNEL = 0;
static const LCG FAM[] = {
  {"java.util.Random",    25214903917ULL,          11ULL,                  48, 16},
  {"java (u>>16 % 80)",   25214903917ULL,          11ULL,                  48, 32},
  {"java (nextInt bits)", 25214903917ULL,          11ULL,                  48, 17},
  {"MMIX 64",             6364136223846793005ULL,  1442695040888963407ULL, 64, 32},
  {"L'Ecuyer 64",         2862933555777941757ULL,  3037000493ULL,          64, 32},
  {"Lehmer64",            0xda942042e4dd58b5ULL,   0ULL,                   64, 32},
  {"PCG (LCG core)",      6364136223846793005ULL,  1442695040888963407ULL, 64, 27},
  {"glibc TYPE_0",        1103515245ULL,           12345ULL,               31, 0},
  {"MSVC",                214013ULL,               2531011ULL,             32, 16},
  {"MSVC (u>>4 % 80)",    214013ULL,               2531011ULL,             32, 20},
  {"Numerical Recipes",   1664525ULL,              1013904223ULL,          32, 0},
};
#define NFAM ((int)(sizeof FAM / sizeof FAM[0]))

static uint32_t N, *IDS, *TS; static uint8_t *NUMS, *BOOST, *BONUS;
static void loadbin(const char *p){
  FILE *f = fopen(p, "rb"); if(!f || fread(&N,4,1,f)!=1){ perror(p); exit(1); }
  IDS=malloc(4*N); TS=malloc(4*N);
  uint64_t *LO=malloc(8*N), *HI=malloc(8*N);
  NUMS=malloc(20*N); BOOST=malloc(N); BONUS=malloc(N);
  if(fread(IDS,4,N,f)!=N||fread(TS,4,N,f)!=N||fread(LO,8,N,f)!=N||fread(HI,8,N,f)!=N||
     fread(NUMS,20,N,f)!=N||fread(BOOST,1,N,f)!=N||fread(BONUS,1,N,f)!=N){
    fprintf(stderr,"short read\n"); exit(1); }
  fclose(f); free(LO); free(HI);
}
/* one draw advances the state by W steps: s -> A*s + C (mod 2^L) */
static void jump(uint64_t a, uint64_t c, int W, uint64_t mask, uint64_t *A, uint64_t *C){
  uint64_t Aa = 1, Cc = 0;
  for(int i = 0; i < W; i++){ Cc = (Cc*a + c) & mask; Aa = (Aa*a) & mask; }
  *A = Aa; *C = Cc;
}
/* observed nibble for draw d: (bonus-1) mod 16 = bits shift..shift+3 of the state */
static int rank_of_bonus(int d, int first){
  for(int q = 0; q < 20; q++) if(NUMS[(size_t)(first+d)*20+q] == BONUS[first+d]) return q;
  return -1;
}
static inline int nib(int d, int first){
  if(CHANNEL == 0) return (BONUS[first+d]-1) & ((1<<NB)-1);
  int r = rank_of_bonus(d, first); return r < 0 ? 0 : (r & ((1<<NB)-1));
}

static long long search(const LCG *g, int W, int ndraws, int first,
                        const int *obs, uint64_t *found){
  int L = g->shift + NB;
  if(L > 40) return -1;                       /* keep the sweep finite */
  uint64_t mask = (L >= 64) ? ~0ULL : ((1ULL << L) - 1);
  uint64_t A, C; jump(g->a, g->c, W, mask, &A, &C);
  long long hits = 0;
  /* The first draw already fixes bits shift..shift+3 of s0, so only 2^(L-4) states are
     worth visiting: enumerate the rest and splice the known nibble in, instead of
     testing sixteen times as many and throwing fifteen sixteenths away. */
  int sh = g->shift;
  uint64_t lowmask = (sh == 0) ? 0 : ((1ULL << sh) - 1);
  uint64_t himask  = mask >> (sh + NB);
  uint64_t nib0 = (uint64_t)obs[0] << sh;
  for(uint64_t hi = 0; ; hi++){
    uint64_t hipart = hi << (sh + NB);
    for(uint64_t lo = 0; ; lo++){
      uint64_t s = (hipart | nib0 | lo) & mask;
      uint64_t t = (A*s + C) & mask;
      int d = 1;
      for(; d < ndraws; d++){
        if((int)((t >> sh) & ((1<<NB)-1)) != obs[d]) break;
        t = (A*t + C) & mask;
      }
      if(d == ndraws){ hits++; if(found) *found = s; }
      if(lo >= lowmask) break;
    }
    if(hi >= himask) break;
  }
  return hits;
}

int main(int argc, char **argv){
  const char *mode = argc > 1 ? argv[1] : "selftest";
  if(!strcmp(mode, "selftest")){
    printf("selftest: plant a state in each family, it must be recovered\n");
    printf("  a wrong candidate survives one draw with probability 1/16,\n");
    printf("  so %d draws should leave exactly one survivor\n\n", 14);
    for(int i = 0; i < NFAM; i++){
      const LCG *g = &FAM[i];
      int L = g->shift + NB; if(L > 40){ printf("  %-22s L=%d too wide for the sweep\n", g->name, L); continue; }
      uint64_t mask = (1ULL << L) - 1;
      int W = 21; uint64_t A, C; jump(g->a, g->c, W, mask, &A, &C);
      uint64_t s0 = 0x0123456789ABCDEFULL & mask, s = s0;
      int obs[64];
      for(int d = 0; d < 14; d++){ obs[d] = (int)((s >> g->shift) & ((1<<NB)-1)); s = (A*s + C) & mask; }
      uint64_t got = 0;
      long long h = search(g, W, 14, 0, obs, &got);
      /* the search only sees s mod 2^L, so any survivor must reproduce the nibbles */
      printf("  %-22s L=%2d  survivors=%lld  %s\n", g->name, L, h,
             (h >= 1 && got == s0) ? "RECOVERED" : (h >= 1 ? "other state, same nibbles" : "MISSED"));
    }
    return 0;
  }
  loadbin("draws.bin");
  int maxW = argc > 2 ? atoi(argv[2]) : 48;
  for(int i = 1; i < argc; i++) if(!strcmp(argv[i], "rank")){ CHANNEL = 1; NB = 2; }
  printf("channel: %s, %d bits per draw\n",
         CHANNEL ? "bonus = sorted[u % 20]" : "bonus = first ball, j = u % 80", NB);
  int ndraws = (NB == 2) ? 34 : 16;
  int starts[] = {0, 12000, 40000, 65000};
  printf("real archive: %u draws, %d nibbles checked per candidate, W swept 1..%d\n", N, ndraws, maxW);
  printf("  a wrong candidate survives with probability 2^-%d\n\n", NB*ndraws);
  fflush(stdout);
  long long total_hits = 0;
  for(int i = 0; i < NFAM; i++){
    const LCG *g = &FAM[i];
    int L = g->shift + NB;
    if(L > 40){ printf("  %-22s skipped (L=%d beyond the sweep)\n", g->name, L); continue; }
    /* Cost is 2^(L-4) candidates per (W, window). The wide families get a shorter
       sweep and a single window rather than being dropped: the archive is one
       continuous stream, so any consecutive block of draws tests the same hypothesis. */
    int wlim = (L > 24) ? (maxW < 16 ? maxW : 16) : maxW;
    int slim = (L > 24) ? 1 : 4;
    long long best = 0; int bw = 0, bs = 0;
    for(int W = 1; W <= wlim; W++){
      for(int si = 0; si < slim; si++){
        int obs[64]; for(int d = 0; d < ndraws; d++) obs[d] = nib(d, starts[si]);
        long long h = search(g, W, ndraws, starts[si], obs, NULL);
        if(h > best){ best = h; bw = W; bs = starts[si]; }
        total_hits += h;
      }
    }
    printf("  %-22s L=%2d  W<=%-2d %d window(s)  best survivors %lld%s\n",
           g->name, L, wlim, slim, best,
           best ? "" : "   (no state reproduces the nibbles at any W)");
    if(best) printf("        at W=%d, start=%d — INVESTIGATE\n", bw, bs);
    fflush(stdout);
  }
  printf("\n  total survivors across every family, W and window: %lld  ->  %s\n", total_hits,
         total_hits ? "INVESTIGATE" : "no congruential generator of this shape fits the archive");
  return 0;
}
