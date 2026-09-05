/* Platform-realistic RNG hunt: .NET Random, V8 Math.random (xorshift128+ fwd/reverse cache),
   Python random.sample (MT19937 + _randbelow pool), PHP mt_rand (MT_RAND_PHP + fixed). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <pthread.h>
static uint32_t N,*IDS,*TS; static uint64_t *LO,*HI;
#define INMASK(lo,hi,v) ( (v)<65 ? (((lo)>>((v)-1))&1ULL) : (((hi)>>((v)-65))&1ULL) )

/* ---- .NET Framework Random ---- */
typedef struct{int32_t A[56];int inext,inextp;}DNET;
static void dnet_init(DNET*R,int32_t Seed){
  const int32_t MBIG=2147483647,MSEED=161803398;
  int32_t sub = (Seed==(int32_t)0x80000000)?MBIG:(Seed<0?-Seed:Seed);
  int32_t mj=MSEED-sub, mk=1; R->A[55]=mj;
  for(int i=1;i<55;i++){int ii=(21*i)%55; R->A[ii]=mk; mk=mj-mk; if(mk<0)mk+=MBIG; mj=R->A[ii];}
  for(int k=1;k<5;k++)for(int i=1;i<56;i++){R->A[i]-=R->A[1+(i+30)%55]; if(R->A[i]<0)R->A[i]+=MBIG;}
  R->inext=0;R->inextp=21;}
static int32_t dnet_sample(DNET*R){const int32_t MBIG=2147483647;
  int li=R->inext,lp=R->inextp; if(++li>=56)li=1; if(++lp>=56)lp=1;
  int32_t v=R->A[li]-R->A[lp]; if(v==MBIG)v--; if(v<0)v+=MBIG;
  R->A[li]=v;R->inext=li;R->inextp=lp; return v;}

/* ---- V8 xorshift128+ ---- */
typedef struct{uint64_t s0,s1;}V8;
static inline void v8_step(V8*v){uint64_t s1=v->s0,s0=v->s1; v->s0=s0;
  s1^=s1<<23; s1^=s1>>17; s1^=s0; s1^=s0>>26; v->s1=s1;}
static inline double v8_val(V8*v){v8_step(v); return (double)((v->s0)>>12)/9007199254740992.0;}

/* ---- MT19937 (python / php-fixed) ---- */
typedef struct{uint32_t mt[624];int mti;}MT;
static void mt_init(MT*S,uint32_t s){S->mt[0]=s;for(int i=1;i<624;i++)S->mt[i]=1812433253U*(S->mt[i-1]^(S->mt[i-1]>>30))+i;S->mti=624;}
static void mt_init_arr(MT*S,uint32_t k){ /* python seeds int via init_by_array */
  mt_init(S,19650218U); uint32_t key[1]={k}; int i=1,j=0,kk=624;
  for(;kk;kk--){S->mt[i]=(S->mt[i]^((S->mt[i-1]^(S->mt[i-1]>>30))*1664525U))+key[j]+j;
    i++;j++; if(i>=624){S->mt[0]=S->mt[623];i=1;} if(j>=1)j=0;}
  for(kk=623;kk;kk--){S->mt[i]=(S->mt[i]^((S->mt[i-1]^(S->mt[i-1]>>30))*1566083941U))-i;
    i++; if(i>=624){S->mt[0]=S->mt[623];i=1;}}
  S->mt[0]=0x80000000U; S->mti=624;}
static uint32_t mt_next(MT*S){static const uint32_t mag[2]={0,0x9908b0dfU};
  if(S->mti>=624){uint32_t y;int k;
    for(k=0;k<227;k++){y=(S->mt[k]&0x80000000U)|(S->mt[k+1]&0x7fffffffU);S->mt[k]=S->mt[k+397]^(y>>1)^mag[y&1];}
    for(;k<623;k++){y=(S->mt[k]&0x80000000U)|(S->mt[k+1]&0x7fffffffU);S->mt[k]=S->mt[k-227]^(y>>1)^mag[y&1];}
    y=(S->mt[623]&0x80000000U)|(S->mt[0]&0x7fffffffU);S->mt[623]=S->mt[396]^(y>>1)^mag[y&1];S->mti=0;}
  uint32_t y=S->mt[S->mti++];y^=y>>11;y^=(y<<7)&0x9d2c5680U;y^=(y<<15)&0xefc60000U;y^=y>>18;return y;}
/* PHP legacy twist bug: uses (-(u&1)) instead of (-(v&1)) */
static uint32_t mtphp_next(MT*S){static const uint32_t mag[2]={0,0x9908b0dfU};
  if(S->mti>=624){uint32_t y;int k;
    for(k=0;k<624;k++){uint32_t u=S->mt[k],v=S->mt[(k+1)%624];
      y=(u&0x80000000U)|(v&0x7fffffffU);
      S->mt[k]=S->mt[(k+397)%624]^(y>>1)^mag[u&1];}
    S->mti=0;}
  uint32_t y=S->mt[S->mti++];y^=y>>11;y^=(y<<7)&0x9d2c5680U;y^=(y<<15)&0xefc60000U;y^=y>>18;return y;}

enum{A_DNET_FY,A_DNET_REJ,A_V8_FY,A_V8_FY_REV,A_V8_REJ,A_PY_POOL,A_PY_POOL_ARR,A_PHP_FY,A_PHP_REJ,A_MTFY_BITS,A_NALG};
static const char*AN[]={"dotnet_Next_FY","dotnet_Next_rejection","v8_math_random_FY","v8_reverse_cache_FY",
  "v8_rejection","python_sample_pool(initgen)","python_sample_pool(init_by_array)","php_mt_rand_FY","php_mt_rand_rej","mt_getrandbits_FY"};

static inline uint32_t py_below(MT*S,uint32_t n){ /* CPython _randbelow_with_getrandbits */
  int k=32-__builtin_clz(n); uint32_t r;
  do{ r=mt_next(S)>>(32-k); }while(r>=n); return r;}

static int gen20(int alg,uint64_t seed,uint64_t lo,uint64_t hi){
  int ok=0; uint8_t a[81]; for(int i=0;i<80;i++)a[i]=i+1;
  if(alg==A_DNET_FY||alg==A_DNET_REJ){ DNET R; dnet_init(&R,(int32_t)seed);
    if(alg==A_DNET_FY){for(int i=0;i<20;i++){double s=(double)dnet_sample(&R)*(1.0/2147483647.0);
        uint32_t j=i+(uint32_t)(s*(80-i)); uint8_t t=a[i];a[i]=a[j];a[j]=t;
        if(!INMASK(lo,hi,a[i]))return ok; ok++;} return ok;}
    uint64_t ul=0,uh=0;int g=0;
    while(ok<20){if(++g>4000)return ok; double s=(double)dnet_sample(&R)*(1.0/2147483647.0);
      uint32_t v=(uint32_t)(s*80)+1; if(INMASK(ul,uh,v))continue;
      if(v<65)ul|=1ULL<<(v-1);else uh|=1ULL<<(v-65);
      if(!INMASK(lo,hi,v))return ok; ok++;} return ok;}
  if(alg==A_V8_FY||alg==A_V8_FY_REV||alg==A_V8_REJ){ V8 v; v.s0=seed?seed:1; v.s1=seed*0x9E3779B97F4A7C15ULL+1;
    double cache[64]; int cn=0;
    if(alg==A_V8_FY_REV){for(int i=0;i<64;i++)cache[i]=v8_val(&v); cn=64;}
    for(int i=0;i<20;i++){double d = (alg==A_V8_FY_REV)? cache[--cn] : v8_val(&v);
      if(alg==A_V8_REJ)break;
      uint32_t j=i+(uint32_t)(d*(80-i)); uint8_t t=a[i];a[i]=a[j];a[j]=t;
      if(!INMASK(lo,hi,a[i]))return ok; ok++;}
    if(alg!=A_V8_REJ)return ok;
    uint64_t ul=0,uh=0;int g=0;
    while(ok<20){if(++g>4000)return ok; uint32_t vv=(uint32_t)(v8_val(&v)*80)+1;
      if(INMASK(ul,uh,vv))continue; if(vv<65)ul|=1ULL<<(vv-1);else uh|=1ULL<<(vv-65);
      if(!INMASK(lo,hi,vv))return ok; ok++;} return ok;}
  if(alg==A_PY_POOL||alg==A_PY_POOL_ARR||alg==A_MTFY_BITS){ MT S;
    if(alg==A_PY_POOL_ARR)mt_init_arr(&S,(uint32_t)seed); else mt_init(&S,(uint32_t)seed);
    if(alg==A_MTFY_BITS){for(int i=0;i<20;i++){uint32_t j=i+py_below(&S,80-i);
        uint8_t t=a[i];a[i]=a[j];a[j]=t; if(!INMASK(lo,hi,a[i]))return ok; ok++;} return ok;}
    uint8_t pool[81]; for(int i=0;i<80;i++)pool[i]=i+1;
    for(int i=0;i<20;i++){uint32_t j=py_below(&S,80-i); uint8_t v=pool[j]; pool[j]=pool[80-i-1];
      if(!INMASK(lo,hi,v))return ok; ok++;} return ok;}
  if(alg==A_PHP_FY||alg==A_PHP_REJ){ MT S; mt_init(&S,(uint32_t)seed);
    if(alg==A_PHP_FY){for(int i=0;i<20;i++){uint32_t r=mtphp_next(&S)>>1;
        uint32_t j=i+(uint32_t)(((uint64_t)r*(80-i))>>31); uint8_t t=a[i];a[i]=a[j];a[j]=t;
        if(!INMASK(lo,hi,a[i]))return ok; ok++;} return ok;}
    uint64_t ul=0,uh=0;int g=0;
    while(ok<20){if(++g>4000)return ok; uint32_t r=mtphp_next(&S)>>1; uint32_t vv=(uint32_t)(((uint64_t)r*80)>>31)+1;
      if(INMASK(ul,uh,vv))continue; if(vv<65)ul|=1ULL<<(vv-1);else uh|=1ULL<<(vv-65);
      if(!INMASK(lo,hi,vv))return ok; ok++;} return ok;}
  return 0;}

typedef struct{uint64_t a,b;int alg;uint64_t lo,hi;int best;uint64_t bs;}JOB;
static pthread_mutex_t MU=PTHREAD_MUTEX_INITIALIZER;
static void*w(void*p){JOB*j=(JOB*)p;j->best=0;
  for(uint64_t s=j->a;s<j->b;s++){int k=gen20(j->alg,s,j->lo,j->hi);
    if(k>j->best){j->best=k;j->bs=s; if(k>=16){pthread_mutex_lock(&MU);
      fprintf(stderr,"  !!! %s seed=%llu %d/20\n",AN[j->alg],(unsigned long long)s,k);pthread_mutex_unlock(&MU);}}}
  return 0;}
int main(int argc,char**argv){
  FILE*f=fopen("draws.bin","rb"); if(fread(&N,4,1,f)!=1)return 1;
  IDS=malloc(4*N);TS=malloc(4*N);LO=malloc(8*N);HI=malloc(8*N);
  if(fread(IDS,4,N,f)!=N)return 1; if(fread(TS,4,N,f)!=N)return 1;
  if(fread(LO,8,N,f)!=N)return 1; if(fread(HI,8,N,f)!=N)return 1; fclose(f);
  int tgt=argc>1?atoi(argv[1]):0; uint64_t A=argc>2?strtoull(argv[2],0,0):0,B=argc>3?strtoull(argv[3],0,0):(1ULL<<32);
  int T=4; fprintf(stderr,"target id=%u  seeds [%llu,%llu)\n",IDS[tgt],(unsigned long long)A,(unsigned long long)B);
  for(int alg=0;alg<A_NALG;alg++){pthread_t th[8];JOB jb[8];uint64_t span=(B-A+T-1)/T;
    for(int t=0;t<T;t++){jb[t]=(JOB){A+t*span,(A+(t+1)*span<B)?A+(t+1)*span:B,alg,LO[tgt],HI[tgt],0,0};
      pthread_create(&th[t],0,w,&jb[t]);}
    int b=0;uint64_t bs=0; for(int t=0;t<T;t++){pthread_join(th[t],0);if(jb[t].best>b){b=jb[t].best;bs=jb[t].bs;}}
    printf("%-30s best=%2d/20 seed=%llu\n",AN[alg],b,(unsigned long long)bs);fflush(stdout);}
  return 0;}
