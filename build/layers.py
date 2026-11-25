"""Second build stage: the whole KJV text, typed edges, KJV-to-Greek lemma alignment and speakers.

Called from build.build_core on the open core database, before the content hash.

Layers written here
  verses/books/chapters  every book of the KJV (Acts was already loaded by build_core)
  edge_types, edges      the typed relationship graph; `relations` and `itinerary` become views over it
  tokens                 KJV words of Acts and John with character spans
  greek_words, lexicon   the Greek (Textus Receptus readings) of Acts and John from STEPBible TAGNT
  alignments             each KJV content word linked to the Greek word it translates (machine-drafted)
  speeches, utterances   who is speaking which characters of which verse, with a basis for each span
"""
import json, math, re, sys
from collections import Counter, defaultdict

from redletter import parse_osis, carry_spans

TOKEN_BOOKS = ("John", "Acts")
WORD_RE = re.compile(r"[A-Za-z]+(?:['’-][A-Za-z]+)*")

# file name in aruljohn/Bible-kjv -> (OSIS code, testament)
BOOKS = [
    ("Genesis", "Gen"), ("Exodus", "Exod"), ("Leviticus", "Lev"), ("Numbers", "Num"), ("Deuteronomy", "Deut"),
    ("Joshua", "Josh"), ("Judges", "Judg"), ("Ruth", "Ruth"), ("1Samuel", "1Sam"), ("2Samuel", "2Sam"),
    ("1Kings", "1Kgs"), ("2Kings", "2Kgs"), ("1Chronicles", "1Chr"), ("2Chronicles", "2Chr"), ("Ezra", "Ezra"),
    ("Nehemiah", "Neh"), ("Esther", "Esth"), ("Job", "Job"), ("Psalms", "Ps"), ("Proverbs", "Prov"),
    ("Ecclesiastes", "Eccl"), ("SongofSolomon", "Song"), ("Isaiah", "Isa"), ("Jeremiah", "Jer"),
    ("Lamentations", "Lam"), ("Ezekiel", "Ezek"), ("Daniel", "Dan"), ("Hosea", "Hos"), ("Joel", "Joel"),
    ("Amos", "Amos"), ("Obadiah", "Obad"), ("Jonah", "Jonah"), ("Micah", "Mic"), ("Nahum", "Nah"),
    ("Habakkuk", "Hab"), ("Zephaniah", "Zeph"), ("Haggai", "Hag"), ("Zechariah", "Zech"), ("Malachi", "Mal"),
    ("Matthew", "Matt"), ("Mark", "Mark"), ("Luke", "Luke"), ("John", "John"), ("Acts", "Acts"),
    ("Romans", "Rom"), ("1Corinthians", "1Cor"), ("2Corinthians", "2Cor"), ("Galatians", "Gal"),
    ("Ephesians", "Eph"), ("Philippians", "Phil"), ("Colossians", "Col"), ("1Thessalonians", "1Thess"),
    ("2Thessalonians", "2Thess"), ("1Timothy", "1Tim"), ("2Timothy", "2Tim"), ("Titus", "Titus"),
    ("Philemon", "Phlm"), ("Hebrews", "Heb"), ("James", "Jas"), ("1Peter", "1Pet"), ("2Peter", "2Pet"),
    ("1John", "1John"), ("2John", "2John"), ("3John", "3John"), ("Jude", "Jude"), ("Revelation", "Rev"),
]
TAGNT_BOOK = dict(zip("Mat Mrk Luk Jhn Act Rom 1Co 2Co Gal Eph Php Col 1Th 2Th 1Ti 2Ti Tit Phm Heb Jas 1Pe 2Pe 1Jn 2Jn 3Jn Jud Rev".split(),
                      [o for _, o in BOOKS[39:]]))

STOP = set("""a an and are as at be been but by did do doth for from had hath have he her hers him his i if in into is it its
me mine my no nor not of on or our ours shall she so than that the thee their them then there these they thine this those
thou thy to unto upon us was we were what when which who whom whose will with ye yet you your o also even art wast
should would might may must let""".split())


def stem(w):
    w = w.lower().replace("’", "'")
    w = re.sub(r"'s$", "", w)
    for suf in ("edst", "eth", "est", "ing", "ed", "es", "s", "e"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: -len(suf)]
    return w


def osis_ref(book, c, v):
    return f"{book}.{c}.{v}"


def order_key(ref):
    b, c, v = ref.split(".")
    return [o for _, o in BOOKS].index(b), int(c), int(v)


# ----------------------------------------------------------------------------- text
def load_all_kjv(src):
    out = []
    for fname, osis in BOOKS:
        d = json.loads((src / "kjv" / f"{fname}.json").read_text(encoding="utf-8"))
        for ch in d["chapters"]:
            for v in ch["verses"]:
                out.append((osis_ref(osis, int(ch["chapter"]), int(v["verse"])), osis, int(ch["chapter"]),
                            int(v["verse"]), v["text"]))
    return out


def insert_other_books(db, allv):
    by_book = defaultdict(list)
    for r in allv:
        by_book[r[1]].append(r)
    for i, (fname, osis) in enumerate(BOOKS):
        if osis == "Acts":
            continue
        chap = defaultdict(lambda: [0, 0])
        tw = tc = 0
        for ref, b, c, v, text in by_book[osis]:
            w = len(WORD_RE.findall(text))
            db.execute("INSERT INTO verses VALUES(?,?,?,?,?,?,?,?)", (ref, "KJV", osis, c, v, text, w, len(text)))
            chap[c][0] += 1; chap[c][1] += w; tw += w; tc += len(text)
        for c in sorted(chap):
            db.execute("INSERT INTO chapters VALUES(?,?,?,?,?)", (osis, "KJV", c, chap[c][0], chap[c][1]))
        db.execute("INSERT INTO books VALUES(?,?,?,?,?,?,?,?)",
                   (osis, "KJV", fname, "OT" if i < 39 else "NT", len(chap), len(by_book[osis]), tw, tc))


# ------------------------------------------------------------------------- Greek NT
VARIANT = re.compile(r"(\S+) \([Tt]=([^)]+)\) (.*?) - ([GH]\d{4}[A-Za-z]?)=(\S+) in: (\S+)")


def load_tagnt(src):
    """-> {ref: [word dict]} with the Textus Receptus reading (the KJV's Greek base) for every NT verse."""
    verses = defaultdict(list)
    folder = src / "stepbible-greek" / "Translators Amalgamated OT+NT"
    for f in sorted(folder.glob("TAGNT*.txt")):
        for line in f.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^([1-3A-Z][a-z0-9]{2})\.(\d+)\.(\d+)\S*#(\d+)=(\S+)\t", line)
            if not m:
                continue
            col = line.split("\t")
            book = TAGNT_BOOK.get(m.group(1))
            if not book:
                continue
            ref = osis_ref(book, int(m.group(2)), int(m.group(3)))
            eds = col[5].split("+") if len(col) > 5 else []
            word, translit = re.match(r"^(\S+)(?: \(([^)]*)\))?", col[1]).groups()
            dstrong, _, morph = col[3].partition("=")
            lemma, _, gloss = col[4].partition("=")
            english = col[2]
            if "TR" not in eds:
                var = [v for v in VARIANT.finditer(col[6] if len(col) > 6 else "") if "TR" in v.group(6).split("+")]
                if not var:
                    continue
                word, translit, english, dstrong, morph = var[0].group(1, 2, 3, 4, 5)
                lemma = gloss = ""
            base = re.match(r"[GH]\d{4}", dstrong)
            if not base:
                continue
            verses[ref].append({"word": word.strip("·,.;:¶"), "translit": translit or "", "strong": base.group(0),
                                "ext": dstrong, "morph": morph, "lemma": lemma, "gloss": gloss, "english": english})
    return verses


def load_lexicon(src):
    lex = {}
    folder = src / "stepbible-greek" / "Lexicons"
    for f in sorted(folder.glob("TBESG*.txt")):
        for line in f.read_text(encoding="utf-8").splitlines():
            col = line.split("\t")
            if len(col) < 7 or not re.match(r"^G\d{4}[A-Za-z]?$", col[0]):
                continue
            base = col[0][:5]
            if base not in lex or col[0] == base:
                lex[base] = {"lemma": col[3], "translit": col[4], "gloss": col[6]}
    return lex


# ------------------------------------------------------------------------ alignment
def align(kjv_by_ref, greek, iters=6, alpha=4.0):
    """IBM Model 1 with a diagonal (word-order) prior over the whole NT, nudged by STEPBible's English glosses.

    Returns {ref: {token_idx: (greek_idx, score, how)}} for the verses of TOKEN_BOOKS.
    Only content words are aligned on both sides: KJV function words (STOP) and Greek words whose STEPBible
    English gloss is only function words (articles, pronouns like με "me") are left out on purpose, otherwise
    they soak up probability and steal alignments. The diagonal prior settles repeats: in John 21:15 the first
    "love" is ἀγαπᾷς and the second is φιλῶ because of where each sits in the verse.
    """
    pairs = []
    for ref, gw in sorted(greek.items(), key=lambda kv: order_key(kv[0])):
        text = kjv_by_ref.get(ref)
        if text is None or not gw:
            continue
        toks = [m.group(0) for m in WORD_RE.finditer(text)]
        es = [(i, stem(w), i / max(1, len(toks) - 1)) for i, w in enumerate(toks) if w.lower() not in STOP]
        gs = []
        for j, g in enumerate(gw):
            hint = {stem(x) for x in WORD_RE.findall(g["english"]) if x.lower() not in STOP}
            if hint:
                gs.append((j, g["strong"], hint, j / max(1, len(gw) - 1)))
        if es and gs:
            pairs.append((ref, es, gs))

    def weights(e, pe, gs, t, first):
        return [(1.0 if first else t[(e, g)]) * (8.0 if e in hint else 1.0) * math.exp(-alpha * abs(pe - pg))
                for _, g, hint, pg in gs]

    t = None
    for it in range(iters):
        count = defaultdict(float)
        total = defaultdict(float)
        for ref, es, gs in pairs:
            for _, e, pe in es:
                ws = weights(e, pe, gs, t, it == 0)
                z = sum(ws) + 1e-12
                for w, (_, g, _, _) in zip(ws, gs):
                    count[(e, g)] += w / z
                    total[g] += w / z
        t = defaultdict(lambda: 1e-6, {k: v / total[k[1]] for k, v in count.items()})
    out = {}
    for ref, es, gs in pairs:
        if ref.split(".")[0] not in TOKEN_BOOKS:
            continue
        res = {}
        for i, e, pe in es:
            ws = weights(e, pe, gs, t, False)
            k = max(range(len(gs)), key=lambda k: (ws[k], -k))
            j, g, hint, _ = gs[k]
            p, h = t[(e, g)], e in hint
            if h or p >= 0.1:
                res[i] = (j, round(min(1.0, p * (2.0 if h else 1.0)), 4), "model1+gloss" if h else "model1")
        out[ref] = res
    return out


# ------------------------------------------------------------------------- speakers
INTRO = re.compile(r"(?<!\bhad )(?<!\bthus )(?<!\bwhich he )(?<!\bwhich I )\b(?:answered and said|said|saith|saying|answered|cried|spake|asked|sayest)\b"
                   r"(?: unto (?:him|her|them|me|us|you|thee|[A-Z][a-z]+)(?: [a-z]+)?)?,\s+")
PRON = {"he", "she", "they", "it", "one", "another", "others", "some", "we", "i", "ye"}


def name_index(db, extra_forms):
    """Name forms that speakers go by: every surface the mention layer found in Acts, plus the new John names.

    Aliases alone are too loose (TIPNR lists "God" among Jacob's forms). When a surface belongs to several
    people, the one it names in at least 80% of Acts mentions wins (KJV "Jesus" is Joshua only in Acts 7:45).
    """
    by_form = defaultdict(Counter)
    for eid, surface, n in db.execute("SELECT m.entity_id, m.surface, count(*) FROM mentions m JOIN entities e "
                                      "ON e.id=m.entity_id WHERE e.kind IN ('person','group') GROUP BY 1, 2"):
        if surface[:1].isupper():  # proper names only; the mention layer also resolves a few pronouns
            by_form[re.sub(r"[’']s$", "", surface)][eid] += n
    for eid, forms in extra_forms.items():
        for f in forms:
            by_form[f][eid] += 1
    idx = {}
    for form, c in by_form.items():
        (top, n), total = c.most_common(1)[0], sum(c.values())
        idx[form] = {top} if n >= 0.8 * total else set(c)
    return idx


def resolve_speaker(before, idx):
    """The speaker is the last name in the clause before the speech verb ("the mother of Jesus" is not Jesus)."""
    clause = re.split(r"[.;:?!]|\bthat\b", before)[-1]
    best = None
    for form, ids in idx.items():
        for m in re.finditer(r"\b" + re.escape(form) + r"\b", clause):
            pre = clause[:m.start()]
            if re.search(r"\b(?:of|to|unto|upon|with|by|in|for)\s+(?:the\s+)?(?:[A-Z]\w*\s+)?$", pre):
                continue  # "the mother of Jesus", "in the name of the LORD Jesus"
            if re.search(r"\b(?:whose|whom|which)\s+(?:\w+\s+)?$", pre):
                continue  # inside a relative clause: "his kinsman whose ear Peter cut off"
            if re.match(r"[’']", clause[m.end():m.end() + 1]):
                continue  # "Jesus’ breast", "Paul’s girdle"
            if re.search(r"\b(?:\w+ed|\w+eth|saw|told|met|bade|took|sent|besought|answered|asked|called)\s+(?:the\s+)?$", pre):
                continue  # object of a verb: "the eunuch answered Philip", "they glorified the Lord"
            if best is None or m.end() > best[0] or (m.end() == best[0] and len(form) > len(best[1])):
                best = (m.end(), form, ids)
    if best:
        ids = best[2]
        if len(ids) == 1:
            return next(iter(ids)), None
        return None, "ambiguous: " + "|".join(sorted(ids))
    words = clause.strip().split()
    if any(w.lower().strip(",") in PRON for w in words[-5:]):
        return None, "pronoun"
    phrase = " ".join(words[-8:]).strip(" ,")
    return None, ("unnamed: " + phrase) if phrase else "no name in the verse"


def draft_utterances(vtext, refs, idx, taken):
    """Within-verse direct speech after an intro like 'X said unto them,'. Never crosses a verse."""
    out = []
    names_re = "|".join(re.escape(f) for f in sorted(idx, key=len, reverse=True) if f[:1].isupper())
    for ref in refs:
        text = vtext[ref]
        ms = list(INTRO.finditer(text))
        for k, m in enumerate(ms):
            start = m.end()
            end = ms[k + 1].start() if k + 1 < len(ms) else len(text)
            # end at the narrator's next sentence if one obviously starts ("And he ...")
            nxt = re.search(r"\. (?:And|Then|But|So) (?:he|she|they|when|" + names_re + r")\b", text[start:end])
            if nxt:
                end = start + nxt.start() + 1
            # back the end up to the last sentence mark before the next intro's narrator words
            if k + 1 < len(ms):
                seg = text[start:end]
                cut = max(seg.rfind(". "), seg.rfind("? "), seg.rfind("! "))
                end = start + cut + 1 if cut > 0 else end
            if end - start < 3:
                continue
            if any(a < end and start < b for a, b in taken.get(ref, [])):
                continue
            who, why = resolve_speaker(text[:m.start()], idx)
            out.append((ref, start, end, who, why))
    return out


# ---------------------------------------------------------------------------- build
SCHEMA = """
CREATE TABLE edge_types(type TEXT PRIMARY KEY, inverse TEXT, accessor TEXT, inverse_accessor TEXT,
  subject_kinds TEXT, object_kinds TEXT, description TEXT);
CREATE TABLE edges(id INTEGER PRIMARY KEY, subject TEXT NOT NULL, type TEXT NOT NULL, object TEXT NOT NULL,
  ref TEXT NOT NULL, start INT NOT NULL, "end" INT NOT NULL, quote TEXT NOT NULL, seq INT, attrs TEXT,
  basis TEXT NOT NULL, source TEXT NOT NULL, note TEXT);
CREATE INDEX edges_s ON edges(subject, type);
CREATE INDEX edges_o ON edges(object, type);
CREATE TABLE tokens(ref TEXT, idx INT, start INT, "end" INT, text TEXT, stem TEXT, PRIMARY KEY(ref, idx));
CREATE TABLE greek_words(ref TEXT, idx INT, word TEXT, translit TEXT, strong TEXT, ext_strong TEXT, morph TEXT,
  english TEXT, PRIMARY KEY(ref, idx));
CREATE TABLE lexicon(strong TEXT PRIMARY KEY, language TEXT, lemma TEXT, translit TEXT, gloss TEXT, source TEXT);
CREATE TABLE alignments(ref TEXT, token_idx INT, greek_idx INT, score REAL, method TEXT, PRIMARY KEY(ref, token_idx));
CREATE TABLE speeches(id TEXT PRIMARY KEY, speaker TEXT, kind TEXT, title TEXT, start_ref TEXT, end_ref TEXT,
  basis TEXT, source TEXT);
CREATE TABLE utterances(ref TEXT, start INT, "end" INT, speaker TEXT, basis TEXT, speech_id TEXT, note TEXT,
  source TEXT, PRIMARY KEY(ref, start));
CREATE INDEX utt_speaker ON utterances(speaker);
CREATE INDEX greek_strong ON greek_words(strong);
"""
FAMILY = ("parent_of", "descendant_of", "spouse_of", "sibling_of", "kin_of")


def span_of(text, quote):
    i = text.find(quote)
    return (i, i + len(quote)) if i >= 0 else (None, None)


def build(db, src, root, read_csv):
    problems = []
    db.executescript(SCHEMA)
    allv = load_all_kjv(src)
    insert_other_books(db, allv)
    vtext = {r[0]: r[4] for r in allv}
    order = {r[0]: n for n, r in enumerate(allv)}
    ents = {r[0]: r[1] for r in db.execute("SELECT id, kind FROM entities")}

    # --- extra entities (speakers in John, recipients of Paul's letters)
    extra_forms = {}
    for r in read_csv(root / "curation/entities_more.csv"):
        if r["id"] in ents:
            problems.append(f"entities_more: {r['id']} already exists")
            continue
        db.execute("INSERT INTO entities VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                   (r["id"], r["kind"], r["label"], r["label"], r["brief"], r["brief"], "", "NT", "", "", "", "curation"))
        for f in r["forms"].split("|"):
            db.execute("INSERT OR IGNORE INTO aliases VALUES(?,?)", (r["id"], f))
        extra_forms[r["id"]] = r["forms"].split("|")
        ents[r["id"]] = r["kind"]
        if r["kind"] == "person":
            for prop in ("born", "died"):
                db.execute("INSERT INTO claims VALUES(?,?,?,?,?,?)",
                           (r["id"], prop, "not-stated", 1, None, "The KJV text gives no year for this."))

    # --- edge types: an open list, extended by adding a row to curation/edge_types.csv
    types = {r["type"]: r for r in read_csv(root / "curation/edge_types.csv")}
    for t, r in sorted(types.items()):
        db.execute("INSERT INTO edge_types VALUES(?,?,?,?,?,?,?)",
                   (t, r["inverse"], r["accessor"], r["inverse_accessor"], r["subject_kinds"], r["object_kinds"],
                    r["description"]))

    edges = []

    def add_edge(s, t, o, ref, quote, basis, source, note="", seq=None, attrs=None):
        if t not in types:
            problems.append(f"edge type {t!r} is not in curation/edge_types.csv")
        for k in (s, o):
            if k not in ents:
                problems.append(f"edge {s} {t} {o}: unknown id {k}")
        text = vtext.get(ref)
        if text is None:
            problems.append(f"edge {s} {t} {o}: no verse {ref}")
            return
        a, b = span_of(text, quote)
        if a is None:
            problems.append(f"edge {s} {t} {o}: quote not in {ref}: {quote!r}")
            return
        edges.append((s, t, o, ref, a, b, quote, seq, json.dumps(attrs, sort_keys=True) if attrs else None,
                      basis, source, note or ""))

    # existing family links and Paul's itinerary move into the edge table
    for s, p, o, ref, q, note, source in db.execute("SELECT * FROM relations ORDER BY subject, predicate, object, ref"):
        add_edge(s, p, o, ref, q, "stated in the verse", source, note)
    for pid, seq, place, ref, leg, q, source in db.execute("SELECT * FROM itinerary ORDER BY person_id, seq"):
        add_edge(pid, "visited", place, ref, q, "stated in the verse", source, seq=seq, attrs={"leg": leg})
    for r in sorted(read_csv(root / "curation/edges.csv"), key=lambda r: (r["subject"], r["type"], r["object"], r["ref"])):
        add_edge(r["subject"], r["type"], r["object"], r["ref"], r["quote"], "stated in the verse", "curation", r["note"])

    # --- words of Jesus (red letter) in Acts and John
    rl = parse_osis(src / "kjv-redletter" / "eng-kjv.osis.xml", set(TOKEN_BOOKS))
    utter = {}
    taken = defaultdict(list)
    for ref, (otext, spans) in sorted(rl.items(), key=lambda kv: order[kv[0]]):
        if not spans or ref not in vtext:
            continue
        moved, ratio = carry_spans(otext, spans, vtext[ref])
        for a, b in moved:
            seg = vtext[ref][a:b]
            a2 = a + (len(seg) - len(seg.lstrip()))
            b2 = b - (len(seg) - len(seg.rstrip()))
            if b2 - a2 < 2:
                continue
            utter[(ref, a2)] = [b2, "jesus", "red-letter edition", None,
                                "" if ratio == 1.0 else f"span carried from a wording {ratio:.3f} similar", "kjv-redletter"]
            taken[ref].append((a2, b2))

    # --- curated speeches (checked by hand: who speaks, where it starts and ends)
    for r in read_csv(root / "curation/speeches.csv"):
        sid, who = r["id"], r["speaker"]
        if who not in ents:
            problems.append(f"speech {sid}: unknown speaker {who}")
            continue
        refs = [x for x in vtext if x.split(".")[0] == r["start_ref"].split(".")[0]
                and order[r["start_ref"]] <= order[x] <= order[r["end_ref"]]]
        refs.sort(key=lambda x: order[x])
        db.execute("INSERT INTO entities VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                   (sid, "speech", r["title"], r["title"], f"{r['kind']} in {r['start_ref']} to {r['end_ref']}",
                    r["kind"], "", "NT", "", "", "", "curation"))
        ents[sid] = "speech"
        db.execute("INSERT INTO speeches VALUES(?,?,?,?,?,?,?,?)",
                   (sid, who, r["kind"], r["title"], r["start_ref"], r["end_ref"], "checked by hand", "curation"))
        first_quote = None
        for n, ref in enumerate(refs):
            text = vtext[ref]
            if who == "jesus":
                spans = [(a, v[0]) for (rr, a), v in utter.items() if rr == ref and v[1] == "jesus"]
                for a, b in spans:
                    utter[(ref, a)][3] = sid
                if spans and first_quote is None:
                    a, b = min(spans)
                    first_quote = (ref, text[a:b])
                continue
            start = 0
            if n == 0 and r["start_after"]:
                i = text.find(r["start_after"])
                if i < 0:
                    problems.append(f"speech {sid}: '{r['start_after']}' not in {ref}")
                    break
                start = i + len(r["start_after"])
                start += len(text[start:]) - len(text[start:].lstrip(" ,:"))
            end = len(text)
            utter[(ref, start)] = [end, who, "curated speech", sid, "", "curation"]
            taken[ref].append((start, end))
            if first_quote is None:
                first_quote = (ref, text[start:end])
        if first_quote:
            ref, q = first_quote
            q = q if len(q) <= 90 else q[:90].rsplit(" ", 1)[0]
            add_edge(who, r["type"], sid, ref, q, "speech boundaries checked by hand", "curation")

    # --- drafted speakers for the rest of the direct speech in Acts and John
    idx = name_index(db, extra_forms)
    refs = sorted((x for x in vtext if x.split(".")[0] in TOKEN_BOOKS), key=lambda x: order[x])
    for ref, a, b, who, why in draft_utterances(vtext, refs, idx, taken):
        seg = vtext[ref][a:b]
        b = a + len(seg.rstrip())
        if (ref, a) not in utter:
            utter[(ref, a)] = [b, who, "drafted", None, why or "", "speech-intro pattern"]
    for (ref, a), (b, who, basis, sid, note, source) in sorted(utter.items(), key=lambda kv: (order[kv[0][0]], kv[0][1])):
        db.execute("INSERT INTO utterances VALUES(?,?,?,?,?,?,?,?)", (ref, a, b, who, basis, sid, note, source))

    for e in sorted(edges, key=lambda e: (e[1], e[0], e[2], order[e[3]], e[4])):
        db.execute('INSERT INTO edges(subject,type,object,ref,start,"end",quote,seq,attrs,basis,source,note) '
                   "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", e)
    db.executescript(f"""
        DROP TABLE relations; DROP TABLE itinerary;
        CREATE VIEW relations AS SELECT subject, type AS predicate, object, ref, quote, note, source FROM edges
          WHERE type IN {FAMILY!r};
        CREATE VIEW itinerary AS SELECT subject AS person_id, seq, object AS place_id, ref,
          json_extract(attrs, '$.leg') AS leg, quote, source FROM edges WHERE type='visited';
    """)

    # --- tokens, Greek, lexicon, alignment for Acts and John
    greek = load_tagnt(src)
    lex = load_lexicon(src)
    al = align(vtext, greek)
    used = set()
    for ref in refs:
        for i, m in enumerate(WORD_RE.finditer(vtext[ref])):
            db.execute("INSERT INTO tokens VALUES(?,?,?,?,?,?)", (ref, i, m.start(), m.end(), m.group(0), stem(m.group(0))))
        for j, g in enumerate(greek.get(ref, [])):
            db.execute("INSERT INTO greek_words VALUES(?,?,?,?,?,?,?,?)",
                       (ref, j, g["word"], g["translit"], g["strong"], g["ext"], g["morph"], g["english"]))
            used.add(g["strong"])
        for ti, (gj, score, how) in sorted(al.get(ref, {}).items()):
            db.execute("INSERT INTO alignments VALUES(?,?,?,?,?)", (ref, ti, gj, score, how))
    first_lemma = {}
    for gw in greek.values():
        for g in gw:
            if g["lemma"]:
                first_lemma.setdefault(g["strong"], (g["lemma"], g["gloss"]))
    for s in sorted(used):
        L = lex.get(s)
        if L:
            db.execute("INSERT INTO lexicon VALUES(?,?,?,?,?,?)", (s, "Greek", L["lemma"], L["translit"], L["gloss"], "TBESG"))
        elif s in first_lemma:
            db.execute("INSERT INTO lexicon VALUES(?,?,?,?,?,?)", (s, "Greek", first_lemma[s][0], "", first_lemma[s][1], "TAGNT"))
    stats = {
        "tokens": db.execute("SELECT count(*) FROM tokens").fetchone()[0],
        "content_tokens": sum(1 for ref in refs for w in WORD_RE.findall(vtext[ref]) if w.lower() not in STOP),
        "aligned": db.execute("SELECT count(*) FROM alignments").fetchone()[0],
        "utterances": dict(db.execute("SELECT basis, count(*) FROM utterances GROUP BY basis").fetchall()),
        "edges": dict(db.execute("SELECT type, count(*) FROM edges GROUP BY type").fetchall()),
    }
    return problems, stats
