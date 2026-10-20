#!/usr/bin/env python3
"""Write a starter brace-findings.json with every item and every check filled in.

Each check starts as "unknown" and each item as "needs_evidence". The reviewer
replaces the answers; validate_findings.py --fix then sets the ratings the rules require.

Usage: python new_findings.py OUT.json [--repo NAME] [--commit HASH] [--aspect B|R|A|C|E]

With --aspect, the file holds only that aspect's items, for reviewing one aspect at a
time. Combine the aspect files with merge_findings.py.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

CHECKS_FILE = Path(__file__).resolve().parent.parent / "references" / "checks.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--repo", default="")
    ap.add_argument("--commit", default=None)
    ap.add_argument("--aspect", choices=list("BRACE"))
    ap.add_argument('--items', help='Only these comma-separated items, at most five for a bounded batch')
    args = ap.parse_args()
    out = Path(args.out)
    if out.exists():
        sys.exit(f"{out} already exists; refusing to overwrite it.")
    items = json.loads(CHECKS_FILE.read_text())
    selected = args.items.split(',') if args.items else None
    if selected and (len(selected)>5 or len(set(selected))!=len(selected) or any(i not in items for i in selected)):
        ap.error('--items requires one to five unique checklist IDs')
    doc = {
        "brace_checklist": "2026-10-01",
        "repo": args.repo,
        "commit": args.commit,
        "reviewed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scope": "TODO: what was reviewed and what wasn't.",
        "review_protocol": "coverage-first-v1",
        "findings": [
            {
                "item": iid,
                "gate": meta["gate"],
                "title": meta["title"],
                "requirement": meta.get("requirement", ""),
                "not_covered": meta.get("not_covered", []),
                "rating": "needs_evidence",
                "confidence": "low",
                "evidence": [],
                "checks": [
                    {"id": c["id"], "check": c["check"], "verify": c.get("verify", ""), "met": "unknown",
                     "evidence": "", "quote": "", "counter_search": "", "note": "",
                     "coverage": [], "deviations": [], "attempts": []}
                    for c in meta["checks"]
                ],
                "red_flags_found": [],
                "violates": [],
                "also_affects": [],
                "summary": "TODO",
                "next_step": "TODO",
                "lead_role": meta["lead_role"],
            }
            for iid, meta in items.items()
            if not args.aspect or iid[0] == args.aspect
            if selected is None or iid in selected
        ],
        "injection_attempts": [],
        "prescan_resolutions": {},
    }
    out.write_text(json.dumps(doc, indent=2) + "\n")
    n = sum(len(f["checks"]) for f in doc["findings"])
    print(f"Wrote {out}: {len(doc['findings'])} items, {n} checks, all unknown.")


if __name__ == "__main__":
    main()
