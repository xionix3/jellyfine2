# Changelog

## [1.1.1] - 2026-11-18

- Fix: closing the list editor without saving could crash the plugin
- Fix: values in the selected row of settings/list screens were invisible (accent text on accent background)
- Fix: grouped "new episodes" tiles no longer show a misleading progress bar; the "gesehen" badge in episode lists is fully visible
- List editor: blue key renames the list
- README in German (default), English and Dutch with screenshots of the real screens; stable asset name for the one-line install

## [1.1.0] - 2026-11-18

- **My lists** ("Meine Listen"): user defined filter rules shown on the start screen (type, library, added vs. released, time window, unplayed, shows I watch, group per show, minimum rating, genre, sort, limit). Defaults: *Neue Filme*, *Neue Episoden meiner Serien*, *Serien mit neuen Folgen*, *Neu erschienen*
- **NEW** badge on posters and episode lists (configurable window)
- Backdrop of the selected title behind grid and start screen (can be disabled)
- Faster: HTTP keep-alive connection reuse, all start screen previews load in parallel and stay cached between plugin starts, next grid page posters are prefetched, optional poster cache on HDD/USB
- List item heights now always match the skin
- Requests only valid `ItemFields`

## [1.0.0] - 2026-11-17

- First release: login (password, Quick Connect, LAN discovery), start screen, poster grid with sort/filter/genre, details, seasons/episodes, music albums, search, settings
- Playback through the Enigma2 movie player with device profile, direct play or HLS transcoding, resume, progress reporting, autoplay next episode, audio/subtitle preselection
- Jellyfin 10.8 – 10.11, OpenPLi 9.0 – 9.2, HD and FHD skins
