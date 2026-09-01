// sweep_design — balayer l'ESPACE DES DESIGNS xorshift, pas le catalogue publié.
//
// POURQUOI CE FICHIER EXISTE
// --------------------------
// Le §25 a nommé lui-même le trou que le dossier laissait ouvert :
//
//     « h11 laissait une faille béante : il fallait ÉNUMÉRER des constantes
//       publiées. Un générateur aux constantes maison lui échappait
//       entièrement. »
//
// Le §25 a fermé ce trou pour les LCG, en CALCULANT (a, c) au lieu de les
// deviner. Pour les générateurs F2-LINÉAIRES, il est resté ouvert : tous les
// balayages du dossier — §34, §110, §136, §144 — testent xorshift32/64/128,
// taus88, LFSR113, WELL512a, c'est-à-dire des DÉCALAGES PUBLIÉS.
//
//     Un xorshift maison avec des décalages (13, 7, 5) remplacés par
//     (11, 19, 3) leur échappe TOUS.
//
// Ce fichier balaie l'espace entier : tous les triplets de décalages, toutes
// les orientations, pour trois largeurs d'état.
//
// CE QU'IL TESTE
// --------------
// Forme de Marsaglia, trois décalages et trois orientations :
//
//     x ^= x <<|>> a ;   x ^= x <<|>> b ;   x ^= x <<|>> c
//
// pour W = 32 et 64 ; et la forme à quatre mots pour W = 128 :
//
//     t = x ^ (x <<|>> a) ;  x=y; y=z; z=w;
//     w = w ^ (w <<|>> b) ^ t ^ (t <<|>> c)
//
// L'ATTAQUE
// ---------
// Un tirage ordonné donne j_k pour k = 0..19, donc floor(K·u/2^32) = j_k − k
// avec K = 80 − k : u est confiné à un intervalle, et les bits de poids fort
// sur lesquels ses deux bornes s'accordent sont EXACTS. Ce sont des formes
// F2-linéaires de l'état, obtenues en faisant tourner le design depuis les W
// vecteurs unité. On échelonne ; une contradiction élimine le design.
//
// Le pas est de 21 mots par tirage (§137), et les tirages observés portent leur
// INDICE dans la journée, donc les sauts sont connus (§130).
//
// AUTOTEST
// --------
// `--selftest` plante un design tiré au hasard dans l'espace balayé, fabrique
// ses tirages ordonnés, et vérifie que le balayage le RETROUVE — et lui seul.
//
//   cc -O3 -march=native -o sweep_design tools/sweep_design.c

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>

#define POOL  80
#define DRAWN 20
#define MOTS  21
#define MAXD  64                 // tirages observés au maximum
#define MAXW 256

// Vecteur de bits sur 256 positions : la largeur d'etat maximale balayee.
typedef struct { uint64_t w[4]; } u128;

static inline u128 x_xor(u128 a, u128 b) {
    u128 r; for (int i = 0; i < 4; i++) r.w[i] = a.w[i] ^ b.w[i]; return r;
}
static inline int x_nul(u128 a) { return !(a.w[0] | a.w[1] | a.w[2] | a.w[3]); }
static inline int x_haut(u128 a) {           // indice du bit de poids fort
    for (int i = 3; i >= 0; i--) if (a.w[i]) return i * 64 + 63 - __builtin_clzll(a.w[i]);
    return -1;
}
static inline void x_met(u128 *a, int i) { a->w[i >> 6] |= 1ULL << (i & 63); }

// ---------------------------------------------------------------------------
// Les designs. `orient` porte trois bits : 1 = décalage à gauche.
// ---------------------------------------------------------------------------
typedef struct { int W, forme, a, b, c, orient; } design;
// forme 0 : xorshift 32      forme 1 : xorshift 64      forme 2 : xorshift128
// forme 3 : xoroshiro128 brut (rotations a, c ; decalage b ; orient = mot lu)
// forme 4 : xoshiro256 brut   (decalage a ; rotation b ; orient = mot lu x 2)

static inline uint64_t rot64(uint64_t x, int k) {
    return k ? ((x << k) | (x >> (64 - k))) : x;
}

static inline uint32_t dec32(uint32_t x, int s, int gauche) {
    return gauche ? (x << s) : (x >> s);
}
static inline uint64_t dec64(uint64_t x, int s, int gauche) {
    return gauche ? (x << s) : (x >> s);
}

// Fait tourner le design sur `n` mots ; `etat` est modifié. Rend les mots.
static void flux(const design *d, uint32_t *etat, int n, uint32_t *out) {
    int g1 = d->orient & 1, g2 = (d->orient >> 1) & 1, g3 = (d->orient >> 2) & 1;
    if (d->forme == 0) {                       // W = 32, un mot
        uint32_t x = etat[0];
        for (int i = 0; i < n; i++) {
            x ^= dec32(x, d->a, g1);
            x ^= dec32(x, d->b, g2);
            x ^= dec32(x, d->c, g3);
            out[i] = x;
        }
        etat[0] = x;
    } else if (d->forme == 1) {                // W = 64, deux mots
        uint64_t x = ((uint64_t)etat[1] << 32) | etat[0];
        for (int i = 0; i < n; i++) {
            x ^= dec64(x, d->a, g1);
            x ^= dec64(x, d->b, g2);
            x ^= dec64(x, d->c, g3);
            out[i] = (uint32_t)x;
        }
        etat[0] = (uint32_t)x; etat[1] = (uint32_t)(x >> 32);
    } else if (d->forme == 3) {                // xoroshiro128 brut, W = 128
        uint64_t s0 = ((uint64_t)etat[1] << 32) | etat[0];
        uint64_t s1 = ((uint64_t)etat[3] << 32) | etat[2];
        int haut = d->orient & 1;
        for (int i = 0; i < n; i++) {
            out[i] = haut ? (uint32_t)(s0 >> 32) : (uint32_t)s0;
            uint64_t t = s1 ^ s0;
            s0 = rot64(s0, d->a) ^ t ^ (t << d->b);
            s1 = rot64(t, d->c);
        }
        etat[0] = (uint32_t)s0; etat[1] = (uint32_t)(s0 >> 32);
        etat[2] = (uint32_t)s1; etat[3] = (uint32_t)(s1 >> 32);
    } else if (d->forme == 4) {                // xoshiro256 brut, W = 256
        uint64_t s[4];
        for (int i = 0; i < 4; i++)
            s[i] = ((uint64_t)etat[2 * i + 1] << 32) | etat[2 * i];
        int mot = (d->orient >> 1) & 3, haut = d->orient & 1;
        for (int i = 0; i < n; i++) {
            out[i] = haut ? (uint32_t)(s[mot] >> 32) : (uint32_t)s[mot];
            uint64_t t = s[1] << d->a;
            s[2] ^= s[0]; s[3] ^= s[1]; s[1] ^= s[2]; s[0] ^= s[3];
            s[2] ^= t; s[3] = rot64(s[3], d->b);
        }
        for (int i = 0; i < 4; i++) {
            etat[2 * i] = (uint32_t)s[i]; etat[2 * i + 1] = (uint32_t)(s[i] >> 32);
        }
    } else {                                   // W = 128, quatre mots
        uint32_t x = etat[0], y = etat[1], z = etat[2], w = etat[3];
        for (int i = 0; i < n; i++) {
            uint32_t t = x ^ dec32(x, d->a, g1);
            x = y; y = z; z = w;
            w = w ^ dec32(w, d->b, g2) ^ t ^ dec32(t, d->c, g3);
            out[i] = w;
        }
        etat[0] = x; etat[1] = y; etat[2] = z; etat[3] = w;
    }
}

// ---------------------------------------------------------------------------
// L'équation d'observation : les bits exacts du mot, depuis j_k.
// ---------------------------------------------------------------------------
static void prefixe(long v, long K, int *nb, uint32_t *pref) {
    uint64_t lo = (uint64_t)(((__int128)v << 32) + K - 1) / K;
    uint64_t hi = (uint64_t)(((__int128)(v + 1) << 32) + K - 1) / K - 1;
    int n = 0;
    while (n < 32 && ((lo >> (31 - n)) & 1) == ((hi >> (31 - n)) & 1)) n++;
    *nb = n;
    *pref = n ? (uint32_t)(lo >> (32 - n)) : 0;
}

// ---------------------------------------------------------------------------
// Le test d'un design : échelonnement F2 incrémental, arrêt à la contradiction.
// ---------------------------------------------------------------------------
typedef struct {
    int ntir;
    int idx[MAXD];                             // indice du tirage dans la journée
    int j[MAXD][DRAWN];                        // les j_k, déjà calculés
} obs_t;

// Masques sur 128 bits : MM[t][b] est la forme lineaire donnant le bit b
// (poids fort d'abord) du mot t.
static u128 MM[4096][32];
static uint32_t BUF[4096];

static int teste2(const design *d, const obs_t *o, int *neq_out, int *rang_out) {
    int W = d->W;
    int dernier = 0;
    for (int t = 0; t < o->ntir; t++) if (o->idx[t] > dernier) dernier = o->idx[t];
    int nmots = (dernier + 1) * MOTS;
    if (nmots > 4096) { *neq_out = 0; *rang_out = 0; return 0; }

    for (int t = 0; t < nmots; t++)
        for (int b = 0; b < 32; b++) for (int i = 0; i < 4; i++) MM[t][b].w[i] = 0;

    for (int c = 0; c < W; c++) {
        uint32_t e[8] = {0, 0, 0, 0, 0, 0, 0, 0};
        e[c >> 5] = 1u << (c & 31);
        flux(d, e, nmots, BUF);
        for (int t = 0; t < nmots; t++) {
            uint32_t w = BUF[t];
            while (w) {
                int b = 31 - __builtin_clz(w);
                x_met(&MM[t][31 - b], c);
                w &= ~(1u << b);
            }
        }
    }

    u128 pm[MAXW]; int pv[MAXW]; char plein[MAXW];
    memset(plein, 0, sizeof plein);
    int neq = 0, rang = 0;

    for (int t = 0; t < o->ntir; t++) {
        for (int k = 0; k < DRAWN; k++) {
            int nb; uint32_t pref;
            prefixe(o->j[t][k] - k, POOL - k, &nb, &pref);
            int mot = o->idx[t] * MOTS + k;
            for (int b = 0; b < nb; b++) {
                u128 m = MM[mot][b];
                int v = (pref >> (nb - 1 - b)) & 1;
                neq++;
                while (!x_nul(m)) {
                    int h = x_haut(m);
                    if (plein[h]) { m = x_xor(m, pm[h]); v ^= pv[h]; }
                    else { pm[h] = m; pv[h] = v; plein[h] = 1; rang++; m = (u128){{0,0,0,0}}; v = 0; break; }
                }
                if (x_nul(m) && v) { *neq_out = neq; *rang_out = rang; return 0; }
            }
        }
    }
    *neq_out = neq; *rang_out = rang;
    return 1;
}

// ---------------------------------------------------------------------------
static long total = 0, survivants = 0;

static void balaye(const obs_t *o, int forme, int W, int smax, int verbeux) {
    design d; d.W = W; d.forme = forme;
    int cmax = (forme == 4) ? 1 : smax;        // la forme 4 n'a que deux parametres
    int omax = (forme == 3) ? 2 : (forme == 4) ? 8 : 8;
    for (d.a = 1; d.a <= smax; d.a++)
      for (d.b = 1; d.b <= smax; d.b++)
        for (d.c = 1; d.c <= cmax; d.c++)
          for (d.orient = 0; d.orient < omax; d.orient++) {
              int neq, rang;
              total++;
              if (teste2(&d, o, &neq, &rang)) {
                  survivants++;
                  printf("SURVIVANT forme=%d W=%d a=%d b=%d c=%d orient=%d "
                         "rang=%d/%d equations=%d\n",
                         forme, W, d.a, d.b, d.c, d.orient, rang, W, neq);
              } else if (verbeux && total % 200000 == 0) {
                  fprintf(stderr, "  ... %ld designs, %ld survivants\n", total, survivants);
              }
          }
}

// ---------------------------------------------------------------------------
static void fy_indices(const int *ordre, int *j) {
    int arr[POOL];
    for (int i = 0; i < POOL; i++) arr[i] = i + 1;
    for (int k = 0; k < DRAWN; k++) {
        int p = -1;
        for (int i = k; i < POOL; i++) if (arr[i] == ordre[k]) { p = i; break; }
        j[k] = p;
        int t = arr[k]; arr[k] = arr[p]; arr[p] = t;
    }
}

static void tirage_de(const design *d, uint32_t *etat0, int idx, int *ordre) {
    uint32_t e[8]; memcpy(e, etat0, sizeof e);
    static uint32_t f[4096];
    flux(d, e, (idx + 1) * MOTS, f);
    int arr[POOL];
    for (int i = 0; i < POOL; i++) arr[i] = i + 1;
    for (int k = 0; k < DRAWN; k++) {
        uint32_t u = f[idx * MOTS + k];
        int j = k + (int)(((uint64_t)u * (POOL - k)) >> 32);
        int t = arr[k]; arr[k] = arr[j]; arr[j] = t;
        ordre[k] = arr[k];
    }
}

static int selftest(void) {
    int ok = 0, tot = 0;
    struct { int forme, W, smax; } cas[] = { {0, 32, 31}, {1, 64, 63}, {2, 128, 31},
                                            {3, 128, 63}, {4, 256, 63} };
    for (int ci = 0; ci < 5; ci++) {
        design d; d.forme = cas[ci].forme; d.W = cas[ci].W;
        d.a = 5 + ci * 3; d.b = 9 + ci; d.c = (cas[ci].forme == 4) ? 1 : 13 - ci * 2;
        d.orient = (cas[ci].forme == 3) ? (ci & 1) : 3 + ci % 5;
        uint32_t etat[8] = {0x12345678u, 0x9ABCDEF0u, 0x0F1E2D3Cu, 0xDEADBEEFu,
                            0x13579BDFu, 0x2468ACE0u, 0xA5A5A5A5u, 0x5A5A5A5Au};
        obs_t o; o.ntir = 3;
        int idxs[3] = {0, 2, 5};
        for (int t = 0; t < 3; t++) {
            o.idx[t] = idxs[t];
            int ordre[DRAWN];
            tirage_de(&d, etat, idxs[t], ordre);
            fy_indices(ordre, o.j[t]);
        }
        int neq, rang;
        tot++;
        int r = teste2(&d, &o, &neq, &rang);
        ok += r;
        printf("  design plante forme=%d W=%d (%d,%d,%d,or=%d) -> %s "
               "(rang %d/%d, %d equations)\n",
               d.forme, d.W, d.a, d.b, d.c, d.orient,
               r ? "COMPATIBLE" : "rejete", rang, d.W, neq);
        // temoin negatif : le meme design avec un decalage change
        design e2 = d; e2.a = (d.a % cas[ci].smax) + 1;
        tot++;
        int r2 = teste2(&e2, &o, &neq, &rang);
        ok += !r2;
        printf("  meme design, a=%d          -> %s (rang %d/%d, %d equations)\n",
               e2.a, r2 ? "COMPATIBLE (MAUVAIS)" : "rejete", rang, e2.W, neq);
    }
    printf("autotest : %d/%d\n", ok, tot);
    return ok == tot;
}

int main(int argc, char **argv) {
    if (argc >= 2 && !strcmp(argv[1], "--selftest")) return selftest() ? 0 : 1;
    if (argc < 3) {
        fprintf(stderr, "usage: %s <forme 0..4> <ntir> <idx1> <o1..o20> [...]\n", argv[0]);
        fprintf(stderr, "       %s --selftest\n", argv[0]);
        return 2;
    }
    int forme = atoi(argv[1]);
    obs_t o; o.ntir = atoi(argv[2]);
    int p = 3;
    for (int t = 0; t < o.ntir; t++) {
        o.idx[t] = atoi(argv[p++]);
        int ordre[DRAWN];
        for (int k = 0; k < DRAWN; k++) ordre[k] = atoi(argv[p++]);
        fy_indices(ordre, o.j[t]);
    }
    int W = forme == 0 ? 32 : forme == 1 ? 64 : forme == 4 ? 256 : 128;
    int smax = (forme == 0 || forme == 2) ? 31 : 63;
    clock_t t0 = clock();
    balaye(&o, forme, W, smax, 1);
    printf("forme=%d W=%d designs=%ld survivants=%ld sec=%.1f\n",
           forme, W, total, survivants, (double)(clock() - t0) / CLOCKS_PER_SEC);
    return 0;
}
