# Attribution and licences

This project builds two data files from four sources, plus a map background. Each source is pinned
to an exact commit in `sources.lock.json`, and every file used is checked by SHA-256 before a build.

## Core file: `dist/acts-core.sqlite` (and the Obsidian vault, maps and MCP answers made from it)

Licence of the core file as a whole: **CC BY 4.0**, because it adapts two CC BY 4.0 sources.
Nothing share-alike is in it.

| Source | What we use | Licence | Pinned at |
|---|---|---|---|
| King James Version text, JSON by Arul John, https://github.com/aruljohn/Bible-kjv | The text of Acts, verse by verse | Text: public domain (Crown rights apply in the UK). JSON packaging: MIT | `a9aa4e55afbb3e095f57e4b14cd1f22c5ee8d7c9` |
| STEPBible TIPNR, Tyndale House Cambridge, https://github.com/STEPBible/STEPBible-Data | Who and where each name is, descriptions, Strong's numbers, references | CC BY 4.0 | `5de0a47f35f0fc13dfe1430d104e5db8a4285f9c` |
| OpenBible.info Bible Geocoding Data, https://github.com/openbibleinfo/Bible-Geocoding-Data | Coordinates and confidence for places | CC BY 4.0 | `7eb18a5ee62f27b9b93bd6689ea272d76dd23b8f` |
| Hand curation for this project (`curation/`) | Ids for hard names, KJV spellings, people groups, family links, Paul's itinerary, corrections | CC BY 4.0 | this repository |

Required credit lines:

- "Proper-name data from STEPBible.org, Tyndale House, Cambridge (TIPNR), CC BY 4.0. Changed: see the corrections table."
- "Geocoding data from OpenBible.info, CC BY 4.0."

TIPNR's licence asks that changes be noted. Every change we make to TIPNR's verse links is a row in
`curation/mention_corrections.csv` with a reason, and is copied into the `corrections` table of the data file.

The MIT licence of the KJV JSON packaging (copyright Arul John) requires its notice to travel with copies of
that packaging. We ship the verse text, not the JSON files; the notice is in `sources/kjv/LICENSE` after a fetch.

## Optional layer: `dist/acts-theographic.sqlite`

| Source | What we use | Licence | Pinned at |
|---|---|---|---|
| Theographic Bible Metadata, Robert Rouse, https://github.com/robertrouse/theographic-bible-metadata | A cross-reference to Theographic ids, and its birth and death years as labelled chronology views (Floyd Nolen Jones chronology) | CC BY-SA 4.0 | `b75c2689bbc396def2b22b4abf4e756ad2732742` |

This layer is a **separate file** on purpose. CC BY-SA 4.0 is share-alike: anything published that adapts it
must also be CC BY-SA 4.0. The core file does not depend on it and builds without it
(`python build/build.py --no-theographic`). The query layer loads it only if it is present. Whether to ship it,
and under which licence the combined work goes out, is still Guy's decision.

Credit line: "Chronology views from Theographic Bible Metadata by Robert Rouse, CC BY-SA 4.0."

## Maps only

| Source | What we use | Licence | Pinned at |
|---|---|---|---|
| Natural Earth 1:50m land, https://github.com/nvkelso/natural-earth-vector | Land outlines in `dist/maps/paul-journeys.svg` | public domain | `ca96624a56bd078437bca8184e78163e5039ad19` |

The interactive map `dist/maps/paul-journeys.html` loads Leaflet (BSD-2-Clause) from cdnjs and map tiles from
OpenStreetMap (data ODbL, "© OpenStreetMap contributors", shown on the map) when it is opened.

## This project's own code

The scripts in `build/`, `bibleobj/`, `mcp_server/` and `tests/` have no licence chosen yet. That is Guy's call.
