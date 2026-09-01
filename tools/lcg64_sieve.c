// lcg64_sieve — le crible des bits bas (§149) étendu aux LCG de 64 bits, aux
// deux mots sûrs d'un tirage, et au tirage par rejet des doublons.
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
// tirage. Filtre ρ = 0,773 par mot contraint (un résidu mod 16 est vide avec
// probabilité C(75,20)/C(80,20) = 0,227).
//
// LES DEUX MOTS SÛRS (lemme des mots 0 et 16). Sous Fisher-Yates partiel
// (mode 0) et sous Collections.shuffle lu par ses vingt dernières cases
// (mode 1), la valeur j_k + 1 est GARANTIE dans l'ensemble pour k = 0 (le
// tableau est l'identité) et pour k = 16 : le modulo y vaut 80 − 16 = 64, donc
// j_16 ≡ x_16 (mod 16), et le numéro j_16 + 1 est tiré — au mot 16 si la case
// j_16 est intacte, au premier mot k' < 16 qui l'a visée sinon (il l'a déposé
// en case k', tirée). Les deux mots sont les seuls (16 | k et 16 | 80 − k,
// k ≤ 19). Le crible contraint donc DEUX mots par tirage : 0,74 bit par tirage
// au lieu de 0,37, et un seul survivant structurel — le registre du mot 0.
// Contraint sur le seul mot 0, il en a deux : le registre du mot 16 est un
// FANTÔME qui satisfait le lemme à chaque tirage (c'est le « 2 candidats bas »
// des témoins du §149). L'autotest exhibe le fantôme à un mot et son absence à
// deux.
//
// LE REJET DES DOUBLONS (mode 2) est le mode le PLUS criblable, et non le moins :
// v = x mod 80 + 1 est tiré si nouveau, rejeté si déjà tiré — dans les deux cas
// v est dans l'ensemble, donc CHAQUE mot du tirage est contraint. Le nombre de
// mots σ par tirage (20 + doublons, ≈ 22,9 en moyenne) est inconnu du crible :
// on branche sur σ ≥ 20 et sur jusqu'à P mots perdus entre deux tirages. Un
// faux candidat survit à un tirage avec espérance Σ_{σ≥20} ρ^σ·(P+1) =
// 0,025·(P+1) — 5,3 bits par tirage à P = 0, 3,0 à P = 4 — contre 0,74 pour les
// modes à pas constant.
//
// LES DÉCALÉS (lemme des décalés, mode 2). Ce mode a lui aussi des survivants
// structurels, et ce sont des REGISTRES DU VRAI FLUX : le registre du mot k du
// tirage 0, pour 0 ≤ k ≤ σ_0 − 20, voit encore σ_0 − k ≥ 20 mots dans
// l'ensemble et peut finir son « tirage » exactement où finit le vrai — il est
// réaligné pour toujours. S'y ajoutent, avec probabilité géométrique ρ^p, les
// registres des p mots qui PRÉCÈDENT le tirage 0 et les décalés qui se
// réalignent un tirage plus tard. On en attend une dizaine ; aucun n'est un
// état étranger, et l'autotest vérifie que chacun est f^k(vrai) mod 2^m pour
// un |k| ≤ 48, et que les 1 + (σ_0 − 20) structurels sont tous là.
//
// D'un tirage au suivant l'état avance de STRIDE mots ; comme la récurrence est
// affine, ce saut est UNE multiplication-addition (a^STRIDE, c·Σ a^i), pas
// STRIDE : ~4 opérations par candidat. Le mode 2 avance mot par mot, mais un
// faux candidat meurt en 4,4 mots.
//
// Les W − m bits hauts d'un survivant se RELÈVENT ensuite par énumération
// (`--lift`) : l'état complet doit reproduire l'ENSEMBLE des vingt numéros du
// premier tirage sous le mode, filtre 1/C(80,20).
//
// CONVENTION : « l'état » est la valeur du registre DONT LA SORTIE EST LE
// PREMIER MOT du tirage visé (le registre après l'appel qui a produit ce mot).
//
//   cc -O3 -march=native -pthread -o lcg64_sieve tools/lcg64_sieve.c
//
//   lcg64_sieve <a> <c> <W> <r> <outmask> <mode> <param> <masques.u16> <n>
//         crible 2^(r+4) ; mode 0 = FY modulo, 1 = shuffle (param = pas en
//         mots), 2 = rejet (param = mots perdus admis entre deux tirages)
//   lcg64_sieve --lift <a> <c> <W> <r> <outmask> <mode> <bas> <n1..n20>
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
#define SIGMAX 48                       // mots par tirage au plus, mode rejet
#define MAXMOTS 400                     // borne du rejet au relèvement

static uint64_t A, C;                   // la récurrence
static int W = 64;                      // largeur du registre
static uint64_t MASQW;                  // 2^W − 1
static int R, M;                        // décalage de sortie, m = r + 4
static uint64_t OUTMASK = ~0ULL;        // masque de sortie
static int NBFILS = 4;
static uint16_t ALLOW[MAXN];            // bit q : le résidu q mod 16 est permis
static int N;                           // tirages de la fenêtre
static int MODE;                        // 0 FY modulo, 1 shuffle, 2 rejet
static int STRIDE;                      // mots par tirage (modes 0, 1)
static int PERDUS;                      // mots perdus admis entre tirages (mode 2)
static int MOTS = 2;                    // mots contraints par tirage (modes 0, 1)
static uint64_t AS, CS;                 // le saut de STRIDE mots, affine
static uint64_t A16, C16;               // le saut de 16 mots

static inline uint64_t largeur(int w) { return (w >= 64) ? ~0ULL : ((1ULL << w) - 1); }

static void saut(int k, uint64_t *ak, uint64_t *ck) {
    // s -> a^k s + c (a^{k-1} + ... + 1), composé pas à pas
    uint64_t as = 1, cs = 0;
    for (int i = 0; i < k; i++) { as = (A * as) & MASQW; cs = (A * cs + C) & MASQW; }
    *ak = as; *ck = cs;
}

static void prepare(void) {
    MASQW = largeur(W);
    M = R + 4;
    saut(STRIDE, &AS, &CS);
    saut(16, &A16, &C16);
}

static inline uint64_t sortie(uint64_t s) { return ((s & MASQW) >> R) & OUTMASK; }

#define GARDE 64
typedef struct { uint64_t lo, hi; long trouves; uint64_t garde[GARDE]; } tache;

// l'inverse de a modulo 2^64 (a impair) : Newton, s <- s(2 − a s)
static uint64_t inverse_a(void) {
    uint64_t s = A;
    for (int i = 0; i < 6; i++) s *= 2 - A * s;
    return s;
}

// ---------------------------------------------------------------------------
// Mode 2 : s est le registre au premier mot du tirage d. Rend 1 s'il existe
// des longueurs σ_d, σ_{d+1}, … ≥ 20 et des pertes ≤ PERDUS telles que tous
// les mots de chaque tirage passent son masque.
// ---------------------------------------------------------------------------
static int rejet_survit(uint64_t s, int d, uint64_t masque) {
    if (d == N) return 1;
    const uint16_t al = ALLOW[d];
    for (int w = 0; ; w++) {
        if (w >= DRAWN) {                                  // le tirage peut finir ici
            uint64_t t = s;
            for (int p = 0; p <= PERDUS; p++) {
                if (rejet_survit(t, d + 1, masque)) return 1;
                t = (A * t + C) & masque;
            }
            if (w == SIGMAX) return 0;
        }
        if (!((al >> ((s >> R) & 15)) & 1)) return 0;      // ce mot est un doublon ou tiré : dans l'ensemble
        s = (A * s + C) & masque;
    }
}

// ---------------------------------------------------------------------------
// Le crible : 2^m candidats bas (le registre au premier mot du tirage 0),
// chacun sauté et testé tirage après tirage.
// ---------------------------------------------------------------------------
static void *fil_crible(void *v) {
    tache *t = (tache *)v;
    const uint64_t masque = largeur(M);
    const uint64_t as = AS, cs = CS, a16 = A16, c16 = C16;
    const int r = R, n = N, deux = (MOTS == 2);
    t->trouves = 0;
    for (uint64_t s0 = t->lo; s0 < t->hi; s0++) {
        int vivant;
        if (MODE == 2) {
            vivant = rejet_survit(s0, 0, masque);
        } else {
            uint64_t s = s0;
            int d;
            for (d = 0; d < n; d++) {
                if (!((ALLOW[d] >> ((s >> r) & 15)) & 1)) break;
                if (deux) {
                    uint64_t s16 = (a16 * s + c16) & masque;   // le mot 16 du tirage d
                    if (!((ALLOW[d] >> ((s16 >> r) & 15)) & 1)) break;
                }
                s = (as * s + cs) & masque;                    // le mot 0 du tirage d+1
            }
            vivant = (d == n);
        }
        if (vivant) {
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
    int nf = (span == 0) ? 1 : NBFILS;
    if (nf == 1) span = total;
    for (int i = 0; i < nf; i++) {
        tk[i].lo = i * span;
        tk[i].hi = (i + 1 == nf) ? total : (i + 1) * span;
        pthread_create(&th[i], NULL, fil_crible, &tk[i]);
    }
    long tot = 0;
    for (int i = 0; i < nf; i++) {
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
// dernières cases, mode 2 = rejet des doublons. `fin` reçoit le registre du
// DERNIER mot consommé.
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
    } else if (mode == 1) {
        for (int i = POOL - 1; i >= 1; i--) {
            if (i != POOL - 1) s = (A * s + C) & MASQW;
            int j = (int)(sortie(s) % (uint64_t)(i + 1));
            int t = arr[i]; arr[i] = arr[j]; arr[j] = t;
        }
        for (int k = 0; k < DRAWN; k++) out[k] = arr[POOL - DRAWN + k];
    } else {
        int pris[POOL + 1]; memset(pris, 0, sizeof pris);
        int n = 0, premier = 1;
        while (n < DRAWN) {
            if (!premier) s = (A * s + C) & MASQW;
            premier = 0;
            int v = (int)(sortie(s) % (uint64_t)POOL) + 1;
            if (pris[v]) continue;
            pris[v] = 1; out[n++] = v;
        }
    }
    if (fin) *fin = s;
}

// Rejet précoce pour le relèvement : rend 1 si l'état produit l'ensemble visé.
static inline int essaie(uint64_t s, int mode) {
    int arr[POOL];
    if (mode == 2) {
        int pris[POOL + 1]; memset(pris, 0, sizeof pris);
        int n = 0;
        for (int mots = 0; mots < MAXMOTS; mots++) {
            if (mots) s = (A * s + C) & MASQW;
            int v = (int)(sortie(s) % (uint64_t)POOL) + 1;
            if (!CIBLE[v]) return 0;
            if (pris[v]) continue;
            pris[v] = 1;
            if (++n == DRAWN) return 1;
        }
        return 0;
    }
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
    int nf = (span == 0) ? 1 : NBFILS;
    if (nf == 1) span = total;
    for (int i = 0; i < nf; i++) {
        tk[i].bas = bas; tk[i].mode = mode;
        tk[i].lo = i * span;
        tk[i].hi = (i + 1 == nf) ? total : (i + 1) * span;
        pthread_create(&th[i], NULL, fil_lift, &tk[i]);
    }
    long tot = 0;
    for (int i = 0; i < nf; i++) {
        pthread_join(th[i], NULL);
        if (tk[i].trouves && premier && !tot) *premier = tk[i].premier;
        tot += tk[i].trouves;
    }
    return tot;
}

// ---------------------------------------------------------------------------
// AUTOTEST : la récurrence de musl (a = 6364136223846793005, c = 1), un état
// planté sous chaque mode, la fenêtre qu'il produit.
//   1. mode 0, UN mot contraint   : deux bas, le vrai et le fantôme du mot 16 ;
//                                   le vrai se relève en UN état, le fantôme en zéro
//   2. mode 0, deux mots          : un seul bas, le vrai, relevé exact
//   3. mode 1, deux mots          : idem
//   4. mode 2 (rejet), pertes 0..2 plantées, PERDUS = 2 : le vrai est là et se
//      relève exact ; tout survivant est un DÉCALÉ f^k(vrai), |k| ≤ 48, et les
//      1 + (σ_0 − 20) décalés structurels sont tous présents
//   5. fenêtre aléatoire, mode 0  : zéro
//   6. fenêtre aléatoire, mode 2  : zéro
// W = 40, r = 13 (crible 2^17, relèvement 2^23) exerce exactement le même code
// que W = 64, r = 33 (crible 2^37, relèvement 2^27) — qui est l'autre option.
// ---------------------------------------------------------------------------
static int selftest(int w) {
    A = 6364136223846793005ULL; C = 1ULL;
    W = w; R = (w == 64) ? 33 : 13; OUTMASK = ~0ULL;
    int ok = 0, tot = 0;
    const uint64_t graines[4] = {0x0123456789ABCDEFULL, 0x0123456789ABCDEFULL,
                                 0xFEDCBA9876543210ULL, 0x5A5A3C3CF0F00F0FULL};
    const int modes[4] = {0, 0, 1, 2}, mots[4] = {1, 2, 2, 2};
    for (int g = 0; g < 4; g++) {
        MODE = modes[g]; MOTS = mots[g];
        STRIDE = (MODE == 1) ? 79 : 21;                  // 20 mots + 1 perdu ; 79 mots
        PERDUS = 2;
        N = 150;
        prepare();
        uint64_t vrai = graines[g] & MASQW;
        uint64_t s = vrai;
        int prem[DRAWN], sigma0 = DRAWN;
        for (int d = 0; d < N; d++) {
            int out[DRAWN];
            uint64_t fin;
            tirage(s, MODE, out, &fin);
            if (d == 0) memcpy(prem, out, sizeof prem);
            if (d == 0 && MODE == 2) {                   // σ_0 : fin = f^(σ_0 − 1)(vrai)
                uint64_t t = s; sigma0 = 1;
                while (t != fin) { t = (A * t + C) & MASQW; sigma0++; }
            }
            ALLOW[d] = 0;
            for (int k = 0; k < DRAWN; k++) ALLOW[d] |= (uint16_t)(1u << ((out[k] - 1) & 15));
            if (MODE == 2) {
                // le mot suivant, puis d mod 3 mots perdus
                s = (A * fin + C) & MASQW;
                for (int p = 0; p < d % 3; p++) s = (A * s + C) & MASQW;
            } else {
                s = (AS * s + CS) & MASQW;               // STRIDE mots depuis le premier
            }
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
        long nl = present ? lift(bas_vrai, MODE, &got) : 0;
        long nf = fantome ? lift(bas_f16, MODE, NULL) : 0;
        int exact = (nl == 1 && got == vrai);
        int bon;
        if (MODE == 2) {
            // chaque survivant est un décalé f^k(vrai) mod 2^m, |k| ≤ 48, et les
            // registres des mots 0..σ_0 − 20 sont tous là
            uint64_t inv = inverse_a(), bm = largeur(M);
            uint64_t reg[97];
            uint64_t t = vrai;
            for (int k = 0; k <= 48; k++) { reg[48 + k] = t & bm; t = (A * t + C) & MASQW; }
            t = vrai;
            for (int k = 1; k <= 48; k++) { t = (inv * (t - C)) & MASQW; reg[48 - k] = t & bm; }
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
            bon = (present && exact && n <= GARDE && etrangers == 0 &&
                   structurels == sigma0 - DRAWN + 1);
            tot++; ok += bon;
            printf("  W=%d etat 0x%016llX mode 2 (rejet) perdus %d : crible 2^%d -> %ld bas, tous "
                   "des decales f^k(vrai), k de %d a %d, %d etranger ; les %d structurels "
                   "(mots 0..%d, sigma_0 = %d) %s ; releve 2^%d : vrai -> %ld etat %s  %s\n",
                   W, (unsigned long long)vrai, PERDUS, M, n, kmin, kmax, etrangers,
                   sigma0 - DRAWN + 1, sigma0 - DRAWN, sigma0,
                   structurels == sigma0 - DRAWN + 1 ? "presents" : "INCOMPLETS",
                   W - M, nl, exact ? "exact" : "FAUX", bon ? "OK" : "ECHEC");
            continue;
        }
        bon = (MOTS == 1) ? (n == 2 && present && fantome && exact && nf == 0)
                          : (n == 1 && present && exact);
        tot++; ok += bon;
        if (MOTS == 1)
            printf("  W=%d etat 0x%016llX mode %d un mot pas %d : crible 2^%d -> %ld bas (vrai %s, "
                   "fantome du mot 16 %s), releve 2^%d : vrai -> %ld etat %s, fantome -> %ld  %s\n",
                   W, (unsigned long long)vrai, MODE, STRIDE, M, n,
                   present ? "present" : "ABSENT", fantome ? "present" : "ABSENT",
                   W - M, nl, exact ? "exact" : "FAUX", nf, bon ? "OK" : "ECHEC");
        else
            printf("  W=%d etat 0x%016llX mode %d deux mots %s %d : crible 2^%d -> %ld bas (vrai %s, "
                   "fantome %s), releve 2^%d : %ld etat %s  %s\n",
                   W, (unsigned long long)vrai, MODE, MODE == 2 ? "perdus" : "pas",
                   MODE == 2 ? PERDUS : STRIDE, M, n,
                   present ? "present" : "ABSENT", fantome ? "PRESENT" : "absent",
                   W - M, nl, exact ? "exact" : "FAUX", bon ? "OK" : "ECHEC");
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
    for (int g = 0; g < 2; g++) {
        MODE = g ? 2 : 0; MOTS = 2; STRIDE = 21; PERDUS = 2; prepare();
        long n = crible(NULL);
        tot++; ok += (n == 0);
        printf("  W=%d fenetre ALEATOIRE mode %d : crible 2^%d -> %ld bas (%s)\n", W, MODE, M, n,
               n == 0 ? "OK" : "ECHEC");
    }
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
        if (mode < 0 || mode > 2) { fprintf(stderr, "mode 0, 1 ou 2\n"); return 2; }
        STRIDE = 1; prepare();
        memset(CIBLE, 0, sizeof CIBLE);
        for (int i = 0; i < DRAWN; i++) CIBLE[atoi(argv[9 + i])] = 1;
        uint64_t premier = 0;
        long n = lift(bas, mode, &premier);
        printf("bas=%llu releves=%ld\n", (unsigned long long)bas, n);
        return 0;
    }
    if (argc < 10) {
        fprintf(stderr, "usage: %s <a> <c> <W> <r> <outmask> <mode> <param> <masques.u16> <n>\n", argv[0]);
        fprintf(stderr, "       %s --lift <a> <c> <W> <r> <outmask> <mode> <bas> <n1..n20>\n", argv[0]);
        fprintf(stderr, "       %s --selftest [W]\n", argv[0]);
        return 2;
    }
    A = strtoull(argv[1], 0, 0); C = strtoull(argv[2], 0, 0);
    W = atoi(argv[3]); R = atoi(argv[4]);
    OUTMASK = strtoull(argv[5], 0, 0); if (!OUTMASK) OUTMASK = ~0ULL;
    MODE = atoi(argv[6]);
    int param = atoi(argv[7]);
    if (W < 8 || W > 64 || R < 0 || R + 4 > W) { fprintf(stderr, "W ou r hors bornes\n"); return 2; }
    if (MODE < 0 || MODE > 2) { fprintf(stderr, "mode 0, 1 ou 2\n"); return 2; }
    if (MODE == 2) { STRIDE = 1; PERDUS = param; } else { STRIDE = param; PERDUS = 0; }
    if (STRIDE < 1 || PERDUS < 0 || PERDUS > 16) { fprintf(stderr, "param hors bornes\n"); return 2; }
    MOTS = 2;
    prepare();
    FILE *f = fopen(argv[8], "rb");
    if (!f) { perror("masques"); return 2; }
    N = atoi(argv[9]);
    if (N > MAXN) N = MAXN;
    if ((int)fread(ALLOW, 2, N, f) != N) { fprintf(stderr, "masques courts\n"); return 2; }
    fclose(f);
    long n = crible(NULL);
    printf("a=%llu c=%llu W=%d r=%d mode=%d %s=%d m=%d candidats=%llu survivants=%ld\n",
           (unsigned long long)A, (unsigned long long)C, W, R, MODE,
           MODE == 2 ? "perdus" : "stride", MODE == 2 ? PERDUS : STRIDE, M,
           (unsigned long long)(1ULL << M), n);
    return 0;
}
