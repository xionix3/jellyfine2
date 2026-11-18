# Changelog

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
