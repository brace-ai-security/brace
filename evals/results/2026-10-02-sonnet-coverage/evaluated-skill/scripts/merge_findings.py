#!/usr/bin/env python3
"""Merge per-aspect findings files into one brace-findings.json.

Usage: python merge_findings.py OUT.json ASPECT_FILE.json [ASPECT_FILE.json ...]
"""
import json
import sys
from pathlib import Path


def main():
    if len(sys.argv) < 3:
        print(__doc__.strip())
        sys.exit(2)
    out = Path(sys.argv[1])
    docs = [json.loads(Path(p).read_text()) for p in sys.argv[2:]]
    merged = {k: v for k, v in docs[0].items() if k not in ("findings", "injection_attempts", "scope", "prescan_resolutions")}
    merged["scope"] = " ".join(d.get("scope", "") for d in docs if d.get("scope") and not d["scope"].startswith("TODO"))
    findings, seen = [], set()
    for d in docs:
        for f in d.get("findings", []):
            if f["item"] in seen:
                sys.exit(f"{f['item']} appears in more than one file.")
            seen.add(f["item"])
            findings.append(f)
    order = "BRACE"
    merged["findings"] = sorted(findings, key=lambda f: (order.index(f["item"][0]), f["item"]))
    attempts, seen_at = [], set()
    for d in docs:
        for a in d.get("injection_attempts", []):
            key = (a.get("file"), a.get("line"))
            if key not in seen_at:
                seen_at.add(key)
                attempts.append(a)
    merged["injection_attempts"] = attempts
    resolutions = {}
    for d in docs:
        resolutions.update(d.get("prescan_resolutions") or {})
    merged["prescan_resolutions"] = resolutions
    out.write_text(json.dumps(merged, indent=2) + "\n")
    print(f"Wrote {out}: {len(findings)} items from {len(docs)} files.")


if __name__ == "__main__":
    main()
