import os
import xml.etree.ElementTree as ET

KEYMAP = {}
WARNINGS = []
_km = os.environ.get("E2_KEYMAP", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "keymap.xml"))
for m in ET.parse(_km).getroot().iter("map"):
	ctx = m.get("context")
	acts = KEYMAP.setdefault(ctx, set())
	for k in m.iter("key"):
		acts.add(k.get("mapto"))


class ActionMap(object):
	def __init__(self, contexts=None, actions=None, prio=0):
		self.contexts = contexts or []
		self.actions = actions or {}
		self.prio = prio
		self.enabled = True
		for c in self.contexts:
			if c not in KEYMAP:
				WARNINGS.append("unknown context %s" % c)
		for a in self.actions:
			if not any(a in KEYMAP.get(c, ()) for c in self.contexts):
				WARNINGS.append("action %s not in contexts %s" % (a, self.contexts))
		for a, f in self.actions.items():
			assert callable(f), a

	def setEnabled(self, e):
		self.enabled = e


class NumberActionMap(ActionMap):
	pass


class HelpableActionMap(ActionMap):
	def __init__(self, parent, contexts, actions=None, prio=0, description=None):
		acts = {}
		for k, v in (actions or {}).items():
			acts[k] = v[0] if isinstance(v, tuple) else v
		ActionMap.__init__(self, contexts if isinstance(contexts, list) else [contexts], acts, prio)
