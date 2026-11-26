"""TOML from untrusted text: tomllib behind a linear pre-scan.

tomllib on Python 3.11-3.13 takes time quadratic in the parts of one dotted key, so an 80 KB
`a.a.a...a = 1` costs seconds and a megabyte half an hour. Before parsing, one pass over the
text (strings and comments skipped) refuses a key or table header with more than
TOML_KEY_PARTS parts, a line longer than TOML_LINE characters, and inline tables and arrays
nested more than TOML_NESTING deep. A refusal is a ValueError, as tomllib's own errors are, so
every caller reports it the same way (a parse error for agent config, exit 2 for the config file).
"""
from __future__ import annotations

import re
import tomllib

from .limits import TOML_KEY_PARTS, TOML_LINE, TOML_NESTING

# Everything the pre-scan reacts to; other characters are skipped in bulk.
TOKEN = re.compile(r'"""|\'\'\'|["\'#.=,\[\]{}\n]')
STRING_END = {'"""': re.compile(r'\\[\s\S]|"""'), "'''": re.compile("'''"),
              '"': re.compile(r'\\[^\n]|"|\n'), "'": re.compile(r"'|\n")}


def check(text: str) -> None:
    """Raise ValueError if the text is past a bound tomllib cannot parse in linear time."""
    for line in text.split("\n"):
        if len(line) > TOML_LINE:
            raise ValueError(f"a line is longer than {TOML_LINE} characters")
    pos, dots, depth = 0, 0, 0
    while True:
        m = TOKEN.search(text, pos)
        if not m:
            return
        tok, pos = m.group(0), m.end()
        if tok in STRING_END:
            while True:
                e = STRING_END[tok].search(text, pos)
                if not e:
                    return  # unclosed: tomllib reports it
                pos = e.end()
                if e.group(0)[0] != "\\":
                    break
        elif tok == "#":
            nl = text.find("\n", pos)
            pos = len(text) if nl < 0 else nl
        elif tok == ".":
            dots += 1
            if dots >= TOML_KEY_PARTS:
                raise ValueError(f"a key has more than {TOML_KEY_PARTS} dotted parts")
        else:
            dots = 0
            if tok in "[{":
                depth += 1
                if depth > TOML_NESTING:
                    raise ValueError(f"nested more than {TOML_NESTING} deep")
            elif tok in "]}":
                depth = max(0, depth - 1)


def loads(text: str) -> dict:
    """tomllib.loads, once check() has passed."""
    check(text)
    return tomllib.loads(text)
