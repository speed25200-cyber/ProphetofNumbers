"""predire — le prédicteur de bout en bout : des tirages publiés à l'état complet, puis aux
vingt numéros du tirage suivant (THEORIE_ETAT §7.24, §7.26 ; RAPPORT §172, §173).

CE QUE C'EST
============
Les pièces existaient séparément — le crible de classes (§172) trouve les classes, le
relèvement par réseau (§173) en tire l'état de `32L` bits — mais rien ne les reliait. Ce
fichier est le fil : il prend une suite de tirages et rend, SOIT le générateur identifié avec
son état exact et sa prédiction du tirage suivant, SOIT « aucun modèle » avec la liste exacte
de ce qui a été parcouru.

LA CHAÎNE
=========
    tirages triés
      -> classes publiées (v - 1)
      -> crible de classes : automate non déterministe sur (Z/80)^L, verdict DUR
      -> pour chaque survivant : sa suite de classes complète
      -> relèvement : les delta donnent T demi-espaces sur les parties fractionnaires,
         CVP résolu par LLL exact
      -> état de 32L bits
      -> REJEU de la fenêtre entière : si un seul tirage diffère, le candidat est rejeté
      -> prédiction du tirage suivant

Le rejeu est la clé : le crible est ambigu (§7.24 (viii)) et le relèvement peut rendre
plusieurs points ; seul le rejeu tranche, et il ne se trompe pas — un état qui rejoue vingt
tirages triés à l'identique est le bon, à `2^{-1232}` près.

USAGE
=====
    python3 lab/predire.py --temoin                  # démonstration sur une suite plantée
    python3 lab/predire.py --archive [--depuis T] [--nb N]
    python3 lab/predire.py --fichier tirages.txt     # 20 numéros 1..80 par ligne
"""

import os
import random
import subprocess
import sys
import time

RACINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RACINE)
sys.path.insert(0, os.path.join(RACINE, "experiments"))

import h153_releve_troncature as R                                      # noqa: E402

M32 = 1 << 32
POOL, DRAWN = 80, 20
OUTIL = os.path.join(RACINE, "tools_bin", "lfg_crible_classe")
SRC = os.path.normpath(os.path.join(RACINE, "..", "tools", "lfg_crible_classe.c"))
NMAXD, NTIR = 45, 25
TMP = "/tmp"


def say(*a):
    print(*a, flush=True)


def compiler():
    os.makedirs(os.path.dirname(OUTIL), exist_ok=True)
    if not os.path.exists(OUTIL) or os.path.getmtime(OUTIL) <= os.path.getmtime(SRC):
        subprocess.run(["gcc", "-O2", "-march=native", "-fopenmp", "-o", OUTIL, SRC], check=True)


def trinomes(lmax):
    def primitif(K, L):
        import h145_sync_rejet as H
        return H.primitif(K, L)
    return [(K, L) for L in range(2, lmax + 1) for K in range(1, L) if primitif(K, L)]


# ------------------------------------------------------------------ le crible

def crible(classes, K, L, shift, ntir=NTIR, plaf=200_000_000_000):
    """renvoie la liste des suites de classes des survivants (au plus une par ancrage)."""
    fc = os.path.join(TMP, f"predire_cls_{os.getpid()}.txt")
    fb = os.path.join(TMP, f"predire_b_{os.getpid()}.txt")
    open(fc, "w").write("\n".join(" ".join(map(str, t)) for t in classes) + "\n")
    open(fb, "w").write("0\n")
    cmd = [OUTIL, str(K), str(L), str(shift), "flux", fc, fb, str(ntir), "1", str(NMAXD),
           str(plaf), "", "chemin"]
    p = subprocess.run(cmd, capture_output=True, text=True,
                       env=dict(os.environ, OMP_NUM_THREADS="4"))
    if p.returncode != 0:
        raise RuntimeError(p.stderr[:300])
    chemins, info = [], {}
    for l in p.stdout.splitlines():
        t = l.split()
        if not t:
            continue
        if t[0] == "noeuds":
            info = dict(noeuds=int(t[1]), surv=int(t[5]), coupes=int(t[7]))
        elif t[0] == "chem":
            chemins.append((int(t[2]), [int(x) for x in t[3:]]))
    for f in (fc, fb):
        try:
            os.unlink(f)
        except OSError:
            pass
    # les plus COURTS d'abord : le chemin vrai consomme E[N] = 22,85 mots par tirage,
    # un faux — collectionneur sur les 20 classes publiees — 71,96 (§7.24 (v))
    chemins.sort(key=lambda c: c[0])
    return [c for _, c in chemins], info


# ------------------------------------------------------------------ la chaîne complète

def essaie(tirages, K, L, shift, verbeux=False):
    """une configuration : crible -> relèvement -> rejeu. Renvoie (etat, diagnostic)."""
    classes = [[v - 1 for v in t] for t in tirages]
    t0 = time.time()
    chemins, info = crible(classes, K, L, shift)
    if info.get("coupes"):
        return None, f"parcours COUPE au plafond ({info['noeuds']:,} noeuds) — n'exclut rien"
    if not chemins:
        return None, f"0 survivant ({info.get('noeuds',0):,} noeuds, {time.time()-t0:.1f} s)"
    Treq = R.mots_utiles(K, L, 25.68 * L)
    if Treq < 0:
        return None, "relèvement hors de portée pour ce trinôme"
    essais = 0
    for cls in chemins:
        if len(cls) < Treq:
            continue
        essais += 1
        etat, s = R.releve(cls, K, L, Treq, shift)
        if etat is None:
            continue
        rejoue = R.rejoue(etat, K, L, len(tirages), shift)
        if rejoue == [sorted(t) for t in tirages]:
            return etat, (f"REJEU EXACT sur {len(tirages)} tirages "
                          f"(candidat {essais} sur {len(chemins)}, {time.time()-t0:.1f} s)")
    if essais == 0:
        return None, (f"{info.get('surv',0):,} survivant(s), mais le relèvement demande {Treq} "
                      f"mots et la fenêtre n'en donne pas assez")
    return None, f"{info.get('surv',0):,} survivant(s), {essais} relevés, aucun ne rejoue"


def chercher(tirages, lmax=7, shifts=(0, 1), verbeux=True):
    """parcourt les configurations ; renvoie (K, L, shift, etat) ou None, et la couverture."""
    compiler()
    couverture = []
    for K, L in trinomes(lmax):
        for shift in shifts:
            etat, diag = essaie(tirages, K, L, shift)
            couverture.append((K, L, shift, diag))
            if verbeux:
                say(f"   ({K},{L}) shift {shift} : {diag}")
            if etat is not None:
                return (K, L, shift, etat), couverture
    return None, couverture


def predire(tirages, lmax=7, shifts=(0, 1), verbeux=True):
    say(f"predire — {len(tirages)} tirages, trinômes de degré ≤ {lmax}, décalages {shifts}")
    trouve, couv = chercher(tirages, lmax, shifts, verbeux)
    if trouve is None:
        say(f"\n   AUCUN MODELE. {len(couv)} configurations parcourues, toutes exclues "
            "(verdict dur : zéro survivant, parcours complet).")
        say("   Ce que cela veut dire : la fenêtre n'est engendrée par aucun Fibonacci "
            f"retardé additif de degré ≤ {lmax} lu par troncature avec rejet, aux deux "
            "décalages. Cela ne dit rien des degrés supérieurs ni des autres familles.")
        return None
    K, L, shift, etat = trouve
    say(f"\n   MODELE TROUVE : x^{L} + x^{L-K} + 1, sortie r >> {shift}, troncature avec rejet")
    say(f"   état ({L} mots de 32 bits) : {etat}")
    suite = R.rejoue(etat, K, L, len(tirages) + 1, shift)
    say(f"   PREDICTION du tirage {len(tirages) + 1} : {suite[len(tirages)]}")
    return dict(K=K, L=L, shift=shift, etat=etat, prediction=suite[len(tirages)])


# ------------------------------------------------------------------ démonstration

def temoin(K=3, L=7, shift=0, ntir=30, graine=20260902):
    tir, cls, mots, etat = R.engendre(K, L, graine, ntir + 1, shift)
    say(f"témoin : x^{L} + x^{L-K} + 1 planté, sortie r >> {shift}, {ntir} tirages TRIÉS donnés")
    say(f"   état vrai (caché au prédicteur) : {etat}")
    res = predire(tir[:ntir], lmax=L, shifts=(shift,))
    if res:
        juste = res["prediction"] == tir[ntir]
        say(f"   tirage {ntir + 1} réel                : {tir[ntir]}")
        say(f"   >>> PREDICTION {'EXACTE, 20/20' if juste else 'FAUSSE'} ; "
            f"état {'exact' if res['etat'] == etat else 'différent'}")
        return juste
    return False


if __name__ == "__main__":
    if "--temoin" in sys.argv:
        ok = temoin()
        sys.exit(0 if ok else 1)
    if "--archive" in sys.argv:
        import lab
        import numpy as np
        A = lab.load()
        NUM = np.sort(np.asarray(A.nums).astype(np.int64), axis=1)
        d = int(sys.argv[sys.argv.index("--depuis") + 1]) if "--depuis" in sys.argv else 0
        n = int(sys.argv[sys.argv.index("--nb") + 1]) if "--nb" in sys.argv else 40
        lm = int(sys.argv[sys.argv.index("--degres") + 1]) if "--degres" in sys.argv else 7
        tir = [[int(v) for v in NUM[i]] for i in range(d, d + n)]
        say(f"archive : tirages {d} à {d + n - 1}")
        predire(tir, lmax=lm)
        sys.exit(0)
    if "--fichier" in sys.argv:
        f = sys.argv[sys.argv.index("--fichier") + 1]
        tir = [[int(x) for x in l.split()] for l in open(f) if l.strip()]
        predire(tir)
        sys.exit(0)
    print(__doc__)
