class ConfigElement(object):
	def __init__(self, default):
		self.default = default
		self.value = default
		self.saved_value = None

	def save(self):
		self.saved_value = self.value


class ConfigText(ConfigElement):
	def __init__(self, default="", fixed_size=True, visible_width=False):
		ConfigElement.__init__(self, default)


class ConfigYesNo(ConfigElement):
	def __init__(self, default=False):
		ConfigElement.__init__(self, default)


class ConfigSubsection(object):
	pass


class _ConfigFile(object):
	saves = 0

	def save(self):
		_ConfigFile.saves += 1


config = ConfigSubsection()
config.plugins = ConfigSubsection()
configfile = _ConfigFile()
