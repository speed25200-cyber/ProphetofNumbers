#include <math.h>
/* bonusseed.c — recherche de graine sur le SEUL flux que le tri n'a pas ecrase.

   Tout le reste du dossier se bat contre le tri : 20 numeros publies en ordre croissant,
   4 bits d'information la ou le tirage en consomme 61,6. Le bonus, lui, est toujours l'un
   des 20 (verifie : 70560/70560), donc sa POSITION parmi les 20 tries porte 4,32 bits de
   l'ordre cache, intacts.

   Sous l'architecture par derangement — celle du paragraphe 6 quater — cette position est
   DIRECTEMENT une sortie du generateur : le derangement produit les 20 numeros deja
   tries, donc « l'element d'indice i » designe le i-eme plus petit, et pos = reduce(u,20).

   Ce qui rend l'attaque bon marche : une graine fausse meurt des la premiere comparaison
   avec probabilite 19/20, donc ~1,05 sortie par graine, contre un rang complet de 20
   numeros dans rankseed. Deux ordres de grandeur de moins par graine.

   Le boost sert de filtre de confirmation : sa table de seuils cumules est etablie a
   (0,512 / 0,75 / 0,90 / 0,95 / 0,975), chi2 = 0,55 sur 5 ddl. Un candidat doit donc
   AUSSI predire le boost — 1,88 bit de plus par tirage, gratuitement.

   usage:  ./bonusseed selftest
           ./bonusseed <pos.bin> <boost.bin> <first_draw> <nseeds> <report_at>
*/
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
typedef uint32_t u32; typedef uint64_t u64;

static unsigned char *POS, *BOO;
static long NDRAW;

/* Table de boost etablie sur l'archive, en FRACTIONS EXACTES : les seuils cumules
   (0,512 / 0,75 / 0,90 / 0,95 / 0,975) valent 64/125, 3/4, 9/10, 19/20, 39/40.
   Chaque generateur a sa propre largeur de sortie M, donc les coupures sont recalculees
   par generateur : comparer une sortie 31 bits a un seuil exprime en 2^64 n'a aucun sens. */
static const unsigned BNUM[5] = {64, 3, 9, 19, 39};
static const unsigned BDEN[5] = {125, 4, 10, 20, 40};

/* ---------------- generateurs, tous pilotes par une graine 32 bits ---------------- */
enum { G_XOR32, G_MINSTD, G_GLIBC, G_MSVC, G_JAVA, G_PCG32, G_SPLITMIX, G_NGEN };
static const char *GNAME[G_NGEN] =
  {"xorshift32","minstd","glibc_lcg","msvc_lcg","java48","pcg32","splitmix64"};

/* la TAILLE DE L'IMAGE de chaque generateur, pas une largeur arrondie : minstd sort dans
   [1, 2^31-2], msvc dans [0, 2^15), java next(32) dans [0, 2^32). C'est ce M qui sert a
   la fois a la reduction sur 0..19 et aux coupures du boost. */
/* la taille de l'ETAT, distincte de celle de la sortie : un balayage 2^32 epuise
   entierement les familles dont l'etat tient sur 32 bits, et ne couvre que les graines
   pour les autres. Confondre les deux ferait annoncer « etat entierement couvert » pour
   pcg32, dont l'etat fait 64 bits. */
static const int GSTATE[G_NGEN] = {32, 31, 32, 32, 48, 64, 64};

static const u64 GMOD[G_NGEN] = {
  1ULL<<32,        /* xorshift32 */
  2147483647ULL,   /* minstd, sortie dans [1, m-1] */
  1ULL<<31,        /* glibc, 31 bits utiles */
  1ULL<<15,        /* msvc rand(), 15 bits */
  1ULL<<32,        /* java next(32) */
  1ULL<<32,        /* pcg32 */
  0                /* splitmix64 : 2^64, traite a part */
};

typedef struct { u64 s; u32 x; int g; } St;

static void gseed(St *st, int g, u32 seed){
  st->g = g;
  switch(g){
    case G_XOR32:    st->x = seed ? seed : 1u; break;
    case G_MINSTD:   st->x = seed % 2147483647u; if(!st->x) st->x = 1u; break;
    case G_GLIBC:
    case G_MSVC:     st->x = seed; break;
    case G_JAVA:     st->s = ((u64)seed ^ 0x5DEECE66DULL) & ((1ULL<<48)-1); break;
    case G_SPLITMIX: st->s = seed; break;
    case G_PCG32:    st->s = 0;
                     st->s = st->s * 6364136223846793005ULL + 1442695040888963407ULL;
                     st->s += (u64)seed;
                     st->s = st->s * 6364136223846793005ULL + 1442695040888963407ULL;
                     break;
  }
}

/* une sortie, dans son domaine NATIF [0, GMOD[g]) — pas promue en poids fort */
static inline u64 gnext(St *st){
  switch(st->g){
    case G_XOR32: { u32 x = st->x; x ^= x<<13; x ^= x>>17; x ^= x<<5; st->x = x; return x; }
    case G_MINSTD: { st->x = (u32)(((u64)st->x * 48271ULL) % 2147483647ULL); return st->x; }
    case G_GLIBC:  { st->x = st->x * 1103515245u + 12345u; return st->x >> 1; }
    case G_MSVC:   { st->x = st->x * 214013u + 2531011u; return (st->x >> 16) & 0x7FFFu; }
    case G_JAVA:   { st->s = (st->s * 0x5DEECE66DULL + 0xB) & ((1ULL<<48)-1);
                     return st->s >> 16; }
    case G_PCG32:  { u64 o = st->s;
                     st->s = o * 6364136223846793005ULL + 1442695040888963407ULL;
                     u32 xs = (u32)(((o >> 18) ^ o) >> 27), r = (u32)(o >> 59);
                     return (u64)((xs >> r) | (xs << ((-r) & 31))); }
    default:       { u64 z = (st->s += 0x9E3779B97F4A7C15ULL);
                     z = (z ^ (z>>30)) * 0xBF58476D1CE4E5B9ULL;
                     z = (z ^ (z>>27)) * 0x94D049BB133111EBULL;
                     return z ^ (z>>31); }
  }
}

/* deux facons de ramener une sortie native sur 0..19 */
static inline int pos_mod(u64 v){ return (int)(v % 20ULL); }
static inline int pos_mulhi(int g, u64 v){
  if(g == G_SPLITMIX) return (int)(((__uint128_t)v * 20u) >> 64);
  return (int)((v * 20ULL) / GMOD[g]);
}
static inline int boost_of(int g, u64 v){
  for(int i = 0; i < 5; i++){
    __uint128_t cut = (g == G_SPLITMIX)
        ? (((__uint128_t)1 << 64) * BNUM[i]) / BDEN[i]
        : ((__uint128_t)GMOD[g] * BNUM[i]) / BDEN[i];
    if((__uint128_t)v < cut) return i;
  }
  return 5;
}

/* combien de positions consecutives une graine reproduit-elle ? */
static int match_len(int g, u32 seed, int stride, int red, int lead, long first, int cap){
  St st; gseed(&st, g, seed);
  for(int i = 0; i < lead; i++) gnext(&st);
  for(int k = 0; k < cap; k++){
    u64 u = gnext(&st);
    int p = red ? pos_mulhi(g, u) : pos_mod(u);
    if(p != POS[first + k]) return k;
    for(int j = 1; j < stride; j++) gnext(&st);
  }
  return cap;
}

/* un candidat doit aussi predire le boost : combien de boosts consecutifs ?
   le boost est suppose tire par l'appel qui suit immediatement l'indice du bonus */
static int boost_len(int g, u32 seed, int stride, int lead, long first, int cap){
  St st; gseed(&st, g, seed);
  for(int i = 0; i < lead; i++) gnext(&st);
  for(int k = 0; k < cap; k++){
    gnext(&st);                       /* l'indice du bonus */
    u64 b = gnext(&st);               /* le boost juste apres */
    if(boost_of(g, b) != BOO[first + k]) return k;
    for(int j = 2; j < stride; j++) gnext(&st);
  }
  return cap;
}

/* ------------------------------ controle positif ------------------------------ */
static int selftest(void){
  printf("selftest : on FABRIQUE un flux de positions avec une graine connue, puis on la\n");
  printf("  recherche. Sans cela un 0 sur l'archive ne prouve rien.\n\n");
  NDRAW = 4000;
  POS = malloc(NDRAW); BOO = malloc(NDRAW);
  int fails = 0;

  /* CONTROLE DE SURJECTIVITE — celui qui manquait.
     Une premiere version promouvait les sorties 32 bits en poids fort puis prenait
     « u % 20 ». Or 2^32 mod 20 = 16 et pgcd(16,20) = 4, donc cette reduction ne pouvait
     produire que {0,4,8,12,16} : cinq positions sur vingt. Sur l'archive elle donnait
     « meilleur appariement 0 » partout, ce qui se lit comme un resultat negatif eclatant
     alors que c'est un outil incapable de produire l'observable. Un outil doit d'abord
     prouver qu'il PEUT sortir la reponse cherchee. */
  printf("  controle de surjectivite : chaque reduction doit couvrir les 20 positions\n");
  for(int g = 0; g < G_NGEN; g++)
    for(int red = 0; red < 2; red++){
      long hit[20] = {0}; St st; gseed(&st, g, 12345u);
      for(long i = 0; i < 200000; i++){
        u64 v = gnext(&st);
        hit[red ? pos_mulhi(g, v) : pos_mod(v)]++;
      }
      int cov = 0; long lo = hit[0], hi = hit[0];
      for(int i = 0; i < 20; i++){ if(hit[i]) cov++; if(hit[i] < lo) lo = hit[i]; if(hit[i] > hi) hi = hit[i]; }
      int bhit[6] = {0}; gseed(&st, g, 999u);
      for(long i = 0; i < 200000; i++) bhit[boost_of(g, gnext(&st))]++;
      int bcov = 0; for(int i = 0; i < 6; i++) if(bhit[i]) bcov++;
      int ok = (cov == 20 && bcov == 6 && hi < 3 * lo + 30);
      fails += !ok;
      printf("    %-11s %-6s : %2d/20 positions, %d/6 boosts, min %ld max %ld  %s\n",
             GNAME[g], red ? "mulhi" : "mod", cov, bcov, lo, hi, ok ? "PASS" : "FAIL");
    }
  printf("\n");
  for(int g = 0; g < G_NGEN; g++){
    for(int red = 0; red < 2; red++){
      const u32 TRUE_SEED = 123456789u; const int TRUE_STRIDE = 23, TRUE_LEAD = 5;
      St st; gseed(&st, g, TRUE_SEED);
      for(int i = 0; i < TRUE_LEAD; i++) gnext(&st);
      for(long k = 0; k < NDRAW; k++){
        u64 u = gnext(&st);
        POS[k] = (unsigned char)(red ? pos_mulhi(g, u) : pos_mod(u));
        BOO[k] = (unsigned char)boost_of(g, gnext(&st));
        for(int j = 2; j < TRUE_STRIDE; j++) gnext(&st);
      }
      /* on cherche la graine en balayant un petit voisinage et TOUS les strides */
      u32 found = 0; int fs = 0, fl = 0, best = 0;
      for(u32 s = TRUE_SEED - 300; s <= TRUE_SEED + 300 && !found; s++)
        for(int stride = 1; stride <= 40 && !found; stride++)
          for(int lead = 0; lead < 8 && !found; lead++){
            int m = match_len(g, s, stride, red, lead, 0, 24);
            if(m > best) best = m;
            if(m >= 24){ found = s; fs = stride; fl = lead; }
          }
      int bl = found ? boost_len(g, found, fs, fl, 0, 24) : 0;
      int ok = (found == TRUE_SEED && fs == TRUE_STRIDE && bl >= 24);
      fails += !ok;
      printf("  %-11s %-6s : %s  (graine %u, stride %d, lead %d ; boost %d/24 ; meilleur %d)\n",
             GNAME[g], red ? "mulhi" : "mod",
             ok ? "RECOVERED" : "FAIL    ", found, fs, fl, bl, best);
    }
  }
  /* controle negatif : des positions vraiment aleatoires ne doivent rien donner */
  u64 z = 0xDEADBEEF12345ULL; int worst = 0;
  for(long k = 0; k < NDRAW; k++){
    z = z * 6364136223846793005ULL + 1; POS[k] = (unsigned char)((z >> 40) % 20);
    z = z * 6364136223846793005ULL + 1; BOO[k] = (unsigned char)(((z >> 40) % 6));
  }
  for(int g = 0; g < G_NGEN; g++)
    for(int red = 0; red < 2; red++)
      for(u32 s = 0; s < 3000; s++)
        for(int stride = 1; stride <= 40; stride++){
          int m = match_len(g, s, stride, red, 0, 0, 24);
          if(m > worst) worst = m;
        }
  long trials = (long)G_NGEN * 2 * 3000 * 40;
  printf("\n  controle negatif : positions aleatoires, %ld essais\n", trials);
  printf("    meilleur appariement %d ; le hasard en attend %.3f de longueur >= %d\n",
         worst, trials * pow(1.0/20.0, worst), worst);
  int neg_ok = (worst <= 5);
  fails += !neg_ok;
  printf("    %s\n", neg_ok ? "PASS (rien d'anormal)" : "FAIL (appariement trop long sur du bruit)");
  printf("\n  %s\n", fails ? "*** CONTROLES ECHOUES ***" : "controles: tous passes");
  return fails ? 1 : 0;
}

int main(int argc, char **argv){
  if(argc > 1 && !strcmp(argv[1], "selftest")) return selftest();
  /* Le chemin rapide du balayage n'est PAS celui qu'exerce le selftest : celui-ci appelle
     match_len directement, le balayage passe par le filtre « premiere position » qui tue
     les 40 pas d'un coup. Une optimisation qui change le resultat est exactement ce qu'il
     faut attraper, donc ce mode fabrique un flux a graine connue que le balayage doit
     retrouver par son propre chemin. */
  if(argc == 9 && !strcmp(argv[1], "plant")){
    int g = atoi(argv[2]); u32 sd = (u32)strtoul(argv[3], 0, 0);
    int stride = atoi(argv[4]), lead = atoi(argv[5]), red = atoi(argv[6]);
    long n = 4000;
    unsigned char *pp = malloc(n), *bb = malloc(n);
    St st; gseed(&st, g, sd);
    for(int i = 0; i < lead; i++) gnext(&st);
    for(long k = 0; k < n; k++){
      u64 u = gnext(&st);
      pp[k] = (unsigned char)(red ? pos_mulhi(g, u) : pos_mod(u));
      bb[k] = (unsigned char)boost_of(g, gnext(&st));
      for(int j = 2; j < stride; j++) gnext(&st);
    }
    FILE *f1 = fopen(argv[7], "wb"); fwrite(pp, 1, n, f1); fclose(f1);
    FILE *f2 = fopen(argv[8], "wb"); fwrite(bb, 1, n, f2); fclose(f2);
    printf("plante : %s graine=%u stride=%d lead=%d red=%s -> %s, %s\n",
           GNAME[g], sd, stride, lead, red ? "mulhi" : "mod", argv[7], argv[8]);
    return 0;
  }
  if(argc < 6){ fprintf(stderr, "usage: %s <pos.bin> <boost.bin> <first> <nseeds> <report_at>\n", argv[0]); return 2; }
  FILE *f = fopen(argv[1], "rb"); if(!f){ perror(argv[1]); return 2; }
  fseek(f, 0, SEEK_END); NDRAW = ftell(f); fseek(f, 0, SEEK_SET);
  POS = malloc(NDRAW); if(fread(POS, 1, NDRAW, f) != (size_t)NDRAW){ fprintf(stderr,"read\n"); return 2; }
  fclose(f);
  f = fopen(argv[2], "rb"); if(!f){ perror(argv[2]); return 2; }
  BOO = malloc(NDRAW); if(fread(BOO, 1, NDRAW, f) != (size_t)NDRAW){ fprintf(stderr,"read\n"); return 2; }
  fclose(f);
  long first = atol(argv[3]);
  u64 nseeds = strtoull(argv[4], 0, 0);
  int report = atoi(argv[5]);
  const int CAP = 24, MAXSTRIDE = 40, LEADS = 4;
  if(NDRAW < first + CAP + 2){ fprintf(stderr, "pas assez de tirages\n"); return 2; }

  printf("archive : %ld tirages ; depart au tirage %ld\n", NDRAW, first);
  printf("balayage : %llu graines x %d generateurs x 2 reductions x %d strides x %d leads\n",
         (unsigned long long)nseeds, G_NGEN, MAXSTRIDE, LEADS);
  double trials = (double)nseeds * G_NGEN * 2 * MAXSTRIDE * LEADS;
  printf("essais : %.4g ; le hasard attend %.4g appariements de longueur >= %d\n\n",
         trials, trials * pow(1.0/20.0, report), report);
  fflush(stdout);

  int best = 0; long alarms = 0;
  /* Le pas (stride) n'intervient PAS dans la premiere comparaison : celle-ci ne regarde
     que la sortie d'indice `lead`. Un seul test tue donc les 40 pas d'un coup, et 19
     graines sur 20 meurent la. Le cout par graine tombe de ~570 sorties a ~5, ce qui
     fait passer le balayage 2^32 de 25 heures a une poignee de minutes. */
  u64 buf[8 + 64];
  for(int g = 0; g < G_NGEN; g++){
    for(int red = 0; red < 2; red++){
      int gbest = 0;
      const int want0 = POS[first], want1 = POS[first + 1];
      for(u64 s = 0; s < nseeds; s++){
        St st; gseed(&st, g, (u32)s);
        int any = 0;
        for(int l = 0; l < LEADS; l++){
          buf[l] = gnext(&st);
          if((red ? pos_mulhi(g, buf[l]) : pos_mod(buf[l])) == want0) any = 1;
        }
        if(!gbest) gbest = 1;                       /* au moins une position comparee */
        if(!any) continue;
        for(int i = LEADS; i < LEADS + MAXSTRIDE; i++) buf[i] = gnext(&st);
        for(int l = 0; l < LEADS; l++){
          if((red ? pos_mulhi(g, buf[l]) : pos_mod(buf[l])) != want0) continue;
          if(gbest < 1) gbest = 1;
          for(int stride = 1; stride <= MAXSTRIDE; stride++){
            u64 v = buf[l + stride];
            if((red ? pos_mulhi(g, v) : pos_mod(v)) != want1){ if(gbest < 1) gbest = 1; continue; }
            int m = match_len(g, (u32)s, stride, red, l, first, CAP);
            if(m > gbest) gbest = m;
            if(m >= report){
              int bl = boost_len(g, (u32)s, stride, l, first, CAP);
              printf("  ALARME %s/%s graine=%llu stride=%d lead=%d : %d positions, %d boosts\n",
                     GNAME[g], red ? "mulhi" : "mod", (unsigned long long)s, stride, l, m, bl);
              fflush(stdout); alarms++;
            }
          }
        }
      }
      if(gbest > best) best = gbest;
      printf("  %-11s %-6s : meilleur appariement %d / %d%s\n", GNAME[g], red ? "mulhi" : "mod",
             gbest, CAP, GSTATE[g] <= 32 ? "   (etat entierement couvert)"
                                        : "   (graines seulement, etat > 32 bits)");
      fflush(stdout);
    }
  }
  printf("\nmeilleur global %d ; alarmes %ld\n", best, alarms);
  return 0;
}
