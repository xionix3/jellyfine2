# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
# Jellyfin for Enigma2 - shared screen helpers
from __future__ import absolute_import

from enigma import ePoint

from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.ProgressBar import ProgressBar
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Tools.LoadPixmap import LoadPixmap

from . import jfconfig
from .jfasync import runner
from .jfimages import image_ref, loader
from .jfskin import S
from .jfutil import display_title, is_new, is_played, played_percentage, unplayed_count


def load_pixmap(path):
	if not path:
		return None
	try:
		return LoadPixmap(path)
	except Exception as e:
		print("[Jellyfin] LoadPixmap failed for %s: %s" % (path, e))
		return None


class JFScreen(Screen):
	"""Base class: async tasks bound to the screen, status overlay, helpers."""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.cl = jfconfig.client()
		self.tasks = runner().group()
		self.images = loader(self.cl)
		self.jf_closed = False
		self.busy = 0
		self._jf_timers = []
		self.onClose.append(self.__jf_on_close)
		self.onLayoutFinish.append(self.__jf_apply_item_heights)

	def __jf_apply_item_heights(self):
		# the skin's itemHeight may differ from what a list needs (e.g. album vs. episode rows)
		for comp in list(self.values()):
			h = getattr(comp, "jf_item_height", None)
			if h:
				try:
					comp.l.setItemHeight(S(h))
				except Exception:
					pass

	def __jf_on_close(self):
		self.jf_closed = True
		self.tasks.cancel()
		for t in self._jf_timers:
			t.stop()
		self._jf_timers = []

	def add_keys(self, red="", green="", yellow="", blue="", hint=None):
		for name, text in (("key_red", red), ("key_green", green), ("key_yellow", yellow), ("key_blue", blue)):
			self[name] = Label(text)
		if hint is not None:
			self["key_hint"] = Label(hint)

	def run(self, fn, *args, **kwargs):
		"""Run fn in a worker; callbacks only fire while the screen is open."""
		callback = kwargs.pop("callback", None)
		errback = kwargs.pop("errback", None)
		status = kwargs.pop("status", None)
		if status:
			self.set_busy(True, status)

		def ok(res):
			if status:
				self.set_busy(False)
			if not self.jf_closed and callback:
				callback(res)

		def fail(err):
			if status:
				self.set_busy(False)
			if self.jf_closed:
				return
			if errback:
				errback(err)
			else:
				self.show_error(err)

		return self.tasks.run(fn, *args, callback=ok, errback=fail, **kwargs)

	def later(self, ms, fn):
		"""Run fn on the GUI thread after ms (e.g. give the server time to process a stop report)."""
		from enigma import eTimer
		t = eTimer()

		def fire():
			self._jf_timers.remove(t)
			if not self.jf_closed:
				fn()
		t.callback.append(fire)
		self._jf_timers.append(t)
		t.start(ms, True)

	def set_busy(self, busy, text="Lade ..."):
		self.busy = max(0, self.busy + (1 if busy else -1))
		if "status" not in self:
			return
		if self.busy:
			self["status"].setText(text)
			self["status"].show()
		else:
			self["status"].hide()

	def set_status(self, text):
		if "status" not in self:
			return
		if text:
			self["status"].setText(text)
			self["status"].show()
		else:
			self["status"].hide()

	def show_error(self, err, title="Fehler"):
		msg = str(err) or err.__class__.__name__
		if getattr(err, "status", None) == 401:
			msg += "\n\nBitte im Hauptmenü des Plugins neu anmelden (rote Taste)."
		self.session.open(MessageBox, "%s:\n%s" % (title, msg), MessageBox.TYPE_ERROR, timeout=10)

	def info(self, text, timeout=3):
		self.session.open(MessageBox, text, MessageBox.TYPE_INFO, timeout=timeout)

	def set_pixmap(self, name, path):
		if self.jf_closed or name not in self:
			return False
		ptr = load_pixmap(path)
		widget = self[name]
		if ptr is None or widget.instance is None:
			widget.hide()
			return False
		widget.instance.setPixmap(ptr)
		widget.show()
		return True

	def load_image(self, name, item, kind, w, h, placeholder=None, keep=False):
		"""Load an image into a Pixmap widget (w/h in FHD units).

		keep=True leaves the previous picture visible until the new one arrived (backdrops)."""
		ref = image_ref(item, kind) if item else None
		widget = self[name]
		if not keep or not ref:
			widget.hide()
		if placeholder is not None and placeholder in self:
			self[placeholder].show()
		if not ref:
			widget.jf_token = None
			return
		if keep and getattr(widget, "jf_token", None) == (ref, w, h):
			return
		token = (ref, w, h)
		widget.jf_token = token

		def done(path):
			if self.jf_closed or getattr(widget, "jf_token", None) != token:
				return
			if self.set_pixmap(name, path) and placeholder is not None and placeholder in self:
				self[placeholder].hide()
		path = self.images.get(ref, S(w), S(h), done)
		if path:
			done(path)

	# --------------------------------------------------- user data toggles
	def toggle_played(self, item, callback=None):
		ud = item.setdefault("UserData", {})
		new = not ud.get("Played")

		def ok(res):
			if isinstance(res, dict) and res:
				item["UserData"].update(res)
			else:
				item["UserData"]["Played"] = new
				if new:
					item["UserData"]["PlaybackPositionTicks"] = 0
					item["UserData"]["PlayedPercentage"] = 0
			if callback:
				callback(item)
		self.run(self.cl.set_played, item["Id"], new, callback=ok)

	def toggle_favorite(self, item, callback=None):
		ud = item.setdefault("UserData", {})
		new = not ud.get("IsFavorite")

		def ok(res):
			if isinstance(res, dict) and res:
				item["UserData"].update(res)
			else:
				item["UserData"]["IsFavorite"] = new
			if callback:
				callback(item)
		self.run(self.cl.set_favorite, item["Id"], new, callback=ok)


class CoverCells(object):
	"""A set of poster cells (placeholder, cover, progress, badges, label) on a screen."""

	def __init__(self, screen, prefix, count, w, h, badges=True):
		self.screen = screen
		self.prefix = prefix
		self.count = count
		self.w = w
		self.h = h
		self.badges = badges
		self.items = [None] * count
		for i in range(count):
			screen[self.n("ph", i)] = Label("")
			screen[self.n("cover", i)] = Pixmap()
			screen[self.n("prog", i)] = ProgressBar()
			if badges:
				screen[self.n("seen", i)] = Label("gesehen")
				screen[self.n("new", i)] = Label("NEU")
				screen[self.n("count", i)] = Label("")
			screen[self.n("label", i)] = Label("")

	def n(self, kind, i):
		return "%s%s%d" % (self.prefix, kind, i)

	def clear(self, i):
		s = self.screen
		self.items[i] = None
		s[self.n("ph", i)].hide()
		s[self.n("cover", i)].hide()
		s[self.n("prog", i)].hide()
		if self.badges:
			s[self.n("seen", i)].hide()
			s[self.n("new", i)].hide()
			s[self.n("count", i)].hide()
		s[self.n("label", i)].setText("")
		widget = s[self.n("cover", i)]
		widget.jf_token = None

	def clear_all(self):
		for i in range(self.count):
			self.clear(i)

	def set_item(self, i, item):
		s = self.screen
		if item is None:
			self.clear(i)
			return
		self.items[i] = item
		title = display_title(item)
		s[self.n("label", i)].setText(title)
		s[self.n("ph", i)].setText(title)
		pct = played_percentage(item)
		played = is_played(item)
		prog = s[self.n("prog", i)]
		if 0 < pct < 100 and not played and item.get("Type") not in ("Series", "Season", "BoxSet", "Folder", "CollectionFolder"):
			prog.setValue(pct)
			prog.show()
		else:
			prog.hide()
		if self.badges:
			seen = s[self.n("seen", i)]
			new = s[self.n("new", i)]
			cnt = s[self.n("count", i)]
			unplayed = unplayed_count(item) if item.get("Type") in ("Series", "Season", "BoxSet", "Folder") else 0
			fresh = item.get("_jf_new_count")
			if played and jfconfig.get_bool("show_played"):
				seen.show()
				new.hide()
			else:
				seen.hide()
				if fresh or is_new(item, jfconfig.get_int("new_days", 7)):
					new.show()
				else:
					new.hide()
			if fresh and fresh > 1:
				cnt.setText("+%d" % fresh if fresh < 100 else "99+")
				cnt.show()
			elif unplayed and not played:
				cnt.setText(str(unplayed) if unplayed < 100 else "99+")
				cnt.show()
			else:
				cnt.hide()
		s.load_image(self.n("cover", i), item, "poster", self.w, self.h, placeholder=self.n("ph", i))


def make_list(fonts=((28,),), item_height=58):
	"""MenuList with MultiContent; fonts = sizes (FHD) for font index 0..n."""
	from enigma import eListboxPythonMultiContent, gFont
	from Components.MenuList import MenuList
	lst = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
	for idx, f in enumerate(fonts):
		size = f[0] if isinstance(f, tuple) else f
		lst.l.setFont(idx, gFont("Regular", S(size)))
	lst.l.setItemHeight(S(item_height))
	lst.jf_item_height = item_height
	return lst


def text_row(data, text, width, height, value=None, value_width=0, x=18, color=None, value_color=None):
	"""Single-line row: text on the left, optional value right aligned (FHD units)."""
	from enigma import RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_CENTER
	from Components.MultiContent import MultiContentEntryText
	row = [data]
	tw = width - x * 2 - (value_width + 10 if value is not None else 0)
	row.append(MultiContentEntryText(pos=(S(x), 0), size=(S(tw), S(height)), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=text, color=color))
	if value is not None:
		row.append(MultiContentEntryText(pos=(S(width - x - value_width), 0), size=(S(value_width), S(height)), font=1 if value_color is None else 1,
			flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER, text=value, color=value_color))
	return row


def prefetch_posters(screen, items, w, h):
	"""Warm the image cache (e.g. next grid page) without touching widgets."""
	for it in items:
		ref = image_ref(it, "poster")
		if ref:
			screen.images.get(ref, S(w), S(h), _ignore)


def _ignore(*args):
	pass


def move_widget(screen, name, x, y):
	w = screen[name]
	if w.instance is not None:
		w.instance.move(ePoint(S(x), S(y)))
