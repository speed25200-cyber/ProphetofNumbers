// lfg_soft_wht — le DÉCODAGE MOU des plans bas sur l'archive triée (h140, §160).
//
// LE MODÈLE
// ---------
// Fibonacci retardé additif r_i = r_{i−K} + r_{i−L} mod 2^32, sortie x_i = r_i >> shift
// (shift 1 : la glibc random() ; shift 0 : sortie brute), lu à pas S constant : le
// tirage t d'un BLOC lit les mots x_{S·t + k}, l'état r_0..r_{L−1} étant celui du
// début du bloc. Un bloc = une journée (réamorçage journalier) ou toute l'archive
// (flux continu, un seul bloc). Deux échantillonneurs, comme lfg_flux_continu :
//   fy       Fisher-Yates partiel par modulo, j = k + x mod (80 − k) :
//            résidu permis (v − 1 − k) mod 2^e pour tout v ≥ k + 1 de l'ensemble
//   shuffle  Collections.shuffle lu sur ses vingt DERNIÈRES cases, mot k ↔ i = 79 − k,
//            j = x mod (80 − k) : résidu permis (v − 1) mod 2^e pour tout v ≤ 80 − k
// Les deux sont SÛRS (le vrai résidu est toujours dans le masque).
//
// L'IDÉE (THEORIE_ETAT §7.13)
// ---------------------------
// Les cribles exacts (§7.11) ne lisent un bit qu'aux ÉVÉNEMENTS (0,06 par tirage :
// une classe de parité absente du masque). Ici CHAQUE mot pair (k = 0, 2, …, 18,
// e = v2(80 − k) ≥ 1 : dix mots par tirage) livre un BIT MOU : parmi les n numéros
// de l'ensemble admissibles au mot k, n0 ont un résidu pair et n1 un résidu impair ;
// le vrai résidu est l'un d'eux, donc P(bit 0 de x pair) ≈ n0/n, soit un poids
// w = ln((n0 + ½)/(n1 + ½)) (rapport de vraisemblance, ±∞ tronqué aux événements).
// Le bit 0 de x est le plan `shift` de r. Le plan 0 est LINÉAIRE dans les L bits p
// de l'état bas : p0_i = <α_i, p> ; le plan 1 est affine en y, de constante
// δ_i(p) : p1_i = <α_i, y> ⊕ δ_i(p).
//
// UNE OBSERVATION PAR TIRAGE (le modèle scalaire, §7.13). Les dix poids d'un tirage
// sont corrélés à 0,88–0,99 (ils lisent tous le même déséquilibre pair/impair de
// l'ensemble) : les traiter comme dix mesures indépendantes (score « plain »
// C = Σ w (−1)^bit, z = C/√Σw²) donne une variance nulle qui DÉPEND de l'état (×9,5
// pour un état dont les dix bits d'un tirage sont égaux) : faux positifs et fausses
// identifications. Le modèle sain : le tirage t livre UNE mesure
//     y_t = moyenne des dix poids − E0,   y_t | B_t ~ (μ B_t, σ1²),
//     B_t(état) = Σ_k (−1)^{bit_tk}  ∈ {−10, …, 10}  (somme des dix bits du plan),
// E[y_t] = 0 sous H0 par la symétrie v ↔ v ± 1 (les dix mots pairs partagent la
// parité de v − 1). μ, σ0² = Var_0 y, σ1² = σ0² − μ² E[B²] sont CALIBRÉS par Monte-Carlo
// au lancement (ligne CALIB). Pour un état p :
//     Λ(p) = Σ_t y_t B_t(p)      Q(p) = Σ_t B_t(p)²      z(p) = Λ/√(σ0² Q)
//     R(p) = Λ − (μ/2) Q  ∝  log-vraisemblance gaussienne (le CLASSEMENT),
// z est de variance EXACTEMENT 1 sous H0 pour tout état (le test), R sélectionne
// (le vrai état a le plus grand R en espérance, pas le plus grand z : un état de
// grand Q se paye). Détection : z de l'état de R maximal ≥ Z1 = Q⁻¹(10⁻⁷/2^nbits)
// (sain : z(sélectionné) ≤ max z). Tout s'obtient POUR TOUS LES ÉTATS par deux
// transformées de Walsh–Hadamard : Λ(p) = WHT(f)(p), f[a] += ±y_t sur les mots
// (α_i = a) ; Q(p) = 10·n + 2·WHT(g)(p), g[a ⊕ a'] += ±1 sur les paires de mots d'un
// même tirage (2^L points, 2^L·L opérations chacune).
//   shift 0 : deux WHT par bloc ; L > 24 : WHT À POSITIONS FIXÉES, les f = L − b
//             observations les plus fiables (vecteurs α indépendants) fixent f bits,
//             chaque motif d'erreur sur ces f décisions dures laisse un sous-espace
//             affine de 2^b états balayé par deux WHT de 2^b ; les motifs sont
//             parcourus par vraisemblance décroissante jusqu'à couvrir la masse
//             WHT_COUV (0,95) des erreurs possibles — ou jusqu'au premier état de
//             R maximal de score z ≥ WHT_ZSTOP (un vrai état arrête le parcours tôt,
//             un bloc nul le parcourt jusqu'à la couverture) ;
//   shift 1 : les 2^L plans 0 sont ÉNUMÉRÉS (64 à la fois, en tranches de bits,
//             δ_i(p) par la récurrence des retenues) et pour chacun deux WHT sur y.
// z ≈ μ√(10 n)/σ0 ≈ 9,2 pour le vrai état d'un bloc de 204 tirages contre un maximum
// de bruit ≈ √(2 ln N) ≈ 6,4 sur N = 2^30 hypothèses. ÉTAPE 2 : le plan shift + 1
// (bit 1 de x aux cinq mots k ≡ 0 mod 4, e ≥ 2) est affine dans ses L bits de
// constante connue (retenues des plans décodés) : même modèle sur cinq mots (y2 =
// moyenne des cinq poids conditionnels ln((c_b + ½)/(c_{b+2} + ½)), b le bit décodé
// du plan shift, c_ρ le compte des résidus ≡ ρ mod 4 ; μ2, σ02 propres), un score z2 de
// CONFIRMATION (z2 ≈ 6,1 attendu).
// LES OMBRES (§7.13) : y_t ne voit que la somme B_t, et l'état vrai décalé de ±2, ±4
// positions (un, deux mots pairs) garde neuf, huit bits sur dix : corrélation des
// B ≈ 0,9, 0,8, donc z ≈ 0,87–0,93 · z_vrai (mesuré). Un arrêt anticipé se pose
// volontiers sur une ombre : l'état rendu est poussé au meilleur R de ses décalés
// (grimpe), et si le plan shift + 1 ne confirme pas un état détecté, ses ombres ±2, ±4
// sont confirmées à leur tour (colonne delta de la sortie).
//
// USAGE
// -----
//   lfg_soft_wht K L S fy|shuffle shift fichier blocs
//        fichier : un tirage par ligne, vingt numéros 1..80
//        blocs   : indices (0-based) des premiers tirages de chaque bloc, un par
//                  ligne ; la seule ligne « 0 » = flux continu (un bloc)
//        sortie  : CALIB mode mu1 s01 s11 e01 mu2 s02 s12 e02 s02_nul (la calibration
//                  Monte-Carlo : μ, σ0², σ1², E0 des deux étapes, unités 256·ln), puis
//                  BLOC b t0 n nobs z1 z1b meth couv plan0 plan1 plan2 z2 z2b meth2 couv2 delta
//                  — une ligne par bloc (meth : wht, ou fixe/NMOTIFS ; couv : masse
//                  d'erreur couverte, 1 pour la WHT complète ; plans en hexadécimal,
//                  « - » = non décodé ; delta : décalage d'ombre retenu par l'étape 2 ;
//                  l'étape 2 n'est faite, pour L > 24, que si z1 ≥ WHT_ZSTOP),
//                  puis FIN K L S mode shift nblocs zmax bloc_zmax sec1 sec2 sec
//   Environnement : SWEEP_THREADS (4), WHT_B (22 : dimension libre pour L > 24),
//                  WHT_COUV (0.95 ; 1 = parcours complet), WHT_ZSTOP (0 : pas d'arrêt).
//   lfg_soft_wht --selftest K L S fy|shuffle shift NB graine [n]
//        plante NB états (32 bits) de NB blocs de n (204) tirages, puis NB blocs de
//        tirages aléatoires ; décode ; VERITE b p0 p1 p2 ok1 ok2 z1_vrai R_vrai R_rendu
//        ombre z_ombres(−2,+2,−4,+4) pour les plantés (R_rendu ≥ R_vrai dès que le vrai
//        état est dans l'espace balayé — WHT complète : toujours ; positions fixées :
//        sauf si le vrai motif d'erreur est hors de la couverture),
//        NUL b pour les autres (les lignes BLOC sont imprimées aussi), puis AUTOTEST
//        … plantes etape1_ok etape2_ok nuls Z1 detectes faux_positifs.
//   lfg_soft_wht --selftest-flux K L S fy|shuffle shift N graine
//        idem avec un seul état planté sur N tirages (bloc 0) et N aléatoires (bloc 1).
//
//   cc -O3 -march=native -pthread -o lfg_soft_wht tools/lfg_soft_wht.c -lm

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#include <pthread.h>
#include <sys/time.h>

#define POOL  80
#define DRAWN 20
#define NWM   10                       // mots pairs lus par tirage
static const int WK[NWM] = {0, 2, 4, 6, 8, 10, 12, 14, 16, 18};
static const int WE[NWM] = {4, 1, 2, 1, 3, 1, 2, 1, 6, 1};
#define MAXL     31
#define WHT_MAXL 24                    // au-delà : WHT à positions fixées
static int WHT_B = 22;                 // dimension libre de la WHT à positions fixées (env WHT_B)
static double WHT_COUV = 0.95;         // masse d'erreur à couvrir sur les positions fixées (env WHT_COUV)
static double ZSTOP = 0;               // arrêt anticipé dès z ≥ ZSTOP (env WHT_ZSTOP ; 0 : jamais)
#define ECHELLE  256.0                 // poids = 256 · ln-rapport

static int K, L, S, SHIFT, MODE, N;
static int *ENS;                       // N × 20
static uint8_t *CNT;                   // N × NWM × 4 : comptes des résidus mod 4 (mod 2 si e = 1)
static int16_t *W1;                    // N × NWM : poids du plan shift
static int16_t *Y1;                    // N : moyenne (centrée) des dix poids du tirage — l'observation scalaire
static uint32_t *ALPHA;                // NPOSMAX
static int NPOSMAX, NMAXBLOC;
static int NB; static int *T0, *NBL;   // blocs : premier tirage, longueur
static int NTHR = 4;

static double now(void) {
    struct timeval tv; gettimeofday(&tv, NULL);
    return tv.tv_sec + 1e-6 * tv.tv_usec;
}

// ----------------------------------------------------------------- comptes et poids
static inline int poids(int c0, int c1) {
    return (int)lrint(ECHELLE * log((c0 + 0.5) / (c1 + 0.5)));
}

static void comptes_tirage(const int *ens, uint8_t *c) {         // c : NWM × 4
    memset(c, 0, NWM * 4);
    for (int m = 0; m < NWM; m++) {
        int k = WK[m], e = WE[m];
        for (int q = 0; q < DRAWN; q++) {
            int v = ens[q], rho;
            if (MODE == 0) { if (v < k + 1) continue; rho = (v - 1 - k) & ((1 << e) - 1); }
            else           { if (v > POOL - k) continue; rho = (v - 1) & ((1 << e) - 1); }
            c[m * 4 + (e == 1 ? (rho & 1) : (rho & 3))]++;
        }
    }
}

// ----------------------------------------------------------------- le modèle scalaire (§7.13) : calibrage
// Les dix poids d'un tirage sont corrélés 0,88–0,99 (ils partagent le déséquilibre pair/impair de
// l'ensemble) : le tirage livre UNE observation y = moyenne des poids, y | B ~ (μB, σ1²) avec
// B = Σ_k (−1)^{bit_k} (dix bits pairs du plan shift). Monte-Carlo sur des tirages de mots uniformes :
// E0 = E[y], σ0² = Var y, μ = Cov(y, B)/Var B, σ1² = σ0² − μ² Var B. Étape 2 : y2 = moyenne des cinq
// poids conditionnels (k ≡ 0 mod 4), B2 sur leurs bits 1 ; σ0² pris au plus grand de Var(y2 | bit 0 vrai)
// et Var(y2 | bit 0 tiré au hasard) (bloc nul ou plan shift faux).
static double MU[2], S0[2], S1[2], E0[2]; static int MUQ[2];   // MUQ = 128·μ (R = Λ − MUQ·Q/256, entier)
#define NCAL 400000

static void tirage_mots(const uint32_t *x, int *ens) {          // x : mots (déjà décalés) k = 0..78 du tirage
    int arr[POOL];
    for (int q = 0; q < POOL; q++) arr[q] = q + 1;
    if (MODE == 0) {
        for (int k = 0; k < DRAWN; k++) { int j = k + (int)(x[k] % (POOL - k)); int tmp = arr[k]; arr[k] = arr[j]; arr[j] = tmp; ens[k] = arr[k]; }
    } else {
        for (int i = POOL - 1; i >= 1; i--) { int k = POOL - 1 - i; int j = (int)(x[k] % (i + 1)); int tmp = arr[i]; arr[i] = arr[j]; arr[j] = tmp; }
        for (int q = 0; q < DRAWN; q++) ens[q] = arr[POOL - DRAWN + q];
    }
}

static void calibre(void) {
    uint64_t cs = 0xD1B54A32D192ED03ull;                        // générateur propre au calibrage
    double sy[3] = {0}, syy[3] = {0}, syb[2] = {0}, sbb[2] = {0}; // 0 : étape 1 ; 1 : étape 2 ; 2 : étape 2, bit 0 au hasard
    uint32_t x[POOL]; int ens[DRAWN]; uint8_t c[NWM * 4];
    for (int it = 0; it < NCAL; it++) {
        for (int k = 0; k < POOL; k++) { cs ^= cs << 13; cs ^= cs >> 7; cs ^= cs << 17; x[k] = (uint32_t)(cs >> 11); }
        tirage_mots(x, ens); comptes_tirage(ens, c);
        double y = 0, y2 = 0, y2r = 0; int B = 0, B2 = 0;
        for (int m = 0; m < NWM; m++) {
            int b0 = x[WK[m]] & 1;
            y += poids(c[m * 4 + 0] + c[m * 4 + 2], c[m * 4 + 1] + c[m * 4 + 3]); B += b0 ? -1 : 1;
            if (m % 2 == 0) {
                int b1 = (x[WK[m]] >> 1) & 1, br = (int)(cs >> (20 + m)) & 1;
                y2 += poids(c[m * 4 + b0], c[m * 4 + b0 + 2]); B2 += b1 ? -1 : 1;
                y2r += poids(c[m * 4 + br], c[m * 4 + br + 2]);
            }
        }
        y /= NWM; y2 /= NWM / 2; y2r /= NWM / 2;
        sy[0] += y; syy[0] += y * y; syb[0] += y * B; sbb[0] += B * B;
        sy[1] += y2; syy[1] += y2 * y2; syb[1] += y2 * B2; sbb[1] += B2 * B2;
        sy[2] += y2r; syy[2] += y2r * y2r;
    }
    for (int e = 0; e < 2; e++) {
        double ey = sy[e] / NCAL, vy = syy[e] / NCAL - ey * ey, vb = sbb[e] / NCAL;   // E[B] = 0
        MU[e] = (syb[e] / NCAL) / vb; E0[e] = ey; S0[e] = vy; S1[e] = vy - MU[e] * MU[e] * vb;
        MUQ[e] = (int)lrint(128 * MU[e]);
    }
    double ey = sy[2] / NCAL, vr = syy[2] / NCAL - ey * ey;
    if (vr > S0[1]) S0[1] = vr;
    printf("CALIB %s mu1=%.3f s01=%.1f s11=%.1f e01=%.2f mu2=%.3f s02=%.1f s12=%.1f e02=%.2f s02_nul=%.1f\n",
           MODE ? "shuffle" : "fy", MU[0], S0[0], S1[0], E0[0], MU[1], S0[1], S1[1], E0[1], vr);
}

static void comptes(void) {
    CNT = calloc((size_t)N * NWM * 4, 1);
    W1 = malloc(sizeof(int16_t) * (size_t)N * NWM);
    Y1 = malloc(sizeof(int16_t) * (size_t)N);
    for (int t = 0; t < N; t++) {
        uint8_t *c = CNT + (size_t)t * NWM * 4;
        comptes_tirage(ENS + (size_t)t * DRAWN, c);
        double y = 0;
        for (int m = 0; m < NWM; m++) { int w = poids(c[m * 4] + c[m * 4 + 2], c[m * 4 + 1] + c[m * 4 + 3]); W1[(size_t)t * NWM + m] = (int16_t)w; y += w; }
        Y1[t] = (int16_t)lrint(y / NWM - E0[0]);
    }
}

static void precalc_alpha(void) {
    NPOSMAX = S * (NMAXBLOC - 1) + POOL + L + 1;
    ALPHA = malloc(sizeof(uint32_t) * (size_t)NPOSMAX);
    for (int i = 0; i < NPOSMAX; i++) ALPHA[i] = i < L ? 1u << i : ALPHA[i - K] ^ ALPHA[i - L];
}

// ----------------------------------------------------------------- top 2
typedef struct { int32_t c1, c2; uint64_t s1, s2; } Top2;
static void top2_init(Top2 *t) { t->c1 = t->c2 = INT32_MIN; t->s1 = t->s2 = 0; }
static inline void top2_push(Top2 *t, int32_t c, uint64_t s) {
    if (s == t->s1) { if (c > t->c1) t->c1 = c; return; }
    if (c > t->c1) { t->c2 = t->c1; t->s2 = t->s1; t->c1 = c; t->s1 = s; }
    else if (c > t->c2) { t->c2 = c; t->s2 = s; }
}
static void top2_merge(Top2 *d, const Top2 *s) { top2_push(d, s->c1, s->s1); top2_push(d, s->c2, s->s2); }

// ----------------------------------------------------------------- WHT
static void fwht(int32_t *f, int n) {
    if (n < 8) {
        for (int h = 1; h < n; h <<= 1)
            for (int i = 0; i < n; i += 2 * h)
                for (int j = i; j < i + h; j++) { int32_t u = f[j], v = f[j + h]; f[j] = u + v; f[j + h] = u - v; }
        return;
    }
    for (int i = 0; i < n; i += 8) {                 // les trois premiers étages, par groupes de 8
        int32_t *g = f + i, a0 = g[0], a1 = g[1], a2 = g[2], a3 = g[3], a4 = g[4], a5 = g[5], a6 = g[6], a7 = g[7];
        int32_t b0 = a0 + a1, b1 = a0 - a1, b2 = a2 + a3, b3 = a2 - a3, b4 = a4 + a5, b5 = a4 - a5, b6 = a6 + a7, b7 = a6 - a7;
        int32_t c0 = b0 + b2, c1 = b1 + b3, c2 = b0 - b2, c3 = b1 - b3, c4 = b4 + b6, c5 = b5 + b7, c6 = b4 - b6, c7 = b5 - b7;
        g[0] = c0 + c4; g[1] = c1 + c5; g[2] = c2 + c6; g[3] = c3 + c7;
        g[4] = c0 - c4; g[5] = c1 - c5; g[6] = c2 - c6; g[7] = c3 - c7;
    }
    for (int h = 8; h < n; h <<= 1)
        for (int i = 0; i < n; i += 2 * h) {
            int32_t *x = f + i, *y = f + i + h;
            for (int j = 0; j < h; j++) { int32_t u = x[j], v = y[j]; x[j] = u + v; y[j] = u - v; }
        }
}

// ----------------------------------------------------------------- la statistique scalaire (§7.13)
// Observations d'un bloc : n tirages × nw mots. a[q] = α de la position ; sg[q] = ±1, constante affine
// de l'observation ; s[q] = sg·w, poids individuel signé (décisions dures) ; y[t] = moyenne centrée des
// nw poids du tirage. Pour un état p et des signes effectifs sc :
//   B_t(p) = Σ_m sc (−1)^{<a,p>},  Λ(p) = Σ_t y_t B_t(p),  Q(p) = Σ_t B_t(p)²
//   z(p) = Λ/√(σ0² Q) : exactement de variance 1 pour tout état faux (Var Λ = σ0² Q, y_t indépendants),
//          quel que soit l'état — l'ancien C/√Σw² gonflait l'état zéro d'un facteur ×3 (Q(0) = 100 n) ;
//   R(p) = Λ − (μ/2) Q  ∝  log-vraisemblance (à une constante près) : le CLASSEMENT des états.
// Par WHT : Λ = WHT(f), f[a] += sc·y ; Q = nw·n + 2·WHT(g), g[a ⊕ a'] += sc·sc' sur les paires d'un tirage.
typedef struct { int n, nw; uint32_t *a; int8_t *sg; int32_t *s; int16_t *y; int *pos; } Obs;

static inline int32_t rde(int32_t lam, int32_t q, int e) { return lam - (int32_t)(((int64_t)MUQ[e] * q) >> 8); }
static inline double zde(int32_t lam, int32_t q, int e) { return q > 0 ? lam / sqrt(S0[e] * q) : 0; }

static void lambda_q(const Obs *o, const uint32_t *ix, const int8_t *sc, int32_t *fl, int32_t *fq, int nn) {
    memset(fl, 0, sizeof(int32_t) * (size_t)nn); memset(fq, 0, sizeof(int32_t) * (size_t)nn);
    int nw = o->nw;
    for (int t = 0, q = 0; t < o->n; t++, q += nw) {
        int32_t y = o->y[t];
        for (int m = 0; m < nw; m++) {
            fl[ix[q + m]] += sc[q + m] * y;
            for (int l = 0; l < m; l++) fq[ix[q + m] ^ ix[q + l]] += sc[q + m] * sc[q + l];
        }
    }
    fwht(fl, nn); fwht(fq, nn);
}

static void scan_top2(const int32_t *fl, const int32_t *fq, int nn, int32_t nwn, int e, uint64_t haut, Top2 *t) {
    int32_t m1 = INT32_MIN, m2 = INT32_MIN; int i1 = 0, i2 = 0;
    for (int i = 0; i < nn; i++) {
        int32_t v = rde(fl[i], nwn + 2 * fq[i], e);
        if (v > m1) { m2 = m1; i2 = i1; m1 = v; i1 = i; } else if (v > m2) { m2 = v; i2 = i; }
    }
    top2_push(t, m1, haut | (uint64_t)i1); top2_push(t, m2, haut | (uint64_t)i2);
}

// Λ, Q d'un état, directement
static void stat_direct(const Obs *o, const int8_t *sc, uint32_t p, int32_t *lam, int32_t *Q) {
    int64_t l = 0, qq = 0; int nw = o->nw;
    for (int t = 0, q = 0; t < o->n; t++, q += nw) {
        int B = 0;
        for (int m = 0; m < nw; m++) B += __builtin_parity(o->a[q + m] & p) ? -sc[q + m] : sc[q + m];
        l += (int64_t)o->y[t] * B; qq += B * B;
    }
    *lam = (int32_t)l; *Q = (int32_t)qq;
}
static int32_t rdirect(const Obs *o, const int8_t *sc, uint32_t p, int e) { int32_t l, q; stat_direct(o, sc, p, &l, &q); return rde(l, q, e); }
static double zdirect(const Obs *o, const int8_t *sc, uint32_t p, int e) { int32_t l, q; stat_direct(o, sc, p, &l, &q); return zde(l, q, e); }

// WHT directe (L ≤ 24) : Λ et Q sur les 2^L états
static void wht_direct(const Obs *o, const int8_t *sc, int32_t *fl, int32_t *fq, int e, uint64_t haut, Top2 *t) {
    int nn = 1 << L;
    lambda_q(o, o->a, sc, fl, fq, nn);
    scan_top2(fl, fq, nn, o->nw * o->n, e, haut, t);
}

static int cmp_abs_desc(const void *x, const void *y, void *arg) {
    const int32_t *s = arg; int i = *(const int *)x, j = *(const int *)y;
    int32_t u = abs(s[i]), v = abs(s[j]);
    return u > v ? -1 : u < v ? 1 : (i - j);
}
static int cmp_cout_asc(const void *x, const void *y, void *arg) {
    const int64_t *c = arg; int i = *(const int *)x, j = *(const int *)y;
    return c[i] < c[j] ? -1 : c[i] > c[j] ? 1 : (i - j);
}

// plan 0 vu depuis la position delta (|delta| ≤ DMAX) : r_i = r_{i−K} ⊕ r_{i−L} vers l'avant,
// r_i = r_{i+L} ⊕ r_{i+L−K} vers l'arrière.
// (m plans : mots mod 2^m, r_i = r_{i−K} + r_{i−L} et r_i = r_{i+L} − r_{i+L−K} mod 2^m)
#define DMAX 32
static void decale_m(uint32_t *pl, int m, int delta) {
    uint32_t r[MAXL + 2 * DMAX], M = (1u << m) - 1;               // r[q] = r_{q − DMAX}
    for (int j = 0; j < L; j++) { r[DMAX + j] = 0; for (int q = 0; q < m; q++) r[DMAX + j] |= ((pl[q] >> j) & 1u) << q; }
    for (int j = L; j < L + DMAX; j++) r[DMAX + j] = (r[DMAX + j - K] + r[DMAX + j - L]) & M;
    for (int i = -1; i >= -DMAX; i--) r[DMAX + i] = (r[DMAX + i + L] - r[DMAX + i + L - K]) & M;
    for (int q = 0; q < m; q++) { pl[q] = 0; for (int j = 0; j < L; j++) pl[q] |= ((r[DMAX + delta + j] >> q) & 1u) << j; }
}
static uint32_t decale(uint32_t p, int delta) { uint32_t pl[1] = {p}; decale_m(pl, 1, delta); return pl[0]; }

// montée locale de R : un puis deux bits, puis les OMBRES DÉCALÉES (§7.13). L'état vrai décalé de ±2,
// ±4, … positions (un, deux, … mots pairs) garde neuf, huit, … bits sur dix par tirage, donc
// B'_t ≈ B_t − s + s' : corrélation 0,9 avec le vrai, z ≈ 0,87·z_vrai (mesuré). Un arrêt anticipé se
// pose volontiers sur une ombre ; la montée par décalage remonte au vrai.
static void grimpe(const Obs *o, const int8_t *sc, int e, uint32_t *p, int32_t *c) {
    for (;;) {
        int mieux = 0;
        for (int j = 0; j < L; j++) {
            uint32_t q = *p ^ (1u << j); int32_t cq = rdirect(o, sc, q, e);
            if (cq > *c) { *p = q; *c = cq; mieux = 1; }
        }
        if (mieux) continue;
        for (int j = 0; j < L && !mieux; j++)
            for (int l = j + 1; l < L; l++) {
                uint32_t q = *p ^ (1u << j) ^ (1u << l); int32_t cq = rdirect(o, sc, q, e);
                if (cq > *c) { *p = q; *c = cq; mieux = 1; break; }
            }
        if (mieux) continue;
        for (int d = -DMAX; d <= DMAX; d++) {
            if (!d) continue;
            uint32_t q = decale(*p, d); int32_t cq = rdirect(o, sc, q, e);
            if (cq > *c) { *p = q; *c = cq; mieux = 1; }
        }
        if (!mieux) return;
    }
}

// WHT À POSITIONS FIXÉES (L > WHT_MAXL, THEORIE_ETAT §7.13). Les f = L − b observations les
// plus fiables dont les vecteurs α sont indépendants fixent f bits de l'état (décision dure
// bit = [s < 0]) ; un motif d'erreur e ∈ {0,1}^f sur ces décisions laisse un sous-espace
// affine de 2^b états, balayé par DEUX WHT de 2^b (Λ et Q, projection des α sur une base du noyau).
// Les 2^f motifs sont parcourus par coût Σ_{r∈e} |s_r| croissant (vraisemblance décroissante)
// et le parcours s'arrête (i) dès que le meilleur état (par R) atteint z ≥ zstop (> 0), (ii) dès
// que la masse P(e) = Π p_r^{e_r} (1−p_r)^{1−e_r} des motifs vus atteint `couv`
// (p_r = 1/(1+e^{|s_r|/256})). couv ≥ 1 et zstop ≤ 0 : parcours complet, identique à la WHT sur
// 2^L ; le meilleur état est ensuite poussé au sommet de son voisinage (grimpe). Retourne le
// nombre de motifs parcourus (−1 si f positions indépendantes manquent) et la masse couverte.
static int wht_fixe(const Obs *o, const int8_t *sc, int32_t *fl, int32_t *fq, int b, double zstop, double couv,
                    int e, Top2 *t, double *masse) {
    int fd = L - b, nn = 1 << b, n = o->n * o->nw;
    const int32_t *s = o->s;
    *masse = 0;
    int *idx = malloc(sizeof(int) * n);
    for (int i = 0; i < n; i++) idx[i] = i;
    qsort_r(idx, n, sizeof(int), cmp_abs_desc, (void *)s);
    uint64_t rows[MAXL]; int piv[MAXL], fix[MAXL], nr = 0;     // ligne : α | rhs << L | origine << (L+1)
    const uint64_t MA = (1ull << L) - 1;
    for (int q = 0; q < n && nr < fd; q++) {
        int i = idx[q];
        uint64_t v = (uint64_t)o->a[i] | ((uint64_t)(s[i] < 0) << L) | (1ull << (L + 1 + nr));
        for (int r = 0; r < nr; r++) if ((v >> piv[r]) & 1) v ^= rows[r];
        if (!(v & MA)) continue;
        int c = __builtin_ctzll(v & MA);
        for (int r = 0; r < nr; r++) if ((rows[r] >> c) & 1) rows[r] ^= v;
        rows[nr] = v; piv[nr] = c; fix[nr] = i; nr++;
    }
    free(idx);
    if (nr < fd) return -1;
    uint32_t noy[MAXL]; int nl = 0, estpiv = 0;                  // base du noyau : une colonne libre par bit de y
    for (int r = 0; r < fd; r++) estpiv |= 1 << piv[r];
    for (int c = 0; c < L; c++) if (!((estpiv >> c) & 1)) {
        uint32_t v = 1u << c;
        for (int r = 0; r < fd; r++) if ((rows[r] >> c) & 1) v |= 1u << piv[r];
        noy[nl++] = v;
    }
    uint32_t *ix = malloc(sizeof(uint32_t) * n), *pm = malloc(sizeof(uint32_t) * n); int8_t *scp = malloc(n);
    for (int i = 0; i < n; i++) {                                // ix : <α, noyau> ; pm : α aux colonnes pivots
        uint32_t u = 0, w = 0;
        for (int j = 0; j < nl; j++) u |= (uint32_t)__builtin_parity(o->a[i] & noy[j]) << j;
        for (int r = 0; r < fd; r++) w |= ((o->a[i] >> piv[r]) & 1u) << r;
        ix[i] = u; pm[i] = w;
    }
    uint32_t rhs0 = 0, orig[MAXL]; double perr[MAXL];
    for (int r = 0; r < fd; r++) {
        rhs0 |= (uint32_t)((rows[r] >> L) & 1) << r; orig[r] = (uint32_t)(rows[r] >> (L + 1));
        perr[r] = 1.0 / (1.0 + exp(fabs((double)s[fix[r]]) / ECHELLE));
    }
    int np = 1 << fd;
    int64_t *cout = malloc(sizeof(int64_t) * np); int *ordre = malloc(sizeof(int) * np);
    for (int ee = 0; ee < np; ee++) {
        int64_t c = 0; for (int r = 0; r < fd; r++) if ((ee >> r) & 1) c += abs(s[fix[r]]);
        cout[ee] = c; ordre[ee] = ee;
    }
    qsort_r(ordre, np, sizeof(int), cmp_cout_asc, cout);
    int vus = 0; int32_t nwn = n;
    for (int q = 0; q < np; q++) {
        int ee = ordre[q];
        uint32_t rhs = rhs0, ppart = 0; double pe = 1;
        for (int r = 0; r < fd; r++) {
            rhs ^= (uint32_t)__builtin_parity(orig[r] & (uint32_t)ee) << r;
            pe *= ((ee >> r) & 1) ? perr[r] : 1 - perr[r];
        }
        for (int r = 0; r < fd; r++) if ((rhs >> r) & 1) ppart |= 1u << piv[r];
        for (int i = 0; i < n; i++) scp[i] = __builtin_parity(pm[i] & rhs) ? -sc[i] : sc[i];
        lambda_q(o, ix, scp, fl, fq, nn);
        Top2 u; top2_init(&u);
        scan_top2(fl, fq, nn, nwn, e, 0, &u);
        uint32_t p1 = ppart, p2 = ppart;
        for (int j = 0; j < nl; j++) { if ((u.s1 >> j) & 1) p1 ^= noy[j]; if ((u.s2 >> j) & 1) p2 ^= noy[j]; }
        int32_t avant = t->c1;
        top2_push(t, u.c1, p1); top2_push(t, u.c2, p2);
        vus++; *masse += pe;
        if (zstop > 0 && t->c1 > avant && zdirect(o, sc, (uint32_t)t->s1, e) >= zstop) break;
        if (*masse >= couv) break;
    }
    free(ix); free(pm); free(scp); free(cout); free(ordre);
    if (t->c1 > INT32_MIN) {
        uint32_t p = (uint32_t)t->s1; int32_t c = t->c1;
        if (rdirect(o, sc, p, e) != c) fprintf(stderr, "wht_fixe : incohérence état/score %08x %d %d\n", p, c, rdirect(o, sc, p, e));
        grimpe(o, sc, e, &p, &c);
        top2_push(t, c, p);
    }
    return vus;
}

// ----------------------------------------------------------------- observations d'un bloc
static int nobs_bloc(int b) { return NBL[b] * NWM; }

static void obs1_bloc(int b, Obs *o) {                             // plan shift : dix mots pairs
    o->n = NBL[b]; o->nw = NWM;
    for (int t = 0, q = 0; t < o->n; t++) {
        o->y[t] = Y1[T0[b] + t];
        for (int m = 0; m < NWM; m++, q++) {
            int i = S * t + WK[m];
            o->a[q] = ALPHA[i]; o->s[q] = W1[(size_t)(T0[b] + t) * NWM + m]; o->sg[q] = 1; o->pos[q] = i;
        }
    }
}

// signes effectifs de l'étape 1 : plan 0, sc = sg ; plan 1, sc[q] = sg[q]·(−1)^{δ_pos(p)} (retenues du plan 0)
static void signes(int b, const Obs *o, uint32_t p, int8_t *sc, uint8_t *buf) {
    int n = o->n * o->nw;
    if (SHIFT == 0) { memcpy(sc, o->sg, n); return; }
    int npos = S * (NBL[b] - 1) + WK[NWM - 1] + 1;
    uint8_t *p0 = buf, *d = buf + npos;
    for (int i = 0; i < npos; i++) {
        if (i < L) { p0[i] = (p >> i) & 1; d[i] = 0; continue; }
        int c1 = p0[i - K] & p0[i - L]; p0[i] = p0[i - K] ^ p0[i - L]; d[i] = d[i - K] ^ d[i - L] ^ c1;
    }
    for (int q = 0; q < n; q++) sc[q] = d[o->pos[q]] ? -o->sg[q] : o->sg[q];
}

// seuil Z(nbits, alpha) = Q^{-1}(alpha / 2^nbits) : niveau alpha par bloc parmi 2^nbits hypothèses
static double seuil_z_alpha(int nbits, double alpha) {
    double cible = alpha / ldexp(1.0, nbits), lo = 0, hi = 20;
    for (int it = 0; it < 200; it++) { double z = 0.5 * (lo + hi); if (0.5 * erfc(z / M_SQRT2) > cible) lo = z; else hi = z; }
    return 0.5 * (lo + hi);
}
// seuil de détection Z1 : un faux positif sur 10^7 blocs ; seuil de confirmation Z2 (étape 2) : 1e-3 par bloc,
// l'étape 2 n'ayant à confirmer que les blocs déjà détectés (z2 vrai ≈ 6,6 par bloc de 204 tirages, §7.13)
static double seuil_z(int nbits) { return seuil_z_alpha(nbits, 1e-7); }
static double seuil_z2(int nbits) { return seuil_z_alpha(nbits, 1e-3); }

// ----------------------------------------------------------------- résultats
typedef struct {
    Top2 e1, e2; int meth1, meth2, np1, np2, delta; double z1, z1b, z2, z2b, couv1, couv2;
    uint32_t plan[3]; int nplan;
} Res;
static Res *RES;
static pthread_mutex_t LOCK = PTHREAD_MUTEX_INITIALIZER;
static const char *METH[] = {"wht", "fixe", "-"};

// ----------------------------------------------------------------- étape 1
static int NSUB; static long NTASK, NEXT = 0;

typedef struct {
    int id; Obs o; int8_t *sc;
    int32_t *fl, *fq; uint64_t *p0, *del; uint8_t *buf;
} Th;

static const uint64_t PAT[6] = {0xAAAAAAAAAAAAAAAAull, 0xCCCCCCCCCCCCCCCCull, 0xF0F0F0F0F0F0F0F0ull,
                                0xFF00FF00FF00FF00ull, 0xFFFF0000FFFF0000ull, 0xFFFFFFFF00000000ull};

static void tache1(Th *th, long id) {
    int b = (int)(id / NSUB), sub = (int)(id % NSUB);
    Obs *o = &th->o;
    Top2 t; top2_init(&t);
    obs1_bloc(b, o);
    int n = o->n * o->nw;
    if (SHIFT == 0) {
        if (L <= WHT_MAXL) { wht_direct(o, o->sg, th->fl, th->fq, 0, 0, &t); RES[b].meth1 = 0; RES[b].couv1 = 1; }
        else { RES[b].np1 = wht_fixe(o, o->sg, th->fl, th->fq, WHT_B, ZSTOP, WHT_COUV, 0, &t, &RES[b].couv1); RES[b].meth1 = 1; }
    } else {
        // 64 plans 0 : p = base + bb, bb = 0..63 ; p0_i et δ_i en tranches de bits
        uint64_t base = (uint64_t)sub << 6;
        int npos = S * (NBL[b] - 1) + WK[NWM - 1] + 1;
        uint64_t *p0 = th->p0, *del = th->del;
        for (int i = 0; i < npos; i++) {
            if (i < L) { p0[i] = i < 6 ? PAT[i] : (((base >> i) & 1) ? ~0ull : 0ull); del[i] = 0; }
            else { uint64_t c1 = p0[i - K] & p0[i - L]; p0[i] = p0[i - K] ^ p0[i - L]; del[i] = del[i - K] ^ del[i - L] ^ c1; }
        }
        int nn = 1 << L;
        for (int bb = 0; bb < 64; bb++) {
            uint64_t p = base + (uint64_t)bb;
            if (p >= (1ull << L)) break;
            for (int q = 0; q < n; q++) th->sc[q] = ((del[o->pos[q]] >> bb) & 1) ? -1 : 1;
            lambda_q(o, o->a, th->sc, th->fl, th->fq, nn);
            scan_top2(th->fl, th->fq, nn, n, 0, p << 32, &t);
        }
        RES[b].meth1 = 0; RES[b].couv1 = 1;
    }
    pthread_mutex_lock(&LOCK);
    top2_merge(&RES[b].e1, &t);
    pthread_mutex_unlock(&LOCK);
}

// z du plan shift d'un état (s : p | y << 32 au plan 1, p au plan 0) sur le bloc b (th : tampons)
static double z1_etat(Th *th, int b, uint64_t s) {
    Obs *o = &th->o; obs1_bloc(b, o);
    uint32_t p = SHIFT == 0 ? (uint32_t)s : (uint32_t)(s >> 32), y = (uint32_t)s;
    signes(b, o, p, th->sc, th->buf);
    return zdirect(o, th->sc, SHIFT == 0 ? p : y, 0);
}

// ----------------------------------------------------------------- étape 2 : le plan shift + 1
// observations du plan shift + 1 sous l'hypothèse (p, y) des plans décodés
static void obs2_bloc(Th *th, int b, uint32_t p, uint32_t y) {
    Obs *o = &th->o;
    int npos = S * (NBL[b] - 1) + WK[NWM - 1] + 1;
    uint8_t *p0 = th->buf, *d = p0 + npos, *p1 = d + npos, *eps = p1 + npos;
    for (int i = 0; i < npos; i++) {
        if (i < L) { p0[i] = (p >> i) & 1; d[i] = 0; p1[i] = (y >> i) & 1; eps[i] = 0; continue; }
        int c1 = p0[i - K] & p0[i - L];
        p0[i] = p0[i - K] ^ p0[i - L];
        d[i] = d[i - K] ^ d[i - L] ^ c1;
        p1[i] = p1[i - K] ^ p1[i - L] ^ c1;
        int a1 = p1[i - K], b1 = p1[i - L];
        int c2 = (a1 & b1) | (a1 & c1) | (b1 & c1);
        eps[i] = eps[i - K] ^ eps[i - L] ^ c2;
    }
    o->n = NBL[b]; o->nw = NWM / 2;
    for (int t = 0, q = 0; t < o->n; t++) {
        double ysum = 0;
        for (int m = 0; m < NWM; m += 2, q++) {          // k ≡ 0 mod 4 : e ≥ 2
            int i = S * t + WK[m];
            const uint8_t *c = CNT + ((size_t)(T0[b] + t) * NWM + m) * 4;
            int bit = SHIFT == 0 ? p0[i] : p1[i];
            int w = poids(c[bit], c[bit + 2]);
            int cst = SHIFT == 0 ? d[i] : eps[i];
            o->a[q] = ALPHA[i]; o->s[q] = cst ? -w : w; o->sg[q] = cst ? -1 : 1; o->pos[q] = i; ysum += w;
        }
        o->y[t] = (int16_t)lrint(ysum / o->nw - E0[1]);
    }
}

// Étape 2 sur l'état rendu par l'étape 1 ; si le plan shift est détecté (z1 ≥ Z1) mais que le
// plan shift + 1 ne le confirme pas (z2 < Z2), les OMBRES ±2, ±4 de l'état (§7.13) sont essayées ;
// une ombre ne remplace l'état de l'étape 1 que si elle est CONFIRMEE (z2 ≥ Z2) et meilleure : sans cela
// le maximum nul de l'étape 2 d'une ombre (≈ 5,5 à 6,5 sur 2^L) supplanterait l'état vrai par bruit.
static void tache2(Th *th, int b) {
    Res *R = &RES[b];
    double z1 = R->z1;
    uint32_t p = SHIFT == 0 ? (uint32_t)R->e1.s1 : (uint32_t)(R->e1.s1 >> 32);
    uint32_t y = (uint32_t)(R->e1.s1 & 0xffffffffu);
    R->plan[0] = p; R->nplan = SHIFT == 0 ? 1 : 2; if (SHIFT == 1) R->plan[1] = y;
    if (L > WHT_MAXL && ZSTOP > 0 && z1 < ZSTOP) { R->meth2 = 2; return; }   // rien à confirmer : pas 2^L
    const int deltas[5] = {0, -2, 2, -4, 4};
    double Z1 = seuil_z(SHIFT == 0 ? L : 2 * L), Z2 = seuil_z2(L), zbest = -1e9;
    int nc = 1;
    Obs *o = &th->o;
    for (int c = 0; c < nc; c++) {
        uint32_t pl[2] = {p, y};
        if (deltas[c]) decale_m(pl, SHIFT == 0 ? 1 : 2, deltas[c]);
        obs2_bloc(th, b, pl[0], pl[1]);
        double couv2 = 1; int np2 = 0, meth2 = 0;
        Top2 t; top2_init(&t);
        if (L <= WHT_MAXL) wht_direct(o, o->sg, th->fl, th->fq, 1, 0, &t);
        else { np2 = wht_fixe(o, o->sg, th->fl, th->fq, WHT_B, ZSTOP, WHT_COUV, 1, &t, &couv2); meth2 = 1; }
        double z2 = zdirect(o, o->sg, (uint32_t)t.s1, 1), z2b = t.c2 > INT32_MIN ? zdirect(o, o->sg, (uint32_t)t.s2, 1) : 0;
        if (c == 0 && z1 >= Z1 && z2 < Z2) nc = 5;                 // détecté, non confirmé : les ombres
        if (z2 > zbest && (c == 0 || z2 >= Z2)) {                  // une ombre ne l'emporte que confirmée
            zbest = z2; R->e2 = t; R->z2 = z2; R->z2b = z2b; R->couv2 = couv2; R->np2 = np2; R->meth2 = meth2; R->delta = deltas[c];
            if (SHIFT == 0) { R->plan[0] = pl[0]; R->plan[1] = (uint32_t)t.s1; R->nplan = 2; }
            else { R->plan[0] = pl[0]; R->plan[1] = pl[1]; R->plan[2] = (uint32_t)t.s1; R->nplan = 3; }
        }
    }
}

static int ETAPE = 1;
static void *fil(void *arg) {
    Th *th = arg;
    for (;;) {
        long id = __atomic_fetch_add(&NEXT, 1, __ATOMIC_RELAXED);
        if (id >= NTASK) break;
        if (ETAPE == 1) tache1(th, id); else tache2(th, (int)id);
    }
    return NULL;
}

static Th *TH;
static void decode(void) {
    RES = calloc(NB, sizeof(Res));
    for (int b = 0; b < NB; b++) { top2_init(&RES[b].e1); top2_init(&RES[b].e2); RES[b].meth1 = RES[b].meth2 = 3; }
    if (SHIFT == 1 && L > WHT_MAXL) { fprintf(stderr, "shift 1 et L > %d : 2^(2L) hors de portée (§7.13)\n", WHT_MAXL); exit(2); }
    if (SHIFT == 0) NSUB = 1; else NSUB = (L <= 6) ? 1 : (1 << (L - 6));
    if (WHT_B > WHT_MAXL) WHT_B = WHT_MAXL;
    if (L > WHT_MAXL && L - WHT_B > 16) WHT_B = L - 16;          // au plus 2^16 motifs d'erreur
    int nmax = 0; for (int b = 0; b < NB; b++) if (NBL[b] > nmax) nmax = NBL[b];
    int nposmax = S * (nmax - 1) + WK[NWM - 1] + 1;
    size_t fsz = (size_t)1 << (L <= WHT_MAXL ? L : WHT_B);
    Th *th = TH = calloc(NTHR, sizeof(Th)); pthread_t *tid = malloc(sizeof(pthread_t) * NTHR);
    for (int i = 0; i < NTHR; i++) {
        th[i].id = i;
        th[i].o.a = malloc(sizeof(uint32_t) * (size_t)nmax * NWM);
        th[i].o.s = malloc(sizeof(int32_t) * (size_t)nmax * NWM);
        th[i].o.sg = malloc((size_t)nmax * NWM);
        th[i].o.pos = malloc(sizeof(int) * (size_t)nmax * NWM);
        th[i].o.y = malloc(sizeof(int16_t) * (size_t)nmax);
        th[i].sc = malloc((size_t)nmax * NWM);
        th[i].fl = malloc(sizeof(int32_t) * fsz); th[i].fq = malloc(sizeof(int32_t) * fsz);
        th[i].buf = malloc(4 * (size_t)nposmax);
        if (SHIFT == 1) { th[i].p0 = malloc(8 * (size_t)nposmax); th[i].del = malloc(8 * (size_t)nposmax); }
    }
    double t0 = now();
    ETAPE = 1; NTASK = (long)NB * NSUB; NEXT = 0;
    for (int i = 0; i < NTHR; i++) pthread_create(&tid[i], NULL, fil, &th[i]);
    for (int i = 0; i < NTHR; i++) pthread_join(tid[i], NULL);
    double t1 = now();
    for (int b = 0; b < NB; b++) {
        RES[b].z1 = z1_etat(&th[0], b, RES[b].e1.s1);
        RES[b].z1b = RES[b].e1.c2 > INT32_MIN ? z1_etat(&th[0], b, RES[b].e1.s2) : 0;
    }
    ETAPE = 2; NTASK = NB; NEXT = 0;
    for (int i = 0; i < NTHR; i++) pthread_create(&tid[i], NULL, fil, &th[i]);
    for (int i = 0; i < NTHR; i++) pthread_join(tid[i], NULL);
    double t2 = now();
    double zmax = -1e9; int bmax = -1;
    for (int b = 0; b < NB; b++) {
        Res *R = &RES[b];
        double z2 = R->meth2 < 2 ? R->z2 : 0, z2b = R->meth2 < 2 ? R->z2b : 0;
        if (R->z1 > zmax) { zmax = R->z1; bmax = b; }
        char pl[3][12], m1[24], m2[24];
        for (int q = 0; q < 3; q++) { if (q < R->nplan) snprintf(pl[q], 12, "%08x", R->plan[q]); else snprintf(pl[q], 12, "-"); }
        if (R->meth1 == 1) snprintf(m1, 24, "fixe/%d", R->np1); else snprintf(m1, 24, "%s", METH[R->meth1]);
        if (R->meth2 == 1) snprintf(m2, 24, "fixe/%d", R->np2); else snprintf(m2, 24, "%s", METH[R->meth2]);
        printf("BLOC %d %d %d %d %.3f %.3f %s %.4f %s %s %s %.3f %.3f %s %.4f %d\n", b, T0[b], NBL[b], nobs_bloc(b), R->z1, R->z1b, m1, R->couv1,
               pl[0], pl[1], pl[2], z2, z2b, m2, R->couv2, R->delta);
    }
    printf("FIN %d %d %d %s %d %d %.3f %d %.1f %.1f %.1f\n", K, L, S, MODE ? "shuffle" : "fy", SHIFT, NB, zmax, bmax, t1 - t0, t2 - t1, t2 - t0);
    fflush(stdout);
}

// ----------------------------------------------------------------- lecture, blocs
static void lit_archive(const char *fn) {
    FILE *fp = fopen(fn, "r"); if (!fp) { perror(fn); exit(1); }
    int cap = 1 << 16; ENS = malloc(sizeof(int) * (size_t)cap * DRAWN); N = 0;
    while (1) {
        if (N == cap) { cap *= 2; ENS = realloc(ENS, sizeof(int) * (size_t)cap * DRAWN); }
        int ok = 1;
        for (int q = 0; q < DRAWN; q++) if (fscanf(fp, "%d", &ENS[N * DRAWN + q]) != 1) { ok = 0; break; }
        if (!ok) break;
        N++;
    }
    fclose(fp);
}

static void lit_blocs(const char *fn) {
    FILE *fp = fopen(fn, "r"); if (!fp) { perror(fn); exit(1); }
    int cap = 1024; T0 = malloc(sizeof(int) * cap); NB = 0; int v;
    while (fscanf(fp, "%d", &v) == 1) { if (NB == cap) { cap *= 2; T0 = realloc(T0, sizeof(int) * cap); } T0[NB++] = v; }
    fclose(fp);
    if (NB == 0 || T0[0] != 0) { fprintf(stderr, "blocs : le premier indice doit être 0\n"); exit(1); }
    NBL = malloc(sizeof(int) * NB);
    for (int b = 0; b < NB; b++) NBL[b] = (b + 1 < NB ? T0[b + 1] : N) - T0[b];
    NMAXBLOC = 0; for (int b = 0; b < NB; b++) if (NBL[b] > NMAXBLOC) NMAXBLOC = NBL[b];
}

// ----------------------------------------------------------------- autotest : générateur
static uint64_t rng_s = 0x9E3779B97F4A7C15ull;
static uint32_t rnd(void) {
    rng_s ^= rng_s << 13; rng_s ^= rng_s >> 7; rng_s ^= rng_s << 17;
    return (uint32_t)(rng_s >> 11);
}

static void genere(const uint32_t *init, int *ens, int n) {          // ens : n × 20, positions S·t + k
    int npos = S * (n - 1) + POOL + L;
    uint32_t *r = malloc(sizeof(uint32_t) * npos);
    for (int i = 0; i < npos; i++) r[i] = i < L ? init[i] : r[i - K] + r[i - L];
    for (int t = 0; t < n; t++) {
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

static void aleatoire(int *ens, int n) {
    for (int t = 0; t < n; t++) {
        int arr[POOL];
        for (int q = 0; q < POOL; q++) arr[q] = q + 1;
        for (int i = POOL - 1; i >= 1; i--) { int j = rnd() % (i + 1); int tmp = arr[i]; arr[i] = arr[j]; arr[j] = tmp; }
        for (int q = 0; q < DRAWN; q++) ens[t * DRAWN + q] = arr[q];
    }
}

static uint32_t plan_de(const uint32_t *init, int q) {
    uint32_t p = 0; for (int j = 0; j < L; j++) p |= ((init[j] >> q) & 1u) << j; return p;
}

// score du bit `shift` de l'état (p, y) sur les observations du bloc b (vérité : shift 0 ou 1)
static void selftest(int nb, int n, uint64_t graine) {
    rng_s = graine ? graine : 0x9E3779B97F4A7C15ull;
    N = 2 * nb * n; ENS = malloc(sizeof(int) * (size_t)N * DRAWN);
    NB = 2 * nb; T0 = malloc(sizeof(int) * NB); NBL = malloc(sizeof(int) * NB);
    uint32_t *inits = malloc(sizeof(uint32_t) * (size_t)nb * MAXL);
    for (int b = 0; b < NB; b++) { T0[b] = b * n; NBL[b] = n; }
    for (int b = 0; b < nb; b++) {
        for (int j = 0; j < L; j++) inits[b * MAXL + j] = rnd();
        genere(inits + b * MAXL, ENS + (size_t)T0[b] * DRAWN, n);
    }
    for (int b = nb; b < NB; b++) aleatoire(ENS + (size_t)T0[b] * DRAWN, n);
    NMAXBLOC = n;
    calibre(); comptes(); precalc_alpha(); decode();
    int ok1t = 0, ok2t = 0;
    Th *th = &TH[0]; Obs *o = &th->o;
    for (int b = 0; b < nb; b++) {
        const uint32_t *in = inits + b * MAXL;
        uint32_t v0 = plan_de(in, 0), v1 = plan_de(in, 1), v2 = plan_de(in, 2);
        Res *R = &RES[b];
        int ok1, ok2;
        if (SHIFT == 0) { ok1 = R->plan[0] == v0; ok2 = R->plan[1] == v1; }
        else { ok1 = R->plan[0] == v0 && R->plan[1] == v1; ok2 = R->plan[2] == v2; }
        ok1t += ok1; ok2t += ok2;
        // z et R du vrai plan shift, z des ombres ±2, ±4 (état vrai décalé, plans p et y ensemble)
        uint64_t sv = SHIFT == 0 ? (uint64_t)v0 : ((uint64_t)v0 << 32) | v1;
        double zv = z1_etat(th, b, sv), zo[4];
        int32_t rv = rdirect(o, th->sc, SHIFT == 0 ? v0 : v1, 0);
        int dd[4] = {-2, 2, -4, 4};
        for (int q = 0; q < 4; q++) {
            uint32_t pl[2] = {v0, v1}; decale_m(pl, SHIFT == 0 ? 1 : 2, dd[q]);
            zo[q] = z1_etat(th, b, SHIFT == 0 ? (uint64_t)pl[0] : (((uint64_t)pl[0] << 32) | pl[1]));
        }
        int ombre = 0;                                            // plan 0 rendu = vrai décalé de δ ≠ 0 ?
        if (!ok1) for (int d = -DMAX; d <= DMAX && !ombre; d++) if (d && decale(v0, d) == R->plan[0]) ombre = d;
        printf("VERITE %d %08x %08x %08x %s %s z1_vrai=%.3f R_vrai=%d R_rendu=%d ombre=%d z_ombres=%.2f,%.2f,%.2f,%.2f\n", b, v0, v1, v2,
               ok1 ? "ETAPE1_OK" : "ETAPE1_RATE", ok2 ? "ETAPE2_OK" : "ETAPE2_RATE", zv, rv, R->e1.c1, ombre, zo[0], zo[1], zo[2], zo[3]);
    }
    for (int b = nb; b < NB; b++) printf("NUL %d\n", b);
    double Z1 = seuil_z(SHIFT == 0 ? L : 2 * L); int det = 0, fp = 0;   // détection au seuil Z1(2^nbits)
    for (int b = 0; b < NB; b++) { int d = RES[b].z1 >= Z1; if (b < nb) det += d; else fp += d; }
    printf("AUTOTEST %d %d %d %s %d plantes=%d etape1_ok=%d etape2_ok=%d nuls=%d Z1=%.2f detectes=%d faux_positifs=%d\n",
           K, L, S, MODE ? "shuffle" : "fy", SHIFT, nb, ok1t, ok2t, nb, Z1, det, fp);
    fflush(stdout);
}

static int lit_mode(const char *s) {
    if (!strcmp(s, "fy")) return 0;
    if (!strcmp(s, "shuffle")) return 1;
    fprintf(stderr, "mode : fy ou shuffle\n"); exit(1);
}

int main(int argc, char **argv) {
    const char *env = getenv("SWEEP_THREADS"); if (env) NTHR = atoi(env); if (NTHR < 1) NTHR = 1;
    if (getenv("WHT_B")) WHT_B = atoi(getenv("WHT_B"));
    if (getenv("WHT_COUV")) WHT_COUV = atof(getenv("WHT_COUV"));
    if (getenv("WHT_ZSTOP")) ZSTOP = atof(getenv("WHT_ZSTOP"));
    if (WHT_B < 8) WHT_B = 8;
    if (argc >= 9 && (!strcmp(argv[1], "--selftest") || !strcmp(argv[1], "--selftest-flux"))) {
        K = atoi(argv[2]); L = atoi(argv[3]); S = atoi(argv[4]); MODE = lit_mode(argv[5]); SHIFT = atoi(argv[6]);
        int nb = atoi(argv[7]); uint64_t graine = strtoull(argv[8], NULL, 10);
        if (L < 2 || L > MAXL || K < 1 || K >= L || S < 1 || (MODE == 1 && S < 1)) { fprintf(stderr, "paramètres\n"); return 1; }
        if (!strcmp(argv[1], "--selftest-flux")) selftest(1, nb, graine);
        else selftest(nb, argc >= 10 ? atoi(argv[9]) : 204, graine);
        return 0;
    }
    if (argc < 8) { fprintf(stderr, "usage : lfg_soft_wht K L S fy|shuffle shift fichier blocs\n"); return 1; }
    K = atoi(argv[1]); L = atoi(argv[2]); S = atoi(argv[3]); MODE = lit_mode(argv[4]); SHIFT = atoi(argv[5]);
    if (L < 2 || L > MAXL || K < 1 || K >= L || S < 1) { fprintf(stderr, "paramètres\n"); return 1; }
    lit_archive(argv[6]); lit_blocs(argv[7]);
    calibre(); comptes(); precalc_alpha(); decode();
    return 0;
}
