// lfg_struct_flux — le DISTINGUEUR STRUCTUREL : TOUTES les relations de poids 3 d'un Fibonacci retardé
// de retard L QUELCONQUE, sans transformée de Walsh–Hadamard et sans état (h143, THEORIE_ETAT §7.15).
//
// LE MODÈLE
// ---------
// Fibonacci retardé r_i = r_{i−K} ∘ r_{i−L} (∘ = + ou − mod 2^32, ou ⊕), lu à pas S constant : le tirage t
// lit les mots x_{S·t + k} (fy : k = 0..19 ; shuffle : k = 0..78), comme lfg_rel3_flux. Sortie x = r
// (décalage 0) pour + et − : le bit 0 observé est le PLAN 0 de r, qui vérifie EXACTEMENT la récurrence
// linéaire b_i = b_{i−K} ⊕ b_{i−L} (le plan 0 d'une somme ou d'une différence est le ⊕ des plans 0), de
// polynôme f(x) = x^L + x^{L−K} + 1. Pour ⊕ tous les plans la vérifient : x = r >> s, tout s.
//
// LA STATISTIQUE (§7.15)
// ----------------------
// Un tirage trié ne révèle qu'UNE variable molle : T = (n_impairs − n_pairs)/20 (moyenne de (−1)^{v−1}
// sur les vingt numéros ; c'est le bit mou du mot k = 0, identique pour fy et shuffle). Le modèle nourri
// de mots uniformes donne C(k') = E[(T − E0)(−1)^{b_{k'}}] pour chaque mot pair k' = 0, 2, …, 18 (seuls les
// mots pairs — modulo pair — livrent leur bit 0 ; C(k') ≈ 0,038 ≈ Var T = τ0², presque plat : les dix bits
// mous sont le même bit). Une RELATION DE POIDS 3 est un couple (d, j), 0 < d < j, tel que
// x^j + x^d + 1 ≡ 0 mod f : alors b_a ⊕ b_{a+d} ⊕ b_{a+j} = 0 pour tout a. On les ÉNUMÈRE TOUTES jusqu'à
// j ≤ étendue (puissances x^e mod f hachées linéairement, tri, dichotomie sur x^j ⊕ 1, vérification exacte)
// — elles sont bien plus nombreuses que la seule famille structurelle (a, a+(L−K)2^m, a+L2^m) : 768 pour
// (3, 31), 87 pour (1, 63) sous 1,4·10^6. Chaque (d, j) et chaque mot pair k du tirage t_a envoie le triple
// (S t_a + k, + d, + j) sur trois tirages (t_a, t_a + δ1, t_a + δ2) s'il tombe sur des mots pairs k1, k2 ≤ 18
// des deux autres tirages ; le MOTIF (δ1, δ2) reçoit le poids w += C(k) C(k1) C(k2) (Fourier au premier
// ordre : E[T_a T_b T_c] = Σ des C C C sur toutes les relations qui relient les trois tirages). D'où
//     Λ = Σ_motifs w_p Σ_{t_a} T_{t_a} T_{t_a+δ1} T_{t_a+δ2},   V = τ⁶ Σ_p w_p² n_p,   z = Λ/√V,
//     z_attendu = √(Σ_p w_p² n_p) / τ³
// (n_p = nombre de t_a valides ; τ² = variance empirique de T, T centré par sa moyenne empirique). Sous H0
// les T sont indépendants et centrés, deux triples distincts sont non corrélés : V est exacte. Il n'y a
// AUCUN état à chercher : pas de borne d'union sur 2^L, le seuil est celui de la grille (Zc = Q⁻¹(10⁻⁷ /
// STRUCT_NTESTS)). La statistique ne dépend pas de l'état : elle se SOMME sur les blocs (mode bloc : un
// état par nuit, motifs internes aux blocs). Ce qu'elle ne fait pas : le décalage 1 des générateurs + et −
// (le bit observé est le plan 1, dont le défaut par rapport à la relation est une somme de ≥ 2 produits de
// bits indépendants du plan 0 : équilibré, §7.15).
//
// USAGE
// -----
//   lfg_struct_flux S fy|shuffle fichier blocs|- K1,L1 [K2,L2 …]
//        fichier : un tirage par ligne, vingt numéros 1..80 ; blocs : '-' = flux continu (un seul état),
//        sinon fichier des indices (0-based) des premiers tirages de chaque bloc. Sortie : CALIB … ; DATA … ;
//        par trinôme : REL K L relations=… motifs=… ; MOTIF … (STRUCT_VERBOSE=1) ; FIN K L S mode flux|bloc
//        relations motifs triples z_attendu z zmax_motif Zc detecte ; SEC.
//   lfg_struct_flux --selftest S fy|shuffle N graine K,L [nbloc]
//        plante un état (L mots de 32 bits) sur N tirages (nbloc ≥ 2 : nbloc états sur nbloc blocs de
//        N/nbloc tirages, mode bloc), décode, puis N tirages nuls ; VERITE … ; NUL … ; AUTOTEST ….
//   Environnement : STRUCT_NTESTS (1 : nombre de statistiques de la grille pour Zc), STRUCT_VERBOSE,
//   LFG_OP (add | sub | xor, autotest), LFG_SHIFT (0 : sortie x = r >> SHIFT dans l'autotest).
//
//   cc -O3 -march=native -o lfg_struct_flux tools/lfg_struct_flux.c -lm

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#include <sys/time.h>

#define POOL  80
#define DRAWN 20
#define NWM   10                              // mots pairs observés k = 0, 2, …, 18
#define WMAX  24                              // L ≤ 64·WMAX
#define RELMAX 400000                         // relations conservées au plus (petits L : période < étendue)
#define PATMAX 65536                          // motifs au plus

static int S, MODE, N;
static int *ENS;                              // N × 20
static float *T;                              // N : (n_impairs − n_pairs)/20, centré
static double TAU2;                           // variance empirique de T
static double E0, TAU0, CK[NWM];              // calibrage : E T, Var T, C(k') sous mots uniformes
static int NB; static int *BLOC;              // bloc de chaque tirage (NULL : flux)
static int NTESTS = 1, VERBOSE = 0;

static double now(void) { struct timeval tv; gettimeofday(&tv, NULL); return tv.tv_sec + 1e-6 * tv.tv_usec; }
static double qinv(double q) {
    double lo = 0, hi = 40;
    for (int it = 0; it < 200; it++) { double m = (lo + hi) / 2; if (0.5 * erfc(m / sqrt(2)) > q) lo = m; else hi = m; }
    return lo;
}

// ----------------------------------------------------------------- la variable molle d'un tirage
static double stat_T(const int *ens) {
    int n = 0;
    for (int q = 0; q < DRAWN; q++) n += (ens[q] & 1) ? 1 : -1;
    return (double)n / DRAWN;
}
static uint64_t rng_s = 0x9E3779B97F4A7C15ull;
static uint32_t rnd(void) { rng_s ^= rng_s << 13; rng_s ^= rng_s >> 7; rng_s ^= rng_s << 17; return (uint32_t)(rng_s >> 11); }
static void tirage_nul(int *ens) {
    int arr[POOL];
    for (int q = 0; q < POOL; q++) arr[q] = q + 1;
    for (int i = POOL - 1; i >= 1; i--) { int j = rnd() % (i + 1); int tmp = arr[i]; arr[i] = arr[j]; arr[j] = tmp; }
    for (int q = 0; q < DRAWN; q++) ens[q] = arr[q];
}
// Le schéma lui-même (fy partiel ou shuffle) nourri de mots x uniformes ; b[m] = bit 0 du mot pair k = 2m.
static void tirage_modele(int *ens, int *b) {
    int arr[POOL];
    for (int q = 0; q < POOL; q++) arr[q] = q + 1;
    if (MODE == 0) {
        for (int k = 0; k < DRAWN; k++) { uint32_t x = rnd(); if (!(k & 1)) b[k >> 1] = x & 1; int j = k + (int)(x % (POOL - k)); int tmp = arr[k]; arr[k] = arr[j]; arr[j] = tmp; ens[k] = arr[k]; }
    } else {
        for (int i = POOL - 1; i >= 1; i--) { int k = POOL - 1 - i; uint32_t x = rnd(); if (k <= 18 && !(k & 1)) b[k >> 1] = x & 1; int j = (int)(x % (i + 1)); int tmp = arr[i]; arr[i] = arr[j]; arr[j] = tmp; }
        for (int q = 0; q < DRAWN; q++) ens[q] = arr[POOL - DRAWN + q];
    }
}
#define NCAL 1000000
static void calibre(void) {
    uint64_t sauve = rng_s; rng_s = 0xD1B54A32D192ED03ull;
    double s1 = 0, s2 = 0, sb[NWM] = {0}, sp[NWM] = {0}; int ens[DRAWN], b[NWM];
    for (int it = 0; it < NCAL; it++) {
        tirage_modele(ens, b); double t = stat_T(ens);
        s1 += t; s2 += t * t;
        for (int m = 0; m < NWM; m++) { double sg = b[m] ? -1 : 1; sb[m] += t * sg; sp[m] += sg; }
    }
    E0 = s1 / NCAL; TAU0 = s2 / NCAL - E0 * E0;
    printf("CALIB %s E0=%.5f tau0²=%.5f C(k')", MODE ? "shuffle" : "fy", E0, TAU0);
    for (int m = 0; m < NWM; m++) { CK[m] = sb[m] / NCAL - E0 * (sp[m] / NCAL); printf(" %.4f", CK[m]); }
    printf("\n");
    rng_s = sauve;
}
static void charge_T(void) {                  // T centré par la moyenne empirique, variance empirique
    T = malloc(sizeof(float) * (size_t)N);
    double s1 = 0, s2 = 0;
    for (int t = 0; t < N; t++) { double x = stat_T(ENS + (size_t)t * DRAWN); T[t] = (float)x; s1 += x; s2 += x * x; }
    double mu = s1 / N; TAU2 = s2 / N - mu * mu;
    for (int t = 0; t < N; t++) T[t] -= (float)mu;
    printf("DATA N=%d moyenne_T=%.5f var_T=%.5f (calibrage %.5f)\n", N, mu, TAU2, TAU0);
}

// ----------------------------------------------------------------- polynômes sur GF(2) modulo f = x^L + x^{L−K} + 1
static int W, PL, PK;                         // mots, L, L−K
static uint64_t RH[WMAX * 64];                // hachage linéaire : h(v) = ⊕_{bit i de v} RH[i]
static uint64_t hache(const uint64_t *v) {
    uint64_t h = 0;
    for (int w = 0; w < W; w++) { uint64_t x = v[w]; while (x) { int b = __builtin_ctzll(x); h ^= RH[w * 64 + b]; x &= x - 1; } }
    return h;
}
static void fois_x(uint64_t *v) {             // v ← x·v mod f
    int top = (int)((v[(PL - 1) >> 6] >> ((PL - 1) & 63)) & 1);
    uint64_t carry = 0;
    for (int w = 0; w < W; w++) { uint64_t nv = (v[w] << 1) | carry; carry = v[w] >> 63; v[w] = nv; }
    v[(PL - 1) >> 6] &= (PL & 63) ? ((1ull << (PL & 63)) - 1) : ~0ull;     // efface x^L
    if (top) { v[0] ^= 1; v[PK >> 6] ^= 1ull << (PK & 63); }
}
static void mulmod(const uint64_t *a, const uint64_t *b, uint64_t *out) {   // out ← a·b mod f
    uint64_t p[2 * WMAX] = {0};
    for (int w = 0; w < W; w++) { uint64_t x = a[w]; while (x) { int i = __builtin_ctzll(x); x &= x - 1; int sh = w * 64 + i, ws = sh >> 6, bs = sh & 63;
        for (int u = 0; u < W; u++) { p[u + ws] ^= b[u] << bs; if (bs) p[u + ws + 1] ^= b[u] >> (64 - bs); } } }
    for (int e = 2 * PL - 2; e >= PL; e--) if ((p[e >> 6] >> (e & 63)) & 1) {
        p[e >> 6] ^= 1ull << (e & 63); int e1 = e - (PL - PK), e2 = e - PL;   // x^e = x^{e−K} + x^{e−L}
        p[e1 >> 6] ^= 1ull << (e1 & 63); p[e2 >> 6] ^= 1ull << (e2 & 63);
    }
    memcpy(out, p, sizeof(uint64_t) * W);
}
static void puissance(int64_t e, uint64_t *out) {    // out ← x^e mod f
    uint64_t r[WMAX] = {1}, x[WMAX] = {0}; x[0] = 2;
    if (PL == 1) { fprintf(stderr, "L = 1 ?\n"); exit(1); }
    for (int b = 62; b >= 0; b--) { uint64_t t[WMAX]; mulmod(r, r, t); memcpy(r, t, sizeof r); if ((e >> b) & 1) { mulmod(r, x, t); memcpy(r, t, sizeof r); } }
    memcpy(out, r, sizeof(uint64_t) * W);
}
typedef struct { int64_t d, j; } Rel;
typedef struct { uint64_t h; int64_t e; } HE;
static int cmp_he(const void *a, const void *b) { uint64_t x = ((const HE *)a)->h, y = ((const HE *)b)->h; return x < y ? -1 : x > y; }
static Rel *REL; static int NREL;
// Toutes les relations (d, j), 0 < d < j ≤ jmax, x^j + x^d + 1 ≡ 0 mod f, par j croissant.
static void enumere_relations(int K, int L, int64_t jmax, int *tronque) {
    PL = L; PK = L - K; W = (L + 63) / 64; *tronque = 0;
    if (W > WMAX) { fprintf(stderr, "L trop grand (≤ %d)\n", 64 * WMAX); exit(1); }
    uint64_t s = 0x243F6A8885A308D3ull;
    for (int i = 0; i < W * 64; i++) { s += 0x9E3779B97F4A7C15ull; uint64_t z = s; z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ull; z = (z ^ (z >> 27)) * 0x94D049BB133111EBull; RH[i] = z ^ (z >> 31); }
    uint64_t v[WMAX] = {1};
    int exact = W == 1;                       // L ≤ 64 : la puissance elle-même tient dans la clé, pas de collision
    uint64_t *H = malloc(sizeof(uint64_t) * (size_t)(jmax + 1)); HE *tab = malloc(sizeof(HE) * (size_t)(jmax + 1));
    for (int64_t e = 0; e <= jmax; e++) { H[e] = exact ? v[0] : hache(v); tab[e].h = H[e]; tab[e].e = e; fois_x(v); }
    qsort(tab, (size_t)(jmax + 1), sizeof(HE), cmp_he);
    REL = malloc(sizeof(Rel) * RELMAX); NREL = 0;
    uint64_t h1 = exact ? 1 : RH[0];          // clé de 1
    int64_t nverif = 0, nfaux = 0;
    for (int64_t j = 1; j <= jmax && !*tronque; j++) {
        uint64_t cible = H[j] ^ h1;           // clé de x^j + 1
        int64_t lo = 0, hi = jmax + 1;
        while (lo < hi) { int64_t m = (lo + hi) / 2; if (tab[m].h < cible) lo = m + 1; else hi = m; }
        for (int64_t q = lo; q <= jmax && tab[q].h == cible; q++) {
            int64_t d = tab[q].e; if (d <= 0 || d >= j) continue;
            if (!exact) {                     // vérification exacte de x^j + x^d + 1 ≡ 0
                uint64_t xd[WMAX], xj[WMAX]; puissance(d, xd); puissance(j, xj); xj[0] ^= 1; nverif++;
                if (memcmp(xd, xj, sizeof(uint64_t) * W)) { nfaux++; continue; }
            }
            if (NREL == RELMAX) { *tronque = 1; break; }
            REL[NREL].d = d; REL[NREL].j = j; NREL++;
        }
    }
    if (nfaux) fprintf(stderr, "collisions de hachage rejetées : %lld\n", (long long)nfaux);
    free(H); free(tab);
}

// ----------------------------------------------------------------- motifs (δ1, δ2)
typedef struct { int64_t d1, d2; double w; int64_t n; int cnt; double lam; } Pat;
static Pat *PAT; static int NPAT; static int64_t *PIDX; static uint64_t PMASK;
static void pat_init(void) {
    uint64_t n = 1; while (n < (uint64_t)PATMAX * 4) n <<= 1;
    PAT = malloc(sizeof(Pat) * PATMAX); NPAT = 0; PIDX = malloc(sizeof(int64_t) * n); PMASK = n - 1;
    for (uint64_t i = 0; i < n; i++) PIDX[i] = -1;
}
static int pat_add(int64_t d1, int64_t d2, double w) {   // 0 si plein
    uint64_t key = ((uint64_t)d1 << 32) | (uint64_t)d2, h = (key * 0x9E3779B97F4A7C15ull) >> 20;
    for (;;) {
        h &= PMASK;
        if (PIDX[h] < 0) { if (NPAT == PATMAX) return 0; PIDX[h] = NPAT; PAT[NPAT].d1 = d1; PAT[NPAT].d2 = d2; PAT[NPAT].w = w; PAT[NPAT].n = 0; PAT[NPAT].cnt = 1; PAT[NPAT].lam = 0; NPAT++; return 1; }
        Pat *p = &PAT[PIDX[h]];
        if (p->d1 == d1 && p->d2 == d2) { p->w += w; p->cnt++; return 1; }
        h++;
    }
}
static int64_t compte_valides(int64_t d2) {   // nombre de t_a avec t_a + δ2 < N (et même bloc)
    if (!BLOC) return d2 < N ? N - d2 : 0;
    int64_t n = 0;
    for (int t = 0; t + d2 < N; t++) if (BLOC[t] == BLOC[t + d2]) n++;
    return n;
}

// ----------------------------------------------------------------- la statistique d'un trinôme
static double rapporte(int K, int L, double Zc, double *z_att_out, double *zmax_out) {
    int64_t jmax = (int64_t)S * (N - 1) + 18;
    if (BLOC) { int64_t lmax = 0, lo = 0; for (int t = 1; t <= N; t++) if (t == N || BLOC[t] != BLOC[t - 1]) { if (t - lo > lmax) lmax = t - lo; lo = t; } jmax = S * (lmax - 1) + 18; }
    int tronque; enumere_relations(K, L, jmax, &tronque);
    pat_init(); int plein = 0;
    for (int q = 0; q < NREL && !plein; q++) {
        int64_t d = REL[q].d, j = REL[q].j;
        for (int m = 0; m < NWM; m++) {
            int64_t p1 = 2 * m + d, p2 = 2 * m + j, d1 = p1 / S, d2 = p2 / S; int k1 = (int)(p1 % S), k2 = (int)(p2 % S);
            if ((k1 & 1) || k1 > 18 || (k2 & 1) || k2 > 18 || d1 < 1 || d2 <= d1) continue;
            if (!pat_add(d1, d2, CK[m] * CK[k1 >> 1] * CK[k2 >> 1])) { plein = 1; break; }
        }
    }
    printf("REL %d %d relations=%d%s motifs=%d%s jmax=%lld premieres:", K, L, NREL, tronque ? "(tronquees)" : "", NPAT, plein ? "(plein)" : "", (long long)jmax);
    for (int q = 0; q < NREL && q < 8; q++) printf(" (%lld,%lld)", (long long)REL[q].d, (long long)REL[q].j);
    printf("\n");
    double lam = 0, V = 0, sw2n = 0, tau6 = TAU2 * TAU2 * TAU2, zmax = 0; int64_t ntri = 0;
    for (int p = 0; p < NPAT; p++) {
        Pat *P = &PAT[p]; P->n = compte_valides(P->d2); if (P->n == 0) continue;
        double s = 0; int64_t d1 = P->d1, d2 = P->d2;
        if (BLOC) { for (int t = 0; t + d2 < N; t++) if (BLOC[t] == BLOC[t + d2]) s += (double)T[t] * T[t + d1] * T[t + d2]; }
        else      { for (int t = 0; t + d2 < N; t++) s += (double)T[t] * T[t + d1] * T[t + d2]; }
        P->lam = s; lam += P->w * s; sw2n += P->w * P->w * P->n; ntri += P->n;
        double zp = s / sqrt(P->n * tau6); if (fabs(zp) > fabs(zmax)) zmax = zp;
        if (VERBOSE) printf("MOTIF %d %d d1=%lld d2=%lld cnt=%d w=%.3e n=%lld z_att=%.2f z=%.2f\n", K, L, (long long)d1, (long long)d2, P->cnt, P->w, (long long)P->n, P->w * P->n / sqrt(P->n * tau6), zp);
    }
    V = tau6 * sw2n;
    double z = V > 0 ? lam / sqrt(V) : 0, za = V > 0 ? sw2n / sqrt(V) : 0;
    *z_att_out = za; *zmax_out = zmax;
    printf("FIN %d %d %d %s %s relations=%d motifs=%d triples=%lld z_attendu=%.2f z=%.2f zmax_motif=%.2f Zc=%.2f detecte=%d\n",
           K, L, S, MODE ? "shuffle" : "fy", BLOC ? "bloc" : "flux", NREL, NPAT, (long long)ntri, za, z, zmax, Zc, z >= Zc);
    free(REL); free(PAT); free(PIDX);
    return z;
}

// ----------------------------------------------------------------- autotest
static int SHIFT = 0; static int OP = 0;       // OP : 0 add, 1 sub, 2 xor
static void genere(int K, int L, int *ens, int t0, int n, uint64_t graine) {   // un état, n tirages à partir du tirage t0
    rng_s = graine * 0x2545F4914F6CDD1Dull + 0x9E3779B97F4A7C15ull;
    int64_t npos = (int64_t)S * (n - 1) + POOL + L;
    uint32_t *r = malloc(sizeof(uint32_t) * npos);
    for (int64_t i = 0; i < npos; i++) {
        if (i < L) r[i] = rnd();
        else r[i] = OP == 0 ? r[i - K] + r[i - L] : OP == 1 ? r[i - K] - r[i - L] : r[i - K] ^ r[i - L];
    }
    for (int t = 0; t < n; t++) {
        int arr[POOL], *e = ens + (size_t)(t0 + t) * DRAWN;
        for (int q = 0; q < POOL; q++) arr[q] = q + 1;
        if (MODE == 0) {
            for (int k = 0; k < DRAWN; k++) { int j = k + (int)((r[(int64_t)S * t + k] >> SHIFT) % (POOL - k)); int tmp = arr[k]; arr[k] = arr[j]; arr[j] = tmp; e[k] = arr[k]; }
        } else {
            for (int i = POOL - 1; i >= 1; i--) { int k = POOL - 1 - i; int j = (int)((r[(int64_t)S * t + k] >> SHIFT) % (i + 1)); int tmp = arr[i]; arr[i] = arr[j]; arr[j] = tmp; }
            for (int q = 0; q < DRAWN; q++) e[q] = arr[POOL - DRAWN + q];
        }
    }
    free(r);
}
static void selftest(int K, int L, int n, uint64_t graine, int nbloc) {
    double t0 = now();
    N = n; ENS = malloc(sizeof(int) * (size_t)N * DRAWN);
    double Zc = qinv(1e-7 / NTESTS);
    calibre();
    if (nbloc >= 2) {                         // un état par bloc, blocs de N/nbloc tirages
        NB = nbloc; BLOC = malloc(sizeof(int) * N);
        int len = N / nbloc;
        for (int b = 0; b < nbloc; b++) {
            int lo = b * len, hi = b == nbloc - 1 ? N : lo + len;
            for (int t = lo; t < hi; t++) BLOC[t] = b;
            genere(K, L, ENS, lo, hi - lo, graine + 1000003ull * b);
        }
    } else genere(K, L, ENS, 0, N, graine);
    charge_T();
    double za, zm; double z = rapporte(K, L, Zc, &za, &zm);
    int det = z >= Zc;
    printf("VERITE op=%s shift=%d blocs=%d z_attendu=%.2f z=%.2f detecte=%d\n", OP == 0 ? "add" : OP == 1 ? "sub" : "xor", SHIFT, nbloc, za, z, det);
    rng_s = graine ^ 0xABCDEF1234567ull;
    for (int t = 0; t < N; t++) tirage_nul(ENS + (size_t)t * DRAWN);
    free(T); charge_T();
    double zn = rapporte(K, L, Zc, &za, &zm);
    int fp = zn >= Zc;
    printf("NUL z=%.2f faux_positif=%d\n", zn, fp);
    printf("AUTOTEST %d %d %d %s op=%s shift=%d blocs=%d plantes=1 detectes=%d nuls=1 Zc=%.2f faux_positifs=%d sec=%.1f\n",
           K, L, S, MODE ? "shuffle" : "fy", OP == 0 ? "add" : OP == 1 ? "sub" : "xor", SHIFT, nbloc, det, Zc, fp, now() - t0);
}

// ----------------------------------------------------------------- lecture
static int lit_archive(const char *fn) {
    FILE *f = fopen(fn, "r"); if (!f) { perror(fn); exit(1); }
    int cap = 1 << 16; ENS = malloc(sizeof(int) * (size_t)cap * DRAWN); N = 0; char line[4096];
    while (fgets(line, sizeof line, f)) {
        int v[DRAWN], q = 0; char *s = line;
        while (q < DRAWN) { char *e; long x = strtol(s, &e, 10); if (e == s) break; v[q++] = (int)x; s = e; }
        if (q < DRAWN) continue;
        if (N == cap) { cap *= 2; ENS = realloc(ENS, sizeof(int) * (size_t)cap * DRAWN); }
        memcpy(ENS + (size_t)N * DRAWN, v, sizeof v); N++;
    }
    fclose(f); return N;
}
static void lit_blocs(const char *fn) {
    FILE *f = fopen(fn, "r"); if (!f) { perror(fn); exit(1); }
    int cap = 1024, *t0 = malloc(sizeof(int) * cap); NB = 0; char line[256];
    while (fgets(line, sizeof line, f)) { char *e; long x = strtol(line, &e, 10); if (e == line) continue; if (NB == cap) { cap *= 2; t0 = realloc(t0, sizeof(int) * cap); } t0[NB++] = (int)x; }
    fclose(f);
    if (NB == 0 || t0[0] != 0) { fprintf(stderr, "blocs : le premier indice doit être 0\n"); exit(1); }
    BLOC = malloc(sizeof(int) * N);
    for (int b = 0; b < NB; b++) { int hi = b + 1 < NB ? t0[b + 1] : N; for (int t = t0[b]; t < hi && t < N; t++) BLOC[t] = b; }
    free(t0);
}

int main(int argc, char **argv) {
    const char *e = getenv("STRUCT_NTESTS"); if (e) NTESTS = atoi(e);
    e = getenv("STRUCT_VERBOSE"); if (e) VERBOSE = atoi(e);
    e = getenv("LFG_SHIFT"); if (e) SHIFT = atoi(e);
    e = getenv("LFG_OP"); if (e) OP = !strcmp(e, "sub") ? 1 : !strcmp(e, "xor") ? 2 : 0;
    if (argc >= 7 && !strcmp(argv[1], "--selftest")) {
        S = atoi(argv[2]); MODE = !strcmp(argv[3], "shuffle"); int n = atoi(argv[4]); uint64_t graine = strtoull(argv[5], NULL, 10);
        int K, L; if (sscanf(argv[6], "%d,%d", &K, &L) != 2 || K <= 0 || K >= L) { fprintf(stderr, "K,L invalides\n"); return 2; }
        int nbloc = argc >= 8 ? atoi(argv[7]) : 1;
        selftest(K, L, n, graine, nbloc); return 0;
    }
    if (argc < 6) { fprintf(stderr, "usage : lfg_struct_flux S fy|shuffle fichier blocs|- K1,L1 [K2,L2 …] | --selftest S fy|shuffle N graine K,L [nbloc]\n"); return 2; }
    S = atoi(argv[1]); MODE = !strcmp(argv[2], "shuffle");
    lit_archive(argv[3]);
    if (strcmp(argv[4], "-")) lit_blocs(argv[4]);
    calibre(); charge_T();
    double Zc = qinv(1e-7 / NTESTS);
    for (int q = 5; q < argc; q++) {
        int K, L; if (sscanf(argv[q], "%d,%d", &K, &L) != 2 || K <= 0 || K >= L) { fprintf(stderr, "K,L invalides : %s\n", argv[q]); return 2; }
        double t0 = now(), za, zm; rapporte(K, L, Zc, &za, &zm);
        printf("SEC %d %d %.1f\n", K, L, now() - t0);
        fflush(stdout);
    }
    return 0;
}
