// Exhaustive PRNG state / seed search against real Loto Express draws.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <pthread.h>

static uint32_t N; static uint32_t *IDS,*TS; static uint64_t *LO,*HI; static uint8_t *NUMS,*BOOST,*BONUS;

static void loadbin(const char*p){
  FILE*f=fopen(p,"rb"); if(!f){perror("open");exit(1);}
  if(fread(&N,4,1,f)!=1)exit(1);
  IDS=malloc(4*N);TS=malloc(4*N);LO=malloc(8*N);HI=malloc(8*N);
  NUMS=malloc(20*N);BOOST=malloc(N);BONUS=malloc(N);
  fread(IDS,4,N,f);fread(TS,4,N,f);fread(LO,8,N,f);fread(HI,8,N,f);
  fread(NUMS,20,N,f);fread(BOOST,1,N,f);fread(BONUS,1,N,f);fclose(f);
}
#define INMASK(lo,hi,v) ( (v)<65 ? (((lo)>>((v)-1))&1ULL) : (((hi)>>((v)-65))&1ULL) )

/* ---------------- generators ---------------- */
enum {G_MINSTD,G_MINSTD48,G_RANDU,G_JAVA,G_MSVC,G_BORLAND,G_XOR32,G_XOR64,
      G_SPLITMIX,G_MMIX,G_NR,G_PCG32,G_MT,G_GLIBC,G_XOSHIRO,G_LCG2,G_NGEN};
static const char*GN[]={"minstd16807","minstd48271","randu","java48","msvc","borland","xorshift32",
  "xorshift64","splitmix64","lcg64_mmix","nr_ranqd1","pcg32","mt19937","glibc_rand","xoshiro256ss","lcg64_2"};

typedef struct { uint64_t s0,s1,s2,s3; uint32_t mt[624]; int mti; int32_t r[344]; int rf,rr; } ST;

static inline uint64_t sm64(uint64_t*x){uint64_t z=(*x+=0x9E3779B97F4A7C15ULL);
  z=(z^(z>>30))*0xBF58476D1CE4E5B9ULL; z=(z^(z>>27))*0x94D049BB133111EBULL; return z^(z>>31);}
static inline uint64_t rotl64(uint64_t x,int k){return (x<<k)|(x>>(64-k));}

static void mt_init(ST*S,uint32_t seed){S->mt[0]=seed;
  for(int i=1;i<624;i++)S->mt[i]=1812433253U*(S->mt[i-1]^(S->mt[i-1]>>30))+i; S->mti=624;}
static uint32_t mt_next(ST*S){
  if(S->mti>=624){static const uint32_t mag[2]={0,0x9908b0dfU};uint32_t y;int k;
    for(k=0;k<227;k++){y=(S->mt[k]&0x80000000U)|(S->mt[k+1]&0x7fffffffU);S->mt[k]=S->mt[k+397]^(y>>1)^mag[y&1];}
    for(;k<623;k++){y=(S->mt[k]&0x80000000U)|(S->mt[k+1]&0x7fffffffU);S->mt[k]=S->mt[k+(397-624)]^(y>>1)^mag[y&1];}
    y=(S->mt[623]&0x80000000U)|(S->mt[0]&0x7fffffffU);S->mt[623]=S->mt[396]^(y>>1)^mag[y&1];S->mti=0;}
  uint32_t y=S->mt[S->mti++]; y^=y>>11; y^=(y<<7)&0x9d2c5680U; y^=(y<<15)&0xefc60000U; y^=y>>18; return y;}

static void glibc_init(ST*S,uint32_t seed){ if(seed==0)seed=1; S->r[0]=(int32_t)seed;
  for(int i=1;i<31;i++){int64_t hi=S->r[i-1]/127773,lo=S->r[i-1]%127773;
    int64_t w=16807*lo-2836*hi; if(w<0)w+=2147483647; S->r[i]=(int32_t)w;}
  for(int i=31;i<34;i++)S->r[i]=S->r[i-31];
  for(int i=34;i<344;i++)S->r[i]=S->r[i-31]+S->r[i-3];
  S->rf=344;}
static uint32_t glibc_next(ST*S){ int i=S->rf;
  S->r[i%344]=S->r[(i-31)%344]+S->r[(i-3)%344]; uint32_t v=((uint32_t)S->r[i%344])>>1; S->rf=i+1;
  if(S->rf>=688){ /* keep indices bounded: shift window */ for(int k=0;k<344;k++);}
  return v;}

static void ginit(int g,ST*S,uint64_t seed){
  switch(g){
   case G_MINSTD: case G_MINSTD48: S->s0=(seed%2147483646ULL)+1; break;
   case G_RANDU: S->s0=(seed|1)&0x7fffffffULL; break;
   case G_JAVA: S->s0=(seed^0x5DEECE66DULL)&((1ULL<<48)-1); break;
   case G_MSVC: case G_BORLAND: case G_NR: S->s0=(uint32_t)seed; break;
   case G_XOR32: S->s0=(uint32_t)seed?(uint32_t)seed:1; break;
   case G_XOR64: S->s0=seed?seed:1; break;
   case G_SPLITMIX: case G_MMIX: case G_LCG2: S->s0=seed; break;
   case G_PCG32: {S->s0=0;S->s1=(seed<<1)|1; S->s0=S->s0*6364136223846793005ULL+S->s1;
                  S->s0+=seed; S->s0=S->s0*6364136223846793005ULL+S->s1;} break;
   case G_MT: mt_init(S,(uint32_t)seed); break;
   case G_GLIBC: glibc_init(S,(uint32_t)seed); break;
   case G_XOSHIRO: {uint64_t x=seed; S->s0=sm64(&x);S->s1=sm64(&x);S->s2=sm64(&x);S->s3=sm64(&x);} break;
  }
}
static inline uint32_t gnext(int g,ST*S){
  switch(g){
   case G_MINSTD: S->s0=(16807ULL*S->s0)%2147483647ULL; return (uint32_t)S->s0;
   case G_MINSTD48:S->s0=(48271ULL*S->s0)%2147483647ULL; return (uint32_t)S->s0;
   case G_RANDU:  S->s0=(65539ULL*S->s0)&0x7fffffffULL; return (uint32_t)S->s0;
   case G_JAVA:   S->s0=(S->s0*0x5DEECE66DULL+0xBULL)&((1ULL<<48)-1); return (uint32_t)(S->s0>>16);
   case G_MSVC:   S->s0=(S->s0*214013ULL+2531011ULL)&0xffffffffULL; return (uint32_t)((S->s0>>16)&0x7fff);
   case G_BORLAND:S->s0=(S->s0*22695477ULL+1ULL)&0xffffffffULL; return (uint32_t)((S->s0>>16)&0x7fff);
   case G_XOR32:  {uint32_t x=(uint32_t)S->s0; x^=x<<13;x^=x>>17;x^=x<<5; S->s0=x; return x;}
   case G_XOR64:  {uint64_t x=S->s0; x^=x<<13;x^=x>>7;x^=x<<17; S->s0=x; return (uint32_t)(x>>32);}
   case G_SPLITMIX:return (uint32_t)(sm64(&S->s0)>>32);
   case G_MMIX:   S->s0=S->s0*6364136223846793005ULL+1442695040888963407ULL; return (uint32_t)(S->s0>>32);
   case G_LCG2:   S->s0=S->s0*2862933555777941757ULL+3037000493ULL; return (uint32_t)(S->s0>>32);
   case G_NR:     S->s0=(S->s0*1664525ULL+1013904223ULL)&0xffffffffULL; return (uint32_t)S->s0;
   case G_PCG32:  {uint64_t o=S->s0; S->s0=o*6364136223846793005ULL+S->s1;
                   uint32_t xs=(uint32_t)(((o>>18)^o)>>27), rot=(uint32_t)(o>>59);
                   return (xs>>rot)|(xs<<((-rot)&31));}
   case G_MT:     return mt_next(S);
   case G_GLIBC:  return glibc_next(S);
   case G_XOSHIRO:{uint64_t r=rotl64(S->s1*5,7)*9,t=S->s1<<17;
                   S->s2^=S->s0;S->s3^=S->s1;S->s1^=S->s2;S->s0^=S->s3;S->s2^=t;S->s3=rotl64(S->s3,45);
                   return (uint32_t)(r>>32);}
  }
  return 0;
}
/* bits of raw output, for mapping */
static inline int gbits(int g){
  switch(g){case G_MINSTD:case G_MINSTD48:case G_RANDU:return 31;
            case G_MSVC:case G_BORLAND:return 15; default:return 32;}
}
/* ---------------- index mappings ---------------- */
enum {M_MOD,M_MULHI,M_SHR16,M_JAVA,M_NMOD};
static const char*MN[]={"mod","mulhi","shr16mod","javaNextInt"};
static inline uint32_t rnd_k(int m,int bits,uint32_t u,uint32_t k){
  switch(m){
   case M_MOD: return u%k;
   case M_MULHI: return (uint32_t)(((uint64_t)u*k)>>bits);
   case M_SHR16: return (u>>16)%k;
   case M_JAVA: {uint32_t r=(u&0x7fffffffU)%k; return r;}
  }
  return 0;
}
/* ---------------- samplers ---------------- */
enum {S_FYF,S_FYB,S_REJ,S_FLOYD,S_NS};
static const char*SN[]={"fisher_yates_fwd","fisher_yates_bwd","rejection","floyd"};

/* returns number of leading values that are inside the mask (20 => full match) */
static int gen_check(int g,int m,int s,uint64_t seed,uint64_t lo,uint64_t hi,uint8_t*out){
  ST S; ginit(g,&S,seed); int bits=gbits(g);
  uint8_t a[81]; int touched[64],nt=0,ok=0;
  if(s==S_FYF||s==S_FYB||s==S_FLOYD){for(int i=0;i<80;i++)a[i]=i+1;}
  if(s==S_FYF){
    for(int i=0;i<20;i++){uint32_t j=i+rnd_k(m,bits,gnext(g,&S),80-i);
      uint8_t t=a[i];a[i]=a[j];a[j]=t; uint8_t v=a[i];
      if(!INMASK(lo,hi,v))return ok; out[ok++]=v;}
    return ok;
  } else if(s==S_FYB){
    for(int i=79;i>=60;i--){uint32_t j=rnd_k(m,bits,gnext(g,&S),i+1);
      uint8_t t=a[i];a[i]=a[j];a[j]=t; uint8_t v=a[i];
      if(!INMASK(lo,hi,v))return ok; out[ok++]=v;}
    return ok;
  } else if(s==S_REJ){
    uint64_t ul=0,uh=0; int guard=0;
    while(ok<20){ if(++guard>4000)return ok;
      uint32_t v=rnd_k(m,bits,gnext(g,&S),80)+1;
      if(INMASK(ul,uh,v))continue;
      if(v<65)ul|=1ULL<<(v-1); else uh|=1ULL<<(v-65);
      if(!INMASK(lo,hi,v))return ok; out[ok++]=v;}
    return ok;
  } else { /* Floyd */
    uint64_t ul=0,uh=0;
    for(int j=61;j<=80;j++){uint32_t t=rnd_k(m,bits,gnext(g,&S),j)+1;
      uint32_t v = INMASK(ul,uh,t)? (uint32_t)j : t;
      if(v<65)ul|=1ULL<<(v-1); else uh|=1ULL<<(v-65);
      if(!INMASK(lo,hi,v))return ok; out[ok++]=v;}
    return ok;
  }
  (void)touched;(void)nt;
}

typedef struct{uint64_t a,b;int g,m,s;uint64_t lo,hi;int tid;long long best;uint64_t bestseed;} JOB;
static pthread_mutex_t MU=PTHREAD_MUTEX_INITIALIZER;
static int GBEST=0; static uint64_t GBSEED=0;

static void* worker(void*p){
  JOB*j=(JOB*)p; uint8_t out[24]; int best=0;uint64_t bs=0;
  for(uint64_t s=j->a;s<j->b;s++){
    int k=gen_check(j->g,j->m,j->s,s,j->lo,j->hi,out);
    if(k>best){best=k;bs=s; if(k>=14){pthread_mutex_lock(&MU);
        fprintf(stderr,"  !! %s/%s/%s seed=%llu matched %d/20\n",GN[j->g],MN[j->m],SN[j->s],(unsigned long long)s,k);
        pthread_mutex_unlock(&MU);} }
  }
  j->best=best;j->bestseed=bs; return NULL;
}

int main(int argc,char**argv){
  loadbin("draws.bin");
  int target = argc>1?atoi(argv[1]):0;
  uint64_t A = argc>2?strtoull(argv[2],0,0):0;
  uint64_t B = argc>3?strtoull(argv[3],0,0):(1ULL<<32);
  int NTH = argc>4?atoi(argv[4]):4;
  int onlyg = argc>5?atoi(argv[5]):-1;
  uint64_t lo=LO[target],hi=HI[target];
  if(argc>6){ int pg,pm,ps; unsigned long long pseed;
    sscanf(argv[6],"%d,%d,%d,%llu",&pg,&pm,&ps,&pseed);
    uint8_t o[24]; uint64_t l=~0ULL,h=~0ULL; gen_check(pg,pm,ps,pseed,l,h,o);
    lo=0;hi=0; for(int i=0;i<20;i++){uint8_t v=o[i]; if(v<65)lo|=1ULL<<(v-1); else hi|=1ULL<<(v-65);}
    fprintf(stderr,"PLANT %s/%s/%s seed=%llu -> set:",GN[pg],MN[pm],SN[ps],pseed);
    for(int i=0;i<20;i++)fprintf(stderr," %d",o[i]); fprintf(stderr,"\n");
    int pc=0; for(int i=0;i<64;i++)pc+=(lo>>i)&1; for(int i=0;i<16;i++)pc+=(hi>>i)&1;
    fprintf(stderr,"PLANT popcount=%d\n",pc); }
  fprintf(stderr,"target draw idx %d id=%u ts=%u  seeds [%llu,%llu) threads=%d\n",
     target,IDS[target],TS[target],(unsigned long long)A,(unsigned long long)B,NTH);
  for(int g=0;g<G_NGEN;g++){ if(onlyg>=0&&g!=onlyg)continue;
   for(int m=0;m<M_NMOD;m++) for(int s=0;s<S_NS;s++){
    pthread_t th[16];JOB jb[16];
    uint64_t span=(B-A+NTH-1)/NTH;
    for(int t=0;t<NTH;t++){jb[t]=(JOB){A+t*span, (A+(t+1)*span<B)?A+(t+1)*span:B, g,m,s,lo,hi,t,0,0};
      pthread_create(&th[t],0,worker,&jb[t]);}
    int best=0;uint64_t bs=0;
    for(int t=0;t<NTH;t++){pthread_join(th[t],0); if(jb[t].best>best){best=jb[t].best;bs=jb[t].bestseed;}}
    printf("%-14s %-12s %-18s best=%2d/20  seed=%llu\n",GN[g],MN[m],SN[s],best,(unsigned long long)bs);
    fflush(stdout);
   }}
  (void)GBEST;(void)GBSEED;
  return 0;
}
