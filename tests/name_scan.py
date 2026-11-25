"""Gate 3 helper: find every capitalised name in the KJV text of Acts and check it has an id.

A token counts as a name candidate when it is capitalised and its lower-case form never
occurs anywhere in KJV Acts (so sentence-initial 'And', 'Then' drop out by themselves).
Divine titles and ordinary words that only happen to start a sentence are listed in
NOT_NAMES with the reason. A candidate is covered when a mention in that same verse
has a surface form containing it.
"""
import re, sqlite3, sys, collections

NOT_NAMES = {
    # divine titles: modelled later as the Godhead, not as Acts people
    "God": "divine title", "God’s": "divine title", "Godhead": "divine title", "Ghost": "divine title (Holy Ghost)",
    "Saviour": "title of Jesus", "Prince": "title of Jesus (Prince of life)", "Highest": "divine title",
    # ordinary words that only ever occur capitalised at the start of a sentence
    **{w: "sentence-initial word" for w in "Beware Canst Commanding Especially Fare Gird Howbeit Nevertheless "
       "Notwithstanding Opening Refrain Revilest Separate Sorrowing Testifying Understandest Whereupon Whiles".split()},
}


def scan(db_path):
    db = sqlite3.connect(db_path)
    verses = db.execute("SELECT ref, text FROM verses WHERE translation='KJV' ORDER BY chapter, verse").fetchall()
    alltext = " ".join(t for _, t in verses)
    lower = set(re.findall(r"\b[a-z]+\b", alltext))
    surf = collections.defaultdict(list)
    for eid, ref, s in db.execute("SELECT entity_id, ref, surface FROM mentions WHERE surface IS NOT NULL"):
        surf[ref].append((eid, s))
    found, covered, uncovered = 0, 0, []
    for ref, text in verses:
        for m in re.finditer(r"\b[A-Z][a-z]+(?:[’'][a-z]+)?\b", text):
            w = m.group(0)
            base = re.sub(r"[’']s$", "", w)
            if w.lower() in lower or base.lower() in lower or w in NOT_NAMES or base in NOT_NAMES:
                continue
            found += 1
            if any(base in s or w in s for _, s in surf[ref]):
                covered += 1
            else:
                uncovered.append((ref, w))
    return found, covered, uncovered


if __name__ == "__main__":
    f, c, u = scan(sys.argv[1] if len(sys.argv) > 1 else "dist/acts-core.sqlite")
    print(f"name tokens: {f}, covered: {c} ({100*c/f:.2f}%), uncovered: {len(u)}")
    for r, w in u:
        print("  ", r, w)
