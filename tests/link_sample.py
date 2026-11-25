"""Gate 5 helper: draw a fixed random sample of 20 links (seed 20261124) for a human check.

Stratified so every kind of link is looked at: 8 name mentions, 6 itinerary stops, 6 family links.
Writes reports/link-sample.md with the verse text beside each link; verdicts are filled in by hand.
"""
import pathlib, random, sqlite3, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SEED = 20261124


def draw(db_path=ROOT / "dist/acts-core.sqlite"):
    db = sqlite3.connect(db_path)
    rnd = random.Random(SEED)
    lab = dict(db.execute("SELECT id, label FROM entities"))
    text = dict(db.execute("SELECT ref, text FROM verses"))
    men = db.execute("SELECT entity_id, ref, pos, surface FROM mentions ORDER BY entity_id, ref, pos").fetchall()
    iti = db.execute("SELECT person_id, seq, place_id, ref, quote FROM itinerary ORDER BY person_id, seq").fetchall()
    rel = db.execute("SELECT subject, predicate, object, ref, quote FROM relations ORDER BY subject, predicate, object").fetchall()
    out = []
    for e, ref, pos, s in rnd.sample(men, 8):
        out.append({"kind": "mention", "claim": f"'{s}' in {ref} is {lab[e]} ({e})", "ref": ref, "text": text[ref],
                    "auto_ok": s in text[ref]})
    for p, seq, pl, ref, q in rnd.sample(iti, 6):
        out.append({"kind": "itinerary", "claim": f"{lab[p]} stop {seq}: {lab[pl]}  (\"{q}\")", "ref": ref,
                    "text": text[ref], "auto_ok": q in text[ref]})
    for s, p, o, ref, q in rnd.sample(rel, 6):
        out.append({"kind": "family", "claim": f"{lab[s]} {p.replace('_', ' ')} {lab[o]}  (\"{q}\")", "ref": ref,
                    "text": text[ref], "auto_ok": q in text[ref]})
    return out


if __name__ == "__main__":
    for i, x in enumerate(draw(), 1):
        print(i, x["kind"], x["auto_ok"], "|", x["claim"], "|", x["ref"], "|", x["text"])
