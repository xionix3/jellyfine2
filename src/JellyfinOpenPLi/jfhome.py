# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 xionix
# Jellyfin for Enigma2 - start screen (modern row layout and classic layout)
from __future__ import absolute_import

from .jfi18n import _, N_, current as current_language

import time

from enigma import eTimer

from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox

from . import jfconfig, jfnav
from .jfcommon import CoverCells, JFScreen, make_list, text_row
from .jfrows import Row, RowsScreen, open_library
from .jfrules import rule_name
from .jfskin import C_DIM, COVER_H, COVER_W, HOME_COLS, HOME_ROWS, home_skin

PREVIEW = HOME_COLS * HOME_ROWS
COLLECTION_LABELS = {"movies": N_("Filme"), "tvshows": N_("Serien"), "music": N_("Musik"), "boxsets": N_("Sammlungen"), "playlists": N_("Wiedergabelisten"),
	"homevideos": N_("Videos"), "musicvideos": N_("Musikvideos"), "mixed": N_("Gemischt")}
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


def home_screen_class():
	return HomeScreen if jfconfig.get("home_layout") == "classic" else HeroHomeScreen


# ------------------------------------------------------------------ sections (shared by both layouts)
def all_sections(views):
	rules = [("rule", rule_name(r), r) for r in jfconfig.load_rules() if r.get("home")]
	base = [("resume", _("Weiterschauen"), None), ("nextup", _("Als Nächstes"), None), ("latest", _("Neu hinzugefügt"), None)]
	libs = [("view", v.get("Name", "?"), v) for v in views]
	pos = jfconfig.get("rules_first")
	if pos == "top":
		s = rules + base + libs
	elif pos == "after_resume":
		s = base[:1] + rules + base[1:] + libs
	else:
		s = base + libs + rules
	return s + [("favorites", _("Favoriten"), None), ("rules", _("Meine Listen"), None), ("search", _("Suche"), None), ("settings", _("Einstellungen"), None)]


def section_key(sec):
	key, _title, data = sec
	if key == "view":
		return ("view", data.get("Id"))
	if key == "rule":
		return ("rule", data.get("id"))
	return (key, None)


def fetch_section(cl, sec, limit):
	"""Worker thread: the newest entries of a section."""
	key, title, data = sec
	if key == "resume":
		return cl.resume(limit=limit)
	if key == "nextup":
		return cl.next_up(limit=limit)
	if key == "latest":
		return cl.latest(limit=limit)
	if key == "favorites":
		return cl.items(filters="IsFavorite", recursive=True, includeItemTypes="Movie,Series,Episode,BoxSet,MusicAlbum",
			sortBy="DateCreated", sortOrder="Descending", limit=limit, enableTotalRecordCount=False).get("Items") or []
	if key == "rule":
		from .jfrules import run_rule
		return run_rule(cl, data, limit=limit)
	if key == "view":
		ctype = (data.get("CollectionType") or "").lower()
		if ctype in ("movies", "tvshows", "music", "musicvideos", "homevideos", "mixed", ""):
			items = cl.latest(data["Id"], limit=limit)
			if items:
				return items
		spec = jfnav.library_spec(data)
		params = dict(spec["params"])
		params.update(sortBy="DateCreated,SortName", sortOrder="Descending", limit=limit, enableTotalRecordCount=False)
		return cl.items(**params).get("Items") or []
	return []


def section_spec(sec):
	"""What "show all" opens for a section: a library as rows, everything else as a poster grid."""
	key, title, data = sec
	if key in ("resume", "nextup", "latest"):
		return {"title": title, "source": key}
	if key == "favorites":
		return {"title": title, "source": "items", "sortable": True, "categories": True,
			"params": {"filters": "IsFavorite", "recursive": True, "includeItemTypes": "Movie,Series,Episode,BoxSet,MusicAlbum,MusicVideo,Video"}}
	if key == "view":
		return lambda scr, cb, v=data: open_library(scr, [v], cb)
	if key == "rule":
		return {"title": title, "source": "rule", "rule": data, "sortable": False}
	return None


class HomeShared(object):
	"""Login check, sidebar targets, menu, settings and logout of both start screens."""
	last_search = ""

	def home_start(self):
		self.ui_language = current_language()
		# look for a new plugin version on GitHub (at most every 12 h, setting "update_check")
		self.later(4000, lambda: self.updater().run_check())
		if self.home_cache["views"] is not None:
			# instant start from the cache of the last visit, refresh quietly
			self.views = self.home_cache["views"]
			self.sections_changed()
			self.load_views(quiet=True)
		else:
			self.load_views()

	def updater(self):
		if getattr(self, "jf_updater", None) is None:
			from .jfupdate import Updater
			self.jf_updater = Updater(self)
		return self.jf_updater

	def server_text(self):
		cl = self.cl
		ver = ".".join(str(x) for x in cl.server_version) if cl.server_version != (0, 0, 0) else ""
		return "%s  @  %s%s" % (cl.user_name or "?", cl.server_name or cl.server, (_("  (Jellyfin %s)") % ver) if ver else "")

	def load_views(self, quiet=False):
		cl = self.cl

		def fetch():
			if cl.server_version == (0, 0, 0):
				cl.public_info()
			return cl.views()  # also validates the token

		def ok(views):
			jfconfig.save_login(cl)
			self.show_server()
			changed = [v.get("Id") for v in views] != [v.get("Id") for v in (self.home_cache["views"] or [])]
			self.views = views
			self.home_cache["views"] = views
			if changed or not quiet:
				self.sections_changed()
			self.refresh_previews(force=quiet)
			self.run(cl.report_capabilities, callback=lambda r: None, errback=lambda e: None, pool="bg")

		def fail(err):
			if getattr(err, "status", None) == 401:
				self.session.openWithCallback(self.relogin, MessageBox, _("Die Anmeldung ist abgelaufen oder wurde widerrufen.\nNeu anmelden?"), MessageBox.TYPE_YESNO)
			elif not quiet:
				self.sections_changed()
				self.show_error(err, _("Server nicht erreichbar"))
		self.run(fetch, callback=ok, errback=fail, status=None if quiet else _("Verbinde mit Server ..."))

	def relogin(self, answer=False):
		self.close("login" if answer else None)

	# ------------------------------------------------------------- sidebar targets
	def home_rail(self, key):
		if key == "search":
			self.key_search()
		elif key in ("movies", "tv"):
			views = jfnav.views_of_kind(self.views, key)
			if views:
				open_library(self, views, self.child_closed, "movies" if key == "movies" else "tvshows")
			else:
				self.info(_("Keine Film-Bibliothek auf dem Server") if key == "movies" else _("Keine Serien-Bibliothek auf dem Server"))
		elif key == "lists":
			self.key_rules()
		elif key == "settings":
			self.key_settings()

	def key_search(self):
		jfnav.open_search(self, self.last_search, self.search_done)

	def search_done(self, term=None, result=None):
		if term:
			self.last_search = term
		self.child_closed(result)

	def key_rules(self):
		from .jfrulesui import RulesScreen
		self.session.openWithCallback(self.rules_closed, RulesScreen, self.views)

	def rules_closed(self, *args):
		for key in list(self.home_cache["previews"].keys()):
			if key[0] == "rule":
				del self.home_cache["previews"][key]
		self.sections_changed()
		self.refresh_previews()

	def key_settings(self):
		from .jfsettings import SettingsScreen
		self.session.openWithCallback(self.settings_closed, SettingsScreen)

	def settings_closed(self, result=None):
		if result == "logout":
			self.do_logout(True)
		elif result == "changed":
			if home_screen_class() is not self.__class__ or current_language() != getattr(self, "ui_language", None):
				self.close("relayout")
				return
			self.backdrops = jfconfig.get_bool("backdrops")
			if not self.backdrops:
				self["backdrop"].hide()
			self.home_cache["previews"].clear()
			self.sections_changed()
			self.refresh_previews()

	def key_logout(self):
		self.session.openWithCallback(self.do_logout, MessageBox, _("Von %s abmelden?") % (self.cl.server_name or self.cl.server), MessageBox.TYPE_YESNO, default=False)

	def do_logout(self, answer=False):
		if not answer:
			return
		cl = self.cl
		self.run(cl.logout, callback=lambda r: None, errback=lambda e: None)
		jfconfig.clear_login()
		_CACHE.update(owner=None, views=None, previews={})
		self.close("login")

	def key_menu(self):
		other = _("Klassische Startseite") if self.__class__ is HeroHomeScreen else _("Moderne Startseite")
		lst = [
			(_("Meine Listen verwalten"), "rules"),
			(_("Suche"), "search"),
			(_("Aktualisieren"), "refresh"),
			(_("Einstellungen"), "settings"),
			(_("Ansicht: %s") % other, "layout"),
			(_("Bild-Cache leeren"), "cache"),
			(_("Abmelden / Benutzer wechseln"), "logout"),
			(_("Nach Updates suchen"), "update"),
			(_("Über dieses Plugin"), "about"),
		]
		self.session.openWithCallback(self.menu_chosen, ChoiceBox, title="Jellyfin", list=lst)

	def menu_chosen(self, choice=None):
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
		elif a == "layout":
			jfconfig.set_value("home_layout", "classic" if self.__class__ is HeroHomeScreen else "hero")
			self.close("relayout")
		elif a == "cache":
			from .jfimages import clear
			self.run(clear, callback=lambda r: self.info(_("Bild-Cache geleert")), pool="bg")
		elif a == "logout":
			self.key_logout()
		elif a == "update":
			self.updater().run_check(manual=True)
		elif a == "about":
			from .jfsettings import about_text
			self.session.open(MessageBox, about_text(self.cl), MessageBox.TYPE_INFO)


class HeroHomeScreen(HomeShared, RowsScreen):
	"""Modern layout: backdrop + info of the focused title, one row of cards per section, sidebar."""
	rail_self = "home"
	load_window = -1  # the start screen loads all rows
	drop_empty = True

	def __init__(self, session):
		cl = jfconfig.client()
		self.home_cache = _cache_for(cl)
		self.views = []
		RowsScreen.__init__(self, session, cache=self.home_cache["previews"])

	def brand_text(self):
		return "JELLYFIN"

	def info_text(self):
		return self.server_text()

	def show_server(self):
		self["server"].setText(self.server_text())

	def rows_start(self):
		self.home_start()

	def build_rows(self):
		rows = []
		for sec in all_sections(self.views):
			if sec[0] in STATIC_KEYS:
				continue
			rows.append(Row(section_key(sec), sec[1], lambda cl, n, sec=sec: fetch_section(cl, sec, n), more=section_spec(sec)))
		return rows

	def sections_changed(self):
		self.set_rows(self.build_rows())

	def refresh_previews(self, force=False):
		if force:
			for key, entry in list(self.cache.items()):
				self.cache[key] = (0, entry[1])
		self.ensure_loaded()

	def key_refresh(self):
		self.cache.clear()
		self.shown = None
		self.load_views()

	def rail_action(self, key):
		if key == "home":
			self.go_home()
		else:
			self.home_rail(key)

	def key_search(self):
		HomeShared.key_search(self)

	def key_rules(self):
		HomeShared.key_rules(self)

	def key_settings(self):
		HomeShared.key_settings(self)

	def key_menu(self):
		HomeShared.key_menu(self)


class HomeScreen(HomeShared, JFScreen):
	"""Classic layout: section menu on the left, poster preview on the right."""

	def __init__(self, session):
		JFScreen.__init__(self, session)
		self.skin = home_skin()
		self.skinName = "JellyfinE2Home"
		self.views = []
		self.sections = []
		self.home_cache = _cache_for(self.cl)
		self.loading = set()
		self.preview_items = []
		self.backdrops = jfconfig.get_bool("backdrops")
		self["status"] = Label("")
		self["backdrop"] = Pixmap()
		self["overlay"] = Pixmap()
		self.static_layers["overlay"] = "dim_overlay.png"
		self["title"] = Label("Jellyfin")
		self["subtitle"] = Label("")
		self["menu"] = make_list(fonts=((34,), (24,)), item_height=66)
		self["preview_title"] = Label("")
		self["preview_hint"] = Label("")
		self.cells = CoverCells(self, "p", PREVIEW, COVER_W, COVER_H)
		self.add_keys(red=_("Abmelden"), green=_("Suche"), yellow=_("Aktualisieren"), blue=_("Meine Listen"), hint=_("MENU Optionen"))
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
		self["menu"].onSelectionChanged.append(self.selection_changed)
		self.preview_timer = eTimer()
		self.preview_timer.callback.append(self.show_current)
		self.bd_timer = eTimer()
		self.bd_timer.callback.append(self.load_backdrop)
		self.onLayoutFinish.append(self.start)
		self.onClose.append(self.preview_timer.stop)
		self.onClose.append(self.bd_timer.stop)

	def start(self):
		self["status"].hide()
		self["backdrop"].hide()
		self.cells.clear_all()
		self["subtitle"].setText(self.server_text())
		self.home_start()

	def show_server(self):
		self["subtitle"].setText(self.server_text())

	def current(self):
		cur = self["menu"].getCurrent()
		return cur[0] if cur else None

	def cached(self, sec):
		return self.home_cache["previews"].get(section_key(sec))

	def sections_changed(self):
		current = self.current()
		self.sections = all_sections(self.views)
		idx = 0
		if current:
			for i, sec in enumerate(self.sections):
				if section_key(sec) == section_key(current):
					idx = i
					break
		rows = []
		for sec in self.sections:
			key, title, data = sec
			if key == "view":
				kind = _(COLLECTION_LABELS.get((data.get("CollectionType") or ""), ""))
				rows.append(text_row(sec, title, 520, 66, value=kind, value_width=170, value_color=C_DIM))
			else:
				rows.append(text_row(sec, title, 520, 66))
		self["menu"].setList(rows)
		self["menu"].moveToIndex(idx)
		self.selection_changed()

	def selection_changed(self):
		sec = self.current()
		if not sec:
			return
		self["preview_title"].setText(sec[1])
		cached = self.cached(sec)
		if cached is not None:
			self.show_preview(sec, cached[1])  # instant
		else:
			self.clear_preview(sec)
		self.preview_timer.stop()
		self.preview_timer.start(200, True)

	def show_current(self):
		sec = self.current()
		if not sec or sec[0] in STATIC_KEYS:
			return
		cached = self.cached(sec)
		if cached is None or time.time() - cached[0] > CACHE_TTL:
			self.load_preview(sec)

	def load_preview(self, sec, background=False):
		key = section_key(sec)
		if key in self.loading:
			return
		self.loading.add(key)

		def ok(items):
			self.loading.discard(key)
			self.home_cache["previews"][key] = (time.time(), items)
			cur = self.current()
			if cur and section_key(cur) == key:
				self.show_preview(cur, items)

		def fail(err):
			self.loading.discard(key)
			cur = self.current()
			if cur and section_key(cur) == key and not background:
				self.cells.clear_all()
				self["preview_hint"].setText(_("Fehler: %s") % err)
		self.run(fetch_section, self.cl, sec, PREVIEW, callback=ok, errback=fail)

	def refresh_previews(self, force=False):
		"""Load every section preview in the background (current one first)."""
		cur = self.current()
		order = ([cur] if cur else []) + [s for s in self.sections if s is not cur]
		for sec in order:
			if sec[0] in STATIC_KEYS:
				continue
			cached = self.cached(sec)
			if force or cached is None or time.time() - cached[0] > CACHE_TTL:
				self.load_preview(sec, background=sec is not cur)

	def clear_preview(self, sec):
		self.cells.clear_all()
		self.preview_items = []
		if not sec:
			return
		if sec[0] in STATIC_KEYS:
			hints = {"search": _("OK: Suchbegriff eingeben - Treffer nach Kategorien"),
				"settings": _("OK: Wiedergabe, Qualität, Player und Anzeige einstellen"),
				"rules": _("OK: eigene Listen anlegen, z.B. 'Neue Filme' oder 'Neue Episoden meiner Serien'")}
			self["preview_hint"].setText(hints.get(sec[0], ""))
		else:
			self["preview_hint"].setText(_("Lade ..."))

	def show_preview(self, sec, items):
		for i in range(PREVIEW):
			self.cells.set_item(i, items[i] if i < len(items) else None)
		self["preview_hint"].setText(_("OK: alle anzeigen") if items else _("Keine Einträge"))
		self.preview_items = items
		if self.backdrops:
			self.bd_timer.stop()
			self.bd_timer.start(450, True)

	def load_backdrop(self):
		item = self.preview_items[0] if self.preview_items else None
		if item:
			self.load_image("backdrop", item.get("_jf_focus") or item, "backdrop", 1920, 1080, keep=True)

	def child_closed(self, result=None, *args):
		if isinstance(result, tuple) and result and result[0] == "rail":
			self.home_rail(result[1])
			return
		self.later(1500, self.invalidate)

	def invalidate(self):
		for key, entry in list(self.home_cache["previews"].items()):
			if key[0] in DYNAMIC:
				self.home_cache["previews"][key] = (0, entry[1])
		self.refresh_previews()

	def key_refresh(self):
		self.home_cache["previews"].clear()
		self.clear_preview(self.current())
		self.load_views()

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
		else:
			spec = section_spec(sec)
			if callable(spec):
				spec(self, self.child_closed)
			elif spec:
				jfnav.open_grid(self, spec, callback=self.child_closed)
