"""Scan settings and the optional `.open-agent-security.toml` config file.

Precedence: defaults < config file < command-line flags. The config file lives in the scanned
folder, so it is untrusted input: it can never load code, its custom tokens are structured
(never regexes), its globs stay inside the folder, its limits can only go up to fixed
ceilings, and anything malformed or unknown is an error rather than silently ignored.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from .agents import CODEX_FILE
from .catalog import SEVERITY_ORDER
from .fsio import ReadFailure, read
from .toml_text import loads as load_toml
from .ignore import PathGlob, PatternTooDeep, flex, parse_pattern
from .limits import (
    CEILINGS,
    CONFIG_FILE_BYTES,
    LIMIT_KEYS,
    MAX_FLEX,
    MAX_GLOBS,
    MAX_IGNORE_RULES,
    MAX_IGNORES,
    MAX_PATTERN,
    MAX_SEGMENTS,
    MAX_TOKENS,
    TOKEN_MAX,
    TOKEN_MIN,
    Limits,
)
from .parse.mcp_json import NOT_JSON
from .secrets import CHARSETS, TOKEN_PREFIX, TokenSpec

CONFIG_FILE = ".open-agent-security.toml"
FAIL_ON = ("critical", "high", "medium", "low", "none")
KEYS = {"version", "fail-on", "rules", "ignore", "include", "agent-config", "tokens", "limits", "plugins"}


class ConfigError(Exception):
    """A config file that cannot be used as written. The scan stops with exit code 2."""


@dataclass(frozen=True)
class Config:
    root: Path | None = None                # the scanned folder
    host: bool = False                      # also scan this machine's agent settings
    fail_on: str | None = None              # None: not set here, so the default (high) applies
    rules: Mapping[str, str] = field(default_factory=dict)  # rule ID -> "off" or a severity
    ignore: tuple[PathGlob, ...] = ()
    include: tuple[PathGlob, ...] = ()   # extra files to read as text
    agent_config: tuple[PathGlob, ...] = ()  # extra files to treat as agent config
    tokens: tuple[TokenSpec, ...] = ()
    limits: Limits = Limits()
    path: str | None = None                 # the config file applied, as shown to the user
    display_prefix: str = ""                # put before repository paths in findings ("sub/" when run from the parent)
    notes: tuple[str, ...] = ()

    @property
    def disabled(self) -> frozenset[str]:
        return frozenset(r for r, v in self.rules.items() if v == "off")


def load(root: Path, known_rules, path: str | None = None, enabled: bool = True) -> Config:
    """The config for scanning `root`: `path` if given, else `.open-agent-security.toml` in the
    root (no upward search), else defaults. `enabled=False` (--no-config) skips the file."""
    base = Config(root=root)
    if not enabled:
        return base
    file = Path(path) if path else root / CONFIG_FILE
    if not path and not file.is_symlink() and not file.exists():
        return base
    # The root's config is read like any scanned file (no symlinks); an explicit --config is the user's choice.
    text = read(file, follow=bool(path), limit=CONFIG_FILE_BYTES)
    shown = str(path) if path else CONFIG_FILE
    if isinstance(text, ReadFailure):
        raise ConfigError(f"{shown}: not a readable regular file of at most {CONFIG_FILE_BYTES // 1024} KB")
    try:
        data = load_toml(text)
    except (ValueError, RecursionError) as e:  # TOMLDecodeError is a ValueError; deep nesting recurses
        reason = "nested too deeply" if isinstance(e, RecursionError) else str(e)
        raise ConfigError(f"{shown}: not valid TOML ({reason})") from None
    return parse(data, base, shown, set(known_rules))


def parse(data: dict, base: Config, shown: str, known_rules: set[str]) -> Config:
    unknown = sorted(set(data) - KEYS)
    if unknown:
        raise ConfigError(f"{shown}: unknown key {unknown[0]!r}")
    version = data.get("version", 1)
    if type(version) is not int or version != 1:
        raise ConfigError(f"{shown}: version must be 1")
    fail_on = data.get("fail-on")
    if fail_on is not None and (not isinstance(fail_on, str) or fail_on not in FAIL_ON):
        raise ConfigError(f"{shown}: fail-on must be one of {', '.join(FAIL_ON)}")
    notes = []
    if "plugins" in data:
        notes.append(f"config {shown}: 'plugins' is ignored; plugins load only with --plugin or "
                     "OPEN_AGENT_SECURITY_PLUGINS")
    limits, capped = parse_limits(data.get("limits", {}), base.limits, shown)
    notes += capped
    return Config(root=base.root, fail_on=fail_on, rules=parse_rules(data.get("rules", {}), known_rules, shown),
                  ignore=parse_ignore(data.get("ignore", []), known_rules, shown),
                  include=tuple(globs(data.get("include", []), "include", shown)),
                  agent_config=tuple(agent_config_globs(data.get("agent-config", []), shown)),
                  tokens=parse_tokens(data.get("tokens", []), shown), limits=limits, path=shown, notes=tuple(notes))


def parse_rules(rules, known: set[str], shown: str) -> dict[str, str]:
    if not isinstance(rules, dict):
        raise ConfigError(f"{shown}: rules must be a table of rule IDs")
    for rid, value in rules.items():
        if rid not in known:
            raise ConfigError(f"{shown}: unknown rule {rid!r} in rules")
        if not isinstance(value, str) or (value != "off" and value not in SEVERITY_ORDER):
            raise ConfigError(f"{shown}: rules.{rid} must be off or a severity")
    return dict(rules)


def glob(pattern, what: str, shown: str, anchor: bool = False) -> PathGlob:
    """A path glob inside the scanned folder: relative, no `..`, no backslashes. With anchor,
    one leading `/` anchors the pattern to the scanned folder, as in the ignore file."""
    if not isinstance(pattern, str) or not pattern or len(pattern) > MAX_PATTERN or not pattern.isprintable():
        raise ConfigError(f"{shown}: {what} entries must be short path globs")
    body = pattern[1:] if pattern.startswith("!") else pattern
    if anchor and body.startswith("/"):
        body = body[1:]
    if body.startswith(("/", "~")) or "\\" in body or (len(body) > 1 and body[1] == ":") \
            or any(seg in (".", "..") for seg in body.split("/")):
        raise ConfigError(f"{shown}: {what} entry {pattern!r} must be a relative path inside the folder")
    try:
        entry = parse_pattern(pattern)
    except PatternTooDeep:
        raise ConfigError(f"{shown}: {what} entry {pattern!r} has more than {MAX_SEGMENTS} folders") from None
    if entry is None:
        raise ConfigError(f"{shown}: {what} entry {pattern!r} is empty")
    return entry


def globs(items, what: str, shown: str) -> list[PathGlob]:
    if not isinstance(items, list) or len(items) > MAX_GLOBS:
        raise ConfigError(f"{shown}: {what} must be a list of at most {MAX_GLOBS} globs")
    out = [glob(p, what, shown) for p in items]
    if any(e.neg for e in out):
        raise ConfigError(f"{shown}: {what} entries cannot start with !")
    return within_budget(out, what, shown)


def agent_config_globs(items, shown: str) -> list[PathGlob]:
    """agent-config globs. Agent config is read as JSON (see parse.mcp_json.is_json), so a
    pattern naming a YAML or TOML file would silently do nothing: refused, except Codex's
    .codex/config.toml, which its own parser reads."""
    out = globs(items, "agent-config", shown)
    for pattern in items:
        if pattern.lower().endswith(NOT_JSON) and not CODEX_FILE.search(pattern):
            raise ConfigError(f"{shown}: agent-config entry {pattern!r} names a YAML or TOML file, but agent "
                              "config is read as JSON or JSONC; list it under include to scan it as text")
    return out


def within_budget(entries: list[PathGlob], what: str, shown: str) -> list[PathGlob]:
    """Matching cost grows with the segments after `**`; a list may hold MAX_FLEX of them."""
    if sum(flex(e) for e in entries) > MAX_FLEX:
        raise ConfigError(f"{shown}: {what} patterns have more than {MAX_FLEX} segments after `**` in all")
    return entries


def parse_ignore(items, known: set[str], shown: str) -> tuple[PathGlob, ...]:
    if not isinstance(items, list) or len(items) > MAX_IGNORES:
        raise ConfigError(f"{shown}: ignore must be a list of at most {MAX_IGNORES} entries")
    out: list[PathGlob] = []
    paths: list[PathGlob] = []
    for item in items:
        if not isinstance(item, dict) or set(item) - {"path", "rules", "reason"} or "path" not in item:
            raise ConfigError(f"{shown}: each [[ignore]] entry takes path, and optionally rules and reason")
        if not isinstance(item.get("reason", ""), str):
            raise ConfigError(f"{shown}: ignore reason must be text")
        rules = item.get("rules", [None])
        if not isinstance(rules, list) or not rules or any(r is not None and (not isinstance(r, str) or r not in known) for r in rules):
            raise ConfigError(f"{shown}: ignore rules must be a list of known rule IDs")
        entry = glob(item["path"], "ignore", shown, anchor=True)
        paths.append(entry)
        entry = entry._replace(text=item["path"], source=shown, reason=item.get("reason", ""))
        out += [entry._replace(rule=r) for r in rules]
    if len(out) > MAX_IGNORE_RULES:
        raise ConfigError(f"{shown}: ignore expands to more than {MAX_IGNORE_RULES} path-and-rule pairs; "
                          "leave out rules to ignore a path for every rule")
    within_budget(paths, "ignore", shown)
    return tuple(out)


def parse_tokens(items, shown: str) -> tuple[TokenSpec, ...]:
    if not isinstance(items, list) or len(items) > MAX_TOKENS:
        raise ConfigError(f"{shown}: tokens must be a list of at most {MAX_TOKENS} entries")
    out = []
    for t in items:
        if not isinstance(t, dict) or set(t) != {"name", "prefix", "charset", "min", "max"}:
            raise ConfigError(f"{shown}: each [[tokens]] entry takes exactly name, prefix, charset, min and max")
        name, prefix, charset, lo, hi = t["name"], t["prefix"], t["charset"], t["min"], t["max"]
        if not isinstance(name, str) or not 0 < len(name) <= 40:
            raise ConfigError(f"{shown}: token name must be 1 to 40 characters")
        if not isinstance(prefix, str) or not TOKEN_PREFIX.match(prefix):
            raise ConfigError(f"{shown}: token {name!r}: prefix must be 2 to 40 letters, digits, '_', '-' or '.'")
        if not isinstance(charset, str) or charset not in CHARSETS:
            raise ConfigError(f"{shown}: token {name!r}: charset must be one of {', '.join(CHARSETS)}")
        if not (is_int(lo) and is_int(hi) and TOKEN_MIN <= lo <= hi <= TOKEN_MAX):
            raise ConfigError(f"{shown}: token {name!r}: need {TOKEN_MIN} <= min <= max <= {TOKEN_MAX}")
        out.append(TokenSpec(name, prefix, charset, lo, hi))
    return tuple(out)


def parse_limits(items, defaults: Limits, shown: str) -> tuple[Limits, list[str]]:
    """The limits, and notes for values capped at a ceiling."""
    if not isinstance(items, dict) or set(items) - {key for key, _ in LIMIT_KEYS}:
        raise ConfigError(f"{shown}: limits takes {' and '.join(key for key, _ in LIMIT_KEYS)}")
    values, notes = {}, []
    for key, attr in LIMIT_KEYS:
        if key not in items:
            continue
        v = items[key]
        if not is_int(v) or v < 1:
            raise ConfigError(f"{shown}: limits.{key} must be a positive integer")
        ceiling = getattr(CEILINGS, attr)
        if v > ceiling:
            notes.append(f"config {shown}: limits.{key} capped at {ceiling}")
        values[attr] = min(v, ceiling)
    return Limits(**{**defaults.__dict__, **values}), notes


def is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)
