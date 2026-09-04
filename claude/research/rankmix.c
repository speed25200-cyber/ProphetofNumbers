/* rankmix — break the "additive state + invertible finalizer" generators from the rank.
 *
 * RECHERCHE.md records splitmix64 / PCG / xoshiro** as OUT OF REACH: reconstructing them
 * from 4 bits per draw needs a SAT solve across the carry chain, and the carry barrier
 * holds (same phase transition delta-chain measures). That barrier exists because the
 * observable was 4 bits wide.
 *
 * Under the unranking hypothesis it is 61.6 bits wide, and the barrier evaporates —
 * not because the solver got better but because the problem stops being a search.
 * splitmix64 is state += gamma, output = fmix(state), and fmix is a BIJECTION. So a
 * full output hands back the state by inverting it, with no search at all:
 *
 *     s_d = fmix^-1(u_d),      s_{d+1} - s_d = W*gamma = the same constant forever.
 *
 * The rank gives u only mod C, so u = r + kC with k in 0..5 and each consecutive pair
 * offers 36 candidate differences. The true one REPEATS at every draw; a wrong one is a
 * random 64-bit value. Over 70k draws that is 2.5M values in a 2^64 space, where even
 * three collisions are far beyond chance. So the test is: does any difference recur?
 *
 * That needs no knowledge of gamma and no knowledge of W — W only scales the constant.
 * It covers every generator of the shape (additive state, bijective finalizer), for each
 * finalizer in the table below.
 *
 *   ./rankmix selftest
 *   ./rankmix real <rankfile>
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

typedef unsigned __int128 u128;
typedef uint64_t u64;
static const uint64_t CC = 3535316142212174320ULL;

static uint64_t inv_odd(uint64_t a){ uint64_t x=a; for(int i=0;i<6;i++) x *= 2-a*x; return x; }
static uint64_t unxsr(uint64_t y, int s){            /* invert x -> x ^ (x>>s) */
  uint64_t x = y; for(int i = 0; i < 64/s + 1; i++) x = y ^ (x >> s); return x; }

/* --- the finalizers.  Each must be a bijection; the selftest checks that. --- */
typedef struct { const char *name; int kind; } MIX;
static const MIX MIXES[] = {
  {"splitmix64 fmix",        0},
  {"murmur3 fmix64",         1},
  {"moremur",                2},
  {"rrmxmx",                 3},
  {"identity (pure adder)",  4},
  {"xor-shift only",         5},
};
#define NMIX ((int)(sizeof MIXES / sizeof MIXES[0]))

static uint64_t rotr64(uint64_t x, int r){ return (x >> r) | (x << (64 - r)); }
static uint64_t rotl64(uint64_t x, int r){ return (x << r) | (x >> (64 - r)); }

static uint64_t fwd(int kind, uint64_t z){
  switch(kind){
    case 0: z ^= z>>30; z *= 0xBF58476D1CE4E5B9ULL; z ^= z>>27;
            z *= 0x94D049BB133111EBULL; z ^= z>>31; return z;
    case 1: z ^= z>>33; z *= 0xFF51AFD7ED558CCDULL; z ^= z>>33;
            z *= 0xC4CEB9FE1A85EC53ULL; z ^= z>>33; return z;
    case 2: z ^= z>>27; z *= 0x3C79AC492BA7B653ULL; z ^= z>>33;
            z *= 0x1C69B3F74AC4AE35ULL; z ^= z>>27; return z;
    case 3: z ^= rotr64(z,49) ^ rotr64(z,24); z *= 0x9FB21C651E98DF25ULL;
            z ^= z>>28; z *= 0x9FB21C651E98DF25ULL; z ^= z>>28; return z;
    case 4: return z;
    case 5: z ^= z>>30; z ^= z>>27; z ^= z>>31; return z;
  }
  return z;
}
static uint64_t inv(int kind, uint64_t z){
  switch(kind){
    case 0: z = unxsr(z,31); z *= inv_odd(0x94D049BB133111EBULL); z = unxsr(z,27);
            z *= inv_odd(0xBF58476D1CE4E5B9ULL); z = unxsr(z,30); return z;
    case 1: z = unxsr(z,33); z *= inv_odd(0xC4CEB9FE1A85EC53ULL); z = unxsr(z,33);
            z *= inv_odd(0xFF51AFD7ED558CCDULL); z = unxsr(z,33); return z;
    case 2: z = unxsr(z,27); z *= inv_odd(0x1C69B3F74AC4AE35ULL); z = unxsr(z,33);
            z *= inv_odd(0x3C79AC492BA7B653ULL); z = unxsr(z,27); return z;
    case 3: { z = unxsr(z,28); z *= inv_odd(0x9FB21C651E98DF25ULL); z = unxsr(z,28);
              z *= inv_odd(0x9FB21C651E98DF25ULL);
              /* invert z ^= rotr(z,49) ^ rotr(z,24) by iterating the affine map */
              uint64_t y = z, x = z;
              for(int i = 0; i < 64; i++) x = y ^ rotr64(x,49) ^ rotr64(x,24);
              return x; }
    case 4: return z;
    case 5: { uint64_t y = z, x = z;
              for(int i = 0; i < 64; i++){ x = y; x ^= x>>31; x ^= x>>27; x ^= x>>30;
                                           x = y ^ ((x^(x>>30)^((x^(x>>30))>>27))>>0)*0; break; }
              /* do it properly: undo in reverse order */
              z = unxsr(z,31); z = unxsr(z,27); z = unxsr(z,30); return z; }
  }
  return z;
}

/* open-addressed table counting 64-bit differences */
#define HB 26
#define HN (1ULL << HB)
static uint64_t *HK; static uint32_t *HV;
static void hinit(void){ HK = calloc(HN, 8); HV = calloc(HN, 4); }
static void hclear(void){ memset(HK, 0, HN*8); memset(HV, 0, HN*4); }
static uint32_t hbump(uint64_t k){
  if(!k) k = 1;
  uint64_t h = (k * 0x9E3779B97F4A7C15ULL) >> (64 - HB);
  for(;;){
    if(HK[h] == k) return ++HV[h];
    if(HK[h] == 0){ HK[h] = k; HV[h] = 1; return 1; }
    h = (h + 1) & (HN - 1);
  }
}

static uint64_t *R; static long N;

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

static void loadrank(const char *fn){
  FILE *f = fopen(fn,"rb"); if(!f){ perror(fn); exit(1); }
  fseek(f,0,SEEK_END); long sz = ftell(f); fseek(f,0,SEEK_SET);
  N = sz/8; R = malloc(sz);
  if((long)fread(R,8,N,f)!=N){ fprintf(stderr,"short read\n"); exit(1); } fclose(f);
}

/* Largest recurrence of any candidate difference; also, if `target` is non-zero, the
   recurrence of that specific difference. The two are not always the same: with the
   identity finalizer the output IS the additive state, so differences of the form
   gamma + jC also recur and can outrank gamma itself. That degeneracy raises the
   tool's chance level for that one row, so the threshold is calibrated per finalizer
   from a mixed stream of the SAME length rather than assumed. */
static uint32_t TGT_COUNT;
static uint32_t scan2(int kind, long nd, uint64_t *bestdiff, uint64_t target){
  hclear(); uint32_t best = 0; *bestdiff = 0; TGT_COUNT = 0;
  uint64_t cand[2][8]; int nc[2];
  for(long d = 0; d + 1 < nd; d++){
    for(int i = 0; i < 2; i++){
      u64 raw[8]; nc[i] = cands_model(R[d+i], raw);
      for(int q = 0; q < nc[i]; q++) cand[i][q] = inv(kind, raw[q]);
    }
    for(int a = 0; a < nc[0]; a++)
      for(int b = 0; b < nc[1]; b++){
        uint64_t df = cand[1][b] - cand[0][a];
        uint32_t c = hbump(df);
        if(c > best){ best = c; *bestdiff = df; }
        if(target && df == target) TGT_COUNT = c;
      }
  }
  return best;
}
static uint32_t scan(int kind, long nd, uint64_t *bestdiff){
  return scan2(kind, nd, bestdiff, 0);
}

int main(int argc, char **argv){
  const char *mode = argc > 1 ? argv[1] : "selftest";
  hinit();
  if(!strcmp(mode, "selftest")){
    MODEL = argc > 2 ? atoi(argv[2]) : 0;
    printf("reduction model: %s\n", MODEL ? "mulhi (Lemire)" : "u mod C");
    printf("selftest: every finalizer must be a bijection, a planted generator must show a\n");
    printf("  difference recurring at every draw, and a mixed stream must show none.\n\n");
    for(int m = 0; m < NMIX; m++){
      int bij = 1;
      for(uint64_t t = 0; t < 40000; t++){
        uint64_t z = t * 0x9E3779B97F4A7C15ULL + 12345;
        if(inv(MIXES[m].kind, fwd(MIXES[m].kind, z)) != z){ bij = 0; break; }
      }
      long nd = 400; R = malloc(8*nd); N = nd;
      uint64_t s = 0xCAFEBABEDEADBEEFULL, g = 0x9E3779B97F4A7C15ULL * 7;  /* W=7 */
      for(long i = 0; i < nd; i++){ R[i] = mkrank(fwd(MIXES[m].kind, s)); s += g; }
      uint64_t bd; uint32_t hit = scan2(MIXES[m].kind, nd, &bd, g);
      uint32_t tgt = TGT_COUNT;
      free(R);
      /* control: a stream from a DIFFERENT construction (not additive-state) */
      R = malloc(8*nd); N = nd; uint64_t st = 0x1234567ULL;
      for(long i = 0; i < nd; i++){
        st = st * 6364136223846793005ULL + 1442695040888963407ULL;   /* LCG, not additive */
        R[i] = mkrank(fwd(MIXES[m].kind, st ^ (st >> 17)));
      }
      uint64_t bd2; uint32_t fp = scan(MIXES[m].kind, nd, &bd2);
      free(R);
      printf("  %-22s bijection=%-3s  gamma recurs %u/%ld  top=%-5u  control max=%-3u  %s\n",
             MIXES[m].name, bij?"yes":"NO", tgt, nd-1, hit, fp,
             (bij && tgt >= nd-2 && fp < nd/10) ? "PASS" : "FAIL");
      fflush(stdout);
    }
    return 0;
  }
  const char *fn = argc > 2 ? argv[2] : "rank_colex0.bin";
  MODEL = argc > 3 ? atoi(argv[3]) : 0;
  loadrank(fn);
  printf("reduction model: %s\n", MODEL ? "mulhi (Lemire)" : "u mod C (with rejection)");
  printf("real archive: %s, %ld ranks\n", fn, N);
  printf("  additive state + bijective finalizer, gamma and W both unknown\n");
  printf("  a recurring difference would be the generator; chance gives at most a few\n\n");
  uint64_t *sav = R;
  for(int m = 0; m < NMIX; m++){
    uint64_t bd; uint32_t best = scan(MIXES[m].kind, N, &bd);
    /* calibrate: the same finalizer, the same number of draws, a stream that is NOT
       an additive state.  Whatever recurrence that reaches is this row's chance level. */
    R = malloc(8*N); uint64_t st = 0x1234567ULL ^ (uint64_t)m;
    for(long i = 0; i < N; i++){
      st = st * 6364136223846793005ULL + 1442695040888963407ULL;
      R[i] = mkrank(fwd(MIXES[m].kind, st ^ (st >> 17)));
    }
    uint64_t bd2; uint32_t nul = scan(MIXES[m].kind, N, &bd2);
    free(R); R = sav;
    printf("  %-22s archive max %-6u   null at same length %-6u   %s\n",
           MIXES[m].name, best, nul,
           best > 4*nul + 16 ? "*** INVESTIGATE ***" : "(at chance — not this construction)");
    fflush(stdout);
  }
  return 0;
}
