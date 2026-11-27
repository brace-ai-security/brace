#!/usr/bin/env python3
"""Fill the label and reason columns of a reviewer CSV (from `harness.py label`) with the
labels the 2026-11 field report used, so a run can be re-labelled the same way.

The labels are a reviewer's judgement, recorded as rules: each rule was written after reading
the findings it covers (every AP20-AP23 finding was read one by one; AP01, AP02, AP04, AP06
and AP10 were labelled by path class after a manual spot check). `override` rows (repo index,
first 8 characters of the finding id) record individual decisions that differ from the class rule. Rows no rule covers
are left blank for a person.

    python3 autolabel.py IN.csv OUT.csv [OVERRIDES.json]
"""
import csv
import json
import re
import sys

TEST_PATH = re.compile(r"(?:^|/)(?:tests?|__tests__|spec|specs|fixtures?|snapshots?|__snapshots__|evals?|"
                       r"integration-tests|e2e|bench|benchmarks?|testdata|examples?)(?:/|$)|"
                       r"\.(?:test|spec)\.[\w]+$|(?:^|/)test_[^/]+$|_test\.\w+$", re.I)
SCHEMA_PATH = re.compile(r"schema|\.jsonl$|catalog|docs/", re.I)


def label(row: dict) -> tuple[str, str]:
    rule, path, detail = row["rule"], row["file"], row["detail"]
    if TEST_PATH.search(path) or path.startswith("vendor/") or "/vendor/" in path:
        return "intended", "test, fixture, example or vendored file"
    if rule in ("AP01", "AP02"):
        if SCHEMA_PATH.search(path):
            return "intended", "schema, catalog or recorded transcript listing the value"
        return "tp", "code or config that passes the bypass to an agent it launches"
    if rule == "AP04":
        return "tp", "MCP server run from an unpinned package or image"
    if rule == "AP05":
        return "tp", "literal credential-shaped value in agent config"
    if rule == "AP06":
        return "tp", "allow-rule that permits any shell command"
    if rule == "AP07":
        return "tp", "remote MCP server over plain http"
    if rule == "AP09":
        return "tp", "likely combination inferred from names (by design marked likely)"
    if rule == "AP10":
        return "tp", "base image not pinned to a digest in an agent repository"
    if rule == "AP20":
        return "tp", "auto-approval setting committed to the repository"
    if rule == "AP21":
        return "tp", "agent on an open trigger with the write-access check opened to everyone"
    if rule == "AP22":
        return "tp", "stray invisible character; no hidden instruction found"
    if rule == "AP23":
        return "tp", "skill or hook instructs piping a download into a shell"
    return "", ""


def main() -> None:
    src, dst = sys.argv[1], sys.argv[2]
    overrides = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else {}
    rows = list(csv.DictReader(open(src, newline="")))
    for row in rows:
        lab, why = label(row)
        o = overrides.get(f"{row['repo_index']}:{row['id'][:8]}")
        if o:
            lab, why = o
        row["label"], row["reason"] = lab, why
    with open(dst, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["label"])
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
