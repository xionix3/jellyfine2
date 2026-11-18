# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
# Jellyfin for Enigma2 - plugin entry
from __future__ import absolute_import

from Plugins.Plugin import PluginDescriptor

from . import jfconfig
from .jfapi import CLIENT_VERSION

NAME = "Jellyfin"
DESCRIPTION = "Jellyfin-Client: Filme, Serien und Musik vom eigenen Server"


class Launcher(object):
	"""Keeps the login <-> home loop going until the user leaves the plugin."""

	def __init__(self, session):
		self.session = session

	def start(self):
		if jfconfig.client().logged_in:
			self.open_home()
		else:
			self.open_login()

	def open_home(self):
		from .jfhome import HomeScreen
		self.session.openWithCallback(self.home_closed, HomeScreen)

	def open_login(self):
		from .jflogin import LoginScreen
		self.session.openWithCallback(self.login_closed, LoginScreen)

	def home_closed(self, result=None):
		if result == "login":
			self.open_login()

	def login_closed(self, result=None):
		if result == "ok":
			self.open_home()


def main(session, **kwargs):
	Launcher(session).start()


def menu_entry(menuid, **kwargs):
	if menuid == "mainmenu" and jfconfig.get_bool("mainmenu"):
		return [(NAME, lambda session, **kw: main(session), "jellyfine2", 45)]
	return []


def Plugins(**kwargs):
	plugins = [
		PluginDescriptor(name=NAME, description="%s (v%s)" % (DESCRIPTION, CLIENT_VERSION), where=PluginDescriptor.WHERE_PLUGINMENU, icon="plugin.png", fnc=main),
		PluginDescriptor(name=NAME, description=DESCRIPTION, where=PluginDescriptor.WHERE_MENU, fnc=menu_entry),
	]
	if jfconfig.get_bool("extmenu"):
		plugins.append(PluginDescriptor(name=NAME, description=DESCRIPTION, where=PluginDescriptor.WHERE_EXTENSIONSMENU, fnc=main))
	return plugins
