# Acts as a Bible object model (first pass)

The Acts of the Apostles in the King James Version, as data you can query: every person, place and group
named in it has an id, every link between them cites the verse it comes from, and no date is ever given
as fact. A query library, an MCP server for Claude Desktop, a map of Paul's travels and an Obsidian vault
are all built from the same data file.

## What is here

| Path | What it is |
|---|---|
| `dist/acts-core.sqlite` | The data file (CC BY 4.0). Verses, people, places, groups, mentions, family links, Paul's route, map sites, corrections. |
| `dist/acts-theographic.sqlite` | Optional share-alike layer (CC BY-SA 4.0): a crosswalk to Theographic and its birth and death years as labelled views. Separate on purpose; see ATTRIBUTION.md. |
| `dist/maps/` | Paul's route: `paul-journeys.svg` (works offline), `paul-journeys.html` (zoomable, needs internet), `paul-journeys.geojson`. |
| `dist/vault/` | Obsidian vault: 120 people, 105 places, 34 groups, other names, 28 chapter notes. Open the folder as a vault; start at "Acts, start here". |
| `bibleobj/` | Python query layer (`from bibleobj import Bible`). |
| `mcp_server/server.py` | MCP server with 12 tools. |
| `build/` | `make_all.py` runs everything: fetch pinned sources, build, maps, vault. |
| `curation/` | Hand decisions, each with a reason: ids for hard names, KJV spellings, people groups, family links, Paul's itinerary, verse corrections. |
| `tests/test_gates.py` | The ten done-gates as tests. `python -m pytest -q tests/` |
| `reports/` | Gate results, the hand-checked link sample, the five MCP questions. |

## Rebuild

Needs Python 3.10+ and git.

```
python build/make_all.py
python -m pytest -q tests/
```

The build is deterministic: same sources, same bytes. `sources.lock.json` pins every source to a commit
and a file hash, and the build stops if a file differs.

## Use it from Python

```python
from bibleobj import Bible
acts = Bible.open()
acts.passage("Acts 13:1-3")
acts.find("James")                                # four different Jameses, pick one by id
acts.relation_path("abraham", "joseph-son-of-jacob")
acts.journey("paul")                              # 73 stops in narrative order, each with coordinates and a quote
acts.contemporaries("paul")
acts.place_history("antioch-of-syria")
```

## Use it from Claude Desktop

1. `pip install "mcp>=1.2"`
2. Copy this folder somewhere on the PC, for example `C:\bible-acts`.
3. In Claude Desktop, Settings, Developer, Edit Config, add:

```json
{
  "mcpServers": {
    "bible-acts": {
      "command": "python",
      "args": ["C:\\bible-acts\\mcp_server\\server.py"]
    }
  }
}
```

4. Restart Claude Desktop and ask, for example, "Which James did Herod kill?"

## Rules the data keeps

- One occurrence of a name is one individual. Where a verse names two people called James, each occurrence is assigned by hand (`curation/occurrence_choices.csv`) and the build refuses to run if any word is claimed twice.
- Every family link and travel stop carries an exact quote from its verse; the build checks the quote is there.
- Dates: Acts states none, so people's birth and death are claims marked "not stated". A chronology's dates can appear only as a labelled view (for example "Theographic (Floyd Nolen Jones chronology)") and only from the optional layer. A test scans every query result for bare years.
- "Contemporaries" means named in the same verse and placed in New Testament times by TIPNR. It does not claim the two met, and lifespans are never compared.
