/* bm — Berlekamp-Massey on every observable bit stream.
 *
 * Everything so far has tested named generators one at a time: pick MT19937, pick a
 * channel, pick W, build the GF(2) system, solve. Thousands of configurations, each a
 * separate hypothesis. That approach can only exclude what it thought to enumerate.
 *
 * Berlekamp-Massey needs no enumeration. If the observed bit is ANY F2-linear functional
 * of the state of ANY F2-linear generator — MT19937, MT19937-64, WELL, xorshift,
 * xoshiro's linear core, an LFSR of any taps, something nobody has published — then the
 * observed bit sequence is a linear recurring sequence whose LINEAR COMPLEXITY is at
 * most the state size. And that stays true when the generator is stepped W times per
 * draw: sampling a linear map every W steps is again a linear map, so W changes nothing.
 *
 * For a random sequence of length N the linear complexity sits at N/2 with a very tight
 * distribution. So one number decides it, for the whole class at once:
 *
 *     complexity << N/2   ->  an F2-linear generator, and the recurrence itself
 *     complexity ~= N/2   ->  no F2-linear generator of state < N/2 can produce it
 *
 * With 70 560 draws a stream detects any state up to ~35 000 bits — MT19937's 19 937
 * included, with room to spare.
 *
 *   ./bm selftest
 *   ./bm <bitfile>          one byte per bit, or use mkbits.py to produce them
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

typedef uint64_t u64;
static int NW;                       /* words per polynomial */

static void shl1(u64 *a){            /* a <<= 1 over the bitset */
  for(int i = NW - 1; i > 0; i--) a[i] = (a[i] << 1) | (a[i-1] >> 63);
  a[0] <<= 1;
}
static int dot(const u64 *a, const u64 *b){
  u64 p = 0; for(int i = 0; i < NW; i++) p ^= a[i] & b[i];
  return __builtin_parityll(p);
}
static void xoreq(u64 *a, const u64 *b){ for(int i = 0; i < NW; i++) a[i] ^= b[i]; }
static void shlk(u64 *dst, const u64 *src, int k){    /* dst = src << k */
  memset(dst, 0, NW * 8);
  int w = k >> 6, b = k & 63;
  for(int i = NW - 1; i >= w; i--){
    u64 v = src[i-w] << b;
    if(b && i - w - 1 >= 0) v |= src[i-w-1] >> (64 - b);
    dst[i] = v;
  }
}

/* linear complexity of s[0..n-1]; caller sizes NW for the largest degree expected */
static int berlekamp_massey(const unsigned char *s, int n){
  u64 *C = calloc(NW, 8), *B = calloc(NW, 8), *T = calloc(NW, 8), *W = calloc(NW, 8);
  u64 *Bs = calloc(NW, 8);
  C[0] = 1; B[0] = 1;
  int L = 0, m = 1;
  for(int i = 0; i < n; i++){
    shl1(W); W[0] |= 1u & s[i];                    /* W holds s[i], s[i-1], ... */
    int d = dot(C, W);
    if(d){
      memcpy(T, C, NW * 8);
      shlk(Bs, B, m);
      xoreq(C, Bs);
      if(2 * L <= i){ L = i + 1 - L; memcpy(B, T, NW * 8); m = 1; }
      else m++;
    } else m++;
    if(L > (NW * 64) - 8){ fprintf(stderr, "degree overflow\n"); exit(1); }
  }
  free(C); free(B); free(T); free(W); free(Bs);
  return L;
}

static unsigned char *readbits(const char *fn, int *n){
  FILE *f = fopen(fn, "rb"); if(!f){ perror(fn); exit(1); }
  fseek(f, 0, SEEK_END); long sz = ftell(f); fseek(f, 0, SEEK_SET);
  unsigned char *b = malloc(sz);
  if((long)fread(b, 1, sz, f) != sz){ fprintf(stderr, "short read\n"); exit(1); }
  fclose(f); *n = (int)sz; return b;
}

int main(int argc, char **argv){
  if(argc > 1 && !strcmp(argv[1], "selftest")){
    printf("selftest: linear complexity must equal the state size for F2-linear sources,\n");
    printf("  and sit at n/2 for a sequence that is not one.\n\n");
    int n = 4000; NW = (n / 64) + 4;
    unsigned char *s = malloc(n);

    /* xorshift64: state 64 bits, so complexity must be <= 64 */
    { u64 x = 0x139408DCBBF7A44ULL;
      for(int i = 0; i < n; i++){ x^=x<<13; x^=x>>7; x^=x<<17; s[i] = x & 1; }
      printf("  xorshift64,      bit 0      : complexity %5d   (state 64)\n",
             berlekamp_massey(s, n)); }
    /* an LFSR of 521 bits */
    { static u64 st[9]; for(int i=0;i<9;i++) st[i] = 0x9E3779B97F4A7C15ULL*(i+1);
      for(int i = 0; i < n; i++){
        int b = ((st[8]>>8) ^ (st[2]>>3)) & 1;      /* x^521 + x^32 + 1 style tap */
        for(int w = 8; w > 0; w--) st[w] = (st[w]<<1) | (st[w-1]>>63);
        st[0] = (st[0]<<1) | (u64)b;
        s[i] = b; }
      printf("  521-bit LFSR                : complexity %5d   (state 521)\n",
             berlekamp_massey(s, n)); }
    /* xorshift128, sampled every W=7 steps — W must not matter */
    { u64 a = 1, b = 2;
      for(int i = 0; i < n; i++){
        for(int k = 0; k < 7; k++){ u64 t = a; t ^= t<<23; t ^= t>>17; t ^= b ^ (b>>26);
                                    a = b; b = t; }
        s[i] = (a + b) & 1;                          /* bit 0 of an additive output is linear */
      }
      printf("  xorshift128+, W=7, bit 0    : complexity %5d   (state 128)\n",
             berlekamp_massey(s, n)); }
    /* NOT F2-linear: a mixed stream */
    { u64 st = 12345;
      for(int i = 0; i < n; i++){
        st += 0x9E3779B97F4A7C15ULL; u64 z = st;
        z = (z ^ (z>>30)) * 0xBF58476D1CE4E5B9ULL;
        z = (z ^ (z>>27)) * 0x94D049BB133111EBULL; z ^= z>>31;
        s[i] = z & 1; }
      printf("  splitmix64 output bit 0     : complexity %5d   (n/2 = %d)\n",
             berlekamp_massey(s, n), n/2); }
    free(s);
    return 0;
  }
  if(argc < 2){ fprintf(stderr, "usage: bm <bitfile> | bm selftest\n"); return 1; }
  int n; unsigned char *s = readbits(argv[1], &n);
  NW = (n / 2 / 64) + 8;
  int L = berlekamp_massey(s, n);
  printf("%-34s n=%6d  linear complexity %6d   n/2=%6d   %s\n",
         argv[1], n, L, n/2,
         L < n/2 - 200 ? "*** F2-LINEAR STRUCTURE ***" : "(no F2-linear generator of state < n/2)");
  return 0;
}
