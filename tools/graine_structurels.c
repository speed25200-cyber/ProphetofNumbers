/* graine_structurels.c — LES QUATRE ECHANTILLONNEURS QUE LE §211 NOMME SANS LES TESTER.
 *
 * CE QUE LE §211 LAISSE OUVERT, ET LE DIT
 * =======================================
 * Le §211 balaie 2^32 graines x 5 generateurs x 6 echantillonneurs. Ses six
 * echantillonneurs partagent tous une meme forme : ils reduisent UN mot a UNE classe, et
 * repetent avec rejet des doublons jusqu'a en tenir vingt. La section conclut elle-meme :
 *
 *   « Six n'est pas tous. Un Fisher-Yates partiel sur un tableau de quatre-vingts, un
 *     tirage par ordre de tri de quatre-vingts cles aleatoires, un rejet sur un intervalle
 *     decale — chacun est un septieme cas. »
 *
 * Voici ces cas. Ils ne sont pas des variantes : ils ont une STRUCTURE differente, et
 * consomment un nombre de mots different.
 *
 *   0  FISHER-YATES PARTIEL, MODULO      exactement 20 mots, AUCUN rejet
 *   1  FISHER-YATES PARTIEL, TRONCATURE  exactement 20 mots, AUCUN rejet
 *   2  TRI DE 80 CLES                    exactement 80 mots, AUCUN rejet
 *   3  SELECTION SEQUENTIELLE (Knuth S)  au plus 80 mots, AUCUN rejet
 *
 * POURQUOI C'EST PLUS QU'UNE COUVERTURE DE PLUS
 * =============================================
 * Le §7.33 etablit que la GIGUE du rejet — le nombre de mots consommes par tirage varie
 * autour de E[N] = 22,8487 — desaligne le flux et rend invisible toute relation creuse a
 * l'echelle du tirage. C'est l'argument central qui protege les generateurs modernes dans
 * ce dossier.
 *
 * Cet argument NE S'APPLIQUE PAS a ces quatre-la. Le Fisher-Yates partiel consomme
 * exactement vingt mots par tirage, le tri de cles exactement quatre-vingts : le pas est
 * CONSTANT, la gigue est nulle, l'alignement est exact pour toujours. Si la machine
 * echantillonne ainsi, non seulement le balayage de graine peut apparier, mais toute la
 * famille d'attaques par alignement que le §7.33 avait declarees mortes redevient vivante.
 *
 * Le reste — les cinq generateurs, la table de hachage des 70 560 masques — est celui de
 * `graine_exhaustive.c`, INCLUS et non recopie.
 *
 * USAGE
 *   graine_structurels cibles.bin debut fin
 */

#define SANS_MAIN
#include "graine_exhaustive.c"

#define NSTR 4
static const char *NOMSTR[NSTR] = {
    "Fisher-Yates modulo", "Fisher-Yates troncature", "tri de 80 cles",
    "selection sequentielle"
};

static const unsigned char IDENT[POOL] = {
     0, 1, 2, 3, 4, 5, 6, 7, 8, 9,10,11,12,13,14,15,16,17,18,19,
    20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,
    40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,
    60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79
};

static void poser(uint64_t *a, uint64_t *b, int c)
{
    if (c < 64) *a |= 1ULL << c; else *b |= 1ULL << (c - 64);
}

/* Renvoie 1 si les vingt classes ont ete produites. Chaque regle est SANS rejet, donc
   elle aboutit toujours ; le booleen est garde pour l'homogeneite avec `engendre`. */
static int engendre_struct(Etat *e, int g, int s, uint64_t *m0, uint64_t *m1)
{
    uint64_t a = 0, b = 0;

    if (s == 0 || s == 1) {                      /* Fisher-Yates partiel : 20 mots */
        unsigned char tab[POOL];
        memcpy(tab, IDENT, POOL);
        for (int j = 0; j < DRAWN; j++) {
            uint32_t w = suivant(e, g);
            unsigned reste = (unsigned)(POOL - j);
            int k = j + (int)(s == 0 ? (w % reste)
                                     : (uint32_t)(((uint64_t)w * reste) >> 32));
            unsigned char t = tab[j]; tab[j] = tab[k]; tab[k] = t;
            poser(&a, &b, tab[j]);
        }
    } else if (s == 2) {                         /* tri de 80 cles : 80 mots */
        uint32_t bv[DRAWN];
        int bi[DRAWN], m = 0;
        for (int i = 0; i < POOL; i++) {
            uint32_t v = suivant(e, g);
            if (m < DRAWN) {
                int p = m++;
                while (p > 0 && bv[p - 1] > v) { bv[p] = bv[p-1]; bi[p] = bi[p-1]; p--; }
                bv[p] = v; bi[p] = i;
            } else if (v < bv[DRAWN - 1]) {
                int p = DRAWN - 1;
                while (p > 0 && bv[p - 1] > v) { bv[p] = bv[p-1]; bi[p] = bi[p-1]; p--; }
                bv[p] = v; bi[p] = i;
            }
        }
        if (m < DRAWN) return 0;
        for (int j = 0; j < DRAWN; j++) poser(&a, &b, bi[j]);
    } else {                                     /* selection sequentielle (Knuth S) */
        int m = 0;
        for (int i = 0; i < POOL && m < DRAWN; i++) {
            uint32_t w = suivant(e, g);
            /* retenir i avec probabilite (20 - m)/(80 - i), en entiers exacts */
            if ((uint64_t)w * (uint64_t)(POOL - i) < ((uint64_t)(DRAWN - m) << 32)) {
                poser(&a, &b, i);
                m++;
            }
        }
        if (m < DRAWN) return 0;
    }
    *m0 = a; *m1 = b;
    return 1;
}

int main(int argc, char **argv)
{
    if (argc < 4) {
        fprintf(stderr, "usage: %s cibles.bin debut fin\n", argv[0]);
        return 2;
    }
    FILE *f = fopen(argv[1], "rb");
    if (!f) { perror("cibles"); return 2; }
    fseek(f, 0, SEEK_END);
    long nc = ftell(f) / (long)sizeof(Cible);
    fseek(f, 0, SEEK_SET);
    Cible *C = malloc((size_t)nc * sizeof(Cible));
    if (fread(C, sizeof(Cible), (size_t)nc, f) != (size_t)nc) {
        fprintf(stderr, "lecture incomplete\n"); return 2;
    }
    fclose(f);

    uint64_t taille = 1;
    while (taille < (uint64_t)nc * 4) taille <<= 1;
    HMASK = taille - 1;
    Ha = calloc(taille, sizeof(uint64_t));
    Hb = calloc(taille, sizeof(uint64_t));
    Hi = calloc(taille, sizeof(long));
    for (long i = 0; i < nc; i++) inserer(C[i].m0, C[i].m1, i);

    unsigned long long deb = strtoull(argv[2], NULL, 10);
    unsigned long long fin = strtoull(argv[3], NULL, 10);
    double essais = (double)(fin - deb) * NGEN * NSTR;
    printf("cibles %ld ; table 2^%d ; graines [%llu, %llu) ; essais %.4e\n",
           nc, __builtin_ctzll(taille), deb, fin, essais);
    printf("faux attendus %.3e (%ld/C(80,20) = %.2e par essai)\n",
           essais * (double)nc / 3.5353e18, nc, (double)nc / 3.5353e18);
    fflush(stdout);

    long trouves = 0;
    unsigned long long jalon = deb;
    for (unsigned long long graine = deb; graine < fin; graine++) {
        for (int g = 0; g < NGEN; g++) {
            Etat e;
            amorce(&e, graine);
            for (int s = 0; s < NSTR; s++) {
                Etat e2 = e;
                uint64_t a, b;
                if (!engendre_struct(&e2, g, s, &a, &b)) continue;
                long idx = chercher(a, b);
                if (idx >= 0) {
                    printf("APPARIEMENT graine %llu generateur %s echantillonneur %s "
                           "cible %ld ts %lld\n", graine, NOMGEN[g], NOMSTR[s],
                           idx, (long long)C[idx].ts);
                    fflush(stdout);
                    trouves++;
                }
            }
        }
        if (graine - jalon >= 50000000ULL) {
            jalon = graine;
            printf("  ... graine %llu (%.1f %%)\n", graine,
                   100.0 * (double)(graine - deb) / (double)(fin - deb));
            fflush(stdout);
        }
    }
    printf("TERMINE [%llu, %llu) : %ld appariement(s) sur %.4e essais\n",
           deb, fin, trouves, essais);
    free(C); free(Ha); free(Hb); free(Hi);
    return 0;
}
