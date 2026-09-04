/* rankseed — the 2^32 seed sweep, redone for the unranking architecture.
 *
 * seedhunt sweeps every 32-bit seed and scores how long a Fisher-Yates prefix matches.
 * That is the right test for a generator that PRODUCES AN ORDER. It says nothing about
 * the architecture of section 6 quater, where the operator draws one integer and
 * unranks it: there is no shuffle for seedhunt to score.
 *
 * So the sweep has never been run for that model. It is run here. For each seed and each
 * generator, take the first output(s), map them into [0, C(80,20)), and compare with the
 * rank actually published. A match is 61.6 bits at once — over 2^32 seeds a false one
 * arrives with probability 2^32 * 2^-61.6 = 2^-29.6, so a single hit is the answer.
 *
 *   ./rankseed selftest
 *   ./rankseed <rankfile> <draw index> <lo> <hi> [threads]
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <pthread.h>

typedef unsigned __int128 u128;
typedef uint64_t u64;
static const u64 CC = 3535316142212174320ULL;

/* ---- generators: seed -> a 64-bit quantity, `skip` outputs discarded first ---- */
static const char *GN[] = {"minstd16807","minstd48271","randu","java48","msvc","borland",
  "xorshift32","xorshift64","splitmix64","lcg64_mmix","nr_ranqd1","pcg32","mt19937",
  "xoshiro256ss","lcg64_knuth","xorshift128"};
#define NG 16

static u64 rotl64(u64 x,int k){ return (x<<k)|(x>>(64-k)); }

/* MT19937 just far enough to produce a couple of outputs */
typedef struct { uint32_t mt[624]; int i; } MT;
static void mt_seed(MT *s, uint32_t seed){
  s->mt[0] = seed;
  for(int i = 1; i < 624; i++) s->mt[i] = 1812433253u*(s->mt[i-1]^(s->mt[i-1]>>30))+i;
  s->i = 624;
}
static uint32_t mt_next(MT *s){
  if(s->i >= 624){
    for(int i = 0; i < 624; i++){
      uint32_t y = (s->mt[i]&0x80000000u)|(s->mt[(i+1)%624]&0x7fffffffu);
      uint32_t n = s->mt[(i+397)%624] ^ (y>>1);
      if(y&1) n ^= 0x9908b0dfu;
      s->mt[i] = n;
    }
    s->i = 0;
  }
  uint32_t y = s->mt[s->i++];
  y^=y>>11; y^=(y<<7)&0x9d2c5680u; y^=(y<<15)&0xefc60000u; y^=y>>18;
  return y;
}

/* returns a 64-bit value for (generator g, seed, skip); 32-bit generators use two words */
static u64 gen64(int g, u64 seed, int skip){
  switch(g){
    case 0: { u64 x = seed % 2147483647ULL; if(!x) x = 1;
              for(int i=0;i<skip;i++) x = (16807ULL*x)%2147483647ULL;
              u64 a = (16807ULL*x)%2147483647ULL, b = (16807ULL*a)%2147483647ULL;
              u64 c = (16807ULL*b)%2147483647ULL; return (a<<33)^(b<<2)^c; }
    case 1: { u64 x = seed % 2147483647ULL; if(!x) x = 1;
              for(int i=0;i<skip;i++) x = (48271ULL*x)%2147483647ULL;
              u64 a = (48271ULL*x)%2147483647ULL, b = (48271ULL*a)%2147483647ULL;
              u64 c = (48271ULL*b)%2147483647ULL; return (a<<33)^(b<<2)^c; }
    case 2: { u64 x = (seed|1) & 0x7FFFFFFFULL;
              for(int i=0;i<skip;i++) x = (65539ULL*x) & 0x7FFFFFFFULL;
              u64 a=(65539ULL*x)&0x7FFFFFFFULL, b=(65539ULL*a)&0x7FFFFFFFULL;
              u64 c=(65539ULL*b)&0x7FFFFFFFULL; return (a<<33)^(b<<2)^c; }
    case 3: { u64 x = (seed ^ 0x5DEECE66DULL) & ((1ULL<<48)-1);
              for(int i=0;i<skip;i++) x = (x*0x5DEECE66DULL+0xB) & ((1ULL<<48)-1);
              x = (x*0x5DEECE66DULL+0xB) & ((1ULL<<48)-1); u64 hi = x>>16;
              x = (x*0x5DEECE66DULL+0xB) & ((1ULL<<48)-1); u64 lo = x>>16;
              return (hi<<32)|(lo&0xFFFFFFFFULL); }
    case 4: { u64 x = seed;
              for(int i=0;i<skip;i++) x = (214013ULL*x+2531011ULL)&0xFFFFFFFFULL;
              u64 a,b,c;
              x=(214013ULL*x+2531011ULL)&0xFFFFFFFFULL; a=(x>>16)&0x7FFF;
              x=(214013ULL*x+2531011ULL)&0xFFFFFFFFULL; b=(x>>16)&0x7FFF;
              x=(214013ULL*x+2531011ULL)&0xFFFFFFFFULL; c=(x>>16)&0x7FFF;
              u64 d; x=(214013ULL*x+2531011ULL)&0xFFFFFFFFULL; d=(x>>16)&0x7FFF;
              return (a<<48)|(b<<33)|(c<<18)|(d<<3); }
    case 5: { u64 x = seed;
              for(int i=0;i<skip;i++) x = (22695477ULL*x+1ULL)&0xFFFFFFFFULL;
              x=(22695477ULL*x+1)&0xFFFFFFFFULL; u64 a=x;
              x=(22695477ULL*x+1)&0xFFFFFFFFULL; u64 b=x;
              return (a<<32)|b; }
    case 6: { uint32_t x = (uint32_t)seed; if(!x) x = 1;
              for(int i=0;i<skip;i++){ x^=x<<13; x^=x>>17; x^=x<<5; }
              x^=x<<13; x^=x>>17; x^=x<<5; u64 a=x;
              x^=x<<13; x^=x>>17; x^=x<<5; u64 b=x;
              return (a<<32)|b; }
    case 7: { u64 x = seed ? seed : 1;
              for(int i=0;i<=skip;i++){ x^=x<<13; x^=x>>7; x^=x<<17; } return x; }
    case 8: { u64 x = seed;
              for(int i=0;i<=skip;i++){ x += 0x9E3779B97F4A7C15ULL; }
              u64 z = x; z=(z^(z>>30))*0xBF58476D1CE4E5B9ULL;
              z=(z^(z>>27))*0x94D049BB133111EBULL; return z^(z>>31); }
    case 9: { u64 x = seed;
              for(int i=0;i<=skip;i++) x = x*6364136223846793005ULL+1442695040888963407ULL;
              return x; }
    case 10:{ u64 x = seed;
              for(int i=0;i<skip;i++) x = (1664525ULL*x+1013904223ULL)&0xFFFFFFFFULL;
              x=(1664525ULL*x+1013904223ULL)&0xFFFFFFFFULL; u64 a=x;
              x=(1664525ULL*x+1013904223ULL)&0xFFFFFFFFULL; u64 b=x;
              return (a<<32)|b; }
    case 11:{ u64 st = seed*6364136223846793005ULL+1442695040888963407ULL;
              uint32_t o1=0,o2=0;
              for(int i=0;i<=skip+1;i++){
                u64 old = st; st = old*6364136223846793005ULL+1442695040888963407ULL;
                uint32_t xs = (uint32_t)(((old>>18)^old)>>27); int r = old>>59;
                uint32_t v = (xs>>r)|(xs<<((-r)&31));
                o1 = o2; o2 = v; }
              return ((u64)o1<<32)|o2; }
    case 12:{ MT s; mt_seed(&s,(uint32_t)seed);
              for(int i=0;i<skip;i++) mt_next(&s);
              u64 a = mt_next(&s), b = mt_next(&s); return (a<<32)|b; }
    case 13:{ u64 st[4]; u64 z = seed;
              for(int i=0;i<4;i++){ z += 0x9E3779B97F4A7C15ULL; u64 w = z;
                w=(w^(w>>30))*0xBF58476D1CE4E5B9ULL; w=(w^(w>>27))*0x94D049BB133111EBULL;
                st[i] = w^(w>>31); }
              u64 out = 0;
              for(int i=0;i<=skip;i++){
                out = rotl64(st[1]*5,7)*9;
                u64 t = st[1]<<17;
                st[2]^=st[0]; st[3]^=st[1]; st[1]^=st[2]; st[0]^=st[3]; st[2]^=t;
                st[3]=rotl64(st[3],45); }
              return out; }
    case 14:{ u64 x = seed;
              for(int i=0;i<=skip;i++) x = x*6364136223846793005ULL+1442695040888963407ULL;
              return x*2862933555777941757ULL+3037000493ULL; }
    default:{ u64 a = seed?seed:1, b = seed^0x9E3779B97F4A7C15ULL;
              for(int i=0;i<=skip;i++){ u64 t=a; t^=t<<23; t^=t>>17; t^=b^(b>>26); a=b; b=t; }
              return a+b; }
  }
}

static u64 TARGET; static u64 A0, B0; static int NTH;
typedef struct { u64 a, b; int tid; long long hits; u64 hs; int hg, hm, hk; } JOB;

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
  if(argc > 1 && !strcmp(argv[1],"selftest")){
    printf("selftest: plant a seed for each generator, it must be found; and the sweep\n");
    printf("  must find nothing when the target rank belongs to no generator.\n\n");
    int found = 0;
    for(int g = 0; g < NG; g++){
      u64 seed = 0x0BADC0DE + g*7919;
      TARGET = gen64(g, seed, 1) % CC;
      JOB j = { seed - 300, seed + 300, 0, 0, 0, 0, 0, 0 };
      worker(&j);
      int ok = (j.hits >= 1);
      found += ok;
      if(!ok) printf("  %-14s MISSED\n", GN[g]);
    }
    printf("  planted seeds found for %d of %d generators\n", found, NG);
    /* a rank that came from no generator at all */
    u64 z = 0xFEEDFACE12345678ULL;
    z=(z^(z>>30))*0xBF58476D1CE4E5B9ULL; z=(z^(z>>27))*0x94D049BB133111EBULL; z^=z>>31;
    TARGET = z % CC;
    JOB j = { 0, 3000000, 0, 0, 0, 0, 0, 0 };
    worker(&j);
    printf("  sweep of 3e6 seeds x %d generators x 3 skips against an unowned rank: %lld hits\n",
           NG, j.hits);
    printf("  %s\n", (found == NG && j.hits == 0) ? "PASS" : "FAIL");
    return 0;
  }
  if(argc < 5){ fprintf(stderr,"usage: rankseed <rankfile> <idx> <lo> <hi> [threads]\n"); return 1; }
  FILE *f = fopen(argv[1],"rb"); if(!f){ perror(argv[1]); return 1; }
  fseek(f,0,SEEK_END); long sz = ftell(f); fseek(f,0,SEEK_SET);
  long n = sz/8; u64 *R = malloc(sz);
  if((long)fread(R,8,n,f)!=n){ fprintf(stderr,"short read\n"); return 1; } fclose(f);
  long idx = atol(argv[2]); TARGET = R[idx];
  u64 lo = strtoull(argv[3],0,0), hi = strtoull(argv[4],0,0);
  NTH = argc>5?atoi(argv[5]):4;
  printf("draw %ld, rank %llu;  seeds [%llu,%llu) x %d generators x 3 skips x 2 mappings\n",
         idx, (unsigned long long)TARGET, (unsigned long long)lo, (unsigned long long)hi, NG);
  pthread_t th[32]; JOB jb[32];
  u64 span = (hi - lo + NTH - 1)/NTH;
  for(int t = 0; t < NTH; t++){
    jb[t] = (JOB){ lo + t*span, (lo+(t+1)*span < hi) ? lo+(t+1)*span : hi, t, 0,0,0,0,0 };
    pthread_create(&th[t],0,worker,&jb[t]);
  }
  long long tot = 0;
  for(int t = 0; t < NTH; t++){ pthread_join(th[t],0); tot += jb[t].hits;
    if(jb[t].hits) printf("  HIT seed=%llu gen=%s skip=%d\n",
                          (unsigned long long)jb[t].hs, GN[jb[t].hg], jb[t].hk); }
  printf("  total hits: %lld  ->  %s\n", tot,
         tot ? "*** INVESTIGATE ***" : "no seed of any swept generator produces this rank");
  return 0;
}
