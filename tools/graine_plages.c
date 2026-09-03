/* graine_plages.c — LA GRAINE REPRISE A CHAQUE TIRAGE.
 *
 * LE MODELE QUE PERSONNE N'AVAIT TESTE
 * ====================================
 * Tous les balayages du dossier — §200 a §206 — supposent que la machine s'amorce UNE
 * FOIS, au debut d'une nuit ou ailleurs, puis deroule son flux. C'est le modele du
 * programmeur soigneux.
 *
 * Le modele du programmeur presse est autre, et il est de loin le plus repandu au monde :
 *
 *      pour chaque tirage :  srand(time(NULL)) ; puis vingt appels a rand()
 *
 * c'est-a-dire une graine REPRISE DE L'HORLOGE A CHAQUE TIRAGE. C'est le bogue de
 * generation aleatoire le plus commun qui soit, et le dossier ne l'avait jamais teste
 * comme tel.
 *
 * POURQUOI C'EST DEJA A MOITIE FERME, ET CE QUI RESTE OUVERT
 * =========================================================
 * A la SECONDE, c'est deja ferme sans le savoir : le §206 balaie les 2^32 graines et
 * compare chacune a l'archive ENTIERE par table de hachage. Tout horodatage unix de
 * l'archive (1,76e9) est inferieur a 2^32, donc toute graine « seconde du tirage » a deja
 * ete essayee, avec les cinq generateurs et les six echantillonneurs.
 *
 * Ce qui reste ouvert, c'est la SOUS-SECONDE PAR TIRAGE. Le §205 ne balaie les
 * millisecondes et les microsecondes qu'autour des 346 DEBUTS DE NUIT. Si la machine
 * reprend l'horloge a chaque tirage, la graine du tirage t vaut `ts_t * 1000 + ms` ou
 * `ts_t * 1000000 + us` — et ces plages-la, sauf pour les 346 premiers tirages de nuit,
 * n'ont jamais ete visitees.
 *
 * CE QUE CET OUTIL FAIT
 * =====================
 * Il balaie une LISTE DE PLAGES arbitraires plutot qu'un intervalle unique, ce qui permet
 * de viser les 70 560 fenetres sous-seconde des tirages eux-memes. Le reste — les cinq
 * generateurs, les six echantillonneurs, la table de hachage des 70 560 masques — est
 * celui de `graine_exhaustive.c`, INCLUS et non recopie : c'est exactement le code que le
 * temoin 30/30 du §211 a valide.
 *
 * La comparaison reste faite contre l'archive entiere, jamais contre le seul tirage vise.
 * C'est plus fort et non moins : une graine de la fenetre du tirage t qui produirait le
 * tirage u serait vue aussi.
 *
 * USAGE
 * =====
 *   graine_plages cibles.bin plages.bin bloc nbloc
 *     cibles.bin : suite d'enregistrements {int64 ts, uint64 m0, uint64 m1}
 *     plages.bin : suite d'enregistrements {uint64 debut, uint64 longueur}
 *     bloc/nbloc : ce processus traite les plages d'indice congru a `bloc` modulo `nbloc`
 */

#define SANS_MAIN
#include "graine_exhaustive.c"

typedef struct { uint64_t debut, longueur; } Plage;

int main(int argc, char **argv)
{
    if (argc < 5) {
        fprintf(stderr, "usage: %s cibles.bin plages.bin bloc nbloc\n", argv[0]);
        return 2;
    }
    FILE *f = fopen(argv[1], "rb");
    if (!f) { perror("cibles"); return 2; }
    fseek(f, 0, SEEK_END);
    long nc = ftell(f) / (long)sizeof(Cible);
    fseek(f, 0, SEEK_SET);
    Cible *C = malloc((size_t)nc * sizeof(Cible));
    if (fread(C, sizeof(Cible), (size_t)nc, f) != (size_t)nc) {
        fprintf(stderr, "lecture cibles incomplete\n"); return 2;
    }
    fclose(f);

    f = fopen(argv[2], "rb");
    if (!f) { perror("plages"); return 2; }
    fseek(f, 0, SEEK_END);
    long np = ftell(f) / (long)sizeof(Plage);
    fseek(f, 0, SEEK_SET);
    Plage *P = malloc((size_t)np * sizeof(Plage));
    if (fread(P, sizeof(Plage), (size_t)np, f) != (size_t)np) {
        fprintf(stderr, "lecture plages incomplete\n"); return 2;
    }
    fclose(f);

    int bloc = atoi(argv[3]), nbloc = atoi(argv[4]);
    if (nbloc < 1 || bloc < 0 || bloc >= nbloc) {
        fprintf(stderr, "bloc %d hors de [0, %d)\n", bloc, nbloc); return 2;
    }

    uint64_t taille = 1;
    while (taille < (uint64_t)nc * 4) taille <<= 1;
    HMASK = taille - 1;
    Ha = calloc(taille, sizeof(uint64_t));
    Hb = calloc(taille, sizeof(uint64_t));
    Hi = calloc(taille, sizeof(long));
    for (long i = 0; i < nc; i++) inserer(C[i].m0, C[i].m1, i);

    double graines = 0.0;
    long amoi = 0;
    for (long i = bloc; i < np; i += nbloc) { graines += (double)P[i].longueur; amoi++; }
    double essais = graines * NGEN * NECH;
    printf("cibles %ld ; plages %ld (dont %ld pour le bloc %d/%d) ; "
           "graines %.4e ; essais %.4e\n", nc, np, amoi, bloc, nbloc, graines, essais);
    printf("faux attendus %.3e (%ld/C(80,20) = %.2e par essai)\n",
           essais * (double)nc / 3.5353e18, nc, (double)nc / 3.5353e18);
    fflush(stdout);

    long trouves = 0, faites = 0;
    for (long i = bloc; i < np; i += nbloc) {
        uint64_t deb = P[i].debut, fin = P[i].debut + P[i].longueur;
        for (uint64_t graine = deb; graine < fin; graine++) {
            for (int g = 0; g < NGEN; g++) {
                Etat e;
                amorce(&e, graine);
                for (int s = 0; s < NECH; s++) {
                    Etat e2 = e;
                    uint64_t a, b;
                    if (!engendre(&e2, g, s, &a, &b)) continue;
                    long idx = chercher(a, b);
                    if (idx >= 0) {
                        printf("APPARIEMENT graine %llu generateur %s echantillonneur %s "
                               "cible %ld ts %lld (plage %ld)\n",
                               (unsigned long long)graine, NOMGEN[g], NOMECH[s], idx,
                               (long long)C[idx].ts, i);
                        fflush(stdout);
                        trouves++;
                    }
                }
            }
        }
        if (++faites % 2000 == 0) {
            printf("  ... plage %ld/%ld (%.1f %%)\n", faites, amoi,
                   100.0 * (double)faites / (double)amoi);
            fflush(stdout);
        }
    }
    printf("TERMINE bloc %d/%d : %ld appariement(s) sur %.4e essais\n",
           bloc, nbloc, trouves, essais);
    free(C); free(P); free(Ha); free(Hb); free(Hi);
    return 0;
}
