# Changelog

## [1.3.2] - 2026-11-20

- New name: the project lives at [xionix3/jellyfine_enigma2_openpli](https://github.com/xionix3/jellyfine_enigma2_openpli), the package is now `enigma2-plugin-extensions-jellyfine-enigma2-openpli` (opkg allows no underscores in package names) and the plugin folder `Extensions/JellyfinOpenPLi`
- The new package replaces `enigma2-plugin-extensions-jellyfine2` on install (Replaces/Conflicts), leftovers of the old folder are removed; settings, server login and lists are kept
- Releases carry the package under the new and the old stable name, so the auto-update of 1.2.x/1.3.x and old install commands keep working

## [1.3.1] - 2026-11-18

- Security: access tokens and passwords no longer appear in the plugin's log lines or error messages (the play line printed the `ApiKey` of transcoded streams - users post these lines in bug reports)
- Bug report template warns to remove tokens from logs (Enigma2/GStreamer log the stream address themselves)
- `SECURITY.md` with private vulnerability reporting; Dependabot keeps the CI actions up to date

## [1.3.0] - 2026-11-18

- **Movies, shows and every library look like the start screen**: rows for continue watching, recently added, new releases, best rated unwatched, favourites, every genre (or every folder) and A-Z; up/down jumps through them instead of a sub menu. Red shows all titles of a row as a grid
- **Search finds exact matches only**: every category (movies, shows, episodes, collections, music, people) is searched on its own, plus titles starting with the term; results that do not contain the term are dropped. Results are shown as one row per category
- Fix: shows were missing in search results - a single query for all types was filled up with fuzzy movie hits of the server before any show appeared
- **No more stutter**: pictures are decoded in ePicLoad threads instead of the GUI thread, at the exact widget size (no scaling while painting), and kept in memory; moving inside the visible cards only moves the frame, unchanged cards are not repainted, nothing is hidden and shown again while a picture loads
- **Details page**: the picture stays visible on the right, the description has room to be read completely, the cast row with photos only appears with the down key (pills and technical line make room for it); the backdrop is there at once when coming from a card
- Sidebar in every row screen; sub screens hand the sidebar back to the start screen (flat screen stack)
- Skin pictures exist pixel exact for 1080p and 720p

## [1.2.0] - 2026-11-18

- **Modern start screen**: large backdrop with title, info and buttons of the focused item, rows of 16:9 cards (one row per section), sidebar with search, movies, shows, lists and settings. The classic layout stays available (setting *Startseite* or MENU)
- **Glass look**: rounded translucent panels, selection frames, buttons and badges as alpha PNGs
- **Details page** redesigned: backdrop, action buttons, **cast row with actor photos** (OK lists the person's titles), full cast as poster grid
- **Search**: results in relevance order (exact title matches first) - an alphabetical sort used to push exact hits like "Bluey" behind the result limit; results that do not contain the term go to the end. New **categories** (movies, shows, episodes, collections, music, people) with counts; people search
- **Category filter** for mixed lists (favourites, collections, own lists, similar titles, continue watching)
- **Auto-update**: checks the GitHub releases on start (at most every 12 h), downloads the package, verifies `SHA256SUMS`, installs with opkg and offers a GUI restart; manual check via MENU, can be turned off
- **Releases are created by CI** when `CLIENT_VERSION` is bumped on `main`
- Fix: backdrops were not visible on the box in 1.0/1.1 - Enigma2 does not blend translucent label fills, the dark overlay replaced the picture. Overlays are now alpha PNGs
- Credits: "von xionix" in the plugin list, settings, about dialog and package

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
