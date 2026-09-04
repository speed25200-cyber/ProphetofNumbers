/* rank128.c — le rang tire sur 128 BITS, l'implementation la plus probable et non couverte.
 *
 * Tous les outils de rang du dossier supposent que le rang vient d'UNE sortie 64 bits :
 * soit u mod C avec rejet, soit Lemire (u*C)>>64. Or C(80,20) = 2^61,617 est proche de
 * 2^64, donc le rejet frappe 4,1 % des tirages et un implementeur soigneux l'evite
 * autrement : il prend DEUX sorties 64 bits consecutives, les concatene en 128 bits, et
 * reduit. Le biais tombe alors a 2^-66,4 — indetectable, et c'est le bon choix technique.
 *
 * C'est donc l'implementation qu'un operateur competent ecrirait, et aucun outil du
 * dossier ne la couvrait. rankw32 fait DEUX MOTS DE 32 bits, ce qui est autre chose :
 * la valeur y reste sur 64 bits et le rejet reste necessaire.
 *
 * Quatre facons de composer les deux mots (ordre des mots x reduction) :
 *   (hi<<64)|lo  et  (lo<<64)|hi        — l'ordre depend de l'implementation
 *   mod C        et  Lemire 256 bits    — les deux reductions non biaisees
 *
 *   ./rank128 selftest
 *   ./rank128 <rank.bin> <nseeds>
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
typedef uint32_t u32; typedef uint64_t u64; typedef unsigned __int128 u128;

static const u64 CC = 3535316142212174320ULL;      /* C(80,20) */

enum { G_XOR64, G_SPLITMIX, G_LCG_MMIX, G_PCG32, G_XOSHIRO, G_JAVA, G_MINSTD, G_NGEN };
static const char *GNAME[G_NGEN] =
  {"xorshift64","splitmix64","lcg64_mmix","pcg32","xoshiro256ss","java48","minstd"};
static const int GSTATE[G_NGEN] = {64, 64, 64, 64, 256, 48, 31};

typedef struct { u64 s, t[4]; u32 x; int g; } St;

static void gseed(St *v, int g, u32 seed){
  v->g = g;
  switch(g){
    case G_XOR64:    v->s = seed ? (u64)seed : 1; break;
    case G_SPLITMIX: v->s = seed; break;
    case G_LCG_MMIX: v->s = seed; break;
    case G_PCG32:    v->s = 0;
                     v->s = v->s*6364136223846793005ULL + 1442695040888963407ULL;
                     v->s += seed;
                     v->s = v->s*6364136223846793005ULL + 1442695040888963407ULL; break;
    case G_XOSHIRO: { u64 z = seed;                 /* amorcage splitmix, l'usage standard */
                      for(int i = 0; i < 4; i++){
                        z += 0x9E3779B97F4A7C15ULL; u64 w = z;
                        w = (w ^ (w>>30)) * 0xBF58476D1CE4E5B9ULL;
                        w = (w ^ (w>>27)) * 0x94D049BB133111EBULL;
                        v->t[i] = w ^ (w>>31);
                      } break; }
    case G_JAVA:     v->s = ((u64)seed ^ 0x5DEECE66DULL) & ((1ULL<<48)-1); break;
    case G_MINSTD:   v->x = seed % 2147483647u; if(!v->x) v->x = 1; break;
  }
}
static inline u64 rotl(u64 x, int k){ return (x<<k)|(x>>(64-k)); }
static inline u64 gnext(St *v){
  switch(v->g){
    case G_XOR64:    { u64 x = v->s; x^=x<<13; x^=x>>7; x^=x<<17; v->s = x; return x; }
    case G_SPLITMIX: { u64 z = (v->s += 0x9E3779B97F4A7C15ULL);
                       z = (z ^ (z>>30)) * 0xBF58476D1CE4E5B9ULL;
                       z = (z ^ (z>>27)) * 0x94D049BB133111EBULL; return z ^ (z>>31); }
    case G_LCG_MMIX: { v->s = v->s*6364136223846793005ULL + 1442695040888963407ULL; return v->s; }
    case G_PCG32:    { /* deux sorties 32 bits assemblees en un mot 64 */
                       u64 o = v->s; v->s = o*6364136223846793005ULL + 1442695040888963407ULL;
                       u32 xs = (u32)(((o>>18)^o)>>27), r = (u32)(o>>59);
                       u64 a = (u64)((xs>>r)|(xs<<((-r)&31)));
                       o = v->s; v->s = o*6364136223846793005ULL + 1442695040888963407ULL;
                       xs = (u32)(((o>>18)^o)>>27); r = (u32)(o>>59);
                       u64 b = (u64)((xs>>r)|(xs<<((-r)&31)));
                       return (a<<32)|b; }
    case G_XOSHIRO:  { u64 *s = v->t, r = rotl(s[1]*5, 7)*9, t = s[1]<<17;
                       s[2]^=s[0]; s[3]^=s[1]; s[1]^=s[2]; s[0]^=s[3]; s[2]^=t;
                       s[3] = rotl(s[3], 45); return r; }
    case G_JAVA:     { u64 a, b;
                       v->s = (v->s*0x5DEECE66DULL + 0xB) & ((1ULL<<48)-1); a = v->s>>16;
                       v->s = (v->s*0x5DEECE66DULL + 0xB) & ((1ULL<<48)-1); b = v->s>>16;
                       return (a<<32)|(b & 0xFFFFFFFFULL); }
    default:         { u64 a, b;
                       v->x = (u32)(((u64)v->x*48271ULL) % 2147483647ULL); a = v->x;
                       v->x = (u32)(((u64)v->x*48271ULL) % 2147483647ULL); b = v->x;
                       return (a<<33)|(b<<2); }
  }
}

/* les 128 bits hauts d'un produit 128 x 64 — la reduction de Lemire portee en 256 bits */
static inline u64 lemire128(u128 u, u64 c){
  u64 ul = (u64)u, uh = (u64)(u >> 64);
  u128 lo = (u128)ul * c;                 /* contribution basse */
  u128 hi = (u128)uh * c;                 /* contribution haute, decalee de 64 */
  u128 mid = hi + (lo >> 64);
  return (u64)(mid >> 64);                /* = floor(u*c / 2^128) */
}

static inline u64 mk(u128 u, int mode){
  return mode ? lemire128(u, CC) : (u64)(u % (u128)CC);
}

static u64 *RANK; static long NR;

/* combien de rangs consecutifs cette graine reproduit-elle ? */
static int match(int g, u32 seed, int stride, int order, int mode, int cap){
  St v; gseed(&v, g, seed);
  for(int k = 0; k < cap; k++){
    u64 a = gnext(&v), b = gnext(&v);
    u128 u = order ? (((u128)b << 64) | a) : (((u128)a << 64) | b);
    if(mk(u, mode) != RANK[k]) return k;
    for(int j = 2; j < stride; j++) gnext(&v);
  }
  return cap;
}

static int selftest(void){
  printf("selftest : on FABRIQUE des rangs 128 bits avec une graine connue, dans les\n");
  printf("  quatre compositions, puis on la recherche. Sans cela un 0 ne vaut rien.\n\n");
  NR = 32; RANK = malloc(NR * 8);
  int fails = 0;
  for(int g = 0; g < G_NGEN; g++)
    for(int order = 0; order < 2; order++)
      for(int mode = 0; mode < 2; mode++){
        const u32 SEED = 1234567u; const int STRIDE = 2;
        St v; gseed(&v, g, SEED);
        for(long k = 0; k < NR; k++){
          u64 a = gnext(&v), bq = gnext(&v);
          u128 u = order ? (((u128)bq << 64) | a) : (((u128)a << 64) | bq);
          RANK[k] = mk(u, mode);
          for(int j = 2; j < STRIDE; j++) gnext(&v);
        }
        u32 found = 0; int fs = 0;
        for(u32 s = SEED - 300; s <= SEED + 300 && !found; s++)
          for(int st = 2; st <= 8 && !found; st++)
            if(match(g, s, st, order, mode, 8) >= 8){ found = s; fs = st; }
        int ok = (found == SEED && fs == STRIDE);
        fails += !ok;
        printf("  %-12s %-9s %-6s : %s\n", GNAME[g], order?"(lo|hi)":"(hi|lo)",
               mode?"lemire":"mod", ok ? "RECOVERED" : "FAIL");
      }
  /* controle negatif : des rangs aleatoires ne doivent rien donner */
  u64 z = 0xC0FFEE99ULL; int worst = 0;
  for(long k = 0; k < NR; k++){ z = z*6364136223846793005ULL + 1; RANK[k] = (z>>2) % CC; }
  for(int g = 0; g < G_NGEN; g++)
    for(int order = 0; order < 2; order++)
      for(int mode = 0; mode < 2; mode++)
        for(u32 s = 0; s < 40000; s++)
          for(int st = 2; st <= 8; st++){
            int m = match(g, s, st, order, mode, 8);
            if(m > worst) worst = m;
          }
  printf("\n  controle negatif : %d essais sur des rangs aleatoires, meilleur %d/8\n",
         G_NGEN*2*2*40000*7, worst);
  int nok = (worst == 0); fails += !nok;
  printf("    %s   (un seul rang reproduit vaut deja 2^-61,6)\n", nok ? "PASS" : "FAIL");
  printf("\n  %s\n", fails ? "*** CONTROLES ECHOUES ***" : "controles: tous passes");
  return fails ? 1 : 0;
}

int main(int argc, char **argv){
  if(argc > 1 && !strcmp(argv[1], "selftest")) return selftest();
  if(argc < 3){ fprintf(stderr, "usage: %s <rank.bin> <nseeds>\n", argv[0]); return 2; }
  FILE *f = fopen(argv[1], "rb"); if(!f){ perror(argv[1]); return 2; }
  fseek(f, 0, SEEK_END); long b = ftell(f); fseek(f, 0, SEEK_SET);
  NR = b/8; RANK = malloc(b);
  if(fread(RANK, 8, NR, f) != (size_t)NR){ fprintf(stderr, "lecture courte\n"); return 2; }
  fclose(f);
  u64 nseeds = strtoull(argv[2], 0, 0);
  int g0 = (argc > 3) ? atoi(argv[3]) : 0;      /* reprise : premier generateur a traiter */
  const int MAXSTRIDE = 6, CAP = 8;
  printf("archive : %ld rangs ; rang tire sur 128 BITS (deux mots de 64)\n", NR);
  printf("balayage : %llu graines x %d generateurs x 2 ordres x 2 reductions x pas 2..%d\n",
         (unsigned long long)nseeds, G_NGEN, MAXSTRIDE);
  printf("  UN SEUL rang reproduit vaut 2^-61,6 : le seuil d'alarme est a 1, pas a 12.\n");
  printf("  essais %.4g -> le hasard en attend %.3e\n\n",
         (double)nseeds*G_NGEN*4*(MAXSTRIDE-1),
         (double)nseeds*G_NGEN*4*(MAXSTRIDE-1)/3.535e18);
  fflush(stdout);
  long alarms = 0; int best = 0;
  for(int g = g0; g < G_NGEN; g++)
    for(int order = 0; order < 2; order++)
      for(int mode = 0; mode < 2; mode++){
        int gb = 0;
        for(u64 s = 0; s < nseeds; s++)
          for(int st = 2; st <= MAXSTRIDE; st++){
            int m = match(g, (u32)s, st, order, mode, CAP);
            if(m > gb) gb = m;
            if(m >= 1){ printf("  ALARME %s %s %s graine=%llu pas=%d : %d rangs\n",
                GNAME[g], order?"(lo|hi)":"(hi|lo)", mode?"lemire":"mod",
                (unsigned long long)s, st, m); fflush(stdout); alarms++; }
          }
        if(gb > best) best = gb;
        printf("  %-12s %-9s %-6s : meilleur %d/%d%s\n", GNAME[g], order?"(lo|hi)":"(hi|lo)",
               mode?"lemire":"mod", gb, CAP,
               GSTATE[g] <= 32 ? "   (etat entierement couvert)" : "   (graines seulement)");
        fflush(stdout);
      }
  printf("\nmeilleur %d/%d ; alarmes %ld\n", best, CAP, alarms);
  return 0;
}
