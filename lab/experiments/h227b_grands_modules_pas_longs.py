"""h227b — LES GRANDS MODULES SANS BABAI, pas de bloc 65 à 128 (RAPPORT §251 addendum).

Le §251 remplace Babai par l'énumération exacte pour `m > 2³²` — et s'arrête au pas `64`, en
le disant : *« les pas 65 à 128 restent couverts par la seule heuristique du §232 »*. C'est le
dernier endroit du dossier où un zéro congruentiel à constantes publiées repose encore sur
Babai. Même machine, même fenêtre, même `n` par canal, même témoin ; seul l'intervalle des
pas change, et le jeton le nomme.

Ce fichier exécute `h227` tel quel, après avoir remplacé textuellement l'intervalle, le nom
d'expérience et le jeton — pour ne rien redéfinir qui puisse diverger.
"""

import os
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(ICI, "h227_grands_modules_exacts.py"), encoding="utf-8").read()
for old, new in (('STRIDES = tuple(range(20, 65))', 'STRIDES = tuple(range(65, 129))'),
                 ('EXP_ID = "h227.grands_modules_exacts"', 'EXP_ID = "h227b.grands_modules_pas_longs"'),
                 ('FJETON = "/tmp/h227_jeton.json"', 'FJETON = "/tmp/h227b_jeton.json"'),
                 ('LES GRANDS MODULES SANS BABAI (§251)', 'LES GRANDS MODULES SANS BABAI, PAS 65 A 128 (§251 addendum)')):
    assert src.count(old) == 1, old
    src = src.replace(old, new)
# DANS LE VRAI __main__, PAS DANS UN DICTIONNAIRE QUI S'APPELLE AINSI. `multiprocessing`
# serialise `_travail` par son nom qualifie, `__main__._travail`, et va le chercher dans
# sys.modules["__main__"] : une premiere version executait h227 dans un dictionnaire a
# part nomme "__main__", et le pool mourait a la premiere tache — apres un autotest reussi.
sys.argv = [os.path.join(ICI, "h227_grands_modules_exacts.py")]
g = sys.modules["__main__"].__dict__
g["__file__"] = os.path.join(ICI, "h227_grands_modules_exacts.py")
exec(compile(src, "h227b", "exec"), g)
