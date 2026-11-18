# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
# Jellyfin for Enigma2 - season/episode browser and album track list
from __future__ import absolute_import

from enigma import RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_CENTER, RT_VALIGN_TOP, RT_WRAP

from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MultiContent import MultiContentEntryPixmapAlphaBlend, MultiContentEntryProgress, MultiContentEntryText
from Components.Pixmap import Pixmap
from Screens.ChoiceBox import ChoiceBox

from .jfcommon import JFScreen, load_pixmap, make_list
from .jfimages import image_ref
from .jfskin import C_ACCENT, C_DIM, C_GREEN, C_PLACEHOLDER, C_TEXT, S, episodes_skin
from . import jfconfig
from .jfutil import (clean_text, fmt_clock, fmt_rating, fmt_runtime, is_favorite, is_new, is_played, played_percentage, resume_ticks,
	ticks_to_seconds)

try:
	from enigma import BT_SCALE, BT_KEEP_ASPECT_RATIO
	PIX_FLAGS = BT_SCALE | BT_KEEP_ASPECT_RATIO
except ImportError:  # pragma: no cover
	PIX_FLAGS = 0

ROW_W = 1800
EP_ROW_H = 174
TH_W = 272
TH_H = 153
TRACK_ROW_H = 64


class EpisodesScreen(JFScreen):
	def __init__(self, session, series_id=None, season_id=None, series_name="", focus_id=None, album=None):
		JFScreen.__init__(self, session)
		self.skin = episodes_skin()
		self.skinName = "JellyfinE2Episodes"
		self.album = album
		self.series_id = series_id
		self.season_id = season_id
		self.focus_id = focus_id
		self.seasons = []
		self.season_pos = 0
		self.entries = []
		self.thumbs = {}
		self.generation = 0
		self.new_days = jfconfig.get_int("new_days", 7)
		self["backdrop"] = Pixmap()
		self["title"] = Label(album.get("Name", "") if album else series_name)
		self["subtitle"] = Label("")
		self["info"] = Label("")
		self["status"] = Label("")
		if album:
			self["list"] = make_list(fonts=((30,), (26,)), item_height=TRACK_ROW_H)
			self.add_keys(red="Gesehen +/-", green="Album abspielen", yellow="", blue="Favorit +/-", hint="OK: ab diesem Titel")
		else:
			self["list"] = make_list(fonts=((32,), (25,)), item_height=EP_ROW_H)
			self.add_keys(red="Gesehen +/-", green="Abspielen", yellow="Details", blue="Favorit +/-", hint="</> Staffel  |  CH+/- Seite")
		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ColorActions", "MenuActions", "ChannelSelectBaseActions",
			"EPGSelectActions", "InfobarSeekActions"], {
			"ok": self.key_ok,
			"cancel": self.close,
			"up": self.key_up,
			"down": self.key_down,
			"upRepeated": self.key_up,
			"downRepeated": self.key_down,
			"left": self.prev_season,
			"right": self.next_season,
			"nextBouquet": self["list"].pageDown,
			"prevBouquet": self["list"].pageUp,
			"red": self.key_red,
			"green": self.key_green,
			"yellow": self.key_yellow,
			"blue": self.key_blue,
			"menu": self.key_menu,
			"info": self.key_yellow,
			"playpauseService": self.key_green,
			"unPauseService": self.key_green,
		}, -1)
		self["list"].onSelectionChanged.append(self.selection_changed)
		self.onLayoutFinish.append(self.start)

	# ------------------------------------------------------------- loading
	def start(self):
		self["status"].hide()
		if self.album:
			self.load_album()
		else:
			self.load_seasons()

	def load_album(self):
		album = self.album
		parts = [album.get("AlbumArtist") or ", ".join(album.get("Artists") or [])]
		if album.get("ProductionYear"):
			parts.append(str(album["ProductionYear"]))
		self["subtitle"].setText("  |  ".join(p for p in parts if p))
		self.load_image("backdrop", album, "backdrop", 1920, 1080)

		def ok(tracks):
			self.entries = tracks
			self.build_list()
		self.run(self.cl.album_tracks, album["Id"], callback=ok, status="Lade Titel ...")

	def load_seasons(self):
		cl = self.cl

		def fetch():
			seasons = cl.seasons(self.series_id)
			series = None
			try:
				series = cl.item(self.series_id, fields="Overview,Genres")
			except Exception:
				pass
			return seasons, series

		def ok(res):
			seasons, series = res
			self.seasons = seasons
			if series:
				self["title"].setText(series.get("Name", ""))
				self.load_image("backdrop", series, "backdrop", 1920, 1080)
			if not seasons:
				self.set_status("Keine Staffeln gefunden")
				return
			pos = 0
			if self.season_id:
				for i, s in enumerate(seasons):
					if s.get("Id") == self.season_id:
						pos = i
						break
			else:
				for i, s in enumerate(seasons):
					ud = s.get("UserData") or {}
					if not ud.get("Played") and (s.get("IndexNumber") or 0) > 0:
						pos = i
						break
			self.season_pos = pos
			self.load_episodes()
		self.run(fetch, callback=ok, status="Lade Staffeln ...")

	def load_episodes(self):
		self.generation += 1
		gen = self.generation
		season = self.seasons[self.season_pos]
		self.update_subtitle()
		self["list"].setList([])
		self["info"].setText("")

		def ok(eps):
			if gen != self.generation:
				return
			self.entries = [e for e in eps if e.get("LocationType") != "Virtual"] or eps
			self.build_list()
		self.run(self.cl.episodes, self.series_id, season["Id"], callback=ok, status="Lade Episoden ...")

	def update_subtitle(self):
		if self.album or not self.seasons:
			return
		season = self.seasons[self.season_pos]
		name = season.get("Name") or "Staffel %s" % season.get("IndexNumber", "?")
		count = len(self.entries) if self.entries else season.get("ChildCount") or 0
		nav = "<  %s  >" % name if len(self.seasons) > 1 else name
		self["subtitle"].setText("%s     (%d von %d)     %s Episoden" % (nav, self.season_pos + 1, len(self.seasons), count))

	# ------------------------------------------------------------- list rendering
	def build_list(self):
		rows = [self.make_row(i, it) for i, it in enumerate(self.entries)]
		self["list"].setList(rows)
		target = 0
		if self.focus_id:
			for i, it in enumerate(self.entries):
				if it.get("Id") == self.focus_id:
					target = i
					break
			self.focus_id = None
		elif not self.album:
			for i, it in enumerate(self.entries):
				if not is_played(it):
					target = i
					break
		if rows:
			self["list"].moveToIndex(target)
		self.update_subtitle()
		self.selection_changed()
		if not rows:
			self.set_status("Keine Einträge")
		if not self.album:
			self.load_thumbs()

	def make_row(self, i, it):
		if self.album:
			return self.track_row(i, it)
		return self.episode_row(i, it)

	def track_row(self, i, it):
		num = it.get("IndexNumber")
		disc = it.get("ParentIndexNumber")
		label = "%s%s" % ("%d." % disc if disc and disc > 1 else "", "%02d" % num if num else "--")
		dur = fmt_clock(ticks_to_seconds(it.get("RunTimeTicks"))) if it.get("RunTimeTicks") else ""
		artists = ", ".join(it.get("Artists") or [])
		name = it.get("Name", "")
		if artists and artists != (self.album or {}).get("AlbumArtist"):
			name = "%s  -  %s" % (name, artists)
		return [it,
			MultiContentEntryText(pos=(S(16), 0), size=(S(90), S(TRACK_ROW_H)), font=1, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=label, color=C_DIM),
			MultiContentEntryText(pos=(S(110), 0), size=(S(ROW_W - 330), S(TRACK_ROW_H)), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=name),
			MultiContentEntryText(pos=(S(ROW_W - 200), 0), size=(S(180), S(TRACK_ROW_H)), font=1, flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER, text=dur, color=C_DIM),
		]

	def episode_row(self, i, it):
		num = it.get("IndexNumber")
		title = "%s. %s" % (num, it.get("Name", "")) if num is not None else it.get("Name", "")
		meta = []
		if it.get("PremiereDate"):
			d = it["PremiereDate"][:10].split("-")
			if len(d) == 3:
				meta.append("%s.%s.%s" % (d[2], d[1], d[0]))
		rt = fmt_runtime(it.get("RunTimeTicks"))
		if rt:
			meta.append(rt)
		r = fmt_rating(it.get("CommunityRating"))
		if r:
			meta.append("Bewertung %s" % r)
		pos = resume_ticks(it)
		if not is_played(it) and is_new(it, self.new_days):
			meta.insert(0, "NEU")
		if is_played(it):
			meta.append("gesehen")
		elif pos:
			meta.append("fortsetzen bei %s" % fmt_clock(ticks_to_seconds(pos)))
		if is_favorite(it):
			meta.append("Favorit")
		overview = clean_text(it.get("Overview")).replace("\n", " ")
		row = [it]
		x_text = 16 + TH_W + 26
		w_text = ROW_W - x_text - 30
		ptr = self.thumbs.get(it.get("Id"))
		if ptr is not None:
			row.append(MultiContentEntryPixmapAlphaBlend(pos=(S(16), S(10)), size=(S(TH_W), S(TH_H)), png=ptr, flags=PIX_FLAGS))
		else:
			row.append(MultiContentEntryText(pos=(S(16), S(10)), size=(S(TH_W), S(TH_H)), font=1, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
				text="", backcolor=C_PLACEHOLDER, backcolor_sel=C_PLACEHOLDER))
		pct = played_percentage(it)
		if 0 < pct < 100 and not is_played(it):
			row.append(MultiContentEntryProgress(pos=(S(16), S(10 + TH_H - 6)), size=(S(TH_W), S(6)), percent=pct, borderWidth=0,
				foreColor=C_ACCENT, foreColorSelected=C_ACCENT, backColor=0x000000, backColorSelected=0x000000))
		if is_played(it):
			row.append(MultiContentEntryText(pos=(S(22), S(16)), size=(S(92), S(28)), font=1, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
				text=" gesehen", color=C_TEXT, color_sel=C_TEXT, backcolor=C_GREEN, backcolor_sel=C_GREEN))
		row.append(MultiContentEntryText(pos=(S(x_text), S(8)), size=(S(w_text), S(42)), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=title))
		row.append(MultiContentEntryText(pos=(S(x_text), S(50)), size=(S(w_text), S(34)), font=1, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
			text="   |   ".join(meta), color=C_ACCENT, color_sel=C_TEXT))
		row.append(MultiContentEntryText(pos=(S(x_text), S(88)), size=(S(w_text), S(78)), font=1, flags=RT_HALIGN_LEFT | RT_VALIGN_TOP | RT_WRAP,
			text=overview, color=C_DIM, color_sel=C_TEXT))
		return row

	def load_thumbs(self):
		gen = self.generation
		for i, it in enumerate(self.entries):
			if it.get("Id") in self.thumbs:
				continue
			ref = image_ref(it, "thumb")
			if not ref:
				continue

			def done(path, i=i, it=it):
				if self.jf_closed or gen != self.generation:
					return
				ptr = load_pixmap(path)
				if ptr is None:
					return
				self.thumbs[it.get("Id")] = ptr
				self.update_row(i)
			path = self.images.get(ref, S(TH_W), S(TH_H), done)
			if path:
				done(path)

	def update_row(self, i):
		lst = self["list"]
		if i >= len(self.entries) or not lst.list or i >= len(lst.list):
			return
		lst.list[i] = self.make_row(i, self.entries[i])
		try:
			lst.l.invalidateEntry(i)
		except Exception:
			idx = lst.getSelectedIndex()
			lst.setList(lst.list)
			lst.moveToIndex(idx)

	def selection_changed(self):
		it = self.current()
		if not it:
			self["info"].setText("")
			return
		if self.album:
			self["info"].setText(clean_text(self.album.get("Overview"))[:500])
			return
		text = clean_text(it.get("Overview")) or "Keine Beschreibung vorhanden."
		self["info"].setText(text[:700])

	def current(self):
		cur = self["list"].getCurrent()
		return cur[0] if cur else None

	# ------------------------------------------------------------- keys
	def key_up(self):
		self["list"].up()

	def key_down(self):
		self["list"].down()

	def prev_season(self):
		if self.album or len(self.seasons) < 2:
			self["list"].pageUp()
			return
		self.season_pos = (self.season_pos - 1) % len(self.seasons)
		self.entries = []
		self.load_episodes()

	def next_season(self):
		if self.album or len(self.seasons) < 2:
			self["list"].pageDown()
			return
		self.season_pos = (self.season_pos + 1) % len(self.seasons)
		self.entries = []
		self.load_episodes()

	def key_ok(self):
		it = self.current()
		if not it:
			return
		from .jfplayer import play_item
		idx = self["list"].getSelectedIndex()
		if self.album:
			from .jfplayer import _ask_resume_and_play
			_ask_resume_and_play(self, self.entries, idx, False, self.child_closed, None, None, None)
		else:
			play_item(self, it, self.entries, idx, on_finished=self.child_closed)

	def key_green(self):
		if self.album:
			from .jfplayer import _ask_resume_and_play
			if self.entries:
				_ask_resume_and_play(self, self.entries, 0, False, self.child_closed, None, None, None)
		else:
			self.key_ok()

	def key_yellow(self):
		it = self.current()
		if it and not self.album:
			from .jfnav import open_detail
			open_detail(self, it, callback=self.child_closed)

	def key_red(self):
		it = self.current()
		if it:
			idx = self["list"].getSelectedIndex()
			self.toggle_played(it, callback=lambda x: self.update_row(idx))

	def key_blue(self):
		it = self.current()
		if it:
			idx = self["list"].getSelectedIndex()
			self.toggle_favorite(it, callback=lambda x: self.update_row(idx))

	def key_menu(self):
		it = self.current()
		if not it:
			return
		lst = [("Abspielen", "play")]
		if resume_ticks(it) and not is_played(it):
			lst.append(("Von Anfang abspielen", "start"))
		if not self.album:
			lst.append(("Details", "detail"))
		lst.append(("Als ungesehen markieren" if is_played(it) else "Als gesehen markieren", "played"))
		if not self.album and self.seasons:
			lst.append(("Ganze Staffel als gesehen markieren", "season_played"))
			lst.append(("Ganze Staffel als ungesehen markieren", "season_unplayed"))
			if len(self.seasons) > 1:
				lst.append(("Staffel wählen ...", "pick_season"))
		lst.append(("Aus Favoriten entfernen" if is_favorite(it) else "Zu Favoriten hinzufügen", "fav"))
		self.session.openWithCallback(self.menu_chosen, ChoiceBox, title=it.get("Name", ""), list=lst)

	def menu_chosen(self, choice):
		if choice is None:
			return
		a = choice[1]
		it = self.current()
		if a == "play":
			self.key_ok()
		elif a == "start":
			from .jfplayer import play_item
			play_item(self, it, self.entries, self["list"].getSelectedIndex(), resume=False, on_finished=self.child_closed)
		elif a == "detail":
			self.key_yellow()
		elif a == "played":
			self.key_red()
		elif a == "fav":
			self.key_blue()
		elif a in ("season_played", "season_unplayed"):
			season = self.seasons[self.season_pos]
			self.run(self.cl.set_played, season["Id"], a == "season_played", callback=lambda r: self.load_episodes(), status="Speichere ...")
		elif a == "pick_season":
			lst = [(s.get("Name") or "Staffel %s" % s.get("IndexNumber"), i) for i, s in enumerate(self.seasons)]
			self.session.openWithCallback(self.season_picked, ChoiceBox, title="Staffel", list=lst, selection=self.season_pos)

	def season_picked(self, choice):
		if choice is not None:
			self.season_pos = choice[1]
			self.entries = []
			self.load_episodes()

	def child_closed(self, *args):
		if self.jf_closed or self.album:
			return
		focus = self.current()
		self.focus_id = focus.get("Id") if focus else None
		if self.seasons:
			self.later(1500, self.load_episodes)
