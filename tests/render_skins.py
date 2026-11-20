# Render the embedded skins to PNG mockups for a visual layout check (approximation of Enigma2 drawing)
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "e2stubs"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from JellyfinOpenPLi import jfskin  # noqa: E402

FONT = os.environ.get("PREVIEW_FONT", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
OUT = sys.argv[1] if len(sys.argv) > 1 else "skin-previews"
os.makedirs(OUT, exist_ok=True)

SAMPLE = {
	"title": "Filme", "subtitle": "245 Titel  |  Sortierung: Name (A-Z)  |  Filter: Ungesehen", "pageinfo": "Seite 1 / 18",
	"info_title": "Der Herr der Ringe: Die Gefährten", "info_meta": "2001  |  2 Std. 58 Min.  |  FSK 12  |  Bewertung 8,8  |  Abenteuer, Fantasy",
	"info_overview": "Der Hobbit Frodo erbt einen mächtigen Ring, der vernichtet werden muss. Gemeinsam mit acht Gefährten bricht er zu einer gefährlichen Reise nach Mordor auf, wo der Ring einst geschmiedet wurde ...",
	"key_red": "Sortierung", "key_green": "Filter", "key_yellow": "Gesehen +/-", "key_blue": "Favorit +/-", "key_hint": "MENU Optionen  |  CH+/- Seite  |  PLAY",
	"preview_title": "Weiterschauen", "preview_hint": "OK: alle anzeigen", "tagline": "Ein Ring, sie zu knechten.",
	"meta": "2001   |   2 Std. 58 Min.   |   FSK 12   |   Bewertung 8,8   |   endet um 23:41", "genres": "Abenteuer, Fantasy, Action",
	"overview": "Der Hobbit Frodo erbt von seinem Onkel Bilbo einen Ring. Der Zauberer Gandalf erkennt, dass es sich um den Einen Ring handelt, mit dem der dunkle Herrscher Sauron Mittelerde unterjochen will. Frodo muss den Ring zerstören ...",
	"tech": "Video: 4K HEVC HDR10   |   Container: MKV   |   58.2 GB\nAudio: [Deutsch EAC3 5.1], Englisch TRUEHD 7.1\nUntertitel: Deutsch, Englisch   (gewählt: aus)",
	"people": "Regie: Peter Jackson\nMit: Elijah Wood, Ian McKellen, Viggo Mortensen, Sean Astin, Orlando Bloom",
	"info": "Die Gefährten erreichen Bruchtal, wo Elrond einen Rat einberuft ...", "description": "Adresse des Jellyfin-Servers, z.B. http://192.168.1.10:8096",
	"status": "", "code": "482915", "text": "Öffne Jellyfin am Handy oder PC, gehe zu Benutzer > Quick Connect und gib diesen Code ein:",
}
LISTS = {
	"menu": ["Weiterschauen", "Als Nächstes", "Neu hinzugefügt", "Filme", "Serien", "Musik", "Favoriten", "Suche", "Einstellungen"],
	"actions": ["Fortsetzen (0:42:13)", "Von Anfang", "Audiospur", "Untertitel", "Gesehen", "Favorit"],
	"list": ["1. Pilot", "2. Der Anfang", "3. Die Rückkehr", "4. Finale"],
}


def color(v, default=(0, 0, 0, 0)):
	if not v or not v.startswith("#"):
		return default
	v = v[1:]
	a = int(v[0:2], 16) if len(v) == 8 else 0
	r, g, b = int(v[-6:-4], 16), int(v[-4:-2], 16), int(v[-2:], 16)
	return (r, g, b, 255 - a)


def font(attr):
	size = int(attr.split(";")[1]) if attr and ";" in attr else 24
	return ImageFont.truetype(FONT, int(size * 0.9))


def render(name, xml, w=1920, h=1080):
	root = ET.fromstring(xml)
	sx, sy = [int(v) for v in root.get("position").split(",")]
	img = Image.new("RGBA", (w, h), (40, 70, 40, 255))
	scr = Image.new("RGBA", tuple(int(v) for v in root.get("size").split(",")), color(root.get("backgroundColor")))
	elems = sorted(list(root), key=lambda e: int(e.get("zPosition") or 0))
	for el in elems:
		pos, size = el.get("position"), el.get("size")
		if not pos or not size:
			continue
		x, y = [int(v) for v in pos.split(",")]
		ew, eh = [int(v) for v in size.split(",")]
		layer = Image.new("RGBA", scr.size, (0, 0, 0, 0))
		d = ImageDraw.Draw(layer)
		bg = color(el.get("backgroundColor"))
		wname = el.get("name") or ""
		if el.tag == "eLabel" or (el.get("transparent") != "1" and bg[3] and "cover" not in wname and wname not in ("backdrop", "poster")):
			if el.tag == "eLabel" or wname in ("frame",) or not wname.startswith(("ph", "pph", "seen", "count")) or True:
				d.rectangle([x, y, x + ew - 1, y + eh - 1], fill=bg)
		if wname in ("backdrop",):
			d.rectangle([x, y, x + ew - 1, y + eh - 1], fill=(70, 50, 30, 255))
		elif "cover" in wname or wname == "poster":
			d.rectangle([x, y, x + ew - 1, y + eh - 1], fill=(60, 90, 130, 255))
			d.line([x, y, x + ew, y + eh], fill=(90, 120, 160, 255), width=2)
		elif "prog" in wname or wname == "progress":
			d.rectangle([x, y, x + int(ew * 0.4), y + eh - 1], fill=color(el.get("foregroundColor")))
		elif wname in LISTS:
			ih = int(el.get("itemHeight") or 50)
			for i, t in enumerate(LISTS[wname]):
				yy = y + i * ih
				if yy + ih > y + eh:
					break
				if i == 1:
					d.rectangle([x, yy, x + ew - 1, yy + ih - 1], fill=color(el.get("backgroundColorSelected"), (0, 164, 220, 255)))
				d.text((x + 16, yy + ih // 2), t, font=ImageFont.truetype(FONT, int(ih * 0.42)), fill=(240, 240, 240, 255), anchor="lm")
		elif el.tag == "widget" and el.get("render") == "Label":
			d.text((x + ew, y + eh // 2), "21:37", font=font(el.get("font")), fill=color(el.get("foregroundColor")), anchor="rm")
		elif el.tag == "widget":
			text = SAMPLE.get(wname)
			if text is None:
				base = wname.rstrip("0123456789").lstrip("p") if wname.startswith("p") and not wname.startswith(("pageinfo", "preview", "poster")) else wname.rstrip("0123456789")
				text = {"new": "NEU", "count": "+3"}.get(base, "")
				if base == "seen":
					continue
				if wname.startswith(("label", "plabel")):
					text = "Filmtitel %s" % wname[-1]
			if text:
				f = font(el.get("font"))
				fc = color(el.get("foregroundColor"), (255, 255, 255, 255))
				ha = el.get("halign", "left")
				lines = []
				for para in text.split("\n"):
					cur = ""
					for word in para.split(" "):
						test = (cur + " " + word).strip()
						if d.textlength(test, font=f) > ew - 4 and cur:
							lines.append(cur)
							cur = word
						else:
							cur = test
					lines.append(cur)
				if el.get("noWrap") == "1":
					lines = lines[:1]
				lh = f.size * 1.25
				total = lh * len(lines)
				ty = y if el.get("valign") == "top" else y + (eh - total) / 2
				for ln in lines:
					if ty + lh > y + eh + 2:
						break
					tx = x + ew / 2 if ha == "center" else (x + ew if ha == "right" else x)
					anchor = "ma" if ha == "center" else ("ra" if ha == "right" else "la")
					d.text((tx, ty), ln, font=f, fill=fc, anchor=anchor)
					ty += lh
		scr = Image.alpha_composite(scr, layer)
	img.paste(scr, (sx, sy))
	path = os.path.join(OUT, name + ".png")
	img.convert("RGB").resize((1280, 720)).save(path)
	return path


for nm, fn in (("home", jfskin.home_skin), ("grid", jfskin.grid_skin), ("detail", jfskin.detail_skin), ("episodes", jfskin.episodes_skin),
		("login", jfskin.list_skin), ("quickconnect", jfskin.quickconnect_skin)):
	print(render(nm, fn()))
