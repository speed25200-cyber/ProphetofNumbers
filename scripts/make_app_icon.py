#!/usr/bin/env python3
"""1024×1024 Prophet icon — dark luxury sphere, cream numerals."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).resolve().parents[1] / "Prophet/Resources/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png"

W = 1024
bg = (8, 8, 12, 255)
fg = (243, 241, 234, 255)
accent = (197, 205, 216, 255)
live = (196, 92, 74, 255)

img = Image.new("RGBA", (W, W), bg)
draw = ImageDraw.Draw(img)

ring = Image.new("RGBA", (W, W), (0, 0, 0, 0))
rd = ImageDraw.Draw(ring)
rd.ellipse((168, 168, 856, 856), outline=accent, width=10)
rd.ellipse((208, 208, 816, 816), outline=(243, 241, 234, 40), width=2)
img = Image.alpha_composite(img, ring)

disc = Image.new("RGBA", (W, W), (0, 0, 0, 0))
dd = ImageDraw.Draw(disc)
dd.ellipse((250, 250, 774, 774), fill=(27, 27, 34, 255))
glow = Image.new("RGBA", (W, W), (0, 0, 0, 0))
gd = ImageDraw.Draw(glow)
gd.ellipse((300, 280, 720, 700), fill=(197, 205, 216, 38))
glow = glow.filter(ImageFilter.GaussianBlur(48))
img = Image.alpha_composite(img, glow)
img = Image.alpha_composite(img, disc)

d = ImageDraw.Draw(img)
d.ellipse((612, 312, 668, 368), fill=live)

try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", 280)
except OSError:
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf", 280)
    except OSError:
        font = ImageFont.load_default()

text = "20"
bbox = d.textbbox((0, 0), text, font=font)
tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
d.text(((W - tw) / 2 - bbox[0], (W - th) / 2 - bbox[1] - 8), text, font=font, fill=fg)

OUT.parent.mkdir(parents=True, exist_ok=True)
img.convert("RGB").save(OUT, "PNG", optimize=True)
print(f"wrote {OUT} {OUT.stat().st_size} bytes")
