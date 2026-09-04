/* rankmwc — multiply-with-carry, a family that is neither congruential nor F2-linear.
 *
 * MWC is its own thing: x_{n} = (a*x_{n-1} + c_{n-1}) mod b, with the carry
 * c_n = floor((a*x_{n-1} + c_{n-1}) / b) fed back. lcgrank cannot see it (the carry is
 * not an increment), ranklfg cannot (there are no lags), and bm cannot (the carry is
 * not linear). It is also not obscure — Marsaglia's MWC, KISS and xorwow all use it.
 *
 * With a full output the test is almost free, because the carry is SMALL. From two
 * consecutive outputs,
 *
 *     c_d = (x_{d+1} - a*x_d) mod b        and the real c_d must satisfy c_d < a.
 *
 * For a wrong multiplier that lands in [0,a) with probability a/b — about 2^-32 for a
 * typical 32-bit a against b = 2^64. Over a few hundred draws a real multiplier holds
 * every time and a wrong one essentially never does.
 *
 *   ./rankmwc selftest
 *   ./rankmwc real <rankfile>
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>

typedef unsigned __int128 u128;
typedef uint64_t u64;
static const u64 CC = 3535316142212174320ULL;

/* published MWC multipliers, 32-bit lag-1 and 64-bit lag-1 */
static const u64 MULT[] = {
  4294967118ULL, 4294963023ULL, 4294962893ULL, 4294957665ULL, 4294954935ULL,
  4294948639ULL, 4294942995ULL, 4294941883ULL, 4294938741ULL, 4294932103ULL,
  698769069ULL, 1690649ULL, 2131995753ULL, 916905990ULL, 1372460312ULL,
  0xffffda61ULL, 0xfffffaabULL, 0xffffe1e7ULL, 0xffffcb1fULL,
  30903ULL, 18000ULL, 29943ULL, 36969ULL, 18030ULL, 30345ULL,
  0xfff62cf2ffb5ULL, 0x14057B7EF767814FULL, 0xff676488ULL,
  0xfeb344657c0afULL, 0xffebb71d94fcdafULL, 0xfff62cf2ULL,
};
#define NM ((int)(sizeof MULT / sizeof MULT[0]))

static u64 *R; static long N;
static int cands(long d, u64 *o){
  int n = 0;
  for(int k = 0; k <= 5; k++){
    u128 u = (u128)R[d] + (u128)k * CC;
    if(u < ((u128)1 << 64)) o[n++] = (u64)u;
  }
  return n;
}

/* Chance that a position admits a carry below a purely by luck. The carry test only has
   power when a is small against the modulus: for a ~ 2^32 against 2^64 a wrong candidate
   passes at 2^-32, but for a ~ 2^60 it passes about 8 times in 100 and, with 36 candidate
   pairs per position, essentially always. Such multipliers are simply not testable this
   way, and saying so is the point of reporting the null next to the observation. */
static double nullrate(int b64, int nassign){
  double p = b64 ? 1.0/18446744073709551616.0 : 1.0/4294967296.0;
  return 1.0 - pow(1.0 - p, (double)nassign);
}

/* The carry-magnitude test (c < a) is nearly powerless where it matters most: a real
   MWC32 has a just under 2^32 against a base of 2^32, so "c < a" is true almost always.
   The test with real power is carry CONSISTENCY across three consecutive outputs:

       c0 = (x1 - a*x0) mod b                     read off the first pair
       c1 = floor((a*x0 + c0) / b)                what the carry must then become
       c1 = (x2 - a*x1) mod b                     what the next pair says it is

   Those two values of c1 agree with probability b^-1 for a wrong multiplier, and always
   for the right one. That is 2^-32 per position at 32 bits and 2^-64 at 64 bits,
   independent of how large a is. */
static int consistent(u64 a, u64 x0, u64 x1, u64 x2, int b64){
  if(b64){
    u64 c0 = x1 - a * x0;                       /* mod 2^64 */
    u128 p = (u128)a * x0 + c0;
    u64 c1a = (u64)(p >> 64);
    u64 c1b = x2 - a * x1;
    return c1a == c1b && c0 < a && c1a < a;
  } else {
    u64 M = 0xFFFFFFFFULL;
    u64 c0 = (x1 - a * x0) & M;
    u64 p = a * (x0 & M) + c0;                  /* fits in 64 bits */
    u64 c1a = p >> 32;
    u64 c1b = (x2 - a * x1) & M;
    return c1a == c1b && c0 < a && c1a < a;
  }
}

/* positions where some assignment of the unknown k values makes the carry consistent */
static long holds(u64 a, int b64, long from, long upto){
  long ok = 0;
  if(upto > N - 2) upto = N - 2;          /* three consecutive draws are needed */
  for(long d = from; d < upto; d++){
    u64 c0[8], c1[8], c2[8];
    int n0 = cands(d, c0), n1 = cands(d+1, c1), n2 = cands(d+2, c2);
    int any = 0;
    if(b64){
      for(int i = 0; i < n0 && !any; i++)
        for(int j = 0; j < n1 && !any; j++)
          for(int k = 0; k < n2 && !any; k++)
            if(consistent(a, c0[i], c1[j], c2[k], 1)) any = 1;
    } else {
      /* each rank carries two 32-bit words, so one draw plus the next gives three */
      for(int i = 0; i < n0 && !any; i++)
        for(int j = 0; j < n1 && !any; j++){
          u64 lo0 = c0[i] & 0xFFFFFFFFULL, hi0 = c0[i] >> 32;
          u64 lo1 = c1[j] & 0xFFFFFFFFULL, hi1 = c1[j] >> 32;
          if(consistent(a, lo0, hi0, lo1, 0)) any = 1;        /* low word first */
          if(consistent(a, hi0, lo0, hi1, 0)) any = 1;        /* high word first */
        }
    }
    ok += any;
  }
  return ok;
}

static void loadrank(const char *fn){
  FILE *f=fopen(fn,"rb"); if(!f){perror(fn);exit(1);}
  fseek(f,0,SEEK_END); long sz=ftell(f); fseek(f,0,SEEK_SET);
  N=sz/8; R=malloc(sz);
  if((long)fread(R,8,N,f)!=N){fprintf(stderr,"short read\n");exit(1);} fclose(f);
}

int main(int argc, char **argv){
  const char *mode = argc>1?argv[1]:"selftest";
  if(!strcmp(mode,"selftest")){
    printf("selftest: a planted MWC must admit a valid carry at every position, and a\n");
    printf("  stream that is not an MWC must not.\n\n");
    long nd = 3000;
    for(int t = 0; t < 3; t++){
      u64 a = MULT[t*7];
      N = nd; R = malloc(8*nd);
      u64 x = 0x12345678ULL, c = 99;
      for(long d = 0; d < nd; d++){
        u128 p = (u128)a * x + c; x = (u64)p; c = (u64)(p >> 64);
        R[d] = x % CC;
      }
      long h = holds(a, 1, 0, nd-2);
      /* the best wrong multiplier AMONG THOSE THE TEST CAN DISCRIMINATE (null < 0.1) */
      long best = 0; u64 ba = 0; int ntest = 0;
      for(int m = 0; m < NM; m++){
        if(MULT[m] == a) continue;
        ntest++;
        long hh = holds(MULT[m], 1, 0, 600);
        if(hh > best){ best = hh; ba = MULT[m]; }
      }
      free(R);
      N = nd; R = malloc(8*nd); u64 st = 0xABCD;
      for(long d = 0; d < nd; d++){ st += 0x9E3779B97F4A7C15ULL; u64 z = st;
        z=(z^(z>>30))*0xBF58476D1CE4E5B9ULL; z=(z^(z>>27))*0x94D049BB133111EBULL; z^=z>>31;
        R[d] = z % CC; }
      long fp = holds(a, 1, 0, 600);
      free(R);
      printf("  a=%-12llu planted %ld/%ld  null %.1e  best of %d testable wrong a: %ld/600  non-MWC %ld/600  %s\n",
             (unsigned long long)a, h, nd-2, nullrate(1,216), ntest, best, fp,
             (h == nd-2 && best == 0 && fp == 0) ? "PASS" : "FAIL");
      fflush(stdout);
    }
    return 0;
  }
  const char *fn = argc>2?argv[2]:"rank_colex0.bin";
  loadrank(fn);
  long W = 4000;
  printf("real archive: %s;  %d published MWC multipliers, %ld positions each\n", fn, NM, W);
  printf("  a real multiplier admits a carry below a at EVERY position\n\n");
  long best = 0; u64 ba = 0; int bw = 0;
  for(int m = 0; m < NM; m++)
    for(int b64 = 0; b64 <= 1; b64++){
      long h = holds(MULT[m], b64, 0, W);
      if(h > best){ best = h; ba = MULT[m]; bw = b64; }
    }
  printf("  best multiplier %llu (%d-bit): %ld / %ld positions   %s\n",
         (unsigned long long)ba, bw?64:32, best, W,
         best > W/2 ? "*** INVESTIGATE ***" : "(no multiply-with-carry generator fits)");
  return 0;
}
