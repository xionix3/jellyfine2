# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 xionix
# Jellyfin for Enigma2 - update check against the GitHub releases of xionix3/jellyfine2
from __future__ import absolute_import

import json
import os
import re
import time

from .jfapi import CLIENT_VERSION

REPO = "xionix3/jellyfine2"
API_URL = "https://api.github.com/repos/%s/releases/latest" % REPO
ASSET = "enigma2-plugin-extensions-jellyfine2_all.ipk"
SUMS = "SHA256SUMS"
TARGET = "/tmp/jellyfine2_update.ipk"
CHECK_INTERVAL = 12 * 3600
USER_AGENT = "JellyfinE2/%s (Enigma2; +https://github.com/%s)" % (CLIENT_VERSION, REPO)


class UpdateError(Exception):
	pass


def parse_version(text):
	"""'v1.2.10' -> (1, 2, 10); unknown parts count as 0."""
	nums = re.findall(r"\d+", text or "")
	return tuple(int(n) for n in nums[:3]) + (0,) * (3 - min(3, len(nums)))


def is_newer(remote, local=CLIENT_VERSION):
	return parse_version(remote) > parse_version(local)


def _open(url, timeout=15):
	try:
		from urllib.request import Request, urlopen
	except ImportError:  # pragma: no cover - python 2
		from urllib2 import Request, urlopen
	req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json, */*"})
	return urlopen(req, timeout=timeout)


def _get(url, timeout=15, limit=64 * 1024 * 1024):
	try:
		resp = _open(url, timeout)
		data = resp.read(limit + 1)
	except Exception as e:
		raise UpdateError("%s: %s" % (url.split("/")[2] if "//" in url else url, e))
	if len(data) > limit:
		raise UpdateError("Download zu groß")
	return data


def check():
	"""Returns {'version', 'notes', 'url', 'sums_url', 'page'} if a newer release exists, else None."""
	try:
		info = json.loads(_get(API_URL).decode("utf-8"))
	except ValueError:
		raise UpdateError("Ungültige Antwort von GitHub")
	if info.get("draft") or info.get("prerelease"):
		return None
	tag = info.get("tag_name") or ""
	if not is_newer(tag):
		return None
	url = sums = None
	for a in info.get("assets") or []:
		if a.get("name") == ASSET:
			url = a.get("browser_download_url")
		elif a.get("name") == SUMS:
			sums = a.get("browser_download_url")
	if not url:
		for a in info.get("assets") or []:
			if (a.get("name") or "").endswith("_all.ipk"):
				url = a.get("browser_download_url")
				break
	if not url:
		return None  # release without package (CI still building)
	return {"version": tag.lstrip("vV"), "notes": release_notes(info.get("body") or ""), "url": url, "sums_url": sums,
		"page": info.get("html_url") or ""}


def release_notes(body, max_lines=8):
	"""Short plain text of the release notes for a message box (only the change list)."""
	lines = []
	for line in body.replace("\r", "").split("\n"):
		s = line.strip()
		if s.startswith("- ") or s.startswith("* "):
			s = re.sub(r"\*\*|__|`", "", s[2:]).strip()
			s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
			lines.append("- " + (s if len(s) <= 90 else s[:87] + "..."))
		if len(lines) >= max_lines:
			lines.append("...")
			break
	return "\n".join(lines)


def download(info, target=TARGET):
	"""Downloads the package and verifies it against SHA256SUMS of the release. Returns the path."""
	data = _get(info["url"])
	if data[:8] != b"!<arch>\n":
		raise UpdateError("Die heruntergeladene Datei ist kein IPK-Paket")
	if info.get("sums_url"):
		sums = _get(info["sums_url"], limit=64 * 1024).decode("utf-8", "replace")
		want = None
		name = info["url"].rsplit("/", 1)[-1]
		for line in sums.splitlines():
			parts = line.split()
			if len(parts) >= 2 and parts[-1].lstrip("*") == name:
				want = parts[0].lower()
		try:
			from hashlib import sha256
		except ImportError:
			raise UpdateError("Prüfsumme kann nicht geprüft werden (hashlib fehlt) - bitte manuell aktualisieren")
		if want and sha256(data).hexdigest() != want:
			raise UpdateError("Prüfsumme stimmt nicht - Update abgebrochen")
	tmp = target + ".part"
	with open(tmp, "wb") as f:
		f.write(data)
	os.rename(tmp, target)
	return target


def due(last_check, now=None):
	try:
		last = float(last_check or 0)
	except ValueError:
		last = 0
	return (now or time.time()) - last >= CHECK_INTERVAL


def install_command(path=TARGET):
	return "opkg install --force-reinstall --force-downgrade %s; rm -f %s" % (path, path)


class Updater(object):
	"""GUI part: ask, download (worker thread), install with opkg, offer an Enigma2 restart."""

	def __init__(self, screen):
		self.screen = screen
		self.session = screen.session
		self.console = None

	def run_check(self, manual=False):
		from . import jfconfig
		if not manual and (not jfconfig.get_bool("update_check") or not due(jfconfig.get_update_stamp())):
			return
		jfconfig.set_update_stamp(time.time())

		def ok(info):
			if info:
				self.offer(info)
			elif manual:
				self.screen.info("Das Plugin ist aktuell (Version %s)." % CLIENT_VERSION, timeout=5)

		def fail(err):
			if manual:
				self.screen.show_error(err, "Update-Prüfung fehlgeschlagen")
			else:
				print("[Jellyfin] update check failed: %s" % err)
		self.screen.run(check, callback=ok, errback=fail, pool="bg", status="Suche nach Updates ..." if manual else None)

	def offer(self, info):
		from Screens.MessageBox import MessageBox
		text = "Jellyfin für Enigma2 %s ist verfügbar (installiert: %s).\n\n%s\n\nJetzt installieren?" % (
			info["version"], CLIENT_VERSION, info["notes"] or "")
		self.session.openWithCallback(lambda yes=False: yes and self.install(info), MessageBox, text.replace("\n\n\n", "\n\n"),
			MessageBox.TYPE_YESNO, default=True)

	def install(self, info):
		def downloaded(path):
			from Components.Console import Console
			self.screen.set_busy(True, "Installiere Update ...")
			self.console = Console()
			self.console.ePopen(install_command(path), self.installed, [info])
		self.screen.run(download, info, callback=downloaded, pool="bg", status="Lade Update %s ..." % info["version"],
			errback=lambda e: self.screen.show_error(e, "Update fehlgeschlagen"))

	def installed(self, output, retval, extra=None):
		from Screens.MessageBox import MessageBox
		self.screen.set_busy(False)
		info = (extra or [{}])[0]
		if retval:
			self.screen.show_error(UpdateError((output or "").strip()[-400:] or "opkg Fehler %s" % retval), "Update fehlgeschlagen")
			return
		self.session.openWithCallback(self.restart, MessageBox,
			"Version %s wurde installiert.\nEnigma2 jetzt neu starten, damit das Update aktiv wird?" % info.get("version", "?"),
			MessageBox.TYPE_YESNO, default=True)

	def restart(self, yes=False):
		if yes:
			from Screens.Standby import TryQuitMainloop
			self.session.open(TryQuitMainloop, 3)
