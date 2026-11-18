# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 xionix
# Jellyfin for Enigma2 - poster grid (libraries, search results, collections ...)
from __future__ import absolute_import

import time

from enigma import eTimer

from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Screens.ChoiceBox import ChoiceBox

from . import jfconfig
from .jfcommon import CoverCells, JFScreen, move_widget, prefetch_posters
from .jfskin import COVER_H, COVER_W, FRAME_PAD, GRID_COLS, GRID_ROWS, cell_pos, grid_skin
from .jfutil import (clean_text, display_title, episode_code, fmt_rating, fmt_runtime, is_favorite, is_new, is_played, parse_date,
	resume_ticks, ticks_to_seconds, fmt_clock)
from .jflog import log

SORTS = [
	("SortName", "Ascending", "Name (A-Z)"),
	("SortName", "Descending", "Name (Z-A)"),
	("DateCreated,SortName", "Descending", "Zuletzt hinzugefügt"),
	("PremiereDate,ProductionYear,SortName", "Descending", "Erscheinungsdatum"),
	("CommunityRating,SortName", "Descending", "Bewertung"),
	("DatePlayed,SortName", "Descending", "Zuletzt gesehen"),
	("Runtime,SortName", "Ascending", "Laufzeit"),
	("Random", "Ascending", "Zufällig"),
]

FILTERS = [
	(None, "Alle"),
	("IsUnplayed", "Ungesehen"),
	("IsPlayed", "Gesehen"),
	("IsFavorite", "Favoriten"),
	("IsResumable", "Begonnen"),
]

# (includeItemTypes, label) - restrict mixed lists and search results to one kind of item
CATEGORIES = [
	(None, "Alle"),
	("Movie", "Filme"),
	("Series", "Serien"),
	("Episode", "Episoden"),
	("BoxSet", "Sammlungen"),
	("MusicAlbum,Audio,MusicArtist,MusicVideo", "Musik"),
	("Video", "Videos"),
	("Person", "Personen"),
]
CLIENT_SIDE = ("resume", "latest", "rule", "similar", "static", "nextup")


def in_category(item, types):
	return not types or item.get("Type") in types.split(",")


def count_categories(items):
	counts = {}
	for types, _label in CATEGORIES[1:]:
		counts[types] = sum(1 for it in items if in_category(it, types))
	counts[None] = len(items)
	return counts


PAGE = GRID_COLS * GRID_ROWS
CHUNK = PAGE * 6


def item_meta(item):
	parts = []
	t = item.get("Type")
	if item.get("_jf_new_count"):
		n = item["_jf_new_count"]
		parts.append("%d neue Folge%s" % (n, "n" if n > 1 else ""))
	elif is_new(item, jfconfig.get_int("new_days", 7)):
		ts = parse_date(item.get("DateLastMediaAdded") if t in ("Series", "Season") else item.get("DateCreated"))
		parts.append("NEU (%s)" % time.strftime("%d.%m.", time.localtime(ts)) if ts else "NEU")
	if t == "Episode":
		code = episode_code(item)
		if code:
			parts.append(code)
	if item.get("ProductionYear") and t != "Episode":
		parts.append(str(item["ProductionYear"]))
	rt = fmt_runtime(item.get("RunTimeTicks"))
	if rt and t not in ("Series", "BoxSet", "MusicAlbum", "Folder"):
		parts.append(rt)
	if item.get("OfficialRating"):
		parts.append(item["OfficialRating"])
	r = fmt_rating(item.get("CommunityRating"))
	if r:
		parts.append("Bewertung %s" % r)
	if t in ("Series", "Season", "BoxSet", "MusicAlbum", "Folder") and item.get("ChildCount"):
		label = {"Series": "Staffeln", "Season": "Episoden", "MusicAlbum": "Titel"}.get(t, "Einträge")
		parts.append("%s %s" % (item["ChildCount"], label))
	if item.get("Genres"):
		parts.append(", ".join(item["Genres"][:3]))
	pos = resume_ticks(item)
	if pos and not is_played(item):
		parts.append("fortsetzen bei %s" % fmt_clock(ticks_to_seconds(pos)))
	if is_played(item):
		parts.append("gesehen")
	if is_favorite(item):
		parts.append("Favorit")
	return "  |  ".join(parts)


class GridScreen(JFScreen):
	def __init__(self, session, spec):
		JFScreen.__init__(self, session)
		self.skin = grid_skin()
		self.skinName = "JellyfinE2Grid"
		self.spec = spec
		self.entries = []
		self.total = 0
		self.index = 0
		self.page = -1
		self.loading = False
		self.generation = 0
		sort = spec.get("sort", 0)
		if not isinstance(sort, int):  # sort by name of the field, e.g. "DateCreated"
			sort = next((i for i, srt in enumerate(SORTS) if srt[0].split(",")[0] == sort), 0)
		self.sort_idx = sort
		self.filter_idx = 0
		self.genre = None
		self.category = None
		self.cat_counts = None
		self["title"] = Label(spec.get("title", ""))
		self["subtitle"] = Label("")
		self["pageinfo"] = Label("")
		self["info_title"] = Label("")
		self["info_meta"] = Label("")
		self["info_overview"] = Label("")
		self["frame"] = Pixmap()
		self["status"] = Label("")
		self["backdrop"] = Pixmap()
		self["overlay"] = Pixmap()
		self.static_layers["overlay"] = "dim_overlay.png"
		self.backdrops = jfconfig.get_bool("backdrops")
		self.bd_timer = eTimer()
		self.bd_timer.callback.append(self.load_backdrop)
		self.onClose.append(self.bd_timer.stop)
		self.cells = CoverCells(self, "", PAGE, COVER_W, COVER_H)
		sortable = spec.get("source") == "items" and spec.get("sortable", True)
		green = "Filter" if sortable else ("Kategorie" if self.has_categories() else "")
		self.add_keys(red="Sortierung" if sortable else "", green=green, yellow="Gesehen +/-", blue="Favorit +/-",
			hint="MENU Optionen  |  CH+/- Seite  |  PLAY")
		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ColorActions", "MenuActions", "ChannelSelectBaseActions",
			"EPGSelectActions", "InfobarSeekActions"], {
			"ok": self.key_ok,
			"cancel": self.close,
			"up": self.key_up,
			"down": self.key_down,
			"left": self.key_left,
			"right": self.key_right,
			"upRepeated": self.key_up,
			"downRepeated": self.key_down,
			"leftRepeated": self.key_left,
			"rightRepeated": self.key_right,
			"nextBouquet": self.key_page_down,
			"prevBouquet": self.key_page_up,
			"red": self.key_red,
			"green": self.key_green,
			"yellow": self.key_yellow,
			"blue": self.key_blue,
			"menu": self.key_menu,
			"info": self.key_info,
			"playpauseService": self.key_play,
			"unPauseService": self.key_play,
		}, -1)
		self.onLayoutFinish.append(self.start)

	# ------------------------------------------------------------- loading
	def start(self):
		self.cells.clear_all()
		self["backdrop"].hide()
		self["frame"].hide()
		self["status"].hide()
		self.reload()

	def reload(self, keep_index=False):
		self.generation += 1
		old_index = self.index
		self.entries = []
		self.total = 0
		self.page = -1
		self.loading = False
		self.index = old_index if keep_index else 0
		self.load_more(first=True)

	def build_params(self, start):
		params = dict(self.spec.get("params") or {})
		if self.spec.get("sortable", True):
			sort_by, order, _label = SORTS[self.sort_idx]
			if params.get("sortBy", "").startswith("IsFolder") and self.sort_idx == 0:
				sort_by = params["sortBy"]
			params["sortBy"] = sort_by
			params["sortOrder"] = order
		f = FILTERS[self.filter_idx][0]
		if f:
			params["filters"] = f
		if self.genre:
			params["genreIds"] = self.genre[0]
		if self.category:
			params["includeItemTypes"] = self.category
			params.setdefault("recursive", True)
		params["startIndex"] = start
		params["limit"] = CHUNK
		return params

	def fetch(self, start):
		"""Worker thread: returns (items, total, category counts or None)."""
		src = self.spec.get("source")
		cl = self.cl
		cat = self.category
		if src == "items":
			res = cl.items(**self.build_params(start))
			return res.get("Items") or [], res.get("TotalRecordCount"), None
		if src == "search":
			term = self.spec["term"]
			if cat == "Person":
				items = cl.search_people(term)
			elif cat:
				items = cl.search(term, types=cat)
			else:
				from .jfutil import rank_search
				try:
					people = cl.search_people(term)
				except Exception as e:
					log("person search failed: %s" % e)
					people = []
				items = rank_search(term, cl.search(term) + people)
				return items, len(items), count_categories(items)
			return items, len(items), None
		if src == "resume":
			items = cl.resume(limit=100)
		elif src == "nextup":
			items = cl.next_up(limit=100)
		elif src == "latest":
			items = cl.latest(self.spec.get("parent_id"), limit=100)
		elif src == "similar":
			items = cl.similar(self.spec["item_id"], limit=60)
		elif src == "static":
			items = list(self.spec.get("items") or [])
		elif src == "rule":
			from .jfrules import run_rule
			items = run_rule(cl, self.spec["rule"])
		else:
			items = []
		counts = count_categories(items)
		items = [it for it in items if in_category(it, cat)]
		return items, len(items), counts

	def load_more(self, first=False):
		if self.loading:
			return
		if not first and (self.spec.get("source") != "items" or len(self.entries) >= self.total):
			return
		self.loading = True
		gen = self.generation
		start = len(self.entries)

		def ok(res):
			if gen != self.generation:
				return
			self.loading = False
			items, total, counts = res
			if counts is not None:
				self.cat_counts = counts
			self.entries.extend(items)
			self.total = total if total is not None else len(self.entries)
			if self.spec.get("source") != "items" or len(items) == 0:
				self.total = len(self.entries)
			if not self.entries:
				self.cells.clear_all()
				self["frame"].hide()
				self.set_info(None)
				self.update_header()
				self.set_status("Keine Einträge gefunden" + ("\n(Kategorie: %s - GRÜN wechselt)" % self.category_label() if self.category else ""))
				return
			self.set_status(None)
			self.index = min(self.index, len(self.entries) - 1)
			self.page = -1
			self.refresh()

		def fail(err):
			if gen != self.generation:
				return
			self.loading = False
			self.set_status(None)
			self.show_error(err)
		self.run(self.fetch, start, callback=ok, errback=fail, status="Lade ..." if first else None)

	# ------------------------------------------------------------- drawing
	def update_header(self):
		parts = ["%d Titel" % self.total]
		if self.category:
			parts.append("Kategorie: %s" % self.category_label())
		if self.spec.get("source") == "items" and self.spec.get("sortable", True):
			parts.append("Sortierung: %s" % SORTS[self.sort_idx][2])
			if self.filter_idx:
				parts.append("Filter: %s" % FILTERS[self.filter_idx][1])
			if self.genre:
				parts.append("Genre: %s" % self.genre[1])
		self["subtitle"].setText("  |  ".join(parts))
		pages = max(1, (self.total + PAGE - 1) // PAGE)
		self["pageinfo"].setText("Seite %d / %d" % (self.index // PAGE + 1, pages) if self.total else "")

	def refresh(self):
		if not self.entries:
			return
		page = self.index // PAGE
		if page != self.page:
			self.page = page
			start = page * PAGE
			for i in range(PAGE):
				idx = start + i
				self.cells.set_item(i, self.entries[idx] if idx < len(self.entries) else None)
		cell = self.index - self.page * PAGE
		x, y = cell_pos(cell)
		move_widget(self, "frame", x - FRAME_PAD, y - FRAME_PAD)
		self["frame"].show()
		self.set_info(self.current())
		self.update_header()
		if self.backdrops:
			self.bd_timer.stop()
			self.bd_timer.start(450, True)
		# warm the poster cache for the next page so paging feels instant
		nxt = (self.page + 1) * PAGE
		if nxt < len(self.entries):
			prefetch_posters(self, self.entries[nxt:nxt + PAGE], COVER_W, COVER_H)
		# prefetch next chunk
		if self.spec.get("source") == "items" and len(self.entries) < self.total and self.index >= len(self.entries) - 2 * PAGE:
			self.load_more()

	def load_backdrop(self):
		item = self.current()
		if item:
			self.load_image("backdrop", item.get("_jf_focus") or item, "backdrop", 1920, 1080, keep=True)

	def redraw_page(self):
		self.page = -1
		self.refresh()

	def set_info(self, item):
		if not item:
			self["info_title"].setText("")
			self["info_meta"].setText("")
			self["info_overview"].setText("")
			return
		title = item.get("Name") or ""
		if item.get("Type") == "Episode" and item.get("SeriesName"):
			title = "%s - %s" % (item["SeriesName"], title)
		self["info_title"].setText(title)
		self["info_meta"].setText(item_meta(item))
		text = clean_text(item.get("Overview"))
		if len(text) > 330:
			text = text[:327].rsplit(" ", 1)[0] + " ..."
		self["info_overview"].setText(text.replace("\n", " "))

	def current(self):
		if 0 <= self.index < len(self.entries):
			return self.entries[self.index]
		return None

	def move_to(self, idx):
		if not self.entries:
			return
		known = max(len(self.entries), 1)
		idx = max(0, min(idx, known - 1))
		if idx != self.index:
			self.index = idx
			self.refresh()

	# ------------------------------------------------------------- keys
	def key_left(self):
		self.move_to(self.index - 1)

	def key_right(self):
		self.move_to(self.index + 1)

	def key_up(self):
		if self.index - GRID_COLS >= 0:
			self.move_to(self.index - GRID_COLS)

	def key_down(self):
		n = len(self.entries)
		target = self.index + GRID_COLS
		if target < n:
			self.move_to(target)
		elif self.index // GRID_COLS < (n - 1) // GRID_COLS:
			self.move_to(n - 1)

	def key_page_down(self):
		self.move_to(min(len(self.entries) - 1, (self.index // PAGE + 1) * PAGE + self.index % PAGE))

	def key_page_up(self):
		self.move_to(max(0, self.index - PAGE))

	def key_ok(self):
		item = self.current()
		if item:
			from .jfnav import open_item
			open_item(self, item, self.entries, self.index, callback=self.child_closed)

	def key_info(self):
		item = self.current()
		if item:
			from .jfnav import open_detail
			open_detail(self, item, callback=self.child_closed)

	def key_play(self):
		item = self.current()
		if item:
			from .jfplayer import play_item
			play_item(self, item, self.entries, self.index, on_finished=self.child_closed)

	def child_closed(self, *args):
		"""Refresh user data of visible items after detail/player screens."""
		if not self.jf_closed and self.entries:
			self.later(1500, self.refresh_userdata)

	def refresh_userdata(self):
		if not self.entries:
			return
		start = (self.index // PAGE) * PAGE
		visible = [it for it in self.entries[start:start + PAGE] if it.get("Id")]
		if not visible:
			return
		ids = ",".join(it["Id"] for it in visible)

		def ok(res):
			fresh = dict((it.get("Id"), it) for it in (res.get("Items") or []))
			for it in visible:
				new = fresh.get(it["Id"])
				if new:
					it["UserData"] = new.get("UserData") or it.get("UserData")
			if self.spec.get("source") in ("resume", "nextup"):
				self.reload(keep_index=True)
			else:
				self.redraw_page()
		self.run(self.cl.items, ids=ids, enableTotalRecordCount=False, callback=ok, errback=lambda e: None)

	def key_red(self):
		if self.spec.get("source") != "items" or not self.spec.get("sortable", True):
			return
		choices = [(label, i) for i, (_s, _o, label) in enumerate(SORTS)]
		self.session.openWithCallback(self.sort_chosen, ChoiceBox, title="Sortierung", list=choices, selection=self.sort_idx)

	def sort_chosen(self, choice=None):
		if choice is not None:
			self.sort_idx = choice[1]
			self.reload()

	# ------------------------------------------------------------- categories
	def has_categories(self):
		src = self.spec.get("source")
		if src == "search" or self.spec.get("categories"):
			return True
		if src == "items":
			types = (self.spec.get("params") or {}).get("includeItemTypes") or ""
			return len([c for c in CATEGORIES[1:] if any(t in types.split(",") for t in c[0].split(","))]) > 1
		return src in CLIENT_SIDE and src != "nextup"

	def category_choices(self):
		"""[(label, types)] for this list; with counts when known (search, client side lists)."""
		src = self.spec.get("source")
		allowed = CATEGORIES
		if src == "items":
			types = (self.spec.get("params") or {}).get("includeItemTypes")
			allowed = [c for c in CATEGORIES if c[0] != "Person"]
			if types:
				wanted = types.split(",")
				allowed = [c for c in allowed if c[0] is None or any(t in wanted for t in c[0].split(","))]
		elif src != "search":
			allowed = [c for c in CATEGORIES if c[0] != "Person"]
		out = []
		counts = self.cat_counts
		for types, label in allowed:
			if counts is not None and src != "items":
				n = counts.get(types, 0)
				if n == 0 and types is not None and types != self.category:
					continue
				label = "%s  (%d%s)" % (label, n, "+" if src == "search" and n >= 150 else "")
			out.append((label, types))
		return out

	def category_label(self):
		for types, label in CATEGORIES:
			if types == self.category:
				return label
		return "?"

	def choose_category(self):
		choices = [(label, ("c", types)) for label, types in self.category_choices()]
		if len(choices) <= 2 and self.spec.get("source") in CLIENT_SIDE:
			self.info("Diese Liste enthält nur eine Kategorie")
			return
		sel = [c[1][1] for c in choices].index(self.category) if self.category in [c[1][1] for c in choices] else 0
		self.session.openWithCallback(self.filter_chosen, ChoiceBox, title="Kategorie", list=choices, selection=sel)

	def key_green(self):
		if self.spec.get("source") != "items" or not self.spec.get("sortable", True):
			if self.has_categories():
				self.choose_category()
			return
		choices = []
		if self.has_categories():
			choices += [("Kategorie: %s" % label, ("c", types)) for label, types in self.category_choices()]
		choices += [(label, ("f", i)) for i, (_f, label) in enumerate(FILTERS)]
		choices.append(("Genre wählen ...", ("g", None)))
		if self.genre:
			choices.append(("Genre-Filter entfernen", ("g-", None)))
		self.session.openWithCallback(self.filter_chosen, ChoiceBox, title="Filter", list=choices)

	def filter_chosen(self, choice=None):
		if choice is None:
			return
		kind, val = choice[1]
		if kind == "c":
			if val != self.category:
				self.category = val
				self.genre = None if val == "Person" else self.genre
				self.reload()
		elif kind == "f":
			self.filter_idx = val
			self.reload()
		elif kind == "g-":
			self.genre = None
			self.reload()
		elif kind == "g":
			params = self.spec.get("params") or {}

			def ok(genres):
				if not genres:
					self.info("Keine Genres gefunden")
					return
				lst = [(g.get("Name", "?"), (g.get("Id"), g.get("Name"))) for g in genres]
				self.session.openWithCallback(self.genre_chosen, ChoiceBox, title="Genre", list=lst)
			self.run(self.cl.genres, params.get("parentId"), self.category or params.get("includeItemTypes"), callback=ok, status="Lade Genres ...")

	def genre_chosen(self, choice=None):
		if choice is not None:
			self.genre = choice[1]
			self.reload()

	def key_yellow(self):
		item = self.current()
		if item and item.get("Type") not in ("CollectionFolder", "UserView"):
			self.toggle_played(item, callback=lambda it: self.redraw_page())

	def key_blue(self):
		item = self.current()
		if item and item.get("Type") not in ("CollectionFolder", "UserView"):
			self.toggle_favorite(item, callback=lambda it: self.set_info(self.current()))

	def key_menu(self):
		item = self.current()
		choices = []
		if item:
			t = item.get("Type")
			choices.append(("Öffnen", "open"))
			if t in ("Movie", "Episode", "Video", "MusicVideo", "Series", "Season", "MusicAlbum", "Audio", "BoxSet"):
				choices.append(("Abspielen", "play"))
			if resume_ticks(item) and not is_played(item):
				choices.append(("Von Anfang abspielen", "play_start"))
			if t in ("Movie", "Episode", "Series", "Video", "MusicVideo"):
				choices.append(("Details", "detail"))
			if t == "Episode" and item.get("SeriesId"):
				choices.append(("Zur Serie", "series"))
				choices.append(("Alle Episoden der Staffel", "season"))
			choices.append(("Als ungesehen markieren" if is_played(item) else "Als gesehen markieren", "played"))
			choices.append(("Aus Favoriten entfernen" if is_favorite(item) else "Zu Favoriten hinzufügen", "fav"))
			if t in ("Movie", "Series"):
				choices.append(("Ähnliche Titel", "similar"))
		if self.spec.get("source") == "items" and self.spec.get("sortable", True):
			choices.append(("Sortierung ...", "sort"))
			choices.append(("Filter ...", "filter"))
		elif self.has_categories():
			choices.append(("Kategorie ...", "category"))
		if self.spec.get("source") == "rule":
			choices.append(("Liste bearbeiten ...", "edit_rule"))
		choices.append(("Neu laden", "reload"))
		self.session.openWithCallback(self.menu_chosen, ChoiceBox, title=display_title(item) if item else "Optionen", list=choices)

	def menu_chosen(self, choice=None):
		if choice is None:
			return
		action = choice[1]
		item = self.current()
		from . import jfnav
		if action == "open":
			self.key_ok()
		elif action == "play":
			self.key_play()
		elif action == "play_start":
			from .jfplayer import play_item
			play_item(self, item, self.entries, self.index, resume=False, on_finished=self.child_closed)
		elif action == "detail":
			self.key_info()
		elif action == "series":
			jfnav.open_detail(self, {"Id": item["SeriesId"], "Type": "Series", "Name": item.get("SeriesName", "")}, callback=self.child_closed)
		elif action == "season":
			jfnav.open_season(self, item, callback=self.child_closed)
		elif action == "played":
			self.key_yellow()
		elif action == "fav":
			self.key_blue()
		elif action == "similar":
			jfnav.open_grid(self, {"title": "Ähnlich wie %s" % item.get("Name", ""), "source": "similar", "item_id": item["Id"]})
		elif action == "sort":
			self.key_red()
		elif action in ("filter", "category"):
			self.key_green()
		elif action == "reload":
			self.reload(keep_index=True)
		elif action == "edit_rule":
			from .jfrulesui import RuleEditScreen
			self.session.openWithCallback(self.rule_edited, RuleEditScreen, self.spec["rule"])

	def rule_edited(self, rule=None):
		if rule:
			self.spec["rule"] = rule
			self["title"].setText(rule.get("name", ""))
			rules = jfconfig.load_rules()
			for i, r in enumerate(rules):
				if r.get("id") == rule.get("id"):
					rules[i] = rule
			jfconfig.save_rules(rules)
			self.reload()
