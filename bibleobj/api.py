"""Read-only object API over the core data file (Acts in depth, the whole KJV as text).

    from bibleobj import Bible
    kjv = Bible.open()                      # dist/acts-core.sqlite (+ theographic layer if present)
    kjv.passage("Acts 13:1-3")
    kjv.find("James")                       # every James, so the caller has to pick one
    kjv.relation_path("abraham", "joseph-son-of-jacob")
    kjv.journey("paul")
    kjv.contemporaries("paul")
    kjv.place_history("antioch-of-syria")
    kjv.paul.wrote_to - kjv.paul.visited    # typed relationships as sets (see graph.py)
    kjv.words("John 21:15")                 # KJV words with their Greek lemmas

Every result is plain JSON-ready data. Every fact that comes from the text carries the
verse it came from. Dates are never returned bare: they only appear inside a Claim,
whose views each carry a label and a source (see claims.py).
"""
import pathlib, re, sqlite3
from collections import defaultdict, deque

from .books import BOOK_ALIASES
from .claims import make_claim, guard
from .graph import GraphMixin, ref_order

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "dist" / "acts-core.sqlite"
DEFAULT_LAYER = ROOT / "dist" / "acts-theographic.sqlite"

PREDICATE_TEXT = {
    "parent_of": ("parent of", "child of"),
    "descendant_of": ("descendant of", "ancestor of"),
    "spouse_of": ("spouse of", "spouse of"),
    "sibling_of": ("sibling of", "sibling of"),
    "kin_of": ("kin of", "kin of"),
}


class NotFound(KeyError):
    pass


def parse_ref(s):
    """'Acts 13:1-3', 'Acts.13.1', 'acts 13' -> (book, chapter, v_from, v_to) (verses may be None)."""
    s = s.strip()
    m = re.match(r"^([1-3]?\s?[A-Za-z]+)[\s.]+(\d+)(?:[:.](\d+)(?:\s*-\s*(\d+))?)?$", s)
    if not m:
        raise ValueError(f"not a reference: {s!r} (try 'Acts 13:1' or 'Acts.13.1-3')")
    book = BOOK_ALIASES.get(m.group(1).lower().replace(" ", ""))
    if not book:
        raise ValueError(f"unknown book {m.group(1)!r} (try 'Acts', 'John', '1 Cor' or an OSIS code)")
    c = int(m.group(2))
    v1 = int(m.group(3)) if m.group(3) else None
    v2 = int(m.group(4)) if m.group(4) else v1
    return book, c, v1, v2


def _ro_uri(path):
    # Path.as_uri() gives file:///C:/... on Windows and file:///home/... elsewhere
    return pathlib.Path(path).resolve().as_uri() + "?mode=ro"


class Bible(GraphMixin):
    def __init__(self, db, layer=None):
        self.db = db
        self.layer = layer
        self.db.row_factory = sqlite3.Row

    @classmethod
    def open(cls, path=None, layer=None, use_layer=True):
        path = pathlib.Path(path or DEFAULT_DB)
        db = sqlite3.connect(_ro_uri(path), uri=True, check_same_thread=False)
        lay = None
        lp = pathlib.Path(layer or DEFAULT_LAYER)
        if use_layer and lp.exists():
            lay = sqlite3.connect(_ro_uri(lp), uri=True, check_same_thread=False)
            lay.row_factory = sqlite3.Row
        return cls(db, lay)

    # ------------------------------------------------------------------ helpers
    def _q(self, sql, *a):
        return [dict(r) for r in self.db.execute(sql, a)]

    def _verse(self, ref, translation="KJV"):
        r = self.db.execute("SELECT text FROM verses WHERE ref=? AND translation=?", (ref, translation)).fetchone()
        return r["text"] if r else None

    def _entity_row(self, eid):
        r = self.db.execute("SELECT * FROM entities WHERE id=?", (eid,)).fetchone()
        if not r:
            raise NotFound(f"no entity with id {eid!r}; use find() to look one up by name")
        return dict(r)

    @staticmethod
    def _order(ref):
        return ref_order(ref)

    def _brief(self, eid):
        e = self._entity_row(eid)
        return {"id": e["id"], "label": e["label"], "kind": e["kind"]}

    # --------------------------------------------------------------------- text
    def info(self):
        meta = {r["key"]: r["value"] for r in self.db.execute("SELECT key, value FROM meta")}
        meta["sources"] = self._q("SELECT id, name, license, repo, commit_sha FROM sources ORDER BY id")
        meta["share_alike_layer_loaded"] = self.layer is not None
        return meta

    @guard
    def passage(self, reference, translation="KJV"):
        book, c, v1, v2 = parse_ref(reference)
        if v1 is None:
            rows = self._q("SELECT ref, verse, text, words FROM verses WHERE book=? AND chapter=? AND translation=? "
                           "ORDER BY verse", book, c, translation)
        else:
            rows = self._q("SELECT ref, verse, text, words FROM verses WHERE book=? AND chapter=? AND verse BETWEEN ? AND ? "
                           "AND translation=? ORDER BY verse", book, c, v1, v2, translation)
        if not rows:
            raise NotFound(f"{reference} is not in the {translation} text of {book}")
        return {"reference": reference, "translation": translation, "verses": rows,
                "words": sum(r["words"] for r in rows), "verse_count": len(rows)}

    @guard
    def length(self, book="Acts", chapter=None, translation="KJV"):
        if chapter is None:
            r = self.db.execute("SELECT chapters, verses, words, chars FROM books WHERE osis=? AND translation=?",
                                (book, translation)).fetchone()
            if not r:
                raise NotFound(book)
            return {"book": book, "translation": translation, "as_chapters": r["chapters"], "as_verses": r["verses"],
                    "as_words": r["words"], "as_characters": r["chars"],
                    "as_reading_minutes": round(r["words"] / 200), "word_rule": self.info()["word_rule"]}
        r = self.db.execute("SELECT verses, words FROM chapters WHERE book=? AND chapter=? AND translation=?",
                            (book, chapter, translation)).fetchone()
        if not r:
            raise NotFound(f"{book} {chapter}")
        return {"book": book, "chapter": chapter, "translation": translation, "as_verses": r["verses"], "as_words": r["words"]}

    # ----------------------------------------------------------------- entities
    @guard
    def find(self, name, kind=None):
        """Every entity whose name or alias matches, so the caller must pick which James."""
        n = name.strip().lower()
        rows = self._q("""
            SELECT DISTINCT e.id, e.label, e.kind, e.brief, e.era FROM entities e LEFT JOIN aliases a ON a.entity_id=e.id
            WHERE lower(e.name)=? OR lower(e.label)=? OR lower(a.form)=? OR e.id=? OR lower(e.label) LIKE ?
            ORDER BY e.id""", n, n, n, n.replace(" ", "-"), f"%{n}%")
        if kind:
            rows = [r for r in rows if r["kind"] == kind]
        for r in rows:
            m = self._q("SELECT ref FROM mentions WHERE entity_id=?", r["id"])
            refs = sorted({x["ref"] for x in m}, key=self._order)
            r["mentioned_in_verses"] = len(refs)
            r["first_mention"] = refs[0] if refs else None
        return {"query": name, "matches": rows,
                "note": "Several matches means several different individuals; pick one by id." if len(rows) > 1 else ""}

    @guard
    def entity(self, eid):
        e = self._entity_row(eid)
        out = {k: e[k] for k in ("id", "label", "kind", "name", "description", "brief", "gender", "era")}
        out["also_called"] = [r["form"] for r in self._q("SELECT form FROM aliases WHERE entity_id=? ORDER BY form", eid)]
        refs = sorted({r["ref"] for r in self._q("SELECT ref FROM mentions WHERE entity_id=?", eid)}, key=self._order)
        out["mentioned_in_verses"] = len(refs)
        out["first_mention"] = refs[0] if refs else None
        out["last_mention"] = refs[-1] if refs else None
        if e["group_of"]:
            out["group_of"] = e["group_of"]
        if e["kind"] == "place":
            out["sites"] = self.sites(eid)
        if e["kind"] == "person":
            out["born"] = self.claim(eid, "born")
            out["died"] = self.claim(eid, "died")
            out["relations"] = self.relations(eid)
        out["source"] = {"tipnr_key": e["tipnr_key"], "ustrong": e["ustrong"], "from": e["source"]}
        return out

    def sites(self, eid):
        return self._q("SELECT rank, lat, lon, confidence, label, source FROM place_sites WHERE entity_id=? ORDER BY rank", eid)

    @guard
    def mentions(self, eid, limit=None):
        self._entity_row(eid)
        rows = self._q("SELECT ref, pos, surface, basis FROM mentions WHERE entity_id=?", eid)
        rows.sort(key=lambda r: (self._order(r["ref"]), r["pos"]))
        if limit:
            rows = rows[:limit]
        for r in rows:
            r["text"] = self._verse(r["ref"])
        return {"id": eid, "count": len(rows), "mentions": rows}

    # ------------------------------------------------------------------- claims
    def claim(self, eid, prop):
        c = self.db.execute("SELECT * FROM claims WHERE entity_id=? AND property=?", (eid, prop)).fetchone()
        views = self._q("SELECT label, value, range_from, range_to, source FROM claim_views WHERE entity_id=? AND property=?",
                        eid, prop)
        if self.layer is not None:
            views += [dict(r) for r in self.layer.execute(
                "SELECT label, value, range_from, range_to, source FROM claim_views WHERE entity_id=? AND property=?",
                (eid, prop))]
        if not c and not views:
            return make_claim(prop, "not-stated", True, [], note="No claim recorded.")
        return make_claim(prop, c["basis"] if c else "view-only", bool(c["not_stated"]) if c else True, views,
                          note=c["note"] if c else "", relative_to=c["relative_to"] if c else None)

    # ---------------------------------------------------------------- relations
    def relations(self, eid):
        out = []
        for r in self._q("SELECT * FROM relations WHERE subject=? OR object=? ORDER BY ref, predicate", eid, eid):
            fwd = r["subject"] == eid
            other = r["object"] if fwd else r["subject"]
            out.append({"relation": PREDICATE_TEXT[r["predicate"]][0 if fwd else 1], "other": self._brief(other),
                        "ref": r["ref"], "quote": r["quote"], "note": r["note"] or ""})
        return out

    @guard
    def relation_path(self, a, b, max_steps=8):
        """Shortest family path between two people, each step citing its verse."""
        self._entity_row(a), self._entity_row(b)
        adj = defaultdict(list)
        for r in self._q("SELECT * FROM relations"):
            adj[r["subject"]].append((r["object"], r, True))
            adj[r["object"]].append((r["subject"], r, False))
        prev = {a: None}
        dq = deque([a])
        while dq:
            x = dq.popleft()
            if x == b:
                break
            for y, r, fwd in sorted(adj[x], key=lambda t: (t[0], t[1]["ref"])):
                if y not in prev:
                    prev[y] = (x, r, fwd)
                    dq.append(y)
        if b not in prev:
            return {"from": self._brief(a), "to": self._brief(b), "found": False, "steps": [],
                    "note": "No family path in the relations Acts itself states."}
        steps, cur = [], b
        while prev[cur]:
            x, r, fwd = prev[cur]
            steps.append({"from": self._brief(x), "relation": PREDICATE_TEXT[r["predicate"]][0 if fwd else 1],
                          "to": self._brief(cur), "ref": r["ref"], "quote": r["quote"], "note": r["note"] or ""})
            cur = x
        steps.reverse()
        if len(steps) > max_steps:
            return {"from": self._brief(a), "to": self._brief(b), "found": False, "steps": [],
                    "note": f"Path longer than {max_steps} steps."}
        return {"from": self._brief(a), "to": self._brief(b), "found": True, "steps": steps}

    # ------------------------------------------------------------------ queries
    @guard
    def contemporaries(self, eid):
        """People 'met in the text': named in the same verse as this person, in New Testament times."""
        me = self._entity_row(eid)
        rows = self._q("""
            SELECT m2.entity_id AS id, m1.ref AS ref FROM mentions m1 JOIN mentions m2 ON m1.ref=m2.ref
            JOIN entities e ON e.id=m2.entity_id
            WHERE m1.entity_id=? AND m2.entity_id!=? AND e.kind='person'""", eid, eid)
        by = defaultdict(set)
        for r in rows:
            by[r["id"]].add(r["ref"])
        met, historical = [], []
        for oid, refs in by.items():
            e = self._entity_row(oid)
            item = {"id": oid, "label": e["label"], "shared_verses": sorted(refs, key=self._order)}
            (met if e["era"] == "NT" else historical).append(item)
        key = lambda i: (-len(i["shared_verses"]), i["id"])
        return {"person": {"id": eid, "label": me["label"]},
                "basis": "met in the text: named in the same verse, and TIPNR places them in New Testament times",
                "met_in_text": sorted(met, key=key),
                "named_alongside_but_not_contemporary": sorted(historical, key=key),
                "alive_at_the_same_time": make_claim(
                    "alive_at_the_same_time", "not-stated", True, [],
                    note="Overlapping lifespans need a chronology; Acts states none. 'met_in_text' is the stated answer.")}

    @guard
    def journey(self, person="paul"):
        """A person's travels in the order the text tells them, with coordinates and the verse for each stop."""
        stops = self._q("SELECT seq, place_id, ref, leg, quote FROM itinerary WHERE person_id=? ORDER BY seq", person)
        if not stops:
            raise NotFound(f"no itinerary curated for {person!r} yet (only 'paul' in this first pass)")
        for s in stops:
            s["place"] = self._entity_row(s["place_id"])["label"]
            site = self.sites(s["place_id"])
            s["site"] = site[0] if site else None
            s["other_candidate_sites"] = len(site) - 1 if site else 0
        return {"person": self._brief(person), "order": "narrative order of Acts (stated), not dated",
                "when": make_claim("when", "not-stated", True, [], note="Acts gives no years for these journeys."),
                "stops": stops}

    def journey_geojson(self, person="paul"):
        j = self.journey(person)
        feats, line = [], []
        for s in j["stops"]:
            if not s["site"]:
                continue
            xy = [s["site"]["lon"], s["site"]["lat"]]
            line.append(xy)
            feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": xy},
                          "properties": {"seq": s["seq"], "place": s["place"], "ref": s["ref"], "leg": s["leg"],
                                         "quote": s["quote"], "confidence": s["site"]["confidence"]}})
        feats.insert(0, {"type": "Feature", "geometry": {"type": "LineString", "coordinates": line},
                         "properties": {"name": f"{j['person']['label']} in Acts (narrative order)"}})
        return {"type": "FeatureCollection", "features": feats}

    @guard
    def place_history(self, eid):
        """Everything Acts says happened at a place, in narrative order, with who was there."""
        e = self._entity_row(eid)
        if e["kind"] != "place":
            raise ValueError(f"{eid} is a {e['kind']}, not a place")
        refs = sorted({r["ref"] for r in self._q("SELECT ref FROM mentions WHERE entity_id=?", eid)}, key=self._order)
        events = []
        for ref in refs:
            people = self._q("""SELECT DISTINCT e.id, e.label FROM mentions m JOIN entities e ON e.id=m.entity_id
                                WHERE m.ref=? AND e.kind='person' ORDER BY e.id""", ref)
            events.append({"ref": ref, "text": self._verse(ref), "people_named": people})
        return {"place": {"id": eid, "label": e["label"]}, "sites": self.sites(eid),
                "order": "narrative order of Acts (stated), not dated",
                "when": make_claim("when", "not-stated", True, [], note="Acts dates none of these."),
                "events": events}

    @guard
    def verse_entities(self, reference):
        book, c, v1, v2 = parse_ref(reference)
        out = []
        for v in range(v1 or 1, (v2 or v1 or 1) + 1):
            ref = f"{book}.{c}.{v}"
            ents = self._q("""SELECT e.id, e.label, e.kind, m.surface, m.pos FROM mentions m JOIN entities e ON e.id=m.entity_id
                              WHERE m.ref=? ORDER BY m.pos""", ref)
            out.append({"ref": ref, "text": self._verse(ref), "entities": ents})
        return {"reference": reference, "verses": out}
