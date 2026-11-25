"""Print the content hash of dist/acts-core.sqlite (the same on every platform; the file's own bytes are not,
because SQLite stamps its version into the file header).

    python build/data_hash.py
"""
import pathlib, sqlite3

db = pathlib.Path(__file__).resolve().parent.parent / "dist" / "acts-core.sqlite"
con = sqlite3.connect(db.as_uri() + "?mode=ro", uri=True)
print(con.execute("SELECT value FROM meta WHERE key = 'content_sha256'").fetchone()[0])
