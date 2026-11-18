from enigma import eListboxPythonStringContent
from Components.GUIComponent import GUIComponent


class MenuList(GUIComponent):
	def __init__(self, list, enableWrapAround=True, content=eListboxPythonStringContent):
		GUIComponent.__init__(self)
		self.list = list
		self.onSelectionChanged = []
		self.l = content()
		self.l.owner = self
		self.l.setList(self.list)
		self.enableWrapAround = enableWrapAround

	def _changed(self):
		for f in self.onSelectionChanged:
			f()

	def getCurrent(self):
		return self.l.getCurrentSelection()

	def getSelectionIndex(self):
		return self.l.getCurrentSelectionIndex()

	def getSelectedIndex(self):
		return self.l.getCurrentSelectionIndex()

	def setList(self, list):
		self.list = list
		self.l.setList(self.list)

	def _move(self, idx):
		n = len(self.l.lst)
		if not n:
			return
		if self.enableWrapAround:
			idx %= n
		idx = max(0, min(n - 1, idx))
		if idx != self.l.index:
			self.l.index = idx
			self._changed()

	def moveToIndex(self, idx):
		assert self.instance is not None, "moveToIndex before layout has no effect on a real box"
		self._move(idx)

	def up(self):
		self._move(self.l.index - 1)

	def down(self):
		self._move(self.l.index + 1)

	def pageUp(self):
		self._move(max(0, self.l.index - 8))

	def pageDown(self):
		self._move(min(len(self.l.lst) - 1, self.l.index + 8))
