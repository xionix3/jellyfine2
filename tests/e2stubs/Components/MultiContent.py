# signatures copied from OpenPLi release-9.0
from enigma import RT_HALIGN_LEFT, RT_VALIGN_TOP, eListboxPythonMultiContent


def _chk_int(*vals):
	for v in vals:
		assert isinstance(v, int), "MultiContent needs int coords, got %r" % (v,)


def MultiContentEntryText(pos=(0, 0), size=(0, 0), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, text="", color=None, color_sel=None, backcolor=None, backcolor_sel=None, border_width=None, border_color=None):
	_chk_int(pos[0], pos[1], size[0], size[1])
	assert isinstance(text, str), text
	return (eListboxPythonMultiContent.TYPE_TEXT, pos[0], pos[1], size[0], size[1], font, flags, text, color, color_sel, backcolor, backcolor_sel, border_width, border_color)


def MultiContentEntryPixmapAlphaBlend(pos=(0, 0), size=(0, 0), png=None, backcolor=None, backcolor_sel=None, flags=0):
	_chk_int(pos[0], pos[1], size[0], size[1])
	assert png is not None
	return (eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, pos[0], pos[1], size[0], size[1], png, backcolor, backcolor_sel, flags)


def MultiContentEntryProgress(pos=(0, 0), size=(0, 0), percent=None, borderWidth=None, foreColor=None, foreColorSelected=None, backColor=None, backColorSelected=None):
	_chk_int(pos[0], pos[1], size[0], size[1])
	return (eListboxPythonMultiContent.TYPE_PROGRESS, pos[0], pos[1], size[0], size[1], percent, borderWidth, foreColor, foreColorSelected, backColor, backColorSelected)
