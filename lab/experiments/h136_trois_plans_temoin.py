"""h136 — TÉMOIN : les trois plans muets (THEORIE_ETAT §7.10) sur états plantés.

CE QUE LE §7.10 AFFIRME
=======================
Pour r_i = r_{i-K} + r_{i-L} mod 2^32 lu sur les mots sûrs d'un tirage trié à
pas constant — mot 0 : (r >> 1) mod 16 = bits 1..4 de r dans les classes
(v-1) mod 16 des vingt numéros (canal 4) ; mot 16 : (r >> 1) mod 64 = bits 1..6
de r dans les v-17 des numéros v >= 17 (canal 6, lemme du mot 16 à six bits) —
il suffit d'ÉNUMÉRER les plans 0..2 des L mots initiaux (2^{3L} états) : les
retenues vers le bit 3 sont alors connues, le plan 3 de chaque mot est une forme
affine sur F_2 du plan 3 initial, et chaque mot sûr dont le masque force b3
donne une équation linéaire ; un faux état est rejeté par Gauss incrémental dès
qu'une équation contredit ; les plans 4 (canal 4) puis 5, 6 (canal 6) se
résolvent de même. Le crible du §155 énumérait 2^{5L} ; ici 2^{3L} — 2^21 au
lieu de 2^35 pour TYPE_1, 2^45 au lieu de 2^75 pour TYPE_2, 2^93 au lieu de
2^155 pour TYPE_3. Les taux (mort, b3 forcé, b4 forcé, ...) sont
hypergéométriques exacts, calculés ci-dessous pour un faux état (résidu au
hasard) et pour le vrai (son résidu est toujours permis).

CE QUE CE TÉMOIN MESURE
=======================
Pour chaque (K, L) et chaque canal : un état 32 bits planté, 204 tirages par
Fisher-Yates partiel (modulo, pas 20), masques au format de l'archive.
  (a) TYPE_1 : énumération COMPLÈTE des 2^21 plans 0..2 — l'outil doit rendre
      exactement l'état bas planté (5L bits au canal 4, 7L au canal 6), seul ;
  (b) contrôle : 204 masques ALÉATOIRES au même taux — 0 survivant attendu ;
  (c) TYPE_2, TYPE_3 : SOUS-CUBE de 2^21 états contenant le vrai (7 mots
      libres, les autres fixés à leurs 3 bits bas plantés) — l'outil doit
      rendre le bas planté ; le coût par état mesuré donne, par
      multiplication, le coût des 2^45 et 2^93 complets ;
  (d) canal 4 contre canal 6 à petite fenêtre (TYPE_2, 5 mots libres, 50
      tirages) : au canal 4 la fenêtre publie moins de bits qu'il n'y a
      d'inconnues et plusieurs bas survivent (le planté parmi eux) ; au canal 6
      la même fenêtre suffit et le planté est seul.
Sont relevés : mots sûrs lus en moyenne avant rejet, états tués par un masque
vide, par Gauss aux plans 3, 4, 5, 6.

TÉMOIN D'OUTIL : aucune donnée du dossier n'est lue, aucune ligne de registre.
Les temps sont mesurés sur une machine partagée avec h130 et h135 (bruit).
Réglages : H136_LAGS ("3,7 1,15 3,31"), H136_CANAUX ("4 6"), H136_N (204),
H136_NLIBRE (7), H136_GRAINE (20260902), H136_TMP.
"""

import math
import os
import random
import subprocess
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lfg_releve import suite_basse  # noqa: E402

T0 = time.time()
POOL, DRAWN = 80, 20
PAS = 20
SURS = (0, 16)
N = int(os.environ.get("H136_N", "204"))
NLIBRE = int(os.environ.get("H136_NLIBRE", "7"))
GRAINE = int(os.environ.get("H136_GRAINE", "20260902"))
LAGS = [tuple(int(x) for x in s.split(",")) for s in os.environ.get("H136_LAGS", "3,7 1,15 3,31").split()]
CANAUX = [int(x) for x in os.environ.get("H136_CANAUX", "4 6").split()]
RACINE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TMP = os.environ.get("H136_TMP", "/tmp")
BIN = os.path.join(TMP, "lfg_trois_plans_h136")
NOMS = {(3, 7): "TYPE_1", (1, 15): "TYPE_2", (3, 31): "TYPE_3", (1, 63): "TYPE_4"}
PLANS = {4: 5, 6: 7}          # plans 0..PFIN-1 dans l'état bas rendu


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# ---------------------------------------------------------------- les taux
def hyp(m):
    """probabilité qu'aucun des m numéros d'un ensemble fixé ne soit tiré (20 sur 80)"""
    return math.comb(POOL - m, DRAWN) / math.comb(POOL, DRAWN)


def hyp_vrai(m):
    """idem sachant qu'un numéro donné hors de l'ensemble est tiré (19 sur 79)"""
    return math.comb(POOL - 1 - m, DRAWN - 1) / math.comb(POOL - 1, DRAWN - 1)


def taux(nb, par_residu):
    """canal à nb bits publiés, par_residu numéros par résidu : pour chaque plan p = 3..nb,
    (faux : mort, forcé ; vrai : forcé) sachant les bits 1..p-1.
    La classe des bits 1..p-1 a 2^(nb-p+1) résidus, coupée en deux moitiés par le bit p."""
    out = {}
    for p in range(3, nb + 1):
        moitie = (1 << (nb - p)) * par_residu        # numéros par moitié
        p_classe = hyp(2 * moitie)                     # classe entière vide
        p_moitie = hyp(moitie)                         # une moitié donnée vide
        p_alive = 1 - hyp(2 * moitie)
        force_faux = 2 * (p_moitie - p_classe) / p_alive   # sachant la classe vivante
        mort_faux = p_classe
        force_vrai = hyp_vrai(moitie)                  # l'autre moitié vide
        out[p] = (mort_faux, force_faux, force_vrai)
    return out


# ---------------------------------------------------------------- le générateur
def lfg(etat, K, L, n):
    r = list(etat)
    for i in range(L, n):
        r.append((r[i - K] + r[i - L]) & 0xFFFFFFFF)
    return r


def tirage_modulo(seq, p):
    arr = list(range(1, POOL + 1))
    out = []
    for k in range(DRAWN):
        j = k + (seq[p + k] >> 1) % (POOL - k)
        arr[k], arr[j] = arr[j], arr[k]
        out.append(arr[k])
    return sorted(out), p + DRAWN


def masques(S):
    m16 = 0
    m64 = 0
    for v in S:
        m16 |= 1 << ((v - 1) % 16)
        if v >= 17:
            m64 |= 1 << (v - 17)
    return m16, m64


def masques_de(etat, K, L, n):
    seq = lfg(etat, K, L, n * PAS)
    ms, p = [], 0
    for _ in range(n):
        S, p = tirage_modulo(seq, p)
        ms.append(masques(S))
    return ms


def masques_aleatoires(rng, n):
    return [masques(sorted(rng.sample(range(1, POOL + 1), DRAWN))) for _ in range(n)]


def ecrire(ms, chemin):
    with open(chemin, "wb") as f:
        f.write(struct.pack("<%dH" % len(ms), *[m16 for m16, _ in ms]))
        f.write(struct.pack("<%dQ" % len(ms), *[m64 for _, m64 in ms]))


def lancer(K, L, ms, nlibre, fixes, canal, chemin):
    ecrire(ms, chemin)
    cmd = [BIN, str(K), str(L), str(PAS), str(len(ms)), chemin, str(nlibre), str(canal)] + [str(x) for x in fixes]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr)
    surv, fin = [], {}
    for ligne in p.stdout.splitlines():
        if ligne.startswith("BAS"):
            surv.append([int(x) for x in ligne.split()[1:]])
        elif ligne.startswith("FIN"):
            for kv in ligne.split()[1:]:
                k, v = kv.split("=")
                fin[k] = float(v)
    return surv, fin, p.stderr


FMT = "   {:>3} {:>3} {:<7} {:>5} {:<9} {:>6} {:>7} {:>8} {:>8} {:>8} {:>5} {:>6} {:>8} {:>8}  {}"


def ligne(K, L, nom, canal, cas, nl, fin, verdict):
    ns = 1e9 * fin["sec"] / fin["etats"]
    say(FMT.format(K, L, nom, canal, cas, "2^%d" % (3 * nl), int(fin["vides"]), int(fin["gauss3"]),
                   int(fin["gauss4"]), int(fin["gauss5"] + fin["gauss6"]), int(fin["survivants"]),
                   "%.1f" % fin["mots_moyens"], "%.2f" % fin["sec"], "%.0f" % ns, verdict))


def main():
    rng = random.Random(GRAINE)
    subprocess.run(["cc", "-O3", "-march=native", "-o", BIN,
                    os.path.join(RACINE, "tools", "lfg_trois_plans.c")], check=True)
    rule("1. LE THÉORÈME ET SES NOMBRES (hypergéométrique exact, 20 numéros sur 80)")
    say("   Plans 0..2 énumérés (2^{3L}) ; plan p >= 3 affine sur F_2 sachant les plans < p.")
    say("   Par mot sûr et par plan : un FAUX état (résidu au hasard) meurt si sa classe est")
    say("   vide, reçoit une équation si un seul bit p est permis ; le VRAI (résidu toujours")
    say("   permis) reçoit une équation si l'autre moitié de sa classe est vide.")
    say("   (au plan p >= 4 la classe est vivante par construction — le plan p-1 résolu a choisi")
    say("   une moitié non vide — : 'mort' ne s'applique qu'au plan 3 ; 'éq.' est conditionnel.)")
    say("\n   {:<28} {:>4} {:>10} {:>10} {:>10}".format("canal", "plan", "mort faux", "éq. faux", "éq. vrai"))
    T4 = taux(4, 5)     # mot 0 (et mot 16 au canal 4) : 16 résidus de 5 numéros
    T6 = taux(6, 1)     # mot 16 au canal 6 : 64 résidus d'un numéro
    for nom, T in (("mot 0, mod 16 (4 bits)", T4), ("mot 16, mod 64 (6 bits)", T6)):
        for p, (mf, ff, fv) in T.items():
            say("   {:<28} {:>4} {:>10} {:>10.4f} {:>10.4f}".format(nom, p, "%.5f" % mf if p == 3 else "—", ff, fv))
    eq3_4 = 2 * N * T4[3][2]
    eq3_6 = N * (T4[3][2] + T6[3][2])
    say(f"\n   {N} tirages : équations du plan 3 attendues pour le vrai état {eq3_4:.1f} (canal 4,")
    say(f"   {2 * N} mots) ou {eq3_6:.1f} (canal 6) ; pour un faux {2 * N * T4[3][1]:.1f} / {N * (T4[3][1] + T6[3][1]):.1f}.")
    say(f"   Rang < L au plan 3 n'est pas fatal : les solutions restantes sont énumérées et le")
    say(f"   plan 4 (éq. vrai {T4[4][2]:.3f}/mot) les départage ; c'est le cas de TYPE_3 (L = 31).")
    rho = 1 - hyp(5)
    say(f"\n   Bits publiés par tirage : mot 0 log2(1/ρ) = {math.log2(1 / rho):.3f} (ρ = {rho:.4f}) ; mot 16 au")
    say(f"   canal 4 idem ; au canal 6 log2(4) = 2 exactement (un numéro sur quatre est tiré).")
    say("   {:>3} {:>3} {:<7} {:>8} {:>10} {:>10} {:>12} {:>12}".format("K", "L", "nom", "énuméré", "bas (c4)", "bas (c6)", "bits c4/204", "bits c6/204"))
    for K, L in LAGS:
        say("   {:>3} {:>3} {:<7} {:>8} {:>10} {:>10} {:>12.0f} {:>12.0f}".format(
            K, L, NOMS.get((K, L), ""), "2^%d" % (3 * L), 5 * L, 7 * L,
            204 * 2 * math.log2(1 / rho), 204 * (math.log2(1 / rho) + 2)))

    rule("2. TÉMOINS PLANTÉS, SOUS-CUBES ET CONTRÔLE")
    say(f"   {N} tirages, Fisher-Yates par modulo au pas {PAS}, mots sûrs {SURS} ;")
    say(f"   {NLIBRE} mots initiaux libres (2^{3 * NLIBRE} états parcourus), les autres fixés au planté.")
    say("   gauss56 = rejets aux plans 5 et 6 (canal 6 seulement).")
    say("\n" + FMT.format("K", "L", "nom", "canal", "cas", "états", "vides", "gauss3", "gauss4", "gauss56",
                          "surv", "mots", "s", "ns/état", "verdict"))
    bilan = []
    chemin = os.path.join(TMP, "masques_h136.bin")
    for K, L in LAGS:
        nom = NOMS.get((K, L), "")
        etat = [rng.getrandbits(32) for _ in range(L)]
        assert suite_basse([x & 31 for x in etat], K, L, 40) == [x & 31 for x in lfg(etat, K, L, 40)]
        ms = masques_de(etat, K, L, N)
        ms_c = masques_aleatoires(rng, N)
        nl = min(NLIBRE, L)
        fixes = [x & 7 for x in etat[nl:]]
        cas = "planté" if nl == L else "sous-cube"
        for canal in CANAUX:
            bas = [x & ((1 << PLANS[canal]) - 1) for x in etat]
            surv, fin, err = lancer(K, L, ms, nl, fixes, canal, chemin)
            ok = surv == [bas]
            verdict = "= le bas planté, seul" if ok else (
                f"{len(surv)} survivants, planté {'présent' if bas in surv else 'ABSENT'}")
            ligne(K, L, nom, canal, cas, nl, fin, verdict)
            if err.strip():
                say("      stderr : " + err.strip()[:200])
            bilan.append((K, L, nom, canal, cas, fin, ok, surv))
            surv_c, fin_c, err_c = lancer(K, L, ms_c, nl, fixes, canal, chemin)
            ligne(K, L, nom, canal, "contrôle", nl, fin_c,
                  "0 survivant" if not surv_c else f"{len(surv_c)} SURVIVANTS PARASITES")
            bilan.append((K, L, nom, canal, "contrôle", fin_c, not surv_c, surv_c))

    rule("3. CANAL 4 CONTRE CANAL 6 : LA MÊME PETITE FENÊTRE")
    K, L = 1, 15
    n_pet, nl_pet = 50, 5
    etat = [rng.getrandbits(32) for _ in range(L)]
    ms = masques_de(etat, K, L, n_pet)
    fixes = [x & 7 for x in etat[nl_pet:]]
    rho = 1 - hyp(5)
    say(f"   TYPE_2, {n_pet} tirages, {nl_pet} mots libres : inconnues {3 * nl_pet + 2 * L} bits au canal 4")
    say(f"   ({n_pet * 2 * math.log2(1 / rho):.0f} bits publiés), {3 * nl_pet + 4 * L} bits au canal 6 "
        f"({n_pet * (math.log2(1 / rho) + 2):.0f} bits publiés).")
    say("\n" + FMT.format("K", "L", "nom", "canal", "cas", "états", "vides", "gauss3", "gauss4", "gauss56",
                          "surv", "mots", "s", "ns/état", "verdict"))
    petit = {}
    for canal in CANAUX:
        bas = [x & ((1 << PLANS[canal]) - 1) for x in etat]
        surv, fin, err = lancer(K, L, ms, nl_pet, fixes, canal, chemin)
        present = bas in surv
        ligne(K, L, "TYPE_2", canal, "petit", nl_pet, fin,
              ("= le bas planté, seul" if surv == [bas] else f"{len(surv)} survivants, planté {'présent' if present else 'ABSENT'}"))
        petit[canal] = (surv, present)
    if 4 in petit and 6 in petit:
        s4, p4 = petit[4]
        s6, p6 = petit[6]
        attendu = p4 and p6 and len(s6) == 1 and len(s4) > 1
        say(f"\n   canal 4 : {len(s4)} survivants (planté {'présent' if p4 else 'ABSENT'}) ; canal 6 : {len(s6)} "
            f"(planté {'présent' if p6 else 'ABSENT'}) — " + ("CONFORME : les deux bits du mot 16 tranchent." if attendu else "INATTENDU"))
        bilan.append((K, L, "TYPE_2", "4v6", "petit", None, attendu, None))

    rule("4. LECTURE : DU COÛT MESURÉ AU COÛT DES 2^{3L}")
    for K, L, nom, canal, cas, fin, ok, surv in bilan:
        if cas != "planté" and cas != "sous-cube":
            continue
        ns = 1e9 * fin["sec"] / fin["etats"]
        sec = 2.0 ** (3 * L) * ns * 1e-9
        say(f"   {nom} canal {canal} : {ns:.0f} ns/état, {fin['mots_moyens']:.1f} mots sûrs lus en moyenne ; "
            f"les 2^{3 * L} états : "
            + (f"{sec:.0f} s" if sec < 3600 else f"{sec / 3600:.1f} h" if sec < 86400 else
               f"{sec / 86400:.1f} jours" if sec < 86400 * 365 else f"{sec / 86400 / 365.25:.3g} ans")
            + " sur un cœur, scalaire.")
    n_ok = sum(1 for b in bilan if b[6])
    say(f"\n   autotest : {n_ok}/{len(bilan)} — " + ("TOUS CONFORMES" if n_ok == len(bilan) else "ÉCHEC"))
    say(f"   ({time.time() - T0:.1f} s)")


if __name__ == "__main__":
    main()
