# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
# Jellyfin for Enigma2 - "Meine Listen": list overview and rule editor
from __future__ import absolute_import

import copy

from enigma import RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_CENTER

from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MultiContent import MultiContentEntryText
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.VirtualKeyBoard import VirtualKeyBoard

from . import jfconfig
from .jfcommon import JFScreen, make_list, text_row
from .jfrules import DEFAULT_RULES, RULE_FIELDS, choice_label, field_applies, new_rule, rule_summary
from .jfskin import C_ACCENT, C_DIM, S, list_skin

ROW_W = 1200
RULE_ROW_H = 84


class RulesScreen(JFScreen):
	def __init__(self, session, views=None):
		JFScreen.__init__(self, session)
		self.skin = list_skin("JellyfinE2Rules", item_height=RULE_ROW_H)
		self.skinName = "JellyfinE2Rules"
		self.views = views or []
		self.rules = jfconfig.load_rules()
		self["title"] = Label("Meine Listen")
		self["subtitle"] = Label("Eigene Filterregeln, z.B. neueste Filme oder neue Episoden deiner Serien")
		self["list"] = make_list(fonts=((32,), (24,)), item_height=RULE_ROW_H)
		self["description"] = Label("")
		self["status"] = Label("")
		self.add_keys(red="Löschen", green="Neue Liste", yellow="Bearbeiten", blue="Nach oben")
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "MenuActions"], {
			"ok": self.key_ok,
			"cancel": self.close,
			"up": self["list"].up,
			"down": self["list"].down,
			"red": self.key_delete,
			"green": self.key_new,
			"yellow": self.key_edit,
			"blue": self.key_move_up,
			"menu": self.key_menu,
		}, -1)
		self["list"].onSelectionChanged.append(self.update_description)
		self.onLayoutFinish.append(self.build)

	def row(self, i, rule):
		home = "Startseite" if rule.get("home") else ""
		return [i,
			MultiContentEntryText(pos=(S(18), S(6)), size=(S(ROW_W - 220), S(42)), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=rule.get("name", "?")),
			MultiContentEntryText(pos=(S(ROW_W - 200), S(6)), size=(S(182), S(42)), font=1, flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER, text=home, color=C_ACCENT),
			MultiContentEntryText(pos=(S(18), S(46)), size=(S(ROW_W - 36), S(34)), font=1, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=rule_summary(rule), color=C_DIM),
		]

	def build(self, select=None):
		idx = self["list"].getSelectedIndex() if self["list"].list else 0
		if select is not None:
			idx = select
		self["list"].setList([self.row(i, r) for i, r in enumerate(self.rules)])
		if self.rules:
			self["list"].moveToIndex(max(0, min(idx, len(self.rules) - 1)))
		self.update_description()

	def save(self):
		jfconfig.save_rules(self.rules)

	def current_index(self):
		cur = self["list"].getCurrent()
		return cur[0] if cur else None

	def update_description(self):
		i = self.current_index()
		if i is None:
			self["description"].setText("Noch keine Listen. Grün legt eine neue an, MENU stellt die Standardlisten wieder her.")
		else:
			self["description"].setText("OK: Liste anzeigen   |   Gelb: Regeln bearbeiten   |   MENU: Startseite an/aus")

	def key_ok(self):
		i = self.current_index()
		if i is None:
			return
		from .jfnav import open_grid
		rule = self.rules[i]
		open_grid(self, {"title": rule.get("name", ""), "source": "rule", "rule": copy.deepcopy(rule), "sortable": False})

	def key_new(self):
		self.session.openWithCallback(self.new_saved, RuleEditScreen, new_rule(), self.views)

	def new_saved(self, rule=None):
		if rule:
			self.rules.append(rule)
			self.save()
			self.build(select=len(self.rules) - 1)

	def key_edit(self):
		i = self.current_index()
		if i is not None:
			self.session.openWithCallback(lambda r=None, i=i: self.edited(i, r), RuleEditScreen, copy.deepcopy(self.rules[i]), self.views)

	def edited(self, i, rule):
		if rule:
			self.rules[i] = rule
			self.save()
			self.build(select=i)

	def key_delete(self):
		i = self.current_index()
		if i is None:
			return
		name = self.rules[i].get("name", "")
		self.session.openWithCallback(lambda yes=False, i=i: yes and self.delete(i), MessageBox, "Liste '%s' löschen?" % name, MessageBox.TYPE_YESNO, default=False)

	def delete(self, i):
		del self.rules[i]
		self.save()
		self.build(select=i)

	def key_move_up(self):
		i = self.current_index()
		if i:
			self.rules[i - 1], self.rules[i] = self.rules[i], self.rules[i - 1]
			self.save()
			self.build(select=i - 1)

	def key_menu(self):
		lst = []
		i = self.current_index()
		if i is not None:
			lst.append(("Von der Startseite nehmen" if self.rules[i].get("home") else "Auf der Startseite zeigen", "home"))
			lst.append(("Nach unten verschieben", "down"))
			lst.append(("Liste duplizieren", "dup"))
		lst.append(("Standardlisten hinzufügen", "defaults"))
		self.session.openWithCallback(self.menu_chosen, ChoiceBox, title="Meine Listen", list=lst)

	def menu_chosen(self, choice):
		if choice is None:
			return
		a = choice[1]
		i = self.current_index()
		if a == "home" and i is not None:
			self.rules[i]["home"] = not self.rules[i].get("home")
			self.save()
			self.build()
		elif a == "down" and i is not None and i + 1 < len(self.rules):
			self.rules[i + 1], self.rules[i] = self.rules[i], self.rules[i + 1]
			self.save()
			self.build(select=i + 1)
		elif a == "dup" and i is not None:
			dup = copy.deepcopy(self.rules[i])
			dup["id"] = new_rule()["id"]
			dup["name"] = dup.get("name", "") + " (Kopie)"
			self.rules.insert(i + 1, dup)
			self.save()
			self.build(select=i + 1)
		elif a == "defaults":
			have = set(r.get("id") for r in self.rules)
			added = [copy.deepcopy(r) for r in DEFAULT_RULES if r["id"] not in have]
			self.rules.extend(added)
			self.save()
			self.build()
			self["status"].setText("%d Standardliste(n) hinzugefügt." % len(added) if added else "Alle Standardlisten sind schon vorhanden.")


class RuleEditScreen(JFScreen):
	def __init__(self, session, rule, views=None):
		JFScreen.__init__(self, session)
		self.skin = list_skin("JellyfinE2RuleEdit", item_height=62)
		self.skinName = "JellyfinE2RuleEdit"
		self.rule = dict(rule)
		self.views = views
		self["title"] = Label("Liste bearbeiten")
		self["subtitle"] = Label("")
		self["list"] = make_list(fonts=((28,), (28,)), item_height=62)
		self["description"] = Label("")
		self["status"] = Label("")
		self.add_keys(red="Abbrechen", green="Speichern", yellow="Vorschau", blue="Name ändern")
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "ChannelSelectBaseActions"], {
			"ok": self.key_ok,
			"cancel": self.close,
			"up": self["list"].up,
			"down": self["list"].down,
			"left": lambda: self.cycle(-1),
			"right": lambda: self.cycle(1),
			"nextBouquet": self["list"].pageDown,
			"prevBouquet": self["list"].pageUp,
			"red": self.close,
			"green": self.key_save,
			"yellow": self.key_preview,
			"blue": self.key_rename,
		}, -1)
		self["list"].onSelectionChanged.append(self.update_description)
		self.onLayoutFinish.append(self.build)

	def key_rename(self):
		self.session.openWithCallback(self.name_entered, VirtualKeyBoard, title="Name der Liste", text=self.rule.get("name", ""))

	def value_text(self, fid):
		v = self.rule.get(fid)
		if fid == "name":
			return v or "(ohne Namen)"
		if fid == "library":
			return self.rule.get("library_name") or "Alle Bibliotheken"
		if fid == "genre":
			return v or "Alle Genres"
		return choice_label(fid, v)

	def build(self):
		rows = []
		for fid, label, choices, _help, _only in RULE_FIELDS:
			if not field_applies(fid, self.rule):
				continue
			arrows = "<  %s  >" if choices else "%s  ..."
			rows.append(text_row(fid, label, ROW_W, 62, value=arrows % self.value_text(fid), value_width=640, value_color=C_ACCENT))
		idx = self["list"].getSelectedIndex() if self["list"].list else 0
		self["list"].setList(rows)
		self["list"].moveToIndex(min(idx, len(rows) - 1))
		self["subtitle"].setText(rule_summary(self.rule))
		self.update_description()

	def current_field(self):
		cur = self["list"].getCurrent()
		return cur[0] if cur else None

	def update_description(self):
		fid = self.current_field()
		for f in RULE_FIELDS:
			if f[0] == fid:
				self["description"].setText(f[3] or "Links/Rechts ändert den Wert.")

	def cycle(self, step):
		fid = self.current_field()
		for f in RULE_FIELDS:
			if f[0] == fid and f[2]:
				values = [v for v, _ in f[2]]
				cur = self.rule.get(fid)
				pos = values.index(cur) if cur in values else 0
				self.rule[fid] = values[(pos + step) % len(values)]
				self.build()
				return

	def key_ok(self):
		fid = self.current_field()
		if fid == "name":
			self.session.openWithCallback(self.name_entered, VirtualKeyBoard, title="Name der Liste", text=self.rule.get("name", ""))
		elif fid == "library":
			self.choose_library()
		elif fid == "genre":
			self.choose_genre()
		else:
			self.cycle(1)

	def name_entered(self, text):
		if text is not None and text.strip():
			self.rule["name"] = text.strip()
			self.build()

	def choose_library(self):
		def show(views):
			self.views = views
			lst = [("Alle Bibliotheken", ("", ""))] + [(v.get("Name", "?"), (v.get("Id"), v.get("Name", ""))) for v in views]
			self.session.openWithCallback(self.library_chosen, ChoiceBox, title="Bibliothek", list=lst)
		if self.views:
			show(self.views)
		else:
			self.run(self.cl.views, callback=show, status="Lade Bibliotheken ...")

	def library_chosen(self, choice):
		if choice is not None:
			self.rule["library"], self.rule["library_name"] = choice[1]
			self.build()

	def choose_genre(self):
		types = "Movie,Series" if self.rule.get("type") == "Episode" else self.rule.get("type")

		def show(genres):
			lst = [("Alle Genres", "")] + [(g.get("Name", "?"), g.get("Name", "")) for g in genres]
			self.session.openWithCallback(self.genre_chosen, ChoiceBox, title="Genre", list=lst)
		self.run(self.cl.genres, self.rule.get("library") or None, types, callback=show)
		self["status"].setText("")

	def genre_chosen(self, choice):
		if choice is not None:
			self.rule["genre"] = choice[1]
			self.build()

	def key_save(self):
		if not (self.rule.get("name") or "").strip():
			self["status"].setText("Bitte einen Namen vergeben.")
			return
		if self.rule.get("type") != "Episode":
			self.rule["my_series"] = False
			self.rule["group"] = False
		self.close(self.rule)

	def key_preview(self):
		from .jfnav import open_grid
		open_grid(self, {"title": "Vorschau: %s" % self.rule.get("name", ""), "source": "rule", "rule": dict(self.rule), "sortable": False})
