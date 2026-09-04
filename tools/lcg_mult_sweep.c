/* lcg_mult_sweep — le balayage du MULTIPLICATEUR inconnu, par énumération exacte.
 *
 * CE QU'IL FERME
 * ==============
 * Le §252 nomme la seule fenêtre qui reste dans la famille congruentielle : les modules
 * 2^29 à 2^32 à constantes NON publiées. Il en donne aussi le prix, et c'est pour cela
 * que ce fichier existe.
 *
 * L'INCRÉMENT S'ÉLIMINE
 * =====================
 * Pour un LCG x_{i+1} = a x_i + c mod m, les DIFFÉRENCES y_i = x_{i+1} - x_i vérifient
 *
 *     y_{i+1} = a y_i   (mod m)
 *
 * sans aucune trace de c. Il ne reste donc qu'un inconnu à balayer — a — au lieu du
 * couple (a, c) : 2^31 valeurs impaires sur 2^32, et non 2^64 couples.
 *
 * LE RÉSEAU, ET POURQUOI IL EST CARRÉ ICI
 * =======================================
 * y_i = a^i y_0 mod m, donc le vecteur (y_0, ..., y_{n-1}) vit dans le réseau engendré par
 *
 *     ( 1, a, a^2, ..., a^{n-1} )
 *     ( 0, m, 0,   ..., 0       )
 *     ( 0, 0, m,   ..., 0       )   ... déterminant m^{n-1}
 *
 * C'est une VRAIE base — la première coordonnée de la première ligne vaut 1 — là où le
 * montage habituel du dossier empile n+1 générateurs dépendants en dimension n. Une base
 * carrée, c'est une Gram-Schmidt sans vecteur nul et un énumérateur plus simple.
 *
 * Chaque y_i est connu à m/40 près et non m/80 : une différence cumule DEUX incertitudes.
 * L'espérance de points parasites vaut donc m/40^n, soit 6,5e-4 pour n = 8 et m = 2^32.
 *
 * L'EXACTITUDE, ET OÙ ELLE S'ARRÊTE
 * =================================
 * La réduction et la Gram-Schmidt tournent en `double` (mantisse de 64 bits sur x86)
 * parce que six ans de `Fraction` ne sont pas une option. Deux garde-fous :
 *
 *   - la transformation reste ENTIÈRE, donc la sortie est toujours une base du même
 *     réseau, quelle que soit la qualité des décisions flottantes. Une réduction médiocre
 *     coûte des nœuds, jamais un point manqué ;
 *   - le rayon d'énumération est gonflé de MARGE (1e-9 relatif), soit sept ordres de
 *     grandeur au-dessus de l'erreur d'arrondi d'un `double` sur des quantites de l'ordre
 *     de 2^67 ; et tout point trouvé est ensuite VÉRIFIÉ EN ENTIERS EXACTS.
 *
 * Ce n'est donc pas « exact » au sens du `lab/cvp_exact.py` en Fraction, mais « exact à une
 * marge rigoureusement bornée près », et le mode `croise` compare les deux sur des
 * instances tirées au hasard pour que cette phrase ne soit pas une opinion.
 *
 *   gcc -O3 -march=native -std=c11 -Wall -Wextra -o lcg_mult_sweep lcg_mult_sweep.c -lm
 *   ./lcg_mult_sweep autotest
 *   ./lcg_mult_sweep bench <bits>
 *   ./lcg_mult_sweep sweep <bits> <classes.txt> [<part> <nparts>]
 */

#include <inttypes.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define NMAX 12
#define POOL 80

typedef __int128 i128;

static int N = 8;                 /* dimension du reseau */
static const double MARGE = 1e-9;

/* ------------------------------------------------------------------ Gram-Schmidt */
static void gso(double B[NMAX][NMAX], int n, double mu[NMAX][NMAX],
                double bs[NMAX])
{
    double bst[NMAX][NMAX];
    for (int i = 0; i < n; i++) {
        for (int k = 0; k < n; k++) bst[i][k] = B[i][k];
        for (int j = 0; j < i; j++) {
            double num = 0.0, den = bs[j];
            for (int k = 0; k < n; k++) num += B[i][k] * bst[j][k];
            mu[i][j] = den > 0.0 ? num / den : 0.0;
            for (int k = 0; k < n; k++) bst[i][k] -= mu[i][j] * bst[j][k];
        }
        bs[i] = 0.0;
        for (int k = 0; k < n; k++) bs[i] += bst[i][k] * bst[i][k];
    }
}

/* ------------------------------------------------------------------------- LLL */
/* Les decisions sont flottantes, la base reste ENTIERE : le resultat engendre donc
 * toujours le meme reseau. Une reduction mediocre coute des noeuds, jamais un point.
 *
 * LA REDUCTION DE TAILLE NE CHANGE PAS LA GRAM-SCHMIDT — et une premiere version
 * l'ignorait, recalculant `gso` apres CHAQUE soustraction de ligne : 375 us par
 * multiplicateur au lieu de quelques dizaines. Or retrancher r*b_j a b_k (j < k) laisse
 * b*_0..b*_k inchanges ; seuls les mu[k][.] bougent, et leur mise a jour est EXACTE :
 *
 *     mu[k][i] -= r * mu[j][i]   (i < j)      et      mu[k][j] -= r
 *
 * On ne recalcule donc `gso` qu'apres un echange, qui lui change vraiment la base
 * orthogonale. */
static void lll(i128 Z[NMAX][NMAX], int n)
{
    double B[NMAX][NMAX], mu[NMAX][NMAX], bs[NMAX];
    int tours = 0;
    for (int i = 0; i < n; i++)
        for (int t = 0; t < n; t++) B[i][t] = (double)Z[i][t];
    gso(B, n, mu, bs);
    for (int k = 1; k < n && tours < 4000; ) {
        tours++;
        for (int j = k - 1; j >= 0; j--) {
            double r = floor(mu[k][j] + 0.5);
            if (r != 0.0) {
                i128 ri = (i128)r;
                for (int t = 0; t < n; t++) Z[k][t] -= ri * Z[j][t];
                for (int i = 0; i < j; i++) mu[k][i] -= r * mu[j][i];
                mu[k][j] -= r;
            }
        }
        if (bs[k] >= (0.99 - mu[k][k - 1] * mu[k][k - 1]) * bs[k - 1]) {
            k++;
        } else {
            for (int t = 0; t < n; t++) {
                i128 tmp = Z[k][t]; Z[k][t] = Z[k - 1][t]; Z[k - 1][t] = tmp;
            }
            for (int i = 0; i < n; i++)
                for (int t = 0; t < n; t++) B[i][t] = (double)Z[i][t];
            gso(B, n, mu, bs);
            k = (k - 1 > 1) ? k - 1 : 1;
        }
    }
}

/* --------------------------------------------- enumeration des points du pave */
struct Pave { i128 lo[NMAX], hi[NMAX]; };

/* Renvoie le nombre de points trouves (au plus `cap`), ecrits dans out[]. */
static int points_pave(i128 Z[NMAX][NMAX], int n, const struct Pave *P,
                       i128 out[][NMAX], int cap, long *noeuds)
{
    double B[NMAX][NMAX], mu[NMAX][NMAX], bs[NMAX], c[NMAX] = {0}, t[NMAX];
    for (int i = 0; i < n; i++)
        for (int k = 0; k < n; k++) B[i][k] = (double)Z[i][k];
    gso(B, n, mu, bs);

    double rho = 0.0;
    for (int i = 0; i < n; i++) {
        t[i] = ((double)P->lo[i] + (double)P->hi[i]) / 2.0;
        double d = ((double)P->hi[i] - (double)P->lo[i]) / 2.0;
        rho += d * d;
    }
    rho *= (1.0 + MARGE);

    /* c_i = <t, b*_i> / |b*_i|^2, par la recurrence de Gram-Schmidt */
    double tb[NMAX], tbs[NMAX];
    for (int i = 0; i < n; i++) {
        tb[i] = 0.0;
        for (int k = 0; k < n; k++) tb[i] += t[k] * B[i][k];
    }
    for (int a = 0; a < n; a++) {
        double s = tb[a];
        for (int j = 0; j < a; j++) s -= mu[a][j] * tbs[j];
        tbs[a] = s;
        c[a] = bs[a] > 0.0 ? s / bs[a] : 0.0;
    }

    double centre[NMAX], reste[NMAX];
    long long x[NMAX], lo[NMAX], hi[NMAX];
    int trouves = 0, i = n - 1;
    centre[i] = c[i];
    reste[i] = rho;

    double s = sqrt(reste[i] / bs[i]);
    lo[i] = (long long)ceil(centre[i] - s);
    hi[i] = (long long)floor(centre[i] + s);
    x[i] = lo[i] - 1;

    for (;;) {
        (*noeuds)++;
        x[i]++;
        if (x[i] > hi[i]) {
            if (++i == n) break;
            continue;
        }
        if (i == 0) {
            i128 v[NMAX];
            for (int k = 0; k < n; k++) v[k] = 0;
            for (int k = 0; k < n; k++)
                if (x[k])
                    for (int u = 0; u < n; u++) v[u] += (i128)x[k] * Z[k][u];
            int dedans = 1;
            for (int k = 0; k < n; k++)
                if (v[k] < P->lo[k] || v[k] > P->hi[k]) { dedans = 0; break; }
            if (dedans && trouves < cap) {
                for (int k = 0; k < n; k++) out[trouves][k] = v[k];
                trouves++;
            }
            continue;
        }
        double d = (double)x[i] - centre[i];
        reste[i - 1] = reste[i] - d * d * bs[i];
        if (reste[i - 1] < 0.0) reste[i - 1] = 0.0;
        double sc = c[i - 1];
        for (int j = i; j < n; j++) sc -= mu[j][i - 1] * (double)x[j];
        centre[i - 1] = sc;
        i--;
        double ss = sqrt(reste[i] / bs[i]);
        lo[i] = (long long)ceil(centre[i] - ss);
        hi[i] = (long long)floor(centre[i] + ss);
        x[i] = lo[i] - 1;
    }
    return trouves;
}

/* ------------------------------------------------------------------- le balayage */
static void base_mult(i128 Z[NMAX][NMAX], int n, uint64_t a, uint64_t m)
{
    uint64_t pw = 1;
    for (int k = 0; k < n; k++) {
        Z[0][k] = (i128)pw;
        pw = (uint64_t)(((unsigned __int128)pw * a) % m);
    }
    for (int i = 1; i < n; i++)
        for (int k = 0; k < n; k++) Z[i][k] = (i == k) ? (i128)m : 0;
}

/* classe d'un mot, troncature par les bits hauts (regle 0 du §232) */
static inline int classe(uint64_t w, uint64_t m)
{
    return (int)(((unsigned __int128)w * POOL) / m);
}

static long nclasses;
static int cls[4096];

/* verification EXACTE en entiers.
 *
 * UNE FAMILLE, PAS UN POINT — et c'est une propriete du probleme, pas un defaut.
 * Si l'on decale x_0 de delta et c de delta*(1-a), alors x_i se decale de delta pour
 * TOUT i : la suite entiere glisse en bloc. Les classes ne changent donc pas tant
 * qu'aucun x_i ne franchit une frontiere. L'ensemble des x_0 compatibles est un
 * INTERVALLE d'environ 2*(m/80)/nclasses valeurs, toutes legitimes. Chercher « le »
 * x_0 n'a pas de sens, et le balayer un par un serait ruineux ; on INTERSECTE.
 *
 * De y_0 et a on tire x_i = x_0 + T_i avec T_i = y_0*(1 + a + ... + a^{i-1}), donc
 * chaque classe impose a x_0 un intervalle CYCLIQUE [lo_i - T_i, hi_i - T_i] mod m.
 * On les intersecte tous, en gardant au plus quelques morceaux, puis on rejoue une
 * fois pour confirmer.
 */
#define MORCEAUX 8

static int verifie(uint64_t a, uint64_t m, const i128 y[], int n, uint64_t *x0out,
                   uint64_t *cout)
{
    (void)n;
    /* y_0 reduit modulo m */
    i128 yy = y[0] % (i128)m;
    if (yy < 0) yy += (i128)m;
    uint64_t y0 = (uint64_t)yy;

    /* morceaux[k] = [b, e] inclus, dans [0, m) */
    uint64_t b[MORCEAUX], e[MORCEAUX];
    int nb = 1;
    b[0] = 0; e[0] = m - 1;

    uint64_t T = 0, pw = 1;                       /* T_i et a^i */
    for (long i = 0; i < nclasses && nb; i++) {
        uint64_t lo = (uint64_t)(((i128)cls[i] * m + POOL - 1) / POOL);
        uint64_t hi = (uint64_t)((((i128)cls[i] + 1) * m + POOL - 1) / POOL - 1);
        uint64_t d0 = (lo + m - T % m) % m;        /* debut de l'intervalle cyclique */
        uint64_t len = hi - lo;                    /* longueur - 1 */
        /* l'intervalle cyclique [d0, d0+len] se coupe en un ou deux morceaux lineaires */
        uint64_t k0b[2], k0e[2];
        int nk = 1;
        k0b[0] = d0;
        if (d0 + len < m) {
            k0e[0] = d0 + len;
        } else {
            k0e[0] = m - 1;
            k0b[1] = 0; k0e[1] = d0 + len - m;
            nk = 2;
        }
        uint64_t nb2b[MORCEAUX], nb2e[MORCEAUX];
        int nb2 = 0;
        for (int u = 0; u < nb; u++)
            for (int v = 0; v < nk; v++) {
                uint64_t lo2 = b[u] > k0b[v] ? b[u] : k0b[v];
                uint64_t hi2 = e[u] < k0e[v] ? e[u] : k0e[v];
                if (lo2 <= hi2 && nb2 < MORCEAUX) {
                    nb2b[nb2] = lo2; nb2e[nb2] = hi2; nb2++;
                }
            }
        nb = nb2;
        for (int u = 0; u < nb; u++) { b[u] = nb2b[u]; e[u] = nb2e[u]; }
        T = (uint64_t)(((i128)T + (i128)y0 * pw) % (i128)m);
        pw = (uint64_t)(((unsigned __int128)pw * a) % m);
    }
    if (!nb) return 0;

    /* un x_0 quelconque du premier morceau suffit : ils sont tous legitimes */
    uint64_t x0 = b[0];
    uint64_t x1 = (uint64_t)(((i128)x0 + (i128)y0) % (i128)m);
    uint64_t ax0 = (uint64_t)(((unsigned __int128)a * x0) % m);
    uint64_t c = (x1 + m - ax0) % m;

    /* et l'on rejoue, en entiers, pour confirmer plutot que pour croire */
    uint64_t w = x0;
    for (long k = 0; k < nclasses; k++) {
        if (classe(w, m) != cls[k]) return 0;
        w = (uint64_t)(((unsigned __int128)a * w + c) % m);
    }
    *x0out = x0; *cout = c;
    return 1;
}

static void pave_diff(struct Pave *P, uint64_t m, int n)
{
    /* y_i = x_{i+1} - x_i : une difference cumule DEUX incertitudes, d'ou m/40 */
    for (int i = 0; i < n; i++) {
        i128 lo0 = ((i128)cls[i] * m + POOL - 1) / POOL;
        i128 hi0 = (((i128)cls[i] + 1) * m + POOL - 1) / POOL - 1;
        i128 lo1 = ((i128)cls[i + 1] * m + POOL - 1) / POOL;
        i128 hi1 = (((i128)cls[i + 1] + 1) * m + POOL - 1) / POOL - 1;
        P->lo[i] = lo1 - hi0;
        P->hi[i] = hi1 - lo0;
    }
}

/* --------------------------------------------------------------------- autotest */
static uint64_t rnd64(uint64_t *s)
{
    *s ^= *s << 13; *s ^= *s >> 7; *s ^= *s << 17;
    return *s;
}

static int autotest(void)
{
    printf("lcg_mult_sweep autotest : temoins plantes, donnees synthetiques\n");
    uint64_t s = 0x9E3779B97F4A7C15ULL;
    int ok = 1;
    for (int bits = 29; bits <= 32; bits++) {
        uint64_t m = 1ULL << bits;
        for (int essai = 0; essai < 3; essai++) {
            uint64_t a = (rnd64(&s) % (m / 4)) * 4 + 1;      /* periode maximale */
            uint64_t c = (rnd64(&s) % (m / 2)) * 2 + 1;
            uint64_t x0 = rnd64(&s) % m;
            nclasses = 40;
            uint64_t w = x0;
            for (long k = 0; k < nclasses; k++) {
                cls[k] = classe(w, m);
                w = (uint64_t)(((unsigned __int128)a * w + c) % m);
            }
            i128 Z[NMAX][NMAX];
            base_mult(Z, N, a, m);
            lll(Z, N);
            struct Pave P;
            pave_diff(&P, m, N);
            i128 out[64][NMAX];
            long nd = 0;
            int nb = points_pave(Z, N, &P, out, 64, &nd);
            int releve = 0;
            uint64_t rx = 0, rc = 0;
            for (int t = 0; t < nb; t++)
                if (verifie(a, m, out[t], N, &rx, &rc)) { releve = 1; break; }
            /* La solution est une FAMILLE : (x0 + d, c + d(1-a)) donne la meme suite
             * decalee de d, donc les memes classes. On exige donc que le couple relevé
             * appartienne a la famille du couple plante, pas qu'il lui soit egal. */
            i128 d = ((i128)rx - (i128)x0 % (i128)m + (i128)m) % (i128)m;
            uint64_t attendu = (uint64_t)((((i128)c + d * ((i128)1 - (i128)a)) % (i128)m
                                           + (i128)m) % (i128)m);
            int famille = releve && rc == attendu;
            printf("   m = 2^%d, a = %" PRIu64 " : %d point(s), %ld noeuds, %s%s\n",
                   bits, a, nb, nd, releve ? "etat RELEVE" : "MANQUE",
                   famille ? " (dans la famille du couple plante)"
                   : (releve ? " (HORS de la famille plantee !)" : ""));
            if (!famille) ok = 0;
        }
    }
    /* temoin NEGATIF : des classes au hasard, et un multiplicateur au hasard */
    {
        uint64_t m = 1ULL << 32;
        nclasses = 40;
        for (long k = 0; k < nclasses; k++) cls[k] = (int)(rnd64(&s) % POOL);
        long faux = 0, nd = 0;
        for (int t = 0; t < 2000; t++) {
            uint64_t a = (rnd64(&s) % (m / 4)) * 4 + 1;
            i128 Z[NMAX][NMAX];
            base_mult(Z, N, a, m);
            lll(Z, N);
            struct Pave P;
            pave_diff(&P, m, N);
            i128 out[64][NMAX];
            int nb = points_pave(Z, N, &P, out, 64, &nd);
            uint64_t rx, rc;
            for (int u = 0; u < nb; u++)
                if (verifie(a, m, out[u], N, &rx, &rc)) faux++;
        }
        printf("   temoin NEGATIF : 2000 multiplicateurs sur des classes au hasard, "
               "%ld survivant(s), attendu 0 (%ld noeuds)\n", faux, nd);
        if (faux) ok = 0;
    }
    printf("   -> %s\n", ok ? "CALIBRE" : "DEFAILLANT");
    return ok;
}

static void bench(int bits)
{
    uint64_t m = 1ULL << bits, s = 12345;
    nclasses = 40;
    for (long k = 0; k < nclasses; k++) cls[k] = (int)(rnd64(&s) % POOL);
    long nd = 0;
    int R = 20000;
    clock_t t0 = clock();
    for (int t = 0; t < R; t++) {
        uint64_t a = (rnd64(&s) % (m / 4)) * 4 + 1;
        i128 Z[NMAX][NMAX];
        base_mult(Z, N, a, m);
        lll(Z, N);
        struct Pave P;
        pave_diff(&P, m, N);
        i128 out[64][NMAX];
        points_pave(Z, N, &P, out, 64, &nd);
    }
    double dt = (double)(clock() - t0) / CLOCKS_PER_SEC;
    double par = dt / R;
    printf("bench m = 2^%d, n = %d : %.2f us par multiplicateur, %ld noeuds\n",
           bits, N, par * 1e6, nd);
    double total = par * (double)(1ULL << (bits - 1));
    printf("   balayage complet des %.0f multiplicateurs impairs : %.1f h sur un coeur\n",
           (double)(1ULL << (bits - 1)), total / 3600.0);
}

/* --------------------------------------------------------------- le balayage reel */
/* LE PAS DE BLOC DISPARAIT, ET C'EST LE POINT.
 * Le flux du bonus donne un mot par tirage, espaces de P mots sous le §225 : la chaine
 * qu'il suit est donc un LCG de multiplicateur A = a^P. Or a^P parcourt les impairs quand
 * a le fait. BALAYER TOUS LES A IMPAIRS COUVRE DONC TOUS LES (a, c, P) A LA FOIS — le pas
 * de bloc n'est plus un parametre a balayer, il est absorbe. */
static long lire_classes(const char *chemin)
{
    FILE *f = fopen(chemin, "r");
    if (!f) { perror(chemin); exit(2); }
    long k = 0;
    int v;
    while (k < (long)(sizeof cls / sizeof cls[0]) && fscanf(f, "%d", &v) == 1) {
        if (v < 0 || v >= POOL) { fprintf(stderr, "classe hors 0..79\n"); exit(2); }
        cls[k++] = v;
    }
    fclose(f);
    return k;
}

static void sweep(int bits, const char *chemin, unsigned long part, unsigned long nparts)
{
    uint64_t m = 1ULL << bits;
    nclasses = lire_classes(chemin);
    if (nclasses < N + 2) { fprintf(stderr, "il faut au moins %d classes\n", N + 2); exit(2); }
    struct Pave P;
    pave_diff(&P, m, N);
    uint64_t total = m / 2;                       /* multiplicateurs impairs */
    long survivants = 0, noeuds = 0;
    uint64_t faits = 0;
    clock_t t0 = clock();
    for (uint64_t idx = part; idx < total; idx += nparts) {
        uint64_t a = 2 * idx + 1;
        i128 Z[NMAX][NMAX];
        base_mult(Z, N, a, m);
        lll(Z, N);
        i128 out[64][NMAX];
        int nb = points_pave(Z, N, &P, out, 64, &noeuds);
        for (int t = 0; t < nb; t++) {
            uint64_t rx, rc;
            if (verifie(a, m, out[t], N, &rx, &rc)) {
                survivants++;
                printf("*** SURVIVANT m=2^%d a=%" PRIu64 " c=%" PRIu64 " x0=%" PRIu64 "\n",
                       bits, a, rc, rx);
                fflush(stdout);
            }
        }
        if (((++faits) & 0xFFFFFF) == 0) {
            double dt = (double)(clock() - t0) / CLOCKS_PER_SEC;
            fprintf(stderr, "   part %lu : %" PRIu64 " / %" PRIu64 " (%.1f%%), %.0f s\n",
                    part, faits, total / nparts, 100.0 * faits / (total / nparts), dt);
        }
    }
    double dt = (double)(clock() - t0) / CLOCKS_PER_SEC;
    printf("part %lu/%lu : m = 2^%d, %" PRIu64 " multiplicateurs impairs, %ld classes, "
           "%ld survivant(s), %ld noeuds, %.0f s\n",
           part, nparts, bits, faits, nclasses, survivants, noeuds, dt);
}

/* Mode `croise` : imprime, pour des instances tirees au hasard, le multiplicateur, les
 * classes et le NOMBRE de points du pave. `lab/cvp_exact.py` refait exactement le meme
 * calcul en Fraction ; si les deux comptes different, c'est que le `double` a
 * manque un point, et la phrase « exact a une marge bornee pres » serait une opinion. */
static void croise(int bits, unsigned long graine, int reps)
{
    uint64_t m = 1ULL << bits, s = graine ? graine : 1;
    printf("%d %d\n", bits, N);
    for (int t = 0; t < reps; t++) {
        uint64_t a = (rnd64(&s) % (m / 4)) * 4 + 1;
        nclasses = N + 1;
        for (long k = 0; k < nclasses; k++) cls[k] = (int)(rnd64(&s) % POOL);
        i128 Z[NMAX][NMAX];
        base_mult(Z, N, a, m);
        lll(Z, N);
        struct Pave P;
        pave_diff(&P, m, N);
        i128 out[256][NMAX];
        long nd = 0;
        int nb = points_pave(Z, N, &P, out, 256, &nd);
        printf("%" PRIu64, a);
        for (long k = 0; k < nclasses; k++) printf(" %d", cls[k]);
        printf(" | %d\n", nb);
    }
}

int main(int argc, char **argv)
{
    if (argc >= 2 && !strcmp(argv[1], "autotest")) return autotest() ? 0 : 1;
    if (argc >= 3 && !strcmp(argv[1], "bench")) { bench(atoi(argv[2])); return 0; }
    if (argc >= 4 && !strcmp(argv[1], "sweep")) {
        unsigned long part = argc >= 5 ? strtoul(argv[4], NULL, 10) : 0;
        unsigned long nparts = argc >= 6 ? strtoul(argv[5], NULL, 10) : 1;
        sweep(atoi(argv[2]), argv[3], part, nparts);
        return 0;
    }
    if (argc >= 5 && !strcmp(argv[1], "croise")) {
        croise(atoi(argv[2]), strtoul(argv[3], NULL, 10), atoi(argv[4]));
        return 0;
    }
    fprintf(stderr, "usage: %s autotest | bench <bits> | croise <bits> <graine> <reps>"
            " | sweep <bits> <classes.txt> [<part> <nparts>]\n", argv[0]);
    return 1;
}
