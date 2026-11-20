# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 xionix
# Jellyfin for Enigma2 - settings
from __future__ import absolute_import

from .jfi18n import _, set_language

from Components.ActionMap import ActionMap
from Components.Label import Label
from Screens.MessageBox import MessageBox

from . import jfconfig
from .jfapi import CLIENT_VERSION
from .jfcommon import JFScreen, make_list, text_row
from .jfskin import C_ACCENT, list_skin

ROW_W = 1200
AUTHOR = "xionix"
HOMEPAGE = "https://github.com/xionix3/jellyfine_enigma2_openpli"


def about_text(cl=None):
	lines = [_("Jellyfin für Enigma2  -  Version %s") % CLIENT_VERSION, "", _("Entwickelt von %s") % AUTHOR, HOMEPAGE, "",
		_("Freie Software (GPL-2.0-or-later). Kein offizielles Jellyfin-Projekt."), _("Box: %s") % jfconfig.box_name()]
	if cl is not None and cl.server:
		ver = ".".join(str(x) for x in cl.server_version) if cl.server_version != (0, 0, 0) else "?"
		lines.append(_("Server: %s (Jellyfin %s)") % (cl.server_name or cl.server, ver))
	return "\n".join(lines)


class SettingsScreen(JFScreen):
	def __init__(self, session):
		JFScreen.__init__(self, session)
		self.skin = list_skin("JellyfinE2Settings", item_height=62)
		self.skinName = "JellyfinE2Settings"
		self.vals = dict((s[0], getattr(jfconfig.config.plugins.jellyfine2, s[0]).value) for s in jfconfig.SETTINGS)
		cl = self.cl
		self["title"] = Label(_("Jellyfin - Einstellungen"))
		self["subtitle"] = Label(_("Plugin %s von %s  |  %s @ %s") % (CLIENT_VERSION, AUTHOR, cl.user_name or "-", cl.server or "-"))
		self["list"] = make_list(fonts=((28,), (28,)), item_height=62)
		self["description"] = Label("")
		self["status"] = Label("")
		self.add_keys(red=_("Abbrechen"), green=_("Speichern"), yellow=_("Bild-Cache leeren"), blue=_("Abmelden"))
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "ChannelSelectBaseActions", "MenuActions"], {
			"menu": self.key_menu,
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
			if sid == "player" and value not in [v for v, _lbl in jfconfig.player_choices()]:
				text = jfconfig.label_for(sid, "4097")
			rows.append(text_row(sid, _(label), ROW_W, 62, value="<  %s  >" % text, value_width=560, value_color=C_ACCENT))
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
					extra = _(" Erkannt: %s.") % (_("UHD-Box") if jfconfig.is_uhd_box() else _("HD-Box"))
				if s[0] == "player" and not jfconfig.serviceapp_installed():
					extra = _(" ServiceApp ist nicht installiert.")
				self["description"].setText(_(s[4]) + extra)
				return

	def change(self, step):
		cur = self["list"].getCurrent()
		if not cur:
			return
		sid = cur[0]
		choices = [v for v, _lbl in jfconfig.choices_for(sid)]
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
		set_language(jfconfig.get("language"))
		self.close("changed" if changed else None)

	def clear_cache(self):
		from .jfimages import clear
		clear()
		self["status"].setText(_("Bild-Cache geleert."))

	def logout(self):
		self.session.openWithCallback(lambda yes=False: yes and self.close("logout"), MessageBox, _("Abmelden und Anmeldedaten löschen?"), MessageBox.TYPE_YESNO, default=False)

	def key_menu(self):
		from Screens.ChoiceBox import ChoiceBox
		self.session.openWithCallback(self.menu_chosen, ChoiceBox, title="Jellyfin", list=[(_("Nach Updates suchen"), "update"), (_("Über dieses Plugin"), "about")])

	def menu_chosen(self, choice=None):
		if choice is None:
			return
		if choice[1] == "update":
			from .jfupdate import Updater
			Updater(self).run_check(manual=True)
		else:
			self.session.open(MessageBox, about_text(self.cl), MessageBox.TYPE_INFO)
