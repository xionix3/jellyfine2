# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
# Jellyfin for Enigma2 - settings
from __future__ import absolute_import

from Components.ActionMap import ActionMap
from Components.Label import Label
from Screens.MessageBox import MessageBox

from . import jfconfig
from .jfapi import CLIENT_VERSION
from .jfcommon import JFScreen, make_list, text_row
from .jfskin import C_ACCENT, list_skin

ROW_W = 1200


class SettingsScreen(JFScreen):
	def __init__(self, session):
		JFScreen.__init__(self, session)
		self.skin = list_skin("JellyfinE2Settings", item_height=62)
		self.skinName = "JellyfinE2Settings"
		self.vals = dict((s[0], getattr(jfconfig.config.plugins.jellyfine2, s[0]).value) for s in jfconfig.SETTINGS)
		cl = self.cl
		self["title"] = Label("Jellyfin - Einstellungen")
		self["subtitle"] = Label("Plugin %s  |  %s @ %s" % (CLIENT_VERSION, cl.user_name or "-", cl.server or "-"))
		self["list"] = make_list(fonts=((28,), (28,)), item_height=62)
		self["description"] = Label("")
		self["status"] = Label("")
		self.add_keys(red="Abbrechen", green="Speichern", yellow="Bild-Cache leeren", blue="Abmelden")
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "ChannelSelectBaseActions"], {
			"ok": lambda: self.change(1),
			"cancel": self.close,
			"up": self["list"].up,
			"down": self["list"].down,
			"left": lambda: self.change(-1),
			"right": lambda: self.change(1),
			"nextBouquet": self["list"].pageDown,
			"prevBouquet": self["list"].pageUp,
			"red": self.close,
			"green": self.save,
			"yellow": self.clear_cache,
			"blue": self.logout,
		}, -1)
		self["list"].onSelectionChanged.append(self.update_description)
		self.onLayoutFinish.append(self.build)

	def build(self):
		rows = []
		for sid, label, _choices, _default, _help in jfconfig.SETTINGS:
			value = self.vals[sid]
			text = jfconfig.label_for(sid, value)
			if sid == "player" and value not in [v for v, _ in jfconfig.player_choices()]:
				text = jfconfig.label_for(sid, "4097")
			rows.append(text_row(sid, label, ROW_W, 62, value="<  %s  >" % text, value_width=560, value_color=C_ACCENT))
		idx = self["list"].getSelectedIndex() if self["list"].list else 0
		self["list"].setList(rows)
		self["list"].moveToIndex(idx)
		self.update_description()

	def update_description(self):
		cur = self["list"].getCurrent()
		if not cur:
			return
		for s in jfconfig.SETTINGS:
			if s[0] == cur[0]:
				extra = ""
				if s[0] == "max_width" and self.vals["max_width"] == "auto":
					extra = " Erkannt: %s." % ("UHD-Box" if jfconfig.is_uhd_box() else "HD-Box")
				if s[0] == "player" and not jfconfig.serviceapp_installed():
					extra = " ServiceApp ist nicht installiert."
				self["description"].setText((s[4] or "") + extra)
				return

	def change(self, step):
		cur = self["list"].getCurrent()
		if not cur:
			return
		sid = cur[0]
		choices = [v for v, _ in jfconfig.choices_for(sid)]
		if not choices:
			return
		value = self.vals[sid]
		pos = choices.index(value) if value in choices else 0
		self.vals[sid] = choices[(pos + step) % len(choices)]
		self.build()

	def save(self):
		changed = False
		for sid, value in self.vals.items():
			if getattr(jfconfig.config.plugins.jellyfine2, sid).value != value:
				jfconfig.set_value(sid, value)
				changed = True
		self.cl.verify_ssl = jfconfig.get_bool("verify_ssl")
		self.close("changed" if changed else None)

	def clear_cache(self):
		from .jfimages import clear
		clear()
		self["status"].setText("Bild-Cache geleert.")

	def logout(self):
		self.session.openWithCallback(lambda yes=False: yes and self.close("logout"), MessageBox, "Abmelden und Anmeldedaten löschen?", MessageBox.TYPE_YESNO, default=False)
