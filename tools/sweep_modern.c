// sweep_modern — balayage de graines contre un tirage ORDONNÉ, pour les
// familles de générateurs que `sweep_order.c` ne couvre pas.
//
// Ce que ce programme ferme, et pourquoi il fallait le fermer
// ---------------------------------------------------------------------
// §34 du rapport nomme lui-même ce qu'il laisse ouvert : « un générateur
// dont l'état ne suit aucune récurrence affine ». La formule est juste mais
// trop large : elle range dans le même sac ce qui est hors de portée du
// calcul (une source matérielle, un chiffrement à clé de 128 bits) et ce qui
// ne l'est pas du tout — un générateur à compteur ou une construction ARX
// amorcés par un entier de 32 bits se balaient exactement comme un LCG, le
// pas est seulement plus cher.
//
// Les familles ajoutées ici sont toutes dans le second cas :
//
//   * les générateurs à COMPTEUR : Philox4x32-10 et ThreeFry4x32-20, tous
//     deux issus de Random123 et exposés par numpy/randomgen ;
//   * les constructions ARX employées comme générateur : ChaCha8, ChaCha12,
//     ChaCha20 — ChaCha12 est le générateur par défaut de la bibliothèque
//     `rand` de Rust, et son amorçage par entier (`seed_from_u64`) est
//     reproduit ici à la ligne près ;
//   * la famille « small fast » : sfc64 (Doty-Humphrey), jsf64 et jsf32
//     (Bob Jenkins), wyrand, romuTrio et romuDuoJr (Overton) ;
//   * les variantes non couvertes de familles déjà présentes dans
//     `sweep_order` : xoshiro256+ et xoshiro256++ (seul ** y figure), pcg32
//     et pcg64 avec un flux (increment) non par défaut et l'amorçage
//     officiel `pcg*_srandom_r`.
//
// Ce que ce programme NE change PAS
// ---------------------------------------------------------------------
// Les quatre échantillonneurs sont ceux de `sweep_order.c`, repris à
// l'identique : modulo + rejet, multiply-shift + rejet, Fisher-Yates
// modulaire, Fisher-Yates multiply-shift. Le protocole aussi : on travaille
// sur l'ORDRE de sortie (filtre 1/80 par pas, probabilité qu'une graine
// fausse survive ≈ (80!/60!)⁻¹ ≈ 1·10⁻³⁷), et on ne confirme PAS sur un
// second tirage — sous l'hypothèse du ré-amorçage chaque tirage a sa propre
// graine, et la confirmation jetterait précisément le cas cherché.
//
// Le piège de la borne 64
// ---------------------------------------------------------------------
// §34 le documente pour `nextInt` : certains échantillonneurs traitent une
// borne puissance de deux à part, en prenant les bits de poids FORT. Parmi
// 80, 79, …, 61 une seule borne est concernée — 64, au dix-septième pas.
// Les quatre échantillonneurs repris ici ne font AUCUN cas particulier :
// `u % m` et `(u·m) >> 32` s'appliquent uniformément, m = 64 compris. Le
// piège est donc évité par construction, et non par vigilance — mais il
// reste ouvert pour les échantillonneurs qui, eux, le font (c'est
// `sweep_java48` qui les couvre).
//
// Vérification des flux
// ---------------------------------------------------------------------
// `--kat` confronte chaque flux à une référence PUBLIÉE et extérieure au
// programme : vecteurs officiels Random123 pour Philox et ThreeFry,
// vecteurs IETF (RFC 8439 / draft-nir-cfrg-chacha20-poly1305-04) pour
// ChaCha, valeurs de référence de Vigna pour xoshiro256+/++, code de
// l'auteur pour romuDuoJr, wyrand, pcg32. La provenance de chaque bloc est
// donnée en commentaire au-dessus de ses constantes.
//
// `--selftest` fabrique, pour chacune des combinaisons famille ×
// échantillonneur, un tirage à partir d'une graine connue, puis balaie et
// exige de la retrouver. Une attaque qui ne retrouve pas son propre témoin
// ne prouve rien quand elle ne trouve rien.
//
//   cc -O3 -march=native -pthread -o sweep_modern sweep_modern.c
//   ./sweep_modern --kat
//   ./sweep_modern --selftest
//   ./sweep_modern --list
//   ./sweep_modern --stream <famille> <graine> <n>
//   ./sweep_modern [--fams a-b|a,b,c] <lo> <hi> <o1..o20>
//
// Les vingt numéros sont donnés DANS L'ORDRE DE SORTIE.

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <pthread.h>

#define POOL   80
#define DRAWN  20
#define NSAMP  4
#define MAXW   4096   // profondeur maximale du tampon de mots

// ---------------------------------------------------------------------------
// Primitives partagées
// ---------------------------------------------------------------------------

static inline uint64_t rotl64(uint64_t x, int k) { return (x << k) | (x >> (64 - k)); }
static inline uint64_t rotr64(uint64_t x, int k) { return (x >> k) | (x << (64 - k)); }
static inline uint32_t rotl32(uint32_t x, int k) { return k ? ((x << k) | (x >> (32 - k))) : x; }
static inline uint32_t rotr32(uint32_t x, int k) { return k ? ((x >> k) | (x << (32 - k))) : x; }

// splitmix64 — l'amorçage recommandé par les auteurs de xoshiro/romu.
static inline uint64_t sm64(uint64_t *x) {
    *x += 0x9E3779B97F4A7C15ULL;
    uint64_t z = *x;
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31);
}

// ---------------------------------------------------------------------------
// Philox4x32-10 — Random123, include/Random123/philox.h
//   M0 = 0xD2511F53, M1 = 0xCD9E8D57, W0 = 0x9E3779B9, W1 = 0xBB67AE85
//   round(ctr, key) : lo0,hi0 = M0·ctr0 ; lo1,hi1 = M1·ctr2
//                     out = { hi1^ctr1^key0, lo1, hi0^ctr3^key1, lo0 }
//   bumpkey : key0 += W0 ; key1 += W1   (avant chaque round sauf le premier)
// ---------------------------------------------------------------------------
static void philox4x32(const uint32_t in[4], const uint32_t k[2], int rounds,
                       uint32_t out[4]) {
    uint32_t c0 = in[0], c1 = in[1], c2 = in[2], c3 = in[3];
    uint32_t k0 = k[0], k1 = k[1];
    for (int r = 0; r < rounds; r++) {
        if (r) { k0 += 0x9E3779B9u; k1 += 0xBB67AE85u; }
        uint64_t p0 = (uint64_t)0xD2511F53u * c0;
        uint64_t p1 = (uint64_t)0xCD9E8D57u * c2;
        uint32_t lo0 = (uint32_t)p0, hi0 = (uint32_t)(p0 >> 32);
        uint32_t lo1 = (uint32_t)p1, hi1 = (uint32_t)(p1 >> 32);
        uint32_t n0 = hi1 ^ c1 ^ k0;
        uint32_t n1 = lo1;
        uint32_t n2 = hi0 ^ c3 ^ k1;
        uint32_t n3 = lo0;
        c0 = n0; c1 = n1; c2 = n2; c3 = n3;
    }
    out[0] = c0; out[1] = c1; out[2] = c2; out[3] = c3;
}

// ---------------------------------------------------------------------------
// ThreeFry4x32-20 — Random123, include/Random123/threefry.h
//   rotations R_32x4 : (10,26) (11,21) (13,27) (23,5) (6,20) (17,11) (25,10)
//                      (18,20), reprises cycliquement tous les huit tours
//   ks4 = 0x1BD11BDA ^ k0 ^ k1 ^ k2 ^ k3
//   injection de clé tous les quatre tours : X_i += ks[(r+i) mod 5], X3 += r
// ---------------------------------------------------------------------------
static const uint8_t TF_ROT[8][2] = {
    {10,26},{11,21},{13,27},{23,5},{6,20},{17,11},{25,10},{18,20}
};
static void threefry4x32(const uint32_t in[4], const uint32_t k[4], int rounds,
                         uint32_t out[4]) {
    uint32_t ks[5];
    ks[4] = 0x1BD11BDAu;
    for (int i = 0; i < 4; i++) { ks[i] = k[i]; ks[4] ^= k[i]; }
    uint32_t X0 = in[0] + ks[0], X1 = in[1] + ks[1];
    uint32_t X2 = in[2] + ks[2], X3 = in[3] + ks[3];
    for (int r = 0; r < rounds; r++) {
        const uint8_t *R = TF_ROT[r & 7];
        if ((r & 1) == 0) {
            X0 += X1; X1 = rotl32(X1, R[0]); X1 ^= X0;
            X2 += X3; X3 = rotl32(X3, R[1]); X3 ^= X2;
        } else {
            X0 += X3; X3 = rotl32(X3, R[0]); X3 ^= X0;
            X2 += X1; X1 = rotl32(X1, R[1]); X1 ^= X2;
        }
        if ((r & 3) == 3) {
            uint32_t inj = (uint32_t)((r + 1) / 4);
            X0 += ks[(inj + 0) % 5];
            X1 += ks[(inj + 1) % 5];
            X2 += ks[(inj + 2) % 5];
            X3 += ks[(inj + 3) % 5];
            X3 += inj;
        }
    }
    out[0] = X0; out[1] = X1; out[2] = X2; out[3] = X3;
}

// ---------------------------------------------------------------------------
// ChaCha — RFC 8439 §2.3. Mot 12 = compteur bas, 13 = compteur haut,
// 14 et 15 = nonce nul. Cette disposition coïncide avec celle de
// `rand_chacha` (nonce de 8 octets, compteur de 64 bits) pour tout bloc
// d'indice < 2³², et avec celle de la RFC (compteur de 32 bits, nonce de
// 96 bits nul) pour les mêmes.
// ---------------------------------------------------------------------------
#define QR(a,b,c,d) \
    a += b; d ^= a; d = rotl32(d,16); \
    c += d; b ^= c; b = rotl32(b,12); \
    a += b; d ^= a; d = rotl32(d, 8); \
    c += d; b ^= c; b = rotl32(b, 7);

static void chacha_block(const uint32_t key[8], uint64_t blk, int rounds,
                         uint32_t out[16]) {
    uint32_t s[16];
    s[0]=0x61707865u; s[1]=0x3320646eu; s[2]=0x79622d32u; s[3]=0x6b206574u;
    for (int i = 0; i < 8; i++) s[4+i] = key[i];
    s[12] = (uint32_t)blk; s[13] = (uint32_t)(blk >> 32); s[14] = 0; s[15] = 0;
    uint32_t x0=s[0],x1=s[1],x2=s[2],x3=s[3],x4=s[4],x5=s[5],x6=s[6],x7=s[7];
    uint32_t x8=s[8],x9=s[9],xa=s[10],xb=s[11],xc=s[12],xd=s[13],xe=s[14],xf=s[15];
    for (int r = 0; r < rounds; r += 2) {
        QR(x0,x4,x8,xc) QR(x1,x5,x9,xd) QR(x2,x6,xa,xe) QR(x3,x7,xb,xf)
        QR(x0,x5,xa,xf) QR(x1,x6,xb,xc) QR(x2,x7,x8,xd) QR(x3,x4,x9,xe)
    }
    out[0]=x0+s[0];   out[1]=x1+s[1];   out[2]=x2+s[2];   out[3]=x3+s[3];
    out[4]=x4+s[4];   out[5]=x5+s[5];   out[6]=x6+s[6];   out[7]=x7+s[7];
    out[8]=x8+s[8];   out[9]=x9+s[9];   out[10]=xa+s[10]; out[11]=xb+s[11];
    out[12]=xc+s[12]; out[13]=xd+s[13]; out[14]=xe+s[14]; out[15]=xf+s[15];
}

// `SeedableRng::seed_from_u64` de rand_core (rand_core/src/lib.rs) : huit
// sorties d'un PCG32 de constantes MUL/INC propres à rand, écrites en
// petit-boutiste dans les 32 octets de graine. C'est ce que fait
// `ChaCha12Rng::seed_from_u64(n)`, donc `StdRng::seed_from_u64(n)`.
static void rand_seed_from_u64(uint64_t state, uint32_t key[8]) {
    const uint64_t MUL = 6364136223846793005ULL;
    const uint64_t INC = 11634580027462260723ULL;
    for (int i = 0; i < 8; i++) {
        state = state * MUL + INC;
        uint32_t xorshifted = (uint32_t)(((state >> 18) ^ state) >> 27);
        uint32_t rot = (uint32_t)(state >> 59);
        key[i] = rotr32(xorshifted, (int)rot);
    }
}

// ---------------------------------------------------------------------------
// PCG — pcg-c-basic (pcg32) et pcg-c (pcg64 setseq XSL-RR 128/64)
// ---------------------------------------------------------------------------
#define PCG32_MULT 6364136223846793005ULL
typedef unsigned __int128 u128;
#define PCG128_MULT (((u128)0x2360ed051fc65da4ULL << 64) | 0x4385df649fccf645ULL)
#define PCG128_DEFINC (((u128)0x5851f42d4c957f2dULL << 64) | 0x14057b7ef767814fULL)

static inline uint32_t pcg32_out(uint64_t old) {
    uint32_t xs = (uint32_t)(((old >> 18) ^ old) >> 27);
    uint32_t rot = (uint32_t)(old >> 59);
    return (xs >> rot) | (xs << ((-rot) & 31));
}
static inline uint64_t pcg64_out(u128 st) {
    uint32_t rot = (uint32_t)(st >> 122);
    uint64_t v = (uint64_t)(st >> 64) ^ (uint64_t)st;
    return rotr64(v, (int)rot);
}

// ---------------------------------------------------------------------------
// Le catalogue des familles
// ---------------------------------------------------------------------------

enum {
    E_PHILOX_K, E_PHILOX_C, E_THREEFRY_K, E_THREEFRY_C,
    E_CHACHA_D, E_CHACHA_R,
    E_SFC64, E_JSF64, E_WYRAND, E_ROMUTRIO, E_ROMUDUOJR,
    E_XOSHIRO256P, E_XOSHIRO256PP, E_PCG64_SRAND, E_PCG64_DEFINC,
    E_JSF32, E_PCG32
};

typedef struct {
    const char *name;
    int  engine;
    int  param;   // nombre de tours (ChaCha / Philox / ThreeFry) ou flux (pcg32)
    int  low;     // 1 = on prend les 32 bits de POIDS FAIBLE d'une sortie 64 bits
} famdesc;

// L'ordre de ce tableau est l'index de famille utilisé par --fams et --stream.
static const famdesc FAM[] = {
    /*  0 */ { "philox4x32-10 cle=g",   E_PHILOX_K,    10, 0 },
    /*  1 */ { "philox4x32-10 ctr=g",   E_PHILOX_C,    10, 0 },
    /*  2 */ { "threefry4x32-20 cle=g", E_THREEFRY_K,  20, 0 },
    /*  3 */ { "threefry4x32-20 ctr=g", E_THREEFRY_C,  20, 0 },
    /*  4 */ { "chacha8 cle=g",         E_CHACHA_D,     8, 0 },
    /*  5 */ { "chacha12 cle=g",        E_CHACHA_D,    12, 0 },
    /*  6 */ { "chacha20 cle=g",        E_CHACHA_D,    20, 0 },
    /*  7 */ { "chacha8 rand:sfu64",    E_CHACHA_R,     8, 0 },
    /*  8 */ { "chacha12 rand:sfu64",   E_CHACHA_R,    12, 0 },
    /*  9 */ { "chacha20 rand:sfu64",   E_CHACHA_R,    20, 0 },
    /* 10 */ { "sfc64 ^H",              E_SFC64,        0, 0 },
    /* 11 */ { "jsf64 ^H",              E_JSF64,        0, 0 },
    /* 12 */ { "wyrand ^H",             E_WYRAND,       0, 0 },
    /* 13 */ { "romuTrio ^H",           E_ROMUTRIO,     0, 0 },
    /* 14 */ { "romuDuoJr ^H",          E_ROMUDUOJR,    0, 0 },
    /* 15 */ { "xoshiro256+ ^H",        E_XOSHIRO256P,  0, 0 },
    /* 16 */ { "xoshiro256++ ^H",       E_XOSHIRO256PP, 0, 0 },
    /* 17 */ { "pcg64 srandom(g,0) ^H", E_PCG64_SRAND,  0, 0 },
    /* 18 */ { "pcg64 etat=g incD ^H",  E_PCG64_DEFINC, 0, 0 },
    /* 19 */ { "sfc64 ^L",              E_SFC64,        0, 1 },
    /* 20 */ { "jsf64 ^L",              E_JSF64,        0, 1 },
    /* 21 */ { "wyrand ^L",             E_WYRAND,       0, 1 },
    /* 22 */ { "romuTrio ^L",           E_ROMUTRIO,     0, 1 },
    /* 23 */ { "romuDuoJr ^L",          E_ROMUDUOJR,    0, 1 },
    /* 24 */ { "xoshiro256+ ^L",        E_XOSHIRO256P,  0, 1 },
    /* 25 */ { "xoshiro256++ ^L",       E_XOSHIRO256PP, 0, 1 },
    /* 26 */ { "pcg64 srandom(g,0) ^L", E_PCG64_SRAND,  0, 1 },
    /* 27 */ { "pcg64 etat=g incD ^L",  E_PCG64_DEFINC, 0, 1 },
    /* 28 */ { "jsf32",                 E_JSF32,        0, 0 },
    /* 29 */ { "pcg32 srandom(g,0)",    E_PCG32,        0, 0 },
    /* 30 */ { "pcg32 srandom(g,54)",   E_PCG32,       54, 0 },
};
#define NFAM ((int)(sizeof FAM / sizeof FAM[0]))

typedef struct {
    uint64_t a, b, c, d;      // état 64 bits générique
    u128     s128, inc128;    // pcg64
    uint32_t key[8];          // ChaCha / Philox / ThreeFry
    uint32_t blkout[16];      // bloc courant d'un générateur à compteur
    uint64_t blk;             // index de bloc
    int      bi, bn;          // position / taille du bloc courant
} estate;

static void eng_init(int f, uint64_t seed, estate *st) {
    const famdesc *F = &FAM[f];
    memset(st, 0, sizeof *st);
    uint64_t x = seed;
    switch (F->engine) {
    case E_PHILOX_K:   st->key[0] = (uint32_t)seed; break;
    case E_PHILOX_C:   break;                                  // graine dans le compteur
    case E_THREEFRY_K: st->key[0] = (uint32_t)seed; break;
    case E_THREEFRY_C: break;
    case E_CHACHA_D:   st->key[0] = (uint32_t)seed; break;     // clé = graine, reste nul
    case E_CHACHA_R:   rand_seed_from_u64(seed, st->key); break;
    case E_SFC64:      // PractRand : a = b = c = graine, compteur = 1, 12 tours
        st->a = st->b = st->c = seed; st->d = 1;
        for (int i = 0; i < 12; i++) {
            uint64_t t = st->a + st->b + st->d; st->d++;
            st->a = st->b ^ (st->b >> 11);
            st->b = st->c + (st->c << 3);
            st->c = rotl64(st->c, 24) + t;
        }
        break;
    case E_JSF64:      // Jenkins : a = 0xf1ea5eed, b = c = d = graine, 20 tours
        st->a = 0xf1ea5eedULL; st->b = st->c = st->d = seed;
        for (int i = 0; i < 20; i++) {
            uint64_t e = st->a - rotl64(st->b, 7);
            st->a = st->b ^ rotl64(st->c, 13);
            st->b = st->c + rotl64(st->d, 37);
            st->c = st->d + e;
            st->d = e + st->a;
        }
        break;
    case E_JSF32: {    // Jenkins 32 bits : rotations 27 et 17, pas de rotation sur d
        uint32_t a = 0xf1ea5eedu, b = (uint32_t)seed, c = (uint32_t)seed, d = (uint32_t)seed;
        for (int i = 0; i < 20; i++) {
            uint32_t e = a - rotl32(b, 27);
            a = b ^ rotl32(c, 17);
            b = c + d;
            c = d + e;
            d = e + a;
        }
        st->a = a; st->b = b; st->c = c; st->d = d;
        break;
    }
    case E_WYRAND:     st->a = seed; break;
    case E_ROMUTRIO:   st->a = sm64(&x); st->b = sm64(&x); st->c = sm64(&x); break;
    case E_ROMUDUOJR:  st->a = sm64(&x); st->b = sm64(&x); break;
    case E_XOSHIRO256P:
    case E_XOSHIRO256PP:
        st->a = sm64(&x); st->b = sm64(&x); st->c = sm64(&x); st->d = sm64(&x);
        break;
    case E_PCG64_SRAND:      // pcg_setseq_128_srandom_r(rng, graine, 0)
        st->inc128 = 1;
        st->s128 = 0;
        st->s128 = st->s128 * PCG128_MULT + st->inc128;
        st->s128 += (u128)seed;
        st->s128 = st->s128 * PCG128_MULT + st->inc128;
        break;
    case E_PCG64_DEFINC:     // état = graine, flux = increment par défaut de PCG
        st->inc128 = PCG128_DEFINC;
        st->s128 = (u128)seed;
        break;
    case E_PCG32: {          // pcg32_srandom_r(rng, graine, F->param)
        uint64_t inc = ((uint64_t)F->param << 1) | 1ULL;
        uint64_t s = 0;
        s = s * PCG32_MULT + inc;
        s += seed;
        s = s * PCG32_MULT + inc;
        st->a = s; st->b = inc;
        break;
    }
    }
    st->bi = st->bn = 0;
    st->blk = 0;
}

static uint32_t eng_next(int f, estate *st) {
    const famdesc *F = &FAM[f];
    uint64_t r64;
    switch (F->engine) {
    case E_PHILOX_K: case E_PHILOX_C:
    case E_THREEFRY_K: case E_THREEFRY_C: {
        if (st->bi >= st->bn) {
            uint32_t in[4] = {0,0,0,0}, out[4];
            if (F->engine == E_PHILOX_K || F->engine == E_THREEFRY_K) {
                in[0] = (uint32_t)st->blk;
            } else {                      // graine dans le compteur
                in[0] = (uint32_t)st->blk;
                in[1] = st->key[4];       // key[4] sert de rangement à la graine
            }
            if (F->engine == E_PHILOX_K || F->engine == E_PHILOX_C)
                philox4x32(in, st->key, F->param, out);
            else
                threefry4x32(in, st->key, F->param, out);
            memcpy(st->blkout, out, sizeof out);
            st->bn = 4; st->bi = 0; st->blk++;
        }
        return st->blkout[st->bi++];
    }
    case E_CHACHA_D: case E_CHACHA_R:
        if (st->bi >= st->bn) {
            chacha_block(st->key, st->blk, F->param, st->blkout);
            st->bn = 16; st->bi = 0; st->blk++;
        }
        return st->blkout[st->bi++];
    case E_SFC64: {
        uint64_t t = st->a + st->b + st->d; st->d++;
        st->a = st->b ^ (st->b >> 11);
        st->b = st->c + (st->c << 3);
        st->c = rotl64(st->c, 24) + t;
        r64 = t;
        break;
    }
    case E_JSF64: {
        uint64_t e = st->a - rotl64(st->b, 7);
        st->a = st->b ^ rotl64(st->c, 13);
        st->b = st->c + rotl64(st->d, 37);
        st->c = st->d + e;
        st->d = e + st->a;
        r64 = st->d;
        break;
    }
    case E_JSF32: {
        uint32_t a = (uint32_t)st->a, b = (uint32_t)st->b;
        uint32_t c = (uint32_t)st->c, d = (uint32_t)st->d;
        uint32_t e = a - rotl32(b, 27);
        a = b ^ rotl32(c, 17);
        b = c + d;
        c = d + e;
        d = e + a;
        st->a = a; st->b = b; st->c = c; st->d = d;
        return d;
    }
    case E_WYRAND: {
        st->a += 0x2d358dccaa6c78a5ULL;
        u128 p = (u128)st->a * (uint64_t)(st->a ^ 0x8bb84b93962eacc9ULL);
        r64 = (uint64_t)p ^ (uint64_t)(p >> 64);
        break;
    }
    case E_ROMUTRIO: {
        uint64_t xp = st->a, yp = st->b, zp = st->c;
        st->a = 15241094284759029579ULL * zp;
        st->b = rotl64(yp - xp, 12);
        st->c = rotl64(zp - yp, 44);
        r64 = xp;
        break;
    }
    case E_ROMUDUOJR: {
        uint64_t xp = st->a;
        st->a = 15241094284759029579ULL * st->b;
        st->b = rotl64(st->b - xp, 27);
        r64 = xp;
        break;
    }
    case E_XOSHIRO256P: {
        r64 = st->a + st->d;
        uint64_t t = st->b << 17;
        st->c ^= st->a; st->d ^= st->b; st->b ^= st->c; st->a ^= st->d;
        st->c ^= t; st->d = rotl64(st->d, 45);
        break;
    }
    case E_XOSHIRO256PP: {
        r64 = rotl64(st->a + st->d, 23) + st->a;
        uint64_t t = st->b << 17;
        st->c ^= st->a; st->d ^= st->b; st->b ^= st->c; st->a ^= st->d;
        st->c ^= t; st->d = rotl64(st->d, 45);
        break;
    }
    case E_PCG64_SRAND: case E_PCG64_DEFINC:
        st->s128 = st->s128 * PCG128_MULT + st->inc128;   // pcg-c : avancer puis sortir
        r64 = pcg64_out(st->s128);
        break;
    default: {  // E_PCG32 — pcg-c-basic : sortir depuis l'ANCIEN état
        uint64_t old = st->a;
        st->a = old * PCG32_MULT + st->b;
        return pcg32_out(old);
    }
    }
    return F->low ? (uint32_t)r64 : (uint32_t)(r64 >> 32);
}

// Les familles à compteur amorcées par le compteur rangent la graine dans
// key[4] (inutilisé par Philox, hors clé pour ThreeFry).
static void eng_init_full(int f, uint64_t seed, estate *st) {
    eng_init(f, seed, st);
    if (FAM[f].engine == E_PHILOX_C || FAM[f].engine == E_THREEFRY_C)
        st->key[4] = (uint32_t)seed;
}

// ---------------------------------------------------------------------------
// Tampon de mots — un seul flux, quatre échantillonneurs
// ---------------------------------------------------------------------------
// Les quatre échantillonneurs lisent le MÊME flux. Le remplir une seule
// fois par graine divise par quatre le coût des familles chères : un bloc
// ChaCha20 coûte vingt tours, et une graine fausse meurt au premier numéro
// (probabilité 1/80), donc un bloc suffit presque toujours.

typedef struct { int fam; estate st; uint32_t w[MAXW]; int n; } wbuf;

static inline uint32_t wb_get(wbuf *b, int i) {
    while (b->n <= i) b->w[b->n++] = eng_next(b->fam, &b->st);
    return b->w[i];
}

// ---------------------------------------------------------------------------
// Les quatre échantillonneurs de sweep_order.c, repris à l'identique.
// Tous les flux d'ici rendent 32 bits utiles, donc bits = 32 partout.
// ---------------------------------------------------------------------------

static int match_order(int s, wbuf *b, const uint8_t *target) {
    if (s == 0 || s == 1) {                      // rejet des doublons
        uint64_t lo = 0, hi = 0;
        int got = 0, steps = 0;
        while (got < DRAWN && steps < 400) {
            uint32_t u = wb_get(b, steps);
            steps++;
            uint32_t n = (s == 0) ? (u % POOL)
                                  : (uint32_t)(((uint64_t)u * POOL) >> 32);
            int bt = (int)n;
            uint64_t bit = (bt < 64) ? (1ULL << bt) : (1ULL << (bt - 64));
            uint64_t *w = (bt < 64) ? &lo : &hi;
            if (*w & bit) continue;
            *w |= bit;
            if (n + 1 != target[got]) return 0;
            got++;
        }
        return got == DRAWN;
    }
    uint8_t arr[POOL];
    for (int i = 0; i < POOL; i++) arr[i] = (uint8_t)(i + 1);
    for (int i = 0; i < DRAWN; i++) {
        uint32_t m = (uint32_t)(POOL - i);
        uint32_t u = wb_get(b, i);
        uint32_t p = (s == 2) ? (u % m) : (uint32_t)(((uint64_t)u * m) >> 32);
        int j = i + (int)p;
        uint8_t t = arr[i]; arr[i] = arr[j]; arr[j] = t;
        if (arr[i] != target[i]) return 0;
    }
    return 1;
}

static void produce(int f, int s, uint64_t seed, uint8_t *out) {
    static __thread wbuf b;
    b.fam = f; b.n = 0;
    eng_init_full(f, seed, &b.st);
    memset(out, 0, DRAWN);
    if (s == 0 || s == 1) {
        uint64_t lo = 0, hi = 0; int got = 0, steps = 0;
        while (got < DRAWN && steps < 4000) {
            uint32_t u = wb_get(&b, steps);
            steps++;
            uint32_t n = (s == 0) ? (u % POOL)
                                  : (uint32_t)(((uint64_t)u * POOL) >> 32);
            int bt = (int)n;
            uint64_t bit = (bt < 64) ? (1ULL << bt) : (1ULL << (bt - 64));
            uint64_t *w = (bt < 64) ? &lo : &hi;
            if (*w & bit) continue;
            *w |= bit;
            out[got++] = (uint8_t)(n + 1);
        }
        return;
    }
    uint8_t arr[POOL];
    for (int i = 0; i < POOL; i++) arr[i] = (uint8_t)(i + 1);
    for (int i = 0; i < DRAWN; i++) {
        uint32_t m = (uint32_t)(POOL - i);
        uint32_t u = wb_get(&b, i);
        uint32_t p = (s == 2) ? (u % m) : (uint32_t)(((uint64_t)u * m) >> 32);
        int j = i + (int)p;
        uint8_t t = arr[i]; arr[i] = arr[j]; arr[j] = t;
        out[i] = arr[i];
    }
}

// ---------------------------------------------------------------------------
// Le balayage
// ---------------------------------------------------------------------------

typedef struct {
    uint64_t lo, hi;
    const uint8_t *target;
    int fam;
    uint64_t hits[NSAMP];
    uint64_t first[NSAMP];
} job;

static void *worker(void *arg) {
    job *j = (job *)arg;
    static __thread wbuf b;
    for (int s = 0; s < NSAMP; s++) { j->hits[s] = 0; j->first[s] = 0; }
    b.fam = j->fam;
    for (uint64_t seed = j->lo; seed < j->hi; seed++) {
        b.n = 0;
        eng_init_full(j->fam, seed, &b.st);
        for (int s = 0; s < NSAMP; s++) {
            if (match_order(s, &b, j->target)) {
                if (j->hits[s] == 0) j->first[s] = seed;
                j->hits[s]++;
            }
        }
    }
    return NULL;
}

static const char *SAMP_NAME[NSAMP] = {
    "modulo + rejet", "multiply-shift + rejet", "Fisher-Yates modulo",
    "Fisher-Yates multiply-shift"
};

static void sweep(int f, uint64_t lo, uint64_t hi, const uint8_t *target,
                  int nthreads, uint64_t *hits, uint64_t *first) {
    pthread_t th[64];
    static job jobs[64];
    if (nthreads > 64) nthreads = 64;
    uint64_t span = (hi - lo) / (uint64_t)nthreads + 1;
    for (int i = 0; i < nthreads; i++) {
        jobs[i].lo = lo + span * (uint64_t)i;
        jobs[i].hi = jobs[i].lo + span; if (jobs[i].hi > hi) jobs[i].hi = hi;
        if (jobs[i].lo > hi) jobs[i].lo = jobs[i].hi = hi;
        jobs[i].target = target; jobs[i].fam = f;
        pthread_create(&th[i], NULL, worker, &jobs[i]);
    }
    for (int s = 0; s < NSAMP; s++) { hits[s] = 0; first[s] = 0; }
    for (int i = 0; i < nthreads; i++) {
        pthread_join(th[i], NULL);
        for (int s = 0; s < NSAMP; s++) {
            if (jobs[i].hits[s] && hits[s] == 0) first[s] = jobs[i].first[s];
            hits[s] += jobs[i].hits[s];
        }
    }
}

// ---------------------------------------------------------------------------
// --kat : confrontation à des références PUBLIÉES
// ---------------------------------------------------------------------------


// ---------------------------------------------------------------------------
// Catalogue complet, graine 1234567 : six mots par famille, TOUS produits par
// une implementation tierce et non par ce programme.
//
//   familles 0-3   randomgen.Philox / randomgen.ThreeFry, number=4 width=32.
//                  numpy et randomgen incrementent le compteur AVANT de
//                  produire un bloc : leur premier bloc est celui d'indice 1
//                  au sens de Random123 (dont le KAT ci-dessus fixe le bloc
//                  0). D'ou le decalage de quatre mots, declare dans CATSKIP.
//   familles 4-9   caisse Rust rand_chacha 0.3 (ChaCha8/12/20Rng), amorcees
//                  par from_seed (cle = graine en petit-boutiste) et par
//                  seed_from_u64. Compilee et executee.
//   10,19          randomgen.SFC64, etat a=b=c=graine, w=1, k=1, 12 tours.
//   11,20,28       randomgen.JSF, size 64 (7,13,37) et 32 (27,17,0),
//                  etat a=0xf1ea5eed, b=c=d=graine, 20 tours.
//   12,21          wyhash.h de wangyi-fudan, re-transcrit en Python.
//   13,22          randomgen.Romu variant="trio".
//   14,23          test.c de eqv/rand_romu (code de Mark Overton).
//   15,16,24,25    caisse Rust rand_xoshiro 0.6, etat = quatre sorties de
//                  SplitMix64 amorce par la graine (convention de Vigna).
//   17,18,26,27    randomgen.PCG64 variante xsl-rr.
//   29,30          randomgen.PCG32, recoupe avec imneme/pcg-c-basic compile.
// ---------------------------------------------------------------------------
static const uint32_t CATKAT[NFAM][6] = {
    { 0x35d94e4au, 0x30119661u, 0x493dd023u, 0x7013bcabu, 0xf1133009u, 0x6e6da62fu },   /* 0 */
    { 0x118be302u, 0x5ba46391u, 0xbc3b5142u, 0x507040dcu, 0xdfbed35au, 0x99b629c3u },   /* 1 */
    { 0x354b27e6u, 0x85710293u, 0x03834e6eu, 0x50b5b392u, 0x568e2b13u, 0xa1de9846u },   /* 2 */
    { 0x1b2b444au, 0x6a0ed49bu, 0x4038881au, 0xd77d7e7bu, 0x5adb48d8u, 0x33dfda54u },   /* 3 */
    { 0x9e409d89u, 0x4d100ce5u, 0x7f162c60u, 0x1934f8b8u, 0x91ac4fabu, 0x7bf3abd6u },   /* 4 */
    { 0xacc1d934u, 0x35830abbu, 0x81c7744cu, 0x72b8809cu, 0x4eb6b184u, 0x88f15533u },   /* 5 */
    { 0x05ef8b14u, 0x8c47345eu, 0x2f8c0730u, 0x179d42c7u, 0x5c0a3e0fu, 0xce469b09u },   /* 6 */
    { 0x62d823a5u, 0x44b05b44u, 0x30993ed3u, 0xd08016adu, 0xa7512795u, 0x198ff65au },   /* 7 */
    { 0xa86bb617u, 0x6193f738u, 0x22fb6850u, 0x5323c7b0u, 0x6b0a43b1u, 0x1787b040u },   /* 8 */
    { 0x8d526f00u, 0x3a528610u, 0xd67282bau, 0xe82c6634u, 0xfa2ac72du, 0xd950b454u },   /* 9 */
    { 0x1d1c7177u, 0xcbb9b762u, 0xc5255716u, 0x92e573e8u, 0x3bf40b91u, 0x28ad9966u },   /* 10 */
    { 0x099f1967u, 0xd05f98e8u, 0xd32ba4c5u, 0xf85557a1u, 0x460995c1u, 0xa709f639u },   /* 11 */
    { 0xbe7b4617u, 0xb5cac5f0u, 0x14e5da3fu, 0x3f9c477cu, 0x56eb5ae8u, 0x40166888u },   /* 12 */
    { 0x599ed017u, 0xa79fefe4u, 0x34fbc2b1u, 0xbecd6b83u, 0xa294d622u, 0xc62a1c68u },   /* 13 */
    { 0x599ed017u, 0x31816313u, 0xe306a474u, 0xc31c5c31u, 0xc32190b2u, 0xa82249d6u },   /* 14 */
    { 0x995dc758u, 0xb8e71a4cu, 0x9c42fc45u, 0x2b8a74ccu, 0x0eeba288u, 0x95e09cb4u },   /* 15 */
    { 0x0610e053u, 0x70c979e2u, 0xfb95f99fu, 0x03890aaeu, 0x536acabdu, 0x1f1a58ffu },   /* 16 */
    { 0x960cebc4u, 0x81240d93u, 0x8133ed74u, 0x27094e4fu, 0x09088d34u, 0x7e49006eu },   /* 17 */
    { 0x5ee9531fu, 0x81435e78u, 0x958c5212u, 0xa9453d5du, 0x143566d8u, 0x6174a69au },   /* 18 */
    { 0x1a756b52u, 0x890bfa56u, 0xdd44c144u, 0x0f5f3460u, 0x8ed48f60u, 0x9892f304u },   /* 19 */
    { 0x9f7a16abu, 0x5b339a64u, 0x1c4de15eu, 0x210a1913u, 0x1e0d4bdau, 0xe4589e94u },   /* 20 */
    { 0xc97ab5efu, 0x9b3b76bfu, 0xf1fe2dbbu, 0xe41aa0ddu, 0xb407e32cu, 0xadf05035u },   /* 21 */
    { 0xfb08fc85u, 0x1caae7ddu, 0x2cfef133u, 0x60e34a33u, 0x74c73bfeu, 0xfa4dbba2u },   /* 22 */
    { 0xfb08fc85u, 0x01eda857u, 0x3b7788e1u, 0x44397364u, 0x905c5334u, 0x057a3c1au },   /* 23 */
    { 0xe42077c4u, 0xeb441e47u, 0x05df856au, 0xe93cc5a2u, 0x37b5014au, 0x136b2deeu },   /* 24 */
    { 0xdd55ab68u, 0x6e27fbacu, 0x9f6bb2deu, 0xcd9fa80au, 0x892d9406u, 0x404b8898u },   /* 25 */
    { 0x62e6a2b9u, 0xcdf907f5u, 0x2d6e5278u, 0x77654ba4u, 0x36bc1fa4u, 0xb16b862fu },   /* 26 */
    { 0xd1afd82du, 0x49bea0aeu, 0x7fc00aa8u, 0x11923d11u, 0x4ae2fe7bu, 0xd1698099u },   /* 27 */
    { 0xb3a4501fu, 0x830bdc15u, 0x7a4d860eu, 0x04754792u, 0x9ea85432u, 0xe34d992eu },   /* 28 */
    { 0x7ab4835bu, 0xd1e80b47u, 0x1231f2c8u, 0xfdfe1529u, 0xd60f5b34u, 0xbfa2d375u },   /* 29 */
    { 0xa735ba6du, 0x756904bfu, 0x8e7ffca7u, 0xa85c0d0eu, 0xd3b2be73u, 0x6ec5328bu },   /* 30 */
};
static const int CATSKIP[NFAM] = { 4,4,4,4, 0,0,0,0,0,0, 0,0,0,0,0,0,0,0,0,
                                   0,0,0,0,0,0,0,0,0, 0,0,0 };

static int kat_fail = 0, kat_run = 0;
static void kat_line(const char *what, const char *src, int ok) {
    kat_run++; if (!ok) kat_fail++;
    printf("%-42s %-46s %s\n", what, src, ok ? "OK" : "ÉCHEC");
}

static int kat(void) {
    printf("%-42s %-46s %s\n", "flux", "reference publiee", "");
    printf("%-42s %-46s %s\n", "----", "-----------------", "------");

    // --- Philox4x32-10, fichier officiel tests/kat_vectors de Random123
    {
        uint32_t o[4];
        uint32_t c0[4] = {0,0,0,0}, k0[2] = {0,0};
        uint32_t e0[4] = {0x6627e8d5u,0xe169c58du,0xbc57ac4cu,0x9b00dbd8u};
        philox4x32(c0, k0, 10, o);
        kat_line("philox4x32-10  ctr=0 key=0", "Random123 tests/kat_vectors", !memcmp(o,e0,16));

        uint32_t c1[4] = {0xffffffffu,0xffffffffu,0xffffffffu,0xffffffffu};
        uint32_t k1[2] = {0xffffffffu,0xffffffffu};
        uint32_t e1[4] = {0x408f276du,0x41c83b0eu,0xa20bc7c6u,0x6d5451fdu};
        philox4x32(c1, k1, 10, o);
        kat_line("philox4x32-10  ctr=ff.. key=ff..", "Random123 tests/kat_vectors", !memcmp(o,e1,16));

        uint32_t c2[4] = {0x243f6a88u,0x85a308d3u,0x13198a2eu,0x03707344u};
        uint32_t k2[2] = {0xa4093822u,0x299f31d0u};
        uint32_t e2[4] = {0xd16cfe09u,0x94fdccebu,0x5001e420u,0x24126ea1u};
        philox4x32(c2, k2, 10, o);
        kat_line("philox4x32-10  ctr=pi key=pi", "Random123 tests/kat_vectors", !memcmp(o,e2,16));

        uint32_t e7[4] = {0x4dfccabau,0x190a87f0u,0xc47362bau,0xb6b5242au};
        philox4x32(c2, k2, 7, o);
        kat_line("philox4x32-7   ctr=pi key=pi", "Random123 tests/kat_vectors", !memcmp(o,e7,16));
    }

    // --- ThreeFry4x32-20, même fichier
    {
        uint32_t o[4];
        uint32_t c0[4] = {0,0,0,0}, k0[4] = {0,0,0,0};
        uint32_t e0[4] = {0x9c6ca96au,0xe17eae66u,0xfc10ecd4u,0x5256a7d8u};
        threefry4x32(c0, k0, 20, o);
        kat_line("threefry4x32-20  ctr=0 key=0", "Random123 tests/kat_vectors", !memcmp(o,e0,16));

        uint32_t cf[4] = {0xffffffffu,0xffffffffu,0xffffffffu,0xffffffffu};
        uint32_t kf[4] = {0xffffffffu,0xffffffffu,0xffffffffu,0xffffffffu};
        uint32_t ef[4] = {0x2a881696u,0x57012287u,0xf6c7446eu,0xa16a6732u};
        threefry4x32(cf, kf, 20, o);
        kat_line("threefry4x32-20  ctr=ff.. key=ff..", "Random123 tests/kat_vectors", !memcmp(o,ef,16));

        uint32_t cp[4] = {0x243f6a88u,0x85a308d3u,0x13198a2eu,0x03707344u};
        uint32_t kp[4] = {0xa4093822u,0x299f31d0u,0x082efa98u,0xec4e6c89u};
        uint32_t ep[4] = {0x59cd1dbbu,0xb8879579u,0x86b5d00cu,0xac8b6d84u};
        threefry4x32(cp, kp, 20, o);
        kat_line("threefry4x32-20  ctr=pi key=pi", "Random123 tests/kat_vectors", !memcmp(o,ep,16));

        uint32_t e13[4] = {0x4aa71d8fu,0x734738c2u,0x431fc6a8u,0xae6debf1u};
        threefry4x32(cp, kp, 13, o);
        kat_line("threefry4x32-13  ctr=pi key=pi", "Random123 tests/kat_vectors", !memcmp(o,e13,16));

        uint32_t e72[4] = {0x09930adfu,0x7f27bd55u,0x9ed68ce1u,0x97f803f6u};
        threefry4x32(cp, kp, 72, o);
        kat_line("threefry4x32-72  ctr=pi key=pi", "Random123 tests/kat_vectors", !memcmp(o,e72,16));
    }

    // --- ChaCha20, clé nulle / nonce nul : vecteur 1 de la RFC 8439 §2.3.2
    //     (identique à draft-nir-cfrg-chacha20-poly1305-04, et repris tel
    //      quel dans les tests de la caisse Rust rand_chacha)
    {
        uint32_t key[8] = {0,0,0,0,0,0,0,0}, out[16];
        uint32_t b0[16] = {
            0xade0b876u,0x903df1a0u,0xe56a5d40u,0x28bd8653u,
            0xb819d2bdu,0x1aed8da0u,0xccef36a8u,0xc70d778bu,
            0x7c5941dau,0x8d485751u,0x3fe02477u,0x374ad8b8u,
            0xf4b8436au,0x1ca11815u,0x69b687c3u,0x8665eeb2u };
        uint32_t b1[16] = {
            0xbee7079fu,0x7a385155u,0x7c97ba98u,0x0d082d73u,
            0xa0290fcbu,0x6965e348u,0x3e53c612u,0xed7aee32u,
            0x7621b729u,0x434ee69cu,0xb03371d5u,0xd539d874u,
            0x281fed31u,0x45fb0a51u,0x1f0ae1acu,0x6f4d794bu };
        chacha_block(key, 0, 20, out);
        kat_line("chacha20 bloc 0  cle=0 nonce=0", "RFC 8439 §2.3.2 vecteur 1", !memcmp(out,b0,64));
        chacha_block(key, 1, 20, out);
        kat_line("chacha20 bloc 1  cle=0 nonce=0", "RFC 8439 §2.3.2 vecteur 2", !memcmp(out,b1,64));

        // Vecteur 3 des mêmes sources : clé dont le dernier octet vaut 1,
        // c'est-à-dire mot de clé 7 = 0x01000000, bloc 1.
        uint32_t key3[8] = {0,0,0,0,0,0,0,0x01000000u};
        uint32_t b3[16] = {
            0x2452eb3au,0x9249f8ecu,0x8d829d9bu,0xddd4ceb1u,
            0xe8252083u,0x60818b01u,0xf38422b8u,0x5aaa49c9u,
            0xbb00ca8eu,0xda3ba7b4u,0xc4b592d1u,0xfdf2732fu,
            0x4436274eu,0x2561b3c8u,0xebdd4aa6u,0xa0136c00u };
        chacha_block(key3, 1, 20, out);
        kat_line("chacha20 bloc 1  cle=00..01", "RFC 8439 §2.3.2 vecteur 3", !memcmp(out,b3,64));
    }

    // --- xoshiro256+ et xoshiro256++, état (1, 2, 3, 4).
    //     Valeurs publiées dans rand_xoshiro (rust-random/rngs), produites
    //     avec l'implémentation de référence de Vigna
    //     http://xoshiro.di.unimi.it/xoshiro256plus.c et …plusplus.c
    {
        estate st; memset(&st, 0, sizeof st);
        st.a = 1; st.b = 2; st.c = 3; st.d = 4;
        static const uint64_t exp_p[10] = {
            5ULL, 211106232532999ULL, 211106635186183ULL,
            9223759065350669058ULL, 9250833439874351877ULL,
            13862484359527728515ULL, 2346507365006083650ULL,
            1168864526675804870ULL, 34095955243042024ULL,
            3466914240207415127ULL };
        int ok = 1;
        for (int i = 0; i < 10; i++) {
            uint64_t r = st.a + st.d;
            uint64_t t = st.b << 17;
            st.c ^= st.a; st.d ^= st.b; st.b ^= st.c; st.a ^= st.d;
            st.c ^= t; st.d = rotl64(st.d, 45);
            if (r != exp_p[i]) ok = 0;
        }
        kat_line("xoshiro256+  etat (1,2,3,4), 10 sorties", "Vigna, via rand_xoshiro (rust-random)", ok);

        memset(&st, 0, sizeof st);
        st.a = 1; st.b = 2; st.c = 3; st.d = 4;
        static const uint64_t exp_pp[10] = {
            41943041ULL, 58720359ULL, 3588806011781223ULL,
            3591011842654386ULL, 9228616714210784205ULL,
            9973669472204895162ULL, 14011001112246962877ULL,
            12406186145184390807ULL, 15849039046786891736ULL,
            10450023813501588000ULL };
        ok = 1;
        for (int i = 0; i < 10; i++) {
            uint64_t r = rotl64(st.a + st.d, 23) + st.a;
            uint64_t t = st.b << 17;
            st.c ^= st.a; st.d ^= st.b; st.b ^= st.c; st.a ^= st.d;
            st.c ^= t; st.d = rotl64(st.d, 45);
            if (r != exp_pp[i]) ok = 0;
        }
        kat_line("xoshiro256++ etat (1,2,3,4), 10 sorties", "Vigna, via rand_xoshiro (rust-random)", ok);
    }

    // --- splitmix64, l'amorçage des familles xoshiro et romu. Valeurs
    //     publiées dans rand_xoshiro (rust-random/rngs), produites avec
    //     l'implémentation de référence http://xoshiro.di.unimi.it/splitmix64.c
    {
        uint64_t x = 1477776061723855037ULL;
        static const uint64_t exp_sm[10] = {
            1985237415132408290ULL, 2979275885539914483ULL, 13511426838097143398ULL,
            8488337342461049707ULL, 15141737807933549159ULL, 17093170987380407015ULL,
            16389528042912955399ULL, 13177319091862933652ULL, 10841969400225389492ULL,
            17094824097954834098ULL };
        int ok = 1;
        for (int i = 0; i < 10; i++) if (sm64(&x) != exp_sm[i]) ok = 0;
        kat_line("splitmix64, 10 sorties depuis 1477776061723855037",
                 "Vigna, via rand_xoshiro (rust-random)", ok);
    }

    // --- romuDuoJr, état témoin du test.c publié par eqv/rand_romu
    //     (transcription directe du code de Mark Overton, romu-random.org)
    {
        uint64_t x = 0x3c91b13ee3913664ULL, y = 0x863f0e37c2637d1fULL;
        static const uint64_t exp_r[8] = {
            0x3c91b13ee3913664ULL, 0x0dc1980b78df3115ULL, 0x1c163b704996d2adULL,
            0xa000c594bb28313bULL, 0xfb6c42e69a523526ULL, 0x1fcebd6988ab21d8ULL,
            0x5e0a8abf025f8f02ULL, 0x29554b00ffab0263ULL };
        int ok = 1;
        for (int i = 0; i < 8; i++) {
            uint64_t xp = x;
            x = 15241094284759029579ULL * y;
            y = rotl64(y - xp, 27);
            if (xp != exp_r[i]) ok = 0;
        }
        kat_line("romuDuoJr, 8 sorties depuis l'etat temoin", "eqv/rand_romu test.c (code Overton)", ok);
    }

    // --- wyrand, code de l'auteur (wangyi-fudan/wyhash, wyhash.h)
    {
        uint64_t s = 1234567ULL;
        static const uint64_t exp_w[8] = {
            0xbe7b4617c97ab5efULL, 0xb5cac5f09b3b76bfULL, 0x14e5da3ff1fe2dbbULL,
            0x3f9c477ce41aa0ddULL, 0x56eb5ae8b407e32cULL, 0x40166888adf05035ULL,
            0xd69f04b4240a8e00ULL, 0x4ff21793376ab081ULL };
        int ok = 1;
        for (int i = 0; i < 8; i++) {
            s += 0x2d358dccaa6c78a5ULL;
            u128 p = (u128)s * (uint64_t)(s ^ 0x8bb84b93962eacc9ULL);
            uint64_t r = (uint64_t)p ^ (uint64_t)(p >> 64);
            if (r != exp_w[i]) ok = 0;
        }
        kat_line("wyrand, graine 1234567, 8 sorties", "wangyi-fudan/wyhash wyhash.h compile", ok);
    }

    // --- pcg32, amorçage officiel pcg32_srandom_r. La ligne (42, 54) est la
    //     sortie publiée de la démonstration pcg32-demo d'O'Neill.
    {
        struct { uint64_t st, inc; } r;
        uint64_t seq = 54, seed = 42;
        r.inc = (seq << 1) | 1; r.st = 0;
        r.st = r.st * PCG32_MULT + r.inc; r.st += seed;
        r.st = r.st * PCG32_MULT + r.inc;
        static const uint32_t exp_d[6] = {
            0xa15c02b7u,0x7b47f409u,0xba1d3330u,0x83d2f293u,0xbfa4784bu,0xcbed606eu };
        int ok = 1;
        for (int i = 0; i < 6; i++) {
            uint64_t old = r.st; r.st = old * PCG32_MULT + r.inc;
            if (pcg32_out(old) != exp_d[i]) ok = 0;
        }
        kat_line("pcg32 srandom(42,54), 6 sorties", "imneme/pcg-c-basic pcg32-demo", ok);
    }

    // --- les familles telles qu'elles seront balayées : on vérifie que
    //     eng_init/eng_next reproduisent bien le flux ci-dessus une fois
    //     branchés dans le catalogue.
    {
        estate st; int ok;
        // famille 6 = chacha20 clé = graine ; graine 0 → clé nulle → vecteur 1.
        eng_init_full(6, 0, &st); ok = 1;
        uint32_t b0[16] = {
            0xade0b876u,0x903df1a0u,0xe56a5d40u,0x28bd8653u,
            0xb819d2bdu,0x1aed8da0u,0xccef36a8u,0xc70d778bu,
            0x7c5941dau,0x8d485751u,0x3fe02477u,0x374ad8b8u,
            0xf4b8436au,0x1ca11815u,0x69b687c3u,0x8665eeb2u };
        for (int i = 0; i < 16; i++) if (eng_next(6, &st) != b0[i]) ok = 0;
        kat_line("famille 6 (chacha20 cle=g), graine 0", "RFC 8439 §2.3.2 vecteur 1", ok);

        // famille 0 = philox4x32-10 clé = graine ; graine 0 → ctr 0, clé 0.
        eng_init_full(0, 0, &st); ok = 1;
        uint32_t p0[4] = {0x6627e8d5u,0xe169c58du,0xbc57ac4cu,0x9b00dbd8u};
        for (int i = 0; i < 4; i++) if (eng_next(0, &st) != p0[i]) ok = 0;
        kat_line("famille 0 (philox4x32-10 cle=g), graine 0", "Random123 tests/kat_vectors", ok);

        // famille 2 = threefry4x32-20 clé = graine ; graine 0.
        eng_init_full(2, 0, &st); ok = 1;
        uint32_t t0[4] = {0x9c6ca96au,0xe17eae66u,0xfc10ecd4u,0x5256a7d8u};
        for (int i = 0; i < 4; i++) if (eng_next(2, &st) != t0[i]) ok = 0;
        kat_line("famille 2 (threefry4x32-20 cle=g), graine 0", "Random123 tests/kat_vectors", ok);

        // famille 29/30 = pcg32 srandom(g, 0 / 54) ; graine 42, flux 54.
        eng_init_full(30, 42, &st); ok = 1;
        static const uint32_t exp_d[6] = {
            0xa15c02b7u,0x7b47f409u,0xba1d3330u,0x83d2f293u,0xbfa4784bu,0xcbed606eu };
        for (int i = 0; i < 6; i++) if (eng_next(30, &st) != exp_d[i]) ok = 0;
        kat_line("famille 30 (pcg32 srandom(g,54)), graine 42", "imneme/pcg-c-basic pcg32-demo", ok);
    }

    // --- le catalogue entier, confronte aux implementations tierces
    {
        for (int f = 0; f < NFAM; f++) {
            estate st; eng_init_full(f, 1234567, &st);
            int ok = 1;
            for (int i = 0; i < CATSKIP[f] + 6; i++) {
                uint32_t u = eng_next(f, &st);
                if (i >= CATSKIP[f] && u != CATKAT[f][i - CATSKIP[f]]) ok = 0;
            }
            char lab[96];
            snprintf(lab, sizeof lab, "famille %d (%s), graine 1234567", f, FAM[f].name);
            kat_line(lab, "implementation tierce (voir CATKAT)", ok);
        }
    }

    printf("\n%d/%d verifications de flux passent.\n", kat_run - kat_fail, kat_run);
    return kat_fail == 0 ? 0 : 1;
}

// ---------------------------------------------------------------------------

static int parse_fams(const char *spec, int *sel) {
    for (int i = 0; i < NFAM; i++) sel[i] = 0;
    const char *p = spec;
    int any = 0;
    while (*p) {
        char *end;
        long a = strtol(p, &end, 10);
        if (end == p) return -1;
        long b = a;
        p = end;
        if (*p == '-') { p++; b = strtol(p, &end, 10); if (end == p) return -1; p = end; }
        if (a < 0 || b >= NFAM || b < a) return -1;
        for (long i = a; i <= b; i++) { sel[i] = 1; any = 1; }
        if (*p == ',') p++;
        else if (*p) return -1;
    }
    return any ? 0 : -1;
}

int main(int argc, char **argv) {
    int nthreads = 4;
    const char *env = getenv("SWEEP_THREADS");
    if (env) nthreads = atoi(env);
    if (nthreads < 1) nthreads = 1;

    if (argc >= 2 && strcmp(argv[1], "--kat") == 0) return kat();

    if (argc >= 2 && strcmp(argv[1], "--list") == 0) {
        for (int f = 0; f < NFAM; f++) printf("%2d  %s\n", f, FAM[f].name);
        return 0;
    }

    if (argc >= 5 && strcmp(argv[1], "--stream") == 0) {
        int f = atoi(argv[2]);
        uint64_t seed = strtoull(argv[3], 0, 10);
        int n = atoi(argv[4]);
        if (f < 0 || f >= NFAM) { fprintf(stderr, "famille hors bornes\n"); return 1; }
        estate st; eng_init_full(f, seed, &st);
        for (int i = 0; i < n; i++) printf("%08x\n", eng_next(f, &st));
        return 0;
    }

    if (argc >= 2 && strcmp(argv[1], "--selftest") == 0) {
        const uint64_t WITNESS = 1234567;
        const uint64_t LO = 0, HI = 2000000;
        int ok = 0, tot = 0;
        printf("AUTOTEST — graine temoin %llu dans [%llu, %llu)\n\n",
               (unsigned long long)WITNESS, (unsigned long long)LO,
               (unsigned long long)HI);
        printf("%-24s %-30s %-10s %s\n", "famille", "echantillonneur",
               "retrouvee", "graines compatibles");
        for (int f = 0; f < NFAM; f++) {
            uint8_t tgt[NSAMP][DRAWN];
            int complete[NSAMP];
            for (int s = 0; s < NSAMP; s++) {
                produce(f, s, WITNESS, tgt[s]);
                complete[s] = 1;
                for (int i = 0; i < DRAWN; i++) if (!tgt[s][i]) complete[s] = 0;
            }
            for (int s = 0; s < NSAMP; s++) {
                if (!complete[s]) {
                    printf("%-24s %-30s %-10s %s\n", FAM[f].name, SAMP_NAME[s],
                           "—", "tirage incomplet");
                    continue;
                }
                uint64_t hits[NSAMP], first[NSAMP];
                sweep(f, LO, HI, tgt[s], nthreads, hits, first);
                tot++;
                int found = (hits[s] >= 1) && (first[s] == WITNESS);
                if (found) ok++;
                printf("%-24s %-30s %-10s %llu\n", FAM[f].name, SAMP_NAME[s],
                       found ? "OUI" : "NON", (unsigned long long)hits[s]);
                fflush(stdout);
            }
        }
        printf("\n%d/%d combinaisons retrouvent leur temoin.\n", ok, tot);
        return ok == tot ? 0 : 1;
    }

    int sel[NFAM];
    for (int i = 0; i < NFAM; i++) sel[i] = 1;
    int ai = 1;
    if (argc >= 3 && strcmp(argv[1], "--fams") == 0) {
        if (parse_fams(argv[2], sel) < 0) {
            fprintf(stderr, "--fams : specification invalide (ex. 0-9 ou 4,6,10)\n");
            return 1;
        }
        ai = 3;
    }

    if (argc < ai + 2 + DRAWN) {
        fprintf(stderr, "usage: %s [--fams a-b|a,b,c] <lo> <hi> <o1..o20>\n", argv[0]);
        fprintf(stderr, "       %s --kat | --selftest | --list\n", argv[0]);
        fprintf(stderr, "       %s --stream <famille> <graine> <n>\n", argv[0]);
        return 1;
    }
    uint64_t lo = strtoull(argv[ai], 0, 10), hi = strtoull(argv[ai+1], 0, 10);
    uint8_t target[DRAWN];
    for (int i = 0; i < DRAWN; i++) target[i] = (uint8_t)atoi(argv[ai+2+i]);

    fprintf(stderr, "plage [%llu, %llu) — %d fils — sans confirmation\n",
            (unsigned long long)lo, (unsigned long long)hi, nthreads);
    printf("%-24s %-30s %s\n", "famille", "echantillonneur", "graines compatibles");
    uint64_t grand = 0;
    for (int f = 0; f < NFAM; f++) {
        if (!sel[f]) continue;
        uint64_t hits[NSAMP], first[NSAMP];
        sweep(f, lo, hi, target, nthreads, hits, first);
        for (int s = 0; s < NSAMP; s++) {
            grand += hits[s];
            if (hits[s])
                printf("%-24s %-30s %llu   PREMIERE = %llu\n", FAM[f].name,
                       SAMP_NAME[s], (unsigned long long)hits[s],
                       (unsigned long long)first[s]);
            else
                printf("%-24s %-30s 0\n", FAM[f].name, SAMP_NAME[s]);
        }
        fflush(stdout);
    }
    printf("\ntotal : %llu graine(s) compatible(s)\n", (unsigned long long)grand);
    return 0;
}
