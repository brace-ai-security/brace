"""What every reporter shares: the options it is given and the clean-or-not headline."""
from __future__ import annotations

from dataclasses import dataclass

from ..output import plural


@dataclass(frozen=True)
class ReportOptions:
    color: bool = False
    sarif_suppressed: bool = False   # list suppressed findings in SARIF (--sarif-suppressed)


def shared_lines(findings) -> set[tuple]:
    """(rule, file, line) that more than one finding shares, such as three AP04s on line 1 of a
    minified .mcp.json: outputs that name a finding by its place tell those apart."""
    seen: set[tuple] = set()
    shared: set[tuple] = set()
    for f in findings:
        key = (f.rule, f.file, f.line)
        (shared if key in seen else seen).add(key)
    return shared


def rules_by_id(report) -> dict:
    return {r.id: r for r in report.rules}


INCOMPLETE = "The scan is incomplete (see the notes)."  # the headline above findings when the scan is incomplete


def headline(report) -> str:
    """The one-line verdict when there are no findings, shared by the text and Markdown reports."""
    if report.verdict == "incomplete":
        return "The scan is incomplete (see the notes), so it cannot say this folder is clean."
    if report.verdict == "unread":
        return (f"Nothing dangerous found in the files read, but {plural(report.skipped, 'file')} could not be "
                "read (see the notes).")
    return "No known-dangerous agent setups found."


def fence(text: str, lang: str = "text") -> str:
    """text as a Markdown fenced code block, with a fence longer than any run of backticks in it,
    so the text cannot close the block early."""
    longest = run = 0
    for ch in text:
        run = run + 1 if ch == "`" else 0
        longest = max(longest, run)
    ticks = "`" * max(3, longest + 1)
    return f"{ticks}{lang}\n{text}\n{ticks}"


def examples_markdown(r) -> str:
    """A rule's before and after examples (and its template) as Markdown, or ''."""
    parts = []
    if r.example_bad:
        parts.append(f"**Before:**\n\n{fence(r.example_bad)}")
    if r.example_good:
        parts.append(f"**After:**\n\n{fence(r.example_good)}")
    if r.template:
        parts.append(f"**Hardened template:** `{r.template.replace('`', '')}`")
    return "\n\n".join(parts)
