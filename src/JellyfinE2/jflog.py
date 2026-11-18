# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 xionix
# Jellyfin for Enigma2 - log output without secrets (users post their logs in bug reports)
from __future__ import absolute_import

import re
import traceback

# api_key=..., ApiKey=..., X-Emby-Token: ..., Token="..." (Authorization header), access_token=...
_SECRET = re.compile(r'(?i)\b((?:api_?key|x-(?:emby|mediabrowser)-token|access_?token|token)\s*[=:]\s*"?)[^&\s",;]+')
_PASSWORD = re.compile(r'(?i)("?\b(?:pw|password)"?\s*[=:]\s*"?)[^&\s",;]+')


def redact(text):
	"""Replaces access tokens and passwords in text (URLs, headers, JSON) by ***."""
	text = "%s" % (text,)
	return _PASSWORD.sub(r"\1***", _SECRET.sub(r"\1***", text))


def log(message):
	print("[Jellyfin] %s" % redact(message))


def log_exception(prefix="error"):
	log("%s:\n%s" % (prefix, traceback.format_exc().rstrip()))
