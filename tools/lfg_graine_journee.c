// lfg_graine_journee.c — la graine journalière de random() : TOUTE graine de
// 32 bits, contre le premier tirage de chacune des journées de l'archive triée.
//
// -------------------------------------------------------------------------
// La case que le dossier n'avait pas ouverte
// -------------------------------------------------------------------------
//
// Le §63 (sweep_time) essaie, tirage par tirage, les graines qu'on CONNAÎT
// (horodatage, numéro, leurs mélanges) ; le §120/§133 (sweep_brouille) essaie
// 2^32 graines INCONNUES mais pour sept familles brouillées amorcées par
// splitmix ; sweep_rand énumère 2^32 graines de random() mais contre les
// douze tirages ORDONNÉS des vidéos ; sweep_archive (§150) énumère 2^32 états
// complets de générateurs à 32 bits d'état. Aucun n'a essayé la lecture la
// plus naïve d'un programme de loterie sous Linux :
//
//     au démarrage du service, srandom(graine) — graine quelconque, horloge,
//     pid, compteur, /dev/urandom tronqué, peu importe — puis random() pour
//     chaque numéro, toute la journée.
//
// Sous cette hypothèse, l'état complet de la journée (992 bits pour TYPE_3)
// est une FONCTION de 32 bits : la graine. srandom(unsigned) tronque à 32
// bits quelle que soit la source ; énumérer 2^32 graines couvre donc TOUTES
// les conventions d'amorçage en une passe, sans en supposer aucune. Et
// l'archive donne, pour chaque journée, le premier tirage : vingt numéros,
// triés. Une graine fausse reproduit un ensemble donné de vingt numéros avec
// probabilité 1/C(80,20) = 2,8e-19.
//
// -------------------------------------------------------------------------
// L'index par journée : une passe de 2^32 pour toutes les journées à la fois
// -------------------------------------------------------------------------
//
// Le flux d'une graine ne dépend pas de la journée. On indexe donc les NJ
// premiers ensembles (un par bloc de cadence : 370 blocs, dont les 346 débuts
// de journée) par un masque de bits M[v] = {journées dont le premier ensemble
// contient v}. Pour une graine, un échantillonneur et un décalage, on engendre
// les numéros dans l'ordre d'émission et on ET-e les masques : après k numéros
// il reste NJ/4^k journées en espérance ; le masque est nul après cinq numéros
// en moyenne, et la graine meurt. Une TOUCHE est un masque non nul après les
// vingt numéros : la journée survivante est nommée.
//
// Pour les mélanges complets « depuis la fin » (tête = les vingt premières
// positions après 79 pas), la tête est fixée dès que les soixante dernières
// positions le sont : on ET-e alors les masques COMPLÉMENTAIRES NM[v] des
// numéros écartés — une journée survit tant qu'aucun numéro écarté n'est dans
// son premier ensemble — ce qui tue la graine en ~25 pas au lieu de 60.
//
// -------------------------------------------------------------------------
// Les quatre amorçages, les quatre tables, les vingt et un échantillonneurs
// -------------------------------------------------------------------------
//
// glibc  : word = (int32) graine (0 → 1), Schrage 16807 sur int32 signé, fptr =
//          sep, rptr = 0, rodage 10·deg. Transcrit de random_r.c, vérifié ici
//          contre la libc réelle de la machine (--selftest : srandom, random,
//          initstate 32/64/128/256 octets, 0 écart).
// bsd_new: FreeBSD moderne, good_rand(ctx) = Schrage sur x = (ctx % 0x7ffffffe)
//          + 1, rendu x − 1 ; état uint32 ; rodage 10·deg.
// bsd_old: 4.4BSD / macOS (long de 64 bits) : good_rand(x) avec x == 0 →
//          123459876, Schrage sur long ; les sorties ne dépendent que des 32 bits
//          bas de l'état, donc la table tient en uint32. Pour une graine
//          < 2^31 non nulle cet amorçage COÏNCIDE avec celui de la glibc (même
//          Schrage sur une valeur positive) ; il n'en diffère que pour graine =
//          0 et pour les graines ≥ 2^31 (la glibc les lit négatives). La
//          variante à long de 32 bits (Apple Libc, int32) coïncide avec la
//          glibc partout sauf en graine = 0 — et ce cas est celui de bsd_old.
// musl   : x[k] = (6364136223846793005·s + 1) >> 32 itéré depuis s = graine,
//          x[0] |= 1, i = 3 (deg 31 ou 7) sinon 1, j = 0, PAS de rodage.
// Types  : T1 (7,3) T2 (15,1) T3 (31,3) T4 (63,1) — T3 est le random() et le
//          rand() par défaut ; les autres viennent d'initstate.
//
// Échantillonneurs (sur la sortie de 31 bits r) :
//   0 rejet_mod      n = r % 80 ; doublon rejeté
//   1 rejet_flot     n = (r·80) >> 31        (rand()/(RAND_MAX+1.0)·80)
//   2 rejet_kr       n = r / 26843546        (K&R : r / (RAND_MAX/80 + 1))
//   3 fy_mod         Fisher-Yates partiel depuis le début, j = i + r % (80−i)
//   4 fy_flot        idem, j = i + (r·(80−i)) >> 31
//   5 dos_mod_queue  depuis la fin (i = 79..1, j = r % (i+1)), vingt premiers
//                    pas, positions 60..79
//   6 dos_flot_queue idem en flottant
//   7 dos_mod_tete   mélange complet depuis la fin, positions 0..19
//   8 dos_flot_tete
//   9 rs_mod_tete    std::random_shuffle (i = 1..79, j = r % (i+1)), 0..19
//  10 rs_mod_queue   idem, positions 60..79
//  11 rs_flot_tete  12 rs_flot_queue
//  13 naif_mod_part  mélange naïf (j = r % 80) sur vingt pas, positions 0..19
//  14 naif_flot_part
//  15 naif_mod_tete  mélange naïf complet (80 pas), 0..19  16 naif_mod_queue
//  17 naif_flot_tete 18 naif_flot_queue
//  19 sel_flot       sélection de Knuth (algorithme S) : k pris si r·restant <
//                    besoin·2^31 — rend l'ensemble TRIÉ, comme l'archive
//  20 sel_mod        idem, k pris si r % restant < besoin
// Les codes 7-12 et 15-18 (« complets ») coûtent 60 à 80 pas ; les autres
// meurent après cinq numéros. Décalages (mots consommés avant le tirage) :
// 0..OP pour les partiels, 0..OC pour les complets.
//
// -------------------------------------------------------------------------
// Modes
// -------------------------------------------------------------------------
//   --selftest                        libc réelle (0 écart) + plantes retrouvées
//   --balaye V lo hi jours.txt [OP OC] graines [lo, hi) de la variante V contre
//                                     les ensembles du fichier (une ligne = 20
//                                     numéros) ; TOUCHE ... ; FIN ...
//   --suite V graine ech dec n        n tirages successifs (ordre d'émission et
//                                     trié) depuis la graine
//   --horloge V archive.txt D         par tirage (ligne : ts id 20 numéros), les
//                                     graines ts+d, id+d (|d| ≤ D) et les mélanges
//                                     du §63 (|d| ≤ 3), 21 échantillonneurs,
//                                     décalages 0..8
//   --pid V archive.txt pidmax        par tirage, graines pid, ts^pid, ts+pid
//                                     (pid < pidmax)
//   --archive V lo hi archive.txt [OP OC] graines [lo, hi) contre TOUS les
//                                     tirages de l'archive (index des
//                                     5-sous-ensembles, 4,4 Go ; une graine
//                                     inconnue PAR TIRAGE) ; défaut OP=1 OC=0
//   --selftest-archive [nt OP OC]     plantes retrouvées dans un index de nt
//                                     tirages aléatoires, et vitesse mesurée
//   SWEEP_THREADS : fils (défaut 4)
//
//   cc -O3 -march=native -pthread -Wall -o lfg_graine_journee lfg_graine_journee.c
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <pthread.h>
#include <time.h>
#include <sys/time.h>

#define POOL   80
#define DRAWN  20
#define NECH   21
#define OMAX   9
#define MOTS   256
#define NJMAX  1024
#define NWMAX  (NJMAX / 64)

static double horloge(void) { struct timeval tv; gettimeofday(&tv, NULL); return tv.tv_sec + tv.tv_usec * 1e-6; }

// ---------------------------------------------------------------------------
// Les variantes
// ---------------------------------------------------------------------------

enum { AM_GLIBC, AM_BSD_NEW, AM_BSD_OLD, AM_MUSL };
typedef struct { const char *nom; int amorce, deg, sep; } variante;
static const variante VAR[] = {
    {"glibc_T3",   AM_GLIBC,   31, 3}, {"glibc_T1",   AM_GLIBC,    7, 3},
    {"glibc_T2",   AM_GLIBC,   15, 1}, {"glibc_T4",   AM_GLIBC,   63, 1},
    {"bsd_new_T3", AM_BSD_NEW, 31, 3}, {"bsd_old_T3", AM_BSD_OLD, 31, 3},
    {"musl_T3",    AM_MUSL,    31, 3},
    {"bsd_new_T1", AM_BSD_NEW,  7, 3}, {"bsd_new_T2", AM_BSD_NEW, 15, 1}, {"bsd_new_T4", AM_BSD_NEW, 63, 1},
    {"bsd_old_T1", AM_BSD_OLD,  7, 3}, {"bsd_old_T2", AM_BSD_OLD, 15, 1}, {"bsd_old_T4", AM_BSD_OLD, 63, 1},
    {"musl_T1",    AM_MUSL,     7, 3}, {"musl_T2",    AM_MUSL,    15, 1}, {"musl_T4",    AM_MUSL,    63, 1},
};
#define NVAR ((int)(sizeof VAR / sizeof VAR[0]))

static const char *ECH[NECH] = {
    "rejet_mod", "rejet_flot", "rejet_kr", "fy_mod", "fy_flot",
    "dos_mod_queue", "dos_flot_queue", "dos_mod_tete", "dos_flot_tete",
    "rs_mod_tete", "rs_mod_queue", "rs_flot_tete", "rs_flot_queue",
    "naif_mod_part", "naif_flot_part", "naif_mod_tete", "naif_mod_queue",
    "naif_flot_tete", "naif_flot_queue", "sel_flot", "sel_mod",
};
static int complet(int e) { return (e >= 7 && e <= 12) || (e >= 15 && e <= 18); }

typedef struct { uint32_t tab[64]; int f, r, deg; } gstate;

// random_r() : *fptr += *rptr, sortie = mot >> 1. Identique pour les quatre
// amorçages (musl : x[i] += x[j], k = x[i] >> 1).
static inline uint32_t suivant(gstate *st) {
    uint32_t v = st->tab[st->f] + st->tab[st->r];
    st->tab[st->f] = v;
    if (++st->f >= st->deg) st->f = 0;
    if (++st->r >= st->deg) st->r = 0;
    return v >> 1;
}

static void amorce(int V, uint32_t seed, gstate *st) {
    const variante *v = &VAR[V];
    int deg = v->deg;
    st->deg = deg;
    switch (v->amorce) {
    case AM_GLIBC: {
        if (seed == 0) seed = 1;
        int32_t word = (int32_t)seed;
        st->tab[0] = (uint32_t)word;
        for (int i = 1; i < deg; i++) {
            long hi = (long)word / 127773L, lo = (long)word % 127773L;
            long w = 16807L * lo - 2836L * hi;
            if (w < 0) w += 2147483647L;
            word = (int32_t)w;
            st->tab[i] = (uint32_t)word;
        }
        st->f = v->sep; st->r = 0;
        for (int k = deg * 10; k > 0; k--) suivant(st);
        break;
    }
    case AM_BSD_NEW: {
        st->tab[0] = seed;
        for (int i = 1; i < deg; i++) {
            uint32_t ctx = st->tab[i - 1];
            int32_t x = (int32_t)((ctx % 0x7ffffffeu) + 1u);
            int32_t hi = x / 127773, lo = x % 127773;
            x = 16807 * lo - 2836 * hi;
            if (x < 0) x += 0x7fffffff;
            st->tab[i] = (uint32_t)(x - 1);
        }
        st->f = v->sep; st->r = 0;
        for (int k = deg * 10; k > 0; k--) suivant(st);
        break;
    }
    case AM_BSD_OLD: {
        st->tab[0] = seed;
        for (int i = 1; i < deg; i++) {
            int64_t x = (int64_t)st->tab[i - 1];
            if (x == 0) x = 123459876;
            int64_t hi = x / 127773, lo = x % 127773;
            x = 16807 * lo - 2836 * hi;
            if (x < 0) x += 0x7fffffff;
            st->tab[i] = (uint32_t)x;
        }
        st->f = v->sep; st->r = 0;
        for (int k = deg * 10; k > 0; k--) suivant(st);
        break;
    }
    default: {                                     // musl
        uint64_t s = seed;
        for (int k = 0; k < deg; k++) { s = 6364136223846793005ULL * s + 1ULL; st->tab[k] = (uint32_t)(s >> 32); }
        st->tab[0] |= 1u;
        st->f = (deg == 31 || deg == 7) ? 3 : 1; st->r = 0;
        break;
    }
    }
}

// ---------------------------------------------------------------------------
// Le flux d'une graine, en tampon paresseux, et le modulo rapide
// ---------------------------------------------------------------------------

typedef struct { gstate st; int n; uint32_t w[MOTS]; } flux;

static inline void flux_init(flux *F, int V, uint32_t seed) { F->n = 0; amorce(V, seed, &F->st); }
static inline uint32_t mot(flux *F, int i) {
    while (F->n <= i) { F->w[F->n] = suivant(&F->st); F->n++; }
    return F->w[i];
}

// r % d pour d ≤ 80 sans division (Lemire) : M = floor(2^64 / d) + 1.
static uint64_t MTAB[POOL + 1];
static inline uint32_t fmod_(uint32_t r, uint32_t d) {
    uint64_t low = MTAB[d] * r;
    return (uint32_t)(((__uint128_t)low * d) >> 64);
}
static inline uint32_t fflot(uint32_t r, uint32_t d) { return (uint32_t)(((uint64_t)r * d) >> 31); }
static inline uint32_t tire(uint32_t r, uint32_t d, int flot) { return flot ? fflot(r, d) : fmod_(r, d); }

// ---------------------------------------------------------------------------
// L'index des journées
// ---------------------------------------------------------------------------

typedef struct {
    int nj, nw;
    uint64_t tous[NWMAX];
    uint64_t M[POOL + 1][NWMAX];        // journées dont le premier ensemble contient v
    uint64_t NM[POOL + 1][NWMAX];       // ... ne contient pas v
} index_t;

static void index_construit(index_t *I, const uint8_t (*ens)[DRAWN], int nj) {
    memset(I, 0, sizeof *I);
    I->nj = nj; I->nw = (nj + 63) / 64;
    for (int d = 0; d < nj; d++) {
        I->tous[d >> 6] |= 1ULL << (d & 63);
        for (int k = 0; k < DRAWN; k++) I->M[ens[d][k]][d >> 6] |= 1ULL << (d & 63);
    }
    for (int v = 1; v <= POOL; v++)
        for (int w = 0; w < I->nw; w++) I->NM[v][w] = I->tous[w] & ~I->M[v][w];
}

static inline void m_tous(uint64_t *m, const index_t *I) { for (int w = 0; w < I->nw; w++) m[w] = I->tous[w]; }
static inline int m_et(uint64_t *m, const uint64_t *mk, int nw) {
    uint64_t any = 0;
    for (int w = 0; w < nw; w++) { m[w] &= mk[w]; any |= m[w]; }
    return any != 0;
}

// ---------------------------------------------------------------------------
// Les échantillonneurs, en mode « masque » : 1 si une journée survit aux vingt
// numéros. Le rappel (cb) reçoit (ech, dec, masque) pour chaque survie.
// ---------------------------------------------------------------------------

typedef void (*touche_cb)(void *ctx, int e, int o, const uint64_t *m);

static inline int rejet(flux *F, int o, int mode, const index_t *I, uint64_t *m) {
    uint64_t vu_lo = 0, vu_hi = 0;
    int got = 0, i = o;
    m_tous(m, I);
    while (got < DRAWN) {
        if (i >= MOTS) return 0;
        uint32_t r = mot(F, i++);
        uint32_t n = mode == 0 ? r % POOL : mode == 1 ? fflot(r, POOL) : r / 26843546u;
        uint64_t bit = 1ULL << (n & 63);
        uint64_t *vu = n < 64 ? &vu_lo : &vu_hi;
        if (*vu & bit) continue;
        *vu |= bit; got++;
        if (!m_et(m, I->M[n + 1], I->nw)) return 0;
    }
    return 1;
}

static inline void arr_init(uint8_t *arr) { for (int i = 0; i < POOL; i++) arr[i] = (uint8_t)(i + 1); }
static inline void echange(uint8_t *arr, int i, int j) { uint8_t t = arr[i]; arr[i] = arr[j]; arr[j] = t; }

static inline int fy(flux *F, int o, int flot, const index_t *I, uint64_t *m) {
    uint8_t arr[POOL]; arr_init(arr);
    m_tous(m, I);
    for (int i = 0; i < DRAWN; i++) {
        uint32_t d = POOL - i;
        int j = i + (int)tire(mot(F, o + i), d, flot);
        echange(arr, i, j);
        if (!m_et(m, I->M[arr[i]], I->nw)) return 0;
    }
    return 1;
}

// depuis la fin : queue (positions 60..79, fixées après vingt pas) et tête
// (positions 0..19 = complément des soixante écartés, masques NM).
static inline void dos(flux *F, int o, int flot, int avec_tete, const index_t *I,
                       uint64_t *mq, int *rq, uint64_t *mt, int *rt) {
    uint8_t arr[POOL]; arr_init(arr);
    m_tous(mq, I); m_tous(mt, I);
    *rq = 1; *rt = avec_tete;
    int pas = avec_tete ? 60 : DRAWN;
    for (int k = 0; k < pas; k++) {
        int i = POOL - 1 - k;
        int j = (int)tire(mot(F, o + k), (uint32_t)(i + 1), flot);
        echange(arr, i, j);
        if (k < DRAWN && *rq && !m_et(mq, I->M[arr[i]], I->nw)) *rq = 0;
        if (*rt && !m_et(mt, I->NM[arr[i]], I->nw)) *rt = 0;
        if (!*rq && !*rt) return;
    }
}

// mélange complet : random_shuffle (i = 1..79, j ≤ i) ou naïf (i = 0..79,
// j = r % 80 quelconque) ; tête et queue lues à la fin. Pour le naïf, la
// « partie » (vingt pas, positions 0..19) est lue en passant.
static inline void complet_lit(const uint8_t *arr, int deb, const index_t *I, uint64_t *m, int *r) {
    m_tous(m, I); *r = 1;
    for (int i = deb; i < deb + DRAWN; i++) if (!m_et(m, I->M[arr[i]], I->nw)) { *r = 0; return; }
}
static inline void rs(flux *F, int o, int flot, const index_t *I, uint64_t *mt, int *rt, uint64_t *mq, int *rq) {
    uint8_t arr[POOL]; arr_init(arr);
    for (int i = 1; i < POOL; i++) echange(arr, i, (int)tire(mot(F, o + i - 1), (uint32_t)(i + 1), flot));
    complet_lit(arr, 0, I, mt, rt);
    complet_lit(arr, POOL - DRAWN, I, mq, rq);
}
static inline void naif(flux *F, int o, int flot, int avec_complet, const index_t *I,
                        uint64_t *mp, int *rp, uint64_t *mt, int *rt, uint64_t *mq, int *rq) {
    uint8_t arr[POOL]; arr_init(arr);
    int pas = avec_complet ? POOL : DRAWN;
    *rt = *rq = 0;
    for (int i = 0; i < pas; i++) {
        echange(arr, i, (int)tire(mot(F, o + i), POOL, flot));
        if (i == DRAWN - 1) complet_lit(arr, 0, I, mp, rp);
    }
    if (avec_complet) { complet_lit(arr, 0, I, mt, rt); complet_lit(arr, POOL - DRAWN, I, mq, rq); }
}

static inline int sel(flux *F, int o, int flot, const index_t *I, uint64_t *m) {
    m_tous(m, I);
    int got = 0;
    for (int k = 0; k < POOL && got < DRAWN; k++) {
        uint32_t r = mot(F, o + k), reste = POOL - k, besoin = DRAWN - got;
        int pris = flot ? ((uint64_t)r * reste < ((uint64_t)besoin << 31)) : (fmod_(r, reste) < besoin);
        if (pris) { got++; if (!m_et(m, I->M[k + 1], I->nw)) return 0; }
    }
    return got == DRAWN;
}

// tous les échantillonneurs et décalages sur une graine déjà amorcée
static void essaie_tout(flux *F, const index_t *I, int OP, int OC, touche_cb cb, void *ctx) {
    uint64_t m[NWMAX], m2[NWMAX], m3[NWMAX];
    int r1, r2, r3;
    for (int o = 0; o <= OP; o++) {
        if (rejet(F, o, 0, I, m)) cb(ctx, 0, o, m);
        if (rejet(F, o, 1, I, m)) cb(ctx, 1, o, m);
        if (rejet(F, o, 2, I, m)) cb(ctx, 2, o, m);
        if (fy(F, o, 0, I, m)) cb(ctx, 3, o, m);
        if (fy(F, o, 1, I, m)) cb(ctx, 4, o, m);
        if (sel(F, o, 1, I, m)) cb(ctx, 19, o, m);
        if (sel(F, o, 0, I, m)) cb(ctx, 20, o, m);
        int ct = o <= OC;
        dos(F, o, 0, ct, I, m, &r1, m2, &r2);
        if (r1) cb(ctx, 5, o, m);
        if (r2) cb(ctx, 7, o, m2);
        dos(F, o, 1, ct, I, m, &r1, m2, &r2);
        if (r1) cb(ctx, 6, o, m);
        if (r2) cb(ctx, 8, o, m2);
        naif(F, o, 0, ct, I, m, &r1, m2, &r2, m3, &r3);
        if (r1) cb(ctx, 13, o, m);
        if (r2) cb(ctx, 15, o, m2);
        if (r3) cb(ctx, 16, o, m3);
        naif(F, o, 1, ct, I, m, &r1, m2, &r2, m3, &r3);
        if (r1) cb(ctx, 14, o, m);
        if (r2) cb(ctx, 17, o, m2);
        if (r3) cb(ctx, 18, o, m3);
        if (ct) {
            rs(F, o, 0, I, m, &r1, m2, &r2);
            if (r1) cb(ctx, 9, o, m);
            if (r2) cb(ctx, 10, o, m2);
            rs(F, o, 1, I, m, &r1, m2, &r2);
            if (r1) cb(ctx, 11, o, m);
            if (r2) cb(ctx, 12, o, m2);
        }
    }
}

// ---------------------------------------------------------------------------
// L'échantillonneur en mode « émission » : un tirage complet, ordre d'émission,
// et le nombre de mots consommés (pour enchaîner les tirages d'une journée).
// ---------------------------------------------------------------------------

static int emet(flux *F, int deb, int e, uint8_t *out) {
    int i = deb;
    if (e <= 2) {
        uint64_t vu_lo = 0, vu_hi = 0; int got = 0;
        while (got < DRAWN) {
            if (i - deb >= MOTS - 8) return -1;
            uint32_t r = mot(F, i++);
            uint32_t n = e == 0 ? r % POOL : e == 1 ? fflot(r, POOL) : r / 26843546u;
            uint64_t bit = 1ULL << (n & 63); uint64_t *vu = n < 64 ? &vu_lo : &vu_hi;
            if (*vu & bit) continue;
            *vu |= bit; out[got++] = (uint8_t)(n + 1);
        }
        return i - deb;
    }
    uint8_t arr[POOL]; arr_init(arr);
    int flot;
    switch (e) {
    case 3: case 4:
        flot = e == 4;
        for (int k = 0; k < DRAWN; k++) echange(arr, k, k + (int)tire(mot(F, i++), (uint32_t)(POOL - k), flot));
        memcpy(out, arr, DRAWN); return DRAWN;
    case 5: case 6:
        flot = e == 6;
        for (int k = 0; k < DRAWN; k++) { int p = POOL - 1 - k; echange(arr, p, (int)tire(mot(F, i++), (uint32_t)(p + 1), flot)); }
        memcpy(out, arr + POOL - DRAWN, DRAWN); return DRAWN;
    case 7: case 8:                                    // mélange complet depuis la fin : 79 mots
        flot = e == 8;
        for (int p = POOL - 1; p >= 1; p--) echange(arr, p, (int)tire(mot(F, i++), (uint32_t)(p + 1), flot));
        memcpy(out, arr, DRAWN); return POOL - 1;
    case 9: case 10: case 11: case 12:
        flot = e >= 11;
        for (int p = 1; p < POOL; p++) echange(arr, p, (int)tire(mot(F, i++), (uint32_t)(p + 1), flot));
        memcpy(out, (e == 9 || e == 11) ? arr : arr + POOL - DRAWN, DRAWN); return POOL - 1;
    case 13: case 14:
        flot = e == 14;
        for (int p = 0; p < DRAWN; p++) echange(arr, p, (int)tire(mot(F, i++), POOL, flot));
        memcpy(out, arr, DRAWN); return DRAWN;
    case 15: case 16: case 17: case 18:
        flot = e >= 17;
        for (int p = 0; p < POOL; p++) echange(arr, p, (int)tire(mot(F, i++), POOL, flot));
        memcpy(out, (e == 15 || e == 17) ? arr : arr + POOL - DRAWN, DRAWN); return POOL;
    default: {                                         // 19, 20 : sélection
        flot = e == 19; int got = 0, k;
        for (k = 0; k < POOL && got < DRAWN; k++) {
            uint32_t r = mot(F, i++), reste = POOL - k, besoin = DRAWN - got;
            int pris = flot ? ((uint64_t)r * reste < ((uint64_t)besoin << 31)) : (fmod_(r, reste) < besoin);
            if (pris) out[got++] = (uint8_t)(k + 1);
        }
        return k;
    }
    }
}

// ---------------------------------------------------------------------------
// Lecture des fichiers
// ---------------------------------------------------------------------------

typedef struct { int64_t ts, id; uint8_t ens[DRAWN]; } tirage;

static int lit_ensembles(const char *fn, uint8_t (*ens)[DRAWN], tirage *tir, int max, int avec_tsid) {
    FILE *f = fopen(fn, "r");
    if (!f) { perror(fn); exit(2); }
    int n = 0; char ligne[1024];
    while (n < max && fgets(ligne, sizeof ligne, f)) {
        char *p = ligne; int k = 0; long long v[DRAWN + 2]; int nv = 0;
        while (nv < DRAWN + 2) { char *q; long long x = strtoll(p, &q, 10); if (q == p) break; v[nv++] = x; p = q; }
        int deb = avec_tsid ? 2 : 0;
        if (nv < deb + DRAWN) continue;
        uint8_t e[DRAWN];
        for (k = 0; k < DRAWN; k++) { if (v[deb + k] < 1 || v[deb + k] > POOL) { fprintf(stderr, "numero hors 1..80 ligne %d\n", n + 1); exit(2); } e[k] = (uint8_t)v[deb + k]; }
        if (ens) memcpy(ens[n], e, DRAWN);
        if (tir) { tir[n].ts = v[0]; tir[n].id = v[1]; memcpy(tir[n].ens, e, DRAWN); }
        n++;
    }
    fclose(f);
    return n;
}

static int nthreads(void) { const char *s = getenv("SWEEP_THREADS"); int n = s ? atoi(s) : 4; return n < 1 ? 1 : n > 64 ? 64 : n; }

// ---------------------------------------------------------------------------
// L'index de toute l'archive : listes inversées des 5-sous-ensembles
// ---------------------------------------------------------------------------
// L'index des journées ne voit que le premier tirage de chaque bloc : il
// suppose une graine par bloc. Pour tester une graine inconnue PAR TIRAGE
// (srandom(x) avant chaque tirage, x quelconque), il faut reconnaître un
// ensemble engendré parmi les 70 560 ensembles triés de l'archive. Un index
// bit à bit sur les tirages (1 103 mots par numéro) coûterait ≈ 3 000 cycles
// par (graine, échantillonneur, décalage) ; on préfère des listes inversées :
// chaque tirage trié engendre C(20,5) = 15 504 sous-ensembles à cinq numéros,
// et le rang combinatoire de {a<b<c<d<e} (numéros 0..79) est
//     C(a,1) + C(b,2) + C(c,3) + C(d,4) + C(e,5)  <  C(80,5) = 24 040 016.
// Pour n tirages les listes totalisent 15 504·n entrées (1,09·10^9 pour
// l'archive, 4,4 Go) et une requête lit en moyenne 15 504·n / C(80,5) ≈ 45
// candidats, chacun vérifié par une comparaison de masque à 80 bits : un
// ensemble engendré est reconnu en ≈ 400 cycles, mémoire comprise. Le taux de
// fausse touche par (graine, échantillonneur, décalage) est n / C(80,20)
// = 2·10^-14 : sur 2^32 graines et 32 combinaisons, 3·10^-3 fausses attendues.

#define NSUB5 24040016u

typedef struct {
    int nt;
    uint64_t (*mk)[2];                  // masque d'appartenance de chaque tirage (bits 0..79)
    uint32_t *off;                      // NSUB5 + 1 débuts de liste
    uint32_t *lst;                      // 15 504·nt entrées : indice de tirage (17 bits) | empreinte << 17
    uint32_t binom[POOL + 1][6];
} arch_index;

static inline void trie5(uint8_t *v) {
    for (int a = 1; a < 5; a++) { uint8_t x = v[a]; int b = a; while (b > 0 && v[b - 1] > x) { v[b] = v[b - 1]; b--; } v[b] = x; }
}
static inline uint32_t rang5(const arch_index *A, const uint8_t *v) {
    return A->binom[v[0]][1] + A->binom[v[1]][2] + A->binom[v[2]][3] + A->binom[v[3]][4] + A->binom[v[4]][5];
}

// empreinte de 15 bits de l'ensemble (ses deux masques) : rangée avec l'indice du
// tirage dans chaque entrée de liste (t < 2^17), elle évite de toucher mk[t] pour
// les ~45 candidats d'une requête — un seul accès aléatoire par requête au lieu de 45
static inline uint32_t empreinte(uint64_t m0, uint64_t m1) {
    return (uint32_t)(((m0 * 0x9E3779B97F4A7C15ULL) ^ (m1 * 0xC2B2AE3D27D4EB4FULL)) >> 49);
}

static void arch_construit(arch_index *A, const uint8_t (*ens)[DRAWN], int nt) {
    memset(A->binom, 0, sizeof A->binom);
    for (int n = 0; n <= POOL; n++) {
        A->binom[n][0] = 1;
        for (int k = 1; k <= 5 && k <= n; k++) A->binom[n][k] = A->binom[n - 1][k - 1] + A->binom[n - 1][k];
    }
    A->nt = nt;
    if (nt >= (1 << 17)) { fprintf(stderr, "index archive : au plus %d tirages (17 bits + 15 bits d'empreinte)\n", (1 << 17) - 1); exit(2); }
    uint64_t total = (uint64_t)nt * 15504u;
    A->mk = calloc((size_t)nt, sizeof *A->mk);
    A->off = calloc((size_t)NSUB5 + 1, sizeof *A->off);
    A->lst = malloc((size_t)total * sizeof *A->lst);
    uint32_t *cur = malloc((size_t)NSUB5 * sizeof *cur);
    if (!A->mk || !A->off || !A->lst || !cur) { fprintf(stderr, "memoire : index archive de %.2f Go\n", total * 4 / 1e9); exit(4); }
    uint8_t (*tri)[DRAWN] = malloc((size_t)nt * DRAWN);
    if (!tri) exit(4);
    for (int t = 0; t < nt; t++) {
        for (int k = 0; k < DRAWN; k++) { uint8_t v = (uint8_t)(ens[t][k] - 1); tri[t][k] = v; A->mk[t][v >> 6] |= 1ULL << (v & 63); }
        for (int a = 1; a < DRAWN; a++) { uint8_t x = tri[t][a]; int b = a; while (b > 0 && tri[t][b - 1] > x) { tri[t][b] = tri[t][b - 1]; b--; } tri[t][b] = x; }
    }
    // deux passes : comptage (dans off[r+1]) puis remplissage
    for (int passe = 0; passe < 2; passe++) {
        if (passe == 1) { for (uint32_t r = 1; r <= NSUB5; r++) A->off[r] += A->off[r - 1]; memcpy(cur, A->off, (size_t)NSUB5 * sizeof *cur); }
        for (int t = 0; t < nt; t++) {
            const uint8_t *v = tri[t];
            for (int a = 0; a < DRAWN; a++) { uint32_t ra = A->binom[v[a]][1];
            for (int b = a + 1; b < DRAWN; b++) { uint32_t rb = ra + A->binom[v[b]][2];
            for (int c = b + 1; c < DRAWN; c++) { uint32_t rc = rb + A->binom[v[c]][3];
            for (int d = c + 1; d < DRAWN; d++) { uint32_t rd = rc + A->binom[v[d]][4];
            for (int e = d + 1; e < DRAWN; e++) {
                uint32_t r = rd + A->binom[v[e]][5];
                if (passe == 0) A->off[r + 1]++; else A->lst[cur[r]++] = (uint32_t)t | (empreinte(A->mk[t][0], A->mk[t][1]) << 17);
            } } } } }
        }
    }
    free(cur); free(tri);
}

typedef void (*arch_cb)(void *ctx, int e, int o, int t);

typedef struct { uint32_t r, h; uint64_t need0, need1; uint8_t e, o; } requete;

// tous les échantillonneurs et décalages sur une graine amorcée, contre l'archive :
// on émet les ensembles d'abord (et on préchauffe les listes), on les cherche ensuite
static void arch_essaie_tout(flux *F, const arch_index *A, int OP, int OC, arch_cb cb, void *ctx) {
    requete Q[NECH * OMAX]; int nq = 0;
    for (int e = 0; e < NECH; e++)
        for (int o = 0; o <= (complet(e) ? OC : OP); o++) {
            uint8_t out[DRAWN];
            if (emet(F, o, e, out) < 0) continue;
            requete *q = &Q[nq++];
            q->need0 = q->need1 = 0;
            for (int k = 0; k < DRAWN; k++) { uint8_t v = (uint8_t)(out[k] - 1); if (v < 64) q->need0 |= 1ULL << v; else q->need1 |= 1ULL << (v - 64); }
            uint8_t v5[5]; for (int k = 0; k < 5; k++) v5[k] = (uint8_t)(out[k] - 1);
            trie5(v5);
            q->r = rang5(A, v5); q->h = empreinte(q->need0, q->need1); q->e = (uint8_t)e; q->o = (uint8_t)o;
            __builtin_prefetch(&A->off[q->r]);
        }
    uint32_t deb[NECH * OMAX], fin[NECH * OMAX];
    for (int i = 0; i < nq; i++) { deb[i] = A->off[Q[i].r]; fin[i] = A->off[Q[i].r + 1]; if (deb[i] < fin[i]) __builtin_prefetch(&A->lst[deb[i]]); }
    for (int i = 0; i < nq; i++)
        for (uint32_t p = deb[i]; p < fin[i]; p++) {
            uint32_t ent = A->lst[p];
            if ((ent >> 17) != Q[i].h) continue;
            uint32_t t = ent & ((1u << 17) - 1);
            if ((A->mk[t][0] & Q[i].need0) == Q[i].need0 && (A->mk[t][1] & Q[i].need1) == Q[i].need1) cb(ctx, Q[i].e, Q[i].o, (int)t);
        }
}

// ---------------------------------------------------------------------------
// --balaye : 2^32 graines contre l'index des journées (ou --archive : contre
// l'index de tous les tirages)
// ---------------------------------------------------------------------------

static pthread_mutex_t verrou = PTHREAD_MUTEX_INITIALIZER;

typedef struct {
    int V, OP, OC;
    const index_t *I;                   // index des journées (--balaye)
    const arch_index *A;                // ou index de l'archive (--archive)
    uint64_t lo, hi, pas;
    uint64_t suivant_chunk;
    uint64_t faits;
    long touches;
    int silencieux;
    // plantes (selftest)
    const int *pl_ech, *pl_dec; const uint32_t *pl_graine; int npl;
    uint8_t *pl_exact;          // journée plantée rendue avec sa graine ET son décalage
    long pl_ok, pl_alias, pl_faux;
} balayage;

typedef struct { balayage *B; uint32_t graine; } cb_ctx;

// une touche : la journée (ou le tirage) d est rendue par (graine, ech, dec)
static void touche_une(cb_ctx *c, int e, int o, int d) {
    balayage *B = c->B;
    pthread_mutex_lock(&verrou);
    B->touches++;
    if (B->npl) {
        // une plante est retrouvée si la journée plantée d est rendue avec sa graine
        // et son décalage ; l'échantillonneur peut être un alias (rejet_kr ≈ rejet_flot).
        // La même graine à un autre décalage est un alias légitime : pour les
        // échantillonneurs à rejet, les décalages o et o+1 donnent le même ensemble
        // quand le mot o revient parmi les 20 suivants (≈ 23 % des cas). Seule une
        // graine étrangère ou une journée non plantée est une fausse touche.
        if (d < B->npl && B->pl_graine[d] == c->graine) {
            if (B->pl_dec[d] == o) { B->pl_ok++; B->pl_exact[d] = 1; }
            else B->pl_alias++;
        } else B->pl_faux++;
    }
    if (!B->silencieux)
        printf("TOUCHE variante=%d %s graine=%u ech=%d %s decalage=%d %s=%d\n",
               B->V, VAR[B->V].nom, c->graine, e, ECH[e], o, B->A ? "tirage" : "jour", d);
    fflush(stdout);
    pthread_mutex_unlock(&verrou);
}

static void cb_touche(void *vctx, int e, int o, const uint64_t *m) {
    cb_ctx *c = (cb_ctx *)vctx;
    for (int w = 0; w < c->B->I->nw; w++) {
        uint64_t x = m[w];
        while (x) { int d = w * 64 + __builtin_ctzll(x); x &= x - 1; touche_une(c, e, o, d); }
    }
}

static void cb_arch(void *vctx, int e, int o, int t) { touche_une((cb_ctx *)vctx, e, o, t); }

static void *balaye_fil(void *arg) {
    balayage *B = (balayage *)arg;
    flux F;
    for (;;) {
        pthread_mutex_lock(&verrou);
        uint64_t a = B->suivant_chunk;
        if (a >= B->hi) { pthread_mutex_unlock(&verrou); break; }
        uint64_t b = a + B->pas; if (b > B->hi) b = B->hi;
        B->suivant_chunk = b;
        pthread_mutex_unlock(&verrou);
        for (uint64_t s = a; s < b; s++) {
            cb_ctx c = { B, (uint32_t)s };
            flux_init(&F, B->V, (uint32_t)s);
            if (B->A) arch_essaie_tout(&F, B->A, B->OP, B->OC, cb_arch, &c);
            else essaie_tout(&F, B->I, B->OP, B->OC, cb_touche, &c);
        }
        pthread_mutex_lock(&verrou);
        B->faits += b - a;
        pthread_mutex_unlock(&verrou);
    }
    return NULL;
}

static void balaye(balayage *B, int verbeux) {
    int nt = nthreads();
    pthread_t th[64];
    B->suivant_chunk = B->lo; B->faits = 0; B->touches = 0;
    B->pas = (B->hi - B->lo) / (uint64_t)(nt * 64) + 1;
    if (B->pas > (1u << 22)) B->pas = 1u << 22;
    double t0 = horloge(), tprec = t0;
    for (int i = 0; i < nt; i++) pthread_create(&th[i], NULL, balaye_fil, B);
    if (verbeux) {
        for (;;) {
            struct timespec ts = { 1, 0 }; nanosleep(&ts, NULL);
            pthread_mutex_lock(&verrou);
            uint64_t faits = B->faits; long touches = B->touches;
            pthread_mutex_unlock(&verrou);
            double t = horloge();
            if (faits >= B->hi - B->lo) break;
            if (t - tprec >= 60) {
                printf("AVANCE variante=%d graines=%llu/%llu touches=%ld sec=%.0f\n", B->V,
                       (unsigned long long)faits, (unsigned long long)(B->hi - B->lo), touches, t - t0);
                fflush(stdout); tprec = t;
            }
        }
    }
    for (int i = 0; i < nt; i++) pthread_join(th[i], NULL);
}

// ---------------------------------------------------------------------------
// --selftest
// ---------------------------------------------------------------------------

static uint64_t sm_x = 0x9E3779B97F4A7C15ULL;
static uint32_t alea32(void) {
    sm_x += 0x9E3779B97F4A7C15ULL;
    uint64_t z = sm_x;
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return (uint32_t)((z ^ (z >> 31)) >> 32);
}
static void ensemble_alea(uint8_t *e) {
    uint8_t arr[POOL]; arr_init(arr);
    for (int i = 0; i < DRAWN; i++) echange(arr, i, i + (int)(alea32() % (uint32_t)(POOL - i)));
    memcpy(e, arr, DRAWN);
}

static int test_libc(void) {
    static char buf[256];
    const uint32_t graines[] = { 0u, 1u, 2u, 12345u, 2147483647u, 2147483648u, 2147483649u,
                                 4294967295u, 0xDEADBEEFu, 0x12345678u, 987654321u, 42u };
    const int ng = (int)(sizeof graines / sizeof graines[0]);
    const int taille[4] = { 128, 32, 64, 256 }, Vt[4] = { 0, 1, 2, 3 };
    int ecarts_tot = 0;
    for (int passe = 0; passe < 5; passe++) {
        int V = passe == 0 ? 0 : Vt[passe - 1];
        long ecarts = 0, sorties = 0;
        for (int g = 0; g < ng; g++) {
            if (passe == 0) { initstate(1, buf, 128); srandom(graines[g]); }
            else initstate(graines[g], buf, taille[passe - 1]);
            gstate st; amorce(V, graines[g], &st);
            for (int k = 0; k < 300; k++) { uint32_t a = (uint32_t)random(), b = suivant(&st); sorties++; if (a != b) ecarts++; }
        }
        printf("LIBC %s %s graines=%d sorties=%ld ecarts=%ld\n", VAR[V].nom,
               passe == 0 ? "srandom" : "initstate", ng, sorties, ecarts);
        ecarts_tot += ecarts;
    }
    return ecarts_tot == 0;
}

static int test_plantes(int V, int OP, int OC) {
    static uint8_t ens[NJMAX][DRAWN];
    static int pl_ech[NJMAX], pl_dec[NJMAX];
    static uint32_t pl_graine[NJMAX];
    static index_t I;
    int nj = 370, npl = 0;
    uint32_t s0 = alea32();
    for (int e = 0; e < NECH; e++)
        for (int o = 0; o <= (complet(e) ? OC : OP); o++) {
            uint32_t g = s0 + (uint32_t)npl;
            flux F; flux_init(&F, V, g);
            uint8_t out[DRAWN];
            if (emet(&F, o, e, out) < 0) { fprintf(stderr, "emission impossible\n"); exit(3); }
            // trié, comme l'archive
            for (int a = 0; a < DRAWN; a++) for (int b = a + 1; b < DRAWN; b++) if (out[b] < out[a]) { uint8_t t = out[a]; out[a] = out[b]; out[b] = t; }
            memcpy(ens[npl], out, DRAWN);
            pl_ech[npl] = e; pl_dec[npl] = o; pl_graine[npl] = g; npl++;
        }
    for (int d = npl; d < nj; d++) ensemble_alea(ens[d]);
    index_construit(&I, ens, nj);
    balayage B; memset(&B, 0, sizeof B);
    B.V = V; B.OP = OP; B.OC = OC; B.I = &I;
    B.lo = (uint64_t)s0 - 700; B.hi = (uint64_t)s0 + (uint64_t)npl + 700;
    // fenêtre modulo 2^32 : s0 est tiré loin des bords
    if ((uint64_t)s0 < 1000 || (uint64_t)s0 + npl + 1000 > 0xFFFFFFFFull) { B.lo = 0; B.hi = (uint64_t)npl + 2000; }
    B.silencieux = 1;
    static uint8_t pl_exact[NJMAX]; memset(pl_exact, 0, sizeof pl_exact);
    B.pl_ech = pl_ech; B.pl_dec = pl_dec; B.pl_graine = pl_graine; B.npl = npl; B.pl_exact = pl_exact;
    // chaque journée plantée doit être rendue au moins une fois avec sa graine et son
    // décalage exacts ; rejet_kr et rejet_flot sont des alias l'un de l'autre (même
    // ensemble 99,99 % des fois) et les décalages voisins d'un rejet le sont souvent
    balaye(&B, 0);
    int exactes = 0;
    for (int d = 0; d < npl; d++) exactes += pl_exact[d];
    // auto-cohérence de l'émission : le tirage rendu par emet() est-il celui indexé ?
    int retrouves = 0;
    for (int d = 0; d < npl; d++) {
        flux F; flux_init(&F, V, pl_graine[d]);
        uint8_t out[DRAWN]; emet(&F, pl_dec[d], pl_ech[d], out);
        for (int a = 0; a < DRAWN; a++) for (int b = a + 1; b < DRAWN; b++) if (out[b] < out[a]) { uint8_t t = out[a]; out[a] = out[b]; out[b] = t; }
        retrouves += memcmp(out, ens[d], DRAWN) == 0;
    }
    printf("PLANTES %s OP=%d OC=%d plantes=%d exactes=%d/%d alias=%ld fausses=%ld emission_coherente=%d/%d\n",
           VAR[V].nom, OP, OC, npl, exactes, npl, B.pl_alias, B.pl_faux, retrouves, npl);
    return exactes == npl && B.pl_faux == 0 && retrouves == npl;
}

// --selftest-archive : nt tirages aléatoires, 149 plantés (une par (ech, dec)),
// index des 5-sous-ensembles, balayage d'une fenêtre autour des graines plantées
static int test_archive(int V, int nt, int OP, int OC) {
    uint8_t (*ens)[DRAWN] = malloc((size_t)nt * DRAWN);
    static int pl_ech[NECH * OMAX], pl_dec[NECH * OMAX];
    static uint32_t pl_graine[NECH * OMAX];
    static uint8_t pl_exact[NECH * OMAX];
    if (!ens) exit(4);
    int npl = 0;
    uint32_t s0 = alea32();
    for (int e = 0; e < NECH; e++)
        for (int o = 0; o <= (complet(e) ? OC : OP); o++) {
            uint32_t g = s0 + (uint32_t)npl;
            flux F; flux_init(&F, V, g);
            uint8_t out[DRAWN];
            if (emet(&F, o, e, out) < 0) { fprintf(stderr, "emission impossible\n"); exit(3); }
            for (int a = 0; a < DRAWN; a++) for (int b = a + 1; b < DRAWN; b++) if (out[b] < out[a]) { uint8_t t = out[a]; out[a] = out[b]; out[b] = t; }
            memcpy(ens[npl], out, DRAWN);
            pl_ech[npl] = e; pl_dec[npl] = o; pl_graine[npl] = g; npl++;
        }
    for (int t = npl; t < nt; t++) ensemble_alea(ens[t]);
    double t0 = horloge();
    static arch_index A; arch_construit(&A, ens, nt);
    double tb = horloge() - t0;
    balayage B; memset(&B, 0, sizeof B);
    B.V = V; B.OP = OP; B.OC = OC; B.A = &A;
    B.lo = (uint64_t)s0 - 700; B.hi = (uint64_t)s0 + (uint64_t)npl + 700;
    if ((uint64_t)s0 < 1000 || (uint64_t)s0 + npl + 1000 > 0xFFFFFFFFull) { B.lo = 0; B.hi = (uint64_t)npl + 2000; }
    B.silencieux = 1;
    memset(pl_exact, 0, sizeof pl_exact);
    B.pl_ech = pl_ech; B.pl_dec = pl_dec; B.pl_graine = pl_graine; B.npl = npl; B.pl_exact = pl_exact;
    t0 = horloge();
    balaye(&B, 0);
    double ts = horloge() - t0;
    int exactes = 0;
    for (int d = 0; d < npl; d++) exactes += pl_exact[d];
    printf("PLANTES_ARCHIVE %s tirages=%d OP=%d OC=%d plantes=%d exactes=%d/%d alias=%ld fausses=%ld construction=%.1fs balayage=%.2fs graines=%llu us_par_graine=%.2f\n",
           VAR[V].nom, nt, OP, OC, npl, exactes, npl, B.pl_alias, B.pl_faux, tb, ts,
           (unsigned long long)(B.hi - B.lo), 1e6 * ts / (double)(B.hi - B.lo));
    free(A.mk); free(A.off); free(A.lst); free(ens);
    return exactes == npl && B.pl_faux == 0;
}

// ---------------------------------------------------------------------------
// --horloge et --pid : graines de convention, tirage par tirage
// ---------------------------------------------------------------------------

typedef struct {
    int V, mode, OP, OC; int64_t D; const tirage *tir; int nt; int suivant_t; long essais, touches;
} conv_job;

typedef struct { conv_job *J; int t; uint32_t graine; const char *conv; } conv_ctx;

static void cb_conv(void *vctx, int e, int o, const uint64_t *m) {
    conv_ctx *c = (conv_ctx *)vctx; (void)m;
    pthread_mutex_lock(&verrou);
    c->J->touches++;
    printf("TOUCHE variante=%d %s tirage=%d ts=%lld id=%lld conv=%s graine=%u ech=%d %s decalage=%d\n",
           c->J->V, VAR[c->J->V].nom, c->t, (long long)c->J->tir[c->t].ts, (long long)c->J->tir[c->t].id,
           c->conv, c->graine, e, ECH[e], o);
    fflush(stdout);
    pthread_mutex_unlock(&verrou);
}

static void essaie_graine(conv_job *J, index_t *I, int t, const char *conv, uint64_t g, long *essais) {
    flux F; flux_init(&F, J->V, (uint32_t)g);
    conv_ctx c = { J, t, (uint32_t)g, conv };
    essaie_tout(&F, I, J->OP, J->OC, cb_conv, &c);
    (*essais)++;
}

static void *conv_fil(void *arg) {
    conv_job *J = (conv_job *)arg;
    static __thread index_t I;
    long essais = 0;
    for (;;) {
        pthread_mutex_lock(&verrou);
        int t = J->suivant_t++;
        pthread_mutex_unlock(&verrou);
        if (t >= J->nt) break;
        uint8_t ens[1][DRAWN]; memcpy(ens[0], J->tir[t].ens, DRAWN);
        index_construit(&I, ens, 1);
        int64_t ts = J->tir[t].ts, id = J->tir[t].id;
        if (J->mode == 0) {
            for (int64_t d = -J->D; d <= J->D; d++) {
                essaie_graine(J, &I, t, "ts+d", (uint64_t)(ts + d), &essais);
                essaie_graine(J, &I, t, "id+d", (uint64_t)(id + d), &essais);
            }
            for (int64_t d = -3; d <= 3; d++) {
                essaie_graine(J, &I, t, "ts/60+d", (uint64_t)(ts / 60 + d), &essais);
                essaie_graine(J, &I, t, "ts/300+d", (uint64_t)(ts / 300 + d), &essais);
                essaie_graine(J, &I, t, "ts^id+d", (uint64_t)((ts ^ id) + d), &essais);
                essaie_graine(J, &I, t, "ts+id+d", (uint64_t)(ts + id + d), &essais);
                essaie_graine(J, &I, t, "ts*1000+d", (uint64_t)(ts * 1000 + d), &essais);
                essaie_graine(J, &I, t, "id*1000+d", (uint64_t)(id * 1000 + d), &essais);
                essaie_graine(J, &I, t, "ts*id+d", (uint64_t)(ts * id + d), &essais);
            }
        } else {
            for (int64_t p = 1; p < J->D; p++) {
                essaie_graine(J, &I, t, "pid", (uint64_t)p, &essais);
                essaie_graine(J, &I, t, "ts^pid", (uint64_t)(ts ^ p), &essais);
                essaie_graine(J, &I, t, "ts+pid", (uint64_t)(ts + p), &essais);
            }
        }
    }
    pthread_mutex_lock(&verrou); J->essais += essais; pthread_mutex_unlock(&verrou);
    return NULL;
}

// ---------------------------------------------------------------------------
// main
// ---------------------------------------------------------------------------

static void usage(void) {
    fprintf(stderr, "usage : --selftest [OP OC] | --selftest-archive [nt OP OC] | --balaye V lo hi jours.txt [OP OC] | --archive V lo hi archive.txt [OP OC] | --suite V graine ech dec n | --horloge V archive.txt D [OP OC] | --pid V archive.txt pidmax [OP OC]\n");
    exit(1);
}

int main(int argc, char **argv) {
    for (uint32_t d = 1; d <= POOL; d++) MTAB[d] = UINT64_C(0xFFFFFFFFFFFFFFFF) / d + 1;
    if (argc < 2) usage();
    if (!strcmp(argv[1], "--selftest")) {
        int OP = argc > 2 ? atoi(argv[2]) : 8, OC = argc > 3 ? atoi(argv[3]) : 4;
        int ok = test_libc(), n_ok = 0;
        for (int V = 0; V < NVAR; V++) n_ok += test_plantes(V, OP, OC);
        printf("AUTOTEST libc=%s plantes=%d/%d %s\n", ok ? "OK" : "ECART", n_ok, NVAR, (ok && n_ok == NVAR) ? "OK" : "ECHEC");
        return (ok && n_ok == NVAR) ? 0 : 1;
    }
    if (!strcmp(argv[1], "--selftest-archive")) {
        int nt = argc > 2 ? atoi(argv[2]) : 20000, OP = argc > 3 ? atoi(argv[3]) : 8, OC = argc > 4 ? atoi(argv[4]) : 4;
        int n_ok = 0; const int Vt[4] = { 0, 6, 4, 5 };
        for (int k = 0; k < 4; k++) n_ok += test_archive(Vt[k], nt, OP, OC);
        printf("AUTOTEST_ARCHIVE plantes=%d/4 %s\n", n_ok, n_ok == 4 ? "OK" : "ECHEC");
        return n_ok == 4 ? 0 : 1;
    }
    if (!strcmp(argv[1], "--balaye") || !strcmp(argv[1], "--archive")) {
        if (argc < 6) usage();
        int arch = !strcmp(argv[1], "--archive");
        int V = atoi(argv[2]);
        if (V < 0 || V >= NVAR) usage();
        uint64_t lo = strtoull(argv[3], NULL, 0), hi = strtoull(argv[4], NULL, 0);
        int OP = argc > 6 ? atoi(argv[6]) : (arch ? 1 : 8), OC = argc > 7 ? atoi(argv[7]) : (arch ? 0 : 4);
        if (OP > OMAX - 1) OP = OMAX - 1;
        if (OC > OP) OC = OP;
        static uint8_t ens[80000][DRAWN];
        static index_t I;
        static arch_index A;
        int nj = lit_ensembles(argv[5], ens, NULL, arch ? 80000 : NJMAX, 0);
        balayage B; memset(&B, 0, sizeof B);
        double t0 = horloge();
        if (arch) { arch_construit(&A, ens, nj); B.A = &A; }
        else { index_construit(&I, ens, nj); B.I = &I; }
        B.V = V; B.OP = OP; B.OC = OC; B.lo = lo; B.hi = hi;
        printf("DEBUT %s variante=%d %s lo=%llu hi=%llu %s=%d OP=%d OC=%d fils=%d construction=%.1fs\n",
               arch ? "archive" : "journees", V, VAR[V].nom, (unsigned long long)lo, (unsigned long long)hi,
               arch ? "tirages" : "journees", nj, OP, OC, nthreads(), horloge() - t0);
        fflush(stdout);
        t0 = horloge();
        balaye(&B, 1);
        printf("FIN %s variante=%d %s lo=%llu hi=%llu graines=%llu touches=%ld sec=%.1f\n", arch ? "archive" : "journees",
               V, VAR[V].nom, (unsigned long long)lo, (unsigned long long)hi, (unsigned long long)(hi - lo), B.touches, horloge() - t0);
        return 0;
    }
    if (!strcmp(argv[1], "--suite")) {
        if (argc < 7) usage();
        int V = atoi(argv[2]); uint32_t g = (uint32_t)strtoull(argv[3], NULL, 0);
        int e = atoi(argv[4]), o = atoi(argv[5]), n = atoi(argv[6]);
        if (V < 0 || V >= NVAR || e < 0 || e >= NECH) usage();
        int pos = o;
        for (int k = 0; k < n; k++) {
            uint8_t out[DRAWN];
            // rejouer sans tampon : repartir d'un flux frais, consommer pos mots, émettre
            flux H; flux_init(&H, V, g);
            for (int i = 0; i < pos; i++) suivant(&H.st);
            H.n = 0;
            int c = emet(&H, 0, e, out);
            if (c < 0) { printf("TIRAGE %d impossible\n", k); break; }
            printf("TIRAGE %d mots=%d..%d emission", k, pos, pos + c - 1);
            for (int i = 0; i < DRAWN; i++) printf(" %d", out[i]);
            for (int a = 0; a < DRAWN; a++) for (int b = a + 1; b < DRAWN; b++) if (out[b] < out[a]) { uint8_t t = out[a]; out[a] = out[b]; out[b] = t; }
            printf(" trie");
            for (int i = 0; i < DRAWN; i++) printf(" %d", out[i]);
            printf("\n");
            pos += c;
        }
        return 0;
    }
    if (!strcmp(argv[1], "--horloge") || !strcmp(argv[1], "--pid")) {
        if (argc < 5) usage();
        int V = atoi(argv[2]);
        if (V < 0 || V >= NVAR) usage();
        static tirage tir[80000];
        int nt = lit_ensembles(argv[3], NULL, tir, 80000, 1);
        conv_job J; memset(&J, 0, sizeof J);
        J.V = V; J.mode = !strcmp(argv[1], "--pid"); J.D = strtoll(argv[4], NULL, 0); J.tir = tir; J.nt = nt;
        J.OP = argc > 5 ? atoi(argv[5]) : OMAX - 1; J.OC = argc > 6 ? atoi(argv[6]) : OMAX - 1;
        if (J.OP > OMAX - 1) J.OP = OMAX - 1;
        if (J.OC > J.OP) J.OC = J.OP;
        int nth = nthreads(); pthread_t th[64];
        printf("DEBUT %s variante=%d %s tirages=%d D=%lld OP=%d OC=%d fils=%d\n", argv[1], V, VAR[V].nom, nt, (long long)J.D, J.OP, J.OC, nth);
        fflush(stdout);
        double t0 = horloge(), tprec = t0;
        for (int i = 0; i < nth; i++) pthread_create(&th[i], NULL, conv_fil, &J);
        for (;;) {
            struct timespec tsl = { 1, 0 }; nanosleep(&tsl, NULL);
            pthread_mutex_lock(&verrou); int fait = J.suivant_t; long touches = J.touches; pthread_mutex_unlock(&verrou);
            if (fait >= nt + nth) break;
            if (horloge() - tprec >= 60) {
                printf("AVANCE %s variante=%d tirages=%d/%d touches=%ld sec=%.0f\n", argv[1], V, fait < nt ? fait : nt, nt, touches, horloge() - t0);
                fflush(stdout); tprec = horloge();
            }
        }
        for (int i = 0; i < nth; i++) pthread_join(th[i], NULL);
        printf("FIN %s variante=%d %s tirages=%d graines=%ld touches=%ld sec=%.1f\n", argv[1], V, VAR[V].nom, nt, J.essais, J.touches, horloge() - t0);
        return 0;
    }
    usage();
    return 1;
}
