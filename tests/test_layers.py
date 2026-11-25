"""Tests for the second round: typed edges, the Greek lemma layer, speakers, the library, MCP tools and raw SQL.

Run with the gates: python -m pytest -q tests/
"""
import asyncio, json, pathlib, re, sqlite3, sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from bibleobj import Bible, EntitySet, parse_ref  # noqa: E402
from bibleobj.books import BOOKS  # noqa: E402

CORE = ROOT / "dist/acts-core.sqlite"


@pytest.fixture(scope="module")
def b():
    return Bible.open()


@pytest.fixture(scope="module")
def db():
    return sqlite3.connect(CORE)


# ------------------------------------------------------------------ text
def test_all_66_books_with_kjv_counts(db):
    assert db.execute("SELECT count(*) FROM books").fetchone()[0] == 66
    assert db.execute("SELECT count(*) FROM verses").fetchone()[0] == 31102  # the standard KJV verse count
    assert [r[0] for r in db.execute("SELECT osis FROM books")] and len(BOOKS) == 66


def test_refs_parse_for_any_book(b):
    assert parse_ref("1 Cor 13:4-7") == ("1Cor", 13, 4, 7)
    assert parse_ref("John.3.16") == ("John", 3, 16, 16)
    assert b.passage("John 3:16")["verses"][0]["text"].startswith("For God so loved the world")


# ----------------------------------------------------------------- edges
def test_every_edge_quote_sits_at_its_span(db):
    text = dict(db.execute("SELECT ref, text FROM verses"))
    n = 0
    for s, t, o, ref, a, z, q in db.execute('SELECT subject, type, object, ref, start, "end", quote FROM edges'):
        assert text[ref][a:z] == q, (s, t, o, ref)
        n += 1
    assert n >= 140


def test_every_edge_type_is_declared_and_ids_exist(db):
    types = {r[0] for r in db.execute("SELECT type FROM edge_types")}
    ids = {r[0] for r in db.execute("SELECT id FROM entities")}
    for s, t, o in db.execute("SELECT subject, type, object FROM edges"):
        assert t in types and s in ids and o in ids, (s, t, o)


def test_old_tables_survive_as_views(db):
    kinds = dict(db.execute("SELECT name, type FROM sqlite_master WHERE name IN ('relations','itinerary')"))
    assert kinds == {"relations": "view", "itinerary": "view"}
    assert db.execute("SELECT count(*) FROM itinerary WHERE person_id='paul'").fetchone()[0] >= 60


def test_wrote_to_minus_visited(b):
    letters_only = b.paul.wrote_to - b.paul.visited
    assert isinstance(letters_only, EntitySet)
    assert "colossae" in letters_only
    assert "rome" not in letters_only and "corinth" not in letters_only  # he wrote to them and went there
    assert "galatia" not in letters_only  # he went "throughout Phrygia and the region of Galatia" (Acts 16:6)
    places = [e for e in letters_only if e.kind == "place"]
    assert [e.id for e in places] == ["colossae"]
    ev = letters_only.evidence["colossae"][0]
    assert ev["ref"] == "Col.1.2" and "Colosse" in ev["quote"]


def test_accessors_and_inverses(b):
    assert "peter-pentecost" in b.peter.sermons
    assert "paul" in b.colossae.written_to_by
    assert "isaac" in b.abraham.children and "abraham" in b.isaac.parents
    assert "james-son-of-zebedee" in b.herod_agrippa_i.killed
    assert {"jesus-bread-of-life", "jesus-light-of-the-world"} <= set(b.jesus.sermons.ids)
    with pytest.raises(AttributeError):
        b.paul.not_a_relationship


def test_new_type_needs_no_code(b):
    # every row of edge_types is reachable by name with no code naming it
    for t in b.edge_types():
        for name in (t["type"], t["accessor"], t["inverse_accessor"]):
            assert name in b._accessors(), name


# ----------------------------------------------------------------- Greek
GOLD = [  # (ref, KJV word, which occurrence, Strong's) checked against the Greek text by hand
    ("John.21.15", "lovest", 0, "G0025"), ("John.21.15", "love", 0, "G5368"),
    ("John.21.16", "lovest", 0, "G0025"), ("John.21.16", "love", 0, "G5368"),
    ("John.21.17", "lovest", 0, "G5368"), ("John.21.17", "Lovest", 0, "G5368"), ("John.21.17", "love", 0, "G5368"),
    ("John.3.16", "loved", 0, "G0025"), ("John.11.3", "lovest", 0, "G5368"), ("John.11.5", "loved", 0, "G0025"),
    ("John.11.36", "loved", 0, "G5368"), ("John.1.1", "Word", 0, "G3056"), ("John.1.1", "God", 0, "G2316"),
    ("Acts.2.38", "Repent", 0, "G3340"), ("Acts.2.38", "baptized", 0, "G0907"), ("Acts.9.4", "persecutest", 0, "G1377"),
    ("Acts.17.22", "superstitious", 0, "G1174"), ("Acts.16.31", "Believe", 0, "G4100"), ("Acts.1.8", "witnesses", 0, "G3144"),
]


@pytest.mark.parametrize("ref,word,nth,strong", GOLD)
def test_alignment_gold(db, ref, word, nth, strong):
    rows = db.execute("""SELECT g.strong FROM tokens t JOIN alignments a ON a.ref=t.ref AND a.token_idx=t.idx
                         JOIN greek_words g ON g.ref=a.ref AND g.idx=a.greek_idx WHERE t.ref=? AND t.text=? ORDER BY t.idx""",
                      (ref, word)).fetchall()
    assert rows and rows[nth][0] == strong, (ref, word, rows)


def test_greek_is_textus_receptus(db):
    # Acts 8:37 is in the TR (and the KJV) but not in NA28; the TR reading must be present
    assert db.execute("SELECT count(*) FROM greek_words WHERE ref='Acts.8.37'").fetchone()[0] > 10
    # John 5:4 likewise
    assert db.execute("SELECT count(*) FROM greek_words WHERE ref='John.5.4'").fetchone()[0] > 10


def test_lexicon_names_both_loves(b):
    lex = {l["strong"]: l["lexicon"]["lemma"] for l in b.lemma_usage("G0025")["lemmas"] + b.lemma_usage("G5368")["lemmas"]}
    assert lex == {"G0025": "ἀγαπάω", "G5368": "φιλέω"}
    assert b.lemma_usage("agapaō")["lemmas"][0]["strong"] == "G0025"


def test_most_content_words_are_aligned(db):
    stats = json.loads(db.execute("SELECT value FROM meta WHERE key='layer_stats'").fetchone()[0])
    assert stats["aligned"] / stats["content_tokens"] > 0.85


# --------------------------------------------------------------- speakers
def _speaker_at(db, ref, needle):
    text = db.execute("SELECT text FROM verses WHERE ref=?", (ref,)).fetchone()[0]
    i = text.index(needle)
    r = db.execute('SELECT speaker, basis FROM utterances WHERE ref=? AND start<=? AND "end">?', (ref, i, i)).fetchone()
    return r


def test_red_letter_and_curated_speakers(db):
    assert _speaker_at(db, "John.3.16", "For God so loved") == ("jesus", "red-letter edition")
    assert _speaker_at(db, "Acts.9.5", "I am Jesus whom thou persecutest") == ("jesus", "red-letter edition")
    assert _speaker_at(db, "Acts.2.22", "Ye men of Israel") == ("peter", "curated speech")
    assert _speaker_at(db, "Acts.17.23", "UNKNOWN GOD") == ("paul", "curated speech")
    assert _speaker_at(db, "Acts.7.2", "Men, brethren, and fathers") == ("stephen", "curated speech")
    assert _speaker_at(db, "Acts.2.14", "Peter, standing up") is None  # the narrator's words are nobody's


def test_quoted_words_of_jesus_inside_a_speech(db):
    # Peter, retelling Cornelius's house, quotes Jesus: those words stay Jesus's and say who quoted them
    r = db.execute("SELECT speaker, note FROM utterances WHERE ref='Acts.11.16' AND basis='red-letter edition'").fetchone()
    assert r[0] == "jesus" and r[1].startswith("quoted by peter")
    assert _speaker_at(db, "Acts.11.16", "Then remembered I the word") == ("peter", "curated speech")


def test_no_two_speakers_share_a_character(db):
    rows = db.execute('SELECT ref, start, "end", basis FROM utterances ORDER BY ref, start').fetchall()
    for (r1, a1, z1, b1), (r2, a2, z2, b2) in zip(rows, rows[1:]):
        if r1 == r2:
            assert z1 <= a2, (r1, a1, z1, b1, a2, b2)


def test_drafted_speaker_examples(db):
    assert _speaker_at(db, "John.14.5", "Lord, we know not") == ("thomas", "drafted")
    assert _speaker_at(db, "John.1.49", "Rabbi, thou art the Son of God") == ("nathanael", "drafted")
    assert _speaker_at(db, "Acts.21.39", "I am a man which am a Jew of Tarsus") == ("paul", "drafted")
    assert _speaker_at(db, "John.2.3", "They have no wine")[0] is None  # Jesus's mother: not a name the data has


def test_crosstab_agape_phileo(b):
    x = b.speaker_lemma_crosstab(["G0025", "G5368"])
    rows = {r["speaker"]: r["counts"] for r in x["rows"]}
    assert rows["jesus"]["G0025"] > rows["jesus"]["G5368"] > 0
    assert "John.21.17" in next(r for r in x["rows"] if r["speaker"] == "jesus")["refs"]["G5368"]
    only_red = b.speaker_lemma_crosstab(["G0025"], basis="red-letter edition")
    assert {r["speaker"] for r in only_red["rows"]} <= {"jesus", "(narration)"}


def test_every_speech_has_an_edge_to_its_speaker(db):
    for sid, who in db.execute("SELECT id, speaker FROM speeches"):
        assert db.execute("SELECT count(*) FROM edges WHERE subject=? AND object=?", (who, sid)).fetchone()[0] == 1, sid


# ------------------------------------------------------------------- raw SQL
@pytest.mark.parametrize("q", ["DELETE FROM edges", "UPDATE verses SET text=''", "DROP TABLE edges",
                               "ATTACH DATABASE 'x.db' AS x", "PRAGMA writable_schema=1", "SELECT 1; DELETE FROM edges",
                               "INSERT INTO meta VALUES('a','b')"])
def test_raw_sql_refuses_writes(b, q):
    with pytest.raises(ValueError):
        b.sql(q)


def test_raw_sql_reads(b):
    r = b.sql("SELECT type, count(*) AS n FROM edges GROUP BY type ORDER BY n DESC", limit=3)
    assert r["columns"] == ["type", "n"] and r["rows"][0][0] == "visited" and r["truncated"]


def test_raw_sql_refuses_writes_even_on_a_writable_connection(tmp_path):
    import shutil
    p = tmp_path / "w.sqlite"
    shutil.copy(CORE, p)
    w = Bible(sqlite3.connect(p))
    with pytest.raises(ValueError):
        w.sql("DELETE FROM edges")
    assert sqlite3.connect(p).execute("SELECT count(*) FROM edges").fetchone()[0] > 0


# ----------------------------------------------------------------------- MCP
async def _mcp(calls):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    p = StdioServerParameters(command=sys.executable, args=[str(ROOT / "mcp_server/server.py")])
    async with stdio_client(p) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            names = {t.name for t in (await s.list_tools()).tools}
            out = []
            for name, args in calls:
                res = await s.call_tool(name, args)
                out.append(json.loads(res.content[0].text))
            return names, out


def test_mcp_new_tools():
    names, (rel, xt, sql, words) = asyncio.run(_mcp([
        ("related", {"entity_id": "paul", "relation": "wrote_to", "minus": "visited"}),
        ("speaker_lemma_crosstab", {"lemmas": ["G0025", "G5368"]}),
        ("run_sql", {"query": "DELETE FROM edges"}),
        ("words_in_verse", {"reference": "John 21:15"}),
    ]))
    assert {"list_edge_types", "get_edges", "related", "speeches", "who_speaks", "words_in_verse", "lemma_usage",
            "speaker_lemma_crosstab", "run_sql"} <= names
    assert "colossae" in {m["id"] for m in rel["members"]}
    assert any(r["speaker"] == "jesus" for r in xt["rows"])
    assert "refused" in sql
    love = [w for w in words["verses"][0]["words"] if w["text"] == "love"]
    assert love[0]["strong"] == "G5368" and love[0]["lemma"] == "φιλέω"


# ------------------------------------------------------------------- viewer
def test_graph_viewer_is_offline_and_complete(db):
    page = (ROOT / "dist/graph/index.html").read_text(encoding="utf-8")
    assert "<script src=" not in page and "vis.Network" in page  # library inlined, opens from disk
    data = json.loads(re.search(r"const D = (.*);\n", page).group(1))
    assert len(data["edges"]) == db.execute("SELECT count(*) FROM edges").fetchone()[0]
    assert set(data["types"]) == {r[0] for r in db.execute("SELECT type FROM edge_types")}
    ids = {n["id"] for n in data["nodes"]}
    assert all(e["from"] in ids and e["to"] in ids for e in data["edges"])
