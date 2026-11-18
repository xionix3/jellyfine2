from Components.GUIComponent import GUIComponent


class ProgressBar(GUIComponent):
	def __init__(self):
		GUIComponent.__init__(self)
		self.value = 0

	def setValue(self, v):
		assert isinstance(v, int) and 0 <= v <= 100, v
		self.value = v
