"""Fetch every source at its pinned commit into ./sources and verify file hashes.

Usage: python build/fetch_sources.py [--sources DIR]
Needs git. Safe to rerun: an existing checkout is reused if its hashes match.
"""
import argparse, hashlib, json, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*args, cwd=None):
    subprocess.run(["git", *args], cwd=cwd, check=True)


def fetch(name, spec, dest):
    d = dest / name
    if not d.exists():
        d.mkdir(parents=True)
        git("init", "-q", cwd=d)
        git("remote", "add", "origin", spec["repo"], cwd=d)
        if spec.get("sparse"):
            git("config", "core.sparseCheckout", "true", cwd=d)
            (d / ".git" / "info" / "sparse-checkout").write_text("\n".join(spec["sparse"]) + "\n")
        git("fetch", "-q", "--depth", "1", "--filter=blob:none", "origin", spec["commit"], cwd=d)
        git("checkout", "-q", "FETCH_HEAD", cwd=d)
    bad = []
    for rel, want in spec["files"].items():
        p = d / rel
        got = sha256(p) if p.exists() else "missing"
        if got != want:
            bad.append(f"{name}/{rel}: expected {want}, got {got}")
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", default=str(ROOT / "sources"))
    a = ap.parse_args()
    dest = pathlib.Path(a.sources)
    lock = json.loads((ROOT / "sources.lock.json").read_text())
    bad = []
    for name, spec in lock.items():
        print(f"fetching {name} @ {spec['commit'][:10]}")
        bad += fetch(name, spec, dest)
    if bad:
        print("HASH MISMATCH:\n  " + "\n  ".join(bad))
        sys.exit(1)
    print("all source files match sources.lock.json")


if __name__ == "__main__":
    main()
