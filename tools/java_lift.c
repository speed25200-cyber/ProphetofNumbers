// java_lift — relever les 27 bits hauts d'un état `java.util.Random`.
//
// Le crible du §149 travaille modulo 2^21, ce que permet le fait que
// 80 = 16 x 5 — donc (v−1) mod 16 vaut les bits 17 à 20 de l'état — et que le
// LCG de module 2^48 soit AUTONOME modulo 2^21. Il rend donc `s mod 2^21`.
//
// Il reste à trouver les 27 bits hauts, et il n'y a pas de raccourci : les bits
// au-dessus de 21 n'apparaissent dans aucune congruence exploitable, puisque
// `j = (s>>>17) mod (80−k)` mêle tout le mot. On les ÉNUMÈRE donc, et 2^27 =
// 134 217 728 essais à vingt pas chacun tiennent en quelques secondes.
//
// Chaque candidat doit reproduire l'ENSEMBLE des vingt numéros du tirage visé —
// filtre 1/C(80,20) = 2,8e-19, donc l'espérance de faux positifs sur 2^27 vaut
// 3,8e-11.
//
//   cc -O3 -march=native -pthread -o java_lift tools/java_lift.c
//
//   java_lift <bas> <stride> <n1..n20>      relève un candidat bas
//   java_lift --selftest

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <pthread.h>

#define POOL 80
#define DRAWN 20
#define A 0x5DEECE66DULL
#define C 0xBULL
#define M48 ((1ULL << 48) - 1)

static int CIBLE[POOL + 1];        // CIBLE[v] = 1 si v est dans l'ensemble visé
static int NBFILS = 4;

// Rend -1 si l'état produit l'ensemble visé, sinon la profondeur du rejet.
static inline int essaie(uint64_t s) {
    int arr[POOL];
    for (int i = 0; i < POOL; i++) arr[i] = i + 1;
    for (int k = 0; k < DRAWN; k++) {
        s = (A * s + C) & M48;
        int j = k + (int)((s >> 17) % (uint32_t)(POOL - k));
        int t = arr[k]; arr[k] = arr[j]; arr[j] = t;
        if (!CIBLE[arr[k]]) return k;
    }
    return -1;
}

typedef struct { uint64_t bas; uint32_t lo, hi; long trouves; uint64_t premier; } tache;

static void *fil(void *v) {
    tache *t = (tache *)v;
    t->trouves = 0;
    for (uint64_t h = t->lo; h < (uint64_t)t->hi; h++) {
        uint64_t s = t->bas | (h << 21);
        if (essaie(s) < 0) {
            if (!t->trouves) t->premier = s;
            t->trouves++;
            printf("TROUVE etat=%llu\n", (unsigned long long)s);
            fflush(stdout);
        }
    }
    return NULL;
}

static long releve(uint64_t bas, uint64_t *premier) {
    pthread_t th[64];
    tache tk[64];
    uint32_t span = (1u << 27) / NBFILS;
    for (int i = 0; i < NBFILS; i++) {
        tk[i].bas = bas;
        tk[i].lo = i * span;
        tk[i].hi = (i + 1 == NBFILS) ? (1u << 27) : (i + 1) * span;
        pthread_create(&th[i], NULL, fil, &tk[i]);
    }
    long tot = 0;
    for (int i = 0; i < NBFILS; i++) {
        pthread_join(th[i], NULL);
        if (tk[i].trouves && premier && !tot) *premier = tk[i].premier;
        tot += tk[i].trouves;
    }
    return tot;
}

static void tirage(uint64_t s, int *out) {
    int arr[POOL];
    for (int i = 0; i < POOL; i++) arr[i] = i + 1;
    for (int k = 0; k < DRAWN; k++) {
        s = (A * s + C) & M48;
        int j = k + (int)((s >> 17) % (uint32_t)(POOL - k));
        int t = arr[k]; arr[k] = arr[j]; arr[j] = t;
        out[k] = arr[k];
    }
}

static int selftest(void) {
    int ok = 0, tot = 0;
    uint64_t graines[3] = {0x0123456789ABULL, 0xFEDCBA987654ULL, 0x5A5A5A5A5A5AULL};
    for (int g = 0; g < 3; g++) {
        uint64_t vrai = graines[g] & M48;
        int d[DRAWN];
        tirage(vrai, d);
        memset(CIBLE, 0, sizeof CIBLE);
        for (int i = 0; i < DRAWN; i++) CIBLE[d[i]] = 1;
        uint64_t got = 0;
        long n = releve(vrai & ((1ULL << 21) - 1), &got);
        tot++;
        ok += (n >= 1 && got == vrai);
        printf("  etat 0x%012llX : %ld releve(s), premier 0x%012llX  %s\n",
               (unsigned long long)vrai, n, (unsigned long long)got,
               (n >= 1 && got == vrai) ? "OK" : "ECHEC");
    }
    printf("autotest : %d/%d\n", ok, tot);
    return ok == tot;
}

int main(int argc, char **argv) {
    if (getenv("SWEEP_THREADS")) NBFILS = atoi(getenv("SWEEP_THREADS"));
    if (NBFILS < 1 || NBFILS > 64) NBFILS = 4;
    if (argc >= 2 && !strcmp(argv[1], "--selftest")) return selftest() ? 0 : 1;
    if (argc < 3 + DRAWN) {
        fprintf(stderr, "usage: %s <bas> <stride> <n1..n20>\n", argv[0]);
        fprintf(stderr, "       %s --selftest\n", argv[0]);
        return 2;
    }
    uint64_t bas = strtoull(argv[1], 0, 10);
    memset(CIBLE, 0, sizeof CIBLE);
    for (int i = 0; i < DRAWN; i++) CIBLE[atoi(argv[3 + i])] = 1;
    uint64_t premier = 0;
    long n = releve(bas, &premier);
    printf("bas=%llu releves=%ld\n", (unsigned long long)bas, n);
    return 0;
}
