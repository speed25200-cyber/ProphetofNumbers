/* successeurs.c — LE TEST DU SUCCESSEUR : une ressemblance se prolonge-t-elle ?
 *
 * L'IDEE
 * ======
 * Si l'etat du generateur collisionne, meme partiellement, deux tirages eloignes se
 * ressemblent — ET LEURS SUCCESSEURS AUSSI. C'est le seul mecanisme qui donnerait une
 * prediction utilisable sans rien casser : on repere une paire qui se ressemble, et l'on
 * joue la suite de la premiere.
 *
 * Le dossier avait mesure le recouvrement MAXIMAL entre paires (16/20 sur 2,49 milliards
 * de paires, conforme au hasard). Il n'avait jamais regarde ce que font les SUCCESSEURS
 * des paires les plus ressemblantes.
 *
 * CE QU'IL CALCULE
 * ================
 * Pour chaque seuil s de 10 a 20 :
 *   - le nombre de paires (i,j), i < j, dont le recouvrement vaut au moins s ;
 *   - la somme des recouvrements de leurs successeurs (i+1, j+1) ;
 *   - la meme chose pour les successeurs a distance 2, pour voir si l'effet dure.
 *
 * Sous SRS, le recouvrement des successeurs vaut 5 en moyenne quel que soit celui des
 * parents — les tirages etant independants. Toute elevation est une trace d'etat.
 *
 * USAGE
 *   successeurs masques.bin      (suite de {uint64 m0, uint64 m1}, dans l'ordre du temps)
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

#define SMIN 10
#define SMAX 20

int main(int argc, char **argv)
{
    if (argc < 2) { fprintf(stderr, "usage: %s masques.bin\n", argv[0]); return 2; }
    FILE *f = fopen(argv[1], "rb");
    if (!f) { perror("masques"); return 2; }
    fseek(f, 0, SEEK_END);
    long n = ftell(f) / 16;
    fseek(f, 0, SEEK_SET);
    uint64_t *a = malloc((size_t)n * 8), *b = malloc((size_t)n * 8);
    for (long i = 0; i < n; i++) {
        uint64_t x[2];
        if (fread(x, 8, 2, f) != 2) { fprintf(stderr, "lecture\n"); return 2; }
        a[i] = x[0]; b[i] = x[1];
    }
    fclose(f);
    printf("tirages %ld ; paires %.4e\n", n, (double)n * (n - 1) / 2);
    fflush(stdout);

    /* comptes[s] : nombre de paires de recouvrement >= s ; somme1/somme2 : recouvrements
       des successeurs a distance 1 et 2 */
    double cnt[SMAX + 1] = {0}, s1[SMAX + 1] = {0}, s2[SMAX + 1] = {0};
    double c1[SMAX + 1] = {0}, c2[SMAX + 1] = {0};

    for (long i = 0; i < n; i++) {
        uint64_t ai = a[i], bi = b[i];
        for (long j = i + 1; j < n; j++) {
            int o = __builtin_popcountll(ai & a[j]) + __builtin_popcountll(bi & b[j]);
            if (o < SMIN) continue;
            for (int s = SMIN; s <= o; s++) {
                cnt[s] += 1.0;
                if (i + 1 < n && j + 1 < n) {
                    int o1 = __builtin_popcountll(a[i + 1] & a[j + 1])
                           + __builtin_popcountll(b[i + 1] & b[j + 1]);
                    s1[s] += o1; c1[s] += 1.0;
                }
                if (i + 2 < n && j + 2 < n) {
                    int o2 = __builtin_popcountll(a[i + 2] & a[j + 2])
                           + __builtin_popcountll(b[i + 2] & b[j + 2]);
                    s2[s] += o2; c2[s] += 1.0;
                }
            }
        }
        if ((i & 8191) == 0) { printf("  ... %ld/%ld\n", i, n); fflush(stdout); }
    }

    printf("\n%5s %14s %14s %10s %14s %10s\n",
           "seuil", "paires", "succ. d=1", "moyenne", "succ. d=2", "moyenne");
    for (int s = SMIN; s <= SMAX; s++) {
        if (cnt[s] < 1) continue;
        printf("%5d %14.0f %14.0f %10.5f %14.0f %10.5f\n",
               s, cnt[s], s1[s], c1[s] > 0 ? s1[s] / c1[s] : 0.0,
               s2[s], c2[s] > 0 ? s2[s] / c2[s] : 0.0);
    }
    free(a); free(b);
    return 0;
}
