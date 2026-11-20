#!/usr/bin/env python3
# Translations of the plugin: German texts in the code are the msgids.
#   python3 scripts/i18n.py extract   -> src/JellyfinOpenPLi/locale/JellyfinOpenPLi.pot
#   python3 scripts/i18n.py update    -> merge new texts into locale/<lang>.po (empty msgstr = untranslated)
#   python3 scripts/i18n.py check     -> every text translated, same %-placeholders, nothing obsolete (CI)
import ast
import glob
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src", "JellyfinOpenPLi")
LOCALE = os.path.join(SRC, "locale")
POT = os.path.join(LOCALE, "JellyfinOpenPLi.pot")
LANGS = ("en", "nl")
CALLS = ("_", "N_", "ngettext")

sys.path.insert(0, os.path.join(ROOT, "src"))
from JellyfinOpenPLi.jfi18n import parse_po  # noqa: E402


def extract():
	"""[(msgid, [file:line])] in order of appearance."""
	found = {}
	for path in sorted(glob.glob(os.path.join(SRC, "*.py"))):
		if path.endswith("jfi18n.py"):
			continue
		tree = ast.parse(io.open(path, encoding="utf-8").read())
		for node in ast.walk(tree):
			if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in CALLS:
				args = [a.value for a in node.args[:2] if isinstance(a, ast.Constant) and isinstance(a.value, str)]
				if not args or not args[0]:
					continue
				key = tuple(args) if node.func.id == "ngettext" else args[0]
				found.setdefault(key, []).append("%s:%d" % (os.path.basename(path), node.lineno))
	return sorted(found.items(), key=lambda kv: (kv[1][0].split(":")[0], int(kv[1][0].split(":")[1])))


def quote(text):
	text = text.replace("\\", "\\\\").replace('"', '\\"').replace("\t", "\\t")
	if "\n" not in text:
		return '"%s"' % text
	parts = text.split("\n")
	lines = ['""'] + ['"%s\\n"' % p for p in parts[:-1]] + (['"%s"' % parts[-1]] if parts[-1] else [])
	return "\n".join(lines)


HEADER = '''msgid ""
msgstr ""
"Project-Id-Version: JellyfinOpenPLi\\n"
"Language: %s\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: 8bit\\n"
"Plural-Forms: nplurals=2; plural=(n != 1);\\n"
'''


def write_po(path, lang, entries, catalog=None):
	out = ["# Jellyfin for Enigma2 - %s" % ("template" if catalog is None else "translation: " + lang),
		"# The msgids are the German texts of the plugin.", HEADER % lang]
	for key, refs in entries:
		out.append("#: %s" % " ".join(sorted(set(r.split(":")[0] for r in refs))))
		if isinstance(key, tuple):
			forms = (catalog or {}).get(key[0]) or ["", ""]
			out.append("msgid %s" % quote(key[0]))
			out.append("msgid_plural %s" % quote(key[1]))
			out.append("msgstr[0] %s" % quote(forms[0]))
			out.append("msgstr[1] %s\n" % quote(forms[1]))
		else:
			out.append("msgid %s" % quote(key))
			out.append("msgstr %s\n" % quote((catalog or {}).get(key, "")))
	with io.open(path, "w", encoding="utf-8", newline="\n") as f:
		f.write("\n".join(out))


def load(lang):
	path = os.path.join(LOCALE, "%s.po" % lang)
	if not os.path.exists(path):
		return {}
	with io.open(path, encoding="utf-8") as f:
		return parse_po(f.read())


PLACEHOLDER = re.compile(r"%(?:\([a-z_]+\))?[-+ #0]*\d*(?:\.\d+)?[sdifr%]")


def import_time_calls():
	"""_() evaluated while a module is imported would stay in the language of that moment: use N_ there."""
	found = []
	for path in sorted(glob.glob(os.path.join(SRC, "*.py"))):
		if path.endswith("jfi18n.py"):
			continue
		tree = ast.parse(io.open(path, encoding="utf-8").read())
		parents = {}
		for node in ast.walk(tree):
			for child in ast.iter_child_nodes(node):
				parents[child] = node
		for node in ast.walk(tree):
			if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("_", "ngettext")):
				continue
			q, runtime = node, False
			while q in parents:
				parent = parents[q]
				if isinstance(parent, (ast.FunctionDef, ast.Lambda)) and not isinstance(q, ast.arguments):  # defaults run at def time
					runtime = True
					break
				q = parent
			if not runtime:
				found.append("%s:%d" % (os.path.basename(path), node.lineno))
	return found


def check():
	entries = extract()
	keys = [k for k, _refs in entries]
	ids = set(k[0] if isinstance(k, tuple) else k for k in keys)
	errors = 0
	for lang in LANGS:
		cat = load(lang)
		for key in keys:
			msgid = key[0] if isinstance(key, tuple) else key
			found = cat.get(msgid)
			if isinstance(key, tuple) != isinstance(found, list):
				pairs = []
			elif isinstance(key, tuple):
				pairs = list(zip(key, found))
			else:
				pairs = [(msgid, found)]
			if not pairs or not all(text for _src, text in pairs):
				print("%s: missing translation: %r" % (lang, key))
				errors += 1
				continue
			for src, text in pairs:
				if sorted(PLACEHOLDER.findall(src)) != sorted(PLACEHOLDER.findall(text)):
					print("%s: placeholders differ: %r -> %r" % (lang, src, text))
					errors += 1
				elif src.startswith(" ") != text.startswith(" ") or src.endswith("\n") != text.endswith("\n"):
					print("%s: leading space/trailing newline differ: %r -> %r" % (lang, src, text))
					errors += 1
		for msgid in sorted(set(cat) - ids):
			print("%s: obsolete entry: %r" % (lang, msgid))
			errors += 1
	for where in import_time_calls():
		print("_() runs at import time (use N_ and translate where shown): %s" % where)
		errors += 1
	print("%d texts, %s: %d errors" % (len(ids), "/".join(LANGS), errors))
	return errors


def main():
	cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
	if cmd == "extract":
		write_po(POT, "", extract())
		print(POT)
	elif cmd == "update":
		entries = extract()
		for lang in LANGS:
			write_po(os.path.join(LOCALE, "%s.po" % lang), lang, entries, load(lang))
		write_po(POT, "", entries)
	elif cmd == "check":
		sys.exit(1 if check() else 0)
	else:
		sys.exit("usage: i18n.py extract|update|check")


if __name__ == "__main__":
	main()
