"""GitLab SAST report (security report schema 15.2.5), for merge request security widgets.

GitLab does not ingest SARIF natively, so this is the format its security dashboards read.
Findings on this machine (--host) are left out, as in SARIF. Each vulnerability's id is the
finding's stable fingerprint written as a UUID; gaps in the scan become warn messages.
"""
from __future__ import annotations

import json
import uuid

from .. import __version__
from ..catalog import DOCS, RuleMeta
from ..model import Report
from ..output import safe_path
from .common import ReportOptions, rules_by_id, shared_lines

SCHEMA_VERSION = "15.2.5"
SEVERITY = {"critical": "Critical", "high": "High", "medium": "Medium", "low": "Low"}
TOOL = {"id": "open-agent-security", "name": "open-agent-security", "version": __version__, "url": DOCS,
        "vendor": {"name": "BRACE"}}


def identifiers(r: RuleMeta) -> list[dict]:
    """The rule first (GitLab's primary identifier), then its CWE entries."""
    cwes = [ref.partition(":")[2] for ref in r.refs if ref.startswith("cwe:")]
    return [{"type": "open_agent_security_rule", "name": f"{r.id}: {r.title}", "value": r.id, "url": r.help_uri},
            *({"type": "cwe", "name": f"CWE-{c}", "value": c, "url": f"https://cwe.mitre.org/data/definitions/{c}.html"}
              for c in cwes)]


def vulnerability(f, m: RuleMeta, shared: bool) -> dict:
    """One finding. When it shares its rule and line with another, its detail goes in the name and
    its short id in the location, which GitLab uses to tell findings apart."""
    location = {"file": safe_path(f.file), "start_line": max(1, f.line)}
    if shared:
        location["method"] = f"finding {f.id[:8]}"
    return {"id": str(uuid.UUID(hex=f.id)), "name": f"{m.title}: {f.detail}" if shared else m.title,
            "description": f"{m.why}\n\nFound: {f.detail}", "severity": SEVERITY[f.severity], "solution": m.fix,
            "identifiers": identifiers(m), "location": location}


def timestamp(t) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%S") if t else "1970-01-01T00:00:00"


class GitlabSast:
    name = "gitlab-sast"
    media = "json"

    def render(self, report: Report, opts: ReportOptions) -> str:
        meta = rules_by_id(report)
        shown = [f for f in report.findings if not f.host]
        shared = shared_lines(shown)
        vulns = [vulnerability(f, meta[f.rule], (f.rule, f.file, f.line) in shared) for f in shown]
        messages = [{"level": "info" if kind in ("info", "suppressed") else "warn", "value": text}
                    for text, kind in zip(report.notes, report.kinds)]
        host = sum(f.host for f in report.findings)
        if host:
            messages.append({"level": "info", "value": f"{host} finding(s) in agent settings on this machine are "
                                                       "not in this report; see the text or JSON output"})
        scan = {"analyzer": TOOL, "scanner": TOOL, "type": "sast", "status": "success",
                "start_time": timestamp(report.started), "end_time": timestamp(report.finished)}
        if messages:
            scan["messages"] = messages
        return json.dumps({"version": SCHEMA_VERSION, "scan": scan, "vulnerabilities": vulns}, indent=2) + "\n"
