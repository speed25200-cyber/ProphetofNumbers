/* rankxo — the ** scramblers, which neither Berlekamp-Massey nor rankmix can touch.
 *
 * bm.c excludes every F2-linear generator whose observed bit is a linear functional of
 * the state. That leaves the modern "scrambled" generators: xoshiro256** and
 * xoroshiro128** put a NON-linear map on top of a linear core —
 *
 *     out = rotl(s1 * 5, 7) * 9
 *
 * so no output bit is a linear functional and the linear-complexity test says nothing
 * about them. RECHERCHE.md files them, with splitmix64 and PCG, under "out of reach":
 * from 4 bits per draw they need a SAT solve across the carry chain.
 *
 * But that scrambler is a BIJECTION — multiply by 5, rotate, multiply by 9, all
 * invertible mod 2^64. With a full 61.6-bit output the non-linearity simply peels off:
 *
 *     s1 = rotr(out * 9^-1, 7) * 5^-1
 *
 * and what is left underneath IS linear. Four recovered words are 256 bits, exactly the
 * state size, so the state falls out of one linear solve — no search over the carry
 * chain, no SAT.
 *
 * The linear map is built by RUNNING the generator on basis states rather than by
 * symbolic algebra: column i of the matrix is what the observable does when the state is
 * the unit vector e_i. That is only valid because the update is purely F2-linear (xor,
 * shift, rotate, no addition), which the selftest verifies directly.
 *
 * The rank leaves out = r + kC undetermined among 6 values, so each window costs 6^D
 * assignments — 1296 for a 256-bit state. The recovered state is then run forward and
 * checked against further draws, where a wrong one passes with probability 2^-185.
 *
 *   ./rankxo selftest
 *   ./rankxo real <rankfile> [maxW]
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

typedef unsigned __int128 u128;
typedef uint64_t u64;
static const u64 CC = 3535316142212174320ULL;

static u64 inv_odd(u64 a){ u64 x=a; for(int i=0;i<6;i++) x *= 2-a*x; return x; }
static u64 rotl(u64 x,int k){ return (x<<k)|(x>>(64-k)); }
static u64 rotr(u64 x,int k){ return (x>>k)|(x<<(64-k)); }

/* ---- generators: purely F2-linear update, bijective scrambler on one state word ---- */
typedef struct { const char *name; int words; } GEN;
static const GEN GENS[] = { {"xoshiro256**", 4}, {"xoroshiro128**", 2}, {"xoshiro512**", 8} };
#define NGEN 3

static u64 observed_word(int g, const u64 *s){          /* the word the scrambler eats */
  return (g == 0) ? s[1] : s[0];
}
static u64 scramble(u64 w){ return rotl(w * 5, 7) * 9; }
static u64 unscramble(u64 o){ return rotr(o * inv_odd(9), 7) * inv_odd(5); }

static void step(int g, u64 *s){
  if(g == 0){                                            /* xoshiro256** */
    const u64 t = s[1] << 17;
    s[2] ^= s[0]; s[3] ^= s[1]; s[1] ^= s[2]; s[0] ^= s[3]; s[2] ^= t; s[3] = rotl(s[3],45);
  } else if(g == 1){                                     /* xoroshiro128** */
    u64 s0 = s[0], s1 = s[1]; s1 ^= s0;
    s[0] = rotl(s0,24) ^ s1 ^ (s1 << 16); s[1] = rotl(s1,37);
  } else {                                               /* xoshiro512** */
    const u64 t = s[1] << 11;
    s[2]^=s[0]; s[5]^=s[1]; s[1]^=s[2]; s[7]^=s[3]; s[3]^=s[4];
    s[4]^=s[5]; s[0]^=s[6]; s[6]^=s[7]; s[6]^=t; s[7]=rotl(s[7],21);
  }
}

/* ---- GF(2) linear algebra on n<=512 bits ---- */
#define MAXW 8
typedef struct { u64 w[MAXW]; } BV;
static int NWD;
static void bv_zero(BV *a){ memset(a->w, 0, sizeof a->w); }
static void bv_xor(BV *a, const BV *b){ for(int i=0;i<NWD;i++) a->w[i] ^= b->w[i]; }
static int  bv_get(const BV *a, int i){ return (a->w[i>>6] >> (i&63)) & 1; }
static void bv_set(BV *a, int i){ a->w[i>>6] |= 1ULL << (i&63); }

/* invert A (n x n, rows as bitvectors over columns) -> INV; returns 0 if singular */
static int singular_col;
static int invert(BV *A, BV *INV, int n){
  singular_col = -1;
  for(int i = 0; i < n; i++){ bv_zero(&INV[i]); bv_set(&INV[i], i); }
  for(int c = 0; c < n; c++){
    int p = -1;
    for(int r = c; r < n; r++) if(bv_get(&A[r], c)){ p = r; break; }
    if(p < 0){ singular_col = c; return 0; }
    if(p != c){ BV t=A[p]; A[p]=A[c]; A[c]=t; t=INV[p]; INV[p]=INV[c]; INV[c]=t; }
    for(int r = 0; r < n; r++)
      if(r != c && bv_get(&A[r], c)){ bv_xor(&A[r], &A[c]); bv_xor(&INV[r], &INV[c]); }
  }
  return 1;
}

static u64 *R; static long N;
static int SEL[640];

/* pick n independent rows out of `rows`, record them in SEL, invert that submatrix */
static int prepare(BV *A, int rows, int n, BV *INV){
  BV *tmp = malloc(sizeof(BV) * n); int got = 0;
  BV *piv = malloc(sizeof(BV) * n); int npiv = 0; int pcol[640];
  for(int r = 0; r < rows && got < n; r++){
    BV v = A[r];
    for(int i = 0; i < npiv; i++) if(bv_get(&v, pcol[i])) bv_xor(&v, &piv[i]);
    int c = -1; for(int b = 0; b < n; b++) if(bv_get(&v, b)){ c = b; break; }
    if(c < 0) continue;
    piv[npiv] = v; pcol[npiv] = c; npiv++;
    tmp[got] = A[r]; SEL[got] = r; got++;
  }
  free(piv);
  if(got < n){ free(tmp); return 0; }
  int ok = invert(tmp, INV, n);
  free(tmp); return ok;
}

/* Build the map (initial state) -> (observed words at draws 0..D-1), W steps per draw.
   D words of 64 bits is exactly n bits, but the sampled functionals are not independent
   — measured rank 253/256 and 125/128 — so the caller passes one draw MORE and picks an
   independent basis out of the rows. */
static void build(int g, int W, int n, int D, BV *A){
  for(int i = 0; i < n; i++) bv_zero(&A[i]);
  u64 s[MAXW];
  for(int col = 0; col < n; col++){
    memset(s, 0, sizeof s); s[col>>6] = 1ULL << (col&63);
    for(int d = 0; d < D; d++){
      u64 o = observed_word(g, s);
      for(int b = 0; b < 64; b++) if((o >> b) & 1) bv_set(&A[d*64 + b], col);
      for(int k = 0; k < W; k++) step(g, s);
    }
  }
}

static int try_window(int g, int W, int n, int D, int DF, const BV *INV, long d0, int V, u64 *out){
  int nc[16]; u64 cand[16][8];
  for(int i = 0; i < DF; i++){
    nc[i] = 0;
    for(int k = 0; k <= 5; k++){
      u128 u = (u128)R[d0+i] + (u128)k * CC;
      if(u < ((u128)1 << 64)) cand[i][nc[i]++] = unscramble((u64)u);
    }
  }
  int idx[16]; memset(idx, 0, sizeof idx);
  for(;;){
    unsigned char raw[640];
    for(int i = 0; i < DF; i++){
      u64 w = cand[i][idx[i]];
      for(int b = 0; b < 64; b++) raw[i*64 + b] = (w >> b) & 1;
    }
    BV obs; bv_zero(&obs);
    for(int r = 0; r < n; r++) if(raw[SEL[r]]) bv_set(&obs, r);
    u64 s[MAXW]; memset(s, 0, sizeof s);
    for(int r = 0; r < n; r++){                       /* s = INV * obs */
      u64 p = 0; for(int q = 0; q < NWD; q++) p ^= INV[r].w[q] & obs.w[q];
      if(__builtin_parityll(p)) s[r>>6] |= 1ULL << (r&63);
    }
    int ok = 1;
    for(int d = 0; d < DF + V && ok; d++){
      u64 o = scramble(observed_word(g, s));
      if(o % CC != R[d0+d]) ok = 0;
      for(int k = 0; k < W; k++) step(g, s);
    }
    if(ok){ memcpy(out, s, sizeof(u64)*MAXW); return 1; }
    int i = 0; for(; i < DF; i++){ if(++idx[i] < nc[i]) break; idx[i] = 0; }
    if(i == DF) return 0;
  }
}

static void loadrank(const char *fn){
  FILE *f=fopen(fn,"rb"); if(!f){perror(fn);exit(1);}
  fseek(f,0,SEEK_END); long sz=ftell(f); fseek(f,0,SEEK_SET);
  N=sz/8; R=malloc(sz);
  if((long)fread(R,8,N,f)!=N){fprintf(stderr,"short read\n");exit(1);} fclose(f);
}

int main(int argc, char **argv){
  const char *mode = argc>1?argv[1]:"selftest";
  int V = 3;                       /* extra draws verified: a wrong state passes at 2^-185 */
  if(!strcmp(mode,"selftest")){
    printf("selftest: the update must be exactly F2-linear, the scrambler a bijection,\n");
    printf("  a planted generator must be recovered, and a mixed stream rejected.\n\n");
    for(int g = 0; g < NGEN; g++){
      int n = GENS[g].words * 64, D = GENS[g].words; NWD = (n + 63) / 64;
      /* the linearity the whole method rests on: step(a XOR b) == step(a) XOR step(b) */
      int lin = 1;
      for(int t = 0; t < 500 && lin; t++){
        u64 a[MAXW], b[MAXW], c[MAXW];
        for(int i = 0; i < GENS[g].words; i++){
          a[i] = 0x9E3779B97F4A7C15ULL*(t+1)+i; b[i] = 0xBF58476D1CE4E5B9ULL*(t+3)+i*7;
          c[i] = a[i] ^ b[i]; }
        step(g,a); step(g,b); step(g,c);
        for(int i = 0; i < GENS[g].words; i++) if((a[i]^b[i]) != c[i]) lin = 0;
      }
      int bij = 1;
      for(u64 t = 0; t < 200000; t++){ u64 z = t*0x9E3779B97F4A7C15ULL+7;
        if(unscramble(scramble(z)) != z){ bij = 0; break; } }
      int DF = D + 1;                       /* one draw more than the state needs */
      if(DF > 5){ printf("  %-16s linear=%-3s bijection=%-3s  6^%d assignments — skipped\n",
                         GENS[g].name, lin?"yes":"NO", bij?"yes":"NO", DF); continue; }
      int W = 5;
      long nd = 60; N = nd; R = malloc(8*nd);
      u64 s[MAXW]; memset(s,0,sizeof s);
      for(int i=0;i<GENS[g].words;i++) s[i] = 0xDEADBEEF12345678ULL*(i+1) ^ 0xABCDEF;
      for(long d=0; d<nd; d++){ R[d] = scramble(observed_word(g,s)) % CC;
                                for(int k=0;k<W;k++) step(g,s); }
      BV *A = malloc(sizeof(BV)*DF*64), *INV = malloc(sizeof(BV)*n);
      build(g, W, n, DF, A);
      int inv_ok = prepare(A, DF*64, n, INV);
      u64 got[MAXW]; int hit = 0;
      if(inv_ok) for(long d=0; d+DF+V<nd && !hit; d++) hit = try_window(g,W,n,D,DF,INV,d,V,got);
      free(R);
      /* control: a non-linear-core stream */
      R = malloc(8*nd); u64 st = 0x1234ULL;
      for(long d=0; d<nd; d++){ st += 0x9E3779B97F4A7C15ULL; u64 z = st;
        z=(z^(z>>30))*0xBF58476D1CE4E5B9ULL; z=(z^(z>>27))*0x94D049BB133111EBULL; z^=z>>31;
        R[d] = z % CC; }
      int fp = 0;
      if(inv_ok) for(long d=0; d+DF+V<nd && !fp; d++) fp = try_window(g,W,n,D,DF,INV,d,V,got);
      free(R); free(A); free(INV);
      printf("  %-16s linear=%-3s bijection=%-3s invertible=%-3s recovered=%-3s control=%-3s  %s\n",
             GENS[g].name, lin?"yes":"NO", bij?"yes":"NO", inv_ok?"yes":"NO",
             hit?"yes":"NO", fp?"HIT":"no", (lin&&bij&&inv_ok&&hit&&!fp)?"PASS":"FAIL");
      fflush(stdout);
    }
    return 0;
  }
  const char *fn = argc>2?argv[2]:"rank_colex0.bin";
  int maxW = argc>3?atoi(argv[3]):24;
  loadrank(fn);
  int STARTS = 64;
  printf("real archive: %s, %ld ranks;  W 1..%d, %d starting windows each\n",
         fn, N, maxW, STARTS);
  printf("  the scrambler is peeled off by inversion, the linear core solved directly\n\n");
  for(int g = 0; g < NGEN; g++){
    int n = GENS[g].words*64, D = GENS[g].words; NWD = (n+63)/64;
    int DF = D + 1;
    if(DF > 5){ printf("  %-16s 6^%d assignments per window — out of budget\n", GENS[g].name, DF);
                continue; }
    int DFMAX = D + 3;
    BV *A = malloc(sizeof(BV)*DFMAX*64), *INV = malloc(sizeof(BV)*n);
    long hits = 0; int sing = 0, maxdf = 0;
    for(int W = 1; W <= maxW; W++){
      /* Some W leave the sampled words short of spanning even with one extra draw.
         Rather than declare those W untested, take further draws until the basis
         closes — each costs a factor 6 in k-assignments, so it is capped. */
      int df = DF, ok = 0;
      for(; df <= DFMAX; df++){ build(g, W, n, df, A); if(prepare(A, df*64, n, INV)){ ok=1; break; } }
      if(!ok){ sing++; continue; }
      if(df > maxdf) maxdf = df;
      u64 got[MAXW];
      for(int t = 0; t < STARTS; t++){
        long d = (N - df - V - 2) * (long)t / STARTS;
        if(try_window(g, W, n, D, df, INV, d, V, got)) hits++;
      }
    }
    printf("  %-16s %ld windows solved out of %d   (%d W still singular, up to %d draws used)   %s\n",
           GENS[g].name, hits, maxW*STARTS, sing, maxdf,
           hits ? "*** INVESTIGATE ***" : "(not this generator, at any W)");
    free(A); free(INV); fflush(stdout);
  }
  return 0;
}
