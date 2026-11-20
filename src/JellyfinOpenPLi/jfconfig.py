# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 xionix
# Jellyfin for Enigma2 - persistent settings
from __future__ import absolute_import

import binascii
import os

from Components.config import config, ConfigSubsection, ConfigText, configfile

from .jfapi import JellyfinClient

config.plugins.jellyfine2 = ConfigSubsection()
_c = config.plugins.jellyfine2
_c.server = ConfigText(default="", fixed_size=False)
_c.username = ConfigText(default="", fixed_size=False)
_c.userid = ConfigText(default="", fixed_size=False)
_c.token = ConfigText(default="", fixed_size=False)
_c.deviceid = ConfigText(default="", fixed_size=False)
_c.servername = ConfigText(default="", fixed_size=False)
_c.serverversion = ConfigText(default="", fixed_size=False)
_c.rules = ConfigText(default="", fixed_size=False)
_c.update_last = ConfigText(default="0", fixed_size=False)


# id, label, choices [(value, label)], default, help
SETTINGS = [
	("playmode", "Wiedergabe-Modus", [
		("auto", "Automatisch (Direkt wenn möglich)"),
		("direct", "Immer direkt (Originaldatei)"),
		("transcode", "Immer transkodieren"),
	], "auto", "Automatisch: Der Server entscheidet anhand der Box-Fähigkeiten, ob direkt abgespielt oder umgewandelt wird."),
	("max_bitrate", "Max. Streaming-Bitrate", [
		("0", "Unbegrenzt"), ("120000000", "120 Mbit/s"), ("80000000", "80 Mbit/s"), ("60000000", "60 Mbit/s"),
		("40000000", "40 Mbit/s"), ("20000000", "20 Mbit/s"), ("10000000", "10 Mbit/s"), ("8000000", "8 Mbit/s"),
		("4000000", "4 Mbit/s"), ("2000000", "2 Mbit/s"),
	], "0", "Dateien mit höherer Bitrate werden vom Server heruntergerechnet (z.B. für Fernzugriff)."),
	("max_width", "Max. Auflösung", [
		("auto", "Automatisch (nach Box)"), ("3840", "4K / UHD (3840)"), ("1920", "Full HD (1920)"), ("1280", "HD (1280)"),
	], "auto", "4K nur auf UHD-Boxen (z.B. SF8008). Höher aufgelöste Videos werden sonst transkodiert."),
	("hevc", "H.265/HEVC direkt abspielen", [("1", "Ja"), ("0", "Nein")], "1", "Die SF8008 und die meisten UHD-Boxen dekodieren HEVC in Hardware."),
	("dts", "DTS direkt abspielen", [("0", "Nein (Server wandelt in AC3)"), ("1", "Ja")], "0", "Nur aktivieren, wenn Box oder AV-Receiver DTS unterstützen."),
	("truehd", "TrueHD direkt abspielen", [("0", "Nein (Server wandelt in AC3)"), ("1", "Ja")], "0", ""),
	("vc1", "VC-1 direkt abspielen", [("0", "Nein"), ("1", "Ja")], "0", ""),
	("vp9", "VP9 direkt abspielen", [("0", "Nein"), ("1", "Ja")], "0", ""),
	("audio_channels", "Max. Audiokanäle (Transkodierung)", [("6", "5.1"), ("8", "7.1"), ("2", "Stereo")], "6", ""),
	("protocol", "Transkodier-Protokoll", [("hls", "HLS (empfohlen)"), ("http", "HTTP-Stream (TS)")], "hls", "HLS erlaubt Spulen in transkodierten Streams."),
	("player", "Player", [], "4097", "4097 = Enigma2 GStreamer. 5001/5002 benötigen das ServiceApp-Plugin."),
	("autoplay_next", "Nächste Episode automatisch", [("1", "Ja"), ("0", "Nein")], "1", "Spielt nach einer Episode die nächste ab."),
	("resume_ask", "Fortsetzen", [("ask", "Nachfragen"), ("resume", "Immer fortsetzen"), ("start", "Immer von vorne")], "ask", "Verhalten bei Titeln mit gespeicherter Position (PLAY-Taste im Raster)."),
	("seek_mode", "Links/Rechts im Player", [("skip", "Springen (-10 s / +30 s)"), ("e2", "Enigma2-Standard (Spulen)")], "skip", ""),
	("show_played", "Gesehen-Markierung im Raster", [("1", "Ja"), ("0", "Nein")], "1", ""),
	("new_days", "NEU-Markierung", [("7", "7 Tage"), ("3", "3 Tage"), ("14", "14 Tage"), ("30", "30 Tage"), ("0", "Aus")], "7",
		"Titel, die in diesem Zeitraum zum Server hinzugefügt wurden (Serien: neue Folgen), bekommen ein NEU-Schild."),
	("home_layout", "Startseite", [("hero", "Modern (großes Titelbild, Kartenreihen)"), ("classic", "Klassisch (Menü links, Poster rechts)")], "hero",
		"Modern: Titelbild des gewählten Films oben, darunter Reihen mit Karten (hoch/runter: Reihe, links/rechts: Titel)."),
	("backdrops", "Hintergrundbilder", [("1", "Ja"), ("0", "Nein (schneller)")], "1", "Zeigt das Hintergrundbild des gewählten Titels auf Startseite, Raster und Detailseite."),
	("rules_first", "Eigene Listen auf der Startseite", [("top", "Ganz oben"), ("after_resume", "Nach 'Weiterschauen'"), ("bottom", "Nach den Bibliotheken")], "top",
		"Position der eigenen Listen (z.B. 'Neue Filme') auf der Startseite. Verwalten unter 'Meine Listen'."),
	("cache_dir", "Bild-Cache", [], "tmp", "RAM ist schnell, wird aber beim Neustart geleert. Auf HDD/USB bleiben Poster erhalten."),
	("verify_ssl", "SSL-Zertifikat prüfen", [("1", "Ja"), ("0", "Nein")], "1", "Für Server mit selbstsigniertem Zertifikat auf 'Nein' stellen."),
	("update_check", "Automatisch nach Updates suchen", [("1", "Ja (beim Start, höchstens 2x täglich)"), ("0", "Nein")], "1",
		"Prüft auf GitHub (xionix3/jellyfine_enigma2_openpli), ob eine neue Version erschienen ist, und bietet die Installation an. Manuell: MENU > Nach Updates suchen."),
	("mainmenu", "Im Hauptmenü anzeigen", [("1", "Ja"), ("0", "Nein")], "1", "Änderung wird nach einem GUI-Neustart wirksam."),
	("extmenu", "Im Erweiterungsmenü (blau) anzeigen", [("1", "Ja"), ("0", "Nein")], "0", "Änderung wird nach einem GUI-Neustart wirksam."),
]

for _sid, _label, _choices, _default, _help in SETTINGS:
	setattr(_c, _sid, ConfigText(default=_default, fixed_size=False))


def serviceapp_installed():
	return os.path.isdir("/usr/lib/enigma2/python/Plugins/SystemPlugins/ServiceApp")


CACHE_MOUNTS = ("/media/hdd", "/media/usb", "/media/usb2", "/media/mmc", "/media/sdcard", "/media/ba")


def cache_choices():
	choices = [("tmp", "RAM (/tmp)")]
	for mp in CACHE_MOUNTS:
		if os.path.ismount(mp):
			choices.append((mp, "%s/jellyfin-cache" % mp))
	return choices


def cache_dir():
	value = getattr(_c, "cache_dir").value
	if value != "tmp" and os.path.ismount(value):
		return os.path.join(value, "jellyfin-cache"), 400 * 1024 * 1024
	return "/tmp/jellyfine2", 80 * 1024 * 1024


def get_update_stamp():
	return _c.update_last.value


def set_update_stamp(ts):
	_c.update_last.value = str(int(ts))
	_c.update_last.save()
	configfile.save()


def load_rules():
	from .jfrules import load_rules as _load
	return _load(_c.rules.value)


def save_rules(rules):
	from .jfrules import dump_rules
	_c.rules.value = dump_rules(rules)
	_c.rules.save()
	configfile.save()


def player_choices():
	choices = [("4097", "Enigma2 GStreamer (4097)")]
	if serviceapp_installed():
		choices += [("5002", "ServiceApp exteplayer3 (5002)"), ("5001", "ServiceApp GStreamer (5001)")]
	return choices


UHD_MODELS = ("sf8008", "sf8008m", "sf8008s", "sx988", "ustym4kpro", "hd51", "hd60", "hd61", "h7", "h9", "h9combo",
	"h9combose", "h10", "dm900", "dm920", "dm820", "osmio4k", "osmio4kplus", "osmini4k", "e4hdultra", "gbquad4k", "gbue4k",
	"gbtrio4k", "gbip4k", "multibox", "pulse4k", "pulse4kmini", "vusolo4k", "vuduo4k", "vuduo4kse", "vuuno4k", "vuuno4kse",
	"vuultimo4k", "vuzero4k", "dinobot4k", "anadol4k", "galaxy4k", "spycat4k", "bre2ze4k", "revo4k", "et11000", "et13000")


def box_name():
	try:
		from Tools.HardwareInfo import HardwareInfo
		name = HardwareInfo().get_device_model()
		if name:
			return name
	except Exception:
		pass
	for path in ("/proc/stb/info/model", "/proc/stb/info/boxtype", "/proc/stb/info/vumodel"):
		try:
			with open(path) as f:
				name = f.read().strip()
				if name:
					return name
		except (IOError, OSError):
			continue
	return "Enigma2"


def is_uhd_box():
	try:
		with open("/proc/stb/video/videomode_choices") as f:
			if "2160" in f.read():
				return True
	except (IOError, OSError):
		pass
	model = box_name().lower()
	return "4k" in model or model in UHD_MODELS


def get(sid):
	value = getattr(_c, sid).value
	if sid == "max_width" and value == "auto":
		return "3840" if is_uhd_box() else "1920"
	if sid == "player":
		valid = [v for v, _ in player_choices()]
		return value if value in valid else "4097"
	return value


def get_int(sid, default=0):
	try:
		return int(get(sid))
	except (TypeError, ValueError):
		return default


def get_bool(sid):
	return get(sid) == "1"


def set_value(sid, value):
	item = getattr(_c, sid)
	item.value = value
	item.save()
	configfile.save()


def choices_for(sid):
	for s in SETTINGS:
		if s[0] == sid:
			if sid == "player":
				return player_choices()
			if sid == "cache_dir":
				return cache_choices()
			if sid == "max_width":
				return s[2]
			return s[2]
	return []


def label_for(sid, value):
	for v, label in choices_for(sid):
		if v == value:
			return label
	return value


def device_id():
	if not _c.deviceid.value:
		_c.deviceid.value = "e2-" + binascii.hexlify(os.urandom(16)).decode("ascii")
		_c.deviceid.save()
		configfile.save()
	return _c.deviceid.value


def playback_options():
	return {
		"mode": get("playmode"),
		"max_bitrate": int(get("max_bitrate") or 0),
		"max_width": int(get("max_width") or 1920),
		"hevc": get_bool("hevc"),
		"dts": get_bool("dts"),
		"truehd": get_bool("truehd"),
		"vc1": get_bool("vc1"),
		"vp9": get_bool("vp9"),
		"audio_channels": int(get("audio_channels") or 6),
		"protocol": get("protocol"),
	}


_client = None


def client():
	global _client
	if _client is None:
		_client = JellyfinClient(
			server=_c.server.value, device_id=device_id(), device_name=box_name(),
			token=_c.token.value, user_id=_c.userid.value, user_name=_c.username.value,
			verify_ssl=get_bool("verify_ssl"))
		ver = _c.serverversion.value
		if ver:
			from .jfapi import parse_version
			_client.server_version = parse_version(ver)
		_client.server_name = _c.servername.value
	_client.verify_ssl = get_bool("verify_ssl")
	return _client


def save_login(cl):
	_c.server.value = cl.server
	_c.username.value = cl.user_name
	_c.userid.value = cl.user_id
	_c.token.value = cl.token
	_c.servername.value = cl.server_name
	_c.serverversion.value = ".".join(str(x) for x in cl.server_version)
	for item in (_c.server, _c.username, _c.userid, _c.token, _c.servername, _c.serverversion):
		item.save()
	configfile.save()


def clear_login():
	cl = client()
	cl.token = ""
	cl.user_id = ""
	_c.token.value = ""
	_c.userid.value = ""
	_c.token.save()
	_c.userid.save()
	configfile.save()


def saved_server():
	return _c.server.value


def saved_username():
	return _c.username.value
