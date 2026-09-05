/* channel_break — MT19937 state recovery from the REAL archive, no draw order needed.
 *
 * The published feed carries two extra outputs of the same generator:
 *   bonus  one of the 20 balls. If it is the FIRST ball drawn then, because
 *          Fisher-Yates starts from the identity array, bonus-1 IS the first index
 *          j0 = (u*80)>>32, so it pins 5.20 leading bits of that 32-bit output.
 *          If instead it is an extra pick sorted[(u*20)>>32], it pins 3.21 bits.
 *   boost  x1/x2/x3/x4/x5/x10 at 51.2/23.8/15.0/5.0/2.5/2.5 % (reconstructed from
 *          the archive, chi2 = 0.55 on df 5). Those are thresholds on u/2^32, so the
 *          value pins 1.15 leading bits on average.
 *
 * MT19937 is F2-linear, so each pinned bit is a linear form over the 19968 state
 * bits. 19937 bits at 1.2-6.4 bits per draw needs 4000-23000 draws; the archive
 * holds 70560. The unknown is the buffer right after a twist, so where the
 * observation window starts inside that buffer is scanned (624 hypotheses); a wrong
 * one leaves the over-determined system inconsistent and is dropped at once.
 *
 * The symbolic propagation does not depend on the alignment — only the indexing
 * does — so the leading bit-forms are computed once and every alignment reuses them.
 *
 *   ./channel_break <mode> <W> <ndraws> <threads> [first] [p_lo] [p_hi] [bin]
 *      mode 0  bonus = first ball drawn                 5.20 bits/draw
 *      mode 1  bonus = sorted[(u*20)>>32] at r=0        3.21 bits/draw
 *      mode 2  mode 1 + boost at r=20                   4.36 bits/draw
 *      mode 3  boost at r=20 only                       1.15 bits/draw
 *      mode 4  mode 0 + boost at r=20                   6.35 bits/draw
 *      mode 5  bonus rank via u %% 20 (low bits)          2.00 bits/draw
 *      mode 6  bonus = first ball via u %% 80 (low bits)  4.00 bits/draw
 *      mode 7  bonus = first ball, Floyd sampler (k=61)   4.75 bits/draw
 *      mode 8  boost at r=0 (its own generator stream)    1.15 bits/draw
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <pthread.h>
#include <time.h>
#define NB 19968
#define NW (NB/64)
#define TOPB 10   /* forms kept per output: 0..5 = bits 31..26, 6..9 = bits 3..0.
                     The low four cover the modulo mappings: 80 = 16*5 and 20 = 4*5,
                     so u % 80 fixes u mod 16 and u % 20 fixes u mod 4. */
#define MATRIX_A 0x9908b0dfU

static uint32_t N,*IDS,*TS; static uint8_t *NUMS,*BOOST,*BONUS;
static uint64_t *FORMS;            /* FORMS[(n*TOPB+b)*NW ..] = form of bit 31-b of output n */
static long NFORM;

static uint64_t *SS;
#define SB(i,b) (SS + (((size_t)(i)*32+(b))*NW))
static inline void rxor(uint64_t*d,const uint64_t*s){for(int w=0;w<NW;w++)d[w]^=s[w];}
static inline void rcpy(uint64_t*d,const uint64_t*s){memcpy(d,s,NW*8);}
static void sym_twist(void){
  static uint64_t nw_[32][NW];
  for(int k=0;k<624;k++){int k1=(k+1)%624,kf=(k+397)%624;
    for(int b=0;b<32;b++){ rcpy(nw_[b],SB(kf,b));
      if(b<=30){int yb=b+1; const uint64_t*src=(yb==31)?SB(k,31):SB(k1,yb); rxor(nw_[b],src);}
      if((MATRIX_A>>b)&1) rxor(nw_[b],SB(k1,0)); }
    for(int b=0;b<32;b++) rcpy(SB(k,b),nw_[b]); }
}
static void sym_temper_top(int idx,long n){
  static uint64_t y[32][NW],t[32][NW];
  for(int b=0;b<32;b++) rcpy(y[b],SB(idx,b));
  for(int b=0;b<32;b++){rcpy(t[b],y[b]); if(b+11<32) rxor(t[b],y[b+11]);}
  for(int b=0;b<32;b++) rcpy(y[b],t[b]);
  for(int b=0;b<32;b++){rcpy(t[b],y[b]); if(b-7>=0&&((0x9d2c5680U>>b)&1)) rxor(t[b],y[b-7]);}
  for(int b=0;b<32;b++) rcpy(y[b],t[b]);
  for(int b=0;b<32;b++){rcpy(t[b],y[b]); if(b-15>=0&&((0xefc60000U>>b)&1)) rxor(t[b],y[b-15]);}
  for(int b=0;b<32;b++) rcpy(y[b],t[b]);
  for(int b=0;b<32;b++){rcpy(t[b],y[b]); if(b+18<32) rxor(t[b],y[b+18]);}
  for(int b=0;b<6;b++) rcpy(FORMS+((size_t)n*TOPB+b)*NW, t[31-b]);
  for(int b=0;b<4;b++) rcpy(FORMS+((size_t)n*TOPB+6+b)*NW, t[b]);
}
/* ---------------- per-thread elimination ---------------- */
typedef struct{uint64_t **PIV; uint8_t *PRHS; int npiv, contra;} BASIS;
static void basis_reset(BASIS*B){ for(int p=0;p<NB;p++) if(B->PIV[p]){free(B->PIV[p]);B->PIV[p]=NULL;}
  B->npiv=0;B->contra=0; }
static void insert_eq(BASIS*B,uint64_t*row,int rhs){
  for(int w=0;w<NW;w++){
    while(row[w]){ int p=w*64+__builtin_ctzll(row[w]);
      if(B->PIV[p]){ for(int q=w;q<NW;q++) row[q]^=B->PIV[p][q]; rhs^=B->PRHS[p]; }
      else { B->PIV[p]=malloc(NW*8); memcpy(B->PIV[p],row,NW*8); B->PRHS[p]=rhs; B->npiv++; return; } } }
  if(rhs) B->contra++;
}
static int lead_bits(uint64_t lo,uint64_t hi,int*bp,int*bv){
  uint32_t x=(uint32_t)(lo^hi); int nb = x ? __builtin_clz(x) : 32; int n=0;
  if(nb>6) nb=6;
  for(int b=31;b>=32-nb;b--){bp[n]=31-b;bv[n]=(lo>>b)&1;n++;}   /* bp = index into TOPB */
  return n;
}
static void range_of_index(uint32_t j,uint32_t k,uint64_t*lo,uint64_t*hi){
  *lo=((uint64_t)j<<32)/k + ((((uint64_t)j<<32)%k)?1:0);
  *hi=(((uint64_t)j+1)<<32)/k + (((((uint64_t)j+1)<<32)%k)?1:0) - 1;
}
static const double BCUM[6]={0.512,0.750,0.900,0.950,0.975,1.0};
static const int BVAL[6]={1,2,3,4,5,10};
static void range_of_boost(int v,uint64_t*lo,uint64_t*hi){
  int i=0; for(;i<6;i++) if(BVAL[i]==v) break; if(i==6)i=0;
  *lo = i? (uint64_t)(BCUM[i-1]*4294967296.0) : 0ULL;
  *hi = i==5 ? 0xFFFFFFFFULL : (uint64_t)(BCUM[i]*4294967296.0)-1ULL;
}
/* low a bits of u, from u = j (mod k) with a = v2(k) */
static int low_bits(uint32_t j,uint32_t k,int*bp,int*bv){
  int a=__builtin_ctz(k); if(a>4)a=4; uint32_t r=j&((1u<<a)-1);
  for(int b=0;b<a;b++){bp[b]=6+b;bv[b]=(r>>b)&1;}
  return a;
}
static int bonus_rank(long d,int first){
  for(int q=0;q<20;q++) if(NUMS[(size_t)(first+d)*20+q]==BONUS[first+d]) return q;
  return -1;
}
/* fills the constraint list for a draw-relative role; returns #bits */
static int role_bits(int mode,int r,long d,int first,int*bp,int*bv){
  uint64_t lo,hi;
  if(r==0 && mode==5){ int rk=bonus_rank(d,first); if(rk<0)return 0;
    return low_bits((uint32_t)rk,20,bp,bv); }                     /* bonus via u % 20 */
  if(r==0 && mode==6) return low_bits((uint32_t)(BONUS[first+d]-1),80,bp,bv); /* first ball via u % 80 */
  if(r==0 && mode==7){ range_of_index((uint32_t)(BONUS[first+d]-1),61,&lo,&hi);
    return lead_bits(lo,hi,bp,bv); }                              /* Floyd: first value has range 61 */
  if(r==0 && (mode==0||mode==4)){ range_of_index((uint32_t)(BONUS[first+d]-1),80,&lo,&hi); }
  else if(r==0 && (mode==1||mode==2)){ int rk=bonus_rank(d,first);
    if(rk<0) return 0; range_of_index((uint32_t)rk,20,&lo,&hi); }
  else if(r==20 && (mode==2||mode==3||mode==4)){ range_of_boost(BOOST[first+d],&lo,&hi); }
  else if(r==0 && mode==8){ range_of_boost(BOOST[first+d],&lo,&hi); }  /* boost from its own stream */
  else return 0;
  return lead_bits(lo,hi,bp,bv);
}
static int VERBOSE=0;
typedef struct{int mode,W;long D;int first,p_lo,p_hi;BASIS*B;int hit,best_rank,best_p;}JOB;
static pthread_mutex_t MU=PTHREAD_MUTEX_INITIALIZER;
static void*worker(void*a){
  JOB*J=(JOB*)a; J->hit=-1; J->best_rank=0; uint64_t row[NW]; int bp[8],bv[8];
  for(int p=J->p_lo;p<J->p_hi;p++){
    basis_reset(J->B); long neq=0;
    for(long k=0;k<J->D*J->W && J->B->contra<3;k++){
      int r=(int)(k%J->W); long d=k/J->W;
      int nb=role_bits(J->mode,r,d,J->first,bp,bv);
      for(int q=0;q<nb;q++){
        memcpy(row, FORMS+((size_t)(p+k)*TOPB+bp[q])*NW, NW*8);
        insert_eq(J->B,row,bv[q]); neq++; } }
    if(VERBOSE){pthread_mutex_lock(&MU);
      fprintf(stderr,"    p=%3d eqs=%ld rank=%d contra=%d\n",p,neq,J->B->npiv,J->B->contra);
      pthread_mutex_unlock(&MU);}
    if(J->B->npiv>J->best_rank){J->best_rank=J->B->npiv;J->best_p=p;}
    if(J->B->contra<3 && J->B->npiv>=19937){ pthread_mutex_lock(&MU);
      fprintf(stderr,"  *** CONSISTENT: mode=%d W=%d alignment=%d rank=%d ***\n",J->mode,J->W,p,J->B->npiv);
      pthread_mutex_unlock(&MU); J->hit=p; return 0; } }
  return 0;
}
int main(int argc,char**argv){
  const char*BIN=argc>8?argv[8]:"draws.bin";
  FILE*f=fopen(BIN,"rb"); if(!f||fread(&N,4,1,f)!=1){perror(BIN);return 1;}
  IDS=malloc(4*N);TS=malloc(4*N);
  uint64_t*LO=malloc(8*N),*HI=malloc(8*N);
  NUMS=malloc(20*N);BOOST=malloc(N);BONUS=malloc(N);
  if(fread(IDS,4,N,f)!=N||fread(TS,4,N,f)!=N||fread(LO,8,N,f)!=N||fread(HI,8,N,f)!=N||
     fread(NUMS,20,N,f)!=N||fread(BOOST,1,N,f)!=N||fread(BONUS,1,N,f)!=N){fprintf(stderr,"short read\n");return 1;}
  fclose(f);
  int mode=argc>1?atoi(argv[1]):0, W=argc>2?atoi(argv[2]):22;
  long D=argc>3?atol(argv[3]):5500; int T=argc>4?atoi(argv[4]):4;
  int first=argc>5?atoi(argv[5]):0, PLO=argc>6?atoi(argv[6]):0, PHI=argc>7?atoi(argv[7]):624;
  VERBOSE = (PHI-PLO)<=12;
  const double BITS[9]={5.20,3.21,4.36,1.15,6.35,2.00,4.00,4.75,1.15};
  NFORM=D*W+PHI+2;
  double gb=(double)NFORM*TOPB*NW*8/1e9;
  printf("channel_break %s: mode=%d W=%d draws=%ld (%.0f bits for 19937 needed) threads=%d\n",
     BIN,mode,W,D,BITS[(mode>=0&&mode<9)?mode:0]*D,T);
  printf("  precomputing %ld leading-bit forms  (%.2f GB)\n",NFORM,gb); fflush(stdout);
  SS=malloc((size_t)624*32*NW*8); FORMS=malloc((size_t)NFORM*TOPB*NW*8);
  if(!SS||!FORMS){fprintf(stderr,"out of memory (%.2f GB needed)\n",gb);return 1;}
  memset(SS,0,(size_t)624*32*NW*8);
  for(int i=0;i<624;i++)for(int b=0;b<32;b++){int p=i*32+b; SB(i,b)[p/64]|=1ULL<<(p%64);}
  time_t w0=time(0); int pos=624;
  for(long n=0;n<NFORM;n++){ if(pos>=624){sym_twist();pos=0;} sym_temper_top(pos,n); pos++; }
  printf("  forms ready in %ld s; scanning alignments [%d,%d)\n",(long)(time(0)-w0),PLO,PHI); fflush(stdout);
  pthread_t th[16]; JOB jb[16]; BASIS*bs=calloc(T,sizeof(BASIS));
  for(int i=0;i<T;i++){bs[i].PIV=calloc(NB,sizeof(uint64_t*)); bs[i].PRHS=calloc(NB,1);}
  int span=(PHI-PLO+T-1)/T; time_t s0=time(0);
  for(int i=0;i<T;i++){ jb[i]=(JOB){mode,W,D,first,PLO+i*span,(PLO+(i+1)*span<PHI)?PLO+(i+1)*span:PHI,&bs[i],-1,0,0};
    pthread_create(&th[i],0,worker,&jb[i]); }
  int hit=-1,best=0,bp2=0;
  for(int i=0;i<T;i++){pthread_join(th[i],0); if(jb[i].hit>=0)hit=jb[i].hit;
    if(jb[i].best_rank>best){best=jb[i].best_rank;bp2=jb[i].best_p;} }
  printf("  scan done in %ld s\n",(long)(time(0)-s0));
  if(hit>=0) printf("  *** BREAK: alignment %d gives a consistent 19937-bit system ***\n",hit);
  else printf("  no consistent alignment (best rank %d at alignment %d, 19937 needed)\n"
              "  -> under this layout the generator is not MT19937\n",best,bp2);
  return hit>=0?0:2;
}
