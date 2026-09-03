/* lin_break — same side-channel algebra as channel_break, for the SMALL F2-linear
 * generators: xorshift64, xorshift96, xorshift128 (Marsaglia), and Galois LFSRs of
 * 48..1024 bits. The 2^32 sweep in seedhunt covers every state of 32 bits or fewer;
 * channel_break covers MT19937's 19937. This closes the range in between.
 *
 * Same idea: bonus and boost each pin leading bits of a 32-bit output, every output
 * bit is a XOR of state bits, so B unknowns fall out of GF(2) elimination. With
 * 5.2 bits per draw a 128-bit state needs ~34 draws, so this is nearly free.
 *
 *   ./lin_break <gen> <mode> <W> <ndraws> [first] [bin]
 *      gen   0 xorshift64(out=hi32)  1 xorshift64(out=lo32)  2 xorshift128(Marsaglia)
 *            3 xorshift96            4 lfsr64  5 lfsr128  6 lfsr256  7 lfsr512
 *      mode  0 bonus = first ball    1 bonus = sorted[(u*20)>>32]    3 boost only
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#define MAXB 1024
#define MAXW (MAXB/64)
static int B, NWB;
static uint64_t SYM[MAXB][MAXW];          /* SYM[i] = linear form of state bit i */
static uint64_t OUT[32][MAXW];            /* forms of the 32 output bits */
static uint32_t N,*IDS,*TS; static uint8_t *NUMS,*BOOST,*BONUS;

static inline void rx(uint64_t*d,const uint64_t*s){for(int w=0;w<NWB;w++)d[w]^=s[w];}
static inline void rc(uint64_t*d,const uint64_t*s){memcpy(d,s,NWB*8);}
static uint64_t TMPS[MAXB][MAXW];

/* x ^= x << k  inside a word of `width` bits based at `base` */
static void sh_left(int base,int width,int k){
  for(int i=0;i<width;i++) rc(TMPS[i],SYM[base+i]);
  for(int i=width-1;i>=k;i--) rx(TMPS[i],SYM[base+i-k]);
  for(int i=0;i<width;i++) rc(SYM[base+i],TMPS[i]);
}
static void sh_right(int base,int width,int k){
  for(int i=0;i<width;i++) rc(TMPS[i],SYM[base+i]);
  for(int i=0;i+k<width;i++) rx(TMPS[i],SYM[base+i+k]);
  for(int i=0;i<width;i++) rc(SYM[base+i],TMPS[i]);
}
static const int LT64[]={64,63,61,60}, LT128[]={128,127,126,121},
                 LT256[]={256,254,251,246}, LT512[]={512,510,507,504};
static void lfsr_step(const int*taps){
  uint64_t fb[MAXW]; rc(fb,SYM[B-1]);
  for(int i=B-1;i>0;i--) rc(SYM[i],SYM[i-1]);
  memset(SYM[0],0,NWB*8);
  rx(SYM[0],fb);
  for(int t=1;t<4;t++){ int p=B-taps[t]; if(p>0&&p<B) rx(SYM[p],fb); }
}
static void gen_step(int g){
  switch(g){
   case 0: case 1: sh_left(0,64,13); sh_right(0,64,7); sh_left(0,64,17); break;
   case 2: {  /* Marsaglia xorshift128 over four 32-bit words x,y,z,w at 0,32,64,96 */
     uint64_t t[32][MAXW];
     for(int i=0;i<32;i++) rc(t[i],SYM[i]);                 /* t = x */
     for(int i=31;i>=11;i--) rx(t[i],t[i-11]);              /* t ^= t<<11 */
     for(int i=0;i+8<32;i++) rx(t[i],t[i+8]);               /* t ^= t>>8  */
     for(int i=0;i<32;i++){ rc(SYM[i],SYM[32+i]); }         /* x = y */
     for(int i=0;i<32;i++){ rc(SYM[32+i],SYM[64+i]); }      /* y = z */
     for(int i=0;i<32;i++){ rc(SYM[64+i],SYM[96+i]); }      /* z = w */
     for(int i=0;i+19<32;i++) rx(SYM[96+i],SYM[96+i+19]);   /* w ^= w>>19 */
     for(int i=0;i<32;i++) rx(SYM[96+i],t[i]);              /* w ^= t */
     break; }
   case 3: {  /* xorshift96: t = x^(x<<3); x=y; y=z; z = (z^(z>>19)) ^ (t^(t>>6)) */
     uint64_t t[32][MAXW];
     for(int i=0;i<32;i++) rc(t[i],SYM[i]);
     for(int i=31;i>=3;i--) rx(t[i],SYM[i-3]);
     for(int i=0;i<32;i++) rc(TMPS[i],t[i]);
     for(int i=0;i+6<32;i++) rx(TMPS[i],t[i+6]);
     for(int i=0;i<32;i++){ rc(SYM[i],SYM[32+i]); }
     for(int i=0;i<32;i++){ rc(SYM[32+i],SYM[64+i]); }
     for(int i=0;i+19<32;i++) rx(SYM[64+i],SYM[64+i+19]);
     for(int i=0;i<32;i++) rx(SYM[64+i],TMPS[i]);
     break; }
   case 4: lfsr_step(LT64); break;
   case 5: lfsr_step(LT128); break;
   case 6: lfsr_step(LT256); break;
   case 7: lfsr_step(LT512); break;
  }
}
static void gen_out(int g){
  if(g==0){ for(int b=0;b<32;b++) rc(OUT[b],SYM[32+b]); }            /* hi 32 of 64 */
  else if(g==1){ for(int b=0;b<32;b++) rc(OUT[b],SYM[b]); }          /* lo 32 of 64 */
  else if(g==2||g==3){ int base=(g==2)?96:64; for(int b=0;b<32;b++) rc(OUT[b],SYM[base+b]); }
  else { for(int b=0;b<32;b++) rc(OUT[b],SYM[B-32+b]); }             /* top 32 of LFSR */
}
/* ---------------- GF(2) elimination on B unknowns ---------------- */
static uint64_t PIV[MAXB][MAXW]; static uint8_t USED[MAXB],PRHS[MAXB]; static int NPIV,CONTRA;
static void reset_basis(void){ memset(USED,0,sizeof USED); NPIV=0;CONTRA=0; }
static void insert_eq(uint64_t*row,int rhs){
  for(int w=0;w<NWB;w++){
    while(row[w]){ int p=w*64+__builtin_ctzll(row[w]);
      if(USED[p]){ for(int q=w;q<NWB;q++) row[q]^=PIV[p][q]; rhs^=PRHS[p]; }
      else { memcpy(PIV[p],row,NWB*8); PRHS[p]=rhs; USED[p]=1; NPIV++; return; } } }
  if(rhs) CONTRA++;
}
static int lead_bits(uint64_t lo,uint64_t hi,int*bp,int*bv){
  uint32_t x=(uint32_t)(lo^hi); int nb=x?__builtin_clz(x):32,n=0;
  for(int b=31;b>=32-nb;b--){bp[n]=b;bv[n]=(lo>>b)&1;n++;}
  return n;
}
static void range_of_index(uint32_t j,uint32_t k,uint64_t*lo,uint64_t*hi){
  *lo=((uint64_t)j<<32)/k+((((uint64_t)j<<32)%k)?1:0);
  *hi=(((uint64_t)j+1)<<32)/k+(((((uint64_t)j+1)<<32)%k)?1:0)-1;
}
static const double BCUM[6]={0.512,0.750,0.900,0.950,0.975,1.0};
static const int BVAL[6]={1,2,3,4,5,10};
static void range_of_boost(int v,uint64_t*lo,uint64_t*hi){
  int i=0;for(;i<6;i++) if(BVAL[i]==v)break; if(i==6)i=0;
  *lo=i?(uint64_t)(BCUM[i-1]*4294967296.0):0ULL;
  *hi=i==5?0xFFFFFFFFULL:(uint64_t)(BCUM[i]*4294967296.0)-1ULL;
}
int main(int argc,char**argv){
  const char*BIN=argc>6?argv[6]:"draws.bin";
  FILE*f=fopen(BIN,"rb"); if(!f||fread(&N,4,1,f)!=1){perror(BIN);return 1;}
  IDS=malloc(4*N);TS=malloc(4*N); uint64_t*LO=malloc(8*N),*HI=malloc(8*N);
  NUMS=malloc(20*N);BOOST=malloc(N);BONUS=malloc(N);
  if(fread(IDS,4,N,f)!=N||fread(TS,4,N,f)!=N||fread(LO,8,N,f)!=N||fread(HI,8,N,f)!=N||
     fread(NUMS,20,N,f)!=N||fread(BOOST,1,N,f)!=N||fread(BONUS,1,N,f)!=N){fprintf(stderr,"short read\n");return 1;}
  fclose(f);
  int g=argc>1?atoi(argv[1]):0, mode=argc>2?atoi(argv[2]):0, W=argc>3?atoi(argv[3]):20;
  long D=argc>4?atol(argv[4]):300; int first=argc>5?atoi(argv[5]):0;
  const int BS[8]={64,64,128,96,64,128,256,512};
  const char*GN[8]={"xorshift64(hi32)","xorshift64(lo32)","xorshift128(Marsaglia)",
                    "xorshift96","lfsr64","lfsr128","lfsr256","lfsr512"};
  B=BS[g]; NWB=(B+63)/64;
  memset(SYM,0,sizeof SYM);
  for(int i=0;i<B;i++) SYM[i][i/64]|=1ULL<<(i%64);
  reset_basis();
  int bp[8],bv[8]; uint64_t row[MAXW]; long neq=0;
  for(long k=0;k<D*W && CONTRA<3;k++){
    int r=(int)(k%W); long d=k/W; int want=0; uint64_t lo=0,hi=0;
    if(r==0&&mode==0){ range_of_index((uint32_t)(BONUS[first+d]-1),80,&lo,&hi); want=1; }
    else if(r==0&&mode==1){ int rk=-1;
      for(int q=0;q<20;q++) if(NUMS[(size_t)(first+d)*20+q]==BONUS[first+d]){rk=q;break;}
      if(rk>=0){ range_of_index((uint32_t)rk,20,&lo,&hi); want=1; } }
    else if(r==20&&mode==3){ range_of_boost(BOOST[first+d],&lo,&hi); want=1; }
    if(want){ gen_out(g); int nb=lead_bits(lo,hi,bp,bv);
      for(int q=0;q<nb;q++){ memcpy(row,OUT[bp[q]],NWB*8); insert_eq(row,bv[q]); neq++; } }
    gen_step(g);
  }
  printf("%-24s B=%4d mode=%d W=%2d draws=%5ld : eqs=%6ld rank=%4d/%d contra=%d  -> %s\n",
     GN[g],B,mode,W,D,neq,NPIV,B,CONTRA,
     (CONTRA>=3)?"REJECTED":(NPIV>=B-1?"*** CONSISTENT ***":"inconclusive (need more draws)"));
  return CONTRA>=3?2:0;
}
