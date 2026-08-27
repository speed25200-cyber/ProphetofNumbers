"""Chasse sur V3 — le résidu le plus cohérent du dossier, et ce qu'il vaudrait.

`d7_bonus.py` rapporte V3 : `bonus_t` appartient au tirage `t+1` dans
**0,24605** des cas, contre 0,25000 attendu — un déficit à `z = −2,58`.

C'est, avec S1, le plus grand écart du dossier. Mais contrairement à S1, il
survit à toutes les vérifications que l'archive permet. Ce fichier les fait
toutes, puis pose la seule question qui décide : **combien vaudrait-il s'il
était entièrement réel ?**

La réponse à cette dernière question est ce qui clôt le dossier, et elle
n'était pas évidente avant de la calculer.
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import lab

P0 = 0.25


def main():
    t0 = time.time()
    a = lab.load()
    n = len(a)
    bonus = a.bonus.astype(np.int64)
    nums = np.sort(a.nums.astype(np.int64), axis=1)
    hit = a.mask[1:][np.arange(n - 1), bonus[:-1] - 1].astype(float)
    se_all = np.sqrt(P0 * (1 - P0) / len(hit))
    obs = float(hit.mean())

    print("=" * 78)
    print("CHASSE SUR V3 — bonus_t dans le tirage t+1")
    print("=" * 78)
    print(f"\nobservé {obs:.5f} sur {len(hit)} paires   H0 = 0,25000   z = {(obs - P0)/se_all:+.2f}")

    print("\n1. Réplication — même signe dans les deux moitiés ?")
    h = len(hit) // 2
    for name, seg in (("1re moitié", hit[:h]), ("2e moitié", hit[h:])):
        se = np.sqrt(P0 * (1 - P0) / len(seg))
        print(f"   {name} : {seg.mean():.5f}   z = {(seg.mean() - P0) / se:+.2f}")
    k8 = len(hit) // 8
    negs = sum(1 for i in range(8) if hit[i * k8:(i + 1) * k8].mean() < P0)
    print(f"   huitièmes sous 0,25 : {negs}/8")
    print("   -> même signe partout. C'est ce que S1 ne faisait pas.")

    print("\n2. Spécificité au lag 1 — ou dérive de tous les lags ?")
    zs = []
    for k in range(1, 31):
        v = a.mask[k:][np.arange(n - k), bonus[:-k] - 1].mean()
        zs.append((v - P0) / np.sqrt(P0 * (1 - P0) / (n - k)))
    zs = np.array(zs)
    print(f"   lag 1 : {zs[0]:+.2f}")
    print(f"   lags 2-30 : moyenne {zs[1:].mean():+.3f} (H0 : 0 ± {1/np.sqrt(29):.3f}), "
          f"{int((zs[1:] < 0).sum())}/29 négatifs (H0 ≈ 14,5)")
    print("   -> le lag 1 est singulier, les autres sont du bruit pur.")

    print("\n3. Placebo — l'écart vient-il du champ bonus, ou du calcul ?")
    rng = np.random.default_rng(3)
    for t in range(5):
        fake = nums[np.arange(n), rng.integers(0, 20, size=n)]
        v = a.mask[1:][np.arange(n - 1), fake[:-1] - 1].mean()
        print(f"   essai {t + 1} : {v:.5f}   z = {(v - P0) / se_all:+.2f}")
    print("   -> en remplaçant le bonus par un des 20 numéros tiré par nous,")
    print("      l'écart disparaît. Il est spécifique au champ bonus réel.")

    print("\n4. Est-ce une propriété générale du tirage ?")
    ov = (a.mask[1:] & a.mask[:-1]).sum(1).astype(float)
    print(f"   recouvrement moyen des mêmes paires : {ov.mean():.5f} (H0 = 5,0)")
    print(f"   les 20 numéros sont repris à {ov.mean()/20:.5f}, le bonus à {obs:.5f}")
    print("   -> les deux vont en sens OPPOSÉS. Ce n'est pas une dérive du tirage.")

    print(f"\n{'-' * 78}\n5. CE QU'IL FAUDRAIT POUR TRANCHER")
    var = P0 * (1 - P0)
    d = P0 - obs
    print(f"   {'seuil visé':<32}{'z':>6}{'N total':>12}{'à collecter':>14}{'jours':>9}")
    for name, z in (("p = 0,05 (test unique)", 1.96), ("p = 0,001", 3.29),
                    ("seuil Holm du registre", 4.30)):
        N = z * z * var / (d * d)
        add = max(0, N - n)
        print(f"   {name:<32}{z:>6.2f}{N:>12,.0f}{add:>14,.0f}{add/204:>9,.0f}")

    print(f"\n{'-' * 78}\n6. ET SURTOUT — COMBIEN VAUDRAIT-IL S'IL ÉTAIT ENTIÈREMENT RÉEL ?")
    p_other = (20 - obs) / 79
    print(f"   Les probabilités d'inclusion somment à 20. Si le bonus précédent")
    print(f"   tombe à {obs:.6f}, les 79 autres montent à {p_other:.6f}.")
    print(f"\n   {'grille':<10}{'en évitant le bonus':>22}{'base':>10}{'gain':>12}")
    for k in (5, 10):
        base, best = k * P0, k * p_other
        print(f"   {k:<10}{best:>22.5f}{base:>10.5f}{(best - base)/base:>11.4%}")
    print("\n   +0,02 %. Une part sur cinq mille. À comparer au plafond de la piste A")
    print("   (+3,46 %), à ce que l'app affiche à tort (+18 à +34 %), et à l'avantage")
    print("   de la maison sur un Keno (−25 à −35 %).")
    print("\n   C'est la vraie conclusion : même en supposant l'écart entièrement réel")
    print("   et stable, l'exploiter ne rapporte rien. Un déficit sur UN numéro parmi")
    print("   80 se dilue sur les 79 autres, et une grille n'en coche que 5 à 10.")

    tok = lab.preregister(
        "d7b.chasse_v3",
        "Le déficit de bonus_t dans le tirage t+1 (z = −2,58) survit-il à la réplication, "
        "à la spécificité de lag et au placebo — et que vaudrait-il s'il était réel ?",
        "valeur exploitable d'un joueur évitant le bonus du tirage précédent",
        "vérifications internes à l'archive ; calcul exact de la valeur sous l'hypothèse réelle",
        "résidu conservé pour re-test sur données neuves si les vérifications passent",
        track="A")
    lab.record(tok, observed=(10 * p_other - 2.5) / 2.5, p=None,
               power_at=f"seuil Holm atteignable après ~{(4.30**2*var/(d*d) - n)/204:.0f} jours de tirages neufs",
               verdict="résidu cohérent mais sans valeur exploitable",
               notes=(f"z = {(obs-P0)/se_all:+.2f}, p = 0,010 contre un seuil de registre à 1,5e-05. "
                      "Survit à tout : même signe dans les deux moitiés et 7/8 huitièmes, lag 1 "
                      "singulier (lags 2-30 : moyenne +0,011), placebo propre, sens opposé au "
                      "recouvrement global. Mais sa valeur exploitable est +0,02 % — un déficit "
                      "sur un numéro parmi 80 se dilue sur les 79 autres."))
    print(f"\n{'=' * 78}\nconsigné au registre. total {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
