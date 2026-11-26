"""What every reporter shares: the options it is given and the clean-or-not headline."""
from __future__ import annotations

from dataclasses import dataclass

from ..output import plural


@dataclass(frozen=True)
class ReportOptions:
    color: bool = False


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


def headline(report) -> str:
    """The one-line verdict when there are no findings, shared by the text and Markdown reports."""
    if report.verdict == "incomplete":
        return "The scan is incomplete (see the notes), so it cannot say this folder is clean."
    if report.verdict == "unread":
        return (f"Nothing dangerous found in the files read, but {plural(report.skipped, 'file')} could not be "
                "read (see the notes).")
    return "No known-dangerous agent setups found."
