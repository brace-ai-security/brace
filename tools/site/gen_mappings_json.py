#!/usr/bin/env python3
"""Generate machine-readable framework mappings (mappings/*.json) from the Markdown mapping tables.

Usage:
    python tools/site/gen_mappings_json.py          # write mappings/<framework>.json
    python tools/site/gen_mappings_json.py --check  # exit 1 if any JSON file is stale

Standard library only. The Markdown pages (mappings/*.md) are the source of truth. Every
table with a "Coverage" and a "BRACE items" column becomes rows of the framework's JSON
file, for security questionnaires and GRC tools to import:

    {"format": "brace-mapping", "version": 1, "framework": {"id", "title"},
     "source": "mappings/<id>.md", "coverage_values": [...],
     "mappings": [{"section", "id", "name", "url", "coverage", "brace_controls",
                   "brace_items", "rationale"}]}

The first column is the framework's own ID (a Markdown link keeps its URL in "url"), the
second its name, the last the rationale as plain text. Item IDs are checked against
src/brace_tools/data/brace_items.json and coverage values against the three the pages define.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = ROOT / "mappings"
ITEMS = {i["id"] for i in json.loads((ROOT / "src/brace_tools/data/brace_items.json").read_text(encoding="utf-8"))}
COVERAGE = ("Direct", "Partial", "Out of scope")
LINK = re.compile(r"\[([^\]]*)\]\(([^)\s]*)\)")
ITEM_ID = re.compile(r"\b[BRACE]\d\d\b")
CONTROL_ID = re.compile(r"\bC\d\b")


class MappingError(Exception):
    pass


def cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def plain(text: str) -> str:
    """Markdown cell text as plain text: links keep their label; emphasis and code marks go."""
    text = LINK.sub(r"\1", text)
    return re.sub(r"\*\*|`", "", text).strip()


def parse(md: Path) -> dict:
    lines = md.read_text(encoding="utf-8").splitlines()
    title = next((plain(l[2:]) for l in lines if l.startswith("# ")), md.stem)
    rows, section, i = [], "", 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("## ") or line.startswith("### "):
            section = plain(line.lstrip("#"))
        head = cells(line) if line.startswith("|") else []
        if "Coverage" in head and "BRACE items" in head and i + 1 < len(lines) and lines[i + 1].startswith("|---"):
            cov, items = head.index("Coverage"), head.index("BRACE items")
            ctl = head.index("BRACE controls") if "BRACE controls" in head else None
            i += 2
            while i < len(lines) and lines[i].startswith("|"):
                row = cells(lines[i])
                where = f"{md.name}:{i + 1}"
                if len(row) != len(head):
                    raise MappingError(f"{where}: {len(row)} cells, expected {len(head)}")
                if row[cov] not in COVERAGE:
                    raise MappingError(f"{where}: coverage {row[cov]!r} is not one of {', '.join(COVERAGE)}")
                ids = ITEM_ID.findall(row[items])
                unknown = [x for x in ids if x not in ITEMS]
                if unknown:
                    raise MappingError(f"{where}: unknown BRACE item(s) {', '.join(unknown)}")
                link = LINK.search(row[0])
                rows.append({"section": section, "id": plain(row[0]), "name": plain(row[1]),
                             "url": link.group(2) if link and link.group(2).startswith("https://") else "",
                             "coverage": row[cov],
                             "brace_controls": CONTROL_ID.findall(row[ctl]) if ctl is not None else [],
                             "brace_items": ids, "rationale": plain(row[-1])})
                i += 1
            continue
        i += 1
    if not rows:
        raise MappingError(f"{md.name}: no table with Coverage and BRACE items columns")
    return {"format": "brace-mapping", "version": 1, "framework": {"id": md.stem, "title": title},
            "source": f"mappings/{md.name}", "coverage_values": list(COVERAGE), "mappings": rows}


def render(doc: dict) -> str:
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="exit 1 if any generated file is stale")
    args = ap.parse_args(argv)
    stale = []
    try:
        outputs = {md.with_suffix(".json"): render(parse(md)) for md in sorted(SOURCES.glob("*.md"))}
    except MappingError as e:
        print(f"gen_mappings_json: {e}", file=sys.stderr)
        return 1
    extra = sorted(set(SOURCES.glob("*.json")) - set(outputs))
    for path, text in outputs.items():
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current != text:
            if args.check:
                stale.append(path.relative_to(ROOT).as_posix())
            else:
                path.write_text(text, encoding="utf-8")
                print(f"wrote {path.relative_to(ROOT).as_posix()}")
    if args.check:
        stale += [f"{p.relative_to(ROOT).as_posix()} (no Markdown source)" for p in extra]
        if stale:
            print("Stale mapping JSON; run python tools/site/gen_mappings_json.py:\n  " + "\n  ".join(stale),
                  file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
