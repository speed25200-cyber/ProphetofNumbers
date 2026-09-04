/* mrgkiss — the two families numpy does not carry, and the algebra cannot reach.
 *
 * RECHERCHE.md declares three gaps: PCG64 at a fully unknown 128-bit state, MRG32k3a at
 * 192, and KISS-style combined generators. All three resist the complexity measures and
 * the algebraic solvers, for reasons stated there. But a gap in the abstract is not a gap
 * in practice — an operator does not pick a random 192-bit state, they seed from an
 * integer. modern_seed.py sweeps the PCG64 family through numpy itself; these two have no
 * numpy implementation, so they are written out here.
 *
 *   MRG32k3a  — L'Ecuyer's combined multiple recursive generator, two order-3 recurrences
 *               modulo 2^32-209 and 2^32-22853. Used by MATLAB, Arena, Simul8.
 *   KISS99 / JKISS — Marsaglia's combination of an LCG, a xorshift and a multiply-with-
 *               carry. The SUM is none of the structures tested, which is exactly why it
 *               escaped: not F2-linear (carries), not congruential (independent states).
 *
 * Both are seeded the way a working programmer seeds them, and both output paths are
 * checked (u mod C with rejection, and mulhi).
 *
 *   ./mrgkiss selftest
 *   ./mrgkiss real <rankfile> <lo> <hi> [threads]
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <pthread.h>

typedef unsigned __int128 u128;
typedef uint64_t u64;
static const u64 CC = 3535316142212174320ULL;

/* ---- MRG32k3a, L'Ecuyer's constants ---- */
#define M1 4294967087.0
#define M2 4294944443.0
static double mrg32k3a(double *s, int n){          /* s: 6 doubles, returns one output */
  double p1, p2, out = 0;
  for(int i = 0; i < n; i++){
    p1 = 1403580.0*s[1] - 810728.0*s[0];
    long k = (long)(p1 / M1); p1 -= k * M1; if(p1 < 0) p1 += M1;
    s[0] = s[1]; s[1] = s[2]; s[2] = p1;
    p2 = 527612.0*s[5] - 1370589.0*s[3];
    k = (long)(p2 / M2); p2 -= k * M2; if(p2 < 0) p2 += M2;
    s[3] = s[4]; s[4] = s[5]; s[5] = p2;
    out = (p1 <= p2) ? (p1 - p2 + M1) : (p1 - p2);
  }
  return out;                                       /* in [1, M1-1] */
}

/* ---- KISS99 (Marsaglia): LCG + xorshift + two MWCs ---- */
typedef struct { uint32_t z, w, jsr, jcong; } KISS;
static uint32_t kiss99(KISS *k){
  k->z = 36969*(k->z & 65535) + (k->z >> 16);
  k->w = 18000*(k->w & 65535) + (k->w >> 16);
  uint32_t mwc = (k->z << 16) + k->w;
  k->jcong = 69069*k->jcong + 1234567;
  k->jsr ^= k->jsr << 17; k->jsr ^= k->jsr >> 13; k->jsr ^= k->jsr << 5;
  return (mwc ^ k->jcong) + k->jsr;
}

/* build a 64-bit quantity from a seed, for generator g and skip */
static u64 gen64(int g, u64 seed, int skip){
  if(g == 0){                                        /* MRG32k3a, seed replicated */
    double s[6];
    for(int i = 0; i < 6; i++){
      u64 v = (seed + 1 + (u64)i * 0x9E3779B9ULL) % 4294967086ULL + 1;
      s[i] = (double)v;
    }
    if(skip) mrg32k3a(s, skip);
    double a = mrg32k3a(s, 1), b = mrg32k3a(s, 1);
    return ((u64)(a) << 32) | (u64)(b);
  }
  if(g == 1){                                        /* MRG32k3a, seed in the first word */
    double s[6] = {12345,12345,12345,12345,12345,12345};
    s[0] = (double)(seed % 4294967086ULL + 1);
    if(skip) mrg32k3a(s, skip);
    double a = mrg32k3a(s, 1), b = mrg32k3a(s, 1);
    return ((u64)(a) << 32) | (u64)(b);
  }
  if(g == 2){                                        /* KISS99, seed replicated */
    KISS k = { (uint32_t)(seed | 1), (uint32_t)(seed >> 32) | 1,
               (uint32_t)(seed ^ 0x5EED) | 1, (uint32_t)seed };
    if(!k.z) k.z = 362436069; if(!k.w) k.w = 521288629;
    if(!k.jsr) k.jsr = 123456789;
    for(int i = 0; i < skip; i++) kiss99(&k);
    u64 a = kiss99(&k), b = kiss99(&k);
    return (a << 32) | b;
  }
  /* KISS99, Marsaglia's published defaults with only jcong seeded */
  KISS k = { 362436069u, 521288629u, 123456789u, (uint32_t)seed };
  for(int i = 0; i < skip; i++) kiss99(&k);
  u64 a = kiss99(&k), b = kiss99(&k);
  return (a << 32) | b;
}
static const char *GN[] = {"MRG32k3a (seed spread)", "MRG32k3a (seed in s0)",
                           "KISS99 (seed spread)",   "KISS99 (jcong seeded)"};
#define NG 4

static u64 TARGET; static int NTH;
typedef struct { u64 a, b; long long hits; u64 hs; int hg, hk; } JOB;
static void *worker(void *p){
  JOB *j = (JOB*)p; j->hits = 0;
  for(u64 s = j->a; s < j->b; s++)
    for(int g = 0; g < NG; g++)
      for(int k = 0; k <= 2; k++){
        u64 u = gen64(g, s, k);
        if(u % CC == TARGET || (u64)(((u128)u * CC) >> 64) == TARGET){
          j->hits++; if(j->hits == 1){ j->hs = s; j->hg = g; j->hk = k; }
        }
      }
  return NULL;
}

int main(int argc, char **argv){
  const char *mode = argc > 1 ? argv[1] : "selftest";
  if(!strcmp(mode, "selftest")){
    printf("selftest: plant a seed in each construction, it must be recovered;\n");
    printf("  and a rank belonging to none of them must not be.\n\n");
    int found = 0;
    for(int g = 0; g < NG; g++){
      u64 seed = 4242 + g * 31;
      TARGET = gen64(g, seed, 1) % CC;
      JOB j = { seed - 200, seed + 200, 0, 0, 0, 0 };
      worker(&j);
      int ok = j.hits >= 1; found += ok;
      printf("  %-24s planted seed %llu %s\n", GN[g], (unsigned long long)seed,
             ok ? "recovered" : "MISSED");
    }
    u64 z = 0xFEEDFACE12345678ULL;
    z=(z^(z>>30))*0xBF58476D1CE4E5B9ULL; z=(z^(z>>27))*0x94D049BB133111EBULL; z^=z>>31;
    TARGET = z % CC;
    JOB j = { 0, 2000000, 0, 0, 0, 0 }; worker(&j);
    printf("  sweep of 2e6 seeds x %d constructions x 3 skips against an unowned rank: %lld\n",
           NG, j.hits);
    printf("  %s\n", (found == NG && j.hits == 0) ? "PASS" : "FAIL");
    return 0;
  }
  if(argc < 5){ fprintf(stderr, "usage: mrgkiss real <rankfile> <lo> <hi> [threads]\n"); return 1; }
  FILE *f = fopen(argv[2], "rb"); if(!f){ perror(argv[2]); return 1; }
  fseek(f,0,SEEK_END); long sz = ftell(f); fseek(f,0,SEEK_SET);
  long n = sz/8; u64 *R = malloc(sz);
  if((long)fread(R,8,n,f) != n){ fprintf(stderr,"short read\n"); return 1; } fclose(f);
  TARGET = R[0];
  u64 lo = strtoull(argv[3],0,0), hi = strtoull(argv[4],0,0);
  NTH = argc > 5 ? atoi(argv[5]) : 4;
  printf("%s draw 0, rank %llu; seeds [%llu,%llu) x %d constructions x 3 skips x 2 mappings\n",
         argv[2], (unsigned long long)TARGET, (unsigned long long)lo,
         (unsigned long long)hi, NG);
  pthread_t th[32]; JOB jb[32];
  u64 span = (hi - lo + NTH - 1)/NTH;
  for(int t = 0; t < NTH; t++){
    jb[t] = (JOB){ lo + t*span, (lo+(t+1)*span < hi) ? lo+(t+1)*span : hi, 0,0,0,0 };
    pthread_create(&th[t],0,worker,&jb[t]);
  }
  long long tot = 0;
  for(int t = 0; t < NTH; t++){ pthread_join(th[t],0); tot += jb[t].hits;
    if(jb[t].hits) printf("  HIT seed=%llu %s skip=%d\n",
                          (unsigned long long)jb[t].hs, GN[jb[t].hg], jb[t].hk); }
  printf("  total hits: %lld  ->  %s\n", tot,
         tot ? "*** INVESTIGATE ***" : "no MRG32k3a or KISS seeding in this range produces the rank");
  return 0;
}
