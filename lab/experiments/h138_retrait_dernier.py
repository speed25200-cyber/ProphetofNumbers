"""h138 — le RETRAIT PAR ECHANGE AVEC LE DERNIER aux pas 20 a 24 : le trou de
couverture de h137, ferme par le meme crible (THEORIE_ETAT §7.11, RAPPORT §158).

LE TROU
=======
h137 crible `fy` (Fisher-Yates partiel par modulo : j = k + x_k mod (80 - k),
echange des cases k et j, numero tire = case k) aux pas 20 a 24, 79 et 80, et
`shuffle` (Collections.shuffle complet, les vingt dernieres cases lues) aux pas
79 et 80 seulement. Or un troisieme echantillonneur est aussi naturel que les
deux autres et consomme exactement vingt mots :

    restant = [1..80]
    pour k = 0..19 :  j = x_k mod (80 - k) ; tire = restant[j] ;
                      restant[j] = restant[79 - k] ; restant.pop()

(retrait par echange avec le dernier, en O(1)). Sa dynamique est celle de
Collections.shuffle lu par ses vingt dernieres cases — a chaque pas la case
79 - k recoit restant[j] et la case j recoit l'ancien dernier — et son masque
est donc le masque `shuffle` : le mot k verifie x_k mod 2^e = (v - 1) mod 2^e
pour un v tire, v <= 80 - k. Preuve : la position j_k <= 79 - k n'est modifiee,
avant le pas k, que si elle est choisie ; la premiere fois qu'elle l'est (au
plus tard au pas k) elle contient encore sa valeur initiale j_k + 1, qui est
tiree ; et j_k mod 2^e = x_k mod 2^e puisque 2^e divise 80 - k. Mais un tel
echantillonneur a vingt mots par tirage, donc un pas de 20 (a 24 avec des mots
perdus), et `shuffle` aux pas 20 a 24 n'est PAS dans h137. Ce trou a ete vu
APRES le scellement du jeton h137, pendant que son crible tournait ; il est
ferme ici par une consignation SEPAREE, jamais par une reecriture de h137.

CE QUE C'EST
============
Le script h137 relu tel quel (H137_ID, H137_VARIANTES, H137_TEMOINS,
H137_SCHEMAS) : 31 trinomes x shuffle {20, 21, 22, 23, 24} x 2 shifts = 310
cribles sur les 60 000 premiers tirages tries, survivants confrontes aux
10 560 retenus ; temoins plantes dans le regime de l'archive, TYPE_1 et TYPE_2
compris, sous le schema teste. Le generateur d'autotest `shuffle` de l'outil
(Collections.shuffle complet lu aux cases 60..79) vaut pour tout pas S >= 20 :
les cases 60..79 ne dependent que des mots 0..19.
"""

import os
import runpy

os.environ.setdefault("H137_ID", "h138.retrait_dernier")
os.environ.setdefault("H137_VARIANTES", "shuffle:20,21,22,23,24")
os.environ.setdefault("H137_SCHEMAS",
                      "retrait par echange avec le dernier (la dynamique de Collections.shuffle "
                      "lu par ses vingt dernieres cases, masque shuffle) aux pas 20 a 24")
os.environ.setdefault("H137_TEMOINS",
                      "3,7,20,shuffle,1,7;3,7,21,shuffle,0,8;1,15,21,shuffle,1,9;3,17,20,shuffle,1,10")
runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "h137_flux_continu.py"),
               run_name="__main__")
