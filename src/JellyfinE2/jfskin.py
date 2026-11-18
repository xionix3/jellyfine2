# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
# Jellyfin for Enigma2 - embedded skins (designed for 1920x1080, scaled at runtime)
from __future__ import absolute_import, division

import re

from enigma import getDesktop

BG = "#00101016"
PANEL = "#001c1c28"
PLACEHOLDER = "#00262634"
ACCENT = "#0000a4dc"
ACCENT2 = "#00aa5cc3"
TEXT = "#00f2f2f2"
DIM = "#009a9aae"
OVERLAY = "#30101016"
GREEN = "#0043a047"
NEW_C = "#00aa5cc3"
BACKDROP_OVERLAY = "#40101016"
RED_C = "#00e53935"
GREEN_C = "#0043a047"
YELLOW_C = "#00fbc02d"
BLUE_C = "#001e88e5"

# integer colours for MultiContent
C_TEXT = 0xf2f2f2
C_DIM = 0x9a9aae
C_ACCENT = 0x00a4dc
C_GREEN = 0x43a047
C_SEL_BG = 0x00a4dc
C_PLACEHOLDER = 0x262634


def factor():
	try:
		h = getDesktop(0).size().height()
	except Exception:
		h = 1080
	return h / 1080.0


def S(v):
	"""Scale a FHD pixel value to the current desktop."""
	return int(round(v * factor()))


def scale_skin(xml):
	f = factor()
	if abs(f - 1.0) < 0.001:
		return xml

	def sc(v):
		return str(int(round(int(v) * f)))

	xml = re.sub(r'(position|size)="(\d+),(\d+)"', lambda m: '%s="%s,%s"' % (m.group(1), sc(m.group(2)), sc(m.group(3))), xml)
	xml = re.sub(r'font="([A-Za-z]+);(\d+)"', lambda m: 'font="%s;%s"' % (m.group(1), sc(m.group(2))), xml)
	xml = re.sub(r'(itemHeight|borderWidth|scrollbarWidth)="(\d+)"', lambda m: '%s="%s"' % (m.group(1), sc(m.group(2))), xml)
	return xml


# ---------------------------------------------------------------- building blocks
def label(name, x, y, w, h, size=28, color=TEXT, bg=None, halign="left", valign="center", extra=""):
	bgattr = 'backgroundColor="%s"' % bg if bg else 'backgroundColor="%s" transparent="1"' % BG
	return ('<widget name="%s" position="%d,%d" size="%d,%d" font="Regular;%d" foregroundColor="%s" %s halign="%s" valign="%s" %s />'
		% (name, x, y, w, h, size, color, bgattr, halign, valign, extra))


def rect(x, y, w, h, color, z=0):
	return '<eLabel position="%d,%d" size="%d,%d" backgroundColor="%s" zPosition="%d" />' % (x, y, w, h, color, z)


def clock():
	return ('<widget source="global.CurrentTime" render="Label" position="1640,30" size="220,50" font="Regular;38" '
		'foregroundColor="%s" backgroundColor="%s" transparent="1" halign="right" valign="center">'
		'<convert type="ClockToText">Default</convert></widget>' % (TEXT, BG))


def keybar(y=1024, hint=True, z=0):
	out = []
	x = 60
	zattr = 'zPosition="%d"' % z if z else ""
	for name, col in (("key_red", RED_C), ("key_green", GREEN_C), ("key_yellow", YELLOW_C), ("key_blue", BLUE_C)):
		out.append(rect(x, y + 4, 8, 32, col, z))
		out.append(label(name, x + 18, y, 300, 40, 26, TEXT, extra=zattr))
		x += 340
	if hint:
		out.append(label("key_hint", 1420, y, 440, 40, 24, DIM, halign="right", extra=zattr))
	return "\n".join(out)


def screen(name, body, title="Jellyfin", bg=BG):
	return scale_skin('<screen name="%s" position="0,0" size="1920,1080" flags="wfNoBorder" backgroundColor="%s" title="%s">\n%s\n</screen>'
		% (name, bg, title, body))


# ---------------------------------------------------------------- grid geometry
GRID_COLS = 7
GRID_ROWS = 2
GRID_X0 = 69
GRID_Y0 = 150
GRID_STEP_X = 264
GRID_STEP_Y = 372
COVER_W = 200
COVER_H = 300
CELL_LABEL_H = 34


def cell_pos(i, cols=GRID_COLS, x0=GRID_X0, y0=GRID_Y0, sx=GRID_STEP_X, sy=GRID_STEP_Y):
	r, c = divmod(i, cols)
	return x0 + c * sx, y0 + r * sy


def cover_cells(prefix, count, cols, x0, y0, sx, sy, w=COVER_W, h=COVER_H, badges=True):
	out = []
	for i in range(count):
		x, y = cell_pos(i, cols, x0, y0, sx, sy)
		out.append(label("%sph%d" % (prefix, i), x, y, w, h, 24, DIM, bg=PLACEHOLDER, halign="center", valign="center"))
		out.append('<widget name="%scover%d" position="%d,%d" size="%d,%d" alphatest="blend" scale="1" zPosition="1" />' % (prefix, i, x, y, w, h))
		out.append('<widget name="%sprog%d" position="%d,%d" size="%d,%d" foregroundColor="%s" backgroundColor="#40000000" borderWidth="0" zPosition="2" />'
			% (prefix, i, x, y + h - 8, w, 8, ACCENT))
		if badges:
			out.append(label("%sseen%d" % (prefix, i), x + 8, y + 8, 92, 28, 19, TEXT, bg=GREEN, halign="center", extra='zPosition="3"'))
			out.append(label("%snew%d" % (prefix, i), x + 8, y + 8, 64, 28, 19, TEXT, bg=NEW_C, halign="center", extra='zPosition="3"'))
			out.append(label("%scount%d" % (prefix, i), x + w - 66, y + 8, 58, 30, 21, TEXT, bg=ACCENT, halign="center", extra='zPosition="3"'))
		out.append(label("%slabel%d" % (prefix, i), x - 10, y + h + 2, w + 20, CELL_LABEL_H, 24, TEXT, halign="center", extra='noWrap="1"'))
	return "\n".join(out)


def backdrop_layer():
	return ('<widget name="backdrop" position="0,0" size="1920,1080" alphatest="off" scale="1" zPosition="-2" />\n'
		'<eLabel position="0,0" size="1920,1080" backgroundColor="%s" zPosition="-1" />' % BACKDROP_OVERLAY)


def grid_skin():
	cells = GRID_COLS * GRID_ROWS
	body = [
		backdrop_layer(),
		label("title", 60, 24, 1300, 64, 46, TEXT),
		label("subtitle", 60, 88, 1350, 40, 26, DIM),
		label("pageinfo", 1420, 88, 440, 40, 26, DIM, halign="right"),
		clock(),
		'<widget name="frame" position="%d,%d" size="%d,%d" backgroundColor="%s" zPosition="0" />' % (GRID_X0 - 7, GRID_Y0 - 7, COVER_W + 14, COVER_H + 14, ACCENT),
		cover_cells("", cells, GRID_COLS, GRID_X0, GRID_Y0, GRID_STEP_X, GRID_STEP_Y),
		rect(60, 862, 1800, 2, PANEL),
		label("info_title", 69, 872, 1782, 44, 34, TEXT, extra='noWrap="1"'),
		label("info_meta", 69, 916, 1782, 34, 26, ACCENT, extra='noWrap="1"'),
		label("info_overview", 69, 952, 1782, 66, 24, DIM, valign="top"),
		keybar(),
		label("status", 560, 440, 800, 140, 34, TEXT, bg=PANEL, halign="center", extra='zPosition="5"'),
	]
	return screen("JellyfinE2Grid", "\n".join(body))


HOME_COLS = 5
HOME_ROWS = 2
HOME_X0 = 640
HOME_Y0 = 214
HOME_STEP_X = 246
HOME_STEP_Y = 372


def home_skin():
	body = [
		backdrop_layer(),
		label("title", 60, 24, 900, 64, 50, ACCENT),
		label("subtitle", 60, 90, 1300, 40, 26, DIM),
		clock(),
		rect(60, 146, 520, 2, PANEL),
		'<widget name="menu" position="60,160" size="520,858" itemHeight="66" scrollbarMode="showOnDemand" backgroundColor="%s" '
		'foregroundColor="%s" backgroundColorSelected="%s" foregroundColorSelected="#00ffffff" transparent="1" />' % (BG, TEXT, ACCENT),
		label("preview_title", HOME_X0, 156, 1220, 46, 34, TEXT),
		cover_cells("p", HOME_COLS * HOME_ROWS, HOME_COLS, HOME_X0, HOME_Y0, HOME_STEP_X, HOME_STEP_Y),
		label("preview_hint", HOME_X0, 960, 1220, 40, 26, DIM),
		keybar(),
		label("status", 760, 440, 800, 140, 34, TEXT, bg=PANEL, halign="center", extra='zPosition="5"'),
	]
	return screen("JellyfinE2Home", "\n".join(body))


def detail_skin():
	body = [
		'<widget name="backdrop" position="0,0" size="1920,1080" alphatest="off" scale="1" zPosition="0" />',
		'<eLabel position="0,0" size="1920,1080" backgroundColor="%s" zPosition="1" />' % OVERLAY,
		label("poster_ph", 80, 120, 340, 510, 26, DIM, bg=PLACEHOLDER, halign="center", extra='zPosition="2"'),
		'<widget name="poster" position="80,120" size="340,510" alphatest="blend" scale="1" zPosition="3" />',
		'<widget name="progress" position="80,634" size="340,8" foregroundColor="%s" backgroundColor="#60000000" borderWidth="0" zPosition="3" />' % ACCENT,
		'<widget name="actions" position="80,664" size="340,350" itemHeight="58" scrollbarMode="showOnDemand" backgroundColor="%s" '
		'foregroundColor="%s" backgroundColorSelected="%s" foregroundColorSelected="#00ffffff" zPosition="3" />' % (PANEL, TEXT, ACCENT),
		label("title", 480, 110, 1380, 72, 54, TEXT, extra='zPosition="3" noWrap="1"'),
		label("tagline", 480, 182, 1380, 40, 28, DIM, extra='zPosition="3" noWrap="1"'),
		label("meta", 480, 226, 1380, 42, 30, ACCENT, extra='zPosition="3" noWrap="1"'),
		label("genres", 480, 270, 1380, 36, 26, DIM, extra='zPosition="3" noWrap="1"'),
		'<widget name="overview" position="480,322" size="1380,330" font="Regular;30" foregroundColor="%s" backgroundColor="%s" transparent="1" zPosition="3" />' % (TEXT, BG),
		label("tech", 480, 668, 1380, 120, 25, DIM, valign="top", extra='zPosition="3"'),
		label("people", 480, 796, 1380, 110, 25, DIM, valign="top", extra='zPosition="3"'),
		label("status", 480, 920, 1380, 40, 26, ACCENT, extra='zPosition="3"'),
		keybar(z=3),
	]
	return screen("JellyfinE2Detail", "\n".join(body))


def episodes_skin():
	body = [
		'<widget name="backdrop" position="0,0" size="1920,1080" alphatest="off" scale="1" zPosition="0" />',
		'<eLabel position="0,0" size="1920,1080" backgroundColor="#20101016" zPosition="1" />',
		label("title", 60, 24, 1500, 64, 46, TEXT, extra='zPosition="3" noWrap="1"'),
		label("subtitle", 60, 88, 1500, 44, 30, ACCENT, extra='zPosition="3"'),
		clock().replace('transparent="1"', 'transparent="1" zPosition="3"'),
		'<widget name="list" position="60,146" size="1800,696" itemHeight="174" scrollbarMode="showOnDemand" backgroundColor="%s" '
		'foregroundColor="%s" backgroundColorSelected="#00203a4c" foregroundColorSelected="#00ffffff" transparent="1" zPosition="3" />' % (BG, TEXT),
		rect(60, 852, 1800, 2, PANEL, 3),
		label("info", 60, 862, 1800, 150, 26, DIM, valign="top", extra='zPosition="3"'),
		keybar(z=3),
		label("status", 560, 440, 800, 140, 34, TEXT, bg=PANEL, halign="center", extra='zPosition="5"'),
	]
	return screen("JellyfinE2Episodes", "\n".join(body))


def list_skin(name="JellyfinE2Login", with_status=True, item_height=70):
	body = [
		label("title", 60, 24, 1500, 64, 46, TEXT),
		label("subtitle", 60, 88, 1500, 40, 26, DIM),
		clock(),
		'<widget name="list" position="360,170" size="1200,560" itemHeight="%d" scrollbarMode="showOnDemand" backgroundColor="%s" '
		'foregroundColor="%s" backgroundColorSelected="%s" foregroundColorSelected="#00ffffff" />' % (item_height, PANEL, TEXT, ACCENT),
		label("description", 360, 750, 1200, 110, 26, DIM, valign="top"),
	]
	if with_status:
		body.append(label("status", 360, 870, 1200, 120, 28, ACCENT, valign="top"))
	body.append(keybar(hint=False))
	return screen(name, "\n".join(body))


def quickconnect_skin():
	body = [
		rect(0, 0, 1000, 520, PANEL),
		label("title", 40, 24, 920, 56, 40, TEXT, bg=PANEL),
		label("text", 40, 92, 920, 120, 28, DIM, bg=PANEL, valign="top"),
		label("code", 40, 220, 920, 140, 110, ACCENT, bg=PANEL, halign="center"),
		label("status", 40, 380, 920, 80, 26, TEXT, bg=PANEL, halign="center"),
		rect(40, 470, 8, 32, RED_C),
		label("key_red", 58, 466, 400, 40, 26, TEXT, bg=PANEL),
	]
	xml = '<screen name="JellyfinE2QuickConnect" position="460,280" size="1000,520" flags="wfNoBorder" backgroundColor="%s">\n%s\n</screen>' % (PANEL, "\n".join(body))
	return scale_skin(xml)
