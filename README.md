# Bible object model

The King James Bible as data you can query. The core is a **graph of typed relationships**: who wrote to whom,
who visited where, who preached which sermon, who is whose parent. Every relationship cites the verse it rests
on and the exact words in that verse. Under the English words of Acts and John sits a **Greek lemma layer**, so
"love" in John 21 resolves to agapaō or phileō, and a **speaker layer** that says who is talking. One data
file feeds a Python library, an MCP server, a graph viewer, a map of Paul's travels and an optional Obsidian vault.

Scope this round: the whole KJV as text; people, places and relationships in depth for Acts (plus the
recipients of Paul's letters); Greek and speakers for Acts and John.

## What is here

| Path | What it is |
|---|---|
| `dist/acts-core.sqlite` | The data file (CC BY 4.0). See "What is in the data file" below. |
| `dist/acts-theographic.sqlite` | Optional share-alike layer (CC BY-SA 4.0), separate on purpose; see ATTRIBUTION.md. |
| `dist/graph/index.html` | The relationship graph. One file, works offline. Tick relationship types on and off; click a node or a line to see the verse. |
| `dist/maps/` | Paul's route: `paul-journeys.svg` (offline), `paul-journeys.html` (zoomable, needs internet), GeoJSON. |
| `dist/vault/` | Obsidian vault (optional view): people, places, groups, speeches, chapters of Acts. |
| `bibleobj/` | Python library (`from bibleobj import Bible`). |
| `mcp_server/server.py` | MCP server with 21 tools, including a read-only raw SQL tool. |
| `build/` | `make_all.py` runs everything: fetch pinned sources, build, maps, vault, graph viewer. |
| `curation/` | Hand decisions, each with a reason. `edge_types.csv` is the open list of relationship types. |
| `tests/` | `test_gates.py` (the ten first-pass gates) and `test_layers.py` (the new layers). `python -m pytest -q tests/` |
| `reports/` | Gate results, hand-checked samples (links, word alignment, speakers), the five MCP questions. |
| `docs/use-cases.md` | Use cases recorded for later, including "principles as code". |

## Run it on Windows (no WSL)

Everything is plain Python and SQLite, so it runs natively. The step-by-step guide is
[docs/build-on-windows.md](docs/build-on-windows.md); in short, after cloning, run
`powershell -ExecutionPolicy Bypass -File .\build.ps1`, which sets up its own Python environment, builds and tests.
Or by hand:

1. Install Python 3.10 or newer from python.org (tick "Add python.exe to PATH"), and Git for Windows.
2. In PowerShell, in this folder:

```
py -3 -m pip install -r requirements.txt
py -3 build\make_all.py
py -3 -m pytest -q tests\
```

The build is deterministic: same sources, same bytes. `sources.lock.json` pins every source to a commit and a
file hash, and the build stops if a file differs. Open `dist\graph\index.html` in any browser.

On macOS or Linux use `python3` in place of `py -3`.

## Use it from Python

```python
from bibleobj import Bible
b = Bible.open()

b.paul.wrote_to - b.paul.visited        # who Paul wrote to but is not shown visiting: Colossae, plus people
b.jesus.sermons                         # Jesus's sermons in John (edge type `preached`)
b.colossae.written_to_by                # read any relationship from the other end
b.herod_agrippa_i.killed                # {james-son-of-zebedee}, with Acts 12:2 as evidence
(b.paul.wrote_to - b.paul.visited).to_list()   # each member with the verse and quote behind it

b.words("John 21:15")                   # each KJV word with the Greek word and lemma it translates
b.lemma_usage("G5368")                  # where phileō occurs and how the KJV renders it
b.speaker_lemma_crosstab(["agapaō", "phileō"])  # who says which, in John and Acts
b.who_speaks("Acts 2:14-16")

b.edges(type="wrote_to")                # raw edges: subject, type, object, ref, start, end, quote
b.sql("SELECT type, count(*) FROM edges GROUP BY type")   # one read-only SELECT
```

Relationship names come from data, not code: every row of `curation/edge_types.csv` gives a type, its
inverse, and the names it is read by (`sermons`, `children`, `visitors`...). Add a row, rebuild, and the
new name works in Python, in the MCP server and in the graph viewer.

The first-pass calls still work: `passage`, `find`, `entity`, `relation_path`, `journey`, `contemporaries`,
`place_history`.

## Use it from Claude Desktop or Claude Code

1. `py -3 -m pip install "mcp>=1.2"`
2. Put this folder somewhere on the PC, for example `C:\bible-object-model`.
3. In Claude Desktop, Settings, Developer, Edit Config, add:

```json
{
  "mcpServers": {
    "bible-object-model": {
      "command": "py",
      "args": ["-3", "C:\\bible-object-model\\mcp_server\\server.py"]
    }
  }
}
```

4. Restart Claude Desktop and ask, for example, "Which places did Paul write to but never visit, with verses?"
   or "In John, who uses agapaō and who uses phileō?"

## What is in the data file

| Table | What it holds |
|---|---|
| `verses`, `books`, `chapters` | All 66 books of the KJV (31,102 verses). |
| `entities`, `aliases`, `mentions` | People, places, groups and speeches; every name occurrence in Acts with its exact position. |
| `edges`, `edge_types` | The typed relationship graph. Each edge: subject, type, object, ref, character span, quote, basis. |
| `relations`, `itinerary` | Views over `edges` with the first pass's column names (family links; Paul's route). |
| `speeches`, `utterances` | Who speaks which characters of which verse in Acts and John, each span with a basis. |
| `tokens`, `greek_words`, `lexicon`, `alignments` | KJV words, the Greek (Textus Receptus readings), lemmas, and which Greek word each KJV word translates. |
| `claims`, `claim_views`, `place_sites`, `corrections` | As in the first pass. |

## What is checked and what is drafted

Every row says which it is.

- **Checked:** the text; relationships (each quote is verified against its verse at build time); speech boundaries in `curation/speeches.csv`; Jesus's words (from a red-letter edition).
- **Drafted by machine:** the KJV-to-Greek alignment (39 of 40 right in a hand-checked sample, `reports/alignment-sample.md`) and speakers with basis `drafted` (23 of 24 named speakers right; most drafted spans are left without a speaker rather than guessed, `reports/speaker-sample.md`).

## Rules the data keeps

- One occurrence of a name is one individual. Where a verse names two people called James, each occurrence is assigned by hand (`curation/occurrence_choices.csv`) and the build refuses to run if any word is claimed twice.
- Every relationship carries an exact quote from its verse and its character span; the build checks both.
- One speaker per character: when Peter quotes Jesus (Acts 11:16), the quoted words stay Jesus's and are marked "quoted by peter".
- Dates: Acts states none, so birth and death are claims marked "not stated". A chronology's dates can appear only as a labelled view from the optional layer. A test scans every query result for bare years.
- "Contemporaries" means named in the same verse and placed in New Testament times by TIPNR. It does not claim the two met.
