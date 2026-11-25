"""The 66 books: aruljohn/Bible-kjv file name, OSIS code, and the names people type."""
import re

# aruljohn/Bible-kjv file name -> OSIS code, in canonical order
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

OSIS = [o for _, o in BOOKS]
BOOK_INDEX = {o: i for i, o in enumerate(OSIS)}


def _aliases():
    out = {}
    for fname, osis in BOOKS:
        name = re.sub(r"^([1-3])", r"\1 ", re.sub(r"(?<=[a-z])(?=of)", " ", fname)).replace("of", "of ").strip()
        for k in {fname, osis, name, name.replace(" ", ""), osis[:3] if not osis[0].isdigit() else osis[:4]}:
            out.setdefault(k.lower().replace(" ", ""), osis)
    out.update({"act": "Acts", "ac": "Acts", "jn": "John", "jhn": "John", "psalm": "Ps", "song": "Song",
                "songofsongs": "Song", "canticles": "Song", "revelations": "Rev", "phm": "Phlm", "php": "Phil"})
    return out


BOOK_ALIASES = _aliases()
