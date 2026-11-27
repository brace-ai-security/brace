"""`open-agent-security merge`: roll JSON reports from several repositories up into one.

    open-agent-security merge [--label NAME]... [--output FILE] [--csv FILE] [--markdown FILE] REPORT.json...

Each input is a report written by `--json` or `--output json=FILE`. The merged JSON lists, per
repository, its verdict and counts by severity and rule, every finding labelled with its
repository, and overall totals; `--csv` and `--markdown` write the per-repository summary as a
table. A repository's label is the matching `--label` (in order) or the report's file name
without `.json`.

Reports may come from many places, so each is untrusted: bounded in size, read as strict JSON,
and checked against the report-1 shape (the keys and types merge reads). A report that fails is
an error (exit code 2), never silently left out. A repository whose scan was incomplete is
counted as incomplete, never as clean.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from pathlib import Path

from .catalog import SEVERITY_ORDER
from .fsio import ReadFailure, read, write_new
from .limits import MERGE_FILE_BYTES, MERGE_FILES, MERGE_FINDINGS, NOTE_CHARS
from .output import clean, md_escape
from .report.json_out import SCHEMA

FORMAT = "open-agent-security-merge"
RULE = re.compile(r"^[A-Z][A-Z0-9_\-]{1,31}$")
ID = re.compile(r"^[0-9a-f]{32}$")
SEVERITIES = tuple(SEVERITY_ORDER)
CSV_FORMULA = ("=", "+", "-", "@", "\t", "\r")  # cells a spreadsheet would run as a formula


class MergeError(Exception):
    """An input that is not a usable report, or too many of them. Exit code 2."""


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="open-agent-security merge",
                                description="Combine JSON reports from several repositories into one.")
    p.add_argument("reports", nargs="+", metavar="REPORT", help="JSON reports (--json output)")
    p.add_argument("--label", action="append", default=[],
                   help="a repository label for each report, in order (default: the file name)")
    p.add_argument("--output", metavar="FILE", help="write the merged JSON to FILE instead of stdout")
    p.add_argument("--csv", metavar="FILE", help="also write a per-repository CSV summary to FILE")
    p.add_argument("--markdown", metavar="FILE", help="also write a per-repository Markdown summary to FILE")
    return p


def main(argv: list[str]) -> int:
    a = build_parser().parse_args(argv)
    try:
        if len(a.reports) > MERGE_FILES:
            raise MergeError(f"at most {MERGE_FILES} reports")
        if len(a.label) > len(a.reports):
            raise MergeError("more --label options than reports")
        merged = merge([(label(a, i, path), load(Path(path))) for i, path in enumerate(a.reports)])
    except MergeError as e:
        print(f"open-agent-security merge: {clean(e, NOTE_CHARS)}", file=sys.stderr)
        return 2
    try:
        text = json.dumps(merged, indent=2) + "\n"
        if a.output:
            write_new(a.output, text)
        else:
            sys.stdout.write(text)
        if a.csv:
            write_new(a.csv, to_csv(merged))
        if a.markdown:
            write_new(a.markdown, to_markdown(merged))
    except OSError as e:
        print(f"open-agent-security merge: could not write output: {clean(e, NOTE_CHARS)}", file=sys.stderr)
        return 2
    return 0


def label(a: argparse.Namespace, i: int, path: str) -> str:
    name = a.label[i] if i < len(a.label) else Path(path).name
    if i >= len(a.label):
        for suffix in (".json", ".oas"):
            name = name[:-len(suffix)] if name.lower().endswith(suffix) else name
    return clean(name, 120, redact=False) or f"report-{i + 1}"


def load(path: Path) -> dict:
    shown = clean(str(path), 120, redact=False)
    text = read(path, follow=True, limit=MERGE_FILE_BYTES)
    if isinstance(text, ReadFailure):
        raise MergeError(f"{shown}: not a readable regular file of at most {MERGE_FILE_BYTES // (1024 * 1024)} MB")
    try:
        data = json.loads(text, parse_constant=_reject)
    except (ValueError, RecursionError):
        raise MergeError(f"{shown}: not valid JSON") from None
    check_report(data, shown)
    return data


def _reject(name: str):
    raise ValueError(name)


def check_report(d, shown: str) -> None:
    """The report-1 shape, as far as merge reads it."""
    def bad(what: str):
        raise MergeError(f"{shown}: not an open-agent-security JSON report ({what})")
    if not isinstance(d, dict):
        bad("not an object")
    if d.get("schema") != SCHEMA or d.get("scanner") != "open-agent-security":
        bad("schema or scanner")
    for key, kind in (("version", str), ("truncated", bool), ("incomplete", bool), ("findings", list),
                      ("notes", list), ("suppressed", int)):
        if not isinstance(d.get(key), kind) or (kind is int and isinstance(d[key], bool)):
            bad(key)
    if not all(isinstance(n, str) for n in d["notes"]):
        bad("notes")
    for f in d["findings"] + (d.get("suppressed_findings") if isinstance(d.get("suppressed_findings"), list) else []):
        if not isinstance(f, dict) or not isinstance(f.get("rule"), str) or not RULE.match(f["rule"]) \
                or f.get("severity") not in SEVERITIES or not isinstance(f.get("file"), str) \
                or type(f.get("line")) is not int or f["line"] < 0 or not isinstance(f.get("detail"), str) \
                or not isinstance(f.get("id"), str) or not ID.match(f["id"]) or not isinstance(f.get("title"), str):
            bad("a finding")


def verdict(d: dict) -> str:
    return "incomplete" if d["incomplete"] or d["truncated"] else "findings" if d["findings"] else "clean"


def merge(reports: list[tuple[str, dict]]) -> dict:
    repos, findings, seen = [], [], {}
    totals = {"repos": len(reports), "findings": 0, "suppressed": 0, "by_severity": dict.fromkeys(SEVERITIES, 0),
              "by_rule": {}, "verdicts": {"clean": 0, "findings": 0, "incomplete": 0}, "repos_by_rule": {}}
    for name, d in reports:
        seen[name] = seen.get(name, 0) + 1
        name = name if seen[name] == 1 else f"{name}#{seen[name]}"
        by_sev, by_rule = dict.fromkeys(SEVERITIES, 0), {}
        for f in d["findings"]:
            by_sev[f["severity"]] += 1
            by_rule[f["rule"]] = by_rule.get(f["rule"], 0) + 1
            if len(findings) >= MERGE_FINDINGS:
                raise MergeError(f"more than {MERGE_FINDINGS} findings in all")
            findings.append({"repo": name, "rule": f["rule"], "severity": f["severity"], "title": clean(f["title"]),
                             "file": clean(f["file"], 300, redact=False), "line": f["line"],
                             "detail": clean(f["detail"]), "id": f["id"]})
        v = verdict(d)
        repos.append({"repo": name, "verdict": v, "scanner_version": clean(d["version"], 40),
                      "findings": len(d["findings"]), "suppressed": d["suppressed"], "by_severity": by_sev,
                      "by_rule": dict(sorted(by_rule.items()))})
        totals["verdicts"][v] += 1
        totals["findings"] += len(d["findings"])
        totals["suppressed"] += d["suppressed"]
        for s, n in by_sev.items():
            totals["by_severity"][s] += n
        for r, n in by_rule.items():
            totals["by_rule"][r] = totals["by_rule"].get(r, 0) + n
            totals["repos_by_rule"][r] = totals["repos_by_rule"].get(r, 0) + 1
    totals["by_rule"] = dict(sorted(totals["by_rule"].items()))
    totals["repos_by_rule"] = dict(sorted(totals["repos_by_rule"].items()))
    return {"format": FORMAT, "version": 1, "repos": repos, "totals": totals, "findings": findings}


def rows(merged: dict) -> list[list[str]]:
    out = [["repo", "verdict", "findings", *SEVERITIES, "suppressed", "rules"]]
    for r in merged["repos"]:
        out.append([r["repo"], r["verdict"], str(r["findings"]), *(str(r["by_severity"][s]) for s in SEVERITIES),
                    str(r["suppressed"]), " ".join(f"{k}:{v}" for k, v in r["by_rule"].items())])
    t = merged["totals"]
    out.append(["TOTAL", f"{t['verdicts']['clean']} clean, {t['verdicts']['findings']} with findings, "
                f"{t['verdicts']['incomplete']} incomplete", str(t["findings"]),
                *(str(t["by_severity"][s]) for s in SEVERITIES), str(t["suppressed"]),
                " ".join(f"{k}:{v}" for k, v in t["by_rule"].items())])
    return out


def to_csv(merged: dict) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    for row in rows(merged):
        w.writerow(["'" + c if c.startswith(CSV_FORMULA) else c for c in row])
    return buf.getvalue()


def to_markdown(merged: dict) -> str:
    table = rows(merged)
    lines = ["## open-agent-security: roll-up", "",
             "| " + " | ".join(table[0]) + " |", "|" + "---|" * len(table[0])]
    lines += ["| " + " | ".join(md_escape(c, dots=True) for c in row) + " |" for row in table[1:]]
    return "\n".join(lines) + "\n"
