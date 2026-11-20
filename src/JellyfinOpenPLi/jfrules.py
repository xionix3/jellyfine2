# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
# Jellyfin for Enigma2 - user defined lists ("Meine Listen"), pure python
from __future__ import absolute_import

from .jfi18n import _, N_, decimal

import copy
import json
import random
import time

from .jfutil import parse_date

YES_NO = [(True, N_("Ja")), (False, N_("Nein"))]

# id, label, choices (None = special editor), help, only_for_types
RULE_FIELDS = [
	("name", N_("Name"), None, N_("OK öffnet die Tastatur."), None),
	("type", N_("Inhalt"), [("Movie", N_("Filme")), ("Series", N_("Serien (mit neuen Folgen)")), ("Episode", N_("Episoden")), ("Movie,Series", N_("Filme & Serien"))],
		N_("Serien werden nach dem Datum der zuletzt hinzugefügten Folge sortiert."), None),
	("library", N_("Bibliothek"), None, N_("OK wählt eine Bibliothek (oder alle)."), None),
	("date_field", N_("Was ist 'neu'?"), [("added", N_("Neu auf dem Server")), ("released", N_("Neu erschienen (Premiere)"))],
		N_("'Neu auf dem Server' = Hinzufügedatum, 'Neu erschienen' = Erscheinungs-/Ausstrahlungsdatum."), None),
	("days", N_("Zeitraum"), [("0", N_("Unbegrenzt")), ("3", N_("3 Tage")), ("7", N_("7 Tage")), ("14", N_("14 Tage")), ("30", N_("30 Tage")), ("60", N_("60 Tage")),
		("90", N_("90 Tage")), ("180", N_("6 Monate")), ("365", N_("1 Jahr")), ("730", N_("2 Jahre"))], N_("Nur Titel, die in diesem Zeitraum neu sind."), None),
	("unplayed", N_("Nur ungesehene"), YES_NO, "", None),
	("my_series", N_("Nur Serien, die ich schaue"), YES_NO, N_("Serien mit Fortschritt ('Als Nächstes') und Favoriten."), ("Episode",)),
	("group", N_("Pro Serie zusammenfassen"), YES_NO, N_("Eine Kachel pro Serie mit Anzahl neuer Folgen."), ("Episode",)),
	("min_rating", N_("Mindestbewertung"), [("0", N_("Egal")), ("5", N_("ab 5")), ("6", N_("ab 6")), ("6.5", N_("ab 6,5")), ("7", N_("ab 7")), ("7.5", N_("ab 7,5")), ("8", N_("ab 8"))], "", None),
	("genre", N_("Genre"), None, N_("OK wählt ein Genre (oder alle)."), None),
	("sort", N_("Sortierung"), [("new", N_("Neueste zuerst")), ("old", N_("Älteste zuerst")), ("rating", N_("Beste Bewertung")), ("name", N_("Name A-Z")), ("random", N_("Zufällig"))], "", None),
	("limit", N_("Max. Einträge"), [("50", "50"), ("100", "100"), ("200", "200"), ("500", "500")], "", None),
	("home", N_("Auf der Startseite"), YES_NO, N_("Liste als eigener Bereich auf der Startseite."), None),
]

TEMPLATE = {
	"id": "", "name": N_("Neue Liste"), "type": "Movie", "library": "", "library_name": "", "date_field": "added", "days": "30",
	"unplayed": True, "my_series": False, "group": False, "min_rating": "0", "genre": "", "sort": "new", "limit": "100", "home": True,
}

DEFAULT_RULES = [
	dict(TEMPLATE, id="new-movies", name=N_("Neue Filme"), type="Movie", days="30"),
	dict(TEMPLATE, id="new-episodes", name=N_("Neue Episoden meiner Serien"), type="Episode", days="30", my_series=True, group=True),
	dict(TEMPLATE, id="new-series", name=N_("Serien mit neuen Folgen"), type="Series", days="30", home=False),
	dict(TEMPLATE, id="released", name=N_("Neu erschienen"), type="Movie,Series", date_field="released", days="365", unplayed=False, home=False),
]

MAX_PAGES = 15
CHUNK = 100


def new_rule():
	r = dict(TEMPLATE)
	r["id"] = "r%x" % int(time.time() * 1000)
	return r


def load_rules(text):
	if not text:
		return copy.deepcopy(DEFAULT_RULES)
	try:
		data = json.loads(text)
	except ValueError:
		return copy.deepcopy(DEFAULT_RULES)
	out = []
	for r in data if isinstance(data, list) else []:
		if isinstance(r, dict):
			full = dict(TEMPLATE)
			full.update(r)
			out.append(full)
	return out


def dump_rules(rules):
	return json.dumps(rules, ensure_ascii=True, separators=(",", ":"))


def rule_name(rule):
	"""Display name of a list; the default lists carry their German name and are shown translated."""
	return _(rule.get("name") or "") or "?"


def choice_label(field, value):
	for f in RULE_FIELDS:
		if f[0] == field and f[2]:
			for v, label in f[2]:
				if v == value:
					return _(label)
	return str(value)


def field_applies(field, rule):
	for f in RULE_FIELDS:
		if f[0] == field:
			return f[4] is None or rule.get("type") in f[4]
	return True


def rule_summary(rule):
	parts = [choice_label("type", rule.get("type"))]
	if rule.get("library_name"):
		parts.append(rule["library_name"])
	days = rule.get("days") or "0"
	if days != "0":
		parts.append("%s: %s" % (_("neu erschienen") if rule.get("date_field") == "released" else _("neu"), choice_label("days", days)))
	if rule.get("unplayed"):
		parts.append(_("ungesehen"))
	if rule.get("type") == "Episode" and rule.get("my_series"):
		parts.append(_("meine Serien"))
	if rule.get("genre"):
		parts.append(rule["genre"])
	if rule.get("min_rating") not in (None, "", "0"):
		parts.append(_("ab %s") % decimal(rule["min_rating"]))
	parts.append(choice_label("sort", rule.get("sort")))
	return "  |  ".join(parts)


def item_date(item, released=False):
	if released:
		return parse_date(item.get("PremiereDate"))
	if item.get("Type") in ("Series", "Season", "BoxSet", "MusicAlbum", "Folder"):
		return parse_date(item.get("DateLastMediaAdded")) or parse_date(item.get("DateCreated"))
	return parse_date(item.get("DateCreated"))


def iso_utc(ts):
	return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))


def _base_params(rule, types):
	params = {"recursive": True, "includeItemTypes": types}
	if rule.get("library"):
		params["parentId"] = rule["library"]
	if rule.get("unplayed"):
		params["filters"] = "IsUnplayed"
	try:
		rating = float(rule.get("min_rating") or 0)
	except ValueError:
		rating = 0
	if rating > 0:
		params["minCommunityRating"] = rating
	if rule.get("genre"):
		params["genres"] = rule["genre"]
	return params


def _date_sort(types, released):
	if released:
		return "PremiereDate,ProductionYear,SortName"
	if types == "Series":
		return "DateLastContentAdded,SortName"
	return "DateCreated,SortName"


def _fetch(cl, params, need, stop=None, accept=None):
	out = []
	start = 0
	for _page in range(MAX_PAGES):
		res = cl.items(startIndex=start, limit=CHUNK, enableTotalRecordCount=False, **params)
		batch = res.get("Items") or []
		done = False
		for it in batch:
			if stop is not None and stop(it):
				done = True
				break
			if accept is None or accept(it):
				out.append(it)
				if len(out) >= need:
					done = True
					break
		start += len(batch)
		if done or len(batch) < CHUNK:
			break
	return out


def _client_sort(items, sort, released):
	if sort == "new":
		items.sort(key=lambda it: item_date(it, released), reverse=True)
	elif sort == "old":
		items.sort(key=lambda it: item_date(it, released))
	elif sort == "rating":
		items.sort(key=lambda it: it.get("CommunityRating") or 0, reverse=True)
	elif sort == "name":
		items.sort(key=lambda it: (it.get("SortName") or it.get("Name") or "").lower())
	elif sort == "random":
		random.shuffle(items)
	return items


def my_series_ids(cl):
	ids = set()
	for e in cl.next_up(limit=300, disableFirstEpisode=True, enableRewatching=False):
		if e.get("SeriesId"):
			ids.add(e["SeriesId"])
	for e in cl.resume(limit=100):
		if e.get("SeriesId"):
			ids.add(e["SeriesId"])
	fav = cl.items(includeItemTypes="Series", filters="IsFavorite", recursive=True, limit=300, enableTotalRecordCount=False)
	for s in fav.get("Items") or []:
		ids.add(s.get("Id"))
	return ids


def group_episodes(episodes):
	groups = []
	index = {}
	for e in episodes:
		key = e.get("SeriesId") or e.get("Id")
		if key not in index:
			index[key] = len(groups)
			groups.append([])
		groups[index[key]].append(e)
	out = []
	for eps in groups:
		rep = dict(eps[0])
		first = min(eps, key=lambda e: (e.get("ParentIndexNumber") or 0, e.get("IndexNumber") or 0))
		rep["_jf_new_count"] = len(eps)
		rep["_jf_focus"] = first
		if len(eps) > 1:
			rep["_jf_label"] = _("%s (%d neu)") % (rep.get("SeriesName") or rep.get("Name") or "", len(eps))
		out.append(rep)
	return out


def run_rule(cl, rule, limit=None, now=None):
	"""Execute a rule against the server and return the matching items."""
	now = now or time.time()
	limit = int(limit or rule.get("limit") or 100)
	types = rule.get("type") or "Movie"
	released = rule.get("date_field") == "released"
	sort = rule.get("sort") or "new"
	try:
		days = int(rule.get("days") or 0)
	except ValueError:
		days = 0
	cutoff = now - days * 86400 if days else None
	episodes = types == "Episode"
	grouping = episodes and rule.get("group")
	accept = None
	if episodes and rule.get("my_series"):
		series = my_series_ids(cl)
		if not series:
			return []
		accept = lambda it: it.get("SeriesId") in series  # noqa: E731
	need = min(1000, limit * 6) if grouping else limit

	def query(t):
		params = _base_params(rule, t)
		if released:
			if cutoff:
				params["minPremiereDate"] = iso_utc(cutoff)
			if sort in ("new", "old"):
				params.update(sortBy=_date_sort(t, True), sortOrder="Descending" if sort == "new" else "Ascending")
				return _fetch(cl, params, need, accept=accept)
			if sort == "rating":
				params.update(sortBy="CommunityRating,SortName", sortOrder="Descending")
			elif sort == "name":
				params.update(sortBy="SortName", sortOrder="Ascending")
			else:
				params.update(sortBy="Random", sortOrder="Ascending")
			return _fetch(cl, params, need, accept=accept)
		if cutoff:
			# walk newest first, stop at the cutoff, sort locally afterwards
			params.update(sortBy=_date_sort(t, False), sortOrder="Descending")
			return _fetch(cl, params, need if sort == "new" else 1000, stop=lambda it: item_date(it) < cutoff, accept=accept)
		if sort in ("new", "old"):
			params.update(sortBy=_date_sort(t, False), sortOrder="Descending" if sort == "new" else "Ascending")
			return _fetch(cl, params, need, accept=accept)
		if sort == "rating":
			params.update(sortBy="CommunityRating,SortName", sortOrder="Descending")
		elif sort == "name":
			params.update(sortBy="SortName", sortOrder="Ascending")
		else:
			params.update(sortBy="Random", sortOrder="Ascending")
		return _fetch(cl, params, need, accept=accept)

	if types == "Movie,Series" and not released:
		items = query("Movie") + query("Series")
	else:
		items = query(types)
	if not (released and sort in ("new", "old")):
		_client_sort(items, sort, released)
	elif types == "Movie,Series":
		_client_sort(items, sort, True)
	if grouping:
		items = group_episodes(items)
	return items[:limit]
