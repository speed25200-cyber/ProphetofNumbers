/* ranklfg — lagged Fibonacci and friends, read off the combinatorial rank.
 *
 * Everything tested so far is either congruential (one previous value) or F2-linear
 * (a matrix on a bit-state). A third family is missing, and it is not exotic: glibc's
 * own random() is an ADDITIVE LAGGED FIBONACCI, r[i] = r[i-3] + r[i-31]. Boost, Knuth's
 * ran_array, Marsaglia's add-with-carry and subtract-with-borrow are all this shape.
 * A congruential sweep cannot see them: they have no multiplier. Berlekamp-Massey sees
 * only the XOR variants, since addition carries.
 *
 * With 61.6 bits per draw they are trivial to test, because the defining relation is a
 * single equation between three outputs:
 *
 *     u_d = u_{d-l}  OP  u_{d-s}   (mod 2^64),     OP in { +, -, ^ },  carry allowed
 *
 * The rank pins each u only modulo C, so the three draws cost 6^3 = 216 assignments —
 * and a wrong lag pair satisfies the equation with probability about 216 * 2^-64. A real
 * one satisfies it at EVERY position. So the test is simply: how often does it hold?
 *
 *   ./ranklfg selftest
 *   ./ranklfg real <rankfile> [maxlag] [positions]
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

typedef unsigned __int128 u128;
typedef uint64_t u64;
static const u64 CC = 3535316142212174320ULL;
static const char *OPN[] = {"+", "-", "^"};

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
static int PLANT = -1;   /* -1 = plant with whatever MODEL searches */
static u64 mkrank(u64 u){
  int m = (PLANT < 0) ? MODEL : PLANT;
  return m ? (u64)(((u128)u * CC) >> 64) : u % CC;
}

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


static int cand_of(long d, u64 *c){ return cands_model(R[d], c); }

/* does u_d = u_{d-l} OP u_{d-s} hold at position d for some assignment of the k's? */
static int holds(long d, int s, int l, int op){
  u64 a[8], b[8], c[8];
  int na = cand_of(d - l, a), nb = cand_of(d - s, b), nc = cand_of(d, c);
  for(int i = 0; i < na; i++)
    for(int j = 0; j < nb; j++){
      u64 v;
      if(op == 0) v = a[i] + b[j];
      else if(op == 1) v = a[i] - b[j];
      else v = a[i] ^ b[j];
      for(int m = 0; m < nc; m++){
        if(c[m] == v) return 1;
        if(op != 2 && (c[m] == v + 1 || c[m] == v - 1)) return 1;   /* carry / borrow */
      }
    }
  return 0;
}

static void loadrank(const char *fn){
  FILE *f = fopen(fn,"rb"); if(!f){ perror(fn); exit(1); }
  fseek(f,0,SEEK_END); long sz = ftell(f); fseek(f,0,SEEK_SET);
  N = sz/8; R = malloc(sz);
  if((long)fread(R,8,N,f)!=N){ fprintf(stderr,"short read\n"); exit(1); } fclose(f);
}

int main(int argc, char **argv){
  const char *mode = argc>1?argv[1]:"selftest";
  if(!strcmp(mode,"selftest")){
    MODEL = argc > 2 ? atoi(argv[2]) : 0;
    printf("reduction model: %s\n", MODEL ? "mulhi (Lemire)" : "u mod C");
    printf("selftest: a planted lagged Fibonacci must hold at every position and be found\n");
    printf("  at its own lags; every other lag pair, and a non-LFG stream, must not.\n\n");
    long nd = 3000;
    struct { int s, l, op; const char *what; } P[] = {
      { 3, 31, 0, "glibc random() lags 3,31, +" },
      { 5, 17, 0, "Boost lags 5,17, +" },
      {10, 24, 1, "subtract-with-borrow 10,24" },
      { 7, 33, 2, "xor lagged 7,33" },
    };
    for(int t = 0; t < 4; t++){
      int s = P[t].s, l = P[t].l, op = P[t].op;
      N = nd; R = malloc(8*nd);
      u64 *u = malloc(8*nd), st = 0x243F6A8885A308D3ULL;
      for(long i = 0; i < l; i++){ st = st*6364136223846793005ULL + 1442695040888963407ULL; u[i] = st; }
      for(long i = l; i < nd; i++)
        u[i] = (op==0) ? u[i-l] + u[i-s] : (op==1) ? u[i-l] - u[i-s] : u[i-l] ^ u[i-s];
      for(long i = 0; i < nd; i++) R[i] = mkrank(u[i]);
      /* the planted lags */
      long hit = 0; for(long d = l; d < nd; d++) hit += holds(d, s, l, op);
      /* every other lag pair at the same op: the best impostor */
      long best = 0; int bs=0, bl=0;
      for(int ll = 2; ll <= 40; ll++) for(int ss = 1; ss < ll; ss++){
        if(ss==s && ll==l) continue;
        long h = 0; for(long d = 40; d < 600; d++) h += holds(d, ss, ll, op);
        if(h > best){ best = h; bs=ss; bl=ll; }
      }
      free(u); free(R);
      /* a stream that is not an LFG at all */
      N = nd; R = malloc(8*nd); st = 0xABCDEF;
      for(long i = 0; i < nd; i++){ st += 0x9E3779B97F4A7C15ULL; u64 z = st;
        z=(z^(z>>30))*0xBF58476D1CE4E5B9ULL; z=(z^(z>>27))*0x94D049BB133111EBULL; z^=z>>31;
        R[i] = mkrank(z); }
      long fp = 0; for(long d = l; d < 600; d++) fp += holds(d, s, l, op);
      free(R);
      printf("  %-28s holds %ld/%ld   best impostor %ld/560 (%d,%d)   non-LFG %ld/560   %s\n",
             P[t].what, hit, nd-l, best, bs, bl, fp,
             (hit == nd-l && best < 20 && fp < 20) ? "PASS" : "FAIL");
      fflush(stdout);
    }
    /* Cross-model measurement.
     *
     * The expectation going in was that searching under the wrong reduction would find
     * nothing. It does not work out that way HERE, and the reason is worth recording:
     * mulhi is a linear rescaling, u -> floor(u*C/2^64), so an ADDITIVE relation
     * survives it. If u_d = u_{d-l} + u_{d-s} - w*2^64 with w in {0,1}, then after
     * rescaling the correction term is exactly w*C — which is precisely the offset the
     * r + kC candidate set already enumerates. So for a lagged Fibonacci the two models
     * are not distinguishable, and this tool was never blind to either.
     *
     * That is specific to an additive relation. rankmix inverts a bijective finalizer
     * and rankmwc multiplies; neither absorbs a rescaling, and for those the flag does
     * change what is found. So this prints the rates rather than passing or failing. */
    printf("\n  cross-model measurement (an additive relation survives the rescaling):\n");
    for(int pm = 0; pm <= 1; pm++){
      int s0 = P[0].s, l0 = P[0].l, op0 = P[0].op;
      long nd = 1200; N = nd; R = malloc(8*nd);
      u64 *u = malloc(8*nd), st = 0x243F6A8885A308D3ULL;
      for(long i = 0; i < l0; i++){ st = st*6364136223846793005ULL + 1442695040888963407ULL; u[i] = st; }
      for(long i = l0; i < nd; i++) u[i] = u[i-l0] + u[i-s0];
      PLANT = pm;
      for(long i = 0; i < nd; i++) R[i] = mkrank(u[i]);
      PLANT = -1;
      int save = MODEL;
      MODEL = pm;      long same  = 0; for(long d=l0; d<nd-1; d++) same  += holds(d, s0, l0, op0);
      MODEL = 1 - pm;  long cross = 0; for(long d=l0; d<nd-1; d++) cross += holds(d, s0, l0, op0);
      MODEL = save;
      free(u); free(R);
      printf("    planted under %-9s matching search %ld/%ld, opposite search %ld/%ld  %s\n",
             pm ? "mulhi" : "u mod C", same, nd-1-l0, cross, nd-1-l0,
             same == nd-1-l0 ? "(detected either way)" : "MATCHING SEARCH FAILED");
    }
    return 0;
  }
  const char *fn = argc>2?argv[2]:"rank_colex0.bin";
  int maxlag = argc>3?atoi(argv[3]):64;
  long pos   = argc>4?atol(argv[4]):3000;
  MODEL      = argc>5?atoi(argv[5]):0;
  printf("reduction model: %s\n", MODEL ? "mulhi (Lemire)" : "u mod C (with rejection)");
  loadrank(fn);
  printf("real archive: %s, %ld ranks;  lags up to %d, %ld positions per pair\n",
         fn, N, maxlag, pos);
  printf("  a real lag pair holds at every position; chance gives 216*2^-64 per position\n\n");
  for(int op = 0; op < 3; op++){
    long best = 0; int bs = 0, bl = 0;
    for(int l = 2; l <= maxlag; l++)
      for(int s = 1; s < l; s++){
        long h = 0;
        for(long d = maxlag; d < maxlag + pos; d++) h += holds(d, s, l, op);
        if(h > best){ best = h; bs = s; bl = l; }
      }
    printf("  op %s : best lag pair (%d,%d) holds %ld / %ld   %s\n", OPN[op], bs, bl, best, pos,
           best > pos/10 ? "*** INVESTIGATE ***" : "(no lagged-Fibonacci relation)");
    fflush(stdout);
  }
  return 0;
}
