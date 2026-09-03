/* graine_exhaustive.c — LE BALAYAGE EXHAUSTIF DE L'ESPACE DE GRAINE 32 BITS.
 *
 * POURQUOI, ET EN QUOI C'EST DIFFERENT DU §200
 * ============================================
 * Les §200 a §202 balayent des graines DERIVEES du tirage — l'heure, l'identifiant, la
 * date. Ils supposent donc que la graine est devinable a partir de ce que l'archive
 * publie. Si la machine s'amorce sur autre chose — `srand(getpid())`, une constante de
 * configuration, un hachage quelconque — aucun de ces balayages ne la trouve.
 *
 * Le present outil ne suppose RIEN sur l'origine de la graine : il les essaie TOUTES.
 *
 * L'ASTUCE QUI REND L'EXHAUSTIF FAISABLE
 * ======================================
 * Naivement, il faudrait balayer 2^32 graines POUR CHAQUE tirage cible, soit 2^32 x 70 560
 * essais. C'est hors de portee.
 *
 * Mais la comparaison peut se faire dans l'autre sens. Pour chaque graine, on engendre UN
 * tirage et l'on demande : « ce tirage est-il DANS l'archive ? » Une table de hachage des
 * 70 560 masques repond en temps constant. Le balayage devient donc
 *
 *      2^32 graines x 5 generateurs x 2 echantillonneurs = 4,3e10 essais
 *
 * pour couvrir l'archive ENTIERE — et non par tirage. C'est deux heures sur un coeur, et
 * une demi-heure sur quatre.
 *
 * CE QUE CELA FERME
 * =================
 * « Un tirage quelconque de l'archive est-il le premier tirage produit par un generateur
 * moderne amorce avec une graine de 32 bits, quelle qu'en soit l'origine ? »
 *
 * Une reponse positive donne la graine, donc l'etat, donc tout ce qui suit. Une
 * coincidence fausse a une probabilite de 70 560/C(80,20) = 2,0e-14 par essai ; sur 4,3e10
 * essais, l'esperance de faux vaut 8,6e-4. Le resultat reste binaire.
 *
 * USAGE
 * =====
 *   graine_exhaustive cibles.bin debut fin [pas_journal]
 *     cibles.bin : suite d'enregistrements {int64 ts, uint64 m0, uint64 m1}
 *     debut, fin : bornes du balayage de graine (fin exclue), en decimal
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>

#define POOL  80
#define DRAWN 20

typedef struct { int64_t ts; uint64_t m0, m1; } Cible;

#define PCG64_MULT ( (((unsigned __int128)0x2360ED051FC65DA4ULL) << 64) \
                   | (unsigned __int128)0x4385DF649FCCF645ULL )

typedef struct {
    uint64_t s64;
    uint64_t s4[4];
    uint32_t s128[4];
    uint64_t pcg_s, pcg_i;
    unsigned __int128 p64_s, p64_i;
} Etat;

static uint64_t sm64_next(uint64_t *s)
{
    uint64_t z = (*s += 0x9E3779B97F4A7C15ULL);
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31);
}
static uint64_t rotl64(uint64_t x, int k) { return (x << k) | (x >> (64 - k)); }
static uint32_t rotl32(uint32_t x, int k) { return (x << k) | (x >> ((32 - k) & 31)); }

static void amorce(Etat *e, uint64_t graine)
{
    uint64_t t = graine;
    e->s64 = graine;
    for (int i = 0; i < 4; i++) e->s4[i] = sm64_next(&t);
    t = graine;
    for (int i = 0; i < 4; i++) e->s128[i] = (uint32_t)(sm64_next(&t) >> 32);
    e->pcg_s = 0; e->pcg_i = (graine << 1) | 1;
    e->pcg_s = e->pcg_s * 6364136223846793005ULL + e->pcg_i;
    e->pcg_s += graine;
    e->pcg_s = e->pcg_s * 6364136223846793005ULL + e->pcg_i;
    e->p64_i = ((unsigned __int128)graine << 1) | 1;
    e->p64_s = 0;
    e->p64_s = e->p64_s * PCG64_MULT + e->p64_i;
    e->p64_s += graine;
    e->p64_s = e->p64_s * PCG64_MULT + e->p64_i;
}

static uint32_t suivant(Etat *e, int g)
{
    switch (g) {
    case 0: return (uint32_t)(sm64_next(&e->s64) >> 32);
    case 1: {
        uint64_t r = rotl64(e->s4[0] + e->s4[3], 23) + e->s4[0];
        uint64_t t = e->s4[1] << 17;
        e->s4[2] ^= e->s4[0]; e->s4[3] ^= e->s4[1];
        e->s4[1] ^= e->s4[2]; e->s4[0] ^= e->s4[3];
        e->s4[2] ^= t;       e->s4[3] = rotl64(e->s4[3], 45);
        return (uint32_t)(r >> 32);
    }
    case 2: {
        uint32_t r = rotl32(e->s128[1] * 5u, 7) * 9u;
        uint32_t t = e->s128[1] << 9;
        e->s128[2] ^= e->s128[0]; e->s128[3] ^= e->s128[1];
        e->s128[1] ^= e->s128[2]; e->s128[0] ^= e->s128[3];
        e->s128[2] ^= t;         e->s128[3] = rotl32(e->s128[3], 11);
        return r;
    }
    case 3: {
        uint64_t old = e->pcg_s;
        e->pcg_s = old * 6364136223846793005ULL + e->pcg_i;
        uint32_t xs = (uint32_t)(((old >> 18) ^ old) >> 27);
        return rotl32(xs, (int)(64 - (old >> 59)) & 31);
    }
    case 4: {
        unsigned __int128 old = e->p64_s;
        e->p64_s = old * PCG64_MULT + e->p64_i;
        uint64_t hi = (uint64_t)(old >> 64), lo = (uint64_t)old;
        uint64_t r = rotl64(hi ^ lo, (int)(64 - (hi >> 58)) & 63);
        return (uint32_t)(r >> 32);
    }
    }
    return 0;
}
#define NGEN 5
static const char *NOMGEN[NGEN] = {
    "splitmix64", "xoshiro256++", "xoshiro128**", "pcg32", "pcg64"
};
/* ------------------------------------------------------------- echantillonneurs
 *
 * SIX, ET C'EST LE POINT. Les §200 a §205 ne balayaient que la troncature et le modulo,
 * c'est-a-dire deux facons de reduire UN mot de 32 bits a une classe. Si la machine
 * utilise nextDouble(), Lemire, ou un modulo debiaise, tous ces balayages testaient un
 * modele qui ne pouvait pas apparier — et leur resultat negatif ne disait rien de la
 * graine. Un balayage exhaustif en graines mais borgne en echantillonneurs ne prouve
 * rien : il faut les deux.
 *
 *   0  troncature        c = (w * 80) >> 32
 *   1  modulo            c = w % 80
 *   2  modulo debiaise   rejet si w >= 2^32 - (2^32 mod 80), puis w % 80
 *   3  Lemire            m = w * 80 ; rejet si (m & 0xFFFFFFFF) < (2^32 mod 80) ;
 *                        c = m >> 32
 *   4  double 53 bits    deux mots -> u = ((w1>>5)*2^26 + (w2>>6)) / 2^53 ; c = 80u
 *   5  sept bits bas     c = w & 127 ; rejet si c >= 80
 */
#define NECH 6
static const char *NOMECH[NECH] = {
    "troncature", "modulo", "modulo debiaise", "Lemire", "double 53 bits",
    "sept bits bas"
};
#define SEUIL80 ((uint32_t)((1ULL << 32) % 80))   /* 2^32 mod 80 = 16 */

/* ------------------------------------------------------ table de hachage des cibles */

static uint64_t *Ha, *Hb;         /* masques ; (0,0) = case vide, impossible pour un vrai
                                     tirage puisqu'il porte vingt bits */
static long     *Hi;              /* indice de la cible */
static uint64_t  HMASK;

static uint64_t melange(uint64_t a, uint64_t b)
{
    uint64_t z = a * 0x9E3779B97F4A7C15ULL ^ b * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 31)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 29);
}

static void inserer(uint64_t a, uint64_t b, long idx)
{
    uint64_t h = melange(a, b) & HMASK;
    while (Ha[h] || Hb[h]) {
        if (Ha[h] == a && Hb[h] == b) return;      /* doublon : on garde le premier */
        h = (h + 1) & HMASK;
    }
    Ha[h] = a; Hb[h] = b; Hi[h] = idx;
}

static long chercher(uint64_t a, uint64_t b)
{
    uint64_t h = melange(a, b) & HMASK;
    while (Ha[h] || Hb[h]) {
        if (Ha[h] == a && Hb[h] == b) return Hi[h];
        h = (h + 1) & HMASK;
    }
    return -1;
}

static int engendre(Etat *e, int g, int s, uint64_t *m0, uint64_t *m1)
{
    uint64_t a = 0, b = 0;
    int pris = 0, tours = 0;
    while (pris < DRAWN) {
        if (++tours > 400) return 0;
        int c;
        uint32_t w = suivant(e, g);
        switch (s) {
        case 0: c = (int)(((uint64_t)w * POOL) >> 32); break;
        case 1: c = (int)(w % POOL); break;
        case 2:
            if (w >= (uint32_t)(0xFFFFFFFFu - SEUIL80 + 1)) continue;
            c = (int)(w % POOL);
            break;
        case 3: {
            uint64_t m = (uint64_t)w * POOL;
            if ((uint32_t)m < SEUIL80) continue;
            c = (int)(m >> 32);
            break;
        }
        case 4: {
            uint32_t w2 = suivant(e, g);
            double u = ((double)(w >> 5) * 67108864.0 + (double)(w2 >> 6))
                     / 9007199254740992.0;
            c = (int)(u * POOL);
            if (c >= POOL) c = POOL - 1;
            break;
        }
        default:
            c = (int)(w & 127u);
            if (c >= POOL) continue;
            break;
        }
        uint64_t *p = (c < 64) ? &a : &b;
        int k = (c < 64) ? c : c - 64;
        if (!((*p >> k) & 1ULL)) { *p |= 1ULL << k; pris++; }
    }
    *m0 = a; *m1 = b;
    return 1;
}

/* Le pilote ci-dessous est compile seul. `graine_plages.c` inclut ce fichier avec
   SANS_MAIN defini afin de reutiliser EXACTEMENT les memes generateurs, les memes six
   echantillonneurs et la meme table de hachage — ceux que le temoin 30/30 du §211 a
   valides. Une seconde copie serait une seconde chose qui peut deriver. */
#ifndef SANS_MAIN

int main(int argc, char **argv)
{
    if (argc < 4) {
        fprintf(stderr, "usage: %s cibles.bin debut fin\n", argv[0]);
        return 2;
    }
    FILE *f = fopen(argv[1], "rb");
    if (!f) { perror("cibles"); return 2; }
    fseek(f, 0, SEEK_END);
    long nc = ftell(f) / (long)sizeof(Cible);
    fseek(f, 0, SEEK_SET);
    Cible *C = malloc((size_t)nc * sizeof(Cible));
    if (fread(C, sizeof(Cible), (size_t)nc, f) != (size_t)nc) {
        fprintf(stderr, "lecture incomplete\n"); return 2;
    }
    fclose(f);

    uint64_t taille = 1;
    while (taille < (uint64_t)nc * 4) taille <<= 1;
    HMASK = taille - 1;
    Ha = calloc(taille, sizeof(uint64_t));
    Hb = calloc(taille, sizeof(uint64_t));
    Hi = calloc(taille, sizeof(long));
    for (long i = 0; i < nc; i++) inserer(C[i].m0, C[i].m1, i);

    unsigned long long deb = strtoull(argv[2], NULL, 10);
    unsigned long long fin = strtoull(argv[3], NULL, 10);
    double essais = (double)(fin - deb) * NGEN * NECH;
    printf("cibles %ld ; table 2^%d ; graines [%llu, %llu) ; essais %.4e\n",
           nc, __builtin_ctzll(taille), deb, fin, essais);
    printf("faux attendus %.3e (%ld/C(80,20) = %.2e par essai)\n",
           essais * (double)nc / 3.5353e18, nc, (double)nc / 3.5353e18);
    fflush(stdout);

    long trouves = 0;
    unsigned long long jalon = deb;
    for (unsigned long long graine = deb; graine < fin; graine++) {
        for (int g = 0; g < NGEN; g++) {
            Etat e;
            amorce(&e, graine);
            for (int s = 0; s < NECH; s++) {
                Etat e2 = e;
                uint64_t a, b;
                if (!engendre(&e2, g, s, &a, &b)) continue;
                long idx = chercher(a, b);
                if (idx >= 0) {
                    printf("APPARIEMENT graine %llu generateur %s echantillonneur %s "
                           "cible %ld ts %lld\n", graine, NOMGEN[g], NOMECH[s],
                           idx, (long long)C[idx].ts);
                    fflush(stdout);
                    trouves++;
                }
            }
        }
        if (graine - jalon >= 100000000ULL) {
            jalon = graine;
            printf("  ... graine %llu (%.1f %%)\n", graine,
                   100.0 * (double)(graine - deb) / (double)(fin - deb));
            fflush(stdout);
        }
    }
    printf("TERMINE [%llu, %llu) : %ld appariement(s) sur %.4e essais\n",
           deb, fin, trouves, essais);
    free(C); free(Ha); free(Hb); free(Hi);
    return 0;
}

#endif  /* SANS_MAIN */
