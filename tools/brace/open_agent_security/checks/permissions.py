"""AP01, AP02, AP05, AP06: agents whose permission checks are off, too broad, or whose settings hold secrets."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator

from ..agents import BYPASS, GATED_BYPASS, GATED_CLI, SHORT_YOLO, SHORT_YOLO_CLI
from ..jsonc import Lines
from ..limits import MAX_PER_LINE
from ..model import CheckContext, Document, Finding
from ..parse.dockerfile import is_dockerfile
from ..secrets import secret_kind
from .mentions import Mentions

# The same setting written as JSON inside another file (for example a workflow passing
# Claude Code settings). Parsed JSON files are checked structurally instead.
INLINE_DEFAULT_MODE = re.compile(r"\\?[\"']defaultMode\\?[\"'][ \t]*:[ \t]*\\?[\"']bypassPermissions\\?[\"']")
# Comment markers by file kind (see file_kind; "" is an extensionless script, Makefile or
# justfile), at the start of a line or after a space. Block comments (/* */, docstrings) are
# found by mentions.Regions.
COMMENT_MARKERS = {**dict.fromkeys((".yml", ".yaml", ".sh", ".bash", ".zsh", ".fish", ".py", ".toml", ".rb", ".ps1",
                                    ".env", ".mk", ".dockerfile", ""), ("#",)),
                   **dict.fromkeys((".ini", ".cfg"), ("#", ";")),
                   **dict.fromkeys((".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".mts", ".cts", ".go", ".rs", ".java",
                                    ".kt", ".jsonc", ".groovy"), ("//",)),
                   **dict.fromkeys((".bat", ".cmd"), ("REM ", "rem ", "Rem ", "@REM ", "@rem ", "::"))}
MAKE_NAMES = {"makefile", "gnumakefile", "justfile", ".justfile"}
# Flags that count only next to a CLI that takes them: the CLI, and whether it must come first.
GATES = {GATED_BYPASS: (GATED_CLI, False), SHORT_YOLO: (SHORT_YOLO_CLI, True)}
CONTINUATION = ("\\", "^", "`")  # a line continued on the next (shell, cmd.exe, PowerShell)
CONTINUED_LINES = 20  # lines looked back through continuations for the CLI a gated flag belongs to
SPACES = re.compile(r"\s+")
SHELL_ALLOW_ALL = {"Bash", "Bash(*)", "Bash(:*)", "Bash(**)", "Bash(*:*)", "*"}


def file_kind(display: str) -> str:
    """The kind of file, as the extension its comments follow: a Dockerfile (`Dockerfile.dev`,
    `app.dockerfile`) is ".dockerfile", `.env.example` is ".env", a Jenkinsfile is ".groovy",
    a Makefile or justfile is ""; anything else is its own extension."""
    name = display.rsplit("/", 1)[-1].lower()
    if is_dockerfile(name):
        return ".dockerfile"
    if name == ".env" or name.startswith(".env."):
        return ".env"
    if name == "jenkinsfile" or name.startswith("jenkinsfile."):
        return ".groovy"
    if name in MAKE_NAMES:
        return ""
    return Path(name).suffix


def logical_start(text: str, lines: Lines, n: int) -> int:
    """Where line n's command starts: back through lines that end with a continuation."""
    first = n
    while first > 1 and n - first < CONTINUED_LINES:
        start, end = lines.span(first - 1)
        if not text[start:end].rstrip().endswith(CONTINUATION):
            break
        first -= 1
    return lines.span(first)[0]


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
        kind = file_kind(src.display)
        if src.origin != "repo" or kind == ".md":
            return
        text = src.text
        lines = Lines(text)
        markers = COMMENT_MARKERS.get(kind, ())
        patterns = [BYPASS, GATED_BYPASS, SHORT_YOLO] + ([INLINE_DEFAULT_MODE] if kind not in (".json", ".jsonc") else [])
        mentions = Mentions(text, kind)
        for rx in patterns:
            gate = GATES.get(rx)
            per_line: dict[int, int] = {}
            comment_at: dict[int, int] = {}  # computed once per line, not per match
            cli_at: dict[int, int] = {}      # where the gating CLI first appears in the line's command, or -1
            for m in rx.finditer(text):
                n = lines.number(m.start())
                per_line[n] = per_line.get(n, 0) + 1
                if per_line[n] > MAX_PER_LINE:
                    continue
                start, end = lines.span(n)
                if n not in comment_at:
                    line = text[start:end]
                    comment_at[n] = start + (comment_start(line, markers) if markers else len(line))
                    if gate:
                        cli = gate[0].search(text, logical_start(text, lines, n), end)
                        cli_at[n] = cli.start() if cli else -1
                if m.start() >= comment_at[n] or (gate and (cli_at[n] < 0 or (gate[1] and cli_at[n] > m.start()))):
                    continue
                if mentions.is_mention(start, text[start:end], n, m.start(), m.end()):
                    continue
                detail = "defaultMode: bypassPermissions" if rx is INLINE_DEFAULT_MODE else \
                    "-y (--yolo)" if rx is SHORT_YOLO else " ".join(m.group(0).split())
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
