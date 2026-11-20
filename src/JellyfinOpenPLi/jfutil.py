# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
# Jellyfin for Enigma2 - small pure-python helpers (no enigma imports)
from __future__ import absolute_import, division

import calendar
import time

TICKS_PER_SECOND = 10000000


def parse_date(text):
	"""Jellyfin ISO date ('2024-05-01T12:34:56.0000000Z') -> epoch seconds (0 if unknown)."""
	if not text or len(text) < 10:
		return 0
	try:
		base = text[:19] if len(text) >= 19 else text[:10] + "T00:00:00"
		return calendar.timegm(time.strptime(base, "%Y-%m-%dT%H:%M:%S"))
	except (ValueError, OverflowError):
		return 0


def is_new(item, days, now=None):
	"""Added (or got new episodes) within the last `days` days."""
	if not days:
		return False
	if item.get("Type") in ("Series", "Season", "BoxSet", "MusicAlbum"):
		ts = parse_date(item.get("DateLastMediaAdded")) or parse_date(item.get("DateCreated"))
	else:
		ts = parse_date(item.get("DateCreated"))
	return bool(ts) and ((now or time.time()) - ts) <= days * 86400


def ticks_to_seconds(ticks):
	try:
		return int(ticks or 0) // TICKS_PER_SECOND
	except (TypeError, ValueError):
		return 0


def seconds_to_ticks(seconds):
	return int(seconds * TICKS_PER_SECOND)


def fmt_clock(seconds):
	"""1:02:03 / 4:05"""
	seconds = max(0, int(seconds))
	h, rem = divmod(seconds, 3600)
	m, s = divmod(rem, 60)
	if h:
		return "%d:%02d:%02d" % (h, m, s)
	return "%d:%02d" % (m, s)


def fmt_runtime(ticks):
	"""'2 Std. 12 Min.' / '45 Min.'"""
	minutes = ticks_to_seconds(ticks) // 60
	if minutes <= 0:
		return ""
	h, m = divmod(minutes, 60)
	if h and m:
		return "%d Std. %d Min." % (h, m)
	if h:
		return "%d Std." % h
	return "%d Min." % m


def fmt_ends_at(ticks, position_ticks=0):
	remaining = ticks_to_seconds(ticks) - ticks_to_seconds(position_ticks)
	if remaining <= 0:
		return ""
	return "endet um %s" % time.strftime("%H:%M", time.localtime(time.time() + remaining))


def fmt_rating(value):
	try:
		v = float(value)
	except (TypeError, ValueError):
		return ""
	if v <= 0:
		return ""
	return ("%.1f" % v).replace(".", ",")


def episode_code(item):
	s = item.get("ParentIndexNumber")
	e = item.get("IndexNumber")
	if s is None and e is None:
		return ""
	if s is None:
		return "E%02d" % e
	if e is None:
		return "S%02d" % s
	end = item.get("IndexNumberEnd")
	if end and end != e:
		return "S%02dE%02d-%02d" % (s, e, end)
	return "S%02dE%02d" % (s, e)


def display_title(item):
	"""Title for grids/lists: episodes get 'Series - S01E02'."""
	if item.get("_jf_label"):
		return item["_jf_label"]
	t = item.get("Type")
	name = item.get("Name") or ""
	if t == "Episode":
		code = episode_code(item)
		series = item.get("SeriesName") or ""
		if series:
			return "%s %s" % (series, code) if code else series
		return "%s %s" % (code, name) if code else name
	if t == "Audio":
		artist = ", ".join(item.get("Artists") or []) or item.get("AlbumArtist") or ""
		return "%s - %s" % (artist, name) if artist else name
	return name


def subtitle_line(item):
	"""Second line under a cover."""
	t = item.get("Type")
	if t == "Episode":
		return item.get("Name") or ""
	if t == "Series":
		start = item.get("ProductionYear")
		end = item.get("EndDate")
		status = item.get("Status")
		if start and status == "Continuing":
			return "%s - heute" % start
		if start and end:
			return "%s - %s" % (start, end[:4])
		return str(start or "")
	if t == "MusicAlbum":
		return item.get("AlbumArtist") or ", ".join(item.get("Artists") or [])
	if item.get("ProductionYear"):
		return str(item.get("ProductionYear"))
	return ""


def played_percentage(item):
	ud = item.get("UserData") or {}
	pct = ud.get("PlayedPercentage")
	if pct:
		try:
			return max(0, min(100, int(pct)))
		except (TypeError, ValueError):
			pass
	pos = ud.get("PlaybackPositionTicks") or 0
	run = item.get("RunTimeTicks") or 0
	if pos and run:
		return max(0, min(100, int(pos * 100 // run)))
	return 0


def is_played(item):
	return bool((item.get("UserData") or {}).get("Played"))


def is_favorite(item):
	return bool((item.get("UserData") or {}).get("IsFavorite"))


def resume_ticks(item):
	return int((item.get("UserData") or {}).get("PlaybackPositionTicks") or 0)


def unplayed_count(item):
	try:
		return int((item.get("UserData") or {}).get("UnplayedItemCount") or 0)
	except (TypeError, ValueError):
		return 0


LANG_NAMES = {
	"ger": "Deutsch", "deu": "Deutsch", "de": "Deutsch",
	"eng": "Englisch", "en": "Englisch",
	"fre": "Französisch", "fra": "Französisch", "fr": "Französisch",
	"spa": "Spanisch", "es": "Spanisch",
	"ita": "Italienisch", "it": "Italienisch",
	"jpn": "Japanisch", "ja": "Japanisch",
	"kor": "Koreanisch", "ko": "Koreanisch",
	"tur": "Türkisch", "tr": "Türkisch",
	"rus": "Russisch", "ru": "Russisch",
	"pol": "Polnisch", "pl": "Polnisch",
	"dut": "Niederländisch", "nld": "Niederländisch", "nl": "Niederländisch",
	"por": "Portugiesisch", "pt": "Portugiesisch",
	"chi": "Chinesisch", "zho": "Chinesisch", "zh": "Chinesisch",
	"hin": "Hindi", "ara": "Arabisch", "swe": "Schwedisch", "dan": "Dänisch",
	"nor": "Norwegisch", "fin": "Finnisch", "cze": "Tschechisch", "ces": "Tschechisch",
	"hun": "Ungarisch", "gre": "Griechisch", "ell": "Griechisch", "hrv": "Kroatisch",
	"srp": "Serbisch", "bos": "Bosnisch", "und": "Unbekannt",
}


def lang_name(code):
	if not code:
		return ""
	return LANG_NAMES.get(code.lower(), code)


def channel_name(ch):
	return {1: "Mono", 2: "Stereo", 6: "5.1", 7: "6.1", 8: "7.1"}.get(ch or 0, "%sch" % ch if ch else "")


def stream_label(stream):
	"""Human readable label for an audio/subtitle MediaStream."""
	if stream.get("DisplayTitle") and stream.get("Type") == "Subtitle":
		title = stream.get("DisplayTitle")
	else:
		parts = []
		lang = lang_name(stream.get("Language"))
		if lang:
			parts.append(lang)
		codec = (stream.get("Codec") or "").upper()
		if codec:
			parts.append(codec)
		if stream.get("Type") == "Audio":
			ch = channel_name(stream.get("Channels"))
			if ch:
				parts.append(ch)
		title = " ".join(parts) or stream.get("DisplayTitle") or "Spur %s" % stream.get("Index")
		extra = stream.get("Title")
		if extra and extra not in title:
			title = "%s (%s)" % (title, extra)
	flags = []
	if stream.get("IsDefault"):
		flags.append("Standard")
	if stream.get("IsForced"):
		flags.append("Erzwungen")
	if stream.get("IsExternal"):
		flags.append("Extern")
	if flags and stream.get("Type") == "Subtitle":
		title = "%s [%s]" % (title, ", ".join(flags))
	return title


def video_label(stream):
	if not stream:
		return ""
	w = stream.get("Width") or 0
	h = stream.get("Height") or 0
	res = ""
	if w >= 3200 or h >= 1800:
		res = "4K"
	elif w >= 1800 or h >= 1000:
		res = "1080p"
	elif w >= 1200 or h >= 700:
		res = "720p"
	elif h:
		res = "%dp" % h
	parts = [p for p in (res, (stream.get("Codec") or "").upper()) if p]
	vr = stream.get("VideoRangeType") or stream.get("VideoRange")
	if vr and vr.upper() not in ("SDR", "UNKNOWN"):
		parts.append(vr.upper())
	return " ".join(parts)


def media_streams(item, media_source=None):
	if media_source is None:
		sources = item.get("MediaSources") or []
		media_source = sources[0] if sources else {}
	return media_source.get("MediaStreams") or item.get("MediaStreams") or []


def safe_int(v, default=0):
	try:
		return int(v)
	except (TypeError, ValueError):
		return default


def clean_text(text):
	if not text:
		return ""
	# Jellyfin overviews may contain basic HTML
	for tag in ("<br>", "<br/>", "<br />", "<p>", "</p>"):
		text = text.replace(tag, "\n")
	out = []
	inside = False
	for ch in text:
		if ch == "<":
			inside = True
			continue
		if ch == ">" and inside:
			inside = False
			continue
		if not inside:
			out.append(ch)
	text = "".join(out)
	text = text.replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'").replace("&lt;", "<").replace("&gt;", ">").replace("&nbsp;", " ")
	while "\n\n\n" in text:
		text = text.replace("\n\n\n", "\n\n")
	return text.strip()


def norm_text(text):
	"""Lowercase, without accents and punctuation: 'Amélie!' -> 'amelie'."""
	import unicodedata
	text = unicodedata.normalize("NFKD", text or "")
	text = "".join(c for c in text if not unicodedata.combining(c)).lower()
	out = []
	for c in text:
		out.append(c if c.isalnum() else " ")
	return " ".join("".join(out).split())


TYPE_ORDER = {"Movie": 0, "Series": 0, "BoxSet": 1, "Person": 1, "MusicArtist": 2, "MusicAlbum": 2, "Season": 3, "Episode": 4,
	"Video": 4, "MusicVideo": 4, "Audio": 5}


def match_rank(term, item):
	"""0 exact title, 1 title starts with term, 2 a word starts with term, 3 contains term,
	4 contains all words of the term, 9 no title match."""
	t = norm_text(term)
	if not t:
		return 9
	words = t.split()
	best = 9
	for field in ("Name", "OriginalTitle", "SortName"):
		n = norm_text(item.get(field))
		if not n:
			continue
		if n == t:
			r = 0
		elif n.startswith(t):
			r = 1
		elif (" " + n).find(" " + t) >= 0:
			r = 2
		elif t in n or t.replace(" ", "") in n.replace(" ", ""):
			r = 3
		elif len(words) > 1 and all(w in n for w in words):
			r = 4
		else:
			continue
		best = min(best, r)
	return best


def rank_search(term, items):
	"""Best title matches first, movies/series before episodes; keeps the server's order otherwise.

	Results that do not contain the search term at all (some servers/plugins search fuzzy) go to the end."""
	keyed = [(match_rank(term, it), TYPE_ORDER.get(it.get("Type"), 6), i, it) for i, it in enumerate(items)]
	keyed.sort(key=lambda k: (min(k[0], 4), k[1] if k[0] < 9 else 0, k[2]))
	return [k[3] for k in keyed]


def strict_matches(term, items):
	"""Only items whose title (or original title) contains the term; best matches first."""
	keyed = [(match_rank(term, it), i, it) for i, it in enumerate(items)]
	return [k[2] for k in sorted((k for k in keyed if k[0] < 9), key=lambda k: (k[0], k[1]))]
