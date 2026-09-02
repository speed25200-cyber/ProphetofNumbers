// lfg_flux_continu — le crible du FLUX CONTINU (h137, §157).
//
// LE MODÈLE
// ---------
// Fibonacci retardé additif r_i = r_{i−K} + r_{i−L} mod 2^32, sortie x_i = r_i >> shift
// (shift 1 : la glibc random() ; shift 0 : sortie brute), UN SEUL flux à pas S
// constant à travers toute l'archive — pauses nocturnes comprises : le tirage
// t lit les mots x_{S·t + k}. Deux lectures des masques :
//   fy       Fisher-Yates partiel par modulo, j = k + x mod (80 − k) :
//            résidu permis (v − 1 − k) mod 2^e pour tout v ≥ k + 1 de l'ensemble
//   shuffle  Collections.shuffle lu sur ses vingt DERNIÈRES cases, mot k ↔ i = 79 − k,
//            j = x mod (80 − k) : résidu permis (v − 1) mod 2^e pour tout v ≤ 80 − k
// Les deux sont SÛRES (un numéro déplacé a déjà été tiré : sa case d'origine est
// dans l'ensemble). Mots lus : k = 0, 4, 8, 12, 16, e = v2(80 − k) = 4, 2, 3, 2, 6.
//
// L'ALGÈBRE (THEORIE_ETAT §7.11)
// ------------------------------
// Le plan 0 de r est ÉNUMÉRÉ (2^L hypothèses, par blocs de 64 en tranches de bits).
// Le plan 1 est affine dans les L bits y du plan 1 initial : p1_i = <α_i, y> ⊕ δ_i ;
// le plan 2 est affine en z et quadratique en y : p2_i = <α_i, z> ⊕ Q_i(y). Un masque
// donne des ÉVÉNEMENTS « si x_i mod 2 = a alors le bit 1 vaut f » et « la parité a est
// morte ». Avec shift 1 (x bit 0 = p1, x bit 1 = p2) le premier s'écrit
// (p1_i ⊕ a ⊕ 1)(p2_i ⊕ f) = 0 — cubique en y, linéaire en z — et il est LINÉARISÉ
// sur les monômes {y, z, yy, yz, yyy, 1} (M = 2L + C(L,2) + L² + C(L,3) + 1 :
// 816 pour L = 15, 1140 pour L = 17). Gauss incrémental ; une hypothèse de plan 0
// fausse meurt par contradiction après ≈ rang + 2 équations (mesuré : 117/220 à
// L = 9, 710/816 à L = 15, 1003/1140 à L = 17, la mort à rang + 1..3).
// Un survivant livre y (les colonnes y sont les plus basses : triangulaire), puis
// les plans 2..5+shift sont RELEVÉS numériquement (le plan p est affine dans ses
// L bits initiaux, retenues exactes), et l'état bas est vérifié par simulation.
// Avec shift 0 (x bit 0 = p0) la parité est connue : mort → p0_i ≠ a ; force →
// <α_i, y> ⊕ δ_i = f, linéaire ; puis le même relèvement.
//
// USAGE
// -----
//   lfg_flux_continu K L S fy|shuffle shift fichier [ndraws]
//        fichier : un tirage par ligne, vingt numéros 1..80
//        sortie  : SURVIVANT K L S mode shift r_0..r_{L−1} (mod 2^{6+shift}) — une ligne
//                  par état bas compatible ; puis
//                  BAS K L S mode shift hyps= survivants= indecis= evenements= rang_max= s=
//   lfg_flux_continu --selftest K L S fy|shuffle shift N graine
//        plante un état de 32 bits, fabrique N tirages, crible : l'état planté doit
//        être LE survivant ; puis N ensembles aléatoires : rien.
//   SWEEP_THREADS fixe le nombre de fils (4 par défaut).
//
//   cc -O3 -march=native -pthread -o lfg_flux_continu tools/lfg_flux_continu.c

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <pthread.h>
#include <time.h>
#include <sys/time.h>

#define POOL  80
#define DRAWN 20
#define NWM   5                        // mots lus par tirage
static const int WK[NWM] = {0, 4, 8, 12, 16};
static const int WE[NWM] = {4, 2, 3, 2, 6};
#define MAXL     24
#define FREE_CAP 12                    // au-delà de 2^12 solutions libres : indécis
#define CHUNK    2000                  // tirages par tranche (Gauss incrémental)
#define MAXSURV  4096

static int K, L, S, SHIFT, MODE, N, NPOS, PMAX;
static uint64_t *MASK;                 // N × NWM
static uint32_t *ALPHA;                // NPOS
static int NBFILS = 4;
static int KIDX[POOL];                 // k -> indice de mot lu, ou -1

// ----------------------------------------------------------------- horloge
static double now(void) {
    struct timeval tv; gettimeofday(&tv, NULL);
    return tv.tv_sec + 1e-6 * tv.tv_usec;
}

// ----------------------------------------------------------------- masques
static uint64_t masque(const int *ens, int m) {
    int k = WK[m], e = WE[m];
    uint64_t mk = 0;
    for (int q = 0; q < DRAWN; q++) {
        int v = ens[q];
        if (MODE == 0) { if (v >= k + 1) mk |= 1ull << ((v - 1 - k) & ((1 << e) - 1)); }
        else           { if (v <= POOL - k) mk |= 1ull << ((v - 1) & ((1 << e) - 1)); }
    }
    return mk;
}

// ----------------------------------------------------------------- événements
typedef struct { int pos, m, type, a, f; } Ev;   // type 0 mort, 1 force
static Ev *EV; static int NE;

static void evenements(void) {
    EV = malloc(sizeof(Ev) * (size_t)N * NWM * 2);
    NE = 0;
    for (int t = 0; t < N; t++)
        for (int m = 0; m < NWM; m++) {
            uint64_t mk = MASK[(size_t)t * NWM + m];
            int e = WE[m];
            for (int a = 0; a < 2; a++) {
                int n = 0, b0 = 0, b1 = 0;
                for (int rho = a; rho < (1 << e); rho += 2)
                    if ((mk >> rho) & 1) { n++; if ((rho >> 1) & 1) b1 = 1; else b0 = 1; }
                if (n == 0) { EV[NE++] = (Ev){S * t + WK[m], m, 0, a, 0}; }
                else if (!(b0 && b1)) { EV[NE++] = (Ev){S * t + WK[m], m, 1, a, b1}; }
            }
        }
}

// ----------------------------------------------------------------- colonnes
static int M, W, WT, CYY, CYZ, CYYY, C1;
static int yyidx[MAXL][MAXL], yyk[MAXL * MAXL], yyl[MAXL * MAXL];
static int *yyyidx;                    // L^3
static inline int col_yy(int j, int k) {
    if (j == k) return j;
    return CYY + (j < k ? yyidx[j][k] : yyidx[k][j]);
}
static inline int col_yyy(int j, int k, int l) {   // k < l
    if (j == k || j == l) return CYY + yyidx[k][l];
    int a = j, b = k, c = l, t;
    if (a > b) { t = a; a = b; b = t; }
    if (b > c) { t = b; b = c; c = t; }
    if (a > b) { t = a; a = b; b = t; }
    return CYYY + yyyidx[(a * L + b) * L + c];
}
static inline void setbit(uint64_t *r, int c) { r[c >> 6] ^= 1ull << (c & 63); }

static void colonnes(void) {
    int n2 = 0;
    for (int j = 0; j < L; j++)
        for (int k = j + 1; k < L; k++) { yyidx[j][k] = n2; yyk[n2] = j; yyl[n2] = k; n2++; }
    int n3 = 0;
    yyyidx = malloc(sizeof(int) * L * L * L);
    for (int j = 0; j < L; j++)
        for (int k = j + 1; k < L; k++)
            for (int l = k + 1; l < L; l++) yyyidx[(j * L + k) * L + l] = n3++;
    CYY = 2 * L; CYZ = CYY + n2; CYYY = CYZ + L * L; C1 = CYYY + n3;
    M = C1 + 1; W = (M + 63) / 64; WT = (CYZ + 63) / 64;
}

// ----------------------------------------------------------------- α et Q_yy
// données par événement, indépendantes de l'hypothèse
static uint32_t *EALPHA;               // NE
static uint64_t *EFIX1, *EFIX2, *ET;   // NE×W, NE×W, NE×L×WT

static void precalc(void) {
    ALPHA = malloc(sizeof(uint32_t) * NPOS);
    for (int i = 0; i < NPOS; i++)
        ALPHA[i] = i < L ? (1u << i) : (ALPHA[i - K] ^ ALPHA[i - L]);
    EALPHA = malloc(sizeof(uint32_t) * NE);
    for (int e = 0; e < NE; e++) EALPHA[e] = ALPHA[EV[e].pos];
    if (!SHIFT) return;
    // Q_yy par anneau
    uint64_t *ring = calloc((size_t)L * WT, 8), *qyy = calloc((size_t)NE * WT, 8);
    uint64_t *cur = malloc(8 * WT);
    int ei = 0;
    for (int i = 0; i < NPOS && ei < NE; i++) {
        int sb = i % L;
        if (i < L) memset(cur, 0, 8 * WT);
        else {
            int sa = (i - K) % L;
            for (int w = 0; w < WT; w++) cur[w] = ring[sa * WT + w] ^ ring[sb * WT + w];
            uint32_t aa = ALPHA[i - K], ab = ALPHA[i - L];
            for (uint32_t u = aa; u; u &= u - 1) {
                int j = __builtin_ctz(u);
                for (uint32_t v = ab; v; v &= v - 1) setbit(cur, col_yy(j, __builtin_ctz(v)));
            }
        }
        memcpy(ring + sb * WT, cur, 8 * WT);
        while (ei < NE && EV[ei].pos == i) { memcpy(qyy + (size_t)ei * WT, cur, 8 * WT); ei++; }
    }
    // FIX1, FIX2, T
    EFIX1 = calloc((size_t)NE * W, 8); EFIX2 = calloc((size_t)NE * W, 8);
    ET = calloc((size_t)NE * L * WT, 8);
    for (int e = 0; e < NE; e++) {
        if (EV[e].type == 0) continue;
        uint32_t al = EALPHA[e]; int f = EV[e].f;
        uint64_t *q = qyy + (size_t)e * WT, *f1 = EFIX1 + (size_t)e * W, *f2 = EFIX2 + (size_t)e * W;
        // FIX1 = α sur z ⊕ Q_yy ⊕ f
        for (uint32_t u = al; u; u &= u - 1) setbit(f1, L + __builtin_ctz(u));
        for (int w = 0; w < WT; w++) f1[w] ^= q[w];
        if (f) setbit(f1, C1);
        // T[k] = Σ_{j∈α} yy(j,k)
        for (int k = 0; k < L; k++) {
            uint64_t *tk = ET + ((size_t)e * L + k) * WT;
            for (uint32_t u = al; u; u &= u - 1) setbit(tk, col_yy(__builtin_ctz(u), k));
        }
        // FIX2 = Σ_{j∈α} [ Σ_{k∈α} yz(j,k) ⊕ Σ_{y_k∈Q} yy(j,k) ⊕ Σ_{yy_kl∈Q} yyy(j,k,l) ⊕ f·y_j ]
        for (uint32_t u = al; u; u &= u - 1) {
            int j = __builtin_ctz(u);
            for (uint32_t v = al; v; v &= v - 1) setbit(f2, CYZ + j * L + __builtin_ctz(v));
            for (int c = 0; c < CYZ; c++) {
                if (!((q[c >> 6] >> (c & 63)) & 1)) continue;
                if (c < L) setbit(f2, col_yy(j, c));
                else { int p = c - CYY; setbit(f2, col_yyy(j, yyk[p], yyl[p])); }
            }
            if (f) setbit(f2, j);
        }
    }
    free(ring); free(qyy); free(cur);
}

// ----------------------------------------------------------------- relèvement numérique
static pthread_mutex_t LOCK = PTHREAD_MUTEX_INITIALIZER;
static int NSURV = 0, NINDECIS = 0, RANGMAX = 0;
static uint32_t SURV[MAXSURV][MAXL];

static inline uint64_t plie(uint64_t mk, int e, int u) {   // résidus mod 2^u atteints
    for (int s = e - 1; s >= u; s--) mk = (mk | (mk >> (1 << s))) & ((1ull << (1 << s)) - 1);
    return mk;
}

static int verifie(const uint32_t *low) {                  // plans 0..PMAX connus
    uint32_t ring[MAXL], mod = (1u << (PMAX + 1)) - 1;
    for (int i = 0; i < NPOS; i++) {
        int sb = i % L;
        uint32_t r = i < L ? (low[i] & mod) : ((ring[(i - K) % L] + ring[sb]) & mod);
        ring[sb] = r;
        int t = i / S, k = i - S * t, m = k < POOL ? KIDX[k] : -1;
        if (m < 0 || t >= N) continue;
        uint32_t x = (r >> SHIFT) & ((1u << WE[m]) - 1);
        if (!((MASK[(size_t)t * NWM + m] >> x) & 1)) return 0;
    }
    return 1;
}

static void sortie(const uint32_t *low) {
    pthread_mutex_lock(&LOCK);
    if (NSURV < MAXSURV) memcpy(SURV[NSURV], low, sizeof(uint32_t) * L);
    NSURV++;
    printf("SURVIVANT %d %d %d %s %d", K, L, S, MODE ? "shuffle" : "fy", SHIFT);
    for (int j = 0; j < L; j++) printf(" %u", low[j]);
    printf("\n"); fflush(stdout);
    pthread_mutex_unlock(&LOCK);
}

// plans 0..p−1 connus (low[j] = r_j mod 2^p) : détermine le plan p, récurse.
static void releve(int p, const uint32_t *low) {
    uint32_t mod = (1u << p) - 1, ring[MAXL]; uint8_t gam[MAXL];
    uint32_t piv[MAXL]; uint8_t has[MAXL]; memset(has, 0, sizeof has);
    uint32_t LM = (1u << L) - 1;
    int w = p - SHIFT, rang = 0;
    for (int i = 0; i < NPOS; i++) {
        int sb = i % L; uint32_t r; uint8_t g;
        if (i < L) { r = low[i] & mod; g = 0; }
        else {
            int sa = (i - K) % L; uint32_t ra = ring[sa], rb = ring[sb];
            r = (ra + rb) & mod; g = gam[sa] ^ gam[sb] ^ (uint8_t)(((ra + rb) >> p) & 1);
        }
        ring[sb] = r; gam[sb] = g;
        int t = i / S, k = i - S * t, m = k < POOL ? KIDX[k] : -1;
        if (m < 0 || t >= N || w >= WE[m]) continue;
        uint64_t fold = plie(MASK[(size_t)t * NWM + m], WE[m], w + 1);
        uint32_t rho = (r >> SHIFT) & ((1u << w) - 1);
        int b0 = (fold >> rho) & 1, b1 = (fold >> (rho | (1u << w))) & 1;
        if (!b0 && !b1) return;
        if (b0 == b1) continue;
        uint32_t row = ALPHA[i] | ((uint32_t)(b1 ^ g) << L);
        for (;;) {
            uint32_t mono = row & LM;
            if (!mono) { if (row >> L) return; break; }
            int h = 31 - __builtin_clz(mono);
            if (has[h]) row ^= piv[h]; else { piv[h] = row; has[h] = 1; rang++; break; }
        }
    }
    int libre = L - rang;
    if (libre > FREE_CAP) { pthread_mutex_lock(&LOCK); NINDECIS++; pthread_mutex_unlock(&LOCK); return; }
    // forme réduite
    for (int h = 0; h < L; h++) if (has[h])
        for (int g2 = h + 1; g2 < L; g2++) if (has[g2] && ((piv[g2] >> h) & 1)) piv[g2] ^= piv[h];
    int fr[MAXL], nf = 0;
    for (int h = 0; h < L; h++) if (!has[h]) fr[nf++] = h;
    for (uint32_t c = 0; c < (1u << nf); c++) {
        uint32_t wp = 0;
        for (int q = 0; q < nf; q++) if ((c >> q) & 1) wp |= 1u << fr[q];
        for (int h = 0; h < L; h++) if (has[h]) {
            uint32_t b = piv[h] >> L;
            for (int q = 0; q < nf; q++) if (((c >> q) & 1) && ((piv[h] >> fr[q]) & 1)) b ^= 1;
            wp |= (b & 1) << h;
        }
        uint32_t nlow[MAXL];
        for (int j = 0; j < L; j++) nlow[j] = low[j] | (((wp >> j) & 1) << p);
        if (p == PMAX) { if (verifie(nlow)) sortie(nlow); }
        else releve(p + 1, nlow);
    }
}

// ----------------------------------------------------------------- crible par blocs de 64
typedef struct {
    uint64_t P0[MAXL], DEL[MAXL], QY[MAXL][MAXL], QC[MAXL];      // anneaux (tranches)
    uint64_t *P0E, *DELE, *QYE, *QCE;                             // aux événements
    uint64_t *PIV; uint8_t *HAS; int rank[64]; uint8_t dead[64];
    uint32_t piv0[64][MAXL]; uint8_t has0[64][MAXL];             // shift 0
    uint64_t *row;
    int rangmax;
} Th;

static const uint64_t PAT[6] = {0xAAAAAAAAAAAAAAAAull, 0xCCCCCCCCCCCCCCCCull, 0xF0F0F0F0F0F0F0F0ull,
                                0xFF00FF00FF00FF00ull, 0xFFFF0000FFFF0000ull, 0xFFFFFFFF00000000ull};

static void flux(Th *th, uint64_t base, int i0, int i1, int *ei) {
    for (int i = i0; i < i1; i++) {
        int sb = i % L;
        uint64_t p0n, deln, qcn = 0, qyn[MAXL];
        if (i < L) {
            p0n = i < 6 ? PAT[i] : (((base >> i) & 1) ? ~0ull : 0ull);
            deln = 0;
            if (SHIFT) memset(qyn, 0, sizeof(uint64_t) * L);
        } else {
            int sa = (i - K) % L;
            uint64_t p0a = th->P0[sa], p0b = th->P0[sb], c1 = p0a & p0b;
            uint64_t dela = th->DEL[sa], delb = th->DEL[sb];
            p0n = p0a ^ p0b; deln = dela ^ delb ^ c1;
            if (SHIFT) {
                uint32_t aa = ALPHA[i - K], ab = ALPHA[i - L], ax = aa ^ ab;
                for (int j = 0; j < L; j++)
                    qyn[j] = th->QY[sa][j] ^ th->QY[sb][j] ^ (((aa >> j) & 1) ? delb : 0)
                             ^ (((ab >> j) & 1) ? dela : 0) ^ (((ax >> j) & 1) ? c1 : 0);
                qcn = th->QC[sa] ^ th->QC[sb] ^ (dela & delb) ^ (c1 & (dela ^ delb));
            }
        }
        th->P0[sb] = p0n; th->DEL[sb] = deln;
        if (SHIFT) { memcpy(th->QY[sb], qyn, sizeof(uint64_t) * L); th->QC[sb] = qcn; }
        while (*ei < NE && EV[*ei].pos == i) {
            th->P0E[*ei] = p0n; th->DELE[*ei] = deln;
            if (SHIFT) { memcpy(th->QYE + (size_t)*ei * L, qyn, sizeof(uint64_t) * L); th->QCE[*ei] = qcn; }
            (*ei)++;
        }
    }
}

// Gauss sur les événements [e0, e1) pour l'hypothèse b du bloc (shift 1)
static void gauss1(Th *th, int b, int e0, int e1) {
    uint64_t *piv = th->PIV + (size_t)b * M * W, *row = th->row;
    uint8_t *has = th->HAS + (size_t)b * M;
    uint64_t topmask = (C1 & 63) ? ((1ull << (C1 & 63)) - 1) : 0;   // colonnes < C1 dans le mot W−1
    int wc = C1 >> 6; uint64_t cbit = 1ull << (C1 & 63);
    for (int e = e0; e < e1; e++) {
        const Ev *ev = &EV[e];
        int del = (th->DELE[e] >> b) & 1;
        if (ev->type == 0) {
            memset(row, 0, 8 * W);
            row[0] = EALPHA[e];
            if (del ^ 1 ^ ev->a) row[wc] ^= cbit;
        } else {
            memcpy(row, EFIX2 + (size_t)e * W, 8 * W);
            uint32_t qy = 0;
            const uint64_t *qye = th->QYE + (size_t)e * L;
            for (int j = 0; j < L; j++) qy |= (uint32_t)((qye[j] >> b) & 1) << j;
            int qc = (th->QCE[e] >> b) & 1;
            for (uint32_t u = qy; u; u &= u - 1) {
                const uint64_t *tk = ET + ((size_t)e * L + __builtin_ctz(u)) * WT;
                for (int w = 0; w < WT; w++) row[w] ^= tk[w];
            }
            if (qc) row[0] ^= EALPHA[e];
            if (del ^ ev->a ^ 1) {
                const uint64_t *f1 = EFIX1 + (size_t)e * W;
                for (int w = 0; w < W; w++) row[w] ^= f1[w];
                row[0] ^= qy;
                if (qc) row[wc] ^= cbit;
            }
        }
        for (;;) {
            int h = -1;
            for (int w = W - 1; w >= 0; w--) {
                uint64_t v = row[w];
                if (w == wc) v &= topmask;
                if (v) { h = w * 64 + 63 - __builtin_clzll(v); break; }
            }
            if (h < 0) { if ((row[wc] >> (C1 & 63)) & 1) th->dead[b] = 1; break; }
            if (has[h]) { const uint64_t *pv = piv + (size_t)h * W; for (int w = 0; w < W; w++) row[w] ^= pv[w]; }
            else { memcpy(piv + (size_t)h * W, row, 8 * W); has[h] = 1; th->rank[b]++; break; }
        }
        if (th->dead[b]) return;
    }
}

// shift 0 : mort → p0_i ≠ a ; force avec p0_i = a → <α, y> ⊕ δ = f
static void gauss0(Th *th, int b, int e0, int e1) {
    uint32_t LM = (1u << L) - 1;
    for (int e = e0; e < e1; e++) {
        const Ev *ev = &EV[e];
        int p0 = (th->P0E[e] >> b) & 1, del = (th->DELE[e] >> b) & 1;
        if (ev->type == 0) { if (p0 == ev->a) { th->dead[b] = 1; return; } continue; }
        if (p0 != ev->a) continue;
        uint32_t row = EALPHA[e] | ((uint32_t)(del ^ ev->f) << L);
        for (;;) {
            uint32_t mono = row & LM;
            if (!mono) { if (row >> L) { th->dead[b] = 1; return; } break; }
            int h = 31 - __builtin_clz(mono);
            if (th->has0[b][h]) row ^= th->piv0[b][h];
            else { th->piv0[b][h] = row; th->has0[b][h] = 1; th->rank[b]++; break; }
        }
    }
}

// lecture de y pour un survivant (shift 1) : colonnes y triangulaires, puis relèvement
static void survivant1(Th *th, int b, uint64_t hyp) {
    uint64_t *piv = th->PIV + (size_t)b * M * W; uint8_t *has = th->HAS + (size_t)b * M;
    int fr[MAXL], nf = 0;
    for (int j = 0; j < L; j++) if (!has[j]) fr[nf++] = j;
    if (nf > FREE_CAP) { pthread_mutex_lock(&LOCK); NINDECIS++; pthread_mutex_unlock(&LOCK); return; }
    for (uint32_t c = 0; c < (1u << nf); c++) {
        uint32_t y = 0;
        for (int q = 0; q < nf; q++) if ((c >> q) & 1) y |= 1u << fr[q];
        for (int j = 0; j < L; j++) if (has[j]) {
            const uint64_t *pv = piv + (size_t)j * W;
            uint32_t bit = (pv[C1 >> 6] >> (C1 & 63)) & 1;
            uint32_t lowbits = (uint32_t)(pv[0] & ((1ull << j) - 1));
            bit ^= __builtin_popcount(lowbits & y) & 1;
            y |= bit << j;
        }
        uint32_t low[MAXL];
        for (int j = 0; j < L; j++) low[j] = (uint32_t)((hyp >> j) & 1) | (((y >> j) & 1) << 1);
        releve(2, low);
    }
}

static void survivant0(Th *th, int b, uint64_t hyp) {
    uint32_t *piv = th->piv0[b]; uint8_t *has = th->has0[b];
    for (int h = 0; h < L; h++) if (has[h])
        for (int g2 = h + 1; g2 < L; g2++) if (has[g2] && ((piv[g2] >> h) & 1)) piv[g2] ^= piv[h];
    int fr[MAXL], nf = 0;
    for (int h = 0; h < L; h++) if (!has[h]) fr[nf++] = h;
    if (nf > FREE_CAP) { pthread_mutex_lock(&LOCK); NINDECIS++; pthread_mutex_unlock(&LOCK); return; }
    for (uint32_t c = 0; c < (1u << nf); c++) {
        uint32_t y = 0;
        for (int q = 0; q < nf; q++) if ((c >> q) & 1) y |= 1u << fr[q];
        for (int h = 0; h < L; h++) if (has[h]) {
            uint32_t bt = piv[h] >> L;
            for (int q = 0; q < nf; q++) if (((c >> q) & 1) && ((piv[h] >> fr[q]) & 1)) bt ^= 1;
            y |= (bt & 1) << h;
        }
        uint32_t low[MAXL];
        for (int j = 0; j < L; j++) low[j] = (uint32_t)((hyp >> j) & 1) | (((y >> j) & 1) << 1);
        releve(2, low);
    }
}

static uint64_t NBLOCS, NEXT = 0;

static void *fil(void *arg) {
    Th *th = calloc(1, sizeof(Th));
    th->P0E = malloc(8 * (size_t)NE); th->DELE = malloc(8 * (size_t)NE);
    if (SHIFT) {
        th->QYE = malloc(8 * (size_t)NE * L); th->QCE = malloc(8 * (size_t)NE);
        th->PIV = malloc(8 * (size_t)64 * M * W); th->HAS = malloc((size_t)64 * M);
        th->row = malloc(8 * W);
    }
    uint64_t nhyp = 1ull << L;
    for (;;) {
        uint64_t blk = __sync_fetch_and_add(&NEXT, 1);
        if (blk >= NBLOCS) break;
        uint64_t base = blk * 64;
        int nb = nhyp - base < 64 ? (int)(nhyp - base) : 64;
        memset(th->rank, 0, sizeof th->rank); memset(th->dead, 0, sizeof th->dead);
        if (SHIFT) memset(th->HAS, 0, (size_t)64 * M); else memset(th->has0, 0, sizeof th->has0);
        int ei = 0, edone = 0, pos = 0, vivants = nb;
        for (int t0 = 0; t0 < N && vivants; t0 += CHUNK) {
            int t1 = t0 + CHUNK < N ? t0 + CHUNK : N;
            int p1 = t1 < N ? S * t1 : NPOS;
            flux(th, base, pos, p1, &ei); pos = p1;
            for (int b = 0; b < nb; b++) {
                if (th->dead[b]) continue;
                if (SHIFT) gauss1(th, b, edone, ei); else gauss0(th, b, edone, ei);
                if (th->dead[b]) vivants--;
            }
            edone = ei;
        }
        for (int b = 0; b < nb; b++) {
            if (th->rank[b] > th->rangmax) th->rangmax = th->rank[b];
            if (th->dead[b]) continue;
            if (SHIFT) survivant1(th, b, base + b); else survivant0(th, b, base + b);
        }
    }
    pthread_mutex_lock(&LOCK);
    if (th->rangmax > RANGMAX) RANGMAX = th->rangmax;
    pthread_mutex_unlock(&LOCK);
    return NULL;
}

static void crible(void) {
    NPOS = S * (N - 1) + DRAWN;
    for (int k = 0; k < POOL; k++) KIDX[k] = -1;
    for (int m = 0; m < NWM; m++) KIDX[WK[m]] = m;
    PMAX = 5 + SHIFT;
    evenements(); colonnes(); precalc();
    NSURV = 0; NINDECIS = 0; RANGMAX = 0; NEXT = 0;
    NBLOCS = ((1ull << L) + 63) / 64;
    double t0 = now();
    pthread_t th[64];
    int nf = NBFILS < 64 ? NBFILS : 64;
    for (int i = 0; i < nf; i++) pthread_create(&th[i], NULL, fil, NULL);
    for (int i = 0; i < nf; i++) pthread_join(th[i], NULL);
    printf("BAS %d %d %d %s %d hyps=%llu survivants=%d indecis=%d evenements=%d M=%d rang_max=%d s=%.1f\n",
           K, L, S, MODE ? "shuffle" : "fy", SHIFT, 1ull << L, NSURV, NINDECIS, NE, M, RANGMAX, now() - t0);
    fflush(stdout);
    free(EV); free(ALPHA); free(EALPHA); free(yyyidx);
    if (SHIFT) { free(EFIX1); free(EFIX2); free(ET); }
}

// ----------------------------------------------------------------- autotest
static uint64_t rng_s = 0x9E3779B97F4A7C15ull;
static uint32_t rnd(void) {
    rng_s ^= rng_s << 13; rng_s ^= rng_s >> 7; rng_s ^= rng_s << 17;
    return (uint32_t)(rng_s >> 11);
}

static void genere(const uint32_t *init, int *ens) {          // ens : N × 20
    int npos = S * (N - 1) + POOL + L;
    uint32_t *r = malloc(sizeof(uint32_t) * npos);
    for (int i = 0; i < npos; i++) r[i] = i < L ? init[i] : r[i - K] + r[i - L];
    for (int t = 0; t < N; t++) {
        int arr[POOL];
        for (int q = 0; q < POOL; q++) arr[q] = q + 1;
        if (MODE == 0) {
            for (int k = 0; k < DRAWN; k++) {
                int j = k + (int)((r[S * t + k] >> SHIFT) % (POOL - k));
                int tmp = arr[k]; arr[k] = arr[j]; arr[j] = tmp;
                ens[t * DRAWN + k] = arr[k];
            }
        } else {
            for (int i = POOL - 1; i >= 1; i--) {
                int k = POOL - 1 - i;
                int j = (int)((r[S * t + k] >> SHIFT) % (i + 1));
                int tmp = arr[i]; arr[i] = arr[j]; arr[j] = tmp;
            }
            for (int q = 0; q < DRAWN; q++) ens[t * DRAWN + q] = arr[POOL - DRAWN + q];
        }
    }
    free(r);
}

static void masques_de(const int *ens) {
    MASK = malloc(8 * (size_t)N * NWM);
    for (int t = 0; t < N; t++)
        for (int m = 0; m < NWM; m++) MASK[(size_t)t * NWM + m] = masque(ens + t * DRAWN, m);
}

static int selftest(int n, uint64_t graine) {
    N = n; rng_s ^= graine * 0x2545F4914F6CDD1Dull; for (int i = 0; i < 8; i++) rnd();
    uint32_t init[MAXL];
    for (int j = 0; j < L; j++) init[j] = rnd();
    int *ens = malloc(sizeof(int) * N * DRAWN);
    genere(init, ens); masques_de(ens);
    printf("autotest K=%d L=%d S=%d %s shift=%d N=%d : etat plante", K, L, S, MODE ? "shuffle" : "fy", SHIFT, N);
    uint32_t mod = (1u << (6 + SHIFT)) - 1;
    for (int j = 0; j < L; j++) printf(" %u", init[j] & mod);
    printf("\n"); fflush(stdout);
    crible();
    int trouve = 0;
    for (int s = 0; s < NSURV && s < MAXSURV; s++) {
        int ok = 1;
        for (int j = 0; j < L; j++) if (SURV[s][j] != (init[j] & mod)) ok = 0;
        if (ok) trouve = 1;
    }
    int ok1 = trouve && NSURV == 1 && NINDECIS == 0;
    printf("  plante : %s, %d survivant(s), %d indecis -> %s\n", trouve ? "RETROUVE" : "ABSENT", NSURV, NINDECIS,
           ok1 ? "ok" : "ECHEC");
    free(MASK);
    // contrôle : ensembles aléatoires
    for (int t = 0; t < N; t++) {
        int arr[POOL];
        for (int q = 0; q < POOL; q++) arr[q] = q + 1;
        for (int k = 0; k < DRAWN; k++) {
            int j = k + rnd() % (POOL - k);
            int tmp = arr[k]; arr[k] = arr[j]; arr[j] = tmp;
            ens[t * DRAWN + k] = arr[k];
        }
    }
    masques_de(ens);
    crible();
    int ok2 = NSURV == 0 && NINDECIS == 0;
    printf("  controle aleatoire : %d survivant(s), %d indecis -> %s\n", NSURV, NINDECIS, ok2 ? "ok" : "ECHEC");
    printf("AUTOTEST %s\n", (ok1 && ok2) ? "OK" : "ECHEC");
    free(MASK); free(ens);
    return ok1 && ok2;
}

// ----------------------------------------------------------------- main
static int lit_mode(const char *s) {
    if (!strcmp(s, "fy")) return 0;
    if (!strcmp(s, "shuffle")) return 1;
    fprintf(stderr, "masques : fy | shuffle\n"); exit(2);
}

int main(int argc, char **argv) {
    if (getenv("SWEEP_THREADS")) NBFILS = atoi(getenv("SWEEP_THREADS"));
    if (argc >= 2 && !strcmp(argv[1], "--selftest")) {
        if (argc < 9) { fprintf(stderr, "--selftest K L S fy|shuffle shift N graine\n"); return 2; }
        K = atoi(argv[2]); L = atoi(argv[3]); S = atoi(argv[4]); MODE = lit_mode(argv[5]);
        SHIFT = atoi(argv[6]);
        if (L < 2 || L > MAXL || K < 1 || K >= L || S < DRAWN) { fprintf(stderr, "design\n"); return 2; }
        return selftest(atoi(argv[7]), strtoull(argv[8], NULL, 10)) ? 0 : 1;
    }
    if (argc < 7) { fprintf(stderr, "usage : K L S fy|shuffle shift fichier [ndraws]\n"); return 2; }
    K = atoi(argv[1]); L = atoi(argv[2]); S = atoi(argv[3]); MODE = lit_mode(argv[4]); SHIFT = atoi(argv[5]);
    if (L < 2 || L > MAXL || K < 1 || K >= L || S < DRAWN || SHIFT < 0 || SHIFT > 1) { fprintf(stderr, "design\n"); return 2; }
    FILE *f = fopen(argv[6], "r");
    if (!f) { perror(argv[6]); return 2; }
    int cap = 1 << 16, n = 0, *ens = malloc(sizeof(int) * cap * DRAWN);
    for (;;) {
        if (n == cap) { cap *= 2; ens = realloc(ens, sizeof(int) * (size_t)cap * DRAWN); }
        int q;
        for (q = 0; q < DRAWN; q++) if (fscanf(f, "%d", &ens[n * DRAWN + q]) != 1) break;
        if (q < DRAWN) break;
        n++;
    }
    fclose(f);
    if (argc >= 8 && atoi(argv[7]) > 0 && atoi(argv[7]) < n) n = atoi(argv[7]);
    N = n;
    masques_de(ens);
    crible();
    free(MASK); free(ens);
    return 0;
}
