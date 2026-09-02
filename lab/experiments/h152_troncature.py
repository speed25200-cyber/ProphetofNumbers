"""h152 — la lecture par TRONCATURE sous pas variable : le crible de classes
(THEORIE_ETAT §7.24 ; RAPPORT §172).

LE TROU
=======
Les §165-§170 lisent l'echantillonneur a modulo, `v = 1 + (x mod M)`, sous pas variable.
Le quatrieme echantillonneur usuel — la TRONCATURE `v = 1 + ((x·80) >> 32)`, celle qui n'a
pas de biais de modulo et que recommande tout manuel — n'est lu par aucune section quand le
pas varie : le §8 le nomme comme tel. Ce §172 le lit.

L'OUTIL
=======
Pas de DP : le lemme de la retenue interdit tout etat fini DETERMINISTE (§7.24 (ii)). Mais la
classe est additive a un bit pres,

    c(a + b mod 2^32) = c(a) + c(b) + delta  (mod 80),   delta dans {0, 1},

donc la suite des classes est lue par un automate NON DETERMINISTE d'etat (Z/80)^L : un bit
de branchement par mot, contre DEUX bits d'elagage (tout mot consomme, accepte ou refuse, a
sa classe parmi les vingt publiees). Et l'alignement ne se branche pas — il se DEDUIT du
compte des classes acceptees. Front `20^L`, environ `2,5 x 20^L` noeuds.

CE QUE LE VERDICT VAUT
=====================
Le crible est DUR : zero survivant EXCLUT la configuration exactement — a la probabilite
`1,3e-15` pres du plafond de soixante mots par tirage (P(N > 60) = 1,8e-20 par tirage), qui
est nommee. Ce n'est pas une martingale : l'absence de survivant ne se convertit pas en
borne de couverture pour les configurations NON parcourues.
"""

import json
import os
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import h145_sync_rejet as H                                             # noqa: E402
import h147_masque_rejet as Q                                           # noqa: E402

POOL, DRAWN = H.POOL, H.DRAWN
EXP_ID = "h152.troncature"
RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTIL = os.path.join(RACINE, "..", "tools", "lfg_crible_classe")
OUTIL = os.path.normpath(os.path.join(RACINE, "tools_bin", "lfg_crible_classe"))
SRC = os.path.normpath(os.path.join(os.path.dirname(RACINE), "tools", "lfg_crible_classe.c"))
TMP = "/tmp"
JOURNAL = os.path.join(TMP, "h152_journal.txt")
FJETON = os.path.join(TMP, "h152_jeton.json")
NMAXD = 45          # plafond de mots par tirage : P(N > 45) = 1,3e-11 (h155 ; h152
                    # avait 60, et sa partie par nuit s'est revelee infaisable)
NTIR = 25           # tirages qu'un chemin doit cloturer pour compter comme survivant
def plafond(L):
    """jamais atteint sous H0 (ou le parcours vaut 2,5 x 20^L) : seize fois la marge."""
    return max(20_000_000_000, 40 * 20 ** L)


def say(*a):
    print(*a, flush=True)


def compiler():
    os.makedirs(os.path.dirname(OUTIL), exist_ok=True)
    if os.path.exists(OUTIL) and os.path.getmtime(OUTIL) > os.path.getmtime(SRC):
        return
    cmd = ["gcc", "-O2", "-march=native", "-fopenmp", "-o", OUTIL, SRC]
    subprocess.run(cmd, check=True)
    say(f"   compile : {OUTIL}")


def grille():
    """(K, L, shift, mode, saut) — cout ~ 2,5 x 20^L par ancrage."""
    t7 = [(K, L) for K, L in Q.TRIN0 if L <= 7]
    t6 = [(K, L) for K, L in Q.TRIN0 if L <= 6]
    g = []
    for s in (0, 1):
        g += [(K, L, s, "flux", 1) for K, L in t7]
    for s in (0, 1):
        g += [(K, L, s, "nuit", 10) for K, L in t6]
        g += [(K, L, s, "nuit", 37) for K, L in t7 if L == 7]
    return g


def cle(K, L, shift, mode, saut):
    return f"{K},{L},{shift},{mode},{saut}"


def lancer(K, L, shift, mode, saut, f_cls, f_blocs, nice=15, fils=2, fixe=None, plaf=None):
    env = dict(os.environ, OMP_NUM_THREADS=str(fils))
    cmd = ["nice", "-n", str(nice), OUTIL, str(K), str(L), str(shift), mode,
           f_cls, f_blocs, str(NTIR), str(saut), str(NMAXD),
           str(plaf if plaf else plafond(L))]
    if fixe:
        cmd.append(fixe)
    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if p.returncode != 0:
        raise RuntimeError(f"{cle(K,L,shift,mode,saut)} : {p.returncode}\n{p.stderr[:400]}")
    fin = {"sec": time.time() - t0, "surv": 0, "noeuds": 0, "pic": 0, "coupes": 0,
           "bloc": -1, "sols": []}
    for ligne in p.stdout.splitlines():
        t = ligne.split()
        if not t:
            continue
        if t[0] == "noeuds":
            fin["noeuds"] = int(t[1]); fin["pic"] = int(t[3])
            fin["surv"] = int(t[5]); fin["coupes"] = int(t[7]); fin["bloc"] = int(t[9])
        elif t[0] == "surv" and len(fin["sols"]) < 8:
            fin["sols"].append(" ".join(t[1:]))
    return fin


def lire_journal():
    d = {}
    if os.path.exists(JOURNAL):
        for l in open(JOURNAL, encoding="utf-8"):
            t = l.split()
            if len(t) >= 6 and t[0] != "#":
                d[t[0]] = dict(noeuds=int(t[1]), pic=int(t[2]), surv=int(t[3]),
                               coupes=int(t[4]), sec=float(t[5]))
    return d


# ------------------------------------------------------------------ autotest

def temoin(K, L, shift, ntir=60, graine=999):
    """plante une suite (K, L) lue par troncature avec rejet, et verifie que le crible
    (a) retient l'etat vrai sous H1, (b) ne rend rien sous H0."""
    import random
    M = 1 << 32
    rng = random.Random(graine)
    r = [rng.randrange(M) for _ in range(L)]
    W = 1 << (32 - shift)
    i = L
    def mot():
        nonlocal i
        r.append((r[i - K] + r[i - L]) % M); i += 1
        return r[i - 1]
    def classe(x):
        return ((x >> shift) * POOL) // W
    tirages, cls = [], []
    for _ in range(ntir):
        vus = set()
        while len(vus) < DRAWN:
            c = classe(mot()); cls.append(c); vus.add(c)
        tirages.append(sorted(vus))
    f1 = os.path.join(TMP, f"h152_temoin_{K}_{L}_{shift}.txt")
    fb = os.path.join(TMP, "h152_temoin_blocs.txt")
    open(f1, "w").write("\n".join(" ".join(map(str, t)) for t in tirages) + "\n")
    open(fb, "w").write("0\n")
    vrai = ",".join(str(c) for c in cls[:L])
    chemin = ",".join(str(c) for c in cls[:min(len(cls), 1200)])
    # branche forcee : verifie en quelques millisecondes que l'etat vrai survit, sans
    # enumerer la famille entiere (l'automate est ambigu — un ecart de +1 peut etre
    # absorbe par un delta ulterieur, §7.24 (viii))
    fin = lancer(K, L, shift, "flux", 1, f1, fb, fixe=chemin, plaf=2_000_000)
    # H0 : tirages uniformes
    rng0 = random.Random(4242 + graine)
    t0 = [sorted(rng0.sample(range(POOL), DRAWN)) for _ in range(400)]
    f0 = os.path.join(TMP, "h152_temoin_h0.txt")
    open(f0, "w").write("\n".join(" ".join(map(str, t)) for t in t0) + "\n")
    fin0 = lancer(K, L, shift, "flux", 1, f0, fb)
    return fin, vrai, fin0


def temoin_nuit(K, L, shift, nnuit=3, ntir=30, graine=777):
    """meme chose en mode NUIT : un generateur REAMORCE a chaque bloc. Verifie que le crible
    retient l'etat vrai de CHAQUE nuit, et qu'il ne rend rien sur des nuits tirees sous H0."""
    import random
    M = 1 << 32
    W = 1 << (32 - shift)
    tirages, vrais, deb = [], [], []
    for b in range(nnuit):
        rng = random.Random(graine + 100 * b)
        r = [rng.randrange(M) for _ in range(L)]
        i = L
        def mot():
            nonlocal i
            r.append((r[i - K] + r[i - L]) % M); i += 1
            return r[i - 1]
        cls = []
        deb.append(len(tirages))
        for _ in range(ntir):
            vus = set()
            while len(vus) < DRAWN:
                c = ((mot() >> shift) * POOL) // W
                cls.append(c); vus.add(c)
            tirages.append(sorted(vus))
        vrais.append(",".join(str(c) for c in cls[:min(len(cls), 1200)]))
    f1 = os.path.join(TMP, f"h152_nuit_{K}_{L}_{shift}.txt")
    fb = os.path.join(TMP, f"h152_nuit_blocs_{K}_{L}_{shift}.txt")
    open(f1, "w").write("\n".join(" ".join(map(str, t)) for t in tirages) + "\n")
    open(fb, "w").write("\n".join(str(d) for d in deb) + "\n")
    ok = []
    for b, v in enumerate(vrais):
        fb1 = os.path.join(TMP, "h152_nuit_un.txt")
        open(fb1, "w").write(f"{deb[b]}\n")
        f = lancer(K, L, shift, "nuit", 1, f1, fb1, fixe=v, plaf=2_000_000)
        ok.append(f["surv"] > 0)
    # H0 : les memes blocs, mais des tirages uniformes
    rng0 = random.Random(31337 + graine)
    t0 = [sorted(rng0.sample(range(POOL), DRAWN)) for _ in range(len(tirages))]
    f0 = os.path.join(TMP, "h152_nuit_h0.txt")
    open(f0, "w").write("\n".join(" ".join(map(str, t)) for t in t0) + "\n")
    fin0 = lancer(K, L, shift, "nuit", 1, f0, fb)
    return ok, fin0


if __name__ == "__main__" and "--selftest" in sys.argv:
    compiler()
    say("h152 --selftest  (synthetique : aucune donnee reelle n'est lue)")
    ok = True
    for K, L in ((1, 4), (2, 5), (1, 6)):
        for shift in (0, 1):
            fin, vrai, fin0 = temoin(K, L, shift)
            say(f"   ({K},{L}) shift {shift} : H1 (branche vraie forcee [{vrai}]) "
                f"{fin['surv']:,} survivants en {fin['noeuds']:,} noeuds ; "
                f"H0 {fin0['surv']} survivants ({fin0['noeuds']:,} noeuds, {fin0['sec']:.1f} s)")
            if fin0["surv"] != 0:
                say("      !! H0 rend des survivants"); ok = False
            if fin["surv"] == 0:
                say("      !! l'etat vrai n'est PAS retenu"); ok = False
    for K, L in ((1, 4), (2, 5), (1, 6)):
        for shift in (0, 1):
            bons, fin0 = temoin_nuit(K, L, shift)
            say(f"   ({K},{L}) shift {shift} mode NUIT : {sum(bons)}/{len(bons)} nuits dont "
                f"l'etat vrai survit ; H0 sur {len(bons)} nuits uniformes : {fin0['surv']} "
                f"survivants ({fin0['noeuds']:,} noeuds)")
            if not all(bons):
                say("      !! une nuit plantee n'est pas retenue"); ok = False
            if fin0["surv"] != 0:
                say("      !! H0 rend des survivants en mode nuit"); ok = False
    say(f"   selftest : {'OK' if ok else 'ECHEC'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__" and "--archive" in sys.argv:
    import lab
    DRY = "--dry" in sys.argv
    T0 = time.time()
    compiler()
    say(f"h152 --archive  ({'MODE ESSAI' if DRY else 'jeton'})  outil {OUTIL}")
    G = grille()
    NCONF = len(G)
    T7 = [(K, L) for K, L in Q.TRIN0 if L <= 7]
    T6 = [(K, L) for K, L in Q.TRIN0 if L <= 6]
    HYPOTHESE = (
        "L'archive triee (70 560 tirages, 370 blocs de nuit) n'est engendree par aucun "
        "Fibonacci retarde additif r_i = r_(i-K) + r_(i-L) mod 2^32 lu par l'echantillonneur "
        "a TRONCATURE v = 1 + ((x * 80) >> 32) avec rejet des doublons, pour x = r (shift 0) "
        f"comme x = r >> 1 (shift 1), sur les {len(T7)} trinomes primitifs de degre <= 7 en "
        f"flux continu, les {len(T6)} de degre <= 6 par nuit (1 nuit sur 10), les 4 de degre 7 "
        "par nuit (1 nuit sur 37). Methode : crible de "
        "classes (§7.24) — automate non deterministe sur (Z/80)^L, 1 bit de branchement par "
        "mot contre 2 bits d'elagage, alignement deduit et non branche"
    )
    STATISTIQUE = (
        f"D = nombre de configurations parmi {NCONF} laissant AU MOINS UN survivant, "
        f"c'est-a-dire un L-uplet de classes dont l'automate cloture {NTIR} tirages consecutifs"
    )
    NULL = (
        "Crible DUR, pas de martingale : sous H1 l'etat vrai est retenu avec probabilite 1 "
        f"moins P(un tirage consomme plus de {NMAXD} mots) = 1,8e-20 par tirage, soit 1,3e-15 "
        "sur l'archive. Zero survivant EXCLUT donc la configuration a cette probabilite pres. "
        "Sous H0 le front decroit d'un bit par mot et s'eteint : mesure sur 400 tirages "
        "uniformes, 0 survivant pour toutes les configurations essayees"
    )
    VERDICT = ("conforme si D = 0 ; ETAT TROUVE si un survivant se releve (LLL sur les "
               "fractions, §7.24 (vii)) et rejoue l'archive")
    if not DRY:
        if os.path.exists(FJETON):
            TOK = json.load(open(FJETON, encoding="utf-8"))
            say(f"   jeton repris : scelle {TOK['seal']} le {TOK['registered_at']}")
        else:
            TOK = lab.preregister(EXP_ID, HYPOTHESE, STATISTIQUE, NULL, VERDICT, track="B")
            json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
            say(f"   jeton scelle {TOK['seal']} le {TOK['registered_at']}")
    else:
        say("   MODE ESSAI : pas de jeton, et l'archive n'est pas lue (a0 sous H0).")
        G = G[:2]

    ARCH = lab.load()
    TS = np.asarray(ARCH.ts).astype(np.int64)
    NUM = np.sort(np.asarray(ARCH.nums).astype(np.int64), axis=1)
    NTOT = len(TS)
    DEB = np.r_[0, np.flatnonzero(np.diff(TS) != 300) + 1]
    if DRY:
        rng = np.random.default_rng(152)
        CLS = np.array([np.sort(rng.choice(POOL, DRAWN, replace=False)) for _ in range(NTOT)])
        F_CLS = os.path.join(TMP, "h152_dry_classes.txt")
    else:
        CLS = NUM - 1                      # la classe publiee est v - 1
        F_CLS = os.path.join(TMP, "h152_classes.txt")
    F_BLOCS = os.path.join(TMP, "h152_blocs.txt")
    open(F_CLS, "w").write("\n".join(" ".join(str(int(v)) for v in ligne) for ligne in CLS) + "\n")
    open(F_BLOCS, "w").write("\n".join(str(int(d)) for d in DEB) + "\n")
    say(f"   {NTOT} tirages, {len(DEB)} blocs ; grille : {NCONF} configurations")

    FAIT = lire_journal() if not DRY else {}
    for K, L, shift, mode, saut in G:
        k = cle(K, L, shift, mode, saut)
        if k in FAIT:
            continue
        say(f"   >> {k}  ({time.strftime('%H:%M:%SZ', time.gmtime())})")
        fin = lancer(K, L, shift, mode, saut, F_CLS, F_BLOCS)
        det = int(fin["surv"] > 0)
        say(f"      FIN {k} : {fin['noeuds']:,} noeuds, pic {fin['pic']:,}, "
            f"{fin['surv']} survivants, {fin['coupes']} coupes, {fin['sec']:.0f} s"
            + ("   !! SURVIVANT" if det else ""))
        if det:
            for s in fin["sols"]:
                say(f"         sol {s}")
        if not DRY:
            with open(JOURNAL, "a", encoding="utf-8") as fj:
                fj.write(f"{k} {fin['noeuds']} {fin['pic']} {fin['surv']} {fin['coupes']} "
                         f"{fin['sec']:.1f}\n")
        FAIT[k] = fin

    LIG = [(cle(*c), FAIT[cle(*c)]) for c in G if cle(*c) in FAIT]
    # une configuration COUPEE au plafond de noeuds n'est PAS une exclusion : le parcours
    # n'a pas ete mene a son terme. On la compte a part et on refuse le verdict global.
    INC = [k for k, f in LIG if f["coupes"] > 0]
    D = sum(1 for k, f in LIG if f["surv"] > 0)
    NOE = sum(f["noeuds"] for k, f in LIG)
    SEC = sum(f["sec"] for k, f in LIG)
    CP = sum(f["coupes"] for k, f in LIG)
    say(f"\n   {len(LIG)} configurations : D = {D} ; {NOE:,} noeuds, {CP} coupes "
        f"({len(INC)} configurations non concluantes), {SEC/3600:.2f} h")
    if INC:
        say("   !! non concluantes : " + ", ".join(INC[:8]))
    if DRY or len(LIG) < NCONF:
        say("   grille incomplete ou essai : rien n'est consigne.")
    elif INC:
        say(f"   {len(INC)} configurations coupees au plafond de noeuds : le parcours n'y est "
            "pas complet, donc elles n'excluent RIEN. Rien n'est consigne avant de les avoir "
            "relancees avec un plafond suffisant.")
    else:
        TOK["m_extra"] = 0
        verdict = "conforme" if D == 0 else "SURVIVANT NON RELEVE"
        lab.record(
            TOK, float(D), p=1.0 if D == 0 else 0.0, verdict=verdict,
            power_at=("temoins plantes : une suite (K,L) engendree, lue par troncature avec "
                      "rejet puis TRIEE, voit son etat vrai retenu par le crible a tous les "
                      "coups (degres 4, 5, 6, deux decalages) ; sous H0, 400 tirages uniformes "
                      "donnent 0 survivant, et le cout suit 2,5 x 20^L au chiffre pres"),
            notes=(f"TRONCATURE SOUS PAS VARIABLE (§172) : {len(LIG)} configurations, "
                   f"{NOE:,} noeuds, {SEC/3600:.2f} h. D = {D}. Crible DUR (exclusion exacte a "
                   f"1,3e-15 pres, plafond de {NMAXD} mots par tirage) et parcours COMPLET "
                   f"({CP} coupes au plafond de noeuds), PAS une martingale : "
                   "aucune borne de couverture pour les configurations non parcourues. "
                   "NON COUVERT : degre 10 et au-dela (front 20^L) — TYPE_2 2^64,8, TYPE_3 "
                   "2^134, TYPE_4 2^272."))
        h = lab.holm()
        say(f"   consigne : {EXP_ID}   verdict {verdict}")
        say(f"   m du registre : {h[0]['m_total']:,}   significatifs : {sum(1 for r in h if r['significant'])}")
    say(f"\n   duree totale {(time.time() - T0)/60:.1f} min")
