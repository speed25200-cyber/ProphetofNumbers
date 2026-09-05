/* selsamp.c — la TROISIEME architecture : l'echantillonnage par selection (Knuth 3.4.2 S).
 *
 * Le dossier a traite deux facons de fabriquer un tirage 20/80 :
 *   - le MELANGE (Fisher-Yates puis tri)        -> §6 bis, shufbias
 *   - le DERANGEMENT (unrank d'un entier)       -> §6 quater
 * Il en existe une troisieme, et elle est la plus naturelle pour un operateur qui publie
 * des numeros tries, parce qu'elle les produit DEJA TRIES sans aucun tri :
 *
 *   m = 0
 *   pour t = 1..80 :  u = next()
 *                     si (80-t+1)*u < (20-m)*M  alors selectionner t, m++
 *                     si m == 20 : arreter
 *
 * Ce qui la rend attaquable : le seuil de CHAQUE appel se calcule entierement a partir du
 * tirage publie. Un tirage donne donc jusqu'a 80 contraintes d'intervalle sur 80 sorties
 * consecutives — pas 4 bits, mais 61,6 repartis sur 80 comparaisons dont je connais
 * chaque seuil. Et une graine fausse meurt vite : la probabilite d'accord par contrainte
 * vaut theta^2 + (1-theta)^2 = 0,625 pour theta = 1/4, donc ~2,7 contraintes examinees.
 *
 * Le nombre d'appels par tirage est variable mais CONNU : c'est n20 si l'implementation
 * s'arrete des les 20 trouves, 80 sinon. Les deux variantes sont balayees.
 *
 *   ./selsamp selftest
 *   ./selsamp <draws.bin> <first> <nseeds> <report_at>
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
typedef uint32_t u32; typedef uint64_t u64; typedef unsigned __int128 u128;

enum { G_XOR32, G_MINSTD, G_GLIBC, G_MSVC, G_JAVA, G_PCG32, G_SPLITMIX, G_NGEN };
static const char *GNAME[G_NGEN] =
  {"xorshift32","minstd","glibc_lcg","msvc_lcg","java48","pcg32","splitmix64"};
static const int GSTATE[G_NGEN] = {32, 31, 32, 32, 48, 64, 64};
static const u64 GMOD[G_NGEN] = {1ULL<<32, 2147483647ULL, 1ULL<<31, 1ULL<<15,
                                 1ULL<<32, 1ULL<<32, 0 /* 2^64 */};
typedef struct { u64 s; u32 x; int g; } St;

static void gseed(St *st, int g, u32 seed){
  st->g = g;
  switch(g){
    case G_XOR32:    st->x = seed ? seed : 1u; break;
    case G_MINSTD:   st->x = seed % 2147483647u; if(!st->x) st->x = 1u; break;
    case G_GLIBC: case G_MSVC: st->x = seed; break;
    case G_JAVA:     st->s = ((u64)seed ^ 0x5DEECE66DULL) & ((1ULL<<48)-1); break;
    case G_SPLITMIX: st->s = seed; break;
    case G_PCG32:    st->s = 0;
                     st->s = st->s * 6364136223846793005ULL + 1442695040888963407ULL;
                     st->s += (u64)seed;
                     st->s = st->s * 6364136223846793005ULL + 1442695040888963407ULL;
                     break;
  }
}
static inline u64 gnext(St *st){
  switch(st->g){
    case G_XOR32: { u32 x = st->x; x ^= x<<13; x ^= x>>17; x ^= x<<5; st->x = x; return x; }
    case G_MINSTD:{ st->x = (u32)(((u64)st->x * 48271ULL) % 2147483647ULL); return st->x; }
    case G_GLIBC: { st->x = st->x * 1103515245u + 12345u; return st->x >> 1; }
    case G_MSVC:  { st->x = st->x * 214013u + 2531011u; return (st->x >> 16) & 0x7FFFu; }
    case G_JAVA:  { st->s = (st->s * 0x5DEECE66DULL + 0xB) & ((1ULL<<48)-1); return st->s >> 16; }
    case G_PCG32: { u64 o = st->s;
                    st->s = o * 6364136223846793005ULL + 1442695040888963407ULL;
                    u32 xs = (u32)(((o >> 18) ^ o) >> 27), r = (u32)(o >> 59);
                    return (u64)((xs >> r) | (xs << ((-r) & 31))); }
    default:      { u64 z = (st->s += 0x9E3779B97F4A7C15ULL);
                    z = (z ^ (z>>30)) * 0xBF58476D1CE4E5B9ULL;
                    z = (z ^ (z>>27)) * 0x94D049BB133111EBULL; return z ^ (z>>31); }
  }
}
/* u/M < a/b   <=>   u*b < a*M   ; en 128 bits pour ne rien perdre */
static inline int below(int g, u64 u, int a, int b){
  u128 M = GMOD[g] ? (u128)GMOD[g] : ((u128)1 << 64);
  return (u128)u * (unsigned)b < (u128)(unsigned)a * M;
}

static u32 N; static uint8_t *NUMS;      /* 20 numeros tries par tirage */

/* combien de tirages consecutifs cette graine reproduit-elle exactement ? */
static int match_draws(int g, u32 seed, int lead, int full80, long first, int cap){
  St st; gseed(&st, g, seed);
  for(int i = 0; i < lead; i++) gnext(&st);
  for(int d = 0; d < cap; d++){
    const uint8_t *row = NUMS + 20 * (size_t)(first + d);
    int m = 0, next = 0, done = 0;
    for(int t = 1; t <= 80 && !done; t++){
      u64 u = gnext(&st);
      int sel = below(g, u, 20 - m, 80 - t + 1);
      int obs = (next < 20 && row[next] == t);
      if(sel != obs) return d;
      if(sel){ m++; next++;
        if(m == 20){ if(full80) for(int q = t + 1; q <= 80; q++) gnext(&st); done = 1; } }
    }
    if(m != 20) return d;
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
      uint8_t v = NUMS[20*(size_t)i+j];
      if(v < 1 || v > 80){ fprintf(stderr,"numero %d hors 1..80 au tirage %u\n", v, i); exit(1); }
      if(j && v <= NUMS[20*(size_t)i+j-1]){ fprintf(stderr,"tirage %u non trie\n", i); exit(1); }
    }
}

static int selftest(void){
  printf("selftest : on FABRIQUE des tirages par l'algorithme S avec une graine connue,\n");
  printf("  puis on la recherche. Un 0 sur l'archive ne vaut rien sans cela.\n\n");
  N = 400; NUMS = malloc(20*(size_t)N);
  int fails = 0;
  for(int g = 0; g < G_NGEN; g++)
    for(int full80 = 0; full80 < 2; full80++){
      const u32 SEED = 987654321u; const int LEAD = 3;
      St st; gseed(&st, g, SEED);
      for(int i = 0; i < LEAD; i++) gnext(&st);
      int built = 1;
      for(u32 d = 0; d < N && built; d++){
        int m = 0, done = 0;
        for(int t = 1; t <= 80 && !done; t++){
          u64 u = gnext(&st);
          if(below(g, u, 20 - m, 80 - t + 1)){ NUMS[20*(size_t)d + m] = (uint8_t)t; m++;
            if(m == 20){ if(full80) for(int q = t + 1; q <= 80; q++) gnext(&st); done = 1; } }
        }
        if(m != 20) built = 0;
      }
      if(!built){ printf("  %-11s %-7s : construction impossible\n", GNAME[g], full80?"full80":"early"); fails++; continue; }
      u32 found = 0; int fl = -1, best = 0;
      for(u32 s = SEED - 200; s <= SEED + 200 && !found; s++)
        for(int lead = 0; lead < 6 && !found; lead++){
          int m2 = match_draws(g, s, lead, full80, 0, 8);
          if(m2 > best) best = m2;
          if(m2 >= 8){ found = s; fl = lead; }
        }
      int ok = (found == SEED && fl == LEAD);
      fails += !ok;
      printf("  %-11s %-7s : %s  (graine %u, lead %d ; meilleur %d/8)\n",
             GNAME[g], full80?"full80":"early", ok?"RECOVERED":"FAIL     ", found, fl, best);
    }
  /* controle negatif : des tirages SRS equitables ne doivent rien donner */
  u64 z = 0x1234567890ABCDEFULL; int worst = 0;
  for(u32 d = 0; d < N; d++){
    uint8_t pool[80]; for(int i = 0; i < 80; i++) pool[i] = (uint8_t)(i+1);
    for(int i = 79; i > 0; i--){ z = z*6364136223846793005ULL+1442695040888963407ULL;
      int j = (int)((z>>33) % (unsigned)(i+1)); uint8_t tmp = pool[i]; pool[i] = pool[j]; pool[j] = tmp; }
    uint8_t row[20]; for(int i = 0; i < 20; i++) row[i] = pool[i];
    for(int i = 1; i < 20; i++){ uint8_t k = row[i]; int j = i-1;
      while(j >= 0 && row[j] > k){ row[j+1] = row[j]; j--; } row[j+1] = k; }
    memcpy(NUMS + 20*(size_t)d, row, 20);
  }
  for(int g = 0; g < G_NGEN; g++)
    for(int full80 = 0; full80 < 2; full80++)
      for(u32 s = 0; s < 40000; s++)
        for(int lead = 0; lead < 6; lead++){
          int m2 = match_draws(g, s, lead, full80, 0, 8);
          if(m2 > worst) worst = m2;
        }
  printf("\n  controle negatif : tirages SRS equitables, %d essais, meilleur %d/8\n",
         G_NGEN*2*40000*6, worst);
  int nok = (worst == 0);
  fails += !nok;
  printf("    %s\n", nok ? "PASS" : "FAIL (un tirage entier reproduit par hasard)");
  printf("\n  %s\n", fails ? "*** CONTROLES ECHOUES ***" : "controles: tous passes");
  return fails ? 1 : 0;
}

int main(int argc, char **argv){
  if(argc > 1 && !strcmp(argv[1], "selftest")) return selftest();
  if(argc < 5){ fprintf(stderr,"usage: %s <draws.bin> <first> <nseeds> <report_at>\n", argv[0]); return 2; }
  loadbin(argv[1]);
  long first = atol(argv[2]);
  u64 nseeds = strtoull(argv[3], 0, 0);
  int report = atoi(argv[4]);
  const int CAP = 8, LEADS = 6;
  printf("archive : %u tirages ; depart au tirage %ld\n", N, first);
  printf("architecture : echantillonnage par selection (Knuth 3.4.2 S) — les 20 numeros\n");
  printf("  sortent deja tries, un appel par candidat, seuil connu a chaque appel\n");
  printf("balayage : %llu graines x %d generateurs x 2 variantes d'arret x %d leads\n",
         (unsigned long long)nseeds, G_NGEN, LEADS);
  double trials = (double)nseeds * G_NGEN * 2 * LEADS;
  printf("essais : %.4g ; un seul tirage reproduit vaut 2^-61,6 par essai, donc le\n", trials);
  printf("  hasard en attend %.3e\n\n", trials * pow(2.0, -61.617));
  fflush(stdout);
  int best = 0; long alarms = 0;
  for(int g = 0; g < G_NGEN; g++){
    for(int full80 = 0; full80 < 2; full80++){
      int gbest = 0;
      for(u64 s = 0; s < nseeds; s++)
        for(int lead = 0; lead < LEADS; lead++){
          int m = match_draws(g, (u32)s, lead, full80, first, CAP);
          if(m > gbest) gbest = m;
          if(m >= report){
            printf("  ALARME %s/%s graine=%llu lead=%d : %d tirages entiers\n",
                   GNAME[g], full80?"full80":"early", (unsigned long long)s, lead, m);
            fflush(stdout); alarms++;
          }
        }
      if(gbest > best) best = gbest;
      printf("  %-11s %-7s : meilleur %d / %d%s\n", GNAME[g], full80?"full80":"early",
             gbest, CAP, GSTATE[g] <= 32 ? "   (etat entierement couvert)" : "   (graines seulement)");
      fflush(stdout);
    }
  }
  printf("\nmeilleur global %d ; alarmes %ld\n", best, alarms);
  return 0;
}
