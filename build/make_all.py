"""One command for everything: fetch pinned sources, build the data files, draw the maps, write the vault.

    python build/make_all.py
"""
import pathlib, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
for step in ("fetch_sources.py", "build.py", "make_map.py", "make_vault.py"):
    print(f"== {step}", flush=True)
    subprocess.run([sys.executable, str(HERE / step)], check=True)
