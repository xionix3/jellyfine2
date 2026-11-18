from Screens.Screen import Screen


class VirtualKeyBoard(Screen):
	def __init__(self, session, title="", text="", maxSize=False, visible_width=False, type=0, currPos=None, allMarked=False, style=0):
		Screen.__init__(self, session)
		assert isinstance(text, str)
		self.dlg_title = title
		self.text = text
