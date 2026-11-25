"""The ten done-gates for the Acts first pass. Run: python -m pytest -q tests/"""
import hashlib, json, pathlib, re, shutil, sqlite3, subprocess, sys, asyncio

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tests"))
from bibleobj import Bible, bare_dates, make_claim  # noqa: E402
from bibleobj.claims import guard, BareDateError  # noqa: E402
import name_scan, theographic_match, link_sample  # noqa: E402

CORE = ROOT / "dist/acts-core.sqlite"


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


@pytest.fixture(scope="session")
def bible():
    return Bible.open()


@pytest.fixture(scope="session")
def db():
    return sqlite3.connect(CORE)


# ---------------------------------------------------------------- gate 1: build
def test_gate1_build_is_reproducible(tmp_path):
    outs = []
    for i in (1, 2):
        out = tmp_path / f"run{i}"
        subprocess.run([sys.executable, str(ROOT / "build/build.py"), "--out", str(out)], check=True,
                       capture_output=True)
        outs.append(out)
    for name in ("acts-core.sqlite", "acts-theographic.sqlite", "build-report.json"):
        assert sha(outs[0] / name) == sha(outs[1] / name), f"{name} differs between runs"
        assert sha(outs[0] / name) == sha(ROOT / "dist" / name), f"{name} differs from the shipped dist/ copy"


# ----------------------------------------------------------------- gate 2: text
def _source_verses():
    d = json.loads((ROOT / "sources/kjv/Acts.json").read_text(encoding="utf-8"))
    return {(int(c["chapter"]), int(v["verse"])): v["text"] for c in d["chapters"] for v in c["verses"]}


WORD = re.compile(r"[A-Za-z]+(?:['’-][A-Za-z]+)*")


def test_gate2_counts_match_source(bible, db):
    src = _source_verses()
    assert len(src) == 1007
    L = bible.length()
    assert L["as_verses"] == len(src)
    assert L["as_chapters"] == len({c for c, _ in src}) == 28
    assert L["as_words"] == sum(len(WORD.findall(t)) for t in src.values())
    assert L["as_characters"] == sum(len(t) for t in src.values())
    for c in range(1, 29):
        assert bible.length("Acts", c)["as_verses"] == sum(1 for k in src if k[0] == c)
    assert (8, 37) in src  # the TR verse modern texts drop is present in the KJV


def test_gate2_every_verse_by_reference(bible):
    src = _source_verses()
    for (c, v), text in src.items():
        got = bible.passage(f"Acts {c}:{v}")["verses"]
        assert len(got) == 1 and got[0]["text"] == text
    assert len(bible.passage("Acts 13")["verses"]) == sum(1 for k in src if k[0] == 13)
    assert [x["verse"] for x in bible.passage("Acts.2.1-4")["verses"]] == [1, 2, 3, 4]


# ------------------------------------------------------- gate 3: people/places
def test_gate3_every_name_has_an_id():
    found, covered, uncovered = name_scan.scan(CORE)
    assert found > 1000
    assert not uncovered, uncovered[:20]


def test_gate3_theographic_agreement_at_least_95():
    o = theographic_match.compare()
    tot = sum(v[0] for v in o.values()); hit = sum(v[1] for v in o.values())
    assert hit / tot >= 0.95, (hit, tot)


# ------------------------------------------------------------ gate 4: hard names
@pytest.mark.parametrize("name,expect", [
    ("James", {"james-son-of-zebedee", "james-son-of-alphaeus", "james-brother-of-jesus", "james-father-of-judas"}),
    ("Herod", {"herod-the-great", "herod-antipas", "herod-agrippa-i"}),
    ("Philip", {"philip-the-apostle", "philip-the-evangelist"}),
])
def test_gate4_hard_names_are_separate(bible, name, expect):
    got = {m["id"] for m in bible.find(name, kind="person")["matches"]}
    assert expect <= got


@pytest.mark.parametrize("ref,surface,nth,eid", [
    ("Acts.12.2", "James", 1, "james-son-of-zebedee"),      # killed by Herod
    ("Acts.12.17", "James", 1, "james-brother-of-jesus"),   # 'shew these things unto James'
    ("Acts.15.13", "James", 1, "james-brother-of-jesus"),   # Jerusalem council
    ("Acts.1.13", "James", 1, "james-son-of-zebedee"),      # 'Peter, and James, and John'
    ("Acts.1.13", "James", 2, "james-son-of-alphaeus"),     # 'James the son of Alphaeus'
    ("Acts.1.13", "James", 3, "james-father-of-judas"),     # 'Judas the brother of James'
    ("Acts.12.1", "Herod", 1, "herod-agrippa-i"),           # Herod the king who killed James
    ("Acts.4.27", "Herod", 1, "herod-antipas"),             # with Pontius Pilate
    ("Acts.13.1", "Herod", 1, "herod-antipas"),             # 'Herod the tetrarch'
    ("Acts.23.35", "Herod", 1, "herod-the-great"),          # 'Herod's judgment hall' (palace he built)
    ("Acts.6.5", "Philip", 1, "philip-the-evangelist"),     # one of the seven
    ("Acts.21.8", "Philip", 1, "philip-the-evangelist"),
    ("Acts.1.13", "Philip", 1, "philip-the-apostle"),
    ("Acts.10.32", "Simon", 1, "peter"),                     # 'Simon, whose surname is Peter'
    ("Acts.10.32", "Simon", 2, "simon-the-tanner"),          # 'one Simon a tanner'
])
def test_gate4_each_occurrence_resolves_to_the_right_one(db, ref, surface, nth, eid):
    rows = db.execute("SELECT pos, entity_id FROM mentions WHERE ref=? AND surface LIKE ? ORDER BY pos",
                      (ref, surface + "%")).fetchall()
    positions = sorted({p for p, _ in rows})
    assert len(positions) >= nth, rows
    assert {e for p, e in rows if p == positions[nth - 1]} == {eid}, rows


def test_gate4_no_two_ids_share_a_verse_occurrence(db):
    dup = db.execute("""SELECT ref, pos, group_concat(entity_id) FROM mentions m JOIN entities e ON e.id=m.entity_id
                        WHERE e.kind IN ('person','place') GROUP BY ref, pos HAVING count(*)>1""").fetchall()
    assert not dup, dup[:10]


# ----------------------------------------------------------------- gate 5: links
def test_gate5_every_link_cites_a_verse(db):
    verses = {r[0] for r in db.execute("SELECT ref FROM verses")}
    for table, cols in (("mentions", "ref"), ("relations", "ref"), ("itinerary", "ref")):
        bad = [r for r in db.execute(f"SELECT {cols} FROM {table}") if r[0] not in verses]
        assert not bad, (table, bad[:5])
    text = dict(db.execute("SELECT ref, text FROM verses"))
    for s, ref, q in db.execute("SELECT subject, ref, quote FROM relations"):
        assert q and q in text[ref], (s, ref, q)
    for p, ref, q in db.execute("SELECT place_id, ref, quote FROM itinerary"):
        assert q and q in text[ref], (p, ref, q)
    for e, ref, pos, s in db.execute("SELECT entity_id, ref, pos, surface FROM mentions"):
        assert text[ref][pos:pos + len(s)] == s, (e, ref, pos, s)


def test_gate5_random_sample_of_20_is_reviewed():
    sample = link_sample.draw()
    assert len(sample) == 20 and all(x["auto_ok"] for x in sample)
    review = (ROOT / "reports/link-sample.md").read_text()
    assert review.count("| correct |") == 20, "every sampled link needs a hand verdict in reports/link-sample.md"
    for x in sample:
        assert x["ref"] in review


# --------------------------------------------------------------- gate 6: queries
def test_gate6_paul_journey_in_order_with_coordinates(bible):
    j = bible.journey("paul")
    seqs = [s["seq"] for s in j["stops"]]
    assert seqs == sorted(seqs) and len(seqs) >= 60
    order = [(int(s["ref"].split(".")[1]), int(s["ref"].split(".")[2])) for s in j["stops"]]
    assert order == sorted(order), "stops must follow the narrative order of Acts"
    assert all(s["site"] and -90 <= s["site"]["lat"] <= 90 for s in j["stops"])
    assert j["stops"][-1]["place_id"] == "rome"
    legs = [s["leg"] for s in j["stops"]]
    for leg in ("First journey", "Second journey", "Third journey", "Voyage to Rome"):
        assert leg in legs
    gj = bible.journey_geojson("paul")
    assert gj["features"][0]["geometry"]["type"] == "LineString"
    assert (ROOT / "dist/maps/paul-journeys.svg").exists() and (ROOT / "dist/maps/paul-journeys.html").exists()


def test_gate6_contemporaries(bible):
    c = bible.contemporaries("paul")
    ids = {x["id"] for x in c["met_in_text"]}
    assert {"barnabas", "silas", "timothy", "festus", "felix", "herod-agrippa-ii", "gallio"} <= ids
    assert all(x["shared_verses"] for x in c["met_in_text"])
    assert "jacob" not in ids  # Old Testament figures are not contemporaries
    assert c["alive_at_the_same_time"]["type"] == "claim"


def test_gate6_family_path(bible):
    p = bible.relation_path("abraham", "joseph-son-of-jacob")
    assert p["found"] and [s["to"]["id"] for s in p["steps"]] == ["isaac", "jacob", "joseph-son-of-jacob"]
    assert all(s["ref"] and s["quote"] for s in p["steps"])


def test_gate6_antioch_history(bible):
    h = bible.place_history("antioch-of-syria")
    refs = [e["ref"] for e in h["events"]]
    assert "Acts.11.26" in refs and "Acts.13.1" in refs and "Acts.15.35" in refs
    assert "Acts.13.14" not in refs  # Pisidian Antioch is a different place
    assert any("Christians" in e["text"] for e in h["events"])
    assert h["sites"][0]["label"].startswith("Antioch")


# ----------------------------------------------------------------- gate 7: dates
def _all_outputs(bible):
    ents = [r[0] for r in bible.db.execute("SELECT id FROM entities ORDER BY id")]
    for e in ents:
        yield f"entity({e})", bible.entity(e)
        yield f"mentions({e})", bible.mentions(e, 3)
    for e in [r[0] for r in bible.db.execute("SELECT id FROM entities WHERE kind='person'")]:
        yield f"contemporaries({e})", bible.contemporaries(e)
    for e in [r[0] for r in bible.db.execute("SELECT id FROM entities WHERE kind='place'")]:
        yield f"place_history({e})", bible.place_history(e)
    yield "journey", bible.journey("paul")
    yield "geojson", bible.journey_geojson("paul")
    yield "path", bible.relation_path("abraham", "joseph-son-of-jacob")
    yield "info", bible.info()


def test_gate7_no_bare_dates_anywhere(bible):
    n = 0
    for name, out in _all_outputs(bible):
        assert not bare_dates(out), (name, bare_dates(out)[:3])
        n += 1
    assert n > 500


def test_gate7_dates_only_as_labelled_views(bible):
    if bible.layer is None:
        pytest.skip("share-alike layer not built")
    born = bible.entity("jesus")["born"]
    assert born["type"] == "claim" and born["not_stated"] is True
    assert born["views"] and all(v["label"] and v["source"] for v in born["views"])


def test_gate7_checker_catches_bare_dates():
    assert bare_dates({"born": "5 BC"})
    assert bare_dates({"x": [{"note": "died AD 44"}]})
    assert bare_dates({"note": "reigned 37-4 BC"})
    assert not bare_dates({"note": "Acts 13:23, verse 44"})
    assert not bare_dates({"born": make_claim("born", "not-stated", True, [{"label": "L", "value": "5 BC", "source": "s"}])})

    @guard
    def leaky():
        return {"people": [{"id": "paul", "year": 5}]}
    with pytest.raises(BareDateError):
        leaky()
    with pytest.raises(ValueError):
        make_claim("born", "x", True, [{"value": "5 BC"}])  # a view with no label is refused


# ------------------------------------------------------------------- gate 8: MCP
SAMPLE_QUESTIONS = [
    # (question, tool, args, refs that a correct answer must cite, ids that must appear)
    ("Which James did Herod kill?", "find_entity", {"name": "James"}, [], ["james-son-of-zebedee"]),
    ("Which James did Herod kill?", "get_mentions", {"entity_id": "james-son-of-zebedee"}, ["Acts.12.2"], []),
    ("Where did Paul go on his first journey?", "journey", {"person_id": "paul"},
     ["Acts.13.4", "Acts.13.5", "Acts.13.13", "Acts.13.14", "Acts.14.6", "Acts.14.26"], ["salamis", "lystra"]),
    ("Who were Paul's companions in Acts?", "contemporaries", {"person_id": "paul"}, ["Acts.15.40"], ["silas", "barnabas"]),
    ("How is Abraham related to Joseph?", "family_path", {"from_id": "abraham", "to_id": "joseph-son-of-jacob"},
     ["Acts.7.8", "Acts.7.14"], ["isaac", "jacob"]),
    ("Where were the disciples first called Christians?", "place_history", {"place_id": "antioch-of-syria"},
     ["Acts.11.26"], []),
]


async def _ask_server():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "mcp_server/server.py")])
    results = []
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = {t.name for t in (await s.list_tools()).tools}
            for q, tool, args, refs, ids in SAMPLE_QUESTIONS:
                res = await s.call_tool(tool, args)
                results.append((q, tool, json.loads(res.content[0].text), refs, ids))
    return tools, results


def test_gate8_mcp_server_answers_sample_questions():
    tools, results = asyncio.run(_ask_server())
    assert {"get_passage", "find_entity", "journey", "family_path", "contemporaries", "place_history"} <= tools
    for q, tool, data, refs, ids in results:
        blob = json.dumps(data)
        for ref in refs:
            assert ref in blob, (q, tool, ref)
        for i in ids:
            assert f'"{i}"' in blob, (q, tool, i)
        assert not bare_dates(data), (q, tool)


# ----------------------------------------------------------- gate 9: attribution
def test_gate9_attribution_names_every_source_and_license():
    att = (ROOT / "ATTRIBUTION.md").read_text()
    lock = json.loads((ROOT / "sources.lock.json").read_text())
    for name, spec in lock.items():
        assert spec["repo"] in att, name
        assert spec["commit"] in att, name
    for lic in ("public domain", "CC BY 4.0", "CC BY-SA 4.0", "MIT"):
        assert lic.lower() in att.lower(), lic
    db = sqlite3.connect(CORE)
    for sid, lic in db.execute("SELECT id, license FROM sources"):
        assert lic.rstrip(".") in att, (sid, lic)


# ----------------------------------------------------------------- gate 10: vault
def test_gate10_vault_links_all_resolve():
    vault = ROOT / "dist/vault"
    notes = {p.stem: p for p in vault.rglob("*.md")}
    assert len(notes) > 200
    links = 0
    for p in notes.values():
        for target in re.findall(r"\[\[([^\]|#]+)", p.read_text()):
            links += 1
            assert target in notes, (p.name, target)
    assert links > 1000
    db = sqlite3.connect(CORE)
    lab = dict(db.execute("SELECT id, label FROM entities"))
    for eid in lab:  # every entity has a note
        assert any(n == lab[eid] or n.endswith(f"({eid})") for n in notes), eid
    paul, antioch = notes[lab["paul"]].read_text(), notes[lab["antioch-of-syria"]].read_text()
    assert f"[[{lab['antioch-of-syria']}]]" in paul and f"[[{lab['barnabas']}]]" in paul
    assert f"[[{lab['paul']}]]" in antioch and f"[[{lab['barnabas']}]]" in antioch
    assert (vault / ".obsidian/graph.json").exists()
