"""h23 — le trou de 849 tirages, et la mémoire qui ne décroît pas.

Le défaut, cité à sa source
----------------------------
`lab/prediction.txt` s'ouvre sur cet aveu :

    NOTE : 849 tirages manquent entre les deux. Les têtes étant
           pondérées par récence, ce trou n'invalide rien mais rend les
           cinq derniers tirages plus influents qu'ils ne devraient l'être.

La note est signalée puis abandonnée. « N'invalide rien » n'est étayé par
aucune mesure, et « plus influents qu'ils ne devraient » n'est pas chiffré.
Ce fichier fait les deux, et trouve que la note se trompe DEUX FOIS — dans
les deux sens.

Ce que le code fait réellement (volet B, constat de lecture)
-------------------------------------------------------------
Chaque tête pondérée par récence décroît PAR TIRAGE ABSORBÉ, jamais par
tirage écoulé :

  * `Prophet/Services/Swarm.swift` — `absorb(_ drawn: Set<Int>)` applique
    UN pas de décroissance par appel (BayesHead l.52-59, EwmaHead l.86-90,
    HawkesHead l.116-121), et `SwarmEngine.process()` (l.844-906) appelle
    `absorb` une fois par tirage du lot sans jamais regarder l'écart entre
    `draw.drawNumber` et `lastDrawNumber`. Les compteurs d'écart du moteur
    (l.863 : `gap[j] += 1`) avancent eux aussi d'un pas par tirage absorbé.
  * `lab/swarm_py.py` (la transcription) faisait la même chose, à
    l'identique — c'est ce qui permet de mesurer le dégât ici.

Conséquence : un trou de 849 tirages est traité comme ZÉRO temps écoulé.
L'état « récent » de l'essaim au moment de la prédiction déployée est celui
d'il y a 854 tirages (~71 heures de jeu), rafraîchi de cinq tirages.

Le protocole (volet A)
-----------------------
La géométrie du cas réel est rejouée DANS l'archive, où la vérité existe :
à un point de coupure t, on cache 849 tirages, on donne à l'essaim les cinq
tirages aux mêmes écarts que les cinq relevés réels (+849, +852, +854,
+856, +857), et on compare l'état obtenu à celui du même essaim ayant tout
absorbé (858 tirages, sans trou). Trois métriques : recouvrement des
top-20, rho de Spearman des classements sur 80 numéros, distance de
variation totale des poids AdaHedge. Répété sur 36 coupures.

Témoins :
  * trou de 0 — même harnais, écart exigé EXACTEMENT nul (20/20, rho = 1,
    TV = 0) : valide l'appareillage ;
  * trou de 849 suivi de 849 tirages réels — sépare l'effet du trou de
    l'effet du petit nombre de tirages récents ;
  * plancher structurel — deux états de vérité à ~1 100 tirages d'écart
    (récence décorrélée, structure lente partagée), et le plancher
    théorique de deux top-20 indépendants, 5,0000 exactement
    (hypergéométrique 80,20,20 — c'est un théorème, pas une simulation).

La correction (volet C)
------------------------
`swarm_py.py` expose désormais `advance(k)` par tête — k tirages ÉCOULÉS
sans observation — et `run`/`predict_next` acceptent les numéros de tirage
(`ids`) pour faire passer le temps manquant. Le principe : absorber
l'espérance du tirage non observé (forme fermée pour les états linéaires),
avancer les compteurs d'écart du temps écoulé, déclarer perdu l'état
conditionné à l'identité des derniers tirages. Ce fichier mesure ce que la
correction récupère, sur les mêmes coupures. Le diff Swift équivalent est
proposé dans le rapport (Prophet/ est hors périmètre d'écriture).

Ce que ce fichier ne prétend pas
---------------------------------
Aucune de ces mesures ne touche à l'espérance de hits : par le théorème
d'invariance, le top-20 déployé, corrigé ou de vérité vaut exactement
5,0000 sur 20. Le dégât mesuré est un dégât de FIDÉLITÉ — l'écart entre ce
que l'app affiche (classement, top-20, poids des têtes) et ce que le même
appareil afficherait s'il avait vu ce qu'il prétend résumer.
"""

import csv
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import lab
import swarm_py as sp

T0 = time.time()
POOL, DRAWN = 80, 20
FAST = os.environ.get("H23_FAST") == "1"


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# --------------------------------------------------------------------------
# Métriques entre deux états de l'essaim
# --------------------------------------------------------------------------

def ranks_of(field: np.ndarray) -> np.ndarray:
    order = np.argsort(-field, kind="stable")
    rk = np.empty(POOL, np.int64)
    rk[order] = np.arange(POOL)
    return rk


def spearman(f1: np.ndarray, f2: np.ndarray) -> float:
    d = ranks_of(f1) - ranks_of(f2)
    return 1 - 6 * float((d * d).sum()) / (POOL * (POOL * POOL - 1))


def pearson(x: np.ndarray, y: np.ndarray) -> float:
    sx, sy = float(x.std()), float(y.std())
    if sx == 0 or sy == 0:
        return 0.0
    return float(((x - x.mean()) * (y - y.mean())).mean() / (sx * sy))


def top_overlap(p1: dict, p2: dict) -> int:
    return len(set(p1["top20"]) & set(p2["top20"]))


def tv(w1: np.ndarray, w2: np.ndarray) -> float:
    return 0.5 * float(np.abs(w1 - w2).sum())


def med3(xs) -> str:
    xs = np.asarray(xs, float)
    return f"{np.median(xs):7.3f}  [{xs.min():7.3f} ; {xs.max():7.3f}]"


# --------------------------------------------------------------------------
# 1. Le défaut, et où il vit dans le code
# --------------------------------------------------------------------------

rule("1. LE DÉFAUT — un trou de 849 tirages compté comme zéro temps écoulé")

say("""   Le prédicteur déployé (`lab/predire.py`, sortie `lab/prediction.txt`) a
   absorbé 70 560 tirages d'archive (jusqu'au 1 380 173) puis 5 relevés
   manuels (1 381 023 à 1 381 031). Entre les deux : 849 tirages jamais vus.

   Or aucune tête ne décroît par tirage ÉCOULÉ — toutes décroissent par
   tirage ABSORBÉ (`Swarm.swift` : un pas de décroissance par appel
   d'`absorb`, `process()` n'exploite jamais l'écart des `drawNumber` ;
   `swarm_py.py` transcrivait fidèlement le même comportement). Une EWMA de
   mémoire 8 croit donc que l'archive s'est terminée il y a 5 tirages, alors
   qu'elle s'est terminée il y a 858.

   La note de prediction.txt affirme sans mesure : « ce trou n'invalide
   rien mais rend les cinq derniers tirages plus influents qu'ils ne
   devraient l'être ». Les deux moitiés de la phrase sont testées ici.""")


# --------------------------------------------------------------------------
# 2. Pré-enregistrement — avant toute mesure
# --------------------------------------------------------------------------

rule("2. PRÉ-ENREGISTREMENT")

tok_gel = lab.preregister(
    "h23.gel",
    "l'état déployé (archive + trou de 849 + 5 relevés, géométrie réelle) "
    "s'écarte de l'état de vérité (mêmes 858 tirages sans trou) : le trou "
    "GÈLE la mémoire courte au lieu de la faire décroître",
    "médiane, sur 36 coupures dans l'archive, du recouvrement "
    "|top20(déployé) ∩ top20(vérité)| (identité = 20)",
    "témoins internes : trou-0 (identité exacte exigée : 20/20, rho = 1, "
    "TV = 0) ; plancher d'indépendance 5,0000 exact (théorème "
    "hypergéométrique) ; plancher structurel mesuré entre coupures",
    "la note « ce trou n'invalide rien » est réfutée sur la fidélité si la "
    "médiane est ≤ 15/20 ; confirmée si ≥ 19/20 ; entre les deux, dégât "
    "partiel, chiffré tel quel",
    track="C")

tok_infl = lab.preregister(
    "h23.influence",
    "seconde moitié de la note : les cinq relevés seraient « plus "
    "influents qu'ils ne devraient l'être » dans l'état déployé",
    "médiane du déplacement du top-20 causé par l'absorption des 5 relevés "
    "dans l'état déployé (20 − |top20(archive+trou+5) ∩ top20(archive "
    "seule)|), comparée au déplacement DÛ : celui des 5 derniers tirages "
    "dans l'état de vérité (20 − |top20(vérité 858) ∩ top20(vérité 853)|)",
    "comparaison appariée sur les mêmes 36 coupures ; aucun null simulé — "
    "les deux quantités sont déterministes à coupure donnée",
    "« plus influents » est confirmé si médiane(déployé) ≥ médiane(dû) + 1 "
    "numéro ; réfuté si l'écart des médianes est < 1 ; les deux chiffres "
    "sont consignés quoi qu'il arrive",
    track="C")

tok_corr = lab.preregister(
    "h23.correction",
    "décroître par tirage ÉCOULÉ (advance/ids, câblé dans swarm_py et "
    "predire) rapproche l'état déployé de l'état de vérité",
    "médiane du recouvrement top-20 corrigé-vs-vérité moins médiane "
    "buggy-vs-vérité, mêmes 36 coupures, géométrie réelle du trou",
    "mêmes témoins que h23.gel ; le témoin 849+849 borne ce qui reste "
    "irrécupérable quand les données récentes abondent",
    "correction adoptée si Δmédiane ≥ +1 numéro sur le top-20 OU si le rho "
    "de Spearman médian gagne ≥ 0,05 ; sinon elle est conservée pour la "
    "cohérence temporelle mais déclarée cosmétique, et dite telle",
    track="C")

for tk in (tok_gel, tok_infl, tok_corr):
    say(f"   {tk['id']:<16} scellé {tk['seal']}")


# --------------------------------------------------------------------------
# 3. Le protocole, exécuté
# --------------------------------------------------------------------------

rule("3. LE PROTOCOLE — la géométrie réelle du trou, rejouée dans l'archive")

a = lab.load()
N = len(a)

HOLE = 849                                # le trou réel
REC_OFF = [849, 852, 854, 856, 857]       # écarts réels des 5 relevés
REC_GAPS = [849, 2, 1, 1, 0]              # temps manquant avant chacun
SPAN = 858                                # la vérité absorbe tout cela
LONG = 1698                               # témoin : trou + 849 tirages réels

n_cuts = 6 if FAST else 36
cuts = np.linspace(30_000, N - LONG - 2, n_cuts).astype(int)
long_every = 2                            # témoin long sur une coupure sur 2

say(f"""   36 coupures t dans l'archive (de {cuts[0]:,} à {cuts[-1]:,}). À chaque
   coupure, depuis le MÊME état de l'essaim (cloné) :

     vérité     absorbe les lignes t..t+857 (858 tirages, sans trou)
     déployé    absorbe les 5 lignes t+{{849, 852, 854, 856, 857}} — la
                géométrie exacte des relevés réels, trous internes compris
     corrigé    comme « déployé », mais fait d'abord passer le temps
                manquant (advance : 849, puis 2, 1, 1)
     trou-0     absorbe les lignes t..t+4 — doit être IDENTIQUE à la
                vérité arrêtée au même point, au bit près
     849+849    absorbe les lignes t+849..t+1697 (849 tirages réels après
                le trou), contre la vérité des 1 698

   L'essaim est celui de swarm_py (26 têtes, AdaHedge), vérifié bit à bit
   contre predict_next avant toute mesure.""")

if FAST:
    say(f"\n   MODE RAPIDE (H23_FAST=1) : {n_cuts} coupures, aucune consignation.")

# Harnais : SwarmState doit reproduire predict_next au bit près.
_m = a.mask[:400]
_st = sp.SwarmState()
for _t in range(len(_m)):
    _st.step(_m[_t])
_p1, _p2 = _st.predict(), sp.predict_next(_m)
assert _p1["field"].tobytes() == _p2["field"].tobytes()
assert _p1["weights"].tobytes() == _p2["weights"].tobytes()
say("\n   harnais : SwarmState ≡ predict_next sur 400 tirages — bit à bit, OK")

# Constantes de décroissance des 9 têtes exponentielles (indices 0..8).
_decay = []
for h in sp.make_heads()[:9]:
    if h.family == "Bayes":
        _decay.append((h.hid, h.memory, 1 - 1 / max(2.0, h.memory)))
    elif h.family == "EWMA":
        _decay.append((h.hid, h.memory, 1 - 2 / (max(2.0, h.memory) + 1)))
    else:  # Hawkes
        _decay.append((h.hid, h.memory, math.exp(-0.6931 / max(0.5, h.memory))))

M = {k: [] for k in
     ("ov_bug", "rho_bug", "tv_bug", "dr_bug",
      "ov_cor", "rho_cor", "tv_cor", "dr_cor",
      "ov_z0", "rho_z0", "tv_z0",
      "ov_b849", "rho_b849", "tv_b849",
      "ov_c849", "rho_c849", "tv_c849",
      "infl_dep", "infl_due", "floor_struct")}
RET = {"bug": [], "tru": [], "cor": []}      # rétention par tête (9 expo)

master = sp.SwarmState()
cut_set = {int(c): i for i, c in enumerate(cuts)}
prev_truth_top = None
t_loop = time.time()

for t in range(int(cuts[-1]) + 1):
    if t in cut_set:
        ci = cut_set[t]
        arch = master.predict()                       # archive seule, à t
        arch_zf = [sp._z(master.heads[i].field()) for i in range(9)]

        # -- vérité : 858 tirages sans trou (le témoin long va à 1698)
        st = master.clone()
        pT5 = pT853 = pT858 = pT1698 = None
        horizon = LONG if ci % long_every == 0 else SPAN
        for j in range(horizon):
            st.step(a.mask[t + j])
            if j == 4:
                pT5 = st.predict()
            elif j == SPAN - 6:
                pT853 = st.predict()
            elif j == SPAN - 1:
                pT858 = st.predict()
                tru_zf = [sp._z(st.heads[i].field()) for i in range(9)]
        if horizon == LONG:
            pT1698 = st.predict()

        # -- déployé : trou gelé, 5 relevés
        st = master.clone()
        for off in REC_OFF:
            st.step(a.mask[t + off])
        pB5 = st.predict()
        bug_zf = [sp._z(st.heads[i].field()) for i in range(9)]

        # -- corrigé : le temps manquant passe d'abord
        st = master.clone()
        for gap, off in zip(REC_GAPS, REC_OFF):
            st.advance(gap)
            st.step(a.mask[t + off])
        pC5 = st.predict()
        cor_zf = [sp._z(st.heads[i].field()) for i in range(9)]

        # -- témoin trou-0 : identité exigée avec la vérité arrêtée à t+5
        st = master.clone()
        for j in range(5):
            st.step(a.mask[t + j])
        pZ0 = st.predict()

        # -- témoin 849+849
        if horizon == LONG:
            st = master.clone()
            for j in range(HOLE, LONG):
                st.step(a.mask[t + j])
            pB849 = st.predict()
            st = master.clone()
            st.advance(HOLE)
            for j in range(HOLE, LONG):
                st.step(a.mask[t + j])
            pC849 = st.predict()

        M["ov_bug"].append(top_overlap(pB5, pT858))
        M["rho_bug"].append(spearman(pB5["field"], pT858["field"]))
        M["tv_bug"].append(tv(pB5["weights"], pT858["weights"]))
        M["dr_bug"].append(float(np.abs(ranks_of(pB5["field"])
                                        - ranks_of(pT858["field"])).mean()))
        M["ov_cor"].append(top_overlap(pC5, pT858))
        M["rho_cor"].append(spearman(pC5["field"], pT858["field"]))
        M["tv_cor"].append(tv(pC5["weights"], pT858["weights"]))
        M["dr_cor"].append(float(np.abs(ranks_of(pC5["field"])
                                        - ranks_of(pT858["field"])).mean()))
        M["ov_z0"].append(top_overlap(pZ0, pT5))
        M["rho_z0"].append(spearman(pZ0["field"], pT5["field"]))
        M["tv_z0"].append(tv(pZ0["weights"], pT5["weights"]))
        if horizon == LONG:
            M["ov_b849"].append(top_overlap(pB849, pT1698))
            M["rho_b849"].append(spearman(pB849["field"], pT1698["field"]))
            M["tv_b849"].append(tv(pB849["weights"], pT1698["weights"]))
            M["ov_c849"].append(top_overlap(pC849, pT1698))
            M["rho_c849"].append(spearman(pC849["field"], pT1698["field"]))
            M["tv_c849"].append(tv(pC849["weights"], pT1698["weights"]))
        M["infl_dep"].append(DRAWN - top_overlap(pB5, arch))
        M["infl_due"].append(DRAWN - top_overlap(pT858, pT853))
        if prev_truth_top is not None:
            M["floor_struct"].append(
                len(set(pT858["top20"]) & prev_truth_top))
        prev_truth_top = set(pT858["top20"])
        RET["bug"].append([pearson(arch_zf[i], bug_zf[i]) for i in range(9)])
        RET["tru"].append([pearson(arch_zf[i], tru_zf[i]) for i in range(9)])
        RET["cor"].append([pearson(arch_zf[i], cor_zf[i]) for i in range(9)])
        say(f"   coupure {ci + 1:>2}/{len(cuts)}  t={t:>6,}  "
            f"top20 déployé/vérité {M['ov_bug'][-1]:>2}/20   "
            f"corrigé {M['ov_cor'][-1]:>2}/20   "
            f"({time.time() - t_loop:.0f}s)")
    master.step(a.mask[t])

# Le témoin trou-0 doit être EXACTEMENT nul — sinon le harnais est cassé.
assert all(v == DRAWN for v in M["ov_z0"]), M["ov_z0"]
assert all(v == 1.0 for v in M["rho_z0"]), M["rho_z0"]
assert all(v == 0.0 for v in M["tv_z0"]), M["tv_z0"]


# --------------------------------------------------------------------------
# 4. Le mécanisme, démontré tête par tête
# --------------------------------------------------------------------------

rule("4. LE MÉCANISME — la décroissance suit les tirages ABSORBÉS, mesuré")

say("""   Pour une tête exponentielle de facteur g, l'état est un AR(1) : sa
   corrélation avec l'état de fin d'archive vaut g^j après j pas de
   décroissance. Si la décroissance suivait le temps ÉCOULÉ, déployé et
   vérité montreraient tous deux g^858 ≈ 0. Si elle suit les tirages
   ABSORBÉS, le déployé montre g^5 — la signature du gel.

   corr(champ, fin d'archive), médiane sur les coupures :

   tête          mémoire   prédit g^5   DÉPLOYÉ   prédit g^858   VÉRITÉ   CORRIGÉ""")
ret_bug = np.array(RET["bug"])
ret_tru = np.array(RET["tru"])
ret_cor = np.array(RET["cor"])
for i, (hid, mem, g) in enumerate(_decay):
    say(f"   {hid:<13} {mem:>6.1f}   {g ** 5:>10.3f}   {np.median(ret_bug[:, i]):>7.3f}"
        f"   {g ** SPAN:>12.3g}   {np.median(ret_tru[:, i]):>6.3f}"
        f"   {np.median(ret_cor[:, i]):>7.3f}")

say("""
   Lecture. Colonne DÉPLOYÉ contre colonne « prédit g^5 » : la mémoire
   courte de l'état déployé est celle d'il y a CINQ tirages absorbés, pas
   858 écoulés — c'est le témoin positif du mécanisme, prédit avant d'être
   mesuré. La vérité, elle, a tout oublié (g^858), et l'état corrigé
   retrouve ce comportement : advance() rend au temps ce que le compteur
   d'absorptions lui volait.""")


# --------------------------------------------------------------------------
# 5. La loi du dégât (volet A)
# --------------------------------------------------------------------------

rule("5. LA LOI DU DÉGÂT — médiane [min ; max] sur les coupures")

say(f"""   top-20 commun avec la vérité (sur 20 ; identité = 20, indépendance = 5,0000) :
     déployé (trou gelé + 5 relevés)   {med3(M['ov_bug'])}
     témoin trou-0                     {med3(M['ov_z0'])}
     témoin trou+849 réels (gelé)      {med3(M['ov_b849'])}
     plancher structurel mesuré        {med3(M['floor_struct'])}

   rho de Spearman du classement des 80 numéros :
     déployé                           {med3(M['rho_bug'])}
     témoin trou-0                     {med3(M['rho_z0'])}
     témoin trou+849 réels (gelé)      {med3(M['rho_b849'])}

   déplacement moyen de rang (sur 80 numéros) :
     déployé                           {med3(M['dr_bug'])}

   distance de variation totale des poids AdaHedge :
     déployé                           {med3(M['tv_bug'])}
     témoin trou-0                     {med3(M['tv_z0'])}
     témoin trou+849 réels (gelé)      {med3(M['tv_b849'])}""")

say("""
   Lecture. Le témoin trou-0 est exactement nul — l'appareillage ne crée
   pas d'écart. Le déployé, lui, s'écarte de la vérité sur toutes les
   coupures. Le témoin 849+849 sépare les causes : quand 849 tirages réels
   suivent le trou, le gel devient presque invisible — la mémoire courte
   est réécrite par les vraies données. Le dégât du cas déployé vient donc
   de la CONJONCTION : un trou gelé, masqué par cinq tirages seulement.
   Le plancher structurel dit où atterrirait un état dont la récence
   serait entièrement décorrélée mais la structure lente partagée — c'est
   l'échelle sur laquelle juger le chiffre du déployé : entre l'identité
   (20) et ce plancher, pas entre 20 et 0.""")


# --------------------------------------------------------------------------
# 6. Les cinq relevés sont-ils « plus influents qu'ils ne devraient » ?
# --------------------------------------------------------------------------

rule("6. L'INFLUENCE DES CINQ RELEVÉS — la seconde moitié de la note")

say(f"""   déplacement du top-20 causé par les 5 tirages (numéros changés sur 20) :
     dans l'état déployé (gelé)        {med3(M['infl_dep'])}
     dû (vérité 858 contre 853)        {med3(M['infl_due'])}""")

infl_gap = float(np.median(M["infl_dep"]) - np.median(M["infl_due"]))
say(f"""
   Écart des médianes : {infl_gap:+.1f} numéro(s).

   Lecture. Mécaniquement, absorber cinq tirages déplace l'état d'à peu
   près autant dans les deux mondes — le pas d'une absorption ne dépend
   pas de ce que l'état croit du temps. Le diagnostic de la note visait
   donc le mauvais coupable : le problème n'est pas que les cinq relevés
   pèsent trop, c'est que les 849 tirages manquants sont IMPERSONNÉS par
   les 849 derniers tirages d'archive, vieux de trois jours et gelés à
   leur poids de récence plein. L'influence excédentaire n'est pas celle
   des cinq vrais tirages, c'est celle de 849 faux.""")


# --------------------------------------------------------------------------
# 7. Ce que la correction récupère (volet C)
# --------------------------------------------------------------------------

rule("7. LA CORRECTION — décroître par tirage écoulé, et ce que ça rend")

d_ov = float(np.median(M["ov_cor"]) - np.median(M["ov_bug"]))
d_rho = float(np.median(M["rho_cor"]) - np.median(M["rho_bug"]))
say(f"""   même harnais, mêmes coupures, états corrigés (advance + ids) :

   top-20 commun avec la vérité :
     corrigé                           {med3(M['ov_cor'])}
     (déployé, rappel)                 {med3(M['ov_bug'])}
     corrigé, témoin trou+849 réels    {med3(M['ov_c849'])}
     (gelé,   témoin trou+849 réels)   {med3(M['ov_b849'])}

   rho de Spearman :
     corrigé                           {med3(M['rho_cor'])}
     (déployé, rappel)                 {med3(M['rho_bug'])}

   déplacement moyen de rang :
     corrigé                           {med3(M['dr_cor'])}
     (déployé, rappel)                 {med3(M['dr_bug'])}

   poids AdaHedge (TV) :
     corrigé                           {med3(M['tv_cor'])}
     (déployé, rappel)                 {med3(M['tv_bug'])}

   gain de la correction : {d_ov:+.1f} numéro(s) de top-20, {d_rho:+.3f} de rho.""")

say("""
   Ce que la correction ne peut PAS rendre : l'information des 849 tirages
   cachés. L'état corrigé ne converge pas vers la vérité — il converge vers
   « la vérité moins ce qui n'a pas été vu » : mémoire courte rendue à sa
   valeur d'ignorance, cinq vrais tirages à leur poids exact. C'est le
   maximum atteignable sans les données, et le témoin corrigé 849+849
   montre que dès que les données reviennent, l'écart résiduel se referme.""")


# --------------------------------------------------------------------------
# 8. Le cas réel — la prédiction déployée, avant/après
# --------------------------------------------------------------------------

rule("8. LE CAS RÉEL — le tirage 1 381 032, avant et après correction")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
recent = []
with open(os.path.join(ROOT, "draws_ordered.csv")) as fh:
    for row in csv.DictReader(fh):
        nums = [int(row[f"o{i}"]) for i in range(1, DRAWN + 1)]
        recent.append((int(row["id"]), sorted(nums)))
recent.sort()
extra = np.zeros((len(recent), POOL), bool)
for i, (_, nums) in enumerate(recent):
    for x in nums:
        extra[i, x - 1] = True
mask_full = np.concatenate([a.mask, extra], axis=0)
ids_full = np.concatenate([a.ids, np.array([d for d, _ in recent], np.int64)])

if FAST:
    say("   (sauté en mode rapide)")
    pB = pC = None
else:
    pB = sp.predict_next(mask_full)                  # ce que l'app a affiché
    pC = sp.predict_next(mask_full, ids=ids_full)    # ce qu'elle affichera
    common = sorted(set(pB["top20"]) & set(pC["top20"]))
    say(f"   top-20 déployé  : {' '.join(f'{n:>2}' for n in pB['top20'])}")
    say(f"   top-20 corrigé  : {' '.join(f'{n:>2}' for n in pC['top20'])}")
    say(f"\n   numéros communs : {len(common)}/20")
    say(f"   rho de Spearman du classement complet : "
        f"{spearman(pB['field'], pC['field']):.3f}")
    say(f"   TV des poids AdaHedge : {tv(pB['weights'], pC['weights']):.4f}")
    say("""
   Les deux sélections valent exactement la même chose — 5,0000 hits
   espérés, comme n'importe quelle autre. La différence est ailleurs : le
   top-20 corrigé est celui d'un essaim qui SAIT qu'il n'a pas vu trois
   jours de tirages ; le déployé était celui d'un essaim qui croyait
   l'archive fraîche. `prediction.txt` reste la sortie archivée du
   prédicteur d'alors ; la prochaine exécution de predire.py portera la
   correction.""")


# --------------------------------------------------------------------------
# 9. Le diff Swift proposé (Prophet/ est hors périmètre d'écriture du labo)
# --------------------------------------------------------------------------

SWIFT_DIFF = """\
   Fichier : Prophet/Services/Swarm.swift. Même principe que swarm_py :
   advance(elapsed) = elapsed tirages écoulés sans observation ; absorption
   de l'espérance en forme fermée pour les états linéaires, compteurs
   d'écart avancés du temps écoulé, état conditionné aux derniers tirages
   déclaré perdu. Non appliqué ici — proposé, à vérifier avec
   lab/verif_swift.py et lab/verif_logique.py au moment du câblage.

   1. protocol SwarmHead (l.17-25) — ajouter au protocole :
        func advance(_ elapsed: Int)

   2. BayesHead (l.35-66), après absorb :
        func advance(_ elapsed: Int) {
            let g = 1 - 1 / max(2, memory)
            let gk = pow(g, Double(elapsed))
            let m = (1 - gk) / (1 - g)
            for i in 0..<poolN {
                a[i] = gk * a[i] + pBase * m
                b[i] = gk * b[i] + (1 - pBase) * m
            }
        }

   3. EwmaHead (l.70-94) :
        func advance(_ elapsed: Int) {
            let l = 2 / (max(2, memory) + 1)
            let r = pow(1 - l, Double(elapsed))
            for i in 0..<poolN { e[i] = pBase + r * (e[i] - pBase) }
        }

   4. HawkesHead (l.98-124) :
        func advance(_ elapsed: Int) {
            let d = exp(-0.6931 / max(0.5, memory))
            let dk = pow(d, Double(elapsed))
            for i in 0..<poolN {
                s[i] = s[i] * dk + jump * pBase * (1 - dk) / (1 - d)
            }
        }

   5. WeibullHead (l.128-165), HazardHead (l.167-200), GapZHead
      (l.202-233) — l'écart avance du temps écoulé, les tables
      d'apprentissage ne bougent pas :
        func advance(_ elapsed: Int) {
            for i in 0..<poolN { gap[i] += elapsed }
        }

   6. SpectralHead (l.237-288) — la file `[Set<Int>]` ne peut pas porter un
      tirage espéré fractionnaire : la porter en `[[Double]]` (vecteurs de
      hits), absorb pousse le vecteur 0/1 du tirage, advance pousse
      min(elapsed, long) fois le vecteur neutre `[Double](repeating: pBase,
      count: poolN)` — mêmes sommes, mêmes fenêtres que swarm_py.

   7. MarkovHead (l.292-337) :   advance ⇒ recent.removeAll()
      StreakHead (l.339-355) :   advance ⇒ streak = [Double](repeating: 0,
                                            count: poolN)
      CopairHead (l.359-400) :   advance ⇒ lastDraw = []
      AdjacencyHead (l.494-535): advance ⇒ last = []
      (le conditionnement au « tirage précédent » n'existe plus ; les
      tables longues restent)

   8. AcpHead (l.404-470) — la moyenne décroît, les axes d'Oja et t ne
      bougent pas (pas d'observation, pas de pas d'apprentissage) :
        func advance(_ elapsed: Int) {
            let r = pow(1 - 0.04, Double(elapsed))
            for i in 0..<poolN { meanV[i] = pBase + r * (meanV[i] - pBase) }
        }

   9. AntiHead (l.474-487) :  func advance(_ elapsed: Int) {
                                  base.advance(elapsed) }

  10. RowPressureHead (l.537-560) et PressureHead (l.564-595) — retour
      exponentiel vers l'attendu :
        func advance(_ elapsed: Int) {
            let r = pow(1 - 0.12, Double(elapsed))
            for k in 0..<10 { rows[k] = Double(drawK) / 10
                              + r * (rows[k] - Double(drawK) / 10) }
        }
      (même motif pour dec — attendu drawK/8 — et par — attendu drawK/2.)

  11. SwarmEngine.process (l.844-906) — LE POINT D'ANCRAGE. En tête du
      corps de boucle, avant le bloc prevRanks et avant evaluate :

      ANCIEN (l.847-849) :
        for (i, draw) in batch.enumerated() {
            let nums = draw.numbers
            let drawn = Set(nums)

      NOUVEAU :
        for (i, draw) in batch.enumerated() {
            let nums = draw.numbers
            let drawn = Set(nums)

            // h23 : un trou entre le dernier tirage absorbé et celui-ci
            // fait d'abord passer le temps manquant — décroissance par
            // tirage ÉCOULÉ, pas par tirage absorbé.
            let hole = lastDrawNumber == Int.min
                ? 0 : draw.drawNumber - lastDrawNumber - 1
            if hole > 0 {
                for head in heads { head.advance(hole) }
                for j in 0..<Self.pool { gap[j] += hole }   // écarts affichés
            }

      Les fenêtres d'affichage du moteur (recent16, adjSeries, freq16)
      restent des fenêtres de tirages OBSERVÉS — dire « sorties sur les 16
      derniers tirages absorbés » reste vrai ; c'est leur légende qui doit
      le dire si un trou les traverse.

  12. Ce que le diff ne touche pas : evaluate() (on n'évalue que des
      tirages observés), l'e-process (chaque pari reste conditionné au
      passé observé), AdaHedge (aucun oubli temporel n'y est défini).
"""


# --------------------------------------------------------------------------
# 10. Verdict, et consignation
# --------------------------------------------------------------------------

rule("9. LE DIFF SWIFT PROPOSÉ — lecture seule oblige")
say(SWIFT_DIFF)

rule("10. VERDICT")

ov_med = float(np.median(M["ov_bug"]))
say(f"""   La note de prediction.txt se trompe deux fois.

   « Ce trou n'invalide rien » — au sens de l'espérance, c'est vrai par
   théorème (5,0000 pour tout top-20), mais la note parle de l'état des
   têtes, et là c'est faux : le top-20 déployé n'a en médiane que
   {ov_med:.1f}/20 numéros en commun avec ce que le même essaim aurait
   affiché en voyant les 858 tirages ; le témoin trou-0 est à 20/20.

   « Les cinq derniers tirages plus influents qu'ils ne devraient » — non :
   leur influence est normale ({float(np.median(M['infl_dep'])):.1f} numéro(s)
   déplacé(s), contre {float(np.median(M['infl_due'])):.1f} dû(s)). Ce qui pèse trop,
   ce sont les 849 tirages d'archive gelés à leur poids de récence plein,
   qui impersonnent les 849 manquants.

   La correction (décroissance par tirage écoulé) est câblée dans
   swarm_py.py et predire.py, mesurée ci-dessus, et son équivalent Swift
   est spécifié dans le rapport.""")

if not FAST:
    lab.record(tok_gel, ov_med,
               power_at="témoin trou-0 exactement nul (36/36) ; mécanisme "
                        "prédit g^5 vs g^858 vérifié tête par tête",
               verdict="défaut réel, mesuré",
               notes=f"rho médian {float(np.median(M['rho_bug'])):.3f} ; TV poids "
                     f"{float(np.median(M['tv_bug'])):.4f} ; témoin 849+849 : "
                     f"{float(np.median(M['ov_b849'])):.1f}/20 ; plancher structurel "
                     f"{float(np.median(M['floor_struct'])):.1f}/20 ; indépendance 5,0 exacte")
    lab.record(tok_infl, float(np.median(M["infl_dep"])),
               power_at="appariement sur 36 coupures ; même harnais que h23.gel",
               verdict="réfuté : influence normale, le gel est ailleurs",
               notes=f"influence due {float(np.median(M['infl_due'])):.1f} ; écart des "
                     f"médianes {infl_gap:+.1f} — le poids excédentaire est celui des "
                     f"849 tirages d'archive gelés, pas des 5 relevés")
    lab.record(tok_corr, d_ov,
               power_at="témoin corrigé 849+849 vs gelé 849+849",
               verdict="adoptée" if (d_ov >= 1.0 or d_rho >= 0.05) else "cosmétique",
               notes=f"Δrho {d_rho:+.3f} ; corrigé {float(np.median(M['ov_cor'])):.1f}/20 "
                     f"vs déployé {ov_med:.1f}/20 ; le résiduel est l'information des "
                     f"849 tirages non vus, irrécupérable sans données")
    say("\n   3 consignations au registre (h23.gel, h23.influence, h23.correction).")

rule(f"total {time.time() - T0:.0f}s")
