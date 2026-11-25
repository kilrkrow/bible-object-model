"""Build the Acts first pass of the Bible object model.

Writes two SQLite files into dist/:
  acts-core.sqlite         KJV text + STEPBible TIPNR names + OpenBible places + our own
                           curation. Data licence: CC BY 4.0 (see ATTRIBUTION.md).
  acts-theographic.sqlite  Optional share-alike layer derived from Theographic
                           (CC BY-SA 4.0): crosswalk ids and its chronology views.
                           Kept separate so the core never carries share-alike terms.

Usage:
  python build/fetch_sources.py      # once, pins and verifies every source
  python build/build.py [--sources DIR] [--out DIR]

The build is deterministic: rows are inserted in sorted order, nothing time-based is
stored, and the file is VACUUMed at the end, so a rerun gives a byte-identical file
on the same SQLite version. meta.content_sha256 is a hash of a canonical dump of
every table, which is identical across SQLite versions.
"""
import argparse, csv, hashlib, json, pathlib, re, sqlite3, sys, unicodedata
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
BUILD_VERSION = "0.1.0"
TIPNR_FILE = "tipnr/Proper Nouns/TIPNR - Translators Individualised Proper Names with all References - STEPBible.org CC BY.txt"

# Words are runs of letters, joined by an apostrophe or hyphen (KJV has few of either).
WORD_RE = re.compile(r"[A-Za-z]+(?:['’-][A-Za-z]+)*")
REF_RE = re.compile(r"\bAct\.(\d+)\.(\d+)([a-z]?)")


def words(text):
    return WORD_RE.findall(text)


def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def sha256_file(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def read_csv(p):
    with open(p, newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if any((v or "").strip() for v in r.values())]


# --------------------------------------------------------------------------- KJV
def load_kjv(src):
    d = json.loads((src / "kjv/Acts.json").read_text(encoding="utf-8"))
    verses = []
    for ch in d["chapters"]:
        for v in ch["verses"]:
            c, n = int(ch["chapter"]), int(v["verse"])
            verses.append((f"Acts.{c}.{n}", c, n, v["text"]))
    verses.sort(key=lambda x: (x[1], x[2]))
    return verses


# ------------------------------------------------------------------------- TIPNR
def parse_tipnr(src):
    """Return entities that occur in Acts, with their forms and Acts references."""
    t = (src / TIPNR_FILE).read_text(encoding="utf-8").replace("\r", "")
    parts = re.split(r"\n\$=+ ?([A-Z+()s ]+?)\s*\n", t)
    out = []
    for i in range(1, len(parts) - 1, 2):
        cat, body = parts[i].strip(), parts[i + 1]
        lines = body.split("\n")
        hdr = lines[0].split("\t")
        if "@" not in hdr[0] or "=" not in hdr[0]:
            continue
        key, ustrong = hdr[0].split("=", 1)
        subs = [l.split("\t") for l in lines[1:] if l.startswith("–")]
        forms, refs = [], []
        for s in subs:
            kind = s[0].replace("–", "").strip()
            if kind.startswith("Total") or len(s) < 5:
                continue
            forms.append(s[3].strip())
            for c, v, suf in REF_RE.findall(s[4]):
                refs.append((int(c), int(v), suf or ""))
        if not refs:
            continue
        brief = re.search(r"@Brief= *(.*)", body)
        typ = hdr[8].strip() if len(hdr) > 8 else ""
        kind = {"PERSON(s)": "person", "PLACE": "place", "PLACE+PERSON": "place",
                "OTHER": "other", "EXCLUDED OTHER": "other"}[cat]
        if kind == "other":
            desc = hdr[1].lower()
            kind = ("deity" if "deity" in desc else "group" if "group" in desc
                    else "festival" if "feast" in desc else "language" if "language" in desc
                    else "title" if "title" in desc else "other")
        out.append({
            "tipnr_key": key.strip(), "ustrong": ustrong.strip(), "category": cat,
            "kind": kind, "name": key.split("@")[0].strip(),
            "description": hdr[1].strip(), "gender": typ if typ in ("Male", "Female") else "",
            "brief": brief.group(1).strip() if brief else "",
            "parents": hdr[2].strip() if kind == "person" and len(hdr) > 2 else "",
            "siblings": hdr[3].strip() if kind == "person" and len(hdr) > 3 else "",
            "partners": hdr[4].strip() if kind == "person" and len(hdr) > 4 else "",
            "offspring": hdr[5].strip() if kind == "person" and len(hdr) > 5 else "",
            "forms": forms, "refs": sorted(set(refs)),
        })
    return out


def form_candidates(forms, extra):
    """Every English spelling a TIPNR record lists (ESV, KJV or NIV), plus curated KJV forms."""
    c = set(extra)
    for f in forms:
        for part in f.split(";"):
            part = re.sub(r"=.*", "", part).strip()
            part = part.strip("[] ").replace("/ ", " ").replace("_", " ")
            part = re.sub(r"\(.*?\)", "", part).strip()
            if not part or not re.search(r"[A-Za-z]", part):
                continue
            for p in part.split(","):
                p = p.strip()
                if p and p[0].isupper():
                    c.add(p)
    return sorted(c, key=lambda s: (-len(s), s))


def era(desc):
    d = desc.lower()
    if "new testament" in d:
        return "NT"
    if "old testament" in d:
        return "OT"
    return ""


# --------------------------------------------------------------------- OpenBible
def load_openbible(src):
    by_tipnr = {}
    for line in (src / "openbible/data/ancient.jsonl").read_text(encoding="utf-8").splitlines():
        d = json.loads(line)
        ld = d.get("linked_data", {}).get("s3b25cf") or {}
        tips = ([ld["id"]] if ld.get("id") else []) + list(ld.get("ids", []))
        cands = []
        for ident in d.get("identifications", []):
            score = (ident.get("score") or {}).get("time_total", 0)
            for r in ident.get("resolutions", []):
                if not r.get("lonlat"):
                    continue
                lon, lat = (float(x) for x in r["lonlat"].split(","))
                label = re.sub(r"<[^>]+>", "", r.get("description") or ident.get("description") or "")
                cands.append((score, lat, lon, label, r.get("lonlat_type", "")))
        cands.sort(key=lambda x: (-x[0], x[3], x[1], x[2]))
        rec = {"openbible_id": d["id"], "friendly": d.get("friendly_id", ""), "cands": cands,
               "shared": len(tips) > 1, "how": "tipnr key"}
        for tip in tips:
            by_tipnr.setdefault(tip, rec)
        by_tipnr.setdefault("name:" + rec["friendly"].lower(), dict(rec, how="name"))
    return by_tipnr


def tipnr_short(key):
    # "Antioch@Act.6.5-Gal" -> "Antioch@Act.6.5"
    return re.sub(r"-[^@]*$", "", key)


# ------------------------------------------------------------------------- build
SCHEMA = """
CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE sources(id TEXT PRIMARY KEY, name TEXT, license TEXT, repo TEXT, commit_sha TEXT, files TEXT, role TEXT);
CREATE TABLE translations(id TEXT PRIMARY KEY, name TEXT, base_text TEXT, versification TEXT, license TEXT, source TEXT);
CREATE TABLE books(osis TEXT, translation TEXT, name TEXT, testament TEXT, chapters INT, verses INT, words INT, chars INT, PRIMARY KEY(osis, translation));
CREATE TABLE chapters(book TEXT, translation TEXT, chapter INT, verses INT, words INT, PRIMARY KEY(book, translation, chapter));
CREATE TABLE verses(ref TEXT, translation TEXT, book TEXT, chapter INT, verse INT, text TEXT NOT NULL, words INT, chars INT, PRIMARY KEY(ref, translation));
CREATE TABLE entities(id TEXT PRIMARY KEY, kind TEXT NOT NULL, name TEXT NOT NULL, label TEXT NOT NULL,
  description TEXT, brief TEXT, gender TEXT, era TEXT, tipnr_key TEXT, ustrong TEXT, group_of TEXT, source TEXT NOT NULL);
CREATE TABLE aliases(entity_id TEXT, form TEXT, PRIMARY KEY(entity_id, form));
CREATE TABLE mentions(entity_id TEXT NOT NULL, ref TEXT NOT NULL, pos INT NOT NULL, surface TEXT NOT NULL,
  basis TEXT NOT NULL, source TEXT NOT NULL, PRIMARY KEY(entity_id, ref, pos));
CREATE TABLE place_sites(entity_id TEXT, rank INT, lat REAL, lon REAL, confidence REAL, label TEXT, geometry TEXT,
  openbible_id TEXT, source TEXT, PRIMARY KEY(entity_id, rank));
CREATE TABLE relations(subject TEXT NOT NULL, predicate TEXT NOT NULL, object TEXT NOT NULL, ref TEXT NOT NULL,
  quote TEXT NOT NULL, note TEXT, source TEXT NOT NULL, PRIMARY KEY(subject, predicate, object, ref));
CREATE TABLE itinerary(person_id TEXT, seq INT, place_id TEXT NOT NULL, ref TEXT NOT NULL, leg TEXT, quote TEXT NOT NULL,
  source TEXT NOT NULL, PRIMARY KEY(person_id, seq));
CREATE TABLE claims(entity_id TEXT, property TEXT, basis TEXT NOT NULL, not_stated INT NOT NULL, relative_to TEXT,
  note TEXT, PRIMARY KEY(entity_id, property));
CREATE TABLE claim_views(entity_id TEXT, property TEXT, label TEXT NOT NULL, value TEXT, range_from TEXT, range_to TEXT,
  source TEXT NOT NULL, PRIMARY KEY(entity_id, property, label));
CREATE TABLE corrections(entity_id TEXT, ref TEXT, action TEXT, value TEXT, note TEXT, PRIMARY KEY(entity_id, ref, action));
CREATE INDEX mentions_ref ON mentions(ref);
CREATE INDEX relations_obj ON relations(object);
"""


def build_core(src, out):
    lock = json.loads((ROOT / "sources.lock.json").read_text())
    kjv = load_kjv(src)
    tip = parse_tipnr(src)
    geo = load_openbible(src)
    ids = {r["ustrong"]: r for r in read_csv(ROOT / "curation/ids.csv")}
    extra_forms = defaultdict(list)
    for r in read_csv(ROOT / "curation/kjv_forms.csv"):
        extra_forms[r["id"]].append(r["form"])
    corrections = read_csv(ROOT / "curation/mention_corrections.csv")
    corr = {(r["id"], r["ref"]): r for r in corrections}
    gentilics = read_csv(ROOT / "curation/gentilics.csv")
    gent_forms = sorted({g["form"] for g in gentilics}, key=lambda f: (-len(f), f))
    gent_of = {g["form"]: g for g in gentilics}
    extra_ents = read_csv(ROOT / "curation/extra_entities.csv")
    vtext = {ref: text for ref, _, _, text in kjv}

    # --- ids: curated first, then slug(name); refuse to build with a collision
    for e in tip:
        e["name"] = e["name"].replace("_", " ")
        cur = ids.get(e["ustrong"])
        e["id"] = cur["id"] if cur else slug(e["name"])
        e["label"] = cur["label"] if cur else e["name"]
        if cur and cur.get("kind"):
            e["kind"] = cur["kind"]
        e["group_of"] = ""
    for x in extra_ents:
        tip.append({"tipnr_key": "", "ustrong": "", "category": "curated", "kind": x["kind"], "name": x["name"],
                    "description": x["description"], "gender": "", "brief": x["description"], "id": x["id"],
                    "label": x["label"], "forms": [f.strip() for f in x["forms"].split("|")], "group_of": "",
                    "refs": [], "curated_refs": [r.strip() for r in x["refs"].split("|") if r.strip()]})
    splits = read_csv(ROOT / "curation/form_splits.csv")
    split_of = {(s_["id"], s_["form"]): s_["target_id"] for s_ in splits}
    for s_ in splits:
        tip.append({"tipnr_key": "", "ustrong": "", "category": "curated", "kind": s_["target_kind"],
                    "name": s_["form"], "description": s_["note"], "gender": "", "brief": "", "id": s_["target_id"],
                    "label": s_["target_label"], "forms": [s_["form"]], "group_of": s_["id"], "refs": [],
                    "curated_refs": []})
    have = {e["id"] for e in tip}
    for g in gentilics:
        if g["group_id"] not in have:
            have.add(g["group_id"])
            tip.append({"tipnr_key": "", "ustrong": "", "category": "curated", "kind": "group",
                        "name": g["label"], "description": "People group named in Acts (gentilic form)",
                        "gender": "", "brief": "", "id": g["group_id"], "label": g["label"],
                        "forms": [], "group_of": g["parent"], "refs": [], "curated_refs": []})
    seen = defaultdict(list)
    for e in tip:
        seen[e["id"]].append(e["tipnr_key"] or e["name"])
    dup = {k: v for k, v in seen.items() if len(v) > 1}
    if dup:
        sys.exit("id collision, add rows to curation/ids.csv: " + json.dumps(dup, indent=1))
    by_id = {e["id"]: e for e in tip}
    for f, g in gent_of.items():
        by_id[g["group_id"]].setdefault("gforms", []).append(f)

    def pattern(form, plural):
        f = re.escape(form).replace("'", "['\u2019]")
        return r"(?<![A-Za-z])" + f + (r"(?:e?s)?" if plural else "") + r"(?:['\u2019]s?)?(?![a-z])"

    def find_all(forms, text, plural):
        """Every non-overlapping match of any form, longest form first."""
        spans = []
        for f in sorted(set(forms), key=lambda x: (-len(x), x)):
            for m in re.finditer(pattern(f, plural), text):
                if not any(a < m.end() and m.start() < b for a, b, _ in spans):
                    spans.append((m.start(), m.end(), m.group(0)))
        return sorted((a, s_) for a, b, s_ in spans)

    # --- mentions: find the surface form of each TIPNR reference in the KJV verse
    mentions = {}  # (entity_id, ref, occurrence) -> (surface, basis, source)
    unmatched = []
    for e in sorted(tip, key=lambda e: e["id"]):
        cands = form_candidates(e["forms"], extra_forms.get(e["id"], []))
        e["cands"] = cands
        if e.get("curated_refs") == ["scan"]:
            refs = sorted({(c_, v_, "") for ref_, c_, v_, text_ in kjv
                           if any(re.search(pattern(f, False), text_) for f in cands)})
        elif e.get("curated_refs"):
            refs = [(int(r.split(".")[1]), int(r.split(".")[2]), "") for r in e["curated_refs"]]
        else:
            refs = e["refs"]
        for c, v, suf in refs:
            ref = f"Acts.{c}.{v}"
            cr = corr.get((e["id"], ref))
            if cr and cr["action"] == "drop":
                continue
            if cr and cr["action"] == "move":
                ref = cr["value"]
            if ref not in vtext:
                unmatched.append((e["id"], ref, "verse not in KJV source"))
                continue
            text = vtext[ref]
            hits = []  # (pos, surface, target)
            if cr and cr["action"] == "retarget":
                t_ = by_id[cr["value"]]
                hits = [(p_, s_, t_["id"]) for p_, s_ in find_all(
                    form_candidates(t_["forms"], extra_forms.get(t_["id"], [])), text, True)]
            elif cr and cr["action"] == "surface":
                m = re.search(r"(?<![A-Za-z])" + re.escape(cr["value"]) + r"(?![a-z])", text)
                hits = [(m.start() if m else -1, cr["value"], e["id"])]
            else:
                # gentilic forms (Jews, Greeks, Romans...) go to their people group
                gf = [f for f in gent_forms
                      if f in cands or any(c_.startswith(f) or f.startswith(c_) for c_ in cands if len(c_) > 3)]
                taken = []
                for p_, s_ in find_all(gf, text, True):
                    root = re.sub(r"(['\u2019]s?|e?s)$", "", s_)
                    g = gent_of.get(s_) or gent_of.get(root) or next(gent_of[f] for f in gf if s_.startswith(f))
                    hits.append((p_, s_, g["group_id"]))
                    taken.append((p_, p_ + len(s_)))
                for p_, s_ in find_all(cands, text, e["kind"] in ("group", "place")):
                    if any(a_ <= p_ < b_ for a_, b_ in taken):
                        continue
                    hits.append((p_, s_, e["id"]))
            if not hits:
                unmatched.append((e["id"], ref, "no listed form found in KJV verse"))
                continue
            for p_, s_, target in hits:
                root = re.sub(r"(['\u2019]s?|e?s)$", "", s_)
                target = split_of.get((target, s_), split_of.get((target, root), target))
                basis = "pronoun" if s_ in ("he", "him", "his") else "name-in-verse"
                mentions.setdefault((target, ref, p_), (s_, basis, "tipnr" + ("+correction" if cr else "")))

    # names the KJV supplies where the Greek (and so TIPNR) has none
    for r in corrections:
        if r["action"] == "add":
            e = by_id[r["id"]]
            for p_, s_ in find_all(form_candidates(e["forms"], extra_forms.get(e["id"], [])), vtext[r["ref"]], False):
                mentions[(e["id"], r["ref"], p_)] = (s_, "name-in-verse", "correction")

    # gentilic groups: scan every verse, since TIPNR does not tag all of them
    for g in gentilics:
        for ref, text in vtext.items():
            for p_, s_ in find_all([g["form"]], text, True):
                if not any(k[1] == ref and k[2] == p_ for k in mentions):
                    mentions[(g["group_id"], ref, p_)] = (s_, "name-in-verse", "curation-scan")

    # one occurrence of a name is one individual: settle verses where TIPNR lists two people with the same name
    choices = read_csv(ROOT / "curation/occurrence_choices.csv")
    at = defaultdict(list)
    for (eid, ref, p_), (s_, _, _) in mentions.items():
        at[(ref, p_)].append(eid)
    drop = []
    for (ref, p_), eids in sorted(at.items()):
        if len(eids) < 2:
            continue
        surface = mentions[(eids[0], ref, p_)][0]
        base = re.sub(r"[’']s$", "", surface)
        nth = 1 + sum(1 for (r2, q), ids2 in at.items() if r2 == ref and q < p_ and len(ids2) > 1
                      and re.sub(r"[’']s$", "", mentions[(ids2[0], r2, q)][0]) == base)
        pick = [c for c in choices if c["ref"] == ref and c["form"] == base and c["occurrence"] == str(nth)] or \
               [c for c in choices if c["ref"] == "*" and c["form"] == base]
        if not pick or pick[0]["id"] not in eids:
            sys.exit(f"{ref} position {p_} '{surface}' is claimed by {sorted(eids)}; add a row to curation/occurrence_choices.csv")
        drop += [(eid, ref, p_) for eid in eids if eid != pick[0]["id"]]
    for k in drop:
        del mentions[k]

    if out.exists():
        out.unlink()
    db = sqlite3.connect(out)
    db.executescript(SCHEMA)
    meta = {
        "build_version": BUILD_VERSION, "scope": "Acts", "default_translation": "KJV",
        "word_rule": "a word is a run of letters A-Z joined by apostrophes or hyphens; numbers and punctuation are not words",
        "data_license": "CC BY 4.0 (derived from STEPBible TIPNR and OpenBible geocoding; KJV text is public domain outside the UK)",
        "date_rule": "No date is ever returned bare. Dates live only in claims and labelled claim_views.",
    }
    for name, spec in sorted(lock.items()):
        if spec["layer"] != "core":
            continue
        db.execute("INSERT INTO sources VALUES(?,?,?,?,?,?,?)",
                   (name, spec["name"], spec["license"], spec["repo"], spec["commit"],
                    json.dumps(spec["files"], sort_keys=True), spec["layer"]))
    db.execute("INSERT INTO sources VALUES(?,?,?,?,?,?,?)",
               ("curation", "Hand curation for this project (ids, KJV forms, people groups, relations, Paul's itinerary, corrections)",
                "CC BY 4.0", "", "", json.dumps(sorted(p.name for p in (ROOT / "curation").glob("*.csv"))), "core"))
    db.execute("INSERT INTO translations VALUES(?,?,?,?,?,?)",
               ("KJV", "King James Version (1769 Oxford text)", "Textus Receptus", "KJV", "Public domain (Crown rights in the UK)", "kjv"))

    # --- text
    chap = defaultdict(lambda: [0, 0])
    tw = tc = 0
    for ref, c, n, text in kjv:
        w, ch = len(words(text)), len(text)
        db.execute("INSERT INTO verses VALUES(?,?,?,?,?,?,?,?)", (ref, "KJV", "Acts", c, n, text, w, ch))
        chap[c][0] += 1
        chap[c][1] += w
        tw += w
        tc += ch
    for c in sorted(chap):
        db.execute("INSERT INTO chapters VALUES(?,?,?,?,?)", ("Acts", "KJV", c, chap[c][0], chap[c][1]))
    db.execute("INSERT INTO books VALUES(?,?,?,?,?,?,?,?)", ("Acts", "KJV", "Acts", "NT", len(chap), len(kjv), tw, tc))

    # --- entities that the KJV text of Acts actually names
    mentioned = {k[0] for k in mentions}
    dropped = sorted(e["id"] for e in tip if e["id"] not in mentioned)
    for e in sorted(tip, key=lambda e: e["id"]):
        if e["id"] not in mentioned:
            continue
        db.execute("INSERT INTO entities VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                   (e["id"], e["kind"], e["name"], e["label"], e["description"], e["brief"], e["gender"],
                    era(e["description"]), e["tipnr_key"], e["ustrong"], e.get("group_of", ""),
                    "tipnr" if e["tipnr_key"] else "curation"))
        for f in sorted(set(e["cands"]) | set(e.get("gforms", []))):
            db.execute("INSERT OR IGNORE INTO aliases VALUES(?,?)", (e["id"], f))
        if e["kind"] == "person":
            for prop in ("born", "died"):
                db.execute("INSERT INTO claims VALUES(?,?,?,?,?,?)",
                           (e["id"], prop, "not-stated", 1, None, "The KJV text of Acts gives no year for this."))
        if e["kind"] == "place" and e["tipnr_key"]:
            g = geo.get(tipnr_short(e["tipnr_key"])) or geo.get("name:" + e["name"].lower()) or geo.get("name:mount " + e["name"].lower())
            if g:
                for rank, (score, lat, lon, label, gtype) in enumerate(g["cands"][:5]):
                    db.execute("INSERT INTO place_sites VALUES(?,?,?,?,?,?,?,?,?)",
                               (e["id"], rank, round(lat, 6), round(lon, 6), round(score / 1000.0, 3), label,
                                gtype, g["openbible_id"], "openbible" if g["how"] == "tipnr key" else "openbible (matched by name)"))
    for (eid, ref, occ), (surface, basis, source) in sorted(mentions.items()):
        if vtext[ref][occ:occ + len(surface)] != surface:
            sys.exit(f"mention {eid} {ref}: '{surface}' is not at position {occ} of the verse")
        db.execute("INSERT INTO mentions VALUES(?,?,?,?,?,?)", (eid, ref, occ, surface, basis, source))
    for r in corrections:
        db.execute("INSERT INTO corrections VALUES(?,?,?,?,?)", (r["id"], r["ref"], r["action"], r["value"], r["note"]))

    # --- curated relations and itinerary, each checked against its verse and TIPNR's mentions
    ent_ids = {e["id"] for e in tip if e["id"] in mentioned}
    mset = {(k[0], k[1]) for k in mentions}
    problems = []
    for r in sorted(read_csv(ROOT / "curation/relations.csv"), key=lambda r: (r["subject"], r["predicate"], r["object"], r["ref"])):
        for k in ("subject", "object"):
            if r[k] not in ent_ids:
                problems.append(f"relation {r}: unknown {k}")
        if r["quote"] not in vtext.get(r["ref"], ""):
            problems.append(f"relation quote not in {r['ref']}: {r['quote']!r}")
        for k in ("subject", "object"):
            if (r[k], r["ref"]) not in mset and not r["note"]:
                problems.append(f"relation {r['subject']}-{r['object']}: {r[k]} has no mention at {r['ref']}")
        db.execute("INSERT INTO relations VALUES(?,?,?,?,?,?,?)",
                   (r["subject"], r["predicate"], r["object"], r["ref"], r["quote"], r["note"], "curation"))
    for i, r in enumerate(read_csv(ROOT / "curation/paul_itinerary.csv"), 1):
        if r["place_id"] not in ent_ids:
            problems.append(f"itinerary {i}: unknown place {r['place_id']}")
        if r["quote"] not in vtext.get(r["ref"], ""):
            problems.append(f"itinerary {i}: quote not in {r['ref']}: {r['quote']!r}")
        if (r["place_id"], r["ref"]) not in mset:
            problems.append(f"itinerary {i}: {r['place_id']} has no mention at {r['ref']}")
        db.execute("INSERT INTO itinerary VALUES(?,?,?,?,?,?,?)",
                   ("paul", i, r["place_id"], r["ref"], r["leg"], r["quote"], "curation"))
    if problems:
        db.close()
        sys.exit("curation problems:\n  " + "\n  ".join(problems))

    # --- canonical content hash, then compact
    for k, v in sorted(meta.items()):
        db.execute("INSERT INTO meta VALUES(?,?)", (k, v))
    db.commit()
    h = content_hash(db)
    db.execute("INSERT INTO meta VALUES('content_sha256', ?)", (h,))
    db.commit()
    db.execute("VACUUM")
    db.close()
    return unmatched, dropped


def content_hash(db):
    h = hashlib.sha256()
    tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    for t in tables:
        if t == "meta":
            rows = db.execute("SELECT * FROM meta WHERE key != 'content_sha256' ORDER BY 1").fetchall()
        else:
            n = len(db.execute(f"SELECT * FROM {t} LIMIT 0").description)
            rows = db.execute(f"SELECT * FROM {t} ORDER BY " + ",".join(str(i) for i in range(1, n + 1))).fetchall()
        h.update(t.encode())
        for row in rows:
            h.update(json.dumps(row, ensure_ascii=False).encode())
    return h.hexdigest()


# ------------------------------------------------------- Theographic (share-alike)
def build_theographic(src, core_path, out):
    th = src / "theographic/json"
    people = {p["id"]: p["fields"] for p in json.loads((th / "people.json").read_text())}
    places = {p["id"]: p["fields"] for p in json.loads((th / "places.json").read_text())}
    verses = json.loads((th / "verses.json").read_text())
    acts = [v["fields"] for v in verses if v["fields"]["osisRef"].startswith("Acts.")]
    theo_refs = defaultdict(set)  # theographic id -> Acts refs
    for v in acts:
        for pid in v.get("people", []):
            theo_refs[pid].add(v["osisRef"])
        for pid in v.get("places", []):
            theo_refs[pid].add(v["osisRef"])

    core = sqlite3.connect(core_path)
    ours = defaultdict(set)
    for eid, ref in core.execute("SELECT entity_id, ref FROM mentions"):
        ours[eid].add(ref)
    names = defaultdict(set)
    for eid, form in core.execute("SELECT entity_id, form FROM aliases"):
        names[eid].add(form.lower())
    kinds = dict(core.execute("SELECT id, kind FROM entities"))
    core.close()

    if out.exists():
        out.unlink()
    db = sqlite3.connect(out)
    db.executescript("""
    CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
    CREATE TABLE crosswalk(entity_id TEXT, theographic_id TEXT, theographic_slug TEXT, kind TEXT, shared_refs INT,
      PRIMARY KEY(entity_id, theographic_id));
    CREATE TABLE claim_views(entity_id TEXT, property TEXT, label TEXT NOT NULL, value TEXT, range_from TEXT,
      range_to TEXT, source TEXT NOT NULL, PRIMARY KEY(entity_id, property, label));
    """)
    rows = []
    for tid, refs in theo_refs.items():
        if tid in people:
            f, kind = people[tid], "person"
            tnames = {f.get("name", "").lower(), f.get("displayTitle", "").lower()}
            tnames |= {n.strip().lower() for n in (f.get("alsoCalled") or "").split(",") if n.strip()}
            slug_ = f.get("slug") or f.get("personLookup")
        elif tid in places:
            f, kind = places[tid], "place"
            tnames = {(f.get("kjvName") or "").lower(), (f.get("esvName") or "").lower(), (f.get("displayTitle") or "").lower()}
            slug_ = f.get("slug") or f.get("placeLookup")
        else:
            continue
        best = None
        for eid, orefs in ours.items():
            shared = len(refs & orefs)
            if shared and names[eid] & tnames and (kinds[eid] == kind or kinds[eid] not in ("person", "place")):
                if not best or shared > best[1]:
                    best = (eid, shared)
        if best:
            rows.append((best[0], tid, slug_, kind, best[1]))
            if kind == "person":
                label = "Theographic (Floyd Nolen Jones chronology)"
                for prop, fld in (("born", "birthYear"), ("died", "deathYear")):
                    if f.get(fld):
                        y = int(f[fld])
                        db.execute("INSERT OR IGNORE INTO claim_views VALUES(?,?,?,?,?,?,?)",
                                   (best[0], prop, label, f"{abs(y)} {'BC' if y < 0 else 'AD'}", None, None,
                                    "theographic"))
    for r in sorted(rows):
        db.execute("INSERT INTO crosswalk VALUES(?,?,?,?,?)", r)
    for k, v in {"license": "CC BY-SA 4.0", "source": "Theographic Bible Metadata",
                 "note": "Share-alike layer. Anything published from this file must stay CC BY-SA 4.0."}.items():
        db.execute("INSERT INTO meta VALUES(?,?)", (k, v))
    db.commit()
    db.execute("INSERT INTO meta VALUES('content_sha256', ?)", (content_hash(db),))
    db.commit()
    db.execute("VACUUM")
    db.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", default=str(ROOT / "sources"))
    ap.add_argument("--out", default=str(ROOT / "dist"))
    ap.add_argument("--no-theographic", action="store_true")
    a = ap.parse_args()
    src, out = pathlib.Path(a.sources), pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    lock = json.loads((ROOT / "sources.lock.json").read_text())
    for name, spec in lock.items():
        if a.no_theographic and name == "theographic":
            continue
        for rel, want in spec["files"].items():
            if sha256_file(src / name / rel) != want:
                sys.exit(f"{name}/{rel} does not match sources.lock.json; run build/fetch_sources.py")
    core = out / "acts-core.sqlite"
    unmatched, dropped = build_core(src, core)
    (out / "build-report.json").write_text(json.dumps(
        {"tipnr_refs_without_kjv_form": sorted(unmatched), "entities_not_named_in_kjv_acts": dropped}, indent=1) + "\n")
    print(f"core: {core}  sha256 {sha256_file(core)}  ({len(unmatched)} TIPNR refs with no KJV surface form)")
    if not a.no_theographic:
        th = out / "acts-theographic.sqlite"
        build_theographic(src, core, th)
        print(f"theographic layer: {th}  sha256 {sha256_file(th)}")


if __name__ == "__main__":
    main()
