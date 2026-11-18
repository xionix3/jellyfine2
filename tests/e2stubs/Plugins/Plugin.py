class PluginDescriptor(object):
	WHERE_EXTENSIONSMENU = 0
	WHERE_MAINMENU = 1
	WHERE_PLUGINMENU = 2
	WHERE_MOVIELIST = 3
	WHERE_MENU = 4
	WHERE_AUTOSTART = 5
	WHERE_SESSIONSTART = 7

	def __init__(self, name="Plugin", where=None, description="", icon=None, fnc=None, wakeupfnc=None, needsRestart=None, internal=False, weight=0):
		self.name = name
		self.where = where if isinstance(where, list) else [where]
		self.description = description
		self.icon = icon
		self.fnc = fnc
