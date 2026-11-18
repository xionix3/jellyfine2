# Jellyfin for Enigma2

An unofficial [Jellyfin](https://jellyfin.org) client for Enigma2 set-top boxes running **OpenPLi 9.x** (Python 3).
Browse and play movies, shows and music from your own Jellyfin server on your receiver (tested layout on Octagon SF8008, works on any OpenPLi 9 box — pure Python, `Architecture: all`).

*Deutsche Kurzanleitung weiter unten.*

[![CI](https://github.com/xionix3/jellyfine2/actions/workflows/ci.yml/badge.svg)](https://github.com/xionix3/jellyfine2/actions/workflows/ci.yml)

## Features

- Login with username/password or **Quick Connect**, LAN **server discovery**
- Start screen with **Continue watching**, **Next up**, **Recently added**, your libraries and favourites — all previews load in parallel and are cached
- **My lists**: your own filter rules shown on the start screen, e.g. *new movies of the last 30 days* or *new episodes of the shows I watch* (one tile per show with "+3")
- Poster grid with sorting, filters (unplayed, played, favourites, in progress, genre), **NEW** badges, progress bars and the backdrop of the selected title
- Detail page: resume, audio/subtitle track selection, versions, cast, similar titles
- Seasons & episodes browser, music albums
- Playback via the Enigma2 movie player (GStreamer `4097`, or ServiceApp `5001/5002`):
  the box sends a device profile, the server decides between **direct play** (original file, 4K/HEVC on UHD boxes) and **transcoding** (HLS), e.g. for DTS/TrueHD audio or picture-based subtitles
- Resume position, played state and progress are reported to the server, **autoplay next episode**
- Jellyfin **10.8 – 10.11** (route changes of 10.9 handled automatically), HD and Full-HD skins
- Keep-alive connections, prefetching, optional poster cache on HDD/USB

Not included: Live TV/DVR, photos, books.

## Install

Download the `.ipk` from the [latest release](../../releases/latest), copy it to `/tmp` on the box and run:

```sh
opkg install /tmp/enigma2-plugin-extensions-jellyfine2_*_all.ipk
init 4 && sleep 2 && init 3   # restart the GUI
```

Open *Main menu → Jellyfin*. Uninstall with `opkg remove enigma2-plugin-extensions-jellyfine2`.

## Remote control

| Screen | Keys |
|---|---|
| Start | ▲▼ section, OK open, GREEN search, YELLOW refresh, BLUE my lists, MENU settings & more, RED log out |
| Poster grid | arrows, CH+/- page, OK open, PLAY play, RED sort, GREEN filter/genre, YELLOW played ±, BLUE favourite ±, INFO details |
| Details | ▲▼ actions, ◀▶ / CH± scroll text, GREEN play, YELLOW audio/subtitles |
| Episodes | ▲▼ episode, ◀▶ season, OK play, YELLOW details, MENU mark season played |
| Player | ◀ −10 s, ▶ +30 s, PREV/NEXT previous/next episode, INFO info, STOP/EXIT quit |

## Development

Everything runs off-box: a fake Jellyfin server (`tests/mockjf.py`) and stubs of the Enigma2 Python API (`tests/e2stubs/`) let the real screens run headless. The stubs validate skins against the screen components (a missing component is a `SkinError` on a real box), check every key action against the real OpenPLi `keymap.xml`, and catch attributes that would shadow the `Screen` dict API.

```sh
pip install -r requirements-dev.txt
make lint test ipk          # ipk ends up in dist/
make previews               # PNG mock-ups of the skins in skin-previews/
```

CI (GitHub Actions) runs lint, a Python 3.6 syntax check, the test matrix (Python 3.9–3.13 × OpenPLi 9.0/9.2 keymaps × Jellyfin 10.8/10.10/10.11 × HD/FHD) and builds the `.ipk` as an artifact. Pushing a tag `vX.Y.Z` (matching `CLIENT_VERSION` in `src/JellyfinE2/jfapi.py`) publishes a GitHub release with the package.

Layout:

```
src/JellyfinE2/      plugin (installed to /usr/lib/enigma2/python/Plugins/Extensions/JellyfinE2)
  jfapi.py           Jellyfin REST client (pure python)
  jfrules.py         "My lists" rule engine (pure python)
  jfhome/jfgrid/jfdetail/jfepisodes/jfplayer/jflogin/jfsettings/jfrulesui.py   screens
  jfskin.py          embedded skins, designed for 1920x1080 and scaled at runtime
tests/               fake server, Enigma2 stubs, end-to-end tests
scripts/             ipk builder, syntax check, icon generator
```

Bug reports: please attach the lines starting with `[Jellyfin]` from the Enigma2 debug log, your box, image version and Jellyfin version.

## Deutsch

Inoffizieller Jellyfin-Client für Enigma2-Receiver mit **OpenPLi 9**. Filme, Serien und Musik vom eigenen Jellyfin-Server direkt auf dem Receiver.

**Installation:** `.ipk` aus dem [neuesten Release](../../releases/latest) nach `/tmp` auf die Box kopieren, `opkg install /tmp/enigma2-plugin-extensions-jellyfine2_*_all.ipk`, danach GUI neu starten (`init 4 && sleep 2 && init 3`). Start über *Hauptmenü → Jellyfin*.

**Anmeldung:** Server-Adresse (z. B. `http://192.168.1.10:8096`), Benutzer und Passwort, oder Quick Connect (gelb), oder Server im Netzwerk suchen (blau).

**Meine Listen** (blaue Taste): eigene Filterregeln für die Startseite – Inhalt (Filme, Serien mit neuen Folgen, Episoden), Bibliothek, „neu auf dem Server“ oder „neu erschienen“, Zeitraum, nur ungesehene, nur Serien die ich schaue, pro Serie zusammenfassen, Mindestbewertung, Genre, Sortierung. Vorbelegt sind *Neue Filme* und *Neue Episoden meiner Serien*.

**Wiedergabe:** Direkt, wenn die Box das Format kann (SF8008: auch 4K/HEVC), sonst wandelt der Server um (HLS). DTS/TrueHD werden standardmäßig in AC3 gewandelt. Fortschritt und Gesehen-Status landen auf dem Server, die nächste Episode startet automatisch.

**Einstellungen:** Wiedergabe-Modus, max. Bitrate und Auflösung, Codecs (HEVC/DTS/TrueHD/VC-1/VP9), Player (GStreamer/ServiceApp), Autoplay, Fortsetzen, NEU-Markierung, Hintergrundbilder, Position der eigenen Listen, Bild-Cache (RAM oder HDD/USB), SSL-Prüfung.

## License

GPL-2.0-or-later, see [LICENSE](LICENSE). This project is not affiliated with the Jellyfin project or OpenPLi. Use it with your own Jellyfin server and media you have the rights to.
