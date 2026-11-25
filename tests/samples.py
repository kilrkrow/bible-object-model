"""Draw the hand-check samples for the machine-drafted layers (fixed seeds, so the same rows come back).

    python tests/samples.py alignment   # 40 random aligned KJV words of Acts and John
    python tests/samples.py speakers    # 20 random drafted speech spans, and 20 with a named speaker
"""
import pathlib, random, sqlite3, sys

CORE = pathlib.Path(__file__).resolve().parent.parent / "dist/acts-core.sqlite"


def alignment(db, n=40, seed=20261125):
    rows = db.execute("""SELECT t.ref, t.text, g.word, g.translit, g.strong, l.gloss, a.score, a.method FROM alignments a
        JOIN tokens t ON t.ref=a.ref AND t.idx=a.token_idx JOIN greek_words g ON g.ref=a.ref AND g.idx=a.greek_idx
        LEFT JOIN lexicon l ON l.strong=g.strong ORDER BY t.ref, t.idx""").fetchall()
    return random.Random(seed).sample(rows, n)


def speakers(db, n=20, seed=20261125, named_only=False):
    rows = db.execute("""SELECT u.ref, u.start, u."end", u.speaker, u.note, v.text FROM utterances u JOIN verses v ON v.ref=u.ref
        WHERE basis='drafted'""" + (" AND speaker IS NOT NULL" if named_only else "") + " ORDER BY u.ref, u.start").fetchall()
    return random.Random(seed).sample(rows, n)


if __name__ == "__main__":
    db = sqlite3.connect(CORE)
    if sys.argv[1:] == ["alignment"]:
        for i, r in enumerate(alignment(db), 1):
            print(i, *r)
    else:
        for i, r in enumerate(speakers(db), 1):
            print("all", i, r[0], r[3], repr(r[5][r[1]:r[2]]))
        for i, r in enumerate(speakers(db, seed=1125, named_only=True), 1):
            print("named", i, r[0], r[3], repr(r[5][r[1]:r[2]]))
