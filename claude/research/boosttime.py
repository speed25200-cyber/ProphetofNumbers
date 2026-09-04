"""Le boost est-il PREVISIBLE PAR L'HORLOGE ? La seule question du dossier dont un « oui »
serait exploitable sans aucune fuite d'information et sans casser le moindre generateur.

Si l'operateur programme les forts multiplicateurs a certaines heures (promotion du soir,
week-end, tranche horaire), alors P(boost >= 4) depend de l'heure — et un joueur qui ne
mise que dans ces creneaux a une esperance superieure SANS voir le boost a l'avance. C'est
le contraire d'un RNG casse : c'est une politique commerciale, et elle laisserait une
trace dans 70 560 tirages horodates.

Tests, dans l'ordre :
  1. tables heure (UTC et heure suisse), jour de semaine, creneau de 5 min : chi2
     d'independance entre le creneau et le boost, et P(boost >= 4) par creneau
  2. autocorrelation de l'indicateur [boost >= 4] a tous les decalages 1..4000
  3. spectre (FFT) du meme indicateur : un pic isole trahirait une periodicite
  4. la meme batterie sur la position du bonus et sur la somme des 20 numeros, pour
     savoir si la GRAINE du generateur, elle, change avec l'heure
Chaque statistique est accompagnee de sa valeur sous un controle ou l'archive est
melangee aleatoirement dans le temps : c'est la reference du « rien ».
"""
import numpy as np, math
from datetime import datetime, timezone, timedelta
from load import load

ids, ts, nums, boost, bonus = load()
N = len(ts)
hi = (boost >= 4).astype(float)            # 10 % des tirages, E[boost|>=4] = 5,75
b10 = (boost == 10).astype(float)
rng = np.random.default_rng(2026)

def zurich(t):
    # heure suisse : CET/CEST, calcul explicite (dernier dimanche de mars / octobre)
    d = datetime.fromtimestamp(int(t), tz=timezone.utc)
    y = d.year
    def last_sun(m):
        x = datetime(y, m, 31, 1, 0, tzinfo=timezone.utc)
        while x.weekday() != 6: x -= timedelta(days=1)
        return x
    off = 2 if last_sun(3) <= d < last_sun(10) else 1
    return d + timedelta(hours=off)

loc = [zurich(t) for t in ts]
hour_utc = np.array([datetime.fromtimestamp(int(t), tz=timezone.utc).hour for t in ts])
hour_ch  = np.array([d.hour for d in loc])
dow_ch   = np.array([d.weekday() for d in loc])
slot     = np.array([(d.hour * 60 + d.minute) // 5 for d in loc])
month    = np.array([d.month for d in loc])

def chi2_indep(cat, val, ncat, label):
    K = len(np.unique(val))
    vv = np.unique(val); vi = np.searchsorted(vv, val)
    tab = np.zeros((ncat, K))
    np.add.at(tab, (cat, vi), 1)
    # le jeu ne tourne pas 24 h sur 24 : les categories VIDES ne comptent pas dans les
    # degres de liberte. Une premiere version comptait 288 creneaux la ou ~197 sont
    # occupes, ce qui faisait sortir un z = -8 « significatif »... que le controle melange
    # reproduisait a l'identique (1005,6 contre 1006,7 +- 30). Le controle a fait son
    # travail ; les ddl sont maintenant justes.
    tab = tab[tab.sum(1) > 0]
    ncat = tab.shape[0]
    row = tab.sum(1, keepdims=True); col = tab.sum(0, keepdims=True)
    exp = row @ col / N
    ok = exp > 0
    chi = float((((tab - exp) ** 2)[ok] / exp[ok]).sum())
    df = (ncat - 1) * (K - 1)
    # controle : meme statistique sur un boost melange dans le temps
    ctrl = []
    for _ in range(5):
        pv = rng.permutation(vi)
        t2 = np.zeros((cat.max() + 1, K)); np.add.at(t2, (cat, pv), 1)
        t2 = t2[t2.sum(1) > 0]
        e2 = t2.sum(1, keepdims=True) @ t2.sum(0, keepdims=True) / N
        ctrl.append(float((((t2 - e2) ** 2)[e2 > 0] / e2[e2 > 0]).sum()))
    z = (chi - df) / math.sqrt(2 * df)
    print("  %-34s chi2 = %8.1f / %5d ddl   z = %+6.2f   (melange : %.1f +- %.1f)%s"
          % (label, chi, df, z, np.mean(ctrl), np.std(ctrl), "   <<<" if abs(z) > 4 else ""))
    return z

print("=" * 90)
print("1. LE BOOST DEPEND-IL DU MOMENT ?   (70 560 tirages, 288 creneaux/jour, 358 jours)")
print("=" * 90)
chi2_indep(hour_utc, boost, 24, "boost x heure UTC")
chi2_indep(hour_ch, boost, 24, "boost x heure suisse")
chi2_indep(dow_ch, boost, 7, "boost x jour de semaine")
chi2_indep(slot, boost, 288, "boost x creneau de 5 min")
chi2_indep(month - 1, boost, 12, "boost x mois")
print()
print("  P(boost >= 4) par heure suisse  (global %.4f, ecart-type par case ~%.4f) :"
      % (hi.mean(), math.sqrt(hi.mean() * (1 - hi.mean()) / (N / 24))))
for h in range(24):
    m = hour_ch == h
    n = int(m.sum())
    if n == 0: print("    %02dh  (pas de tirage)" % h); continue
    p = hi[m].mean()
    z = (p - hi.mean()) / math.sqrt(hi.mean() * (1 - hi.mean()) / n)
    print("    %02dh  n=%4d  P=%.4f  z=%+5.2f  %s" % (h, n, p, z, "#" * int(abs(z) * 2)))
print()
print("  P(boost >= 4) par jour (lun=0) :")
for d in range(7):
    m = dow_ch == d; n = int(m.sum())
    if n == 0: continue
    p = hi[m].mean()
    z = (p - hi.mean()) / math.sqrt(hi.mean() * (1 - hi.mean()) / n)
    print("    %d  n=%5d  P=%.4f  z=%+5.2f" % (d, n, p, z))

print("\n" + "=" * 90)
print("2. AUTOCORRELATION DE [boost >= 4], decalages 1..4000")
print("=" * 90)
x = hi - hi.mean()
den = float((x * x).sum())
lags = np.arange(1, 4001)
ac = np.array([float((x[:-L] * x[L:]).sum()) / den for L in lags])
sd = 1 / math.sqrt(N)
top = np.argsort(-np.abs(ac))[:8]
print("  ecart-type sous le nul : %.5f ; sur 4000 decalages le max attendu ~ %.4f" % (sd, 3.9 * sd))
for i in top:
    print("    lag %4d  r = %+.5f  (%+.1f sigma)%s" % (lags[i], ac[i], ac[i] / sd, "   <<<" if abs(ac[i]) > 4.5 * sd else ""))
print("  decalages structurels : 288 (un jour) r=%+.5f, 2016 (une semaine) r=%+.5f"
      % (ac[287], ac[2015]))

print("\n" + "=" * 90)
print("3. SPECTRE DE [boost >= 4]")
print("=" * 90)
F = np.abs(np.fft.rfft(x)) ** 2
F[0] = 0
freqs = np.fft.rfftfreq(N, d=1.0)
med = np.median(F[1:])
top = np.argsort(-F)[:6]
print("  puissance mediane %.3g ; un pic isole depasserait ~%.3g (30 x mediane)" % (med, 30 * med))
for i in top:
    per = 1 / freqs[i] if freqs[i] > 0 else float("inf")
    print("    periode %9.2f tirages (%7.2f h)  puissance %.3g  (%.1f x mediane)%s"
          % (per, per * 5 / 60, F[i], F[i] / med, "   <<<" if F[i] > 30 * med else ""))
Fc = np.abs(np.fft.rfft(rng.permutation(x))) ** 2; Fc[0] = 0
print("  controle melange : max = %.1f x mediane" % (Fc.max() / np.median(Fc[1:])))

print("\n" + "=" * 90)
print("4. ET LE GENERATEUR LUI-MEME : la position du bonus et la somme des 20 par heure")
print("=" * 90)
srt = np.sort(nums, axis=1)
pos = np.array([int(np.searchsorted(srt[i], bonus[i])) for i in range(N)])
chi2_indep(hour_ch, pos, 24, "position du bonus x heure")
chi2_indep(dow_ch, pos, 7, "position du bonus x jour")
ssum = srt.astype(int).sum(1)
q = np.digitize(ssum, np.quantile(ssum, np.linspace(0, 1, 11)[1:-1]))
chi2_indep(hour_ch, q, 24, "somme des 20 (deciles) x heure")
chi2_indep(hour_ch, srt[:, 0].astype(int) // 8, 24, "plus petit numero (8 classes) x heure")
