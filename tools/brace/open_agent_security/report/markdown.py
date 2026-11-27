"""A Markdown summary for pull requests and the GitHub job summary."""
from __future__ import annotations

from ..limits import MAX_NOTES, MAX_ROWS
from ..model import Report
from ..output import md_escape
from .common import INCOMPLETE, ReportOptions, headline, rules_by_id


class Markdown:
    name = "markdown"
    media = "text"
    appends = True  # to a job summary such as $GITHUB_STEP_SUMMARY

    def render(self, report: Report, opts: ReportOptions) -> str:
        findings, out = report.findings, []
        if not findings and report.verdict == "clean":
            out.append(f"### open-agent-security: no known-dangerous agent setups found\n\n"
                       f"Checked {len(report.rules)} anti-patterns. This is not a full review; see the "
                       f"[BRACE checklist](https://braceframework.org/checklist/).\n")
        elif not findings and report.verdict == "incomplete":
            out.append("### open-agent-security: the scan is incomplete and cannot report this folder clean\n")
        elif not findings:
            out.append(f"### open-agent-security\n\n{headline(report)}\n")
        else:
            meta = rules_by_id(report)
            out += ["### open-agent-security", ""] + ([INCOMPLETE, ""] if report.verdict == "incomplete" else [])
            out += ["| Severity | Problem | Where | Fix |", "|---|---|---|---|"]
            for f in findings[:MAX_ROWS]:
                m = meta[f.rule]
                out.append(f"| {f.severity} | [{md_escape(m.title)}]({m.help_uri}) | "
                           f"{md_escape(f.file, dots=True)}:{f.line} | {md_escape(m.fix)} |")
            if len(findings) > MAX_ROWS:
                out.append(f"\nand {len(findings) - MAX_ROWS} more (see the SARIF or JSON output)")
            out.append("")
        for n in report.notes[:MAX_NOTES]:
            out.append(f"- note: {md_escape(n, dots=True)}")
        if len(report.notes) > MAX_NOTES:
            out.append(f"- and {len(report.notes) - MAX_NOTES} more notes (see the JSON output)")
        return "\n".join(out) + "\n"
