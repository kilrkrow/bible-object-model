# Done-gates

First pass run on 2026-11-24 (36 passed). Rerun on 2026-11-25 after the second round: `python -m pytest -q tests/`
gives **83 passed** (the 36 gate tests unchanged, plus 47 for the new layers). Each gate below names its tests and evidence.

| # | Gate | Result | Evidence |
|---|---|---|---|
| 1 | One script builds the data; rerun gives the identical file | PASS | `test_gate1_build_is_reproducible` builds twice into fresh folders and compares SHA-256 of both data files and the report with each other and with `dist/`. Core file now `5e7f5b2a…2844`, layer `b9cb3fbf…fc3d1a`. `build/make_all.py` runs fetch, build, maps and vault in one go. |
| 2 | Acts verse and word counts match the source exactly; every verse comes back by reference | PASS | Recounted straight from the source JSON: 28 chapters, 1,007 verses, 24,245 words, 128,829 characters, and each chapter's verse count. All 1,007 verses fetched one by one by "Acts c:v" and compared character for character. Acts 8:37 present. |
| 3 | Every name in Acts has an id; at least 95% match Theographic's list | PASS | Name scan: 1,297 capitalised name tokens in KJV Acts, 1,297 covered (100%). Theographic: 220 of 225 Acts people and places matched (97.8%). The 5 misses: Theographic's "Heber" at 23:35 (a mislink for Herod's hall), the Holy Spirit (left out by design), Pharaoh's daughter (unnamed), and Mount Sinai and Mount of Olives (same places, labelled without "Mount"). |
| 4 | Two Jameses, two Herods, two Philips stay separate | PASS | Four Jameses, four Herods (the Great, Antipas, Agrippa I, Agrippa II) and two Philips, each its own id. 15 occurrence checks, e.g. the three Jameses in Acts 1:13 each resolve to a different person, and "Simon" in 10:32 is Peter first and the tanner second. No word in Acts belongs to two ids. |
| 5 | Every link cites a verse; 20 random links check out | PASS | Every mention sits at its recorded position in its verse; every family link and travel stop quotes its verse exactly. Seeded sample of 8 mentions, 6 stops and 6 family links: 20 of 20 correct by hand (`reports/link-sample.md`). |
| 6 | Paul's journey in order with coordinates on a map; contemporaries; a family path; Antioch's history with citations | PASS | 73 stops, Jerusalem 9:2 to Rome 28:16, every one with coordinates and a quote, drawn in `dist/maps/`. Paul named alongside 35 New Testament people (Barnabas 17 verses, Silas 10). Abraham to Joseph: 7:8, 7:8, 7:14. Antioch in Syria: 13 verses from 6:5 to 18:22, with Pisidian Antioch kept apart. |
| 7 | No bare dates, only labelled views | PASS | A checker walks every result of every query for all 276 entities and fails on any year outside a claim. A guard on every query refuses to return one. A claim view without a label and source cannot be made. Theographic's years appear only as views labelled "Theographic (Floyd Nolen Jones chronology)". |
| 8 | MCP server Claude Desktop can use to answer five sample questions with correct citations | PASS (here); Desktop step is Guy's | 12-tool stdio server in the first pass, 21 tools now. Tested two ways: an MCP client test of six tool calls, and a real Claude client (Claude Code CLI over stdio, the same setup Desktop uses) answering five questions, all citations correct (`reports/mcp-five-questions.md`). Not yet run inside Claude Desktop on Guy's PC. |
| 9 | Attribution file naming every source and licence | PASS | `ATTRIBUTION.md`: KJV (public domain, JSON MIT), STEPBible TIPNR (CC BY 4.0), OpenBible (CC BY 4.0), Theographic (CC BY-SA 4.0, separate file), Natural Earth (public domain, maps only), each with repo and commit. Test checks it against `sources.lock.json` and the data file. |
| 10 | Obsidian vault of Acts people and places, linked, navigable in graph view | PASS (built); not yet in glow-up | `dist/vault/`: 306 notes in the first pass (349 now, with speeches and relationship sections), 4,126 links, every link resolves; colour groups for people, places, groups and chapters in graph view. Neither glow-up nor Dropbox was reachable from here, so copying it in is still to do. |

## Fixes the gates forced

- TIPNR sometimes lists two people of the same name at one verse, so the first build gave Acts 1:13's three "James" words to all three Jameses, and "Caesar" (Nero, unnamed) to Claudius. Now each occurrence is assigned by hand with a reason in `curation/occurrence_choices.csv`, and the build stops if any word is claimed twice.
- OpenBible keys some places by a different TIPNR reference, which left Jerusalem without coordinates. Places now fall back to a name match, marked "openbible (matched by name)".

## Second round: typed relationships, Greek, speakers (2026-11-25)

The ten gates still pass after the core moved to a typed graph. Two gate checks were narrowed to Acts, because the
data file now holds the whole KJV text: the name scan (gate 3) and the vault's chapter notes read Acts only.

| Layer | Result | Evidence (`tests/test_layers.py` unless named) |
|---|---|---|
| Whole KJV text | PASS | 66 books, 31,102 verses. Any reference parses (`1 Cor 13:4-7`, `John.3.16`). |
| Typed relationships | PASS | 157 edges across 21 types from `curation/edge_types.csv`. Every edge's quote sits exactly at its recorded character span. Every type is reachable by name with no code naming it. `relations` and `itinerary` are views with the first pass's columns. `paul.wrote_to - paul.visited` leaves Colossae as the only place. |
| Greek lemma layer | PASS | 34,313 Greek words of Acts and John (Textus Receptus readings; Acts 8:37 and John 5:4 present), 2,416 lemmas. 17,953 of 19,362 KJV content words aligned (93%). Gold set of 19 words passes, including every "love" in John 21:15-17. Random sample: 39 of 40 right (`reports/alignment-sample.md`). |
| Speakers | PASS | 468 red-letter spans (Jesus), 285 curated speech spans (33 speeches), 293 drafted spans. No character has two speakers; Jesus quoted inside Peter's speech stays Jesus's. Named drafted speakers 23 of 24 right; boundaries 17 of 20 (`reports/speaker-sample.md`). |
| Speaker × lemma | PASS | In John and Acts, Jesus's words translate agapaō more than phileō, and John 21:17 is among his phileō verses. |
| Library and raw SQL | PASS | Entity sets support minus, union and intersection and keep their evidence. Raw SQL refuses DELETE, UPDATE, DROP, INSERT, ATTACH, PRAGMA and stacked statements, also on a writable copy. |
| MCP | PASS | Nine new tools over stdio; `related`, `speaker_lemma_crosstab`, `run_sql` (refusal) and `words_in_verse` called from a real MCP client. |
| Graph viewer | PASS (checked as data, not in a browser) | `dist/graph/index.html` has no external script, holds every edge and every type, and every edge's ends exist. The page's scripts pass a syntax check. It was not opened in a browser here. |
