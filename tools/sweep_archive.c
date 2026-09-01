// sweep_archive — l'attaque du confinement, exécutée sur L'ARCHIVE ELLE-MÊME.
//
// POURQUOI CE FICHIER EXISTE
// --------------------------
// Tout ce que le dossier a construit récemment s'applique aux douze tirages
// ORDONNÉS des vidéos. L'archive, elle, n'a que des ensembles TRIÉS — et c'est
// elle qui compte, parce qu'elle fait 70 560 tirages et qu'elle est publique.
//
// CE QUE CE FICHIER FAIT
// ----------------------
// Il énumère L'ESPACE D'ÉTAT ENTIER — les 2^32 états, pas les graines — pour un
// design donné, et demande : cet état produit-il EXACTEMENT l'ensemble des vingt
// numéros d'un tirage de l'archive ?
//
// C'est strictement plus fort que le §120, qui balayait 2^32 GRAINES sous des
// amorçages NOMMÉS : ici l'état est libre, amorcé n'importe comment, y compris
// par une source d'entropie.
//
// POURQUOI UN SEUL TIRAGE SUFFIT, ET CE QUE ÇA SUPPRIME
// -----------------------------------------------------
// Le filtre d'un ensemble complet vaut 1/C(80,20) = 2,8e-19, donc l'espérance de
// faux positifs sur les 2^32 états vaut 1,2e-9. UN tirage suffit. Il n'y a donc
//
//     AUCUNE HYPOTHÈSE DE PAS entre tirages — les vingt et un mots du §137 ne
//     servent plus — ET AUCUNE HYPOTHÈSE D'ALIGNEMENT, puisque énumérer TOUS
//     les états couvre tous les points de départ possibles.
//
// C'est aussi PLUS RAPIDE que le confinement du seul mot 0 : chaque numéro émis
// doit appartenir à l'ensemble, donc on rejette avec probabilité 3/4 dès le
// PREMIER mot, et l'espérance vaut 1/(1−1/4) = 1,33 mot par état — contre 8 pour
// une fenêtre de quarante tirages sur le seul mot 0.
//
// CE QU'IL REND
// -------------
// Pour chaque état survivant, il affiche l'état, et `predit()` donne les vingt
// numéros du tirage suivant. C'est le seul point du dossier où une prédiction
// sortirait de l'archive seule.
//
// AUTOTEST
// --------
// `--selftest` plante un état, fabrique la fenêtre de masques qu'il produirait,
// et vérifie que le balayage RETROUVE cet état et lui seul.
//
//   cc -O3 -march=native -pthread -o sweep_archive tools/sweep_archive.c

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>
#include <pthread.h>

#define POOL  80
#define DRAWN 20
#define MOTS  21
#define MAXF  4096                 // tirages de la fenetre au maximum

static uint64_t MASQ[MAXF][2];     // MASQ[d] : bits j autorises pour le tirage d
static int NF;                     // nombre de tirages de la fenetre
static int NBFILS = 4;

static inline int permis(int d, int j) {
    return (MASQ[d][j >> 6] >> (j & 63)) & 1;
}

// ---------------------------------------------------------------------------
// Le design : forme de Marsaglia sur 32 bits. `orient` porte trois bits.
// ---------------------------------------------------------------------------
typedef struct { int a, b, c, orient; } design;

static inline uint32_t pas32(uint32_t x, const design *d) {
    x ^= (d->orient & 1) ? (x << d->a) : (x >> d->a);
    x ^= (d->orient & 2) ? (x << d->b) : (x >> d->b);
    x ^= (d->orient & 4) ? (x << d->c) : (x >> d->c);
    return x;
}

// ---------------------------------------------------------------------------
// Le noyau : un etat survit s'il satisfait le confinement sur toute la fenetre.
// ---------------------------------------------------------------------------
// L'ENSEMBLE COMPLET D'UN SEUL TIRAGE, verifie numero par numero.
//
// C'est strictement plus fort que le confinement du seul mot 0, et c'est aussi
// PLUS RAPIDE : chaque numero emis doit appartenir a l'ensemble publie, donc on
// rejette avec probabilite 3/4 des le PREMIER mot, et l'esperance de mots
// evalues vaut 1/(1-1/4) = 1,33 par etat contre 8 auparavant.
//
// Et surtout, UN SEUL TIRAGE SUFFIT : le filtre vaut 1/C(80,20) = 2,8e-19, donc
// l'esperance de faux positifs sur les 2^32 etats vaut 1,2e-9. Il n'y a donc
//
//     AUCUNE HYPOTHESE DE PAS ENTRE TIRAGES — les vingt et un mots du §137 ne
//     servent plus — ET AUCUNE HYPOTHESE D'ALIGNEMENT, puisque enumerer TOUS
//     les etats couvre tous les points de depart possibles.
static inline int survit(uint32_t s, const design *d, int t) {
    uint32_t x = s;
    int arr[POOL];
    for (int i = 0; i < POOL; i++) arr[i] = i + 1;
    for (int k = 0; k < DRAWN; k++) {
        x = pas32(x, d);
        int j = k + (int)(((uint64_t)x * (POOL - k)) >> 32);
        int tmp = arr[k]; arr[k] = arr[j]; arr[j] = tmp;
        if (!permis(t, arr[k] - 1)) return k;   // rejete : rend la profondeur
    }
    return -1;                                   // survivant
}

typedef struct {
    uint64_t lo, hi;                             // [lo, hi) ; hi = 2^32 pour le dernier fil
    const design *d;
    int cible;                                   // indice du tirage vise
    long trouves;
    uint32_t premier;
    long long pas;
} tache;

static void *fil(void *v) {
    tache *t = (tache *)v;
    t->trouves = 0;
    long long p = 0;
    for (uint64_t s = t->lo; s < t->hi; s++) {
        int r = survit((uint32_t)s, t->d, t->cible);
        p += (r < 0) ? DRAWN : (r + 1);
        if (r < 0) {
            if (!t->trouves) t->premier = (uint32_t)s;
            t->trouves++;
            printf("TROUVE etat=%u a=%d b=%d c=%d orient=%d\n",
                   (uint32_t)s, t->d->a, t->d->b, t->d->c, t->d->orient);
            fflush(stdout);
        }
    }
    t->pas = p;
    return NULL;
}

static long balaye_design(const design *d, int cible, long long *pas) {
    pthread_t th[64];
    tache tk[64];
    uint64_t span = (1ULL << 32) / NBFILS;
    for (int i = 0; i < NBFILS; i++) {
        tk[i].lo = (uint64_t)i * span;
        tk[i].hi = (i + 1 == NBFILS) ? (1ULL << 32) : (uint64_t)(i + 1) * span;   // l'etat 2^32-1 inclus
        tk[i].d = d; tk[i].cible = cible;
        pthread_create(&th[i], NULL, fil, &tk[i]);
    }
    long tot = 0; long long p = 0;
    for (int i = 0; i < NBFILS; i++) {
        pthread_join(th[i], NULL);
        tot += tk[i].trouves; p += tk[i].pas;
    }
    if (pas) *pas = p;
    return tot;
}

// ---------------------------------------------------------------------------
// La prediction : les vingt numeros du tirage d'indice `idx`, depuis un etat.
// ---------------------------------------------------------------------------
static void predit(uint32_t s, const design *d, int idx, int *out) {
    uint32_t x = s;
    for (int t = 0; t < idx; t++)
        for (int k = 0; k < MOTS; k++) x = pas32(x, d);
    int arr[POOL];
    for (int i = 0; i < POOL; i++) arr[i] = i + 1;
    for (int k = 0; k < DRAWN; k++) {
        x = pas32(x, d);
        int j = k + (int)(((uint64_t)x * (POOL - k)) >> 32);
        int t = arr[k]; arr[k] = arr[j]; arr[j] = t;
        out[k] = arr[k];
    }
}

// ---------------------------------------------------------------------------
static int selftest(void) {
    int ok = 0, tot = 0;
    design d = {13, 17, 5, 5};                   // xorshift32 de Marsaglia
    uint32_t vrai = 0xC0FFEE42u;
    NF = 24;
    // on fabrique la fenetre que cet etat produirait
    uint32_t x = vrai;
    for (int t = 0; t < NF; t++) {
        MASQ[t][0] = MASQ[t][1] = 0;
        int arr[POOL];
        for (int i = 0; i < POOL; i++) arr[i] = i + 1;
        uint32_t y = x;
        for (int k = 0; k < DRAWN; k++) {
            y = pas32(y, &d);
            int j = k + (int)(((uint64_t)y * (POOL - k)) >> 32);
            int tt = arr[k]; arr[k] = arr[j]; arr[j] = tt;
        }
        for (int k = 0; k < DRAWN; k++) {        // le masque = l'ensemble TRIE - 1
            int v = arr[k] - 1;
            MASQ[t][v >> 6] |= 1ULL << (v & 63);
        }
        for (int k = 0; k < MOTS; k++) x = pas32(x, &d);
    }
    long long pas;
    clock_t t0 = clock();
    long n = balaye_design(&d, 0, &pas);
    double sec = (double)(clock() - t0) / CLOCKS_PER_SEC / NBFILS;
    tot++; ok += (n == 1);
    printf("  etat plante 0x%08X retrouve : %ld survivant(s)  %s  (%.0f s, %.2e pas)\n",
           vrai, n, n == 1 ? "OK" : "ECHEC", sec, (double)pas);

    // temoin negatif : le meme balayage sur des masques ALEATOIRES
    srand(12345);
    for (int t = 0; t < NF; t++) {
        MASQ[t][0] = MASQ[t][1] = 0;
        int pris[POOL]; memset(pris, 0, sizeof pris);
        for (int k = 0; k < DRAWN; k++) {
            int v; do { v = rand() % POOL; } while (pris[v]);
            pris[v] = 1; MASQ[t][v >> 6] |= 1ULL << (v & 63);
        }
    }
    long n2 = balaye_design(&d, 0, NULL);
    tot++; ok += (n2 == 0);
    printf("  masques ALEATOIRES : %ld survivant(s)  %s\n",
           n2, n2 == 0 ? "OK" : "ECHEC");
    printf("autotest : %d/%d\n", ok, tot);
    return ok == tot;
}

// ---------------------------------------------------------------------------
int main(int argc, char **argv) {
    if (getenv("SWEEP_THREADS")) NBFILS = atoi(getenv("SWEEP_THREADS"));
    if (NBFILS < 1 || NBFILS > 64) NBFILS = 4;
    if (argc >= 2 && !strcmp(argv[1], "--selftest")) return selftest() ? 0 : 1;
    if (argc < 4) {
        fprintf(stderr, "usage: %s <masques.bin> <nfenetre> <a> <b> <c> <orient>\n",
                argv[0]);
        fprintf(stderr, "       %s <masques.bin> <nfenetre> --tous <amax>\n", argv[0]);
        fprintf(stderr, "       %s --selftest\n", argv[0]);
        return 2;
    }
    FILE *f = fopen(argv[1], "rb");
    if (!f) { perror("masques"); return 2; }
    NF = atoi(argv[2]);
    if (NF > MAXF) NF = MAXF;
    if ((int)fread(MASQ, 16, NF, f) != NF) { fprintf(stderr, "masques courts\n"); return 2; }
    fclose(f);

    clock_t t0 = clock();
    long total = 0, ndes = 0;
    long long pas = 0, ptot = 0;
    if (!strcmp(argv[3], "--tous")) {
        int amax = argc > 4 ? atoi(argv[4]) : 31;
        for (int a = 1; a <= amax; a++)
          for (int b = 1; b <= amax; b++)
            for (int c = 1; c <= amax; c++)
              for (int o = 0; o < 8; o++) {
                  design d = {a, b, c, o};
                  total += balaye_design(&d, 0, &pas);
                  ptot += pas; ndes++;
                  if (ndes % 50 == 0)
                      fprintf(stderr, "  ... %ld designs, %ld survivants, %.0f s\n",
                              ndes, total,
                              (double)(clock() - t0) / CLOCKS_PER_SEC / NBFILS);
              }
    } else {
        design d = {atoi(argv[3]), atoi(argv[4]), atoi(argv[5]), atoi(argv[6])};
        total += balaye_design(&d, 0, &pas);
        ptot += pas; ndes = 1;
    }
    printf("designs=%ld etats=%lld survivants=%ld pas=%.3e sec=%.1f\n",
           ndes, (long long)ndes * 4294967296LL, total, (double)ptot,
           (double)(clock() - t0) / CLOCKS_PER_SEC / NBFILS);
    return 0;
}
