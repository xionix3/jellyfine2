class Screen(dict):
	def __init__(self, session, parent=None, mandatoryWidgets=None):
		dict.__init__(self)
		self.session = session
		self.onClose = []
		self.onFirstExecBegin = []
		self.onExecBegin = []
		self.onExecEnd = []
		self.onLayoutFinish = []
		self.onShown = []
		self.onShow = []
		self.onHide = []
		self.skinName = self.__class__.__name__
		self.instance = None
		self.execing = True
		self.shown = True
		self.screenTitle = ""

	def close(self, *retval):
		self.session.close(self, *retval)

	def setTitle(self, title, showPath=True):
		self.screenTitle = title

	def getTitle(self):
		return self.screenTitle

	def show(self):
		self.shown = True

	def hide(self):
		self.shown = False
