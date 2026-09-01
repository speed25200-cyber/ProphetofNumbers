// sweep_archive3 — le balayage d'espace d'état du §150, pour les TROIS AUTRES
// façons de tirer vingt numéros.
//
// POURQUOI CE FICHIER EXISTE
// --------------------------
// `sweep_archive.c` (§150) énumère les 2^32 états d'un xorshift de 32 bits et
// demande à chacun s'il produit EXACTEMENT l'ensemble des vingt numéros d'un
// tirage de l'archive — mais sous UN SEUL échantillonneur, la troncature
// `(x·(80−k)) >> 32` de Lemire, et un seul schéma, Fisher-Yates partiel.
//
// Or le code qui tire vingt numéros s'écrit bien plus souvent avec un MODULO.
// Ce fichier balaie donc, pour le même design et le même tirage :
//
//   MODULO   Fisher-Yates partiel, j = k + x mod (80−k)
//   REJET    v = x mod 80 + 1, tiré jusqu'à vingt DISTINCTS (doublons rejetés)
//   SHUFFLE  `Collections.shuffle` : pour i = 79..1, swap(i, x mod (i+1)) ; le
//            tirage est constitué des VINGT DERNIÈRES cases, qui sont fixées
//            par les vingt premiers mots
//
// Les trois partagent le PREMIER mot : sa valeur est x mod 80 + 1 dans les trois
// cas, et elle doit appartenir à l'ensemble publié. Trois états sur quatre
// meurent donc avant qu'aucun tableau ne soit construit — et c'est ce qui rend
// le balayage des trois modes moins cher que celui d'un seul dans la version
// précédente, qui initialisait ses 80 cases avant de regarder le premier mot.
//
// Ce qu'on ne balaie PAS : les vingt PREMIÈRES cases d'un shuffle complet, qui
// dépendent des 79 mots — 60 fois plus cher, et sans rejet précoce.
//
// AUTOTEST
// --------
// `--selftest` plante un état sous chacun des trois modes, fabrique l'ensemble
// trié qu'il produit, et vérifie que le balayage le retrouve, LUI SEUL, et dans
// SON mode seulement ; puis qu'un ensemble aléatoire ne rend rien.
//
//   cc -O3 -march=native -pthread -o sweep_archive3 tools/sweep_archive3.c

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>
#include <pthread.h>

#define POOL  80
#define DRAWN 20
#define NMODES 3
#define MAXMOTS 400                 // borne du schéma à rejet : au-delà, rejeté

static uint64_t MASQ[2];            // bits j autorisés (numéro j+1 dans l'ensemble)
static int NBFILS = 4;

static inline int permis(int j) {
    return (MASQ[j >> 6] >> (j & 63)) & 1;
}

typedef struct { int a, b, c, orient; } design;

static inline uint32_t pas32(uint32_t x, const design *d) {
    x ^= (d->orient & 1) ? (x << d->a) : (x >> d->a);
    x ^= (d->orient & 2) ? (x << d->b) : (x >> d->b);
    x ^= (d->orient & 4) ? (x << d->c) : (x >> d->c);
    return x;
}

// ---------------------------------------------------------------------------
// Les trois continuations, après un premier mot accepté (j0 = x0 mod 80).
// Chacune rend 1 si l'état produit l'ensemble, 0 sinon.
// ---------------------------------------------------------------------------
static inline int suite_modulo(uint32_t x, const design *d, int j0) {
    int arr[POOL];
    for (int i = 0; i < POOL; i++) arr[i] = i + 1;
    int t = arr[0]; arr[0] = arr[j0]; arr[j0] = t;
    for (int k = 1; k < DRAWN; k++) {
        x = pas32(x, d);
        int j = k + (int)(x % (uint32_t)(POOL - k));
        t = arr[k]; arr[k] = arr[j]; arr[j] = t;
        if (!permis(arr[k] - 1)) return 0;
    }
    return 1;
}

static inline int suite_rejet(uint32_t x, const design *d, int j0) {
    uint64_t pris[2] = {0, 0};
    pris[j0 >> 6] |= 1ULL << (j0 & 63);
    int n = 1;
    for (int mots = 1; mots < MAXMOTS; mots++) {
        x = pas32(x, d);
        int v = (int)(x % (uint32_t)POOL);
        if ((pris[v >> 6] >> (v & 63)) & 1) continue;      // doublon : rejeté
        if (!permis(v)) return 0;
        pris[v >> 6] |= 1ULL << (v & 63);
        if (++n == DRAWN) return 1;
    }
    return 0;
}

static inline int suite_shuffle(uint32_t x, const design *d, int j0) {
    int arr[POOL];
    for (int i = 0; i < POOL; i++) arr[i] = i + 1;
    int t = arr[POOL - 1]; arr[POOL - 1] = arr[j0]; arr[j0] = t;
    for (int k = 1; k < DRAWN; k++) {
        int i = POOL - 1 - k;                                // i = 78 .. 60
        x = pas32(x, d);
        int j = (int)(x % (uint32_t)(i + 1));
        t = arr[i]; arr[i] = arr[j]; arr[j] = t;
        if (!permis(arr[i] - 1)) return 0;
    }
    return 1;
}

typedef struct {
    uint32_t lo, hi;
    const design *d;
    long trouves[NMODES];
    long long pas;
} tache;

static const char *NOMS[NMODES] = {"modulo", "rejet", "shuffle"};

static void *fil(void *v) {
    tache *t = (tache *)v;
    memset(t->trouves, 0, sizeof t->trouves);
    long long p = 0;
    for (uint64_t s = t->lo; s < (uint64_t)t->hi; s++) {
        uint32_t x = pas32((uint32_t)s, t->d);
        int j0 = (int)(x % (uint32_t)POOL);
        p++;
        if (!permis(j0)) continue;                          // 3/4 meurent ici
        int r[NMODES];
        r[0] = suite_modulo(x, t->d, j0);
        r[1] = suite_rejet(x, t->d, j0);
        r[2] = suite_shuffle(x, t->d, j0);
        p += 3 * 4;                                         // ordre de grandeur
        for (int m = 0; m < NMODES; m++)
            if (r[m]) {
                t->trouves[m]++;
                printf("TROUVE mode=%s etat=%u a=%d b=%d c=%d orient=%d\n",
                       NOMS[m], (uint32_t)s, t->d->a, t->d->b, t->d->c,
                       t->d->orient);
                fflush(stdout);
            }
    }
    t->pas = p;
    return NULL;
}

static void balaye_design(const design *d, long *trouves, long long *pas) {
    pthread_t th[64];
    tache tk[64];
    uint64_t span = (1ULL << 32) / NBFILS;
    for (int i = 0; i < NBFILS; i++) {
        tk[i].lo = (uint32_t)(i * span);
        tk[i].hi = (uint32_t)((i + 1 == NBFILS) ? 0xFFFFFFFFu : (i + 1) * span);
        tk[i].d = d;
        pthread_create(&th[i], NULL, fil, &tk[i]);
    }
    for (int m = 0; m < NMODES; m++) trouves[m] = 0;
    long long p = 0;
    for (int i = 0; i < NBFILS; i++) {
        pthread_join(th[i], NULL);
        for (int m = 0; m < NMODES; m++) trouves[m] += tk[i].trouves[m];
        p += tk[i].pas;
    }
    if (pas) *pas = p;
}

// ---------------------------------------------------------------------------
// Fabriquer l'ensemble qu'un état produit sous un mode — pour l'autotest.
// ---------------------------------------------------------------------------
static void produit(uint32_t s, const design *d, int mode, uint64_t *masq) {
    masq[0] = masq[1] = 0;
    uint32_t x = s;
    int arr[POOL];
    for (int i = 0; i < POOL; i++) arr[i] = i + 1;
    if (mode == 0) {
        for (int k = 0; k < DRAWN; k++) {
            x = pas32(x, d);
            int j = k + (int)(x % (uint32_t)(POOL - k));
            int t = arr[k]; arr[k] = arr[j]; arr[j] = t;
            masq[(arr[k] - 1) >> 6] |= 1ULL << ((arr[k] - 1) & 63);
        }
    } else if (mode == 1) {
        int n = 0;
        while (n < DRAWN) {
            x = pas32(x, d);
            int v = (int)(x % (uint32_t)POOL);
            if ((masq[v >> 6] >> (v & 63)) & 1) continue;
            masq[v >> 6] |= 1ULL << (v & 63);
            n++;
        }
    } else {
        for (int i = POOL - 1; i >= 1; i--) {
            x = pas32(x, d);
            int j = (int)(x % (uint32_t)(i + 1));
            int t = arr[i]; arr[i] = arr[j]; arr[j] = t;
        }
        for (int i = POOL - DRAWN; i < POOL; i++)
            masq[(arr[i] - 1) >> 6] |= 1ULL << ((arr[i] - 1) & 63);
    }
}

static int selftest(void) {
    int ok = 0, tot = 0;
    design d = {13, 17, 5, 5};
    uint32_t vrais[NMODES] = {0xC0FFEE42u, 0x1234ABCDu, 0xDEADBEEFu};
    for (int mode = 0; mode < NMODES; mode++) {
        produit(vrais[mode], &d, mode, MASQ);
        long tr[NMODES]; long long pas;
        clock_t t0 = clock();
        balaye_design(&d, tr, &pas);
        double sec = (double)(clock() - t0) / CLOCKS_PER_SEC / NBFILS;
        int bon = 1;
        for (int m = 0; m < NMODES; m++) bon &= (tr[m] == (m == mode ? 1 : 0));
        tot++; ok += bon;
        printf("  mode %-7s etat plante 0x%08X : survivants modulo=%ld rejet=%ld "
               "shuffle=%ld  %s  (%.0f s)\n", NOMS[mode], vrais[mode],
               tr[0], tr[1], tr[2], bon ? "OK" : "ECHEC", sec);
    }
    // témoin négatif : un ensemble aléatoire
    srand(12345);
    MASQ[0] = MASQ[1] = 0;
    int pris[POOL]; memset(pris, 0, sizeof pris);
    for (int k = 0; k < DRAWN; k++) {
        int v; do { v = rand() % POOL; } while (pris[v]);
        pris[v] = 1; MASQ[v >> 6] |= 1ULL << (v & 63);
    }
    long tr[NMODES];
    balaye_design(&d, tr, NULL);
    int bon = (tr[0] == 0 && tr[1] == 0 && tr[2] == 0);
    tot++; ok += bon;
    printf("  ensemble ALEATOIRE : survivants modulo=%ld rejet=%ld shuffle=%ld  %s\n",
           tr[0], tr[1], tr[2], bon ? "OK" : "ECHEC");
    printf("autotest : %d/%d\n", ok, tot);
    return ok == tot;
}

// ---------------------------------------------------------------------------
int main(int argc, char **argv) {
    if (getenv("SWEEP_THREADS")) NBFILS = atoi(getenv("SWEEP_THREADS"));
    if (NBFILS < 1 || NBFILS > 64) NBFILS = 4;
    if (argc >= 2 && !strcmp(argv[1], "--selftest")) return selftest() ? 0 : 1;
    if (argc < 5 + DRAWN) {
        fprintf(stderr, "usage: %s <a> <b> <c> <orient> <n1..n20>\n", argv[0]);
        fprintf(stderr, "       %s --selftest\n", argv[0]);
        return 2;
    }
    design d = {atoi(argv[1]), atoi(argv[2]), atoi(argv[3]), atoi(argv[4])};
    MASQ[0] = MASQ[1] = 0;
    for (int i = 0; i < DRAWN; i++) {
        int v = atoi(argv[5 + i]) - 1;
        if (v < 0 || v >= POOL) { fprintf(stderr, "numero hors 1..80\n"); return 2; }
        MASQ[v >> 6] |= 1ULL << (v & 63);
    }
    clock_t t0 = clock();
    long tr[NMODES]; long long pas;
    balaye_design(&d, tr, &pas);
    printf("designs=1 etats=4294967296 modulo=%ld rejet=%ld shuffle=%ld "
           "pas=%.3e sec=%.1f\n", tr[0], tr[1], tr[2], (double)pas,
           (double)(clock() - t0) / CLOCKS_PER_SEC / NBFILS);
    return 0;
}
