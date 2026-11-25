"""Gate 3 helper: how many of Theographic's people and places in Acts have an id here.

Theographic (CC BY-SA 4.0) is read straight from the pinned source for this check only.
A Theographic entity counts as matched when one of our entities shares a name with it
and is mentioned in at least one of the same Acts verses.
"""
import json, sqlite3, sys, pathlib, collections

ROOT = pathlib.Path(__file__).resolve().parent.parent


def norm(s):
    return (s or "").lower().replace("’", "'").strip()


def compare(core=ROOT / "dist/acts-core.sqlite", src=ROOT / "sources/theographic/json"):
    people = {p["id"]: p["fields"] for p in json.loads((src / "people.json").read_text(encoding="utf-8"))}
    places = {p["id"]: p["fields"] for p in json.loads((src / "places.json").read_text(encoding="utf-8"))}
    refs = collections.defaultdict(set)
    for v in json.loads((src / "verses.json").read_text(encoding="utf-8")):
        f = v["fields"]
        if f["osisRef"].startswith("Acts."):
            for k in ("people", "places"):
                for tid in f.get(k, []):
                    refs[tid].add(f["osisRef"])
    db = sqlite3.connect(core)
    ours = collections.defaultdict(set)
    for eid, ref in db.execute("SELECT entity_id, ref FROM mentions"):
        ours[eid].add(ref)
    names = collections.defaultdict(set)
    for eid, form in db.execute("SELECT entity_id, form FROM aliases"):
        names[eid].add(norm(form))
    for eid, name, label in db.execute("SELECT id, name, label FROM entities"):
        names[eid] |= {norm(name), norm(label)}
    by_ref = collections.defaultdict(set)
    for eid, rs in ours.items():
        for r in rs:
            by_ref[r].add(eid)
    out = {"person": [0, 0, []], "place": [0, 0, []]}
    for tid, rs in sorted(refs.items()):
        if tid in people:
            f, kind = people[tid], "person"
            tn = {norm(f.get("name")), norm(f.get("displayTitle"))} | {norm(x) for x in (f.get("alsoCalled") or "").split(",")}
            label = f.get("displayTitle") or f.get("name")
        elif tid in places:
            f, kind = places[tid], "place"
            tn = {norm(f.get("kjvName")), norm(f.get("esvName")), norm(f.get("displayTitle"))}
            label = f.get("displayTitle")
        else:
            continue
        tn.discard("")
        out[kind][0] += 1
        cands = set().union(*(by_ref[r] for r in rs)) if rs else set()
        hit = [e for e in cands if names[e] & tn]
        if hit:
            out[kind][1] += 1
        else:
            out[kind][2].append((label, sorted(rs)[:3], sorted(cands)[:6]))
    return out


if __name__ == "__main__":
    o = compare()
    tot = sum(v[0] for v in o.values()); hit = sum(v[1] for v in o.values())
    for k, (t, h, miss) in o.items():
        print(f"{k}: {h}/{t} matched ({100*h/t:.1f}%)")
        for m in miss:
            print("   missing:", m)
    print(f"overall: {hit}/{tot} = {100*hit/tot:.1f}%")
