from Screens.Screen import Screen

RESTARTS = []


class TryQuitMainloop(Screen):
	def __init__(self, session, retvalue=1, timeout=-1, default_yes=True):
		Screen.__init__(self, session)
		RESTARTS.append(retvalue)
		self.skin = None
