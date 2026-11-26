"""AP01, AP02, AP05, AP06: agents whose permission checks are off, too broad, or whose settings hold secrets."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator

from ..agents import BYPASS, GATED_BYPASS, GATED_CLI
from ..jsonc import Lines
from ..limits import MAX_PER_LINE
from ..model import CheckContext, Document, Finding
from ..secrets import secret_kind
from .mentions import Mentions

# The same setting written as JSON inside another file (for example a workflow passing
# Claude Code settings). Parsed JSON files are checked structurally instead.
INLINE_DEFAULT_MODE = re.compile(r"\\?[\"']defaultMode\\?[\"'][ \t]*:[ \t]*\\?[\"']bypassPermissions\\?[\"']")
# Comment markers by file type ("" is an extensionless script, Makefile or justfile), at the
# start of a line or after a space. Block comments (/* */, docstrings) are found by mentions.Regions.
COMMENT_MARKERS = {**dict.fromkeys((".yml", ".yaml", ".sh", ".bash", ".zsh", ".fish", ".py", ".toml", ".rb", ".ps1",
                                    ".env", ".mk", ""), ("#",)),
                   **dict.fromkeys((".ini", ".cfg"), ("#", ";")),
                   **dict.fromkeys((".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".mts", ".cts", ".go", ".rs", ".java",
                                    ".kt", ".jsonc"), ("//",)),
                   **dict.fromkeys((".bat", ".cmd"), ("REM ", "rem ", "Rem ", "@REM ", "@rem ", "::"))}
SPACES = re.compile(r"\s+")
SHELL_ALLOW_ALL = {"Bash", "Bash(*)", "Bash(:*)", "Bash(**)", "Bash(*:*)", "*"}


def comment_start(line: str, markers: tuple[str, ...]) -> int:
    """Index where a trailing comment starts (outside quotes), or len(line). In double quotes
    a backslash escapes the next character; single quotes have no escapes."""
    quote, i = "", 0
    while i < len(line):
        ch = line[i]
        if quote:
            if ch == "\\" and quote == '"':
                i += 1
            elif ch == quote:
                quote = ""
        elif ch in "\"'":
            quote = ch
        else:
            for m in markers:
                if line.startswith(m, i) and (i == 0 or line[i - 1] in " \t"):
                    return i
        i += 1
    return len(line)


class PermissionFlags:
    """Bypass flags and settings written as text in any file in the folder, except Markdown.

    Raw text, not parsed facts: these flags appear in shell scripts, workflows, code and
    config of every kind. A flag that is only mentioned (see mentions.py) is not reported.
    Files on this machine are read structurally only."""
    name = "permission-flags"
    emits = ("AP01", "AP02")
    scope = "file"

    def run(self, doc: Document, ctx: CheckContext) -> Iterator[Finding]:
        src = doc.source
        suffix = Path(src.display.lower()).suffix
        if src.origin != "repo" or suffix == ".md":
            return
        text = src.text
        lines = Lines(text)
        markers = COMMENT_MARKERS.get(suffix, ())
        patterns = [BYPASS, GATED_BYPASS] + ([INLINE_DEFAULT_MODE] if suffix not in (".json", ".jsonc") else [])
        mentions = Mentions(text, suffix)
        for rx in patterns:
            per_line: dict[int, int] = {}
            comment_at: dict[int, int] = {}  # computed once per line, not per match
            for m in rx.finditer(text):
                n = lines.number(m.start())
                per_line[n] = per_line.get(n, 0) + 1
                if per_line[n] > MAX_PER_LINE:
                    continue
                start, end = lines.span(n)
                if n not in comment_at:
                    line = text[start:end]
                    skip = rx is GATED_BYPASS and not GATED_CLI.search(line)
                    comment_at[n] = -1 if skip else start + (comment_start(line, markers) if markers else len(line))
                if m.start() >= comment_at[n] or mentions.is_mention(start, text[start:end], n, m.start(), m.end()):
                    continue
                detail = "defaultMode: bypassPermissions" if rx is INLINE_DEFAULT_MODE else " ".join(m.group(0).split())
                yield Finding("AP02" if src.is_ci else "AP01", src.display, n, detail)


class ClaudeSettings:
    """Claude Code settings: allow-everything shell rules, bypass mode and secrets in env."""
    name = "claude-settings"
    emits = ("AP06", "AP01", "AP05")
    scope = "file"

    def run(self, doc: Document, ctx: CheckContext) -> Iterator[Finding]:
        perms, where, at = doc.permissions, doc.source.display, doc.line_of
        if perms is None:
            return
        for rule in perms.allow:
            if SPACES.sub("", rule) in SHELL_ALLOW_ALL:
                yield Finding("AP06", where, at(("permissions", "allow")), f'allow "{rule}"')
        if perms.default_mode == "bypassPermissions":
            yield Finding("AP01", where, at(("permissions", "defaultMode")), "defaultMode: bypassPermissions")
        for k, v in (perms.env or {}).items():
            if isinstance(v, (str, int, float)) and ctx.secrets.secret_pair(k, v):
                yield Finding("AP05", where, at(("env", str(k))), f"env.{k} = <redacted>{secret_kind(v)}")
