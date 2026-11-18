# Minimal enigma stub for off-box testing
import itertools

VCLOCK = [0]  # virtual milliseconds


class eTimer(object):
	all = []

	def __init__(self):
		self.callback = []
		self.active = False
		self.interval = 0
		self.single = False
		self.next_fire = 0
		eTimer.all.append(self)

	def start(self, msec, singleShot=False):
		self.active = True
		self.interval = int(msec)
		self.single = bool(singleShot)
		self.next_fire = VCLOCK[0] + self.interval

	def startLongTimer(self, sec):
		self.start(sec * 1000, True)

	def stop(self):
		self.active = False

	def isActive(self):
		return self.active

	def due(self):
		return self.active and self.next_fire <= VCLOCK[0]

	def fire(self):
		if self.single:
			self.active = False
		else:
			self.next_fire = VCLOCK[0] + max(self.interval, 1)
		for cb in list(self.callback):
			cb()


class ePoint(object):
	def __init__(self, x, y):
		self.px, self.py = x, y

	def x(self):
		return self.px

	def y(self):
		return self.py


class gRGB(object):
	def __init__(self, *a):
		if len(a) == 1:
			self.v = int(a[0])
		else:
			r, g, b = a[:3]
			self.v = (int(r) << 16) | (int(g) << 8) | int(b)

	def argb(self):
		return self.v


class eSize(object):
	def __init__(self, w, h):
		self.w, self.h = w, h

	def width(self):
		return self.w

	def height(self):
		return self.h


DESKTOP = [1920, 1080]


class _Desktop(object):
	def size(self):
		return eSize(DESKTOP[0], DESKTOP[1])

	def makeCompatiblePixmap(self, p):
		pass


def getDesktop(i):
	return _Desktop()


class eServiceReference(object):
	def __init__(self, type_, flags=0, path=""):
		self.type = type_
		self.flags = flags
		self.path = path
		self.name = ""

	def setName(self, n):
		self.name = n

	def getName(self):
		return self.name

	def getPath(self):
		return self.path

	def toString(self):
		return "%d:%d:0:0:0:0:0:0:0:0:%s:%s" % (self.type, self.flags, self.path.replace(":", "%3a"), self.name)


class iPlayableService(object):
	evStart = 1
	evEnd = 2
	evEOF = 3
	evSOF = 4
	evUpdatedInfo = 5
	evSeekableStatusChanged = 6
	evCuesheetChanged = 7
	evUpdatedEventInfo = 8
	evVideoSizeChanged = 9


class gFont(object):
	def __init__(self, name, size):
		self.name, self.size = name, size


class _Content(object):
	TYPE_TEXT = 0
	TYPE_PROGRESS = 1
	TYPE_PIXMAP = 2
	TYPE_PIXMAP_ALPHATEST = 3
	TYPE_PIXMAP_ALPHABLEND = 4
	TYPE_PROGRESS_PIXMAP = 5

	def __init__(self):
		self.lst = []
		self.index = 0
		self.fonts = {}
		self.item_height = 0
		self.owner = None
		self.invalidated = []

	def setList(self, lst):
		self.lst = lst
		self.index = 0
		if self.owner is not None:
			self.owner._changed()

	def setFont(self, idx, font):
		self.fonts[idx] = font

	def setItemHeight(self, h):
		self.item_height = h

	def getCurrentSelection(self):
		if 0 <= self.index < len(self.lst):
			return self.lst[self.index]
		return None

	def getCurrentSelectionIndex(self):
		return self.index

	def invalidateEntry(self, i):
		self.invalidated.append(i)

	def invalidate(self):
		pass


class eListboxPythonMultiContent(_Content):
	pass


class eListboxPythonStringContent(_Content):
	pass


class eListbox(object):
	moveUp, moveDown, pageUp, pageDown, moveTop, moveEnd = range(6)


RT_HALIGN_LEFT = 0
RT_HALIGN_RIGHT = 1
RT_HALIGN_CENTER = 2
RT_HALIGN_BLOCK = 4
RT_VALIGN_TOP = 0
RT_VALIGN_CENTER = 8
RT_VALIGN_BOTTOM = 16
RT_WRAP = 32
BT_ALPHATEST = 1
BT_ALPHABLEND = 2
BT_SCALE = 4
BT_KEEP_ASPECT_RATIO = 8
BT_HALIGN_CENTER = 16
BT_VALIGN_CENTER = 64


class FakePixmap(object):
	def __init__(self, path, size=None):
		self.path = path
		self.size = size


class _Signal(object):
	def __init__(self):
		self.cbs = []

	def get(self):
		return self.cbs


class ePicLoad(object):
	"""Like the real one: one decode at a time, result via PictureData on the main loop, getData() once."""
	instances = []
	decoded = []

	def __init__(self):
		self.PictureData = _Signal()
		self.para = None
		self.job = None
		self.busy = False
		self.timer = None
		ePicLoad.instances.append(self)

	def setPara(self, para):
		assert len(para) >= 7
		self.para = tuple(para)
		return 1

	def startDecode(self, path, x=0, y=0, *args):
		import os
		if self.busy:
			raise AssertionError("ePicLoad.startDecode while busy - the running decode would lose its callback")
		if not os.path.exists(path):
			return 1
		self.busy = True
		self.job = (path, x, y)
		self.timer = eTimer()
		self.timer.callback.append(self._fire)
		self.timer.start(5, True)
		return 0

	def _fire(self):
		self.busy = False
		for cb in list(self.PictureData.get()):
			cb("%s|%d|%d" % self.job)

	def getData(self):
		path, x, y = self.job
		with open(path, "rb") as f:
			head = f.read(8)
		ePicLoad.decoded.append((path, x, y))
		if head[:3] != b"\xff\xd8\xff" and head[:8] != b"\x89PNG\r\n\x1a\n":
			return None
		return FakePixmap(path, (x, y))


def loadPNG(path, *a):
	import os
	return FakePixmap(path) if os.path.exists(path) else None


JPG_LOADS = []


def loadJPG(path, *a):
	import os
	JPG_LOADS.append(path)  # a JPEG decoded on the GUI thread
	with open(path, "rb") as f:
		head = f.read(3)
	if head != b"\xff\xd8\xff":
		return None
	return FakePixmap(path) if os.path.exists(path) else None


def loadSVG(*a):
	return None
