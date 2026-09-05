/* Algebraic recovery of a full MT19937 state from ORDERED keno draws (20 of 80).
   Each Fisher-Yates index j_i = (u*k)>>32 pins the leading bits of the 32-bit output u.
   MT19937 is F2-linear, so every output bit is a known linear form over the 19968
   state bits; the pinned bits give a linear system that we solve by GF(2) elimination.
   Demonstrates: with ~N ordered draws the generator is fully determined and every
   future draw is predicted exactly.                                                */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>
#define NB 19968            /* 624*32 unknown state bits */
#define NW (NB/64)          /* 312 words per row */
#define MATRIX_A 0x9908b0dfU

/* ---------- concrete MT19937 ---------- */
typedef struct{uint32_t mt[624];int mti;}MT;
static void mt_seed(MT*S,uint32_t s){S->mt[0]=s;for(int i=1;i<624;i++)S->mt[i]=1812433253U*(S->mt[i-1]^(S->mt[i-1]>>30))+i;S->mti=624;}
static void mt_twist(MT*S){uint32_t y;int k;
  for(k=0;k<227;k++){y=(S->mt[k]&0x80000000U)|(S->mt[k+1]&0x7fffffffU);S->mt[k]=S->mt[k+397]^(y>>1)^((y&1)?MATRIX_A:0);}
  for(;k<623;k++){y=(S->mt[k]&0x80000000U)|(S->mt[k+1]&0x7fffffffU);S->mt[k]=S->mt[k-227]^(y>>1)^((y&1)?MATRIX_A:0);}
  y=(S->mt[623]&0x80000000U)|(S->mt[0]&0x7fffffffU);S->mt[623]=S->mt[396]^(y>>1)^((y&1)?MATRIX_A:0);S->mti=0;}
static uint32_t mt_next(MT*S){ if(S->mti>=624)mt_twist(S);
  uint32_t y=S->mt[S->mti++];y^=y>>11;y^=(y<<7)&0x9d2c5680U;y^=(y<<15)&0xefc60000U;y^=y>>18;return y;}

/* ---------- symbolic state: 624 words x 32 bits, each a row of NW uint64 ---------- */
static uint64_t *SS;                       /* SS[(i*32+b)*NW + w] */
#define SB(i,b) (SS+(((size_t)(i)*32+(b))*NW))
static uint64_t *TMP;
static inline void rxor(uint64_t*d,const uint64_t*s){for(int w=0;w<NW;w++)d[w]^=s[w];}
static inline void rcpy(uint64_t*d,const uint64_t*s){memcpy(d,s,NW*8);}
static inline void rzero(uint64_t*d){memset(d,0,NW*8);}

static void sym_twist(void){
  static uint64_t nw_[32][NW];
  for(int k=0;k<624;k++){
    int k1=(k+1)%624, kf=(k+397)%624;
    /* y = (mt[k]&0x80000000)|(mt[k1]&0x7fffffff) : bit31 from k, bits30..0 from k1 */
    /* new mt[k] = mt[kf] ^ (y>>1) ^ (y&1 ? A : 0)  ; y&1 = bit0 of mt[k1] */
    for(int b=0;b<32;b++){
      rcpy(nw_[b], SB(kf,b));
      /* (y>>1) bit b  = y bit b+1  (b<=30), 0 for b=31 */
      if(b<=30){ int yb=b+1; const uint64_t*src = (yb==31)? SB(k,31) : SB(k1,yb); rxor(nw_[b],src); }
      if((MATRIX_A>>b)&1) rxor(nw_[b], SB(k1,0));
    }
    for(int b=0;b<32;b++) rcpy(SB(k,b), nw_[b]);
  }
}
/* tempering, symbolic: returns rows for the 32 output bits of state word idx */
static uint64_t TEMPO[32][NW];
static void sym_temper(int idx){
  static uint64_t y[32][NW], t[32][NW];
  for(int b=0;b<32;b++) rcpy(y[b], SB(idx,b));
  for(int b=0;b<32;b++){ rcpy(t[b],y[b]); if(b+11<32) rxor(t[b], y[b+11]); }      /* y ^= y>>11 */
  for(int b=0;b<32;b++) rcpy(y[b],t[b]);
  for(int b=0;b<32;b++){ rcpy(t[b],y[b]); if(b-7>=0 && ((0x9d2c5680U>>b)&1)) rxor(t[b], y[b-7]); } /* y ^= (y<<7)&M */
  for(int b=0;b<32;b++) rcpy(y[b],t[b]);
  for(int b=0;b<32;b++){ rcpy(t[b],y[b]); if(b-15>=0 && ((0xefc60000U>>b)&1)) rxor(t[b], y[b-15]); }
  for(int b=0;b<32;b++) rcpy(y[b],t[b]);
  for(int b=0;b<32;b++){ rcpy(t[b],y[b]); if(b+18<32) rxor(t[b], y[b+18]); }
  for(int b=0;b<32;b++) rcpy(TEMPO[b], t[b]);
}
/* ---------- GF(2) echelon solver ---------- */
static uint64_t **PIV; static uint8_t *PRHS; static int NPIV=0;
static int CONTRA=0;
static int insert_eq(uint64_t*row, int rhs){
  for(int w=0;w<NW;w++){
    while(row[w]){
      int b=__builtin_ctzll(row[w]); int p=w*64+b;
      if(PIV[p]){ for(int q=w;q<NW;q++) row[q]^=PIV[p][q]; rhs^=PRHS[p]; }
      else { PIV[p]=malloc(NW*8); memcpy(PIV[p],row,NW*8); PRHS[p]=rhs; NPIV++; return 1; }
    }
  }
  if(rhs) CONTRA++;                 /* 0 = rhs(1)  -> hypothesis refuted */
  return 0;
}
static int POS0=624;
int main(int argc,char**argv){
  int DRAWS = argc>1?atoi(argv[1]):400;
  uint32_t SEED = argc>2?(uint32_t)strtoul(argv[2],0,0):0xC0FFEE42U;
  int SKIP = argc>3?atoi(argv[3]):0;      /* outputs consumed before observation window */
  int SCAN = argc>4?atoi(argv[4]):0;      /* 1 = scan the 624 unknown buffer alignments */
  printf("MT19937 keno break: %d ordered draws, hidden seed 0x%08X, skip %d\n",DRAWS,SEED,SKIP);
  MT G; mt_seed(&G,SEED); for(int i=0;i<SKIP;i++) mt_next(&G);
  if(!SCAN){ while(G.mti!=624 && G.mti!=0) mt_next(&G); }   /* aligned demo */
  int TRUEPOS = (G.mti>=624)?624:G.mti;
  int T = DRAWS*20;
  uint8_t *jidx = malloc(T);
  int (*draws)[20] = malloc(sizeof(int)*20*(DRAWS+50));
  for(int d=0;d<DRAWS+50;d++){
    uint8_t a[81]; for(int i=0;i<80;i++)a[i]=i+1;
    for(int i=0;i<20;i++){uint32_t u=mt_next(&G); uint32_t j=i+(uint32_t)(((uint64_t)u*(80-i))>>32);
      if(d<DRAWS) jidx[d*20+i]=(uint8_t)(j-i);
      uint8_t t=a[i];a[i]=a[j];a[j]=t; draws[d][i]=a[i];}
  }
  printf("  observation = %d outputs; future draws kept hidden for the check\n",T);
  if(SCAN) printf("  true buffer index (hidden from the solver) = %d\n",TRUEPOS);
  clock_t c0=clock();
  SS=calloc((size_t)624*32*NW,8); TMP=malloc(NW*8);
  PIV=calloc(NB,sizeof(uint64_t*)); PRHS=calloc(NB,1);
  int LOP = SCAN?0:624, HIP=625;
  for(POS0=LOP; POS0<HIP; POS0++){
  if(SCAN&&POS0%100==0){printf("   scanning alignment %d ...\n",POS0);fflush(stdout);}
  memset(SS,0,(size_t)624*32*NW*8);
  for(int i=0;i<624;i++)for(int b=0;b<32;b++){int p=i*32+b; SB(i,b)[p/64]|=1ULL<<(p%64);}
  int eqs=0, known_bits=0;
  int pos=POS0;                   /* hypothesis: buffer index at the first observed output */
  for(int t=0;t<T && NPIV<NB && CONTRA<3; t++){
    if(pos>=624){ sym_twist(); pos=0; }
    sym_temper(pos);
    int i=t%20, k=80-i; uint32_t j=jidx[t];
    /* u in [ ceil(j*2^32/k), ceil((j+1)*2^32/k) ) : take the common leading bits */
    uint64_t lo=((uint64_t)j<<32)/k + ((((uint64_t)j<<32)%k)?1:0);
    uint64_t hi=(((uint64_t)j+1)<<32)/k + (((((uint64_t)j+1)<<32)%k)?1:0);
    hi-=1;                                   /* inclusive upper bound */
    uint32_t x=(uint32_t)(lo^hi); int nb= x? 32-(32-__builtin_clz(x)) : 32;
    for(int b=31;b>=32-nb;b--){ int v=(lo>>b)&1;
      uint64_t*r=TMP; memcpy(r,TEMPO[b],NW*8);
      insert_eq(r,v); eqs++; known_bits++; }
    pos++;
  }
  if(!SCAN) printf("  linear equations used: %d (%.2f known bits per output)  rank=%d/%d  [%.1fs]\n",
     eqs,(double)known_bits/T,NPIV,NB,(double)(clock()-c0)/CLOCKS_PER_SEC);
  if(SCAN && CONTRA>0){ for(int p=0;p<NB;p++) if(PIV[p]){free(PIV[p]);PIV[p]=NULL;} NPIV=0;CONTRA=0; continue; }
  /* back substitution: free vars = 0 */
  uint64_t *x=calloc(NW,8);
  for(int p=NB-1;p>=0;p--){ if(!PIV[p])continue;
    uint64_t acc=0; for(int w=0;w<NW;w++) acc^=PIV[p][w]&x[w];
    int par=__builtin_parityll(acc);
    /* remove own bit contribution (x[p] currently 0) */
    if(PRHS[p]^par) x[p/64]|=1ULL<<(p%64);
  }
  MT R; for(int i=0;i<624;i++){uint32_t v=0;for(int b=0;b<32;b++) if((x[(i*32+b)/64]>>((i*32+b)%64))&1) v|=1u<<b; R.mt[i]=v;} R.mti=624;
  /* verify: replay observed draws, then PREDICT the hidden ones */
  int okobs=0,okfut=0;
  for(int d=0;d<DRAWS+50;d++){
    uint8_t a[81]; for(int i=0;i<80;i++)a[i]=i+1; int match=1;
    for(int i=0;i<20;i++){uint32_t u=mt_next(&R); uint32_t j=i+(uint32_t)(((uint64_t)u*(80-i))>>32);
      uint8_t tt=a[i];a[i]=a[j];a[j]=tt; if(a[i]!=draws[d][i])match=0;}
    if(d<DRAWS) okobs+=match; else okfut+=match;
  }
  if(okfut==50){
    printf("  alignment %d -> rank %d, contradictions %d\n",POS0,NPIV,CONTRA);
    printf("  RESULT: observed %d/%d reproduced ; FUTURE %d/50 predicted  [%.1fs]\n",okobs,DRAWS,okfut,(double)(clock()-c0)/CLOCKS_PER_SEC);
    printf("  *** FULL BREAK: every future draw predicted exactly ***\n"); return 0; }
  if(!SCAN){ printf("  rank %d/%d contradictions %d -> observed %d/%d future %d/50 : incomplete\n",
      NPIV,NB,CONTRA,okobs,DRAWS,okfut); return 0; }
  for(int p=0;p<NB;p++) if(PIV[p]){free(PIV[p]);PIV[p]=NULL;}
  NPIV=0;CONTRA=0;free(x);
  }
  printf("  no consistent alignment found\n");
  return 0;
}
