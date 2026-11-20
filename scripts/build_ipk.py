#!/usr/bin/env python3
# Build an opkg .ipk for the Jellyfin Enigma2 plugin (ar archive: debian-binary, control.tar.gz, data.tar.gz)
import io
import os
import re
import subprocess
import sys
import tarfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src", "JellyfinOpenPLi")
OUTDIR = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "dist"))
DEST = "usr/lib/enigma2/python/Plugins/Extensions/JellyfinOpenPLi"
PKG = "enigma2-plugin-extensions-jellyfine-enigma2-openpli"
# package name and plugin folder up to 1.3.1; the new package replaces it on install
OLD_PKG = "enigma2-plugin-extensions-jellyfine2"
OLD_DEST = "/usr/lib/enigma2/python/Plugins/Extensions/JellyfinE2"
VERSION = re.search(r'CLIENT_VERSION = "([^"]+)"', open(os.path.join(SRC, "jfapi.py")).read()).group(1)
MTIME = int(os.environ.get("SOURCE_DATE_EPOCH") or time.time())

CONTROL = """Package: {pkg}
Version: {ver}
Description: Jellyfin-Client für Enigma2 (OpenPLi 9, Python 3) - von xionix
 Filme, Serien und Musik vom eigenen Jellyfin-Server: moderne Startseite mit
 Titelbild und Kartenreihen, Detailseite mit Schauspielerfotos, Suche mit
 Kategorien, Fortsetzen, Gesehen-Status, Favoriten, Quick Connect, eigene Listen,
 NEU-Markierung, Direktwiedergabe oder HLS-Transkodierung, Auto-Update.
Section: extra
Priority: optional
Maintainer: {maint}
License: GPL-2.0-or-later
Architecture: all
OE: {pkg}
Homepage: {home}
Depends: enigma2
Provides: {old}
Replaces: {old}
Conflicts: {old}
Source: local
""".format(pkg=PKG, old=OLD_PKG, ver=VERSION, maint=os.environ.get("IPK_MAINTAINER", "xionix <https://github.com/xionix3>"),
	home=os.environ.get("IPK_HOMEPAGE", "https://github.com/" + os.environ.get("GITHUB_REPOSITORY", "xionix3/jellyfine_enigma2_openpli")))

POSTINST = """#!/bin/sh
# Umstieg vom alten Paketnamen: Reste des alten Plugin-Ordners entfernen, sobald
# das alte Paket nicht mehr installiert ist (sonst erscheint das Plugin doppelt).
if [ ! -f /var/lib/opkg/info/{old}.control ] && [ ! -f /usr/lib/opkg/info/{old}.control ]; then
	rm -rf {old_dest} >/dev/null 2>&1
fi
echo ""
echo "Jellyfin-Plugin {ver} (von xionix) installiert."
echo "Bitte Enigma2 neu starten (Menü > Standby/Neustart > GUI neu starten)."
echo ""
exit 0
""".format(ver=VERSION, old=OLD_PKG, old_dest=OLD_DEST)

POSTRM = """#!/bin/sh
if [ "$1" = "remove" ] || [ "$1" = "purge" ]; then
	rm -rf /{dest} >/dev/null 2>&1
	rm -rf /tmp/jellyfine2 >/dev/null 2>&1
	echo "Jellyfin-Plugin entfernt. Bitte Enigma2 neu starten."
fi
exit 0
""".format(dest=DEST)

PREINST = """#!/bin/sh
# remove stale bytecode of a previous version
rm -rf /{dest}/__pycache__ >/dev/null 2>&1
exit 0
""".format(dest=DEST)


def add_dir(tar, name):
	ti = tarfile.TarInfo(name)
	ti.type = tarfile.DIRTYPE
	ti.mode = 0o755
	ti.uid = ti.gid = 0
	ti.uname = ti.gname = "root"
	ti.mtime = MTIME
	tar.addfile(ti)


def add_bytes(tar, name, data, mode=0o644):
	ti = tarfile.TarInfo(name)
	ti.size = len(data)
	ti.mode = mode
	ti.uid = ti.gid = 0
	ti.uname = ti.gname = "root"
	ti.mtime = MTIME
	tar.addfile(ti, io.BytesIO(data))


def targz(build):
	buf = io.BytesIO()
	with tarfile.open(fileobj=buf, mode="w:gz", format=tarfile.GNU_FORMAT) as tar:
		build(tar)
	return buf.getvalue()


def build_data(tar):
	add_dir(tar, "./")
	parts = DEST.split("/")
	for i in range(1, len(parts) + 1):
		add_dir(tar, "./" + "/".join(parts[:i]) + "/")
	for root, dirs, files in os.walk(SRC):
		dirs[:] = sorted(d for d in dirs if d != "__pycache__" and not d.startswith("."))
		rel = os.path.relpath(root, SRC)
		base = DEST if rel == "." else "%s/%s" % (DEST, rel.replace(os.sep, "/"))
		if rel != ".":
			add_dir(tar, "./%s/" % base)
		for name in sorted(files):
			if name.endswith((".pyc", ".pyo")) or name.startswith("."):
				continue
			with open(os.path.join(root, name), "rb") as f:
				add_bytes(tar, "./%s/%s" % (base, name), f.read())


def build_control(tar):
	add_dir(tar, "./")
	add_bytes(tar, "./control", CONTROL.encode("utf-8"))
	add_bytes(tar, "./preinst", PREINST.encode("utf-8"), 0o755)
	add_bytes(tar, "./postinst", POSTINST.encode("utf-8"), 0o755)
	add_bytes(tar, "./postrm", POSTRM.encode("utf-8"), 0o755)


def main():
	os.makedirs(OUTDIR, exist_ok=True)
	work = os.path.join(OUTDIR, ".ipkwork")
	os.makedirs(work, exist_ok=True)
	files = {
		"debian-binary": b"2.0\n",
		"control.tar.gz": targz(build_control),
		"data.tar.gz": targz(build_data),
	}
	for name, data in files.items():
		with open(os.path.join(work, name), "wb") as f:
			f.write(data)
	out = os.path.join(OUTDIR, "%s_%s_all.ipk" % (PKG, VERSION))
	if os.path.exists(out):
		os.remove(out)
	subprocess.check_call(["ar", "-rcD", out, "debian-binary", "control.tar.gz", "data.tar.gz"], cwd=work)
	for name in files:
		os.remove(os.path.join(work, name))
	os.rmdir(work)
	print(out)


if __name__ == "__main__":
	main()
