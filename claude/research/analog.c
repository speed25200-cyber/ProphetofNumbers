/* analog — nonparametric out-of-sample test: does a similar past predict a similar future?
 *
 * The score test and the logistic model are linear in their features. This one is not:
 * for each held-out draw it finds the historical draws whose context (the previous one
 * or two draws) most resembles the current context, pools what actually followed them,
 * and plays the numbers that came up most often. Any local structure at all — a
 * conditional bias, an attractor, a repeating pattern the linear tests average away —
 * would show up as a hit rate above 25%.
 *
 *   ./analog [k_neighbours] [k_picks] [test_draws] [context_lags]
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
static uint32_t N,*IDS,*TS; static uint64_t *LO,*HI; static uint8_t *NUMS;
static inline int ov(uint32_t a,uint32_t b){
  return __builtin_popcountll(LO[a]&LO[b])+__builtin_popcountll(HI[a]&HI[b]); }

int main(int argc,char**argv){
  FILE*f=fopen("draws.bin","rb"); if(!f||fread(&N,4,1,f)!=1){perror("draws.bin");return 1;}
  IDS=malloc(4*N);TS=malloc(4*N);LO=malloc(8*N);HI=malloc(8*N);
  uint8_t*BO=malloc(N),*BN=malloc(N); NUMS=malloc(20*N);
  if(fread(IDS,4,N,f)!=N||fread(TS,4,N,f)!=N||fread(LO,8,N,f)!=N||fread(HI,8,N,f)!=N||
     fread(NUMS,20,N,f)!=N||fread(BO,1,N,f)!=N||fread(BN,1,N,f)!=N){fprintf(stderr,"short read\n");return 1;}
  fclose(f);
  int KN=argc>1?atoi(argv[1]):400, KP=argc>2?atoi(argv[2]):10;
  int NT=argc>3?atoi(argv[3]):8000, LAGS=argc>4?atoi(argv[4]):2;
  uint32_t split=N-NT;
  printf("analog test: %d neighbours, %d picks, %d held-out draws, %d-draw context\n",
     KN,KP,NT,LAGS);
  printf("  training pool = draws 0..%u ; nothing after the split is ever consulted\n\n",split-1);
  long hits=0, anti=0; double score[80];
  int *sim=malloc(sizeof(int)*N);
  for(uint32_t t=split;t<N;t++){
    /* similarity of every past context to the current one */
    for(uint32_t q=LAGS;q<split;q++){
      int s=0; for(int L=1;L<=LAGS;L++) s+=ov(q-L,t-L);
      sim[q]=s;
    }
    /* pick the KN most similar without a full sort: threshold from a counting pass */
    int cnt[41]; memset(cnt,0,sizeof cnt);
    for(uint32_t q=LAGS;q<split;q++) cnt[sim[q]]++;
    int thr=40,acc=0; while(thr>0 && acc+cnt[thr]<=KN){acc+=cnt[thr];thr--;}
    memset(score,0,sizeof score); int used=0;
    for(uint32_t q=LAGS;q<split && used<KN;q++) if(sim[q]>=thr){
      for(int j=0;j<20;j++) score[NUMS[(size_t)q*20+j]-1]+=1.0;
      used++; }
    /* play the KP most frequent successors of the analogues */
    int idx[80]; for(int i=0;i<80;i++) idx[i]=i;
    for(int a=0;a<KP;a++){ int best=a;
      for(int b=a+1;b<80;b++) if(score[idx[b]]>score[idx[best]]) best=b;
      int tmp=idx[a];idx[a]=idx[best];idx[best]=tmp; }
    for(int a=79;a>=80-KP;a--){ int worst=a;
      for(int b=0;b<a;b++) if(score[idx[b]]<score[idx[worst]]) worst=b;
      int tmp=idx[a];idx[a]=idx[worst];idx[worst]=tmp; }
    for(int a=0;a<KP;a++){ uint8_t v=idx[a]+1;
      if(v<65){ if((LO[t]>>(v-1))&1ULL) hits++; } else { if((HI[t]>>(v-65))&1ULL) hits++; } }
    for(int a=80-KP;a<80;a++){ uint8_t v=idx[a]+1;
      if(v<65){ if((LO[t]>>(v-1))&1ULL) anti++; } else { if((HI[t]>>(v-65))&1ULL) anti++; } }
  }
  double mu=(double)NT*KP*0.25;
  double sd=sqrt((double)NT*KP*0.25*0.75*(80.0-KP)/79.0);
  printf("  analogue picks : %ld hits, expected %.1f, z = %+.2f   (%.4f per draw vs %.4f)\n",
     hits,mu,(hits-mu)/sd,(double)hits/NT,KP*0.25);
  printf("  anti-picks     : %ld hits, expected %.1f, z = %+.2f\n",anti,mu,(anti-mu)/sd);
  printf("\n  a real local structure would separate the two; chance keeps them together.\n");
  return 0;
}
