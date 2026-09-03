"""verif_rsa260.py — CE QUE J'AI PU VÉRIFIER MOI-MÊME DE LA FACTORISATION DE RSA-260.

POURQUOI CE FICHIER EST DANS CE DÉPÔT
=====================================
Il n'a rien à voir avec les tirages. Il y est parce que la règle de ce dossier est que
**tout chiffre publié doit être recalculable**, et que la nouvelle du 3 septembre 2026 —
RSA-260 factorisé sans ordinateur quantique — est arrivée dans la discussion sous forme de
**capture d'écran**. Une capture d'écran n'est pas une source : c'est une lecture, et une
lecture se trompe.

Elle s'est trompée, d'ailleurs, et c'est la partie instructive.

CE QUI S'EST PASSÉ, DANS L'ORDRE
================================
1. J'ai relu les chiffres du facteur sur l'image : **131** chiffres.
2. Test de Miller-Rabin, 64 rondes : **composé**. Or RSA-260 est un semi-premier, donc ses
   seuls diviseurs sont `1`, `p`, `q`, `N` — un composé de 131 chiffres ne peut pas le
   diviser. J'allais en conclure que l'annonce était fausse.
3. **Je me suis retenu, et j'ai mesuré la fragilité de ma propre lecture** : sur les `1 179`
   variantes à un chiffre près, `12` sont premières, soit `1,02 %`. Un seul chiffre mal lu
   suffisait donc à retourner la conclusion. Le test ne prouvait rien contre l'annonce ; il
   prouvait seulement que **ma transcription** était mauvaise.
4. Vérification par recherche : le facteur publié a **130** chiffres, pas 131. J'avais donc
   dupliqué un chiffre.
5. Des `119` suppressions distinctes d'un chiffre, exactement **deux** donnent un premier de
   130 chiffres — et l'une d'elles est en position `113`, c'est-à-dire **au raccord de deux
   lignes de la capture**, là où un chiffre se duplique naturellement à la lecture.

LA MORALE, ET ELLE EST CELLE DE TOUT LE DOSSIER
===============================================
Un test statistiquement impeccable appliqué à une donnée mal lue produit une fausse
certitude avec la même assurance qu'une vraie. Miller-Rabin ne se trompe **jamais** quand il
dit « composé » — et il avait raison : le nombre *que je lui ai donné* est bien composé.
C'est l'entrée qui était fausse.

    python3 lab/verif_rsa260.py

CE QUE JE N'AI PAS PU VÉRIFIER
==============================
La **divisibilité**. Elle exige les `260` chiffres exacts de `N`, et toutes les sources qui
les portent sont bloquées par le proxy de cet environnement. La seule valeur obtenue par
recherche en comptait `259` — donc tronquée, donc inutilisable. **Je ne peux donc pas
confirmer moi-même que ce premier divise RSA-260 ; je peux seulement dire qu'il est premier,
qu'il a la bonne taille, et que rien de ce que j'ai pu contrôler ne cloche.**
"""

import random
import sys

# Les 131 chiffres tels que je les ai lus sur la capture d'ecran — transcription FAUSSE,
# conservee parce que c'est elle qui a failli produire la fausse conclusion.
LU = ("43973286548448269237950681025058725717"
      "21883526553349659561256924505973939597"
      "59348227250569800480120798804308865641"
      "11102133523080581")


def miller_rabin(n, rondes=64, graine=12345):
    """Probabiliste dans UN sens seulement : « compose » est une PREUVE, jamais un doute."""
    if n < 2:
        return False
    for q in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47):
        if n % q == 0:
            return n == q
    d, r = n - 1, 0
    while d % 2 == 0:
        d //= 2
        r += 1
    rng = random.Random(graine)
    for _ in range(rondes):
        a = rng.randrange(2, n - 1)
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(r - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


def say(*a):
    print(*a, flush=True)


if __name__ == "__main__":
    say("=" * 78)
    say("RSA-260 : ce que j'ai pu verifier moi-meme")
    say("=" * 78)

    say(f"\n1. LA TRANSCRIPTION QUE J'AI FAITE DE LA CAPTURE : {len(LU)} chiffres")
    compose = not miller_rabin(int(LU))
    say(f"   Miller-Rabin 64 rondes : {'COMPOSE' if compose else 'premier'}")
    say("   RSA-260 etant un semi-premier, ses seuls diviseurs sont 1, p, q, N.")
    say("   Un compose de 131 chiffres ne peut donc PAS le diviser.")
    say("   -> j'allais conclure que l'annonce etait fausse.")

    say("\n2. LA FRAGILITE DE MA PROPRE LECTURE, mesuree avant de conclure")
    tot = prem = 0
    for i in range(len(LU)):
        for c in "0123456789":
            if c == LU[i]:
                continue
            tot += 1
            if miller_rabin(int(LU[:i] + c + LU[i + 1:]), 12, graine=9):
                prem += 1
    say(f"   variantes a UN chiffre pres : {tot}, dont {prem} premieres "
        f"({100*prem/tot:.2f} %)")
    say("   -> un seul chiffre mal lu suffisait a retourner la conclusion.")
    say("      Le test ne disait rien de l'annonce : il disait que ma lecture etait fausse.")

    say("\n3. LE FACTEUR PUBLIE FAIT 130 CHIFFRES, PAS 131 (verifie par recherche)")
    say("   J'avais donc duplique un chiffre. Des 119 suppressions distinctes possibles,")
    say("   lesquelles donnent un premier de 130 chiffres ?")
    vus, trouves = set(), []
    for i in range(len(LU)):
        t = LU[:i] + LU[i + 1:]
        if t in vus or t[0] == "0":
            continue
        vus.add(t)
        if miller_rabin(int(t), 40, graine=7):
            trouves.append((i, t))
    say(f"   suppressions testees : {len(vus)} ; premieres : {len(trouves)}")
    for i, t in trouves:
        raccord = " <- raccord de lignes de la capture" if i == 113 else ""
        say(f"     position {i:3d}{raccord}")
        say(f"       {t}")

    say("\n4. CE QUE JE N'AI PAS PU VERIFIER")
    say("   La DIVISIBILITE : elle exige les 260 chiffres exacts de N, et les sources qui")
    say("   les portent sont bloquees par le proxy. La seule valeur obtenue en comptait 259,")
    say("   donc tronquee. Je peux dire que ce nombre est premier et de la bonne taille.")
    say("   Je ne peux pas dire moi-meme qu'il divise RSA-260.")

    ok = compose and len(trouves) >= 1 and any(i == 113 for i, _ in trouves)
    say("\n" + "=" * 78)
    say("DIAGNOSTIC COHERENT" if ok else "DIAGNOSTIC INCOHERENT")
    say("=" * 78)
    sys.exit(0 if ok else 1)
