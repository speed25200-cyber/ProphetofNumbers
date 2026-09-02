/* lfg_crible_classe — le crible de CLASSES pour la lecture par TRONCATURE sous pas variable
 * (THEORIE_ETAT §7.24 ; RAPPORT §172).
 *
 * LE LEMME QUI REND LA CHOSE POSSIBLE.  La classe d'un mot, c(r) = (r * 80) >> 32, n'est
 * pas additive — mais elle l'est A UN BIT PRES :
 *
 *      c(a + b mod 2^32) = c(a) + c(b) + delta   (mod 80),   delta dans {0, 1}
 *
 * (et delta dans {0, -16} pour l'echantillonneur a modulo, ou 2^32 mod 80 = 16).  La suite
 * des classes d'un Fibonacci retarde additif est donc lue par un AUTOMATE NON DETERMINISTE
 * d'etat (Z/80)^L : un bit de branchement par mot.
 *
 * LE LEMME DE LA CLASSE.  Sous le rejet, TOUT mot consomme — accepte ou refuse — a sa classe
 * parmi les vingt valeurs publiees par le tirage qui le contient (un mot accepte publie sa
 * classe ; un mot refuse duplique une classe deja acceptee dans le meme tirage).  C'est deux
 * bits d'elagage par mot, contre un bit de branchement : le front DECROIT.
 *
 * ET L'ALIGNEMENT NE SE BRANCHE PAS.  Le tirage courant se deduit des classes acceptees
 * depuis le debut du bloc : des que vingt classes distinctes ont ete acceptees, le tirage
 * est clos et le suivant commence.  Le pas variable ne coute donc RIEN ici — contrairement
 * aux §7.17-§7.21, ou il coute H(N) = 2,846 bits par tirage.
 *
 * COMPTABILITE.  Mot libre (les L premiers) : +log2(20) = +4,3219 bits.  Mot determine :
 * +1 bit (delta) - 2 bits (classe) = -1 bit.  Le pic du front vaut donc 20^L et le parcours
 * total environ 2,5 x 20^L noeuds.
 *
 * SORTIE.  Zero survivant = la configuration est EXCLUE, exactement (verdict dur, pas un
 * seuil).  Un survivant = un L-uplet de classes a relever (les delta lus sur la solution
 * donnent T demi-espaces sur les parties fractionnaires : CVP resolu par LLL, §7.24 (vii)).
 *
 * LE PLAFOND PAR TIRAGE.  Un chemin degenere — toutes les classes egales, donc des refus a
 * l'infini — ne cloturerait jamais un tirage et survivrait a tort.  On coupe donc tout chemin
 * dont le tirage courant depasse NMAXD mots.  Ce n'est pas une approximation gratuite :
 * P(N > 60) = 1,8e-20, soit 1,3e-15 sur les 70 560 tirages de l'archive.  Le crible reste
 * exact a cette probabilite pres, qui est nommee.
 *
 * usage : lfg_crible_classe K L shift mode f_tirages f_blocs ntir [saut] [nmaxd] [plafond]
 *   mode  : flux (un seul ancrage, au premier tirage) | nuit (un ancrage par bloc)
 *   shift : 0 (x = r) | 1 (x = r >> 1, glibc random())
 *   f_tirages : une ligne par tirage, vingt classes v-1 dans 0..79
 *   f_blocs   : les indices de debut de bloc, un par ligne
 *   ntir      : nombre de tirages qu'un chemin doit CLOTURER pour compter comme survivant
 *   saut      : ne traiter qu'un bloc sur `saut` (mode nuit ; defaut 1)
 *   nmaxd     : plafond de mots par tirage (defaut 60)
 *   plafond   : plafond de noeuds (defaut 2e11)
 *   fixe      : L classes separees par des virgules — on ne parcourt QUE cette branche.
 *               Sert aux temoins : verifier en quelques millisecondes qu'un etat plante
 *               est bien retenu, sans enumerer la famille entiere.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>
#ifdef _OPENMP
#include <omp.h>
#endif

#define POOL 80
#define DRAWN 20
#define NSURV 65536

static int NT, NB;
static int FIXE[64], NFIXE = 0;
static unsigned char *PUB;      /* NT x POOL : 1 si la classe est publiee par le tirage */
static unsigned char *LST;      /* NT x DRAWN : la liste des vingt classes publiees */
static int *DEB;                /* debuts de blocs */

static double horloge(void)
{
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec + 1e-9 * t.tv_nsec;
}

/* ------------------------------------------------------------------ lecture */

static int lire_tirages(const char *f)
{
    FILE *fp = fopen(f, "r");
    if (!fp) { perror(f); exit(1); }
    int cap = 1024, n = 0;
    unsigned char *pub = malloc((size_t)cap * POOL);
    unsigned char *lst = malloc((size_t)cap * DRAWN);
    char ligne[512];
    while (fgets(ligne, sizeof ligne, fp)) {
        if (n == cap) {
            cap *= 2;
            pub = realloc(pub, (size_t)cap * POOL);
            lst = realloc(lst, (size_t)cap * DRAWN);
        }
        memset(pub + (size_t)n * POOL, 0, POOL);
        char *p = ligne;
        int k = 0;
        while (k < DRAWN) {
            while (*p == ' ' || *p == '\t') p++;
            if (*p < '0' || *p > '9') break;
            int v = (int)strtol(p, &p, 10);
            if (v < 0 || v >= POOL) { fprintf(stderr, "classe hors bornes : %d\n", v); exit(1); }
            pub[(size_t)n * POOL + v] = 1;
            lst[(size_t)n * DRAWN + k] = (unsigned char)v;
            k++;
        }
        if (k == 0) continue;
        if (k != DRAWN) { fprintf(stderr, "tirage %d : %d classes\n", n, k); exit(1); }
        n++;
    }
    fclose(fp);
    PUB = pub; LST = lst;
    return n;
}

static int lire_blocs(const char *f, int nt)
{
    FILE *fp = fopen(f, "r");
    if (!fp) { perror(f); exit(1); }
    int cap = 1024, n = 0;
    int *d = malloc((size_t)cap * sizeof *d);
    char ligne[64];
    while (fgets(ligne, sizeof ligne, fp)) {
        if (n == cap) { cap *= 2; d = realloc(d, (size_t)cap * sizeof *d); }
        d[n++] = (int)strtol(ligne, NULL, 10);
    }
    fclose(fp);
    (void)nt;
    DEB = d;
    return n;
}

/* ------------------------------------------------------------------ le crible */

typedef struct {
    int K, L, nmax, ndelta, nmaxd, ntir;
    int delta[3];
    int tfin;                   /* dernier tirage utilisable (exclus) */
    long long plafond;
} Reglage;

typedef struct {
    long long noeuds, coupes;
    int surv;
    unsigned char sol[64];      /* le premier survivant, ses L classes */
    unsigned char (*tous)[64];  /* jusqu'a NSURV survivants, pour les temoins */
    int ntous;
    long long *front;           /* front[i] : noeuds poses a la profondeur i */
} Bilan;

/* DFS iteratif : pile explicite, un cadre par mot pose. */
typedef struct {
    unsigned char cand[3 + DRAWN];  /* candidats restants a cette profondeur */
    signed char ncand, icand;
    int d;                          /* tirage courant AVANT ce mot */
    short wd;                       /* mots deja consommes dans le tirage courant */
    unsigned char nacc;             /* classes acceptees dans le tirage courant */
    uint64_t acc0, acc1;            /* bitmap des classes acceptees (0..63, 64..79) */
} Cadre;

/* prem >= 0 : ne parcourir que la branche dont le premier mot porte la classe LST[t0][prem] */
static void crible_bloc(const Reglage *R, int t0, Bilan *B, int prem)
{
    const int L = R->L, K = R->K, nmax = R->nmax;
    Cadre *pile = malloc((size_t)(nmax + 2) * sizeof *pile);
    unsigned char *hist = malloc((size_t)(nmax + 2));
    int prof = 0;

    /* cadre initial : le premier mot du bloc, tirage t0, rien d'accepte */
    Cadre *c = &pile[0];
    c->d = t0; c->nacc = 0; c->wd = 0; c->acc0 = c->acc1 = 0;
    c->ncand = DRAWN; c->icand = 0;
    if (t0 >= R->tfin) { free(pile); free(hist); return; }
    if (NFIXE) { c->cand[0] = (unsigned char)FIXE[0]; c->ncand = 1; }
    else if (prem >= 0) { c->cand[0] = LST[(size_t)t0 * DRAWN + prem]; c->ncand = 1; }
    else memcpy(c->cand, LST + (size_t)t0 * DRAWN, DRAWN);

    while (prof >= 0) {
        Cadre *f = &pile[prof];
        if (f->icand >= f->ncand) { prof--; continue; }
        int cl = f->cand[(int)f->icand++];
        B->noeuds++;
        if (B->front) B->front[prof]++;
        if (B->noeuds > R->plafond) { B->coupes++; break; }
        hist[prof] = (unsigned char)cl;

        /* etat apres avoir pose ce mot : accepte ou refuse ? */
        int d = f->d, nacc = f->nacc, wd = f->wd + 1;
        uint64_t a0 = f->acc0, a1 = f->acc1;
        int deja = (cl < 64) ? (int)((a0 >> cl) & 1) : (int)((a1 >> (cl - 64)) & 1);
        if (!deja) {
            if (cl < 64) a0 |= (uint64_t)1 << cl; else a1 |= (uint64_t)1 << (cl - 64);
            nacc++;
            if (nacc == DRAWN) { d++; nacc = 0; wd = 0; a0 = a1 = 0; }
        }
        if (wd > R->nmaxd) continue;             /* tirage interminable : chemin mort */

        int prochain = prof + 1;
        if (prochain >= nmax || d >= R->tfin || d - t0 >= R->ntir) {     /* survivant */
            if (B->surv == 0) memcpy(B->sol, hist, (size_t)L);
            if (B->tous && B->ntous < NSURV) { memcpy(B->tous[B->ntous], hist, (size_t)L); B->ntous++; }
            B->surv++;
            continue;
        }

        /* candidats du mot suivant */
        Cadre *g = &pile[prochain];
        g->d = d; g->nacc = (unsigned char)nacc; g->wd = (short)wd; g->acc0 = a0; g->acc1 = a1;
        g->icand = 0;
        const unsigned char *pub = PUB + (size_t)d * POOL;
        if (NFIXE && prochain < L) {
            g->cand[0] = (unsigned char)FIXE[prochain];
            g->ncand = pub[FIXE[prochain]] ? 1 : 0;
        } else if (prochain < L) {
            g->ncand = DRAWN;
            memcpy(g->cand, LST + (size_t)d * DRAWN, DRAWN);
        } else {
            int base = hist[prochain - K] + hist[prochain - L];
            int n = 0;
            for (int e = 0; e < R->ndelta; e++) {
                int v = base + R->delta[e];
                v %= POOL; if (v < 0) v += POOL;
                int vu = 0;
                for (int j = 0; j < n; j++) if (g->cand[j] == v) { vu = 1; break; }
                if (!vu && pub[v]) g->cand[n++] = (unsigned char)v;
            }
            g->ncand = (signed char)n;
        }
        prof = prochain;
    }
    free(pile); free(hist);
}

int main(int argc, char **argv)
{
    if (argc < 8) {
        fprintf(stderr, "usage: %s K L shift mode f_tirages f_blocs nmax [saut] [plafond]\n", argv[0]);
        return 2;
    }
    Reglage R;
    R.K = atoi(argv[1]); R.L = atoi(argv[2]);
    int shift = atoi(argv[3]);
    const char *mode = argv[4];
    NT = lire_tirages(argv[5]);
    NB = lire_blocs(argv[6], NT);
    R.ntir = atoi(argv[7]);
    int saut = (argc > 8) ? atoi(argv[8]) : 1;
    R.nmaxd = (argc > 9) ? atoi(argv[9]) : 60;
    R.plafond = (argc > 10) ? atoll(argv[10]) : 200000000000LL;
    if (argc > 11) {
        char *q = argv[11];
        while (NFIXE < 64 && *q) { FIXE[NFIXE++] = (int)strtol(q, &q, 10); if (*q == ',') q++; }
        if (NFIXE != R.L) { fprintf(stderr, "fixe : %d classes pour L = %d\n", NFIXE, R.L); return 2; }
    }
    R.nmax = R.ntir * R.nmaxd + R.L + 2;
    if (R.K <= 0 || R.L <= R.K || R.L > 60) { fprintf(stderr, "K, L invalides\n"); return 2; }

    /* delta : {0,1} au shift 0 ; {0,1,2} au shift 1 (le bit perdu peut ajouter une unite,
     * avec une probabilite de 80/2^31 — on le garde pour rester EXACT). */
    R.delta[0] = 0; R.delta[1] = 1;
    R.ndelta = 2;
    if (shift == 1) { R.delta[2] = 2; R.ndelta = 3; }

    int nuit = (strcmp(mode, "nuit") == 0);
    int nanc = nuit ? NB : (NFIXE ? 1 : DRAWN);   /* en flux, scission sur la classe du 1er mot */
    double t0 = horloge();

    long long noeuds = 0, coupes = 0;
    int surv = 0, bmax = -1;
    long long pic = 0;
    unsigned char sol[64]; memset(sol, 0, sizeof sol);

#ifdef _OPENMP
#pragma omp parallel for schedule(dynamic, 1) reduction(+:noeuds, coupes, surv)
#endif
    for (int b = 0; b < nanc; b++) {
        if (nuit && (b % saut)) continue;
        Reglage r = R;
        int anc = nuit ? DEB[b] : 0;
        r.tfin = nuit ? ((b + 1 < NB) ? DEB[b + 1] : NT) : NT;
        Bilan B; memset(&B, 0, sizeof B);
        B.front = calloc((size_t)R.nmax + 2, sizeof *B.front);
        B.tous = malloc((size_t)NSURV * 64);
        crible_bloc(&r, anc, &B, nuit ? -1 : b);
        noeuds += B.noeuds; coupes += B.coupes; surv += B.surv;
        long long p = 0;
        for (int i = 0; i <= R.nmax; i++) if (B.front[i] > p) p = B.front[i];
#ifdef _OPENMP
#pragma omp critical
#endif
        {
            if (p > pic) pic = p;
            if (B.surv && bmax < 0) { bmax = b; memcpy(sol, B.sol, (size_t)R.L); }
            for (int u = 0; u < B.ntous; u++) {
                printf("surv %d", nuit ? b : 0);
                for (int i = 0; i < R.L; i++) printf(" %d", B.tous[u][i]);
                printf("\n");
            }
        }
        free(B.front); free(B.tous);
    }

    double sec = horloge() - t0;
    printf("K %d L %d shift %d mode %s ancrages %d tirages %d nmaxd %d fils %d\n", R.K, R.L, shift, mode,
           nuit ? (NB + saut - 1) / saut : 1, R.ntir, R.nmaxd,
#ifdef _OPENMP
           omp_get_max_threads()
#else
           1
#endif
           );
    printf("noeuds %lld pic %lld survivants %d coupes %lld bloc %d sec %.2f\n",
           noeuds, pic, surv, coupes, bmax, sec);
    if (surv) {
        printf("sol");
        for (int i = 0; i < R.L; i++) printf(" %d", sol[i]);
        printf("\n");
    }
    return 0;
}
