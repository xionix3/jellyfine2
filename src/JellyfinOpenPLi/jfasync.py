# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
# Jellyfin for Enigma2 - run blocking work in threads, deliver results on the GUI thread
from __future__ import absolute_import

import threading

try:
	import queue
except ImportError:  # pragma: no cover
	import Queue as queue

from enigma import eTimer
from .jflog import log, log_exception


class _Task(object):
	__slots__ = ("fn", "args", "kwargs", "callback", "errback", "group", "cancelled")

	def __init__(self, fn, args, kwargs, callback, errback, group):
		self.fn = fn
		self.args = args
		self.kwargs = kwargs
		self.callback = callback
		self.errback = errback
		self.group = group
		self.cancelled = False


class TaskGroup(object):
	"""Tasks bound to a screen; cancel() drops pending callbacks (e.g. on close)."""

	def __init__(self, runner):
		self.runner = runner
		self.cancelled = False

	def run(self, fn, *args, **kwargs):
		callback = kwargs.pop("callback", None)
		errback = kwargs.pop("errback", None)
		pool = kwargs.pop("pool", "api")
		if self.cancelled:
			return None
		return self.runner.submit(_Task(fn, args, kwargs, callback, errback, self), pool)

	def cancel(self):
		self.cancelled = True


class AsyncRunner(object):
	def __init__(self, api_threads=3, image_threads=4):
		self.results = queue.Queue()
		self.queues = {"api": queue.Queue(), "image": queue.LifoQueue(), "bg": queue.Queue()}
		self.pending = 0
		self.lock = threading.Lock()
		self.timer = eTimer()
		try:
			self.timer.callback.append(self._drain)
		except AttributeError:  # DreamOS style
			self._conn = self.timer.timeout.connect(self._drain)
		for name, count in (("api", api_threads), ("image", image_threads), ("bg", 1)):
			for i in range(count):
				t = threading.Thread(target=self._worker, args=(self.queues[name],), name="jellyfin-%s-%d" % (name, i))
				t.daemon = True
				t.start()

	def group(self):
		return TaskGroup(self)

	def submit(self, task, pool="api"):
		with self.lock:
			self.pending += 1
		self.queues.get(pool, self.queues["api"]).put(task)
		if not self.timer.isActive():
			self.timer.start(40, False)
		return task

	def _worker(self, q):
		while True:
			task = q.get()
			if task is None:
				return
			if task.group is not None and task.group.cancelled:
				self.results.put((task, False, None, True))
				continue
			try:
				res = task.fn(*task.args, **task.kwargs)
				self.results.put((task, True, res, False))
			except Exception as e:  # noqa
				if not getattr(e, "status", None) and e.__class__.__name__ != "JellyfinError":
					log_exception("background task")
				self.results.put((task, False, e, False))

	def _drain(self):
		handled = 0
		while handled < 50:
			try:
				task, ok, res, skipped = self.results.get_nowait()
			except queue.Empty:
				break
			handled += 1
			with self.lock:
				self.pending -= 1
			if skipped or task.cancelled or (task.group is not None and task.group.cancelled):
				continue
			try:
				if ok:
					if task.callback:
						task.callback(res)
				elif task.errback:
					task.errback(res)
				else:
					log("background task failed: %s" % res)
			except Exception:
				log_exception("error in callback")
		with self.lock:
			idle = self.pending <= 0
		if idle and self.results.empty():
			self.timer.stop()


_runner = None


def runner():
	global _runner
	if _runner is None:
		_runner = AsyncRunner()
	return _runner
