"""MCP server for the Acts object model. Runs over stdio for Claude Desktop.

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

INSTRUCTIONS = """Acts of the Apostles (KJV) as an object model: people, places, family links and Paul's route.
Always cite the verse refs the tools return. Names are ambiguous: use find_entity first and pick an id
(there are four Jameses, four Herods, two Philips). Dates are never stated by Acts; if a tool returns a claim
with views, name the source label of each view and say it is that chronology's view, not the text's."""

bible = Bible.open()
mcp = _Server("bible-acts", instructions=INSTRUCTIONS)


def _j(x):
    return json.dumps(x, ensure_ascii=False, indent=1)


@mcp.tool()
def get_passage(reference: str) -> str:
    """KJV text of a verse, range or chapter of Acts, e.g. 'Acts 13:1-3', 'Acts 2'."""
    return _j(bible.passage(reference))


@mcp.tool()
def book_length(chapter: int | None = None) -> str:
    """How long Acts (or one chapter) is, in chapters, verses, words, characters and reading minutes."""
    return _j(bible.length("Acts", chapter))


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


if __name__ == "__main__":
    mcp.run(transport="stdio")
