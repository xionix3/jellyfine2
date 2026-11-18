from Screens.Screen import Screen


class MessageBox(Screen):
	TYPE_YESNO = 0
	TYPE_INFO = 1
	TYPE_WARNING = 2
	TYPE_ERROR = 3
	TYPE_MESSAGE = 4

	def __init__(self, session, text, type=TYPE_YESNO, timeout=-1, close_on_any_key=False, default=True, enable_input=True, msgBoxID=None, picon=None, simple=False, list=[], timeout_default=None, title=None):
		Screen.__init__(self, session)
		assert isinstance(text, str)
		self.text = text
		self.type = type
		self.default = default
