"""Write an Obsidian vault of Acts: one note per person, place, group and other named thing,
one note per chapter, and a start page. Every [[link]] comes from the data and cites its verse.

    python build/make_vault.py [--out dist/vault]
Deterministic: same data file, same vault.
"""
import argparse, json, pathlib, re, shutil, sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from bibleobj import Bible  # noqa: E402

FOLDER = {"person": "People", "place": "Places", "group": "Groups", "speech": "Speeches"}
BAD = re.compile(r'[\\/:*?"<>|#^\[\]]')


def nice(ref):
    bk, c, v = ref.split(".")
    return f"{bk} {c}:{v}"


def order(ref):
    _, c, v = ref.split(".")
    return int(c), int(v)


def note_names(b):
    names, used = {}, set()
    for eid, label in b.db.execute("SELECT id, label FROM entities ORDER BY id"):
        n = BAD.sub("", label).strip()
        if n in used or n.lower().startswith("acts "):
            n = f"{n} ({eid})"
        used.add(n)
        names[eid] = n
    return names


def yaml_list(xs):
    return "[" + ", ".join(json.dumps(x, ensure_ascii=False) for x in xs) + "]"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "dist/vault"))
    out = pathlib.Path(ap.parse_args().out)
    if out.exists():
        shutil.rmtree(out)
    b = Bible.open(use_layer=False)
    names = note_names(b)
    L = lambda eid: f"[[{names[eid]}]]"
    kind = dict(b.db.execute("SELECT id, kind FROM entities"))
    text = dict(b.db.execute("SELECT ref, text FROM verses"))
    by_ref = defaultdict(list)
    for eid, ref, pos, surface in b.db.execute("SELECT entity_id, ref, pos, surface FROM mentions ORDER BY ref, pos"):
        by_ref[ref].append((pos, eid, surface))
    refs_of = defaultdict(set)
    for ref, xs in by_ref.items():
        for _, eid, _ in xs:
            refs_of[eid].add(ref)
    itin = b._q("SELECT * FROM itinerary ORDER BY person_id, seq")
    visitors = defaultdict(list)
    for s in itin:
        visitors[s["place_id"]].append(s)
    groups_of_place = defaultdict(list)
    for gid, parent in b.db.execute("SELECT id, group_of FROM entities WHERE group_of != '' ORDER BY id"):
        if parent in names:
            groups_of_place[parent].append(gid)

    files = {}
    for eid in sorted(names):
        e = b.entity(eid)
        k = e["kind"]
        refs = sorted(refs_of[eid], key=order)
        fm = ["---", f"id: {eid}", f"kind: {k}", f"aliases: {yaml_list(sorted(set(e['also_called']) - {names[eid]}))}",
              f"mentions: {len(refs)}", f"first_mention: {nice(refs[0])}" if refs else "first_mention:",
              f"tags: [acts/{k}]"]
        if k == "place" and e.get("sites"):
            s0 = e["sites"][0]
            fm.append(f"location: [{s0['lat']}, {s0['lon']}]")
        fm.append("---")
        body = [f"# {names[eid]}", ""]
        if e.get("brief"):
            body += [e["brief"], ""]
        if e.get("description") and e["description"] != e.get("brief") and not re.fullmatch(r"[\w-]+_\d+", e["description"]):
            body += [f"> {e['description']}", ""]
        if e.get("group_of") and e["group_of"] in names:
            body += [f"People of {L(e['group_of'])}.", ""]
        if k == "person":
            rel = e["relations"]
            if rel:
                body += ["## Family, as Acts states it", ""]
                body += [f"- {r['relation']} {L(r['other']['id'])}: {nice(r['ref'])}, \"{r['quote']}\""
                         + (f" ({r['note']})" if r["note"] else "") for r in rel]
                body.append("")
            mine = [s for s in itin if s["person_id"] == eid]
            if mine:
                body += ["## Travels, in the order Acts tells them", ""]
                leg = None
                for s in mine:
                    if s["leg"] != leg:
                        body += (["", f"**{s['leg']}**", ""] if leg else [f"**{s['leg']}**", ""])
                        leg = s["leg"]
                    body.append(f"{s['seq']}. {L(s['place_id'])}: {nice(s['ref'])}, \"{s['quote']}\"")
                body.append("")
            c = b.contemporaries(eid)
            if c["met_in_text"]:
                body += ["## Named in the same verse (New Testament times)", ""]
                body += [f"- {L(x['id'])}: " + ", ".join(nice(r) for r in x["shared_verses"][:8])
                         + (f" and {len(x['shared_verses']) - 8} more" if len(x["shared_verses"]) > 8 else "")
                         for x in c["met_in_text"]]
                body.append("")
            if c["named_alongside_but_not_contemporary"]:
                body += ["## Named alongside earlier figures", ""]
                body += [f"- {L(x['id'])}: " + ", ".join(nice(r) for r in x["shared_verses"][:5])
                         for x in c["named_alongside_but_not_contemporary"]]
                body.append("")
            places = defaultdict(set)
            for r in refs:
                for _, o, _ in by_ref[r]:
                    if kind[o] == "place":
                        places[o].add(r)
            if places:
                body += ["## Places named with them", ""]
                body += [f"- {L(p)}: " + ", ".join(nice(r) for r in sorted(rs, key=order)[:6])
                         for p, rs in sorted(places.items(), key=lambda t: (-len(t[1]), t[0]))]
                body.append("")
            body += ["## Born and died", "", "Acts gives no year for either. Any date would be a chronology's view, "
                     "kept in the separate share-alike layer.", ""]
        if k == "speech":
            sp = b.speeches()
            sp = next(x for x in sp if x["id"] == eid)
            body += [f"Given by {L(sp['speaker'])}, {nice(sp['start_ref'])} to {nice(sp['end_ref'])} ({sp['kind']}).", ""]
            rows = b._q('SELECT u.ref, u.start, u."end", v.text FROM utterances u JOIN verses v ON v.ref=u.ref '
                        "WHERE u.speech_id=?", eid)
            rows.sort(key=lambda r: (b._order(r["ref"]), r["start"]))
            body += ["## The words", ""] + [f"**{nice(r['ref'])}** {r['text'][r['start']:r['end']]}" for r in rows] + [""]
        typed = [x for x in b.edges(subject=eid) + b.edges(object=eid)
                 if x["type"] not in ("visited",) and not (k == "speech")]
        if typed:
            body += ["## Relationships", ""]
            for x in sorted(typed, key=lambda x: (x["type"], b._order(x["ref"]))):
                other = x["object"] if x["subject"] == eid else x["subject"]
                verb = x["type"].replace("_", " ") if x["subject"] == eid else f"{x['type'].replace('_', ' ')} (by)"
                body.append(f"- {verb} {L(other)}: {nice(x['ref'])}, \"{x['quote']}\"")
            body.append("")
        if k == "place":
            if e.get("sites"):
                body += ["## Where it was", ""]
                body += [f"- {s['label']}: {s['lat']}, {s['lon']} (confidence {s['confidence']}, {s['source']})"
                         for s in e["sites"]]
                body.append("")
            if visitors[eid]:
                body += ["## Who travelled here", ""]
                body += [f"- {L(s['person_id'])}, stop {s['seq']} ({s['leg']}): {nice(s['ref'])}, \"{s['quote']}\""
                         for s in visitors[eid]]
                body.append("")
            if groups_of_place[eid]:
                body += ["## Its people", ""] + [f"- {L(g)}" for g in groups_of_place[eid]] + [""]
        if True:  # every note lists the verses that name it
            hist = []
            for r in refs:
                others = sorted({o for _, o, _ in by_ref[r] if o != eid and kind[o] in ("person", "place")})
                hist.append(f"- **{nice(r)}** ([[Acts {order(r)[0]}]]) {text[r]}"
                            + (("  \n  With: " + ", ".join(L(o) for o in others)) if others and k != "person" else ""))
            body += ["## Every verse that names it" if k != "person" else "## Every verse that names them", ""] + hist + [""]
        body += ["---", f"Source: STEPBible TIPNR ({e['source']['tipnr_key'] or 'hand curation'}), KJV text. "
                 "See [[About this vault]]."]
        files[f"{FOLDER.get(k, 'Other')}/{names[eid]}.md"] = "\n".join(fm + body) + "\n"

    for c in range(1, 29):
        rows = b._q("SELECT ref, verse FROM verses WHERE book='Acts' AND chapter=? ORDER BY verse", c)
        named = defaultdict(list)
        for r in rows:
            for _, eid, _ in by_ref[r["ref"]]:
                if r["verse"] not in named[eid]:
                    named[eid].append(r["verse"])
        body = ["---", "tags: [acts/chapter]", "---", f"# Acts {c}", "",
                ("[[Acts " + str(c - 1) + "]] | " if c > 1 else "") + "[[Acts, start here]]"
                + (" | [[Acts " + str(c + 1) + "]]" if c < 28 else ""), ""]
        for kk, title in (("person", "People"), ("place", "Places"), ("group", "Groups")):
            xs = sorted((e for e in named if kind[e] == kk), key=lambda e: named[e][0])
            if xs:
                body += [f"## {title}", ""] + [f"- {L(e)}: verse " + ", ".join(map(str, named[e])) for e in xs] + [""]
        others = sorted((e for e in named if kind[e] not in ("person", "place", "group")), key=lambda e: named[e][0])
        if others:
            body += ["## Other names", ""] + [f"- {L(e)}: verse " + ", ".join(map(str, named[e])) for e in others] + [""]
        files[f"Chapters/Acts {c}.md"] = "\n".join(body) + "\n"

    counts = defaultdict(int)
    for eid in names:
        counts[kind[eid]] += 1
    top = sorted(names, key=lambda e: (-len(refs_of[e]), e))
    start = ["# Acts, start here", "", "Every person, place and group named in the King James text of Acts, "
             "linked by the verses that name them. Open the graph view to wander.", "",
             f"{counts['person']} people, {counts['place']} places, {counts['group']} groups and "
             f"{sum(v for k, v in counts.items() if k not in ('person', 'place', 'group'))} other names.", "",
             "## Chapters", "", " | ".join(f"[[Acts {c}]]" for c in range(1, 29)), "",
             "## Most named people", ""] + [f"- {L(e)} ({len(refs_of[e])} verses)" for e in top if kind[e] == "person"][:15] + [
             "", "## Most named places", ""] + [f"- {L(e)} ({len(refs_of[e])} verses)" for e in top if kind[e] == "place"][:15] + [
             "", "## Good walks through the graph", "",
             f"- {L('paul')}: his travels in order, then out to every place and companion.",
             f"- {L('antioch-of-syria')}: where the disciples were first called Christians.",
             f"- The four Jameses: {L('james-son-of-zebedee')}, {L('james-son-of-alphaeus')}, "
             f"{L('james-brother-of-jesus')}, {L('james-father-of-judas')}.",
             f"- {L('abraham')} to {L('joseph-son-of-jacob')} through the family links in Acts 7.", "",
             "See [[About this vault]]."]
    files["Acts, start here.md"] = "\n".join(start) + "\n"
    info = b.info()
    about = ["# About this vault", "", "Generated by build/make_vault.py from the Acts data file. Do not edit by hand; "
             "rebuild instead.", "", f"Data file content hash: `{info['content_sha256']}`", "",
             "## Rules", "", "- A link exists only where a verse names both things, or where a family link or travel stop "
             "is stated in the verse quoted beside it.", "- No dates. Acts states none; chronology views live in the "
             "separate share-alike layer and are not in this vault.", "", "## Sources", ""] + [
             f"- {s['name']}: {s['license']}" for s in info["sources"]] + [
             "", "Names, descriptions and references are adapted from STEPBible TIPNR (Tyndale House, Cambridge, "
             "CC BY 4.0). Changes are listed in the data file's corrections table. Coordinates from OpenBible.info "
             "(CC BY 4.0). KJV text is public domain outside the UK."]
    files["About this vault.md"] = "\n".join(about) + "\n"

    for rel, content in sorted(files.items()):
        p = out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    ob = out / ".obsidian"
    ob.mkdir(parents=True, exist_ok=True)
    rgb = lambda h: int(h.lstrip("#"), 16)
    (ob / "graph.json").write_text(json.dumps({
        "collapse-filter": False, "search": "", "showTags": False, "showAttachments": False, "hideUnresolved": True,
        "showOrphans": False, "collapse-color-groups": False,
        "colorGroups": [{"query": "path:People", "color": {"a": 1, "rgb": rgb("#2563eb")}},
                        {"query": "path:Places", "color": {"a": 1, "rgb": rgb("#059669")}},
                        {"query": "path:Groups", "color": {"a": 1, "rgb": rgb("#d97706")}},
                        {"query": "path:Chapters", "color": {"a": 1, "rgb": rgb("#9ca3af")}},
                        {"query": "path:Other", "color": {"a": 1, "rgb": rgb("#7c3aed")}}],
        "showArrow": False, "textFadeMultiplier": 0, "nodeSizeMultiplier": 1, "lineSizeMultiplier": 0.6,
        "centerStrength": 0.5, "repelStrength": 12, "linkStrength": 1, "linkDistance": 120}, indent=2) + "\n")
    (ob / "app.json").write_text(json.dumps({"alwaysUpdateLinks": True}, indent=2) + "\n")
    print(f"vault: {out} ({len(files)} notes)")


if __name__ == "__main__":
    main()
