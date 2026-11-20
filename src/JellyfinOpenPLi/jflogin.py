# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
# Jellyfin for Enigma2 - login (password, Quick Connect, LAN discovery)
from __future__ import absolute_import

from .jfi18n import _, N_

from enigma import eTimer

from Components.ActionMap import ActionMap
from Components.Label import Label
from Screens.ChoiceBox import ChoiceBox
from Screens.VirtualKeyBoard import VirtualKeyBoard

from . import jfconfig
from .jfapi import discover_servers, normalize_server
from .jfcommon import JFScreen, make_list, text_row
from .jfskin import C_ACCENT, C_DIM, list_skin, quickconnect_skin

ROW_W = 1200


class LoginScreen(JFScreen):
	def __init__(self, session):
		JFScreen.__init__(self, session)
		self.skin = list_skin("JellyfinE2Login")
		self.skinName = "JellyfinE2Login"
		self.server = jfconfig.saved_server()
		self.username = jfconfig.saved_username()
		self.password = ""
		self["title"] = Label(_("Jellyfin - Anmeldung"))
		self["subtitle"] = Label(_("Mit deinem Jellyfin-Server verbinden"))
		self["list"] = make_list(fonts=((32,), (30,)), item_height=70)
		self["description"] = Label("")
		self["status"] = Label("")
		self.add_keys(red=_("Abbrechen"), green=_("Anmelden"), yellow=_("Quick Connect"), blue=_("Server suchen"))
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions"], {
			"ok": self.key_ok,
			"cancel": self.close,
			"up": self["list"].up,
			"down": self["list"].down,
			"red": self.close,
			"green": self.login,
			"yellow": self.quick_connect,
			"blue": self.discover,
		}, -1)
		self["list"].onSelectionChanged.append(self.update_description)
		self.onLayoutFinish.append(self.build)

	DESCRIPTIONS = {
		"server": N_("Adresse des Jellyfin-Servers, z.B. http://192.168.1.10:8096 oder https://jellyfin.example.de. OK öffnet die Tastatur."),
		"user": N_("Dein Jellyfin-Benutzername."),
		"pass": N_("Dein Passwort (leer lassen, falls keines gesetzt ist)."),
		"login": N_("Mit Benutzername und Passwort anmelden."),
		"qc": N_("Anmeldung ohne Passwort-Eingabe: Code in der Jellyfin-App/Web unter Benutzer > Quick Connect bestätigen."),
		"discover": N_("Sucht Jellyfin-Server im lokalen Netzwerk."),
	}

	def build(self):
		self["status"].setText("")
		masked = "*" * len(self.password) if self.password else _("(leer)")
		rows = [
			text_row("server", _("Server"), ROW_W, 70, value=self.server or _("(nicht gesetzt)"), value_width=820, value_color=C_ACCENT),
			text_row("user", _("Benutzer"), ROW_W, 70, value=self.username or _("(nicht gesetzt)"), value_width=820, value_color=C_ACCENT),
			text_row("pass", _("Passwort"), ROW_W, 70, value=masked, value_width=820, value_color=C_ACCENT),
			text_row("login", _(">  Anmelden"), ROW_W, 70),
			text_row("qc", _(">  Mit Quick Connect anmelden"), ROW_W, 70),
			text_row("discover", _(">  Server im Netzwerk suchen"), ROW_W, 70, color=C_DIM),
		]
		idx = self["list"].getSelectedIndex() if self["list"].list else 0
		self["list"].setList(rows)
		self["list"].moveToIndex(idx)
		self.update_description()

	def update_description(self):
		cur = self["list"].getCurrent()
		if cur:
			self["description"].setText(_(self.DESCRIPTIONS.get(cur[0], "")))

	def key_ok(self):
		cur = self["list"].getCurrent()
		if not cur:
			return
		key = cur[0]
		if key == "server":
			self.session.openWithCallback(self.set_server, VirtualKeyBoard, title=_("Server-Adresse"), text=self.server or "http://")
		elif key == "user":
			self.session.openWithCallback(self.set_user, VirtualKeyBoard, title=_("Benutzername"), text=self.username)
		elif key == "pass":
			self.session.openWithCallback(self.set_pass, VirtualKeyBoard, title=_("Passwort"), text="")
		elif key == "login":
			self.login()
		elif key == "qc":
			self.quick_connect()
		elif key == "discover":
			self.discover()

	def set_server(self, text):
		if text is not None:
			self.server = normalize_server(text)
			self.build()

	def set_user(self, text):
		if text is not None:
			self.username = text.strip()
			self.build()

	def set_pass(self, text):
		if text is not None:
			self.password = text
			self.build()

	def error(self, err):
		self["status"].setText(_("Fehler: %s") % err)

	def check_server(self):
		if not self.server:
			self["status"].setText(_("Bitte zuerst die Server-Adresse eingeben (oder blaue Taste: Server suchen)."))
			return False
		return True

	def login(self):
		if not self.check_server():
			return
		if not self.username:
			self["status"].setText(_("Bitte einen Benutzernamen eingeben."))
			return
		cl = self.cl
		server, user, pw = self.server, self.username, self.password

		def work():
			cl.server = normalize_server(server)
			cl.token = ""
			cl.public_info()
			cl.authenticate(user, pw)
			return cl

		def ok(res):
			jfconfig.save_login(cl)
			self.close("ok")
		self["status"].setText(_("Melde an ..."))
		self.run(work, callback=ok, errback=self.error)

	def quick_connect(self):
		if not self.check_server():
			return
		cl = self.cl
		server = self.server

		def work():
			cl.server = normalize_server(server)
			cl.token = ""
			cl.public_info()
			return cl.quickconnect_initiate()

		def ok(res):
			self["status"].setText("")
			self.session.openWithCallback(self.qc_done, QuickConnectScreen, res.get("Code", "?"), res.get("Secret"))
		self["status"].setText(_("Starte Quick Connect ..."))
		self.run(work, callback=ok, errback=self.error)

	def qc_done(self, result=None):
		if result == "ok":
			jfconfig.save_login(self.cl)
			self.close("ok")
		elif result:
			self["status"].setText(str(result))

	def discover(self):
		def ok(servers):
			if not servers:
				self["status"].setText(_("Kein Server gefunden. Adresse bitte manuell eingeben."))
				return
			self["status"].setText("")
			lst = [("%s  (%s)" % (s["Name"], s["Address"]), s["Address"]) for s in servers]
			self.session.openWithCallback(self.server_chosen, ChoiceBox, title=_("Gefundene Jellyfin-Server"), list=lst)
		self["status"].setText(_("Suche Server im Netzwerk ..."))
		self.run(discover_servers, 2.5, callback=ok, errback=self.error)

	def server_chosen(self, choice):
		if choice is not None:
			self.server = choice[1]
			self.build()
			self["list"].moveToIndex(1)


class QuickConnectScreen(JFScreen):
	def __init__(self, session, code, secret):
		JFScreen.__init__(self, session)
		self.skin = quickconnect_skin()
		self.skinName = "JellyfinE2QuickConnect"
		self.secret = secret
		self.polls = 0
		self.checking = False
		self["title"] = Label(_("Quick Connect"))
		self["text"] = Label(_("Öffne Jellyfin am Handy oder PC, gehe zu Benutzer > Quick Connect und gib diesen Code ein:"))
		self["code"] = Label(code)
		self["status"] = Label(_("Warte auf Bestätigung ..."))
		self["key_red"] = Label(_("Abbrechen"))
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
			"cancel": self.close,
			"red": self.close,
		}, -1)
		self.timer = eTimer()
		self.timer.callback.append(self.poll)
		self.onLayoutFinish.append(lambda: self.timer.start(3000, False))
		self.onClose.append(self.timer.stop)

	def poll(self):
		if self.checking:
			return
		self.polls += 1
		if self.polls > 100:  # ~5 minutes
			self.timer.stop()
			self.close(_("Quick Connect abgelaufen - bitte erneut versuchen."))
			return
		cl = self.cl
		secret = self.secret

		def work():
			if cl.quickconnect_check(secret):
				cl.quickconnect_authenticate(secret)
				return True
			return False

		def ok(done):
			self.checking = False
			if done:
				self.timer.stop()
				self.close("ok")

		def fail(err):
			self.checking = False
			self["status"].setText(_("Fehler: %s") % err)
		self.checking = True
		self.run(work, callback=ok, errback=fail)
