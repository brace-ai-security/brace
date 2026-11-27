"""A Markdown summary for pull requests and the GitHub job summary."""
from __future__ import annotations

from ..limits import MAX_NOTES, MAX_ROWS
from ..model import Report
from ..output import md_escape
from .common import INCOMPLETE, ReportOptions, examples_markdown, headline, rules_by_id


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
            out += rule_sections(findings, meta)
        for n in report.notes[:MAX_NOTES]:
            out.append(f"- note: {md_escape(n, dots=True)}")
        if len(report.notes) > MAX_NOTES:
            out.append(f"- and {len(report.notes) - MAX_NOTES} more notes (see the JSON output)")
        return "\n".join(out) + "\n"


def rule_sections(findings, meta) -> list[str]:
    """One section per rule found, in order of first finding: why, the fix, a before and after
    example and the hardened template, folded so the table stays the summary."""
    out = []
    for rule in dict.fromkeys(f.rule for f in findings):
        m = meta[rule]
        body = examples_markdown(m)
        out += ["<details>", f"<summary>{md_escape(rule)}: {md_escape(m.title)}</summary>", "",
                f"**Why:** {md_escape(m.why)}", "", f"**Fix:** {md_escape(m.fix)}", ""]
        if body:
            out += [body, ""]
        out += ["</details>", ""]
    return out
