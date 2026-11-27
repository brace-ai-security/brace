"""What a scan runs: rules, collectors, parsers, checks and reporters, and plugin loading.

Built-ins are listed explicitly in builtin(). Plugins are installed packages that expose
`register(registry)` under the `open_agent_security.plugins` entry-point group. They are
found but never loaded unless named with --plugin or OPEN_AGENT_SECURITY_PLUGINS: a scanned
repository can never cause one to load. A loaded plugin is ordinary Python with the user's
full rights. The plugin API is provisional.
"""
from __future__ import annotations

import os
import re
from importlib.metadata import entry_points

from .catalog import RULE_ID_PATTERN, RULES, SEVERITY_ORDER, TAXONOMIES, RuleMeta
from .plugin import Check, Collector, Parser, Reporter

GROUP = "open_agent_security.plugins"
PLUGIN_ENV = "OPEN_AGENT_SECURITY_PLUGINS"
RULE_ID = re.compile(f"^{RULE_ID_PATTERN}$")
RESERVED = re.compile(r"^AP\d\d$")  # built-in rule IDs, now and future


class PluginError(Exception):
    """A plugin that is unknown, fails to load or registers something invalid. Exit code 2."""


class Registry:
    def __init__(self):
        self.rules: dict[str, RuleMeta] = {}
        self.collectors: list[Collector] = []
        self.parsers: list[Parser] = []
        self.checks: list[Check] = []
        self.reporters: dict[str, Reporter] = {}

    def add_rule(self, meta: RuleMeta) -> None:
        if not RULE_ID.match(meta.id) or meta.severity not in SEVERITY_ORDER:
            raise ValueError(f"invalid rule {meta.id!r}")
        if meta.id in self.rules:
            raise ValueError(f"duplicate rule {meta.id}")
        if any(r.partition(":")[0] not in TAXONOMIES or not r.partition(":")[2] for r in meta.refs):
            raise ValueError(f"rule {meta.id}: refs are prefix:id with a prefix in {', '.join(TAXONOMIES)}")
        if RESERVED.match(meta.id) and meta not in RULES:
            raise ValueError(f"rule IDs APnn are reserved for built-in rules: {meta.id}")
        self.rules[meta.id] = meta

    def add_collector(self, c: Collector) -> None:
        self.collectors.append(c)

    def add_parser(self, p: Parser) -> None:
        self.parsers.append(p)

    def add_check(self, c: Check) -> None:
        if c.scope not in ("file", "project") or not c.emits:
            raise ValueError(f"check {c.name}: scope must be file or project, and it must emit a rule")
        if c.scope == "project" and not callable(getattr(c, "facts", None)):
            raise ValueError(f"check {c.name}: a project check must declare facts(document)")
        unknown = [r for r in c.emits if r not in self.rules]
        if unknown:
            raise ValueError(f"check {c.name} emits unknown rule {unknown[0]}")
        self.checks.append(c)

    def add_reporter(self, r: Reporter) -> None:
        if r.name in self.reporters:
            raise ValueError(f"duplicate reporter {r.name}")
        self.reporters[r.name] = r


def builtin() -> Registry:
    """The built-in rules, collectors, parsers, checks and reporters, listed in each subpackage."""
    from . import checks, collect, parse, report

    reg = Registry()
    for meta in RULES:
        reg.add_rule(meta)
    for c in collect.BUILTIN:
        reg.add_collector(c)
    for p in parse.BUILTIN:
        reg.add_parser(p)
    for c in checks.BUILTIN:
        reg.add_check(c)
    for r in report.BUILTIN:
        reg.add_reporter(r)
    return reg


def requested(cli_names, env=None) -> list[str]:
    """Plugin names from --plugin and OPEN_AGENT_SECURITY_PLUGINS (comma-separated), in order, once each."""
    env = os.environ if env is None else env
    names = list(cli_names or []) + [n.strip() for n in env.get(PLUGIN_ENV, "").split(",")]
    return list(dict.fromkeys(n for n in names if n))


def load_plugins(reg: Registry, names) -> None:
    """Load the named plugins only. Never by path, never from the scanned folder."""
    if not names:
        return
    eps = {e.name: e for e in entry_points(group=GROUP)}
    for n in names:
        if n not in eps:
            raise PluginError(f"no installed plugin named {n!r} (group {GROUP})")
        try:
            eps[n].load()(reg)
        except Exception as e:
            raise PluginError(f"plugin {n!r} failed to load: {type(e).__name__}: {e}") from e
