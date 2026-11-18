# Stub of Components.Console: records commands and answers like a successful opkg run
COMMANDS = []
RESULT = [0, "Installing enigma2-plugin-extensions-jellyfine2 (9.9.9) on root.\nConfiguring enigma2-plugin-extensions-jellyfine2.\n"]


class Console(object):
	def __init__(self, binary=False):
		self.binary = binary

	def ePopen(self, cmd, callback=None, extra_args=[]):
		COMMANDS.append(cmd)
		if callback:
			callback(RESULT[1], RESULT[0], extra_args)
