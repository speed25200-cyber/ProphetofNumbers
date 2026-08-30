"""h55 — la fuite est un accident arithmetique de la taille du vivier.

Deux questions, une negative et une structurelle
================================================
(1) Le §69 compte 80 bits par tirage sous rejet modulo 80 : 4 bits x 20
    numeros ACCEPTES. Il ignore les ~2,85 mots REJETES par tirage. Jetait-on
    de l'information ?

(2) Le theoreme du §68 existe parce que 80 = 16 x 5 est divisible par 16.
    De quoi depend-il exactement, et un vivier de taille voisine
    changerait-il quelque chose ?

La reponse a (1) est NON, et c'est un resultat negatif qui VALIDE le §69
plutot que de le corriger. La reponse a (2) est que la vulnerabilite est
totale ou nulle selon la PARITE du vivier, ce qui en fait un accident
arithmetique et non une propriete du jeu.

Il ne teste pas l'archive : il derive. Registre : inchange.
"""

import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

T0 = time.time()
POOL, DRAWN = 80, 20


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def v2(n):
    k = 0
    while n and n % 2 == 0:
        n //= 2
        k += 1
    return k


def rejection_bits(pool=POOL, drawn=DRAWN):
    """Rejet modulo `pool` : tous les numeros passent par le meme module."""
    return drawn * v2(pool)


def fy_bits(pool=POOL, drawn=DRAWN):
    """Fisher-Yates : le pas i tire modulo pool - i."""
    return sum(v2(pool - i) for i in range(drawn))


# ==========================================================================
rule("1. LES MOTS REJETÉS PORTENT-ILS QUELQUE CHOSE ?")
# ==========================================================================

say(f"""   Un mot est rejete exactement quand out mod {POOL} + 1 est DEJA VU. A
   l'etape k (k numeros acceptes), cela contraint out mod {POOL} a k valeurs sur
   {POOL}, donc out mod 16 a au plus min(k, 16) valeurs sur 16 :

       information d'un rejet a l'etape k = 4 - log2(min(k, 16)) bits

   et il y a en moyenne k/({POOL}-k) rejets a cette etape.
""")
say(f"   {'étape k':>8} {'rejets attendus':>16} {'candidats':>10} {'bits gagnés':>12} {'contribution':>13}")
tot_rej = tot_bits = 0.0
for k in range(DRAWN):
    r = k / (POOL - k)
    cand = min(k, 16)
    bits = 4 - math.log2(cand) if cand >= 1 else 0.0
    tot_rej += r
    tot_bits += r * bits
    if k in (1, 2, 5, 10, 15, 19):
        say(f"   {k:>8} {r:>16.4f} {cand:>10} {bits:>12.3f} {r * bits:>13.4f}")

acc = DRAWN * v2(POOL)
say(f"""
     rejets attendus par tirage   {tot_rej:.4f}
     mots consommes par tirage    {DRAWN + tot_rej:.4f}
     bits des ACCEPTES            {acc}
     bits des REJETES             {tot_bits:.2f}
     total                        {acc + tot_bits:.2f}   soit +{tot_bits / acc:.1%}

   LA REPONSE EST NON, et elle est nette. Les rejets arrivent TARD — leur
   frequence croit en k/({POOL}-k) — et c'est precisement quand ils sont
   frequents que l'ambiguite les vide : a k = 16 numeros deja vus, un rejet
   ne dit plus rien du tout sur out mod 16, puisque les 16 residus sont tous
   candidats.

   Le §69 avait donc raison a 1,6 % pres, et exploiter les rejets
   multiplierait l'arbre de recherche par une dizaine par rejet — {tot_rej:.2f} par
   tirage — pour {tot_bits:.2f} bit. C'est un mauvais echange, et le chiffrer etait
   la seule facon de le savoir.""")


# ==========================================================================
rule("2. DE QUOI LA FUITE DÉPEND-ELLE ?")
# ==========================================================================

say(f"""   Le theoreme du §68 dit : un modulo par n publie v2(n) bits. Sous rejet,
   TOUS les numeros passent par le meme module, donc

       fuite = {DRAWN} x v2(vivier)

   Elle ne depend donc PAS du jeu, ni du generateur, ni du joueur : elle
   depend de la valuation 2-adique d'un seul entier, la taille du vivier.

   Et v2 est brutalement discontinue.
""")
say(f"   {'vivier':>7} {'v2':>4} {'rejet modulo':>14} {'Fisher-Yates':>14}   commentaire")
for n in (76, 77, 78, 79, 80, 81, 82, 84, 88, 96, 100, 128):
    r, f = rejection_bits(n), fy_bits(n)
    note = ""
    if n == POOL:
        note = "<- le vivier reel"
    elif v2(n) == 0:
        note = "vivier IMPAIR : fuite nulle sous rejet"
    elif r > rejection_bits(POOL):
        note = "pire que 80"
    say(f"   {n:>7} {v2(n):>4} {r:>14} {f:>14}   {note}")

odd = [n for n in range(60, 129) if v2(n) == 0]
worst = max(range(60, 129), key=lambda n: rejection_bits(n))
say(f"""
   LECTURE, et c'est le resultat de la section.

   Sous l'echantillonneur le plus courant — rejet modulo le vivier — la fuite
   est TOUT OU RIEN : {len(odd)} des 69 tailles de vivier entre 60 et 128 sont
   IMPAIRES et ne publient RIEN. Un vivier de 79 ou de 81 rendrait le
   theoreme du §68 entierement vide.

   Le vivier reel vaut {POOL} = 2^{v2(POOL)} x 5, et c'est presque le pire choix de la
   plage : seul {worst} = 2^{v2(worst)} fait mieux ({rejection_bits(worst)} bits contre {rejection_bits(POOL)}).

   La vulnerabilite que les §68 a §73 exploitent n'est donc pas une propriete
   du jeu de loterie. C'est un ACCIDENT ARITHMETIQUE du nombre 80 — et un
   operateur qui aurait choisi 79 numeros au lieu de 80 aurait ferme cette
   voie sans le savoir, sans changer une ligne de son code.""")

say(f"""
   SOUS FISHER-YATES, en revanche, la fuite ne s'annule jamais : les modules
   {POOL}, {POOL-1}, ..., {POOL-DRAWN+1} balaient une plage ou l'on rencontre toujours des
   puissances de deux. Le minimum sur la plage 60-128 vaut {min(fy_bits(n) for n in range(60,129))} bits, le
   maximum {max(fy_bits(n) for n in range(60,129))}. Choisir un vivier impair protege du rejet modulo, pas du
   Fisher-Yates — et l'ecart entre les deux echantillonneurs, {rejection_bits(POOL)} contre {fy_bits(POOL)}
   bits a vivier {POOL}, s'inverse completement a vivier impair : {rejection_bits(79)} contre {fy_bits(79)}.""")


# ==========================================================================
rule("3. CE QUE CELA ÉTABLIT")
# ==========================================================================

say(f"""   1. Le budget du §69 est juste a 1,6 % pres. Les mots rejetes portent
      {tot_bits:.2f} bit par tirage, pas les ~11 qu'un compte naif (4 bits x 2,85
      rejets) laisserait croire : l'ambiguite du rejet croit exactement au
      rythme de sa frequence. Le resultat est NEGATIF et il valide le §69.

   2. La fuite sous rejet vaut {DRAWN} x v2(vivier). Elle est TOUT OU RIEN, et le
      vivier reel — 80 = 2^4 x 5 — est presque le pire de sa plage. Un vivier
      impair l'annulerait entierement.

   3. Consequence pour la lecture des §68 a §73 : ils n'exploitent pas une
      faiblesse des generateurs mais une rencontre entre un generateur
      lineaire, un echantillonneur par modulo, et un entier divisible par 16.
      Les trois sont necessaires. Retirer n'importe lequel ferme la voie.

   Registre : inchange. h55 ne teste pas l'archive — il derive.

   ({time.time() - T0:.2f} s)""")
