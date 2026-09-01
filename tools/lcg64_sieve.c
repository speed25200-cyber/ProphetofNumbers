// lcg64_sieve — le crible des bits bas (§149) étendu aux LCG de 64 bits.
//
// LE THÉORÈME QU'IL EXÉCUTE (Théorème Q, THEORIE_ETAT.md §7.6)
// -------------------------------------------------------------
// Un LCG de module 2^W, s <- a·s + c mod 2^W, est AUTONOME modulo 2^m pour
// tout m ≤ W : s mod 2^m n'a jamais besoin des bits au-dessus. Si la sortie
// est s >> r et que le tirage lit `sortie mod 80`, alors, comme 80 = 16·5,
//
//     (v − 1) mod 16 = (s >> r) mod 16 = les bits r à r+3 de l'état,
//
// qui ne dépendent que de s mod 2^(r+4). On crible donc 2^(r+4) candidats — et
// non 2^W — contre les résidus mod 16 de l'ensemble publié, tirage après
// tirage, sur le PREMIER mot de chaque tirage : à l'étape 0 de Fisher-Yates la
// valeur émise vaut j_0 + 1, qui est dans l'ensemble ; pour Collections.shuffle
// la première valeur nextInt(80) est placée en case 79 et n'en bouge plus.
// Filtre 0,774 par tirage (un résidu mod 16 est vide avec probabilité
// C(75,20)/C(80,20) = 0,226) ; 150 tirages ramènent 2^37 à 2^37·0,774^150 ≈ 3·10^−6.
//
// D'un tirage au suivant l'état avance de STRIDE mots ; comme la récurrence est
// affine, ce saut est UNE multiplication-addition (a^STRIDE, c·Σ a^i), pas
// STRIDE : le crible coûte ~4 opérations par candidat.
//
// LE FANTÔME DU MOT 16. Le crible a DEUX survivants structurels par état vrai :
// le registre du mot 0 et celui du mot 16. Au mot k le modulo vaut 80 − k, et
// 80 − 16 = 64 est divisible par 16 : j_16 ≡ x_16 (mod 16), et le numéro
// j_16 + 1 est toujours dans l'ensemble — tiré au mot 16 si la case j_16 est
// intacte, tiré au mot k' < 16 sinon (c'est k' qui l'a pris en y déposant
// k' + 1). Le relèvement départage : seul le vrai registre reproduit
// l'ensemble. L'autotest exige exactement ces deux survivants.
//
// Les W − m bits hauts d'un survivant se RELÈVENT ensuite par énumération
// (`--lift`) : l'état complet doit reproduire l'ENSEMBLE des vingt numéros du
// premier tirage, filtre 1/C(80,20).
//
// CONVENTION : « l'état » est la valeur du registre DONT LA SORTIE EST LE
// PREMIER MOT du tirage visé (le registre après l'appel qui a produit ce mot).
//
//   cc -O3 -march=native -pthread -o lcg64_sieve tools/lcg64_sieve.c
//
//   lcg64_sieve <a> <c> <W> <r> <outmask> <stride> <masques.u16> <n>
//                                                       crible 2^(r+4)
//   lcg64_sieve --lift <a> <c> <W> <r> <outmask> <mode> <bas> <n1..n20>
//                                relève (mode 0 = FY modulo, 1 = shuffle)
//   lcg64_sieve --selftest [W]        (W = 40 par défaut : crible 2^17,
//                                      relèvement 2^23 ; W = 64 : le vrai musl)
//
// <outmask> : masque appliqué à la sortie après décalage (0 = aucun ;
// newlib : 0x7fffffff).

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <pthread.h>

#define POOL 80
#define DRAWN 20
#define MAXN 4096

static uint64_t A, C;                   // la récurrence
static int W = 64;                      // largeur du registre
static uint64_t MASQW;                  // 2^W − 1
static int R, M;                        // décalage de sortie, m = r + 4
static uint64_t OUTMASK = ~0ULL;        // masque de sortie
static int NBFILS = 4;
static uint16_t ALLOW[MAXN];            // bit q : le résidu q mod 16 est permis
static int N;                           // tirages de la fenêtre
static int STRIDE;
static uint64_t AS, CS;                 // le saut de STRIDE mots, affine

static inline uint64_t largeur(int w) { return (w >= 64) ? ~0ULL : ((1ULL << w) - 1); }

static void prepare(void) {
    MASQW = largeur(W);
    M = R + 4;
    // s -> a^S s + c (a^{S-1} + ... + 1), composé pas à pas
    AS = 1; CS = 0;
    for (int k = 0; k < STRIDE; k++) { AS = (A * AS) & MASQW; CS = (A * CS + C) & MASQW; }
}

static inline uint64_t sortie(uint64_t s) { return ((s & MASQW) >> R) & OUTMASK; }

#define GARDE 8
typedef struct { uint64_t lo, hi; long trouves; uint64_t garde[GARDE]; } tache;

// ---------------------------------------------------------------------------
// Le crible : 2^m candidats bas (le registre au premier mot du tirage 0),
// chacun sauté et testé tirage après tirage.
// ---------------------------------------------------------------------------
static void *fil_crible(void *v) {
    tache *t = (tache *)v;
    const uint64_t masque = largeur(M);
    const uint64_t as = AS, cs = CS;
    const int r = R, n = N;
    t->trouves = 0;
    for (uint64_t s0 = t->lo; s0 < t->hi; s0++) {
        uint64_t s = s0;
        int d;
        for (d = 0; d < n; d++) {
            if (!((ALLOW[d] >> ((s >> r) & 15)) & 1)) break;
            s = (as * s + cs) & masque;                   // le mot 0 du tirage d+1
        }
        if (d == n) {
            if (t->trouves < GARDE) t->garde[t->trouves] = s0;
            t->trouves++;
            printf("BAS %llu\n", (unsigned long long)s0);
            fflush(stdout);
        }
    }
    return NULL;
}

// `garde` (GARDE cases au plus) reçoit les premiers survivants.
static long crible(uint64_t *garde) {
    pthread_t th[64];
    tache tk[64];
    uint64_t total = 1ULL << M, span = total / NBFILS;
    for (int i = 0; i < NBFILS; i++) {
        tk[i].lo = i * span;
        tk[i].hi = (i + 1 == NBFILS) ? total : (i + 1) * span;
        pthread_create(&th[i], NULL, fil_crible, &tk[i]);
    }
    long tot = 0;
    for (int i = 0; i < NBFILS; i++) {
        pthread_join(th[i], NULL);
        for (long k = 0; k < tk[i].trouves && k < GARDE; k++)
            if (garde && tot + k < GARDE) garde[tot + k] = tk[i].garde[k];
        tot += tk[i].trouves;
    }
    return tot;
}

// ---------------------------------------------------------------------------
// Le tirage complet depuis un état (registre au premier mot) : mode 0 =
// Fisher-Yates partiel par modulo, mode 1 = Collections.shuffle, les vingt
// dernières cases. `fin` reçoit le registre du DERNIER mot consommé.
// ---------------------------------------------------------------------------
static int CIBLE[POOL + 1];

static void tirage(uint64_t s, int mode, int *out, uint64_t *fin) {
    int arr[POOL];
    for (int i = 0; i < POOL; i++) arr[i] = i + 1;
    if (mode == 0) {
        for (int k = 0; k < DRAWN; k++) {
            if (k) s = (A * s + C) & MASQW;
            int j = k + (int)(sortie(s) % (uint64_t)(POOL - k));
            int t = arr[k]; arr[k] = arr[j]; arr[j] = t;
            out[k] = arr[k];
        }
    } else {
        for (int i = POOL - 1; i >= 1; i--) {
            if (i != POOL - 1) s = (A * s + C) & MASQW;
            int j = (int)(sortie(s) % (uint64_t)(i + 1));
            int t = arr[i]; arr[i] = arr[j]; arr[j] = t;
        }
        for (int k = 0; k < DRAWN; k++) out[k] = arr[POOL - DRAWN + k];
    }
    if (fin) *fin = s;
}

// Rejet précoce pour le relèvement : rend 1 si l'état produit l'ensemble visé.
static inline int essaie(uint64_t s, int mode) {
    int arr[POOL];
    for (int i = 0; i < POOL; i++) arr[i] = i + 1;
    if (mode == 0) {
        for (int k = 0; k < DRAWN; k++) {
            if (k) s = (A * s + C) & MASQW;
            int j = k + (int)(sortie(s) % (uint64_t)(POOL - k));
            int t = arr[k]; arr[k] = arr[j]; arr[j] = t;
            if (!CIBLE[arr[k]]) return 0;
        }
        return 1;
    }
    for (int k = 0; k < DRAWN; k++) {
        int i = POOL - 1 - k;
        if (k) s = (A * s + C) & MASQW;
        int j = (int)(sortie(s) % (uint64_t)(i + 1));
        int t = arr[i]; arr[i] = arr[j]; arr[j] = t;
        if (!CIBLE[arr[i]]) return 0;
    }
    return 1;
}

typedef struct { uint64_t bas; uint64_t lo, hi; int mode; long trouves; uint64_t premier; } tlift;

static void *fil_lift(void *v) {
    tlift *t = (tlift *)v;
    t->trouves = 0;
    for (uint64_t h = t->lo; h < t->hi; h++) {
        uint64_t s = t->bas | (h << M);
        if (essaie(s, t->mode)) {
            if (!t->trouves) t->premier = s;
            t->trouves++;
            printf("TROUVE etat=%llu\n", (unsigned long long)s);
            fflush(stdout);
        }
    }
    return NULL;
}

static long lift(uint64_t bas, int mode, uint64_t *premier) {
    pthread_t th[64];
    tlift tk[64];
    uint64_t total = 1ULL << (W - M), span = total / NBFILS;
    for (int i = 0; i < NBFILS; i++) {
        tk[i].bas = bas; tk[i].mode = mode;
        tk[i].lo = i * span;
        tk[i].hi = (i + 1 == NBFILS) ? total : (i + 1) * span;
        pthread_create(&th[i], NULL, fil_lift, &tk[i]);
    }
    long tot = 0;
    for (int i = 0; i < NBFILS; i++) {
        pthread_join(th[i], NULL);
        if (tk[i].trouves && premier && !tot) *premier = tk[i].premier;
        tot += tk[i].trouves;
    }
    return tot;
}

// ---------------------------------------------------------------------------
// AUTOTEST : la récurrence de musl (a = 6364136223846793005, c = 1), un état
// planté sous chaque mode, la fenêtre qu'il produit ; le crible doit rendre
// UN SEUL bas, le vrai, et le relèvement UN SEUL état, le vrai.
// W = 40, r = 13 (crible 2^17, relèvement 2^23) exerce exactement le même code
// que W = 64, r = 33 (crible 2^37, relèvement 2^27) — qui est l'autre option.
// ---------------------------------------------------------------------------
static int selftest(int w) {
    A = 6364136223846793005ULL; C = 1ULL;
    W = w; R = (w == 64) ? 33 : 13; OUTMASK = ~0ULL;
    int ok = 0, tot = 0;
    uint64_t graines[2] = {0x0123456789ABCDEFULL, 0xFEDCBA9876543210ULL};
    for (int g = 0; g < 2; g++) {
        int mode = g;                                    // 0 : FY modulo, 1 : shuffle
        STRIDE = mode ? 79 : 21;                         // 20 mots + 1 perdu ; 79 mots
        N = 150;
        prepare();
        uint64_t vrai = graines[g] & MASQW;
        uint64_t s = vrai;
        int prem[DRAWN];
        for (int d = 0; d < N; d++) {
            int out[DRAWN];
            uint64_t fin;
            tirage(s, mode, out, &fin);
            if (d == 0) memcpy(prem, out, sizeof prem);
            ALLOW[d] = 0;
            for (int k = 0; k < DRAWN; k++) ALLOW[d] |= (uint16_t)(1u << ((out[k] - 1) & 15));
            // avancer jusqu'au premier mot du tirage suivant : STRIDE mots
            // depuis le premier mot de celui-ci
            s = (AS * s + CS) & MASQW;
        }
        uint64_t f16 = vrai;                             // le fantôme du mot 16
        for (int k = 0; k < 16; k++) f16 = (A * f16 + C) & MASQW;
        uint64_t bas_vrai = vrai & largeur(M), bas_f16 = f16 & largeur(M);
        uint64_t garde[GARDE] = {0};
        long n = crible(garde);
        int present = 0, fantome = 0;
        for (long k = 0; k < n && k < GARDE; k++) {
            present |= (garde[k] == bas_vrai);
            fantome |= (garde[k] == bas_f16);
        }
        memset(CIBLE, 0, sizeof CIBLE);
        for (int k = 0; k < DRAWN; k++) CIBLE[prem[k]] = 1;
        uint64_t got = 0;
        long nl = present ? lift(bas_vrai, mode, &got) : 0;
        long nf = fantome ? lift(bas_f16, mode, NULL) : 0;
        int exact = (nl == 1 && got == vrai);
        int bon = (n == 2 && present && fantome && exact && nf == 0);
        tot++; ok += bon;
        printf("  W=%d etat 0x%016llX mode %d pas %d : crible 2^%d -> %ld bas (vrai %s, "
               "fantome du mot 16 %s), releve 2^%d : vrai -> %ld etat %s, fantome -> %ld  %s\n",
               W, (unsigned long long)vrai, mode, STRIDE, M, n,
               present ? "present" : "ABSENT", fantome ? "present" : "ABSENT",
               W - M, nl, exact ? "exact" : "FAUX", nf, bon ? "OK" : "ECHEC");
    }
    // témoin négatif : des masques aléatoires (vingt numéros au hasard par tirage)
    srand(4242);
    for (int d = 0; d < N; d++) {
        int pris[POOL]; memset(pris, 0, sizeof pris);
        ALLOW[d] = 0;
        for (int k = 0; k < DRAWN; k++) {
            int v; do { v = rand() % POOL; } while (pris[v]);
            pris[v] = 1; ALLOW[d] |= (uint16_t)(1u << (v & 15));
        }
    }
    STRIDE = 21; prepare();
    long n = crible(NULL);
    tot++; ok += (n == 0);
    printf("  W=%d fenetre ALEATOIRE : crible 2^%d -> %ld bas (%s)\n", W, M, n,
           n == 0 ? "OK" : "ECHEC");
    printf("autotest : %d/%d\n", ok, tot);
    return ok == tot;
}

// ---------------------------------------------------------------------------
int main(int argc, char **argv) {
    if (getenv("SWEEP_THREADS")) NBFILS = atoi(getenv("SWEEP_THREADS"));
    if (NBFILS < 1 || NBFILS > 64) NBFILS = 4;
    if (argc >= 2 && !strcmp(argv[1], "--selftest"))
        return selftest(argc >= 3 ? atoi(argv[2]) : 40) ? 0 : 1;
    if (argc >= 2 && !strcmp(argv[1], "--lift")) {
        if (argc < 9 + DRAWN) { fprintf(stderr, "usage --lift\n"); return 2; }
        A = strtoull(argv[2], 0, 0); C = strtoull(argv[3], 0, 0);
        W = atoi(argv[4]); R = atoi(argv[5]);
        OUTMASK = strtoull(argv[6], 0, 0); if (!OUTMASK) OUTMASK = ~0ULL;
        int mode = atoi(argv[7]);
        uint64_t bas = strtoull(argv[8], 0, 0);
        STRIDE = 1; prepare();
        memset(CIBLE, 0, sizeof CIBLE);
        for (int i = 0; i < DRAWN; i++) CIBLE[atoi(argv[9 + i])] = 1;
        uint64_t premier = 0;
        long n = lift(bas, mode, &premier);
        printf("bas=%llu releves=%ld\n", (unsigned long long)bas, n);
        return 0;
    }
    if (argc < 9) {
        fprintf(stderr, "usage: %s <a> <c> <W> <r> <outmask> <stride> <masques.u16> <n>\n", argv[0]);
        fprintf(stderr, "       %s --lift <a> <c> <W> <r> <outmask> <mode> <bas> <n1..n20>\n", argv[0]);
        fprintf(stderr, "       %s --selftest [W]\n", argv[0]);
        return 2;
    }
    A = strtoull(argv[1], 0, 0); C = strtoull(argv[2], 0, 0);
    W = atoi(argv[3]); R = atoi(argv[4]);
    OUTMASK = strtoull(argv[5], 0, 0); if (!OUTMASK) OUTMASK = ~0ULL;
    STRIDE = atoi(argv[6]);
    if (W < 8 || W > 64 || R < 0 || R + 4 > W) { fprintf(stderr, "W ou r hors bornes\n"); return 2; }
    prepare();
    FILE *f = fopen(argv[7], "rb");
    if (!f) { perror("masques"); return 2; }
    N = atoi(argv[8]);
    if (N > MAXN) N = MAXN;
    if ((int)fread(ALLOW, 2, N, f) != N) { fprintf(stderr, "masques courts\n"); return 2; }
    fclose(f);
    long n = crible(NULL);
    printf("a=%llu c=%llu W=%d r=%d stride=%d m=%d candidats=%llu survivants=%ld\n",
           (unsigned long long)A, (unsigned long long)C, W, R, STRIDE, M,
           (unsigned long long)(1ULL << M), n);
    return 0;
}
