/* pcg64seed.c — PCG64 a etat 128 bits : fermer le cas ensemence, exhaustivement.
 *
 * Le §9 listait PCG64 comme la seule famille repandue encore debout. Deux sous-cas, et il
 * faut les distinguer nettement :
 *
 *  (a) etat 128 bits VRAIMENT aleatoire — hors de portee. J'ai essaye la voie SMT (z3 sur
 *      vecteurs de bits, avec la decomposition exacte de la multiplication 128 bits en
 *      operations 64 bits, verifiee sur 20 000 etats). Le solveur ne conclut pas, meme a
 *      K = 2 observations et meme en fixant la rotation : « unknown » a 45 s par appel.
 *      C'est une mesure sur la METHODE, pas un resultat sur PCG64 : le pliage hi^lo suivi
 *      d'une rotation dependant de l'etat est precisement concu pour cela. Reste declare
 *      ouvert.
 *
 *  (b) etat DERIVE d'une graine de 32 bits — le cas reellement deploye : un service qui
 *      s'ensemence sur l'horloge, un identifiant, un compteur. Celui-la se balaie
 *      entierement, et c'est ce que fait cet outil.
 *
 * Deux variantes de sortie : XSL-RR (le PCG64 classique) et DXSM (le defaut de numpy
 * depuis 1.19). Deux observables : le rang (61,6 bits, architecture par derangement) et
 * l'indice du bonus (4,32 bits, §6 sexies). Deux reductions chacun.
 *
 *   ./pcg64seed selftest
 *   ./pcg64seed <rank.bin> <bonuspos.bin> <nseeds>
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
typedef uint64_t u64; typedef unsigned __int128 u128;

static const u128 MULT_XSL = ((u128)2549297995355413924ULL << 64) | 4865540595714422341ULL;
static const u64  MULT_DXSM = 0xda942042e4dd58b5ULL;
static const u128 INC_DEF  = ((u128)6364136223846793005ULL << 64) | 1442695040888963407ULL;

/* C(80,20) tient sur 62 bits */
static const u64 CC = 3535316142212174320ULL;

typedef struct { u128 s, inc; int dxsm; } Pcg;

static inline void pstep(Pcg *p){
  p->s = p->s * (p->dxsm ? (u128)MULT_DXSM : MULT_XSL) + p->inc;
}
static inline u64 pout(const Pcg *p){
  u64 hi = (u64)(p->s >> 64), lo = (u64)p->s;
  if(!p->dxsm){
    u64 x = hi ^ lo; unsigned r = (unsigned)(p->s >> 122) & 63u;
    return (x >> r) | (x << ((64 - r) & 63));
  }
  u64 h = hi, l = lo | 1ULL;
  h ^= h >> 32; h *= MULT_DXSM; h ^= h >> 48; h *= l;
  return h;
}
static inline u64 pnext(Pcg *p){ pstep(p); return pout(p); }

/* trois conventions d'ensemencement, toutes pilotees par une graine 32 bits */
static void pseed(Pcg *p, int dxsm, int conv, u64 seed){
  p->dxsm = dxsm; p->inc = INC_DEF | 1;
  switch(conv){
    case 0: p->s = (u128)seed; break;                        /* etat brut = graine */
    case 1: p->s = 0; pstep(p); p->s += (u128)seed; pstep(p); break;   /* amorcage PCG */
    case 2: p->s = ((u128)seed << 64) | seed; break;         /* graine dupliquee */
  }
}
static const char *CONV[3] = {"etat=graine", "amorcage PCG", "graine dupliquee"};

static inline u64 red_rank(u64 u, int mulhi){
  return mulhi ? (u64)(((u128)u * CC) >> 64) : (u % CC);
}
static inline int red_pos(u64 u, int mulhi){
  return mulhi ? (int)(((u128)u * 20u) >> 64) : (int)(u % 20ULL);
}

static u64 *RANK; static unsigned char *POS; static long NR, NP;

static int match_rank(int dxsm, int conv, u64 seed, int stride, int mulhi, int cap){
  Pcg p; pseed(&p, dxsm, conv, seed);
  for(int k = 0; k < cap; k++){
    if(red_rank(pnext(&p), mulhi) != RANK[k]) return k;
    for(int j = 1; j < stride; j++) pnext(&p);
  }
  return cap;
}
static int match_pos(int dxsm, int conv, u64 seed, int stride, int mulhi, int cap){
  Pcg p; pseed(&p, dxsm, conv, seed);
  for(int k = 0; k < cap; k++){
    if(red_pos(pnext(&p), mulhi) != POS[k]) return k;
    for(int j = 1; j < stride; j++) pnext(&p);
  }
  return cap;
}

static void *slurp(const char *fn, long *n, int elem){
  FILE *f = fopen(fn, "rb"); if(!f){ perror(fn); exit(1); }
  fseek(f, 0, SEEK_END); long b = ftell(f); fseek(f, 0, SEEK_SET);
  void *p = malloc(b); if(fread(p, 1, b, f) != (size_t)b){ fprintf(stderr,"short\n"); exit(1); }
  fclose(f); *n = b / elem; return p;
}

static int selftest(void){
  printf("selftest : PCG64 plante, graine connue, dans les deux variantes de sortie\n");
  printf("  et les trois conventions d'ensemencement. Sans cela un 0 ne vaut rien.\n\n");
  int fails = 0;
  NR = 64; NP = 64;
  RANK = malloc(NR * 8); POS = malloc(NP);
  for(int dxsm = 0; dxsm < 2; dxsm++)
    for(int conv = 0; conv < 3; conv++)
      for(int mulhi = 0; mulhi < 2; mulhi++){
        const u64 SEED = 4242424242ULL; const int STRIDE = 3;
        Pcg p; pseed(&p, dxsm, conv, SEED);
        for(long k = 0; k < NR; k++){
          u64 u = pnext(&p);
          RANK[k] = red_rank(u, mulhi); POS[k] = (unsigned char)red_pos(u, mulhi);
          for(int j = 1; j < STRIDE; j++) pnext(&p);
        }
        u64 f1 = 0, f2 = 0; int s1 = 0, s2 = 0;
        for(u64 s = SEED - 500; s <= SEED + 500; s++)
          for(int st = 1; st <= 6; st++){
            if(!f1 && match_rank(dxsm, conv, s, st, mulhi, 8) >= 8){ f1 = s; s1 = st; }
            if(!f2 && match_pos (dxsm, conv, s, st, mulhi, 24) >= 24){ f2 = s; s2 = st; }
          }
        int ok = (f1 == SEED && s1 == STRIDE && f2 == SEED && s2 == STRIDE);
        fails += !ok;
        printf("  %-7s %-17s %-6s : rang %s  indice %s\n",
               dxsm ? "DXSM" : "XSL-RR", CONV[conv], mulhi ? "mulhi" : "mod",
               (f1 == SEED && s1 == STRIDE) ? "RECOVERED" : "FAIL",
               (f2 == SEED && s2 == STRIDE) ? "RECOVERED" : "FAIL");
      }
  /* controle negatif : des rangs/positions aleatoires ne doivent rien donner */
  u64 z = 0xFEEDFACE12345ULL; int worst_r = 0, worst_p = 0;
  for(long k = 0; k < NR; k++){
    z = z * 6364136223846793005ULL + 1; RANK[k] = (z >> 2) % CC;
    z = z * 6364136223846793005ULL + 1; POS[k] = (unsigned char)((z >> 33) % 20);
  }
  for(int dxsm = 0; dxsm < 2; dxsm++)
    for(int conv = 0; conv < 3; conv++)
      for(int mulhi = 0; mulhi < 2; mulhi++)
        for(u64 s = 0; s < 30000; s++)
          for(int st = 1; st <= 6; st++){
            int a = match_rank(dxsm, conv, s, st, mulhi, 8); if(a > worst_r) worst_r = a;
            int b = match_pos (dxsm, conv, s, st, mulhi, 24); if(b > worst_p) worst_p = b;
          }
  printf("\n  controle negatif (2,16e6 essais) : meilleur rang %d/8, meilleur indice %d/24\n",
         worst_r, worst_p);
  int nok = (worst_r == 0 && worst_p <= 6);
  fails += !nok;
  printf("    %s\n", nok ? "PASS" : "FAIL");
  printf("\n  %s\n", fails ? "*** CONTROLES ECHOUES ***" : "controles: tous passes");
  return fails ? 1 : 0;
}

int main(int argc, char **argv){
  if(argc > 1 && !strcmp(argv[1], "selftest")) return selftest();
  if(argc < 4){ fprintf(stderr, "usage: %s <rank.bin> <bonuspos.bin> <nseeds>\n", argv[0]); return 2; }
  RANK = slurp(argv[1], &NR, 8);
  POS  = slurp(argv[2], &NP, 1);
  u64 nseeds = strtoull(argv[3], 0, 0);
  const int MAXSTRIDE = 8;
  printf("archive : %ld rangs, %ld indices de bonus\n", NR, NP);
  printf("balayage : %llu graines x 2 sorties x 3 amorcages x 2 reductions x %d pas\n",
         (unsigned long long)nseeds, MAXSTRIDE);
  printf("  le rang vaut 61,6 bits : UN SEUL tirage reproduit serait deja concluant.\n");
  printf("  l'indice vaut 4,32 bits : il en faut 12, et le hasard en attend %.3e\n\n",
         (double)nseeds * 2 * 3 * 2 * MAXSTRIDE * 1.9e-16);
  fflush(stdout);
  long alarms = 0; int bestr = 0, bestp = 0;
  for(int dxsm = 0; dxsm < 2; dxsm++)
    for(int conv = 0; conv < 3; conv++)
      for(int mulhi = 0; mulhi < 2; mulhi++){
        int br = 0, bp = 0;
        for(u64 s = 0; s < nseeds; s++)
          for(int st = 1; st <= MAXSTRIDE; st++){
            int a = match_rank(dxsm, conv, s, st, mulhi, 8);
            if(a > br) br = a;
            if(a >= 1){ printf("  ALARME RANG %s/%s/%s graine=%llu pas=%d : %d rangs\n",
                dxsm?"DXSM":"XSL-RR", CONV[conv], mulhi?"mulhi":"mod",
                (unsigned long long)s, st, a); fflush(stdout); alarms++; }
            int b = match_pos(dxsm, conv, s, st, mulhi, 24);
            if(b > bp) bp = b;
            if(b >= 12){ printf("  ALARME INDICE %s/%s/%s graine=%llu pas=%d : %d indices\n",
                dxsm?"DXSM":"XSL-RR", CONV[conv], mulhi?"mulhi":"mod",
                (unsigned long long)s, st, b); fflush(stdout); alarms++; }
          }
        if(br > bestr) bestr = br;
        if(bp > bestp) bestp = bp;
        printf("  %-7s %-17s %-6s : rang %d/8   indice %d/24\n",
               dxsm?"DXSM":"XSL-RR", CONV[conv], mulhi?"mulhi":"mod", br, bp);
        fflush(stdout);
      }
  printf("\nmeilleur rang %d/8, meilleur indice %d/24 ; alarmes %ld\n", bestr, bestp, alarms);
  return 0;
}
