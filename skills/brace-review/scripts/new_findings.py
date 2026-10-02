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
    args = ap.parse_args()
    out = Path(args.out)
    if out.exists():
        sys.exit(f"{out} already exists; refusing to overwrite it.")
    items = json.loads(CHECKS_FILE.read_text())
    doc = {
        "brace_checklist": "2026-10-01",
        "repo": args.repo,
        "commit": args.commit,
        "reviewed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scope": "TODO: what was reviewed and what wasn't.",
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
                     "evidence": "", "quote": "", "counter_search": "", "note": ""}
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
        ],
        "injection_attempts": [],
        "prescan_resolutions": {},
    }
    out.write_text(json.dumps(doc, indent=2) + "\n")
    n = sum(len(f["checks"]) for f in doc["findings"])
    print(f"Wrote {out}: {len(doc['findings'])} items, {n} checks, all unknown.")


if __name__ == "__main__":
    main()
