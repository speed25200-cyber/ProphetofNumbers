/* lcg_lll — lattice attack on a 64-bit LCG with high-half output, run against the
 * real archive. The Python version proved the attack works (it recovers a synthetic
 * LCG64 at K = 13 and K = 20, better than the worst-case LLL bound predicts) but its
 * exact-fraction LLL is far too slow for a sweep. This is the same attack with the
 * basis in __int128 and the Gram-Schmidt in long double: microseconds per reduction.
 *
 * Setup. bonus = first ball drawn means bonus-1 = (u*80)>>32 with u = s>>32, so each
 * state s_d is pinned to an interval of width 2^57.7 out of 2^64 — 6.32 bits. With
 * s_{d+1} = A s_d + C (mod 2^64), differencing kills the unknown increment:
 * D_d = s_{d+1} - s_d satisfies D_{d+1} = A D_d. Centring gives e_d = A^d e_0 + b_d
 * (mod 2^64) with every |e_d| <= 2^58.7, a Hidden Number Problem that LLL solves.
 * The multiplier is guessed from the standard list and W is swept.
 *
 *   ./lcg_lll selftest        positive and negative controls on synthetic data
 *   ./lcg_lll real [K] [maxW] sweep the real archive
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#define MAXN 64
typedef __int128 i128;
typedef unsigned __int128 u128;
static const u128 MOD = (u128)1 << 64;

static int NDIM;
static i128 Bm[MAXN][MAXN];
static long double mu[MAXN][MAXN], Bst[MAXN];

static long double dotf(const i128*a, const i128*b){
  long double s=0; for(int i=0;i<NDIM;i++) s += (long double)a[i]*(long double)b[i]; return s; }

static void gso(void){
  static long double v[MAXN][MAXN];
  for(int i=0;i<NDIM;i++){
    for(int k=0;k<NDIM;k++) v[i][k]=(long double)Bm[i][k];
    for(int j=0;j<i;j++){
      long double d=Bst[j]; long double num=0;
      for(int k=0;k<NDIM;k++) num += (long double)Bm[i][k]*v[j][k];
      mu[i][j] = d>0 ? num/d : 0.0L;
      for(int k=0;k<NDIM;k++) v[i][k] -= mu[i][j]*v[j][k];
    }
    long double s=0; for(int k=0;k<NDIM;k++) s += v[i][k]*v[i][k];
    Bst[i]=s;
  }
}
static void lll(void){
  gso();
  int k=1, guard=0;
  while(k<NDIM && guard++ < 200000){
    for(int j=k-1;j>=0;j--){
      long double q=mu[k][j];
      long double r = (q>=0)? floorl(q+0.5L) : -floorl(-q+0.5L);
      if(r!=0){ i128 ri=(i128)r;
        for(int t=0;t<NDIM;t++) Bm[k][t] -= ri*Bm[j][t];
        gso(); }
    }
    if(Bst[k] >= (0.99L - mu[k][k-1]*mu[k][k-1])*Bst[k-1]) k++;
    else { for(int t=0;t<NDIM;t++){ i128 tmp=Bm[k][t]; Bm[k][t]=Bm[k-1][t]; Bm[k-1][t]=tmp; }
           gso(); k = (k-1>1)?k-1:1; }
  }
}
static uint64_t powmod(uint64_t a,int e){ uint64_t r=1,b=a; while(e){ if(e&1)r*=b; b*=b; e>>=1; } return r; }

/* returns 1 if a vector consistent with every |e_d| <= bound is found */
static int hnp(uint64_t A, const uint64_t*cen, int K, u128 bound){
  int n=K+1; NDIM=n;
  static uint64_t Dc[MAXN], beta[MAXN];
  for(int d=0; d<K; d++) Dc[d] = cen[d+1]-cen[d];            /* mod 2^64 by wraparound */
  for(int d=1; d<K; d++) beta[d-1] = powmod(A,d)*Dc[0] - Dc[d];
  memset(Bm,0,sizeof Bm);
  for(int i=0;i<K-1;i++) Bm[i][i] = (i128)MOD;
  for(int d=1; d<K; d++) Bm[K-1][d-1] = (i128)powmod(A,d);
  Bm[K-1][K-1] = 1;
  for(int d=0; d<K-1; d++) Bm[K][d] = (i128)beta[d];
  Bm[K][K] = (i128)bound;
  lll();
  for(int i=0;i<n;i++){
    i128 last=Bm[i][K];
    if(last!=(i128)bound && last!=-(i128)bound) continue;
    int sgn = (last<0)?1:-1; int ok=1;
    for(int d=0; d<K-1 && ok; d++){ i128 e=sgn*Bm[i][d]; if(e<0)e=-e; if((u128)e>bound) ok=0; }
    i128 e0=sgn*Bm[i][K-1]; if(e0<0)e0=-e0;
    if(ok && (u128)e0<=bound) return 1;
  }
  return 0;
}
static void interval(uint32_t j,uint32_t k,uint64_t*lo,uint64_t*hi){
  u128 a=((u128)j<<32), b=((u128)(j+1)<<32);
  uint64_t l=(uint64_t)(a/k) + ((a%k)?1:0), h=(uint64_t)(b/k) + ((b%k)?1:0);
  *lo=(uint64_t)l<<32; *hi=((uint64_t)h<<32);
}
static uint64_t centre_from_bonus(int bonus){
  uint64_t lo,hi; interval((uint32_t)(bonus-1),80,&lo,&hi); return lo + ((hi-lo)>>1);
}
static const uint64_t MULT[]={6364136223846793005ULL,2862933555777941757ULL,3202034522624059733ULL,
  3935559000370003845ULL,1181783497276652981ULL,0xda942042e4dd58b5ULL,25214903917ULL,
  1103515245ULL,214013ULL,1664525ULL,6364136223846793005ULL,0x27BB2EE687B0B0FDULL};
static const char*MNAME[]={"MMIX / PCG","L'Ecuyer a","L'Ecuyer b","L'Ecuyer c","ranqd1-64",
  "Lehmer64","drand48","glibc LCG","MSVC","Numerical Recipes","PCG-XSL-RR","Knuth 64"};
#define NMULT 12

static uint32_t N,*IDS,*TS; static uint8_t *NUMS,*BOOST,*BONUS;
static void loadbin(void){
  FILE*f=fopen("draws.bin","rb"); if(!f||fread(&N,4,1,f)!=1){perror("draws.bin");exit(1);}
  IDS=malloc(4*N);TS=malloc(4*N); uint64_t*LO=malloc(8*N),*HI=malloc(8*N);
  NUMS=malloc(20*N);BOOST=malloc(N);BONUS=malloc(N);
  if(fread(IDS,4,N,f)!=N||fread(TS,4,N,f)!=N||fread(LO,8,N,f)!=N||fread(HI,8,N,f)!=N||
     fread(NUMS,20,N,f)!=N||fread(BOOST,1,N,f)!=N||fread(BONUS,1,N,f)!=N){fprintf(stderr,"short read\n");exit(1);}
  fclose(f);
}
int main(int argc,char**argv){
  const char*mode = argc>1?argv[1]:"selftest";
  uint64_t lo,hi; interval(0,80,&lo,&hi); u128 bound=(u128)(hi-lo);
  if(!strcmp(mode,"selftest")){
    uint64_t a=6364136223846793005ULL, c=1442695040888963407ULL; int W=21;
    printf("selftest: synthetic LCG64 (MMIX), W=%d, output s>>32, bonus = first ball\n",W);
    printf("  positive AND negative controls must both pass before any real run\n\n");
    for(int K=12;K<=24;K+=4){
      static uint64_t cen[MAXN]; uint64_t s=0xC0FFEE1234567890ULL;
      for(int d=0;d<=K;d++){ uint32_t u=(uint32_t)(s>>32); uint32_t j=(uint32_t)(((uint64_t)u*80)>>32);
        uint64_t l,h; interval(j,80,&l,&h); cen[d]=l+((h-l)>>1);
        for(int t=0;t<W;t++) s=a*s+c; }
      int good=hnp(powmod(a,W),cen,K,bound);
      int badW=hnp(powmod(a,W+1),cen,K,bound);
      int badA=hnp(powmod(2862933555777941757ULL,W),cen,K,bound);
      static uint64_t rnd[MAXN]; uint64_t z=1;
      for(int d=0;d<=K;d++){ z=z*6364136223846793005ULL+1442695040888963407ULL; rnd[d]=z; }
      int badD=hnp(powmod(a,W),rnd,K,bound);
      printf("  K=%2d  correct a,W: %-10s | wrong W: %-9s | wrong a: %-9s | random data: %s\n",
        K, good?"RECOVERED":"missed", badW?"false hit":"rejected",
        badA?"false hit":"rejected", badD?"false hit":"rejected");
    }
    return 0;
  }
  loadbin();
  int K=argc>2?atoi(argv[2]):20, maxW=argc>3?atoi(argv[3]):48;
  int starts[]={0,5000,20000,50000,70000-40};
  printf("real archive: %u draws, K=%d constraints, W swept 1..%d, %d start offsets\n",N,K,maxW,5);
  printf("  bonus = first ball drawn, LCG64 output s>>32, increment differenced away\n\n");
  int total=0;
  for(int m=0;m<NMULT;m++){
    int found=0;
    for(int W=1;W<=maxW;W++){
      uint64_t A=powmod(MULT[m],W);
      for(int si=0;si<5;si++){ int st=starts[si];
        static uint64_t cen[MAXN];
        for(int d=0;d<=K;d++) cen[d]=centre_from_bonus(BONUS[st+d]);
        if(hnp(A,cen,K,bound)){ printf("  !!! HIT %s W=%d start=%d\n",MNAME[m],W,st); found++; }
      }
    }
    printf("  %-20s a=%-22llu %s\n",MNAME[m],(unsigned long long)MULT[m],
           found?"SEE HITS ABOVE":"no fit at any W");
    total+=found;
  }
  printf("\n  total hits: %d  ->  %s\n",total,
     total?"INVESTIGATE":"no 64-bit LCG with a standard multiplier fits the archive");
  return 0;
}
