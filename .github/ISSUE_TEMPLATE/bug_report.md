---
name: Bug report / Fehlerbericht
about: Something does not work / Etwas funktioniert nicht
labels: bug
---

**What happened / Was ist passiert?**

**Steps / Schritte**
1.
2.

**Environment / Umgebung**
- Box (e.g. Octagon SF8008):
- Image (e.g. OpenPLi 9.2):
- Plugin version (Plugin browser / `opkg list-installed | grep jellyfin`):
- Jellyfin server version:
- Playback mode / player (Settings):

**Log**
Enable the debug log (Menu → Setup → System → Logs) and paste the lines containing `[Jellyfin]` and any traceback.
Debug-Log einschalten (Menü → Einstellungen → System → Logs) und die Zeilen mit `[Jellyfin]` samt Traceback einfügen.

> ⚠️ **Before posting / Vor dem Posten:** The plugin hides access tokens in its own lines, but Enigma2/GStreamer log the stream address themselves. Replace anything after `api_key=`, `ApiKey=` or `Token=` and your server address if it is reachable from the internet.
> Das Plugin blendet Zugangsschlüssel in seinen eigenen Zeilen aus, Enigma2/GStreamer schreiben die Stream-Adresse aber selbst ins Log. Alles nach `api_key=`, `ApiKey=` oder `Token=` und ggf. die aus dem Internet erreichbare Server-Adresse unkenntlich machen.

```
```
