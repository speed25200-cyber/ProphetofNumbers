/* graine_moderne.c — LE BALAYAGE DE GRAINE DES GENERATEURS MODERNES.
 *
 * POURQUOI CET OUTIL EXISTE
 * =========================
 * Le §199 a mesure la frontiere du dossier : les detecteurs de relation et les cribles
 * d'etat attrapent les familles classiques et sont AVEUGLES a toute conception moderne a
 * un seul pas — splitmix64, PCG, xoshiro. Ces familles restent donc entierement ouvertes,
 * et c'est la seule chose qui reste debout.
 *
 * Elles ont pourtant un point faible, et c'est celui que l'utilisateur du depot avait
 * nomme : LA GRAINE. Un etat de 64 ou 128 bits est hors de portee ; une graine tiree de
 * l'horloge ne l'est pas. L'archive donne l'horodatage EXACT de chaque tirage, a la
 * seconde. Si la machine s'amorce sur l'heure, la graine est connue a une fenetre pres.
 *
 * Les §161 et suivants ont balaye les graines d'horloge pour glibc random(), Java 48 bits
 * et V8. Aucun n'a couvert les generateurs modernes. Ce fichier comble ce trou.
 *
 * CE QU'IL FAIT
 * =============
 * Pour chaque tirage cible, pour chaque graine candidate dans une fenetre autour de son
 * horodatage, pour chaque generateur et chaque echantillonneur : engendrer les vingt
 * classes et comparer au masque observe.
 *
 * Une coincidence fausse a une probabilite de 1/C(80,20) = 2,8e-19 par essai. Meme a
 * 10^12 essais l'esperance de faux est de 2,8e-7 : TOUT appariement est reel.
 *
 * USAGE
 * =====
 *   graine_moderne cibles.bin mode fenetre [pas]
 *     cibles.bin : suite d'enregistrements {int64 ts, uint64 m0, uint64 m1}
 *     mode       : 0 = graine en SECONDES (ts + delta)
 *                  1 = graine en MILLISECONDES (ts*1000 + delta)
 *                  2 = graine en secondes, mais l'etat avance de `saut` tirages avant
 *                      le tirage cible (amorcage en debut de nuit)
 *                  3 = ECHAUFFEMENT : graine en secondes, et l'on balaye le nombre de
 *                      mots jetes apres l'amorcage, de 0 a `saut`. C'est le cas qu'un
 *                      balayage de graine simple manque : la machine s'amorce, consomme
 *                      quelques mots pour autre chose, puis tire.
 *     fenetre    : |delta| maximal
 *     pas        : increment de delta (defaut 1)
 *
 * Ecrit sur la sortie standard une ligne par appariement, et un resume.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#define POOL  80
#define DRAWN 20

typedef struct { int64_t ts; uint64_t m0, m1; } Cible;

/* le multiplicateur de PCG64 tient sur 128 bits : un litteral ULL le TRONQUE
 * silencieusement (gcc ne rend qu'un avertissement). On le construit en deux moities. */
#define PCG64_MULT ( (((unsigned __int128)0x2360ED051FC65DA4ULL) << 64) \
                   | (unsigned __int128)0x4385DF649FCCF645ULL )

/* ------------------------------------------------------------------ generateurs */

typedef struct {
    uint64_t s64;               /* splitmix64 */
    uint64_t s4[4];             /* xoshiro256 */
    uint32_t s128[4];           /* xoshiro128 */
    uint64_t pcg_s, pcg_i;      /* pcg32 */
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

/* chaque generateur rend un mot de 32 bits */
static uint32_t suivant(Etat *e, int g)
{
    switch (g) {
    case 0:                                            /* splitmix64 */
        return (uint32_t)(sm64_next(&e->s64) >> 32);
    case 1: {                                          /* xoshiro256++ */
        uint64_t r = rotl64(e->s4[0] + e->s4[3], 23) + e->s4[0];
        uint64_t t = e->s4[1] << 17;
        e->s4[2] ^= e->s4[0]; e->s4[3] ^= e->s4[1];
        e->s4[1] ^= e->s4[2]; e->s4[0] ^= e->s4[3];
        e->s4[2] ^= t;       e->s4[3] = rotl64(e->s4[3], 45);
        return (uint32_t)(r >> 32);
    }
    case 2: {                                          /* xoshiro128** */
        uint32_t r = rotl32(e->s128[1] * 5u, 7) * 9u;
        uint32_t t = e->s128[1] << 9;
        e->s128[2] ^= e->s128[0]; e->s128[3] ^= e->s128[1];
        e->s128[1] ^= e->s128[2]; e->s128[0] ^= e->s128[3];
        e->s128[2] ^= t;         e->s128[3] = rotl32(e->s128[3], 11);
        return r;
    }
    case 3: {                                          /* pcg32 xsh-rr */
        uint64_t old = e->pcg_s;
        e->pcg_s = old * 6364136223846793005ULL + e->pcg_i;
        uint32_t xs = (uint32_t)(((old >> 18) ^ old) >> 27);
        return rotl32(xs, (int)(64 - (old >> 59)) & 31);
    }
    case 4: {                                          /* pcg64 xsl-rr, 32 bits hauts */
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

/* ------------------------------------------------------------- echantillonneurs */
/* s = 0 : troncature  c = (w * 80) >> 32     s = 1 : modulo  c = w % 80 */
#define NECH 2
static const char *NOMECH[NECH] = { "troncature", "modulo" };

/* engendre un tirage ; rend 0 si plus de nmax mots ont ete consommes */
static int engendre(Etat *e, int g, int s, uint64_t *m0, uint64_t *m1, int nmax)
{
    uint64_t a = 0, b = 0;
    int pris = 0, tours = 0;
    while (pris < DRAWN) {
        if (++tours > nmax) return 0;
        uint32_t w = suivant(e, g);
        int c = (s == 0) ? (int)(((uint64_t)w * POOL) >> 32) : (int)(w % POOL);
        uint64_t *p = (c < 64) ? &a : &b;
        int k = (c < 64) ? c : c - 64;
        if (!((*p >> k) & 1ULL)) { *p |= 1ULL << k; pris++; }
    }
    *m0 = a; *m1 = b;
    return 1;
}

int main(int argc, char **argv)
{
    if (argc < 4) {
        fprintf(stderr, "usage: %s cibles.bin mode fenetre [pas] [saut]\n", argv[0]);
        return 2;
    }
    const char *chemin = argv[1];
    int mode = atoi(argv[2]);
    long fen = atol(argv[3]);
    long pas = (argc > 4) ? atol(argv[4]) : 1;
    int saut = (argc > 5) ? atoi(argv[5]) : 0;

    FILE *f = fopen(chemin, "rb");
    if (!f) { perror("cibles"); return 2; }
    fseek(f, 0, SEEK_END);
    long taille = ftell(f);
    fseek(f, 0, SEEK_SET);
    long nc = taille / (long)sizeof(Cible);
    Cible *C = malloc((size_t)nc * sizeof(Cible));
    if (fread(C, sizeof(Cible), (size_t)nc, f) != (size_t)nc) {
        fprintf(stderr, "lecture incomplete\n"); return 2;
    }
    fclose(f);

    long nd = 2 * fen / pas + 1;
    double essais = (double)nc * (double)nd * NGEN * NECH
                  * ((mode == 3) ? (double)(saut + 1) : 1.0);
    printf("cibles %ld ; mode %d ; fenetre %ld ; pas %ld ; saut %d\n",
           nc, mode, fen, pas, saut);
    printf("graines par cible %ld ; essais totaux %.3e\n", nd, essais);
    printf("faux attendus %.3e (1/C(80,20) = 2.8e-19 par essai)\n", essais * 2.8e-19);
    fflush(stdout);

    long trouves = 0;
    for (long i = 0; i < nc; i++) {
        int64_t base = (mode == 1) ? C[i].ts * 1000 : C[i].ts;
        for (int g = 0; g < NGEN; g++)
            for (int s = 0; s < NECH; s++)
                for (long d = -fen; d <= fen; d += pas) {
                    int wmax = (mode == 3) ? saut : 0;
                    for (int w = 0; w <= wmax; w++) {
                        Etat e;
                        amorce(&e, (uint64_t)(base + d));
                        uint64_t a, b;
                        if (mode == 3)
                            for (int k = 0; k < w; k++) suivant(&e, g);
                        if (mode == 2)
                            for (int k = 0; k < saut; k++)
                                if (!engendre(&e, g, s, &a, &b, 200)) goto suivant_w;
                        if (!engendre(&e, g, s, &a, &b, 200)) goto suivant_w;
                        if (a == C[i].m0 && b == C[i].m1) {
                            printf("APPARIEMENT cible %ld ts %lld generateur %s "
                                   "echantillonneur %s graine %lld (delta %ld) "
                                   "echauffement %d\n",
                                   i, (long long)C[i].ts, NOMGEN[g], NOMECH[s],
                                   (long long)(base + d), d, w);
                            fflush(stdout);
                            trouves++;
                        }
                    suivant_w: ;
                    }
                }
        if ((i + 1) % 500 == 0) {
            printf("  ... %ld/%ld cibles\n", i + 1, nc);
            fflush(stdout);
        }
    }
    printf("TERMINE : %ld appariement(s) sur %.3e essais\n", trouves, essais);
    free(C);
    return 0;
}
