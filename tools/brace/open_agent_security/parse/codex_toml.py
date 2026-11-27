"""Codex's config.toml: MCP servers (`[mcp_servers.<name>]` tables and their `.env` tables) and
full access (`sandbox_mode = "danger-full-access"`, at the top level or in a profile).

tomllib reads the file, behind toml_text's linear pre-scan; a file that does not parse makes
the scan incomplete. tomllib keeps no line numbers, so findings point at the line of the
server's table header, or of another key or table, found with one bounded regex per line.
"""
from __future__ import annotations

import re

from ..agents import CODEX_FILE
from ..model import Document, ParseError, SourceFile
from ..toml_text import loads as load_toml
from .mcp_json import servers_at, to_server

HEADER = re.compile(r"^[ \t]*\[(?!\[)[ \t]*([^\]\n]{1,300})\][ \t]*(?:#.*)?$")
KEY_PART = r"(?:[A-Za-z0-9_\-]{1,200}|\"[^\"\n]{0,200}\"|'[^'\n]{0,200}')"
KEY_PARTS = re.compile(KEY_PART)
DOTTED = re.compile(rf"^[ \t]*({KEY_PART}(?:[ \t]*\.[ \t]*{KEY_PART}){{0,4}})[ \t]*$")
ASSIGNED = re.compile(rf"^[ \t]*({KEY_PART}(?:[ \t]*\.[ \t]*{KEY_PART}){{0,4}})[ \t]*=")
FULL_ACCESS = "danger-full-access"


def key_parts(dotted: str) -> list[str]:
    return [p.strip().strip("\"'") for p in KEY_PARTS.findall(dotted)]


class TomlLines:
    """at(path) for findings: for an MCP server, the line of its table (or its env table); for
    anything else, the line of the key or of the nearest table that holds it."""

    def __init__(self, where: dict[tuple, int], keys: dict[tuple, int] | None = None):
        self.where, self.keys = where, keys or {}

    def at(self, path: tuple) -> int:
        index = self.where if path[:1] == ("mcp_servers",) else self.keys
        for k in range(len(path), 0, -1):
            if tuple(path[:k]) in index:
                return index[tuple(path[:k])]
        return 1


def table_lines(text: str) -> dict[tuple, int]:
    """The line of each [mcp_servers.<name>] and [mcp_servers.<name>.env] header."""
    return lines_of(text)[0]


def lines_of(text: str) -> tuple[dict[tuple, int], dict[tuple, int]]:
    """The line of each [mcp_servers.<name>] and [mcp_servers.<name>.env] header, and of every
    table header and `key =` line (keys under their table), first occurrence kept."""
    where: dict[tuple, int] = {}
    keys: dict[tuple, int] = {}
    table: list[str] = []
    for n, line in enumerate(text.split("\n"), 1):
        h = HEADER.match(line)
        if h:
            m = DOTTED.match(h.group(1))
            table = key_parts(m.group(1)) if m else []
            if len(table) in (2, 3) and table[0] == "mcp_servers":
                where.setdefault(("mcp_servers", *table[1:]), n)
            if table:
                keys.setdefault(tuple(table), n)
            continue
        a = ASSIGNED.match(line)
        if a:
            keys.setdefault((*table, *key_parts(a.group(1))), n)
    return where, keys


def full_access(data: dict) -> list[tuple[tuple, str]]:
    """(path, detail) of each sandbox_mode = "danger-full-access", at the top level and in
    profiles.*; the detail adds `approval_policy = "never"` when the same scope sets it."""
    scopes = [((), data)]
    profiles = data.get("profiles")
    if isinstance(profiles, dict):
        scopes += [(("profiles", str(name)), p) for name, p in profiles.items() if isinstance(p, dict)]
    found = []
    for prefix, scope in scopes:
        if scope.get("sandbox_mode") == FULL_ACCESS:
            shown = ".".join((*prefix, "sandbox_mode"))
            never = " + approval_policy = \"never\"" if scope.get("approval_policy") == "never" else ""
            found.append(((*prefix, "sandbox_mode"), f'{shown} = "{FULL_ACCESS}"{never}'))
    return found


def load(text: str) -> tuple[dict, tuple[dict[tuple, int], dict[tuple, int]]]:
    try:
        return load_toml(text), lines_of(text)
    except (ValueError, RecursionError) as e:  # TOMLDecodeError is a ValueError; deep nesting recurses
        raise ParseError("nested too deeply" if isinstance(e, RecursionError) else str(e)) from None


class CodexToml:
    name = "codex-toml"

    def claims(self, src: SourceFile) -> bool:
        return bool(CODEX_FILE.search(src.display))

    def parse(self, src: SourceFile, doc: Document) -> None:
        data, (where, keys) = load(src.text)
        doc.use_lines(TomlLines(where, keys).at)
        doc.data = data
        doc.servers += [to_server(*s) for s in servers_at(data, ("mcp_servers",))]
        doc.full_access += full_access(data)
