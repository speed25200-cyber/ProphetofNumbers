/* Closes the seeded-generator gap: MT19937 / MT19937(init_by_array) / glibc rand(),
   full 2^32 seed space, with 0..63 outputs consumed before the 20 numbers
   (boost, bonus, warm-up...). One init per seed, all offsets tested by sliding. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <pthread.h>
static uint32_t N,*IDS,*TS; static uint64_t *LO,*HI;
#define INMASK(lo,hi,v) ((v)<65 ? (((lo)>>((v)-1))&1ULL) : (((hi)>>((v)-65))&1ULL))
#define MAXOFF 64
#define NEED (MAXOFF+20)
typedef struct{uint32_t mt[624];int mti;}MT;
static void mt_seed(MT*S,uint32_t s){S->mt[0]=s;for(int i=1;i<624;i++)S->mt[i]=1812433253U*(S->mt[i-1]^(S->mt[i-1]>>30))+i;S->mti=624;}
static void mt_seed_arr(MT*S,uint32_t k){mt_seed(S,19650218U);int i=1,j=0,c=624;
  for(;c;c--){S->mt[i]=(S->mt[i]^((S->mt[i-1]^(S->mt[i-1]>>30))*1664525U))+k+j;i++;j=0;if(i>=624){S->mt[0]=S->mt[623];i=1;}}
  for(c=623;c;c--){S->mt[i]=(S->mt[i]^((S->mt[i-1]^(S->mt[i-1]>>30))*1566083941U))-i;i++;if(i>=624){S->mt[0]=S->mt[623];i=1;}}
  S->mt[0]=0x80000000U;S->mti=624;}
static uint32_t mt_next(MT*S){static const uint32_t mag[2]={0,0x9908b0dfU};
  if(S->mti>=624){uint32_t y;int k;
    for(k=0;k<227;k++){y=(S->mt[k]&0x80000000U)|(S->mt[k+1]&0x7fffffffU);S->mt[k]=S->mt[k+397]^(y>>1)^mag[y&1];}
    for(;k<623;k++){y=(S->mt[k]&0x80000000U)|(S->mt[k+1]&0x7fffffffU);S->mt[k]=S->mt[k-227]^(y>>1)^mag[y&1];}
    y=(S->mt[623]&0x80000000U)|(S->mt[0]&0x7fffffffU);S->mt[623]=S->mt[396]^(y>>1)^mag[y&1];S->mti=0;}
  uint32_t y=S->mt[S->mti++];y^=y>>11;y^=(y<<7)&0x9d2c5680U;y^=(y<<15)&0xefc60000U;y^=y>>18;return y;}
typedef struct{int32_t r[34];int f;}GL;
static void gl_seed(GL*G,uint32_t s){if(!s)s=1;int32_t t[344];t[0]=(int32_t)s;
  for(int i=1;i<31;i++){int64_t hi=t[i-1]/127773,lo=t[i-1]%127773;int64_t w=16807*lo-2836*hi;if(w<0)w+=2147483647;t[i]=(int32_t)w;}
  for(int i=31;i<34;i++)t[i]=t[i-31];
  for(int i=34;i<344;i++)t[i]=t[i-31]+t[i-3];
  for(int i=0;i<34;i++)G->r[i]=t[310+i];G->f=0;}
static uint32_t gl_next(GL*G){int i=G->f%34;int a=(G->f+34-31)%34,b=(G->f+34-3)%34;
  G->r[i]=G->r[a]+G->r[b];G->f=(G->f+1)%34;return ((uint32_t)G->r[i])>>1;}

enum{M_MULHI,M_MOD,M_SHR16,M_NM};
static const char*MN[]={"mulhi","mod","shr16mod"};
enum{S_FYF,S_REJ,S_NS};
static const char*SN[]={"fy_fwd","rejection"};
enum{G_MT,G_MTARR,G_GLIBC,G_NG};
static const char*GN[]={"mt19937(init_genrand)","mt19937(init_by_array)","glibc_rand"};
static inline uint32_t mapk(int m,uint32_t u,uint32_t k){
  if(m==M_MULHI)return (uint32_t)(((uint64_t)u*k)>>32);
  if(m==M_MOD)return u%k; return (u>>16)%k;}
/* persistent identity array; only the touched cells are restored after each probe,
   so an early rejection costs a couple of writes instead of an 80-entry reset */
static __thread uint8_t A[81];
static int run20(const uint32_t*w,int off,int m,int s,uint64_t lo,uint64_t hi){
  int ok=0;
  if(s==S_FYF){
    uint32_t j0=mapk(m,w[off],80);
    if(!INMASK(lo,hi,j0+1)) return 0;              /* 75% die here, no array work */
    uint8_t tch[42]; int nt=0;
    for(int i=0;i<20;i++){uint32_t j=i+mapk(m,w[off+i],80-i);
      uint8_t t=A[i];A[i]=A[j];A[j]=t; tch[nt++]=i; tch[nt++]=(uint8_t)j;
      if(!INMASK(lo,hi,A[i])){for(int q=0;q<nt;q++)A[tch[q]]=tch[q]+1; return ok;}
      ok++;}
    for(int q=0;q<nt;q++)A[tch[q]]=tch[q]+1;
    return ok;}
  uint64_t ul=0,uh=0;int p=off;
  while(ok<20){ if(p>=NEED+120)return ok; uint32_t v=mapk(m,w[p++],80)+1;
    if(INMASK(ul,uh,v))continue; if(v<65)ul|=1ULL<<(v-1);else uh|=1ULL<<(v-65);
    if(!INMASK(lo,hi,v))return ok; ok++;} return ok;}
typedef struct{uint64_t a,b;int g;uint64_t lo,hi;int best;uint64_t bs;int bo,bm,bsamp;}JOB;
static pthread_mutex_t MU=PTHREAD_MUTEX_INITIALIZER;
static void*wk(void*p){JOB*J=(JOB*)p;J->best=0;uint32_t w[NEED+140];
  for(int i=0;i<80;i++)A[i]=i+1;
  for(uint64_t s=J->a;s<J->b;s++){
    if(J->g==G_GLIBC){GL G;gl_seed(&G,(uint32_t)s);for(int i=0;i<NEED+140;i++)w[i]=gl_next(&G);}
    else{MT M;if(J->g==G_MT)mt_seed(&M,(uint32_t)s);else mt_seed_arr(&M,(uint32_t)s);
         for(int i=0;i<NEED+140;i++)w[i]=mt_next(&M);}
    for(int off=0;off<MAXOFF;off++)for(int m=0;m<M_NM;m++)for(int sm=0;sm<S_NS;sm++){
      int k=run20(w,off,m,sm,J->lo,J->hi);
      if(k>J->best){J->best=k;J->bs=s;J->bo=off;J->bm=m;J->bsamp=sm;
        if(k>=17){pthread_mutex_lock(&MU);
          fprintf(stderr,"  !!! %s off=%d %s/%s seed=%llu %d/20\n",GN[J->g],off,MN[m],SN[sm],(unsigned long long)s,k);
          pthread_mutex_unlock(&MU);} } }
  } return 0;}
int main(int argc,char**argv){
  FILE*f=fopen("draws.bin","rb"); if(fread(&N,4,1,f)!=1)return 1;
  IDS=malloc(4*N);TS=malloc(4*N);LO=malloc(8*N);HI=malloc(8*N);
  if(fread(IDS,4,N,f)!=N)return 1; if(fread(TS,4,N,f)!=N)return 1;
  if(fread(LO,8,N,f)!=N)return 1; if(fread(HI,8,N,f)!=N)return 1; fclose(f);
  int tgt=argc>1?atoi(argv[1]):0; uint64_t A=argc>2?strtoull(argv[2],0,0):0,B=argc>3?strtoull(argv[3],0,0):(1ULL<<32);
  int T=argc>4?atoi(argv[4]):4, only=argc>5?atoi(argv[5]):-1;
  fprintf(stderr,"target id=%u  seeds [%llu,%llu)  offsets 0..%d  %d mappings x %d samplers\n",
    IDS[tgt],(unsigned long long)A,(unsigned long long)B,MAXOFF-1,M_NM,S_NS);
  for(int g=0;g<G_NG;g++){ if(only>=0&&g!=only)continue;
    pthread_t th[8];JOB jb[8];uint64_t span=(B-A+T-1)/T;
    for(int t=0;t<T;t++){jb[t]=(JOB){A+t*span,(A+(t+1)*span<B)?A+(t+1)*span:B,g,LO[tgt],HI[tgt],0,0,0,0,0};
      pthread_create(&th[t],0,wk,&jb[t]);}
    int b=0;JOB*bj=&jb[0];
    for(int t=0;t<T;t++){pthread_join(th[t],0);if(jb[t].best>b){b=jb[t].best;bj=&jb[t];}}
    printf("%-24s best=%2d/20  seed=%llu off=%d %s/%s\n",GN[g],b,(unsigned long long)bj->bs,bj->bo,MN[bj->bm],SN[bj->bsamp]);
    fflush(stdout);}
  return 0;}
