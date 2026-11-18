from enigma import loadPNG, loadJPG


def LoadPixmap(path, desktop=None, cached=None, width=0, height=0):
	if path[-4:] == ".png":
		return loadPNG(path, 0, 0)
	elif path[-4:] == ".jpg":
		return loadJPG(path, 0)
	raise Exception("Neither .png nor .jpg nor .svg, please fix file extension")
