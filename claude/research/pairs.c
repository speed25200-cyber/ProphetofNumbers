// All-pairs overlap distribution over 70560 draws  (~2.5e9 pairs) - birthday/collision test
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <pthread.h>
static uint32_t N,*IDS,*TS; static uint64_t *LO,*HI;
typedef struct{uint32_t a,b;long long h[21];int maxk;uint32_t mi,mj;} JOB;
static void* w(void*p){ JOB*j=(JOB*)p; for(int i=0;i<21;i++)j->h[i]=0; j->maxk=0;
  for(uint32_t i=j->a;i<j->b;i++){uint64_t l=LO[i],h=HI[i];
    for(uint32_t k=i+1;k<N;k++){int c=__builtin_popcountll(l&LO[k])+__builtin_popcountll(h&HI[k]);
      j->h[c]++; if(c>j->maxk){j->maxk=c;j->mi=i;j->mj=k;}}}
  return 0;}
int main(int argc,char**argv){
  FILE*f=fopen("draws.bin","rb");
  if(fread(&N,4,1,f)!=1)return 1; IDS=malloc(4*N);TS=malloc(4*N);LO=malloc(8*N);HI=malloc(8*N);
  if(fread(IDS,4,N,f)!=N)return 1; if(fread(TS,4,N,f)!=N)return 1;
  if(fread(LO,8,N,f)!=N)return 1; if(fread(HI,8,N,f)!=N)return 1; fclose(f);
  int T=4; pthread_t th[8];JOB jb[8];
  // balance: work for start i is (N-i); split by equal area
  double tot=(double)N*(N-1)/2; uint32_t prev=0;
  for(int t=0;t<T;t++){ double target=tot*(t+1)/T; uint32_t x=prev;
    while(x<N && (double)(N-1+N-x)*(x)/2.0 < target) x++;   /* area of first x rows */
    jb[t].a=prev; jb[t].b=(t==T-1)?N:x; prev=jb[t].b;
    pthread_create(&th[t],0,w,&jb[t]); }
  long long H[21]={0}; int mk=0;uint32_t mi=0,mj=0;
  for(int t=0;t<T;t++){pthread_join(th[t],0); for(int i=0;i<21;i++)H[i]+=jb[t].h[i];
    if(jb[t].maxk>mk){mk=jb[t].maxk;mi=jb[t].mi;mj=jb[t].mj;}}
  double C[21]; // hypergeometric expected
  double lC80=0; for(int i=0;i<20;i++) lC80+=log(80.0-i)-log(i+1.0);
  long long tot2=0; for(int i=0;i<21;i++)tot2+=H[i];
  printf("total pairs = %lld  (expect %.0f)\n",tot2,tot);
  printf(" k   observed        expected        z\n");
  for(int k=0;k<21;k++){
    double lp=0; for(int i=0;i<k;i++)lp+=log(20.0-i)-log(i+1.0);
    for(int i=0;i<20-k;i++)lp+=log(60.0-i)-log(i+1.0);
    lp-=lC80; double e=tot*exp(lp); C[k]=e;
    if(e>1e-9||H[k]>0) printf("%3d %12lld %16.3f  %+8.2f\n",k,H[k],e,(H[k]-e)/(e>0?sqrt(e):1));
  }
  printf("MAX overlap = %d  between draws idx %u (id %u) and %u (id %u), lag=%d\n",
     mk,mi,IDS[mi],mj,IDS[mj],(int)(mj-mi));
  return 0;
}
