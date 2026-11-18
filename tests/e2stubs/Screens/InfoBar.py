from Screens.Screen import Screen
from Components.ActionMap import HelpableActionMap


class InfoBar(object):
	instance = None


class MoviePlayer(Screen):
	ENABLE_RESUME_SUPPORT = True
	ALLOW_SUSPEND = True
	SEEK_STATE_PLAY = (0, 0, 0, ">")
	SEEK_STATE_PAUSE = (1, 0, 0, "||")
	SEEK_STATE_EOF = (1, 0, 0, "END")
	movie_instance = None

	def __init__(self, session, service, slist=None, lastservice=None, infobar=None):
		Screen.__init__(self, session)
		self["actions"] = HelpableActionMap(self, ["MoviePlayerActions"], {
			"leavePlayer": (self.leavePlayer, "leave"),
			"leavePlayerOnExit": (self.leavePlayerOnExit, "leave"),
			"channelUp": (self.channelUp, "up"),
			"channelDown": (self.channelDown, "down"),
		})
		self["DirectionActions"] = HelpableActionMap(self, ["DirectionActions"], {"left": self.left, "right": self.right}, prio=-2)
		self["MovieListActions"] = HelpableActionMap(self, ["InfobarMovieListActions"], {
			"movieList": (self.showMovies, "list"), "up": (self.up, "up"), "down": (self.down, "down")})
		self.servicelist = slist
		self.lastservice = lastservice or session.nav.getCurrentlyPlayingServiceOrGroup()
		self.seekstate = self.SEEK_STATE_PLAY
		self.is_closing = False
		session.nav.playService(service)
		self.cur_service = service
		self.selected_subtitle = None
		self.seek_calls = []
		self.onClose.append(self.__onClose)
		MoviePlayer.movie_instance = self

	def __onClose(self):
		MoviePlayer.movie_instance = None
		self.session.nav.playService(self.lastservice)

	def getSeek(self):
		s = self.session.nav.getCurrentService()
		return s and s.seek()

	def doSeek(self, pts):
		s = self.getSeek()
		if s:
			s.seekTo(pts)

	def doSeekRelative(self, pts):
		s = self.getSeek()
		if s:
			s.seekRelative(pts < 0 and -1 or 1, abs(pts))
		self.seek_calls.append(pts)

	def toggleShow(self):
		self.shown = not self.shown

	def left(self):
		self.seek_calls.append("seekBack")

	def right(self):
		self.seek_calls.append("seekFwd")

	def enableSubtitle(self, sub):
		self.selected_subtitle = sub

	def leavePlayer(self):
		self.close()

	def leavePlayerOnExit(self):
		self.close()

	def channelUp(self):
		return 0

	def channelDown(self):
		return 0

	def showMovies(self):
		raise AssertionError("movie list must not open")

	def up(self):
		self.showMovies()

	def down(self):
		self.showMovies()

	def doEofInternal(self, playing):
		self.close()
