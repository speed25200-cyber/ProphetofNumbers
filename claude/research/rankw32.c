/* rankw32 — the rank assembled from TWO machine words, which lcgrank cannot see.
 *
 * lcgrank solves u_{d+1} = A u_d + B on the rank itself. That is exact when the operator
 * draws one 64-bit value. But a 32-bit generator cannot produce 61.6 bits in one call:
 * it must concatenate two outputs. And then the rank is NOT an affine function of any
 * single state — (w_2d, w_2d+1) are two different points of the orbit — so lcgrank's
 * closed form does not apply and the family escapes it.
 *
 * It does not escape for long. Splitting u back into its two words returns two
 * consecutive generator outputs, and one draw already gives the relation
 *
 *     w1 = a*w0 + c          (mod 2^B)
 *
 * with two unknowns. A second draw gives a second instance of the same relation, and
 * the pair solves in closed form:
 *
 *     a = (w3 - w1) / (w2 - w0)       c = w1 - a*w0
 *
 * again with no multiplier assumed. The step count W between draws is then read off by
 * checking which power of a carries w0 to w2, and the candidate is verified on further
 * draws where a wrong one survives at 2^-61.6 apiece.
 *
 *   ./rankw32 selftest
 *   ./rankw32 real <rankfile> [starts]
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

typedef unsigned __int128 u128;
typedef uint64_t u64;
static const u64 CC = 3535316142212174320ULL;

typedef struct { const char *name; int B; int hi_first; } LAY;
static const LAY LAYS[] = {
  {"2 x 32 bits, high word first", 32, 1},
  {"2 x 32 bits, low word first",  32, 0},
  {"2 x 31 bits, high word first", 31, 1},
  {"2 x 31 bits, low word first",  31, 0},
};
#define NLAY 4

static u64 inv_odd(u64 a){ u64 x=a; for(int i=0;i<6;i++) x *= 2-a*x; return x; }
static int v2(u64 x){ return x ? __builtin_ctzll(x) : 64; }

static u64 *R; static long N;

/* Candidate outputs behind a rank.
 *
 * Two reductions are live. Under `u mod C` (with rejection — modbias.py excludes the
 * biased form) the preimages of a rank are r + kC. Under Lemire/mulhi, r = (u*C) >> 64
 * and the preimages are an interval of about 5.2 integers instead: the same count, a
 * different set. A tool that only knows the first is blind to an operator who used the
 * second, so MODEL selects between them and both are swept.
 */
static int MODEL = 0;   /* 0 = u mod C (with rejection), 1 = mulhi */

/* plant a rank using whichever reduction MODEL names, so the selftest exercises the
   same path the archive run will take */
static u64 mkrank(u64 u){ return MODEL ? (u64)(((u128)u * CC) >> 64) : u % CC; }

static int cands_model(u64 rank, u64 *o){
  int n = 0;
  if(MODEL == 0){
    for(int k = 0; k <= 5; k++){
      u128 u = (u128)rank + (u128)k * CC;
      if(u < ((u128)1 << 64)) o[n++] = (u64)u;
    }
  } else {
    u128 lo = (((u128)rank) << 64) / CC, hi = (((u128)(rank + 1)) << 64) / CC;
    for(u128 u = lo; u <= hi && n < 8; u++)
      if((u64)(((u128)(u64)u * CC) >> 64) == rank) o[n++] = (u64)u;
  }
  return n;
}


static int cands(long d, int B, u64 *out){
  u64 raw[8]; int m = cands_model(R[d], raw), n = 0;
  u64 lim = (B == 32) ? 0 : (1ULL << 62);           /* 2x31 bits spans only 2^62 */
  for(int i = 0; i < m; i++)
    if(!lim || raw[i] < lim) out[n++] = raw[i];
  return n;
}
static void split(u64 u, int B, int hi_first, u64 *w0, u64 *w1){
  u64 m = (1ULL << B) - 1;
  u64 a = (u >> B) & m, b = u & m;
  if(hi_first){ *w0 = a; *w1 = b; } else { *w0 = b; *w1 = a; }
}

/* verify (a,c,W) forward from the words of draw d0 */
static int verify(int lay, u64 a, u64 c, int W, long d0, int need){
  int B = LAYS[lay].B; u64 M = (B==64)?~0ULL:((1ULL<<B)-1);
  u64 w0, w1; u64 cd[8]; int nc = cands(d0, B, cd);
  if(!nc) return 0;
  for(int q = 0; q < nc; q++){
    split(cd[q], B, LAYS[lay].hi_first, &w0, &w1);
    if(((a*w0 + c) & M) != w1) continue;
    u64 x = w1; int ok = 1;
    for(int j = 1; j <= need && ok; j++){
      for(int t = 0; t < W - 1; t++) x = (a*x + c) & M;    /* to the next draw's first word */
      u64 y0 = x, y1 = (a*x + c) & M;
      u64 u = LAYS[lay].hi_first ? ((y0 << B) | y1) : ((y1 << B) | y0);
      if(mkrank(u) != R[d0 + j]) ok = 0;
      x = y1;
    }
    if(ok) return 1;
  }
  return 0;
}

static int solve_at(int lay, long d, int need, int maxW, u64 *oa, u64 *oc, int *oW){
  int B = LAYS[lay].B; u64 M = (1ULL << B) - 1;
  u64 c0[8], c1[8]; int n0 = cands(d, B, c0), n1 = cands(d+1, B, c1);
  for(int i = 0; i < n0; i++)
    for(int j = 0; j < n1; j++){
      u64 w0, w1, w2, w3;
      split(c0[i], B, LAYS[lay].hi_first, &w0, &w1);
      split(c1[j], B, LAYS[lay].hi_first, &w2, &w3);
      u64 dx = (w2 - w0) & M, dy = (w3 - w1) & M;
      int e = v2(dx); if(e >= B) continue;
      if(v2(dy) < e) continue;
      u64 a0 = ((dy >> e) * inv_odd(dx >> e)) & M;
      u64 step = (e == 0) ? 0 : (1ULL << (B - e));
      for(u64 t = 0; t < (1ULL << e) && (t == 0 || step); t++){
        u64 a = (a0 + t*step) & M;
        u64 c = (w1 - a*w0) & M;
        for(int W = 2; W <= maxW; W++){          /* which power of a carries w0 to w2 */
          u64 x = w0; for(int s = 0; s < W; s++) x = (a*x + c) & M;
          if(x != w2) continue;
          if(verify(lay, a, c, W, d, need)){ *oa=a; *oc=c; *oW=W; return 1; }
        }
        if(!step) break;
      }
    }
  return 0;
}

static void loadrank(const char *fn){
  FILE *f=fopen(fn,"rb"); if(!f){perror(fn);exit(1);}
  fseek(f,0,SEEK_END); long sz=ftell(f); fseek(f,0,SEEK_SET);
  N=sz/8; R=malloc(sz);
  if((long)fread(R,8,N,f)!=N){fprintf(stderr,"short read\n");exit(1);} fclose(f);
}

int main(int argc, char **argv){
  const char *mode = argc>1?argv[1]:"selftest";
  int need = 4, maxW = 8;
  if(!strcmp(mode,"selftest")){
    MODEL = argc > 2 ? atoi(argv[2]) : 0;
    printf("reduction model: %s\n", MODEL ? "mulhi (Lemire)" : "u mod C");
    printf("selftest: plant a 32-bit congruential generator whose two consecutive outputs\n");
    printf("  are concatenated into the rank; recover it with no multiplier assumed.\n\n");
    for(int lay = 0; lay < NLAY; lay++){
      int B = LAYS[lay].B; u64 M = (1ULL << B) - 1;
      u64 a = 1103515245ULL & M, c = 12345 & M, x = 0x5EED1234 & M;
      int W = 2;
      long nd = 200; N = nd; R = malloc(8*nd);
      for(long d = 0; d < nd; d++){
        u64 y0 = x, y1 = (a*x + c) & M;
        R[d] = mkrank(LAYS[lay].hi_first ? ((y0<<B)|y1) : ((y1<<B)|y0));
        x = y1; for(int t = 0; t < W-1; t++) x = (a*x + c) & M;
      }
      u64 ga, gc; int gW; int hit = 0;
      for(long d = 0; d + need + 2 < nd && !hit; d++) hit = solve_at(lay,d,need,maxW,&ga,&gc,&gW);
      int right = hit && ga == a && gc == c;
      free(R);
      /* control: a mixed stream */
      N = nd; R = malloc(8*nd); u64 st = 0x77777;
      for(long d = 0; d < nd; d++){ st += 0x9E3779B97F4A7C15ULL; u64 z = st;
        z=(z^(z>>30))*0xBF58476D1CE4E5B9ULL; z=(z^(z>>27))*0x94D049BB133111EBULL; z^=z>>31;
        R[d] = mkrank(z); }
      int fp = 0;
      for(long d = 0; d + need + 2 < nd && !fp; d++) fp = solve_at(lay,d,need,maxW,&ga,&gc,&gW);
      free(R);
      printf("  %-30s recovered=%-3s exact(a,c)=%-3s  control=%-3s  %s\n",
             LAYS[lay].name, hit?"yes":"NO", right?"yes":"no", fp?"HIT":"no",
             (hit && right && !fp) ? "PASS" : "FAIL");
      fflush(stdout);
    }
    return 0;
  }
  const char *fn = argc>2?argv[2]:"rank_colex0.bin";
  long starts = argc>3?atol(argv[3]):20000;
  MODEL = argc>4?atoi(argv[4]):0;
  loadrank(fn);
  printf("reduction model: %s\n", MODEL ? "mulhi (Lemire)" : "u mod C (with rejection)");
  printf("real archive: %s, %ld ranks;  %ld starting positions, W up to %d\n",
         fn, N, starts, maxW);
  printf("  the two words are recovered from the rank, then a and c solved in closed form\n\n");
  for(int lay = 0; lay < NLAY; lay++){
    long hits = 0; u64 ga, gc; int gW;
    for(long t = 0; t < starts; t++){
      long d = (N - need - 3) * t / starts;
      if(solve_at(lay, d, need, maxW, &ga, &gc, &gW)) hits++;
    }
    printf("  %-30s %ld / %ld positions solved   %s\n", LAYS[lay].name, hits, starts,
           hits ? "*** INVESTIGATE ***" : "(no two-word congruential generator fits)");
    fflush(stdout);
  }
  return 0;
}
