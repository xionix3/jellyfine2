#!/usr/bin/env python3
"""Fail if plugin sources use syntax newer than the oldest supported Python (3.6) or do not compile."""
import ast
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
errors = 0
for path in sorted(glob.glob(os.path.join(ROOT, "src", "JellyfinOpenPLi", "*.py"))):
	src = open(path, encoding="utf-8").read()
	try:
		ast.parse(src, filename=path, feature_version=(3, 6))
		compile(src, path, "exec")
	except SyntaxError as e:
		print("ERROR %s: %s" % (os.path.relpath(path, ROOT), e))
		errors += 1
	if "\r" in src:
		print("ERROR %s: CRLF line endings" % path)
		errors += 1
print("%d files checked, %d errors" % (len(glob.glob(os.path.join(ROOT, "src", "JellyfinOpenPLi", "*.py"))), errors))
sys.exit(1 if errors else 0)
