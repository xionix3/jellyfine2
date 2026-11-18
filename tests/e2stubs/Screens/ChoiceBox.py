from Screens.Screen import Screen


class ChoiceBox(Screen):
	def __init__(self, session, title="", list=[], keys=None, selection=0, skin_name=[], reorderConfig="", windowTitle=None):
		Screen.__init__(self, session)
		assert list, "empty ChoiceBox"
		for entry in list:
			assert isinstance(entry[0], str), entry
		self.dlg_title = title
		self.list = list
		self.selection = selection
		assert 0 <= selection < len(list), (selection, len(list))
