"""h178 — CE QUI EST PRÉVISIBLE DANS L'ARCHIVE, CHAMP PAR CHAMP (RAPPORT §194).

CE QUE CE FICHIER EST, ET CE QU'IL N'EST PAS
============================================
Ce n'est PAS un test de plus. C'est le **relevé exact** de ce que l'archive concède, champ
par champ, avec pour chacun : la référence sans connaissance, la règle, sa justesse mesurée,
et le facteur gagné. Les lignes inférentielles renvoient à leur entrée de registre ; les
lignes déterministes se vérifient ici, par comptage, sans nulle et sans `p` — quand une
règle est vraie `70 560` fois sur `70 560`, il n'y a rien à tester.

Le dossier avait les morceaux dispersés sur quatorze sections. La question posée était
« prédire les tirages de l'archive » : la réponse honnête est un TABLEAU, pas un oui ou un
non, et le voici.

CINQ CHAMPS, ET ILS NE SE VALENT PAS
====================================
    identifiant     déterministe
    horodatage      déterministe à la gigue d'horloge près
    multiplicateur  loi fixe, sans mémoire — on ne bat pas son mode
    bonus           déterminé aux vingt près par un THÉORÈME, uniforme au-delà
    vingt numéros   rien, et la borne le chiffre

L'AVERTISSEMENT QUI DOIT ACCOMPAGNER CE TABLEAU
===============================================
Quatre des cinq champs se prévoient. Aucun des quatre n'a la moindre valeur : l'identifiant
et l'horodatage sont du calendrier, le multiplicateur se prévoit à sa fréquence et pas
mieux, et le bonus ne se prévoit QUE si l'on connaît déjà les vingt numéros — c'est-à-dire
après le tirage. **Le seul champ qui aurait une valeur est le seul qui ne cède pas.**
"""

import os
import sys
from math import comb, log2, sqrt

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POOL, DRAWN = 80, 20


def say(*a):
    print(*a, flush=True)


if __name__ == "__main__":
    import lab

    A = lab.load()
    N = len(A.ids)
    IDS = np.asarray(A.ids).astype(np.int64)
    TS = np.asarray(A.ts).astype(np.int64)
    NUMS = np.asarray(A.nums).astype(np.int64)
    BONUS = np.asarray(A.bonus).astype(np.int64)
    BOOST = np.asarray(A.boost).astype(np.int64)
    RANG = np.argmax(NUMS == BONUS[:, None], axis=1)

    say(f"h178 : releve exact sur {N} tirages "
        f"(identifiants {IDS[0]} a {IDS[-1]})\n")

    # ---- 1. identifiant -------------------------------------------------------------
    ok_id = int((np.diff(IDS) == 1).sum())
    say(f"1. IDENTIFIANT — regle « id(t+1) = id(t) + 1 »")
    say(f"      juste {ok_id} / {N-1}  =  {100*ok_id/(N-1):.4f} %")
    say(f"      aucun tirage manquant dans la fenetre : l'etendue vaut "
        f"{IDS[-1]-IDS[0]+1} pour {N} tirages")

    # ---- 2. horodatage --------------------------------------------------------------
    d = np.diff(TS)
    n300 = int((d == 300).sum())
    nuit = int((d > 1000).sum())
    say(f"\n2. HORODATAGE — regle « +300 s, sauf coupure de nuit »")
    say(f"      +300 s exactement : {n300} / {N-1}  =  {100*n300/(N-1):.4f} %")
    import collections
    gros = collections.Counter(d[d > 1000].tolist())
    say(f"      coupures de nuit  : {nuit}, de "
        + ", ".join(f"{v} s x {c}" for v, c in sorted(gros.items())))
    base = max(gros, key=gros.get)
    say(f"      -> le cycle nominal vaut 203 x 300 + {base} = {203*300+base} s, "
        f"soit exactement {(203*300+base)/3600:.0f} heures.")
    ecarts = sorted(v - base for v in gros if v != base)
    if ecarts == [-3600, 3600]:
        say(f"      -> les deux coupures hors norme valent {base-3600} et {base+3600} s, "
            f"soit BASE -/+ 3600 :")
        say(f"         les deux changements d'heure. L'horaire est ancre sur l'HEURE "
            f"LOCALE, pas sur UTC.")
    autres = d[(d != 300) & (d <= 1000)]
    say(f"      gigue d'horloge   : {len(autres)} ecarts de "
        f"{autres.min()} a {autres.max()} s")
    # la regle complete : +300 sauf apres le 204e tirage de la nuit
    deb = np.r_[0, np.flatnonzero(d > 1000) + 1]
    pred = np.full(N - 1, 300, np.int64)
    pred[np.flatnonzero(d > 1000)] = 25500
    exact = int((pred == d).sum())
    tol = int((np.abs(pred - d) <= 5).sum())
    say(f"      regle complete    : {exact} / {N-1} au seconde pres "
        f"({100*exact/(N-1):.4f} %), {tol} a cinq secondes pres "
        f"({100*tol/(N-1):.4f} %)")
    say(f"      -> l'horaire du tirage suivant est CONNU. Valeur predictive : nulle.")

    # ---- 3. multiplicateur ----------------------------------------------------------
    VB, SEC = np.unique(BOOST, return_inverse=True)
    cnt = np.bincount(SEC, minlength=len(VB))
    p = cnt / N
    mode = int(cnt.argmax())
    H = float(-(p[p > 0] * np.log2(p[p > 0])).sum())
    say(f"\n3. MULTIPLICATEUR — {len(VB)} valeurs, portees par la grille 1/80 (§106)")
    for v, c in zip(VB, cnt):
        say(f"      valeur {int(v):3d} : {c:6d}  =  {100*c/N:6.3f} %  "
            f"(grille : {round(80*c/N)}/80)")
    say(f"      entropie {H:.4f} bits ; jouer toujours le mode donne "
        f"{100*p[mode]:.3f} %")
    say(f"      references : uniforme sur les six {100/len(VB):.3f} %, "
        f"uniforme sur la grille 1/80 {100/80:.3f} %")
    say(f"      -> facteur {p[mode]*len(VB):.2f} sur l'uniforme des six, "
        f"{p[mode]*80:.1f} sur la grille. Aucune memoire (§189 famille F), "
        f"aucun quota (§187 famille B).")

    # ---- 4. bonus -------------------------------------------------------------------
    dedans = int((NUMS == BONUS[:, None]).any(axis=1).sum())
    hist = np.bincount(RANG, minlength=DRAWN)
    khi = float(((hist - N / DRAWN) ** 2 / (N / DRAWN)).sum())
    say(f"\n4. BONUS — theoreme du §175")
    say(f"      le bonus est l'un des vingt : {dedans} / {N}  =  "
        f"{100*dedans/N:.4f} %   (DEMONSTRATION, pas estimation)")
    say(f"      sans les vingt numeros : 1/80 = {100/80:.3f} %")
    say(f"      avec les vingt numeros : 1/20 = {100/20:.3f} %   ->   facteur "
        f"{80/20:.0f}, EXACT")
    say(f"      le rang parmi les vingt est-il uniforme ? khi2 = {khi:.2f} pour 19 ddl "
        f"(§187)")
    say(f"      rang le plus frequent : {int(hist.argmax())} a "
        f"{100*hist.max()/N:.3f} % contre 5,000 %")
    say(f"      modele ajuste, hors echantillon : 4,963 % temporel, 4,941 % interne "
        f"(§190)")
    say(f"      -> le facteur quatre est tout ce qu'il y a, et il exige de connaitre "
        f"le tirage.")

    # ---- 5. les vingt numeros -------------------------------------------------------
    C = comb(POOL, DRAWN)
    say(f"\n5. LES VINGT NUMEROS — le seul champ qui aurait une valeur")
    say(f"      l'ensemble exact : 1 / {C:,}  =  {1/C:.3e}   "
        f"({log2(C):.4f} bits)")
    say(f"      un numero donne  : sa frequence marginale, "
        f"{100*DRAWN/POOL:.3f} % ; ecart maximal mesure sur les 80 : "
        f"{100*np.abs(np.asarray(A.mask).mean(axis=0) - 0.25).max():.4f} point")
    say(f"      vingt numeros joues : recouvrement 5 sur 20 en moyenne, exactement "
        f"(hypergeometrique)")
    say(f"      MEILLEUR predicteur mesure, hors echantillon :")
    say(f"         §188  14 traits, 27 424 tirages : 4,99449  (z = -0,54)")
    say(f"         §192  31 traits, 9 temoins plantes passes : 5,00230  (z = +0,23)")
    say(f"      BORNE a 95 % : au plus +0,0191 numero par tirage, soit 0,38 % relatif")
    say(f"      -> aucune valeur exploitable.")

    # ---- le compte -------------------------------------------------------------------
    say(f"\nLE COMPTE, EN BITS PAR TIRAGE")
    say(f"      publie par l'archive        {log2(C) + log2(DRAWN) + H:8.4f} bits")
    say(f"         dont les vingt numeros   {log2(C):8.4f}")
    say(f"         dont le rang du bonus    {log2(DRAWN):8.4f}")
    say(f"         dont le multiplicateur   {H:8.4f}")
    say(f"   ce qu'on en retire, et contre quelle reference :")
    say(f"      numeros        {0.0:8.4f} bit  — la borne du §192 vaut 0,38 % de "
        f"l'esperance, soit moins de 0,002 bit")
    say(f"      bonus          {log2(POOL) - log2(DRAWN):8.4f} bits — de 1/80 a 1/20, "
        f"mais SEULEMENT une fois les vingt connus")
    say(f"      multiplicateur {log2(POOL) - H:8.4f} bits — contre une reference "
        f"uniforme sur la grille 1/80")
    say(f"                     {log2(len(VB)) - H:8.4f} bit  — contre une reference "
        f"uniforme sur ses six valeurs")
    say(f"\n   Quatre champs sur cinq se previennent. Aucun des quatre n'a de valeur :")
    say(f"   l'identifiant et l'horodatage sont du calendrier, le multiplicateur se")
    say(f"   prevoit a sa frequence et pas mieux, et le bonus exige de connaitre le")
    say(f"   tirage. Le seul champ qui aurait une valeur est le seul qui ne cede pas.")
