#!/usr/bin/env python3
"""Icône Prophet 1024×1024 — l'œil de l'oracle.

Fond obsidienne aux halos aurora (violet / sarcelle), tableau officiel
8×10 en filigrane avec quelques numéros allumés, et au centre une
lentille dorée dont l'iris est un orbe or : l'œil qui lit les nombres.
Rendu en 2048 puis réduction Lanczos pour l'antialiasing.
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = Path(__file__).resolve().parents[1] / (
    "Prophet/Resources/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png"
)

S = 2048  # supersampling

# Palette (alignée sur Theme.swift)
BG = np.array([6, 6, 11], dtype=np.float32)
VIOLET = np.array([122, 104, 199], dtype=np.float32)
TEAL = np.array([67, 158, 153], dtype=np.float32)
GOLD = np.array([217, 179, 107], dtype=np.float32)
GOLD_SOFT = np.array([242, 221, 175], dtype=np.float32)
GOLD_DEEP = np.array([166, 128, 62], dtype=np.float32)

yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
u, v = xx / S, yy / S


def radial(cx, cy, radius, color, strength):
    d2 = (u - cx) ** 2 + (v - cy) ** 2
    w = strength * np.exp(-d2 / (radius**2))
    return w[..., None] * color[None, None, :]


# --- Fond : obsidienne + aurora -------------------------------------------
img = np.ones((S, S, 3), dtype=np.float32) * BG[None, None, :]
img += radial(0.14, 0.04, 0.42, VIOLET, 0.16)
img += radial(0.92, 0.16, 0.38, GOLD, 0.05)
img += radial(0.50, 1.02, 0.50, TEAL, 0.10)
# léger vignettage
d_c = np.sqrt((u - 0.5) ** 2 + (v - 0.5) ** 2)
img *= (1.0 - 0.35 * np.clip(d_c - 0.45, 0, 1))[..., None]

# --- Tableau 8×10 en filigrane --------------------------------------------
grid = Image.new("L", (S, S), 0)
gd = ImageDraw.Draw(grid)
margin = 0.115 * S
cols, rows = 8, 10
cw = (S - 2 * margin) / (cols - 1)
ch = (S - 2 * margin) / (rows - 1)
r_dot = 0.0055 * S
centers = {}
for c in range(cols):
    for r in range(rows):
        x = margin + c * cw
        y = margin + r * ch
        centers[(c, r)] = (x, y)
        gd.ellipse((x - r_dot, y - r_dot, x + r_dot, y + r_dot), fill=255)
grid_m = np.asarray(grid, dtype=np.float32) / 255.0
# le filigrane s'efface près de l'œil
fade = np.clip((d_c - 0.20) / 0.10, 0, 1)
img += (grid_m * fade * 0.085)[..., None] * GOLD_SOFT[None, None, :]

# --- Numéros « tirés » : cellules allumées --------------------------------
lit_cells = [(1, 1), (6, 1), (0, 4), (7, 5), (1, 8), (5, 9), (3, 0)]
lit = Image.new("L", (S, S), 0)
ld = ImageDraw.Draw(lit)
r_lit = 0.011 * S
for cell in lit_cells:
    x, y = centers[cell]
    ld.ellipse((x - r_lit, y - r_lit, x + r_lit, y + r_lit), fill=255)
lit_m = np.asarray(lit, dtype=np.float32) / 255.0
lit_glow = np.asarray(
    lit.filter(ImageFilter.GaussianBlur(0.02 * S)), dtype=np.float32
) / 255.0
img += (lit_glow * 0.55)[..., None] * GOLD[None, None, :]
img = img * (1 - lit_m[..., None]) + lit_m[..., None] * GOLD_SOFT[None, None, :] * 0.9

# --- La lentille de l'œil --------------------------------------------------
a = 0.335  # demi-largeur
b = 0.180  # demi-hauteur
R = (a * a / b + b) / 2
k = (a * a / b - b) / 2
d_top = np.sqrt((u - 0.5) ** 2 + (v - (0.5 - k)) ** 2)
d_bot = np.sqrt((u - 0.5) ** 2 + (v - (0.5 + k)) ** 2)
lens = ((d_top <= R) & (d_bot <= R)).astype(np.float32)
t = 0.0115  # épaisseur du trait
lens_in = ((d_top <= R - t) & (d_bot <= R - t)).astype(np.float32)
ring = np.clip(lens - lens_in, 0, 1)

ring_img = Image.fromarray((ring * 255).astype(np.uint8), "L")
ring_soft = np.asarray(
    ring_img.filter(ImageFilter.GaussianBlur(0.0018 * S)), dtype=np.float32
) / 255.0
ring_glow = np.asarray(
    ring_img.filter(ImageFilter.GaussianBlur(0.018 * S)), dtype=np.float32
) / 255.0

# dégradé or vertical sur le trait
tgrad = np.clip((v - (0.5 - b)) / (2 * b), 0, 1)[..., None]
gold_grad = GOLD_SOFT[None, None, :] * (1 - tgrad) + GOLD[None, None, :] * tgrad

img += (ring_glow * 0.45)[..., None] * GOLD[None, None, :]
img = img * (1 - ring_soft[..., None]) + ring_soft[..., None] * gold_grad

# l'intérieur de la lentille s'assombrit légèrement (profondeur)
inner = np.asarray(
    Image.fromarray((lens_in * 255).astype(np.uint8), "L").filter(
        ImageFilter.GaussianBlur(0.004 * S)
    ),
    dtype=np.float32,
) / 255.0
img *= (1 - inner * 0.22)[..., None]

# --- L'iris : orbe doré ----------------------------------------------------
r_orb = 0.150
d_orb = np.sqrt((u - 0.5) ** 2 + (v - 0.5) ** 2)
orb = np.clip((r_orb - d_orb) / 0.0015, 0, 1)
# éclairage sphérique : point chaud haut-gauche
d_hl = np.sqrt((u - 0.445) ** 2 + (v - 0.44) ** 2)
shade = np.clip(1.0 - d_hl / (2.1 * r_orb), 0, 1) ** 1.6
orb_col = GOLD_DEEP[None, None, :] + (GOLD_SOFT - GOLD_DEEP)[None, None, :] * shade[..., None]

orb_img = Image.fromarray((orb * 255).astype(np.uint8), "L")
orb_glow = np.asarray(
    orb_img.filter(ImageFilter.GaussianBlur(0.03 * S)), dtype=np.float32
) / 255.0
img += (orb_glow * 0.5)[..., None] * GOLD[None, None, :]
img = img * (1 - orb[..., None]) + orb[..., None] * orb_col

# --- La pupille : obsidienne, avec un éclat -------------------------------
r_pup = 0.052
pup = np.clip((r_pup - d_orb) / 0.0015, 0, 1)
img = img * (1 - pup[..., None]) + pup[..., None] * (BG[None, None, :] * 1.4)
d_glint = np.sqrt((u - 0.478) ** 2 + (v - 0.474) ** 2)
glint = np.clip((0.012 - d_glint) / 0.0015, 0, 1)
img = img * (1 - glint[..., None]) + glint[..., None] * GOLD_SOFT[None, None, :]

# --- Export ----------------------------------------------------------------
out = np.clip(img, 0, 255).astype(np.uint8)
icon = Image.fromarray(out, "RGB").resize((1024, 1024), Image.LANCZOS)
OUT.parent.mkdir(parents=True, exist_ok=True)
icon.save(OUT, "PNG")
print(f"OK → {OUT} ({OUT.stat().st_size / 1024:.0f} Ko)")
