# Fictional demo library + generated artwork for README screenshots (no real titles or images)
import io
import random
import time

from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
NOW = time.time()


def ago(days):
	return time.strftime("%Y-%m-%dT%H:%M:%S.0000000Z", time.gmtime(NOW - days * 86400))


MOVIES = [
	("Nordlicht", 2026, 118, "FSK 12", 7.6, ["Drama", "Abenteuer"], 1, None,
		"Eine Meteorologin reist in den hohen Norden, um ein rätselhaftes Leuchten am Himmel zu erforschen - und stößt auf ein Geheimnis, das ihr Leben verändert."),
	("Stadt aus Glas", 2025, 131, "FSK 16", 8.1, ["Thriller", "Krimi"], 2, 0.42,
		"Eine Architektin entdeckt in den Plänen ihres eigenen Hochhauses einen Raum, der offiziell nicht existiert."),
	("Die Insel", 2026, 104, "FSK 12", 7.2, ["Abenteuer"], 3, None,
		"Nach einem Sturm strandet eine Schulklasse auf einer Insel, die auf keiner Karte verzeichnet ist."),
	("Tiefsee", 2024, 97, "FSK 16", 6.9, ["Science-Fiction", "Thriller"], 9, None,
		"Die Crew einer Forschungsstation am Meeresgrund empfängt ein Signal - aus noch größerer Tiefe."),
	("Funkstille", 2025, 88, "FSK 12", 7.4, ["Komödie"], 12, None,
		"Ein Wochenende ohne Handy: Drei Freunde wetten, wer es länger aushält. Es läuft nicht nach Plan."),
	("Der letzte Sommer", 2023, 112, "FSK 6", 7.8, ["Drama", "Familie"], 40, None,
		"Ein Großvater, zwei Enkel und ein alter Segelbootmotor - ein Sommer, der alles verändert."),
	("Sternenstaub", 2024, 126, "FSK 12", 8.3, ["Science-Fiction"], 55, None,
		"Eine junge Astronomin findet in alten Aufnahmen einen Stern, der jedes Jahr ein kleines Stück näher kommt."),
	("Grenzland", 2022, 119, "FSK 16", 7.0, ["Western", "Drama"], 80, None,
		"An der Grenze zweier Täler kämpft eine Rancherin um das Wasser, das beiden gehört."),
	("Das Erbe", 2025, 101, "FSK 12", 6.6, ["Krimi", "Komödie"], 18, None,
		"Sieben Erben, ein Testament und ein verschwundener Schlüssel."),
	("Zugvögel", 2021, 95, "FSK 0", 7.9, ["Dokumentation"], 120, None,
		"Eine Reise mit den Kranichen von Skandinavien bis nach Spanien."),
	("Morgenrot", 2023, 108, "FSK 12", 7.1, ["Drama", "Romanze"], 30, None,
		"Zwei Fremde verpassen in einer Nacht denselben letzten Zug und erzählen sich bis zum Morgen ihre Geschichten."),
	("Schattenspiel", 2024, 115, "FSK 16", 7.5, ["Mystery", "Thriller"], 6, None,
		"Ein Puppenspieler bemerkt, dass seine Figuren nachts ihre Position ändern."),
	("Polarstern", 2022, 99, "FSK 6", 7.3, ["Abenteuer", "Familie"], 160, None,
		"Ein Mädchen und ihr Schlittenhund auf der Suche nach dem verschollenen Vater."),
	("Kaltfront", 2026, 109, "FSK 16", 6.8, ["Action", "Thriller"], 4, None,
		"Ein Wetterdienst sagt einen Sturm voraus, den es eigentlich nicht geben dürfte."),
]

SERIES = [
	("Lichterstadt", 2023, "Continuing", ["Krimi", "Drama"], 8.2,
		"Eine Kommissarin ermittelt in einer Stadt, in der nachts nie das Licht ausgeht.", 3, 6),
	("Das Archiv", 2024, "Continuing", ["Mystery"], 7.9,
		"Im Keller eines Museums lagern Akten zu Fällen, die nie stattgefunden haben - angeblich.", 2, 8),
	("Glasmeer", 2021, "Ended", ["Science-Fiction"], 7.4,
		"Eine Kolonie auf einem Planeten, dessen Ozean aus flüssigem Glas besteht.", 2, 6),
]
EPISODE_NAMES = ["Ankunft", "Spuren", "Der Zeuge", "Nachtschicht", "Funkloch", "Die Akte", "Gegenlicht", "Finale"]


class DemoLibrary(object):
	def __init__(self, media_source):
		self.items = {}
		self.views = [
			{"Id": "lib-movies", "Name": "Filme", "Type": "CollectionFolder", "CollectionType": "movies", "ImageTags": {}},
			{"Id": "lib-tv", "Name": "Serien", "Type": "CollectionFolder", "CollectionType": "tvshows", "ImageTags": {}},
		]
		for v in self.views:
			self.items[v["Id"]] = dict(v)
		for i, (name, year, minutes, fsk, rating, genres, added, progress, overview) in enumerate(MOVIES):
			mid = "dm%d" % i
			ud = {"Played": added > 100, "IsFavorite": i in (1, 6), "PlaybackPositionTicks": 0, "PlayedPercentage": 0}
			if progress:
				ud.update(PlaybackPositionTicks=int(minutes * 60 * progress * 10000000), PlayedPercentage=progress * 100)
			self.items[mid] = {"Id": mid, "Name": name, "Type": "Movie", "MediaType": "Video", "ParentId": "lib-movies",
				"ProductionYear": year, "RunTimeTicks": minutes * 60 * 10000000, "OfficialRating": fsk, "CommunityRating": rating,
				"Genres": genres, "Overview": overview, "ImageTags": {"Primary": "p"}, "BackdropImageTags": ["b"],
				"UserData": ud, "DateCreated": ago(added), "PremiereDate": ago(added + 30),
				"MediaSources": [media_source(mid, "hevc" if i % 3 == 0 else "h264", ("eac3", "ac3"), 3840 if i % 3 == 0 else 1920)],
				"People": demo_people(i),
				"Studios": [{"Name": "Demo Studios"}], "Taglines": []}
		for si, (name, year, status, genres, rating, overview, seasons, eps) in enumerate(SERIES):
			sid = "ds%d" % si
			self.items[sid] = {"Id": sid, "Name": name, "Type": "Series", "ParentId": "lib-tv", "ProductionYear": year, "Status": status,
				"ChildCount": seasons, "ImageTags": {"Primary": "p"}, "BackdropImageTags": ["b"], "Overview": overview, "Genres": genres,
				"CommunityRating": rating, "OfficialRating": "FSK 12", "People": [], "DateCreated": ago(300), "DateLastMediaAdded": ago(2 + si * 20),
				"UserData": {"UnplayedItemCount": 3 + si, "Played": False}}
			for s in range(1, seasons + 1):
				season_id = "%s-s%d" % (sid, s)
				self.items[season_id] = {"Id": season_id, "Name": "Staffel %d" % s, "Type": "Season", "SeriesId": sid, "SeriesName": name,
					"IndexNumber": s, "ParentId": sid, "ImageTags": {}, "SeriesPrimaryImageTag": "p", "UserData": {}, "ChildCount": eps}
				for e in range(1, eps + 1):
					eid = "%s-e%d%02d" % (sid, s, e)
					last = s == seasons
					played = not last or e <= 2
					ud = {"Played": played, "PlaybackPositionTicks": 0, "PlayedPercentage": 0}
					if last and e == 3:
						ud.update(PlaybackPositionTicks=14 * 60 * 10000000, PlayedPercentage=31)
					self.items[eid] = {"Id": eid, "Name": EPISODE_NAMES[(e - 1) % len(EPISODE_NAMES)], "Type": "Episode", "MediaType": "Video",
						"SeriesId": sid, "SeriesName": name, "SeasonId": season_id, "SeasonName": "Staffel %d" % s, "ParentIndexNumber": s,
						"IndexNumber": e, "ParentId": season_id, "RunTimeTicks": 45 * 60 * 10000000, "ImageTags": {"Primary": "p"},
						"SeriesPrimaryImageTag": "p", "ParentBackdropItemId": sid, "ParentBackdropImageTags": ["b"],
						"PremiereDate": ago(400 - s * 100 - e * 7), "CommunityRating": 7 + (e % 3) / 2.0,
						"Overview": "Folge %d der %s. Staffel von %s: Neue Hinweise führen das Team in eine unerwartete Richtung." % (e, s, name),
						"UserData": ud, "MediaSources": [media_source(eid)], "LocationType": "FileSystem",
						"DateCreated": ago((e if last else 200) + si * 20)}

	def children(self, parent):
		return [it for it in self.items.values() if it.get("ParentId") == parent]

	def descendants(self, parent):
		out = []
		stack = [parent]
		while stack:
			p = stack.pop()
			for it in self.children(p):
				out.append(it)
				stack.append(it["Id"])
		return out


_cache = {}

DEMO_CAST = [("dp1", "Lena Berger", "Mira Sand"), ("dp2", "Jonas Wirth", "Kommissar Falk"), ("dp4", "Selin Aydın", "Dr. Yara Lenz"),
	("dp5", "Tobias Kern", "Vincent"), ("dp6", "Nora Lindqvist", "Agentin Holm"), ("dp7", "Paul Hofer", "Großvater Emil"),
	("dp8", "Elif Demir", "Journalistin"), ("dp9", "Ben Okafor", "Pilot"), ("dp10", "Clara Weiß", "Nachbarin"), ("dp11", "Max Brandt", "Barkeeper")]


def demo_people(i):
	order = DEMO_CAST[i % 3:] + DEMO_CAST[:i % 3]
	people = [{"Id": pid, "Name": n, "Type": "Actor", "Role": r, "PrimaryImageTag": "pp"} for pid, n, r in order]
	people[5].pop("PrimaryImageTag")  # one without photo -> initials
	return people + [{"Id": "dp3", "Name": "Mara Ostrowski", "Type": "Director", "PrimaryImageTag": "pp"}]


def _font(size):
	try:
		return ImageFont.truetype(FONT_BOLD, size)
	except IOError:
		return ImageFont.load_default()


def artwork(item, kind, w, h):
	key = (item.get("Id"), kind, w, h)
	if key in _cache:
		return _cache[key]
	seed = sum(ord(c) * (i + 1) for i, c in enumerate(item.get("SeriesId") or item.get("Id", "x"))) + (0 if kind != "episode" else item.get("IndexNumber", 0) * 31)
	rnd = random.Random(seed)
	c1 = tuple(rnd.randint(15, 90) for _ in range(3))
	c2 = tuple(rnd.randint(110, 235) for _ in range(3))
	img = Image.new("RGB", (w, h))
	d = ImageDraw.Draw(img)
	for y in range(h):
		t = y / float(h)
		d.line([(0, y), (w, y)], fill=tuple(int(c2[i] * (1 - t) + c1[i] * t) for i in range(3)))
	cx, cy = rnd.uniform(0.25, 0.75) * w, rnd.uniform(0.15, 0.4) * h
	r = rnd.uniform(0.10, 0.18) * max(w, h)
	d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=tuple(min(255, c + 50) for c in c2))
	for layer in range(3):
		base = h * (0.52 + layer * 0.14)
		pts = [(0, h)]
		step = max(8, w // 24)
		for x in range(0, w + step, step):
			pts.append((x, base - rnd.uniform(0, 0.16) * h))
		pts.append((w, h))
		d.polygon(pts, fill=tuple(int(c * (0.8 - layer * 0.25)) for c in c1))
	img = img.filter(ImageFilter.GaussianBlur(max(1, w // 400)))
	if kind == "person":
		img = Image.new("RGB", (w, h))
		d = ImageDraw.Draw(img)
		for y in range(h):
			t = y / float(h)
			d.line([(0, y), (w, y)], fill=tuple(int(c2[i] * 0.55 * (1 - t) + c1[i] * t) for i in range(3)))
		skin = rnd.choice([(232, 196, 170), (198, 150, 118), (150, 104, 76), (240, 210, 190), (110, 76, 56)])
		hair = rnd.choice([(40, 30, 25), (90, 60, 35), (180, 140, 90), (25, 25, 30), (120, 120, 125)])
		shirt = tuple(rnd.randint(40, 200) for _ in range(3))
		d.ellipse([w * 0.12, h * 0.66, w * 0.88, h * 1.25], fill=shirt)
		d.rectangle([w * 0.42, h * 0.52, w * 0.58, h * 0.70], fill=skin)
		d.ellipse([w * 0.27, h * 0.20, w * 0.73, h * 0.60], fill=skin)
		d.chord([w * 0.25, h * 0.15, w * 0.75, h * 0.50], 180, 360, fill=hair)
		img = img.filter(ImageFilter.GaussianBlur(max(1, w // 120)))
	elif kind == "poster":
		d = ImageDraw.Draw(img)
		title = item.get("SeriesName") if item.get("Type") == "Episode" else item.get("Name", "")
		size = max(12, int(w / 9))
		f = _font(size)
		words, lines, line = title.upper().split(), [], ""
		for wd in words:
			test = (line + " " + wd).strip()
			if d.textlength(test, font=f) > w * 0.86 and line:
				lines.append(line)
				line = wd
			else:
				line = test
		lines.append(line)
		y = h * 0.80 - (len(lines) - 1) * size * 1.1
		for ln in lines:
			d.text((w / 2, y), ln, font=f, fill=(250, 250, 250), anchor="mm")
			y += size * 1.1
	buf = io.BytesIO()
	img.save(buf, "JPEG", quality=88)
	_cache[key] = buf.getvalue()
	return _cache[key]
