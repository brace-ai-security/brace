"""Plain-language terminal output, grouped by rule, with why and how to fix."""
from __future__ import annotations

from ..catalog import SEVERITY_ORDER
from ..ignore import IGNORE_FILE, IGNORE_MARK
from ..limits import MAX_PLACES
from ..model import Finding, Report
from ..output import plural, shown_path
from .common import INCOMPLETE, ReportOptions, headline, rules_by_id

COLORS = {"critical": "\033[1;31m", "high": "\033[31m", "medium": "\033[33m", "low": "\033[36m",
          "dim": "\033[2m", "bold": "\033[1m", "end": "\033[0m"}


class Text:
    name = "text"
    media = "text"

    def render(self, report: Report, opts: ReportOptions) -> str:
        c = COLORS if opts.color else {}

        def g(k):
            return c.get(k, "")
        findings, meta = report.findings, rules_by_id(report)
        lines = []
        if not findings:
            lines.append(f"{g('bold')}{headline(report)}{g('end')}")
        elif report.verdict == "incomplete":
            lines.append(f"{g('bold')}{INCOMPLETE}{g('end')}")
        if not findings and report.verdict != "incomplete":
            lines.append(f"{g('dim')}This checks {len(report.rules)} anti-patterns only. It is not a security review; "
                         f"see https://braceframework.org/checklist/ for the full sign-off.{g('end')}")
        groups: dict[str, list[Finding]] = {}
        for f in findings:
            groups.setdefault(f.rule, []).append(f)
        for rule, fs in groups.items():
            f, m = fs[0], meta[rule]
            lines.append(f"{g(f.severity)}✗ {f.severity.upper():8}{g('end')} {g('bold')}{m.title}{g('end')}  "
                         f"{g('dim')}[{rule}] ×{len(fs)}{g('end')}")
            for x in fs[:MAX_PLACES]:
                lines.append(f"    {shown_path(x.file)}:{x.line}  {g('dim')}{x.detail}{g('end')}")
            if len(fs) > MAX_PLACES:
                lines.append(f"    {g('dim')}… and {len(fs) - MAX_PLACES} more (use --json for all){g('end')}")
            lines.append(f"    Why:  {m.why}")
            lines.append(f"    Fix:  {m.fix}")
            checklist = f"BRACE checklist {', '.join(m.checklist)} · " if m.checklist else ""
            lines.append(f"    {g('dim')}{checklist}{m.help_uri}{g('end')}")
            lines.append("")
        if findings:
            counts = {s: sum(1 for f in findings if f.severity == s) for s in SEVERITY_ORDER}
            summary = ", ".join(f"{n} {s}" for s, n in counts.items() if n)
            lines.append(f"{summary}  ({plural(len(findings), 'finding')}). "
                         f"Silence a reviewed line with an '{IGNORE_MARK}' comment, or add an entry to {IGNORE_FILE}.")
        for n in report.notes:
            lines.append(f"{g('dim')}note: {n}{g('end')}")
        out = "\n".join(lines) + "\n"
        return out
