"""Transcription fidèle de l'Essaim de `Prophet/Services/Swarm.swift` en numpy.

Pourquoi ce fichier existe
--------------------------
Les 23 voies du dossier testent toutes une propriété des TIRAGES. Aucune n'a
jamais testé le PRÉDICTEUR lui-même. C'est pourtant la seule question dont la
réponse change le produit : « l'essaim déployé bat-il le hasard, et de
combien ? »

Pour poser cette question il faut le null de l'essaim, donc pouvoir le
rejouer des centaines de fois sur des archives synthétiques. Swift ne s'y
prête pas ici (pas de toolchain) ; cette transcription le permet.

Fidélité — ce qui est identique, ce qui ne l'est pas
----------------------------------------------------
Identique : les 26 têtes, leurs constantes, l'ordre des opérations
(évaluation AVANT absorption, à partir du 13ᵉ tirage), le z-score de
population, le top-20, AdaHedge (η = ln N / Δ, part fixe 2 %).

Différences assumées, toutes CONSERVATRICES pour le test :
  * l'évolution (mutation de la tête la plus faible d'une famille vers la
    plus forte, tous les 24 tirages) est DÉSACTIVÉE. Elle rendrait « la tête
    h » une cible mouvante, donc `S_h` ininterprétable. Une tête figée ne
    peut que sous-performer une tête qui s'adapte : si le banc figé ne bat
    pas le hasard, l'écart mesuré n'est pas gonflé par l'adaptation.
  * les égalités du tri sont départagées par l'indice croissant (Swift ne
    garantit pas la stabilité). L'effet porte sur ~0 numéro par tirage, les
    champs étant continus.
  * l'écho du bonus n'est pas appliqué : il ne concerne que la sélection des
    grilles affichées, pas les champs des têtes.

Toute la mécanique tourne sur des masques (T,80) booléens, réels ou simulés,
strictement de la même façon — c'est ce qui rend le null valide.

Le temps écoulé, et le bug qu'il révélait (h23)
-----------------------------------------------
Chaque tête ne décroissait que PAR TIRAGE ABSORBÉ : un trou de 849 tirages
dans le flux était traité comme zéro temps écoulé, et l'état « récent » de
l'essaim restait celui d'il y a 854 tirages (c'est le cas du prédicteur
déployé, cf. `lab/prediction.txt` et `lab/experiments/h23_trou_recence.py`).

La correction : chaque tête expose `advance(k)` — k tirages ÉCOULÉS sans
observation — et `run`/`predict_next` acceptent un vecteur `ids` de numéros
de tirage ; quand deux tirages absorbés consécutifs ne sont pas des numéros
consécutifs, les têtes avancent d'abord du temps manquant. Le principe est
uniforme : absorber l'ESPÉRANCE du tirage non observé (hit ≡ 20/80), en
forme fermée pour les états linéaires ; incrémenter les compteurs d'écart
du temps écoulé ; et déclarer perdu l'état conditionné à l'identité des
derniers tirages (Markov, voisinage, série), qu'un trou rend inconnaissable.
Sans `ids` (ou avec des ids consécutifs), rien ne change : les sorties sont
bit à bit identiques à la version antérieure.
"""

from __future__ import annotations

import copy

import numpy as np

POOL, DRAWN = 80, 20
P_BASE = DRAWN / POOL

# Le tirage « espéré » : ce qu'une absorption sans information injecte.
_NEUTRAL = np.full(POOL, P_BASE)


# --------------------------------------------------------------------------
# Têtes — chacune expose absorb(hit), field() et advance(k), hit étant un
# vecteur (80,) de 0/1. `field()` est TOUJOURS lue avant l'absorption du
# tirage courant ; `advance(k)` fait passer k tirages NON OBSERVÉS.
# --------------------------------------------------------------------------

class Head:
    family = "?"
    hid = "?"

    def absorb(self, hit: np.ndarray) -> None: ...
    def field(self) -> np.ndarray: ...

    def advance(self, k: int) -> None:
        """k tirages écoulés sans observation. Chaque tête doit dire ce que
        le temps seul fait à son état — aucune n'a le droit de l'ignorer."""
        raise NotImplementedError(self.hid)


class Bayes(Head):
    family = "Bayes"

    def __init__(self, memory, variant):
        self.memory, self.hid = memory, f"bayes.{variant}"
        self.a = np.full(POOL, 2.0)
        self.b = np.full(POOL, 6.0)

    def absorb(self, hit):
        g = 1 - 1 / max(2.0, self.memory)
        self.a = g * self.a + hit
        self.b = g * self.b + (1 - hit)

    def advance(self, k):
        # k absorptions de l'espérance (hit ≡ p), en forme fermée :
        # a ← gᵏ·a + p·(1−gᵏ)/(1−g). Le posterior décroît vers Beta(p·m, q·m),
        # de moyenne exactement p — l'ignorance, à la bonne vitesse.
        g = 1 - 1 / max(2.0, self.memory)
        gk = g ** k
        m = (1 - gk) / (1 - g)
        self.a = gk * self.a + P_BASE * m
        self.b = gk * self.b + (1 - P_BASE) * m

    def field(self):
        return self.a / (self.a + self.b)


class Ewma(Head):
    family = "EWMA"

    def __init__(self, memory, variant):
        self.memory, self.hid = memory, f"ewma.{variant}"
        self.e = np.full(POOL, P_BASE)

    def absorb(self, hit):
        l = 2 / (max(2.0, self.memory) + 1)
        self.e = (1 - l) * self.e + l * hit

    def advance(self, k):
        # e ← p + (1−l)ᵏ·(e − p) : la moyenne mobile décroît vers la base.
        l = 2 / (max(2.0, self.memory) + 1)
        self.e = P_BASE + (1 - l) ** k * (self.e - P_BASE)

    def field(self):
        return self.e


class Hawkes(Head):
    family = "Hawkes"

    def __init__(self, memory, variant):
        self.memory, self.hid = memory, f"hawkes.{variant}"
        self.s = np.zeros(POOL)

    def absorb(self, hit):
        d = np.exp(-0.6931 / max(0.5, self.memory))
        self.s = self.s * d + 0.42 * hit

    def advance(self, k):
        # s ← dᵏ·s + 0,42·p·(1−dᵏ)/(1−d) : l'excitation retombe vers son
        # niveau stationnaire, qui est uniforme — donc neutre après z-score.
        d = np.exp(-0.6931 / max(0.5, self.memory))
        dk = d ** k
        self.s = self.s * dk + 0.42 * P_BASE * (1 - dk) / (1 - d)

    def field(self):
        return 0.07 + self.s


class Weibull(Head):
    family = "Écarts"

    def __init__(self, k):
        self.k, self.hid = k, f"weibull.{int(k * 100)}"
        self.gap = np.zeros(POOL, np.int64)
        self.gap_mean = np.full(POOL, 1 / P_BASE)
        self.gap_count = np.zeros(POOL)

    def absorb(self, hit):
        self.gap += 1
        h = hit > 0
        c = self.gap_count
        first = h & (c <= 0)
        again = h & (c > 0)
        self.gap_mean[again] = ((self.gap_mean[again] * c[again] + self.gap[again])
                                / (c[again] + 1))
        self.gap_mean[first] = self.gap[first]
        self.gap_count[h] += 1
        self.gap[h] = 0

    def advance(self, k):
        # L'écart est un compteur de temps : il avance du temps écoulé. C'est
        # l'écart depuis la dernière sortie OBSERVÉE — le seul calculable ;
        # un numéro sorti dans le trou le garde donc surévalué, et la
        # normalisation z absorbe la part commune de ce biais.
        self.gap += k

    def field(self):
        mu = np.maximum(1.2, self.gap_mean)
        return 1 - np.exp(-np.power(self.gap / mu, self.k))


class Hazard(Head):
    family = "Écarts"
    hid = "hazard"

    def __init__(self):
        self.gap = np.zeros(POOL, np.int64)
        self.attempts = np.zeros(61)
        self.hits = np.zeros(61)

    def absorb(self, hit):
        self.gap += 1
        g = np.minimum(60, self.gap)
        np.add.at(self.attempts, g, 1.0)
        h = hit > 0
        np.add.at(self.hits, g[h], 1.0)
        self.gap[h] = 0

    def advance(self, k):
        # Même règle que Weibull ; les tables attempts/hits, elles, ne
        # comptent que des tirages OBSERVÉS et ne bougent pas.
        self.gap += k

    def field(self):
        g = np.minimum(60, self.gap + 1)
        return (self.hits[g] + 2) / (self.attempts[g] + 8)


class GapZ(Head):
    family = "Écarts"
    hid = "gapz"

    def __init__(self):
        self.gap = np.zeros(POOL, np.int64)
        self.m1 = np.full(POOL, 1 / P_BASE)
        self.m2 = np.full(POOL, 28.0)

    def absorb(self, hit):
        self.gap += 1
        h = hit > 0
        x = self.gap[h].astype(float)
        self.m1[h] += 0.15 * (x - self.m1[h])
        self.m2[h] += 0.15 * (x * x - self.m2[h])
        self.gap[h] = 0

    def advance(self, k):
        self.gap += k

    def field(self):
        sd = np.sqrt(np.maximum(1.0, self.m2 - self.m1 * self.m1))
        return (self.gap - self.m1) / sd


class Spectral(Head):
    family = "Spectre"

    def __init__(self, short, long, momentum):
        self.short, self.long, self.momentum = short, long, momentum
        self.hid = f"{'mom' if momentum else 'rev'}.{short}x{long}"
        self.q: list[np.ndarray] = []
        self.s_sum = np.zeros(POOL)
        self.l_sum = np.zeros(POOL)

    def absorb(self, hit):
        self.q.append(hit)
        self.s_sum += hit
        self.l_sum += hit
        if len(self.q) > self.short:
            self.s_sum -= self.q[len(self.q) - 1 - self.short]
        if len(self.q) > self.long:
            self.l_sum -= self.q.pop(0)

    def advance(self, k):
        # k absorptions du tirage espéré : les fenêtres vieillissent du temps
        # écoulé et les tirages non observés y pèsent leur espérance. Au-delà
        # de `long` pas, absorber davantage ne change plus rien.
        for _ in range(min(k, self.long)):
            self.absorb(_NEUTRAL)

    def field(self):
        n = max(1, len(self.q))
        s = self.s_sum / min(self.short, n)
        l = self.l_sum / min(self.long, n)
        return s - l if self.momentum else l - s


class Markov(Head):
    family = "Markov"

    def __init__(self, k):
        self.k, self.hid = k, f"markov.{k}"
        self.recent: list[np.ndarray] = []
        self.attempts = np.zeros(k + 1)
        self.hits = np.zeros(k + 1)

    def _presence(self):
        return np.sum(self.recent, axis=0).astype(np.int64) if self.recent \
            else np.zeros(POOL, np.int64)

    def absorb(self, hit):
        if len(self.recent) == self.k:
            c = self._presence()
            np.add.at(self.attempts, c, 1.0)
            np.add.at(self.hits, c[hit > 0], 1.0)
        self.recent.append(hit)
        if len(self.recent) > self.k:
            self.recent.pop(0)

    def advance(self, k):
        # La présence dans les k derniers tirages devient inconnaissable dès
        # qu'un tirage manque : l'état conditionnant est perdu. La tête
        # s'abstient (champ plat) jusqu'à revoir k tirages consécutifs, et
        # ses tables n'apprennent aucune transition traversant un trou.
        self.recent = []

    def field(self):
        if len(self.recent) != self.k:
            return np.full(POOL, P_BASE)
        c = self._presence()
        return (self.hits[c] + 2) / (self.attempts[c] + 8)


class Streak(Head):
    family = "Markov"
    hid = "streak"

    def __init__(self):
        self.streak = np.zeros(POOL)

    def absorb(self, hit):
        self.streak = np.where(hit > 0, self.streak + 1, 0.0)

    def advance(self, k):
        # Une série qui traverse k tirages non observés survit avec une
        # probabilité (1/4)ᵏ : la tête ne peut plus rien certifier.
        self.streak = np.zeros(POOL)

    def field(self):
        return self.streak


class Copair(Head):
    family = "Graphe"
    hid = "copair"

    def __init__(self):
        self.co = np.zeros((POOL, POOL))
        self.counts = np.zeros(POOL)
        self.n = 0
        self.last: np.ndarray | None = None

    def absorb(self, hit):
        nums = np.flatnonzero(hit > 0)
        self.co[np.ix_(nums, nums)] += 1
        self.co[nums, nums] -= 1          # la diagonale ne compte pas
        self.counts[nums] += 1
        self.n += 1
        self.last = nums

    def advance(self, k):
        # Les tables de co-sorties (long terme) restent ; l'ACTIVATION, elle,
        # est conditionnée au dernier tirage — qui n'est plus le précédent.
        self.last = None

    def field(self):
        if self.n <= 8 or self.last is None or len(self.last) == 0:
            return np.zeros(POOL)
        j = self.last
        denom = (self.counts[:, None] * self.counts[None, j] + 1) / self.n
        term = np.log((self.co[:, j] + 0.25) / denom)
        term[j, np.arange(len(j))] = 0.0  # a == b sauté
        return term.sum(axis=1) / len(j)


class Acp(Head):
    family = "ACP"

    def __init__(self, axis):
        self.axis, self.hid = axis, f"acp.{axis}"
        self.mean = np.full(POOL, P_BASE)
        self.pc1 = np.zeros(POOL)
        self.pc2 = np.zeros(POOL)
        self.t = 0

    @staticmethod
    def _norm(v):
        n = np.sqrt((v * v).sum())
        return v / (n if n != 0 else 1.0)

    def _oja(self, pc, x):
        if (pc * pc).sum() < 1e-9:
            return self._norm(x.copy())
        d = float(pc @ x)
        eta = 1 / np.sqrt(self.t + 2)
        return self._norm(pc + eta * d * (x - d * pc))

    def absorb(self, hit):
        self.mean += 0.04 * (hit - self.mean)
        x = hit - self.mean
        self.pc1 = self._oja(self.pc1, x)
        if self.axis == 2:
            xr = x - float(self.pc1 @ x) * self.pc1
            self.pc2 = self._oja(self.pc2, xr)
            self.pc2 = self._norm(self.pc2 - float(self.pc1 @ self.pc2) * self.pc1)
        self.t += 1

    def advance(self, k):
        # La moyenne décroît vers la base ; les axes d'Oja ne bougent pas —
        # le pas d'Oja sur x = E[hit] − mean ≈ 0 est un pas nul, et t ne
        # compte que les observations réelles.
        self.mean = P_BASE + (1 - 0.04) ** k * (self.mean - P_BASE)

    def field(self):
        pc = self.pc2 if self.axis == 2 else self.pc1
        return -pc * (self.mean - P_BASE) * 8


class Anti(Head):
    family = "Contra"

    def __init__(self, base):
        self.base, self.hid = base, f"anti.{base.hid}"

    def absorb(self, hit):
        self.base.absorb(hit)

    def advance(self, k):
        self.base.advance(k)

    def field(self):
        return -self.base.field()


_ROW = (np.arange(POOL)) % 10           # rangée du numéro n = (n-1) % 10


class Adjacency(Head):
    family = "Géo"
    hid = "geo.adj"

    def __init__(self):
        self.last: np.ndarray | None = None
        self.attempts = np.zeros(5)
        self.hits = np.zeros(5)

    @staticmethod
    def _neigh(last_hit):
        """Nombre de voisins (haut/bas/gauche/droite) sortis au tirage last."""
        c = np.zeros(POOL, np.int64)
        c[1:] += (last_hit[:-1] * (_ROW[1:] > 0)).astype(np.int64)      # n-1
        c[:-1] += (last_hit[1:] * (_ROW[:-1] < 9)).astype(np.int64)     # n+1
        c[10:] += last_hit[:-10].astype(np.int64)                       # n-10
        c[:-10] += last_hit[10:].astype(np.int64)                       # n+10
        return c

    def absorb(self, hit):
        if self.last is not None:
            k = self._neigh(self.last)
            np.add.at(self.attempts, k, 1.0)
            np.add.at(self.hits, k[hit > 0], 1.0)
        self.last = hit

    def advance(self, k):
        # Le « tirage précédent » du conditionnement n'existe plus.
        self.last = None

    def field(self):
        if self.last is None:
            return np.full(POOL, P_BASE)
        k = self._neigh(self.last)
        return (self.hits[k] + 2) / (self.attempts[k] + 8)


class RowPressure(Head):
    family = "Géo"
    hid = "geo.rangs"

    def __init__(self):
        self.rows = np.full(10, DRAWN / 10)

    def absorb(self, hit):
        count = np.bincount(_ROW, weights=hit, minlength=10)
        self.rows += 0.12 * (count - self.rows)

    def advance(self, k):
        exp_row = DRAWN / 10
        self.rows = exp_row + (1 - 0.12) ** k * (self.rows - exp_row)

    def field(self):
        exp_row = DRAWN / 10
        return (exp_row - self.rows[np.arange(POOL) % 10]) / exp_row


_DEC = np.arange(POOL) // 10            # décade du numéro n = (n-1) // 10
_PAR = (np.arange(POOL) + 1) % 2        # parité n % 2


class Pressure(Head):
    family = "Pression"
    hid = "pression"

    def __init__(self):
        self.dec = np.full(8, DRAWN / 8)
        self.par = np.full(2, DRAWN / 2)

    def absorb(self, hit):
        self.dec += 0.12 * (np.bincount(_DEC, weights=hit, minlength=8) - self.dec)
        self.par += 0.12 * (np.bincount(_PAR, weights=hit, minlength=2) - self.par)

    def advance(self, k):
        r = (1 - 0.12) ** k
        self.dec = DRAWN / 8 + r * (self.dec - DRAWN / 8)
        self.par = DRAWN / 2 + r * (self.par - DRAWN / 2)

    def field(self):
        d_exp, p_exp = DRAWN / 8, DRAWN / 2
        return (d_exp - self.dec[_DEC]) / d_exp + 0.5 * (p_exp - self.par[_PAR]) / p_exp


def make_heads() -> list[Head]:
    """Le banc exact de `SwarmEngine.makeHeads()`, dans le même ordre."""
    return [
        Bayes(10, "a"), Bayes(33, "b"), Bayes(200, "c"),
        Ewma(8, "a"), Ewma(25, "b"), Ewma(64, "c"),
        Hawkes(2.3, "a"), Hawkes(3.9, "b"), Hawkes(8.7, "c"),
        Weibull(1.25), Weibull(1.55),
        Hazard(), GapZ(),
        Spectral(16, 64, False), Spectral(8, 32, True),
        Markov(1), Markov(3), Streak(),
        Copair(),
        Acp(1), Acp(2),
        Anti(Ewma(25, "b")), Anti(Hawkes(3.9, "b")),
        Pressure(),
        Adjacency(), RowPressure(),
    ]


HEAD_IDS = [h.hid for h in make_heads()]
N_HEADS = len(HEAD_IDS)
WARMUP = 13                              # `absorbed > 12` dans Swift

# Loi exacte d'un recouvrement top-20 / tirage, pour TOUT choix de 20 numéros :
# hypergéométrique(80,20,20). C'est le théorème qui rend le test valide sans
# rien supposer du contenu des prédictions.
OV_MEAN = DRAWN * DRAWN / POOL                                  # 5
OV_SD = float(np.sqrt(DRAWN * (DRAWN / POOL) * (1 - DRAWN / POOL)
                      * (POOL - DRAWN) / (POOL - 1)))           # 1.68764


def _z(v: np.ndarray) -> np.ndarray:
    m = v.mean()
    s = np.sqrt(((v - m) ** 2).mean())
    return (v - m) / (s if s != 0 else 1.0)


def _top(v: np.ndarray, k: int = DRAWN) -> np.ndarray:
    """Les k plus grands, égalités départagées par indice croissant."""
    return np.argsort(-v, kind="stable")[:k]


def _ada_update(w, cum_loss, ada_gap, losses, n):
    """Un pas d'AdaHedge — extrait pour être exécuté à l'IDENTIQUE (mêmes
    opérations, même ordre) par run, predict_next et SwarmState. Mute
    `cum_loss` en place ; renvoie (w, ada_gap)."""
    eta = np.log(n) / ada_gap
    h_loss = float(w @ losses)
    lmin = float(losses.min())
    accum = float(w @ np.exp(-eta * (losses - lmin)))
    mix = lmin - np.log(max(accum, 1e-300)) / eta
    ada_gap += max(0.0, h_loss - mix)
    cum_loss += losses
    eta = np.log(n) / ada_gap
    raw = np.exp(-eta * (cum_loss - cum_loss.min()))
    s = raw.sum()
    raw = np.full(n, 1 / n) if (s <= 0 or not np.isfinite(s)) else raw / s
    return 0.98 * raw + 0.02 / n, ada_gap


def _advance_if_hole(heads, ids, t) -> None:
    """Fait passer aux têtes le temps manquant entre ids[t-1] et ids[t]."""
    if ids is None or t == 0:
        return
    k = int(ids[t]) - int(ids[t - 1]) - 1
    if k > 0:
        for h in heads:
            h.advance(k)


def run(mask: np.ndarray, keep_picks: bool = True, progress: int = 0,
        ids: np.ndarray | None = None) -> dict:
    """Rejoue l'essaim en marche avant sur une archive (T,80).

    Renvoie les recouvrements par tête et par tirage — jamais un score
    agrégé : c'est l'appelant qui décide de la statistique, après
    pré-enregistrement.

    `ids`, optionnel : les numéros de tirage alignés sur `mask`. Quand deux
    lignes consécutives ne portent pas des numéros consécutifs, les têtes
    avancent d'abord du temps écoulé (h23). Sans `ids`, comportement
    antérieur, bit à bit.
    """
    T = len(mask)
    if ids is not None and len(ids) != T:
        raise ValueError("ids doit être aligné sur mask")
    heads = make_heads()
    n = len(heads)
    w = np.full(n, 1 / n)
    cum_loss = np.zeros(n)
    ada_gap = 1e-3
    steps = max(0, T - WARMUP)

    ov = np.empty((steps, n), np.int8)
    ov_ens = np.empty(steps, np.int8)
    eff = np.empty(steps)
    picks = np.empty((steps, n, DRAWN), np.int8) if keep_picks else None
    picks_ens = np.empty((steps, DRAWN), np.int8) if keep_picks else None

    j = 0
    for t in range(T):
        _advance_if_hole(heads, ids, t)
        hit = mask[t].astype(float)
        if t >= WARMUP:
            fields = np.stack([_z(h.field()) for h in heads])
            ens = w @ fields
            top_ens = _top(ens)
            ov_ens[j] = int(mask[t][top_ens].sum())
            tops = np.stack([_top(fields[i]) for i in range(n)])
            o = mask[t][tops].sum(axis=1)
            ov[j] = o
            if keep_picks:
                picks[j] = tops
                picks_ens[j] = top_ens
            # AdaHedge : pertes dans [0,1], η = ln(N)/Δ, Δ = écart de
            # mixabilité cumulé. Zéro paramètre libre.
            losses = 1 - o / DRAWN
            w, ada_gap = _ada_update(w, cum_loss, ada_gap, losses, n)
            p = w[w > 1e-12]
            eff[j] = float(np.exp(-(p * np.log(p)).sum()))
            j += 1
        for h in heads:
            h.absorb(hit)
        if progress and t % progress == 0:
            print(f"    swarm {t}/{T}", flush=True)

    return {"ov": ov, "ov_ens": ov_ens, "eff": eff,
            "picks": picks, "picks_ens": picks_ens, "steps": steps}


class SwarmState:
    """L'essaim comme ÉTAT clonable — pour les expériences qui branchent
    plusieurs futurs depuis un même préfixe (h23). `step()` exécute
    exactement les opérations de `run`/`predict_next`, dans le même ordre ;
    `advance()` fait passer du temps sans observation ; `predict()` rend le
    champ, le classement et les poids courants.
    """

    def __init__(self):
        self.heads = make_heads()
        self.n = len(self.heads)
        self.w = np.full(self.n, 1 / self.n)
        self.cum_loss = np.zeros(self.n)
        self.ada_gap = 1e-3
        self.absorbed = 0

    def clone(self) -> "SwarmState":
        return copy.deepcopy(self)

    def advance(self, k: int) -> None:
        if k > 0:
            for h in self.heads:
                h.advance(k)

    def step(self, hit_row: np.ndarray) -> None:
        """Évalue (dès l'échauffement passé) puis absorbe UN tirage."""
        hit = hit_row.astype(float)
        if self.absorbed >= WARMUP:
            fields = np.stack([_z(h.field()) for h in self.heads])
            o = hit_row[np.stack([_top(fields[i]) for i in range(self.n)])].sum(axis=1)
            losses = 1 - o / DRAWN
            self.w, self.ada_gap = _ada_update(
                self.w, self.cum_loss, self.ada_gap, losses, self.n)
        for h in self.heads:
            h.absorb(hit)
        self.absorbed += 1

    def predict(self) -> dict:
        fields = np.stack([_z(h.field()) for h in self.heads])
        ens = self.w @ fields
        order = np.argsort(-ens, kind="stable")
        return {"field": ens, "weights": self.w.copy(),
                "ranking": (order + 1).tolist(),
                "top20": sorted((_top(ens) + 1).tolist())}


def predict_next(mask: np.ndarray, ids: np.ndarray | None = None) -> dict:
    """Le champ de l'essaim APRÈS absorption du dernier tirage connu.

    `run` rejoue et note ; cette fonction fait la même boucle, exactement les
    mêmes mises à jour d'AdaHedge et les mêmes absorptions, puis pousse un
    pas de plus : elle calcule le champ que l'essaim opposerait au tirage
    SUIVANT, celui qui n'a pas encore eu lieu.

    C'est la seule fonction du dossier qui produise une prédiction plutôt
    qu'une évaluation. Elle ne prétend rien sur sa valeur : sous le théorème
    d'invariance, ses vingt numéros ont exactement la même loi de hits que
    n'importe quels vingt autres. Elle existe pour que cette affirmation
    porte sur une prédiction RÉELLE, et non sur une abstraction.

    `ids`, optionnel : numéros de tirage alignés sur `mask` — un trou entre
    deux lignes fait d'abord passer le temps manquant aux têtes (h23). La
    prédiction vise le tirage qui SUIT immédiatement le dernier absorbé.
    """
    T = len(mask)
    if ids is not None and len(ids) != T:
        raise ValueError("ids doit être aligné sur mask")
    heads = make_heads()
    n = len(heads)
    w = np.full(n, 1 / n)
    cum_loss = np.zeros(n)
    ada_gap = 1e-3
    for t in range(T):
        _advance_if_hole(heads, ids, t)
        hit = mask[t].astype(float)
        if t >= WARMUP:
            fields = np.stack([_z(h.field()) for h in heads])
            o = mask[t][np.stack([_top(fields[i]) for i in range(n)])].sum(axis=1)
            losses = 1 - o / DRAWN
            w, ada_gap = _ada_update(w, cum_loss, ada_gap, losses, n)
        for h in heads:
            h.absorb(hit)
    fields = np.stack([_z(h.field()) for h in heads])
    ens = w @ fields
    order = np.argsort(-ens, kind="stable")
    return {"field": ens, "weights": w,
            "heads": [type(h).__name__ for h in heads],
            "ranking": (order + 1).tolist(),
            "top20": sorted((_top(ens) + 1).tolist())}


def z_of(ov_col: np.ndarray) -> float:
    """Écart standardisé d'une série de recouvrements à son espérance exacte."""
    T = len(ov_col)
    return float((ov_col.sum() - T * OV_MEAN) / (OV_SD * np.sqrt(T)))
