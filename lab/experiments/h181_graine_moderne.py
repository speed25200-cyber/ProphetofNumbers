"""h181 — LA GRAINE D'HORLOGE DES GÉNÉRATEURS MODERNES (RAPPORT §200).

LE TROU QUE LE §199 A OUVERT
============================
Le §199 a mesuré la frontière du dossier : les détecteurs de relation et les cribles d'état
attrapent les familles classiques et sont **aveugles** à toute conception moderne à un seul
pas — `splitmix64`, `PCG`, `xoshiro`. Ces familles-là restent entièrement debout, et c'est
tout ce qui reste debout.

Elles ont pourtant un point faible, et c'est exactement celui que l'utilisateur du dépôt
avait nommé : **la graine**. Un état de `64` ou `128` bits est hors de portée de tout
crible ; une graine tirée de l'horloge ne l'est pas du tout. Et l'archive donne
l'horodatage **exact** de chaque tirage, à la seconde.

Les §161 et suivants ont balayé les graines d'horloge — mais pour `glibc random()`, Java
`48` bits et V8. **Aucun n'a couvert les générateurs modernes.** Ce fichier comble ce trou.

CE QUI EST BALAYÉ
=================
  cinq générateurs   `splitmix64`, `xoshiro256++`, `xoshiro128**`, `pcg32`, `pcg64`
  deux échantillonneurs   troncature `(w·80) >> 32`, et modulo `w mod 80`
  trois modes de graine   la seconde `ts + δ` sur **tous** les tirages (`|δ| ≤ 3 600`),
                          la milliseconde `ts·1000 + δ` sur les débuts de nuit
                          (`|δ| ≤ 600 000`, soit dix minutes), et la **journée entière**
                          en secondes sur les débuts de nuit (`|δ| ≤ 86 400`)

UNE COÏNCIDENCE FAUSSE EST IMPOSSIBLE
=====================================
Un appariement fortuit sur les vingt numéros a une probabilité de `1/C(80,20) = 2,8·10⁻¹⁹`.
Même à `10¹²` essais, l'espérance de faux vaut `2,8·10⁻⁷`. **Tout appariement est réel**,
et le résultat est binaire : ou bien on trouve la graine et on prédit tout ce qui suit, ou
bien on ne trouve rien.

LE TÉMOIN EST OBLIGATOIRE
=========================
Un balayeur qui ne retrouve pas une graine **plantée** ne prouve rien. L'autotest fait deux
choses :

  1. il ancre `splitmix64` sur ses **vecteurs de test publiés** (graine `0` →
     `0xE220A8397B1DCDAF`, `0x6E789E6AA1B965F4`, `0x06C45D188009454F`) ;
  2. pour chacun des dix couples générateur × échantillonneur, il plante un tirage à une
     graine d'horloge connue et vérifie que l'outil la retrouve.
"""

import json
import os
import struct
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POOL, DRAWN = 80, 20
M64 = (1 << 64) - 1
M32 = (1 << 32) - 1
EXP_ID = "h181.graine_moderne"
FJETON = "/tmp/h181_jeton.json"
OUTIL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "tools_bin", "graine_moderne")
NOMGEN = ("splitmix64", "xoshiro256++", "xoshiro128**", "pcg32", "pcg64")
NOMECH = ("troncature", "modulo")
PCG64_MULT = (0x2360ED051FC65DA4 << 64) | 0x4385DF649FCCF645


def say(*a):
    print(*a, flush=True)


# --------------------------------------------------------------------------------------
# Miroir Python de l'outil C — il sert a PLANTER les temoins, donc a verifier le balayage
# --------------------------------------------------------------------------------------

def _sm64(s):
    s = (s + 0x9E3779B97F4A7C15) & M64
    z = s
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & M64
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & M64
    return s, z ^ (z >> 31)


def _rotl(x, k, w):
    m = (1 << w) - 1
    k &= (w - 1)
    return ((x << k) | (x >> ((w - k) & (w - 1)))) & m if k else x


class Gen:
    """reproduit exactement `amorce` et `suivant` de tools/graine_moderne.c."""

    def __init__(self, graine, g):
        self.g = g
        self.s64 = graine & M64
        t = graine & M64
        self.s4 = []
        for _ in range(4):
            t, z = _sm64(t)
            self.s4.append(z)
        t = graine & M64
        self.s128 = []
        for _ in range(4):
            t, z = _sm64(t)
            self.s128.append((z >> 32) & M32)
        self.pcg_i = ((graine << 1) | 1) & M64
        self.pcg_s = 0
        self.pcg_s = (self.pcg_s * 6364136223846793005 + self.pcg_i) & M64
        self.pcg_s = (self.pcg_s + graine) & M64
        self.pcg_s = (self.pcg_s * 6364136223846793005 + self.pcg_i) & M64
        M128 = (1 << 128) - 1
        self.p64_i = ((graine << 1) | 1) & M128
        self.p64_s = 0
        self.p64_s = (self.p64_s * PCG64_MULT + self.p64_i) & M128
        self.p64_s = (self.p64_s + graine) & M128
        self.p64_s = (self.p64_s * PCG64_MULT + self.p64_i) & M128

    def suivant(self):
        g = self.g
        if g == 0:
            self.s64, z = _sm64(self.s64)
            return (z >> 32) & M32
        if g == 1:
            s = self.s4
            r = (_rotl((s[0] + s[3]) & M64, 23, 64) + s[0]) & M64
            t = (s[1] << 17) & M64
            s[2] ^= s[0]; s[3] ^= s[1]; s[1] ^= s[2]; s[0] ^= s[3]
            s[2] ^= t;    s[3] = _rotl(s[3], 45, 64)
            return (r >> 32) & M32
        if g == 2:
            s = self.s128
            r = (_rotl((s[1] * 5) & M32, 7, 32) * 9) & M32
            t = (s[1] << 9) & M32
            s[2] ^= s[0]; s[3] ^= s[1]; s[1] ^= s[2]; s[0] ^= s[3]
            s[2] ^= t;    s[3] = _rotl(s[3], 11, 32)
            return r
        if g == 3:
            old = self.pcg_s
            self.pcg_s = (old * 6364136223846793005 + self.pcg_i) & M64
            xs = (((old >> 18) ^ old) >> 27) & M32
            return _rotl(xs, (64 - (old >> 59)) & 31, 32)
        M128 = (1 << 128) - 1
        old = self.p64_s
        self.p64_s = (old * PCG64_MULT + self.p64_i) & M128
        hi, lo = (old >> 64) & M64, old & M64
        r = _rotl(hi ^ lo, (64 - (hi >> 58)) & 63, 64)
        return (r >> 32) & M32


def tirage(graine, g, s, nmax=200):
    gen = Gen(graine, g)
    vus = set()
    for _ in range(nmax):
        w = gen.suivant()
        c = ((w * POOL) >> 32) if s == 0 else (w % POOL)
        vus.add(c)
        if len(vus) == DRAWN:
            m0 = m1 = 0
            for c in vus:
                if c < 64:
                    m0 |= 1 << c
                else:
                    m1 |= 1 << (c - 64)
            return m0, m1
    return None


def ecrire_cibles(chemin, lignes):
    with open(chemin, "wb") as f:
        for ts, m0, m1 in lignes:
            f.write(struct.pack("<qQQ", int(ts), int(m0), int(m1)))


def lancer(chemin, mode, fen, pas=1, saut=0):
    r = subprocess.run([OUTIL, chemin, str(mode), str(fen), str(pas), str(saut)],
                       capture_output=True, text=True, timeout=100000)
    if r.returncode != 0:
        raise RuntimeError(f"outil en echec ({r.returncode}) : {r.stderr[:400]}")
    return r.stdout


def selftest():
    say("h181 --autotest : donnees synthetiques uniquement, aucune archive lue")

    # (1) vecteurs de test PUBLIES de splitmix64, graine 0
    attendus = [0xE220A8397B1DCDAF, 0x6E789E6AA1B965F4, 0x06C45D188009454F]
    s, obtenus = 0, []
    for _ in range(3):
        s, z = _sm64(s)
        obtenus.append(z)
    ok1 = obtenus == attendus
    say(f"   splitmix64, vecteurs publies (graine 0) : "
        f"{'CONFORMES' if ok1 else 'FAUX'}")
    for a, b in zip(attendus, obtenus):
        say(f"      attendu {a:#018x}   obtenu {b:#018x}")

    # (2) dix temoins plantes : un par couple generateur x echantillonneur
    say(f"\n   {'generateur':>14} | {'echantillonneur':>15} | graine plantee | retrouvee")
    ok2 = True
    base = 1757829900
    for g in range(5):
        for s_ in range(2):
            graine = base + 137 * g + 11 * s_
            t = tirage(graine, g, s_)
            if t is None:
                say(f"   {NOMGEN[g]:>14} | {NOMECH[s_]:>15} | ENGENDREMENT IMPOSSIBLE")
                ok2 = False
                continue
            ecrire_cibles("/tmp/h181_temoin.bin", [(graine - 7, t[0], t[1])])
            sortie = lancer("/tmp/h181_temoin.bin", 0, 50)
            vu = any(f"generateur {NOMGEN[g]} echantillonneur {NOMECH[s_]}" in L
                     and f"graine {graine} " in L
                     for L in sortie.splitlines())
            say(f"   {NOMGEN[g]:>14} | {NOMECH[s_]:>15} | {graine} | "
                f"{'OUI' if vu else 'NON'}")
            ok2 &= vu
    say(f"\n   -> vecteurs {'OK' if ok1 else 'FAUX'} ; "
        f"balayage {'CALIBRE 10/10' if ok2 else 'DEFAILLANT'}")
    return ok1 and ok2


if __name__ == "__main__":
    if "--autotest" in sys.argv:
        sys.exit(0 if selftest() else 1)

    import lab

    A = lab.load()
    N = len(A.ids)
    TS = np.asarray(A.ts).astype(np.int64)
    NUMS = np.asarray(A.nums).astype(np.int64)
    M0 = np.zeros(N, np.uint64)
    M1 = np.zeros(N, np.uint64)
    for j in range(DRAWN):
        c = NUMS[:, j] - 1
        bas = c < 64
        M0[bas] |= (np.uint64(1) << c[bas].astype(np.uint64))
        M1[~bas] |= (np.uint64(1) << (c[~bas] - 64).astype(np.uint64))

    FEN_S = int(os.environ.get("H181_FEN_S", 3600))
    FEN_MS = int(os.environ.get("H181_FEN_MS", 600000))
    FEN_J = int(os.environ.get("H181_FEN_J", 86400))
    DEB = np.r_[0, np.flatnonzero(np.diff(TS) > 1000) + 1]

    HYP = ("Aucun generateur moderne a un seul pas — splitmix64, xoshiro256++, "
           "xoshiro128**, pcg32, pcg64 — amorce sur l'horloge du tirage n'engendre le "
           "tirage observe, ni sous troncature ni sous modulo, ni a la seconde ni a la "
           "milliseconde. C'est le SEUL point faible qui reste a la famille que le §199 a "
           "montree hors de portee des detecteurs de relation comme des cribles d'etat : "
           "son etat de 64 a 128 bits est inatteignable, mais une graine tiree de l'heure "
           "ne l'est pas, et l'archive donne l'horodatage exact de chaque tirage. Les §161 "
           "et suivants ont balaye glibc, Java 48 bits et V8 ; aucun n'a couvert les "
           "generateurs modernes")
    STAT = (f"nombre d'appariements exacts sur les vingt numeros. Mode SECONDE : les "
            f"{N} tirages, graines ts+delta pour |delta| <= {FEN_S}. Mode MILLISECONDE : "
            f"les {len(DEB)} premiers tirages de nuit, graines ts*1000+delta pour "
            f"|delta| <= {FEN_MS}. Mode JOURNEE : les memes debuts de nuit, graines "
            f"ts+delta pour |delta| <= {FEN_J}, soit la journee entiere. Cinq generateurs "
            "x deux echantillonneurs")
    NUL = ("Aucune simulation n'est necessaire : un appariement fortuit sur les vingt "
           "numeros a une probabilite de 1/C(80,20) = 2,8e-19 par essai. Meme a 10^12 "
           "essais l'esperance de faux vaut 2,8e-7. Le resultat est BINAIRE : tout "
           "appariement est reel")
    VER = ("conforme si zero appariement ; GRAINE TROUVEE sinon, auquel cas l'etat est "
           "connu et tout ce qui suit le tirage apparie est predit")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    total = 0
    trouves = []

    say(f"\nMODE SECONDE : {N} tirages, fenetre +-{FEN_S} s")
    ecrire_cibles("/tmp/h181_sec.bin", zip(TS, M0, M1))
    out = lancer("/tmp/h181_sec.bin", 0, FEN_S)
    for L in out.splitlines():
        if L.startswith("APPARIEMENT"):
            trouves.append(L)
            say("   " + L)
        elif L.startswith("cibles") or L.startswith("graines") or L.startswith("TERMINE"):
            say("   " + L)
    total += N * (2 * FEN_S + 1) * 10

    say(f"\nMODE MILLISECONDE : {len(DEB)} premiers tirages de nuit, "
        f"fenetre +-{FEN_MS} ms")
    ecrire_cibles("/tmp/h181_ms.bin", [(TS[i], M0[i], M1[i]) for i in DEB])
    out = lancer("/tmp/h181_ms.bin", 1, FEN_MS)
    for L in out.splitlines():
        if L.startswith("APPARIEMENT"):
            trouves.append(L)
            say("   " + L)
        elif L.startswith("cibles") or L.startswith("graines") or L.startswith("TERMINE"):
            say("   " + L)
    total += len(DEB) * (2 * FEN_MS + 1) * 10

    say(f"\nMODE JOURNEE : {len(DEB)} premiers tirages de nuit, fenetre +-{FEN_J} s "
        f"(la journee entiere)")
    out = lancer("/tmp/h181_ms.bin", 0, FEN_J)
    for L in out.splitlines():
        if L.startswith("APPARIEMENT"):
            trouves.append(L)
            say("   " + L)
        elif L.startswith("cibles") or L.startswith("graines") or L.startswith("TERMINE"):
            say("   " + L)
    total += len(DEB) * (2 * FEN_J + 1) * 10

    say(f"\n   essais totaux {total:.3e} ; faux attendus {total*2.8e-19:.3e}")
    say(f"   appariements : {len(trouves)}")
    TOK["m_extra"] = 0
    lab.record(
        TOK, float(len(trouves)),
        p=1.0 if not trouves else 0.0,
        verdict="GRAINE TROUVEE" if trouves else "conforme",
        power_at=(f"le balayage est EXACT et non statistique : il retrouve une graine "
                  f"plantee dans dix cas sur dix (autotest, un par couple generateur x "
                  f"echantillonneur), et splitmix64 est ancre sur ses vecteurs de test "
                  f"publies. Sur {total:.2e} essais l'esperance de faux vaut "
                  f"{total*2.8e-19:.1e} : un appariement, s'il existait, serait certain"),
        notes=(f"GRAINE D'HORLOGE DES GENERATEURS MODERNES (§200) — le trou ouvert par le "
               f"§199. Cinq generateurs a un seul pas x deux echantillonneurs x deux modes "
               f"de graine. Mode seconde : {N} tirages, fenetre +-{FEN_S} s. Mode "
               f"milliseconde : {len(DEB)} debuts de nuit, fenetre +-{FEN_MS} ms. "
               f"Mode journee : les memes, fenetre +-{FEN_J} s. "
               f"{total:.3e} essais, {len(trouves)} appariement(s). Le resultat est binaire : "
               "une coincidence fausse a une probabilite de 2,8e-19 par essai."))
    say("   consigne.")
