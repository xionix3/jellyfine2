# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 xionix
# Jellyfin for Enigma2 - translations (German source texts, locale/<lang>.po)
#
# Every module imports _ from here (it shadows the Enigma2 builtin _ of the
# enigma2 text domain). Texts in module level tables are marked with N_ and
# translated where they are shown, so a language change needs no restart.
from __future__ import absolute_import

import io
import os

SOURCE = "de"
# (value, label) - each language in its own name
LANGUAGES = (("de", "Deutsch"), ("en", "English"), ("nl", "Nederlands"))
LOCALE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "locale")

# badges with the text drawn into the PNG (scripts/make_assets.py): kind -> {lang: (text, width at 1080p)}
BADGES = {
	"new": {"de": ("NEU", 64), "en": ("NEW", 64), "nl": ("NIEUW", 84)},
	"seen": {"de": ("gesehen", 104), "en": ("watched", 104), "nl": ("bekeken", 104)},
}

_state = {"lang": SOURCE, "catalog": {}}
_cache = {}


def N_(text):
	"""Marks a text for translation without translating it (module level tables)."""
	return text


def _(text):
	if not text:
		return text
	found = _state["catalog"].get(text)
	if isinstance(found, list):
		return found[0]
	return found or text


def ngettext(singular, plural, n):
	"""German, English and Dutch: one form for 1, another for everything else."""
	found = _state["catalog"].get(singular)
	if isinstance(found, list):
		return found[0 if n == 1 else 1]
	return singular if n == 1 else plural


def _unquote(s):
	s = s.strip()
	if len(s) < 2 or s[0] != '"' or s[-1] != '"':
		return ""
	out = []
	i, s = 0, s[1:-1]
	while i < len(s):
		c = s[i]
		if c == "\\" and i + 1 < len(s):
			i += 1
			c = {"n": "\n", "t": "\t", '"': '"', "\\": "\\"}.get(s[i], "\\" + s[i])
		out.append(c)
		i += 1
	return "".join(out)


def parse_po(text):
	"""Minimal .po reader: msgid -> msgstr, plural entries msgid -> [msgstr[0], msgstr[1]]; fuzzy entries are skipped."""
	catalog = {}
	entries = []
	entry, key, fuzzy = None, None, False
	for line in text.splitlines():
		line = line.strip()
		if line.startswith("#,") and "fuzzy" in line:
			fuzzy = True
		elif line.startswith("msgid "):
			entry, key = {"msgid": _unquote(line[6:]), "fuzzy": fuzzy}, "msgid"
			entries.append(entry)
			fuzzy = False
		elif entry is not None and line.startswith(("msgid_plural ", "msgstr")) and " " in line:
			key, value = line.split(" ", 1)
			entry[key] = _unquote(value)
		elif line.startswith('"') and entry is not None and key:
			entry[key] = entry.get(key, "") + _unquote(line)
		elif not line.startswith("#"):
			key = None
	for e in entries:
		if not e["msgid"] or e["fuzzy"]:
			continue
		if "msgid_plural" in e:
			forms = [e.get("msgstr[0]"), e.get("msgstr[1]")]
			if all(forms):
				catalog[e["msgid"]] = forms
		elif e.get("msgstr"):
			catalog[e["msgid"]] = e["msgstr"]
	return catalog


def load_catalog(lang):
	if lang == SOURCE:
		return {}
	if lang not in _cache:
		path = os.path.join(LOCALE_DIR, "%s.po" % lang)
		try:
			with io.open(path, encoding="utf-8") as f:
				_cache[lang] = parse_po(f.read())
		except (IOError, OSError):
			_cache[lang] = {}
	return _cache[lang]


def system_language():
	try:
		from Components.Language import language
		return (language.getLanguage() or "")[:2].lower()
	except Exception:
		return ""


def resolve(setting):
	"""'auto' follows the Enigma2 menu language; languages without translation get English."""
	codes = [code for code, _name in LANGUAGES]
	if setting in codes:
		return setting
	system = system_language()
	if system in codes:
		return system
	return "en" if system else SOURCE


def set_language(setting):
	lang = resolve(setting)
	_state["lang"] = lang
	_state["catalog"] = load_catalog(lang)
	return lang


def current():
	return _state["lang"]


def badge_file(kind, lang):
	return "badge_%s.png" % kind if lang == SOURCE else "badge_%s_%s.png" % (kind, lang)


def badge(kind):
	"""(image file, width at 1080p) of a text badge in the current language."""
	lang = _state["lang"]
	return badge_file(kind, lang), BADGES[kind][lang][1]


def decimal(text):
	"""'7.5' -> '7,5' in German and Dutch."""
	text = str(text)
	return text if _state["lang"] == "en" else text.replace(".", ",")
