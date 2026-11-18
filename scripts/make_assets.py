#!/usr/bin/env python3
"""Generates the PNG skin assets in src/JellyfinE2/images (original artwork).

Enigma2 fills (eLabel backgroundColor) overwrite pixels instead of blending, so every
translucent layer (gradients, glass panels, rounded frames, badges) is an alpha PNG
that the box blends with alphatest="blend".
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "src", "JellyfinE2", "images")
FB = os.environ.get("ASSET_FONT_BOLD", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
BG = (11, 11, 16)
ACCENT = (0, 164, 220)
PURPLE = (170, 92, 195)
GREEN = (67, 160, 71)
SS = 4
os.makedirs(OUT, exist_ok=True)


def save(img, name):
	img.save(os.path.join(OUT, name), optimize=True)


def gradient_overlay(w, h, fn):
	img = Image.new("RGBA", (w, h))
	px = img.load()
	for y in range(h):
		for x in range(w):
			px[x, y] = BG + (int(max(0.0, min(1.0, fn(x / float(w), y / float(h)))) * 255),)
	return img


def rounded(w, h, r, fill, outline=None, width=0):
	big = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
	d = ImageDraw.Draw(big)
	d.rounded_rectangle([0, 0, w * SS - 1, h * SS - 1], radius=r * SS, fill=fill, outline=outline, width=width * SS)
	return big.resize((w, h), Image.LANCZOS)


def glass(w, h, r=22, tint=(255, 255, 255), alpha=22, border=58):
	"""Translucent panel with a soft top highlight and a thin light border."""
	base = rounded(w, h, r, tint + (alpha,), outline=tint + (border,), width=2)
	hl = Image.new("RGBA", (w, h), (0, 0, 0, 0))
	hd = ImageDraw.Draw(hl)
	for y in range(int(h * 0.45)):
		a = int(16 * (1 - y / (h * 0.45)))
		hd.line([(0, y), (w, y)], fill=(255, 255, 255, a))
	mask = rounded(w, h, r, (255, 255, 255, 255)).split()[3]
	hl.putalpha(Image.composite(hl.split()[3], Image.new("L", (w, h), 0), mask))
	return Image.alpha_composite(base, hl)


def font(size):
	return ImageFont.truetype(FB, size)


def badge(text, w, h, color):
	img = rounded(w, h, h // 3, color + (255,))
	d = ImageDraw.Draw(img)
	d.text((w / 2, h / 2 + 1), text, font=font(int(h * 0.62)), fill=(255, 255, 255, 255), anchor="mm")
	return img


def icon(kind, size=44, color=(235, 235, 240, 255)):
	s = size * SS
	img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
	d = ImageDraw.Draw(img)
	lw = int(s * 0.09)
	if kind == "search":
		r = s * 0.30
		d.ellipse([s * 0.12, s * 0.12, s * 0.12 + 2 * r, s * 0.12 + 2 * r], outline=color, width=lw)
		d.line([s * 0.62, s * 0.62, s * 0.88, s * 0.88], fill=color, width=lw)
	elif kind == "home":
		d.polygon([(s * 0.5, s * 0.10), (s * 0.92, s * 0.48), (s * 0.08, s * 0.48)], fill=color)
		d.rectangle([s * 0.2, s * 0.46, s * 0.8, s * 0.88], fill=color)
		d.rectangle([s * 0.42, s * 0.62, s * 0.58, s * 0.88], fill=(0, 0, 0, 0))
	elif kind == "movies":
		d.rounded_rectangle([s * 0.1, s * 0.3, s * 0.9, s * 0.88], radius=s * 0.06, outline=color, width=lw)
		for i in range(4):
			x = s * (0.12 + i * 0.2)
			d.polygon([(x, s * 0.12), (x + s * 0.1, s * 0.12), (x + s * 0.17, s * 0.28), (x + s * 0.07, s * 0.28)], fill=color)
	elif kind == "tv":
		d.rounded_rectangle([s * 0.08, s * 0.16, s * 0.92, s * 0.72], radius=s * 0.06, outline=color, width=lw)
		d.line([s * 0.3, s * 0.88, s * 0.7, s * 0.88], fill=color, width=lw)
	elif kind == "lists":
		for i in range(3):
			y = s * (0.22 + i * 0.28)
			d.ellipse([s * 0.08, y - s * 0.06, s * 0.2, y + s * 0.06], fill=color)
			d.line([s * 0.3, y, s * 0.92, y], fill=color, width=lw)
	elif kind == "settings":
		c = s / 2
		for i in range(8):
			a = i * math.pi / 4
			d.line([c + math.cos(a) * s * 0.18, c + math.sin(a) * s * 0.18, c + math.cos(a) * s * 0.42, c + math.sin(a) * s * 0.42], fill=color, width=int(lw * 1.6))
		d.ellipse([c - s * 0.30, c - s * 0.30, c + s * 0.30, c + s * 0.30], fill=color)
		d.ellipse([c - s * 0.13, c - s * 0.13, c + s * 0.13, c + s * 0.13], fill=(0, 0, 0, 0))
	elif kind == "play":
		d.polygon([(s * 0.22, s * 0.12), (s * 0.22, s * 0.88), (s * 0.88, s * 0.5)], fill=color)
	elif kind == "info":
		d.ellipse([s * 0.08, s * 0.08, s * 0.92, s * 0.92], outline=color, width=lw)
		d.ellipse([s * 0.45, s * 0.24, s * 0.55, s * 0.34], fill=color)
		d.rectangle([s * 0.45, s * 0.42, s * 0.55, s * 0.76], fill=color)
	elif kind == "person":
		d.ellipse([s * 0.30, s * 0.10, s * 0.70, s * 0.50], fill=color)
		d.pieslice([s * 0.10, s * 0.52, s * 0.90, s * 1.30], 180, 360, fill=color)
	return img.resize((size, size), Image.LANCZOS)


def background(w=960, h=540):
	"""Opaque dark background with a soft accent glow (screens without backdrop)."""
	img = Image.new("RGBA", (w, h))
	px = img.load()
	for y in range(h):
		for x in range(w):
			fx, fy = x / float(w), y / float(h)
			g1 = max(0.0, 1 - math.hypot(fx - 0.05, fy - 0.0) / 0.9) ** 2
			g2 = max(0.0, 1 - math.hypot(fx - 1.0, fy - 1.0) / 0.9) ** 2
			r = BG[0] + ACCENT[0] * 0.10 * g1 + PURPLE[0] * 0.14 * g2
			g = BG[1] + ACCENT[1] * 0.10 * g1 + PURPLE[1] * 0.14 * g2
			b = BG[2] + ACCENT[2] * 0.12 * g1 + PURPLE[2] * 0.14 * g2
			px[x, y] = (int(r), int(g), int(b), 255)
	return img


# backdrop overlays (960x540, scaled to the screen)
def _c(v):
	return max(0.0, min(1.0, v))


def hero_alpha(fx, fy):
	side = _c((1 - fx / 0.78) * 1.25) ** 1.1 * 0.94
	bottom = (0.0 if fy < 0.48 else _c((fy - 0.48) / 0.28)) ** 1.1 * 0.97
	return max(0.30, side, bottom)


def detail_alpha(fx, fy):
	side = _c((1 - fx / 0.85) * 1.15) * 0.92
	bottom = (0.0 if fy < 0.55 else _c((fy - 0.55) / 0.30)) * 0.95
	return max(0.62, side, bottom)


save(gradient_overlay(960, 540, hero_alpha), "hero_overlay.png")
save(gradient_overlay(960, 540, lambda fx, fy: 0.78 + 0.18 * _c((fy - 0.70) / 0.30)), "dim_overlay.png")
# expanded icon rail on the start screen: darkens the left part so the names stay readable
save(gradient_overlay(960, 540, lambda fx, fy: _c(1.15 - fx / 0.42) * 0.9 if fy < 0.6 else _c(1.15 - fx / 0.42) * 0.9 * _c((0.75 - fy) / 0.15)), "rail_overlay.png")
save(gradient_overlay(960, 540, detail_alpha), "detail_overlay.png")
save(background(), "background.png")
# glass panels (exact FHD sizes, scaled together with the skin)
for name, (w, h, r) in {
	"glass_list.png": (1240, 600, 24),
	"glass_info.png": (1820, 168, 22),
	"glass_episodes.png": (1820, 712, 24),
	"glass_menu.png": (540, 872, 24),
	"glass_dialog.png": (1000, 520, 26),
	"glass_tech.png": (1000, 52, 16),
}.items():
	save(glass(w, h, r), name)
# frames, pills, badges
save(rounded(216, 316, 14, (0, 0, 0, 0), outline=(255, 255, 255, 255), width=4), "frame_poster.png")
save(rounded(316, 185, 14, (0, 0, 0, 0), outline=(255, 255, 255, 255), width=4), "frame_card.png")
save(rounded(166, 241, 14, (0, 0, 0, 0), outline=(255, 255, 255, 255), width=4), "frame_person.png")
save(rounded(280, 64, 32, (245, 245, 248, 255)), "pill_primary.png")
save(glass(280, 64, 32, alpha=40, border=70), "pill_secondary.png")
save(rounded(72, 72, 36, ACCENT + (255,)), "rail_sel.png")
save(badge("NEU", 64, 28, PURPLE), "badge_new.png")
save(badge("gesehen", 104, 28, GREEN), "badge_seen.png")
for k in ("search", "home", "movies", "tv", "lists", "settings"):
	save(icon(k), "icon_%s.png" % k)
save(icon("play", 28, (16, 16, 22, 255)), "icon_play_dark.png")
save(icon("info", 28), "icon_info.png")
save(icon("person", 64, (90, 90, 105, 255)), "icon_person.png")
print("assets written to %s" % OUT)
