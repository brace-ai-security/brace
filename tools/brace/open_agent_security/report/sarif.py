"""SARIF 2.1.0 for GitHub code scanning and other SARIF consumers.

Findings on this machine (--host) are left out, with a notification counting them. Each
result has a line-independent fingerprint, so a consumer can track a finding as code moves;
rules link to OWASP, MITRE ATLAS and CWE entries through run.taxonomies. The invocation always
says whether the scan was complete and how many findings were suppressed.

Suppressed findings (inline marks, ignore entries, rules turned off) are listed too, after the
reported ones, each with a SARIF suppression (SARIF 2.1.0 §3.27.23, §3.35): kind "inSource" or
"external", status "accepted" and a justification. Consumers such as GitHub code scanning then
show them as dismissed, not open, and an audit can see every suppression and why it was made.
They keep the ruleId, level, message, location and fingerprint they would have unsuppressed.
"""
from __future__ import annotations

import json

from .. import __version__
from ..catalog import DOCS, TAXA, TAXONOMIES, RuleMeta
from ..limits import MAX_RESULTS
from ..model import Finding, Report
from ..output import path_uri
from .common import ReportOptions, rules_by_id

SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
LEVEL = {"critical": "error", "high": "error", "medium": "warning", "low": "note"}
SECURITY_SEVERITY = {"critical": "9.5", "high": "8.0", "medium": "5.5", "low": "3.0"}
FINGERPRINT = "openAgentSecurity/v1"
SRCROOT = "%SRCROOT%"
# Notification descriptors, by the kind of note: gaps are warnings, the rest are notes.
NOTIFICATIONS = {
    "info": ("note", "A note about the scan."),
    "incomplete": ("warning", "The scan is incomplete: a file the rules need was not read or checked."),
    "skipped": ("warning", "Files could not be read."),
    "suppressed": ("note", "Ignore entries, inline marks, rules turned off or lowered limits hid findings or files."),
    "host-findings": ("note", "Findings in agent settings on this machine are in the text and JSON output only."),
    "results-capped": ("warning", "More results than one SARIF file lists; the JSON output has all of them."),
}


def split_ref(ref: str) -> tuple[str, str]:
    """("owasp-asi", "ASI02") from "owasp-asi:ASI02"."""
    prefix, _, entry = ref.partition(":")
    return prefix, entry


def rule_entry(r: RuleMeta) -> dict:
    checklist = f"BRACE checklist: {', '.join(r.checklist)}." if r.checklist else ""
    cwes = [entry for prefix, entry in map(split_ref, r.refs) if prefix == "cwe"]
    entry = {"id": r.id, "name": r.name, "shortDescription": {"text": r.title}, "fullDescription": {"text": r.why},
             "help": {"text": f"{r.fix} {checklist}".strip(),
                      "markdown": f"{r.why}\n\n**Fix:** {r.fix}\n\n{checklist} [Details]({r.help_uri})".replace(
                          "\n\n [", "\n\n[")},
             "helpUri": r.help_uri, "defaultConfiguration": {"level": LEVEL[r.severity]},
             "properties": {"security-severity": SECURITY_SEVERITY[r.severity],
                            "tags": ["security", "ai-agent", *(f"external/cwe/cwe-{c}" for c in cwes)]}}
    if r.refs:
        entry["relationships"] = [{"target": {"id": e, "toolComponent": {"name": TAXONOMIES[p].name}},
                                   "kinds": ["relevant"]} for p, e in map(split_ref, r.refs)]
    return entry


def taxonomies(rules) -> list[dict]:
    """One taxonomy per prefix the rules refer to, listing only the entries they use."""
    used: dict[str, dict[str, None]] = {}
    for r in rules:
        for ref in r.refs:
            used.setdefault(split_ref(ref)[0], {})[ref] = None
    return [{"name": t.name, **({"version": t.version} if t.version else {}), "informationUri": t.uri,
             "organization": t.organization, "isComprehensive": False,
             "taxa": [{"id": split_ref(ref)[1], **({"name": TAXA[ref]} if ref in TAXA else {})} for ref in used[p]]}
            for p, t in TAXONOMIES.items() if p in used]


def notification(kind: str, text: str) -> dict:
    return {"level": NOTIFICATIONS[kind][0], "descriptor": {"id": kind}, "message": {"text": text}}


def result(f: Finding, meta: dict) -> dict:
    out = {"ruleId": f.rule, "level": LEVEL[f.severity],
           "message": {"text": f"{meta[f.rule].title}: {f.detail}. {meta[f.rule].fix}"},
           "locations": [location(f.file, f.line)],
           "partialFingerprints": {FINGERPRINT: f.id}}
    s = f.suppression
    if s:
        sup = {"kind": s.kind, "status": "accepted", "justification": s.justification}
        if s.file:
            sup["location"] = location(s.file, s.line)
        out["suppressions"] = [sup]
    return out


def location(file: str, line: int) -> dict:
    return {"physicalLocation": {"artifactLocation": {"uri": path_uri(file), "uriBaseId": SRCROOT},
                                 "region": {"startLine": max(1, line)}}}


class Sarif:
    name = "sarif"
    media = "json"

    def render(self, report: Report, opts: ReportOptions) -> str:
        meta = {**{r.id: r for r in report.rules_off}, **rules_by_id(report)}
        shown = [f for f in report.findings if not f.host]
        hidden = [f for f in report.suppressed if not f.host]
        # Reported results come first, so the cap never pushes one out for a suppressed one.
        listed = (shown + hidden)[:MAX_RESULTS]
        results = [result(f, meta) for f in listed]
        notes = [notification(kind, text) for text, kind in zip(report.notes, report.kinds)]
        host = len(report.findings) - len(shown)
        if host:
            notes.append(notification("host-findings", f"{host} finding(s) in agent settings on this machine are "
                                                       "not in SARIF; see the text or JSON output"))
        if len(shown) + len(hidden) > MAX_RESULTS:
            notes.append(notification("results-capped", f"{len(shown) + len(hidden) - MAX_RESULTS} more results "
                                                        "are not listed; see the JSON output"))
        driver = {"name": "open-agent-security", "version": __version__, "informationUri": DOCS,
                  "rules": [rule_entry(r) for r in report.rules] +
                           [rule_entry(r) for r in report.rules_off if r.id in {f.rule for f in listed}],
                  "notifications": [{"id": kind, "shortDescription": {"text": text},
                                     "defaultConfiguration": {"level": level}}
                                    for kind, (level, text) in NOTIFICATIONS.items()]}
        run = {"tool": {"driver": driver},
               "originalUriBaseIds": {SRCROOT: {"description": {"text": (
                   "The folder the scan ran from when the scanned folder is inside it, else the scanned folder.")}}},
               "invocations": [{"executionSuccessful": True, "toolExecutionNotifications": notes,
                                "properties": {"incomplete": report.verdict == "incomplete",
                                               "suppressed": report.tally.suppressed}}],
               "results": results}
        tax = taxonomies(report.rules)
        if tax:
            run["taxonomies"] = tax
        return json.dumps({"version": "2.1.0", "$schema": SCHEMA, "runs": [run]}, indent=2)
