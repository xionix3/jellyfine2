from Components.GUIComponent import GUIComponent


class ScrollLabel(GUIComponent):
	def __init__(self, text="", showscrollbar=True):
		GUIComponent.__init__(self)
		self.text = text
		self.page = 0

	def setText(self, text, showBottom=False):
		assert isinstance(text, str)
		self.text = text
		self.page = 0

	def pageUp(self):
		self.page = max(0, self.page - 1)

	def pageDown(self):
		self.page += 1
