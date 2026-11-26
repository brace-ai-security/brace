"""The command line: arguments, outputs and exit codes.

Exit codes: 0 nothing at or above --fail-on, 1 findings at or above it or an incomplete scan,
2 a usage, config, plugin or output-file error, 3 an internal error. A crash must never look
like "found problems".
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import replace
from pathlib import Path

from . import __version__
from .catalog import SEVERITY_ORDER
from .config import FAIL_ON, Config, ConfigError, load
from .engine import run_scan
from .fsio import write_new
from .limits import NOTE_CHARS
from .model import Report
from .output import clean, defuse, inert
from .registry import PluginError, Registry, builtin, load_plugins, requested
from .report import ReportOptions


def add_arguments(p: argparse.ArgumentParser) -> None:
    """The scan arguments, shared by `open-agent-security` and `brace.py scan`."""
    p.add_argument("path", nargs="?", default=".", help="folder to scan (default: .)")
    p.add_argument("--host", action="store_true", help="also read the agent and MCP settings on this machine")
    p.add_argument("--json", action="store_true", help="print JSON instead of text (same as --output json=-)")
    p.add_argument("--fail-on", choices=FAIL_ON, default=None,
                   help="exit 1 when a finding is this severe or worse, or the scan is incomplete (default: high)")
    p.add_argument("--output", metavar="NAME=FILE", action="append", default=[], type=output_arg,
                   help="also write the NAME report to FILE (repeatable): text, json, sarif, markdown, gitlab-sast, "
                        "junit, or a plugin's; FILE - replaces the report on stdout")
    p.add_argument("--sarif", metavar="FILE",
                   help="also write SARIF (GitHub code scanning) to FILE (--output sarif=FILE)")
    p.add_argument("--markdown", metavar="FILE",
                   help="also append a Markdown summary to FILE (--output markdown=FILE)")
    p.add_argument("--github-output", metavar="FILE", help=argparse.SUPPRESS)
    p.add_argument("--config", metavar="FILE", help="read settings from FILE instead of .open-agent-security.toml")
    p.add_argument("--no-config", action="store_true", help="ignore .open-agent-security.toml")
    p.add_argument("--plugin", metavar="NAME", action="append", default=[],
                   help="load an installed plugin (repeatable); plugins run as ordinary Python")
    p.add_argument("--list-rules", action="store_true", help="list the rules (with --json, as JSON) and exit")


def output_arg(value: str) -> tuple[str, str]:
    name, eq, target = value.partition("=")
    if not (eq and name and target):
        raise argparse.ArgumentTypeError(f"expected NAME=FILE, got {value!r}")
    return name, target


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="open-agent-security",
                                description="Find known-dangerous AI agent setups. Local and read-only.")
    add_arguments(p)
    p.add_argument("--version", action="version", version=f"open-agent-security {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    return run_args(build_parser().parse_args(argv))


def run_args(a: argparse.Namespace) -> int:
    """Run parsed arguments; shared by `open-agent-security` and `brace.py scan`."""
    for stream in (sys.stdout, sys.stderr):  # file names may not fit the console's encoding
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    try:
        return run(a)
    except Exception as e:  # never let a crash look like "found problems" (exit 1)
        error(f"internal error: {type(e).__name__}: {clean(e, NOTE_CHARS)}")
        return 3


def actions_log() -> bool:
    """Output goes to a GitHub Actions log, which runs workflow commands it finds."""
    return bool(os.environ.get("GITHUB_ACTIONS"))


def error(message: str) -> None:
    line = f"open-agent-security: {message}"
    print(defuse(line) if actions_log() else line, file=sys.stderr)


def run(a: argparse.Namespace) -> int:
    root = Path(a.path).resolve()
    if not root.is_dir():
        error(f"not a folder: {clean(a.path)}")
        return 2
    try:
        registry = builtin()
        load_plugins(registry, requested(a.plugin))
        config = resolve_config(a, root, registry)
    except (ConfigError, PluginError) as e:
        error(clean(e, NOTE_CHARS))
        return 2
    if a.list_rules:
        sys.stdout.write(rule_list(registry, config.rules, a.json))
        return 0
    try:
        stdout, files = outputs(a, registry)
    except ValueError as e:
        error(str(e))
        return 2
    report = run_scan(config, registry)
    try:
        write_outputs(report, registry, stdout, files)
    except OSError as e:
        error(f"could not write output: {clean(e, NOTE_CHARS)}")
        return 2
    return exit_code(report, config.fail_on)


def resolve_config(a: argparse.Namespace, root: Path, registry: Registry) -> Config:
    """The config file's settings with the command line on top: defaults < config file < flags.
    The Action always passes --fail-on, so a config file in a pull request cannot lower its gate."""
    config = load(root, registry.rules, a.config, not a.no_config)
    notes = config.notes
    if not a.fail_on and config.fail_on:
        notes += (f"config {config.path}: fail-on {config.fail_on} (the exit code follows the config file, "
                  "not the default high)",)
    return replace(config, host=a.host, fail_on=a.fail_on or config.fail_on or "high", notes=notes,
                   display_prefix=display_prefix(root))


def display_prefix(root: Path) -> str:
    """The scanned folder relative to the current one, when it is inside it, so SARIF annotations
    and messages point at the right file in the repository; '' otherwise."""
    try:
        prefix = root.relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return ""
    return "" if prefix == "." else prefix + "/"


def outputs(a: argparse.Namespace, registry: Registry) -> tuple[str, list[tuple[str, str]]]:
    """The reporter for stdout and the (reporter, file) pairs to write, from --output and its
    aliases. Raises ValueError for an unknown reporter or more than one on stdout."""
    files = list(a.output) + [(name, target) for name, target in (
        ("sarif", a.sarif), ("markdown", a.markdown), ("github-output", a.github_output)) if target]
    unknown = sorted({name for name, _ in files} - set(registry.reporters))
    if unknown:
        raise ValueError(f"no output format {clean(unknown[0])!r}; choose from {', '.join(registry.reporters)}")
    to_stdout = [name for name, target in files if target == "-"]
    if len(to_stdout) > 1 or (to_stdout and a.json):
        raise ValueError("only one report can go to stdout")
    stdout = to_stdout[0] if to_stdout else "json" if a.json else "text"
    return stdout, [(name, target) for name, target in files if target != "-"]


def write_outputs(report: Report, registry: Registry, stdout: str, files: list[tuple[str, str]]) -> None:
    """The stdout report, made inert for a GitHub Actions log, then each output file."""
    out = sys.stdout
    reporter = registry.reporters[stdout]
    color = hasattr(out, "isatty") and out.isatty() and not os.environ.get("NO_COLOR")
    rendered = reporter.render(report, ReportOptions(color=bool(color)))
    # A plugin reporter that declares no media is treated as text, so it is defused too.
    out.write(inert(rendered, getattr(reporter, "media", "text")) if actions_log() else rendered)
    for name, target in files:
        reporter = registry.reporters[name]
        write_new(target, reporter.render(report, ReportOptions()), append=getattr(reporter, "appends", False))


def exit_code(report: Report, fail_on: str) -> int:
    """1 when a finding is at or above fail_on, or the scan is incomplete (unless fail_on is none)."""
    limit = {"none": -1, **SEVERITY_ORDER}[fail_on]
    failed = any(SEVERITY_ORDER[f.severity] <= limit for f in report.findings) \
        or (report.verdict == "incomplete" and limit >= 0)
    return 1 if failed else 0


def rule_list(registry: Registry, overrides, as_json: bool) -> str:
    """Every registered rule with its effective severity, and whether the config turned it off."""
    rows = [(m, overrides.get(m.id, m.severity)) for m in registry.rules.values()]
    if as_json:
        return json.dumps({"rules": [{"id": m.id, "title": m.title, "severity": m.severity if s == "off" else s,
                                      "enabled": s != "off", "why": m.why, "fix": m.fix,
                                      "checklist": list(m.checklist), "help_uri": m.help_uri} for m, s in rows]},
                          indent=2) + "\n"
    return "".join(f"{m.id:6} {s:9} {m.title}\n" for m, s in rows)
