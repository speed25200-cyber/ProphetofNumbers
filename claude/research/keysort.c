/* keysort.c — les DEUX dernieres facons standard de tirer un 20-sous-ensemble.
 *
 * Le dossier couvre maintenant :
 *   Fisher-Yates avant/arriere, rejet avec saut des doublons, Floyd   -> seedhunt.c
 *   echantillonnage par selection (Knuth 3.4.2 S)                     -> selsamp.c
 *   derangement (unrank d'un entier)                                  -> §6 quater
 * Il en restait deux, toutes deux courantes dans du vrai code :
 *
 *  (A) TRI PAR CLE. On tire une cle par numero (80 sorties), on trie, on garde les 20
 *      plus petites. C'est l'idiome « sort by random key » qu'on ecrit en une ligne dans
 *      la plupart des langages, et c'est aussi la base du tirage pondere.
 *      Elagage : des qu'une cle d'un numero TIRE depasse une cle d'un numero NON TIRE,
 *      la graine est morte — on rejette apres quelques cles, pas apres 80.
 *
 *  (B) ECHANTILLONNAGE PAR RESERVOIR (Knuth algorithme R). On garde 1..20, puis pour
 *      t = 21..80 on tire j dans [0,t) et si j < 20 l'element t remplace res[j].
 *      Elagage : si t EST dans le tirage publie mais que j >= 20, l'element n'entre
 *      jamais dans le reservoir — contradiction immediate.
 *
 *   ./keysort selftest
 *   ./keysort <draws.bin> <first> <nseeds>
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
typedef uint32_t u32; typedef uint64_t u64; typedef unsigned __int128 u128;

enum { G_XOR32, G_MINSTD, G_GLIBC, G_MSVC, G_JAVA, G_PCG32, G_SPLITMIX, G_NGEN };
static const char *GNAME[G_NGEN] =
  {"xorshift32","minstd","glibc_lcg","msvc_lcg","java48","pcg32","splitmix64"};
static const int GSTATE[G_NGEN] = {32, 31, 32, 32, 48, 64, 64};
static const u64 GMOD[G_NGEN] = {1ULL<<32, 2147483647ULL, 1ULL<<31, 1ULL<<15,
                                 1ULL<<32, 1ULL<<32, 0};
typedef struct { u64 s; u32 x; int g; } St;

static void gseed(St *v, int g, u32 seed){
  v->g = g;
  switch(g){
    case G_XOR32:    v->x = seed ? seed : 1u; break;
    case G_MINSTD:   v->x = seed % 2147483647u; if(!v->x) v->x = 1u; break;
    case G_GLIBC: case G_MSVC: v->x = seed; break;
    case G_JAVA:     v->s = ((u64)seed ^ 0x5DEECE66DULL) & ((1ULL<<48)-1); break;
    case G_SPLITMIX: v->s = seed; break;
    case G_PCG32:    v->s = 0;
                     v->s = v->s*6364136223846793005ULL + 1442695040888963407ULL;
                     v->s += (u64)seed;
                     v->s = v->s*6364136223846793005ULL + 1442695040888963407ULL; break;
  }
}
static inline u64 gnext(St *v){
  switch(v->g){
    case G_XOR32: { u32 x = v->x; x^=x<<13; x^=x>>17; x^=x<<5; v->x = x; return x; }
    case G_MINSTD:{ v->x = (u32)(((u64)v->x*48271ULL) % 2147483647ULL); return v->x; }
    case G_GLIBC: { v->x = v->x*1103515245u + 12345u; return v->x >> 1; }
    case G_MSVC:  { v->x = v->x*214013u + 2531011u; return (v->x>>16) & 0x7FFFu; }
    case G_JAVA:  { v->s = (v->s*0x5DEECE66DULL + 0xB) & ((1ULL<<48)-1); return v->s>>16; }
    case G_PCG32: { u64 o = v->s;
                    v->s = o*6364136223846793005ULL + 1442695040888963407ULL;
                    u32 xs = (u32)(((o>>18)^o)>>27), r = (u32)(o>>59);
                    return (u64)((xs>>r)|(xs<<((-r)&31))); }
    default:      { u64 z = (v->s += 0x9E3779B97F4A7C15ULL);
                    z = (z ^ (z>>30)) * 0xBF58476D1CE4E5B9ULL;
                    z = (z ^ (z>>27)) * 0x94D049BB133111EBULL; return z ^ (z>>31); }
  }
}
/* un entier dans [0,k) — les deux reductions usuelles */
static inline u32 rk(int g, u64 u, u32 k, int mulhi){
  if(!mulhi) return (u32)(u % k);
  u128 M = GMOD[g] ? (u128)GMOD[g] : ((u128)1 << 64);
  return (u32)(((u128)u * k) / M);
}

static u32 N; static uint8_t *NUMS;

/* L'appartenance au tirage ne depend PAS de la graine : la recalculer dans la boucle
   interne coutait un memset de 324 octets par appel, 42 fois par graine — c'etait le vrai
   gouffre, pas l'avance morte du generateur. Precalculee une fois ici. */
#define MAXCAP 16
static uint8_t INSET[MAXCAP][81];
static void build_inset(long first, int cap){
  for(int d = 0; d < cap; d++){
    memset(INSET[d], 0, 81);
    const uint8_t *row = NUMS + 20*(size_t)(first + d);
    for(int j = 0; j < 20; j++) INSET[d][row[j]] = 1;
  }
}

/* (A) tri par cle, avec elagage des que l'ordre est viole */
static int match_key(int g, u32 seed, int lead, long first, int cap){
  St v; gseed(&v, g, seed);
  for(int i = 0; i < lead; i++) gnext(&v);
  for(int d = 0; d < cap; d++){
    const uint8_t *in = INSET[d];
    u64 maxDrawn = 0, minUn = ~(u64)0;
    int haveD = 0, haveU = 0, dead = 0;
    for(int t = 1; t <= 80; t++){
      u64 key = gnext(&v);
      if(in[t]){ if(!haveD || key > maxDrawn){ maxDrawn = key; haveD = 1; } }
      else     { if(!haveU || key < minUn   ){ minUn    = key; haveU = 1; } }
      /* pas besoin de consommer les cles restantes : on rend la main tout de suite,
         donc avancer le generateur ne sert a rien. Une premiere version le faisait et
         payait 80 sorties par graine au lieu de ~8 — 19 heures au lieu de deux. */
      if(haveD && haveU && maxDrawn > minUn){ dead = 1; break; }
    }
    if(dead) return d;
  }
  return cap;
}

/* (B) reservoir, algorithme R */
static int match_res(int g, u32 seed, int lead, int mulhi, long first, int cap){
  St v; gseed(&v, g, seed);
  for(int i = 0; i < lead; i++) gnext(&v);
  for(int d = 0; d < cap; d++){
    const uint8_t *row = NUMS + 20*(size_t)(first + d);
    const uint8_t *in = INSET[d];
    uint8_t res[20]; for(int i = 0; i < 20; i++) res[i] = (uint8_t)(i + 1);
    int dead = 0;
    for(u32 t = 21; t <= 80; t++){
      u32 j = rk(g, gnext(&v), t, mulhi);
      if(j < 20) res[j] = (uint8_t)t;
      else if(in[t]){ dead = 1; break; }              /* tire mais jamais entre */
    }
    if(!dead){
      int seen[81]; memset(seen, 0, sizeof seen);
      for(int i = 0; i < 20; i++) seen[res[i]] = 1;
      for(int i = 0; i < 20; i++) if(!seen[row[i]]){ dead = 1; break; }
    }
    if(dead) return d;
  }
  return cap;
}

static void loadbin(const char *fn){
  FILE *f = fopen(fn, "rb"); if(!f || fread(&N,4,1,f)!=1){ perror(fn); exit(1); }
  u32 *ids = malloc(4*(size_t)N), *ts = malloc(4*(size_t)N);
  u64 *lo = malloc(8*(size_t)N), *hi = malloc(8*(size_t)N);
  NUMS = malloc(20*(size_t)N);
  uint8_t *bo = malloc(N), *bn = malloc(N);
  if(fread(ids,4,N,f)!=N||fread(ts,4,N,f)!=N||fread(lo,8,N,f)!=N||fread(hi,8,N,f)!=N||
     fread(NUMS,20,N,f)!=N||fread(bo,1,N,f)!=N||fread(bn,1,N,f)!=N){
    fprintf(stderr,"draws.bin tronque\n"); exit(1); }
  fclose(f);
  for(u32 i = 0; i < N; i++)
    for(int j = 0; j < 20; j++){
      uint8_t x = NUMS[20*(size_t)i+j];
      if(x < 1 || x > 80){ fprintf(stderr,"numero hors 1..80 au tirage %u\n", i); exit(1); }
      if(j && x <= NUMS[20*(size_t)i+j-1]){ fprintf(stderr,"tirage %u non trie\n", i); exit(1); }
    }
}

static int selftest(void){
  printf("selftest : on FABRIQUE des tirages par chaque methode avec une graine connue,\n");
  printf("  puis on la recherche. Un 0 sur l'archive ne vaut rien sans cela.\n\n");
  N = 400; NUMS = malloc(20*(size_t)N);
  int fails = 0;
  const u32 SEED = 55555555u; const int LEAD = 4;
  for(int g = 0; g < G_NGEN; g++){
    /* --- (A) tri par cle --- */
    { St v; gseed(&v, g, SEED);
      for(int i = 0; i < LEAD; i++) gnext(&v);
      for(u32 d = 0; d < N; d++){
        u64 key[81]; for(int t = 1; t <= 80; t++) key[t] = gnext(&v);
        uint8_t idx[80]; for(int t = 0; t < 80; t++) idx[t] = (uint8_t)(t+1);
        for(int a = 1; a < 80; a++){ uint8_t kk = idx[a]; int b = a-1;
          while(b >= 0 && key[idx[b]] > key[kk]){ idx[b+1] = idx[b]; b--; } idx[b+1] = kk; }
        uint8_t row[20]; for(int i = 0; i < 20; i++) row[i] = idx[i];
        for(int a = 1; a < 20; a++){ uint8_t kk = row[a]; int b = a-1;
          while(b >= 0 && row[b] > kk){ row[b+1] = row[b]; b--; } row[b+1] = kk; }
        memcpy(NUMS + 20*(size_t)d, row, 20);
      }
      build_inset(0, 6);
      u32 found = 0; int fl = -1;
      for(u32 s = SEED - 200; s <= SEED + 200 && !found; s++)
        for(int l = 0; l < 8 && !found; l++)
          if(match_key(g, s, l, 0, 6) >= 6){ found = s; fl = l; }
      int ok = (found == SEED && fl == LEAD); fails += !ok;
      printf("  %-11s tri par cle          : %s\n", GNAME[g], ok?"RECOVERED":"FAIL");
    }
    /* --- (B) reservoir --- */
    for(int mulhi = 0; mulhi < 2; mulhi++){
      St v; gseed(&v, g, SEED);
      for(int i = 0; i < LEAD; i++) gnext(&v);
      for(u32 d = 0; d < N; d++){
        uint8_t res[20]; for(int i = 0; i < 20; i++) res[i] = (uint8_t)(i+1);
        for(u32 t = 21; t <= 80; t++){ u32 j = rk(g, gnext(&v), t, mulhi);
          if(j < 20) res[j] = (uint8_t)t; }
        uint8_t row[20]; memcpy(row, res, 20);
        for(int a = 1; a < 20; a++){ uint8_t kk = row[a]; int b = a-1;
          while(b >= 0 && row[b] > kk){ row[b+1] = row[b]; b--; } row[b+1] = kk; }
        memcpy(NUMS + 20*(size_t)d, row, 20);
      }
      build_inset(0, 6);
      u32 found = 0; int fl = -1;
      for(u32 s = SEED - 200; s <= SEED + 200 && !found; s++)
        for(int l = 0; l < 8 && !found; l++)
          if(match_res(g, s, l, mulhi, 0, 6) >= 6){ found = s; fl = l; }
      int ok = (found == SEED && fl == LEAD); fails += !ok;
      printf("  %-11s reservoir %-6s     : %s\n", GNAME[g], mulhi?"mulhi":"mod",
             ok?"RECOVERED":"FAIL");
    }
  }
  /* controle negatif : des tirages SRS equitables */
  u64 z = 0x9911AABBCCDDULL; int worst = 0;
  for(u32 d = 0; d < N; d++){
    uint8_t pool[80]; for(int i = 0; i < 80; i++) pool[i] = (uint8_t)(i+1);
    for(int i = 79; i > 0; i--){ z = z*6364136223846793005ULL+1442695040888963407ULL;
      int j = (int)((z>>33) % (unsigned)(i+1)); uint8_t t = pool[i]; pool[i]=pool[j]; pool[j]=t; }
    uint8_t row[20]; for(int i = 0; i < 20; i++) row[i] = pool[i];
    for(int a = 1; a < 20; a++){ uint8_t kk = row[a]; int b = a-1;
      while(b >= 0 && row[b] > kk){ row[b+1] = row[b]; b--; } row[b+1] = kk; }
    memcpy(NUMS + 20*(size_t)d, row, 20);
  }
  build_inset(0, 6);
  for(int g = 0; g < G_NGEN; g++)
    for(u32 s = 0; s < 30000; s++)
      for(int l = 0; l < 8; l++){
        int a = match_key(g, s, l, 0, 6); if(a > worst) worst = a;
        for(int mh = 0; mh < 2; mh++){ int b = match_res(g, s, l, mh, 0, 6); if(b > worst) worst = b; }
      }
  printf("\n  controle negatif : %d essais sur tirages SRS equitables, meilleur %d/6\n",
         G_NGEN*30000*8*3, worst);
  int nok = (worst == 0); fails += !nok;
  printf("    %s   (un seul tirage reproduit vaut deja 2^-61,6)\n", nok?"PASS":"FAIL");
  printf("\n  %s\n", fails ? "*** CONTROLES ECHOUES ***" : "controles: tous passes");
  return fails ? 1 : 0;
}

int main(int argc, char **argv){
  if(argc > 1 && !strcmp(argv[1], "selftest")) return selftest();
  if(argc < 4){ fprintf(stderr,"usage: %s <draws.bin> <first> <nseeds>\n", argv[0]); return 2; }
  loadbin(argv[1]);
  long first = atol(argv[2]);
  u64 nseeds = strtoull(argv[3], 0, 0);
  const int CAP = 6;
  /* Le decalage initial n'est utile que si le balayage ne couvre PAS tout l'etat.
     Pour un generateur d'etat 32 bits, parcourir les 2^32 graines visite deja chaque
     etat atteignable, donc l'etat obtenu apres L avances est celui d'une AUTRE graine
     du meme balayage : les decalages y sont de la pure redondance. Ils ne servent que
     pour java48, pcg32 et splitmix64, ou l'on balaie des graines et non des etats. */
  #define NLEADS(g) (GSTATE[g] <= 32 ? 1 : 6)
  build_inset(first, CAP);
  printf("archive : %u tirages ; depart %ld\n", N, first);
  printf("architectures : (A) tri par cle 80 sorties  (B) reservoir, algorithme R\n");
  printf("balayage : %llu graines x %d generateurs ; decalages 1 (etat 32 bits, couvert\n"
         "  entierement par les graines) ou 6 (java48, pcg32, splitmix64)\n",
         (unsigned long long)nseeds, G_NGEN);
  printf("  UN SEUL tirage reproduit vaut 2^-61,6 : seuil d'alarme a 1.\n\n");
  fflush(stdout);
  int best = 0; long alarms = 0;
  for(int g = 0; g < G_NGEN; g++){
    int bk = 0;
    for(u64 s = 0; s < nseeds; s++)
      for(int l = 0; l < NLEADS(g); l++){
        int m = match_key(g, (u32)s, l, first, CAP);
        if(m > bk) bk = m;
        if(m >= 1){ printf("  ALARME CLE %s graine=%llu lead=%d : %d tirages\n",
            GNAME[g], (unsigned long long)s, l, m); fflush(stdout); alarms++; }
      }
    printf("  %-11s tri par cle      : meilleur %d/%d%s\n", GNAME[g], bk, CAP,
           GSTATE[g] <= 32 ? "   (etat entierement couvert)" : "   (graines seulement)");
    fflush(stdout);
    if(bk > best) best = bk;
    for(int mh = 0; mh < 2; mh++){
      int br = 0;
      for(u64 s = 0; s < nseeds; s++)
        for(int l = 0; l < NLEADS(g); l++){
          int m = match_res(g, (u32)s, l, mh, first, CAP);
          if(m > br) br = m;
          if(m >= 1){ printf("  ALARME RESERVOIR %s/%s graine=%llu lead=%d : %d tirages\n",
              GNAME[g], mh?"mulhi":"mod", (unsigned long long)s, l, m); fflush(stdout); alarms++; }
        }
      printf("  %-11s reservoir %-6s : meilleur %d/%d\n", GNAME[g], mh?"mulhi":"mod", br, CAP);
      fflush(stdout);
      if(br > best) best = br;
    }
  }
  printf("\nmeilleur %d/%d ; alarmes %ld\n", best, CAP, alarms);
  return 0;
}
