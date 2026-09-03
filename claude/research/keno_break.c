/* keno_break — algebraic recovery of an MT19937 state from ORDERED keno draws (20 of 80).
 *
 *   ./keno_break demo <draws> <seed> <skip> <sampler> <mapping>
 *   ./keno_break file <path> <sampler> <mapping>
 *   ./keno_break scanfile <path>          try all 3x3 sampler/mapping hypotheses
 *
 * <path> holds one draw per line, 20 numbers in DRAW order (not sorted).
 *
 * samplers  0 fisher-yates forward   1 fisher-yates backward   2 floyd
 * mappings  0 mulhi (u*k)>>32        1 u%k                     2 (u>>16)%k
 *
 * Every mapping leaks F2-linear bits of the 32-bit output u:
 *   mulhi  -> the common leading bits of the interval u must lie in   (~4.5 bits)
 *   u%k    -> 80 = 16*5, so u mod 16 = j mod 16, i.e. bits 0..3       (4 bits)
 *   u>>16  -> bits 16..19                                            (4 bits)
 * MT19937 is F2-linear, so those bits are linear forms over the 19968 state bits
 * and Gaussian elimination over GF(2) finishes the job. A wrong hypothesis makes
 * the (heavily over-determined) system inconsistent, which is how the scan works.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>
#define NB 19968
#define NW (NB/64)
#define MATRIX_A 0x9908b0dfU

typedef struct{uint32_t mt[624];int mti;}MT;
static void mt_seed(MT*S,uint32_t s){S->mt[0]=s;for(int i=1;i<624;i++)S->mt[i]=1812433253U*(S->mt[i-1]^(S->mt[i-1]>>30))+i;S->mti=624;}
static void mt_twist(MT*S){uint32_t y;int k;
  for(k=0;k<227;k++){y=(S->mt[k]&0x80000000U)|(S->mt[k+1]&0x7fffffffU);S->mt[k]=S->mt[k+397]^(y>>1)^((y&1)?MATRIX_A:0);}
  for(;k<623;k++){y=(S->mt[k]&0x80000000U)|(S->mt[k+1]&0x7fffffffU);S->mt[k]=S->mt[k-227]^(y>>1)^((y&1)?MATRIX_A:0);}
  y=(S->mt[623]&0x80000000U)|(S->mt[0]&0x7fffffffU);S->mt[623]=S->mt[396]^(y>>1)^((y&1)?MATRIX_A:0);S->mti=0;}
static uint32_t mt_next(MT*S){ if(S->mti>=624)mt_twist(S);
  uint32_t y=S->mt[S->mti++];y^=y>>11;y^=(y<<7)&0x9d2c5680U;y^=(y<<15)&0xefc60000U;y^=y>>18;return y;}

/* ---------- index mapping ---------- */
static inline uint32_t mapk(int m,uint32_t u,uint32_t k){
  if(m==0) return (uint32_t)(((uint64_t)u*k)>>32);
  if(m==1) return u%k;
  return (u>>16)%k;
}
/* known F2-linear bits of u given the index j and the range k.
   Fills bitpos[]/bitval[], returns how many. */
static int known_bits(int m,uint32_t j,uint32_t k,int*bitpos,int*bitval){
  int n=0;
  if(m==0){
    uint64_t lo=((uint64_t)j<<32)/k + ((((uint64_t)j<<32)%k)?1:0);
    uint64_t hi=(((uint64_t)j+1)<<32)/k + (((((uint64_t)j+1)<<32)%k)?1:0);
    hi-=1;
    uint32_t x=(uint32_t)(lo^hi);
    int nb = x ? __builtin_clz(x) : 32;          /* leading bits that agree */
    for(int b=31;b>=32-nb;b--){bitpos[n]=b;bitval[n]=(lo>>b)&1;n++;}
    return n;
  }
  /* u = j (mod k) also fixes u mod 2^a where a = v2(k), i.e. a low bits of u.
     Over k = 80..61 that is 22 linear bits per draw (k=64 alone gives 6). */
  int a=__builtin_ctz(k); if(a>16)a=16; if(!a) return 0;
  int base = (m==1)?0:16;
  uint32_t r = j & ((1u<<a)-1);
  for(int b=0;b<a;b++){bitpos[n]=base+b;bitval[n]=(r>>b)&1;n++;}
  return n;
}
/* ---------- samplers: value sequence <-> index sequence ---------- */
/* forward: returns the 20 raw indices r_i in [0,80-i) */
static int invert_sampler(int s,const int*v,uint32_t*r){
  uint8_t a[81]; for(int i=0;i<80;i++)a[i]=i+1;
  if(s==0){
    for(int i=0;i<20;i++){int j=-1; for(int q=i;q<80;q++) if(a[q]==v[i]){j=q;break;}
      if(j<0)return 0; r[i]=j-i; uint8_t t=a[i];a[i]=a[j];a[j]=t;}
    return 1;
  }
  if(s==1){
    for(int i=79,c=0;i>=60;i--,c++){int j=-1; for(int q=0;q<=i;q++) if(a[q]==v[c]){j=q;break;}
      if(j<0)return 0; r[c]=j; uint8_t t=a[i];a[i]=a[j];a[j]=t;}
    return 1;
  }
  /* floyd: for j=61..80, t=rnd(j)+1 ; value = t if unseen else j */
  uint64_t lo=0,hi=0; int seen[81]={0};
  for(int c=0,jj=61;jj<=80;jj++,c++){
    int val=v[c];
    if(val==jj){ /* t was already seen: t is not observable -> hypothesis unusable */
      return 0; }
    if(seen[val])return 0;
    seen[val]=1; r[c]=val-1;
  }
  (void)lo;(void)hi; return 1;
}
static void run_sampler(int s,int m,MT*G,int*out){
  uint8_t a[81]; for(int i=0;i<80;i++)a[i]=i+1;
  if(s==0){for(int i=0;i<20;i++){uint32_t j=i+mapk(m,mt_next(G),80-i);uint8_t t=a[i];a[i]=a[j];a[j]=t;out[i]=a[i];}return;}
  if(s==1){for(int i=79,c=0;i>=60;i--,c++){uint32_t j=mapk(m,mt_next(G),i+1);uint8_t t=a[i];a[i]=a[j];a[j]=t;out[c]=a[i];}return;}
  int seen[81]={0};
  for(int c=0,jj=61;jj<=80;jj++,c++){uint32_t t=mapk(m,mt_next(G),jj)+1;
    int val = seen[t]? jj : (int)t; seen[val]=1; out[c]=val;}
}
static uint32_t range_at(int s,int i){ if(s==0)return 80-i; if(s==1)return 80-i; return 61+i; }

/* ---------- symbolic MT ---------- */
static uint64_t *SS;
#define SB(i,b) (SS+(((size_t)(i)*32+(b))*NW))
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
static uint64_t TEMPO[32][NW];
static void sym_temper(int idx){
  static uint64_t y[32][NW],t[32][NW];
  for(int b=0;b<32;b++) rcpy(y[b],SB(idx,b));
  for(int b=0;b<32;b++){rcpy(t[b],y[b]); if(b+11<32) rxor(t[b],y[b+11]);}
  for(int b=0;b<32;b++) rcpy(y[b],t[b]);
  for(int b=0;b<32;b++){rcpy(t[b],y[b]); if(b-7>=0&&((0x9d2c5680U>>b)&1)) rxor(t[b],y[b-7]);}
  for(int b=0;b<32;b++) rcpy(y[b],t[b]);
  for(int b=0;b<32;b++){rcpy(t[b],y[b]); if(b-15>=0&&((0xefc60000U>>b)&1)) rxor(t[b],y[b-15]);}
  for(int b=0;b<32;b++) rcpy(y[b],t[b]);
  for(int b=0;b<32;b++){rcpy(t[b],y[b]); if(b+18<32) rxor(t[b],y[b+18]);}
  for(int b=0;b<32;b++) rcpy(TEMPO[b],t[b]);
}
/* ---------- GF(2) elimination ---------- */
static uint64_t **PIV; static uint8_t *PRHS; static int NPIV,CONTRA;
static void insert_eq(uint64_t*row,int rhs){
  for(int w=0;w<NW;w++){
    while(row[w]){ int p=w*64+__builtin_ctzll(row[w]);
      if(PIV[p]){ for(int q=w;q<NW;q++) row[q]^=PIV[p][q]; rhs^=PRHS[p]; }
      else { PIV[p]=malloc(NW*8); memcpy(PIV[p],row,NW*8); PRHS[p]=rhs; NPIV++; return; } } }
  if(rhs) CONTRA++;
}
static void reset_basis(void){ for(int p=0;p<NB;p++) if(PIV[p]){free(PIV[p]);PIV[p]=NULL;} NPIV=0;CONTRA=0; }

/* attempt one hypothesis; returns 1 on a consistent full recovery */
static int attempt(int s,int m,int D,uint32_t (*R)[20],int (*draws)[20],int nchk,int pos0,int verbose){
  reset_basis();
  memset(SS,0,(size_t)624*32*NW*8);
  for(int i=0;i<624;i++)for(int b=0;b<32;b++){int p=i*32+b; SB(i,b)[p/64]|=1ULL<<(p%64);}
  uint64_t row[NW]; int pos=pos0, eqs=0;
  int bitpos[32],bitval[32];
  for(int t=0;t<D*20 && CONTRA<3;t++){
    if(pos>=624){sym_twist();pos=0;}
    int i=t%20;
    int nb=known_bits(m,R[t/20][i],range_at(s,i),bitpos,bitval);
    if(nb){ sym_temper(pos);
      for(int q=0;q<nb;q++){ memcpy(row,TEMPO[bitpos[q]],NW*8); insert_eq(row,bitval[q]); eqs++; } }
    pos++;
  }
  if(CONTRA>=3){ if(verbose)printf("    sampler %d mapping %d : INCONSISTENT (rank %d, %d eqs)\n",s,m,NPIV,eqs); return 0; }
  uint64_t x[NW]; memset(x,0,NW*8);
  for(int p=NB-1;p>=0;p--){ if(!PIV[p])continue;
    uint64_t acc=0; for(int w=0;w<NW;w++) acc^=PIV[p][w]&x[w];
    if(PRHS[p]^__builtin_parityll(acc)) x[p/64]|=1ULL<<(p%64); }
  MT G; for(int i=0;i<624;i++){uint32_t v=0;for(int b=0;b<32;b++) if((x[(i*32+b)/64]>>((i*32+b)%64))&1) v|=1u<<b; G.mt[i]=v;} G.mti=624;
  for(int i=0;i<pos0 && pos0<624;i++) mt_next(&G);
  int okobs=0,okfut=0,o[20];
  for(int d=0;d<D+nchk;d++){ run_sampler(s,m,&G,o); int mt2=1;
    for(int i=0;i<20;i++) if(o[i]!=draws[d][i]) mt2=0;
    if(d<D) okobs+=mt2; else okfut+=mt2; }
  if(verbose) printf("    sampler %d mapping %d : rank %d/%d, %d eqs -> replayed %d/%d, predicted %d/%d\n",
      s,m,NPIV,NB,eqs,okobs,D,okfut,nchk);
  return (okobs==D && (nchk==0||okfut==nchk));
}

int main(int argc,char**argv){
  const char*mode = argc>1?argv[1]:"demo";
  SS=calloc((size_t)624*32*NW,8); PIV=calloc(NB,sizeof(uint64_t*)); PRHS=calloc(NB,1);
  if(!strcmp(mode,"demo")){
    int D=argc>2?atoi(argv[2]):400; uint32_t seed=argc>3?(uint32_t)strtoul(argv[3],0,0):0xC0FFEE42U;
    int skip=argc>4?atoi(argv[4]):0, s=argc>5?atoi(argv[5]):0, m=argc>6?atoi(argv[6]):0;
    printf("demo: %d ordered draws, hidden seed 0x%08X, skip %d, sampler %d, mapping %d\n",D,seed,skip,s,m);
    MT G; mt_seed(&G,seed); for(int i=0;i<skip;i++)mt_next(&G);
    while(G.mti!=624 && G.mti!=0) mt_next(&G);
    int (*draws)[20]=malloc(sizeof(int)*20*(D+50));
    uint32_t (*R)[20]=malloc(sizeof(uint32_t)*20*D);
    for(int d=0;d<D+50;d++){ run_sampler(s,m,&G,draws[d]);
      if(d<D && !invert_sampler(s,draws[d],R[d])){printf("  sampler %d not invertible on draw %d\n",s,d);return 1;} }
    clock_t c0=clock();
    int ok=attempt(s,m,D,R,draws,50,624,1);
    printf("  %s   [%.1fs]\n", ok?"*** FULL BREAK: every future draw predicted exactly ***":"incomplete",
           (double)(clock()-c0)/CLOCKS_PER_SEC);
    return ok?0:2;
  }
  /* file / scanfile: one draw per line, 20 numbers in DRAW order */
  const char*path = argc>2?argv[2]:"ordered.txt";
  FILE*f=fopen(path,"r"); if(!f){perror(path);return 1;}
  int cap=4096,D=0; int (*draws)[20]=malloc(sizeof(int)*20*cap);
  char line[512];
  while(fgets(line,sizeof line,f)){
    int v[20],n=0; char*p=line;
    while(n<20){ while(*p&&!(*p>='0'&&*p<='9'))p++; if(!*p)break; v[n++]=(int)strtol(p,&p,10); }
    if(n!=20)continue;
    if(D>=cap){cap*=2;draws=realloc(draws,sizeof(int)*20*cap);}
    memcpy(draws[D++],v,sizeof v);
  }
  fclose(f);
  printf("%s: %d ordered draws read\n",path,D);
  if(D<300) printf("  WARNING: %d draws; MT19937 needs ~300 (19937 bits / ~90 usable bits per draw)\n",D);
  /* sanity: is the feed really ordered, or already sorted? */
  int sortedcount=0, rankhist[21]={0};
  for(int d=0;d<D;d++){ int srt[20]; memcpy(srt,draws[d],sizeof srt);
    for(int a=0;a<20;a++)for(int b=a+1;b<20;b++) if(srt[b]<srt[a]){int t=srt[a];srt[a]=srt[b];srt[b]=t;}
    int issorted=1; for(int i=0;i<20;i++) if(srt[i]!=draws[d][i]) issorted=0;
    sortedcount+=issorted;
    for(int i=0;i<20;i++) if(srt[i]==draws[d][0]){rankhist[i]++;break;} }
  printf("  already-sorted lines: %d/%d  (%.1f%%; a real draw order gives ~0%%)\n",sortedcount,D,100.0*sortedcount/D);
  printf("  rank of the first drawn ball inside the sorted set:");
  for(int i=0;i<20;i++)printf(" %d",rankhist[i]); printf("\n");
  if(sortedcount>D/2){ printf("  -> the feed publishes sorted numbers; the order attack cannot run.\n"); return 3; }
  int lo_s=0,hi_s=3,lo_m=0,hi_m=3;
  if(!strcmp(mode,"file")){ lo_s=argc>3?atoi(argv[3]):0; hi_s=lo_s+1; lo_m=argc>4?atoi(argv[4]):0; hi_m=lo_m+1; }
  int nchk = D>350 ? 25 : 0; int Duse = D-nchk;
  uint32_t (*R)[20]=malloc(sizeof(uint32_t)*20*Duse);
  for(int s=lo_s;s<hi_s;s++){
    int bad=0; for(int d=0;d<Duse;d++) if(!invert_sampler(s,draws[d],R[d])){bad=1;break;}
    if(bad){ printf("    sampler %d : draw order not consistent with this sampler\n",s); continue; }
    for(int m=lo_m;m<hi_m;m++) if(attempt(s,m,Duse,R,draws,nchk,624,1)){
      printf("  *** CONSISTENT: sampler %d, mapping %d — generator recovered ***\n",s,m); return 0; }
  }
  printf("  no consistent hypothesis: the generator is not MT19937 under these samplers,\n");
  printf("  or the buffer alignment differs (rerun with a shifted window).\n");
  return 2;
}
