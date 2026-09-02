/* lfg_crible_classe — le crible de CLASSES pour la lecture par TRONCATURE sous pas variable
 * (THEORIE_ETAT §7.24 ; RAPPORT §172).
 *
 * LE LEMME QUI REND LA CHOSE POSSIBLE.  La classe d'un mot, c(r) = (r * 80) >> 32, n'est
 * pas additive — mais elle l'est A UN BIT PRES :
 *
 *      c(a + b mod 2^32) = c(a) + c(b) + delta   (mod 80),   delta dans {0, 1}
 *
 * (et delta dans {0, -16} pour l'echantillonneur a modulo, ou 2^32 mod 80 = 16).  La suite
 * des classes d'un Fibonacci retarde additif est donc lue par un AUTOMATE NON DETERMINISTE
 * d'etat (Z/80)^L : un bit de branchement par mot.
 *
 * LE LEMME DE LA CLASSE.  Sous le rejet, TOUT mot consomme — accepte ou refuse — a sa classe
 * parmi les vingt valeurs publiees par le tirage qui le contient (un mot accepte publie sa
 * classe ; un mot refuse duplique une classe deja acceptee dans le meme tirage).  C'est deux
 * bits d'elagage par mot, contre un bit de branchement : le front DECROIT.
 *
 * ET L'ALIGNEMENT NE SE BRANCHE PAS.  Le tirage courant se deduit des classes acceptees
 * depuis le debut du bloc : des que vingt classes distinctes ont ete acceptees, le tirage
 * est clos et le suivant commence.  Le pas variable ne coute donc RIEN ici — contrairement
 * aux §7.17-§7.21, ou il coute H(N) = 2,846 bits par tirage.
 *
 * COMPTABILITE.  Mot libre (les L premiers) : +log2(20) = +4,3219 bits.  Mot determine :
 * +1 bit (delta) - 2 bits (classe) = -1 bit.  Le pic du front vaut donc 20^L et le parcours
 * total environ 2,5 x 20^L noeuds.
 *
 * SORTIE.  Zero survivant = la configuration est EXCLUE, exactement (verdict dur, pas un
 * seuil).  Un survivant = un L-uplet de classes a relever (les delta lus sur la solution
 * donnent T demi-espaces sur les parties fractionnaires : CVP resolu par LLL, §7.24 (vii)).
 *
 * LE PLAFOND PAR TIRAGE, ET L'ELAGAGE QUI COMPTE.  Un chemin degenere — beaucoup de refus —
 * ne cloturerait jamais son tirage.  On coupe donc tout chemin dont le tirage courant depasse
 * NMAXD mots, et — c'est le point qui change tout — tout chemin qui ne PEUT PLUS le cloturer :
 * il faut encore 20 - nacc mots acceptants, donc au moins 20 - nacc mots, et
 *
 *      wd + (20 - nacc) > NMAXD   =>   chemin mort.
 *
 * Sans cet elagage le parcours explose sur certains tirages : le facteur de branchement moyen
 * vaut 0,50 (sous-critique) mais un tirage contenant des classes CONSECUTIVES — 25, 26, 27, 28
 * par exemple — cree des poches SURCRITIQUES ou les deux valeurs de delta sont publiees, et un
 * arbre sous-critique en moyenne peut y grossir sans fin.  Mesure : la nuit 20 de l'archive
 * coutait 2,4e9 noeuds au degre 3 contre 2e4 predits.  L'elagage est EXACT — le chemin vrai
 * verifie wd + (20 - nacc) <= N <= NMAXD a chaque instant.  Ce n'est pas une approximation gratuite :
 * P(N > 60) = 1,8e-20, soit 1,3e-15 sur les 70 560 tirages de l'archive.  Le crible reste
 * exact a cette probabilite pres, qui est nommee.
 *
 * usage : lfg_crible_classe K L shift mode f_tirages f_blocs ntir [saut] [nmaxd] [plafond]
 *   mode  : flux (un seul ancrage, au premier tirage) | nuit (un ancrage par bloc)
 *   shift : 0 (x = r) | 1 (x = r >> 1, glibc random())
 *   f_tirages : une ligne par tirage, vingt classes v-1 dans 0..79
 *   f_blocs   : les indices de debut de bloc, un par ligne
 *   ntir      : nombre de tirages qu'un chemin doit CLOTURER pour compter comme survivant
 *   saut      : ne traiter qu'un bloc sur `saut` (mode nuit ; defaut 1)
 *   nmaxd     : plafond de mots par tirage (defaut 60)
 *   plafond   : plafond de noeuds (defaut 2e11)
 *   fixe      : des classes separees par des virgules — les mots 0..n-1 sont FORCES a
 *               ces classes, et l'on ne parcourt que cette branche.  Avec L classes on
 *               force l'etat initial ; avec toute la suite on force le chemin entier, ce
 *               qui rend le verdict instantane.  Sert aux temoins : verifier qu'un etat
 *               plante est retenu, sans enumerer la famille (qui se compte en millions).
 *   chemin    : si le mot "chemin" est passe en 13e argument, chaque survivant est imprime
 *               AVEC TOUTE SA SUITE DE CLASSES (ligne "chem"), et non seulement ses L
 *               premieres.  C'est ce dont le relevement a besoin (§173) : les delta se
 *               lisent sur la suite complete, pas sur l'etat initial.
 *
 * LE MOT DU BONUS (§7.27).  Le bonus de l'archive est TOUJOURS l'un des vingt numeros tires
 * — 70 560 sur 70 560 — donc il n'est pas un vingt-et-unieme numero tire dans 1..80 : c'est un
 * INDEX dans le tirage.  S'il est tire du meme flux, la machine consomme au moins un mot de
 * plus par tirage, et le crible qui l'ignore teste un modele DECALE D'UN MOT PAR TIRAGE : il
 * ne peut pas trouver le vrai generateur, meme s'il est la.  On modelise donc explicitement
 * la phase bonus, avec ces regles (arguments cle=valeur, apres les positionnels) :
 *
 *   bmode=0  aucun mot de bonus (le modele des §172/§174, conserve a l'identique)
 *   bmode=1  UN mot apres les vingt, d'index r = floor(u*20) dans le tableau TRIE.  Comme
 *            floor(x*20/2^32) = floor(c(x)/4), sa classe est contrainte a {4r, ..., 4r+3} :
 *            quatre valeurs sur quatre-vingts, soit 4,32 bits d'elagage EN PLUS par tirage.
 *            La phase bonus ne coute donc pas : elle RAPPORTE.
 *   bmode=2  des mots apres les vingt jusqu'a ce que l'un porte exactement la classe du bonus
 *            (tirage dans 1..80 avec rejet jusqu'a tomber sur un numero deja sorti) ; les mots
 *            intermediaires doivent porter une classe NON acceptee.  Longueur geometrique,
 *            esperance 4 mots.
 *   bmode=3  comme bmode=1, mais l'index porte sur l'ordre d'ACCEPTATION et non sur l'ordre
 *            trie.  Cet ordre est inconnu de l'archive mais CONNU DU CHEMIN : le crible le
 *            reconstruit, donc la contrainte est la meme, 4 classes sur 80.
 *   fsupp=n  n mots supplementaires par tirage, sans aucun test (multiplicateur, jeton, sel).
 *            Chacun coute un facteur ndelta et ne rapporte rien : c'est la borne de tolerance
 *            du §7.24 (xiii) rendue executable.
 *   bonus=f  fichier : une ligne par tirage, « rang classe » (rang du bonus dans le tableau
 *            trie, 0..19 ; classe du bonus, 0..79).  Requis des que bmode > 0.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>
#include <math.h>
#ifdef _OPENMP
#include <omp.h>
#endif

#define POOL 80
#define DRAWN 20
#define NSURV 4096
#define CHEMMAX 12      /* chemins complets imprimes, les plus courts */

static int NT, NB;
static int FIXE[4096], NFIXE = 0;
static int CHEMIN = 0;          /* imprimer la suite de classes complete des survivants */
static unsigned char *PUB;      /* NT x POOL : 1 si la classe est publiee par le tirage */
static unsigned char *LST;      /* NT x DRAWN : la liste des vingt classes publiees */
static int *DEB;                /* debuts de blocs */
static int BMODE = 0, FSUPP = 0;
static int BINDEX = 0;          /* 0 : index = c/4 (troncature) ; 1 : index = c mod 20 (modulo) */
static int ORDONNE = 0;         /* les vingt classes sont donnees DANS L'ORDRE DU TIRAGE */
static int RMAX = -1;           /* refus tolerés parmi les L PREMIERS mots (-1 : aucun plafond)

   En lecture ordonnee, un mot libre a deux emplois : accepter la classe suivante (une
   valeur, LUE) ou refuser en dupliquant une classe deja sortie (nacc valeurs).  Le front
   des L premiers mots vaut donc produit_j (1 + a_j), et c'est lui qui fixe le mur.  Or le
   VRAI chemin a peu de refus dans ses premiers mots : le mot d'indice j est un refus avec
   probabilite a_j/80 <= j/80, d'esperance L(L-1)/160.  Plafonner ce compte a RMAX coupe le
   front de plusieurs ordres de grandeur et ne perd le chemin vrai qu'avec la probabilite —
   CALCULEE EXACTEMENT par l'appelant, pas bornee — que ce compte depasse RMAX. */
static unsigned char *BRANG;    /* NT : rang du bonus dans le tableau trie, 0..19 */
static unsigned char *BCLS;     /* NT : classe du bonus, 0..79 */

/* racine carree SANS libm : le budget global en a besoin une fois au demarrage, et
 * dependre de -lm pour cela rendait le fichier non liable par les appelants qui ne le
 * passent pas — c'est ce qui a casse la reprise de h157 apres un redemarrage.  Newton
 * converge en une dizaine d'iterations, la precision n'a aucune importance ici. */
static double racine(double x)
{
    if (x <= 0.0) return 0.0;
    double r = x > 1.0 ? x : 1.0;
    for (int i = 0; i < 60; i++) r = 0.5 * (r + x / r);
    return r;
}

static double horloge(void)
{
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec + 1e-9 * t.tv_nsec;
}

/* ------------------------------------------------------------------ lecture */

static int lire_tirages(const char *f)
{
    FILE *fp = fopen(f, "r");
    if (!fp) { perror(f); exit(1); }
    int cap = 1024, n = 0;
    unsigned char *pub = malloc((size_t)cap * POOL);
    unsigned char *lst = malloc((size_t)cap * DRAWN);
    char ligne[512];
    while (fgets(ligne, sizeof ligne, fp)) {
        if (n == cap) {
            cap *= 2;
            pub = realloc(pub, (size_t)cap * POOL);
            lst = realloc(lst, (size_t)cap * DRAWN);
        }
        memset(pub + (size_t)n * POOL, 0, POOL);
        char *p = ligne;
        int k = 0;
        while (k < DRAWN) {
            while (*p == ' ' || *p == '\t') p++;
            if (*p < '0' || *p > '9') break;
            int v = (int)strtol(p, &p, 10);
            if (v < 0 || v >= POOL) { fprintf(stderr, "classe hors bornes : %d\n", v); exit(1); }
            pub[(size_t)n * POOL + v] = 1;
            lst[(size_t)n * DRAWN + k] = (unsigned char)v;
            k++;
        }
        if (k == 0) continue;
        if (k != DRAWN) { fprintf(stderr, "tirage %d : %d classes\n", n, k); exit(1); }
        n++;
    }
    fclose(fp);
    PUB = pub; LST = lst;
    return n;
}

static void lire_bonus(const char *f, int nt)
{
    FILE *fp = fopen(f, "r");
    if (!fp) { perror(f); exit(1); }
    BRANG = malloc((size_t)nt); BCLS = malloc((size_t)nt);
    char ligne[64];
    int n = 0;
    while (n < nt && fgets(ligne, sizeof ligne, fp)) {
        int r, c;
        if (sscanf(ligne, "%d %d", &r, &c) != 2) continue;
        if (r < 0 || r >= DRAWN || c < 0 || c >= POOL) {
            fprintf(stderr, "bonus ligne %d hors bornes : %d %d\n", n, r, c); exit(1);
        }
        BRANG[n] = (unsigned char)r; BCLS[n] = (unsigned char)c; n++;
    }
    fclose(fp);
    if (n != nt) { fprintf(stderr, "bonus : %d lignes pour %d tirages\n", n, nt); exit(1); }
}

static int lire_blocs(const char *f, int nt)
{
    FILE *fp = fopen(f, "r");
    if (!fp) { perror(f); exit(1); }
    int cap = 1024, n = 0;
    int *d = malloc((size_t)cap * sizeof *d);
    char ligne[64];
    while (fgets(ligne, sizeof ligne, fp)) {
        if (n == cap) { cap *= 2; d = realloc(d, (size_t)cap * sizeof *d); }
        d[n++] = (int)strtol(ligne, NULL, 10);
    }
    fclose(fp);
    (void)nt;
    DEB = d;
    return n;
}

/* ------------------------------------------------------------------ le crible */

typedef struct {
    int K, L, nmax, ndelta, nmaxd, ntir, budget;
    int delta[4];
    int tfin;                   /* dernier tirage utilisable (exclus) */
    long long plafond;
} Reglage;

typedef struct {
    long long noeuds, coupes;
    int surv;
    int dmax;                   /* plus grand nombre de tirages CLOTURES par un chemin */
    unsigned char sol[64];      /* le premier survivant, ses L classes */
    unsigned char (*tous)[64];  /* jusqu'a NSURV survivants, pour les temoins */
    int *lg;                    /* longueur (en mots) du chemin de chaque survivant */
    int ntous, pire, ipire;     /* le plus long des survivants gardes, et son indice */
    unsigned char *chems;       /* suite de classes complete de CHAQUE survivant garde */
    long long *front;           /* front[i] : noeuds poses a la profondeur i */
} Bilan;

/* DFS iteratif : pile explicite, un cadre par mot pose. */
typedef struct {
    unsigned char cand[POOL];       /* candidats restants a cette profondeur */
    short ncand, icand;
    int d;                          /* tirage courant AVANT ce mot */
    int ds;                         /* profondeur du PREMIER mot du tirage courant */
    short wd;                       /* mots deja consommes dans le tirage courant */
    unsigned char nacc;             /* classes acceptees dans le tirage courant */
    unsigned char ph;               /* 0 = les vingt ; 1 = le bonus ; 2 = les mots muets */
    unsigned char ns;               /* mots muets deja consommes */
    short rl;                       /* refus parmi les mots d'indice < L */
    uint64_t acc0, acc1;            /* bitmap des classes acceptees (0..63, 64..79) */
} Cadre;

/* la classe `v` est-elle admissible pour un mot pose dans la phase `ph` du tirage `d` ?
 * `q` : l'index du bonus dans l'ordre d'ACCEPTATION (bmode 3), calcule par l'appelant. */
static inline int deja_pris(uint64_t a0, uint64_t a1, int v)
{
    return (v < 64) ? (int)((a0 >> v) & 1) : (int)((a1 >> (v - 64)) & 1);
}

static inline int autorise(int ph, int d, int v, uint64_t a0, uint64_t a1, int q, int nacc)
{
    if (ph == 0) {
        /* LECTURE ORDONNEE.  Quand le tirage est publie DANS SON ORDRE, la classe du
         * prochain mot accepte n'est plus a deviner parmi vingt : elle est LUE.  Il ne
         * reste que le choix « accepter la prochaine, ou refuser en dupliquant une classe
         * deja sortie » — 1 + nacc valeurs au lieu de 20.  C'est ce qui fait passer le seuil
         * du theoreme du tirage unitaire de 6,95 a 18,43 (THEORIE_ETAT §7.27 (iii)). */
        if (ORDONNE)
            return v == LST[(size_t)d * DRAWN + nacc] || deja_pris(a0, a1, v);
        return PUB[(size_t)d * POOL + v];
    }
    if (ph == 2) return 1;
    /* l'index que le mot du bonus porte depend de l'echantillonneur : sous la
     * troncature floor(x*20/2^32) = floor(c/4) ; sous le modulo x mod 20 = c mod 20. */
    if (ph == 3) return (BINDEX ? (v % DRAWN) : (v >> 2)) == BRANG[d];
    if (BMODE == 1) return (BINDEX ? (v % DRAWN) : (v >> 2)) == BRANG[d];
    if (BMODE == 3) return (BINDEX ? (v % DRAWN) : (v >> 2)) == q;
    /* bmode 2 : soit le bonus lui-meme, soit un refus (classe non encore acceptee) */
    if (v == BCLS[d]) return 1;
    return !deja_pris(a0, a1, v);
}

/* prem >= 0 : ne parcourir que la branche dont le premier mot porte la classe LST[t0][prem] */
static void crible_bloc(const Reglage *R, int t0, Bilan *B, int prem)
{
    const int L = R->L, K = R->K, nmax = R->nmax;
    Cadre *pile = malloc((size_t)(nmax + 2) * sizeof *pile);
    unsigned char *hist = malloc((size_t)(nmax + 2));
    int prof = 0;

    /* cadre initial : le premier mot du bloc, tirage t0, rien d'accepte */
    Cadre *c = &pile[0];
    c->d = t0; c->nacc = 0; c->wd = 0; c->acc0 = c->acc1 = 0;
    c->ph = (BMODE == 4) ? 3 : 0; c->ns = 0; c->ds = 0; c->rl = 0;
    c->ncand = DRAWN; c->icand = 0;
    if (t0 >= R->tfin) { free(pile); free(hist); return; }
    if (NFIXE) { c->cand[0] = (unsigned char)FIXE[0]; c->ncand = 1; }
    else if (ORDONNE) { c->cand[0] = LST[(size_t)t0 * DRAWN]; c->ncand = 1; }
    else if (BMODE == 4) {
        /* Au bmode 4 le PREMIER mot du tirage est celui du bonus : sa classe n'a aucune
         * raison d'etre publiee — elle doit seulement porter le bon index.  L'ancrage par
         * classe publiee, correct pour les autres regles, ecartait donc le chemin vrai des
         * le mot zero.  On enumere ici les classes admissibles de la phase 3. */
        int n = 0;
        for (int v = 0; v < POOL; v++)
            if (autorise(3, t0, v, 0, 0, -1, 0)) c->cand[n++] = (unsigned char)v;
        c->ncand = (short)n;
    }
    else if (prem >= 0) { c->cand[0] = LST[(size_t)t0 * DRAWN + prem]; c->ncand = 1; }
    else memcpy(c->cand, LST + (size_t)t0 * DRAWN, DRAWN);

    while (prof >= 0) {
        Cadre *f = &pile[prof];
        if (f->icand >= f->ncand) { prof--; continue; }
        int cl = f->cand[(int)f->icand++];
        B->noeuds++;
        if (B->front) B->front[prof]++;
        if (B->noeuds > R->plafond) { B->coupes++; break; }
        hist[prof] = (unsigned char)cl;

        /* etat apres avoir pose ce mot : accepte ou refuse ? */
        int d = f->d, nacc = f->nacc, wd = f->wd + 1;
        int ph = f->ph, ns = f->ns, ds = f->ds;
        int rl = f->rl;
        uint64_t a0 = f->acc0, a1 = f->acc1;
        int ferme = 0, mort = 0;
        if (RMAX >= 0 && prof < L && ph == 0 && deja_pris(a0, a1, cl)) rl++;
        if (ph == 3) {
            ph = 0;                        /* le mot du bonus, deja teste a la generation */
        } else if (ph == 0) {
            int deja = (cl < 64) ? (int)((a0 >> cl) & 1) : (int)((a1 >> (cl - 64)) & 1);
            if (!deja) {
                if (cl < 64) a0 |= (uint64_t)1 << cl; else a1 |= (uint64_t)1 << (cl - 64);
                nacc++;
                if (nacc == DRAWN) {
                    ph = (BMODE && BMODE != 4) ? 1 : 2;
                    if (ph == 2 && FSUPP == 0) ferme = 1;
                }
            }
        } else if (ph == 1) {
            if (BMODE == 2) {
                if (cl == BCLS[d]) { ph = 2; if (FSUPP == 0) ferme = 1; }
                else if ((cl < 64) ? ((a0 >> cl) & 1) : ((a1 >> (cl - 64)) & 1)) mort = 1;
                /* sinon : un refus de plus dans la phase bonus, on y reste */
            } else {                       /* bmode 1 ou 3 : un seul mot, deja teste */
                ph = 2; if (FSUPP == 0) ferme = 1;
            }
        } else {                           /* ph == 2 : les mots muets */
            ns++;
            if (ns >= FSUPP) ferme = 1;
        }
        if (mort) continue;
        if (ferme && d + 1 - t0 > B->dmax) B->dmax = d + 1 - t0;
        if (ferme) { d++; nacc = 0; wd = 0; a0 = a1 = 0; ns = 0; ds = prof + 1;
                     ph = (BMODE == 4) ? 3 : 0; }
        /* tirage interminable, ou deja hors d'atteinte : chemin mort */
        if (wd + (DRAWN - nacc) > R->nmaxd) continue;
        /* BUDGET GLOBAL : le chemin vrai consomme E[N] = 22,85 mots par tirage, un faux —
         * collectionneur sur les 20 classes publiees — 71,96.  Le total est donc lui aussi
         * un discriminant, et a huit ecarts-types il ne coute rien au vrai chemin. */
        /* Le reste MINIMAL est (20 - nacc) mots pour le tirage courant — pas vingt : dix-neuf
         * classes peuvent deja y etre acceptees — puis vingt par tirage encore a ouvrir.
         * Compter vingt pour le tirage courant surestime le reste de dix-neuf mots et rend
         * l'elagage TROP AGRESSIF : il rabote le budget d'autant et peut tuer le chemin vrai.
         * Mesure : (1,6) au decalage 1, deux tirages ordonnes, le vrai chemin mourait sur son
         * DERNIER mot.  Sur les grilles a ntir = 25 le budget effectif tombait de 8 a 6,8
         * ecarts-types, soit 6e-12 par ancrage au lieu de 1e-15 — sans effet sur leur verdict,
         * mais faux. */
        int reste = (d - t0 >= R->ntir) ? 0
                  : (DRAWN - nacc) + (R->ntir - (d - t0) - 1) * DRAWN;
        if (R->budget > 0 && prof + 1 + reste > R->budget) continue;

        int prochain = prof + 1;
        if (prochain >= nmax || d >= R->tfin || d - t0 >= R->ntir) {     /* survivant */
            if (B->surv == 0) memcpy(B->sol, hist, (size_t)L);
            /* On ne garde pas les PREMIERS survivants mais les PLUS COURTS : le chemin vrai
             * consomme E[N] = 22,85 mots par tirage, un chemin faux — collectionneur sur les
             * 20 classes publiees — en consomme 71,96 en moyenne.  La longueur totale est
             * donc un rang, et le vrai chemin y est quasi minimal (mesure : 345 mots contre
             * un minimum de 344 sur 2,1 millions de chemins).  Sans ce tri, le vrai chemin
             * est noye : il est RARE en nombre de chemins, meme s'il est court. */
            if (B->tous) {
                if (B->ntous < NSURV) {
                    memcpy(B->tous[B->ntous], hist, (size_t)L);
                    B->lg[B->ntous] = prochain;
                    if (B->chems) memcpy(B->chems + (size_t)B->ntous * (nmax + 2), hist,
                                         (size_t)prochain);
                    if (prochain > B->pire) { B->pire = prochain; B->ipire = B->ntous; }
                    B->ntous++;
                } else if (prochain < B->pire) {
                    memcpy(B->tous[B->ipire], hist, (size_t)L);
                    B->lg[B->ipire] = prochain;
                    if (B->chems) memcpy(B->chems + (size_t)B->ipire * (nmax + 2), hist,
                                         (size_t)prochain);
                    B->pire = -1;
                    for (int u = 0; u < NSURV; u++)
                        if (B->lg[u] > B->pire) { B->pire = B->lg[u]; B->ipire = u; }
                }
            }
            B->surv++;
            continue;
        }

        /* candidats du mot suivant */
        Cadre *g = &pile[prochain];
        g->d = d; g->nacc = (unsigned char)nacc; g->wd = (short)wd; g->acc0 = a0; g->acc1 = a1;
        g->ph = (unsigned char)ph; g->ns = (unsigned char)ns; g->ds = ds;
        g->rl = (short)rl;
        g->icand = 0;
        /* bmode 3 : l'index du bonus dans l'ordre d'ACCEPTATION.  L'archive ne le publie pas,
         * mais le chemin le reconstruit — on le relit sur les mots du tirage courant. */
        int q = -1;
        if (BMODE == 3 && ph == 1) {
            uint64_t v0 = 0, v1 = 0;
            int r = 0, cible = BCLS[d];
            for (int i = ds; i <= prof; i++) {
                int u = hist[i];
                int vu = (u < 64) ? (int)((v0 >> u) & 1) : (int)((v1 >> (u - 64)) & 1);
                if (vu) continue;
                if (u < 64) v0 |= (uint64_t)1 << u; else v1 |= (uint64_t)1 << (u - 64);
                if (u == cible) { q = r; break; }
                r++;
            }
            if (q < 0) continue;           /* le bonus n'est pas dans le tirage reconstruit */
        }
        if (NFIXE > prochain) {
            /* mot force : il doit etre admissible, et — au-dela de L — compatible avec la
             * recurrence (c'est exactement le test du chemin vrai). */
            int v = FIXE[prochain], bon = autorise(ph, d, v, a0, a1, q, nacc);
            if (bon && prochain >= L) {
                int base = hist[prochain - K] + hist[prochain - L], vu = 0;
                for (int e = 0; e < R->ndelta; e++) {
                    int w = (base + R->delta[e]) % POOL; if (w < 0) w += POOL;
                    if (w == v) { vu = 1; break; }
                }
                bon = vu;
            }
            g->cand[0] = (unsigned char)v;
            g->ncand = bon ? 1 : 0;
        } else if (prochain < L) {
            if (ph == 0 && !ORDONNE) {
                g->ncand = DRAWN;
                memcpy(g->cand, LST + (size_t)d * DRAWN, DRAWN);
            } else if (ph == 0 && ORDONNE && RMAX >= 0 && rl >= RMAX) {
                g->cand[0] = LST[(size_t)d * DRAWN + nacc];   /* plus droit au refus */
                g->ncand = 1;
            } else {
                int n = 0;
                for (int v = 0; v < POOL; v++)
                    if (autorise(ph, d, v, a0, a1, q, nacc)) g->cand[n++] = (unsigned char)v;
                g->ncand = (short)n;
            }
        } else {
            int base = hist[prochain - K] + hist[prochain - L];
            int n = 0;
            for (int e = 0; e < R->ndelta; e++) {
                int v = base + R->delta[e];
                v %= POOL; if (v < 0) v += POOL;
                int vu = 0;
                for (int j = 0; j < n; j++) if (g->cand[j] == v) { vu = 1; break; }
                if (!vu && autorise(ph, d, v, a0, a1, q, nacc)) g->cand[n++] = (unsigned char)v;
            }
            g->ncand = (short)n;
        }
        prof = prochain;
    }
    free(pile); free(hist);
}

int main(int argc, char **argv)
{
    if (argc < 8) {
        fprintf(stderr, "usage: %s K L shift mode f_tirages f_blocs nmax [saut] [plafond]\n", argv[0]);
        return 2;
    }
    Reglage R;
    R.K = atoi(argv[1]); R.L = atoi(argv[2]);
    int shift = atoi(argv[3]);
    const char *mode = argv[4];
    NT = lire_tirages(argv[5]);
    NB = lire_blocs(argv[6], NT);
    R.ntir = atoi(argv[7]);
    int saut = (argc > 8) ? atoi(argv[8]) : 1;
    R.nmaxd = (argc > 9) ? atoi(argv[9]) : 60;
    R.plafond = (argc > 10) ? atoll(argv[10]) : 200000000000LL;
    if (argc > 12 && strcmp(argv[12], "chemin") == 0) CHEMIN = 1;
    if (argc > 11 && argv[11][0] && !strchr(argv[11], '=') && strcmp(argv[11], "chemin") != 0) {
        char *q = argv[11];
        while (NFIXE < 4096 && *q) { FIXE[NFIXE++] = (int)strtol(q, &q, 10); if (*q == ',') q++; }
        if (NFIXE < R.L) { fprintf(stderr, "fixe : %d classes, il en faut au moins L = %d\n", NFIXE, R.L); return 2; }
    }
    const char *fbonus = NULL, *fdelta = NULL;
    for (int i = 8; i < argc; i++) {
        if (!strncmp(argv[i], "bmode=", 6)) BMODE = atoi(argv[i] + 6);
        else if (!strncmp(argv[i], "fsupp=", 6)) FSUPP = atoi(argv[i] + 6);
        else if (!strncmp(argv[i], "bonus=", 6)) fbonus = argv[i] + 6;
        else if (!strncmp(argv[i], "ordonne=", 8)) ORDONNE = atoi(argv[i] + 8);
        else if (!strncmp(argv[i], "delta=", 6)) fdelta = argv[i] + 6;
        else if (!strncmp(argv[i], "rmax=", 5)) RMAX = atoi(argv[i] + 5);
        else if (!strncmp(argv[i], "bindex=", 7)) BINDEX = atoi(argv[i] + 7);
    }
    if (BMODE < 0 || BMODE > 4 || FSUPP < 0 || FSUPP > 8) {
        fprintf(stderr, "bmode dans 0..4, fsupp dans 0..8\n"); return 2;
    }
    if (BMODE && !fbonus) { fprintf(stderr, "bmode > 0 exige bonus=fichier\n"); return 2; }
    if (fbonus) lire_bonus(fbonus, NT);
    R.nmax = R.ntir * R.nmaxd + R.L + 2;
    {   /* budget global a huit ecarts-types de la loi du vrai chemin.  La phase bonus
         * ajoute sa propre esperance et sa propre variance : un mot exactement aux bmode
         * 1 et 3, une geometrique de parametre 1/4 au bmode 2 (esperance 4, variance 12). */
        double m = 22.8487, v = 3.4318;                 /* 1,8525^2 */
        if (BMODE == 1 || BMODE == 3 || BMODE == 4) m += 1.0;
        else if (BMODE == 2) { m += 4.0; v += 12.0; }
        m += FSUPP;
        R.budget = (int)(m * R.ntir + 8.0 * racine(v * R.ntir)) + R.L + 2;
    }
    if (R.K <= 0 || R.L <= R.K || R.L > 60) { fprintf(stderr, "K, L invalides\n"); return 2; }

    /* delta : {0,1} dans les deux cas.  Au shift 1 le bit perdu peut en principe ajouter
     * une unite de plus (delta = 2), mais seulement si la partie fractionnaire tombe a
     * 80/2^31 = 3,7e-8 pres d'un entier : sur les ~571 mots d'un ancrage, la probabilite
     * de perdre le vrai chemin vaut 2,1e-5, et elle est NOMMEE.  La garder coutait un
     * facteur 1 500 sur les ancrages difficiles (mesure : (1,3) shift 1 passe de 3,0e7 a
     * 2,0e4 noeuds), parce que log2(3) = 1,585 bit de branchement contre 2 bits d'elagage
     * ne laisse que 0,415 bit de decroissance par mot au lieu de 1. */
    R.delta[0] = 0; R.delta[1] = 1;
    R.ndelta = 2;
    if (fdelta) {           /* delta=0,-16 pour l'echantillonneur a modulo (2^32 mod 80 = 16) */
        char *q = (char *)fdelta;
        R.ndelta = 0;
        while (R.ndelta < 4 && *q) {
            R.delta[R.ndelta++] = (int)strtol(q, &q, 10);
            if (*q == ',') q++;
        }
        if (R.ndelta < 1) { fprintf(stderr, "delta vide\n"); return 2; }
    }

    int nuit = (strcmp(mode, "nuit") == 0);
    /* en flux, scission sur la classe du 1er mot ; en lecture ORDONNEE ce mot est LU,
     * donc il n'y a rien a scinder. */
    int nanc = nuit ? NB : ((NFIXE || ORDONNE || BMODE == 4) ? 1 : DRAWN);
    double t0 = horloge();

    long long noeuds = 0, coupes = 0;
    int surv = 0, bmax = -1, dmax = 0;
    long long pic = 0;
    unsigned char sol[64]; memset(sol, 0, sizeof sol);

#ifdef _OPENMP
#pragma omp parallel for schedule(dynamic, 1) reduction(+:noeuds, coupes, surv)
#endif
    for (int b = 0; b < nanc; b++) {
        if (nuit && (b % saut)) continue;
        Reglage r = R;
        int anc = nuit ? DEB[b] : 0;
        r.tfin = nuit ? ((b + 1 < NB) ? DEB[b + 1] : NT) : NT;
        Bilan B; memset(&B, 0, sizeof B); B.pire = -1;
        B.front = calloc((size_t)R.nmax + 2, sizeof *B.front);
        B.tous = malloc((size_t)NSURV * 64);
        B.lg = malloc((size_t)NSURV * sizeof(int));
        B.chems = CHEMIN ? malloc((size_t)NSURV * (R.nmax + 2)) : NULL;
        crible_bloc(&r, anc, &B, nuit ? -1 : b);
        noeuds += B.noeuds; coupes += B.coupes; surv += B.surv;
        long long p = 0;
        for (int i = 0; i <= R.nmax; i++) if (B.front[i] > p) p = B.front[i];
#ifdef _OPENMP
#pragma omp critical
#endif
        {
            if (p > pic) pic = p;
            if (B.dmax > dmax) dmax = B.dmax;
            if (B.surv && bmax < 0) { bmax = b; memcpy(sol, B.sol, (size_t)R.L); }
            if (CHEMIN && B.chems) {
                /* les CHEMMAX plus COURTS : le chemin vrai est quasi minimal (lemme du
                 * contraste de collectionneur), donc c'est la qu'il faut le chercher. */
                int ord[CHEMMAX], no = 0;
                for (int u = 0; u < B.ntous; u++) {
                    int j = no;
                    while (j > 0 && B.lg[ord[j - 1]] > B.lg[u]) { if (j < CHEMMAX) ord[j] = ord[j - 1]; j--; }
                    if (j < CHEMMAX) { ord[j] = u; if (no < CHEMMAX) no++; }
                }
                for (int k = 0; k < no; k++) {
                    int u = ord[k];
                    printf("chem %d %d", nuit ? b : 0, B.lg[u]);
                    for (int i = 0; i < B.lg[u]; i++)
                        printf(" %d", B.chems[(size_t)u * (R.nmax + 2) + i]);
                    printf("\n");
                }
            }
            for (int u = 0; u < B.ntous; u++) {
                printf("surv %d %d", nuit ? b : 0, B.lg ? B.lg[u] : -1);
                for (int i = 0; i < R.L; i++) printf(" %d", B.tous[u][i]);
                printf("\n");
            }
        }
        free(B.front); free(B.tous); free(B.chems); free(B.lg);
    }

    double sec = horloge() - t0;
    printf("bmode %d fsupp %d ordonne %d ndelta %d rmax %d budget %d dmax %d\n",
           BMODE, FSUPP, ORDONNE, R.ndelta, RMAX, R.budget, dmax);
    printf("K %d L %d shift %d mode %s ancrages %d tirages %d nmaxd %d fils %d\n", R.K, R.L, shift, mode,
           nuit ? (NB + saut - 1) / saut : 1, R.ntir, R.nmaxd,
#ifdef _OPENMP
           omp_get_max_threads()
#else
           1
#endif
           );
    printf("noeuds %lld pic %lld survivants %d coupes %lld bloc %d sec %.2f\n",
           noeuds, pic, surv, coupes, bmax, sec);
    if (surv) {
        printf("sol");
        for (int i = 0; i < R.L; i++) printf(" %d", sol[i]);
        printf("\n");
    }
    return 0;
}
