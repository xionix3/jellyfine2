import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "e2stubs"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from mockjf import start_server
from JellyfinE2.jfapi import JellyfinClient
from JellyfinE2.jfrules import run_rule, TEMPLATE, DEFAULT_RULES, load_rules, dump_rules, rule_summary
srv, st, url = start_server("10.10.3")
cl = JellyfinClient(url, "dev", "test")
cl.public_info(); cl.authenticate("patrick", "geheim")
fails = 0
def check(c, m):
    global fails
    print(("ok  : " if c else "FAIL: ") + m); fails += 0 if c else 1
r = dict(TEMPLATE, type="Movie,Series", date_field="released", days="365", unplayed=False, sort="new")
items = run_rule(cl, r)
check([i["Id"] for i in items][:3] == ["m1", "m2", "m3"], "released mixed newest: %s" % [i["Id"] for i in items][:4])
# movies premiere every 20 days (m18 = 360 days ago), both shows premiered years ago -> 18 hits
check(all(i["Type"] in ("Movie", "Series") for i in items) and len(items) == 18, "released within 1y: %d" % len(items))
r = dict(TEMPLATE, type="Movie", days="0", unplayed=False, sort="rating", min_rating="9", limit="50")
items = run_rule(cl, r)
check(items and all(i["CommunityRating"] >= 9 for i in items) and items[0]["CommunityRating"] >= items[-1]["CommunityRating"], "min rating 9 + rating sort (%d)" % len(items))
r = dict(TEMPLATE, type="Series", days="7", sort="new")
items = run_rule(cl, r)
check([i["Id"] for i in items] == ["s1", "s2"] or [i["Id"] for i in items] == ["s2", "s1"], "series with new episodes: %s" % [i["Id"] for i in items])
r = dict(TEMPLATE, type="Movie", days="0", sort="old", unplayed=False, limit="5")
check([i["Id"] for i in run_rule(cl, r)] == ["m40", "m39", "m38", "m37", "m36"], "oldest first")
r = dict(TEMPLATE, type="Episode", days="30", my_series=False, group=False)
check([i["Id"] for i in run_rule(cl, r)] == ["e23", "e211", "e22", "e21"], "all new episodes ungrouped: %s" % [i["Id"] for i in run_rule(cl, r)])
r = dict(TEMPLATE, type="Movie", days="0", sort="random", limit="10")
check(len(run_rule(cl, r)) == 10, "random 10")
check(load_rules("") == DEFAULT_RULES and load_rules("kaputt") == DEFAULT_RULES, "defaults on empty/broken config")
check(load_rules(dump_rules(DEFAULT_RULES)) == DEFAULT_RULES, "roundtrip")
print(rule_summary(DEFAULT_RULES[1]))
# search ranking: exact/prefix title matches first, fuzzy server results last (the "bluey" report)
from JellyfinE2.jfutil import rank_search, norm_text
fuzzy = [{"Id": "1", "Name": "Blue Planet", "Type": "Movie"}, {"Id": "2", "Name": "Die wilden Kerle", "Type": "Movie"},
    {"Id": "3", "Name": "Bluey - Die Folge", "Type": "Episode"}, {"Id": "4", "Name": "Bluey", "Type": "Series"},
    {"Id": "5", "Name": "Mein Freund Bluey", "Type": "Movie"}, {"Id": "6", "Name": "BLUEY: Der Film", "Type": "Movie"},
    {"Id": "7", "Name": "Big Blue", "Type": "Movie", "OriginalTitle": "Le Grand Bleu"}]
ranked = [i["Id"] for i in rank_search("bluey", fuzzy)]
check(ranked == ["4", "6", "3", "5", "1", "2", "7"], "bluey ranking %s" % ranked)
check(norm_text("Amélie: Die fabelhafte Welt!") == "amelie die fabelhafte welt" and [i["Id"] for i in rank_search("amelie", [{"Id": "a", "Name": "x"}, {"Id": "b", "Name": "Amélie"}])] == ["b", "a"],
    "accents ignored")
print("failures", fails); srv.shutdown(); os._exit(1 if fails else 0)
