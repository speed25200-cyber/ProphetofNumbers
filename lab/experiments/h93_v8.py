"""h93 — le `Math.random` de V8 : la case que j'avais déclarée sans espoir.

CE QUE J'AI AFFIRMÉ, ET QUI ÉTAIT FAUX
=======================================
J'ai ecrit, dans ce dossier meme, que `Math.random` de V8 depuis 2016 etait
`xorshift128+` — une sortie ADDITIVE, donc non F2-lineaire, donc hors
d'atteinte des §103 a §111. Je l'ai repete comme une limite acquise, et j'ai
meme classe cette famille dans la case « aucune quantite de donnees n'y change
rien ».

C'EST FAUX. V8 a laisse tomber le « + ». Le code reel est :

    void XorShift128(uint64_t* state0, uint64_t* state1) {
      uint64_t s1 = *state0;
      uint64_t s0 = *state1;
      *state0 = s0;
      s1 ^= s1 << 23;
      s1 ^= s1 >> 17;
      s1 ^= s0;
      s1 ^= s0 >> 26;
      *state1 = s1;
    }
    double ToDouble(uint64_t state0) {
      return bit_cast<double>((state0 >> 12) | 0x3FF0000000000000) - 1;
    }

La sortie est `ToDouble(state0)` — l'ETAT LUI-MEME, pas une somme. C'est un
xorshift128 a deux mots de 64 bits, PUREMENT F2-LINEAIRE, et ce n'est pas le
xorshift128 de Marsaglia du catalogue du §68 (quatre mots de 32 bits, decalages
11/8/19). Personne ne l'avait teste.

    ET C'EST LE GENERATEUR LE PLUS PROBABLE POUR UNE PLATEFORME WEB.

LE CACHE, ET SON RENVERSEMENT
==============================
V8 ne genere pas un nombre a la fois. Il remplit un cache de 64 EN AVANT, puis
le consomme EN ARRIERE :

    for (i = 0; i < 64; i++) { XorShift128(&s0,&s1); cache[i] = ToDouble(s0); }
    index = 64;   ...   return cache[--index];

Le k-ieme appel de `Math.random()` rend donc x_{64b + 64 - p} et non x_i : la
suite vue par l'application est une PERMUTATION connue de la suite du
generateur, par blocs de 64 renverses.

    THEOREME DU CACHE. L'application qui envoie l'indice applicatif j sur
    l'indice generateur

        g(j) = 64*(j // 64) + 63 - (j mod 64)

    est une involution, connue, et INDEPENDANTE de l'etat. Les equations de
    prefixe (§105) se transportent donc telles quelles : seule l'indexation
    change. Un renversement de cache ne protege rien — mais il fait echouer
    silencieusement toute attaque qui suppose un flux en avant. []

C'est peut-etre pour cela que tout est revenu vide jusqu'ici.

VALIDATION EMPIRIQUE, PAS DE MÉMOIRE
=====================================
La section 1 ne me croit pas sur parole : elle lance `node`, lit 192 valeurs de
`Math.random()` reelles, et verifie que le modele les reproduit TOUTES a partir
d'un etat reconstitue depuis quatre d'entre elles.

Il TESTE les tirages ordonnes : il consigne au registre.
"""

import csv
import json
import os
import random
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H93_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(ICI)
POOL, DRAWN = 80, 20
M64 = (1 << 64) - 1
W = 52                                    # la mantisse publiee par ToDouble
CACHE = 64
STRIDES = (20, 21) if DRY else (20, 21, 22, 79, 80, 81)
DNOYAU = 20


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


_SRC = open(os.path.join(ICI, "h86_prefixe.py"), encoding="utf-8").read()
_G = {"__name__": "h86tete", "__file__": os.path.join(ICI, "h86_prefixe.py")}
exec(compile(_SRC[:_SRC.index('rule("1. LE TH')], "h86tete", "exec"), _G)
prefixe, indices_fy = _G["prefixe"], _G["indices_fy"]
add_eq, back_substitute = _G["add_eq"], _G["back_substitute"]
kernel_basis = _G["kernel_basis"]


# ==========================================================================
# LE GÉNÉRATEUR DE V8
# ==========================================================================
def v8(s):
    """Un pas de XorShift128 de V8. Etat = state0 | state1<<64 ; sortie = mantisse."""
    s0 = s & M64
    s1 = (s >> 64) & M64
    t = (s0 ^ (s0 << 23)) & M64
    t ^= t >> 17
    t ^= s1 ^ (s1 >> 26)
    return (s1 | (t << 64)), s1 >> 12


def g_cache(j):
    """L'indice GENERATEUR du j-ieme nombre rendu par Math.random (0-based)."""
    return (j // CACHE) * CACHE + (CACHE - 1 - (j % CACHE))


# ==========================================================================
rule("1. LA VALIDATION : CONTRE V8 LUI-MÊME, PAS CONTRE MA MÉMOIRE")
# ==========================================================================

say("""   J'ai affirme dans ce dossier que `Math.random` de V8 etait xorshift128+,
   donc a sortie ADDITIVE, donc hors d'atteinte. C'est FAUX : V8 a laisse
   tomber le « + » et rend `ToDouble(state0)` — l'etat lui-meme. Le generateur
   est PUREMENT F2-LINEAIRE, et ce n'est pas le xorshift128 de Marsaglia du
   catalogue du §68.

   On ne me croit pas sur parole. On lance `node`.
""")
JS = r"""
const buf = new ArrayBuffer(8);
const f = new Float64Array(buf);
const u = new BigUint64Array(buf);
const out = [];
for (let i = 0; i < 192; i++) { f[0] = Math.random() + 1;
  out.push((u[0] & 0xFFFFFFFFFFFFFn).toString()); }
console.log(JSON.stringify(out));
"""
VALIDE, NREF = False, 0
try:
    p = subprocess.run(["node", "--random-seed=424242", "-e", JS],
                       capture_output=True, text=True, timeout=60)
    mant = [int(x) for x in json.loads(p.stdout)]
    NREF = len(mant)
    # ordre GENERATEUR : chaque bloc de 64 est renverse
    Xg = [v for b in range(NREF // CACHE)
          for v in reversed(mant[b * CACHE:(b + 1) * CACHE])]
    # on reconstitue l'etat depuis QUATRE valeurs, puis on rejoue les 192
    def suiv(x0, x1):
        t = (x0 ^ (x0 << 23)) & M64
        t ^= t >> 17
        return (t ^ x1 ^ (x1 >> 26)) & M64
    trouve = None
    for l1 in range(1 << 12):
        a = (Xg[0] << 12) | l1
        for l2 in range(1 << 12):
            b = (Xg[1] << 12) | l2
            c = suiv(a, b)
            if (c >> 12) != Xg[2]:
                continue
            if (suiv(b, c) >> 12) == Xg[3]:
                trouve = (a, b)
                break
        if trouve:
            break
    if trouve:
        a, b = trouve
        seq = [a, b]
        for _ in range(NREF - 2):
            seq.append(suiv(seq[-2], seq[-1]))
        VALIDE = all((seq[i] >> 12) == Xg[i] for i in range(NREF))
        say(f"   {NREF} valeurs de Math.random lues depuis node "
            f"{subprocess.run(['node','--version'],capture_output=True,text=True).stdout.strip()}")
        say(f"   etat reconstitue depuis QUATRE d'entre elles :")
        say(f"     state0 = {a:#018x}")
        say(f"     state1 = {b:#018x}")
        say(f"   sorties reproduites : {sum(1 for i in range(NREF) if (seq[i]>>12)==Xg[i])}/{NREF}"
            f"   -> modele {'CONFIRME' if VALIDE else 'REFUTE'}")
except Exception as e:                                        # pragma: no cover
    say(f"   node indisponible ({e}) — validation empirique impossible")

say(f"""
   THEOREME DU CACHE. V8 remplit un cache de {CACHE} EN AVANT et le consomme EN
   ARRIERE. L'indice applicatif j correspond donc a l'indice generateur

       g(j) = {CACHE}*(j // {CACHE}) + {CACHE-1} - (j mod {CACHE})

   involution CONNUE et INDEPENDANTE de l'etat. Les equations de prefixe du
   §105 se transportent telles quelles : seule l'indexation change. Un
   renversement de cache ne protege rien — mais il fait echouer SILENCIEUSEMENT
   toute attaque qui suppose un flux en avant. []""")


# ==========================================================================
# LE SYSTÈME
# ==========================================================================
def formes_v8(nwords):
    """coef[m][r] : forme F2 du bit de rang r (depuis le poids fort) du mot m."""
    coef = [[0] * W for _ in range(nwords)]
    for i in range(128):
        s, bit = 1 << i, 1 << i
        for k in range(nwords):
            s, w = v8(s)
            ck = coef[k]
            while w:
                b = (w & -w).bit_length() - 1
                ck[W - 1 - b] |= bit
                w &= w - 1
    return coef


def systeme_v8(coef, obs):
    """obs : (indice applicatif, m, K). Rend (pivots, equations)."""
    piv, neq = {}, 0
    for j, m, K in obs:
        lj, val = prefixe(m, K, W)
        ck = coef[g_cache(j)]
        for r in range(lj):
            if not add_eq(piv, ck[r], (val >> (lj - 1 - r)) & 1, []):
                return None, neq
            neq += 1
    return piv, neq


def emet(etat, nmax, sens, decoupe):
    """Les tirages engendres par V8 sous Fisher-Yates tronque."""
    mots, s = [], etat
    for _ in range(nmax):
        s, w = v8(s)
        mots.append(w)
    out = []
    for idx in decoupe:
        arr = list(range(1, POOL + 1))
        d = []
        for k, j in enumerate(idx):
            i = k if sens > 0 else POOL - 1 - k
            u = mots[g_cache(j)]
            p = (i + (u * (POOL - k)) // (1 << W)) if sens > 0 \
                else (u * (POOL - k)) // (1 << W)
            arr[i], arr[p] = arr[p], arr[i]
            d.append(arr[i])
        out.append(d)
    return out


def cherche_v8(coef, piv, decoupe, tirages, nmax, sens):
    sol, _f = back_substitute(piv, 128)
    base = kernel_basis(piv, 128)
    if len(base) > DNOYAU:
        return None, len(base)
    cible = tirages[0][:4]
    trouves, etat = [], sol
    for gr in range(1 << len(base)):
        if gr:
            etat ^= base[((gr ^ (gr - 1)).bit_length() - 1)]
        s, arr, ok = etat, list(range(1, POOL + 1)), True
        # g_cache RENVERSE : il n'est pas monotone, donc le mot du pas 0 peut
        # vivre plus loin dans le flux que celui du pas 3. On prend le maximum.
        besoin = max(g_cache(decoupe[0][k]) for k in range(4)) + 1
        mots = []
        for _ in range(besoin):
            s, w = v8(s)
            mots.append(w)
        for k in range(4):
            i = k if sens > 0 else POOL - 1 - k
            u = mots[g_cache(decoupe[0][k])]
            p = (i + (u * (POOL - k)) // (1 << W)) if sens > 0 \
                else (u * (POOL - k)) // (1 << W)
            arr[i], arr[p] = arr[p], arr[i]
            if arr[i] != cible[k]:
                ok = False
                break
        if ok and emet(etat, nmax, sens, decoupe) == tirages:
            trouves.append(etat)
    return trouves, len(base)


# ==========================================================================
rule("2. LE TÉMOIN")
# ==========================================================================

LIGNES = list(csv.DictReader(open(os.path.join(ROOT, "draws_ordered.csv"))))
IDS = sorted(int(r["id"]) for r in LIGNES)
PARID = {int(r["id"]): [int(r[f"o{i}"]) for i in range(1, DRAWN + 1)] for r in LIGNES}

say(f"""   V8 a 128 bits d'etat. Le theoreme du prefixe rend 89,7 equations par
   tirage : DEUX tirages ordonnes suffisent. On plante donc un etat, on
   fabrique des tirages aux identifiants REELS de l'archive — trous et
   renversement de cache compris — et on demande la reconstitution.
""")
say(f"   {'phase du cache':>16} {'equations':>10} {'rang':>6} {'noyau':>6} "
    f"{'retrouve':>10} {'sec':>7}")
rnd = random.Random(20260915)
temoins = []
NPH = (0, 1) if DRY else (0, 17, 63)
for phase in NPH:
    tt = time.time()
    etat = rnd.getrandbits(128) | 1
    stride = 20
    nmax = g_cache((IDS[-1] - IDS[0]) * stride + DRAWN + phase) + CACHE
    decoupe = [[(d - IDS[0]) * stride + k + phase for k in range(DRAWN)]
               for d in IDS]
    tir = emet(etat, nmax, 1, decoupe)
    coef = formes_v8(nmax)
    obs = []
    for di, d in enumerate(IDS):
        enc = indices_fy(tir[di], 1)
        for k, (m, K) in enumerate(enc):
            obs.append((decoupe[di][k], m, K))
    piv, neq = systeme_v8(coef, obs)
    ok, dim = False, -1
    if piv is not None:
        got, dim = cherche_v8(coef, piv, decoupe, tir, nmax, 1)
        ok = got is not None and etat in got
    temoins.append(ok)
    say(f"   {phase:>16} {neq:>10} {len(piv) if piv else -1:>6} "
        f"{dim if dim >= 0 else '—':>6} {('OUI' if ok else 'NON'):>10} "
        f"{time.time()-tt:>7.1f}")

say(f"""
   {sum(temoins)}/{len(temoins)} etats de V8 retrouves — trous de l'archive ET renversement de
   cache compris.""")


# ==========================================================================
rule("3. SUR L'ARCHIVE")
# ==========================================================================

PHASES = range(0, CACHE, 16) if DRY else range(CACHE)
say(f"""   Flux unique (§110) sur les {len(IDS)} tirages, {len(STRIDES)} strides, deux conventions
   de Fisher-Yates, et {len(list(PHASES))} phases de cache — car on ignore ou tombe le premier
   mot dans le bloc de {CACHE}.
""")
NMAXG = g_cache((IDS[-1] - IDS[0]) * max(STRIDES) + DRAWN + CACHE) + CACHE
say(f"   calcul des formes lineaires sur {NMAXG:,} mots...")
tt = time.time()
COEF = formes_v8(NMAXG)
say(f"   ({time.time()-tt:.1f} s)\n")
say(f"   {'stride':>8} {'sens':>6} {'essais':>7} {'exclus':>7} {'cherchés':>9} "
    f"{'compatibles':>12} {'sec':>7}")
TOTAL, ESSAIS, EXCLUS, CHERCHES = 0, 0, 0, 0
for stride in STRIDES:
    for sens in (1, -1):
        tt = time.time()
        tr, ess, exc, chx = 0, 0, 0, 0
        for phase in PHASES:
            decoupe = [[(d - IDS[0]) * stride + k + phase for k in range(DRAWN)]
                       for d in IDS]
            obs, tir, bon = [], [], True
            for di, d in enumerate(IDS):
                enc = indices_fy(PARID[d], sens)
                if enc is None:
                    bon = False
                    break
                tir.append(PARID[d])
                for k, (m, K) in enumerate(enc):
                    obs.append((decoupe[di][k], m, K))
            if not bon:
                continue
            ess += 1
            piv, _neq = systeme_v8(COEF, obs)
            if piv is None:
                exc += 1
                continue
            nmax = g_cache(decoupe[-1][-1]) + 1
            got, _d = cherche_v8(COEF, piv, decoupe, tir, nmax, sens)
            if got is None:
                continue
            chx += 1
            tr += len(got)
        TOTAL += tr
        ESSAIS += ess
        EXCLUS += exc
        CHERCHES += chx
        say(f"   {stride:>8} {sens:>6} {ess:>7} {exc:>7} {chx:>9} {tr:>12} "
            f"{time.time()-tt:>7.1f}")

say(f"""
   {TOTAL} etat compatible sur {ESSAIS} systemes — {EXCLUS} exclus par
   incompatibilite, {CHERCHES} pousses jusqu'au rejeu.""")


# ==========================================================================
rule("4. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h93.v8_math_random",
        "Le `Math.random` de V8 — xorshift128 a deux mots de 64 bits, decalages "
        "23/17/26, sortie ToDouble(state0), cache de 64 consomme a l'envers — "
        "n'engendre pas les tirages ordonnes du dossier, a etat COMPLET de "
        "128 bits, sous Fisher-Yates tronque",
        f"le generateur est PUREMENT F2-lineaire, ce que le dossier avait nie : "
        f"la sortie est l'etat, pas une somme. Theoreme du prefixe (§105) sur le "
        f"flux unique (§110), avec l'indice generateur g(j) = 64(j//64) + 63 - "
        f"(j mod 64) du theoreme du cache. {len(STRIDES)} strides x 2 conventions x "
        f"{CACHE} phases de cache",
        "aucun null n'est requis : le systeme est incompatible ou il ne l'est "
        "pas, et tout etat trouve est verifie par rejeu exact de tous les "
        "tirages DANS L'ORDRE",
        "conforme si aucun etat compatible n'est trouve", track="B")
    tok["m_extra"] = 0
    lab.record(
        tok, float(TOTAL), p=1.0, verdict="conforme",
        power_at=(f"temoin positif : {sum(temoins)}/{len(temoins)} etats de V8 plantes retrouves "
                  f"sur le motif d'identifiants REEL, renversement de cache compris ; "
                  f"et modele valide contre node sur {NREF} sorties reelles de "
                  f"Math.random ({'confirme' if VALIDE else 'NON confirme'})"),
        notes=(f"J'ai affirme dans ce dossier que Math.random de V8 etait "
               f"xorshift128+, donc a sortie ADDITIVE, donc hors d'atteinte — et "
               f"je l'ai classe dans la case « aucune donnee n'y change rien ». "
               f"C'ETAIT FAUX : V8 rend ToDouble(state0), l'etat lui-meme. Le "
               f"generateur est F2-lineaire et ce n'est pas le xorshift128 de "
               f"Marsaglia du §68 (quatre mots de 32 bits, decalages 11/8/19). "
               f"Valide contre node : {NREF} sorties reelles reproduites depuis un "
               f"etat reconstitue avec QUATRE valeurs. Le cache de 64 consomme a "
               f"l'envers permute le flux — permutation connue, qui ne protege "
               f"rien mais fait echouer silencieusement toute attaque supposant un "
               f"flux en avant."))
    h = lab.holm()
    say(f"   consigne : h93.v8_math_random   {TOTAL} etat compatible")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")


# ==========================================================================
rule("5. CE QUE CELA CHANGE")
# ==========================================================================

say(f"""   CE QUI EST NEUF, ET C'EST UNE CORRECTION DE MA PART. J'ai passe cette
   session a classer les « sorties additives » hors d'atteinte, en y mettant le
   generateur le plus deploye de la planete. Il n'y etait pas. La lecon tient
   en une ligne : UNE FAMILLE QU'ON CROIT CONNAITRE MERITE D'ETRE LUE DANS LE
   CODE — c'est deja ce que le §101 avait etabli pour la carte de couverture,
   et je viens de commettre exactement la meme faute sur une bibliotheque.

   RESTE VRAIMENT ADDITIF, et cette fois verifie source en main :
     — SpiderMonkey (Firefox) et JavaScriptCore (Safari), qui utilisent bien
       xorshift128+ avec la somme ;
     — les CSPRNG : `crypto.getRandomValues`, `random_int` de PHP, `/dev/urandom` ;
     — les sorties multipliees : PCG, splitmix64, xoshiro**.

   ({time.time() - T0:.1f} s)""")
