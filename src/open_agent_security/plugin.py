"""The pluggability contract: what a collector, parser, check and reporter provide. Provisional.

Provisional and frozen: no changes to the plugin interfaces until there is a real plugin;
breaking changes would be called out in release notes.

The registry accepts any object with these members, and the built-ins follow the same
contract, so a plugin can do what a built-in does and no more. What a scan's trustworthiness
depends on stays in the engine, not here: redaction, inline marks and ignore entries,
de-duplication, the per-file cap, and turning a crash into a note and an incomplete scan.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable, Iterator, Literal, Protocol

if TYPE_CHECKING:
    from .engine import ScanContext
    from .model import CheckContext, Document, Finding, Project, Report, Skipped, SourceFile
    from .report import ReportOptions


class Collector(Protocol):
    """Where source files come from. Yields Skipped for a file it could not read; a required
    one makes the scan incomplete."""
    name: str

    def collect(self, ctx: ScanContext) -> Iterator[SourceFile | Skipped]: ...


class Parser(Protocol):
    """Turns a file it claims into facts on the Document. Raises ParseError when it cannot
    read one; for agent config that makes the scan incomplete."""
    name: str

    def claims(self, src: SourceFile) -> bool: ...

    def parse(self, src: SourceFile, doc: Document) -> None: ...


class Check(Protocol):
    """Turns facts into findings of the rules it emits. A file check runs on each Document;
    a project check keeps small facts per file (facts) and runs once on the Project."""
    name: str
    emits: tuple[str, ...]
    scope: Literal["file", "project"]

    def run(self, target: Document | Project, ctx: CheckContext) -> Iterable[Finding]: ...

    def facts(self, doc: Document) -> Any: ...  # project checks only; None keeps nothing


class Reporter(Protocol):
    """Renders a finished Report in one format, selected with --output NAME=FILE. `media` says
    how the command line makes the output inert when it goes to a GitHub Actions log: "json"
    or "text" (the default). `appends` (default False) appends to FILE instead of replacing it."""
    name: str
    media: str
    appends: bool

    def render(self, report: Report, opts: ReportOptions) -> str: ...
