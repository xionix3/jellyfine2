# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
# Jellyfin for Enigma2 - start screen
from __future__ import absolute_import

import time

from enigma import eTimer

from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.VirtualKeyBoard import VirtualKeyBoard

from . import jfconfig, jfnav
from .jfcommon import CoverCells, JFScreen, make_list, text_row
from .jfskin import C_DIM, COVER_H, COVER_W, HOME_COLS, HOME_ROWS, home_skin

PREVIEW = HOME_COLS * HOME_ROWS
COLLECTION_LABELS = {"movies": "Filme", "tvshows": "Serien", "music": "Musik", "boxsets": "Sammlungen", "playlists": "Wiedergabelisten",
	"homevideos": "Videos", "musicvideos": "Musikvideos", "mixed": "Gemischt"}
DYNAMIC = ("resume", "nextup", "latest", "favorites", "rule")
STATIC_KEYS = ("search", "settings", "rules")
CACHE_TTL = 300  # seconds a preview is shown without refetching

# survives closing/reopening the plugin (python modules stay loaded) -> instant start
_CACHE = {"owner": None, "views": None, "previews": {}}


def _cache_for(cl):
	owner = (cl.server, cl.user_id)
	if _CACHE["owner"] != owner:
		_CACHE.update(owner=owner, views=None, previews={})
	return _CACHE


class HomeScreen(JFScreen):
	def __init__(self, session):
		JFScreen.__init__(self, session)
		self.skin = home_skin()
		self.skinName = "JellyfinE2Home"
		self.views = []
		self.sections = []
		self.cache = _cache_for(self.cl)
		self.loading = set()
		self.last_search = ""
		self.backdrops = jfconfig.get_bool("backdrops")
		self["title"] = Label("Jellyfin")
		self["subtitle"] = Label("")
		self["menu"] = make_list(fonts=((34,), (24,)), item_height=66)
		self["preview_title"] = Label("")
		self["preview_hint"] = Label("")
		self["status"] = Label("")
		self["backdrop"] = Pixmap()
		self.cells = CoverCells(self, "p", PREVIEW, COVER_W, COVER_H)
		self.add_keys(red="Abmelden", green="Suche", yellow="Aktualisieren", blue="Meine Listen", hint="MENU Optionen")
		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ColorActions", "MenuActions", "ChannelSelectBaseActions", "EPGSelectActions"], {
			"ok": self.key_ok,
			"cancel": self.close,
			"up": self["menu"].up,
			"down": self["menu"].down,
			"upRepeated": self["menu"].up,
			"downRepeated": self["menu"].down,
			"left": self["menu"].pageUp,
			"right": self["menu"].pageDown,
			"nextBouquet": self["menu"].pageDown,
			"prevBouquet": self["menu"].pageUp,
			"red": self.key_logout,
			"green": self.key_search,
			"yellow": self.key_refresh,
			"blue": self.key_rules,
			"menu": self.key_menu,
		}, -1)
		self.preview_timer = eTimer()
		self.preview_timer.callback.append(self.show_current)
		self.bd_timer = eTimer()
		self.bd_timer.callback.append(self.load_backdrop)
		self["menu"].onSelectionChanged.append(self.selection_changed)
		self.onLayoutFinish.append(self.start)
		self.onClose.append(self.preview_timer.stop)
		self.onClose.append(self.bd_timer.stop)

	# ------------------------------------------------------------- startup
	def start(self):
		self["status"].hide()
		self["backdrop"].hide()
		self.cells.clear_all()
		cl = self.cl
		self["subtitle"].setText("%s  @  %s" % (cl.user_name or "?", cl.server_name or cl.server))
		if self.cache["views"] is not None:
			# instant start from the cache of the last visit, refresh quietly
			self.views = self.cache["views"]
			self.build_sections()
			self.load_views(quiet=True)
		else:
			self.load_views()

	def load_views(self, quiet=False):
		cl = self.cl

		def fetch():
			if cl.server_version == (0, 0, 0):
				cl.public_info()
			views = cl.views()  # also validates the token
			return views

		def ok(views):
			jfconfig.save_login(cl)
			self["subtitle"].setText("%s  @  %s  (Jellyfin %s)" % (cl.user_name, cl.server_name or cl.server, ".".join(str(x) for x in cl.server_version)))
			changed = [v.get("Id") for v in views] != [v.get("Id") for v in (self.cache["views"] or [])]
			self.views = views
			self.cache["views"] = views
			if changed or not quiet:
				self.build_sections()
			self.prefetch_all(force=quiet)
			self.run(cl.report_capabilities, callback=lambda r: None, errback=lambda e: None, pool="bg")

		def fail(err):
			if getattr(err, "status", None) == 401:
				self.session.openWithCallback(self.relogin, MessageBox, "Die Anmeldung ist abgelaufen oder wurde widerrufen.\nNeu anmelden?", MessageBox.TYPE_YESNO)
			elif not quiet:
				self.build_sections()
				self.show_error(err, "Server nicht erreichbar")
		self.run(fetch, callback=ok, errback=fail, status=None if quiet else "Verbinde mit Server ...")

	def relogin(self, answer):
		self.close("login" if answer else None)

	def build_sections(self):
		rules = [("rule", r.get("name", "?"), r) for r in jfconfig.load_rules() if r.get("home")]
		base = [("resume", "Weiterschauen", None), ("nextup", "Als Nächstes", None), ("latest", "Neu hinzugefügt", None)]
		libs = [("view", v.get("Name", "?"), v) for v in self.views]
		pos = jfconfig.get("rules_first")
		if pos == "top":
			s = rules + base + libs
		elif pos == "after_resume":
			s = base[:1] + rules + base[1:] + libs
		else:
			s = base + libs + rules
		s += [("favorites", "Favoriten", None), ("rules", "Meine Listen", None), ("search", "Suche", None), ("settings", "Einstellungen", None)]
		current = self.current()
		self.sections = s
		rows = []
		for key, title, data in s:
			if key == "view":
				kind = COLLECTION_LABELS.get((data.get("CollectionType") or ""), "")
				rows.append(text_row((key, title, data), title, 520, 66, value=kind, value_width=170, value_color=C_DIM))
			else:
				rows.append(text_row((key, title, data), title, 520, 66))
		self["menu"].setList(rows)
		idx = 0
		if current:
			for i, sec in enumerate(s):
				if self.section_key(sec) == self.section_key(current):
					idx = i
					break
		self["menu"].moveToIndex(idx)
		self.selection_changed()

	# ------------------------------------------------------------- previews
	def current(self):
		cur = self["menu"].getCurrent()
		return cur[0] if cur else None

	@staticmethod
	def section_key(sec):
		key, _title, data = sec
		if key == "view":
			return ("view", data.get("Id"))
		if key == "rule":
			return ("rule", data.get("id"))
		return (key, None)

	def selection_changed(self):
		sec = self.current()
		if not sec:
			return
		self["preview_title"].setText(sec[1])
		cached = self.cache["previews"].get(self.section_key(sec))
		if cached is not None:
			self.show_preview(sec, cached[1])  # instant
		else:
			self.cells.clear_all()
			self["preview_hint"].setText("Lade ..." if sec[0] not in STATIC_KEYS else "")
		self.preview_timer.stop()
		self.preview_timer.start(200, True)

	def show_current(self):
		sec = self.current()
		if not sec:
			return
		if sec[0] in STATIC_KEYS:
			self.cells.clear_all()
			self["backdrop"].hide()
			hints = {"search": "OK: Suchbegriff eingeben (Filme, Serien, Episoden, Musik)",
				"settings": "OK: Wiedergabe, Qualität, Player und Anzeige einstellen",
				"rules": "OK: eigene Listen anlegen, z.B. 'Neue Filme' oder 'Neue Episoden meiner Serien'"}
			self["preview_hint"].setText(hints.get(sec[0], ""))
			return
		cached = self.cache["previews"].get(self.section_key(sec))
		if cached is None or time.time() - cached[0] > CACHE_TTL:
			self.load_preview(sec)

	def fetch_preview(self, sec):
		key, title, data = sec
		cl = self.cl
		if key == "resume":
			return cl.resume(limit=PREVIEW)
		if key == "nextup":
			return cl.next_up(limit=PREVIEW)
		if key == "latest":
			return cl.latest(limit=PREVIEW)
		if key == "favorites":
			return cl.items(filters="IsFavorite", recursive=True, includeItemTypes="Movie,Series,Episode,BoxSet,MusicAlbum",
				sortBy="DateCreated", sortOrder="Descending", limit=PREVIEW, enableTotalRecordCount=False).get("Items") or []
		if key == "rule":
			from .jfrules import run_rule
			return run_rule(cl, data, limit=PREVIEW)
		if key == "view":
			ctype = (data.get("CollectionType") or "").lower()
			if ctype in ("movies", "tvshows", "music", "musicvideos", "homevideos", "mixed", ""):
				items = cl.latest(data["Id"], limit=PREVIEW)
				if items:
					return items
			spec = jfnav.library_spec(data)
			params = dict(spec["params"])
			params.update(sortBy="DateCreated,SortName", sortOrder="Descending", limit=PREVIEW, enableTotalRecordCount=False)
			return cl.items(**params).get("Items") or []
		return []

	def load_preview(self, sec, background=False):
		key = self.section_key(sec)
		if key in self.loading:
			return
		self.loading.add(key)

		def ok(items):
			self.loading.discard(key)
			self.cache["previews"][key] = (time.time(), items)
			cur = self.current()
			if cur and self.section_key(cur) == key:
				self.show_preview(cur, items)

		def fail(err):
			self.loading.discard(key)
			cur = self.current()
			if cur and self.section_key(cur) == key and not background:
				self.cells.clear_all()
				self["preview_hint"].setText("Fehler: %s" % err)
		self.run(self.fetch_preview, sec, callback=ok, errback=fail)

	def prefetch_all(self, force=False):
		"""Load every section preview in the background (current one first)."""
		cur = self.current()
		order = ([cur] if cur else []) + [s for s in self.sections if s is not cur]
		for sec in order:
			if sec[0] in STATIC_KEYS:
				continue
			cached = self.cache["previews"].get(self.section_key(sec))
			if force or cached is None or time.time() - cached[0] > CACHE_TTL:
				self.load_preview(sec, background=sec is not cur)

	def show_preview(self, sec, items):
		for i in range(PREVIEW):
			self.cells.set_item(i, items[i] if i < len(items) else None)
		self["preview_hint"].setText("OK: alle anzeigen" if items else "Keine Einträge")
		self.preview_items = items
		if self.backdrops:
			self.bd_timer.stop()
			self.bd_timer.start(350, True)

	def load_backdrop(self):
		items = getattr(self, "preview_items", None) or []
		if items:
			first = items[0].get("_jf_focus") or items[0]
			self.load_image("backdrop", first, "backdrop", 1280, 720, keep=True)
		else:
			self["backdrop"].hide()

	def invalidate(self):
		for key in list(self.cache["previews"].keys()):
			if key[0] in DYNAMIC:
				del self.cache["previews"][key]
		cur = self.current()
		if cur:
			self.selection_changed()
		self.prefetch_all()

	# ------------------------------------------------------------- keys
	def key_ok(self):
		sec = self.current()
		if not sec:
			return
		if sec[0] == "search":
			self.key_search()
		elif sec[0] == "settings":
			self.key_settings()
		elif sec[0] == "rules":
			self.key_rules()
		elif sec[0] == "rule":
			spec = {"title": sec[1], "source": "rule", "rule": sec[2], "sortable": False}
			jfnav.open_grid(self, spec, callback=lambda *a: self.later(1500, self.invalidate))
		else:
			spec = self.section_spec(sec)
			if spec:
				jfnav.open_grid(self, spec, callback=lambda *a: self.later(1500, self.invalidate))

	def section_spec(self, sec):
		key, title, view = sec
		if key in ("resume", "nextup", "latest"):
			return {"title": title, "source": key}
		if key == "favorites":
			return {"title": title, "source": "items", "sortable": True,
				"params": {"filters": "IsFavorite", "recursive": True, "includeItemTypes": "Movie,Series,Episode,BoxSet,MusicAlbum,MusicVideo,Video"}}
		if key == "view":
			return jfnav.library_spec(view)
		return None

	def key_search(self):
		self.session.openWithCallback(self.search_entered, VirtualKeyBoard, title="Jellyfin durchsuchen", text=self.last_search)

	def search_entered(self, text):
		if text is None:
			return
		text = text.strip()
		if not text:
			return
		self.last_search = text
		jfnav.open_grid(self, {"title": 'Suche: "%s"' % text, "source": "search", "term": text}, callback=lambda *a: self.later(1500, self.invalidate))

	def key_refresh(self):
		self.cache["previews"] = {}
		self.cells.clear_all()
		self.load_views()

	def key_rules(self):
		from .jfrulesui import RulesScreen
		self.session.openWithCallback(self.rules_closed, RulesScreen, self.views)

	def rules_closed(self, *args):
		for key in list(self.cache["previews"].keys()):
			if key[0] == "rule":
				del self.cache["previews"][key]
		self.build_sections()
		self.prefetch_all()

	def key_settings(self):
		from .jfsettings import SettingsScreen
		self.session.openWithCallback(self.settings_closed, SettingsScreen)

	def settings_closed(self, result=None):
		if result == "logout":
			self.do_logout(True)
		elif result == "changed":
			self.backdrops = jfconfig.get_bool("backdrops")
			if not self.backdrops:
				self["backdrop"].hide()
			self.cache["previews"] = {}
			self.build_sections()
			self.prefetch_all()

	def key_logout(self):
		self.session.openWithCallback(self.do_logout, MessageBox, "Von %s abmelden?" % (self.cl.server_name or self.cl.server), MessageBox.TYPE_YESNO, default=False)

	def do_logout(self, answer):
		if not answer:
			return
		cl = self.cl
		self.run(cl.logout, callback=lambda r: None, errback=lambda e: None)
		jfconfig.clear_login()
		_CACHE.update(owner=None, views=None, previews={})
		self.close("login")

	def key_menu(self):
		lst = [
			("Meine Listen verwalten", "rules"),
			("Suche", "search"),
			("Aktualisieren", "refresh"),
			("Einstellungen", "settings"),
			("Bild-Cache leeren", "cache"),
			("Abmelden / Benutzer wechseln", "logout"),
		]
		self.session.openWithCallback(self.menu_chosen, ChoiceBox, title="Jellyfin", list=lst)

	def menu_chosen(self, choice):
		if choice is None:
			return
		a = choice[1]
		if a == "rules":
			self.key_rules()
		elif a == "search":
			self.key_search()
		elif a == "refresh":
			self.key_refresh()
		elif a == "settings":
			self.key_settings()
		elif a == "cache":
			from .jfimages import clear
			self.run(clear, callback=lambda r: self.info("Bild-Cache geleert"), pool="bg")
		elif a == "logout":
			self.key_logout()
