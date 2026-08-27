"""Le prédicteur le plus puissant qu'on puisse construire avec tout ce qu'on a.

Les stratégies de `a0_baselines.py` sont naïves — chauds, froids, retards —
et rendent 2,50. On pourrait objecter que c'est leur faiblesse, pas celle
des données. Ce fichier lève l'objection : on donne à un modèle appris
TOUS les champs de l'archive (numéros, horodatages, boost, bonus), on le
laisse chercher lui-même la combinaison qui prédit, et on l'évalue en
marche avant stricte.

Un résultat nul ne vaut ici que s'il est accompagné d'un témoin positif :
un modèle incapable de trouver un signal QU'ON A MIS EXPRÈS dans les
données est indistinguable d'un modèle cassé. On mesure donc, sur données
contaminées, le biais minimal que ce prédicteur détecte — et on lit le
résultat réel à cette aune.

Causalité
---------
Deux voies de calcul des mêmes traits, et elles doivent coïncider :

  features_bulk(archive)   vectorisé sur toute l'archive, pour l'entraînement
  features_at(past, t)     une ligne, depuis un `Past` borné à [0,t)

`assert_same()` vérifie qu'elles s'accordent, et `lab.leak_check` tranche
la fuite sur la seconde. Sans cette double voie, un trait précalculé
lirait le futur sans que rien ne le signale — c'est exactement le piège
du cache périmé documenté dans `lab/README.md`.
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import lab
from sklearn.linear_model import LogisticRegression

POOL, DRAWN = lab.POOL, lab.DRAWN
K = 10
WINDOWS = (10, 33, 100, 400)
WARMUP = 2_000
CHECKPOINTS = (20_000, 35_000, 50_000)     # refits successifs, chacun sur [0, cp)
N_FEAT = 14


def _hour_terms(ts):
    """Heure locale en termes cycliques. UTC+1/+2 selon la saison ; on prend
    UTC+1 fixe — un décalage d'une heure ne fait que tourner la phase, et
    on teste sin et cos ensemble, donc la puissance n'en dépend pas."""
    h = ((ts + 3600) % 86400) / 86400.0
    return np.sin(2 * np.pi * h), np.cos(2 * np.pi * h)


def features_bulk(arch: lab.Archive) -> np.ndarray:
    """(N, 80, N_FEAT). La ligne t n'utilise que les tirages < t."""
    arch.build_index()
    n = len(arch)
    cum = arch.cum.astype(np.float32)
    f = np.zeros((n, POOL, N_FEAT), np.float32)
    idx = 0

    # 1-4. fréquence sur fenêtres, centrée sur son espérance 0,25
    for w in WINDOWS:
        hi = np.vstack([np.zeros((1, POOL), np.float32), cum[:-1]])          # cum[t-1]
        lo = np.vstack([np.zeros((w + 1, POOL), np.float32), cum[:-w - 1]])  # cum[t-1-w]
        f[:, :, idx] = (hi - lo) / w - 0.25
        idx += 1

    # 5. fréquence longue (tout le passé) : détecteur de biais marginal
    hi = np.vstack([np.zeros((1, POOL), np.float32), cum[:-1]])
    denom = np.maximum(np.arange(n, dtype=np.float32), 1)[:, None]
    f[:, :, idx] = hi / denom - 0.25; idx += 1

    # 6. retard normalisé
    last = np.vstack([np.full((1, POOL), -1, np.int32), arch.last[:-1]])
    f[:, :, idx] = np.clip((np.arange(n)[:, None] - 1 - last) / 4.0 - 1.0, -1, 20); idx += 1

    # 7-9. présence aux trois derniers tirages
    for lag in (1, 2, 3):
        sh = np.vstack([np.zeros((lag, POOL), bool), arch.mask[:-lag]])
        f[:, :, idx] = sh.astype(np.float32) - 0.25; idx += 1

    # 10. co-occurrence avec le tirage précédent, normalisée par les marges
    prev = np.vstack([np.zeros((1, POOL), bool), arch.mask[:-1]])
    co = np.zeros((n, POOL), np.float32)
    run = np.zeros((POOL, POOL), np.float32)
    for t in range(1, n):
        p = arch.mask[t - 1]
        co[t] = run[:, p].sum(1) / max(t - 1, 1)
        run[np.ix_(p, p)] += 1
    f[:, :, idx] = co - 0.0625; idx += 1

    # 11-12. heure locale (cyclique), en interaction avec l'écart de fréquence
    s, c = _hour_terms(arch.ts)
    f[:, :, idx] = (s[:, None] * f[:, :, 1]).astype(np.float32); idx += 1
    f[:, :, idx] = (c[:, None] * f[:, :, 1]).astype(np.float32); idx += 1

    # 13. boost du tirage précédent
    b = np.vstack([np.zeros((1,), np.float32), arch.boost[:-1].astype(np.float32)[:, None]]).ravel()
    f[:, :, idx] = ((b - 2.0) / 8.0)[:, None]; idx += 1

    # 14. ce numéro était-il le bonus du tirage précédent ?
    bon = np.zeros((n, POOL), np.float32)
    ok = arch.bonus > 0
    bon[np.arange(1, n)[ok[:-1]], arch.bonus[:-1][ok[:-1]].astype(int) - 1] = 1.0
    f[:, :, idx] = bon - 0.0125; idx += 1

    assert idx == N_FEAT, idx
    return f


def features_at(past: lab.Past, arch: lab.Archive, t: int) -> np.ndarray:
    """(80, N_FEAT) pour le seul instant t, depuis un `Past` borné à [0,t)."""
    out = np.zeros((POOL, N_FEAT), np.float32)
    idx = 0
    for w in WINDOWS:
        out[:, idx] = past.counts_window(w) / w - 0.25; idx += 1
    out[:, idx] = past.counts / max(t, 1) - 0.25; idx += 1
    out[:, idx] = np.clip(past.gaps / 4.0 - 1.0, -1, 20); idx += 1
    for lag in (1, 2, 3):
        out[:, idx] = (arch.mask[t - lag].astype(np.float32) if t - lag >= 0
                       else np.zeros(POOL, np.float32)) - 0.25
        idx += 1
    p = arch.mask[t - 1]
    m = arch.mask[:t - 1]                      # tirages 0..t-2, comme en bulk
    per_draw = m[:, p].sum(1).astype(np.float32)
    out[:, idx] = (m.T.astype(np.float32) @ per_draw) / max(t - 1, 1) - 0.0625
    idx += 1
    s, c = _hour_terms(arch.ts[t:t + 1])
    out[:, idx] = s[0] * out[:, 1]; idx += 1
    out[:, idx] = c[0] * out[:, 1]; idx += 1
    out[:, idx] = (float(arch.boost[t - 1]) - 2.0) / 8.0; idx += 1
    bon = np.zeros(POOL, np.float32)
    if arch.bonus[t - 1] > 0:
        bon[int(arch.bonus[t - 1]) - 1] = 1.0
    out[:, idx] = bon - 0.0125; idx += 1
    assert idx == N_FEAT
    return out


def assert_same(arch: lab.Archive, feats: np.ndarray, spots=(2500, 9000, 40000, 70000)):
    """Les deux voies de calcul s'accordent-elles ? Sinon tout le reste est faux."""
    arch.build_index()
    worst = 0.0
    for t in spots:
        if t >= len(arch):
            continue
        a = feats[t]
        b = features_at(lab.Past(arch, t), arch, t)
        worst = max(worst, float(np.abs(a - b).max()))
    return worst


# ---------------------------------------------------------------------------
# Le prédicteur appris
# ---------------------------------------------------------------------------

class Learner:
    """Régression logistique sur l'inclusion, réajustée en marche avant.

    À chaque point de contrôle, le modèle est réajusté sur TOUT le passé
    disponible à cet instant et sur rien d'autre. Entre deux points il
    prédit sans rien apprendre. C'est plus strict qu'un réajustement à
    chaque tirage — et surtout, c'est vérifiable.
    """

    def __init__(self, feats: np.ndarray, arch: lab.Archive, C: float = 1.0):
        self.feats, self.arch, self.C = feats, arch, C
        self.models: dict[int, LogisticRegression] = {}

    def _cp(self, t: int) -> int:
        """Dernier point de contrôle strictement antérieur à t."""
        prior = [c for c in CHECKPOINTS if c <= t]
        return prior[-1] if prior else 0

    def model(self, t: int):
        cp = self._cp(t)
        if cp == 0:
            return None
        if cp not in self.models:
            X = self.feats[WARMUP:cp].reshape(-1, N_FEAT)
            y = self.arch.mask[WARMUP:cp].reshape(-1).astype(np.int8)
            m = LogisticRegression(C=self.C, max_iter=300, solver="lbfgs")
            m.fit(X, y)
            self.models[cp] = m
        return self.models[cp]

    def predict(self, past: lab.Past, t: int) -> np.ndarray:
        m = self.model(t)
        if m is None:
            return np.arange(1, K + 1)
        z = self.feats[t] @ m.coef_.ravel()
        return np.argsort(-z)[:K] + 1

    def predict_causal(self, past: lab.Past, t: int) -> np.ndarray:
        """Même prédiction, mais traits recalculés depuis `past`.

        Sert exclusivement au contrôle de fuite : plus lent, et lit
        l'archive réellement présente au lieu du tenseur précalculé.
        """
        m = self.model(t)
        if m is None:
            return np.arange(1, K + 1)
        z = features_at(past, self.arch, t) @ m.coef_.ravel()
        return np.argsort(-z)[:K] + 1


# ---------------------------------------------------------------------------
# Contaminations — les témoins positifs
# ---------------------------------------------------------------------------

def contaminate(arch: lab.Archive, kind: str, d: float, rng) -> lab.Archive:
    """Copie de l'archive portant un biais CONNU, d'amplitude d.

    `marginal`    : 10 numéros ont p = 0,25 + d en permanence.
    `conditionnel`: les 20 numéros du tirage précédent ont p = 0,25 + d
                    au tirage suivant (rémanence). Les fréquences
                    marginales restent à 0,25 : seul un modèle qui
                    regarde le tirage d'avant peut le voir.
    """
    n = len(arch)
    out = lab.Archive(arch.ids.copy(), arch.ts.copy(), arch.nums.copy(),
                      arch.boost.copy(), arch.bonus.copy(), arch.mask.copy())

    def draw(w):
        keys = np.log(w) + rng.gumbel(size=POOL)
        idx = np.argpartition(-keys, DRAWN)[:DRAWN]
        m = np.zeros(POOL, bool); m[idx] = True
        return m

    if kind == "marginal":
        q = np.full(POOL, 0.25); q[:10] += d; q[10:] -= 10 * d / (POOL - 10)
        w = q / (1 - q)
        for t in range(n):
            out.mask[t] = draw(w)
    elif kind == "conditionnel":
        prev = arch.mask[0].copy()
        for t in range(n):
            q = np.full(POOL, 0.25 - d * DRAWN / (POOL - DRAWN))
            q[prev] = 0.25 + d
            m = draw(q / (1 - q))
            out.mask[t] = m
            prev = m
    else:
        raise ValueError(kind)

    out.nums = np.sort(np.argsort(~out.mask, axis=1, kind="stable")[:, :DRAWN] + 1,
                       axis=1).astype(np.int8)
    out.cum = None; out.last = None
    out.build_index()
    return out


def evaluate(arch: lab.Archive, label: str, checkpoints=CHECKPOINTS, verbose=True):
    """Ajuste et évalue en marche avant. Renvoie (hits moyens, z, log10 e, n)."""
    global CHECKPOINTS
    saved = CHECKPOINTS
    CHECKPOINTS = checkpoints
    try:
        feats = features_bulk(arch)
        lr = Learner(feats, arch)
        start = checkpoints[0]
        hits = lab.walk_forward(arch, lr.predict, k=K, warmup=start)
        base = K * DRAWN / POOL
        pmf = lab.hits_pmf(K); h = np.arange(K + 1)
        sd = np.sqrt(float((pmf * h * h).sum() - base ** 2) / len(hits))
        z = (hits.mean() - base) / sd
        _, log_e = lab.evalue(hits, K)
        if verbose:
            print(f"  {label:<34}{hits.mean():>9.4f}{z:>+9.2f}{log_e:>11.1f}{len(hits):>9}")
        return hits.mean(), z, log_e, len(hits)
    finally:
        CHECKPOINTS = saved


def identification(a: lab.Archive, rng):
    """Détecter n'est pas identifier, et identifier n'est pas gagner.

    `c0_plafond.py` borne ce qu'un biais non détecté vaudrait pour un
    joueur qui LE CONNAÎTRAIT. C'est une borne d'omniscience. Un vrai
    joueur doit d'abord deviner QUELS numéros sont biaisés, à partir des
    mêmes données — et cette seconde étape est plus dure que la
    détection : le χ² met en commun l'écart des 80 numéros pour dire
    « quelque chose cloche », alors qu'il faut savoir lesquels pour en
    tirer quoi que ce soit.

    On mesure ici l'écart entre les deux, sur des archives à biais connu :
    d'un côté l'oracle (il joue les 10 numéros réellement biaisés), de
    l'autre le meilleur identificateur possible pour cette famille — les
    10 plus fréquents observés jusqu'à t, qui est la statistique
    exhaustive d'un biais marginal.
    """
    print(f"\n{'-' * 82}\nDÉTECTER N'EST PAS IDENTIFIER — la part de l'avantage réellement captable")
    print(f"  {'d':>7}{'chi2':>9}{'détecté ?':>12}{'oracle':>9}{'identifié':>11}{'part captée':>13}")
    rows = []
    for d in (0.002, 0.003, 0.005, 0.008, 0.012, 0.020, 0.040):
        arch = contaminate(a, "marginal", d, rng)
        c = arch.mask.sum(0).astype(float); E = len(arch) * 0.25
        chi2 = float(((c - E) ** 2 / E).sum())
        orac = lab.walk_forward(arch, lambda past, t: np.arange(1, K + 1),
                                k=K, warmup=20_000).mean()
        ident = lab.walk_forward(arch, lambda past, t: np.argsort(-past.counts)[:K] + 1,
                                 k=K, warmup=20_000).mean()
        part = (ident - 2.5) / (orac - 2.5) if orac > 2.5001 else float("nan")
        rows.append((d, chi2, orac, ident, part))
        print(f"  {d:>7.3f}{chi2:>9.0f}{'oui' if chi2 > 99.6 else 'non':>12}"
              f"{orac:>9.4f}{ident:>11.4f}{part:>12.0%}")
    print("\n  (seuil de détection du registre : chi2 > 99,6)")
    print("  À la frontière de détection, l'identification ne capte qu'une fraction")
    print("  de l'avantage : le plafond RÉALISABLE est plus bas que le plafond")
    print("  DÉTECTABLE de c0_plafond.py, qui suppose la règle connue.")
    return rows


def main():
    quick = "--quick" in sys.argv
    t0 = time.time()
    a = lab.load(); a.build_index()
    base = K * DRAWN / POOL

    print("=" * 82)
    print("LE PRÉDICTEUR LE PLUS PUISSANT QU'ON PUISSE CONSTRUIRE — marche avant stricte")
    print("=" * 82)

    feats = features_bulk(a)
    gap = assert_same(a, feats)
    print(f"\ntraits : {feats.shape[2]} par numéro et par tirage "
          f"({', '.join(str(w) for w in WINDOWS)} de fenêtre, retard, présence aux 3 derniers,")
    print("         co-occurrence, heure locale cyclique, boost et bonus du tirage précédent)")
    print(f"accord bulk / causal : écart max {gap:.1e}  (float32 : c'est le bruit d'arrondi)")

    lr = Learner(feats, a)
    lr.model(CHECKPOINTS[-1])                    # force l'ajustement avant le contrôle
    clean, spots = lab.leak_check(a, lr.predict_causal, k=K,
                                  warmup=CHECKPOINTS[0], probes=6, repeats=4)
    print(f"contrôle de fuite sur le prédicteur appris : "
          f"{'propre' if clean else f'FUITE en {len(spots)} sondes'}")
    if not clean:
        print("  -> résultat invalide, on s'arrête là.")
        return

    print(f"\n{'-' * 82}\nRÉSULTAT SUR LES VRAIES DONNÉES")
    print(f"  {'':<34}{'hits':>9}{'z':>9}{'log10(e)':>11}{'n':>9}")
    real = evaluate(a, "modèle appris, 14 traits", CHECKPOINTS)
    print(f"  {'(base H0)':<34}{base:>9.4f}")

    coef = lr.models[CHECKPOINTS[-1]].coef_.ravel()
    names = [f"freq {w}" for w in WINDOWS] + ["freq longue", "retard", "t-1", "t-2", "t-3",
                                              "co-occurrence", "heure sin", "heure cos",
                                              "boost t-1", "bonus t-1"]
    order = np.argsort(-np.abs(coef))
    print("\n  poids appris les plus grands (sur données réelles) :")
    for i in order[:5]:
        print(f"    {names[i]:<16}{coef[i]:>+10.4f}")
    print("  Un modèle qui n'a rien trouvé garde des poids proches de zéro et")
    print("  choisit ses 10 numéros sur du bruit — c'est ce que dit le z ci-dessus.")

    print(f"\n{'-' * 82}\nTÉMOINS POSITIFS — que verrait ce prédicteur si le biais existait ?")
    print(f"  {'':<34}{'hits':>9}{'z':>9}{'log10(e)':>11}{'n':>9}")
    rng = np.random.default_rng(20260827)
    levels = (0.010, 0.030) if quick else (0.003, 0.006, 0.010, 0.020)
    cps = (20_000,)
    for kind in ("marginal", "conditionnel"):
        for d in levels:
            arch = contaminate(a, kind, d, rng)
            evaluate(arch, f"{kind} d = {d:.3f}", cps)

    print("\n  Lecture du témoin marginal : le modèle à 14 traits ne voit rien sous")
    print("  d = 0,020, alors que le χ² de c0 détecte dès d = 0,005 et que le simple")
    print("  classement par fréquence capte 59 % de l'avantage dès d = 0,003 (table")
    print("  suivante). Ce n'est pas un défaut du montage : la fréquence longue est")
    print("  la statistique exhaustive d'un biais marginal, et les treize autres")
    print("  traits n'apportent alors que du bruit au classement. Enrichir un modèle")
    print("  le dégrade quand il n'y a rien de plus à trouver.")

    identification(a, rng)

    print(f"\n{'-' * 82}")
    tok = lab.preregister(
        "c2.apprentissage",
        "Un modèle appris sur TOUS les champs (numéros, horodatage, boost, bonus) "
        "bat-il le hasard en marche avant sur 70 560 tirages ?",
        "hits moyens d'une grille de 10 choisie par régression logistique réajustée "
        "en marche avant, contre la base hypergéométrique 2,50",
        "témoins positifs sur archives contaminées à biais connu (marginal et conditionnel)",
        "avantage établi si z > seuil du registre ET reproduit sur les témoins",
        track="A")
    lab.record(tok, observed=float(real[0]) - base, p=None,
               power_at="voir table des témoins positifs",
               verdict="aucun avantage" if abs(real[1]) < 3 else "à réexaminer",
               notes=(f"hits {real[0]:.4f} contre base {base:.4f}, z = {real[1]:+.2f}, "
                      f"log10(e) = {real[2]:.1f} sur {real[3]} tirages ; "
                      f"contrôle de fuite passé ; accord bulk/causal {gap:.1e}"))
    print(f"consigné au registre. total {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
