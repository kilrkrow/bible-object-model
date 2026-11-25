"""Words of Jesus (red letter) from a public-domain KJV OSIS file, as character spans on our verse text."""
import difflib, re

TOK = re.compile(r"<[^>]+>|[^<]+")
ATTR = re.compile(r'(\w+)="([^"]*)"')


def parse_osis(path, books):
    """-> {ref: (plain_text, [(start, end)])} for verses whose book is in `books`."""
    s = open(path, encoding="utf-8").read()
    out, cur, buf, spans, qstart, in_q, skip = {}, None, [], [], None, False, 0
    for t in TOK.findall(s):
        if t.startswith("<"):
            name = re.match(r"</?\s*([\w:]+)", t).group(1) if re.match(r"</?\s*([\w:]+)", t) else ""
            a = dict(ATTR.findall(t))
            if name in ("title", "note") and not t.endswith("/>"):
                skip += -1 if t.startswith("</") else 1
            elif name == "verse" and "sID" in a:
                ref = a.get("osisID", "").split()[0]
                cur = ref if ref.split(".")[0] in books else None
                buf, spans = [], []
                if in_q and cur:
                    qstart = 0
            elif name == "verse" and "eID" in a:
                if cur:
                    if in_q and qstart is not None:
                        spans.append((qstart, len("".join(buf))))
                        qstart = 0
                    out[cur] = ("".join(buf), spans)
                cur = None
            elif name == "q":
                if "sID" in a and a.get("who") == "Jesus":
                    in_q, qstart = True, len("".join(buf))
                elif "eID" in a and in_q:
                    if cur is not None:
                        spans.append((qstart, len("".join(buf))))
                    in_q, qstart = False, None
            continue
        if cur and not skip:
            buf.append(t)
    clean = {}
    for ref, (txt, sp) in out.items():
        # collapse whitespace while carrying span offsets across
        mapping, res = [], []
        prev_space = True
        for i, ch in enumerate(txt):
            if ch.isspace():
                if not prev_space:
                    res.append(" "); mapping.append(i)
                prev_space = True
            else:
                res.append(ch); mapping.append(i); prev_space = False
        while res and res[-1] == " ":
            res.pop(); mapping.pop()
        new = "".join(res)
        def conv(off):
            for j, m in enumerate(mapping):
                if m >= off:
                    return j
            return len(new)
        clean[ref] = (new, [(conv(a), conv(b)) for a, b in sp if conv(b) > conv(a)])
    return clean


def carry_spans(src_text, spans, dst_text):
    """Move character spans from one wording of a verse to another (they differ only in small ways)."""
    if src_text == dst_text:
        return spans, 1.0
    sm = difflib.SequenceMatcher(None, src_text, dst_text, autojunk=False)
    blocks = sm.get_matching_blocks()

    def conv(off):
        for a, b, n in blocks:
            if a <= off <= a + n:
                return b + (off - a)
        best = min(blocks, key=lambda blk: abs(blk[0] - off))
        return min(len(dst_text), best[1])
    return [(conv(a), conv(b)) for a, b in spans], sm.ratio()
