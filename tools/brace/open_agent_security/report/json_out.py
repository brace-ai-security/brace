"""JSON output: every finding with its metadata, for scripts.

The shape is described by report/schema/report-1.schema.json, shipped in the package; the
`schema` key names it. New keys may be added; existing ones keep their meaning until the
schema's number changes.
"""
from __future__ import annotations

import json

from .. import __version__
from ..catalog import RuleMeta
from ..model import Finding, Report
from ..output import safe_path
from .common import ReportOptions, rules_by_id

SCHEMA = "https://braceframework.org/tools/brace/open_agent_security/report/schema/report-1.schema.json"


# The report's top-level keys (collect/repo.py knows a report by them, so it does not scan one).
KEYS = frozenset({"schema", "scanner", "version", "rules", "truncated", "incomplete", "findings", "notes",
                  "suppressed", "config"})


def finding(f: Finding, m: RuleMeta) -> dict:
    """One finding with its rule's metadata, in the public key order."""
    return {"rule": f.rule, "file": safe_path(f.file), "line": f.line, "detail": f.detail, "severity": f.severity,
            "title": m.title, "why": m.why, "fix": m.fix, "items": list(m.checklist), "host": f.host, "id": f.id}


class Json:
    name = "json"
    media = "json"  # how the CLI makes it inert in a GitHub Actions log

    def render(self, report: Report, opts: ReportOptions) -> str:
        meta = rules_by_id(report)
        return json.dumps({"schema": SCHEMA, "scanner": "open-agent-security", "version": __version__,
                           "rules": len(report.rules),
                           "truncated": report.truncated, "incomplete": report.verdict == "incomplete",
                           "findings": [finding(f, meta[f.rule]) for f in report.findings],
                           "notes": report.notes,
                           "suppressed": report.tally.suppressed, "config": report.config}, indent=2) + "\n"
