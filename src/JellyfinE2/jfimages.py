# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
# Jellyfin for Enigma2 - poster/backdrop cache in RAM (/tmp)
from __future__ import absolute_import

import os
import re
import threading

try:
	from hashlib import md5 as _md5
except ImportError:  # pragma: no cover
	_md5 = None

from .jfasync import runner


def cache_location():
	try:
		from .jfconfig import cache_dir
		return cache_dir()
	except Exception:
		return "/tmp/jellyfine2", 80 * 1024 * 1024


def _ensure_dir():
	d = cache_location()[0]
	if not os.path.isdir(d):
		try:
			os.makedirs(d)
		except OSError:
			pass
	return d


def cleanup(max_bytes=None):
	"""Drop oldest files when the cache grows too large (runs in a worker)."""
	d, limit = cache_location()
	max_bytes = max_bytes or limit
	try:
		files = []
		total = 0
		for name in os.listdir(d):
			p = os.path.join(d, name)
			try:
				st = os.stat(p)
			except OSError:
				continue
			files.append((st.st_mtime, st.st_size, p))
			total += st.st_size
		if total <= max_bytes:
			return
		files.sort()
		for _mtime, size, p in files:
			try:
				os.remove(p)
			except OSError:
				pass
			total -= size
			if total <= max_bytes * 0.7:
				break
	except OSError:
		pass


def clear():
	d = cache_location()[0]
	try:
		for name in os.listdir(d):
			try:
				os.remove(os.path.join(d, name))
			except OSError:
				pass
	except OSError:
		pass


def image_ref(item, kind="poster"):
	"""Return (item_id, image_type, tag) for the best image of an item or None.

	kind: poster (2:3), thumb (16:9, falls back to the poster), landscape (16:9 only),
	backdrop (16:9 large), person (actor photo of a People entry or Person item)
	"""
	tags = item.get("ImageTags") or {}
	t = item.get("Type")
	if kind == "poster":
		if t == "Episode":
			if item.get("SeriesPrimaryImageTag") and item.get("SeriesId"):
				return (item["SeriesId"], "Primary", item["SeriesPrimaryImageTag"])
		if t == "Season" and not tags.get("Primary") and item.get("SeriesPrimaryImageTag") and item.get("SeriesId"):
			return (item["SeriesId"], "Primary", item["SeriesPrimaryImageTag"])
		if tags.get("Primary"):
			return (item["Id"], "Primary", tags["Primary"])
		if t == "Audio" and item.get("AlbumId") and item.get("AlbumPrimaryImageTag"):
			return (item["AlbumId"], "Primary", item["AlbumPrimaryImageTag"])
		return None
	if kind == "thumb":
		if tags.get("Primary") and t in ("Episode", "Video", "MusicVideo", "Audio"):
			return (item["Id"], "Primary", tags["Primary"])
		if tags.get("Thumb"):
			return (item["Id"], "Thumb", tags["Thumb"])
		if item.get("ParentThumbItemId") and item.get("ParentThumbImageTag"):
			return (item["ParentThumbItemId"], "Thumb", item["ParentThumbImageTag"])
		bd = item.get("BackdropImageTags") or []
		if bd:
			return (item["Id"], "Backdrop", bd[0])
		pb = item.get("ParentBackdropImageTags") or []
		if pb and item.get("ParentBackdropItemId"):
			return (item["ParentBackdropItemId"], "Backdrop", pb[0])
		if tags.get("Primary"):
			return (item["Id"], "Primary", tags["Primary"])
		return None
	if kind == "landscape":
		ref = image_ref(item, "thumb")
		if ref and ref[1] == "Primary" and t not in ("Episode", "Video", "MusicVideo"):
			return None
		return ref
	if kind == "person":
		tag = item.get("PrimaryImageTag") or tags.get("Primary")
		if tag and item.get("Id"):
			return (item["Id"], "Primary", tag)
		return None
	if kind == "backdrop":
		bd = item.get("BackdropImageTags") or []
		if bd:
			return (item["Id"], "Backdrop", bd[0])
		pb = item.get("ParentBackdropImageTags") or []
		if pb and item.get("ParentBackdropItemId"):
			return (item["ParentBackdropItemId"], "Backdrop", pb[0])
		if tags.get("Thumb"):
			return (item["Id"], "Thumb", tags["Thumb"])
		return None
	return None


class ImageLoader(object):
	"""Downloads images (resized server side) and calls back with a local path."""

	def __init__(self, client):
		self.client = client
		self.inflight = {}
		self.lock = threading.Lock()
		self.counter = 0
		self.group = runner().group()  # never cancelled: in-flight downloads always finish
		_ensure_dir()

	def path_for(self, ref, w, h):
		item_id, image_type, tag = ref
		key = "%s_%s_%s_%dx%d" % (item_id, image_type, tag or "", int(w), int(h))
		if _md5 is not None:
			name = _md5(key.encode("utf-8")).hexdigest()
		else:
			name = re.sub(r"[^A-Za-z0-9_.-]", "_", key)[:200]
		return os.path.join(cache_location()[0], name)

	def cached(self, ref, w, h):
		base = self.path_for(ref, w, h)
		for ext in (".jpg", ".png"):
			if os.path.exists(base + ext):
				return base + ext
		return None

	def get(self, ref, w, h, callback):
		"""callback(path or None) on the GUI thread. Returns path immediately if cached."""
		if not ref:
			return None
		hit = self.cached(ref, w, h)
		if hit:
			return hit
		base = self.path_for(ref, w, h)
		with self.lock:
			waiters = self.inflight.get(base)
			if waiters is not None:
				waiters.append(callback)
				return None
			self.inflight[base] = [callback]
		url = self.client.image_url(ref[0], ref[1], ref[2], max_width=w, max_height=h)
		self.group.run(self._fetch, url, base, pool="image", callback=lambda p: self._done(base, p), errback=lambda e: self._done(base, None))
		return None

	def _fetch(self, url, base):
		data = self.client.download(url)
		if not data or len(data) < 64:
			return None
		if data[:3] == b"\xff\xd8\xff":
			ext = ".jpg"
		elif data[:8] == b"\x89PNG\r\n\x1a\n":
			ext = ".png"
		else:
			return None  # webp/gif/svg cannot be shown by LoadPixmap
		if not os.path.isdir(os.path.dirname(base)):
			_ensure_dir()
		tmp = base + ".part"
		with open(tmp, "wb") as f:
			f.write(data)
		os.rename(tmp, base + ext)
		self.counter += 1
		if self.counter % 150 == 0:
			cleanup()
		return base + ext

	def _done(self, base, path):
		with self.lock:
			waiters = self.inflight.pop(base, [])
		for cb in waiters:
			try:
				cb(path)
			except Exception as e:
				print("[Jellyfin] image callback failed: %s" % e)


_loader = None


def loader(client):
	global _loader
	if _loader is None or _loader.client is not client:
		_loader = ImageLoader(client)
	return _loader
