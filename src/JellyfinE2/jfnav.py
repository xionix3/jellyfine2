# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
# Jellyfin for Enigma2 - where to go when an item is selected
from __future__ import absolute_import

FOLDER_TYPES = ("BoxSet", "Folder", "CollectionFolder", "UserView", "Playlist", "PhotoAlbum", "ManualPlaylistsFolder", "Channel", "ChannelFolderItem")
DETAIL_TYPES = ("Movie", "Episode", "Video", "MusicVideo", "Series", "Trailer", "Program", "Recording", "TvChannel")


def _noop(*args):
	pass


def library_spec(view):
	"""Grid spec for a library (user view)."""
	ctype = (view.get("CollectionType") or "").lower()
	params = {"parentId": view["Id"]}
	sortable = True
	sort = 0
	if ctype == "movies":
		params.update(includeItemTypes="Movie", recursive=True)
	elif ctype == "tvshows":
		params.update(includeItemTypes="Series", recursive=True)
	elif ctype == "boxsets":
		params.update(includeItemTypes="BoxSet", recursive=True)
	elif ctype == "music":
		params.update(includeItemTypes="MusicAlbum", recursive=True)
	elif ctype == "musicvideos":
		params.update(includeItemTypes="MusicVideo", recursive=True)
	elif ctype == "trailers":
		params.update(includeItemTypes="Trailer", recursive=True)
	elif ctype == "playlists":
		pass
	else:
		params.update(sortBy="IsFolder,SortName")  # home videos, mixed, folders
	return {"title": view.get("Name", ""), "source": "items", "params": params, "sortable": sortable, "sort": sort, "collection_type": ctype}


def folder_spec(item):
	params = {"parentId": item["Id"]}
	sortable = True
	if item.get("Type") == "BoxSet":
		params.update(sortBy="PremiereDate,ProductionYear,SortName", sortOrder="Ascending")
		sortable = False
	elif item.get("Type") == "Playlist":
		sortable = False  # keep playlist order
	return {"title": item.get("Name", ""), "source": "items", "params": params, "sortable": sortable}


def open_grid(screen, spec, callback=None):
	from .jfgrid import GridScreen
	screen.session.openWithCallback(callback or _noop, GridScreen, spec)


def open_search(screen, text="", done=None):
	"""Keyboard -> result grid (relevance order, restrict by category with the green key)."""
	from Screens.VirtualKeyBoard import VirtualKeyBoard

	def entered(term=None):
		term = (term or "").strip()
		if not term:
			return
		open_grid(screen, {"title": 'Suche: "%s"' % term, "source": "search", "term": term, "categories": True},
			callback=lambda *a: done and done(term))
	screen.session.openWithCallback(entered, VirtualKeyBoard, title="Jellyfin durchsuchen (Filme, Serien, Episoden, Musik, Personen)", text=text or "")


def open_detail(screen, item, callback=None):
	from .jfdetail import DetailScreen
	screen.session.openWithCallback(callback or _noop, DetailScreen, item)


def open_season(screen, episode, callback=None):
	from .jfepisodes import EpisodesScreen
	screen.session.openWithCallback(callback or _noop, EpisodesScreen, series_id=episode.get("SeriesId"),
		season_id=episode.get("SeasonId"), series_name=episode.get("SeriesName", ""), focus_id=episode.get("Id"))


def open_item(screen, item, context=None, index=0, callback=None):
	t = item.get("Type")
	cb = callback or _noop
	focus = item.get("_jf_focus")
	if focus and focus.get("SeriesId"):
		# grouped "new episodes" tile -> straight to the first new episode of that series
		open_season(screen, focus, cb)
		return
	if t in DETAIL_TYPES:
		open_detail(screen, item, cb)
	elif t == "Season":
		from .jfepisodes import EpisodesScreen
		screen.session.openWithCallback(cb, EpisodesScreen, series_id=item.get("SeriesId"), season_id=item["Id"],
			series_name=item.get("SeriesName", ""))
	elif t == "MusicAlbum":
		from .jfepisodes import EpisodesScreen
		screen.session.openWithCallback(cb, EpisodesScreen, album=item)
	elif t == "Audio":
		from .jfplayer import play_item
		play_item(screen, item, context, index, on_finished=cb)
	elif t == "MusicArtist":
		open_grid(screen, {"title": item.get("Name", ""), "source": "items", "sortable": True, "sort": 3,
			"params": {"artistIds": item["Id"], "includeItemTypes": "MusicAlbum", "recursive": True}}, cb)
	elif t == "Person":
		open_grid(screen, {"title": item.get("Name", ""), "source": "items", "sortable": True, "sort": 3,
			"params": {"personIds": item["Id"], "includeItemTypes": "Movie,Series,Episode", "recursive": True}}, cb)
	elif t in ("CollectionFolder", "UserView") and item.get("CollectionType"):
		open_grid(screen, library_spec(item), cb)
	elif t in FOLDER_TYPES or item.get("IsFolder"):
		open_grid(screen, folder_spec(item), cb)
	else:
		open_detail(screen, item, cb)
