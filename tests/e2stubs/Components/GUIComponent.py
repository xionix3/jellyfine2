class FakeInstance(object):
	def __init__(self, comp):
		self.comp = comp
		self.pos = None
		self.pixmap = None
		self.title = None
		self.fg = None

	def move(self, p):
		self.pos = (p.x(), p.y())

	def resize(self, s):
		pass

	def setPixmap(self, ptr):
		self.pixmap = ptr

	def show(self):
		pass

	def hide(self):
		pass

	def setTitle(self, t):
		self.title = t

	def setForegroundColor(self, col):
		self.fg = col.argb() if hasattr(col, "argb") else col

	def invalidate(self):
		pass


class GUIComponent(object):
	def __init__(self):
		self.instance = None
		self.visible = True

	def show(self):
		self.visible = True

	def hide(self):
		self.visible = False

	def _attach(self):
		self.instance = FakeInstance(self)
