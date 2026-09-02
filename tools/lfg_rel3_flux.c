// lfg_rel3_flux — les RELATIONS DE POIDS 3 SUR Z/4 sous le flux continu (h142, THEORIE_ETAT §7.14, RAPPORT §162).
//
// LE MODÈLE
// ---------
// Fibonacci retardé additif r_i = r_{i−K} + r_{i−L} mod 2^32, sortie x_i = r_i >> 1 (la glibc
// random(), shift 1), lu à pas S constant sous le FLUX CONTINU : le tirage t lit les mots
// x_{S·t + k}, k = 0..19 (fy) ou 0..78 (shuffle), l'état r_0..r_{L−1} étant les L premières
// positions de la seule suite qui traverse toute l'archive. Deux échantillonneurs, comme
// lfg_soft_wht : fy (j = k + x mod (80 − k), résidu (v − 1 − k) mod 2 pour v ≥ k + 1) et
// shuffle (mot k ↔ case 79 − k, résidu (v − 1) mod 2 pour v ≤ 80 − k). Le bit 0 de x est le
// PLAN 1 de r ; chaque mot pair k = 0, 2, …, 18 en livre un bit MOU t = (n0 − n1)/n (moyenne a
// posteriori de (−1)^{bit} sur l'ensemble trié : n0 numéros admissibles de résidu pair, n1 impair).
//
// L'IDÉE (§7.14)
// --------------
// Le plan 0 est linéaire dans les L bits p de l'état bas : p0_i = <α_i, p>, α_i = α_{i−K} ⊕ α_{i−L}.
// Le plan 1 est linéaire dans y (le plan 1 de l'état) et QUADRATIQUE en p :
//     r1_i = <α_i, y> ⊕ <α'_i, p> ⊕ e2(α_i ∧ p),   α'_i = α'_{i−K} ⊕ α'_{i−L} ⊕ (α_{i−K} ∧ α_{i−L}),
// (a_i = α_i + 2α'_i est la ligne i de la transition sur Z/4 ; e2 = deuxième fonction symétrique
// élémentaire mod 2, la retenue de la somme des bits). Pour TROIS positions observées a, b, c avec
// α_a ⊕ α_b ⊕ α_c = 0 (x^a + x^b + x^c ≡ 0 mod x^L + x^K + 1 : b − a = d, c − a = Z(d), le log de
// Zech de d), la partie en y DISPARAÎT :
//     r1_a ⊕ r1_b ⊕ r1_c = <β, p> ⊕ maj(<α_a,p>, <α_b,p>, <α_c,p>),
//     β = α'_a ⊕ α'_b ⊕ α'_c ⊕ maj(α_a, α_b, α_c)   (bit à bit),
// et (−1)^{maj(x,y,z)} = ½[(−1)^x + (−1)^y + (−1)^z − 1] quand x ⊕ y ⊕ z = 0 : le signe prédit d'une
// relation est une somme de QUATRE caractères de p. La statistique
//     Λ(p) = Σ_R u_R · ε_R(p),   u_R = t_a t_b t_c,   ε_R(p) = (−1)^{r1_a ⊕ r1_b ⊕ r1_c prédit}
// s'obtient pour les 2^L états par UNE transformée de Walsh–Hadamard : Λ = WHT(g),
//     g[β ⊕ α_a] += u/2,  g[β ⊕ α_b] += u/2,  g[β ⊕ α_c] += u/2,  g[β] −= u/2.
// Sous H0 (archive sans rapport avec l'hypothèse) E[t] = 0 exactement (symétrie v ↔ v ± 1 des
// classes admissibles, de cardinal pair), les tirages sont indépendants, et deux relations de
// triples de tirages DISTINCTS sont non corrélées : Var Λ(p) = V = Σ_R τ0²(k_a) τ0²(k_b) τ0²(k_c)
// pour TOUT p (τ0²(k) = E[t²] au mot k, calibré par Monte-Carlo). z(p) = Λ/√V est de variance 1 ;
// seuil Z1 = Q⁻¹(10⁻⁷/2^L) (borne d'union). Pour l'état vrai E[t (−1)^{r1}] = E[t²] = τ0² (moyenne a
// posteriori), donc E Λ(p_vrai) = V et z_attendu = √V ≈ τ³ √M. Une seule relation par triple de
// tirages (les dix bits mous d'un tirage sont corrélés à 0,9 : la famille des relations décalées
// d'un mot dans les mêmes trois tirages ne porte qu'une mesure — on garde celle dont un mot est 0).
// Les relations : pour j = 1..span−1, d = log⁻¹(α_j ⊕ 1) < j (table de hachage des α_d) donne le
// triple (a, a + d, a + j) pour tout a tel que les trois positions soient observées.
// Ce que cela atteint : TYPE_3 (3, 31) à shift 1 sous le flux (2^62 par l'énumération : hors de
// portée de lfg_soft_wht), M ≈ 2–6·10^6 relations, z_attendu ≈ 15–25 contre un maximum de bruit
// √(2 ln 2^31) = 6,6 ; et tous les trinômes de degré 15..31. Par NUIT (204 tirages) M ≈ 10^-3 :
// rien — cohérent avec le §7.13.
// L > CB (28) : la WHT de 2^L est faite par morceaux de 2^CB (bits hauts h de g fixés) :
// Λ(p_haut, p_bas) = Σ_h (−1)^{<h, p_haut>} WHT_CB(g_h)(p_bas). Plutôt que de recalculer les 2^{L−CB}
// WHT partielles pour chaque p_haut (4^{L−CB} WHT), on les combine de façon INCOHÉRENTE :
// χ²(p_bas) = Σ_h WHT_CB(g_h)(p_bas)² ne dépend pas de p_haut et vaut, au p_bas vrai, une χ² non
// centrale de paramètre z² (chaque terme porte z²/2^{L−CB}) contre une χ² centrale à 2^{L−CB} degrés
// ailleurs ; les NCAND (256) meilleurs p_bas sont ensuite évalués EXACTEMENT pour tous les p_haut (une
// passe sur les relations par candidat). Coût : 2^{L−CB} WHT de 2^CB (8 pour L = 31) au lieu de 64. Le
// maximum sur ce sous-ensemble est ≤ celui sur 2^L : le seuil Z1 reste conservatif ; la puissance est
// celle du classement χ² (le p_bas vrai est dans les 256 premiers avec probabilité ≈ 1 dès z ≥ Z1 + 1).
//
// LE PLAN SUIVANT. p connu, r1_i ⊕ <α'_i, p> ⊕ e2(α_i ∧ p) = <α_i, y> est LINÉAIRE en y : une WHT des
// 10 N mots (poids t_i, signe corrigé) donne y avec z_y = Λ_y/√Σ t_i² d'espérance √Σ τ0² ≈ 0,66 √N
// (94 pour 20 000 tirages, 175 pour l'archive) — la confirmation est bien plus forte que la détection.
// Avec p = 0 la même WHT est le test du PLAN 0 à décalage 0 (sortie x = r, plan linéaire) : zlin, plin.
// Une sortie à décalage 0 se voit aussi dans les relations (p̂ = 0 : aucune retenue). Cohérence : mots
// dont la classe de résidu prédite par (p, y) est vide (0 pour l'état vrai).
//
// USAGE
// -----
//   lfg_rel3_flux K L S fy|shuffle fichier [Mmax]
//        fichier : un tirage par ligne, vingt numéros 1..80 (flux : un seul bloc, tout le fichier)
//        Mmax    : plafond de relations gardées (défaut 20 000 000)
//        sortie  : CALIB mode tau0² des dix mots ; RELATIONS K L S mode paires brutes M z_attendu Z1 ;
//                  FLUX M Z1 zmax pmax(hex) z2 direct(zmax recalculée sans WHT) rang_chi(rang χ² de
//                  p_bas, L > CB) zy zy_bas y contradictions zlin plin ; FIN K L S mode M zmax zlin
//                  detecte(zmax ≥ Z1) detecte_lin(zlin ≥ Z1) sec
//   lfg_rel3_flux --selftest-flux K L S fy|shuffle N graine [Mmax]
//        plante un état (32 bits) sur N tirages, décode, puis N tirages aléatoires ; VERITE shift p_true
//        y_true z_true zmax pmax ok zy y_ok contradictions zlin ok_lin detecte detecte_lin identifie ;
//        NUL zmax zy zlin faux_positif ; AUTOTEST … shift plantes detectes identifies nuls Z1
//        faux_positifs sec. LFG_SHIFT=0 plante une sortie x = r (le plan 0 est observé : detecte_lin).
//   Environnement : SWEEP_THREADS (2), WHT_CB (28), WHT_CAND (256), LFG_SHIFT (1, autotest).
//
//   cc -O3 -march=native -pthread -o lfg_rel3_flux tools/lfg_rel3_flux.c -lm

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#include <pthread.h>
#include <sys/time.h>

#define POOL  80
#define DRAWN 20
#define NWM   10
static const int WK[NWM] = {0, 2, 4, 6, 8, 10, 12, 14, 16, 18};
#define MAXL 31
#define ECH  16384.0                         // u/2 en entier : 2^14 (|u| ≤ 1)

static int K, L, S, MODE, N, NTHR = 2, CB = 28;
static int *ENS;                              // N × 20
static float *TS;                             // N × NWM : bits mous
static double TAU0[NWM], E0M[NWM];
static uint32_t *AL, *AP;                     // α, α' aux positions 0..SPAN−1
static int SPAN;
static uint32_t *RA, *RB, *RC; static int64_t M; // relations (positions)
static double V;                              // variance nulle de Λ

static double now(void) { struct timeval tv; gettimeofday(&tv, NULL); return tv.tv_sec + 1e-6 * tv.tv_usec; }
static double qinv(double q) {                // quantile gaussien supérieur
    double lo = 0, hi = 40;
    for (int it = 0; it < 200; it++) { double m = (lo + hi) / 2; if (0.5 * erfc(m / sqrt(2)) > q) lo = m; else hi = m; }
    return lo;
}
static inline int par(uint32_t x) { return __builtin_parity(x); }
static inline int e2(uint32_t x) { return (__builtin_popcount(x) >> 1) & 1; }

// ----------------------------------------------------------------- bits mous
static void bits_mous(const int *ens, float *ts) {
    for (int m = 0; m < NWM; m++) {
        int k = WK[m], n0 = 0, n1 = 0;
        for (int q = 0; q < DRAWN; q++) {
            int v = ens[q], rho;
            if (MODE == 0) { if (v < k + 1) continue; rho = (v - 1 - k) & 1; }
            else           { if (v > POOL - k) continue; rho = (v - 1) & 1; }
            if (rho) n1++; else n0++;
        }
        ts[m] = (n0 + n1) ? (float)(n0 - n1) / (n0 + n1) : 0.f;
    }
}

static uint64_t rng_s = 0x9E3779B97F4A7C15ull;
static uint32_t rnd(void) { rng_s ^= rng_s << 13; rng_s ^= rng_s >> 7; rng_s ^= rng_s << 17; return (uint32_t)(rng_s >> 11); }

static void tirage_nul(int *ens) {
    int arr[POOL];
    for (int q = 0; q < POOL; q++) arr[q] = q + 1;
    for (int i = POOL - 1; i >= 1; i--) { int j = rnd() % (i + 1); int tmp = arr[i]; arr[i] = arr[j]; arr[j] = tmp; }
    for (int q = 0; q < DRAWN; q++) ens[q] = arr[q];
}

#define NCAL 400000
static void calibre(void) {
    uint64_t sauve = rng_s; rng_s = 0xD1B54A32D192ED03ull;
    double s2[NWM] = {0}, s1[NWM] = {0}; int ens[DRAWN]; float ts[NWM];
    for (int it = 0; it < NCAL; it++) {
        tirage_nul(ens); bits_mous(ens, ts);
        for (int m = 0; m < NWM; m++) { s2[m] += (double)ts[m] * ts[m]; s1[m] += ts[m]; }
    }
    printf("CALIB %s tau0²", MODE ? "shuffle" : "fy");
    for (int m = 0; m < NWM; m++) { TAU0[m] = s2[m] / NCAL; E0M[m] = s1[m] / NCAL; printf(" %.4f", TAU0[m]); }
    printf(" E0max %.4f\n", fmax(fabs(E0M[0]), fabs(E0M[NWM - 1])));
    rng_s = sauve;
}

// ----------------------------------------------------------------- α, α'
static void precalc_alpha(void) {
    SPAN = S * (N - 1) + POOL + L;
    AL = malloc(sizeof(uint32_t) * (size_t)SPAN); AP = calloc((size_t)SPAN, sizeof(uint32_t));
    for (int i = 0; i < SPAN; i++) {
        if (i < L) { AL[i] = 1u << i; AP[i] = 0; }
        else { AL[i] = AL[i - K] ^ AL[i - L]; AP[i] = AP[i - K] ^ AP[i - L] ^ (AL[i - K] & AL[i - L]); }
    }
}

static inline int mot_de(int i) {           // indice du mot pair observé à la position i, ou −1
    if (i < 0 || i >= SPAN) return -1;
    int t = i / S, k = i - S * t;
    if (t >= N || k > 18 || (k & 1)) return -1;
    return k >> 1;
}

// ----------------------------------------------------------------- table de hachage α_d → d
static uint32_t *HK; static int32_t *HV; static uint32_t HMASK;
static inline uint32_t hh(uint32_t x) { x *= 0x9E3779B1u; return x ^ (x >> 15); }
static void hash_build(void) {
    uint32_t n = 1; while (n < 4u * (uint32_t)SPAN) n <<= 1;
    HMASK = n - 1; HK = malloc(sizeof(uint32_t) * n); HV = malloc(sizeof(int32_t) * n);
    for (uint32_t i = 0; i < n; i++) HV[i] = -1;
    for (int d = 1; d < SPAN; d++) {
        uint32_t h = hh(AL[d]) & HMASK;
        while (HV[h] >= 0) h = (h + 1) & HMASK;
        HK[h] = AL[d]; HV[h] = d;
    }
}
static inline int hash_get(uint32_t x) {
    uint32_t h = hh(x) & HMASK;
    while (HV[h] >= 0) { if (HK[h] == x) return HV[h]; h = (h + 1) & HMASK; }
    return -1;
}

// ----------------------------------------------------------------- ensemble des triples de tirages
static uint64_t *TK; static uint64_t TMASK; static int64_t TN;
static void tri_build(int64_t cap) {
    uint64_t n = 1; while (n < 2 * (uint64_t)cap + 16) n <<= 1;
    TMASK = n - 1; TK = malloc(sizeof(uint64_t) * n); memset(TK, 0xff, sizeof(uint64_t) * n); TN = 0;
}
static inline int tri_add(uint64_t key) {   // 1 si nouveau
    uint64_t h = (key * 0x9E3779B97F4A7C15ull) >> 20; h &= TMASK;
    while (TK[h] != ~0ull) { if (TK[h] == key) return 0; h = (h + 1) & TMASK; }
    TK[h] = key; TN++; return 1;
}

// ----------------------------------------------------------------- les relations
static int64_t NPAIRES, MBRUT;
static void relations(int64_t mmax) {
    hash_build();
    RA = malloc(sizeof(uint32_t) * (size_t)mmax); RB = malloc(sizeof(uint32_t) * (size_t)mmax); RC = malloc(sizeof(uint32_t) * (size_t)mmax);
    tri_build(mmax);
    M = 0; NPAIRES = 0; MBRUT = 0;
    for (int j = 1; j < SPAN && M < mmax; j++) {
        int d = hash_get(AL[j] ^ 1u);
        if (d <= 0 || d >= j) continue;       // triple canonique (a, a + d, a + j), 0 < d < j
        NPAIRES++;
        for (int a = 0; a + j < SPAN && M < mmax; a++) {
            int ma = mot_de(a); if (ma < 0) continue;
            int mb = mot_de(a + d); if (mb < 0) continue;
            int mc = mot_de(a + j); if (mc < 0) continue;
            int ta = a / S, tb = (a + d) / S, tc = (a + j) / S;
            if (ta == tb || ta == tc || tb == tc) continue;
            MBRUT++;
            if (ma && mb && mc) continue;     // famille décalée d'un mot : on garde celle qui touche le mot 0
            int u = ta, v = tb, w = tc, tmp;
            if (u > v) { tmp = u; u = v; v = tmp; } if (v > w) { tmp = v; v = w; w = tmp; } if (u > v) { tmp = u; u = v; v = tmp; }
            uint64_t key = ((uint64_t)u << 42) | ((uint64_t)v << 21) | (uint64_t)w;
            if (!tri_add(key)) continue;
            RA[M] = a; RB[M] = a + d; RC[M] = a + j; M++;
        }
    }
    free(TK); free(HK); free(HV);
    V = 0;
    for (int64_t r = 0; r < M; r++) V += TAU0[mot_de(RA[r])] * TAU0[mot_de(RB[r])] * TAU0[mot_de(RC[r])];
}

// ----------------------------------------------------------------- WHT (int32, pthreads)
typedef struct { int32_t *f; int64_t n; int h0, h1; int64_t lo, hi; } WArg;
static void *wht_stages(void *arg) {           // étages h0..h1 (h = 1 << e) sur les blocs de [lo, hi)
    WArg *w = arg;
    for (int e = w->h0; e < w->h1; e++) {
        int64_t h = (int64_t)1 << e;
        for (int64_t i = w->lo; i < w->hi; i += 2 * h) {
            int32_t *x = w->f + i, *y = w->f + i + h;
            for (int64_t j = 0; j < h; j++) { int32_t u = x[j], v = y[j]; x[j] = u + v; y[j] = u - v; }
        }
    }
    return NULL;
}
static void *wht_split(void *arg) {            // un étage h ≥ taille de segment : la boucle j partagée
    WArg *w = arg; int64_t h = (int64_t)1 << w->h0;
    for (int64_t i = 0; i < w->n; i += 2 * h) {
        int32_t *x = w->f + i, *y = w->f + i + h;
        for (int64_t j = w->lo; j < w->hi; j++) { int32_t u = x[j], v = y[j]; x[j] = u + v; y[j] = u - v; }
    }
    return NULL;
}
static void fwht(int32_t *f, int lb) {
    int64_t n = (int64_t)1 << lb;
    int nt = 1; while (2 * nt <= NTHR && ((int64_t)nt * 2) * 8 <= n) nt *= 2;
    int lt = 0; while ((1 << lt) < nt) lt++;
    int ls = lb - lt;                              // segments de 2^ls
    pthread_t th[64]; WArg wa[64];
    for (int q = 0; q < nt; q++) { wa[q] = (WArg){f, n, 0, ls, (int64_t)q << ls, (int64_t)(q + 1) << ls}; pthread_create(&th[q], NULL, wht_stages, &wa[q]); }
    for (int q = 0; q < nt; q++) pthread_join(th[q], NULL);
    for (int e = ls; e < lb; e++) {
        int64_t h = (int64_t)1 << e, part = h / nt;
        for (int q = 0; q < nt; q++) { wa[q] = (WArg){f, n, e, e + 1, q * part, (q + 1) * part}; pthread_create(&th[q], NULL, wht_split, &wa[q]); }
        for (int q = 0; q < nt; q++) pthread_join(th[q], NULL);
    }
}

// ----------------------------------------------------------------- Λ pour tous les états
static inline double u_reel(int64_t r) {
    int a = RA[r], b = RB[r], c = RC[r];
    return (double)TS[(a / S) * NWM + mot_de(a)] * TS[(b / S) * NWM + mot_de(b)] * TS[(c / S) * NWM + mot_de(c)];
}
static inline int32_t u_de(int64_t r) { return (int32_t)lrint(u_reel(r) * ECH / 2); }   // u/2 à l'échelle
static inline uint32_t beta_de(int64_t r) {
    uint32_t aa = AL[RA[r]], ab = AL[RB[r]], ac = AL[RC[r]];
    return AP[RA[r]] ^ AP[RB[r]] ^ AP[RC[r]] ^ ((aa & ab) | (aa & ac) | (ab & ac));
}
static void accumule(int32_t *g, int lb, uint32_t haut) {   // g[w & (2^lb − 1)] pour les w de bits hauts `haut`
    memset(g, 0, sizeof(int32_t) << lb);
    uint32_t mask = ((uint32_t)1 << lb) - 1;
    for (int64_t r = 0; r < M; r++) {
        int32_t u2 = u_de(r); if (!u2) continue;
        uint32_t aa = AL[RA[r]], ab = AL[RB[r]], ac = AL[RC[r]], beta = beta_de(r), w;
        w = beta ^ aa; if ((w >> lb) == haut) g[w & mask] += u2;
        w = beta ^ ab; if ((w >> lb) == haut) g[w & mask] += u2;
        w = beta ^ ac; if ((w >> lb) == haut) g[w & mask] += u2;
        w = beta;      if ((w >> lb) == haut) g[w & mask] -= u2;
    }
}

static double lambda_direct(uint32_t p) {
    double l = 0;
    for (int64_t r = 0; r < M; r++) {
        uint32_t aa = AL[RA[r]], ab = AL[RB[r]], ac = AL[RC[r]], beta = beta_de(r);
        int xa = par(aa & p), xb = par(ab & p), xc = par(ac & p);
        int bit = par(beta & p) ^ ((xa & xb) | (xa & xc) | (xb & xc));
        double u = u_reel(r);
        l += bit ? -u : u;
    }
    return l;
}

// Λ(p_haut · 2^lb + p_bas) pour les 2^{L−lb} valeurs de p_haut, en une passe sur les relations.
// Les signes des 2^{L−lb} ≤ 2^16 valeurs sont traités en parallèle bit à bit : WS[x] = Σ_h <x, h> 2^h
// (motif de Walsh des bits hauts x), le bit prédit de chaque p_haut est un mot de 2^{L−lb} bits, et l'on
// histogramme u par motif (2^{2^{L−lb}} cases : 256 pour L − lb = 3) avant de replier sur les p_haut.
static uint32_t *WS; static int WS_N;
static void lambda_hauts(uint32_t pbas, int lb, double *out) {
    int nh = 1 << (L - lb); uint32_t mask = ((uint32_t)1 << lb) - 1;
    for (int h = 0; h < nh; h++) out[h] = 0;
    if (nh > 16) {                                   // chemin lent (L − lb > 4)
        for (int64_t r = 0; r < M; r++) {
            double u = u_reel(r); if (u == 0) continue;
            uint32_t aa = AL[RA[r]], ab = AL[RB[r]], ac = AL[RC[r]], beta = beta_de(r);
            int xa = par(aa & mask & pbas), xb = par(ab & mask & pbas), xc = par(ac & mask & pbas), xg = par(beta & mask & pbas);
            uint32_t ha = aa >> lb, hb = ab >> lb, hc = ac >> lb, hg = beta >> lb;
            for (int h = 0; h < nh; h++) {
                int ya = xa ^ par(ha & (uint32_t)h), yb = xb ^ par(hb & (uint32_t)h), yc = xc ^ par(hc & (uint32_t)h);
                int bit = xg ^ par(hg & (uint32_t)h) ^ ((ya & yb) | (ya & yc) | (yb & yc));
                out[h] += bit ? -u : u;
            }
        }
        return;
    }
    if (WS_N != nh) { free(WS); WS = malloc(sizeof(uint32_t) * nh); WS_N = nh;
        for (int x = 0; x < nh; x++) { uint32_t m = 0; for (int h = 0; h < nh; h++) m |= (uint32_t)par((uint32_t)(x & h)) << h; WS[x] = m; } }
    uint32_t full = nh == 32 ? ~0u : ((1u << nh) - 1);
    size_t nmot = (size_t)1 << nh; double *hist = calloc(nmot, sizeof(double));
    for (int64_t r = 0; r < M; r++) {
        double u = u_reel(r); if (u == 0) continue;
        uint32_t aa = AL[RA[r]], ab = AL[RB[r]], ac = AL[RC[r]], beta = beta_de(r);
        uint32_t ya = WS[aa >> lb] ^ (par(aa & mask & pbas) ? full : 0), yb = WS[ab >> lb] ^ (par(ab & mask & pbas) ? full : 0);
        uint32_t yc = WS[ac >> lb] ^ (par(ac & mask & pbas) ? full : 0), yg = WS[beta >> lb] ^ (par(beta & mask & pbas) ? full : 0);
        uint32_t bits = yg ^ ((ya & yb) | (ya & yc) | (yb & yc));
        hist[bits] += u;
    }
    for (size_t m = 0; m < nmot; m++) if (hist[m] != 0)
        for (int h = 0; h < nh; h++) out[h] += ((m >> h) & 1) ? -hist[m] : hist[m];
    free(hist);
}

typedef struct { int64_t c1, c2; uint32_t p1, p2; } Top2;
static void top2_push(Top2 *t, int64_t c, uint32_t p) {
    if (c > t->c1) { t->c2 = t->c1; t->p2 = t->p1; t->c1 = c; t->p1 = p; } else if (c > t->c2) { t->c2 = c; t->p2 = p; }
}

// Λ(p) sur les 2^L états (à l'échelle 2^14), top 2.
// L ≤ CB : une WHT exacte. L > CB : les 2^{L−CB} WHT partielles WHT_CB(g_h) (bits hauts h de g fixés) sont
// combinées de façon INCOHÉRENTE, χ²(p_bas) = Σ_h WHT_CB(g_h)(p_bas)², qui ne dépend pas de p_haut
// (Λ(p_haut, p_bas) = Σ_h (−1)^{<h,p_haut>} WHT_CB(g_h)(p_bas) : pour le p_bas vrai les 2^{L−CB} termes
// portent chacun z²/2^{L−CB} de signal, χ² non centrale de paramètre z²) ; les NCAND meilleurs p_bas sont
// ensuite évalués EXACTEMENT pour tous les p_haut (une passe sur les relations par candidat). Le maximum
// sur ce sous-ensemble est ≤ celui sur 2^L : le seuil Z1 reste conservatif ; la puissance est celle du
// classement χ² (p_bas vrai parmi les NCAND premiers : ≈ 1 dès que z ≥ Z1 + 1).
static int NCAND = 256;
static void balaye(Top2 *top, int *rang_chi) {
    top->c1 = top->c2 = INT64_MIN; top->p1 = top->p2 = 0; *rang_chi = 0;
    if (L <= CB) {
        int32_t *g = malloc(sizeof(int32_t) << L);
        accumule(g, L, 0); fwht(g, L);
        for (int64_t i = 0; i < ((int64_t)1 << L); i++) top2_push(top, g[i], (uint32_t)i);
        free(g); return;
    }
    int lb = CB, nh = 1 << (L - lb); int64_t n = (int64_t)1 << lb;
    int32_t *g = malloc(sizeof(int32_t) * (size_t)n); float *chi = calloc((size_t)n, sizeof(float));
    for (int h = 0; h < nh; h++) {
        accumule(g, lb, (uint32_t)h); fwht(g, lb);
        for (int64_t i = 0; i < n; i++) { float v = (float)(g[i] / ECH); chi[i] += v * v; }
    }
    free(g);
    float *cv = malloc(sizeof(float) * NCAND); uint32_t *ci = malloc(sizeof(uint32_t) * NCAND); int nc = 0;
    for (int64_t i = 0; i < n; i++) {
        float v = chi[i];
        if (nc == NCAND && v <= cv[nc - 1]) continue;
        int k = nc < NCAND ? nc++ : nc - 1;
        while (k > 0 && cv[k - 1] < v) { cv[k] = cv[k - 1]; ci[k] = ci[k - 1]; k--; }
        cv[k] = v; ci[k] = (uint32_t)i;
    }
    free(chi);
    double *out = malloc(sizeof(double) * nh);
    for (int c = 0; c < nc; c++) {
        lambda_hauts(ci[c], lb, out);
        for (int h = 0; h < nh; h++) top2_push(top, llrint(out[h] * ECH), ((uint32_t)h << lb) | ci[c]);
    }
    uint32_t mask = ((uint32_t)1 << lb) - 1;
    for (int c = 0; c < nc; c++) if (ci[c] == (top->p1 & mask)) { *rang_chi = c; break; }
    free(out); free(cv); free(ci);
}

// ----------------------------------------------------------------- le plan suivant : y (ou le plan 0 linéaire)
// Λ_y(y) = Σ_i s_i (−1)^{<α_i, y>} sur les 10 N mots observés, s_i = t_i (−1)^{<α'_i, p> ⊕ e2(α_i ∧ p)} :
// p connu, r1_i ⊕ c_i(p) = <α_i, y> est LINÉAIRE en y, une WHT des mots suffit ; z_y = Λ_y/√Σ t_i²
// (variance nulle exacte, conditionnelle aux |t_i|), E z_y = √Σ τ0² ≈ 0,66 √N. Avec p = 0 c'est le test
// du plan 0 à décalage 0 (sortie x = r). L > CB : y_bas par la WHT des mots dont α a ses bits hauts nuls
// (un mot sur 2^{L−CB}, z encore ≈ 0,66 √(N/2^{L−CB})), puis y_haut par la WHT de taille 2^{L−CB} des
// sommes de signes par valeur des bits hauts.
#define ECHY 1024.0
static inline double s_mot(int t, int m, uint32_t p) {
    int i = S * t + WK[m]; double ts = TS[t * NWM + m];
    return (par(AP[i] & p) ^ e2(AL[i] & p)) ? -ts : ts;
}
static double resout_plan(uint32_t p, uint32_t *y_out, double *z_bas) {
    int lb = L <= CB ? L : CB; int nh = 1 << (L - lb); uint32_t mask = ((uint32_t)1 << lb) - 1;
    int64_t n = (int64_t)1 << lb;
    int32_t *g = calloc((size_t)n, sizeof(int32_t)); double vbas = 0;
    for (int t = 0; t < N; t++) for (int m = 0; m < NWM; m++) {
        int i = S * t + WK[m]; double ts = TS[t * NWM + m]; if (ts == 0 || (AL[i] >> lb) != 0) continue;
        g[AL[i] & mask] += (int32_t)lrint(s_mot(t, m, p) * ECHY); vbas += ts * ts;
    }
    fwht(g, lb);
    Top2 top = {INT64_MIN, INT64_MIN, 0, 0};
    for (int64_t i = 0; i < n; i++) top2_push(&top, g[i], (uint32_t)i);
    free(g);
    uint32_t y = top.p1; *z_bas = vbas > 0 ? top.c1 / ECHY / sqrt(vbas) : 0;
    if (nh > 1) {
        double *lh = calloc((size_t)nh, sizeof(double));
        for (int t = 0; t < N; t++) for (int m = 0; m < NWM; m++) {
            int i = S * t + WK[m]; uint32_t h = AL[i] >> lb; if (h == 0) continue;
            double s = s_mot(t, m, p); lh[h] += par(AL[i] & y) ? -s : s;
        }
        double best = -1e300; uint32_t yh_best = 0;
        for (uint32_t yh = 0; yh < (uint32_t)nh; yh++) {
            double v = 0; for (uint32_t h = 1; h < (uint32_t)nh; h++) v += par(h & yh) ? -lh[h] : lh[h];
            if (v > best) { best = v; yh_best = yh; }
        }
        y |= yh_best << lb; free(lh);
    }
    double lam = 0, var = 0;
    for (int t = 0; t < N; t++) for (int m = 0; m < NWM; m++) {
        int i = S * t + WK[m]; double ts = TS[t * NWM + m], s = s_mot(t, m, p);
        lam += par(AL[i] & y) ? -s : s; var += ts * ts;
    }
    *y_out = y; return var > 0 ? lam / sqrt(var) : 0;
}
static int coherence(uint32_t p, uint32_t y) {          // mots dont la classe prédite est vide
    int contra = 0;
    for (int t = 0; t < N; t++) for (int m = 0; m < NWM; m++) {
        int i = S * t + WK[m]; int bit = par(AL[i] & y) ^ par(AP[i] & p) ^ e2(AL[i] & p);
        int k = WK[m], n0 = 0, n1 = 0;
        for (int q = 0; q < DRAWN; q++) {
            int v = ENS[t * DRAWN + q], rho;
            if (MODE == 0) { if (v < k + 1) continue; rho = (v - 1 - k) & 1; }
            else           { if (v > POOL - k) continue; rho = (v - 1) & 1; }
            if (rho) n1++; else n0++;
        }
        if ((bit ? n1 : n0) == 0) contra++;
    }
    return contra;
}

// ----------------------------------------------------------------- décodage d'un fichier de tirages
static void charge_ts(void) {
    TS = malloc(sizeof(float) * (size_t)N * NWM);
    for (int t = 0; t < N; t++) bits_mous(ENS + (size_t)t * DRAWN, TS + (size_t)t * NWM);
}
typedef struct { uint32_t pmax, y, plin; double zmax, z2, direct, zy, zy_bas, zlin, zlin_bas; int rang_chi, contra; } Res;
static void decode(const char *etiq, Res *r) {
    Top2 top; balaye(&top, &r->rang_chi);
    r->pmax = top.p1; r->zmax = top.c1 / ECH / sqrt(V); r->z2 = top.c2 / ECH / sqrt(V);
    r->direct = lambda_direct(top.p1) / sqrt(V);
    r->zy = resout_plan(top.p1, &r->y, &r->zy_bas); r->contra = coherence(top.p1, r->y);
    r->zlin = resout_plan(0, &r->plin, &r->zlin_bas);
    printf("%s M=%lld Z1=%.2f zmax=%.2f pmax=%#x z2=%.2f direct=%.2f rang_chi=%d zy=%.2f zy_bas=%.2f y=%#x contradictions=%d zlin=%.2f plin=%#x\n",
           etiq, (long long)M, qinv(1e-7 / ldexp(1, L)), r->zmax, r->pmax, r->z2, r->direct, r->rang_chi, r->zy, r->zy_bas, r->y, r->contra, r->zlin, r->plin);
}

// ----------------------------------------------------------------- autotest
static int SHIFT = 1;                          // LFG_SHIFT : sortie x = r >> SHIFT dans l'autotest
static void genere(const uint32_t *init, int *ens, int n) {
    int npos = S * (n - 1) + POOL + L;
    uint32_t *r = malloc(sizeof(uint32_t) * npos);
    for (int i = 0; i < npos; i++) r[i] = i < L ? init[i] : r[i - K] + r[i - L];
    for (int t = 0; t < n; t++) {
        int arr[POOL];
        for (int q = 0; q < POOL; q++) arr[q] = q + 1;
        if (MODE == 0) {
            for (int k = 0; k < DRAWN; k++) { int j = k + (int)((r[S * t + k] >> SHIFT) % (POOL - k)); int tmp = arr[k]; arr[k] = arr[j]; arr[j] = tmp; ens[t * DRAWN + k] = arr[k]; }
        } else {
            for (int i = POOL - 1; i >= 1; i--) { int k = POOL - 1 - i; int j = (int)((r[S * t + k] >> SHIFT) % (i + 1)); int tmp = arr[i]; arr[i] = arr[j]; arr[j] = tmp; }
            for (int q = 0; q < DRAWN; q++) ens[t * DRAWN + q] = arr[POOL - DRAWN + q];
        }
    }
    free(r);
}
static uint32_t plan_de(const uint32_t *init, int q) { uint32_t p = 0; for (int j = 0; j < L; j++) p |= ((init[j] >> q) & 1u) << j; return p; }

static void selftest(int n, uint64_t graine, int64_t mmax) {
    double t0 = now(); rng_s = graine * 0x2545F4914F6CDD1Dull + 0x9E3779B97F4A7C15ull;
    N = n; ENS = malloc(sizeof(int) * (size_t)N * DRAWN);
    uint32_t init[MAXL]; for (int j = 0; j < L; j++) init[j] = rnd();
    uint32_t p_true = plan_de(init, 0), y_true = plan_de(init, 1);   // plans 0 et 1 de l'état
    calibre(); precalc_alpha(); relations(mmax);
    double Z1 = qinv(1e-7 / ldexp(1, L));
    printf("RELATIONS %d %d %d %s paires=%lld brutes=%lld M=%lld z_attendu=%.2f Z1=%.2f\n", K, L, S, MODE ? "shuffle" : "fy",
           (long long)NPAIRES, (long long)MBRUT, (long long)M, sqrt(V), Z1);
    // planté : à SHIFT 1 le plan observé est le plan 1 (relations → p, puis y) ; à SHIFT 0 c'est le plan 0,
    // linéaire : zlin doit le trouver (plin = p_true), et les relations donnent p = 0 (aucune retenue)
    genere(init, ENS, N); charge_ts();
    double z_true = lambda_direct(SHIFT ? p_true : 0) / sqrt(V);
    Res r; decode("FLUX", &r);
    int det = r.zmax >= Z1, det_lin = r.zlin >= Z1, ok, y_ok, ident;
    if (SHIFT) { ok = r.pmax == p_true; y_ok = r.y == y_true; }
    else       { ok = r.pmax == 0;      y_ok = r.y == p_true; }
    int ok_lin = r.plin == p_true;
    ident = SHIFT ? (ok && y_ok && r.contra == 0) : (ok_lin && r.contra == 0);
    printf("VERITE shift=%d p_true=%#x y_true=%#x z_true=%.2f zmax=%.2f pmax=%#x ok=%d zy=%.2f y_ok=%d contradictions=%d zlin=%.2f ok_lin=%d detecte=%d detecte_lin=%d identifie=%d\n",
           SHIFT, p_true, y_true, z_true, r.zmax, r.pmax, ok, r.zy, y_ok, r.contra, r.zlin, ok_lin, det, det_lin, ident);
    // nul
    for (int t = 0; t < N; t++) tirage_nul(ENS + (size_t)t * DRAWN);
    free(TS); charge_ts();
    Res rn; decode("FLUX", &rn);
    int fp = rn.zmax >= Z1 || rn.zlin >= Z1;
    printf("NUL zmax=%.2f zy=%.2f zlin=%.2f faux_positif=%d\n", rn.zmax, rn.zy, rn.zlin, fp);
    printf("AUTOTEST %d %d %d %s shift=%d plantes=1 detectes=%d identifies=%d nuls=1 Z1=%.2f faux_positifs=%d sec=%.1f\n",
           K, L, S, MODE ? "shuffle" : "fy", SHIFT, SHIFT ? det : det_lin, ident, Z1, fp, now() - t0);
}

// ----------------------------------------------------------------- main
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

int main(int argc, char **argv) {
    const char *e = getenv("SWEEP_THREADS"); if (e) NTHR = atoi(e);
    e = getenv("WHT_CB"); if (e) CB = atoi(e);
    e = getenv("WHT_CAND"); if (e) NCAND = atoi(e);
    e = getenv("LFG_SHIFT"); if (e) SHIFT = atoi(e);
    if (argc >= 8 && !strcmp(argv[1], "--selftest-flux")) {
        K = atoi(argv[2]); L = atoi(argv[3]); S = atoi(argv[4]); MODE = !strcmp(argv[5], "shuffle");
        int n = atoi(argv[6]); uint64_t graine = strtoull(argv[7], NULL, 10);
        int64_t mmax = argc >= 9 ? atoll(argv[8]) : 20000000;
        if (L < 2 || L > MAXL || K <= 0 || K >= L || CB < 8) { fprintf(stderr, "K, L, CB invalides\n"); return 2; }
        selftest(n, graine, mmax); return 0;
    }
    if (argc < 6) { fprintf(stderr, "usage : lfg_rel3_flux K L S fy|shuffle fichier [Mmax] | --selftest-flux K L S fy|shuffle N graine [Mmax]\n"); return 2; }
    K = atoi(argv[1]); L = atoi(argv[2]); S = atoi(argv[3]); MODE = !strcmp(argv[4], "shuffle");
    int64_t mmax = argc >= 7 ? atoll(argv[6]) : 20000000;
    if (L < 2 || L > MAXL || K <= 0 || K >= L || CB < 8) { fprintf(stderr, "K, L, CB invalides\n"); return 2; }
    double t0 = now();
    lit_archive(argv[5]);
    calibre(); precalc_alpha(); relations(mmax);
    double Z1 = qinv(1e-7 / ldexp(1, L));
    printf("RELATIONS %d %d %d %s paires=%lld brutes=%lld M=%lld z_attendu=%.2f Z1=%.2f\n", K, L, S, MODE ? "shuffle" : "fy",
           (long long)NPAIRES, (long long)MBRUT, (long long)M, sqrt(V), Z1);
    charge_ts();
    Res r = {0};
    if (M > 0) decode("FLUX", &r);
    else { r.zlin = resout_plan(0, &r.plin, &r.zlin_bas); printf("FLUX M=0 zlin=%.2f plin=%#x\n", r.zlin, r.plin); }
    printf("FIN %d %d %d %s M=%lld zmax=%.2f zlin=%.2f detecte=%d detecte_lin=%d sec=%.1f\n", K, L, S, MODE ? "shuffle" : "fy",
           (long long)M, r.zmax, r.zlin, r.zmax >= Z1, r.zlin >= Z1, now() - t0);
    return 0;
}
