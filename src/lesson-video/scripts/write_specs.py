# -*- coding: utf-8 -*-
"""Collect SPECS from every build/specs/*.py and write beats/<chapter id>.json."""
import importlib.util
import json
import sys
from pathlib import Path

BUILD = Path(__file__).resolve().parent
sys.path.insert(0, str(BUILD))


def load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.SPECS


def main():
    out = BUILD / "beats"
    out.mkdir(exist_ok=True)
    specs = {}
    for path in sorted((BUILD / "specs").glob("*.py")):
        specs.update(load(path))
    for cid, spec in specs.items():
        (out / f"{cid}.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(specs), "chapters,", sum(len(s["beats"]) for s in specs.values()), "beats")


if __name__ == "__main__":
    main()
