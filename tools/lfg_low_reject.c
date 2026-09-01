/*
 * lfg_low_reject.c — l'ETAT BAS d'un Fibonacci retardé additif, retrouvé à
 * partir de tirages ORDONNÉS consécutifs sous rejet des doublons.
 *
 *   générateur      r_i = r_{i-k} + r_{i-L}  mod 2^32      (glibc random() : k=3, L=31)
 *   échantillonneur v = (r_i >> 1) % 80 + 1, rejeté s'il est déjà sorti dans le tirage
 *   observation     un tirage ordonné = la suite des mots ACCEPTÉS ; les mots
 *                   perdus (doublons) sont invisibles, leur nombre par tirage ≤ cap
 *
 * Ce que l'on retrouve : les CINQ bits bas de chacun des L mots d'état, soit
 * 5L bits — le quotient mod 32 de la récurrence est autonome (THEORIE_ETAT.md
 * §7.6–7.7). Écrivons r = 2q + b : b est le plan 0 (un LFSR, jamais publié),
 * q mod 16 est le nibble (v−1) mod 16 publié par chaque mot accepté, et
 *
 *     b_i = b_{i-k} ⊕ b_{i-L}
 *     q_i = q_{i-k} + q_{i-L} + c_i  (mod 16),   c_i = b_{i-k} ∧ b_{i-L}
 *
 * Quatre étapes :
 *   1. ALIGNEMENT : recherche en profondeur des positions des mots perdus.
 *      Un mot accepté dont les deux antécédents sont acceptés doit vérifier
 *      (q_i − q_{i-k} − q_{i-L}) mod 16 ∈ {0,1} (élague 7/8) ; un mot perdu
 *      doit être un doublon : son nibble, {s, s+1}, doit être une classe déjà
 *      sortie dans le tirage.
 *   2. PLAN 0 : chaque cohérence livre la retenue c_i = b_{i-k} ∧ b_{i-L}.
 *      c_i = 1 donne deux équations linéaires sur les L bits initiaux du LFSR,
 *      c_i = 0 un NON-ET. Élimination de Gauss sur GF(2), énumération du noyau,
 *      filtre par les NON-ET.
 *   3. NIBBLES : le plan 0 connu, les retenues sont des constantes et
 *      q_i est AFFINE mod 16 dans les L nibbles initiaux — on résout par
 *      relèvement de Hensel, plan par plan, avec la même matrice sur GF(2).
 *   4. VÉRIFICATION : le flux bas régénéré doit rendre tous les nibbles
 *      acceptés, les doublons doivent être des doublons, et — les bits bas
 *      connus — la relation mod 5 (2^32 ≡ 1 mod 5) rend le bit de débordement
 *      w_i = [r_{i-k} + r_{i-L} ≥ 2^32] de chaque mot accepté à antécédents
 *      acceptés : il doit valoir 0 ou 1 (élague 3/5). Puis les SATELLITES :
 *      des tirages ordonnés du même jour, à un écart d'identifiants connu, sont
 *      rejoués à partir de l'état trouvé (le flux bas s'étend dans les deux
 *      sens, la récurrence est inversible) pour chaque décalage possible.
 *
 * usage : lfg_low_reject k L cap threads < entrée
 * entrée : ND                        nombre de tirages du noyau (consécutifs)
 *          20 numéros × ND lignes    dans l'ordre de sortie
 *          NS                        nombre de satellites
 *          g n1 … n20 × NS lignes    g = identifiant du satellite − identifiant
 *                                    du premier tirage du noyau (g < 0 : avant)
 * sortie : lignes ETAT (les L mots bas, du plus ancien au plus récent),
 *          DEBORD (bits de débordement lus), SAT (satellites), FIN (comptes).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <pthread.h>

#define MAXD   8          /* tirages du noyau */
#define MAXS   8          /* satellites */
#define MAXL   63
#define MAXCAP 12
#define MAXP   (MAXD * (20 + MAXCAP) + 4)
#define MAXROW MAXP
#define MAXKER 22         /* 2^22 complétions de noyau au plus, par étape */

static int K, L, CAP, NTH;
static int ND, NS;
static int num[MAXD][20], cls[MAXD][20], clsmask[MAXD][21];   /* classes déjà sorties */
static int satg[MAXS], satnum[MAXS][20], satcls[MAXS][20], satmask[MAXS][21];

/* ------------------------------------------------------------------ comptes */
static pthread_mutex_t mu = PTHREAD_MUTEX_INITIALIZER;
static long long n_align = 0, n_plan0 = 0, n_hensel = 0, n_etats = 0, n_etats_sat = 0;
static long long n_ker_abandon = 0;     /* noyaux de dimension > MAXKER, non énumérés */
static int VERBOSE = 0;

/* --------------------------------------------------------- une recherche */
typedef struct {
    int q[MAXP + MAXL + 1]; /* nibble du mot à la position p, -1 si inconnu (perdu ou non décidé) */
    int o[MAXP];        /* v-1 (0..79) du mot accepté */
    int known[MAXP];    /* 1 : accepté, 0 : perdu */
    int draw[MAXP];     /* tirage du mot */
    int acc[MAXP];      /* nombre de mots acceptés AVANT ce mot dans son tirage */
    int P;              /* longueur du flux du noyau */
    int P1, l1, f1, ac1, lost1;   /* tirage 1 : longueur supposée 20+l1, frontière décidée, compteurs */
} align_t;

/* ----------------------------------------------------- GF(2) : élimination */
/* Système  A x = r  sur GF(2), A : m lignes de L bits (uint64), r : m bits.
 * Rend le rang, une solution particulière x0 (si consistant) et une base du
 * noyau. Renvoie -1 si inconsistant. */
static int gf2_solve(const uint64_t *A, const uint8_t *r, int m, int nvar,
                     uint64_t *x0, uint64_t *ker, int *kdim)
{
    uint64_t rows[MAXROW]; uint8_t rhs[MAXROW];
    int piv[MAXL]; int rank = 0;
    for (int i = 0; i < m; i++) { rows[i] = A[i]; rhs[i] = r[i] & 1; }
    for (int c = 0; c < nvar && rank < m; c++) {
        int pr = -1;
        for (int i = rank; i < m; i++) if ((rows[i] >> c) & 1) { pr = i; break; }
        if (pr < 0) continue;
        uint64_t t = rows[pr]; rows[pr] = rows[rank]; rows[rank] = t;
        uint8_t tb = rhs[pr]; rhs[pr] = rhs[rank]; rhs[rank] = tb;
        for (int i = 0; i < m; i++)
            if (i != rank && ((rows[i] >> c) & 1)) { rows[i] ^= rows[rank]; rhs[i] ^= rhs[rank]; }
        piv[rank++] = c;
    }
    for (int i = rank; i < m; i++) if (rhs[i]) return -1;
    /* colonnes libres */
    uint64_t pivmask = 0;
    for (int i = 0; i < rank; i++) pivmask |= 1ULL << piv[i];
    uint64_t x = 0;
    for (int i = 0; i < rank; i++) if (rhs[i]) x |= 1ULL << piv[i];
    *x0 = x;
    int kd = 0;
    for (int c = 0; c < nvar; c++) if (!((pivmask >> c) & 1)) {
        uint64_t v = 1ULL << c;
        for (int i = 0; i < rank; i++) if ((rows[i] >> c) & 1) v |= 1ULL << piv[i];
        ker[kd++] = v;
    }
    *kdim = kd;
    return rank;
}

/* ------------------------------------------------- étape 4 : vérification */
/* état bas : low[j], j = 0..L-1 = positions -L..-1 (5 bits). Étend le flux bas
 * sur [-L-back, P+fwd). */
static int verifie_et_satellites(const align_t *a, const uint8_t *low, int emit)
{
    int back = 0, fwd = 0;
    for (int s = 0; s < NS; s++) {
        int g = satg[s];
        if (g < 0) { int b = (-g) * (20 + CAP) + 20 + CAP; if (b > back) back = b; }
        else { int f = (g - ND + 1) * (20 + CAP) + 20 + CAP; if (f > fwd) fwd = f; }
    }
    int base = L + back;                  /* indice du tableau pour la position 0 */
    int n = base + a->P + fwd + 1;
    uint8_t *r = malloc(n);
    for (int j = 0; j < L; j++) r[back + j] = low[j];
    for (int p = 0; p < a->P + fwd + 1; p++)
        r[base + p] = (r[base + p - K] + r[base + p - L]) & 31;
    /* en arrière : r_{p-L} = r_p - r_{p-k} */
    for (int p = -L - 1; p >= -L - back; p--)
        r[base + p] = (r[base + p + L] - r[base + p + L - K]) & 31;

    /* mots acceptés : nibble exact ; perdus : doublon ; débordement ∈ {0,1} */
    int ok = 1, nw = 0, w[MAXP], wp[MAXP];
    for (int p = 0; p < a->P && ok; p++) {
        int nib = (r[base + p] >> 1) & 15;
        if (a->q[p] >= 0) {
            if (nib != a->q[p]) ok = 0;
            else if (a->known[p] && p - K >= 0 && p - L >= 0 && a->known[p - K] && a->known[p - L]) {
                /* r mod 5 = (2·o + b) mod 5 ; w = (r_{p-k} + r_{p-L} - r_p) mod 5 */
                int b0 = r[base + p] & 1, bk = r[base + p - K] & 1, bl = r[base + p - L] & 1;
                int m0 = (2 * a->o[p] + b0) % 5, mk = (2 * a->o[p - K] + bk) % 5,
                    ml = (2 * a->o[p - L] + bl) % 5;
                int ww = ((mk + ml - m0) % 5 + 5) % 5;
                if (ww > 1) ok = 0; else { w[nw] = ww; wp[nw] = p; nw++; }
            }
        } else {
            if (!((clsmask[a->draw[p]][a->acc[p]] >> nib) & 1)) ok = 0;
        }
    }
    if (!ok) { free(r); return 0; }

    /* satellites : pour chaque décalage possible, rejouer le tirage */
    int satok[MAXS], satcount[MAXS];
    for (int s = 0; s < NS; s++) {
        int g = satg[s], lo, hi;
        if (g < 0) { lo = -(-g) * (20 + CAP); hi = -(-g) * 20; }
        else { int inter = g - ND; lo = a->P + inter * 20; hi = a->P + inter * (20 + CAP); }
        satcount[s] = 0;
        for (int st = lo; st <= hi; st++) {
            /* marche : accepte si nibble == classe du prochain numéro, perd si doublon */
            /* petite recherche (ambiguïtés possibles) */
            int stack_p[64], stack_a[64], stack_l[64], stack_c[64], sp = 0;
            stack_p[0] = st; stack_a[0] = 0; stack_l[0] = 0; stack_c[0] = 0; sp = 1;
            int found = 0;
            while (sp > 0 && !found) {
                sp--;
                int p = stack_p[sp], ac = stack_a[sp], lo_ = stack_l[sp];
                if (ac == 20) {
                    if (g < 0) {
                        /* la fin du satellite précède (−g−1) tirages inconnus */
                        int inter = -g - 1, e = -p;
                        if (e >= inter * 20 && e <= inter * (20 + CAP)) found = 1;
                    } else found = 1;
                    continue;
                }
                if (p >= a->P + fwd) continue;
                if (base + p < 0) continue;
                int nib = (r[base + p] >> 1) & 15;
                /* accepter */
                if (nib == satcls[s][ac]) {
                    stack_p[sp] = p + 1; stack_a[sp] = ac + 1; stack_l[sp] = lo_; sp++;
                }
                /* perdre */
                if (ac > 0 && lo_ < CAP && ((satmask[s][ac] >> nib) & 1)) {
                    stack_p[sp] = p + 1; stack_a[sp] = ac; stack_l[sp] = lo_ + 1; sp++;
                }
            }
            if (found) satcount[s]++;
        }
        satok[s] = satcount[s] > 0;
    }
    int allsat = 1;
    for (int s = 0; s < NS; s++) allsat &= satok[s];

    if (emit) {
        pthread_mutex_lock(&mu);
        int nok = 0; for (int s = 0; s < NS; s++) nok += satok[s];
        printf("ETAT satellites=%d/%d mots=", nok, NS);
        for (int j = 0; j < L; j++) printf("%d%c", low[j], j + 1 < L ? ',' : '\n');
        printf("DEBORD n=%d", nw);
        for (int i = 0; i < nw; i++) printf(" %d:%d", wp[i], w[i]);
        printf("\n");
        for (int s = 0; s < NS; s++) printf("SAT g=%d decalages=%d\n", satg[s], satcount[s]);
        printf("POSITIONS");
        for (int p = 0; p < a->P; p++) printf(" %d", a->known[p]);
        printf("\n");
        fflush(stdout);
        pthread_mutex_unlock(&mu);
    }
    free(r);
    return allsat ? 2 : 1;
}

/* contexte du relèvement de Hensel : x = x1 + 2 x2 + 4 x3 + 8 x4, chaque
 * plan résolu sur GF(2) avec la même matrice A2 = A mod 2 */
typedef struct {
    const align_t *a; int m; const int *rows; uint8_t (*An)[MAXL]; const uint64_t *A2;
    uint64_t x; int rhs[MAXROW];
} hctx_t;

static void hensel(hctx_t *h, int lv, const int *vals)
{
    int L_ = L;
    if (lv == 4) {
        pthread_mutex_lock(&mu); n_hensel++; pthread_mutex_unlock(&mu);
        uint8_t low[MAXL];
        for (int j = 0; j < L_; j++) low[j] = (uint8_t)(((vals[j] & 15) << 1) | ((h->x >> j) & 1));
        int v = verifie_et_satellites(h->a, low, 1);
        if (v) { pthread_mutex_lock(&mu); n_etats++; if (v == 2) n_etats_sat++; pthread_mutex_unlock(&mu); }
        return;
    }
    uint8_t rr[MAXROW];
    for (int i = 0; i < h->m; i++) {
        int s = 0; for (int j = 0; j < L_; j++) s += h->An[h->rows[i]][j] * vals[j];
        int res = (h->rhs[i] - s) & 15;
        if (res & ((1 << lv) - 1)) return;          /* inconsistant à ce plan */
        rr[i] = (res >> lv) & 1;
    }
    uint64_t y0, kk[MAXL]; int kdd;
    int rk = gf2_solve(h->A2, rr, h->m, L_, &y0, kk, &kdd);
    if (rk < 0) return;
    if (kdd > 12) { pthread_mutex_lock(&mu); n_ker_abandon++; pthread_mutex_unlock(&mu); return; }
    int nv[MAXL];
    for (uint64_t u = 0; u < (1ULL << kdd); u++) {
        uint64_t y = y0; for (int i = 0; i < kdd; i++) if ((u >> i) & 1) y ^= kk[i];
        for (int j = 0; j < L_; j++) nv[j] = vals[j] + (int)(((y >> j) & 1) << lv);
        hensel(h, lv + 1, nv);
    }
}

/* ------------------------------------------------ étapes 2–3 : plan 0, Hensel */
static void resout(const align_t *a)
{
    /* masques du LFSR : bit j ↔ bit initial de la position -L+j */
    uint64_t M[MAXP + MAXL];
    uint64_t *Mp = M + L;                   /* Mp[p] pour p ≥ -L */
    for (int j = 0; j < L; j++) Mp[-L + j] = 1ULL << j;
    for (int p = 0; p < a->P; p++) Mp[p] = Mp[p - K] ^ Mp[p - L];

    /* retenues observées */
    uint64_t eqA[2 * MAXROW]; uint8_t eqR[2 * MAXROW]; int ne = 0;
    uint64_t nandA[MAXROW], nandB[MAXROW]; int nn = 0;
    for (int p = L; p < a->P; p++) {
        if (!(a->q[p] >= 0 && a->q[p - K] >= 0 && a->q[p - L] >= 0)) continue;
        int c = (a->q[p] - a->q[p - K] - a->q[p - L]) & 15;
        if (c == 1) { eqA[ne] = Mp[p - K]; eqR[ne++] = 1; eqA[ne] = Mp[p - L]; eqR[ne++] = 1; }
        else { nandA[nn] = Mp[p - K]; nandB[nn] = Mp[p - L]; nn++; }
    }
    uint64_t x0, ker[MAXL]; int kd;
    int rank = gf2_solve(eqA, eqR, ne, L, &x0, ker, &kd);
    if (rank < 0) return;
    if (kd > MAXKER) { pthread_mutex_lock(&mu); n_ker_abandon++; pthread_mutex_unlock(&mu); return; }

    /* matrice mod 2 des nibbles (indépendante du plan 0) : A2[p] */
    uint8_t Anib[MAXP + MAXL][MAXL];      /* coefficients mod 16 */
    uint8_t (*An)[MAXL] = Anib + L;
    for (int j = 0; j < L; j++) { memset(An[-L + j], 0, L); An[-L + j][j] = 1; }
    for (int p = 0; p < a->P; p++)
        for (int j = 0; j < L; j++) An[p][j] = (An[p - K][j] + An[p - L][j]) & 15;
    uint64_t A2[MAXROW]; int rows[MAXROW]; int m = 0;
    for (int p = 0; p < a->P; p++) if (a->q[p] >= 0) {
        uint64_t v = 0;
        for (int j = 0; j < L; j++) if (An[p][j] & 1) v |= 1ULL << j;
        A2[m] = v; rows[m] = p; m++;
    }

    for (uint64_t t = 0; t < (1ULL << kd); t++) {
        uint64_t x = x0;
        for (int i = 0; i < kd; i++) if ((t >> i) & 1) x ^= ker[i];
        int ok = 1;
        for (int i = 0; i < nn && ok; i++)
            if ((__builtin_popcountll(nandA[i] & x) & 1) && (__builtin_popcountll(nandB[i] & x) & 1)) ok = 0;
        if (!ok) continue;
        pthread_mutex_lock(&mu); n_plan0++; pthread_mutex_unlock(&mu);

        /* plan 0 fixé : retenues, puis constante affine kappa[p] mod 16 */
        int b[MAXP + MAXL]; int *bp = b + L;
        for (int j = 0; j < L; j++) bp[-L + j] = (x >> j) & 1;
        for (int p = 0; p < a->P; p++) bp[p] = bp[p - K] ^ bp[p - L];
        int kap[MAXP + MAXL]; int *kp = kap + L;
        for (int j = 0; j < L; j++) kp[-L + j] = 0;
        for (int p = 0; p < a->P; p++) kp[p] = (kp[p - K] + kp[p - L] + (bp[p - K] & bp[p - L])) & 15;

        /* second membre mod 16 par ligne, puis relèvement de Hensel */
        hctx_t h; h.a = a; h.m = m; h.rows = rows; h.An = An; h.A2 = A2; h.x = x;
        for (int i = 0; i < m; i++) h.rhs[i] = (a->q[rows[i]] - kp[rows[i]]) & 15;
        int vals[MAXL]; memset(vals, 0, sizeof vals);
        hensel(&h, 0, vals);
    }
}

/* ------------------------------------------------- étape 1 : alignement */
/* Recherche PARESSEUSE : le tirage 1 n'est pas énuméré d'avance. On suppose sa
 * longueur 20+l1, on avance dans les tirages 2..ND, et une position du
 * tirage 1 n'est décidée qu'au moment où une cohérence en a besoin — chaque
 * décision est ainsi élaguée aussitôt. Un mot perdu dont les deux antécédents
 * sont connus reçoit son nibble ({s, s+1} ∩ classes sorties) ; un mot accepté
 * dont UN antécédent est un perdu au nibble inconnu le lui assigne (deux
 * candidats) : les cohérences en aval s'appliquent alors aussi aux perdus. */
typedef struct { int p, d, ac, lost, depth; } cont_t;
static int collecting = 0, TASK_DEPTH = 0;
typedef struct {
    int8_t q[MAXP + MAXL + 1]; uint8_t known[MAXP], draw[MAXP], acc[MAXP]; uint8_t o[MAXP];
    int P1, l1, f1, ac1, lost1; cont_t c;
} task_t;
static task_t *tasks; static long long ntasks = 0, captasks = 0, taskcount = 0; static int storetasks = 0;
#define MAXTASKS 120000

static inline int coh(const align_t *a, int j)
{
    if (j < L || a->q[j] < 0 || a->q[j - K] < 0 || a->q[j - L] < 0) return 1;
    return ((a->q[j] - a->q[j - K] - a->q[j - L]) & 15) <= 1;
}
static void search(align_t *a, cont_t c);

static void snapshot(const align_t *a, const cont_t *c)
{
    taskcount++;
    if (!storetasks) return;
    if (ntasks == captasks) { captasks = captasks ? captasks * 2 : 1 << 12; tasks = realloc(tasks, captasks * sizeof(task_t)); }
    task_t *t = &tasks[ntasks++];
    for (int j = 0; j < MAXP + MAXL + 1; j++) t->q[j] = (int8_t)a->q[j];
    for (int j = 0; j < MAXP; j++) { t->known[j] = (uint8_t)a->known[j]; t->draw[j] = (uint8_t)a->draw[j]; t->acc[j] = (uint8_t)a->acc[j]; t->o[j] = (uint8_t)a->o[j]; }
    t->P1 = a->P1; t->l1 = a->l1; t->f1 = a->f1; t->ac1 = a->ac1; t->lost1 = a->lost1; t->c = *c;
}
static void restore(align_t *a, const task_t *t)
{
    for (int j = 0; j < MAXP + MAXL + 1; j++) a->q[j] = t->q[j];
    for (int j = 0; j < MAXP; j++) { a->known[j] = t->known[j]; a->draw[j] = t->draw[j]; a->acc[j] = t->acc[j]; a->o[j] = t->o[j]; }
    a->P1 = t->P1; a->l1 = t->l1; a->f1 = t->f1; a->ac1 = t->ac1; a->lost1 = t->lost1;
}

static void leaf_full(align_t *a)
{
    pthread_mutex_lock(&mu); n_align++;
    if (VERBOSE && n_align <= 5) {
        printf("ALIGN P=%d :", a->P);
        for (int p = 0; p < a->P; p++) printf("%d", a->known[p]);
        printf("\n"); fflush(stdout);
    }
    pthread_mutex_unlock(&mu);
    resout(a);
}

/* décide la position u comme ACCEPTÉE (numéro d'indice ac du tirage d), puis continue */
static void accept_at(align_t *a, int u, int d, int ac, const cont_t *c)
{
    int cl = cls[d][ac];
    a->q[u] = cl; a->known[u] = 1; a->o[u] = num[d][ac] - 1; a->draw[u] = d; a->acc[u] = ac;
    if (coh(a, u)) {
        int v = -1;
        if (u >= L) {
            if (a->q[u - K] < 0 && a->q[u - L] >= 0) v = u - K;
            else if (a->q[u - L] < 0 && a->q[u - K] >= 0) v = u - L;
        }
        if (v >= 0) {   /* un antécédent perdu au nibble inconnu : deux candidats */
            int other = a->q[v == u - K ? u - L : u - K];
            int mk = clsmask[a->draw[v]][a->acc[v]];
            for (int cc = 0; cc < 2; cc++) {
                int val = (cl - other - cc) & 15;
                if (!((mk >> val) & 1)) continue;
                a->q[v] = val;
                if (coh(a, v) && coh(a, v + K) && coh(a, v + L)) search(a, *c);
                a->q[v] = -1;
            }
        } else search(a, *c);
    }
    a->q[u] = -1; a->known[u] = 0;
}
/* décide la position u comme PERDUE (doublon, après ac acceptés du tirage d) */
static void lose_at(align_t *a, int u, int d, int ac, const cont_t *c)
{
    a->known[u] = 0; a->draw[u] = d; a->acc[u] = ac; a->q[u] = -1;
    int mk = clsmask[d][ac];
    if (u >= L && a->q[u - K] >= 0 && a->q[u - L] >= 0) {
        int s = (a->q[u - K] + a->q[u - L]) & 15;
        for (int cc = 0; cc < 2; cc++) {
            int val = (s + cc) & 15;
            if ((mk >> val) & 1) { a->q[u] = val; search(a, *c); a->q[u] = -1; }
        }
    } else search(a, *c);
}
/* décide la prochaine position non décidée du tirage 1, puis reprend la continuation */
static void decide1(align_t *a, const cont_t *c)
{
    int u = a->f1, ac1 = a->ac1, lo1 = a->lost1;
    cont_t n = *c; n.depth = c->depth + 1;
    a->f1 = u + 1;
    if (ac1 < 20 && (ac1 < 19 || lo1 == a->l1)) { a->ac1 = ac1 + 1; accept_at(a, u, 0, ac1, &n); a->ac1 = ac1; }
    if (ac1 > 0 && lo1 < a->l1) { a->lost1 = lo1 + 1; lose_at(a, u, 0, ac1, &n); a->lost1 = lo1; }
    a->f1 = u;
}
static void search(align_t *a, cont_t c)
{
    if (c.ac == 20) { c.d++; c.ac = 0; c.lost = 0; }
    if (c.d == ND) {
        if (a->f1 < a->P1) { decide1(a, &c); return; }
        if (collecting) { snapshot(a, &c); return; }
        a->P = c.p; leaf_full(a); return;
    }
    if (collecting && c.depth >= TASK_DEPTH) { snapshot(a, &c); return; }
    int p = c.p;
    if (p >= L && a->f1 < a->P1) {
        int need = -1;
        if (p - K < a->P1) need = p - K; else if (p - L < a->P1) need = p - L;
        if (need >= a->f1) { decide1(a, &c); return; }
    }
    if (p >= MAXP - 1) return;
    cont_t n = c; n.p = p + 1; n.depth = c.depth + 1;
    { cont_t na = n; na.ac = c.ac + 1; accept_at(a, p, c.d, c.ac, &na); }
    if (c.ac > 0 && c.lost < CAP) { cont_t nl = n; nl.lost = c.lost + 1; lose_at(a, p, c.d, c.ac, &nl); }
}
static void roots(align_t *a)
{
    for (int l1 = 0; l1 <= CAP; l1++) {
        for (int j = 0; j < MAXP + MAXL + 1; j++) a->q[j] = -1;
        memset(a->known, 0, sizeof a->known);
        a->P1 = 20 + l1; a->l1 = l1; a->f1 = 0; a->ac1 = 0; a->lost1 = 0;
        cont_t c = { a->P1, 1, 0, 0, 0 };
        search(a, c);
    }
}
static long long next_task = 0;
static void *worker(void *arg)
{
    (void)arg;
    align_t *a = calloc(1, sizeof(align_t));
    for (;;) {
        pthread_mutex_lock(&mu); long long i = next_task++; pthread_mutex_unlock(&mu);
        if (i >= ntasks) break;
        restore(a, &tasks[i]);
        search(a, tasks[i].c);
    }
    free(a);
    return NULL;
}

int main(int argc, char **argv)
{
    if (argc < 5) { fprintf(stderr, "usage: %s k L cap threads [-v] < entree\n", argv[0]); return 2; }
    K = atoi(argv[1]); L = atoi(argv[2]); CAP = atoi(argv[3]); NTH = atoi(argv[4]);
    if (argc > 5 && !strcmp(argv[5], "-v")) VERBOSE = 1;
    if (L > MAXL || CAP > MAXCAP || K >= L) { fprintf(stderr, "parametres hors bornes\n"); return 2; }
    if (scanf("%d", &ND) != 1 || ND < 1 || ND > MAXD) return 2;
    for (int d = 0; d < ND; d++) {
        clsmask[d][0] = 0;
        for (int i = 0; i < 20; i++) {
            if (scanf("%d", &num[d][i]) != 1) return 2;
            cls[d][i] = (num[d][i] - 1) & 15;
            clsmask[d][i + 1] = clsmask[d][i] | (1 << cls[d][i]);
        }
    }
    if (scanf("%d", &NS) != 1 || NS < 0 || NS > MAXS) return 2;
    for (int s = 0; s < NS; s++) {
        if (scanf("%d", &satg[s]) != 1) return 2;
        satmask[s][0] = 0;
        for (int i = 0; i < 20; i++) {
            if (scanf("%d", &satnum[s][i]) != 1) return 2;
            satcls[s][i] = (satnum[s][i] - 1) & 15;
            satmask[s][i + 1] = satmask[s][i] | (1 << satcls[s][i]);
        }
    }

    /* étape 1a : découpage en tâches — profondeur adaptée pour en avoir ≥ 2000 */
    align_t *a0 = calloc(1, sizeof(align_t));
    collecting = 1;
    int D = 8, Dprev = 8;
    for (;;) {
        TASK_DEPTH = D; storetasks = 0; taskcount = 0; roots(a0);
        if (taskcount > MAXTASKS && D > 8) { D = Dprev; break; }   /* trop fin : reculer */
        if (taskcount >= 2000 || D >= 40) break;
        Dprev = D; D += 4;
    }
    TASK_DEPTH = D; storetasks = 1; ntasks = 0; roots(a0);
    collecting = 0; free(a0);
    printf("TACHES profondeur=%d n=%lld\n", TASK_DEPTH, ntasks); fflush(stdout);

    pthread_t th[64]; if (NTH > 64) NTH = 64; if (NTH < 1) NTH = 1;
    for (int t = 0; t < NTH; t++) pthread_create(&th[t], NULL, worker, NULL);
    for (int t = 0; t < NTH; t++) pthread_join(th[t], NULL);

    printf("FIN alignements=%lld plan0=%lld hensel=%lld etats=%lld etats_satellites=%lld noyaux_abandonnes=%lld\n",
           n_align, n_plan0, n_hensel, n_etats, n_etats_sat, n_ker_abandon);
    return 0;
}
