#!/usr/bin/env python3
"""Generate tools/brace/brace_items.json and the record.yaml template.

Sources:
  CHECKLIST.md  item headings, e.g. `**B05 · G1 · C4 — Destructive-action interception.**`
                top-3 = items listed under each "IF YOU DO NOTHING ELSE" heading
  ROLES.md      item tables, e.g. `| B05 | G1 | Title | **Agent team** | Business owner, Security |`

Usage:
  python tools/brace/gen_items.py           # write the files
  python tools/brace/gen_items.py --check   # exit 1 if either file is out of date
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
ITEMS_JSON = HERE / "brace_items.json"
RECORD_TEMPLATE = HERE / "templates" / ".brace" / "record.yaml"

ASPECTS = {
    "B": "build-time",
    "R": "run-time",
    "A": "agent",
    "C": "configuration",
    "E": "ecosystem",
}
ASPECT_ORDER = list(ASPECTS)

ROLE_KEYS = {
    "agent team": "agent_team",
    "operations": "operations",
    "security": "security",
    "infrastructure": "infrastructure",
    "governance": "governance",
    "business owner": "business_owner",
    "data and privacy": "data_privacy",
    "model team": "model_team",
    "vendors": "vendors",
    "independent audit": "independent_audit",
}

EXPECTED_COUNT = 53

HEADING_RE = re.compile(
    r"^- \[[ xX]\] \*\*(?P<id>[BRACE]\d{2}) · (?P<gate>G[123]) · (?P<controls>[^—]+?) — (?P<title>.+?)\.\*\*"
)
ROLES_ROW_RE = re.compile(
    r"^\|\s*(?P<id>[BRACE]\d{2})\s*\|\s*(?P<gate>G[123])\s*\|\s*(?P<title>[^|]+?)\s*\|"
    r"\s*\*\*(?P<lead>[^*]+)\*\*\s*\|\s*(?P<shares>[^|]*?)\s*\|\s*$"
)


class GenError(Exception):
    pass


def role_key(name: str) -> str:
    key = ROLE_KEYS.get(name.strip().lower())
    if key is None:
        raise GenError(f"ROLES.md: unknown role name {name!r}")
    return key


def parse_checklist(text: str) -> dict[str, dict]:
    items: dict[str, dict] = {}
    in_top3 = False
    for line in text.splitlines():
        if line.startswith("#"):
            in_top3 = "IF YOU DO NOTHING ELSE" in line
            continue
        m = HEADING_RE.match(line)
        if not m:
            continue
        item_id = m["id"]
        if item_id in items:
            raise GenError(f"CHECKLIST.md: {item_id} appears twice")
        items[item_id] = {
            "id": item_id,
            "aspect": ASPECTS[item_id[0]],
            "gate": m["gate"],
            "controls": m["controls"].strip(),
            "title": m["title"].strip(),
            "top3": in_top3,
        }
    return items


def parse_roles(text: str) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    for line in text.splitlines():
        m = ROLES_ROW_RE.match(line.strip())
        if not m:
            continue
        item_id = m["id"]
        if item_id in rows:
            raise GenError(f"ROLES.md: {item_id} appears twice")
        shares = [s for s in (p.strip() for p in m["shares"].split(",")) if s]
        rows[item_id] = {
            "gate": m["gate"],
            "title": m["title"].strip(),
            "lead_role": role_key(m["lead"]),
            "share_roles": [role_key(s) for s in shares],
        }
    return rows


def sort_key(item_id: str):
    return (ASPECT_ORDER.index(item_id[0]), int(item_id[1:]))


def build_items(checklist_text: str, roles_text: str) -> list[dict]:
    checklist = parse_checklist(checklist_text)
    roles = parse_roles(roles_text)
    problems = []
    if len(checklist) != EXPECTED_COUNT:
        problems.append(f"CHECKLIST.md has {len(checklist)} items, expected {EXPECTED_COUNT}")
    missing = sorted(set(checklist) - set(roles), key=sort_key)
    extra = sorted(set(roles) - set(checklist), key=sort_key)
    if missing:
        problems.append("ROLES.md has no row for: " + ", ".join(missing))
    if extra:
        problems.append("ROLES.md lists items not in CHECKLIST.md: " + ", ".join(extra))
    for item_id, item in checklist.items():
        row = roles.get(item_id)
        if not row:
            continue
        if row["gate"] != item["gate"]:
            problems.append(f"{item_id}: gate is {item['gate']} in CHECKLIST.md but {row['gate']} in ROLES.md")
        if row["title"] != item["title"]:
            problems.append(f"{item_id}: title {item['title']!r} in CHECKLIST.md but {row['title']!r} in ROLES.md")
    for aspect in ASPECT_ORDER:
        n = sum(1 for i in checklist.values() if i["id"][0] == aspect and i["top3"])
        if n != 3:
            problems.append(f"aspect {aspect} has {n} top-3 items, expected 3")
    if problems:
        raise GenError("\n".join(problems))

    out = []
    for item_id in sorted(checklist, key=sort_key):
        item = checklist[item_id]
        row = roles[item_id]
        out.append(
            {
                "id": item_id,
                "aspect": item["aspect"],
                "gate": item["gate"],
                "controls": item["controls"],
                "title": item["title"],
                "top3": item["top3"],
                "lead_role": row["lead_role"],
                "share_roles": row["share_roles"],
            }
        )
    return out


def render_items_json(items: list[dict]) -> str:
    return json.dumps(items, indent=2, ensure_ascii=False) + "\n"


def render_record_template(items: list[dict]) -> str:
    lines = [
        "# BRACE evidence record: one entry for each of the 53 checklist items.",
        "# Generated by tools/brace/gen_items.py. Fill it in; don't remove items.",
        "#",
        "# outcome:   pass | gap | na | not_reviewed",
        "# lead:      the person or team who answers for the item (replace the TODO).",
        "#            The TODO names the role that usually leads it (see ROLES.md).",
        "# shares:    other people or teams who help or review.",
        "# evidence:  a pass needs at least one entry with a link and a date, e.g.",
        "#              - link: \"https://ci.example/run/123\"",
        "#                date: 2026-09-30",
        "#                note: \"What the test showed.\"",
        "# exception: for a G2 gap (or a G3 gap on a low-stakes, low-autonomy deployment),",
        "#            the name of a file in .brace/exceptions/ without .yaml.",
        "# na:        for an N/A item, the name of a file in .brace/na/ without .yaml.",
        "# verified_by, notes: optional.",
        "items:",
    ]
    current_aspect = None
    for item in items:
        if item["aspect"] != current_aspect:
            current_aspect = item["aspect"]
            lines.append("")
            lines.append(f"  # --- {current_aspect} ---")
        top = " · top 3" if item["top3"] else ""
        shares = ", ".join(item["share_roles"]) or "none"
        lines.append(f"  # {item['id']} · {item['gate']} · {item['title']}{top} (shares: {shares})")
        lines.append(f"  {item['id']}:")
        lines.append("    outcome: not_reviewed")
        lines.append(f"    lead: \"TODO ({item['lead_role']})\"")
        lines.append("    shares: []")
        lines.append("    evidence: []")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="exit 1 if the generated files are out of date")
    parser.add_argument("--repo", default=str(REPO), help="repository root holding CHECKLIST.md and ROLES.md")
    args = parser.parse_args(argv)

    repo = Path(args.repo)
    try:
        items = build_items(
            (repo / "CHECKLIST.md").read_text(encoding="utf-8"),
            (repo / "ROLES.md").read_text(encoding="utf-8"),
        )
    except (GenError, OSError) as exc:
        print(f"gen_items: {exc}", file=sys.stderr)
        return 2

    outputs = {
        ITEMS_JSON: render_items_json(items),
        RECORD_TEMPLATE: render_record_template(items),
    }
    if args.check:
        stale = [p for p, text in outputs.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
        for p in stale:
            print(f"out of date: {p.relative_to(REPO) if p.is_relative_to(REPO) else p}", file=sys.stderr)
        if stale:
            print("Run: python tools/brace/gen_items.py", file=sys.stderr)
            return 1
        print(f"up to date ({len(items)} items)")
        return 0

    for p, text in outputs.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    print(f"wrote {len(items)} items to {ITEMS_JSON.name} and {RECORD_TEMPLATE.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
