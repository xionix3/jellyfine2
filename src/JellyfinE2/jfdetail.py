# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
# Jellyfin for Enigma2 - detail page for movies, episodes and series
from __future__ import absolute_import

from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.ProgressBar import ProgressBar
from Components.ScrollLabel import ScrollLabel
from Screens.ChoiceBox import ChoiceBox

from .jfcommon import JFScreen, make_list, text_row
from .jfskin import detail_skin
from .jfutil import (clean_text, episode_code, fmt_clock, fmt_ends_at, fmt_rating, fmt_runtime, is_favorite, is_played,
	lang_name, played_percentage, resume_ticks, stream_label, ticks_to_seconds, video_label)

PLAYABLE = ("Movie", "Episode", "Video", "MusicVideo", "Trailer", "Recording", "Program", "TvChannel")


class DetailScreen(JFScreen):
	def __init__(self, session, item):
		JFScreen.__init__(self, session)
		self.skin = detail_skin()
		self.skinName = "JellyfinE2Detail"
		self.item = item
		self.next_up = None
		self.audio_index = None
		self.sub_index = None
		self.source_id = None
		self["backdrop"] = Pixmap()
		self["poster"] = Pixmap()
		self["poster_ph"] = Label(item.get("Name", ""))
		self["progress"] = ProgressBar()
		self["actions"] = make_list(fonts=((28,), (24,)), item_height=58)
		self["title"] = Label(item.get("Name", ""))
		self["tagline"] = Label("")
		self["meta"] = Label("")
		self["genres"] = Label("")
		self["overview"] = ScrollLabel("")
		self["tech"] = Label("")
		self["people"] = Label("")
		self["status"] = Label("")
		self.add_keys(red="Gesehen +/-", green="Abspielen", yellow="Audio / Untertitel", blue="Favorit +/-", hint="CH+/- oder </> Text blättern")
		self["key_actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ColorActions", "MenuActions", "ChannelSelectBaseActions",
			"EPGSelectActions", "InfobarSeekActions"], {
			"ok": self.key_ok,
			"cancel": self.close,
			"up": self["actions"].up,
			"down": self["actions"].down,
			"left": self["overview"].pageUp,
			"right": self["overview"].pageDown,
			"nextBouquet": self["overview"].pageDown,
			"prevBouquet": self["overview"].pageUp,
			"red": self.key_red,
			"green": self.key_green,
			"yellow": self.key_yellow,
			"blue": self.key_blue,
			"menu": self.key_menu,
			"playpauseService": self.key_green,
			"unPauseService": self.key_green,
		}, -1)
		self.onLayoutFinish.append(self.start)

	# ------------------------------------------------------------- data
	def start(self):
		self["progress"].hide()
		self["status"].setText("")
		self.render()
		self.load()

	def load(self):
		item_id = self.item.get("Id")
		cl = self.cl
		is_series = self.item.get("Type") == "Series"

		def fetch():
			full = cl.item(item_id)
			nxt = None
			if is_series or (full and full.get("Type") == "Series"):
				try:
					lst = cl.next_up(limit=1, series_id=item_id)
					nxt = lst[0] if lst else None
				except Exception:
					nxt = None
			return full, nxt

		def ok(res):
			full, nxt = res
			if full:
				self.item = full
			self.next_up = nxt
			self.render()
		self.run(fetch, callback=ok, status=None)
		self["status"].setText("Lade Details ...")

	def media_source(self):
		sources = self.item.get("MediaSources") or []
		if not sources:
			return {}
		if self.source_id:
			for s in sources:
				if s.get("Id") == self.source_id:
					return s
		return sources[0]

	def streams(self, kind):
		return [s for s in (self.media_source().get("MediaStreams") or self.item.get("MediaStreams") or []) if s.get("Type") == kind]

	def selected_audio(self):
		idx = self.audio_index
		if idx is None:
			idx = self.media_source().get("DefaultAudioStreamIndex")
		for s in self.streams("Audio"):
			if s.get("Index") == idx:
				return s
		audio = self.streams("Audio")
		return audio[0] if audio else None

	def selected_sub(self):
		idx = self.sub_index
		if idx is None:
			idx = self.media_source().get("DefaultSubtitleStreamIndex")
		if idx is None or idx < 0:
			return None
		for s in self.streams("Subtitle"):
			if s.get("Index") == idx:
				return s
		return None

	# ------------------------------------------------------------- drawing
	def render(self):
		it = self.item
		t = it.get("Type")
		self["status"].setText("")
		title = it.get("Name") or ""
		if t == "Episode":
			title = "%s  %s" % (episode_code(it), title) if episode_code(it) else title
		self["title"].setText(title)
		tag = ""
		if t == "Episode" and it.get("SeriesName"):
			tag = it["SeriesName"] + (" - %s" % it["SeasonName"] if it.get("SeasonName") else "")
		elif it.get("Taglines"):
			tag = it["Taglines"][0]
		elif it.get("OriginalTitle") and it.get("OriginalTitle") != it.get("Name"):
			tag = it["OriginalTitle"]
		self["tagline"].setText(tag)

		meta = []
		if it.get("ProductionYear"):
			meta.append(str(it["ProductionYear"]))
		if t == "Series":
			if it.get("ChildCount"):
				meta.append("%s Staffeln" % it["ChildCount"])
			if it.get("Status") == "Continuing":
				meta.append("laufend")
			elif it.get("Status") == "Ended":
				meta.append("beendet")
		rt = fmt_runtime(it.get("RunTimeTicks"))
		if rt and t != "Series":
			meta.append(rt)
		if it.get("OfficialRating"):
			meta.append(it["OfficialRating"])
		r = fmt_rating(it.get("CommunityRating"))
		if r:
			meta.append("Bewertung %s" % r)
		if it.get("CriticRating"):
			meta.append("Kritiker %s%%" % it["CriticRating"])
		if t in PLAYABLE and it.get("RunTimeTicks"):
			ends = fmt_ends_at(it["RunTimeTicks"], resume_ticks(it) if not is_played(it) else 0)
			if ends:
				meta.append(ends)
		if is_played(it):
			meta.append("gesehen")
		if is_favorite(it):
			meta.append("Favorit")
		self["meta"].setText("   |   ".join(meta))
		self["genres"].setText(", ".join(it.get("Genres") or []))
		self["overview"].setText(clean_text(it.get("Overview")) or "Keine Beschreibung vorhanden.")
		self["tech"].setText(self.tech_text())
		self["people"].setText(self.people_text())
		pct = played_percentage(it)
		if 0 < pct < 100 and not is_played(it) and t in PLAYABLE:
			self["progress"].setValue(pct)
			self["progress"].show()
		else:
			self["progress"].hide()
		self["poster_ph"].setText(it.get("SeriesName") if t == "Episode" else it.get("Name", ""))
		self.load_image("poster", it, "poster", 340, 510, placeholder="poster_ph")
		self.load_image("backdrop", it, "backdrop", 1920, 1080)
		self.build_actions()

	def tech_text(self):
		it = self.item
		if it.get("Type") not in PLAYABLE:
			studios = ", ".join(s.get("Name", "") for s in (it.get("Studios") or [])[:4])
			return "Studio/Sender: %s" % studios if studios else ""
		lines = []
		video = self.streams("Video")
		ms = self.media_source()
		first = []
		if video:
			first.append("Video: %s" % video_label(video[0]))
		if ms.get("Container"):
			first.append("Container: %s" % ms["Container"].split(",")[0].upper())
		if ms.get("Size"):
			first.append("%.1f GB" % (ms["Size"] / 1073741824.0))
		if len(it.get("MediaSources") or []) > 1:
			first.append("Version: %s" % (ms.get("Name") or "?"))
		if first:
			lines.append("   |   ".join(first))
		audio = self.streams("Audio")
		if audio:
			sel = self.selected_audio()
			names = []
			for s in audio[:5]:
				label = stream_label(s)
				names.append("[%s]" % label if sel is s else label)
			more = " (+%d)" % (len(audio) - 5) if len(audio) > 5 else ""
			lines.append("Audio: %s%s" % (", ".join(names), more))
		subs = self.streams("Subtitle")
		if subs:
			langs = []
			for s in subs:
				name = lang_name(s.get("Language")) or s.get("DisplayTitle") or "?"
				if name not in langs:
					langs.append(name)
			sel = self.selected_sub()
			lines.append("Untertitel: %s   (gewählt: %s)" % (", ".join(langs[:8]), stream_label(sel) if sel else "aus"))
		return "\n".join(lines)

	def people_text(self):
		people = self.item.get("People") or []
		directors = [p.get("Name") for p in people if p.get("Type") == "Director"]
		actors = [p.get("Name") for p in people if p.get("Type") == "Actor"]
		lines = []
		if directors:
			lines.append("Regie: %s" % ", ".join(directors[:3]))
		if actors:
			lines.append("Mit: %s" % ", ".join(actors[:8]))
		studios = [s.get("Name") for s in (self.item.get("Studios") or [])]
		if studios and self.item.get("Type") in PLAYABLE:
			lines.append("Studio: %s" % ", ".join(studios[:3]))
		return "\n".join(lines)

	def build_actions(self):
		it = self.item
		t = it.get("Type")
		rows = []
		w = 340

		def add(text, key, value=None):
			rows.append(text_row(key, text, w, 58, x=16))

		if t in PLAYABLE:
			pos = resume_ticks(it)
			if pos and not is_played(it):
				add("Fortsetzen (%s)" % fmt_clock(ticks_to_seconds(pos)), "resume")
				add("Von Anfang", "start")
			else:
				add("Abspielen", "start")
			if len(self.streams("Audio")) > 1:
				add("Audiospur", "audio")
			if self.streams("Subtitle"):
				add("Untertitel", "subs")
			if len(it.get("MediaSources") or []) > 1:
				add("Version", "version")
			if t == "Episode" and it.get("SeriesId"):
				add("Alle Episoden", "season")
				add("Zur Serie", "series")
		elif t == "Series":
			if self.next_up:
				add("Weiter: %s" % episode_code(self.next_up), "nextup")
			add("Staffeln & Episoden", "episodes")
			add("Serie abspielen", "playseries")
		add("Ungesehen" if is_played(it) else "Gesehen", "played")
		add("Aus Favoriten" if is_favorite(it) else "Favorit", "fav")
		if t in ("Movie", "Series"):
			add("Ähnliche Titel", "similar")
		if it.get("People"):
			add("Besetzung", "cast")
		idx = self["actions"].getSelectedIndex() if self["actions"].list else 0
		self["actions"].setList(rows)
		if rows:
			self["actions"].moveToIndex(min(idx, len(rows) - 1))

	# ------------------------------------------------------------- actions
	def key_ok(self):
		cur = self["actions"].getCurrent()
		if cur:
			self.do(cur[0])

	def do(self, action):
		from . import jfnav
		from .jfplayer import play_item
		it = self.item
		if action == "resume":
			play_item(self, it, resume=True, on_finished=self.after_play, audio_index=self.audio_index, sub_index=self.sub_index, media_source_id=self.source_id)
		elif action == "start":
			play_item(self, it, resume=False, on_finished=self.after_play, audio_index=self.audio_index, sub_index=self.sub_index, media_source_id=self.source_id)
		elif action == "audio":
			self.choose_audio()
		elif action == "subs":
			self.choose_subs()
		elif action == "version":
			lst = [(s.get("Name") or s.get("Id"), s.get("Id")) for s in it.get("MediaSources") or []]
			self.session.openWithCallback(self.version_chosen, ChoiceBox, title="Version", list=lst)
		elif action == "season":
			jfnav.open_season(self, it, callback=self.after_play)
		elif action == "series":
			jfnav.open_detail(self, {"Id": it["SeriesId"], "Type": "Series", "Name": it.get("SeriesName", "")}, callback=self.after_play)
		elif action == "nextup" and self.next_up:
			play_item(self, self.next_up, on_finished=self.after_play)
		elif action == "episodes":
			from .jfepisodes import EpisodesScreen
			focus_season = self.next_up.get("SeasonId") if self.next_up else None
			focus_ep = self.next_up.get("Id") if self.next_up else None
			self.session.openWithCallback(self.after_play, EpisodesScreen, series_id=it["Id"], season_id=focus_season,
				series_name=it.get("Name", ""), focus_id=focus_ep)
		elif action == "playseries":
			play_item(self, it, on_finished=self.after_play)
		elif action == "played":
			self.key_red()
		elif action == "fav":
			self.key_blue()
		elif action == "similar":
			jfnav.open_grid(self, {"title": "Ähnlich wie %s" % it.get("Name", ""), "source": "similar", "item_id": it["Id"]})
		elif action == "cast":
			people = it.get("People") or []
			roles = {"Actor": "Darsteller", "Director": "Regie", "Writer": "Drehbuch", "Producer": "Produktion", "GuestStar": "Gaststar"}
			lst = []
			for p in people[:40]:
				role = p.get("Role") or roles.get(p.get("Type"), p.get("Type") or "")
				lst.append(("%s%s" % (p.get("Name"), " - %s" % role if role else ""), p))
			self.session.openWithCallback(self.person_chosen, ChoiceBox, title="Besetzung", list=lst)

	def person_chosen(self, choice):
		if choice is None:
			return
		p = choice[1]
		from .jfnav import open_item
		open_item(self, {"Id": p.get("Id"), "Type": "Person", "Name": p.get("Name")})

	def version_chosen(self, choice):
		if choice is not None:
			self.source_id = choice[1]
			self.audio_index = None
			self.sub_index = None
			self.render()

	def choose_audio(self):
		audio = self.streams("Audio")
		if not audio:
			return
		sel = self.selected_audio()
		lst = [(stream_label(s), s.get("Index")) for s in audio]
		pos = audio.index(sel) if sel in audio else 0
		self.session.openWithCallback(self.audio_chosen, ChoiceBox, title="Audiospur", list=lst, selection=pos)

	def audio_chosen(self, choice):
		if choice is not None:
			self.audio_index = choice[1]
			self["tech"].setText(self.tech_text())

	def choose_subs(self):
		subs = self.streams("Subtitle")
		lst = [("Aus", -1)] + [(stream_label(s), s.get("Index")) for s in subs]
		sel = self.selected_sub()
		pos = subs.index(sel) + 1 if sel in subs else 0
		self.session.openWithCallback(self.subs_chosen, ChoiceBox, title="Untertitel (externe/Bild-Untertitel werden eingebrannt)", list=lst, selection=pos)

	def subs_chosen(self, choice):
		if choice is not None:
			self.sub_index = choice[1]
			self["tech"].setText(self.tech_text())

	def after_play(self, *args):
		if not self.jf_closed:
			self.later(1500, self.load)

	def key_green(self):
		it = self.item
		if it.get("Type") in PLAYABLE:
			from .jfplayer import play_item
			play_item(self, it, on_finished=self.after_play, audio_index=self.audio_index, sub_index=self.sub_index, media_source_id=self.source_id)
		elif it.get("Type") == "Series":
			self.do("nextup" if self.next_up else "playseries")

	def key_yellow(self):
		if self.item.get("Type") not in PLAYABLE:
			return
		lst = []
		if self.streams("Audio"):
			lst.append(("Audiospur wählen", "audio"))
		if self.streams("Subtitle"):
			lst.append(("Untertitel wählen", "subs"))
		if not lst:
			self.info("Keine Audio-/Untertitelspuren bekannt")
			return
		if len(lst) == 1:
			self.do(lst[0][1])
			return
		self.session.openWithCallback(lambda c=None: c and self.do(c[1]), ChoiceBox, title="Audio / Untertitel", list=lst)

	def key_red(self):
		self.toggle_played(self.item, callback=lambda it: self.render())

	def key_blue(self):
		self.toggle_favorite(self.item, callback=lambda it: self.render())

	def key_menu(self):
		rows = self["actions"].list or []
		labels = {"resume": "Fortsetzen", "start": "Abspielen / Von Anfang", "audio": "Audiospur", "subs": "Untertitel", "version": "Version",
			"season": "Alle Episoden", "series": "Zur Serie", "nextup": "Nächste Episode", "episodes": "Staffeln & Episoden",
			"playseries": "Serie abspielen", "played": "Gesehen-Status ändern", "fav": "Favorit ändern", "similar": "Ähnliche Titel", "cast": "Besetzung"}
		lst = [(labels.get(r[0], r[0]), r[0]) for r in rows]
		lst.append(("Neu laden", "reload"))
		self.session.openWithCallback(self.menu_chosen, ChoiceBox, title=self.item.get("Name", ""), list=lst)

	def menu_chosen(self, choice):
		if choice is None:
			return
		if choice[1] == "reload":
			self.load()
		else:
			self.do(choice[1])
