#!/usr/bin/env python3
"""Generates docs/banner.png for the README (original artwork, no third-party logos)."""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "docs", "banner.png")
FB = os.environ.get("BANNER_FONT_BOLD", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
FR = os.environ.get("BANNER_FONT", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
W, H, SS = 1280, 320, 2
img = Image.new("RGB", (W * SS, H * SS))
d = ImageDraw.Draw(img)
c1, c2, c3 = (0, 164, 220), (170, 92, 195), (16, 16, 22)
for x in range(W * SS):
	t = x / float(W * SS - 1)
	col = tuple(int(c1[i] * (1 - t) + c2[i] * t) for i in range(3))
	d.line([(x, 0), (x, H * SS)], fill=col)
shade = Image.new("L", (W * SS, H * SS))
sd = ImageDraw.Draw(shade)
for y in range(H * SS):
	sd.line([(0, y), (W * SS, y)], fill=int(140 * y / (H * SS)))
img = Image.composite(Image.new("RGB", img.size, c3), img, shade)
d = ImageDraw.Draw(img)
cx, cy, r = 190 * SS, 160 * SS, 92 * SS
d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 255, 255), width=8 * SS)
d.polygon([(cx - 30 * SS, cy - 48 * SS), (cx - 30 * SS, cy + 48 * SS), (cx + 52 * SS, cy)], fill=(255, 255, 255))
d.text((330 * SS, 120 * SS), "Jellyfin für Enigma2", font=ImageFont.truetype(FB, 64 * SS), fill=(255, 255, 255), anchor="lm")
d.text((334 * SS, 196 * SS), "Filme, Serien & Musik vom eigenen Server  ·  OpenPLi 9", font=ImageFont.truetype(FR, 30 * SS), fill=(235, 235, 245), anchor="lm")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
img.resize((W, H), Image.LANCZOS).save(OUT, optimize=True)
print(OUT)
