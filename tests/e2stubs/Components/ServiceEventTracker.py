TRACKERS = []


class ServiceEventTracker(object):
	def __init__(self, screen, eventmap):
		self.screen = screen
		self.eventmap = eventmap
		TRACKERS.append(self)
