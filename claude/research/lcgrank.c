/* lcgrank — solve an ARBITRARY LCG from the combinatorial rank of the sorted draws.
 *
 * The premise is in rank.py: if the operator draws one integer and *unranks* it into a
 * combination (the standard way to get a uniform k-subset without a shuffle), then the
 * published sorted draw is the generator output in full — 61.6 bits, not the 4 bits of
 * the bonus channel. Sorting destroys nothing, because there never was an order.
 *
 * With that much per draw the attack needs no guessed multiplier. Writing
 * u_{d+1} = A u_d + B (mod 2^64), three consecutive outputs give
 *
 *     A = (u2 - u1) / (u1 - u0),      B = u1 - A u0
 *
 * in closed form. And since A = a^W and B = c(a^{W-1}+...+1) for a generator stepped W
 * times per draw, solving for arbitrary (A,B) covers EVERY multiplier, EVERY increment
 * and EVERY W at once — the whole family in one shot, with no sweep.
 *
 * The rank r only gives u modulo C = C(80,20), but 2^64/C = 5.22, so u = r + kC with
 * k in 0..5: 216 combinations for a triple. Each candidate (A,B) is then checked against
 * further draws, where a wrong one survives with probability 1/C = 2^-61.6 per draw.
 *
 * modes   0  u mod 2^64,  r = u mod C
 *         1  u mod 2^64,  r = mulhi(u,C) = (u*C)>>64
 *         2  LCG modulo C itself, r = u
 *         3  u mod 2^63,  r = u mod C          (k in 0..2)
 *         4  u mod 2^62,  r = u mod C          (k in 0..1)
 *
 *   ./lcgrank selftest
 *   ./lcgrank real <rankfile> [mode]
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

typedef unsigned __int128 u128;
static const uint64_t CC = 3535316142212174320ULL;   /* C(80,20) */

static uint64_t inv_odd(uint64_t a){          /* inverse mod 2^64, a odd */
  uint64_t x = a;                             /* Newton: x <- x(2-ax) */
  for(int i = 0; i < 6; i++) x *= 2 - a * x;
  return x;
}
static int v2(uint64_t x){ return x ? __builtin_ctzll(x) : 64; }

/* --- arithmetic modulo CC (composite, so use __int128 and gcd where needed) --- */
static uint64_t mulC(uint64_t a, uint64_t b){ return (uint64_t)(((u128)a * b) % CC); }
static uint64_t egcd(uint64_t a, uint64_t b, long long *x, long long *y){
  if(!b){ *x = 1; *y = 0; return a; }
  long long x1, y1; uint64_t g = egcd(b, a % b, &x1, &y1);
  *x = y1; *y = x1 - (long long)(a / b) * y1; return g;
}

static uint64_t *R; static long N;
static inline int mode_is_mulhi(int m){ return m == 1; }

/* verify a candidate (A,B) forward from state u at draw d0, over `need` further draws */
static int verify(int mode, uint64_t A, uint64_t B, uint64_t u, long d0, int need,
                  uint64_t M, uint64_t mask){
  for(int j = 0; j < need; j++){
    if(mode == 2) u = (mulC(A, u) + B) % CC;
    else          u = (A * u + B) & mask;   /* mask carries the modulus for modes 3,4 */
    uint64_t pred;
    if(mode == 1) pred = (uint64_t)(((u128)u * CC) >> 64);
    else if(mode == 2) pred = u;
    else pred = u % CC;
    if(pred != R[d0 + 1 + j]) return 0;
  }
  return 1;
}

/* try every k-triple at one starting draw; returns 1 and fills A,B if something verifies */
static int solve_at(int mode, long d, int need, uint64_t *oA, uint64_t *oB, uint64_t *oU){
  uint64_t M, mask; int kmax, bits;
  switch(mode){
    case 3: M = 1ULL << 63; mask = M - 1;  kmax = 2; bits = 63; break;
    case 4: M = 1ULL << 62; mask = M - 1;  kmax = 1; bits = 62; break;
    case 2: M = CC;         mask = ~0ULL;  kmax = 0; bits = 64; break;
    default: M = 0;         mask = ~0ULL;  kmax = 5; bits = 64; break;  /* M=0 = full 2^64 */
  }
  uint64_t cand[3][8]; int nc[3];
  for(int i = 0; i < 3; i++){
    nc[i] = 0;
    if(mode == 1){                       /* r = mulhi(u,C): u lies in a short interval */
      u128 lo = (((u128)R[d+i]) << 64) / CC, hi = (((u128)(R[d+i]+1)) << 64) / CC;
      for(u128 u = lo; u <= hi && nc[i] < 8; u++)
        if((uint64_t)(((u128)(uint64_t)u * CC) >> 64) == R[d+i]) cand[i][nc[i]++] = (uint64_t)u;
    } else if(mode == 2){
      cand[i][nc[i]++] = R[d+i];
    } else {
      for(int k = 0; k <= kmax; k++){
        u128 u = (u128)R[d+i] + (u128)k * CC;
        if(M ? (u < M) : (u < ((u128)1 << 64))) cand[i][nc[i]++] = (uint64_t)u;
      }
    }
  }
  for(int a0 = 0; a0 < nc[0]; a0++)
  for(int a1 = 0; a1 < nc[1]; a1++)
  for(int a2 = 0; a2 < nc[2]; a2++){
    uint64_t u0 = cand[0][a0], u1 = cand[1][a1], u2 = cand[2][a2];
    if(mode == 2){
      uint64_t d1 = (u1 + CC - u0) % CC, d2 = (u2 + CC - u1) % CC;
      long long x, y; uint64_t g = egcd(d1, CC, &x, &y);
      if(g > 64 || d2 % g) continue;
      uint64_t md = CC / g;
      long long xi = x % (long long)md; if(xi < 0) xi += md;
      uint64_t A0 = (uint64_t)(((u128)(d2 / g) * (uint64_t)xi) % md);
      for(uint64_t t = 0; t < g; t++){
        uint64_t A = (A0 + t * md) % CC;
        uint64_t B = (u1 + CC - mulC(A, u0)) % CC;
        if(verify(2, A, B, u1, d + 1, need, M, mask)){ *oA=A; *oB=B; *oU=u0; return 1; }
      }
      continue;
    }
    uint64_t d1 = (u1 - u0) & mask, d2 = (u2 - u1) & mask;
    int e = v2(d1); if(e > 12 || e >= bits) continue;   /* 2^e candidates for A; keep it sane */
    if(v2(d2) < e) continue;                            /* no solution 2-adically */
    uint64_t A0 = ((d2 >> e) * inv_odd(d1 >> e)) & mask; /* A mod 2^(bits-e) */
    uint64_t step = (e == 0) ? 0 : (1ULL << (bits - e));
    for(uint64_t t = 0; t < (1ULL << e); t++){
      uint64_t A = (A0 + t * step) & mask;
      uint64_t B = (u1 - A * u0) & mask;
      if(verify(mode, A, B, u1, d + 1, need, M, mask)){ *oA=A; *oB=B; *oU=u0; return 1; }
      if(!step) break;
    }
  }
  return 0;
}

static void loadrank(const char *fn){
  FILE *f = fopen(fn, "rb"); if(!f){ perror(fn); exit(1); }
  fseek(f, 0, SEEK_END); long sz = ftell(f); fseek(f, 0, SEEK_SET);
  N = sz / 8; R = malloc(sz);
  if((long)fread(R, 8, N, f) != N){ fprintf(stderr,"short read\n"); exit(1); }
  fclose(f);
}

int main(int argc, char **argv){
  const char *mode = argc > 1 ? argv[1] : "selftest";
  int need = 6;                 /* 6 further draws: a wrong (A,B) survives at 2^-370 */
  if(!strcmp(mode, "selftest")){
    printf("selftest: plant an LCG behind the rank stream, recover it with no guessed\n");
    printf("  multiplier; then confirm random ranks and the wrong mode yield nothing.\n\n");
    N = 200; R = malloc(8 * N);
    uint64_t As[5] = {6364136223846793005ULL, 2862933555777941757ULL, 1181783497276652981ULL,
                      6364136223846793005ULL, 6364136223846793005ULL};
    uint64_t Bs[5] = {1442695040888963407ULL, 3037000493ULL, 1ULL,
                      1442695040888963407ULL, 1442695040888963407ULL};
    for(int m = 0; m <= 4; m++){
      uint64_t M = (m==3)?(1ULL<<63):((m==4)?(1ULL<<62):0);
      uint64_t A = As[m], B = Bs[m], u = 0x123456789ABCDEFULL;
      if(m == 2){ A %= CC; B %= CC; u %= CC; }
      if(m >= 3){ u %= M; }
      for(long i = 0; i < N; i++){
        if(m == 2) R[i] = u;
        else if(m == 1) R[i] = (uint64_t)(((u128)u * CC) >> 64);
        else R[i] = u % CC;
        if(m == 2) u = (mulC(A,u) + B) % CC;
        else { u = A*u + B; if(m >= 3) u %= M; }
      }
      uint64_t gA=0, gB=0, gU=0;
      int hit = 0; for(long d = 0; d + 3 + need < N && !hit; d++) hit = solve_at(m, d, need, &gA,&gB,&gU);
      /* Negative controls must NOT be LCG-generated. The obvious "random ranks" —
         an LCG reduced mod C — is mode 0 itself, so it is a second positive, not a
         control. These two streams are bijectively mixed and affine in nothing. */
      uint64_t *sav = R;
      int fp[2] = {0, 0};
      for(int c = 0; c < 2; c++){
        R = malloc(8 * N); uint64_t st = (c ? 0x1234ABCDULL : 0xDEADBEEFCAFEULL) ^ m;
        for(long i = 0; i < N; i++){
          st += 0x9E3779B97F4A7C15ULL;                 /* splitmix64: mixed, not affine */
          uint64_t z = st;
          z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
          z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
          z ^= z >> 31;
          if(c) z = (z ^ (z >> 33)) * 0xFF51AFD7ED558CCDULL;   /* second stream: extra mix */
          R[i] = (mode_is_mulhi(m)) ? (uint64_t)(((u128)z * CC) >> 64) : z % CC;
        }
        for(long d = 0; d + 3 + need < N && !fp[c]; d++) fp[c] = solve_at(m, d, need, &gA,&gB,&gU);
        free(R);
      }
      R = sav;
      /* cross-mode control, where the two models are genuinely incompatible */
      int wm = (m == 0) ? 1 : (m == 1 ? 0 : -1), wr = 0;
      if(wm >= 0) for(long d = 0; d + 3 + need < N && !wr; d++) wr = solve_at(wm, d, need,&gA,&gB,&gU);
      printf("  mode %d  planted recovered=%-3s  mixed stream A=%-3s B=%-3s  %s%s  %s\n",
             m, hit?"yes":"NO", fp[0]?"HIT":"no", fp[1]?"HIT":"no",
             wm >= 0 ? "read as other mode=" : "", wm >= 0 ? (wr?"HIT":"no ") : "",
             (hit && !fp[0] && !fp[1] && !wr) ? "PASS" : "FAIL");
      fflush(stdout);
    }
    return 0;
  }
  const char *fn = argc > 2 ? argv[2] : "rank_colex0.bin";
  int only = argc > 3 ? atoi(argv[3]) : -1;
  loadrank(fn);
  printf("real archive: %s, %ld ranks\n", fn, N);
  printf("  arbitrary (A,B) mod 2^64 — no multiplier assumed, every W absorbed by A=a^W\n");
  printf("  a wrong candidate survives %d further draws with probability 2^-%d\n\n",
         need, (int)(need * 61.6));
  for(int m = 0; m <= 4; m++){
    if(only >= 0 && m != only) continue;
    uint64_t gA=0, gB=0, gU=0; long hits = 0, firstd = -1;
    for(long d = 0; d + 3 + need < N; d++)
      if(solve_at(m, d, need, &gA, &gB, &gU)){ hits++; if(firstd < 0) firstd = d; }
    printf("  mode %d : %ld starting positions solved%s\n", m, hits,
           hits ? "  *** INVESTIGATE ***" : "   (no LCG of this shape generates the ranks)");
    if(hits) printf("        first at draw %ld  A=%llu B=%llu u0=%llu\n", firstd,
                    (unsigned long long)gA, (unsigned long long)gB, (unsigned long long)gU);
    fflush(stdout);
  }
  return 0;
}
