// Balayage exhaustif de l'espace d'états 48 bits sur GPU.
//
// Ferme la dernière classe de générateurs atteignable par le calcul :
// java.util.Random et les LCG modulo 2^48, dont l'observable dépend des
// bits de POIDS FORT de l'état (s >> 17) et échappe donc au théorème de
// la récurrence basse close (claude/AUDIT-CLAUDE.md §2).
//
// Logique strictement identique à tools/sweep48.c, validée sur CPU à
// 156 M états/s/coeur. Sur A100 : ~2 h pour les 2^48 complets.
//
//   nvcc -O3 -arch=sm_80 -o sweep48cu sweep48.cu
//   ./sweep48cu <lo> <hi> <n1> ... <n20>
//
// Exemple (tirage 1380172) :
//   ./sweep48cu 0 281474976710656 5 6 10 11 13 22 26 28 32 35 37 38 39 41 50 55 66 68 78 79
//
// Découpage : lancer plusieurs instances sur des tranches disjointes,
// une par GPU. Aucune communication entre elles.

#include <cstdio>
#include <cstdlib>
#include <cstdint>

#define A48  0x5DEECE66DULL
#define C48  0xBULL
#define M48  0xFFFFFFFFFFFFULL
#define MAXH 64

__constant__ uint32_t d_target_lo;   // numéros 1..32  -> bits 0..31
__constant__ uint64_t d_target_mask; // numéros 1..64  -> bits 0..63
__constant__ uint16_t d_target_hi;   // numéros 65..80 -> bits 0..15

__device__ __forceinline__ bool in_target(uint32_t n) {
    uint32_t b = n - 1u;
    return (b < 64u) ? ((d_target_mask >> b) & 1ULL) != 0ULL
                     : ((d_target_hi   >> (b - 64u)) & 1u) != 0u;
}

// Un état candidat : reproduit-il les 20 numéros de la cible ?
// Arrêt anticipé au premier écart — coût moyen ~1,34 pas.
__device__ __forceinline__ bool matches(uint64_t seed) {
    uint64_t s = seed;
    uint64_t seen_lo = 0ULL;
    uint32_t seen_hi = 0u;
    int matched = 0;
#pragma unroll 4
    for (int step = 0; step < MAXH; ++step) {
        s = (s * A48 + C48) & M48;
        // next(31) tient sur 32 bits : modulo 32 bits, bien moins cher
        // qu'un modulo 64 bits sur GPU.
        uint32_t out = (uint32_t)(s >> 17);
        uint32_t n   = out % 80u + 1u;
        uint32_t b   = n - 1u;
        if (b < 64u) {
            uint64_t bit = 1ULL << b;
            if (seen_lo & bit) continue;   // doublon rejeté par le tireur
            seen_lo |= bit;
        } else {
            uint32_t bit = 1u << (b - 64u);
            if (seen_hi & bit) continue;
            seen_hi |= bit;
        }
        if (!in_target(n)) return false;
        if (++matched == 20) return true;
    }
    return false;
}

__global__ void sweep(uint64_t lo, uint64_t hi, uint64_t *hits, uint32_t *nhits) {
    uint64_t stride = (uint64_t)gridDim.x * blockDim.x;
    uint64_t idx    = lo + (uint64_t)blockIdx.x * blockDim.x + threadIdx.x;
    for (uint64_t s = idx; s < hi; s += stride) {
        if (matches(s)) {
            uint32_t k = atomicAdd(nhits, 1u);
            if (k < 256u) hits[k] = s;
        }
    }
}

int main(int argc, char **argv) {
    if (argc < 23) {
        fprintf(stderr, "usage: %s lo hi n1..n20\n", argv[0]);
        return 1;
    }
    uint64_t lo = strtoull(argv[1], nullptr, 10);
    uint64_t hi = strtoull(argv[2], nullptr, 10);

    uint64_t mask = 0ULL; uint16_t hi16 = 0u;
    for (int i = 0; i < 20; ++i) {
        int n = atoi(argv[3 + i]);
        if (n < 1 || n > 80) { fprintf(stderr, "numero hors bornes: %d\n", n); return 1; }
        if (n <= 64) mask |= 1ULL << (n - 1);
        else         hi16 |= (uint16_t)(1u << (n - 65));
    }
    cudaMemcpyToSymbol(d_target_mask, &mask, sizeof mask);
    cudaMemcpyToSymbol(d_target_hi,   &hi16, sizeof hi16);

    uint64_t *d_hits; uint32_t *d_n;
    cudaMalloc(&d_hits, 256 * sizeof(uint64_t));
    cudaMalloc(&d_n, sizeof(uint32_t));
    cudaMemset(d_n, 0, sizeof(uint32_t));

    int dev = 0, sms = 0;
    cudaGetDevice(&dev);
    cudaDeviceGetAttribute(&sms, cudaDevAttrMultiProcessorCount, dev);
    int threads = 256;
    int blocks  = sms * 32;          // occupation large, boucle à pas de grille

    cudaEvent_t t0, t1;
    cudaEventCreate(&t0); cudaEventCreate(&t1);
    cudaEventRecord(t0);
    sweep<<<blocks, threads>>>(lo, hi, d_hits, d_n);
    cudaEventRecord(t1);
    cudaEventSynchronize(t1);

    cudaError_t err = cudaGetLastError();
    if (err != cudaSuccess) { fprintf(stderr, "CUDA: %s\n", cudaGetErrorString(err)); return 2; }

    float ms = 0.f; cudaEventElapsedTime(&ms, t0, t1);
    uint32_t n = 0; cudaMemcpy(&n, d_n, sizeof n, cudaMemcpyDeviceToHost);
    uint64_t h[256];
    cudaMemcpy(h, d_hits, 256 * sizeof(uint64_t), cudaMemcpyDeviceToHost);

    double span = (double)(hi - lo);
    fprintf(stderr, "tranche [%llu, %llu) : %.3e etats en %.1f s -> %.1f G etats/s\n",
            (unsigned long long)lo, (unsigned long long)hi, span, ms / 1000.f,
            span / (ms / 1000.f) / 1e9);
    fprintf(stderr, "candidats complets : %u\n", n);
    for (uint32_t i = 0; i < n && i < 256u; ++i)
        printf("HIT %llu\n", (unsigned long long)h[i]);

    // Extrapolation utile pour planifier la couverture complète.
    if (span > 0 && ms > 0) {
        double rate = span / (ms / 1000.f);
        fprintf(stderr, "2^48 complet a ce debit : %.2f h sur ce GPU\n",
                281474976710656.0 / rate / 3600.0);
    }
    return 0;
}
