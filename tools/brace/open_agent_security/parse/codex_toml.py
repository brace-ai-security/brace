"""MCP servers in Codex's config.toml: `[mcp_servers.<name>]` tables and their `.env` tables.

tomllib reads the file, behind toml_text's linear pre-scan; a file that does not parse makes
the scan incomplete. tomllib keeps no line numbers, so findings point at the line of the
server's table header, found with one bounded regex per line.
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


def key_parts(dotted: str) -> list[str]:
    return [p.strip().strip("\"'") for p in KEY_PARTS.findall(dotted)]


class TomlLines:
    """at(path) for findings: the line of the server's table (or its env table)."""

    def __init__(self, where: dict[tuple, int]):
        self.where = where

    def at(self, path: tuple) -> int:
        for k in range(len(path), 0, -1):
            if tuple(path[:k]) in self.where:
                return self.where[tuple(path[:k])]
        return 1


def table_lines(text: str) -> dict[tuple, int]:
    """The line of each [mcp_servers.<name>] and [mcp_servers.<name>.env] header."""
    where: dict[tuple, int] = {}
    for n, line in enumerate(text.split("\n"), 1):
        h = HEADER.match(line)
        m = DOTTED.match(h.group(1)) if h else None
        parts = key_parts(m.group(1)) if m else []
        if len(parts) in (2, 3) and parts[0] == "mcp_servers":
            where.setdefault(("mcp_servers", *parts[1:]), n)
    return where


def load(text: str) -> tuple[dict, dict[tuple, int]]:
    try:
        return load_toml(text), table_lines(text)
    except (ValueError, RecursionError) as e:  # TOMLDecodeError is a ValueError; deep nesting recurses
        raise ParseError("nested too deeply" if isinstance(e, RecursionError) else str(e)) from None


class CodexToml:
    name = "codex-toml"

    def claims(self, src: SourceFile) -> bool:
        return bool(CODEX_FILE.search(src.display))

    def parse(self, src: SourceFile, doc: Document) -> None:
        data, where = load(src.text)
        doc.use_lines(TomlLines(where).at)
        doc.servers += [to_server(*s) for s in servers_at(data, ("mcp_servers",))]
