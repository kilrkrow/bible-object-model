"""Dates and other uncertain facts only ever leave this package as a Claim.

A Claim says what the text states (basis, not_stated) and lists views. Each view must
carry a label and a source, so a reader always sees whose chronology a date comes from.
`guard` wraps every public query and refuses to return a bare date anywhere in the output.
"""
import functools, re

CLAIM_KEYS = {"type", "property", "basis", "not_stated", "views", "note", "relative_to"}
DATE_KEYS = {"date", "year", "born", "died", "when", "start", "end", "birth", "death",
             "birth_year", "death_year", "birthyear", "deathyear", "dated", "year_ad", "year_bc"}
ERA_YEAR = re.compile(r"\b\d{1,4}\s?(?:BC|AD|BCE|CE|B\.C\.|A\.D\.)(?![A-Za-z])|\b(?:AD|A\.D\.)\s?\d{1,4}\b")


def make_claim(prop, basis, not_stated, views, note="", relative_to=None):
    for v in views:
        if not v.get("label") or not v.get("source"):
            raise ValueError(f"claim view for {prop} lacks a label or source: {v}")
    return {"type": "claim", "property": prop, "basis": basis, "not_stated": bool(not_stated),
            "relative_to": relative_to, "note": note or "",
            "views": [{"label": v["label"], "value": v.get("value"), "range_from": v.get("range_from"),
                       "range_to": v.get("range_to"), "source": v["source"]} for v in views]}


def bare_dates(obj, path="$"):
    """Return every place in obj where a date appears outside a labelled claim view."""
    found = []
    if isinstance(obj, dict):
        if obj.get("type") == "claim":
            if set(obj) - CLAIM_KEYS:
                found.append(f"{path}: claim has unexpected keys {sorted(set(obj) - CLAIM_KEYS)}")
            for i, v in enumerate(obj.get("views", [])):
                if not v.get("label") or not v.get("source"):
                    found.append(f"{path}.views[{i}]: view without label or source")
            return found
        for k, v in obj.items():
            p = f"{path}.{k}"
            if str(k).lower() in DATE_KEYS and not (isinstance(v, dict) and v.get("type") == "claim"):
                found.append(f"{p}: date-like field not wrapped in a claim")
            else:
                found += bare_dates(v, p)
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            found += bare_dates(v, f"{path}[{i}]")
    elif isinstance(obj, str) and ERA_YEAR.search(obj):
        found.append(f"{path}: year outside a claim: {ERA_YEAR.search(obj).group(0)!r}")
    return found


class BareDateError(AssertionError):
    pass


def guard(fn):
    @functools.wraps(fn)
    def wrapper(*a, **k):
        out = fn(*a, **k)
        bad = bare_dates(out)
        if bad:
            raise BareDateError(f"{fn.__name__} would return a bare date: {bad[:3]}")
        return out
    return wrapper
