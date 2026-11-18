# Renders the real plugin screens (driven against the fake server in demo mode) to images for the README.
# usage: python3 tests/screenshots.py [outdir]
import os
import shutil
import sys
import xml.etree.ElementTree as ET

from harness import Session, press, pump  # sets up sys.path and the Enigma2 stubs
import enigma  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from Components.GUIComponent import GUIComponent  # noqa: E402
from Components.Label import Label  # noqa: E402
from Components.MenuList import MenuList  # noqa: E402
from Components.Pixmap import Pixmap  # noqa: E402
from Components.ProgressBar import ProgressBar  # noqa: E402
from Components.ScrollLabel import ScrollLabel  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "docs", "screenshots"))
FONT = os.environ.get("PREVIEW_FONT", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
_fonts = {}


def font(size):
	size = max(8, int(size * 0.92))
	if size not in _fonts:
		try:
			_fonts[size] = ImageFont.truetype(FONT, size)
		except IOError:
			_fonts[size] = ImageFont.load_default()
	return _fonts[size]


def parse_color(v, default=None):
	if v is None:
		return default
	if isinstance(v, int):
		return ((v >> 16) & 255, (v >> 8) & 255, v & 255, 255 - ((v >> 24) & 255))
	v = v.lstrip("#")
	a = int(v[0:2], 16) if len(v) == 8 else 0
	return (int(v[-6:-4], 16), int(v[-4:-2], 16), int(v[-2:], 16), 255 - a)


def xy(el, attr):
	return [int(n) for n in el.get(attr).split(",")]


def wrap(d, text, f, width, nowrap=False):
	lines = []
	for para in text.split("\n"):
		if nowrap:
			lines.append(para)
			continue
		cur = ""
		for word in para.split(" "):
			test = (cur + " " + word).strip() if cur else word
			if d.textlength(test, font=f) > width and cur:
				lines.append(cur)
				cur = word
			else:
				cur = test
		lines.append(cur)
	return lines


def draw_text(d, box, text, size, color, halign="left", valign="top", nowrap=False, wrap_ok=True):
	x, y, w, h = box
	if not text:
		return
	f = font(size)
	lines = wrap(d, text, f, w - 4, nowrap or not wrap_ok)
	lh = int(f.size * 1.22)
	max_lines = max(1, h // lh)
	if len(lines) > max_lines:
		lines = lines[:max_lines]
	total = lh * len(lines)
	ty = y if valign == "top" else (y + (h - total) // 2 if valign == "center" else y + h - total)
	for ln in lines:
		while ln and d.textlength(ln, font=f) > w:
			ln = ln[:-2] + "…" if len(ln) > 2 else ""
		if halign == "center":
			d.text((x + w / 2, ty), ln, font=f, fill=color, anchor="ma")
		elif halign == "right":
			d.text((x + w, ty), ln, font=f, fill=color, anchor="ra")
		else:
			d.text((x, ty), ln, font=f, fill=color, anchor="la")
		ty += lh


def draw_list(img, el, comp):
	x, y = xy(el, "position")
	w, h = xy(el, "size")
	ih = comp.l.item_height or int(el.get("itemHeight", 50))
	rows = comp.list or []
	sel = comp.l.index
	visible = max(1, h // ih)
	top = max(0, sel - visible + 1)
	bg = parse_color(el.get("backgroundColor"), (0, 0, 0, 0)) if el.get("transparent") != "1" else (0, 0, 0, 0)
	bg_sel = parse_color(el.get("backgroundColorSelected"), (0, 164, 220, 255))
	fg = parse_color(el.get("foregroundColor"), (240, 240, 240, 255))
	fg_sel = parse_color(el.get("foregroundColorSelected"), (255, 255, 255, 255))
	layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
	d = ImageDraw.Draw(layer)
	d.rectangle([x, y, x + w - 1, y + h - 1], fill=bg)
	for n, row in enumerate(rows[top:top + visible]):
		ry = y + n * ih
		selected = top + n == sel
		if selected:
			d.rectangle([x, ry, x + w - 1, ry + ih - 1], fill=bg_sel)
		for e in row[1:]:
			kind = e[0]
			ex, ey, ew, eh = x + e[1], ry + e[2], e[3], e[4]
			if kind == 0:  # text
				flags = e[6]
				bc = e[11] if selected and e[11] is not None else e[10]
				if bc is not None:
					d.rectangle([ex, ey, ex + ew - 1, ey + eh - 1], fill=parse_color(bc))
				col = e[9] if selected and e[9] is not None else e[8]
				color = parse_color(col, fg_sel if selected else fg) if col is not None else (fg_sel if selected else fg)
				size = comp.l.fonts.get(e[5]).size if comp.l.fonts.get(e[5]) else 26
				halign = "right" if flags & enigma.RT_HALIGN_RIGHT else ("center" if flags & enigma.RT_HALIGN_CENTER else "left")
				valign = "center" if flags & enigma.RT_VALIGN_CENTER else ("bottom" if flags & enigma.RT_VALIGN_BOTTOM else "top")
				draw_text(d, (ex, ey, ew, eh), e[7], size, color, halign, valign, wrap_ok=bool(flags & enigma.RT_WRAP))
			elif kind == 4 and e[5] is not None:  # pixmap
				pic = Image.open(e[5].path).convert("RGBA")
				pic.thumbnail((ew, eh))
				layer.alpha_composite(pic, (ex, ey))
			elif kind == 1:  # progress
				d.rectangle([ex, ey, ex + ew - 1, ey + eh - 1], fill=parse_color(e[9], (0, 0, 0, 255)))
				d.rectangle([ex, ey, ex + int(ew * (e[5] or 0) / 100.0) - 1, ey + eh - 1], fill=parse_color(e[7], (0, 164, 220, 255)))
	img.alpha_composite(layer)


_png = {}


def skin_png(path, w, h):
	key = (path, w, h)
	if key not in _png:
		_png[key] = Image.open(path).convert("RGBA").resize((w, h), Image.LANCZOS)
	return _png[key]


def render(scr, name, background=None):
	root = ET.fromstring(scr.skin)
	sx, sy = xy(root, "position")
	sw, sh = xy(root, "size")
	W, H = enigma.DESKTOP
	img = background.copy() if background is not None else Image.new("RGBA", (W, H), (0, 0, 0, 255))
	canvas = Image.new("RGBA", (sw, sh), parse_color(root.get("backgroundColor"), (0, 0, 0, 255)))
	for el in sorted(list(root), key=lambda e: int(e.get("zPosition") or 0)):
		if not el.get("position") or not el.get("size"):
			continue
		x, y = xy(el, "position")
		w, h = xy(el, "size")
		name_ = el.get("name")
		comp = scr.get(name_) if name_ else None
		if isinstance(comp, GUIComponent) and comp.instance is not None and comp.instance.pos is not None:
			x, y = comp.instance.pos  # moved at runtime (selection frames, badges ...)
		layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
		d = ImageDraw.Draw(layer)
		bg = parse_color(el.get("backgroundColor"))
		if el.tag == "ePixmap":
			canvas.alpha_composite(skin_png(el.get("pixmap"), w, h), (x, y))
			continue
		if el.tag == "eLabel":
			d.rectangle([x, y, x + w - 1, y + h - 1], fill=bg)
			canvas.alpha_composite(layer)
			continue
		if el.get("source") == "global.CurrentTime":
			draw_text(d, (x, y, w, h), "20:15", int(el.get("font").split(";")[1]), parse_color(el.get("foregroundColor")), "right", "center")
			canvas.alpha_composite(layer)
			continue
		if not isinstance(comp, GUIComponent) or not comp.visible:
			continue
		if isinstance(comp, MenuList):
			draw_list(canvas, el, comp)
			continue
		if isinstance(comp, Pixmap):
			pix = comp.instance.pixmap if comp.instance else None
			path = pix.path if pix is not None else el.get("pixmap")  # skin pixmap until setPixmap
			if path:
				pic = Image.open(path).convert("RGBA")
				pic = pic.resize((w, h), Image.LANCZOS) if el.get("scale") == "1" else pic
				if el.get("alphatest") != "blend":
					pic.putalpha(255)
				canvas.alpha_composite(pic, (x, y))
			continue
		if isinstance(comp, ProgressBar):
			d.rectangle([x, y, x + w - 1, y + h - 1], fill=bg or (0, 0, 0, 120))
			d.rectangle([x, y, x + int(w * comp.value / 100.0) - 1, y + h - 1], fill=parse_color(el.get("foregroundColor")))
			canvas.alpha_composite(layer)
			continue
		if isinstance(comp, (Label, ScrollLabel)):
			if el.get("transparent") != "1" and bg:
				d.rectangle([x, y, x + w - 1, y + h - 1], fill=bg)
			size = int(el.get("font", "Regular;28").split(";")[1])
			fg = comp.instance.fg if comp.instance is not None and comp.instance.fg is not None else el.get("foregroundColor")
			draw_text(d, (x, y, w, h), comp.text, size, parse_color(fg, (240, 240, 240, 255)),
				el.get("halign", "left"), "top" if isinstance(comp, ScrollLabel) else el.get("valign", "top"), el.get("noWrap") == "1")
			canvas.alpha_composite(layer)
	img.alpha_composite(canvas, (sx, sy))
	os.makedirs(OUT, exist_ok=True)
	path = os.path.join(OUT, name + ".jpg")
	img.convert("RGB").resize((1280, 720), Image.LANCZOS).save(path, quality=90)
	print(path)
	return img


def render_choice(box, name, background):
	"""ChoiceBox in a neutral dialog look (the real one comes from the user's skin)."""
	img = background.copy()
	W, H = img.size
	rows = box.list
	rh = 54
	w, h = 760, 90 + rh * len(rows) + 30
	x, y = (W - w) // 2, (H - h) // 2
	layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
	d = ImageDraw.Draw(layer)
	d.rounded_rectangle([x, y, x + w, y + h], radius=18, fill=(26, 26, 36, 245), outline=(255, 255, 255, 60), width=2)
	draw_text(d, (x + 30, y + 22, w - 60, 50), box.dlg_title, 34, (240, 240, 240, 255))
	for i, row in enumerate(rows):
		ry = y + 90 + i * rh
		if i == box.selection:
			d.rounded_rectangle([x + 16, ry, x + w - 16, ry + rh - 6], radius=12, fill=(0, 164, 220, 255))
		draw_text(d, (x + 36, ry, w - 72, rh - 6), row[0], 28, (245, 245, 245, 255), valign="center", nowrap=True)
	img.alpha_composite(layer)
	path = os.path.join(OUT, name + ".jpg")
	img.convert("RGB").resize((1280, 720), Image.LANCZOS).save(path, quality=90)
	print(path)


def settle(cond=None, timeout=10):
	pump(cond, timeout=timeout)
	pump(timeout=0.6)


def main():
	from mockjf import start_server
	enigma.DESKTOP[:] = [1920, 1080]
	srv, state, url = start_server("10.10.7", demo=True)
	shutil.rmtree("/tmp/jellyfine2", ignore_errors=True)
	from JellyfinE2 import plugin, jfconfig
	jfconfig.set_value("update_check", "0")
	s = Session()
	plugin.main(s)
	login = s.top
	login.server, login.username, login.password = "http://192.168.1.10:8096", "patrick", "geheim"
	login.build()
	login["list"].moveToIndex(3)
	login["description"].setText(login.DESCRIPTIONS["login"])
	render(login, "01-anmeldung")
	login.server = url
	press(login, "green")
	settle(lambda: s.top.__class__.__name__ == "HeroHomeScreen")
	hero = s.top
	hero.cl.server_name = "Mein Jellyfin"
	hero["server"].setText("patrick  @  Mein Jellyfin  (Jellyfin 10.10.7)")
	settle(lambda: len(hero.rows) > 4 and not hero.loading, 15)

	def ready(scr):
		def cond():
			n = len([i for i in scr.row_items if not i.get("_jf_more")])
			return (scr.row_items and scr["backdrop"].instance.pixmap is not None
				and all(scr["ccover%d" % i].instance.pixmap is not None for i in range(min(5, n))))
		return cond

	def goto(scr, title):
		settle(lambda: any(r.title == title for r in scr.rows), 15)
		for _ in range(60):
			if scr.current() is not None and scr.current().title == title:
				break
			press(scr, "down" if [r.title for r in scr.rows].index(title) > scr.row else "up")
		settle(ready(scr), 15)

	goto(hero, "Weiterschauen")
	press(hero, "right")
	settle(ready(hero), 15)
	render(hero, "02-startseite")
	goto(hero, "Neue Episoden meiner Serien")
	settle(lambda: hero.row_items[0].get("_jf_new_count"), 15)
	render(hero, "03-neue-episoden")
	press(hero, "left")
	press(hero, "down")
	render(hero, "03b-navigation")
	press(hero, "ok")  # sidebar -> movies: the library looks like the start screen
	lib = s.top
	settle(lambda: lib.__class__.__name__ == "LibraryRowsScreen" and any(r.title == "Alle Filme A-Z" for r in lib.rows), 15)
	goto(lib, "Neu hinzugefügt")
	press(lib, "right")
	press(lib, "right")
	settle(ready(lib), 15)
	render(lib, "04-filme")
	goto(lib, "Drama")
	render(lib, "04b-filme-genre")
	goto(lib, "Alle Filme A-Z")
	press(lib, "red")
	grid = s.top
	settle(lambda: grid.entries and all(grid["cover%d" % i].instance.pixmap is not None for i in range(14)) and grid["backdrop"].instance.pixmap is not None, 15)
	grid.move_to(8)
	settle(lambda: grid["backdrop"].instance.pixmap is not None)
	render(grid, "04c-raster")
	idx = [e["Name"] for e in grid.entries].index("Stadt aus Glas")
	grid.move_to(idx)
	press(grid, "ok")
	det = s.top
	settle(lambda: det.item.get("People") and det["backdrop"].instance.pixmap is not None, 15)
	render(det, "05-details")
	press(det, "down")
	settle(lambda: all(det["pphoto%d" % i].instance.pixmap is not None for i in (0, 1, 2, 3, 4)), 15)
	press(det, "right")
	press(det, "right")
	render(det, "05b-besetzung")
	press(det, "cancel")
	press(grid, "cancel")
	lib.close()
	# series detail -> episodes
	tv = [v for v in hero.views if v.get("CollectionType") == "tvshows"]
	from JellyfinE2.jfrows import LibraryRowsScreen
	s.open(LibraryRowsScreen, tv, "tvshows")
	tvl = s.top
	goto(tvl, "Alle Serien A-Z")
	tvl.card = [e.get("Name") for e in tvl.row_items].index("Lichterstadt")
	tvl.draw_cards()
	press(tvl, "ok")
	sdet = s.top
	settle(lambda: sdet.next_up is not None)
	sdet.pill = sdet.pills.index("episodes")
	press(sdet, "ok")
	eps = s.top
	settle(lambda: eps.entries and len(eps.thumbs) >= min(4, len(eps.entries)) and eps["backdrop"].instance.pixmap is not None, 15)
	render(eps, "06-episoden")
	press(eps, "cancel")
	press(sdet, "cancel")
	tvl.close()
	# search: rows per category
	hero.key_search()
	s.top.close("er")
	sr = s.top
	settle(lambda: not sr.loading and sr.rows and ready(sr)(), 15)
	render(sr, "07-suche")
	sr.close()
	press(hero, "blue")
	rs = s.top
	rs["list"].moveToIndex(1)
	render(rs, "08-meine-listen")
	press(rs, "yellow")
	ed = s.top
	ed["list"].moveToIndex(3)
	ed.update_description()
	render(ed, "09-listen-editor")
	press(ed, "cancel")
	press(rs, "cancel")
	hero.key_settings()
	st = s.top
	st["list"].moveToIndex([r[0] for r in st["list"].list].index("home_layout"))
	st.update_description()
	render(st, "10-einstellungen")
	press(st, "red")
	# classic layout for comparison
	jfconfig.set_value("home_layout", "classic")
	hero.close("relayout")
	settle(lambda: s.top.__class__.__name__ == "HomeScreen")
	home = s.top
	home["subtitle"].setText("patrick  @  Mein Jellyfin  (Jellyfin 10.10.7)")
	settle(lambda: home.cells.items[0] is not None and home["backdrop"].instance.pixmap is not None
		and all(home["pcover%d" % i].instance.pixmap is not None for i in range(4)), 15)
	render(home, "11-startseite-klassisch")
	srv.shutdown()
	os._exit(0)


if __name__ == "__main__":
	main()
