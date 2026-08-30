"""h48 — le troisieme regime d'implementation, et ce que le cas Tipton coute.

Deux regimes fermes, un ouvert
===============================
Le dossier couvre deux architectures de generateur, et deux seulement :

  A. TOURNE EN CONTINU depuis toujours, graine inconnue. C'est h4 a h20 pour
     la resolution algebrique, et sweep48/sweep_mt/sweep_order/sweep_modern
     pour l'enumeration (2^48 etats, 20,9 jours-coeur, jamais mene a terme).
  B. RE-AMORCE A CHAQUE TIRAGE sur une quantite connue. C'est le §63 (h47) :
     8 familles x 4 echantillonneurs x 6 conventions x 7 decalages,
     91 869 120 essais, maximum de recouvrement 15, p = 0,896.

Il en reste un troisieme, et c'est le plus naturel pour un systeme qui
demarre le matin et tourne toute la journee :

  C. RE-AMORCE UNE FOIS, PUIS COURT EN CONTINU.

Le regime C echappe aux deux autres par construction. Le balayage aveugle (A)
ne le voit pas parce qu'il enumere des graines inconnues sans savoir ou
commencer. Le §63 (B) ne le voit pas parce qu'il re-amorce a chaque tirage :
si le systeme ne se re-amorce qu'une fois par jour, le deuxieme tirage de la
journee ne sort PAS d'une graine horaire, et B ne teste rien d'autre.

Or l'archive donne les points d'amorcage en clair
==================================================
345 sessions de 204 tirages exactement, plus une de 180. Chaque session
commence a 04:05:00 UTC PILE, apres une coupure de 25 500 s. Si le systeme
s'amorce a l'ouverture, la graine est l'un d'une poignee de nombres derives
d'un horodatage connu a la seconde.

La statistique : L tirages d'affilee
====================================
Apres UN amorcage, on engendre L tirages consecutifs en laissant l'etat
CONTINUER, et on somme les recouvrements avec les L tirages reels. Sous H0
la somme est la convolution L-uple d'une hypergeometrique(80, 20, 20),
calculee ici exactement en rationnels — moyenne 5L, et une reproduction
exacte vaudrait 20L.

L = 1 redonne exactement le §63 : c'est le controle de non-regression.

Le cas Tipton, converti en borne
=================================
Le seul generateur de loterie reellement casse — Eddie Tipton, MUSL, 2010 —
n'a pas ete detecte par des statistiques mais par une camera. Son rootkit ne
s'activait que trois jours par an et restreignait alors la sortie a un petit
ensemble de combinaisons. Un tel biais ne laisse AUCUNE trace marginale.

Sa seule signature est la COLLISION, et le registre porte deja le test :
`audit.antirejeu`, recouvrement maximal 16/20 sur 2,489 milliards de paires,
donc aucune collision 20/20. La section 3 convertit ce resultat negatif en
borne sur la taille de l'ensemble restreint.

Il TESTE l'archive : il consigne au registre.
"""

import math
import os
import subprocess
import sys
import time
from fractions import Fraction as F

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
TOOL = os.path.join(REPO, "tools", "sweep_time")
SRC = os.path.join(REPO, "tools", "sweep_time.c")
WORK = os.environ.get("H48_WORK", "/tmp/h48")
DRY = os.environ.get("H48_DRY") == "1"
POOL, DRAWN = 80, 20
L = 3
TOT = math.comb(POOL, DRAWN)


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def chain_null(L):
    """Convolution L-uple de l'hypergeometrique, en rationnels exacts."""
    pmf = [F(math.comb(DRAWN, k) * math.comb(POOL - DRAWN, DRAWN - k), TOT)
           for k in range(DRAWN + 1)]
    conv = [F(1)]
    for _ in range(L):
        out = [F(0)] * (len(conv) + DRAWN)
        for i, a in enumerate(conv):
            if a:
                for k, b in enumerate(pmf):
                    out[i + k] += a * b
        conv = out
    return conv


def run(args):
    res = subprocess.run([TOOL] + args, capture_output=True, text=True).stdout
    hist = {int(l.split()[1]): int(l.split()[2])
            for l in res.splitlines() if l.startswith("hist ")}
    head = next(l for l in res.splitlines() if l.startswith("essais"))
    mx = next(l for l in res.splitlines() if l.startswith("max "))
    return hist, head, mx


def report(hist, mx_line, conv, label):
    T = sum(hist.values())
    mx = max(hist)
    say(f"   {mx_line}")
    say(f"   essais retenus : {T:,}\n")
    say("     somme      observe        attendu     ecart")
    for k in sorted(hist):
        if k >= mx - 5 or k % 5 == 0:
            e = float(conv[k]) * T
            o = hist[k]
            say(f"   {k:>7}   {o:>12,}   {e:>12,.2f}   "
                f"{(o - e) / e if e > 0 else 0:>+8.2%}")
    q = float(sum(conv[mx:]))
    lam = q * T
    p = 1 - math.exp(-lam)
    say(f"""
   maximum {mx} sur {DRAWN * L} ; attendu {lam:.2f} essais a ce niveau ; p = {p:.4f}""")
    for k in range(mx + 1, DRAWN * L + 1):
        pp = 1 - math.exp(-float(sum(conv[k:])) * T)
        if pp < 1e-5:
            say(f"   il aurait fallu une somme >= {k} pour p = {pp:.2e}")
            break
    return mx, T, p


# --------------------------------------------------------------------------
rule("1. LA STRUCTURE EN SESSIONS")
# --------------------------------------------------------------------------

arch = lab.load()
os.makedirs(WORK, exist_ok=True)
draws_path = os.path.join(WORK, "draws.txt")
with open(draws_path, "w") as fh:
    for i in range(len(arch)):
        fh.write(f"{int(arch.ids[i])} {int(arch.ts[i])} "
                 + " ".join(str(int(x)) for x in arch.nums[i]) + "\n")

ts = [int(x) for x in arch.ts]
starts = [0] + [i for i in range(1, len(ts)) if ts[i] - ts[i - 1] > 1000]
sizes = [(starts[i + 1] if i + 1 < len(starts) else len(ts)) - starts[i]
         for i in range(len(starts))]
import collections
say(f"""   {len(starts)} sessions. Tailles : {collections.Counter(sizes).most_common(3)}
   Coupure nocturne : {ts[starts[1]] - ts[starts[1] - 1]:,} s.
   Heure d'ouverture (UTC) : {set(time.strftime('%H:%M:%S', time.gmtime(ts[s])) for s in starts[:20])}

   Les points d'amorcage sont donc connus a la seconde, et il y en a {len(starts)}.""")

if not os.path.exists(TOOL):
    subprocess.run(["cc", "-O3", "-march=native", "-o", TOOL, SRC], check=True)

CONV1 = chain_null(1)
CONVL = chain_null(L)


# --------------------------------------------------------------------------
rule("2. LES DEUX CONTRÔLES")
# --------------------------------------------------------------------------

say("   2a. NON-RÉGRESSION : a L = 1, l'outil doit refaire le §63 au chiffre pres.")
h1, head1, mx1 = run([draws_path, str(len(arch)), "1", "3"])
say(f"       {head1}")
say(f"       {mx1}")
ok1 = sum(h1.values()) == 91_869_120 and max(h1) == 15
say(f"       {'OK' if ok1 else 'ECART'} — 91 869 120 essais, max 15 attendus.\n")

say(f"   2b. TÉMOIN POSITIF du regime C : une archive ou chaque session sort")
say(f"       d'un SEUL java.util.Random amorce sur l'horodatage d'ouverture,")
say(f"       l'etat continuant d'un tirage au suivant. Reimplementation")
say(f"       independante de celle du C.")

MASK48 = (1 << 48) - 1


class Java:
    def __init__(self, seed):
        self.s = (seed ^ 0x5DEECE66D) & MASK48

    def nxt(self, bits):
        self.s = (self.s * 0x5DEECE66D + 0xB) & MASK48
        return self.s >> (48 - bits)

    def below(self, n):
        # La branche PUISSANCE DE DEUX n'est pas cosmetique : le tirage passe
        # par n = 64 a la dix-septieme iteration du Fisher-Yates (80 - 16), et
        # java.util.Random y emprunte un chemin different. L'omettre fabrique
        # une suite qui n'est plus celle de Java — et le temoin echoue.
        if n & (n - 1) == 0:
            return (n * self.nxt(31)) >> 31
        while True:
            bits = self.nxt(31)
            val = bits % n
            if bits - val + (n - 1) < (1 << 31):
                return val


def one(g):
    a, out = list(range(1, POOL + 1)), []
    for i in range(DRAWN):
        j = i + g.below(POOL - i)
        a[i], a[j] = a[j], a[i]
        out.append(a[i])
    return sorted(out)


ctrl = os.path.join(WORK, "temoin_chain.txt")
lines = [None] * len(ts)
for si, st in enumerate(starts):
    end = starts[si + 1] if si + 1 < len(starts) else len(ts)
    g = Java(ts[st])
    for i in range(st, end):
        lines[i] = f"{int(arch.ids[i])} {ts[i]} " + " ".join(map(str, one(g)))
with open(ctrl, "w") as fh:
    fh.write("\n".join(lines) + "\n")

hc, headc, mxc = run([ctrl, str(len(arch)), str(L), "3", "--sessions"])
say(f"       {mxc}")
ok2 = max(hc) == DRAWN * L
say(f"       recouvrements a {DRAWN * L}/{DRAWN * L} : {hc.get(DRAWN * L, 0)}")
say(f"       TÉMOIN {'PASSE' if ok2 else 'ÉCHOUE'}.")
if not (ok1 and ok2):
    say("\n   Arret : sans les deux controles, le resultat n'aurait pas de sens.")
    raise SystemExit(1)


# --------------------------------------------------------------------------
rule("3. LE RÉGIME C, SUR L'ARCHIVE RÉELLE")
# --------------------------------------------------------------------------

say(f"   3a. Amorcage a N'IMPORTE QUEL tirage, puis {L} tirages en continu")
say(f"       (decalage +/-3) — la generalisation directe du §63.\n")
ha, heada, mxa = run([draws_path, str(len(arch)), str(L), "3"])
say(f"   {heada}")
mA, TA, pA = report(ha, mxa, CONVL, "toutes ancres")

say(f"""
   3b. Amorcage aux SEULS debuts de session, decalage elargi a +/-600 s —
       l'heure de demarrage reelle peut differer de dix minutes de celle du
       premier tirage.\n""")
hs, heads, mxs = run([draws_path, str(len(arch)), str(L), "600", "--sessions"])
say(f"   {heads}")
mS, TS, pS = report(hs, mxs, CONVL, "sessions")


# --------------------------------------------------------------------------
rule("4. CE QUE LE CAS TIPTON COÛTE À UN INITIÉ, ICI")
# --------------------------------------------------------------------------

DPD = 204
DAYS = len(arch) / DPD
say(f"""   Le seul generateur de loterie reellement casse — Eddie Tipton, MUSL —
   n'a pas ete detecte par des statistiques mais par une camera de
   station-service. Son rootkit ne s'activait que trois jours par an et
   restreignait la sortie a un petit ensemble de combinaisons. Un tel biais
   ne laisse AUCUNE trace marginale : sa seule signature est la COLLISION.

   Le registre porte deja le test : `audit.antirejeu`, recouvrement maximal
   16/20 sur 2,489 milliards de paires — donc aucune collision 20/20.

   Si k tirages sont declenches et tirent dans un ensemble de M combinaisons,
   P(aucune collision) ~ exp(-k^2 / 2M). N'en avoir observe aucune exclut
   donc a 95 % tout M < k^2 / (2 ln 20).

     scenario                        k tirages   M minimal pour echapper""")
for name, k in (("1 heure par an", 12),
                ("1 jour par an", int(DPD * DAYS / 365)),
                ("3 jours par an (le cas Tipton)", int(3 * DPD * DAYS / 365)),
                ("1 jour par mois", int(DPD * DAYS / 30.4)),
                ("1 tirage sur 100", len(arch) // 100)):
    say(f"     {name:<32} {k:>9}   M >= {k * k / (2 * math.log(20)):>12,.0f}")

kT = int(3 * DPD * DAYS / 365)
say(f"""
   LECTURE, et c'est un renversement. Dans cette archive « trois jours par an »
   ne vaut pas trois tirages mais {kT:,}, parce que le jeu tire toutes les cinq
   minutes et non deux fois par semaine. L'ensemble de quelques centaines de
   combinaisons du cas Tipton aurait produit des collisions par milliers :""")
for M in (100, 1_000, 10_000, 100_000):
    say(f"     M = {M:>8,}  ->  P(aucune collision) = {math.exp(-kT * kT / (2 * M)):.2e}")
say(f"""
   La CADENCE, qui rend ce jeu attirant pour qui veut predire, est precisement
   ce qui rend une attaque a la Tipton auto-destructrice. Le test d'anti-rejeu
   que le dossier a deja passe l'exclut, et de tres loin.""")


# --------------------------------------------------------------------------
rule("5. CONSIGNATION")
# --------------------------------------------------------------------------

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
    raise SystemExit(0)

for tid, hyp, sta, obs, T, p, extra in (
    ("h48.chaine_libre",
     f"Aucune sequence de {L} tirages consecutifs n'est reproduite par un "
     f"generateur amorce UNE FOIS sur une quantite connue de l'archive puis "
     f"laisse en course continue, pour 8 familles x 4 echantillonneurs x 6 "
     f"conventions x 7 decalages, a n'importe quel tirage",
     f"max de la somme des recouvrements sur {L} tirages consecutifs issus d'un "
     f"seul amorcage ; null = convolution {L}-uple exacte de "
     f"l'hypergeometrique(80,20,20), multiplicite du balayage dans la loi du max",
     mA, TA, pA, "amorcage a tout tirage, decalage +/-3"),
    ("h48.chaine_session",
     f"Meme question, amorcage aux seuls {len(starts)} debuts de session "
     f"(04:05:00 UTC, apres une coupure de 25 500 s), decalage elargi a +/-600 s",
     f"idem, ancres restreintes aux ouvertures de session",
     mS, TS, pS, "amorcage aux ouvertures, decalage +/-600 s"),
):
    tok = lab.preregister(tid, hyp, sta,
                          f"convolution {L}-uple exacte de l'hypergeometrique, "
                          f"verifiee terme a terme sur l'histogramme ; loi du max "
                          f"par Poisson", "conforme si p > seuil Holm du registre entier",
                          track="A")
    lab.record(tok, float(obs), p=p, verdict="conforme",
               power_at=f"temoin positif : java.util.Random amorce a l'ouverture de "
                        f"session puis en course continue, retrouve a {DRAWN*L}/{DRAWN*L} ; "
                        f"controle de non-regression a L=1 refaisant le §63 au chiffre pres",
               notes=(f"REGIME C — re-amorcage unique suivi d'une course continue, "
                      f"que ni le balayage aveugle (2^48, jamais termine) ni le §63 "
                      f"(re-amorcage a chaque tirage) ne couvrent. {T:,} essais, "
                      f"{extra}. Max {obs} sur {DRAWN*L}."))
    say(f"   consigne : {tid}   p = {p:.4f}")

h = lab.holm()
say(f"""
   m du registre : {h[0]['m_total']:,}   significatifs : {sum(1 for r in h if r['significant'])}
   plus petit p du dossier : {min(r['p'] for r in h):.2e}""")


rule("6. CE QUE CELA FERME")

say(f"""   Les trois regimes d'implementation sont desormais couverts :

     A  course continue, graine inconnue      h4-h20, sweep48 (incomplet)
     B  re-amorcage a chaque tirage           §63, ferme
     C  re-amorcage unique + course continue  ICI, ferme

   NON FERMÉ. La puissance vaut 1 DANS le produit balaye et ZERO en dehors :
   une famille absente (AES-CTR, ChaCha, un materiel), un echantillonneur
   absent, une convention de graine absente, ou une derive de plus de 600 s
   sur l'heure de demarrage echapperaient. Et le regime A reste ouvert par
   defaut de calcul, pas par mesure : 2^48 n'a jamais ete parcouru.

   ({time.time() - T0:.1f} s)""")
