# Sicherheit / Security

## Sicherheitslücke melden

Bitte **kein öffentliches Issue** anlegen. Melde die Lücke vertraulich über
[„Report a vulnerability“](https://github.com/xionix3/jellyfine2/security/advisories/new)
(Reiter *Security* im Repository). Beschreibe, was passiert und wie man es nachvollziehen kann.
Ich melde mich so schnell wie möglich und veröffentliche die Korrektur als neue Version.

## Was das Plugin tut

- Es spricht nur mit **deinem** Jellyfin-Server und – für das Auto-Update – mit `api.github.com`
  und `github.com` (Releases dieses Repositorys). „Server suchen“ schickt eine Anfrage ins lokale
  Netz (UDP 7359). Es gibt keine Telemetrie.
- Zugangsdaten: gespeichert wird nur das Zugriffs-Token des Servers in der Enigma2-Konfiguration,
  nicht das Passwort. Das Plugin schreibt Tokens und Passwörter nicht ins Log.
- Auto-Update: lädt nur Releases dieses Repositorys, prüft die Datei gegen `SHA256SUMS` und
  installiert erst nach deiner Bestätigung. Abschaltbar unter *Einstellungen → Automatisch nach
  Updates suchen*.

## Unterstützte Versionen

Sicherheitskorrekturen gibt es für die jeweils neueste Version (siehe Releases).

---

## Reporting a vulnerability

Please **do not open a public issue**. Report it privately via
[“Report a vulnerability”](https://github.com/xionix3/jellyfine2/security/advisories/new)
(*Security* tab of the repository) with a description and steps to reproduce.
Fixes are published as a new release.

## What the plugin does

- It only talks to **your** Jellyfin server and, for the auto-update, to `api.github.com` and
  `github.com` (releases of this repository). "Server suchen" sends a discovery request into the
  local network (UDP 7359). No telemetry.
- Only the server's access token is stored in the Enigma2 settings, never the password.
  Tokens and passwords are not written to the log.
- Auto-update: only releases of this repository, verified against `SHA256SUMS`, installed after
  you confirm. Can be turned off in the settings.

Security fixes are provided for the latest release.
