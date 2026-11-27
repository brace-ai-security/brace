"""The data that flows through the pipeline: collect -> parse -> check -> filter -> report.

Collectors produce SourceFiles, parsers turn them into Documents of facts, checks turn facts
into Findings and the engine gathers everything into a Report. File checks see one whole
Document, raw text included, and it is dropped once they have run. Project checks see only
the facts each of them declared it keeps from a file (Check.facts), so memory stays bounded by
those small facts, not by the files read.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping

from .jsonc import JsonLines, load_json_text
from .limits import LISTED_FILES, LISTED_PATH_CHARS, NOTE_CHARS
from .output import clean, size_label
from .secrets import DEFAULT, Secrets


@dataclass(frozen=True)
class SourceFile:
    display: str                 # repo-relative, or ~/... for a file on this machine
    origin: str                  # "repo" | "host"
    text: str
    is_ci: bool = False
    is_agent_config: bool = False
    server_keys: tuple[str, ...] | None = None  # JSON keys that hold MCP servers; None: infer from the path
    project: Path | None = None  # host files: read only this project's block in ~/.claude.json


@dataclass(frozen=True)
class Skipped:
    """A file a collector could not read. A required one makes the scan incomplete."""
    display: str
    reason: str                  # a ReadFailure reason: "oversized", "symlink", "not a regular file", "unreadable"
    required: bool = False       # the rules must read it: agent config, CI, a Dockerfile or a script
    size_limit: int = 0


@dataclass(frozen=True)
class Server:
    path: tuple                  # JSON path, for line lookup
    name: str
    command: str                 # the program, normalised to a runner such as npx when it wraps one
    args: tuple[str, ...]
    env: Mapping[str, Any]
    headers: Mapping[str, Any]
    url: str
    raw: Mapping                 # the original entry, so odd shapes are not lost


@dataclass(frozen=True)
class Permissions:
    allow: tuple[str, ...] = ()
    default_mode: Any = None
    env: Mapping[str, Any] | None = None  # top-level env, read only where it configures an agent


@dataclass(frozen=True)
class Image:
    ref: str
    line: int
    stage: bool                  # names an earlier build stage, not a registry image


@dataclass(frozen=True)
class WorkflowFacts:
    trigger_line: int | None     # first line that triggers on pull_request_target
    agent_step: bool             # a step runs an agent
    local_uses: tuple[str, ...] = ()  # local actions and reusable workflows it uses (`./.github/actions/x`)


class ParseError(Exception):
    """A parser could not read a file it claims. The engine notes it for agent config files."""


@dataclass
class Document:
    """One file and the facts its parsers found. Parsers fill it in; checks then read it.

    Line numbers come from an index of the JSON keys unless a parser sets its own with
    use_lines(); only one may, so two parsers cannot silently disagree about lines."""
    source: SourceFile
    servers: list[Server] = field(default_factory=list)
    permissions: Permissions | None = None
    images: list[Image] = field(default_factory=list)
    workflow: WorkflowFacts | None = None
    full_access: list[tuple[tuple, str]] = field(default_factory=list)  # (key path, detail): Codex full access
    data: Any = None             # the parsed document, for parsers that do not read JSON (Codex's TOML)

    def __post_init__(self):
        self._json: tuple | None = None
        self._lines: Callable[[tuple], int] | None = None

    def json(self):
        """The parsed JSON or JSONC, loaded at most once; raises ParseError when the text is neither."""
        if self._json is None:
            self._json = load_json_text(self.source.text)
        data, err = self._json
        if err:
            raise ParseError(err)
        return data

    def use_lines(self, line_of: Callable[[tuple], int]) -> None:
        if self._lines is not None:
            raise ValueError("two parsers set line numbers for one file")
        self._lines = line_of

    def line_of(self, path: tuple) -> int:
        """The line of a key path such as ("mcpServers", "github", "env", "TOKEN")."""
        if self._lines is None:
            self._lines = JsonLines(self.source.text).at
        return self._lines(path)


@dataclass(frozen=True)
class Project:
    """What project checks see: per check, the facts it kept from each file."""
    facts: Mapping[str, tuple]   # check name -> one value per file it kept facts from
    is_agent_repo: bool          # an agent runs here, so image pinning matters

    def of(self, check) -> tuple:
        return self.facts.get(check.name, ())


@dataclass(frozen=True)
class CheckContext:
    secrets: Secrets = DEFAULT   # built-in token formats plus the config's custom tokens


@dataclass(frozen=True)
class Suppression:
    """How a finding was suppressed, for the SARIF and JSON outputs: "inSource" (an inline mark)
    or "external" (an ignore entry or a rule turned off), why, and where the suppression is
    written when that is a file in the scanned folder (file "" when not known)."""
    kind: str
    justification: str
    file: str = ""
    line: int = 0


@dataclass(frozen=True)
class Edit:
    """A fix that follows from the finding alone, safe to apply without judgement: on `line`,
    replace columns start..end (1-based, end exclusive, counted in UTF-16 code units as SARIF
    counts them by default) holding `deleted` with `replacement` ("" removes it). Checks set one
    only when the change is unambiguous offline, such as removing a bypass flag from a command
    line; never for a change that needs information the scan does not have (a version, a digest)."""
    line: int
    start: int
    end: int
    deleted: str
    replacement: str
    description: str


@dataclass
class Finding:
    """Checks set rule, file, line and detail; the engine sets the effective severity and host.
    Title, why, fix and checklist items are the rule's, in Report.rules."""
    rule: str
    file: str
    line: int
    detail: str
    severity: str = ""
    host: bool = False  # a file on this machine, not in the scanned folder
    id: str = ""        # a stable fingerprint, set by the engine
    suppression: Suppression | None = None  # set by the engine on a suppressed finding
    edit: Edit | None = None  # a deterministic fix, when one exists (see Edit)


SKIP_LABELS = {"symlink": "symlink(s), not followed", "not a regular file": "special file(s) such as FIFOs"}


@dataclass
class Tally:
    """Everything that hid findings or files from one scan, counted as it runs. A pull request
    can add any of these, so suppression.py turns them into a note every output carries."""
    rules_off: int = 0
    overrides: int = 0                 # rules re-rated to another severity
    config_ignores: int = 0            # config ignore entries, one per path and rule
    ignore_file_entries: int = 0
    lowered: tuple[str, ...] = ()      # limits set below the defaults, as shown
    by_mark: int = 0                   # findings dropped by an inline ignore mark
    suppressed: int = 0                # findings dropped by ignore entries, inline marks or rules turned off
    files: int = 0                     # files not read because an ignore entry matched them
    own_reports: int = 0               # this scanner's own report files, not scanned
    folders: int = 0                   # folders not entered because an ignore entry matched them
    dependency_dirs: dict[str, int] = field(default_factory=dict)  # never entered, by name
    other_dirs: dict[str, int] = field(default_factory=dict)       # version control and caches, by name
    links_inside: int = 0              # symlinks to paths the walk reads where they point, not followed
    link_names: list[str] = field(default_factory=list)            # the first LISTED_FILES of them


@dataclass
class Report:
    """The result of a scan, and the one place that decides what the scan can claim.

    Every note goes through note(), which cleans and redacts it once. fail(), truncate() and
    skip() are the only ways to record a gap, and verdict reads them, so the text headline,
    Markdown, JSON, SARIF, GitHub outputs and the exit code cannot disagree."""
    findings: list[Finding] = field(default_factory=list)
    suppressed: list[Finding] = field(default_factory=list)  # at most MAX_SUPPRESSED; never in the verdict
    notes: list[str] = field(default_factory=list)
    kinds: list[str] = field(default_factory=list)  # one per note: "info", "incomplete", "skipped" or "suppressed"
    truncated: bool = False      # stopped at the file limit
    incomplete: bool = False     # a required file could not be read, agent config did not parse, or a check failed
    skipped: int = 0             # files the scan wanted to read but could not
    config: str | None = None    # the config file that was applied
    rules: tuple = ()            # RuleMeta of every rule that ran, with effective severity
    rules_off: tuple = ()        # RuleMeta of the rules turned off, for their suppressed findings
    tally: Tally = field(default_factory=Tally)
    secrets: Secrets = DEFAULT   # what note() redacts: built-in token formats plus the config's
    inventory: list = field(default_factory=list)  # agent config files and MCP servers seen (inventory.py)
    started: datetime | None = None   # UTC, set by the engine
    finished: datetime | None = None

    def note(self, text: str, kind: str = "info") -> None:
        self.notes.append(clean(text, NOTE_CHARS, secrets=self.secrets))
        self.kinds.append(kind)

    def fail(self, text: str) -> None:
        """A gap in what was read or checked: the scan cannot call itself complete."""
        self.incomplete = True
        self.note(text, "incomplete")

    def truncate(self, text: str) -> None:
        """The walk stopped early (the file limit)."""
        self.truncated = True
        self.note(text, "incomplete")

    def skip(self, skipped: list[Skipped], prefix: str = "") -> None:
        """Files a collector could not read, as one note per reason, each path shown with the
        prefix findings carry. A required one makes the scan incomplete; any skipped file keeps
        the headline from saying clean."""
        groups: dict[str, list[Skipped]] = {}
        for s in skipped:
            groups.setdefault(s.reason, []).append(s)
            self.incomplete = self.incomplete or s.required
            self.skipped += 1
        for reason, group in groups.items():
            label = f"file(s) over {size_label(group[0].size_limit)}" if reason == "oversized" else \
                SKIP_LABELS.get(reason, "file(s) unreadable or binary")
            shown = ", ".join(clean(prefix + s.display, LISTED_PATH_CHARS, redact=False) for s in group[:LISTED_FILES])
            more = f" and {len(group) - LISTED_FILES} more" if len(group) > LISTED_FILES else ""
            self.note(f"skipped {len(group)} {label}: {shown}{more}", "skipped")

    @property
    def verdict(self) -> str:
        """What the scan can say about what it did not see: "incomplete" (a gap the rules needed,
        or the walk stopped), "unread" (other files could not be read) or "clean" (nothing missed)."""
        if self.truncated or self.incomplete:
            return "incomplete"
        return "unread" if self.skipped else "clean"
