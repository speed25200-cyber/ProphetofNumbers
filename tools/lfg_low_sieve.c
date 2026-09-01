// lfg_low_sieve — le crible des 5L bits BAS d'un Fibonacci retardé additif contre
// une fenêtre de tirages triés consécutifs (§155).
//
// LE GÉNÉRATEUR : r_i = r_{i−K} + r_{i−L} mod 2^32 (glibc random() : TYPE_1 (K, L) =
// (3, 7), TYPE_2 (1, 15), TYPE_3 (3, 31), TYPE_4 (1, 63)), sortie r >> 1, numéro
// (sortie mod 80) + 1. Ici L ≤ 7 : les treize trinômes primitifs de degré 2 à 7.
//
// LE THÉORÈME QU'IL EXÉCUTE (Théorème Q étendu, THEORIE_ETAT.md §7.7). La
// récurrence est linéaire, donc AUTONOME modulo 2^m : r_i mod 32 ne dépend que des
// r_j mod 32 ; et (v − 1) mod 16 = (r >> 1) mod 16 = les bits 1 à 4 de r. L'état
// bas vaut 5L bits — 2^35 pour L = 7 — et non 32L. Chaque mot contraint filtre
// ρ = 1 − C(75,20)/C(80,20) = 0,773 (un résidu mod 16 est vide de l'ensemble avec
// probabilité 0,227).
//
// LES MODES sont ceux de lcg64_sieve (§152) : 0 = Fisher-Yates partiel par modulo,
// 1 = Collections.shuffle lu par ses vingt dernières cases — les deux mots SÛRS 0
// et 16 de chaque tirage (lemme des mots 0 et 16), à pas constant STRIDE ;
// 2 = rejet des doublons, TOUS les mots contraints, σ ≥ 20 mots par tirage,
// 0..PERDUS mots perdus entre deux tirages (lemme des décalés : les survivants
// d'un vrai flux sont ses registres f^k(vrai)).
//
// L'ÉNUMÉRATION VECTORIELLE. Le mot i du flux est une forme LINÉAIRE des L mots
// d'état : r_i = Σ_j α_ij r_j (mod 32), α donné par la récurrence elle-même. On
// parcourt (r_0, …, r_{L−1}) en boucles emboîtées avec des sommes courantes : au
// niveau le plus profond, les VL formes d'un vecteur avancent d'UNE addition
// vectorielle par état, et le test (ALLOW >> ((r >> 1) & 15)) & 1 se fait lane
// par lane (décalage variable). Étage 1 : les seize premiers mots contraints
// (0,773^16 = 1,6 % passent) ; étage 2, sur les seuls passants : les seize
// suivants (2,6·10⁻⁴ passent) ; puis la vérification SCALAIRE complète du
// candidat sur les n tirages, par le même code que l'autotest compare à
// l'énumération purement scalaire.
//
// CONVENTION : « l'état » est le registre (r_0, …, r_{L−1}) DONT r_0 EST LE
// PREMIER MOT du tirage 0. Il est imprimé compacté : r_j aux bits 5j..5j+4.
//
//   cc -O3 -march=native -pthread -o lfg_low_sieve tools/lfg_low_sieve.c
//
//   lfg_low_sieve <K> <L> <mode> <param> <masques.u16> <n>
//         crible 2^(5L) ; mode 0 = FY modulo, 1 = shuffle (param = pas en mots),
//         2 = rejet (param = mots perdus admis entre deux tirages)
//   lfg_low_sieve --selftest [L]      (L = 5 par défaut : 2^25 états)
//
// SWEEP_THREADS fixe le nombre de fils (4 par défaut).

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdatomic.h>
#include <pthread.h>
#include <immintrin.h>

#define POOL 80
#define DRAWN 20
#define MAXN 4096
#define SIGMAX 48                       // mots par tirage au plus, mode rejet
#define GARDE 64
#define MAXL 7
#define MAXFORMES 64
#define MAXALPHA 2048                   // mots dont la forme linéaire est calculée
#define TAMPON (MAXN * 80 + 64)         // mots bas d'un candidat, par fil

#ifndef VL
#if defined(__AVX512F__)
#define VL 16
#elif defined(__AVX2__)
#define VL 8
#else
#define VL 4
#endif
#endif
typedef uint32_t vu __attribute__((vector_size(VL * 4)));
#define MAXV (MAXFORMES / VL + 1)

static int K, L, MODE, STRIDE, PERDUS, N;
static int NBFILS = 4, SILENCIEUX = 0;
static uint16_t ALLOW[MAXN];            // bit q : le résidu q mod 16 est permis au tirage d
static uint8_t ALPHA[MAXALPHA][MAXL];   // r_i = Σ_j ALPHA[i][j] r_j mod 32
static int NV1, NV2;                    // vecteurs des deux étages
static vu COL1[MAXV][MAXL], COL2[MAXV][MAXL], AL1[MAXV], AL2[MAXV], UN;

static inline int tous(vu ok) {         // toutes les lanes valent 1 ?
#if defined(__AVX512F__) && VL == 16
    return _mm512_test_epi32_mask((__m512i)ok, (__m512i)ok) == 0xFFFF;
#elif defined(__AVX2__) && VL == 8
    return _mm256_movemask_ps(_mm256_castsi256_ps((__m256i)(ok << 31))) == 0xFF;
#else
    for (int i = 0; i < VL; i++) if (!ok[i]) return 0;
    return 1;
#endif
}

// ---------------------------------------------------------------------------
// Les formes linéaires et les deux étages du pré-crible.
// ---------------------------------------------------------------------------
static void prepare(void) {
    for (int i = 0; i < MAXALPHA; i++)
        for (int j = 0; j < L; j++)
            ALPHA[i][j] = (i < L) ? (uint8_t)(i == j)
                                  : (uint8_t)((ALPHA[i - K][j] + ALPHA[i - L][j]) & 31);
    for (int i = 0; i < VL; i++) UN[i] = 1;
    int mots[MAXFORMES], tir[MAXFORMES], nf = 0;
    if (MODE == 2) {
        for (int i = 0; i < DRAWN; i++) { mots[nf] = i; tir[nf] = 0; nf++; }
    } else {
        for (int d = 0; d < 16 && d < N; d++) {
            mots[nf] = d * STRIDE; tir[nf] = d; nf++;
            mots[nf] = d * STRIDE + 16; tir[nf] = d; nf++;
        }
    }
    int nf1 = nf < 16 ? nf : 16, nf2 = nf - nf1;
    NV1 = (nf1 + VL - 1) / VL;
    NV2 = (nf2 + VL - 1) / VL;
    for (int v = 0; v < MAXV; v++) {
        for (int j = 0; j < MAXL; j++) COL1[v][j] = COL2[v][j] = (vu){0};
        AL1[v] = AL2[v] = (vu){0} + 0xFFFFu;             // lane de remplissage : passe
    }
    for (int f = 0; f < nf; f++) {
        int e = f < nf1 ? 0 : 1, g = e ? f - nf1 : f, v = g / VL, lane = g % VL;
        vu *col = e ? COL2[v] : COL1[v];
        for (int j = 0; j < L; j++) col[j][lane] = ALPHA[mots[f]][j];
        (e ? AL2 : AL1)[v][lane] = ALLOW[tir[f]];
    }
}

// ---------------------------------------------------------------------------
// La vérification scalaire complète d'un candidat (les mots bas, paresseux).
// ---------------------------------------------------------------------------
typedef struct {
    long trouves; uint64_t somme; uint64_t garde[GARDE];
    uint8_t *buf; int rempli;
} ctx;

static inline int mot(ctx *c, int i) {
    while (c->rempli <= i) {
        int p = c->rempli;
        c->buf[p] = (uint8_t)((c->buf[p - K] + c->buf[p - L]) & 31);
        c->rempli = p + 1;
    }
    return c->buf[i];
}

// Mode 2, définition : le mot `pos` est le premier du tirage d. Rend 1 s'il existe
// des longueurs σ_d, σ_{d+1}, … dans [20, SIGMAX] et des pertes ≤ PERDUS telles que
// tous les mots de chaque tirage passent son masque. (Branchement explicite ;
// référence de l'autotest.)
static int rejet_survit(ctx *c, int pos, int d) {
    if (d == N) return 1;
    const uint16_t al = ALLOW[d];
    for (int w = 0; ; w++, pos++) {
        if (w >= DRAWN) {
            for (int p = 0; p <= PERDUS; p++)
                if (rejet_survit(c, pos + p, d + 1)) return 1;
            if (w == SIGMAX) return 0;
        }
        if (!((al >> ((mot(c, pos) >> 1) & 15)) & 1)) return 0;
    }
}

// Mode 2, par INTERVALLES (lemme des courses) : les départs possibles du tirage d
// forment un intervalle [a, b]. Une course de R ≥ 20 mots permis depuis s couvre
// les départs s..min(b, s + R − 20), et l'union de leurs départs suivants est
// encore un intervalle, [s + 20, min(s + R, b' + SIGMAX) + PERDUS]. Même valeur
// que rejet_survit, sans le facteur de branchement (P + 1)^n.
static int rejet_int(ctx *c, int d, int a, int b) {
    if (d == N) return 1;
    const uint16_t al = ALLOW[d];
    for (int s = a; s <= b; ) {
        int R = 0, cap = b - s + SIGMAX + 1;
        while (R < cap && ((al >> ((mot(c, s + R) >> 1) & 15)) & 1)) R++;
        if (R >= DRAWN) {
            int bp = (b < s + R - DRAWN) ? b : s + R - DRAWN;
            int hi = (s + R < bp + SIGMAX) ? s + R : bp + SIGMAX;
            if (rejet_int(c, d + 1, s + DRAWN, hi + PERDUS)) return 1;
        }
        s += R + 1;
    }
    return 0;
}

static int REFERENCE = 0;               // autotest : la définition plutôt que les intervalles

static int verifie(ctx *c, uint64_t packed) {
    for (int j = 0; j < L; j++) c->buf[j] = (uint8_t)((packed >> (5 * j)) & 31);
    c->rempli = L;
    if (MODE == 2) return REFERENCE ? rejet_survit(c, 0, 0) : rejet_int(c, 0, 0, 0);
    for (int d = 0; d < N; d++) {
        int i = d * STRIDE;
        if (!((ALLOW[d] >> ((mot(c, i) >> 1) & 15)) & 1)) return 0;
        if (!((ALLOW[d] >> ((mot(c, i + 16) >> 1) & 15)) & 1)) return 0;
    }
    return 1;
}

static void survivant(ctx *c, uint64_t packed) {
    if (c->trouves < GARDE) c->garde[c->trouves] = packed;
    c->trouves++;
    c->somme += packed * 0x9E3779B97F4A7C15ULL;        // empreinte de l'ensemble
    if (!SILENCIEUX) { printf("BAS %llu\n", (unsigned long long)packed); fflush(stdout); }
}

// ---------------------------------------------------------------------------
// L'énumération : boucles emboîtées, sommes courantes, l'étage 1 au niveau le
// plus profond, l'étage 2 puis la vérification scalaire sur les passants.
// ---------------------------------------------------------------------------
static inline int etage2(const vu *a2, int r) {
    for (int v = 0; v < NV2; v++) {
        vu s = a2[v] + COL2[v][L - 1] * (uint32_t)r;
        if (!tous((AL2[v] >> ((s >> 1) & 15)) & 1)) return 0;
    }
    return 1;
}

static void enumere(ctx *c, int depth, const vu *a1, const vu *a2, uint64_t packed) {
    if (depth == L - 1) {
        const int sh = 5 * (L - 1);
        if (NV1 == 1) {
            vu s = a1[0];
            const vu col = COL1[0][L - 1], al = AL1[0];
            for (int r = 0; r < 32; r++) {
                if (tous((al >> ((s >> 1) & 15)) & 1) && etage2(a2, r)) {
                    uint64_t p = packed | ((uint64_t)r << sh);
                    if (verifie(c, p)) survivant(c, p);
                }
                s += col;
            }
        } else if (NV1 == 2) {
            vu s0 = a1[0], s1 = a1[1];
            const vu c0 = COL1[0][L - 1], c1 = COL1[1][L - 1], al0 = AL1[0], al1 = AL1[1];
            for (int r = 0; r < 32; r++) {
                vu ok = ((al0 >> ((s0 >> 1) & 15)) & 1) & ((al1 >> ((s1 >> 1) & 15)) & 1);
                if (tous(ok) && etage2(a2, r)) {
                    uint64_t p = packed | ((uint64_t)r << sh);
                    if (verifie(c, p)) survivant(c, p);
                }
                s0 += c0; s1 += c1;
            }
        } else {
            vu s[MAXV];
            for (int v = 0; v < NV1; v++) s[v] = a1[v];
            for (int r = 0; r < 32; r++) {
                vu ok = UN;
                for (int v = 0; v < NV1; v++) ok &= (AL1[v] >> ((s[v] >> 1) & 15)) & 1;
                if (tous(ok) && etage2(a2, r)) {
                    uint64_t p = packed | ((uint64_t)r << sh);
                    if (verifie(c, p)) survivant(c, p);
                }
                for (int v = 0; v < NV1; v++) s[v] += COL1[v][L - 1];
            }
        }
        return;
    }
    vu b1[MAXV], b2[MAXV];
    for (int v = 0; v < NV1; v++) b1[v] = a1[v];
    for (int v = 0; v < NV2; v++) b2[v] = a2[v];
    for (int r = 0; r < 32; r++) {
        enumere(c, depth + 1, b1, b2, packed | ((uint64_t)r << (5 * depth)));
        for (int v = 0; v < NV1; v++) b1[v] += COL1[v][depth];
        for (int v = 0; v < NV2; v++) b2[v] += COL2[v][depth];
    }
}

static atomic_int PROCHAINE;
static int NTACHES, PROF0;              // tâches = les 32^PROF0 valeurs des PROF0 premiers mots

static void *fil(void *v) {
    ctx *c = (ctx *)v;
    for (;;) {
        int t = atomic_fetch_add(&PROCHAINE, 1);
        if (t >= NTACHES) break;
        vu a1[MAXV], a2[MAXV];
        for (int q = 0; q < MAXV; q++) a1[q] = a2[q] = (vu){0};
        uint64_t packed = 0;
        for (int j = 0; j < PROF0; j++) {
            uint32_t r = (uint32_t)(t >> (5 * (PROF0 - 1 - j))) & 31;
            for (int q = 0; q < NV1; q++) a1[q] += COL1[q][j] * r;
            for (int q = 0; q < NV2; q++) a2[q] += COL2[q][j] * r;
            packed |= (uint64_t)r << (5 * j);
        }
        enumere(c, PROF0, a1, a2, packed);
    }
    return NULL;
}

// `garde` (GARDE cases au plus) reçoit les premiers survivants ; `somme` une empreinte.
static long crible(uint64_t *garde, uint64_t *somme) {
    pthread_t th[64];
    static ctx tk[64];
    PROF0 = (L - 1 < 2) ? L - 1 : 2;
    NTACHES = 1 << (5 * PROF0);
    atomic_store(&PROCHAINE, 0);
    for (int i = 0; i < NBFILS; i++) {
        tk[i].trouves = 0; tk[i].somme = 0;
        if (!tk[i].buf) tk[i].buf = malloc(TAMPON);
        pthread_create(&th[i], NULL, fil, &tk[i]);
    }
    long tot = 0; uint64_t s = 0;
    for (int i = 0; i < NBFILS; i++) {
        pthread_join(th[i], NULL);
        for (long k = 0; k < tk[i].trouves && k < GARDE; k++)
            if (garde && tot + k < GARDE) garde[tot + k] = tk[i].garde[k];
        tot += tk[i].trouves; s += tk[i].somme;
    }
    if (somme) *somme = s;
    return tot;
}

// L'énumération purement scalaire (référence de l'autotest).
static long crible_scalaire(uint64_t *somme) {
    static ctx c; if (!c.buf) c.buf = malloc(TAMPON);
    c.trouves = 0; c.somme = 0;
    for (uint64_t p = 0; p < (1ULL << (5 * L)); p++)
        if (verifie(&c, p)) survivant(&c, p);
    if (somme) *somme = c.somme;
    return c.trouves;
}

// ---------------------------------------------------------------------------
// AUTOTEST. Un état 32 bits planté, le flux 32 bits qu'il engendre, la fenêtre
// de N = 60 tirages lue sous chaque mode.
//   1. mode 0, pas 20 : un seul bas, le vrai (à 25 bits, 60 tirages en filtrent 44)
//   2. mode 0, pas 22 : idem
//   3. mode 1, pas 79 : idem
//   4. mode 2, pertes 0..2 plantées entre les tirages, PERDUS = 4 : le vrai est
//      là ; tout survivant est un DÉCALÉ f^k(vrai) mod 32, |k| ≤ 48 ; les
//      1 + (σ_0 − 20) décalés structurels (registres des mots 0..σ_0 − 20 du
//      tirage 0) sont tous présents
//   5. fenêtre aléatoire, mode 0  : zéro
//   6. fenêtre aléatoire, mode 2  : zéro
//   7. l'énumération vectorielle et l'énumération scalaire donnent le même
//      ensemble de survivants (L = 4, trois tirages, comptés et empreints) ; en
//      mode 2 la fenêtre a trente numéros par tirage (courses longues) et le
//      scalaire applique la DÉFINITION (rejet_survit) contre les INTERVALLES
//      (rejet_int) du vectoriel
// ---------------------------------------------------------------------------
static uint64_t RNG = 0x9E3779B97F4A7C15ULL;
static uint32_t alea(void) { RNG ^= RNG << 13; RNG ^= RNG >> 7; RNG ^= RNG << 17; return (uint32_t)(RNG >> 16); }

#define MAXFLUX (MAXL + 80 * 64 + 256)
static uint32_t FLUX[MAXFLUX];

// un tirage complet depuis le mot `deb` sous `mode` ; rend le nombre de mots consommés
static int tirage(int deb, int mode, int *out) {
    int arr[POOL];
    for (int i = 0; i < POOL; i++) arr[i] = i + 1;
    if (mode == 0) {
        for (int k = 0; k < DRAWN; k++) {
            int j = k + (int)((FLUX[deb + k] >> 1) % (uint32_t)(POOL - k));
            int t = arr[k]; arr[k] = arr[j]; arr[j] = t;
            out[k] = arr[k];
        }
        return DRAWN;
    }
    if (mode == 1) {
        for (int i = POOL - 1; i >= 1; i--) {
            int j = (int)((FLUX[deb + (POOL - 1 - i)] >> 1) % (uint32_t)(i + 1));
            int t = arr[i]; arr[i] = arr[j]; arr[j] = t;
        }
        for (int k = 0; k < DRAWN; k++) out[k] = arr[POOL - DRAWN + k];
        return POOL - 1;
    }
    int pris[POOL + 1]; memset(pris, 0, sizeof pris);
    int n = 0, p = deb;
    while (n < DRAWN) {
        int v = (int)((FLUX[p++] >> 1) % (uint32_t)POOL) + 1;
        if (!pris[v]) { pris[v] = 1; out[n++] = v; }
    }
    return p - deb;
}

static void masque_aleatoire(int n, int nb) {      // nb numéros au hasard par tirage
    for (int d = 0; d < n; d++) {
        int pris[POOL]; memset(pris, 0, sizeof pris);
        ALLOW[d] = 0;
        for (int k = 0; k < nb; k++) {
            int v; do { v = (int)(alea() % POOL); } while (pris[v]);
            pris[v] = 1; ALLOW[d] |= (uint16_t)(1u << (v & 15));
        }
    }
}

static const int KDEF[MAXL + 1] = {0, 0, 1, 1, 1, 2, 1, 3};    // un trinôme primitif par degré

static int selftest(int l) {
    if (l < 2 || l > MAXL) { fprintf(stderr, "L entre 2 et %d\n", MAXL); return 0; }
    int ok = 0, tot = 0;
    const int modes[4] = {0, 0, 1, 2}, pas[4] = {20, 22, 79, 1};
    for (int g = 0; g < 4; g++) {
        L = l; K = KDEF[l]; MODE = modes[g]; STRIDE = pas[g]; PERDUS = 4; N = 60;
        uint32_t etat[MAXL];
        for (int j = 0; j < L; j++) etat[j] = alea();
        for (int j = 0; j < L; j++) FLUX[j] = etat[j];
        for (int i = L; i < MAXFLUX; i++) FLUX[i] = FLUX[i - K] + FLUX[i - L];
        int pos = 0, sigma0 = DRAWN;
        for (int d = 0; d < N; d++) {
            int out[DRAWN];
            int used = tirage(pos, MODE, out);
            if (d == 0) sigma0 = used;
            ALLOW[d] = 0;
            for (int k = 0; k < DRAWN; k++) ALLOW[d] |= (uint16_t)(1u << ((out[k] - 1) & 15));
            pos += (MODE == 2) ? used + d % 3 : STRIDE;
        }
        prepare();
        uint64_t vrai = 0;
        for (int j = 0; j < L; j++) vrai |= (uint64_t)(FLUX[j] & 31) << (5 * j);
        uint64_t garde[GARDE] = {0};
        long n = crible(garde, NULL);
        int present = 0;
        for (long k = 0; k < n && k < GARDE; k++) present |= (garde[k] == vrai);
        int bon;
        if (MODE == 2) {
            // les décalés f^k(vrai) mod 32, |k| ≤ 48 : la suite basse, en arrière par
            // r_{i−L} = r_i − r_{i−K}
            enum { OFF = 48 + MAXL };
            uint8_t bas[2 * OFF + 64];
            for (int i = 0; i < OFF + 64; i++) bas[OFF + i] = (uint8_t)(FLUX[i] & 31);
            for (int m = 1; m <= OFF; m++)
                bas[OFF - m] = (uint8_t)((bas[OFF + L - m] - bas[OFF + L - m - K]) & 31);
            uint64_t reg[97];
            for (int k = -48; k <= 48; k++) {
                uint64_t p = 0;
                for (int j = 0; j < L; j++) p |= (uint64_t)bas[OFF + k + j] << (5 * j);
                reg[48 + k] = p;
            }
            int etrangers = 0, structurels = 0, kmin = 99, kmax = -99;
            for (long q = 0; q < n && q < GARDE; q++) {
                int k = -99;
                for (int i = 0; i < 97; i++) if (reg[i] == garde[q]) { k = i - 48; break; }
                if (k == -99) etrangers++;
                else { if (k < kmin) kmin = k; if (k > kmax) kmax = k; }
            }
            for (int k = 0; k <= sigma0 - DRAWN; k++) {
                int la = 0;
                for (long q = 0; q < n && q < GARDE; q++) la |= (garde[q] == reg[48 + k]);
                structurels += la;
            }
            bon = (present && n <= GARDE && etrangers == 0 && structurels == sigma0 - DRAWN + 1);
            tot++; ok += bon;
            printf("  K=%d L=%d mode 2 (rejet) perdus %d : crible 2^%d -> %ld bas, tous des decales "
                   "f^k(vrai), k de %d a %d, %d etranger ; les %d structurels (mots 0..%d, "
                   "sigma_0 = %d) %s  %s\n", K, L, PERDUS, 5 * L, n, kmin, kmax, etrangers,
                   sigma0 - DRAWN + 1, sigma0 - DRAWN, sigma0,
                   structurels == sigma0 - DRAWN + 1 ? "presents" : "INCOMPLETS", bon ? "OK" : "ECHEC");
            continue;
        }
        bon = (n == 1 && present);
        tot++; ok += bon;
        printf("  K=%d L=%d mode %d deux mots pas %d : crible 2^%d -> %ld bas (vrai %s)  %s\n",
               K, L, MODE, STRIDE, 5 * L, n, present ? "present" : "ABSENT", bon ? "OK" : "ECHEC");
    }
    // témoins négatifs : des masques aléatoires (vingt numéros au hasard par tirage)
    N = 60; masque_aleatoire(N, DRAWN);
    for (int g = 0; g < 2; g++) {
        MODE = g ? 2 : 0; STRIDE = g ? 1 : 20; PERDUS = 4; prepare();
        long n = crible(NULL, NULL);
        tot++; ok += (n == 0);
        printf("  K=%d L=%d fenetre ALEATOIRE mode %d : crible 2^%d -> %ld bas (%s)\n", K, L, MODE,
               5 * L, n, n == 0 ? "OK" : "ECHEC");
    }
    // vectoriel contre scalaire : même ensemble de survivants
    L = 4; K = KDEF[4]; SILENCIEUX = 1;
    int coherent = 1;
    for (int g = 0; g < 2; g++) {
        MODE = g ? 2 : 0; STRIDE = g ? 1 : 20; PERDUS = 4; N = 3;
        masque_aleatoire(N, g ? 30 : DRAWN); prepare();     // 30 numéros : courses longues
        uint64_t sv = 0, ss = 0;
        long nv = crible(NULL, &sv);
        REFERENCE = 1;
        long ns = crible_scalaire(&ss);
        REFERENCE = 0;
        int meme = (nv == ns && sv == ss);
        coherent &= meme;
        printf("  K=%d L=%d mode %d, %d tirages : vectoriel%s %ld survivants, scalaire%s %ld, "
               "empreintes %s\n", K, L, MODE, N, g ? " (intervalles)" : "", nv,
               g ? " (branchement)" : "", ns, meme ? "egales" : "DIFFERENTES");
    }
    SILENCIEUX = 0;
    tot++; ok += coherent;
    printf("autotest : %d/%d\n", ok, tot);
    return ok == tot;
}

// ---------------------------------------------------------------------------
int main(int argc, char **argv) {
    if (getenv("SWEEP_THREADS")) NBFILS = atoi(getenv("SWEEP_THREADS"));
    if (NBFILS < 1 || NBFILS > 64) NBFILS = 4;
    if (argc >= 2 && !strcmp(argv[1], "--selftest"))
        return selftest(argc >= 3 ? atoi(argv[2]) : 5) ? 0 : 1;
    if (argc < 7) {
        fprintf(stderr, "usage: %s <K> <L> <mode> <param> <masques.u16> <n>\n", argv[0]);
        fprintf(stderr, "       %s --selftest [L]\n", argv[0]);
        return 2;
    }
    K = atoi(argv[1]); L = atoi(argv[2]); MODE = atoi(argv[3]);
    int param = atoi(argv[4]);
    if (L < 2 || L > MAXL || K < 1 || K >= L) { fprintf(stderr, "K ou L hors bornes\n"); return 2; }
    if (MODE < 0 || MODE > 2) { fprintf(stderr, "mode 0, 1 ou 2\n"); return 2; }
    if (MODE == 2) { STRIDE = 1; PERDUS = param; } else { STRIDE = param; PERDUS = 0; }
    if (MODE == 2 ? (PERDUS < 0 || PERDUS > 16) : (STRIDE < 17 || STRIDE > 80)) {
        fprintf(stderr, "param hors bornes\n"); return 2;
    }
    FILE *f = fopen(argv[5], "rb");
    if (!f) { perror("masques"); return 2; }
    N = atoi(argv[6]);
    if (N > MAXN) N = MAXN;
    if ((int)fread(ALLOW, 2, N, f) != N) { fprintf(stderr, "masques courts\n"); return 2; }
    fclose(f);
    prepare();
    long n = crible(NULL, NULL);
    printf("K=%d L=%d mode=%d %s=%d m=%d candidats=%llu survivants=%ld lanes=%d\n",
           K, L, MODE, MODE == 2 ? "perdus" : "stride", MODE == 2 ? PERDUS : STRIDE, 5 * L,
           (unsigned long long)(1ULL << (5 * L)), n, VL);
    return 0;
}
