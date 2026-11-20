# Local helpers (CI runs the same commands)
OPENPLI_BRANCH ?= release-9.2
JELLYFIN ?= 10.10.7

.PHONY: all lint test ipk previews screenshots banner clean

all: lint test ipk

tests/keymap.xml:
	curl -fsSL https://raw.githubusercontent.com/OpenPLi/enigma2/$(OPENPLI_BRANCH)/data/keymap.xml -o $@

lint:
	python3 -m pyflakes src/JellyfinOpenPLi scripts tests/*.py
	python3 scripts/check_syntax.py

test: tests/keymap.xml
	python3 tests/test_rules.py
	python3 tests/test_flow.py $(JELLYFIN)
	python3 tests/test_flow.py $(JELLYFIN) 720

ipk:
	python3 scripts/build_ipk.py dist

previews:
	python3 tests/render_skins.py skin-previews

screenshots: tests/keymap.xml
	python3 tests/screenshots.py docs/screenshots

banner:
	python3 scripts/make_banner.py

clean:
	rm -rf dist skin-previews tests/keymap.xml
	find . -name __pycache__ -prune -exec rm -rf {} +
