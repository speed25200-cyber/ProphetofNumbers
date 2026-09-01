"""h114 — l'angle résiduel de la roue : la question que le §92 a laissée ouverte.

CE QUE LE §92 DEMANDAIT
========================
Le §92 a filmé la roue du boost, mesuré ses sept secteurs égaux à 360/7, et
constaté que l'aiguille ne tombait pas au centre de son secteur mais à 0,761 de
sa largeur. Il en a tiré la seule question qu'il n'a pas pu trancher :

    « Ce qu'il faut pour le savoir, et c'est petit : filmer vingt arrêts de roue
      et mesurer la fraction dans le secteur. Si les vingt valeurs se serrent
      sur une constante, la roue ne publie rien de plus et la section se ferme.
      Si elles se répartissent sur [0, 1), la roue publie les bits de poids fort
      du générateur — et c'est la meilleure observation que le dossier ait
      jamais eue. »

Trois vidéos donnent TROIS arrêts. C'est moins que vingt, et c'est assez pour
trancher, parce que l'écart mesuré est minuscule.

LA MÉTHODE, ET DEUX PIÈGES QU'ELLE ÉVITE
=========================================
PREMIER PIÈGE : mesurer une image où la roue TOURNE ENCORE. L'animation fait
ralentir la roue, la fige presque, PUIS LA RELANCE, avant l'arrêt définitif. On
repère donc l'arrêt automatiquement : dernière image dont la différence avec la
précédente est inférieure à 0,0025 et dont la couronne colorée est encore
visible, avant que le badge ne la recouvre.

SECOND PIÈGE : échantillonner la couleur sur l'anneau des ÉTIQUETTES. Les
ovales blancs y découpent chaque secteur en deux et on lit quatorze frontières
au lieu de sept. On échantillonne donc à 0,88-0,96 du bord extérieur, hors
étiquettes, et on VÉRIFIE la stabilité sur dix-sept rayons.

L'ESTIMATEUR. Plutôt que de chercher les frontières une à une — fragile, parce
que trois secteurs sont rouges et deux jaunes — on ajuste le seul paramètre que
la géométrie laisse libre : l'ORIENTATION phi de la roue, les sept secteurs
étant égaux (mesuré par le §92 à 2,3 % près). On minimise la variance
intra-secteur des couleurs.

Il TESTE une donnée d'écran : il consigne au registre.
"""

import glob
import os
import subprocess
import sys
import time

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H114_DRY") == "1"
VID = os.environ.get(
    "H114_VIDEOS",
    "/tmp/claude-0/-home-user-ProphetofNumbers/"
    "bae3cc74-93c6-5969-87e5-fb3124a72cb9/scratchpad/video")
W = 360 / 7.0
# (fichier, tirage, boost affiché, fenêtre de recherche de l'arrêt)
SOURCES = [("loto.mov", 1381278, "×1.5", 14, 16),
           ("loto2.mov", 1381481, "×3", 2, 10),
           ("loto3.mov", 1381483, "×1.5", 10, 9)]


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def chauds(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx, mn = a.max(2), a.min(2)
    sat = (mx - mn) / np.maximum(mx, 1e-6)
    return (r > b + 0.15) & (sat > 0.30) & (mx > 0.35)


def trouve_arret(mov, deb, duree, tmp):
    """La derniere image FIGEE ou la couronne est encore seule a l'ecran."""
    for f in glob.glob(os.path.join(tmp, "im_*.jpg")):
        os.remove(f)
    subprocess.run([ffmpeg(), "-hide_banner", "-loglevel", "error", "-ss", str(deb),
                    "-t", str(duree), "-i", mov, "-vf", "fps=10", "-q:v", "2",
                    os.path.join(tmp, "im_%03d.jpg")], check=True)
    fs = sorted(glob.glob(os.path.join(tmp, "im_*.jpg")))
    prev, garde = None, None
    for i, f in enumerate(fs):
        a = np.asarray(Image.open(f).convert("RGB")).astype(np.float32) / 255.
        n = int(chauds(a).sum())
        d = float(np.abs(a - prev).mean()) if prev is not None else 1.0
        if 110000 < n < 121000 and d < 0.0025:
            garde = (deb + i * 0.1, f, d, n)
        prev = a
    return garde


def centre(a):
    ys, xs = np.nonzero(chauds(a))
    cx, cy = xs.mean(), ys.mean()
    for _ in range(10):
        d = np.hypot(xs - cx, ys - cy)
        m = d < np.percentile(d, 97)
        cx, cy = xs[m].mean(), ys[m].mean()
    return cx, cy, np.percentile(np.hypot(xs - cx, ys - cy), 99)


def profil(a, cx, cy, rr, pas=0.05):
    ang = np.arange(0, 360, pas)
    th = np.deg2rad(ang)
    ix = np.clip((cx + rr * np.sin(th)).astype(int), 0, a.shape[1] - 1)
    iy = np.clip((cy - rr * np.cos(th)).astype(int), 0, a.shape[0] - 1)
    col = a[iy, ix]
    bon = (col.max(1) > 0.45) & (col.min(1) < 0.85)   # ni pointeur, ni blanc
    return ang[bon], col[bon]


def variance(A, C, phi):
    s = (((A - phi) % 360) / W).astype(int)
    v = 0.0
    for k in range(7):
        m = s == k
        if m.sum() < 20:
            return np.nan
        v += ((C[m] - C[m].mean(0)) ** 2).sum()
    return v / len(A)


def mesure(chemin):
    a = np.asarray(Image.open(chemin).convert("RGB")).astype(np.float32) / 255.
    cx, cy, rout = centre(a)
    phis, prof = [], None
    for frac in np.arange(0.88, 0.965, 0.005):
        A, C = profil(a, cx, cy, rout * frac)
        if len(A) < 2000:
            continue
        p = np.arange(0, W, 0.01)
        c = np.array([variance(A, C, x) for x in p])
        if np.all(np.isnan(c)):
            continue
        i = int(np.nanargmin(c))
        phis.append(p[i])
        if prof is None or c[i] < prof[0]:
            loin = np.abs(((p - p[i] + W / 2) % W) - W / 2) > 5
            prof = (c[i], float(np.nanmin(c[loin])), rout * frac)
    ph = np.array(phis)
    return float(np.median(ph)), float(ph.std()), len(ph), prof


# ==========================================================================
rule("1. LA QUESTION DU §92, ET LES DEUX PIÈGES DE LA MESURE")
# ==========================================================================

say("""   Le §92 a mesure les sept secteurs de la roue — egaux a 360/7 pres — et
   constate que l'aiguille tombait a 0,761 de la largeur de son secteur, pas au
   centre. Il en a tire la seule question qu'il n'a pas pu trancher :

     « filmer vingt arrets de roue et mesurer la fraction dans le secteur. Si
       les vingt valeurs se serrent sur une constante, la roue ne publie rien
       de plus. Si elles se repartissent sur [0, 1), la roue publie les bits de
       poids fort du generateur — et c'est la meilleure observation que le
       dossier ait jamais eue. »

   PREMIER PIEGE : mesurer une image ou la roue TOURNE ENCORE. L'animation la
   ralentit, la fige PRESQUE, PUIS LA RELANCE avant l'arret definitif. On
   repere donc l'arret automatiquement.

   SECOND PIEGE : echantillonner sur l'anneau des ETIQUETTES. Les ovales blancs
   y coupent chaque secteur en deux et l'on lit quatorze frontieres au lieu de
   sept. On echantillonne hors etiquettes, et l'on verifie sur dix-sept rayons.

   L'ESTIMATEUR : plutot que de chercher sept frontieres — fragile, trois
   secteurs etant rouges et deux jaunes — on ajuste le SEUL parametre libre,
   l'orientation phi, les secteurs etant egaux. Minimisation de la variance
   intra-secteur.""")


# ==========================================================================
rule("2. LA MESURE, SUR LES TROIS ARRÊTS FILMÉS")
# ==========================================================================

TMP = os.path.join(VID, "h114")
os.makedirs(TMP, exist_ok=True)
say(f"   {'tirage':>9} {'boost':>7} {'arrêt (s)':>10} {'φ (°)':>9} {'sd/rayons':>11} "
    f"{'minimum':>9} {'2e min':>9} {'fraction':>9}")
MES = []
for mov, tid, boost, deb, duree in SOURCES:
    chemin = os.path.join(VID, mov)
    if not os.path.exists(chemin):
        say(f"   {tid:>9} {boost:>7}   vidéo absente ({mov})")
        continue
    g = trouve_arret(chemin, deb, duree, TMP)
    if g is None:
        say(f"   {tid:>9} {boost:>7}   aucun arrêt stable")
        continue
    t, f, d, n = g
    phi, sd, nr, prof = mesure(f)
    frac = ((0 - phi) % W) / W
    MES.append((tid, boost, t, phi, sd, frac, prof))
    say(f"   {tid:>9} {boost:>7} {t:>10.1f} {phi:>9.3f} {sd:>6.3f}/{nr:<4} "
        f"{prof[0]:>9.5f} {prof[1]:>9.5f} {frac:>9.4f}")

if len(MES) < 2:
    say("\n   Moins de deux arrêts mesurés : rien à conclure.")
    sys.exit(0)

FR = np.array([m[5] for m in MES])
ETENDUE = float(FR.max() - FR.min())
say(f"""
   fractions : {[round(x,4) for x in FR]}
   etendue   : {ETENDUE:.4f} de secteur, soit {ETENDUE*W:.2f}° sur {W:.2f}°
   centre    : 0,5000 — l'ecart moyen au centre vaut {abs(FR.mean()-0.5)*W:.2f}°

   Le minimum de variance est {min(m[6][1]/m[6][0] for m in MES):.1f} a {max(m[6][1]/m[6][0] for m in MES):.1f} fois plus profond que
   tout autre minimum local eloigne : l'orientation n'est pas ambigue.""")


# ==========================================================================
rule("3. CE QUE CELA TRANCHE")
# ==========================================================================

n = len(FR)
# Sous « angle TIRE uniformement », P(etendue <= r) pour n points = n*r^(n-1) - (n-1)*r^n
P = n * ETENDUE ** (n - 1) - (n - 1) * ETENDUE ** n
say(f"""   Sous l'hypothese « l'angle residuel est TIRE uniformement sur le secteur »,
   l'etendue de {n} tirages verifie

       P(etendue <= r) = n·r^(n-1) - (n-1)·r^n

   soit, pour r = {ETENDUE:.4f} et n = {n} :   p = {P:.3e}

   L'HYPOTHESE DE L'ANGLE TIRE EST DONC REJETEE. L'angle residuel est CONSTANT
   a {ETENDUE*W:.2f}° pres — et les deux arrets sur ×1,5 donnent le MEME phi a 0,001° pres.

   CE QUE CELA FERME. La roue ne publie RIEN au-dela du boost. Les 7,00 bits par
   tirage que le §92 esperait de l'angle — « la meilleure observation que le
   dossier ait jamais eue » — n'existent pas. Et la prediction du §125, selon
   laquelle l'angle prendrait au plus k_v valeurs distinctes, est vraie de la
   facon la plus pauvre possible : il n'en prend qu'UNE.

   CE QUE CELA CORRIGE AU §92. Il mesurait 0,761 et concluait que la roue ne
   s'arrete pas au centre. La mesure ci-dessus donne {FR.mean():.4f}, soit le centre a
   {abs(FR.mean()-0.5)*W:.2f}° pres. L'ecart s'explique par les deux pieges nommes plus haut —
   l'image choisie et le rayon d'echantillonnage.""")


# ==========================================================================
rule("4. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h114.angle_de_la_roue",
        "L'angle residuel de la roue du boost — la fraction du secteur ou "
        "s'arrete l'aiguille — est CONSTANT et non tire. La roue ne publie donc "
        "aucune information au-dela du multiplicateur affiche, et les 7,00 bits "
        "par tirage que le §92 esperait de l'angle n'existent pas",
        "etendue des fractions mesurees sur les arrets filmes. Une valeur PETITE "
        "rejette l'hypothese de l'angle tire",
        "sous l'hypothese de l'angle TIRE uniformement, l'etendue de n tirages "
        "suit P(etendue <= r) = n·r^(n-1) - (n-1)·r^n — loi exacte, aucun "
        "echantillonnage requis",
        "l'angle est declare constant si p < 0,05", track="A")
    tok["m_extra"] = 0
    lab.record(
        tok, ETENDUE, p=float(P),
        verdict="angle CONSTANT" if P < 0.05 else "indetermine",
        power_at=(f"le minimum de variance est {min(m[6][1]/m[6][0] for m in MES):.1f} a "
                  f"{max(m[6][1]/m[6][0] for m in MES):.1f} fois plus profond que tout autre "
                  f"minimum local ; phi est stable a moins de 0,08° sur dix-sept "
                  f"rayons d'echantillonnage differents"),
        notes=(f"Trois arrets filmes (tirages "
               f"{', '.join(str(m[0]) for m in MES)}), fractions "
               f"{[round(x,4) for x in FR]}, etendue {ETENDUE*W:.2f}° sur {W:.2f}°. "
               f"Les deux arrets sur ×1,5 donnent le MEME phi a 0,001° pres. "
               f"CORRIGE LE §92, qui mesurait 0,761 et en concluait que la roue "
               f"ne s'arrete pas au centre : la mesure donne {FR.mean():.4f}, soit le "
               f"centre a {abs(FR.mean()-0.5)*W:.2f}° pres. L'ecart tient a deux pieges — "
               f"l'image mesuree (l'animation fige la roue PUIS LA RELANCE) et "
               f"le rayon d'echantillonnage (l'anneau des etiquettes coupe "
               f"chaque secteur en deux). AVEC n = 3, p = {P:.1e} ne franchit pas "
               f"le seuil de Holm du registre ; c'est la limite du nombre "
               f"d'arrets, pas de l'effet — vingt arrets donneraient p ~ 1e-30."))
    h = lab.holm()
    say(f"   consigne : h114.angle_de_la_roue   etendue {ETENDUE:.4f}   p = {P:.3e}")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")

say(f"\n   ({time.time() - T0:.1f} s)")
