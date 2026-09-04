/* poslll — la meme attaque par reseau que lcg_lll, mais sur l'AUTRE observable.
 *
 * lcg_lll suppose « bonus = premiere boule tiree » : le bonus est alors une sortie brute
 * ramenee sur 1..80, soit 6,32 bits. C'est l'hypothese de l'architecture par MELANGE.
 *
 * Sous l'architecture par DERANGEMENT — celle du paragraphe 6 quater — il n'existe pas de
 * « premiere boule » : le derangement rend les 20 numeros deja tries. Le bonus ne peut
 * alors etre designe que par son INDICE parmi les 20, et c'est cet indice qui est la
 * sortie brute : p = (u*20)>>32, soit 4,32 bits. Observable different, hypothese
 * differente, et aucun des deux ne subsume l'autre.
 *
 * Moins d'information par tirage (4,32 contre 6,32 bits) donc il en faut davantage :
 * l'unicite demande 2^(64/K) < 20, soit K > 14,8, et LLL exige une marge par-dessus.
 * Le controle balaie donc K jusqu'a 40 au lieu de 24.
 *
 *   ./poslll selftest          controles positifs ET negatifs sur donnees synthetiques
 *   ./poslll real [K] [maxW]   balayage de l'archive reelle
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#define MAXN 64
typedef __int128 i128;
typedef unsigned __int128 u128;
static u128 MOD = (u128)1 << 64;
static int MODBITS = 64;   /* 48 for java.util.Random, 64 for the rest */

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
static inline uint64_t mmask(void){ return (MODBITS>=64)? ~0ULL : ((1ULL<<MODBITS)-1); }
static uint64_t powmod(uint64_t a,int e){ uint64_t r=1,b=a&mmask();
  while(e){ if(e&1) r=(r*b)&mmask(); b=(b*b)&mmask(); e>>=1; } return r; }

/* returns 1 if a vector consistent with every |e_d| <= bound is found */
static int hnp(uint64_t A, const uint64_t*cen, int K, u128 bound){
  int n=K+1; NDIM=n;
  static uint64_t Dc[MAXN], beta[MAXN];
  for(int d=0; d<K; d++) Dc[d] = (cen[d+1]-cen[d]) & mmask();
  for(int d=1; d<K; d++) beta[d-1] = (powmod(A,d)*Dc[0] - Dc[d]) & mmask();
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
  /* u = the 32-bit output taken from the top of the state; bonus-1 = (u*k)>>32 pins u
     to [l,h), and the state's remaining low bits (MODBITS-32 of them) are free. */
  u128 a=((u128)j<<32), b=((u128)(j+1)<<32);
  uint64_t l=(uint64_t)(a/k) + ((a%k)?1:0), h=(uint64_t)(b/k) + ((b%k)?1:0);
  int sh = MODBITS-32;
  *lo=(uint64_t)l<<sh; *hi=((uint64_t)h<<sh);
}
static uint64_t centre_from_pos(int p){
  uint64_t lo,hi; interval((uint32_t)p,20,&lo,&hi); return lo + ((hi-lo)>>1);
}
static const uint64_t MULT[]={6364136223846793005ULL,2862933555777941757ULL,3202034522624059733ULL,
  3935559000370003845ULL,1181783497276652981ULL,0xda942042e4dd58b5ULL,25214903917ULL,
  1103515245ULL,214013ULL,1664525ULL,0x27BB2EE687B0B0FDULL,6364136223846793005ULL,
  0x5851F42D4C957F2DULL,44485709377909ULL,0x2545F4914F6CDD1DULL,0xff1cd035ULL};
static const char*MNAME[]={"MMIX / PCG","L'Ecuyer a","L'Ecuyer b","L'Ecuyer c","ranqd1-64",
  "Lehmer64","drand48","glibc LCG","MSVC","Numerical Recipes","Knuth 64","PCG-XSL-RR",
  "PCG32 mult","CMRG","xorshift* mult","Borland"};
#define NMULT 16

/* le flux des positions, ecrit par bonusline.py */
static long NP; static unsigned char *PP;
static void loadpos(const char*f){
  FILE*h=fopen(f,"rb"); if(!h){perror(f);exit(1);}
  fseek(h,0,SEEK_END); NP=ftell(h); fseek(h,0,SEEK_SET);
  PP=malloc(NP); if(fread(PP,1,NP,h)!=(size_t)NP){fprintf(stderr,"short read\n");exit(1);}
  fclose(h);
  for(long i=0;i<NP;i++) if(PP[i]>19){fprintf(stderr,"position %d hors 0..19 en %ld\n",PP[i],i);exit(1);}
}

int main(int argc,char**argv){
  const char*mode = argc>1?argv[1]:"selftest";
  for(int i=1;i<argc;i++) if(!strcmp(argv[i],"m48")){ MODBITS=48; MOD=(u128)1<<48; }
  uint64_t lo,hi; interval(0,20,&lo,&hi); u128 bound=(u128)(hi-lo);

  if(!strcmp(mode,"selftest")){
    uint64_t a = (MODBITS==48)? 25214903917ULL : 6364136223846793005ULL;
    uint64_t c = (MODBITS==48)? 11ULL : 1442695040888963407ULL; int W=21;
    printf("selftest: LCG synthetique mod 2^%d (%s), W=%d, observable = INDICE du bonus\n",
           MODBITS, MODBITS==48?"java.util.Random":"MMIX", W);
    printf("  4,32 bits par tirage au lieu de 6,32 : il faut plus de contraintes.\n");
    printf("  controles positifs ET negatifs, tous deux exiges avant tout passage reel\n\n");
    int usable_at = 0;
    for(int K=12;K<=40;K+=4){
      static uint64_t cen[MAXN]; uint64_t s=0xC0FFEE1234567890ULL & mmask();
      for(int d=0;d<=K;d++){ uint32_t u=(uint32_t)(s>>(MODBITS-32));
        uint32_t j=(uint32_t)(((uint64_t)u*20)>>32);
        cen[d]=centre_from_pos((int)j);
        for(int t=0;t<W;t++) s=(a*s+c)&mmask(); }
      int good=hnp(powmod(a,W),cen,K,bound);
      int badW=hnp(powmod(a,W+1),cen,K,bound);
      int badA=hnp(powmod((MODBITS==48)?1103515245ULL:2862933555777941757ULL,W),cen,K,bound);
      static uint64_t rnd[MAXN]; uint64_t z=1;
      for(int d=0;d<=K;d++){ z=(z*6364136223846793005ULL+1442695040888963407ULL)&mmask();
        rnd[d]=centre_from_pos((int)((z>>59)%20)); }
      int badD=hnp(powmod(a,W),rnd,K,bound);
      /* « recupere » ne suffit pas : un K qui retrouve l'etat MAIS accepte aussi un
         mauvais W, un mauvais multiplicateur ou des positions aleatoires n'a aucune valeur
         de preuve. Le K utilisable est le plus petit qui reussit le controle positif ET
         rejette les trois controles negatifs. */
      if(good && !badW && !badA && !badD && !usable_at) usable_at = K;
      printf("  K=%2d  bons a,W: %-10s | mauvais W: %-9s | mauvais a: %-9s | positions aleatoires: %s\n",
        K, good?"RECOVERED":"manque", badW?"faux positif":"rejete",
        badA?"faux positif":"rejete", badD?"faux positif":"rejete");
    }
    printf("\n  %s\n", usable_at ? "controles passes"
                                 : "*** CONTROLE ECHOUE : aucun K ne separe le vrai du faux ***");
    if(usable_at)
      printf("  plus petit K UTILISABLE (recupere et rejette les trois faux) : %d\n"
             "  la borne d'unicite theorique en donne 15 ; en dessous de %d l'attaque\n"
             "  accepte aussi les mauvaises hypotheses, donc n'y rien lire.\n", usable_at, usable_at);
    return usable_at ? 0 : 1;
  }

  loadpos(argc>4?argv[4]:"bonuspos.bin");
  int K=argc>2?atoi(argv[2]):28, maxW=argc>3?atoi(argv[3]):48;
  long starts[]={0,5000,20000,50000,NP-K-2};
  printf("archive : %ld positions ; K=%d contraintes, W balaye 1..%d, 5 points de depart\n",
         NP,K,maxW);
  printf("  hypothese : indice du bonus = (u*20)>>32, u = poids fort d'un LCG mod 2^%d,\n", MODBITS);
  printf("  increment elimine par differenciation\n\n");
  int total=0;
  for(int m=0;m<NMULT;m++){
    int found=0;
    for(int W=1;W<=maxW;W++){
      uint64_t A=powmod(MULT[m],W);
      for(int si=0;si<5;si++){ long st=starts[si];
        static uint64_t cen[MAXN];
        for(int d=0;d<=K;d++) cen[d]=centre_from_pos(PP[st+d]);
        if(hnp(A,cen,K,bound)){ printf("  !!! TOUCHE %s W=%d depart=%ld\n",MNAME[m],W,st); found++; }
      }
    }
    printf("  %-20s a=%-22llu %s\n",MNAME[m],(unsigned long long)MULT[m],
           found?"VOIR CI-DESSUS":"aucun ajustement, quel que soit W");
    total+=found;
  }
  printf("\n  total : %d  ->  %s\n",total,
     total?"A INSTRUIRE":"aucun LCG 64 bits a multiplicateur standard ne colle a l'archive");
  return 0;
}
