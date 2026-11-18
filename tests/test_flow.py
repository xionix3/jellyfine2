# End-to-end flow against the fake Jellyfin server using fake Enigma2 screens.
# usage: python3 test_flow.py <server-version> [desktop-height]
import os
import shutil
import sys

VERSION = sys.argv[1] if len(sys.argv) > 1 else "10.10.3"
HEIGHT = int(sys.argv[2]) if len(sys.argv) > 2 else 1080

from harness import Session, pump, press, choose, type_text, answer, fire_event, SKIN_ERRORS  # noqa: E402
import enigma  # noqa: E402

enigma.DESKTOP[:] = [HEIGHT * 16 // 9, HEIGHT]

from mockjf import start_server  # noqa: E402

srv, state, URL = start_server(VERSION)
shutil.rmtree("/tmp/jellyfine2", ignore_errors=True)

from JellyfinE2 import plugin  # noqa: E402
from JellyfinE2 import jfconfig  # noqa: E402
from JellyfinE2.jfapi import parse_version  # noqa: E402
from Components.ActionMap import WARNINGS  # noqa: E402
from Plugins.Plugin import PluginDescriptor  # noqa: E402

failures = []


def check(cond, msg):
	if not cond:
		failures.append(msg)
		print("FAIL:", msg)
	else:
		print("ok  :", msg)


def name(scr):
	return scr.__class__.__name__ if scr is not None else None


s = Session()

# --- plugin descriptors
descs = plugin.Plugins()
check(any(PluginDescriptor.WHERE_PLUGINMENU in d.where for d in descs), "plugin menu entry")
menu_desc = [d for d in descs if PluginDescriptor.WHERE_MENU in d.where][0]
check(menu_desc.fnc("mainmenu") and menu_desc.fnc("setup") == [], "main menu hook")

# --- start: login screen
plugin.main(s)
check(name(s.top) == "LoginScreen", "login screen shown when not logged in")
login = s.top
press(login, "ok")  # server field
type_text(s, URL + "/web/#/home")
check(login.server == URL, "server url normalized (%s)" % login.server)
press(login, "down")
press(login, "ok")
type_text(s, "patrick")
press(login, "down")
press(login, "ok")
type_text(s, "falsch")
press(login, "green")
pump(lambda: "Fehler" in login["status"].getText())
check("falsch" in login["status"].getText() or "Fehler" in login["status"].getText(), "wrong password -> error shown: %s" % login["status"].getText())
press(login, "ok")  # still on password row
type_text(s, "geheim")
press(login, "green")
pump(lambda: name(s.top) == "HomeScreen")
check(name(s.top) == "HomeScreen", "login ok -> home")
cl = jfconfig.client()
check(cl.token == "tok123" and cl.user_id == "u1", "token stored")
check(cl.new_api == (parse_version(VERSION) >= (10, 9, 0)), "api style by version")

home = s.top
pump(lambda: len(home.sections) > 5 and home.cells.items[0] is not None, timeout=10)
titles = [sec[1] for sec in home.sections]
check("Fotos" not in titles and "Filme" in titles and "Serien" in titles, "views listed, photos hidden: %s" % titles)
check(titles[:2] == ["Neue Filme", "Neue Episoden meiner Serien"] and "Meine Listen" in titles, "own lists on top: %s" % titles[:4])
check(home.cells.items[0] is not None and home.cells.items[0]["Id"] == "m3", "newest unplayed movie first (%s)" % (home.cells.items[0] or {}).get("Id"))
check(home["pnew0"].visible and not home["pseen0"].visible, "NEU badge on new movie")
check(home["pph0"].visible and not home["pcover0"].visible, "placeholder for movie without poster")
pump(lambda: home["pcover1"].visible and home["pcover1"].instance.pixmap is not None, timeout=10)
check(home["pcover1"].instance.pixmap is not None, "preview poster loaded")
pump(lambda: home["backdrop"].instance.pixmap is not None, timeout=10)
check(home["backdrop"].instance.pixmap is not None, "home backdrop loaded")
# all previews prefetched in background -> switching sections is instant
pump(lambda: len(home.cache["previews"]) >= 6, timeout=10)
check(len(home.cache["previews"]) >= 6, "previews prefetched (%d)" % len(home.cache["previews"]))

# own list: new movies (30 days, unplayed, newest first)
home["menu"].moveToIndex(0)
press(home, "ok")
rg = s.top
pump(lambda: len(rg.entries) > 0, timeout=10)
ids = [e["Id"] for e in rg.entries]
check(name(rg) == "GridScreen" and ids[0] == "m3" and ids[-1] == "m29" and len(ids) == 27, "rule grid newest movies %s..%s (%d)" % (ids[:1], ids[-1:], len(ids)))
check(rg["key_red"].getText() == "", "no sort keys on rule grid")
press(rg, "cancel")

# own list: new episodes of my series, grouped per series
home["menu"].moveToIndex(1)
pump(lambda: home.cells.items[0] is not None and home.cells.items[0].get("Type") == "Episode", timeout=10)
tile = home.cells.items[0]
check(tile["SeriesId"] == "s1" and tile["_jf_new_count"] == 3 and tile["_jf_focus"]["Id"] == "e21", "grouped new episodes tile")
check(home.cells.items[1] is None, "series I don't watch excluded")
check(home["pcount0"].getText() == "+3" and home["plabel0"].getText() == "Serie Eins (3 neu)", "tile badge/label %s / %s" % (home["pcount0"].getText(), home["plabel0"].getText()))
press(home, "ok")
eg = s.top
pump(lambda: len(eg.entries) == 1, timeout=10)
press(eg, "ok")
ep = s.top
check(name(ep) == "EpisodesScreen", "grouped tile opens episodes")
pump(lambda: ep.entries and ep.current() is not None and ep.current()["Id"] == "e21", timeout=10)
check(ep.current()["Id"] == "e21", "focused first new episode e21")
check("NEU" in ep["list"].list[ep["list"].getSelectedIndex()][-2][7], "episode row marked NEU")
press(ep, "cancel")
press(eg, "cancel")

# go to Filme
idx = titles.index("Filme")
home["menu"].moveToIndex(idx)
pump(lambda: home.cells.items[0] is not None and home.cells.items[0].get("Type") == "Movie", timeout=10)
check(home.cells.items[0].get("Type") == "Movie", "movie preview")
press(home, "ok")
grid = s.top
check(name(grid) == "GridScreen", "grid opened")
pump(lambda: len(grid.entries) > 0, timeout=10)
check(grid.total == 40 and len(grid.entries) == 40, "40 movies loaded (got %d/%d)" % (len(grid.entries), grid.total))
check(grid["frame"].instance.pos is not None, "selection frame positioned")
for _ in range(15):
	press(grid, "right")
check(grid.index == 15 and grid.page == 1, "navigate to page 2 (index %d page %d)" % (grid.index, grid.page))
press(grid, "nextBouquet")
check(grid.index == 29, "page down (%d)" % grid.index)
press(grid, "up")
check(grid.index == 22, "up (%d)" % grid.index)
press(grid, "prevBouquet")
press(grid, "prevBouquet")
press(grid, "prevBouquet")
check(grid.index == 0, "back to start")
# sort + filter
press(grid, "red")
choose(s, "Name (Z-A)")
pump(lambda: grid.entries and grid.entries[0]["Name"] == "Film 40", timeout=10)
check(grid.entries[0]["Name"] == "Film 40", "sorted Z-A")
press(grid, "green")
choose(s, "Gesehen")
pump(lambda: grid.total == 2, timeout=10)
check(grid.total == 2, "filter played -> 2")
press(grid, "green")
choose(s, "Genre wählen")
pump(lambda: name(s.top) == "ChoiceBox", timeout=10)
choose(s, "Komödie")
pump(lambda: not grid.loading and grid.genre is not None, timeout=10)
press(grid, "green")
choose(s, "Alle")
pump(lambda: grid.total == 20, timeout=10)
check(grid.total == 20, "genre filter Komödie + Alle -> 20 (got %d)" % grid.total)
press(grid, "green")
choose(s, "Genre-Filter entfernen")
pump(lambda: grid.total == 40, timeout=10)
press(grid, "red")
choose(s, "Name (A-Z)")
pump(lambda: grid.entries and grid.entries[0]["Name"] == "Film 01", timeout=10)

# yellow toggles played on Film 01 (played -> unplayed)
first = grid.entries[0]
press(grid, "yellow")
pump(lambda: not first["UserData"]["Played"], timeout=5)
check(not first["UserData"]["Played"] and not state.lib.items["m1"]["UserData"]["Played"], "toggle played")
press(grid, "blue")
pump(lambda: first["UserData"].get("IsFavorite"), timeout=5)
check(state.lib.items["m1"]["UserData"]["IsFavorite"], "toggle favorite")

# open detail of Film 06 (has resume)
grid.move_to(5)
check(grid.current()["Id"] == "m6", "film 06 selected")
press(grid, "ok")
det = s.top
check(name(det) == "DetailScreen", "detail opened")
pump(lambda: det.item.get("People") is not None, timeout=10)
acts = [r[0] for r in det["actions"].list]
check(acts[:2] == ["resume", "start"] and "audio" in acts and "subs" in acts, "detail actions %s" % acts)
check("Video: 1080p H264" in det["tech"].getText(), "tech info: %s" % det["tech"].getText().split("\n")[0])
check("Regie: Rex Regie" in det["people"].getText(), "people")
check(det["progress"].visible and det["progress"].value == 30, "resume progress bar")
pump(lambda: det["backdrop"].instance.pixmap is not None and det["poster"].instance.pixmap is not None, timeout=10)
check(det["poster"].instance.pixmap is not None, "poster loaded")
# choose english audio + german subs
press(det, "yellow")
choose(s, "Audiospur")
choose(s, "Englisch")
check(det.audio_index == 2, "audio index 2 selected")
press(det, "yellow")
choose(s, "Untertitel")
choose(s, "GER")
check(det.sub_index == 3, "subtitle index 3")
# resume playback
det["actions"].moveToIndex(0)
press(det, "ok")
pump(lambda: name(s.top) == "JellyfinPlayer", timeout=10)
player = s.top
check(name(player) == "JellyfinPlayer", "player opened")
pb = state.playback_infos[-1]
check(pb["AudioStreamIndex"] == 2 and pb["SubtitleStreamIndex"] == 3 and pb["StartTimeTicks"] == 30 * 60 * 10000000, "playback info params")
ref = s.nav.history[-1]
check(ref.type == 4097 and "/Videos/m6/stream.mkv?static=true" in ref.path and "api_key=tok123" in ref.path, "direct play url %s" % ref.path)
check(ref.getName() == "Film 06", "service name")
fire_event(player, enigma.iPlayableService.evStart)
pump(lambda: any(r[0] == "/Sessions/Playing" for r in state.reports), timeout=5)
check(any(r[0] == "/Sessions/Playing" for r in state.reports), "playback start reported")
pump(lambda: s.nav.current._seek.seeks, timeout=5)
check(s.nav.current._seek.seeks and s.nav.current._seek.seeks[0] == 30 * 60 * 90000, "resumed at 30min")
pump(lambda: s.nav.current._tracks.selected, timeout=5)
check(s.nav.current._tracks.selected == [1], "audio track 2 (pos 1) selected in E2")
check(player.selected_subtitle == (2, 0, 0, 0, "ger"), "subtitle enabled")
s.nav.current._seek.pos = 40 * 60 * 90000
pump(timeout=0.8)  # report timer fires
press(player, "right")
check(s.nav.current._seek.seeks[-1] == ("rel", 30 * 90000), "right = +30s")
press(player, "leavePlayer")
check(name(s.top) == "DetailScreen", "back on detail after stop")
pump(lambda: any(r[0] == "/Sessions/Playing/Stopped" for r in state.reports), timeout=5)
stop = [r for r in state.reports if r[0] == "/Sessions/Playing/Stopped"][-1][1]
check(stop["PositionTicks"] == (40 * 60 + 30) * 10000000 and stop["PlayMethod"] == "DirectPlay", "stop reported at 40:30 (%s)" % stop["PositionTicks"])
check(s.nav.history[-1].type == 1, "live TV restored")
pump(lambda: det.item["UserData"].get("PlaybackPositionTicks") == stop["PositionTicks"], timeout=5)
check(det.item["UserData"]["PlaybackPositionTicks"] == stop["PositionTicks"], "detail refreshed after playback")
press(det, "cancel")
check(name(s.top) == "GridScreen", "back to grid")

# DTS movie (m7) needs transcoding -> HLS
grid.move_to(6)
press(grid, "playpauseService")
pump(lambda: name(s.top) == "JellyfinPlayer", timeout=10)
player = s.top
ref = s.nav.history[-1]
check("/videos/m7/master.m3u8" in ref.path and "ApiKey=tok123" in ref.path and "api_key" not in ref.path, "DTS -> HLS transcode url")
check(player.stream["play_method"] == "Transcode" and player.stream["is_hls"], "transcode flags")
fire_event(player, enigma.iPlayableService.evStart)
pump(timeout=0.3)
press(player, "leavePlayerOnExit")  # hides infobar first
check(name(s.top) == "JellyfinPlayer", "exit hides infobar first")
press(player, "leavePlayerOnExit")
check(name(s.top) == "GridScreen", "second exit closes")
pump(lambda: "ps-m7" in state.deleted_encodings, timeout=5)
check("ps-m7" in state.deleted_encodings, "transcode encoding stopped")

# 4K HEVC movie (m5): direct on UHD box
grid.move_to(4)
press(grid, "playpauseService")
pump(lambda: name(s.top) == "JellyfinPlayer", timeout=10)
check("/Videos/m5/stream.mkv" in s.nav.history[-1].path, "4K HEVC plays direct on sf8008")
press(s.top, "leavePlayer")

# set max resolution full HD -> m5 transcodes
jfconfig.set_value("max_width", "1920")
press(grid, "playpauseService")
pump(lambda: name(s.top) == "JellyfinPlayer", timeout=10)
check("master.m3u8" in s.nav.history[-1].path, "4K transcodes when limited to 1920")
press(s.top, "leavePlayer")
jfconfig.set_value("max_width", "auto")

# grid menu -> similar
press(grid, "menu")
choose(s, "Ähnliche Titel")
sim = s.top
pump(lambda: len(sim.entries) > 0, timeout=10)
check(name(sim) == "GridScreen" and len(sim.entries) == 5, "similar grid")
press(sim, "cancel")
press(grid, "cancel")
check(name(s.top) == "HomeScreen", "back home")

# --- series flow
home["menu"].moveToIndex(titles.index("Serien"))
press(home, "ok")
sgrid = s.top
pump(lambda: len(sgrid.entries) == 2, timeout=10)
check(sgrid.entries[0]["Name"] == "Serie Eins", "series grid")
check(sgrid["count0"].visible and sgrid["count0"].getText() == "4", "unplayed badge")
press(sgrid, "ok")
sdet = s.top
pump(lambda: sdet.next_up is not None, timeout=10)
acts = [r[0] for r in sdet["actions"].list]
check(acts[0] == "nextup" and "episodes" in acts, "series detail actions %s" % acts)
sdet["actions"].moveToIndex(acts.index("episodes"))
press(sdet, "ok")
eps = s.top
check(name(eps) == "EpisodesScreen", "episodes screen")
pump(lambda: len(eps.entries) == 3, timeout=10)
check(eps.seasons[eps.season_pos]["Id"] == "s1-1", "focused season 1 (next up)")
check(eps.current()["Id"] == "e12", "focused next-up episode e12 (%s)" % eps.current()["Id"])
pump(lambda: len(eps.thumbs) == 3, timeout=10)
check(len(eps.thumbs) == 3, "episode thumbnails")
press(eps, "right")
pump(lambda: eps.entries and eps.entries[0]["Id"] == "e21", timeout=10)
check([e["Id"] for e in eps.entries] == ["e21", "e22", "e23"], "season 2, virtual episode hidden")
check("Staffel 2" in eps["subtitle"].getText(), "season header %s" % eps["subtitle"].getText())
press(eps, "left")
pump(lambda: eps.entries and eps.entries[0]["Id"] == "e11", timeout=10)
eps["list"].moveToIndex(1)
press(eps, "ok")
choose(s, "Von Anfang")
pump(lambda: name(s.top) == "JellyfinPlayer", timeout=10)
player = s.top
check(player.current_item()["Id"] == "e12", "playing e12")
pump(lambda: len(player.queue) > 1, timeout=10)
check([e["Id"] for e in player.queue] == ["e12", "e13", "e21", "e22", "e23"], "autoplay queue %s" % [e["Id"] for e in player.queue])
fire_event(player, enigma.iPlayableService.evStart)
pump(timeout=0.2)
check(not s.nav.current._seek.seeks, "no resume seek when starting from beginning")
# EOF -> next episode in same player
player.doEofInternal(True)
pump(lambda: player.current_item()["Id"] == "e13", timeout=10)
check(player.current_item()["Id"] == "e13" and "/Videos/e13/" in s.nav.history[-1].path, "autoplay next episode")
check(name(s.top) == "JellyfinPlayer", "still in player")
stops = [r[1]["ItemId"] for r in state.reports if r[0] == "/Sessions/Playing/Stopped"]
check(stops[-1] == "e12", "e12 stop reported")
check(state.lib.items["e12"]["UserData"]["Played"], "e12 marked played by server (finished)")
fire_event(player, enigma.iPlayableService.evStart)
pump(lambda: [r for r in state.reports if r[0] == "/Sessions/Playing" and r[1]["ItemId"] == "e13"], timeout=5)
check([r for r in state.reports if r[0] == "/Sessions/Playing" and r[1]["ItemId"] == "e13"], "e13 start reported")
press(player, "moveNext")
pump(lambda: player.current_item()["Id"] == "e21", timeout=10)
check(player.current_item()["Id"] == "e21", "next key -> e21")
press(player, "leavePlayer")
check(name(s.top) == "EpisodesScreen", "back to episodes")
pump(lambda: eps["list"].list and eps.current() is not None and eps.current()["Id"] == "e12", timeout=10)
check(eps.current()["Id"] == "e12", "episode focus restored after player")
press(eps, "menu")
choose(s, "Ganze Staffel als gesehen markieren")
pump(lambda: state.lib.items["s1-1"]["UserData"].get("Played"), timeout=5)
check(state.lib.items["s1-1"]["UserData"].get("Played"), "season marked played")
press(eps, "cancel")
press(sdet, "cancel")
press(sgrid, "cancel")

# --- music
home["menu"].moveToIndex(titles.index("Musik"))
press(home, "ok")
mgrid = s.top
pump(lambda: len(mgrid.entries) == 1, timeout=10)
press(mgrid, "ok")
alb = s.top
check(name(alb) == "EpisodesScreen" and alb.album, "album screen")
pump(lambda: len(alb.entries) == 3, timeout=10)
alb["list"].moveToIndex(1)
press(alb, "ok")
pump(lambda: name(s.top) == "JellyfinPlayer", timeout=10)
player = s.top
check(player.current_item()["Id"] == "t2" and "/Audio/t2/stream?static=true" in s.nav.history[-1].path, "audio direct url")
player.doEofInternal(True)
pump(lambda: player.current_item()["Id"] == "t3", timeout=10)
check(player.current_item()["Id"] == "t3", "next track")
player.doEofInternal(True)
check(name(s.top) == "EpisodesScreen", "album end closes player")
press(alb, "cancel")
press(mgrid, "cancel")

# --- home videos (folders)
home["menu"].moveToIndex(titles.index("Heimvideos"))
press(home, "ok")
hv = s.top
pump(lambda: len(hv.entries) == 1, timeout=10)
check(hv.entries[0]["Type"] == "Folder", "folder listed")
press(hv, "ok")
sub = s.top
pump(lambda: len(sub.entries) == 1, timeout=10)
check(sub.entries[0]["Name"] == "Strand", "folder content")
press(sub, "cancel")
press(hv, "cancel")

# --- search
press(home, "green")
type_text(s, "film 1")
sr = s.top
pump(lambda: len(sr.entries) > 0, timeout=10)
check(name(sr) == "GridScreen" and len(sr.entries) == 10, "search results %d" % len(sr.entries))
press(sr, "cancel")

# --- settings
# --- rule editor: new list "Komödien" (all time, newest first)
press(home, "blue")
rs = s.top
check(name(rs) == "RulesScreen" and len(rs.rules) == 4, "rules screen with 4 default lists")
press(rs, "green")
ed = s.top
check(name(ed) == "RuleEditScreen", "rule editor")
press(ed, "ok")
type_text(s, "Komödien")
fields = [r[0] for r in ed["list"].list]
check("my_series" not in fields, "episode-only fields hidden for movies")
ed["list"].moveToIndex(fields.index("genre"))
press(ed, "ok")
pump(lambda: name(s.top) == "ChoiceBox", timeout=10)
choose(s, "Komödie")
ed["list"].moveToIndex(fields.index("days"))
while ed.rule["days"] != "0":
	press(ed, "left")
ed["list"].moveToIndex(fields.index("type"))
press(ed, "right")
press(ed, "right")
check(ed.rule["type"] == "Episode" and "group" in [r[0] for r in ed["list"].list], "episode fields appear")
press(ed, "left")
press(ed, "left")
press(ed, "green")
check(name(s.top) == "RulesScreen" and len(rs.rules) == 5 and rs.rules[-1]["name"] == "Komödien", "rule saved")
import json as _json
check("Komödien" in [r["name"] for r in _json.loads(jfconfig.config.plugins.jellyfine2.rules.value)], "rules persisted in config")
rs["list"].moveToIndex(4)
press(rs, "ok")
kg = s.top
pump(lambda: len(kg.entries) > 0, timeout=10)
kids = [e["Id"] for e in kg.entries]
check(len(kids) == 19 and kids[0] == "m4", "comedy rule: %d items, first %s" % (len(kids), kids[:1]))
press(kg, "cancel")
press(rs, "cancel")
pump(lambda: "Komödien" in [sec[1] for sec in home.sections], timeout=5)
check("Komödien" in [sec[1] for sec in home.sections], "new list on start screen")

home["menu"].moveToIndex([sec[0] for sec in home.sections].index("settings"))
press(home, "ok")
st = s.top
check(name(st) == "SettingsScreen", "settings opened")
rows = [r[0] for r in st["list"].list]
st["list"].moveToIndex(rows.index("playmode"))
press(st, "right")
check(st.vals["playmode"] == "direct", "change setting")
press(st, "green")
check(jfconfig.get("playmode") == "direct", "setting saved")
jfconfig.set_value("playmode", "auto")
check(name(s.top) == "HomeScreen", "settings closed")

# --- logout + quick connect
press(home, "red")
answer(s, True)
pump(lambda: name(s.top) == "LoginScreen", timeout=5)
check(name(s.top) == "LoginScreen" and not jfconfig.client().token, "logout -> login")
login = s.top
check(login.server == URL, "server remembered")
press(login, "yellow")
pump(lambda: name(s.top) == "QuickConnectScreen", timeout=10)
qc = s.top
check(qc["code"].getText() == "123456", "quick connect code shown")
pump(lambda: name(s.top) == "HomeScreen", timeout=15)
check(name(s.top) == "HomeScreen" and jfconfig.client().token == "tok123", "quick connect login")
home = s.top
pump(lambda: len(home.sections) > 5, timeout=10)
press(home, "cancel")
check(not s.stack, "plugin closed")

# --- static checks
unexpected = [w for w in WARNINGS]
check(not unexpected, "all actions exist in keymap contexts %s" % unexpected[:5])
check(not SKIN_ERRORS, "skins valid %s" % SKIN_ERRORS[:5])
# api routes used match version
new_routes = [r for r in state.requests if r[1].startswith(("/UserViews", "/UserItems", "/UserPlayedItems", "/UserFavoriteItems"))]
old_routes = [r for r in state.requests if r[1].startswith("/Users/u1/")]
if parse_version(VERSION) >= (10, 9, 0):
	check(new_routes and not old_routes, "new routes only")
else:
	check(old_routes and not new_routes, "old routes only")
missing = [r for r in state.requests if r[1] not in ("/System/Info/Public",) and r[0] != "GET" or False]
noauth = [r for r in state.requests if 'Client="Jellyfin Enigma2"' not in r[4].get("Authorization", "")]
check(not noauth, "every request carries the MediaBrowser auth header")
check(len(state.connections) < 40 and len(state.requests) > 150, "keep-alive: %d requests over %d connections" % (len(state.requests), len(state.connections)))

print("\nVERSION %s HEIGHT %d: %d failures" % (VERSION, HEIGHT, len(failures)))
srv.shutdown()
os._exit(1 if failures else 0)
