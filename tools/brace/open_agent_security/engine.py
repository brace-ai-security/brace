"""The one pipeline: collect -> parse -> check -> filter -> report.

The engine, not the plugins, owns everything a scan's trustworthiness depends on: every
detail is redacted, inline marks, ignore entries and disabled rules are applied, findings
are de-duplicated, and a parser or check that crashes turns into a note and an incomplete
scan. A plugin cannot make a scan look clean by failing.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone

from .agents import AGENT_SIGNAL, SHARED_SETTINGS
from .catalog import SEVERITY_ORDER, RuleMeta
from .config import Config
from .inventory import record as record_inventory
from .ignore import IGNORE_FILE, IGNORE_MARK, Ignores, load_ignores, marked_lines
from .limits import MAX_INVENTORY, MAX_PER_FILE, MAX_SUPPRESSED, NOTE_CHARS, NOTE_PATH_CHARS
from .model import (CheckContext, Document, Finding, ParseError, Project, Report, Skipped, SourceFile, Suppression,
                    Tally)
from .output import clean, path_bytes, plural
from .registry import Registry
from .secrets import Secrets
from .suppression import lowered, skipped_dirs_notes, suppression_note


@dataclass
class ScanContext:
    """One scan in progress. Collectors read config and ignores and record what they skip on
    report (report.truncate, report.tally); the rest is the engine's own bookkeeping."""
    config: Config
    registry: Registry
    report: Report
    ignores: Ignores
    check_ctx: CheckContext
    enabled: set[str]
    rules: dict[str, RuleMeta]                                # rule id -> effective metadata
    facts: dict[str, list] = field(default_factory=dict)      # project check name -> its facts, one per file
    origins: dict[str, str] = field(default_factory=dict)     # file -> origin, for files with facts
    marks: dict[str, set[int]] = field(default_factory=dict)  # file -> marked lines, kept for files with facts
    capped: set[str] = field(default_factory=set)             # files already noted as over MAX_PER_FILE
    capped_suppressed: bool = False                           # past MAX_SUPPRESSED, noted once
    agent_repo: bool = False                                  # an agent runs in the scanned folder
    inventory_full: bool = False                              # past MAX_INVENTORY, noted once


def run_scan(config: Config, registry: Registry) -> Report:
    rules = tuple(replace(m, severity=config.rules.get(m.id, m.severity)) for m in registry.rules.values()
                  if m.id not in config.disabled)
    secrets = Secrets(config.tokens)
    off = len(config.disabled)
    tally = Tally(rules_off=off, overrides=len(config.rules) - off, config_ignores=len(config.ignore),
                  lowered=lowered(config.limits))
    report = Report(rules=rules, rules_off=tuple(m for m in registry.rules.values() if m.id in config.disabled),
                    config=config.path, tally=tally, secrets=secrets, started=now())
    for n in config.notes:
        report.note(n)
    from_file, notes = load_ignores(config.root, config.limits.max_file_bytes, registry.rules) if config.root else ([], [])
    for n in notes:
        report.note(n)
    unknown = sorted({e.rule for e in from_file if e.rule and e.rule not in registry.rules})
    if unknown:
        report.note(f"ignore file: unknown rule {', '.join(unknown[:5])}; those entries match nothing")
    tally.ignore_file_entries = len(from_file)
    ctx = ScanContext(config, registry, report, Ignores(list(config.ignore) + from_file), CheckContext(secrets),
                      {m.id for m in rules}, {m.id: m for m in rules})
    for collector in registry.collectors:
        skipped: list[Skipped] = []
        try:
            for item in collector.collect(ctx):
                if isinstance(item, Skipped):
                    skipped.append(item)
                else:
                    scan_file(ctx, item)
        except Exception as e:
            report.fail(f"could not collect {collector.name}: {type(e).__name__}")
        report.skip(skipped, config.display_prefix if collector.name == "repo" else "")
    for n in skipped_dirs_notes(tally):
        report.note(n)
    run_project_checks(ctx)
    # Ids hash the path within the scanned folder. Paths stay exact (a name that is not UTF-8
    # included): machine outputs need the real file; human outputs show output.shown_path() of it.
    # Suppressed findings get their ids together with the reported ones, so each id is the one
    # the finding would have unsuppressed: removing a suppression does not make a "new" finding.
    every = [prefixed(f, "" if f.host else config.display_prefix)
             for f in assign_ids(dedupe(report.findings + report.suppressed))]
    report.findings = [f for f in every if f.suppression is None]
    report.suppressed = [f for f in every if f.suppression is not None]
    if tally.own_reports:
        report.note(f"skipped {plural(tally.own_reports, 'open-agent-security report file')}")
    note = suppression_note(tally, config.path)
    if note:
        report.note(note, "suppressed")
    report.finished = now()
    return report


def prefixed(f: Finding, prefix: str) -> Finding:
    """The finding with its path, and its suppression's file, as shown from where the scan ran."""
    s = f.suppression
    return replace(f, file=prefix + f.file, suppression=replace(s, file=prefix + s.file) if s and s.file else s)


def now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def enabled_checks(ctx: ScanContext, scope: str) -> list:
    """Checks of this scope. A check whose rules are all off still runs, so what it finds is listed
    as suppressed; if it fails, that is only a note (see check_failed)."""
    return [c for c in ctx.registry.checks if c.scope == scope]


def check_failed(ctx: ScanContext, check, text: str) -> None:
    """A failed check makes the scan incomplete, unless every rule it emits is turned off."""
    if set(check.emits) & ctx.enabled:
        ctx.report.fail(text)
    else:
        ctx.report.note(f"{text} (its rules are off)")


def agent_evidence(src: SourceFile, doc: Document) -> bool:
    """Whether a repository file shows that an agent runs here: agent config (an editor's
    general settings only when they hold MCP servers or permissions), or an agent SDK, action
    or package. Project checks such as AP10 report only in such a folder."""
    general = SHARED_SETTINGS.search(src.display) and not (doc.servers or doc.permissions)
    return bool((src.is_agent_config and not general) or AGENT_SIGNAL.search(src.text))


def scan_file(ctx: ScanContext, src: SourceFile) -> None:
    """Parse one file, run the file checks on it and give each project check its facts.
    A check that crashes loses only its own findings for this file, and makes the scan incomplete."""
    shown = clean(src.display, NOTE_PATH_CHARS, redact=False)
    marks = marked_lines(src.text) if src.origin == "repo" else set()
    if marks:
        ctx.marks[src.display] = marks
    try:
        doc = parse_file(ctx, src, shown)
    except Exception as e:  # one odd file must not end the scan
        ctx.report.fail(f"could not scan {shown}: {type(e).__name__}")
        ctx.marks.pop(src.display, None)
        return
    if src.origin == "repo" and not ctx.agent_repo:
        ctx.agent_repo = agent_evidence(src, doc)
    take_inventory(ctx, doc, shown)
    for check in enabled_checks(ctx, "file"):
        for f in filter_and_cap(ctx, checked(ctx, check, doc, shown), src.origin):
            f.host = src.origin == "host"
            ctx.report.findings.append(f)
    collect_facts(ctx, src, doc, shown)
    if src.display not in ctx.origins:  # only project checks' findings need a file's marks later
        ctx.marks.pop(src.display, None)


def take_inventory(ctx: ScanContext, doc: Document, shown: str) -> None:
    """List the file's agent config and MCP servers for the inventory outputs. A failure here
    loses only the inventory entry, never findings, and is noted."""
    if ctx.inventory_full:
        return
    try:
        if not record_inventory(doc, ctx.config.display_prefix, ctx.report.inventory):
            ctx.inventory_full = True
            ctx.report.note(f"inventory: stopped listing at {MAX_INVENTORY} agent config files and MCP servers")
    except Exception as e:
        ctx.report.note(f"inventory: could not list {shown}: {type(e).__name__}")


def checked(ctx: ScanContext, check, doc: Document, shown: str):
    """A file check's findings as it yields them. If it crashes, what it found before still counts
    and the scan is incomplete."""
    try:
        for f in check.run(doc, ctx.check_ctx):
            yield declared(f, check)
    except Exception as e:
        check_failed(ctx, check, f"could not scan {shown} with check {check.name}: {type(e).__name__}")


def collect_facts(ctx: ScanContext, src: SourceFile, doc: Document, shown: str) -> None:
    """Give each project check the facts it keeps from this file."""
    for check in enabled_checks(ctx, "project"):
        try:
            value = check.facts(doc)
        except Exception as e:
            check_failed(ctx, check, f"could not scan {shown} with check {check.name}: {type(e).__name__}")
            continue
        if value is not None:
            ctx.facts.setdefault(check.name, []).append(value)
            ctx.origins[src.display] = src.origin


def parse_file(ctx: ScanContext, src: SourceFile, shown: str) -> Document:
    """The file's Document. A parse failure of an agent config file makes the scan incomplete."""
    doc = Document(src)
    parse_failed = ""
    for parser in ctx.registry.parsers:
        if parser.claims(src):
            try:
                parser.parse(src, doc)
            except ParseError as e:
                parse_failed = str(e)
    if parse_failed and src.is_agent_config:
        ctx.report.fail(f"could not parse {shown}; its findings are unknown" if src.origin == "repo"
                        else f"could not parse {shown}: {parse_failed}")
    return doc


def run_project_checks(ctx: ScanContext) -> None:
    # Any repository finding also shows an agent runs here.
    agent_repo = ctx.agent_repo or any(not f.host for f in ctx.report.findings)
    project = Project({name: tuple(values) for name, values in ctx.facts.items()}, agent_repo)
    for check in enabled_checks(ctx, "project"):
        try:
            by_file: dict[str, list[Finding]] = {}
            for f in check.run(project, ctx.check_ctx):
                f = declared(f, check)
                by_file.setdefault(f.file, []).append(f)
            for file, findings in by_file.items():
                for f in filter_and_cap(ctx, findings, ctx.origins.get(file, "repo")):
                    f.host = ctx.origins.get(file) == "host"
                    ctx.report.findings.append(f)
        except Exception as e:
            check_failed(ctx, check, f"could not run check {check.name}: {type(e).__name__}")


def declared(f: Finding, check) -> Finding:
    """A check may only emit the rules it declared."""
    if not isinstance(f, Finding) or f.rule not in check.emits:
        raise ValueError(f"check {check.name} emitted an undeclared rule")
    return f


def filter_and_cap(ctx: ScanContext, findings, origin: str) -> list[Finding]:
    """The distinct findings of one check on one file that survive the filters, at most MAX_PER_FILE,
    each finalized (redacted, then cut) as it arrives, so no raw detail is kept. Suppression
    comes first, so suppressed findings cannot use up the cap; the rest of the check's output is
    still drained so suppressed counts stay right. Suppressed findings are kept apart, up to
    MAX_SUPPRESSED, for the outputs that list them; they never count towards the verdict."""
    out: list[Finding] = []
    seen: set[tuple] = set()
    for f in findings:
        f = finalize(f, ctx.rules.get(f.rule) or ctx.registry.rules.get(f.rule), ctx.check_ctx.secrets)
        f.host = origin == "host"
        if (f.rule, f.line, f.detail) in seen:
            continue
        seen.add((f.rule, f.line, f.detail))
        how = suppression(ctx, f, origin)
        if how:
            keep_suppressed(ctx, replace(f, suppression=how))
            continue
        if len(out) >= MAX_PER_FILE:
            note_capped(ctx, f.file)
            continue
        out.append(f)
    return out


def suppression(ctx: ScanContext, f: Finding, origin: str) -> Suppression | None:
    """Apply disabled rules, inline marks and ignore entries (repository files only); count what
    they drop, and say how each was dropped (None: the finding is reported)."""
    config = ctx.config.path or "the config"
    how = None
    if f.rule not in ctx.enabled:
        how = Suppression("external", f"rule {f.rule} turned off in {config}")
    elif origin != "repo":
        return None
    elif f.line in ctx.marks.get(f.file, ()):
        how = Suppression("inSource", f"inline '{IGNORE_MARK}' mark on line {f.line}", f.file, f.line)
        ctx.report.tally.by_mark += 1
    else:
        entry = ctx.ignores.deciding(f.file, f.rule)
        if entry is None or entry.neg:
            return None
        if entry.source == IGNORE_FILE:
            how = Suppression("external", f"{IGNORE_FILE} entry '{entry.text}'", IGNORE_FILE, entry.line)
        else:
            how = Suppression("external", entry.reason or f"config ignore entry '{entry.text}' in {entry.source}")
    ctx.report.tally.suppressed += 1
    # The justification quotes the scanned folder's own files, so it is cleaned like a note.
    return replace(how, justification=clean(how.justification, NOTE_CHARS, secrets=ctx.check_ctx.secrets))


def keep_suppressed(ctx: ScanContext, f: Finding) -> None:
    """Keep a suppressed finding for SARIF and JSON, up to MAX_SUPPRESSED; past it, only count it."""
    kept = ctx.report.suppressed
    if len(kept) < MAX_SUPPRESSED:
        kept.append(f)
    elif not ctx.capped_suppressed:
        ctx.capped_suppressed = True
        ctx.report.note(f"more than {MAX_SUPPRESSED} findings suppressed; only the first {MAX_SUPPRESSED} are "
                        "listed in SARIF and JSON", "suppressed")


def note_capped(ctx: ScanContext, file: str) -> None:
    """A capped file hides findings, so the scan cannot call itself complete."""
    ctx.report.incomplete = True
    if file not in ctx.capped:
        ctx.capped.add(file)
        ctx.report.fail(f"more than {MAX_PER_FILE} findings of one kind in "
                        f"{clean(file, NOTE_PATH_CHARS, redact=False)}; some are not shown")


def finalize(f: Finding, meta: RuleMeta | None, secrets: Secrets) -> Finding:
    """The effective severity (None: a rule turned off, about to be dropped), and the redaction
    every detail goes through. This is the only place a detail is cleaned, so no check can leak
    part of a secret by cutting it first."""
    return replace(f, detail=clean(f.detail, secrets=secrets), severity=meta.severity if meta else f.severity)


def assign_ids(findings: list[Finding]) -> list[Finding]:
    """A stable id for each finding: a hash of the rule, the path within the scanned folder,
    the redacted detail and which occurrence of that triple it is. It does not change when
    lines move, and never hashes a raw secret. SARIF uses it as a fingerprint."""
    seen: dict[tuple, int] = {}
    for f in findings:
        key = (f.rule, f.file, f.detail)
        occurrence = seen[key] = seen.get(key, -1) + 1
        f.id = hashlib.sha256(path_bytes("\0".join((*key, str(occurrence))))).hexdigest()[:32]
    return findings


def dedupe(findings: list[Finding]) -> list[Finding]:
    seen, out = set(), []
    for f in findings:
        k = (f.rule, f.file, f.line, f.detail)
        if k not in seen:
            seen.add(k)
            out.append(f)
    return sorted(out, key=lambda f: (SEVERITY_ORDER[f.severity], f.rule, f.file, f.line))
