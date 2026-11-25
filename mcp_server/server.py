"""MCP server for the Bible object model (Acts in depth, John for speakers and Greek, the whole KJV as text).
Runs over stdio for Claude Desktop or Claude Code.

    python mcp_server/server.py            # stdio
Every tool returns JSON. Text facts carry the verse they come from; dates only appear inside labelled claims.
"""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from bibleobj import Bible  # noqa: E402

try:  # MCP Python SDK 2.x
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:  # 1.x
    from mcp.server.fastmcp import FastMCP as _Server

INSTRUCTIONS = """The Bible (KJV) as an object model: a graph of typed relationships (wrote_to, visited, preached,
parent_of and more; list_edge_types shows them all), Greek lemmas behind the English words of Acts and John, and
who is speaking in Acts and John. Always cite the verse refs the tools return. Say when a result rests on a
machine draft (word alignment, or a speaker with basis 'drafted'). Names are ambiguous: use find_entity first and pick an id
(there are four Jameses, four Herods, two Philips). Dates are never stated by Acts; if a tool returns a claim
with views, name the source label of each view and say it is that chronology's view, not the text's."""

bible = Bible.open()
mcp = _Server("bible-object-model", instructions=INSTRUCTIONS)


def _j(x):
    return json.dumps(x, ensure_ascii=False, indent=1)


@mcp.tool()
def get_passage(reference: str) -> str:
    """KJV text of a verse, range or chapter of any book, e.g. 'Acts 13:1-3', 'John 3', '1 Cor 13:4-7'."""
    return _j(bible.passage(reference))


@mcp.tool()
def book_length(chapter: int | None = None, book: str = "Acts") -> str:
    """How long a book (or one chapter) is, in chapters, verses, words, characters and reading minutes.
    book is an OSIS code such as Acts, John, Rom, 1Cor."""
    return _j(bible.length(book, chapter))


@mcp.tool()
def find_entity(name: str, kind: str | None = None) -> str:
    """Every person, place or group in Acts matching a name. Several matches are different individuals; pick one by id.
    kind may be person, place, group, deity, title, festival, other."""
    return _j(bible.find(name, kind))


@mcp.tool()
def get_entity(entity_id: str) -> str:
    """Full record for one entity id: description, other names, mention count, map sites for places,
    family links (each with its verse) and born/died claims for people."""
    return _j(bible.entity(entity_id))


@mcp.tool()
def get_mentions(entity_id: str, limit: int | None = None) -> str:
    """Every verse in Acts that names this entity, with the exact words used and the verse text."""
    return _j(bible.mentions(entity_id, limit))


@mcp.tool()
def verse_entities(reference: str) -> str:
    """Which people, places and groups are named in a verse or range, with the words used."""
    return _j(bible.verse_entities(reference))


@mcp.tool()
def family_path(from_id: str, to_id: str) -> str:
    """Shortest family path between two people using only relations Acts states, each step with its verse and quote."""
    return _j(bible.relation_path(from_id, to_id))


@mcp.tool()
def contemporaries(person_id: str) -> str:
    """People this person is named alongside in the same verse, split into New Testament contemporaries and
    earlier figures who are only mentioned. Each with the shared verses."""
    return _j(bible.contemporaries(person_id))


@mcp.tool()
def journey(person_id: str = "paul") -> str:
    """A person's travels in Acts in narrative order, with coordinates and the verse and quote for each stop."""
    return _j(bible.journey(person_id))


@mcp.tool()
def journey_geojson(person_id: str = "paul") -> str:
    """The same journey as GeoJSON, ready to draw on a map."""
    return _j(bible.journey_geojson(person_id))


@mcp.tool()
def place_history(place_id: str) -> str:
    """Everything Acts says happens at a place, in narrative order, with the people named in each verse."""
    return _j(bible.place_history(place_id))


@mcp.tool()
def about_this_data() -> str:
    """Sources, licences, versions and the content hash of the data file."""
    return _j(bible.info())


# ------------------------------------------------------------ typed relationships
@mcp.tool()
def list_edge_types() -> str:
    """Every relationship type in the graph with its inverse, the names it is read by, and how many edges it has.
    The list is open: new types are added as data, not code."""
    return _j(bible.edge_types())


@mcp.tool()
def get_edges(subject: str | None = None, type: str | None = None, object: str | None = None,
              ref: str | None = None, limit: int = 200) -> str:
    """Relationships filtered by subject id, type (or a name like 'sermons' or 'children'), object id or verse ref
    ('Acts.12.2'). Each edge gives the verse, the quote and its character span in the verse."""
    return _j(bible.edges(subject=subject, type=type, object=object, ref=ref, limit=limit))


@mcp.tool()
def related(entity_id: str, relation: str, minus: str | None = None) -> str:
    """Entities linked to one entity by a relationship name, as a set with the verses behind each member.
    relation is a type or accessor ('wrote_to', 'visited', 'sermons', 'children', 'written_to_by').
    minus subtracts a second relation of the same entity, e.g. relation='wrote_to', minus='visited'."""
    e = bible.get(entity_id)
    s = getattr(e, relation)
    if minus:
        s = s - getattr(e, minus)
    return _j({"entity": entity_id, "relation": relation, "minus": minus, "members": s.to_list()})


@mcp.tool()
def speeches(speaker: str | None = None) -> str:
    """Curated speeches, sermons, defences and prayers in Acts and John (boundaries checked by hand)."""
    return _j(bible.speeches(speaker))


@mcp.tool()
def who_speaks(reference: str) -> str:
    """Who is speaking which words of a verse or range in Acts or John. Each span has a basis: 'red-letter edition'
    (Jesus), 'curated speech' (checked), or 'drafted' (pattern-based, unchecked; speaker may be blank)."""
    return _j(bible.who_speaks(reference))


# --------------------------------------------------------------------- Greek
@mcp.tool()
def words_in_verse(reference: str) -> str:
    """Each KJV word of a verse in Acts or John with the Greek word, Strong's number and lemma it translates.
    The alignment is machine-drafted, with a score."""
    return _j(bible.words(reference))


@mcp.tool()
def lemma_usage(lemma: str, book: str | None = None) -> str:
    """Where a Greek lemma occurs in the NT and how the KJV renders it in Acts and John.
    lemma is a Strong's number (G0025), a Greek lemma (ἀγαπάω) or a transliteration (agapaō)."""
    return _j(bible.lemma_usage(lemma, book))


@mcp.tool()
def speaker_lemma_crosstab(lemmas: list[str], books: list[str] | None = None, basis: str | None = None) -> str:
    """Who says which Greek lemma: rows are speakers, columns lemmas, cells counts with verse refs.
    books defaults to John and Acts. basis limits to 'red-letter edition', 'curated speech' or 'drafted'."""
    return _j(bible.speaker_lemma_crosstab(lemmas, tuple(books or ("John", "Acts")), basis))


# ------------------------------------------------------------------------ raw
@mcp.tool()
def run_sql(query: str, limit: int = 200) -> str:
    """One read-only SQL SELECT against the core data file, for anything the named tools do not cover.
    Tables: verses, books, entities, aliases, mentions, edges, edge_types, speeches, utterances, tokens,
    greek_words, lexicon, alignments, place_sites, claims. Writes, ATTACH and PRAGMA are refused."""
    try:
        return _j(bible.sql(query, limit=min(limit, 1000)))
    except ValueError as e:
        return _j({"refused": str(e), "hint": "Only a single SELECT is allowed."})


if __name__ == "__main__":
    mcp.run(transport="stdio")
