# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 xionix
# Jellyfin for Enigma2 - start screen (modern hero layout and classic layout)
from __future__ import absolute_import

import time

from enigma import eTimer

from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox

from . import jfconfig, jfnav
from .jfcommon import CoverCells, JFScreen, hero_meta, make_list, move_widget, play_label, prefetch_posters, set_text_color, text_row
from .jfskin import (C_DIM, C_TEXT, CARD_COUNT, CARD_H, CARD_STEP, CARD_W, CARD_X0, CARD_Y, COVER_H, COVER_W, FRAME_PAD, HERO_RAIL, HOME_COLS,
	HOME_ROWS, RAIL_STEP, RAIL_X, RAIL_Y0, hero_skin, home_skin)
from .jfutil import clean_text

PREVIEW = HOME_COLS * HOME_ROWS
HERO_LIMIT = 20
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


def home_screen_class():
	return HomeScreen if jfconfig.get("home_layout") == "classic" else HeroHomeScreen


class _HomeBase(JFScreen):
	"""Sections (libraries, rows, own lists), preview cache and the shared keys of both layouts."""
	preview_limit = PREVIEW

	def init_common(self):
		self.views = []
		self.sections = []
		self.cache = _cache_for(self.cl)
		self.loading = set()
		self.last_search = ""
		self.preview_items = []
		self.backdrops = jfconfig.get_bool("backdrops")
		self["status"] = Label("")
		self["backdrop"] = Pixmap()
		self.preview_timer = eTimer()
		self.preview_timer.callback.append(self.show_current)
		self.bd_timer = eTimer()
		self.bd_timer.callback.append(self.load_backdrop)
		self.onLayoutFinish.append(self.start)
		self.onClose.append(self.preview_timer.stop)
		self.onClose.append(self.bd_timer.stop)

	# ------------------------------------------------------------- startup
	def start(self):
		self["status"].hide()
		self["backdrop"].hide()
		self.layout_ready()
		# look for a new plugin version on GitHub (at most every 12 h, setting "update_check")
		self.later(4000, lambda: self.updater().run_check())
		if self.cache["views"] is not None:
			# instant start from the cache of the last visit, refresh quietly
			self.views = self.cache["views"]
			self.build_sections()
			self.load_views(quiet=True)
		else:
			self.load_views()

	def layout_ready(self):
		pass

	def updater(self):
		if getattr(self, "jf_updater", None) is None:
			from .jfupdate import Updater
			self.jf_updater = Updater(self)
		return self.jf_updater

	def server_text(self):
		cl = self.cl
		ver = ".".join(str(x) for x in cl.server_version) if cl.server_version != (0, 0, 0) else ""
		return "%s  @  %s%s" % (cl.user_name or "?", cl.server_name or cl.server, ("  (Jellyfin %s)" % ver) if ver else "")

	def load_views(self, quiet=False):
		cl = self.cl

		def fetch():
			if cl.server_version == (0, 0, 0):
				cl.public_info()
			return cl.views()  # also validates the token

		def ok(views):
			jfconfig.save_login(cl)
			self.show_server()
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

	def show_server(self):
		pass

	def relogin(self, answer=False):
		self.close("login" if answer else None)

	def all_sections(self):
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
		return s + [("favorites", "Favoriten", None), ("rules", "Meine Listen", None), ("search", "Suche", None), ("settings", "Einstellungen", None)]

	def build_sections(self):
		current = self.current()
		self.sections = self.all_sections()
		idx = 0
		if current:
			for i, sec in enumerate(self.sections):
				if self.section_key(sec) == self.section_key(current):
					idx = i
					break
		self.show_sections(idx)

	@staticmethod
	def section_key(sec):
		key, _title, data = sec
		if key == "view":
			return ("view", data.get("Id"))
		if key == "rule":
			return ("rule", data.get("id"))
		return (key, None)

	def cached(self, sec):
		return self.cache["previews"].get(self.section_key(sec))

	# ------------------------------------------------------------- previews
	def selection_changed(self):
		sec = self.current()
		if not sec:
			return
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

	def fetch_preview(self, sec):
		key, title, data = sec
		cl = self.cl
		limit = self.preview_limit
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

	def load_preview(self, sec, background=False):
		key = self.section_key(sec)
		if key in self.loading:
			return
		self.loading.add(key)

		def ok(items):
			self.loading.discard(key)
			self.cache["previews"][key] = (time.time(), items)
			self.preview_loaded(key, items)

		def fail(err):
			self.loading.discard(key)
			cur = self.current()
			if cur and self.section_key(cur) == key and not background:
				self.preview_failed(cur, err)
		self.run(self.fetch_preview, sec, callback=ok, errback=fail)

	def preview_loaded(self, key, items):
		cur = self.current()
		if cur and self.section_key(cur) == key:
			self.show_preview(cur, items)

	def prefetch_all(self, force=False):
		"""Load every section preview in the background (current one first)."""
		cur = self.current()
		order = ([cur] if cur else []) + [s for s in self.sections if s is not cur]
		for sec in order:
			if sec[0] in STATIC_KEYS:
				continue
			cached = self.cached(sec)
			if force or cached is None or time.time() - cached[0] > CACHE_TTL:
				self.load_preview(sec, background=sec is not cur)

	def schedule_backdrop(self, delay=350):
		if self.backdrops:
			self.bd_timer.stop()
			self.bd_timer.start(delay, True)

	def backdrop_item(self):
		items = self.preview_items or []
		return items[0] if items else None

	def load_backdrop(self):
		item = self.backdrop_item()
		if item and not item.get("_jf_more"):
			self.load_image("backdrop", item.get("_jf_focus") or item, "backdrop", 1280, 720, keep=True)
		else:
			self["backdrop"].hide()

	def invalidate(self):
		"""Data may have changed (played, favourites ...): reload dynamic rows, keep showing the old ones meanwhile."""
		for key, entry in list(self.cache["previews"].items()):
			if key[0] in DYNAMIC:
				self.cache["previews"][key] = (0, entry[1])
		self.prefetch_all()

	def child_closed(self, *args):
		self.later(1500, self.invalidate)

	# ------------------------------------------------------------- shared keys
	def section_spec(self, sec):
		key, title, data = sec
		if key in ("resume", "nextup", "latest"):
			return {"title": title, "source": key}
		if key == "favorites":
			return {"title": title, "source": "items", "sortable": True, "categories": True,
				"params": {"filters": "IsFavorite", "recursive": True, "includeItemTypes": "Movie,Series,Episode,BoxSet,MusicAlbum,MusicVideo,Video"}}
		if key == "view":
			return jfnav.library_spec(data)
		if key == "rule":
			return {"title": title, "source": "rule", "rule": data, "sortable": False}
		return None

	def open_section(self, sec):
		if sec[0] == "search":
			self.key_search()
		elif sec[0] == "settings":
			self.key_settings()
		elif sec[0] == "rules":
			self.key_rules()
		else:
			spec = self.section_spec(sec)
			if spec:
				jfnav.open_grid(self, spec, callback=self.child_closed)

	def key_search(self):
		jfnav.open_search(self, self.last_search, self.search_done)

	def search_done(self, term=None):
		if term:
			self.last_search = term
		self.child_closed()

	def key_refresh(self):
		self.cache["previews"] = {}
		self.clear_preview(self.current())
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
			if home_screen_class() is not self.__class__:
				self.close("relayout")
				return
			self.backdrops = jfconfig.get_bool("backdrops")
			if not self.backdrops:
				self["backdrop"].hide()
			self.cache["previews"] = {}
			self.build_sections()
			self.prefetch_all()

	def key_logout(self):
		self.session.openWithCallback(self.do_logout, MessageBox, "Von %s abmelden?" % (self.cl.server_name or self.cl.server), MessageBox.TYPE_YESNO, default=False)

	def do_logout(self, answer=False):
		if not answer:
			return
		cl = self.cl
		self.run(cl.logout, callback=lambda r: None, errback=lambda e: None)
		jfconfig.clear_login()
		_CACHE.update(owner=None, views=None, previews={})
		self.close("login")

	def key_menu(self):
		other = "Klassische Startseite" if self.__class__ is HeroHomeScreen else "Moderne Startseite"
		lst = [
			("Meine Listen verwalten", "rules"),
			("Suche", "search"),
			("Aktualisieren", "refresh"),
			("Einstellungen", "settings"),
			("Ansicht: %s" % other, "layout"),
			("Bild-Cache leeren", "cache"),
			("Abmelden / Benutzer wechseln", "logout"),
			("Nach Updates suchen", "update"),
			("Über dieses Plugin", "about"),
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
			self.run(clear, callback=lambda r: self.info("Bild-Cache geleert"), pool="bg")
		elif a == "logout":
			self.key_logout()
		elif a == "update":
			self.updater().run_check(manual=True)
		elif a == "about":
			from .jfsettings import about_text
			self.session.open(MessageBox, about_text(self.cl), MessageBox.TYPE_INFO)


class HomeScreen(_HomeBase):
	"""Classic layout: section menu on the left, poster preview on the right."""

	def __init__(self, session):
		JFScreen.__init__(self, session)
		self.skin = home_skin()
		self.skinName = "JellyfinE2Home"
		self.init_common()
		self["title"] = Label("Jellyfin")
		self["subtitle"] = Label("")
		self["menu"] = make_list(fonts=((34,), (24,)), item_height=66)
		self["preview_title"] = Label("")
		self["preview_hint"] = Label("")
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
		self["menu"].onSelectionChanged.append(self.selection_changed)

	def layout_ready(self):
		self.cells.clear_all()
		self["subtitle"].setText(self.server_text())

	def show_server(self):
		self["subtitle"].setText(self.server_text())

	def current(self):
		cur = self["menu"].getCurrent()
		return cur[0] if cur else None

	def show_sections(self, idx):
		rows = []
		for sec in self.sections:
			key, title, data = sec
			if key == "view":
				kind = COLLECTION_LABELS.get((data.get("CollectionType") or ""), "")
				rows.append(text_row(sec, title, 520, 66, value=kind, value_width=170, value_color=C_DIM))
			else:
				rows.append(text_row(sec, title, 520, 66))
		self["menu"].setList(rows)
		self["menu"].moveToIndex(idx)
		self.selection_changed()

	def selection_changed(self):
		sec = self.current()
		if sec:
			self["preview_title"].setText(sec[1])
		_HomeBase.selection_changed(self)

	def clear_preview(self, sec):
		self.cells.clear_all()
		self.preview_items = []
		if not sec:
			return
		if sec[0] in STATIC_KEYS:
			self["backdrop"].hide()
			hints = {"search": "OK: Suchbegriff eingeben, danach nach Kategorie einschränken",
				"settings": "OK: Wiedergabe, Qualität, Player und Anzeige einstellen",
				"rules": "OK: eigene Listen anlegen, z.B. 'Neue Filme' oder 'Neue Episoden meiner Serien'"}
			self["preview_hint"].setText(hints.get(sec[0], ""))
		else:
			self["preview_hint"].setText("Lade ...")

	def preview_failed(self, sec, err):
		self.cells.clear_all()
		self["preview_hint"].setText("Fehler: %s" % err)

	def show_preview(self, sec, items):
		for i in range(PREVIEW):
			self.cells.set_item(i, items[i] if i < len(items) else None)
		self["preview_hint"].setText("OK: alle anzeigen" if items else "Keine Einträge")
		self.preview_items = items
		self.schedule_backdrop()

	def key_ok(self):
		sec = self.current()
		if sec:
			self.open_section(sec)


class HeroHomeScreen(_HomeBase):
	"""Modern layout: large backdrop + title of the focused item, a row of 16:9 cards per section, icon rail on the left."""
	preview_limit = HERO_LIMIT

	def __init__(self, session):
		JFScreen.__init__(self, session)
		self.skin = hero_skin()
		self.skinName = "JellyfinE2Hero"
		self.init_common()
		self.row = 0
		self.card = 0
		self.first = 0
		self.mode = "rows"
		self.rail = 1
		self.row_items = []
		for name in ("brand", "server", "hero_title", "hero_meta", "hero_genres", "hero_overview", "hero_pill1", "hero_pill2",
				"row_title", "row_count", "next_row", "more_rows"):
			self[name] = Label("")
		for name in ("hero_new", "rail_sel", "rail_shade", "frame", "hero_pillbg1", "hero_pillbg2", "hero_icon1", "hero_icon2"):
			self[name] = Pixmap()
		for i, (_key, title) in enumerate(HERO_RAIL):
			self["rail_name%d" % i] = Label(title)
		self.cells = CoverCells(self, "c", CARD_COUNT, CARD_W, CARD_H, kind="landscape")
		self.add_keys(red="Alle anzeigen", green="Suche", yellow="Aktualisieren", blue="Meine Listen", hint="OK Details   ▶ Abspielen   MENU Optionen")
		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ColorActions", "MenuActions", "ChannelSelectBaseActions",
			"EPGSelectActions", "InfobarSeekActions"], {
			"ok": self.key_ok,
			"cancel": self.key_cancel,
			"up": lambda: self.key_vertical(-1),
			"down": lambda: self.key_vertical(1),
			"upRepeated": lambda: self.key_vertical(-1),
			"downRepeated": lambda: self.key_vertical(1),
			"left": lambda: self.key_horizontal(-1),
			"right": lambda: self.key_horizontal(1),
			"leftRepeated": lambda: self.key_horizontal(-1),
			"rightRepeated": lambda: self.key_horizontal(1),
			"nextBouquet": lambda: self.key_horizontal(CARD_COUNT),
			"prevBouquet": lambda: self.key_horizontal(-CARD_COUNT),
			"red": self.key_all,
			"green": self.key_search,
			"yellow": self.key_refresh,
			"blue": self.key_rules,
			"menu": self.key_menu,
			"info": self.key_info,
			"playpauseService": self.key_play,
			"unPauseService": self.key_play,
		}, -1)

	# ------------------------------------------------------------- layout
	def layout_ready(self):
		self.cells.clear_all()
		self["brand"].setText("JELLYFIN")
		self["server"].setText(self.server_text())
		self["hero_pill2"].setText("Details")
		self.show_rail(False)
		self["hero_new"].hide()
		self.clear_hero("Lade ...")

	def show_server(self):
		self["server"].setText(self.server_text())

	def all_sections(self):
		return [s for s in _HomeBase.all_sections(self) if s[0] not in STATIC_KEYS]

	def current(self):
		if 0 <= self.row < len(self.sections):
			return self.sections[self.row]
		return None

	def show_sections(self, idx):
		self.row = idx
		self.card = 0
		self.first = 0
		self.selection_changed()

	def update_row_labels(self):
		sec = self.current()
		self["row_title"].setText(sec[1] if sec else "")
		nxt = self.sections[self.row + 1:]
		self["next_row"].setText(nxt[0][1] if nxt else "")
		self["more_rows"].setText("   ·   ".join(s[1] for s in nxt[1:5]))
		real = [it for it in self.row_items if not it.get("_jf_more")]
		self["row_count"].setText("%d / %d" % (min(self.card + 1, len(real)), len(real)) if real and self.card < len(real) else "")

	def selection_changed(self):
		self.update_row_labels()
		_HomeBase.selection_changed(self)

	def clear_preview(self, sec):
		self.row_items = []
		self.preview_items = []
		self.cells.clear_all()
		self["frame"].hide()
		self.clear_hero("Lade ..." if sec else "")
		self.update_row_labels()

	def preview_failed(self, sec, err):
		self.clear_preview(None)
		self.clear_hero("Fehler: %s" % err)

	def clear_hero(self, text=""):
		sec = self.current()
		self["hero_title"].setText(sec[1] if sec else "")
		self["hero_meta"].setText("")
		self["hero_genres"].setText("")
		self["hero_overview"].setText(text)
		self["hero_pill1"].setText("Öffnen")
		self["hero_new"].hide()
		move_widget(self, "hero_meta", 160, 206)

	def show_preview(self, sec, items):
		self.row_items = list(items)
		if items:
			self.row_items.append({"_jf_more": True, "Name": "Alle anzeigen", "Id": None})
		self.preview_items = self.row_items
		self.card = max(0, min(self.card, len(self.row_items) - 1))
		self.draw_cards()
		prefetch_posters(self, items, CARD_W, CARD_H, kind="landscape")

	def draw_cards(self):
		n = len(self.row_items)
		if self.card < self.first:
			self.first = self.card
		elif self.card >= self.first + CARD_COUNT:
			self.first = self.card - CARD_COUNT + 1
		self.first = max(0, min(self.first, max(0, n - CARD_COUNT)))
		for i in range(CARD_COUNT):
			idx = self.first + i
			self.cells.set_item(i, self.row_items[idx] if idx < n else None)
		if n and self.mode == "rows":
			move_widget(self, "frame", CARD_X0 + (self.card - self.first) * CARD_STEP - FRAME_PAD, CARD_Y - FRAME_PAD)
			self["frame"].show()
		else:
			self["frame"].hide()
		self.update_hero()
		self.update_row_labels()

	def focused(self):
		if self.mode == "rows" and 0 <= self.card < len(self.row_items):
			return self.row_items[self.card]
		return None

	def backdrop_item(self):
		it = self.focused()
		if it is None and self.row_items:
			it = self.row_items[0]
		return it

	def update_hero(self):
		it = self.focused() or (self.row_items[0] if self.row_items else None)
		sec = self.current()
		if it is None:
			self.clear_hero("Keine Einträge" if sec and self.cached(sec) is not None else "Lade ...")
			self["backdrop"].hide()
			return
		if it.get("_jf_more"):
			real = len(self.row_items) - 1
			self["hero_title"].setText(sec[1] if sec else "")
			self["hero_meta"].setText("")
			self["hero_new"].hide()
			move_widget(self, "hero_meta", 160, 206)
			self["hero_genres"].setText("")
			self["hero_overview"].setText("OK: alle Titel von '%s' anzeigen (hier die neuesten %d)." % (sec[1] if sec else "", real))
			self["hero_pill1"].setText("Alle anzeigen")
			self.schedule_backdrop(150)
			return
		t = it.get("Type")
		title = it.get("SeriesName") if t == "Episode" and it.get("SeriesName") else it.get("Name", "")
		focus = it.get("_jf_focus")
		meta, new = hero_meta(it)
		self["hero_title"].setText(title or "")
		self["hero_meta"].setText(meta)
		if new:
			self["hero_new"].show()
			move_widget(self, "hero_meta", 236, 206)
		else:
			self["hero_new"].hide()
			move_widget(self, "hero_meta", 160, 206)
		self["hero_genres"].setText(", ".join((it.get("Genres") or [])[:4]))
		overview = clean_text((focus or it).get("Overview") or it.get("Overview") or "")
		self["hero_overview"].setText(overview)
		self["hero_pill1"].setText(play_label(it))
		if self.mode == "rail":
			self["hero_new"].hide()
		self.schedule_backdrop()

	# ------------------------------------------------------------- navigation
	def key_vertical(self, step):
		if self.mode == "rail":
			self.rail = (self.rail + step) % len(HERO_RAIL)
			self.draw_rail()
			return
		if not self.sections:
			return
		row = self.row + step
		# skip rows that are known to be empty
		while 0 <= row < len(self.sections):
			c = self.cached(self.sections[row])
			if c is None or c[1]:
				break
			row += step
		if not 0 <= row < len(self.sections):
			return
		self.row = row
		self.card = 0
		self.first = 0
		self.selection_changed()

	def key_horizontal(self, step):
		if self.mode == "rail":
			if step > 0:
				self.leave_rail()
			return
		if step < 0 and self.card == 0:
			self.enter_rail()
			return
		n = len(self.row_items)
		if not n:
			return
		self.card = max(0, min(n - 1, self.card + step))
		self.draw_cards()

	HERO_WIDGETS = ("hero_title", "hero_meta", "hero_genres", "hero_overview", "hero_pill1", "hero_pill2", "hero_pillbg1", "hero_pillbg2",
		"hero_icon1", "hero_icon2")

	def show_rail(self, on):
		"""Expanded sidebar: names next to the icons, hero text hidden underneath."""
		for i in range(len(HERO_RAIL)):
			w = self["rail_name%d" % i]
			w.show() if on else w.hide()
		for name in ("rail_sel", "rail_shade"):
			self[name].show() if on else self[name].hide()
		for name in self.HERO_WIDGETS:
			self[name].hide() if on else self[name].show()
		if on:
			self["hero_new"].hide()

	def enter_rail(self, idx=1):
		self.mode = "rail"
		self.rail = idx
		self["frame"].hide()
		self.show_rail(True)
		self.draw_rail()

	def leave_rail(self):
		self.mode = "rows"
		self.show_rail(False)
		self.draw_cards()

	def draw_rail(self):
		y = RAIL_Y0 + self.rail * RAIL_STEP
		move_widget(self, "rail_sel", RAIL_X - 14, y - 14)
		for i in range(len(HERO_RAIL)):
			set_text_color(self, "rail_name%d" % i, C_TEXT if i == self.rail else C_DIM)

	def key_cancel(self):
		if self.mode == "rail":
			self.leave_rail()
		elif self.row > 0 or self.card > 0:
			self.row = 0
			self.card = 0
			self.first = 0
			self.selection_changed()
		else:
			self.close()

	def key_ok(self):
		if self.mode == "rail":
			self.rail_action(HERO_RAIL[self.rail][0])
			return
		it = self.focused()
		if it is None:
			return
		if it.get("_jf_more"):
			self.key_all()
		else:
			jfnav.open_item(self, it, self.row_items[:-1], self.card, callback=self.child_closed)

	def key_info(self):
		it = self.focused()
		if it is not None and not it.get("_jf_more"):
			jfnav.open_detail(self, it.get("_jf_focus") or it, self.child_closed)

	def key_play(self):
		it = self.focused()
		if it is None or it.get("_jf_more"):
			self.key_ok()
			return
		if play_label(it) == "Öffnen":
			self.key_ok()
			return
		from .jfplayer import play_item
		play_item(self, it, [x for x in self.row_items if not x.get("_jf_more")], self.card, on_finished=self.child_closed)

	def key_all(self):
		sec = self.current()
		if sec:
			self.open_section(sec)

	def rail_action(self, key):
		if key == "search":
			self.key_search()
		elif key == "home":
			self.leave_rail()
			self.row = 0
			self.card = 0
			self.selection_changed()
		elif key in ("movies", "tv"):
			want = "movies" if key == "movies" else "tvshows"
			views = [v for v in self.views if (v.get("CollectionType") or "").lower() == want]
			if not views:
				self.info("Keine %s-Bibliothek auf dem Server" % ("Film" if key == "movies" else "Serien"))
			elif len(views) == 1:
				jfnav.open_grid(self, jfnav.library_spec(views[0]), callback=self.child_closed)
			else:
				self.session.openWithCallback(self.view_chosen, ChoiceBox, title=HERO_RAIL[self.rail][1], list=[(v.get("Name", "?"), v) for v in views])
		elif key == "lists":
			self.key_rules()
		elif key == "settings":
			self.key_settings()

	def view_chosen(self, choice=None):
		if choice:
			jfnav.open_grid(self, jfnav.library_spec(choice[1]), callback=self.child_closed)
