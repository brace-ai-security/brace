"""Step outputs for the GitHub Action: the finding count and whether the scan is incomplete."""
from __future__ import annotations

from ..model import Report
from .common import ReportOptions


class GithubOutput:
    name = "github-output"
    media = "text"
    appends = True  # to $GITHUB_OUTPUT

    def render(self, report: Report, opts: ReportOptions) -> str:
        return f"findings={len(report.findings)}\nincomplete={str(report.verdict == 'incomplete').lower()}\n"
