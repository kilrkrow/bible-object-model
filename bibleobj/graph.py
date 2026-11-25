"""The typed-relationship graph, the Greek lemma layer and speakers, as Python objects.

    from bibleobj import Bible
    b = Bible.open()
    paul = b.paul                       # or b.get("paul") / b["paul"]
    paul.wrote_to - paul.visited        # letters to places and people Paul is not shown visiting
    b.jesus.sermons                     # speeches Jesus gave (edge type `preached`, accessor `sermons`)
    b.colossae.written_to_by            # the inverse accessor works from the other end
    b.words("John.21.15")               # each KJV word with the Greek word and lemma it translates
    b.speaker_lemma_crosstab(["G0025", "G5368"])   # who says agapaō vs phileō in Acts and John

Relationship types are not fixed in code: every row of the `edge_types` table gives a type, its inverse and
the names it is read by (`accessor`, `inverse_accessor`). Add a row to curation/edge_types.csv and rebuild,
and the new name works here, in the MCP server and in the graph viewer.

Every edge carries the verse it rests on and the exact character span of its quote in that verse.
"""
import json, re, sqlite3, unicodedata
from collections import Counter, defaultdict

from .books import BOOK_INDEX


def ref_order(ref):
    b, c, v = ref.split(".")
    return BOOK_INDEX.get(b, 99), int(c), int(v)


class Entity:
    """One person, place, group or speech. Unknown attribute names resolve to relationship types."""

    def __init__(self, bible, eid):
        row = bible._entity_row(eid)
        self._b, self.id, self.label, self.kind = bible, eid, row["label"], row["kind"]

    def __repr__(self):
        return f"<{self.kind} {self.id}: {self.label}>"

    def __eq__(self, other):
        return isinstance(other, Entity) and other.id == self.id

    def __hash__(self):
        return hash(self.id)

    def __dir__(self):
        return sorted(set(super().__dir__()) | set(self._b._accessors()))

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        acc = self._b._accessors()
        if name not in acc:
            raise AttributeError(f"{self.id} has no relationship called {name!r}; known: {', '.join(sorted(acc))}")
        types, direction = acc[name]
        return self._b.related(self.id, types, direction)

    def edges(self, type=None):
        out = self._b.edges(subject=self.id, type=type) + self._b.edges(object=self.id, type=type)
        return sorted(out, key=lambda e: (ref_order(e["ref"]), e["type"]))

    def info(self):
        return self._b.entity(self.id)


class EntitySet:
    """A set of entities that keeps, for each member, the edges that put it there (its evidence)."""

    def __init__(self, bible, evidence):
        self._b = bible
        self.evidence = {k: list(v) for k, v in evidence.items()}

    @property
    def ids(self):
        return sorted(self.evidence)

    def __iter__(self):
        return (Entity(self._b, i) for i in self.ids)

    def __len__(self):
        return len(self.evidence)

    def __contains__(self, x):
        return (x.id if isinstance(x, Entity) else x) in self.evidence

    def __bool__(self):
        return bool(self.evidence)

    def __sub__(self, other):
        return EntitySet(self._b, {k: v for k, v in self.evidence.items() if k not in other.evidence})

    def __and__(self, other):
        return EntitySet(self._b, {k: v + other.evidence[k] for k, v in self.evidence.items() if k in other.evidence})

    def __or__(self, other):
        ev = defaultdict(list)
        for s in (self, other):
            for k, v in s.evidence.items():
                ev[k] += v
        return EntitySet(self._b, ev)

    def __repr__(self):
        return "{" + ", ".join(self.ids) + "}"

    def to_list(self):
        """JSON-ready: each member with the verses that support it."""
        out = []
        for i in self.ids:
            e = self._b._entity_row(i)
            out.append({"id": i, "label": e["label"], "kind": e["kind"],
                        "evidence": [{"type": x["type"], "ref": x["ref"], "quote": x["quote"]} for x in self.evidence[i]]})
        return out


class GraphMixin:
    """Methods mixed into Bible. They read the `edges`, `tokens`, `greek_words`, `alignments` and `utterances` tables."""

    # ---------------------------------------------------------------- edges
    def _accessors(self):
        if getattr(self, "_acc_cache", None) is None:
            acc = defaultdict(lambda: [set(), None])
            for r in self.db.execute("SELECT * FROM edge_types"):
                for name, d in ((r["type"], "out"), (r["accessor"], "out"), (r["inverse"], "in"),
                                (r["inverse_accessor"], "in")):
                    if not name:
                        continue
                    if r["inverse"] == r["type"] and d == "in":
                        d = "both"  # symmetric types: spouse_of, sibling_of, kin_of
                    if r["inverse"] == r["type"]:
                        d = "both"
                    acc[name][0].add(r["type"])
                    acc[name][1] = d
            self._acc_cache = {k: (tuple(sorted(v[0])), v[1]) for k, v in acc.items()}
        return self._acc_cache

    def edge_types(self):
        rows = self._q("SELECT * FROM edge_types ORDER BY type")
        counts = dict(self.db.execute("SELECT type, count(*) FROM edges GROUP BY type").fetchall())
        for r in rows:
            r["count"] = counts.get(r["type"], 0)
        return rows

    def edges(self, subject=None, type=None, object=None, ref=None, limit=None):
        where, args = [], []
        for col, val in (("subject", subject), ("object", object), ("ref", ref)):
            if val:
                where.append(f"{col}=?")
                args.append(val)
        if type:
            types = [type] if isinstance(type, str) else list(type)
            acc = self._accessors()
            types = sorted({t for x in types for t in (acc[x][0] if x in acc else (x,))})
            where.append("type IN (" + ",".join("?" * len(types)) + ")")
            args += types
        sql = 'SELECT id, subject, type, object, ref, start, "end", quote, seq, attrs, basis, source, note FROM edges'
        rows = self._q(sql + (" WHERE " + " AND ".join(where) if where else ""), *args)
        for r in rows:
            r["attrs"] = json.loads(r["attrs"]) if r["attrs"] else {}
        rows.sort(key=lambda r: (r["type"], r["subject"], r["seq"] or 0, ref_order(r["ref"]), r["object"]))
        return rows[:limit] if limit else rows

    def related(self, eid, types, direction="out"):
        self._entity_row(eid)
        ev = defaultdict(list)
        for t in types:
            if direction in ("out", "both"):
                for e in self.edges(subject=eid, type=t):
                    ev[e["object"]].append(e)
            if direction in ("in", "both"):
                for e in self.edges(object=eid, type=t):
                    ev[e["subject"]].append(e)
        ev.pop(eid, None)
        return EntitySet(self, ev)

    def get(self, eid):
        return Entity(self, eid)

    def __getitem__(self, eid):
        return Entity(self, eid)

    def __getattr__(self, name):
        # b.paul, b.herod_agrippa_ii -> Entity; only for names that are entity ids
        if name.startswith("_") or name in ("db", "layer"):
            raise AttributeError(name)
        eid = name.replace("_", "-")
        if self.db.execute("SELECT 1 FROM entities WHERE id=?", (eid,)).fetchone():
            return Entity(self, eid)
        raise AttributeError(f"Bible has no attribute or entity id {name!r}")

    def speeches(self, speaker=None):
        rows = self._q("SELECT * FROM speeches" + (" WHERE speaker=?" if speaker else "") + " ORDER BY id",
                       *([speaker] if speaker else []))
        rows.sort(key=lambda r: ref_order(r["start_ref"]))
        return rows

    # ------------------------------------------------------------- words
    def words(self, reference):
        """Every KJV word of a verse in Acts or John, with the Greek word it was aligned to (a machine draft)."""
        from .api import parse_ref
        book, c, v1, v2 = parse_ref(reference)
        out = []
        for v in range(v1 or 1, (v2 or v1 or 1) + 1):
            ref = f"{book}.{c}.{v}"
            toks = self._q("""SELECT t.idx, t.start, t."end", t.text, a.score, a.method, g.idx AS greek_idx, g.word AS greek,
                                     g.translit, g.strong, g.morph, l.lemma, l.translit AS lemma_translit, l.gloss
                              FROM tokens t LEFT JOIN alignments a ON a.ref=t.ref AND a.token_idx=t.idx
                              LEFT JOIN greek_words g ON g.ref=a.ref AND g.idx=a.greek_idx
                              LEFT JOIN lexicon l ON l.strong=g.strong
                              WHERE t.ref=? ORDER BY t.idx""", ref)
            if not toks:
                from .api import NotFound
                raise NotFound(f"{ref}: word-level data covers Acts and John only in this round")
            greek = self._q("SELECT idx, word, translit, strong, morph, english FROM greek_words WHERE ref=? ORDER BY idx", ref)
            out.append({"ref": ref, "text": self._verse(ref), "words": toks, "greek": greek,
                        "note": "Alignment is machine-drafted (IBM Model 1 with STEPBible glosses); score is its confidence."})
        return {"reference": reference, "verses": out}

    def _strongs(self, query):
        q = unicodedata.normalize("NFC", query.strip())
        if re.fullmatch(r"[GgHh]\d{1,4}", q):
            return [q[0].upper() + q[1:].zfill(4)]
        rows = self.db.execute("SELECT strong FROM lexicon WHERE lemma=? OR lower(translit)=lower(?) OR lower(gloss)=lower(?)",
                               (q, q, q)).fetchall()
        return sorted({r[0] for r in rows})

    def lemma_usage(self, query, book=None):
        """Where a Greek lemma (Strong's number, lemma or transliteration) occurs, and how the KJV renders it."""
        strongs = self._strongs(query)
        out = []
        for s in strongs:
            lex = self._q("SELECT * FROM lexicon WHERE strong=?", s)
            occ = self._q("SELECT ref, idx, word FROM greek_words WHERE strong=?", s)
            if book:
                occ = [o for o in occ if o["ref"].split(".")[0] == book]
            occ.sort(key=lambda o: (ref_order(o["ref"]), o["idx"]))
            kjv = Counter()
            for t in self._q("""SELECT lower(t.text) AS w FROM alignments a JOIN greek_words g ON g.ref=a.ref AND g.idx=a.greek_idx
                                JOIN tokens t ON t.ref=a.ref AND t.idx=a.token_idx WHERE g.strong=?""", s):
                kjv[t["w"]] += 1
            out.append({"strong": s, "lexicon": lex[0] if lex else None, "occurrences": len(occ),
                        "verses": sorted({o["ref"] for o in occ}, key=ref_order),
                        "kjv_renderings": dict(kjv.most_common())})
        return {"query": query, "lemmas": out,
                "note": "" if strongs else "No lemma matched; try a Strong's number like G0025 or a lemma like ἀγαπάω."}

    # ----------------------------------------------------------- speakers
    def who_speaks(self, reference):
        from .api import parse_ref
        book, c, v1, v2 = parse_ref(reference)
        out = []
        for v in range(v1 or 1, (v2 or v1 or 1) + 1):
            ref = f"{book}.{c}.{v}"
            text = self._verse(ref)
            us = self._q('SELECT start, "end", speaker, basis, speech_id, note FROM utterances WHERE ref=? ORDER BY start', ref)
            for u in us:
                u["words"] = text[u["start"]:u["end"]]
            out.append({"ref": ref, "text": text, "utterances": us})
        return {"reference": reference, "verses": out}

    def speaker_lemma_crosstab(self, lemmas, books=("John", "Acts"), basis=None):
        """Rows: speakers. Columns: lemmas. Cells: how many times that speaker's words translate that lemma.

        Counts Greek words through the alignment, inside utterance spans. `basis` can limit the spans to
        'red-letter edition', 'curated speech' or 'drafted'. Words outside any utterance count as narration.
        """
        strongs = []
        for q in lemmas:
            strongs += self._strongs(q)
        strongs = sorted(set(strongs))
        if not strongs:
            return {"lemmas": [], "rows": [], "note": "No lemma matched."}
        spans = defaultdict(list)
        for u in self._q('SELECT ref, start, "end", speaker, basis FROM utterances'):
            if basis and u["basis"] not in (basis if isinstance(basis, (list, tuple)) else [basis]):
                continue
            spans[u["ref"]].append(u)
        cells = defaultdict(Counter)
        refs = defaultdict(list)
        q = """SELECT t.ref, t.start, g.strong FROM alignments a JOIN greek_words g ON g.ref=a.ref AND g.idx=a.greek_idx
               JOIN tokens t ON t.ref=a.ref AND t.idx=a.token_idx
               WHERE g.strong IN (""" + ",".join("?" * len(strongs)) + ")"
        for r in self._q(q, *strongs):
            if r["ref"].split(".")[0] not in books:
                continue
            who = "(narration)"
            for u in spans.get(r["ref"], []):
                if u["start"] <= r["start"] < u["end"]:
                    who = u["speaker"] or "(speaker not resolved)"
                    break
            cells[who][r["strong"]] += 1
            refs[(who, r["strong"])].append(r["ref"])
        lex = {s: self._q("SELECT lemma, translit, gloss FROM lexicon WHERE strong=?", s) for s in strongs}
        rows = []
        for who in sorted(cells, key=lambda w: (-sum(cells[w].values()), w)):
            rows.append({"speaker": who, "counts": {s: cells[who][s] for s in strongs}, "total": sum(cells[who].values()),
                         "refs": {s: sorted(set(refs[(who, s)]), key=ref_order) for s in strongs if refs[(who, s)]}})
        return {"lemmas": [{"strong": s, **(lex[s][0] if lex[s] else {})} for s in strongs], "books": list(books),
                "basis": basis or "all", "rows": rows,
                "note": "Counts go through a machine-drafted word alignment; drafted speakers are unchecked."}

    # ---------------------------------------------------------------- raw
    def sql(self, query, params=(), limit=500):
        """Run one read-only SELECT. Writes, ATTACH and PRAGMA are refused even on a writable connection."""
        allowed = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE}

        def auth(action, *_):
            return sqlite3.SQLITE_OK if action in allowed else sqlite3.SQLITE_DENY

        if ";" in query.strip().rstrip(";"):
            raise ValueError("one statement at a time")
        steps = [0]

        def tick():
            steps[0] += 1
            return 1 if steps[0] > 2000 else 0  # about 20 million VM steps, then interrupt

        self.db.set_authorizer(auth)
        self.db.set_progress_handler(tick, 10000)
        try:
            cur = self.db.execute(query, params)
            cols = [d[0] for d in cur.description or []]
            rows = cur.fetchmany(limit + 1)
        except sqlite3.DatabaseError as e:
            raise ValueError(f"query refused or failed: {e}") from None
        finally:
            self.db.set_authorizer(None)
            self.db.set_progress_handler(None, 0)
        return {"columns": cols, "rows": [list(r) for r in rows[:limit]], "truncated": len(rows) > limit}
