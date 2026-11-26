"""JSON with comments: tolerant loading, and line numbers for positions and JSON paths.

Agent config files are often JSONC (VS Code, Cursor). Findings point at lines, so the
scanner maps a JSON path back to the line of its key without a second parser. Every pass
here is linear in the size of the text.
"""
from __future__ import annotations

import bisect
import json
import re

from .limits import JSON_INDEX_DEPTH, JSON_INDEX_KEYS

NEWLINE = re.compile("\n")


def strip_jsonc(text: str) -> str:
    """Remove // and /* */ comments and trailing commas outside strings, keeping line breaks."""
    out: list[str] = []
    i, n, in_str = 0, len(text), False
    pending_comma = -1  # index in `out` of a comma that may turn out to be trailing
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if c == '"':
                in_str = False
        elif c == '"':
            in_str = True
            pending_comma = -1
            out.append(c)
        elif text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            out.append("\n" * text.count("\n", i, n if j < 0 else j + 2))
            i = n if j < 0 else j + 2
            continue
        elif c in "}]":
            if pending_comma >= 0:
                out[pending_comma] = ""
            pending_comma = -1
            out.append(c)
        elif c == ",":
            pending_comma = len(out)
            out.append(c)
        else:
            if not c.isspace():
                pending_comma = -1
            out.append(c)
        i += 1
    return "".join(out)


def load_json_text(text: str):
    """(data, None) for JSON or JSONC, else (None, the error's type name)."""
    try:
        return json.loads(text), None
    except (ValueError, RecursionError):
        pass
    try:
        return json.loads(strip_jsonc(text)), None
    except (ValueError, RecursionError) as e:
        return None, type(e).__name__


class Lines:
    """Line numbers and line text for positions in a text, in O(log n) per lookup."""

    def __init__(self, text: str):
        self.text = text
        self.breaks = [m.start() for m in NEWLINE.finditer(text)]

    def number(self, pos: int) -> int:
        return bisect.bisect_right(self.breaks, pos - 1) + 1

    def span(self, n: int) -> tuple[int, int]:
        start = self.breaks[n - 2] + 1 if n >= 2 else 0
        end = self.breaks[n - 1] if n - 1 < len(self.breaks) else len(self.text)
        return start, end


class JsonLines:
    """at(path): the line of the object key at a JSON path such as ("mcpServers", "github",
    "env", "TOKEN"); the nearest indexed parent when the exact key isn't found, else 1.
    Built lazily on first use in one linear, string-aware pass (JSONC comments allowed)."""

    def __init__(self, text: str):
        self.text = text
        self.where: dict[tuple, int] | None = None

    def _index(self) -> dict[tuple, int]:
        text, n, i = self.text, len(self.text), 0
        where: dict[tuple, int] = {}
        stack: list[list] = []  # [kind 'o'|'a', key or index, expecting key]
        while i < n:
            c = text[i]
            if c == '"':
                start, j = i, i + 1
                while j < n and text[j] != '"':
                    j += 2 if text[j] == "\\" else 1
                raw, i = text[start + 1: j], j + 1
                top = stack[-1] if stack else None
                if top and top[0] == "o" and top[2]:
                    k = i
                    while k < n and text[k] in " \t\n":
                        k += 1
                    if k < n and text[k] == ":":
                        try:
                            key = json.loads(f'"{raw}"') if "\\" in raw else raw
                        except ValueError:
                            key = raw
                        top[1], top[2] = key, False
                        if len(stack) <= JSON_INDEX_DEPTH and len(where) < JSON_INDEX_KEYS:
                            where.setdefault(tuple(f[1] for f in stack), start)
                continue
            if c == "/" and text.startswith("//", i):
                j = text.find("\n", i)
                i = n if j < 0 else j
                continue
            if c == "/" and text.startswith("/*", i):
                j = text.find("*/", i + 2)
                i = n if j < 0 else j + 2
                continue
            if c == "{":
                stack.append(["o", None, True])
            elif c == "[":
                stack.append(["a", 0, False])
            elif c in "}]":
                if stack:
                    stack.pop()
            elif c == "," and stack:
                top = stack[-1]
                if top[0] == "o":
                    top[1], top[2] = None, True
                else:
                    top[1] += 1
            i += 1
        return where

    def at(self, path: tuple) -> int:
        if self.where is None:
            self.where = self._index()
            self.lines = Lines(self.text)
        for k in range(len(path), 0, -1):
            pos = self.where.get(tuple(path[:k]))
            if pos is not None:
                return self.lines.number(pos)
        return 1
