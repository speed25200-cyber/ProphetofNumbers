/* langhunt.c — deux runtimes courants que rien ne couvrait : C# System.Random et Ruby.
 *
 * Le dossier couvre Python (random.sample exact), PHP (mt_rand), V8, Java, glibc, MSVC,
 * et Go via sa propre bibliotheque (gohunt). Restaient deux runtimes de back-end tres
 * repandus, chacun avec un generateur et une API de tirage qui lui sont propres :
 *
 *  C#  System.Random(seed) — Knuth soustractif (SeedArray[56]), Next(min,max) via Sample().
 *      Verifie contre les vecteurs publies : new Random(0).Next() == 1559595546.
 *      Trois idiomes : Fisher-Yates (avant et arriere), Next(1,81) avec rejet applicatif,
 *      OrderBy(x => rnd.Next()).Take(20) — le « tri par cle » LINQ.
 *
 *  Ruby Random.new(seed) + Array#sample(20) — MT19937 (init_genrand pour une graine sur
 *      32 bits), et un melange partiel dont le tirage borne est « masque de bits BAS avec
 *      rejet » — la ou Python prend les bits HAUTS. C'est ce detail qui en fait un cas a
 *      part. Verifie contre Ruby 3.3.6 sur six graines, trois tirages chacune.
 *
 *   ./langhunt selftest
 *   ./langhunt <draws.bin> <first> <nseeds>
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
typedef uint32_t u32; typedef uint64_t u64; typedef int32_t i32;

/* ------------------------------ C# System.Random ------------------------------ */
typedef struct { i32 arr[56]; int inext, inextp; } CS;
static void cs_seed(CS *r, i32 seed){
  const i32 IMAX = 2147483647;
  i32 sub = (seed == (i32)0x80000000) ? IMAX : (seed < 0 ? -seed : seed);
  i32 mj = 161803398 - sub, mk = 1;
  r->arr[55] = mj;
  for(int i = 1; i < 55; i++){
    int ii = (21 * i) % 55;
    r->arr[ii] = mk; mk = mj - mk; if(mk < 0) mk += IMAX; mj = r->arr[ii];
  }
  for(int k = 1; k < 5; k++)
    for(int i = 1; i < 56; i++){
      r->arr[i] -= r->arr[1 + (i + 30) % 55];
      if(r->arr[i] < 0) r->arr[i] += IMAX;
    }
  r->inext = 0; r->inextp = 21;
}
static inline i32 cs_sample(CS *r){
  int a = r->inext, b = r->inextp;
  if(++a >= 56) a = 1;
  if(++b >= 56) b = 1;
  i32 v = r->arr[a] - r->arr[b];
  if(v == 2147483647) v--;
  if(v < 0) v += 2147483647;
  r->arr[a] = v; r->inext = a; r->inextp = b;
  return v;
}
static inline i32 cs_next(CS *r){ return cs_sample(r); }
static inline i32 cs_next_max(CS *r, i32 max){        /* Next(maxValue) */
  return (i32)((double)cs_sample(r) * (1.0 / 2147483647.0) * max);
}
static inline i32 cs_next_range(CS *r, i32 lo, i32 hi){ /* Next(min,max), range < INT_MAX */
  return (i32)((double)cs_sample(r) * (1.0 / 2147483647.0) * (hi - lo)) + lo;
}

/* --------------------------------- Ruby MT --------------------------------- */
typedef struct { u32 mt[624]; int mti; } MT;
static void mt_init(MT *S, u32 s){
  S->mt[0] = s;
  for(int i = 1; i < 624; i++) S->mt[i] = 1812433253U * (S->mt[i-1] ^ (S->mt[i-1] >> 30)) + i;
  S->mti = 624;
}
static void mt_init_arr(MT *S, const u32 *key, int len){
  mt_init(S, 19650218U); int i = 1, j = 0;
  for(int k = (624 > len ? 624 : len); k; k--){
    S->mt[i] = (S->mt[i] ^ ((S->mt[i-1] ^ (S->mt[i-1] >> 30)) * 1664525U)) + key[j] + j;
    i++; j++; if(i >= 624){ S->mt[0] = S->mt[623]; i = 1; } if(j >= len) j = 0;
  }
  for(int k = 623; k; k--){
    S->mt[i] = (S->mt[i] ^ ((S->mt[i-1] ^ (S->mt[i-1] >> 30)) * 1566083941U)) - i;
    i++; if(i >= 624){ S->mt[0] = S->mt[623]; i = 1; }
  }
  S->mt[0] = 0x80000000U; S->mti = 624;
}
static u32 mt_next(MT *S){
  static const u32 mag[2] = {0, 0x9908b0dfU};
  if(S->mti >= 624){ u32 y; int k;
    for(k = 0; k < 227; k++){ y = (S->mt[k]&0x80000000U)|(S->mt[k+1]&0x7fffffffU); S->mt[k] = S->mt[k+397]^(y>>1)^mag[y&1]; }
    for(; k < 623; k++){ y = (S->mt[k]&0x80000000U)|(S->mt[k+1]&0x7fffffffU); S->mt[k] = S->mt[k-227]^(y>>1)^mag[y&1]; }
    y = (S->mt[623]&0x80000000U)|(S->mt[0]&0x7fffffffU); S->mt[623] = S->mt[396]^(y>>1)^mag[y&1]; S->mti = 0; }
  u32 y = S->mt[S->mti++]; y ^= y>>11; y ^= (y<<7)&0x9d2c5680U; y ^= (y<<15)&0xefc60000U; y ^= y>>18; return y;
}
/* Ruby : limited_rand — bits BAS masques, rejet si > limit */
static inline u32 rb_limited(MT *S, u32 limit){
  if(!limit) return 0;
  u32 mask = limit; mask |= mask>>1; mask |= mask>>2; mask |= mask>>4; mask |= mask>>8; mask |= mask>>16;
  for(;;){ u32 v = mt_next(S) & mask; if(v <= limit) return v; }
}
/* Ruby : Random.new(seed) pour une graine sur 32 bits */
static void rb_seed(MT *S, u32 seed, int by_array){
  if(by_array){ u32 k[1] = {seed}; mt_init_arr(S, k, 1); } else mt_init(S, seed);
}
/* Ruby : Array#sample(20) sur (1..80), melange partiel avec RAND_UPTO(len-i)+i */
static void rb_sample20(MT *S, uint8_t *out){
  uint8_t a[80]; for(int i = 0; i < 80; i++) a[i] = (uint8_t)(i+1);
  for(int i = 0; i < 20; i++){
    u32 j = rb_limited(S, (u32)(80 - i - 1)) + (u32)i;
    uint8_t t = a[j]; a[j] = a[i]; a[i] = t;
    out[i] = a[i];
  }
}

static void sort20(uint8_t *r){ for(int a = 1; a < 20; a++){ uint8_t k = r[a]; int b = a-1;
  while(b >= 0 && r[b] > k){ r[b+1] = r[b]; b--; } r[b+1] = k; } }
static int same20(const uint8_t *a, const uint8_t *b){ return memcmp(a, b, 20) == 0; }

/* ------------------------------ les methodes C# ------------------------------ */
enum { CS_FY_BWD, CS_FY_FWD, CS_REJ, CS_ORDERBY, CS_NM };
static const char *CSN[CS_NM] = {"FY arriere Next(i+1)", "FY avant Next(i,80)", "Next(1,81)+rejet", "OrderBy(Next())"};
static void cs_draw(CS *r, int m, uint8_t *out){
  uint8_t a[80]; for(int i = 0; i < 80; i++) a[i] = (uint8_t)(i+1);
  switch(m){
    case CS_FY_BWD: for(int i = 79; i > 0; i--){ i32 j = cs_next_max(r, i+1); uint8_t t = a[i]; a[i] = a[j]; a[j] = t; }
                    memcpy(out, a, 20); break;
    case CS_FY_FWD: for(int i = 0; i < 20; i++){ i32 j = cs_next_range(r, i, 80); uint8_t t = a[i]; a[i] = a[j]; a[j] = t; }
                    memcpy(out, a, 20); break;
    case CS_REJ:  { int seen[81] = {0}, n = 0;
                    while(n < 20){ i32 v = cs_next_range(r, 1, 81); if(!seen[v]){ seen[v] = 1; out[n++] = (uint8_t)v; } } break; }
    case CS_ORDERBY: { i32 key[80]; for(int i = 0; i < 80; i++) key[i] = cs_next(r);
                    uint8_t idx[80]; for(int i = 0; i < 80; i++) idx[i] = (uint8_t)i;
                    for(int x = 1; x < 80; x++){ uint8_t k = idx[x]; int y = x-1;      /* tri stable, comme OrderBy */
                      while(y >= 0 && key[idx[y]] > key[k]){ idx[y+1] = idx[y]; y--; } idx[y+1] = k; }
                    for(int i = 0; i < 20; i++) out[i] = (uint8_t)(idx[i]+1); break; }
  }
  sort20(out);
}

static u32 N; static uint8_t *NUMS;
static void loadbin(const char *fn){
  FILE *f = fopen(fn, "rb"); if(!f || fread(&N,4,1,f)!=1){ perror(fn); exit(1); }
  u32 *ids = malloc(4*(size_t)N), *ts = malloc(4*(size_t)N);
  u64 *lo = malloc(8*(size_t)N), *hi = malloc(8*(size_t)N);
  NUMS = malloc(20*(size_t)N); uint8_t *bo = malloc(N), *bn = malloc(N);
  if(fread(ids,4,N,f)!=N||fread(ts,4,N,f)!=N||fread(lo,8,N,f)!=N||fread(hi,8,N,f)!=N||
     fread(NUMS,20,N,f)!=N||fread(bo,1,N,f)!=N||fread(bn,1,N,f)!=N){ fprintf(stderr,"tronque\n"); exit(1); }
  fclose(f);
}

static int selftest(void){
  int fails = 0;
  printf("C# System.Random — vecteurs publies :\n");
  { struct { i32 seed, want; } V[] = {{0, 1559595546}, {1, 534011718}, {42, 1434747710}};
    for(int i = 0; i < 3; i++){ CS r; cs_seed(&r, V[i].seed); i32 got = cs_next(&r);
      int ok = (got == V[i].want); fails += !ok;
      printf("  new Random(%d).Next() = %d   attendu %d   %s\n", V[i].seed, got, V[i].want, ok?"OK":"FAUX"); } }

  printf("\nRuby 3.3.6 — Random.new(seed), (1..80).to_a.sample(20) x3, vecteurs du runtime :\n");
  { const char *ref[] = {
      "0 7,13,15,22,26,28,30,40,41,44,45,49,52,60,67,69,71,72,77,79 1,13,14,21,22,25,26,30,34,39,42,46,48,49,52,53,67,70,76,80 4,5,11,13,15,16,27,30,37,42,45,47,53,54,56,57,60,71,74,75",
      "1 2,8,10,11,13,14,16,24,26,32,33,36,38,44,46,62,69,71,75,80 5,8,9,10,11,14,18,19,22,24,25,28,37,44,60,64,66,67,70,75 5,12,18,22,24,25,30,35,36,38,39,45,46,47,54,57,72,77,78,79",
      "42 7,9,10,12,13,15,16,25,30,37,41,50,52,62,64,74,75,77,78,80 1,3,16,17,20,22,26,37,45,50,55,57,61,64,65,66,68,69,71,76 2,4,5,7,8,10,12,16,17,18,23,46,48,52,57,61,63,66,72,78",
      "12345 2,3,4,8,10,12,17,20,21,23,30,35,38,39,45,50,53,57,67,73 4,5,6,8,9,12,13,15,16,20,25,28,37,41,42,50,54,62,66,71 2,3,4,13,16,21,25,34,35,43,47,56,58,62,66,67,69,75,76,78",
      "4294967295 1,2,15,19,23,24,27,36,39,44,51,53,57,60,65,66,67,70,74,75 6,7,8,10,14,18,29,30,31,38,47,55,56,57,58,60,69,72,75,78 1,2,5,9,11,17,20,22,24,28,35,36,39,41,43,45,48,67,70,75",
      "1757829900 1,3,4,7,11,13,14,16,18,20,23,35,39,40,43,57,75,76,77,80 4,13,14,17,20,21,23,27,28,30,32,33,42,52,54,55,61,78,79,80 3,6,8,17,21,24,25,29,31,32,37,39,42,43,50,57,63,64,71,77"};
    { MT S; rb_seed(&S, 0, 0); uint8_t o[20]; rb_sample20(&S, o); sort20(o);
      printf("  mon modele, graine 0, tirage 1 : "); for(int i = 0; i < 20; i++) printf("%d%s", o[i], i<19?",":"\n"); }
    int which_ok[2] = {0, 0};
    for(int by = 0; by < 2; by++){
      int ok_all = 1;
      for(int v = 0; v < 6; v++){
        char buf[512]; strcpy(buf, ref[v]); char *p = strtok(buf, " "); u32 seed = (u32)strtoul(p, 0, 10);
        MT S; rb_seed(&S, seed, by);
        for(int d = 0; d < 3; d++){
          /* un strtok(p, ",") imbrique ici corrompait l'etat du strtok externe et faisait
             echouer la comparaison alors que le modele etait juste : parser a la main */
          p = strtok(0, " "); uint8_t want[20]; int n = 0;
          { const char *s = p; while(*s && n < 20){ want[n++] = (uint8_t)strtoul(s, (char**)&s, 10); if(*s == ',') s++; } }
          uint8_t got[20]; rb_sample20(&S, got); sort20(got);
          if(!same20(got, want)) ok_all = 0;
        }
      }
      which_ok[by] = ok_all;
      printf("  amorcage %-13s : %s\n", by ? "init_by_array" : "init_genrand", ok_all ? "les 18 tirages reproduits" : "ecart");
    }
    if(!which_ok[0] && !which_ok[1]){ fails++; printf("  *** aucun amorcage ne reproduit Ruby : implementation fausse ***\n"); }
  }

  /* controle negatif : tirages equitables d'un autre generateur */
  printf("\ncontrole negatif : 40 000 graines x methodes sur 3 tirages SRS d'un autre generateur\n");
  { u64 z = 0xABCDEF; uint8_t rows[3][20];
    for(int d = 0; d < 3; d++){ uint8_t pool[80]; for(int i = 0; i < 80; i++) pool[i] = (uint8_t)(i+1);
      for(int i = 79; i > 0; i--){ z = z*6364136223846793005ULL+1442695040888963407ULL; int j = (int)((z>>33)%(unsigned)(i+1)); uint8_t t = pool[i]; pool[i] = pool[j]; pool[j] = t; }
      memcpy(rows[d], pool, 20); sort20(rows[d]); }
    int worst = 0;
    for(u32 s = 0; s < 40000; s++){
      for(int m = 0; m < CS_NM; m++){ CS r; cs_seed(&r, (i32)s); int k = 0;
        for(int d = 0; d < 3; d++){ uint8_t o[20]; cs_draw(&r, m, o); if(same20(o, rows[d])) k++; else break; }
        if(k > worst) worst = k; }
      for(int by = 0; by < 2; by++){ MT S; rb_seed(&S, s, by); int k = 0;
        for(int d = 0; d < 3; d++){ uint8_t o[20]; rb_sample20(&S, o); sort20(o); if(same20(o, rows[d])) k++; else break; }
        if(k > worst) worst = k; }
    }
    printf("  meilleur %d/3   %s\n", worst, worst == 0 ? "PASS" : "FAIL");
    fails += (worst != 0);
  }
  printf("\n  %s\n", fails ? "*** CONTROLES ECHOUES ***" : "controles: tous passes");
  return fails ? 1 : 0;
}

int main(int argc, char **argv){
  if(argc > 1 && !strcmp(argv[1], "selftest")) return selftest();
  if(argc < 4){ fprintf(stderr, "usage: %s <draws.bin> <first> <nseeds>\n", argv[0]); return 2; }
  loadbin(argv[1]);
  long first = atol(argv[2]); u64 nseeds = strtoull(argv[3], 0, 0);
  const uint8_t *row0 = NUMS + 20*(size_t)first;
  printf("archive : %u tirages ; depart %ld ; %llu graines\n", N, first, (unsigned long long)nseeds);
  printf("  UN SEUL tirage reproduit vaut 2^-61,6 : seuil d'alarme a 1.\n\n");
  fflush(stdout);
  long alarms = 0;
  for(int m = 0; m < CS_NM; m++){
    long hits = 0;
    for(u64 s = 0; s < nseeds && s < 2147483648ULL; s++){
      CS r; cs_seed(&r, (i32)s); uint8_t o[20]; cs_draw(&r, m, o);
      if(same20(o, row0)){ hits++; alarms++;
        int k = 1; for(int d = 1; d < 4; d++){ cs_draw(&r, m, o); if(same20(o, NUMS + 20*(size_t)(first+d))) k++; else break; }
        printf("  ALARME C# %s graine=%llu : %d tirages consecutifs\n", CSN[m], (unsigned long long)s, k); fflush(stdout); }
    }
    printf("  C#   %-22s : %ld touche(s) sur %llu graines (etat 31 bits, entierement couvert)\n",
           CSN[m], hits, (unsigned long long)(nseeds < 2147483648ULL ? nseeds : 2147483648ULL));
    fflush(stdout);
  }
  /* Ruby n'emploie init_by_array que pour une graine de plus d'un mot : sur 32 bits c'est
     toujours init_genrand (verifie contre le runtime). Balayer l'autre serait 2 h perdues. */
  for(int by = 0; by < 1; by++){
    long hits = 0;
    for(u64 s = 0; s < nseeds; s++){
      MT S; rb_seed(&S, (u32)s, by); uint8_t o[20]; rb_sample20(&S, o); sort20(o);
      if(same20(o, row0)){ hits++; alarms++;
        int k = 1; for(int d = 1; d < 4; d++){ rb_sample20(&S, o); sort20(o); if(same20(o, NUMS + 20*(size_t)(first+d))) k++; else break; }
        printf("  ALARME Ruby %s graine=%llu : %d tirages consecutifs\n", by?"init_by_array":"init_genrand", (unsigned long long)s, k); fflush(stdout); }
    }
    printf("  Ruby %-22s : %ld touche(s) sur %llu graines\n", by?"init_by_array":"init_genrand", hits, (unsigned long long)nseeds);
    fflush(stdout);
  }
  printf("\nalarmes : %ld\n", alarms);
  return 0;
}
